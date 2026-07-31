@echo off
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" tool\villager_editor.py
) else (
  python tool\villager_editor.py
)

