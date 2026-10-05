"""ExeForge : python main.py  (ou ExeForge.exe)"""

import os
import sys
import time
import traceback
from pathlib import Path

from auteur import ligne_contact


def journal(texte):
    try:
        dossier = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "ExeForge"
        dossier.mkdir(parents=True, exist_ok=True)
        with open(dossier / "erreurs.log", "a", encoding="utf-8") as f:
            f.write(f"--- {time.strftime('%d/%m/%Y %H:%M:%S')}\n{texte}\n{ligne_contact()}\n")
    except OSError:
        pass


def nettete_windows():
    """Affichage net sur les écrans haute résolution + icône correcte dans la barre des tâches."""
    if os.name != "nt":
        return
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ExeForge.App")
    except Exception:
        pass


def main():
    import tkinter as tk
    from tkinter import messagebox
    try:
        import PIL  # noqa: F401
    except ImportError:
        racine = tk.Tk()
        racine.withdraw()
        if not getattr(sys, "frozen", False) and messagebox.askyesno(
                "ExeForge", "La bibliothèque Pillow (images) est nécessaire.\nL'installer maintenant ?"):
            import subprocess
            subprocess.call([sys.executable, "-m", "pip", "install", "Pillow"])
            racine.destroy()
            os.execv(sys.executable, [sys.executable] + sys.argv)
        messagebox.showerror("ExeForge", "Pillow est introuvable : pip install Pillow")
        return
    nettete_windows()
    from app import App
    racine = tk.Tk()

    def erreur(exc, val, tb):
        texte = "".join(traceback.format_exception(exc, val, tb))
        journal(texte)
        try:
            messagebox.showerror("ExeForge", f"Une erreur est survenue :\n{val}\n\n(détails : %LOCALAPPDATA%\\ExeForge\\erreurs.log)")
        except Exception:
            pass
    racine.report_callback_exception = erreur
    App(racine)
    racine.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        journal(traceback.format_exc())
        raise
