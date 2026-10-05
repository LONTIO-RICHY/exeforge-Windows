"""Interface graphique de ExeForge."""

import os
import queue
import subprocess
import sys
import threading
import time
import traceback
import webbrowser
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

import analyseur
from auteur import AUTEUR, ligne_contact
import constructeur
import diagnostic
import icones
import runtime_python as RP
import theme as T
from widgets import (BarreProgression, Bouton, Carte, FrameDefilant, Interrupteur, Segment,
                     auto_retour_ligne, champ, etiquette, rrect)

TITRE = "ExeForge — Créateur d'exécutables Python"
PAGES = (("creer", "🚀  Créer un .exe"), ("icone", "🖼  Convertisseur d'icône"),
         ("python", "🐍  Python & outils"), ("aide", "ℹ  Aide"), ("contact", "👤  Contact / Créateur"))
IMAGES = [("Images", "*.png *.jpg *.jpeg *.jfif *.bmp *.gif *.webp *.tif *.tiff *.ico *.tga"), ("Tous les fichiers", "*.*")]


def chemin_ressource(nom):
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / nom


class App:
    def __init__(self, root):
        self.root = root
        root.title(TITRE)
        root.configure(bg=T.FOND)
        root.geometry("1220x800+50+30")
        root.minsize(980, 660)
        try:
            root.iconbitmap(str(chemin_ressource("exeforge.ico")))
        except Exception:
            pass
        T.creer_polices(root)
        self.q = queue.Queue()
        self.plein = False
        self._apres_echelle = None
        self._photos = {}
        # état
        self.analyse = None
        self.info_py = None
        self.icone_source = None
        self.icone_reglages = ("ajuster", 0.0)
        self.conv_img = None
        self.conv_chemin = None
        self.annuler = threading.Event()
        self.en_cours = False
        self.dernier_exe = None
        self.derniere_activite = time.time()
        self.blocage_signale = False
        # variables
        self.v_nom = tk.StringVar()
        self.v_entree = tk.StringVar()
        self.v_format = tk.StringVar(value="un")
        self.v_fenetre = tk.StringVar(value="sans")
        self.v_res = tk.BooleanVar(value=True)
        self.v_sortie = tk.StringVar()
        self.v_extra = tk.StringVar()
        self.v_conv_mode = tk.StringVar(value="ajuster")
        self.v_conv_arrondi = tk.StringVar(value="aucun")
        self.v_conv_mode.trace_add("write", lambda *a: self.maj_conversion())
        self.v_conv_arrondi.trace_add("write", lambda *a: self.maj_conversion())

        self.style_ttk()
        self.construire()
        root.bind("<F11>", lambda e: self.basculer_plein_ecran())
        root.bind("<Escape>", lambda e: self.quitter_plein_ecran())
        root.bind("<Configure>", self.on_configure)
        self.afficher("creer")
        self.poll()
        self.detecter_python()

    # ================================================================== style
    def style_ttk(self):
        st = ttk.Style(self.root)
        try:
            st.theme_use("clam")
        except tk.TclError:
            pass
        st.configure("Fonce.Treeview", background=T.CARTE, fieldbackground=T.CARTE, foreground=T.TEXTE,
                     bordercolor=T.BORD, borderwidth=0, rowheight=T.px(26), font=T.POL["normal"])
        st.configure("Fonce.Treeview.Heading", background=T.CARTE_HAUT, foreground=T.BLANC, relief="flat",
                     font=T.POL["gras"], borderwidth=0)
        st.map("Fonce.Treeview", background=[("selected", T.CARTE_HAUT)], foreground=[("selected", T.BLANC)])
        st.map("Fonce.Treeview.Heading", background=[("active", T.BORD)])
        st.configure("Fonce.Vertical.TScrollbar", background=T.BORD, troughcolor=T.CARTE, bordercolor=T.CARTE,
                     arrowcolor=T.GRIS, lightcolor=T.BORD, darkcolor=T.BORD, gripcount=0)
        st.map("Fonce.Vertical.TScrollbar", background=[("active", T.ACCENT2)])

    def on_configure(self, e):
        if e.widget is not self.root:
            return
        if self._apres_echelle:
            self.root.after_cancel(self._apres_echelle)
        self._apres_echelle = self.root.after(120, self.recalculer_echelle)

    def recalculer_echelle(self):
        """Plus la fenêtre est grande (jusqu'au plein écran), plus textes et boutons grandissent."""
        w, h = self.root.winfo_width(), self.root.winfo_height()
        s = max(0.85, min(1.9, min(w / 1220.0, h / 800.0)))
        if abs(s - T.ECHELLE) < 0.04:
            return
        T.appliquer_echelle(s)
        self.style_ttk()
        for wdg in list(T.REG):
            try:
                wdg.ajuster()
            except tk.TclError:
                pass

    def basculer_plein_ecran(self):
        self.plein = not self.plein
        self.root.attributes("-fullscreen", self.plein)

    def quitter_plein_ecran(self):
        if self.plein:
            self.plein = False
            self.root.attributes("-fullscreen", False)

    # ================================================================== squelette
    def construire(self):
        r = self.root
        r.grid_rowconfigure(1, weight=1)
        r.grid_columnconfigure(0, weight=1)
        # ---- en-tête
        ent = tk.Frame(r, bg=T.PANEL)
        ent.grid(row=0, column=0, sticky="ew")
        ent.grid_columnconfigure(1, weight=1)
        logo = tk.Canvas(ent, width=46, height=46, bg=T.PANEL, highlightthickness=0)
        logo.grid(row=0, column=0, padx=(18, 10), pady=10)
        rrect(logo, 2, 2, 44, 44, 12, fill=T.ACCENT2, outline="")
        rrect(logo, 8, 8, 38, 38, 8, fill=T.ACCENT, outline="")
        logo.create_text(23, 23, text="EF", fill=T.FOND, font=("Segoe UI", 12, "bold"))
        titres = tk.Frame(ent, bg=T.PANEL)
        titres.grid(row=0, column=1, sticky="w")
        etiquette(titres, "ExeForge", "titre_app", fg=T.BLANC, bg=T.PANEL).pack(anchor="w")
        etiquette(titres, "Transforme tes programmes Python en applications Windows (.exe)", "petit",
                  fg=T.GRIS, bg=T.PANEL).pack(anchor="w")
        Bouton(ent, "⛶  Plein écran (F11)", self.basculer_plein_ecran, bg=T.PANEL, police="petit_gras",
               vpad=6).grid(row=0, column=2, padx=18)
        tk.Frame(r, bg=T.BORD, height=1).grid(row=0, column=0, sticky="sew")
        # ---- corps : navigation + pages
        corps = tk.Frame(r, bg=T.FOND)
        corps.grid(row=1, column=0, sticky="nsew")
        corps.grid_rowconfigure(0, weight=1)
        corps.grid_columnconfigure(1, weight=1)
        nav = tk.Frame(corps, bg=T.PANEL)
        nav.grid(row=0, column=0, sticky="ns")
        self.nav = {}
        for cle, texte in PAGES:
            lab = tk.Label(nav, text=texte, bg=T.PANEL, fg=T.GRIS, font=T.POL["nav"], anchor="w",
                           padx=20, pady=14, cursor="hand2")
            lab.pack(fill="x")
            lab.bind("<Button-1>", lambda e, c=cle: self.afficher(c))
            lab.bind("<Enter>", lambda e, l=lab: l.configure(bg=T.CARTE) if l["bg"] != T.CARTE_HAUT else None)
            lab.bind("<Leave>", lambda e, l=lab: l.configure(bg=T.PANEL) if l["bg"] != T.CARTE_HAUT else None)
            self.nav[cle] = lab
        pied = tk.Frame(r, bg=T.PANEL, cursor="hand2")
        pied.grid(row=2, column=0, sticky="ew")
        tk.Frame(pied, bg=T.BORD, height=1).pack(fill="x")
        self.lbl_pied = tk.Label(pied, text=f"Créé par {AUTEUR['nom']}   ·   Un problème ? Contacte-moi : "
                                            f"WhatsApp {AUTEUR['whatsapp']}  ·  {AUTEUR['email']}",
                                 bg=T.PANEL, fg=T.GRIS, font=T.POL["petit"], pady=6, cursor="hand2")
        self.lbl_pied.pack()
        self.lbl_pied.bind("<Button-1>", lambda e: self.afficher("contact"))
        self.lbl_pied.bind("<Enter>", lambda e: self.lbl_pied.configure(fg=T.ACCENT))
        self.lbl_pied.bind("<Leave>", lambda e: self.lbl_pied.configure(fg=T.GRIS))
        zone = tk.Frame(corps, bg=T.FOND)
        zone.grid(row=0, column=1, sticky="nsew")
        zone.grid_rowconfigure(0, weight=1)
        zone.grid_columnconfigure(0, weight=1)
        self.pages = {}
        for cle, fabrique in (("creer", self.page_creer), ("icone", self.page_icone),
                              ("python", self.page_python), ("aide", self.page_aide),
                              ("contact", self.page_contact)):
            page = tk.Frame(zone, bg=T.FOND)
            page.grid(row=0, column=0, sticky="nsew")
            fabrique(page)
            self.pages[cle] = page

    def afficher(self, cle):
        self.pages[cle].tkraise()
        for c, lab in self.nav.items():
            lab.configure(bg=T.CARTE_HAUT if c == cle else T.PANEL, fg=T.ACCENT if c == cle else T.GRIS)

    # ================================================================== page « Créer »
    def page_creer(self, page):
        page.grid_columnconfigure(0, weight=5, uniform="c")
        page.grid_columnconfigure(1, weight=6, uniform="c")
        page.grid_rowconfigure(0, weight=1)
        gauche = FrameDefilant(page, T.FOND)
        gauche.grid(row=0, column=0, sticky="nsew", padx=(18, 8), pady=14)
        g = gauche.interieur
        g.grid_columnconfigure(0, weight=1)

        # ① programme
        c1 = Carte(g, "①  Ton programme Python")
        c1.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        b = c1.corps
        b.grid_columnconfigure(0, weight=1)
        ligne = tk.Frame(b, bg=T.CARTE)
        ligne.grid(row=0, column=0, sticky="w")
        Bouton(ligne, "📄  Choisir un fichier .py", self.choisir_fichier, style="primaire").pack(side="left")
        Bouton(ligne, "📁  Choisir un dossier", self.choisir_dossier).pack(side="left", padx=(8, 0))
        self.lbl_projet = etiquette(b, "Aucun programme choisi. Prends un fichier seul, ou un dossier "
                                       "contenant plusieurs fichiers.", "petit", fg=T.GRIS)
        self.lbl_projet.grid(row=1, column=0, sticky="ew", pady=(8, 6))
        auto_retour_ligne(self.lbl_projet)
        etiquette(b, "Fichier de démarrage", "petit_gras", fg=T.GRIS).grid(row=2, column=0, sticky="w")
        self.menu_entree = tk.OptionMenu(b, self.v_entree, "")
        self.menu_entree.configure(bg=T.FOND, fg=T.BLANC, activebackground=T.CARTE_HAUT, activeforeground=T.BLANC,
                                   highlightthickness=1, highlightbackground=T.BORD, relief="flat", bd=0,
                                   font=T.POL["normal"], anchor="w", indicatoron=True)
        self.menu_entree["menu"].configure(bg=T.FOND, fg=T.BLANC, activebackground=T.ACCENT,
                                           activeforeground=T.FOND, font=T.POL["normal"], bd=0)
        self.menu_entree.grid(row=3, column=0, sticky="ew", pady=(2, 8))
        etiquette(b, "Nom de l'application", "petit_gras", fg=T.GRIS).grid(row=4, column=0, sticky="w")
        champ(b, self.v_nom).grid(row=5, column=0, sticky="ew", pady=(2, 0), ipady=5)

        # ② icône
        c2 = Carte(g, "②  Icône de l'exécutable")
        c2.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        b = c2.corps
        b.grid_columnconfigure(1, weight=1)
        self.cv_icone = tk.Canvas(b, width=96, height=96, bg=T.CARTE, highlightthickness=1,
                                  highlightbackground=T.BORD)
        self.cv_icone.grid(row=0, column=0, rowspan=3, padx=(0, 14))
        Bouton(b, "🖼  Choisir une image", self.choisir_icone, style="primaire").grid(row=0, column=1, sticky="w")
        bas = tk.Frame(b, bg=T.CARTE)
        bas.grid(row=1, column=1, sticky="w", pady=(6, 0))
        Bouton(bas, "Régler / aperçu", lambda: self.ouvrir_convertisseur(self.icone_source)).pack(side="left")
        Bouton(bas, "✕", self.retirer_icone).pack(side="left", padx=(6, 0))
        self.lbl_icone = etiquette(b, "N'importe quelle image (PNG, JPG, WEBP, BMP, GIF, ICO…) : elle est "
                                      "adaptée automatiquement.", "petit", fg=T.GRIS)
        self.lbl_icone.grid(row=2, column=1, sticky="ew", pady=(6, 0))
        auto_retour_ligne(self.lbl_icone, marge=T.px(110))
        self.maj_apercu_icone()

        # ③ options
        c3 = Carte(g, "③  Options")
        c3.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        b = c3.corps
        b.grid_columnconfigure(0, weight=1)
        etiquette(b, "Format", "petit_gras", fg=T.GRIS).grid(row=0, column=0, sticky="w")
        Segment(b, [("un", "Un seul fichier .exe"), ("dossier", "Dossier (démarre plus vite)")],
                self.v_format).grid(row=1, column=0, sticky="ew", pady=(2, 10))
        etiquette(b, "Fenêtre", "petit_gras", fg=T.GRIS).grid(row=2, column=0, sticky="w")
        Segment(b, [("sans", "Sans console (application graphique)"), ("avec", "Avec console")],
                self.v_fenetre).grid(row=3, column=0, sticky="ew", pady=(2, 10))
        Interrupteur(b, "Inclure les images, sons et données du projet", self.v_res).grid(
            row=4, column=0, sticky="ew", pady=(0, 10))
        etiquette(b, "Dossier de l'exécutable", "petit_gras", fg=T.GRIS).grid(row=5, column=0, sticky="w")
        ls = tk.Frame(b, bg=T.CARTE)
        ls.grid(row=6, column=0, sticky="ew", pady=(2, 10))
        ls.grid_columnconfigure(0, weight=1)
        champ(ls, self.v_sortie).grid(row=0, column=0, sticky="ew", ipady=5)
        Bouton(ls, "Parcourir", self.choisir_sortie).grid(row=0, column=1, padx=(8, 0))
        etiquette(b, "Options PyInstaller supplémentaires (avancé)", "petit_gras", fg=T.GRIS).grid(
            row=7, column=0, sticky="w")
        champ(b, self.v_extra).grid(row=8, column=0, sticky="ew", pady=(2, 0), ipady=5)

        # ---------------- colonne droite
        droite = tk.Frame(page, bg=T.FOND)
        droite.grid(row=0, column=1, sticky="nsew", padx=(8, 18), pady=14)
        droite.grid_columnconfigure(0, weight=1)
        droite.grid_rowconfigure(1, weight=1)

        ca = Carte(droite, "Analyse du projet")
        ca.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        b = ca.corps
        b.grid_columnconfigure(0, weight=1)
        self.lbl_py = etiquette(b, "🐍  Recherche de Python…", "gras", fg=T.JAUNE)
        self.lbl_py.grid(row=0, column=0, sticky="ew")
        auto_retour_ligne(self.lbl_py)
        self.lbl_resume = etiquette(b, "Choisis un programme pour lancer l'analyse.", "normal", fg=T.GRIS)
        self.lbl_resume.grid(row=1, column=0, sticky="ew", pady=(4, 8))
        auto_retour_ligne(self.lbl_resume)
        tf = tk.Frame(b, bg=T.CARTE)
        tf.grid(row=2, column=0, sticky="ew")
        tf.grid_columnconfigure(0, weight=1)
        self.arbre = ttk.Treeview(tf, columns=("lib", "pip", "etat"), show="headings", height=6,
                                  style="Fonce.Treeview")
        for col, titre, larg in (("lib", "Bibliothèque utilisée", 200), ("pip", "Paquet à installer", 170),
                                 ("etat", "État sur ce PC", 150)):
            self.arbre.heading(col, text=titre)
            self.arbre.column(col, width=larg, anchor="w")
        self.arbre.tag_configure("ok", foreground=T.VERT)
        self.arbre.tag_configure("dl", foreground=T.JAUNE)
        self.arbre.tag_configure("std", foreground=T.GRIS)
        sb = ttk.Scrollbar(tf, orient="vertical", command=self.arbre.yview, style="Fonce.Vertical.TScrollbar")
        self.arbre.configure(yscrollcommand=sb.set)
        self.arbre.grid(row=0, column=0, sticky="ew")
        sb.grid(row=0, column=1, sticky="ns")

        cc = Carte(droite, "Création")
        cc.grid(row=1, column=0, sticky="nsew")
        b = cc.corps
        b.grid_columnconfigure(0, weight=1)
        b.grid_rowconfigure(4, weight=1)
        boutons = tk.Frame(b, bg=T.CARTE)
        boutons.grid(row=0, column=0, sticky="ew")
        boutons.grid_columnconfigure(0, weight=1)
        self.btn_creer = Bouton(boutons, "🚀   CRÉER L'EXÉCUTABLE", self.lancer_creation, style="succes",
                                police="grand", vpad=12, rayon=14)
        self.btn_creer.grid(row=0, column=0, sticky="ew")
        self.btn_annuler = Bouton(boutons, "Annuler", self.demander_annulation, style="danger", vpad=12, rayon=14)
        self.btn_annuler.grid(row=0, column=1, padx=(8, 0))
        self.btn_annuler.activer(False)
        self.barre = BarreProgression(b, bg=T.CARTE)
        self.barre.grid(row=1, column=0, sticky="ew", pady=(12, 4))
        self.lbl_etape = etiquette(b, "En attente.", "normal", fg=T.GRIS)
        self.lbl_etape.grid(row=2, column=0, sticky="ew")
        self.cadre_fin = tk.Frame(b, bg=T.CARTE)
        self.cadre_fin.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        self.cadre_fin.grid_remove()
        self.lbl_fin = etiquette(self.cadre_fin, "", "gras", fg=T.VERT, bg=T.CARTE)
        self.lbl_fin.pack(anchor="w")
        auto_retour_ligne(self.lbl_fin)
        bf = tk.Frame(self.cadre_fin, bg=T.CARTE)
        bf.pack(anchor="w", pady=(6, 0))
        Bouton(bf, "📂  Ouvrir le dossier", self.ouvrir_dossier_exe, style="primaire").pack(side="left")
        Bouton(bf, "▶  Lancer l'application", self.lancer_exe).pack(side="left", padx=(8, 0))
        self.cadre_aide = tk.Frame(b, bg=T.CARTE, highlightthickness=1, highlightbackground=T.ROUGE)
        self.cadre_aide.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        self.cadre_aide.grid_remove()
        self.lbl_aide = etiquette(self.cadre_aide, "", "normal", fg=T.TEXTE, bg=T.CARTE)
        self.lbl_aide.pack(fill="x", padx=10, pady=(8, 4))
        auto_retour_ligne(self.lbl_aide, marge=T.px(24))
        ba = tk.Frame(self.cadre_aide, bg=T.CARTE)
        ba.pack(anchor="w", padx=10, pady=(0, 8))
        Bouton(ba, "📋  Copier le journal", self.copier_journal, style="primaire").pack(side="left")
        Bouton(ba, "💾  Enregistrer le journal", self.enregistrer_journal).pack(side="left", padx=(8, 0))
        Bouton(ba, "📞  Contacter le créateur", lambda: self.afficher("contact")).pack(side="left", padx=(8, 0))
        lf = tk.Frame(b, bg=T.CARTE)
        lf.grid(row=4, column=0, sticky="nsew", pady=(10, 0))
        lf.grid_rowconfigure(0, weight=1)
        lf.grid_columnconfigure(0, weight=1)
        self.journal = tk.Text(lf, bg=T.FOND, fg=T.TEXTE, font=T.POL["mono"], relief="flat", bd=0, height=8,
                               wrap="word", state="disabled", highlightthickness=1, highlightbackground=T.BORD,
                               padx=8, pady=6)
        sj = ttk.Scrollbar(lf, orient="vertical", command=self.journal.yview, style="Fonce.Vertical.TScrollbar")
        self.journal.configure(yscrollcommand=sj.set)
        self.journal.grid(row=0, column=0, sticky="nsew")
        sj.grid(row=0, column=1, sticky="ns")
        for tag, couleur in (("info", T.TEXTE), ("gris", T.GRIS), ("ok", T.VERT), ("warn", T.JAUNE),
                             ("err", T.ROUGE), ("etape", T.ACCENT)):
            self.journal.tag_configure(tag, foreground=couleur)
        self.journal.tag_configure("etape", font=T.POL["gras"], spacing1=6)

    # ---------------------------------------------------------------- choix du projet
    def choisir_fichier(self):
        if self.en_cours:
            return
        chemin = filedialog.askopenfilename(title="Choisis ton programme Python",
                                            filetypes=[("Programmes Python", "*.py *.pyw"), ("Tous", "*.*")])
        if chemin:
            self.charger_projet(chemin)

    def choisir_dossier(self):
        if self.en_cours:
            return
        chemin = filedialog.askdirectory(title="Choisis le dossier de ton projet", mustexist=True)
        if chemin:
            self.charger_projet(chemin)

    def charger_projet(self, chemin):
        self.lbl_projet.configure(text=f"Analyse de {chemin} …", fg=T.JAUNE)
        self.lbl_resume.configure(text="Analyse en cours…", fg=T.JAUNE)
        self.arbre.delete(*self.arbre.get_children())

        def travail():
            try:
                a = analyseur.analyser(chemin)
                info = RP.chercher_python(exiger_tk="tkinter" in a.stdlib_utilises)
                imports = sorted({m for p in a.paquets.values() for m in p.modules})
                dists = sorted({p.pip for p in a.paquets.values() if not p.modules})
                etat = RP.verifier(info, imports, dists)
                for p in a.paquets.values():
                    ok = all(etat["imports"].get(m) for m in p.modules) if p.modules else etat["dists"].get(p.pip)
                    p.etat = "installé" if ok else "à télécharger"
                self.q.put(("analyse", chemin, a, info, None))
            except Exception as e:
                self.q.put(("analyse", chemin, None, None, str(e)))
        threading.Thread(target=travail, daemon=True).start()

    def afficher_analyse(self, chemin, a, info, erreur):
        if erreur:
            self.analyse = None
            self.lbl_projet.configure(text=f"❌  {erreur}", fg=T.ROUGE)
            self.lbl_resume.configure(text="L'analyse a échoué.", fg=T.ROUGE)
            return
        self.analyse = a
        self.info_py = info
        n = len(a.fichiers)
        self.lbl_projet.configure(
            text=f"✔  {chemin}\n{n} fichier{'s' if n > 1 else ''} Python"
                 + (" (fichier seul + modules du même dossier qu'il utilise)" if a.mode == "fichier" else ""),
            fg=T.VERT)
        # point de départ
        menu = self.menu_entree["menu"]
        menu.delete(0, "end")
        for e in a.entrees:
            menu.add_command(label=e.as_posix(), command=lambda v=e.as_posix(): self.v_entree.set(v))
        self.v_entree.set(a.entree_defaut.as_posix())
        self.v_nom.set(a.entree_defaut.stem if a.entree_defaut.stem not in ("main", "app", "run", "__main__")
                       else a.racine.name)
        self.v_sortie.set(str(a.racine / "ExeForge_sortie"))
        self.v_res.set(bool(a.ressources))
        # tableau
        self.arbre.delete(*self.arbre.get_children())
        for p in sorted(a.paquets.values(), key=lambda p: p.pip.lower()):
            tag = "ok" if p.etat == "installé" else "dl"
            etat = "✔ déjà installé" if tag == "ok" else "⬇ à télécharger"
            self.arbre.insert("", "end", values=(", ".join(sorted(p.modules)) or "(requirements.txt)", p.pip, etat),
                              tags=(tag,))
        for m in sorted(a.stdlib_utilises):
            self.arbre.insert("", "end", values=(m, "inclus dans Python", "● standard"), tags=("std",))
        dl = [p for p in a.paquets.values() if p.etat != "installé"]
        texte = (f"{len(a.paquets)} bibliothèque(s) externe(s) : "
                 f"{len(a.paquets) - len(dl)} déjà installée(s), {len(dl)} à télécharger.")
        if not a.paquets:
            texte = "Aucune bibliothèque externe : seule la bibliothèque standard de Python est utilisée."
        if a.ressources:
            texte += f"\n{len(a.ressources)} élément(s) de ressources détecté(s) (images, sons, données)."
        for av in a.avertissements:
            texte += "\n⚠ " + av
        self.lbl_resume.configure(text=texte, fg=T.TEXTE)
        self.maj_etat_python(info, a)

    def maj_etat_python(self, info, a=None):
        a = a or self.analyse
        if info:
            self.lbl_py.configure(text=f"🐍  Python {info.txt} détecté ({info.source}) : aucun téléchargement "
                                       f"de Python nécessaire.", fg=T.VERT)
        elif a is not None and "tkinter" in a.stdlib_utilises:
            self.lbl_py.configure(text=f"🐍  Aucun Python avec Tkinter : Python {RP.VERSION} sera installé "
                                       f"automatiquement.", fg=T.JAUNE)
        else:
            self.lbl_py.configure(text=f"🐍  Aucun Python trouvé : Python {RP.VERSION} sera installé "
                                       f"automatiquement.", fg=T.JAUNE)

    # ---------------------------------------------------------------- icône (page Créer)
    def choisir_icone(self):
        chemin = filedialog.askopenfilename(title="Choisis l'image de ton icône", filetypes=IMAGES)
        if chemin:
            self.icone_source = Path(chemin)
            self.icone_reglages = ("ajuster", 0.0)
            self.maj_apercu_icone()

    def retirer_icone(self):
        self.icone_source = None
        self.maj_apercu_icone()

    def maj_apercu_icone(self):
        self.cv_icone.delete("all")
        try:
            if self.icone_source is None:
                raise ValueError
            img = icones.adapter_carre(icones.ouvrir_image(self.icone_source), *self.icone_reglages)
            photo = ImageTk.PhotoImage(icones.sur_damier(img, 90))
            self._photos["icone"] = photo
            self.cv_icone.create_image(48, 48, image=photo)
            self.lbl_icone.configure(text=f"{self.icone_source.name} → sera converti en .ico (16 à 256 px).",
                                     fg=T.VERT)
        except ValueError as e:
            self.cv_icone.create_text(48, 48, text="aucune\nicône", fill=T.GRIS, font=T.POL["petit"], justify="center")
            if self.icone_source is not None:
                self.lbl_icone.configure(text=f"❌ {e}", fg=T.ROUGE)
                self.icone_source = None
            else:
                self.lbl_icone.configure(text="N'importe quelle image (PNG, JPG, WEBP, BMP, GIF, ICO…) : elle est "
                                              "adaptée automatiquement.", fg=T.GRIS)

    def choisir_sortie(self):
        d = filedialog.askdirectory(title="Où créer l'exécutable ?")
        if d:
            self.v_sortie.set(d)

    # ---------------------------------------------------------------- création
    def lancer_creation(self):
        if self.en_cours:
            return
        if self.analyse is None:
            messagebox.showinfo("ExeForge", "Choisis d'abord un programme Python (fichier ou dossier).")
            return
        nom = self.v_nom.get().strip()
        if not nom or not self.v_sortie.get().strip():
            messagebox.showinfo("ExeForge", "Donne un nom à l'application et choisis le dossier de sortie.")
            return
        a = self.analyse
        opt = constructeur.Options(
            analyse=a, entree=a.racine / self.v_entree.get(), nom=nom, icone=self.icone_source,
            icone_reglages=self.icone_reglages, un_fichier=self.v_format.get() == "un",
            sans_console=self.v_fenetre.get() == "sans", ressources=self.v_res.get(),
            sortie=Path(self.v_sortie.get().strip()), extra=self.v_extra.get())
        self.en_cours = True
        self.annuler.clear()
        self.dernier_exe = None
        self.cadre_fin.grid_remove()
        self.cadre_aide.grid_remove()
        self.derniere_activite = time.time()
        self.blocage_signale = False
        self.btn_creer.activer(False)
        self.btn_annuler.activer(True)
        self.journal.configure(state="normal")
        self.journal.delete("1.0", "end")
        self.journal.configure(state="disabled")
        self.barre.reinitialiser()
        self.barre.activer(True)
        self.lbl_etape.configure(text="Démarrage…", fg=T.TEXTE)

        jauge = constructeur.Jauge(lambda v, t: self.q.put(("prog", v, t)))
        log = lambda texte, niveau="info": self.q.put(("log", texte, niveau))

        def travail():
            try:
                exe = constructeur.construire(opt, jauge, log, self.annuler)
                self.q.put(("fin", exe, None, []))
            except RP.Annule:
                self.q.put(("fin", None, "annule", []))
            except Exception as e:
                if not isinstance(e, (constructeur.ErreurConstruction, RP.ErreurPython)):
                    log(traceback.format_exc(), "err")
                conseils = getattr(e, "conseils", None) or diagnostic.diagnostiquer([], str(e))
                self.q.put(("fin", None, str(e) or e.__class__.__name__, conseils))
        threading.Thread(target=travail, daemon=True).start()

    def demander_annulation(self):
        if self.en_cours:
            self.annuler.set()
            self.lbl_etape.configure(text="Annulation en cours…", fg=T.JAUNE)

    def terminer_creation(self, exe, erreur, conseils=None):
        self.en_cours = False
        self.barre.activer(False)
        self.btn_creer.activer(True)
        self.btn_annuler.activer(False)
        if exe:
            self.dernier_exe = Path(exe)
            self.barre.definir(100)
            taille = self.dernier_exe.stat().st_size / 1e6 if self.dernier_exe.exists() else 0
            self.lbl_etape.configure(text="Terminé !", fg=T.VERT)
            self.lbl_fin.configure(text=f"✔  Exécutable créé ({taille:.1f} Mo) :\n{self.dernier_exe}")
            self.cadre_fin.grid()
            self.ecrire_journal(f"✔ Exécutable créé : {self.dernier_exe}", "ok")
        elif erreur == "annule":
            self.barre.reinitialiser()
            self.lbl_etape.configure(text="Création annulée.", fg=T.JAUNE)
            self.ecrire_journal("Création annulée.", "warn")
        else:
            self.lbl_etape.configure(text=f"❌  {erreur}", fg=T.ROUGE)
            self.ecrire_journal(f"❌ {erreur}", "err")
            conseils = conseils or diagnostic.diagnostiquer([], erreur)
            self.ecrire_journal("\n" + diagnostic.formater(conseils), "warn")
            self.lbl_aide.configure(text="Que faire ?  " + diagnostic.formater(conseils, 2))
            self.cadre_aide.grid()
            self.sauver_journal_auto()

    def ouvrir_dossier_exe(self):
        if self.dernier_exe and self.dernier_exe.exists():
            self.ouvrir_chemin(self.dernier_exe.parent)

    def lancer_exe(self):
        if self.dernier_exe and self.dernier_exe.exists():
            try:
                subprocess.Popen([str(self.dernier_exe)], cwd=str(self.dernier_exe.parent))
            except OSError as e:
                messagebox.showerror("ExeForge", f"Impossible de lancer l'application :\n{e}")

    @staticmethod
    def ouvrir_chemin(chemin):
        try:
            if os.name == "nt":
                os.startfile(str(chemin))
            else:
                subprocess.Popen(["xdg-open", str(chemin)])
        except Exception:
            pass

    # ---------------------------------------------------------------- journal
    def ecrire_journal(self, texte, niveau="info"):
        j = self.journal
        j.configure(state="normal")
        j.insert("end", texte + "\n", niveau)
        if int(float(j.index("end-1c"))) > 4000:
            j.delete("1.0", "500.0")
        j.see("end")
        j.configure(state="disabled")

    def texte_journal(self):
        return f"ExeForge — journal du {time.strftime('%d/%m/%Y %H:%M:%S')}\n{ligne_contact()}\n\n" \
               + self.journal.get("1.0", "end").strip()

    def copier_journal(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.texte_journal())
        self.lbl_etape.configure(text="📋 Journal copié : colle-le dans un message ou un document.", fg=T.VERT)

    def sauver_journal_auto(self):
        try:
            d = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "ExeForge"
            d.mkdir(parents=True, exist_ok=True)
            (d / "dernier_journal.txt").write_text(self.texte_journal(), encoding="utf-8")
        except OSError:
            pass

    def enregistrer_journal(self):
        f = filedialog.asksaveasfilename(title="Enregistrer le journal", defaultextension=".txt",
                                         initialfile="journal_exeforge.txt", filetypes=[("Texte", "*.txt")])
        if f:
            try:
                Path(f).write_text(self.texte_journal(), encoding="utf-8")
            except OSError as e:
                messagebox.showerror("ExeForge", f"Impossible d'enregistrer :\n{e}")

    # ================================================================== page « Icône »
    def page_icone(self, page):
        page.grid_columnconfigure(0, weight=1, uniform="i")
        page.grid_columnconfigure(1, weight=1, uniform="i")
        page.grid_rowconfigure(0, weight=1)
        etiquette(page, "Convertisseur d'icône", "titre_page", fg=T.BLANC, bg=T.FOND).grid(
            row=0, column=0, columnspan=2, sticky="nw", padx=22, pady=(14, 0))
        page.grid_rowconfigure(0, weight=0)
        page.grid_rowconfigure(1, weight=1)
        c1 = Carte(page, "Image de départ et réglages")
        c1.grid(row=1, column=0, sticky="nsew", padx=(18, 8), pady=14)
        b = c1.corps
        b.grid_columnconfigure(0, weight=1)
        Bouton(b, "🖼  Choisir une image…", self.conv_choisir, style="primaire").grid(row=0, column=0, sticky="w")
        self.lbl_conv = etiquette(b, "Aucune image. Formats acceptés : PNG, JPG, WEBP, BMP, GIF, TIFF, ICO…",
                                  "petit", fg=T.GRIS)
        self.lbl_conv.grid(row=1, column=0, sticky="ew", pady=(8, 14))
        auto_retour_ligne(self.lbl_conv)
        etiquette(b, "Adaptation au carré de l'icône", "petit_gras", fg=T.GRIS).grid(row=2, column=0, sticky="w")
        Segment(b, [("ajuster", "Ajuster"), ("remplir", "Remplir"), ("etirer", "Étirer")],
                self.v_conv_mode).grid(row=3, column=0, sticky="ew", pady=(2, 4))
        etiquette(b, "Ajuster : image entière, marges transparentes · Remplir : recadre au centre · "
                     "Étirer : déforme pour remplir", "petit", fg=T.GRIS).grid(row=4, column=0, sticky="w",
                                                                              pady=(0, 12))
        etiquette(b, "Coins arrondis", "petit_gras", fg=T.GRIS).grid(row=5, column=0, sticky="w")
        Segment(b, [("aucun", "Aucun"), ("leger", "Légers"), ("fort", "Forts")],
                self.v_conv_arrondi).grid(row=6, column=0, sticky="ew", pady=(2, 16))
        Bouton(b, "💾  Enregistrer en .ico…", self.conv_enregistrer, style="succes").grid(
            row=7, column=0, sticky="ew", pady=(0, 8))
        Bouton(b, "✔  Utiliser pour mon exécutable", self.conv_utiliser).grid(row=8, column=0, sticky="ew")
        c2 = Carte(page, "Aperçu (damier = transparence)")
        c2.grid(row=1, column=1, sticky="nsew", padx=(8, 18), pady=14)
        b = c2.corps
        b.grid_columnconfigure(0, weight=1)
        self.cv_conv = tk.Canvas(b, width=270, height=270, bg=T.CARTE, highlightthickness=0)
        self.cv_conv.grid(row=0, column=0, pady=(4, 10))
        self.cv_mini = tk.Canvas(b, width=420, height=140, bg=T.CARTE, highlightthickness=0)
        self.cv_mini.grid(row=1, column=0)
        self.lbl_tailles = etiquette(b, "Tailles enregistrées dans le .ico : 16, 24, 32, 48, 64, 96, 128 et 256 px "
                                        "(toutes les résolutions utilisées par Windows).", "petit", fg=T.GRIS)
        self.lbl_tailles.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        auto_retour_ligne(self.lbl_tailles)
        self.maj_conversion()

    def ouvrir_convertisseur(self, chemin=None):
        self.afficher("icone")
        if chemin:
            self.conv_charger(chemin)

    def conv_choisir(self):
        chemin = filedialog.askopenfilename(title="Choisis une image", filetypes=IMAGES)
        if chemin:
            self.conv_charger(chemin)

    def conv_charger(self, chemin):
        try:
            self.conv_img = icones.ouvrir_image(chemin)
            self.conv_chemin = Path(chemin)
            self.lbl_conv.configure(text=f"{self.conv_chemin.name} — {self.conv_img.width} × {self.conv_img.height} px",
                                    fg=T.VERT)
        except ValueError as e:
            self.conv_img = None
            self.lbl_conv.configure(text=f"❌ {e}", fg=T.ROUGE)
        self.maj_conversion()

    def conv_reglages(self):
        return self.v_conv_mode.get(), icones.ARRONDIS[self.v_conv_arrondi.get()]

    def maj_conversion(self):
        if not hasattr(self, "cv_conv"):
            return
        self.cv_conv.delete("all")
        self.cv_mini.delete("all")
        if self.conv_img is None:
            self.cv_conv.create_text(135, 135, text="Choisis une image\npour voir l'aperçu", fill=T.GRIS,
                                     font=T.POL["normal"], justify="center")
            return
        img = icones.adapter_carre(self.conv_img, *self.conv_reglages())
        grande = ImageTk.PhotoImage(icones.sur_damier(img, 256))
        self._photos["grande"] = grande
        self.cv_conv.create_image(135, 135, image=grande)
        x = 8
        for i, t in enumerate((16, 32, 48, 64, 96)):
            p = ImageTk.PhotoImage(icones.sur_damier(img, t))
            self._photos[f"mini{i}"] = p
            self.cv_mini.create_image(x + t // 2, 56, image=p)
            self.cv_mini.create_text(x + t // 2, 124, text=f"{t}", fill=T.GRIS, font=T.POL["petit"])
            x += t + 22

    def conv_enregistrer(self):
        if self.conv_img is None:
            messagebox.showinfo("ExeForge", "Choisis d'abord une image.")
            return
        sortie = filedialog.asksaveasfilename(title="Enregistrer l'icône", defaultextension=".ico",
                                              initialfile=self.conv_chemin.stem + ".ico",
                                              filetypes=[("Icône Windows", "*.ico")])
        if not sortie:
            return
        try:
            tailles = icones.convertir_en_ico(self.conv_chemin, sortie, *self.conv_reglages())
            messagebox.showinfo("ExeForge", f"Icône enregistrée !\n{sortie}\n\nTailles : "
                                            + ", ".join(str(t) for t in tailles) + " px")
        except Exception as e:
            messagebox.showerror("ExeForge", f"Conversion impossible :\n{e}")

    def conv_utiliser(self):
        if self.conv_img is None:
            messagebox.showinfo("ExeForge", "Choisis d'abord une image.")
            return
        self.icone_source = self.conv_chemin
        self.icone_reglages = self.conv_reglages()
        self.maj_apercu_icone()
        self.afficher("creer")

    # ================================================================== page « Python & outils »
    def page_python(self, page):
        page.grid_columnconfigure(0, weight=1)
        etiquette(page, "Python & outils", "titre_page", fg=T.BLANC, bg=T.FOND).grid(
            row=0, column=0, sticky="nw", padx=22, pady=(14, 0))
        c = Carte(page, "Python utilisé pour créer tes exécutables")
        c.grid(row=1, column=0, sticky="new", padx=18, pady=14)
        b = c.corps
        b.grid_columnconfigure(0, weight=1)
        self.lbl_py2 = etiquette(b, "Recherche en cours…", "normal", fg=T.JAUNE)
        self.lbl_py2.grid(row=0, column=0, sticky="ew")
        auto_retour_ligne(self.lbl_py2)
        lbl_info = etiquette(b, f"ExeForge réutilise le Python déjà installé sur ce PC. S'il n'y en a pas, il installe Python "
                     f"{RP.VERSION} (version stable 3.12) pour lui seul, sans droits administrateur et sans "
                     f"toucher à ton système. Si le fichier python-{RP.VERSION}-amd64.exe est placé dans le "
                     f"dossier « runtime » à côté de ExeForge, il est utilisé sans connexion Internet.",
                  "petit", fg=T.GRIS)
        lbl_info.grid(row=1, column=0, sticky="ew", pady=(8, 12))
        auto_retour_ligne(lbl_info)
        lb = tk.Frame(b, bg=T.CARTE)
        lb.grid(row=2, column=0, sticky="w")
        Bouton(lb, "🔄  Détecter à nouveau", self.detecter_python).pack(side="left")
        self.btn_inst_py = Bouton(lb, f"⬇  Installer Python {RP.VERSION}", self.installer_python, style="primaire")
        self.btn_inst_py.pack(side="left", padx=(8, 0))
        Bouton(lb, "📂  Dossier privé", lambda: self.ouvrir_chemin(RP.dossier_prive().parent)).pack(
            side="left", padx=(8, 0))
        self.barre_py = BarreProgression(b, bg=T.CARTE)
        self.barre_py.grid(row=3, column=0, sticky="ew", pady=(14, 4))
        self.lbl_py_etape = etiquette(b, "", "petit", fg=T.GRIS)
        self.lbl_py_etape.grid(row=4, column=0, sticky="ew")

    def detecter_python(self):
        self.lbl_py2_texte("Recherche de Python…", T.JAUNE)

        def travail():
            self.q.put(("python", RP.chercher_python()))
        threading.Thread(target=travail, daemon=True).start()

    def lbl_py2_texte(self, texte, couleur):
        if hasattr(self, "lbl_py2"):
            self.lbl_py2.configure(text=texte, fg=couleur)

    def installer_python(self):
        if self.en_cours:
            return
        self.en_cours = True
        self.annuler.clear()
        self.btn_inst_py.activer(False)
        self.barre_py.reinitialiser()
        self.barre_py.activer(True)

        def travail():
            try:
                info = RP.installer_python_prive(lambda f, t: self.q.put(("py_prog", f * 100, t)), self.annuler)
                self.q.put(("py_fin", info, None))
            except Exception as e:
                self.q.put(("py_fin", None, str(e) or "annulé"))
        threading.Thread(target=travail, daemon=True).start()

    # ================================================================== page « Aide »
    def page_aide(self, page):
        page.grid_columnconfigure(0, weight=1)
        etiquette(page, "Aide", "titre_page", fg=T.BLANC, bg=T.FOND).grid(
            row=0, column=0, sticky="nw", padx=22, pady=(14, 0))
        c = Carte(page, "Comment ça marche ?")
        c.grid(row=1, column=0, sticky="new", padx=18, pady=14)
        etapes = (
            "1.  Choisis ton programme : un fichier .py seul, ou le dossier d'un projet qui contient plusieurs fichiers.",
            "2.  ExeForge lit le code, repère les bibliothèques utilisées et regarde lesquelles sont déjà sur ce PC. "
            "Seules celles qui manquent sont téléchargées.",
            "3.  (Facultatif) Choisis une image : elle est convertie automatiquement en icône .ico à toutes les tailles.",
            "4.  Clique sur « Créer l'exécutable » : la barre de progression avance étape par étape. "
            "À la fin, ouvre le dossier ou lance directement ton application.",
            "",
            "• Fichier de démarrage : le fichier qui lance ton programme (souvent main.py).",
            "• Sans console : l'application s'ouvre sans fenêtre noire (pour les programmes graphiques : Tkinter, pygame…).",
            "• Un seul fichier : pratique à partager, mais démarre un peu plus lentement que le format « dossier ».",
            "• Les programmes créés tournent sans Python installé sur l'ordinateur de ceux qui les utilisent.",
            "• Raccourcis : F11 plein écran · Échap quitter le plein écran. La fenêtre s'agrandit à volonté.",
            f"• Un problème ? Contacte le créateur ({AUTEUR['nom']}) : onglet « Contact / Créateur » ou WhatsApp "
            f"{AUTEUR['whatsapp']}.",
        )
        for i, t in enumerate(etapes):
            lab = etiquette(c.corps, t, "normal", fg=T.TEXTE if t[:1].isdigit() else T.GRIS)
            lab.grid(row=i, column=0, sticky="ew", pady=2)
            c.corps.grid_columnconfigure(0, weight=1)
        for lab in c.corps.grid_slaves():
            lab.configure(wraplength=700)
        c.corps.bind("<Configure>", lambda e: [l.configure(wraplength=max(200, e.width - 10))
                                              for l in c.corps.grid_slaves()])

    # ================================================================== page « Contact »
    def page_contact(self, page):
        page.grid_columnconfigure(0, weight=1)
        etiquette(page, "Contact / Créateur", "titre_page", fg=T.BLANC, bg=T.FOND).grid(
            row=0, column=0, sticky="nw", padx=22, pady=(14, 0))
        c = Carte(page, "Créateur du logiciel")
        c.grid(row=1, column=0, sticky="new", padx=18, pady=14)
        b = c.corps
        b.grid_columnconfigure(0, weight=1)
        etiquette(b, AUTEUR["nom"], "titre_page", fg=T.ACCENT).grid(row=0, column=0, sticky="w")
        lab = etiquette(b, "ExeForge a été créé par lui. Un problème, une erreur, une question ou une idée "
                           "d'amélioration ? Écris-lui : joins le journal (bouton « Copier le journal » après un échec) "
                           "pour qu'il comprenne vite.", "normal", fg=T.GRIS)
        lab.grid(row=1, column=0, sticky="ew", pady=(4, 14))
        auto_retour_ligne(lab)
        lignes = (("💬  WhatsApp", AUTEUR["whatsapp"], AUTEUR["whatsapp_lien"], "WhatsApp"),
                  ("✉  E-mail", AUTEUR["email"], "mailto:" + AUTEUR["email"], "E-mail"),
                  ("</>  GitHub", AUTEUR["github"], AUTEUR["github"], "GitHub"))
        for i, (titre, valeur, lien, nom) in enumerate(lignes):
            ligne = tk.Frame(b, bg=T.CARTE_HAUT, highlightthickness=1, highlightbackground=T.BORD)
            ligne.grid(row=2 + i, column=0, sticky="ew", pady=5)
            ligne.grid_columnconfigure(0, weight=1)
            txt = tk.Frame(ligne, bg=T.CARTE_HAUT)
            txt.grid(row=0, column=0, sticky="w", padx=14, pady=10)
            etiquette(txt, titre, "petit_gras", fg=T.ACCENT, bg=T.CARTE_HAUT).pack(anchor="w")
            etiquette(txt, valeur, "gras", fg=T.BLANC, bg=T.CARTE_HAUT).pack(anchor="w")
            bt = tk.Frame(ligne, bg=T.CARTE_HAUT)
            bt.grid(row=0, column=1, padx=12)
            Bouton(bt, "Ouvrir", lambda l=lien: self.ouvrir_lien(l), style="primaire", bg=T.CARTE_HAUT).pack(
                side="left")
            Bouton(bt, "Copier", lambda v=valeur, n=nom: self.copier_contact(v, n), bg=T.CARTE_HAUT).pack(
                side="left", padx=(6, 0))
        self.lbl_contact = etiquette(b, "", "petit", fg=T.VERT)
        self.lbl_contact.grid(row=6, column=0, sticky="w", pady=(10, 0))

    def ouvrir_lien(self, url):
        try:
            webbrowser.open(url)
        except Exception:
            self.copier_contact(url, "Lien")

    def copier_contact(self, texte, nom):
        self.root.clipboard_clear()
        self.root.clipboard_append(texte)
        self.lbl_contact.configure(text=f"✔ {nom} copié : colle-le où tu veux.")

    # ================================================================== file de messages (threads -> interface)
    def poll(self):
        if self.en_cours and not self.blocage_signale and time.time() - self.derniere_activite > 150:
            self.blocage_signale = True
            self.ecrire_journal("⏳ Aucune activité depuis plus de 2 minutes. Ça peut être normal (gros téléchargement, "
                                "grosse compilation, antivirus qui analyse). Patiente encore un peu ; sinon clique sur "
                                "« Annuler », vérifie ta connexion Internet, puis relance. Si ça bloque toujours, "
                                "essaie le format « Dossier » ou copie le journal pour le montrer à quelqu'un.", "warn")
            self.lbl_etape.configure(text="⏳ Toujours en cours… (rien de nouveau depuis 2 min, voir le journal)",
                                     fg=T.JAUNE)
        try:
            for _ in range(300):
                self.traiter(self.q.get_nowait())
        except queue.Empty:
            pass
        except Exception:
            self.ecrire_journal(traceback.format_exc(), "err")
        self.root.after(40, self.poll)

    def traiter(self, msg):
        genre = msg[0]
        self.derniere_activite = time.time()
        self.blocage_signale = False
        if genre == "log":
            self.ecrire_journal(msg[1], msg[2])
        elif genre == "prog":
            self.barre.definir(msg[1])
            if msg[2]:
                self.lbl_etape.configure(text=msg[2], fg=T.TEXTE)
        elif genre == "fin":
            self.terminer_creation(msg[1], msg[2], msg[3] if len(msg) > 3 else None)
        elif genre == "analyse":
            self.afficher_analyse(msg[1], msg[2], msg[3], msg[4])
        elif genre == "python":
            self.info_py = msg[1]
            if msg[1]:
                self.lbl_py2_texte(f"✔  Python {msg[1].txt} ({msg[1].source})\n{msg[1].exe}", T.VERT)
            else:
                self.lbl_py2_texte(f"Aucun Python utilisable trouvé. Python {RP.VERSION} sera installé "
                                   f"automatiquement au premier besoin (ou clique sur « Installer »).", T.JAUNE)
            self.maj_etat_python(msg[1])
        elif genre == "py_prog":
            self.barre_py.definir(msg[1])
            self.lbl_py_etape.configure(text=msg[2])
        elif genre == "py_fin":
            self.en_cours = False
            self.barre_py.activer(False)
            self.btn_inst_py.activer(True)
            if msg[1]:
                self.barre_py.definir(100)
                self.lbl_py_etape.configure(text=f"✔ Python {msg[1].txt} installé.", fg=T.VERT)
                self.q.put(("python", msg[1]))
            else:
                self.lbl_py_etape.configure(text=f"❌ {msg[2]}\n\n" + diagnostic.formater(
                    diagnostic.diagnostiquer([], msg[2]), 1), fg=T.ROUGE)
