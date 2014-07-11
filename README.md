jakpak
======

Compare Arch Linux local packages versions with Arch Rollback Machine packages version and see the differences

###Installation
The dependencies shall be installed using pip (hopefully in virtualenv):
```
pip install -r requirements.txt
```

That is it.

###Usage
```
jakpak -d 05-07-2014 -r core
```

will give a list of core local and repo packages with their respective versions, so
one can compare what has been updated since a given day.

```
jakpak -h
```

for help.