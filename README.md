<div align="center">

<img src="exeforge_icone.png" alt="Logo ExeForge" width="140">

# ExeForge

**Transforme n'importe quel programme Python en application Windows (.exe), en quelques clics.**

Fichier seul ou projet de plusieurs fichiers · icône personnalisée · barre de progression · interface graphique

</div>

---

## ✨ Fonctionnalités

- **Un fichier ou un projet entier** : choisis un `.py`, ou le dossier d'un projet qui contient plusieurs fichiers.
- **Analyse automatique du code** : ExeForge repère toutes les bibliothèques utilisées (et lit `requirements.txt` s'il existe).
- **Aucun téléchargement inutile** : il vérifie ce qui est déjà installé sur le PC et ne télécharge que ce qui manque.
- **Python intégré si besoin** : s'il n'y a pas de Python sur l'ordinateur, ExeForge installe **Python 3.12.10** (version stable) pour son propre usage, sans droits administrateur et sans toucher au système.
- **Icône `.ico` à partir de n'importe quelle image** : PNG, JPG, WEBP, BMP, GIF, TIFF, ICO… L'image est adaptée automatiquement (ajuster, recadrer, étirer, coins arrondis) et enregistrée à toutes les tailles Windows (16 à 256 px).
- **Convertisseur d'icône** : un onglet dédié pour créer un `.ico` sans fabriquer d'exécutable.
- **Barre de progression** animée qui suit chaque étape de la création.
- **Aide en cas d'erreur** : ExeForge explique la cause probable (module manquant, Internet, antivirus, chemin trop long…) et ce que tu peux faire à la main ; journal copiable et ligne de commande réutilisable.
- **Design moderne et redimensionnable** : la fenêtre s'agrandit jusqu'au plein écran (`F11`) et l'interface suit.

## 📦 Installation

### Prérequis
- Windows 10 ou 11
- [Python 3.9 ou plus récent](https://www.python.org/downloads/) (3.12 recommandé) — *uniquement pour lancer ExeForge depuis le code source*

### Lancer depuis le code source
```bat
git clone https://github.com/LONTIo-RICHY/ExeForge.git
cd ExeForge
py -m pip install -r requirements.txt
py main.py
```
Ou double-clique sur **`LANCER.bat`**.

### Créer `ExeForge.exe` (application autonome)
Double-clique sur **`CREER_EXE.bat`** : le résultat est dans `dist\ExeForge.exe`.

> **Version 100 % autonome (sans Internet)** : place l'installateur officiel
> [`python-3.12.10-amd64.exe`](https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe)
> dans le dossier `runtime/` avant de lancer `CREER_EXE.bat`. Il sera intégré à `ExeForge.exe`.

## 🚀 Utilisation

1. **Ton programme** : clique sur *Choisir un fichier .py* ou *Choisir un dossier*.
2. **Analyse** : le tableau liste les bibliothèques (`✔ déjà installé` / `⬇ à télécharger`).
3. **Icône** *(facultatif)* : choisis une image, elle devient un `.ico`.
4. **Options** : format, fenêtre, ressources, dossier de sortie.
5. **CRÉER L'EXÉCUTABLE** : suis la barre de progression, puis ouvre le dossier ou lance l'application.

### Les options en bref

| Option | Rôle |
|---|---|
| Fichier de démarrage | Le fichier qui lance le programme (souvent `main.py`) |
| Nom de l'application | Nom du futur `.exe` |
| Un seul fichier / Dossier | Un `.exe` unique (simple à partager) ou un dossier (démarrage plus rapide) |
| Sans console / Avec console | Sans fenêtre noire (programmes graphiques) ou avec (programmes en texte, utile pour déboguer) |
| Inclure les ressources | Emporte images, sons et données du projet |
| Options PyInstaller | Pour les cas difficiles, ex. `--hidden-import nom` |

## ⚙️ Comment ça marche

```
Ton code ──► Analyse (imports, fichiers, ressources)
        ──► Python : détecté, sinon Python 3.12.10 installé en privé
        ──► Bibliothèques : seules celles qui manquent sont téléchargées (pip)
        ──► Icône : image ──► .ico multi-tailles
        ──► PyInstaller ──► ton .exe
```

ExeForge s'appuie sur [PyInstaller](https://pyinstaller.org/) pour la compilation et [Pillow](https://python-pillow.org/) pour les images.

## 🛠️ En cas de problème

- Le cadre rouge **« Que faire ? »** explique la cause probable et la solution.
- Boutons **Copier / Enregistrer le journal** ; une copie est écrite dans `%LOCALAPPDATA%\ExeForge\dernier_journal.txt`.
- La ligne **« Commande : … »** du journal peut être collée dans `cmd` pour voir l'erreur en direct.
- Faux positif antivirus : fréquent avec les `.exe` créés par PyInstaller (surtout en « un seul fichier »). Ajoute le dossier de sortie aux exclusions.

Limites connues : certaines bibliothèques lourdes (IA, Qt…) demandent des options PyInstaller supplémentaires ; les `.exe` créés fonctionnent sous Windows.

## 🗂️ Structure du projet

| Fichier | Rôle |
|---|---|
| `main.py` | Point d'entrée |
| `app.py` | Interface graphique |
| `widgets.py`, `theme.py` | Design (boutons, barre de progression, couleurs) |
| `analyseur.py` | Analyse du code et des bibliothèques |
| `runtime_python.py` | Détection / installation de Python, pip |
| `icones.py` | Conversion d'images en `.ico` |
| `constructeur.py` | Création de l'exécutable et progression |
| `diagnostic.py` | Explication des erreurs |
| `auteur.py` | Informations du créateur |

## 👤 Créateur et contact

**LONTIO KESSEL || LONTIO RICHY**

Un problème, une question, une idée ? Contacte-moi :

- 💬 WhatsApp : [+237 650 196 251](https://wa.me/237650196251)
- ✉️ E-mail : [lontiokessel@gmail.com](mailto:lontiokessel@gmail.com)
- 🐙 GitHub : [github.com/LONTIo-RICHY](https://github.com/LONTIo-RICHY)

Tu peux aussi ouvrir une **issue** sur ce dépôt (colle le journal d'ExeForge).
