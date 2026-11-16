"""Fresh recursive size without Path.stat twice per file. No cached sizes/intervals.
Never follow directory symlinks; follow regular-file symlinks like Path.rglob/is_file.
Any unexpected I/O error fails closed, rather than undercounting the native budget.
"""
import os,stat
def fresh_size(root):
 total=0;stack=[os.fspath(root)]
 while stack:
  with os.scandir(stack.pop())as entries:
   for entry in entries:
    if entry.is_dir(follow_symlinks=False):stack.append(entry.path)
    else:
     s=entry.stat(follow_symlinks=True)
     if stat.S_ISREG(s.st_mode):total+=s.st_size
 return total
