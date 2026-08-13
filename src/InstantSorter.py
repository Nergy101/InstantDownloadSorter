#!/usr/bin/env python3
"""
Instant Download Sorter — a modern, sleek curses TUI.

Sorts everything in a folder (default ~/Downloads) into extension-based
subfolders configured in settings.json. Keyboard-driven, undoable, with
a lazygit-style panel layout.

Keys:
    j/k or up/down : move selection
    tab or h/l     : switch between the Files and Plan panels
    g/G            : jump to first/last
    space          : exclude/include the selected file from the sort
    a              : exclude/include everything
    s              : sort now (asks for confirmation first)
    u              : undo the last sort (repeat to walk further back)
    r              : rescan the folder
    ?              : help
    q              : quit
"""

import curses
import errno
import json
import os
import shutil
import stat
import time
from pathlib import Path

# ---------------------------------------------------------------- config ---

SETTINGS_NAME = "settings.json"


def expand(path):
    """Resolve ~ and $VARS. Settings are hand-written, so accept both."""
    return os.path.abspath(os.path.expanduser(os.path.expandvars(path)))


def settings_path():
    """Find settings.json next to this script first, then the working dir, so
    the tool runs from anywhere instead of only from the repo root."""
    here = Path(__file__).resolve().parent
    cwd = Path.cwd()
    for candidate in (here / SETTINGS_NAME, here.parent / SETTINGS_NAME,
                      cwd / "src" / SETTINGS_NAME, cwd / SETTINGS_NAME):
        if candidate.is_file():
            return candidate
    return None


def load_config():
    """Return (folder_location, folders) from settings.json.
    folders is a list of (name, [extensions]) in config order; first match wins."""
    path = settings_path()
    if path is None:
        raise FileNotFoundError(
            "settings.json not found next to %s or in %s"
            % (Path(__file__).resolve().parent, Path.cwd())
        )
    with open(path, "r") as f:
        settings = json.load(f)

    raw = str(settings.get("FolderLocation") or "").strip()
    location = expand(raw) if raw else str(Path.home() / "Downloads")
    folders = []
    for entry in settings.get("Folders", []):
        for name, exts in entry.items():
            folders.append((name, [str(e).lower() for e in exts]))
    return location, folders


# ----------------------------------------------------------------- model ---

def classify(folders, filename):
    """Return the target folder name for filename, or None if unclassified."""
    ext = os.path.splitext(filename)[1].lower()
    if not ext:
        return None
    for name, exts in folders:
        if ext in exts:
            return name
    return None


def move_file(src, dst):
    """Rename, falling back to a copy when src and dst are on different
    filesystems (external drives mounted under the sorted folder)."""
    try:
        os.rename(src, dst)
    except OSError as e:
        if e.errno != errno.EXDEV:
            raise
        shutil.move(src, dst)


class Sorter:
    """Pure model: scan, classify, sort, undo. No curses here."""

    def __init__(self, location, folders):
        self.location = location
        self.folders = folders
        self.files = []          # dicts: name, target, excluded, size, mtime
        self.selected = 0
        self.undo_stack = []     # one [(src, dst), ...] batch per sort
        self.last_summary = None
        self.status = ""
        self._created_dirs = set()

    # --- reading ---
    def scan(self):
        """Rebuild the file list. Exclusions and the cursor survive a rescan;
        losing them on every 'r' made the exclude flow useless."""
        excluded = {r["name"] for r in self.files if r["excluded"]}
        cursor = self.files[self.selected]["name"] if self.files else None
        try:
            entries = os.listdir(self.location)
        except OSError as e:
            self.files, self.selected = [], 0
            self.status = "Cannot read %s — %s" % (self.location, e.strerror or e)
            return []
        rows = []
        for name in entries:
            if name.startswith("."):
                continue
            try:
                st = os.stat(os.path.join(self.location, name))
            except OSError:
                continue                    # vanished mid-scan, or a dead link
            if stat.S_ISDIR(st.st_mode):
                continue
            rows.append({
                "name": name,
                "target": classify(self.folders, name),
                "excluded": name in excluded,
                "size": st.st_size,
                "mtime": st.st_mtime,
            })
        rows.sort(key=lambda r: (r["target"] is None, r["name"].lower()))
        self.files = rows
        self.selected = 0
        if cursor is not None:
            for i, r in enumerate(rows):
                if r["name"] == cursor:
                    self.selected = i
                    break
        self.selected = min(self.selected, max(0, len(rows) - 1))
        return rows

    def pending(self):
        """Files that would actually move if you sorted right now."""
        return [r for r in self.files
                if r["target"] is not None and not r["excluded"]]

    # --- editing the plan ---
    def toggle_exclude(self):
        if not self.files:
            return
        row = self.files[self.selected]
        if row["target"] is None:
            self.status = "No target folder for this file — it already stays put"
            return
        row["excluded"] = not row["excluded"]
        self.status = ("Excluded: %s (will stay put)" if row["excluded"]
                       else "Included again: %s") % row["name"]

    def toggle_all(self):
        matched = [r for r in self.files if r["target"] is not None]
        if not matched:
            self.status = "Nothing matched — no exclusions to toggle"
            return
        exclude = not all(r["excluded"] for r in matched)
        for r in matched:
            r["excluded"] = exclude
        self.status = ("Excluded all %d matched file(s)" if exclude
                       else "Included all %d matched file(s)") % len(matched)

    # --- writing ---
    def sort(self):
        """Move all non-excluded classified files. Returns (moves, errors).

        Collisions are detected before the move: os.rename replaces an existing
        destination silently on POSIX, so the old `except FileExistsError`
        branch never ran and a same-named file in the target folder was
        destroyed without a word."""
        moves, errors, created = [], [], []
        for row in self.files:
            if row["target"] is None or row["excluded"]:
                continue
            src = os.path.join(self.location, row["name"])
            dst_dir = os.path.join(self.location, row["target"])
            dst = os.path.join(dst_dir, row["name"])
            if os.path.lexists(dst):
                errors.append("%s — already in %s, left alone"
                              % (row["name"], row["target"]))
                continue
            try:
                if not os.path.isdir(dst_dir):
                    os.makedirs(dst_dir, exist_ok=True)
                    created.append(dst_dir)
                move_file(src, dst)
                moves.append((src, dst))
            except OSError as e:
                errors.append("%s — %s" % (row["name"], e.strerror or e))
        if moves:
            self.undo_stack.append(moves)
        self._created_dirs.update(created)
        self._prune_empty_folders()
        self.scan()
        by_folder = {}
        for _src, dst in moves:
            folder = os.path.basename(os.path.dirname(dst))
            by_folder[folder] = by_folder.get(folder, 0) + 1
        self.last_summary = {"by_folder": by_folder, "errors": errors,
                             "moves": moves}
        self.status = "Sorted %d file(s)" % len(moves)
        if errors:
            self.status += " · %d conflict(s) skipped" % len(errors)
        return moves, errors

    def undo(self):
        """Reverse the most recent sort. Repeat to walk further back."""
        if not self.undo_stack:
            self.status = "Nothing to undo"
            return False
        batch = self.undo_stack.pop()
        undone, errors = 0, []
        for src, dst in reversed(batch):
            if os.path.lexists(src):
                errors.append("%s — something took its place"
                              % os.path.basename(src))
                continue
            try:
                os.makedirs(os.path.dirname(src), exist_ok=True)
                move_file(dst, src)
                undone += 1
            except OSError as e:
                errors.append("%s — %s" % (os.path.basename(dst),
                                           e.strerror or e))
        self._prune_empty_folders()
        self.scan()
        self.status = "Undid %d move(s)" % undone
        if self.undo_stack:
            self.status += " · %d sort(s) left to undo" % len(self.undo_stack)
        if errors:
            self.status += " · %d problem(s)" % len(errors)
        return True

    def _prune_empty_folders(self):
        """Only clean up folders this session created and then emptied. The
        old version rmdir'd any empty folder whose name matched the config,
        deleting folders the user had made on purpose."""
        for path in sorted(self._created_dirs, key=len, reverse=True):
            try:
                if os.path.isdir(path) and not os.listdir(path):
                    os.rmdir(path)
                    self._created_dirs.discard(path)
            except OSError:
                pass


# ------------------------------------------------------------------- ui ----

PALETTE = [11, 13, 14, 12, 9, 5, 3, 6]   # bright colors for folder badges

# xterm base-16 colors
BASE16 = [
    (0, 0, 0), (205, 49, 49), (13, 188, 121), (229, 229, 16),
    (36, 114, 200), (188, 63, 188), (17, 168, 205), (229, 229, 229),
    (102, 102, 102), (241, 76, 76), (35, 209, 139), (245, 245, 67),
    (59, 142, 234), (214, 112, 214), (41, 184, 219), (255, 255, 255),
]

BORDER, BORDER_ON, HEADER, ACCENT, SELECTED = 1, 2, 3, 4, 5
SELECTED_DIM, UNCLASS, DIM, EXCLUDED, FOOTER, FOOTER_KEY = 6, 7, 8, 9, 10, 11
BADGE_BASE = 20                          # pairs 20.. hold the folder palette


def _pair(idx, fg, bg):
    """init_pair that degrades instead of exploding on 8/16-colour terminals."""
    try:
        curses.init_pair(idx, fg, bg)
    except (curses.error, ValueError):
        try:
            curses.init_pair(idx, fg % 8, -1)
        except (curses.error, ValueError):
            pass


def setup_colors():
    curses.start_color()
    curses.use_default_colors()          # -1 = terminal default bg
    _pair(BORDER, 8, -1)                 # idle panel recedes
    _pair(BORDER_ON, 10, -1)             # focused panel: bright green
    _pair(HEADER, 10, -1)
    _pair(ACCENT, 14, -1)
    _pair(SELECTED, 0, 250)              # dark text on light gray row
    _pair(SELECTED_DIM, 252, 238)        # cursor in the unfocused panel
    _pair(UNCLASS, 8, -1)                # gray
    _pair(DIM, 8, -1)
    _pair(EXCLUDED, 9, -1)               # red
    _pair(FOOTER, 252, 238)
    _pair(FOOTER_KEY, 0, 250)
    for i, color in enumerate(PALETTE):
        _pair(BADGE_BASE + i, color, -1)


def draw_box(win, y, x, h, w, title=None, focused=False, count=None):
    """Single-line border. The focused panel glows, the idle one recedes —
    that contrast is how you tell where the keys go."""
    a = curses.color_pair(BORDER_ON) | curses.A_BOLD if focused \
        else curses.color_pair(BORDER)
    try:
        win.addch(y, x, "\u250c", a)                   # ┌
        win.addch(y, x + w - 1, "\u2510", a)           # ┐
        win.addch(y + h - 1, x, "\u2514", a)           # └
        win.addch(y + h - 1, x + w - 1, "\u2518", a)   # ┘
        for i in range(1, w - 1):
            win.addch(y, x + i, "\u2500", a)           # ─
            win.addch(y + h - 1, x + i, "\u2500", a)
        for i in range(1, h - 1):
            win.addch(y + i, x, "\u2502", a)           # │
            win.addch(y + i, x + w - 1, "\u2502", a)
        if title:
            attr = curses.A_BOLD | curses.color_pair(
                HEADER if focused else BORDER)
            win.addnstr(y, x + 2, " %s " % title, w - 4, attr)
        if count and w > len(count) + 8:
            # bottom-right of the border, the way lazygit reports position
            win.addnstr(y + h - 1, x + w - 3 - len(count), " %s " % count,
                        len(count) + 2, a)
    except curses.error:
        pass


class App:
    FILES, PLAN = 0, 1

    def __init__(self, stdscr, sorter):
        self.stdscr = stdscr
        self.s = sorter
        self.modal = None            # (kind, [lines], title)
        self.running = True
        self.focus = self.FILES
        self.files_top = 0
        self.plan_top = 0
        self.plan_sel = 0
        self.plan_follow = False     # Plan chases Files only after a real move

    # --- layout ---
    def layout(self):
        return self.stdscr.getmaxyx()

    def panel_rects(self, h, w):
        """Row 0 is the header, the bottom two rows are status + footer.
        The panels used to start at row 0 and paint straight over the header."""
        mid = max(30, int(w * 0.60))
        return (1, 0, h - 3, mid), (1, mid, h - 3, w - mid)

    # --- primitives ---
    def _put(self, y, x, text, n, attr=0):
        """addnstr that tolerates the edges instead of aborting the frame."""
        if n <= 0 or y < 0 or x < 0:
            return
        try:
            self.stdscr.addnstr(y, x, text, n, attr)
        except curses.error:
            pass

    @staticmethod
    def _ellipsis(text, width):
        if width <= 1 or len(text) <= width:
            return text
        return text[:width - 1] + "\u2026"

    @staticmethod
    def _viewport(cursor, total, height, top):
        """Sticky window with a small scrolloff. The old formula was
        `top = cursor - height + 1`, which pinned the cursor to the bottom row
        and scrolled the entire list on every single keypress."""
        if total <= height or height <= 0:
            return 0
        pad = min(2, max(0, (height - 1) // 2))
        top = max(0, min(top, total - height))
        if cursor - pad < top:
            top = cursor - pad
        elif cursor + pad > top + height - 1:
            top = cursor + pad - height + 1
        return max(0, min(top, total - height))

    def _scrollbar(self, iy, ix, ih, iw, total, top):
        if total <= ih or ih <= 0:
            return
        bar_h = max(1, ih * ih // total)
        bar_y = iy + (ih - bar_h) * top // max(1, total - ih)
        for i in range(bar_h):
            self._put(bar_y + i, ix + iw - 1, "\u2503", 1,
                      curses.color_pair(BORDER_ON))

    def _badge_attr(self, target):
        """Each configured folder keeps its own colour, so the badges become
        scannable. PALETTE was defined but never actually reached before."""
        for i, (name, _exts) in enumerate(self.s.folders):
            if name == target:
                return curses.color_pair(BADGE_BASE + i % len(PALETTE))
        return curses.color_pair(UNCLASS)

    @staticmethod
    def _badge_text(row):
        if row["excluded"]:
            return "[excluded]"
        if row["target"] is None:
            return "[no match]"
        return "[%s]" % row["target"]

    @staticmethod
    def _human_size(n):
        if n < 1024:
            return "%d B" % n
        if n < 1024 * 1024:
            return "%.1f KB" % (n / 1024.0)
        if n < 1024 * 1024 * 1024:
            return "%.1f MB" % (n / 1048576.0)
        return "%.1f GB" % (n / 1073741824.0)

    @staticmethod
    def _human_age(secs):
        secs = max(0.0, secs)
        if secs < 60:
            return "just now"
        if secs < 3600:
            return "%d min ago" % int(secs // 60)
        if secs < 86400:
            return "%d h ago" % int(secs // 3600)
        return "%d d ago" % int(secs // 86400)

    # --- drawing ---
    def draw(self):
        self.stdscr.erase()
        h, w = self.layout()
        if h < 12 or w < 60:
            self._put(0, 0, "Terminal too small — resize to at least 60x12",
                      w - 1, curses.A_BOLD)
            self.stdscr.refresh()
            return
        files_rect, plan_rect = self.panel_rects(h, w)
        self.draw_header(w)
        self.draw_files_panel(files_rect)
        self.draw_plan_panel(plan_rect)
        self.draw_status(h, w)
        self.draw_footer(h, w)
        if self.modal:
            self.draw_modal()
        self.stdscr.refresh()

    def draw_header(self, w):
        title = " Instant Download Sorter "
        self._put(0, 0, title, w, curses.A_BOLD | curses.color_pair(HEADER))
        n, n_move = len(self.s.files), len(self.s.pending())
        right = " %d file%s · %d to move " % (n, "" if n == 1 else "s", n_move)
        room = w - len(title) - len(right) - 1
        if room > 4:
            self._put(0, len(title), self._ellipsis(self.s.location, room),
                      room, curses.color_pair(DIM))
        self._put(0, max(0, w - len(right) - 1), right, len(right),
                  curses.A_BOLD | curses.color_pair(ACCENT))

    def draw_files_panel(self, rect):
        y0, x0, ph, pw = rect
        focused = self.focus == self.FILES
        rows = self.s.files
        count = "%d of %d" % (self.s.selected + 1, len(rows)) if rows else None
        draw_box(self.stdscr, y0, x0, ph, pw, "Files", focused, count)
        iy, ix, ih, iw = y0 + 1, x0 + 1, ph - 2, pw - 2
        if not rows:
            self._put(iy + max(0, ih // 2 - 1), ix + 2,
                      "Nothing to sort — all clear", iw - 2,
                      curses.A_BOLD | curses.color_pair(HEADER))
            return
        self.files_top = self._viewport(self.s.selected, len(rows), ih,
                                        self.files_top)
        top = self.files_top
        now = time.time()
        # Column widths come from every row, not the visible ones, so nothing
        # shifts while scrolling. A column that renders the same string on every
        # row discriminates nothing, so it is not drawn at all.
        badge_w = min(20, max(len(self._badge_text(r)) for r in rows))
        sizes = [self._human_size(r["size"]) for r in rows]
        ages = [self._human_age(now - r["mtime"]) for r in rows]
        size_w = max(len(s) for s in sizes) if len(set(sizes)) > 1 else 0
        age_w = max(len(a) for a in ages) if len(set(ages)) > 1 else 0
        name_room = iw - 5 - badge_w - (size_w + 2 if size_w else 0) \
            - (age_w + 2 if age_w else 0)
        # Pack the columns against the names instead of flinging the tail to the
        # right edge; a 50-column gutter made rows impossible to track across.
        name_w = max(6, min(name_room, max(len(r["name"]) for r in rows)))
        for i in range(min(ih, len(rows) - top)):
            row = rows[top + i]
            y = iy + i
            sel = (top + i) == self.s.selected
            base = 0
            if sel:
                base = curses.color_pair(SELECTED if focused else SELECTED_DIM)
                self._put(y, ix, " " * iw, iw, base)
            self._put(y, ix, " \u25b8 " if sel else "   ", 3,
                      base | curses.A_BOLD)
            nattr = base
            if not sel:
                if row["excluded"]:
                    nattr = curses.color_pair(EXCLUDED)
                elif row["target"] is None:
                    nattr = curses.color_pair(UNCLASS)
            self._put(y, ix + 3, self._ellipsis(row["name"], name_w), name_w,
                      nattr)
            x = ix + 3 + name_w + 2
            dim = base if sel else curses.color_pair(DIM)
            if size_w:
                self._put(y, x, "%*s" % (size_w, sizes[top + i]), size_w, dim)
                x += size_w + 2
            if age_w:
                self._put(y, x, "%-*s" % (age_w, ages[top + i]), age_w, dim)
                x += age_w + 2
            battr = base | curses.A_BOLD
            if not sel:
                battr = curses.A_BOLD | (
                    curses.color_pair(EXCLUDED) if row["excluded"]
                    else curses.color_pair(UNCLASS) if row["target"] is None
                    else self._badge_attr(row["target"]))
            self._put(y, x, self._ellipsis(self._badge_text(row), badge_w),
                      badge_w, battr)
        self._scrollbar(iy, ix, ih, iw, len(rows), top)

    def plan_rows(self):
        """Rows for the Plan panel: (kind, text, file_name_or_None).
        kind is 'folder' (group header) or 'file'. Files group under their
        destination folder; excluded + unmatched files group under 'stays put'."""
        rows = []
        for name, _exts in self.s.folders:
            files = [r for r in self.s.files
                     if r["target"] == name and not r["excluded"]]
            if not files:
                continue
            rows.append(("folder", "%s (%d)" % (name, len(files)), None))
            for r in files:
                rows.append(("file", r["name"], r["name"]))
        stays = [r for r in self.s.files if r["excluded"] or r["target"] is None]
        if stays:
            rows.append(("folder", "stays put (%d)" % len(stays), None))
            for r in stays:
                rows.append(("file", r["name"], r["name"]))
        return rows

    def plan_cursor(self, rows):
        """Which plan row is highlighted. With the Plan panel focused the
        cursor is authoritative; otherwise it follows the Files selection."""
        if not rows:
            return 0
        if self.focus == self.PLAN:
            self.plan_sel = max(0, min(self.plan_sel, len(rows) - 1))
            return self.plan_sel
        name = self.s.files[self.s.selected]["name"] if self.s.files else None
        for i, (_k, _t, n) in enumerate(rows):
            if n == name:
                return i
        return 0

    def draw_plan_panel(self, rect):
        y0, x0, ph, pw = rect
        focused = self.focus == self.PLAN
        iy, ix, ih, iw = y0 + 1, x0 + 1, ph - 2, pw - 2
        list_h = ih - 1                   # bottom line is the consequence
        rows = self.plan_rows()
        n_files = sum(1 for k, _t, _n in rows if k == "file")
        cur = self.plan_cursor(rows) if rows else 0
        rank = sum(1 for k, _t, _n in rows[:cur + 1] if k == "file")
        count = "%d of %d" % (max(1, rank), n_files) if n_files else None
        draw_box(self.stdscr, y0, x0, ph, pw, "Plan", focused, count)
        if not rows:
            self._put(iy + 1, ix + 1, "Nothing to sort — all clear", iw - 2,
                      curses.A_BOLD | curses.color_pair(HEADER))
        else:
            # Only chase the Files cursor once the user has actually moved it.
            # Following it on the first frame opened the panel mid-list, which
            # made the very first impression look like a scrolled-away mess.
            if focused or self.plan_follow:
                self.plan_top = self._viewport(cur, len(rows), list_h,
                                               self.plan_top)
            top = self.plan_top
            by_name = {r["name"]: r for r in self.s.files}
            for i in range(min(list_h, len(rows) - top)):
                kind, text, name = rows[top + i]
                y = iy + i
                sel = (top + i) == cur
                base = 0
                if sel:
                    base = curses.color_pair(
                        SELECTED if focused else SELECTED_DIM)
                    self._put(y, ix, " " * iw, iw, base)
                if kind == "folder":
                    label = text.split(" ")[0]
                    attr = base if sel else (
                        curses.color_pair(UNCLASS) if label == "stays"
                        else self._badge_attr(label))
                    self._put(y, ix + 1, "\u25be " + self._ellipsis(text, iw - 4),
                              iw - 2, attr | curses.A_BOLD)
                else:
                    r = by_name.get(name)
                    if sel:
                        mark = "\u25b8 "
                    elif r and r["excluded"]:
                        mark = "\u2717 "
                    else:
                        mark = "  "
                    attr = base
                    if not sel:
                        attr = (curses.color_pair(EXCLUDED) if r and r["excluded"]
                                else curses.color_pair(UNCLASS)
                                if r and r["target"] is None
                                else curses.color_pair(DIM))
                    self._put(y, ix + 2, mark + self._ellipsis(text, iw - 6),
                              iw - 3, attr | (curses.A_BOLD if sel else 0))
            self._scrollbar(iy, ix, list_h, iw, len(rows), top)
        self.draw_plan_summary(iy, ix, ih, iw)

    def draw_plan_summary(self, iy, ix, ih, iw):
        """Bottom line of the Plan panel: the consequence preview."""
        n_move = len(self.s.pending())
        n_excluded = sum(1 for r in self.s.files if r["excluded"])
        n_unclass = sum(1 for r in self.s.files if r["target"] is None)

        def build(long):
            if not n_move:
                parts = ["nothing to move"]
            elif long:
                parts = ["%d file%s will move"
                         % (n_move, "" if n_move == 1 else "s")]
            else:
                parts = ["%d to move" % n_move]
            if n_excluded:
                parts.append("%d %s" % (n_excluded,
                                        "excluded" if long else "excl"))
            if n_unclass:
                parts.append("%d %s" % (n_unclass,
                                        "unmatched" if long else "unmat"))
            return "  " + " · ".join(parts)

        line = build(True)
        if len(line) > iw - 2:
            line = build(False)
        self._put(iy + ih - 1, ix + 1, line, iw - 2,
                  curses.A_BOLD | curses.color_pair(HEADER if n_move else DIM))

    def draw_status(self, h, w):
        """Transient line above the footer (e.g. 'Undid 3 moves')."""
        if not self.s.status:
            return
        self._put(h - 2, 1, self._ellipsis(self.s.status, w - 2), w - 2,
                  curses.color_pair(ACCENT))

    def footer_segments(self):
        """A modal captures every key, so advertising the main bindings while
        one is up is a lie. Swap the bar for the overlay's own actions."""
        if self.modal:
            if self.modal[0] == "confirm":
                return [("y", "sort"), ("n / esc", "cancel")]
            return [("any key", "close")]
        return [("tab", "panel"), ("j/k", "move"), ("space", "toggle"),
                ("a", "all"), ("s", "sort"), ("u", "undo"), ("r", "rescan"),
                ("?", "help"), ("q", "quit")]

    def draw_footer(self, h, w):
        plain = curses.color_pair(FOOTER)
        key = curses.color_pair(FOOTER_KEY) | curses.A_BOLD
        self._put(h - 1, 0, " " * w, w - 1, plain)
        segs = self.footer_segments()
        x = 1
        for k, label in segs:
            width = len(k) + len(label) + 5
            if x + width >= w:
                break
            self._put(h - 1, x, " %s " % k, len(k) + 2, key)
            x += len(k) + 2
            self._put(h - 1, x, " %s  " % label, len(label) + 3, plain)
            x += len(label) + 3

    def draw_modal(self):
        _kind, lines, title = self.modal
        h, w = self.layout()
        lines = lines or [""]
        mh = min(len(lines) + 4, h - 6)
        mw = min(max(len(l) for l in lines) + 6, w - 10)
        mw = max(mw, len(title) + 8)
        my, mx = (h - mh) // 2, (w - mw) // 2
        fill = curses.color_pair(SELECTED)
        mat = curses.color_pair(SELECTED_DIM)
        # Dim the whole horizontal band at the modal's rows, not just a box
        # around the frame. A fixed-width mat left orphaned fragments ("g]",
        # "s]") peeking out beside wide modals AND clipped panel cells that
        # fell inside its rectangle (a "[Pictures]" badge lost its bracket).
        # Full-width dimming is uniform, so nothing is half-erased and no
        # underlying text shows through beside the frame.
        for i in range(-1, mh + 1):
            y = my + i
            if 0 <= y < h - 1:
                self._put(y, 0, " " * w, w, mat)
        for i in range(mh):
            self._put(my + i, mx, " " * mw, mw, fill)
        draw_box(self.stdscr, my, mx, mh, mw, title, focused=True)
        for i, line in enumerate(lines):
            if 2 + i >= mh - 1:
                break
            self._put(my + 2 + i, mx + 2, line, mw - 4, fill)

    # --- input ---
    KEYS_ENTER = (ord("\n"), ord("\r"), curses.KEY_ENTER)

    def handle(self, key):
        if self.modal:
            self.dismiss_modal(key)
            return
        if key in (ord("q"), 27):
            self.running = False
        elif key in (ord("\t"), ord("l"), curses.KEY_RIGHT):
            self.set_focus(self.PLAN)
        elif key in (curses.KEY_BTAB, ord("h"), curses.KEY_LEFT):
            self.set_focus(self.FILES)
        elif key in (ord("j"), curses.KEY_DOWN):
            self.move(1)
        elif key in (ord("k"), curses.KEY_UP):
            self.move(-1)
        elif key == curses.KEY_NPAGE:
            self.move(max(1, self.page()))
        elif key == curses.KEY_PPAGE:
            self.move(-max(1, self.page()))
        elif key == ord("g"):
            self.move(-10 ** 6)
        elif key == ord("G"):
            self.move(10 ** 6)
        elif key == ord(" "):
            self.s.toggle_exclude()
        elif key == ord("a"):
            self.s.toggle_all()
        elif key == ord("s"):
            self.confirm_sort()
        elif key == ord("u"):
            self.s.undo()
        elif key == ord("r"):
            self.s.scan()
            self.s.status = "Rescanned %s" % self.s.location
        elif key == ord("?"):
            self.show_help()

    def dismiss_modal(self, key):
        kind = self.modal[0]
        self.modal = None
        if kind != "confirm":
            return
        if key in (ord("y"), ord("Y")) or key in self.KEYS_ENTER:
            self.do_sort()
        else:
            self.s.status = "Sort cancelled — nothing moved"

    def page(self):
        return max(1, self.layout()[0] - 7)

    def set_focus(self, which):
        if self.focus == which:
            return
        self.focus = which
        if which == self.PLAN:
            rows = self.plan_rows()
            self.plan_sel = self.plan_cursor(rows)
            if rows and rows[self.plan_sel][0] != "file":
                self.plan_move(1)

    def move(self, delta):
        if self.focus == self.PLAN:
            self.plan_move(delta)
            return
        rows = self.s.files
        if not rows:
            return
        self.s.selected = max(0, min(self.s.selected + delta, len(rows) - 1))
        self.plan_follow = True

    def plan_move(self, delta):
        """Step over file rows only — landing on a group header would leave
        space/enter with nothing to act on."""
        rows = self.plan_rows()
        if not rows:
            return
        step = 1 if delta > 0 else -1
        i = max(0, min(self.plan_sel, len(rows) - 1))
        for _ in range(min(abs(delta), len(rows))):
            j = i + step
            while 0 <= j < len(rows) and rows[j][0] != "file":
                j += step
            if not 0 <= j < len(rows):
                break
            i = j
        self.plan_sel = i
        name = rows[i][2]
        if name is not None:
            for k, r in enumerate(self.s.files):
                if r["name"] == name:
                    self.s.selected = k
                    break

    # --- actions ---
    def confirm_sort(self):
        """Moving files is destructive; show the plan and ask first."""
        pending = self.s.pending()
        if not pending:
            self.s.status = "Nothing to move — every file is excluded or unmatched"
            return
        by = {}
        for r in pending:
            by[r["target"]] = by.get(r["target"], 0) + 1
        lines = ["Move %d file(s) into:" % len(pending), ""]
        for name, _exts in self.s.folders:
            if name in by:
                lines.append("    %-16s %3d" % (name, by[name]))
        stay = len(self.s.files) - len(pending)
        if stay:
            lines.append("")
            lines.append("%d file(s) stay put." % stay)
        lines.append("")
        lines.append("[y] sort    [n] cancel")
        self.modal = ("confirm", lines, "Confirm sort")

    def do_sort(self):
        moves, errors = self.s.sort()
        if not moves and not errors:
            self.s.status = "Nothing to sort"
            return
        lines = []
        by = self.s.last_summary["by_folder"]
        for name, _exts in self.s.folders:
            if name in by:
                lines.append("  %-16s %3d" % (name, by[name]))
        lines.append("")
        lines.append("  Total: %d moved" % len(moves))
        if errors:
            lines.append("")
            lines.append("  %d skipped (nothing overwritten):" % len(errors))
            for e in errors[:6]:
                lines.append("    ! %s" % e)
            if len(errors) > 6:
                lines.append("    ... and %d more" % (len(errors) - 6))
        lines.append("")
        lines.append("  Press any key to continue")
        self.modal = ("sort_summary", lines, "Sort complete")

    HELP = [
        ("j / k / \u2193 \u2191", "move the cursor"),
        ("tab / h / l", "switch panel"),
        ("g / G", "first / last"),
        ("pgup / pgdn", "page"),
        (None, None),
        ("space", "exclude or include the file"),
        ("a", "exclude or include everything"),
        (None, None),
        ("s", "sort (asks to confirm)"),
        ("u", "undo the last sort, repeatable"),
        ("r", "rescan the folder"),
        (None, None),
        ("q", "quit"),
    ]

    def show_help(self):
        """Keys right-aligned against their descriptions. Left-aligning them in
        a fixed field stranded every single-letter binding ~15 columns from its
        meaning, so the two columns never read as bound pairs."""
        kw = max(len(k) for k, _d in self.HELP if k)
        lines = ["" if k is None else "%*s   %s" % (kw, k, d)
                 for k, d in self.HELP]
        lines += ["", "%*s   %s" % (kw, "any key", "close this")]
        self.modal = ("help", lines, "Keys")

    def run(self):
        self.s.scan()
        self.s.status = "%d file(s) in %s — press ? for keys" % (
            len(self.s.files), self.s.location)
        while self.running:
            self.draw()
            try:
                key = self.stdscr.getch()
            except curses.error:
                break
            if key == curses.KEY_RESIZE:
                self.files_top = self.plan_top = 0
                continue
            if key == -1:
                continue
            self.handle(key)
        self.s.status = ""


def bail(stdscr, *lines):
    """Readable startup failure instead of a traceback through curses."""
    stdscr.erase()
    for i, line in enumerate(lines):
        try:
            stdscr.addnstr(i, 0, line, stdscr.getmaxyx()[1] - 1,
                           curses.A_BOLD if i == 0 else 0)
        except curses.error:
            pass
    try:
        stdscr.addnstr(len(lines) + 1, 0, "Press q to quit",
                       stdscr.getmaxyx()[1] - 1)
    except curses.error:
        pass
    stdscr.refresh()
    while stdscr.getch() not in (ord("q"), 27):
        pass


def main(stdscr):
    setup_colors()
    stdscr.keypad(True)
    curses.curs_set(0)
    try:
        location, folders = load_config()
    except FileNotFoundError as e:
        return bail(stdscr, "Missing settings", str(e))
    except ValueError as e:
        return bail(stdscr, "settings.json is not valid JSON", str(e))

    if not os.path.isdir(location):
        return bail(stdscr, "Folder does not exist: %s" % location,
                    "Set FolderLocation in settings.json, or leave it empty",
                    "to sort %s" % (Path.home() / "Downloads"))
    if not folders:
        return bail(stdscr, "No Folders configured in settings.json",
                    "Nothing can be classified without extension rules.")

    App(stdscr, Sorter(location, folders)).run()


if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
