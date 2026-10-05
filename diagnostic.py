"""Diagnostic des échecs : lit le journal et explique la cause probable + comment réparer à la main."""

import re

from analyseur import nom_pip
from auteur import AUTEUR

PYTHON_URL = "https://www.python.org/downloads/release/python-31210/"


def _regles():
    return [
        (r"no module named '(_tkinter|tkinter)'",
         "Ce Python n'a pas Tkinter",
         "Ton programme utilise Tkinter mais le Python trouvé ne l'a pas.\n"
         "→ Onglet « Python & outils » > « Installer Python 3.12.10 » (Tkinter inclus), puis relance la création.\n"
         f"→ Ou réinstalle Python depuis {PYTHON_URL} en gardant la case « tcl/tk and IDLE » cochée."),
        (r"no matching distribution found for ([\w\-\.]+)|could not find a version that satisfies the requirement ([\w\-\.]+)",
         "Bibliothèque introuvable sur Internet (PyPI)",
         "Le nom de paquet deviné « {0} » n'existe pas, ou pas pour cette version de Python.\n"
         "→ Vérifie le vrai nom sur pypi.org, puis installe-le toi-même : ouvre l'invite de commandes et tape\n"
         "   py -m pip install NOM_DU_PAQUET\n"
         "→ Relance ensuite la création (il sera vu comme « déjà installé »)."),
        (r"microsoft visual c\+\+ 14\.0|failed building wheel|building wheel for .* did not run",
         "Une bibliothèque doit être compilée sur ton PC",
         "Cette bibliothèque n'a pas de version toute prête pour ton Python.\n"
         "→ Le plus simple : utilise Python 3.12 (onglet « Python & outils »).\n"
         "→ Sinon installe « Microsoft C++ Build Tools » (visualstudio.microsoft.com/visual-cpp-build-tools)."),
        (r"requires a different python|requires-python|python_requires",
         "Version de Python incompatible",
         "Une bibliothèque ne supporte pas cette version de Python.\n"
         "→ Onglet « Python & outils » > installe Python 3.12.10 : la version la plus compatible."),
        (r"getaddrinfo failed|name resolution|connection (refused|reset|aborted|timed out)|max retries exceeded|"
         r"urlerror|téléchargement impossible|timed out|network is unreachable|ssl.*(error|certificate)",
         "Problème de connexion Internet",
         "ExeForge n'a pas pu télécharger ce dont il avait besoin.\n"
         "→ Vérifie ta connexion, désactive un éventuel VPN/proxy, puis relance.\n"
         "→ Réseau d'entreprise ou d'école : télécharge toi-même Python 3.12.10 sur python.org et place le fichier "
         "python-3.12.10-amd64.exe dans le dossier « runtime » à côté de ExeForge (installation hors-ligne)."),
        (r"permissionerror|access is denied|accès refusé|winerror 5\b|winerror 32|being used by another process|"
         r"utilisé par un autre processus",
         "Windows refuse l'accès à un fichier",
         "Souvent : l'application est déjà ouverte, ou l'antivirus bloque le fichier.\n"
         "→ Ferme l'application (même nom) si elle tourne, puis relance.\n"
         "→ Choisis un autre « Dossier de l'exécutable » (ex. Bureau ou C:\\Projets).\n"
         "→ Ajoute temporairement ce dossier aux exclusions de Windows Defender / ton antivirus."),
        (r"winerror 225|contains a virus|operation did not complete successfully because",
         "L'antivirus a supprimé un fichier",
         "Faux positif classique avec les .exe créés par PyInstaller.\n"
         "→ Windows Sécurité > Protection contre les virus > Gérer les paramètres > Exclusions : ajoute le "
         "dossier de sortie et le dossier %TEMP%\\exeforge, puis relance."),
        (r"winerror 206|filename or extension is too long|path too long|nom de fichier ou l'extension est trop long",
         "Chemin trop long",
         "Un des chemins dépasse la limite de Windows (260 caractères).\n"
         "→ Déplace ton projet dans un dossier court (ex. C:\\Projets\\MonApp) et choisis un dossier de sortie court."),
        (r"no space left|not enough space|winerror 112|errno 28|espace insuffisant",
         "Disque plein",
         "Il n'y a plus assez de place pour compiler.\n"
         "→ Libère de l'espace (compte quelques centaines de Mo) ou change le dossier de sortie."),
        (r"syntaxerror|indentationerror|taberror",
         "Erreur dans ton propre code",
         "Un de tes fichiers Python contient une erreur de syntaxe : il ne peut pas être compilé.\n"
         "→ Lance-le d'abord avec Python (py ton_fichier.py), corrige l'erreur, puis relance la création."),
        (r"unsupported icon|failed to update icon|cannot (find|open) icon|icon.*(invalid|error|failed)",
         "Problème avec l'icône",
         "L'icône n'a pas pu être intégrée.\n"
         "→ Choisis une autre image, ou clique sur « ✕ » pour créer l'exécutable sans icône.\n"
         "→ Tu peux aussi générer le .ico dans l'onglet « Convertisseur d'icône »."),
        (r"no module named '([\w\.]+)'|modulenotfounderror|importerror: (dll load failed|cannot import)",
         "Module manquant dans l'exécutable",
         "PyInstaller n'a pas vu le module « {0} » (import caché ou dynamique).\n"
         "→ Dans « Options PyInstaller supplémentaires », écris :  --hidden-import {0}\n"
         "   (ou  --collect-all {0}  pour tout inclure, utile pour les gros paquets).\n"
         "→ Si le module n'est pas installé : py -m pip install {1}"),
        (r"l'installation de python a échoué|code 1603|inutilisable|installation automatique de python",
         "L'installation automatique de Python a échoué",
         f"→ Installe Python toi-même : {PYTHON_URL} (Windows installer 64-bit).\n"
         "→ Sur la 1re page de l'installateur, coche « Add python.exe to PATH ».\n"
         "→ Reviens dans ExeForge > « Python & outils » > « Détecter à nouveau »."),
        (r"pip est introuvable|no module named pip|ensurepip",
         "pip est absent de ce Python",
         "→ Dans l'invite de commandes :  py -m ensurepip --upgrade\n"
         "→ Ou réinstalle Python (onglet « Python & outils »)."),
    ]


def diagnostiquer(lignes, message=""):
    """-> liste de (titre, texte). La première entrée est la cause la plus probable."""
    original = "\n".join(list(lignes)[-400:] + [message or ""])
    texte = original.lower()
    conseils = []
    for motif, titre, aide in _regles():
        m = re.search(motif, texte, re.IGNORECASE)
        if not m:
            continue
        if titre.startswith("Module manquant"):
            mm = re.search(r"no module named '([\w\.]+)'", original, re.IGNORECASE)
            nom = mm.group(1).split(".")[0] if mm else "NOM_DU_MODULE"
            if nom in ("_tkinter", "tkinter"):
                continue
        else:
            nom = next((g for g in m.groups() if g), "NOM_DU_PAQUET").split(".")[0]
        conseils.append((titre, aide.replace("{0}", nom).replace("{1}", nom_pip(nom))))
    conseils.append((
        "Dans tous les cas",
        "→ Clique sur « Copier le journal » (ou « Enregistrer le journal ») : la dernière ligne ERROR indique la cause "
        "exacte ; tu peux la chercher sur Internet ou l'envoyer à quelqu'un qui peut t'aider.\n"
        "→ Pour essayer à la main : la ligne « Commande » du journal est celle que ExeForge lance ; "
        "colle-la dans l'invite de commandes (cmd) pour voir l'erreur en direct.\n"
        "→ Réessaie avec le format « Dossier » et « Avec console » : l'erreur apparaît alors au lancement du programme.\n"
        f"→ Toujours bloqué ? Contacte le créateur ({AUTEUR['nom']}) avec le journal : WhatsApp {AUTEUR['whatsapp']} "
        f"ou e-mail {AUTEUR['email']}."))
    return conseils


def formater(conseils, limite=None):
    sel = conseils[:limite] if limite else conseils
    return "\n\n".join(f"💡 {t}\n{a}" for t, a in sel)
