import os
import json

settings = json.load(open('settings.json', 'r'))
path_to_search = settings["DownloadLocation"]

print(f"Searching: {path_to_search}")
if not os.path.exists(path_to_search):
    print(f" Path: '{path_to_search}' does not exist")
    input("Press Enter to exit...")
    exit()


# region create dirs if not yet exists
if not os.path.exists(path_to_search+"Pictures\\"):
    os.makedirs(path_to_search+"Pictures\\")

if not os.path.exists(path_to_search+"Documents\\"):
    os.makedirs(path_to_search+"Documents\\")

if not os.path.exists(path_to_search+"Music\\"):
    os.makedirs(path_to_search+"Music\\")

if not os.path.exists(path_to_search+"Executables\\"):
    os.makedirs(path_to_search+"Executables\\")

if not os.path.exists(path_to_search+"Compressed\\"):
    os.makedirs(path_to_search+"Compressed\\")

if not os.path.exists(path_to_search+"Arma\\"):
    os.makedirs(path_to_search+"Arma\\")
# endregion

errors = []
documentAmount = 0
photoAmount = 0
soundAmount = 0
execAmount = 0
compressedAmount = 0
webAmount = 0
all_paths = os.listdir(path_to_search)

for path in all_paths:
    # region relocate files
    try:
        if path.__contains__(".jpg") or path.__contains__(".jpeg") or path.__contains__(".png") \
                or path.__contains__(".gif") or path.__contains__(".HEIC"):
            print(f"Relocating {path} to {path_to_search}"+f"Pictures\\{path}")
            os.rename(path_to_search + path, path_to_search+f"Pictures\\{path}")
            photoAmount += 1

        if path.__contains__(".md") or path.__contains__(".pdf") or path.__contains__(".txt") or path.__contains__(".docx") or path.__contains__(".xlsx") or path.__contains__(
                ".pptx"):
            print(f"Relocating {path} to {path_to_search}"+f"Documents\\{path}")
            os.rename(path_to_search + path, path_to_search+f"Documents\\{path}")
            documentAmount += 1

        if path.__contains__(".mid") or path.__contains__(".wav") or path.__contains__(".mp3") or path.__contains__(
                ".ogg"):
            print(f"Relocating {path} to {path_to_search}"+f"Music\\{path}")
            os.rename(path_to_search + path, path_to_search+f"Music\\{path}")
            soundAmount += 1

        if path.__contains__(".html") or path.__contains__(".css") or path.__contains__(".js"):
            print(f"Relocating {path} to {path_to_search}"+f"Web\\{path}")
            os.rename(path_to_search + path, path_to_search+f"Web\\{path}")
            webAmount += 1

        if path.__contains__(".exe") or path.__contains__(".msi") or path.__contains__(".apk") or path.__contains__(
                ".iso"):
            print(f"Relocating {path} to {path_to_search}"+f"Executables\\{path}")
            os.rename(path_to_search + path, path_to_search+f"Executables\\{path}")
            execAmount += 1

        if path.__contains__(".zip") or path.__contains__(".gz") or path.__contains__(".7z") or path.__contains__(".rar"):
            print(f"Relocating {path} to {path_to_search}"+f"Compressed\\{path}")
            os.rename(path_to_search + path, path_to_search+f"Compressed\\{path}")
            compressedAmount += 1

        if path.__contains__(".sqf") or path.__contains__(".sqm") or path.__contains__(".ext"):
            print(f"Relocating {path} to {path_to_search}"+f"Arma\\{path}")
            os.rename(path_to_search + path, path_to_search+f"Arma\\{path}")

    except FileNotFoundError:
        errors.append(f"Could not relocate '{path}'")
    except FileExistsError:
        errors.append(f"File already exists at '{path}', deleted")
        os.remove(path_to_search+""+path)
    # endregion

[print(e) for e in errors]

total = webAmount + photoAmount + documentAmount + soundAmount + execAmount + compressedAmount

print("#------------Summary------------#")

if total == 0:
    print("Nothing to relocate")
if webAmount != 0:
    print(f"Relocated {webAmount} web file(s)")
if photoAmount != 0:
    print(f"Relocated {photoAmount} photo(s)")
if documentAmount != 0:
    print(f"Relocated {documentAmount} document(s)")
if soundAmount != 0:
    print(f"Relocated {soundAmount} sound file(s)")
if execAmount != 0:
    print(f"Relocated {execAmount} executable(s)")
if compressedAmount != 0:
    print(f"Relocated {compressedAmount} compressed file(s)")
print()
input("Press 'Enter'-key to quit...")
