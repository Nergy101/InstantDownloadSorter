import json
import re

settings_dict = json.load(open('settings.json', 'r'))


def check_download_location(_download_location: str):
    _download_location = _download_location[0].upper() + _download_location[1:]
    if _download_location[-1] is not "\\":
        _download_location += "\\"

    regex_pattern = r"""^[a-zA-Z]:\\(((?![<>:"/\\|?*]).)+((?<![ .])\\)?)*$"""
    if re.search(regex_pattern, _download_location) is not None:
        print(f" given path {_download_location} is valid")
    else:
        print(f" error: given path {_download_location} is invalid")
        input("Press Enter to Exit...")
        exit()
    return _download_location


i_download_location = input(r"Insert your download location using '\' as path delimiter"
                            + "\n" + r" example: C:\downloads\ " + "\n download-folder-path: ")

download_location = check_download_location(i_download_location)
settings_dict['DownloadLocation'] = download_location
json.dump(settings_dict, open("settings.json", 'w'))
print()
print("Settings updated")
input("Press Enter to Exit...")
