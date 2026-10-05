"""Création de l'exécutable : Python -> bibliothèques -> icône -> PyInstaller (avec progression)."""

import os
import re
import shlex
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

import diagnostic
import icones
import runtime_python as RP
from runtime_python import Annule


class ErreurConstruction(Exception):
    pass


@dataclass
class Options:
    analyse: object
    entree: Path
    nom: str
    icone: object              # Path ou None
    icone_reglages: tuple      # (mode d'adaptation, arrondi)
    un_fichier: bool
    sans_console: bool
    ressources: bool
    sortie: Path
    extra: str = ""


class Jauge:
    """Progression globale 0..100 qui ne recule jamais."""

    def __init__(self, cb):
        self.cb, self.v, self.txt = cb, 0.0, ""

    def aller(self, v, txt=None):
        self.v = max(self.v, min(100.0, v))
        if txt is not None:
            self.txt = txt
        self.cb(self.v, self.txt)

    def creep(self, plafond, pas=0.08):
        if self.v < plafond:
            self.aller(self.v + pas)


def nettoyer_nom(nom):
    nom = re.sub(r'[\\/:*?"<>|]+', "_", nom).strip(" .")
    return nom or "MonProgramme"


# ------------------------------------------------------------------ étapes
def _preparer_python(opt, jauge, log, annuler):
    jauge.aller(3, "Recherche de Python…")
    besoin_tk = "tkinter" in opt.analyse.stdlib_utilises
    info = RP.chercher_python(exiger_tk=besoin_tk)
    if info is None:
        log("Aucun Python utilisable trouvé" + (" (avec Tkinter)" if besoin_tk else "")
            + f" : installation automatique de Python {RP.VERSION}.", "warn")
        info = RP.installer_python_prive(lambda f, t: jauge.aller(5 + f * 20, t), annuler)
    log(f"Python {info.txt} ({info.source}) : {info.exe}", "ok")
    if not RP.assurer_pip(info, lambda l: log(l, "gris"), annuler):
        raise ErreurConstruction("pip est introuvable dans ce Python.")
    jauge.aller(25, f"Python {info.txt} prêt")
    return info


def _suivre_pip(ligne, jauge, debut, fin):
    paliers = (("Collecting", 0.15), ("Using cached", 0.35), ("Downloading", 0.35),
               ("Installing collected packages", 0.75), ("Successfully installed", 1.0))
    for mot, f in paliers:
        if ligne.startswith(mot):
            texte = None
            if mot == "Collecting" and len(ligne.split()) > 1:
                texte = f"Téléchargement de {ligne.split()[1]}…"
            elif mot == "Installing collected packages":
                texte = "Installation des bibliothèques…"
            jauge.aller(debut + (fin - debut) * f, texte)
            return
    jauge.creep(debut + (fin - debut) * 0.7)


def _preparer_paquets(opt, py, jauge, log, annuler):
    jauge.aller(26, "Vérification des bibliothèques…")
    paquets = list(opt.analyse.paquets.values())
    imports = sorted({m for p in paquets for m in p.modules} | {"PyInstaller"})
    dists = sorted({p.pip for p in paquets if not p.modules})
    etat = RP.verifier(py, imports, dists)
    installes, manquants = [], []
    for p in paquets:
        ok = all(etat["imports"].get(m) for m in p.modules) if p.modules else etat["dists"].get(p.pip)
        (installes if ok else manquants).append(p)
    specs = [p.spec or p.pip for p in manquants]
    if not etat["imports"].get("PyInstaller"):
        specs.append("pyinstaller")
    if installes:
        log("Déjà installées (rien à télécharger) : " + ", ".join(p.pip for p in installes), "ok")
    if etat["imports"].get("PyInstaller"):
        log("PyInstaller est déjà installé.", "ok")
    if not specs:
        log("Toutes les bibliothèques sont déjà présentes.", "ok")
        jauge.aller(50, "Bibliothèques prêtes")
        return
    log("À télécharger : " + ", ".join(specs), "warn")
    jauge.aller(28, "Téléchargement des bibliothèques…")
    suivre = lambda l: (log(l, "gris"), _suivre_pip(l, jauge, 28, 50))
    if RP.pip_installer(py, specs, suivre, annuler) != 0:
        log("Installation groupée échouée : essai paquet par paquet.", "warn")
        echecs = []
        for s in specs:
            if RP.pip_installer(py, [s], suivre, annuler) != 0:
                echecs.append(s)
        if "pyinstaller" in echecs:
            raise ErreurConstruction("Impossible d'installer PyInstaller (connexion Internet ?).")
        for s in echecs:
            log(f"« {s} » n'a pas pu être installé : vérifie son nom ou installe-le toi-même.", "err")
    jauge.aller(50, "Bibliothèques prêtes")


def _preparer_icone(opt, temp, jauge, log):
    if not opt.icone:
        log("Pas d'icône choisie : icône par défaut.", "gris")
        jauge.aller(54, "Préparation de la compilation…")
        return None
    jauge.aller(51, "Conversion de l'icône…")
    ico = temp / "icone.ico"
    mode, arrondi = opt.icone_reglages
    tailles = icones.convertir_en_ico(opt.icone, ico, mode, arrondi)
    log(f"Icône convertie en .ico ({', '.join(str(t) for t in tailles)} px).", "ok")
    jauge.aller(54, "Préparation de la compilation…")
    return ico


JALONS = (("Build complete", 99, 99), ("Building COLLECT", 97, 99), ("Copying icon", 95, 97),
          ("Building EXE from", 92, 97), ("Bootloader", 91, 92), ("Building PKG", 87, 91),
          ("Building PYZ", 82, 86), ("Loading module hook", 72, 80), ("Processing module hooks", 72, 80),
          ("Analyzing", 58, 72), ("Running Analysis", 56, 72))
TEXTES = {"Running Analysis": "Analyse du code…", "Analyzing": "Analyse du code…",
          "Processing module hooks": "Traitement des bibliothèques…", "Building PYZ": "Compression du code…",
          "Building PKG": "Assemblage du programme…", "Building EXE from": "Création de l'exécutable…",
          "Building COLLECT": "Rassemblement des fichiers…", "Build complete": "Finalisation…"}


def _suivre_pyinstaller(ligne, jauge, etat):
    texte = ligne.split(":", 1)[-1].strip()
    for mot, bas, haut in JALONS:
        if mot in texte:
            etat["plafond"] = haut
            jauge.aller(bas, TEXTES.get(mot))
            return
    jauge.creep(etat["plafond"], 0.05)


def _niveau(ligne):
    if "ERROR" in ligne or "Traceback" in ligne:
        return "err"
    if "WARNING" in ligne:
        return "warn"
    return "gris"


def _lancer_pyinstaller(opt, py, ico, nom, temp, jauge, log, annuler):
    cmd = [py.exe, "-m", "PyInstaller", "--noconfirm", "--clean",
           "--onefile" if opt.un_fichier else "--onedir",
           "--windowed" if opt.sans_console else "--console",
           "--name", nom, "--distpath", str(opt.sortie), "--workpath", str(temp / "work"),
           "--specpath", str(temp), "--paths", str(opt.analyse.racine)]
    if ico:
        cmd += ["--icon", str(ico)]
    if opt.ressources:
        for src, dest in opt.analyse.ressources:
            cmd += ["--add-data", f"{src}{os.pathsep}{dest}"]
    for m in sorted(opt.analyse.dynamiques):
        cmd += ["--hidden-import", m]
    if opt.extra.strip():
        cmd += [a.strip('"') for a in shlex.split(opt.extra, posix=(os.name != "nt"))]
    cmd.append(str(opt.entree))
    log("Compilation avec PyInstaller…", "etape")
    log("Commande : " + subprocess.list2cmdline(cmd), "gris")
    jauge.aller(55, "Compilation…")
    etat = {"plafond": 58}

    def ligne(l):
        log(l, _niveau(l))
        _suivre_pyinstaller(l, jauge, etat)
    rc = RP.executer(cmd, ligne, annuler, cwd=str(opt.entree.parent))
    if rc != 0:
        raise ErreurConstruction("PyInstaller a échoué : lis le journal ci-dessus (dernières lignes en rouge).")
    ext = ".exe" if RP.WIN else ""
    exe = opt.sortie / (nom + ext) if opt.un_fichier else opt.sortie / nom / (nom + ext)
    if not exe.exists():
        raise ErreurConstruction("La compilation s'est terminée mais l'exécutable est introuvable.")
    return exe


def construire(opt, jauge, log_ui, annuler):
    """Pipeline complet. Retourne le chemin de l'exécutable créé."""
    lignes = []

    def log(texte, niveau="info"):
        lignes.append(texte)
        log_ui(texte, niveau)

    try:
        return _construire(opt, jauge, log, annuler)
    except Annule:
        raise
    except Exception as e:
        e.conseils = diagnostic.diagnostiquer(lignes, str(e))
        e.journal = lignes
        raise


def _construire(opt, jauge, log, annuler):
    nom = nettoyer_nom(opt.nom)
    if not Path(opt.entree).is_file():
        raise ErreurConstruction("Le fichier de démarrage est introuvable.")
    temp = Path(tempfile.gettempdir()) / "exeforge" / f"{nom}_{int(time.time())}"
    temp.mkdir(parents=True, exist_ok=True)
    try:
        jauge.aller(1, "Préparation…")
        opt.sortie.mkdir(parents=True, exist_ok=True)
        log("① Python", "etape")
        py = _preparer_python(opt, jauge, log, annuler)
        log("② Bibliothèques", "etape")
        _preparer_paquets(opt, py, jauge, log, annuler)
        log("③ Icône", "etape")
        ico = _preparer_icone(opt, temp, jauge, log)
        log("④ Compilation", "etape")
        exe = _lancer_pyinstaller(opt, py, ico, nom, temp, jauge, log, annuler)
        jauge.aller(100, "Terminé !")
        return exe
    finally:
        shutil.rmtree(temp, ignore_errors=True)
