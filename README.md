# Atelier des villageois

Application autonome de création de villageois `.bdengine`.

## Installation

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Lancement

Double-cliquer sur `start.bat` ou exécuter :

```powershell
python tool/villager_editor.py
```

L’éditeur s’ouvre sur <http://127.0.0.1:8765>.

Les composants ajoutés à la bibliothèque sont conservés dans `bdengine/characters/villagers/`. Les personnages exportés sont placés dans `bdengine/characters/villagers/custom/`.
