"""Analyse d'un projet Python : fichiers, point de départ, bibliothèques utilisées, ressources."""

import ast
import os
import re
import sys
import sysconfig
import pkgutil
from dataclasses import dataclass, field
from pathlib import Path

EXT_PY = {".py", ".pyw"}
DOSSIERS_IGNORES = {"__pycache__", ".git", ".hg", ".svn", ".idea", ".vscode", "venv", ".venv", "env",
                    "node_modules", "build", "dist", "site-packages", ".mypy_cache", ".pytest_cache",
                    "ExeForge_sortie", ".tox", "__MACOSX"}
EXT_RESSOURCES_IGNOREES = EXT_PY | {".pyc", ".pyo", ".spec", ".bat", ".cmd", ".sh", ".log", ".tmp", ".zip",
                                    ".exe", ".msi", ".gitignore", ".lnk"}
NOMS_RESSOURCES_IGNORES = {"requirements.txt", "thumbs.db", "desktop.ini", ".ds_store"}
NOMS_DEMARRAGE = ("main.py", "__main__.py", "app.py", "run.py", "start.py", "launcher.py", "game.py")

# nom d'import -> nom du paquet à installer avec pip (quand ils diffèrent)
PIP = {
    "PIL": "Pillow", "cv2": "opencv-python", "yaml": "PyYAML", "sklearn": "scikit-learn",
    "bs4": "beautifulsoup4", "skimage": "scikit-image", "dateutil": "python-dateutil",
    "serial": "pyserial", "usb": "pyusb", "Crypto": "pycryptodome", "Cryptodome": "pycryptodomex",
    "OpenSSL": "pyOpenSSL", "jwt": "PyJWT", "dotenv": "python-dotenv", "docx": "python-docx",
    "pptx": "python-pptx", "fitz": "PyMuPDF", "win32api": "pywin32", "win32com": "pywin32",
    "win32con": "pywin32", "win32gui": "pywin32", "win32file": "pywin32", "win32process": "pywin32",
    "win32clipboard": "pywin32", "pythoncom": "pywin32", "pywintypes": "pywin32", "wx": "wxPython",
    "attr": "attrs", "magic": "python-magic", "zmq": "pyzmq", "git": "GitPython",
    "MySQLdb": "mysqlclient", "psycopg2": "psycopg2-binary", "telegram": "python-telegram-bot",
    "discord": "discord.py", "yt_dlp": "yt-dlp", "speech_recognition": "SpeechRecognition",
    "flask": "Flask", "django": "Django", "jinja2": "Jinja2", "markdown": "Markdown",
    "sqlalchemy": "SQLAlchemy", "pygame_gui": "pygame-gui", "OpenGL": "PyOpenGL", "Xlib": "python-xlib",
    "mpl_toolkits": "matplotlib", "pkg_resources": "setuptools", "google": "protobuf", "ttkbootstrap": "ttkbootstrap",
    "tkinterdnd2": "tkinterdnd2", "customtkinter": "customtkinter", "PyQt5": "PyQt5", "PyQt6": "PyQt6",
    "PySide2": "PySide2", "PySide6": "PySide6", "kivy": "Kivy", "gtts": "gTTS", "bcrypt": "bcrypt",
}


def nom_pip(module):
    return PIP.get(module, module)


def normaliser(nom):
    return re.sub(r"[-_.]+", "-", nom).lower()


@dataclass
class Paquet:
    pip: str
    spec: str = ""
    modules: set = field(default_factory=set)
    utilise_par: set = field(default_factory=set)
    etat: str = "inconnu"        # "installé" | "à télécharger" | "inconnu"


@dataclass
class Analyse:
    racine: Path
    mode: str                              # "fichier" ou "dossier"
    fichiers: list                         # chemins relatifs des .py analysés
    entrees: list                          # points de départ possibles (relatifs)
    entree_defaut: Path
    stdlib_utilises: set
    locaux: set
    paquets: dict                          # clé normalisée -> Paquet
    avertissements: list
    ressources: list                       # [(chemin absolu, dossier de destination)]
    dynamiques: set


def _stdlib():
    if hasattr(sys, "stdlib_module_names"):
        return set(sys.stdlib_module_names) | set(sys.builtin_module_names)
    noms = set(sys.builtin_module_names)
    try:
        noms |= {m.name for m in pkgutil.iter_modules([sysconfig.get_paths()["stdlib"]])}
    except Exception:
        pass
    return noms


def lister_fichiers(racine, profondeur=6):
    """Tous les .py du dossier (sans les dossiers techniques : venv, .git, build...)."""
    resultat = []
    base = len(racine.parts)
    for dossier, sous, noms in os.walk(racine):
        sous[:] = sorted(d for d in sous if d not in DOSSIERS_IGNORES and not d.startswith("."))
        if len(Path(dossier).parts) - base >= profondeur:
            sous[:] = []
        resultat += [Path(dossier, n) for n in sorted(noms) if Path(n).suffix.lower() in EXT_PY]
    return resultat


def analyser_source(chemin):
    """-> (modules importés (niveau 1), imports dynamiques, a un 'if __name__ == "__main__"', erreur)"""
    try:
        arbre = ast.parse(Path(chemin).read_bytes(), filename=str(chemin))
    except (SyntaxError, ValueError, OSError) as e:
        return set(), set(), False, f"{Path(chemin).name} : {e.__class__.__name__}"
    imports, dyn, garde = set(), set(), False
    for n in ast.walk(arbre):
        if isinstance(n, ast.Import):
            imports |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            if n.level == 0 and n.module:
                imports.add(n.module.split(".")[0])
        elif isinstance(n, ast.Call) and n.args and isinstance(n.args[0], ast.Constant) \
                and isinstance(n.args[0].value, str):
            f = n.func
            nom = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
            if nom in ("import_module", "__import__") and n.args[0].value:
                dyn.add(n.args[0].value.split(".")[0])
        elif isinstance(n, ast.Compare) and isinstance(n.left, ast.Name) and n.left.id == "__name__":
            if any(isinstance(c, ast.Constant) and c.value == "__main__" for c in n.comparators):
                garde = True
    return imports, dyn, garde, None


def lire_requirements(racine):
    """requirements.txt -> [(nom du paquet, ligne complète)]"""
    fichier = Path(racine) / "requirements.txt"
    if not fichier.is_file():
        return []
    sortie = []
    for ligne in fichier.read_text(encoding="utf-8", errors="replace").splitlines():
        ligne = ligne.split("#")[0].strip()
        if not ligne or ligne.startswith(("-", "git+", "http")):
            continue
        m = re.match(r"[A-Za-z0-9][A-Za-z0-9._-]*", ligne)
        if m:
            sortie.append((m.group(0), ligne))
    return sortie


def _ressources(racine):
    """Fichiers et dossiers (non Python) à embarquer avec l'exécutable."""
    liste = []
    for e in sorted(racine.iterdir(), key=lambda p: p.name.lower()):
        if e.name in DOSSIERS_IGNORES or e.name.startswith("."):
            continue
        if e.is_file():
            if e.suffix.lower() not in EXT_RESSOURCES_IGNOREES and e.name.lower() not in NOMS_RESSOURCES_IGNORES \
                    and not e.name.endswith(".corrompu.json"):
                liste.append((e, "."))
        elif e.is_dir():
            if any(f.is_file() and f.suffix.lower() not in EXT_PY | {".pyc"}
                   for f in e.rglob("*") if not set(f.parts) & DOSSIERS_IGNORES):
                liste.append((e, e.name))
    return liste


def analyser(chemin):
    chemin = Path(chemin).resolve()
    if chemin.is_file():
        mode, racine = "fichier", chemin.parent
        fichiers = [chemin]
    elif chemin.is_dir():
        mode, racine = "dossier", chemin
        fichiers = lister_fichiers(racine)
    else:
        raise ValueError("Chemin introuvable.")
    if not fichiers:
        raise ValueError("Aucun fichier Python (.py) trouvé dans ce dossier.")

    tous = lister_fichiers(racine) if mode == "fichier" else fichiers
    locaux = {f.stem for f in tous}
    for f in tous:
        locaux |= set(f.relative_to(racine).parts[:-1])
    locaux.add("__main__")

    donnees, avert = {}, []
    a_faire = list(fichiers)
    while a_faire:                      # en mode « fichier » : on suit les modules locaux importés
        f = a_faire.pop()
        if f in donnees:
            continue
        imports, dyn, garde, err = analyser_source(f)
        donnees[f] = (imports, dyn, garde)
        if err:
            avert.append("Fichier illisible (erreur de syntaxe ?) : " + err)
        if mode == "fichier":
            for m in imports:
                cand = racine / f"{m}.py"
                if cand.is_file():
                    a_faire.append(cand)
                elif (racine / m).is_dir():
                    a_faire += lister_fichiers(racine / m)
    fichiers = sorted(donnees)

    std = _stdlib()
    stdlib_utilises, paquets, dynamiques = set(), {}, set()
    for f, (imports, dyn, _garde) in donnees.items():
        rel = f.relative_to(racine).as_posix()
        dynamiques |= {d for d in dyn if d not in std and d not in locaux}
        for m in imports | dyn:
            if m in locaux:
                continue
            if m in std:
                stdlib_utilises.add(m)
                continue
            p = paquets.setdefault(normaliser(nom_pip(m)), Paquet(pip=nom_pip(m)))
            p.modules.add(m)
            p.utilise_par.add(rel)
    for nom, ligne in lire_requirements(racine):
        p = paquets.setdefault(normaliser(nom), Paquet(pip=nom))
        p.spec = ligne
        if not p.modules:
            p.utilise_par.add("requirements.txt")

    rel = [f.relative_to(racine) for f in fichiers]
    gardes = [f.relative_to(racine) for f, (_i, _d, g) in donnees.items() if g]
    if mode == "fichier":
        entrees = [chemin.relative_to(racine)]
    else:
        gardes.sort(key=lambda p: (len(p.parts), p.name))
        reste = [p for p in rel if len(p.parts) == 1 and p not in gardes]
        entrees = gardes + reste
    defaut = next((p for n in NOMS_DEMARRAGE for p in entrees if p.name == n and len(p.parts) == 1), entrees[0])
    if not gardes and mode == "dossier":
        avert.append("Aucun fichier avec « if __name__ == \"__main__\" » : vérifie le fichier de démarrage.")
    return Analyse(racine=racine, mode=mode, fichiers=rel, entrees=entrees, entree_defaut=defaut,
                   stdlib_utilises=stdlib_utilises, locaux=locaux, paquets=paquets, avertissements=avert,
                   ressources=_ressources(racine) if mode == "dossier" else [], dynamiques=dynamiques)
