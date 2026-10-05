"""Python pour la compilation : détection d'un Python existant, sinon installation de Python 3.12 (privée).

Un Python « privé » est installé dans %LOCALAPPDATA%\\ExeForge\\python312 : sans droits administrateur,
sans toucher au Python du système. Si l'installateur officiel est livré avec ExeForge (dossier « runtime »),
il est utilisé hors-ligne ; sinon il est téléchargé depuis python.org.
"""

import glob
import json
import math
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path

VERSION = "3.12.10"          # dernière 3.12 avec installateur Windows officiel
WIN = os.name == "nt"
NO_WINDOW = 0x08000000 if WIN else 0
VERSIONS_OK = ((3, 9), (3, 13))


class Annule(Exception):
    pass


class ErreurPython(Exception):
    pass


@dataclass
class InfoPython:
    exe: str
    version: tuple
    source: str        # "privé" ou "système"
    pip: bool
    tk: bool
    venv: bool

    @property
    def txt(self):
        return ".".join(str(n) for n in self.version)


def dossier_app():
    return Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent


def dossier_prive():
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / ".local" / "share")
    return Path(base) / "ExeForge" / "python312"


def _env():
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8",
               PIP_DISABLE_PIP_VERSION_CHECK="1", PIP_NO_INPUT="1")
    for cle in list(env):
        if cle in ("PYTHONHOME", "PYTHONPATH", "_MEIPASS2") or cle.startswith("_PYI"):
            env.pop(cle, None)
    return env


# ------------------------------------------------------------------ exécution de commandes
def _tuer(proc):
    try:
        if WIN:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True,
                           creationflags=NO_WINDOW)
        else:
            proc.kill()
    except Exception:
        pass


def executer(cmd, ligne_cb=None, annuler=None, cwd=None):
    """Lance une commande, envoie chaque ligne de sortie à ligne_cb, retourne le code de retour."""
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                            cwd=cwd, env=_env(), text=True, encoding="utf-8", errors="replace",
                            bufsize=1, creationflags=NO_WINDOW)
    fini = threading.Event()
    if annuler is not None:
        def guet():
            while not fini.is_set():
                if annuler.wait(0.25):
                    _tuer(proc)
                    return
        threading.Thread(target=guet, daemon=True).start()
    try:
        for ligne in proc.stdout:
            if ligne_cb:
                ligne_cb(ligne.rstrip("\r\n"))
        proc.wait()
    finally:
        fini.set()
    if annuler is not None and annuler.is_set():
        raise Annule()
    return proc.returncode


# ------------------------------------------------------------------ détection
_SONDE = ("import sys, json, struct, importlib.util as u;"
          "print(json.dumps({'v': list(sys.version_info[:3]), 'exe': sys.executable,"
          "'pip': u.find_spec('pip') is not None, 'tk': u.find_spec('tkinter') is not None,"
          "'venv': sys.prefix != getattr(sys, 'base_prefix', sys.prefix)}))")


def sonder(exe, source="système"):
    """Interroge un exécutable Python. Retourne InfoPython ou None s'il est inutilisable."""
    try:
        r = subprocess.run([str(exe), "-c", _SONDE], capture_output=True, text=True, timeout=25,
                           env=_env(), creationflags=NO_WINDOW, cwd=tempfile.gettempdir())
        d = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        return None
    v = tuple(d["v"])
    if v < (3, 8):
        return None
    return InfoPython(exe=d["exe"], version=v, source=source, pip=d["pip"], tk=d["tk"], venv=d["venv"])


def _candidats():
    prive = dossier_prive() / ("python.exe" if WIN else "bin/python3")
    if prive.is_file():
        yield str(prive), "privé"
    if WIN:
        try:
            r = subprocess.run(["py", "-0p"], capture_output=True, text=True, errors="replace", timeout=15,
                               creationflags=NO_WINDOW)
            for chemin in re.findall(r"([A-Za-z]:\\[^\r\n]*?python\.exe)", r.stdout):
                yield chemin.strip(), "système"
        except Exception:
            pass
    for nom in ("python", "python3"):
        chemin = shutil.which(nom)
        if chemin and "WindowsApps" not in chemin:      # évite le faux « python » du Microsoft Store
            yield chemin, "système"
    if WIN:
        for modele in (os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python3*\python.exe"),
                       os.path.expandvars(r"%ProgramFiles%\Python3*\python.exe"),
                       os.path.expandvars(r"%ProgramFiles(x86)%\Python3*\python.exe"),
                       r"C:\Python3*\python.exe"):
            for chemin in sorted(glob.glob(modele), reverse=True):
                yield chemin, "système"
    if not getattr(sys, "frozen", False):
        yield sys.executable, "système"


def chercher_python(exiger_tk=False):
    """Meilleur Python déjà présent (3.12 de préférence), ou None."""
    vus, trouves = set(), []
    for chemin, source in _candidats():
        cle = os.path.normcase(os.path.realpath(chemin))
        if cle in vus:
            continue
        vus.add(cle)
        info = sonder(chemin, source)
        if info and (info.tk or not exiger_tk):
            trouves.append(info)

    def rang(i):
        return (i.version[:2] == (3, 12), VERSIONS_OK[0] <= i.version[:2] <= VERSIONS_OK[1], i.version)
    return max(trouves, key=rang) if trouves else None


def verifier(info, imports, dists):
    """Quelles bibliothèques sont déjà installées dans ce Python ? -> {"imports": {...}, "dists": {...}}"""
    code = ("import sys, json, importlib.util as u\n"
            "from importlib import metadata as m\n"
            "d = json.load(sys.stdin)\n"
            "o = {'imports': {}, 'dists': {}}\n"
            "for n in d['imports']:\n"
            "    try: o['imports'][n] = u.find_spec(n) is not None\n"
            "    except Exception: o['imports'][n] = False\n"
            "for n in d['dists']:\n"
            "    try: m.version(n); o['dists'][n] = True\n"
            "    except Exception: o['dists'][n] = False\n"
            "print(json.dumps(o))")
    vide = {"imports": {n: False for n in imports}, "dists": {n: False for n in dists}}
    if info is None:
        return vide
    try:
        r = subprocess.run([info.exe, "-c", code], input=json.dumps({"imports": list(imports), "dists": list(dists)}),
                           capture_output=True, text=True, timeout=60, env=_env(),
                           creationflags=NO_WINDOW, cwd=tempfile.gettempdir())
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        return vide


def pip_installer(info, specs, ligne_cb=None, annuler=None):
    cmd = [info.exe, "-m", "pip", "install", "--disable-pip-version-check", "--no-input"]
    if info.source == "système" and not info.venv:
        cmd.append("--user")          # pas besoin de droits administrateur
    return executer(cmd + list(specs), ligne_cb, annuler)


def assurer_pip(info, ligne_cb=None, annuler=None):
    if info.pip:
        return True
    return executer([info.exe, "-m", "ensurepip", "--upgrade"], ligne_cb, annuler) == 0


# ------------------------------------------------------------------ installation de Python 3.12
def url_installateur():
    machine = platform.machine().lower()
    suffixe = "-amd64" if machine in ("amd64", "x86_64", "arm64", "aarch64") else ""
    return f"https://www.python.org/ftp/python/{VERSION}/python-{VERSION}{suffixe}.exe"


def installateur_local():
    dossiers = [dossier_app() / "runtime", dossier_app(),
                Path(getattr(sys, "_MEIPASS", dossier_app())) / "runtime"]
    for d in dossiers:
        for f in sorted(d.glob("python-3.12*.exe")) if d.is_dir() else []:
            if f.stat().st_size > 15_000_000:
                return f
    return None


def telecharger(url, dest, rappel, annuler):
    """Téléchargement avec progression. rappel(fraction, texte)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(".part")
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "ExeForge"}), timeout=30) as r, \
                open(part, "wb") as f:
            total = int(r.headers.get("Content-Length") or 0)
            lu, t0 = 0, time.time()
            while True:
                if annuler.is_set():
                    raise Annule()
                bloc = r.read(64 * 1024)
                if not bloc:
                    break
                f.write(bloc)
                lu += len(bloc)
                if total:
                    vitesse = lu / max(0.1, time.time() - t0) / 1e6
                    rappel(lu / total, f"Téléchargement de Python {VERSION} : {lu / 1e6:.0f} / {total / 1e6:.0f} Mo "
                                       f"({vitesse:.1f} Mo/s)")
        os.replace(part, dest)
    except Annule:
        raise
    except Exception as e:
        raise ErreurPython(f"Téléchargement impossible ({e}). Vérifie ta connexion Internet.") from e
    finally:
        try:
            part.unlink()
        except OSError:
            pass
    with open(dest, "rb") as f:
        if dest.stat().st_size < 15_000_000 or f.read(2) != b"MZ":
            raise ErreurPython("Le fichier téléchargé est incomplet ou invalide.")


def installer_python_prive(rappel, annuler):
    """Installe Python 3.12 pour ExeForge. rappel(fraction 0..1, texte). Retourne InfoPython."""
    if not WIN:
        raise ErreurPython("L'installation automatique de Python fonctionne uniquement sous Windows.")
    cible = dossier_prive()
    installateur = installateur_local()
    if installateur:
        rappel(0.4, "Installateur Python 3.12 trouvé (hors-ligne)")
    else:
        installateur = Path(tempfile.gettempdir()) / "exeforge_dl" / url_installateur().rsplit("/", 1)[1]
        telecharger(url_installateur(), installateur, lambda f, t: rappel(f * 0.4, t), annuler)
    rappel(0.42, f"Installation de Python {VERSION} (quelques instants)…")
    cible.parent.mkdir(parents=True, exist_ok=True)
    cmd = (f'"{installateur}" /quiet InstallAllUsers=0 TargetDir="{cible}" Include_launcher=0 '
           "InstallLauncherAllUsers=0 Include_test=0 Include_doc=0 Include_dev=0 Include_tcltk=1 Include_pip=1 "
           "PrependPath=0 Shortcuts=0 AssociateFiles=0 CompileAll=0")
    proc = subprocess.Popen(cmd, creationflags=NO_WINDOW, env=_env())
    t0 = time.time()
    while proc.poll() is None:
        if annuler.is_set():
            _tuer(proc)
            raise Annule()
        t = time.time() - t0
        rappel(0.42 + 0.55 * (1 - math.exp(-t / 45.0)), f"Installation de Python {VERSION}… ({int(t)} s)")
        time.sleep(0.5)
    if proc.returncode not in (0, 3010):
        raise ErreurPython(f"L'installation de Python a échoué (code {proc.returncode}).")
    info = sonder(cible / "python.exe", "privé")
    if info is None:
        raise ErreurPython("Python a été installé mais reste inutilisable.")
    rappel(1.0, f"Python {info.txt} installé")
    return info
