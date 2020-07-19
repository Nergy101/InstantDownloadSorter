# How to run

Have Python 3 installed and available in PATH as either `py` or `python`.  
go inside CMD at `/src` and:  
- run `InstantSorter.py` with python  

`settings.json` should have a valid configuration.

This is the default for windows:

```json
{"FolderLocation": "C:\\Users\\<Username>\\Downloads\\",
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

FolderLocation should be the path to the folder you want to sort.  
Folders is an array of objects with one key-value pair, where the key is a Foldername and the value a list of extensions  
that should be put inside the belonging Folder(name).  
Beware that double extensions will be sorted to their first occurrence.
