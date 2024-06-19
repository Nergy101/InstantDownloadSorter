import os
import json
from pathlib import Path

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

path_to_search = settings["FolderLocation"] or str(
    os.path.join(Path.home(), "Downloads"))
folders = settings["Folders"]

print(f"Searching: {path_to_search}")
if not os.path.exists(path_to_search):
    print(f"Path: '{path_to_search}' does not exist")
    input("Press Enter to exit...")
    exit()

for folder_dict in folders:
    folder_name = list(folder_dict.keys())[0]
    if not os.path.exists(os.path.join(path_to_search, folder_name)):
        print(f"Creating folder {folder_name}")
        os.makedirs(os.path.join(path_to_search, folder_name))

all_paths = os.listdir(path_to_search)
errors = []
summary = {}

for folder_dict in folders:
    folder_name = list(folder_dict.keys())[0]
    summary[folder_name] = 0

for path in all_paths:
    try:
        for folder_dict in folders:
            folder_name = list(folder_dict.keys())[0]
            for extension in list(folder_dict.values())[0]:
                file_to_move = os.path.join(path_to_search, path)
                move_to = os.path.join(
                    path_to_search, os.path.join(folder_name, path))

                if os.path.splitext(path)[1].lower() == extension.lower():
                    print(f"Relocating '{file_to_move}' to '{move_to}'")
                    os.rename(file_to_move, move_to)
                    summary[folder_name] = summary[folder_name]+1

    except FileNotFoundError as e:
        errors.append(f"Could not relocate '{path}': {e}")
    except FileExistsError:
        errors.append(f"File already exists at '{
                      path}', delete the file yourself")

[print(e) for e in errors]

print()
print("#------------Summary------------#")
print()

did_something = False

for folder in summary:
    if summary[folder] > 0:
        did_something = True
        print(f"Relocated {summary[folder]} files to {folder}.")

if not did_something:
    print("There was nothing to relocate.")

for folder in summary:
    dir_to_delete = os.path.join(path_to_search, folder)
    if not os.listdir(dir_to_delete):
        try:
            os.rmdir(dir_to_delete)
        except OSError as e:
            print(f"Error: {dir_to_delete} : {e.strerror}")

print(f"Deleted empty folders.")

print()
print("#------------Finished-----------#")
print()

input("Press 'Enter'-key to quit...")
