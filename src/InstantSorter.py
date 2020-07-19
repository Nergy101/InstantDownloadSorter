import os
import json

try:
    settings = json.load(open('src/settings.json', 'r'))
except FileNotFoundError:
    try:
        settings = json.load(open('settings.json', 'r'))
    except FileNotFoundError as e:
        print(e)
        print("Path: 'settings.json' does not exist and should be created with a valid config.")
        input("Press 'Enter'-key to quit...")
        exit()

path_to_search = settings["FolderLocation"]
folders = settings["Folders"]

print(f"Searching: {path_to_search}")
if not os.path.exists(path_to_search):
    print(f"Path: '{path_to_search}' does not exist")
    input("Press Enter to exit...")
    exit()


# region create dirs if not yet exists
for folder_dict in folders:
    folder_name = list(folder_dict.keys())[0]
    if not os.path.exists(path_to_search+f"{folder_name}\\"):
        print(f"Creating folder {folder_name}")
        os.makedirs(path_to_search+f"{folder_name}\\")

# endregion

# region relocate files
errors = []
summary = {}
for folder_dict in folders:
    folder_name = list(folder_dict.keys())[0]
    summary[folder_name] = 0
all_paths = os.listdir(path_to_search)

for path in all_paths:
    try:
        for folder_dict in folders:
            folder_name = list(folder_dict.keys())[0]
            for extension in list(folder_dict.values())[0]:
                if path.__contains__(extension):
                    print(f"Relocating '{path}' to " + f"{folder_name}")
                    os.rename(path_to_search + path, path_to_search + f"{folder_name}\\{path}")
                    summary[folder_name] = summary[folder_name]+1

    except FileNotFoundError:
        errors.append(f"Could not relocate '{path}'")
    except FileExistsError:
        errors.append(f"File already exists at '{path}', deleted")
        os.remove(path_to_search+""+path)
    # endregion

[print(e) for e in errors]

print("#------------Summary------------#")

did_something = False

for folder in summary:
    if summary[folder] > 0:
        did_something = True
        print(f"Relocated {summary[folder]} files to {folder}")

if not did_something:
    print("Nothing to relocate")
print()
print("#------------Finished-----------#")
print()
input("Press 'Enter'-key to quit...")
