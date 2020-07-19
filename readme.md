# How to run

go inside CMD at `/src` and:
- run the `setup.py`
- run `InstantSorter.py`

`settings.json` should have a valid configuration.

This is the default for windows:

FolderLocation should be the path to the folder you want to sort.
Folders is an array of objects with one key-value pair, where the key is a Foldername and the value a list of extensions
```json
{"DownloadLocation": "C:\\Users\\<Username>\\Downloads\\",
"Folders":  [
  {"Pictures": [".jpg", ".JPG", ".jpeg", ".png", ".gif"]},
  {"Documents":  [".md",".pdf",".txt",".docx", ".xlsx", ".pptx"]},
  {"Audio":  [".mid",".wav",".mp3", ".ogg"]},
  {"Programming":  [".html", ".css", ".js", ".cs", ".java", ".py"]},
  {"Executables": [".exe",".msi",".apk",".iso"]},
  {"Compressed": [".zip",".gz",".7z",".rar"]},
  {"Gaming":  [".sqf",".sqm",".ext", ".savegame"]}
]}
```