"""Widgets personnalisés : boutons arrondis, barre de progression animée, interrupteurs..."""

import tkinter as tk
from tkinter import ttk

import theme as T


def rrect(c, x0, y0, x1, y1, r, **kw):
    """Rectangle aux coins arrondis dessiné sur un Canvas."""
    r = max(0, min(r, (x1 - x0) / 2, (y1 - y0) / 2))
    pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1, x1 - r, y1,
           x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
    return c.create_polygon(pts, smooth=True, **kw)


def etiquette(parent, texte, police="normal", fg=None, bg=None, **kw):
    bg = bg or parent.cget("bg")
    kw.setdefault("anchor", "w")
    kw.setdefault("justify", "left")
    return tk.Label(parent, text=texte, bg=bg, fg=fg or T.TEXTE, font=T.POL[police], **kw)


def auto_retour_ligne(label, marge=0):
    """Le texte du label passe à la ligne selon la largeur de son conteneur."""
    label.master.bind("<Configure>",
                      lambda e, l=label: l.configure(wraplength=max(80, e.width - marge)), add="+")


def champ(parent, variable, bg=None):
    bg = bg or parent.cget("bg")
    return tk.Entry(parent, textvariable=variable, bg=T.FOND, fg=T.BLANC, insertbackground=T.ACCENT,
                    relief="flat", bd=0, font=T.POL["normal"], highlightthickness=1,
                    highlightbackground=T.BORD, highlightcolor=T.ACCENT,
                    disabledbackground=T.FOND, disabledforeground=T.GRIS)


# ------------------------------------------------------------------ boutons
STYLES = {      # fond, fond survolé, texte, bordure
    "primaire": (T.ACCENT, T.melanger(T.ACCENT, "#ffffff", 0.28), T.FOND, ""),
    "succes": (T.VERT_BOUTON, T.melanger(T.VERT_BOUTON, "#ffffff", 0.22), T.FOND, ""),
    "danger": (T.ROUGE_BOUTON, T.melanger(T.ROUGE_BOUTON, "#ffffff", 0.2), T.BLANC, ""),
    "secondaire": (T.CARTE_HAUT, T.melanger(T.CARTE_HAUT, "#ffffff", 0.14), T.BLANC, T.BORD),
}


class Bouton(tk.Canvas):
    def __init__(self, parent, texte, commande=None, style="secondaire", police="gras",
                 bg=None, hpad=16, vpad=8, rayon=10):
        super().__init__(parent, bg=bg or parent.cget("bg"), highlightthickness=0, bd=0, cursor="hand2")
        self.texte, self.commande, self.style = texte, commande, style
        self.police, self.hpad, self.vpad, self.rayon = police, hpad, vpad, rayon
        self._actif, self._survol, self._appui = True, False, False
        self.bind("<Configure>", lambda e: self._dessiner())
        self.bind("<Enter>", lambda e: self._maj(survol=True))
        self.bind("<Leave>", lambda e: self._maj(survol=False, appui=False))
        self.bind("<ButtonPress-1>", lambda e: self._maj(appui=True))
        self.bind("<ButtonRelease-1>", self._relache)
        T.REG.append(self)
        self.ajuster()

    def ajuster(self):
        f = T.POL[self.police]
        self.configure(width=f.measure(self.texte) + 2 * T.px(self.hpad),
                       height=f.metrics("linespace") + 2 * T.px(self.vpad))
        self._dessiner()

    def definir_texte(self, texte):
        self.texte = texte
        self.ajuster()

    def activer(self, oui):
        self._actif = bool(oui)
        self.configure(cursor="hand2" if oui else "arrow")
        self._dessiner()

    def _maj(self, survol=None, appui=None):
        if survol is not None:
            self._survol = survol
        if appui is not None:
            self._appui = appui
        self._dessiner()

    def _relache(self, e):
        etait = self._appui
        self._maj(appui=False)
        if etait and self._actif and self.commande and 0 <= e.x <= self.winfo_width() and 0 <= e.y <= self.winfo_height():
            self.commande()

    def _dessiner(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 1:
            w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        fond, survol, fg, bord = STYLES[self.style]
        if not self._actif:
            couleur, fg, bord = T.CARTE, T.GRIS, T.BORD
        else:
            couleur = survol if self._survol else fond
            if self._appui:
                couleur = T.melanger(fond, "#000000", 0.2)
        rrect(self, 1, 1, w - 1, h - 1, T.px(self.rayon), fill=couleur, outline=bord)
        self.create_text(w / 2, h / 2, text=self.texte, fill=fg, font=T.POL[self.police])


# ------------------------------------------------------------------ barre de progression
class BarreProgression(tk.Canvas):
    """Barre arrondie en dégradé violet -> cyan, avec rayures animées pendant le travail."""

    def __init__(self, parent, bg=None):
        super().__init__(parent, bg=bg or parent.cget("bg"), highlightthickness=0, bd=0, height=T.px(30))
        self.cible = self.affiche = 0.0
        self.actif = False
        self.phase = 0.0
        self._boucle = False
        self.bind("<Configure>", lambda e: self._dessiner())
        T.REG.append(self)

    def ajuster(self):
        self.configure(height=T.px(30))
        self._dessiner()

    def definir(self, valeur):
        self.cible = max(0.0, min(100.0, float(valeur)))
        self._demarrer()

    def reinitialiser(self):
        self.cible = self.affiche = 0.0
        self.actif = False
        self._dessiner()

    def activer(self, oui):
        self.actif = bool(oui)
        self._demarrer()

    def _demarrer(self):
        if not self._boucle:
            self._boucle = True
            self.after(16, self._tick)

    def _tick(self):
        try:
            ecart = self.cible - self.affiche
            self.affiche = self.cible if abs(ecart) < 0.05 else self.affiche + ecart * 0.15
            if self.actif:
                self.phase = (self.phase + 1.4) % 28
            self._dessiner()
            continuer = self.actif or abs(self.cible - self.affiche) > 0.01
        except tk.TclError:
            self._boucle = False
            return
        if continuer:
            self.after(33, self._tick)
        else:
            self._boucle = False

    def _dessiner(self):
        w, h = self.winfo_width(), self.winfo_height()
        if w < 10 or h < 6:
            return
        self.delete("all")
        r = h / 2
        rrect(self, 1, 1, w - 1, h - 1, r, fill=T.CARTE, outline=T.BORD)
        largeur = (w - 4) * self.affiche / 100.0
        if largeur > 2:
            fx1 = 2 + largeur
            couleur = T.melanger(T.ACCENT2, T.ACCENT, self.affiche / 100.0)
            rrect(self, 2, 2, fx1, h - 2, r - 2, fill=couleur, outline="")
            if self.actif and largeur > 24:
                clair = T.melanger(couleur, "#ffffff", 0.25)
                for sx in range(-28, int(fx1) + 28, 28):
                    xs = sx + self.phase
                    pts = [(xs, h - 4), (xs + 9, 4), (xs + 21, 4), (xs + 12, h - 4)]
                    xs_c = [min(max(p[0], 4), fx1 - 4) for p in pts]
                    if max(xs_c) - min(xs_c) > 1:
                        self.create_polygon([c for x, (_, y) in zip(xs_c, pts) for c in (x, y)],
                                            fill=clair, outline="")
        texte = f"{int(self.affiche)} %"
        self.create_text(w / 2 + 1, h / 2 + 1, text=texte, fill="#000000", font=T.POL["pct"])
        self.create_text(w / 2, h / 2, text=texte, fill=T.BLANC, font=T.POL["pct"])


# ------------------------------------------------------------------ interrupteur et sélecteur
class Interrupteur(tk.Frame):
    def __init__(self, parent, texte, variable, bg=None):
        bg = bg or parent.cget("bg")
        super().__init__(parent, bg=bg)
        self.var, self.fond = variable, bg
        self.sw = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0, cursor="hand2")
        self.sw.grid(row=0, column=0, sticky="n", padx=(0, 10))
        self.lab = tk.Label(self, text=texte, bg=bg, fg=T.TEXTE, font=T.POL["normal"], anchor="w",
                            justify="left", cursor="hand2")
        self.lab.grid(row=0, column=1, sticky="ew")
        self.grid_columnconfigure(1, weight=1)
        for w in (self.sw, self.lab):
            w.bind("<Button-1>", lambda e: self.var.set(not self.var.get()))
        self.var.trace_add("write", lambda *a: self._dessiner())
        self.bind("<Configure>", lambda e: self.lab.configure(wraplength=max(60, e.width - T.px(60))))
        T.REG.append(self)
        self.ajuster()

    def ajuster(self):
        self.sw.configure(width=T.px(42), height=T.px(22))
        self._dessiner()

    def _dessiner(self):
        c, w, h = self.sw, T.px(42), T.px(22)
        c.delete("all")
        on = bool(self.var.get())
        rrect(c, 1, 1, w - 1, h - 1, h / 2, fill=T.VERT_BOUTON if on else T.BORD, outline="")
        k = h - 6
        x = w - 3 - k if on else 3
        c.create_oval(x, 3, x + k, 3 + k, fill=T.BLANC, outline="")


class Segment(tk.Frame):
    """Choix exclusif sous forme de boutons côte à côte."""

    def __init__(self, parent, options, variable, bg=None):
        super().__init__(parent, bg=bg or parent.cget("bg"))
        self.var, self.labels = variable, {}
        for i, (valeur, texte) in enumerate(options):
            lab = tk.Label(self, text=texte, font=T.POL["gras"], cursor="hand2", bd=0)
            lab.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 2, 0))
            self.grid_columnconfigure(i, weight=1)
            lab.bind("<Button-1>", lambda e, v=valeur: self.var.set(v))
            self.labels[valeur] = lab
        self.var.trace_add("write", lambda *a: self._maj())
        T.REG.append(self)
        self.ajuster()

    def ajuster(self):
        for lab in self.labels.values():
            lab.configure(padx=T.px(10), pady=T.px(7))
        self._maj()

    def _maj(self):
        for valeur, lab in self.labels.items():
            sel = self.var.get() == valeur
            lab.configure(bg=T.ACCENT if sel else T.CARTE_HAUT, fg=T.FOND if sel else T.BLANC)


# ------------------------------------------------------------------ cartes et zone défilante
class Carte(tk.Frame):
    """Panneau à bordure fine. Les widgets s'ajoutent dans `.corps`."""

    def __init__(self, parent, titre=None, bg=None):
        bg = bg or T.CARTE
        super().__init__(parent, bg=bg, highlightbackground=T.BORD, highlightcolor=T.BORD, highlightthickness=1)
        if titre:
            etiquette(self, titre, "titre_carte", fg=T.ACCENT, bg=bg).pack(fill="x", padx=16, pady=(12, 2))
        self.corps = tk.Frame(self, bg=bg)
        self.corps.pack(fill="both", expand=True, padx=16, pady=(6, 14))


class FrameDefilant(tk.Frame):
    """Zone verticale défilante (molette de la souris). Les widgets s'ajoutent dans `.interieur`."""

    def __init__(self, parent, bg):
        super().__init__(parent, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.barre = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview,
                                   style="Fonce.Vertical.TScrollbar")
        self.canvas.configure(yscrollcommand=self.barre.set)
        self.interieur = tk.Frame(self.canvas, bg=bg)
        self.fenetre = self.canvas.create_window((0, 0), window=self.interieur, anchor="nw")
        self.barre.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.interieur.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self.fenetre, width=e.width))
        self.canvas.bind("<Enter>", lambda e: self.canvas.bind_all("<MouseWheel>", self._molette))
        self.canvas.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))

    def _molette(self, e):
        if self.interieur.winfo_reqheight() > self.canvas.winfo_height():
            self.canvas.yview_scroll(int(-e.delta / 120) or (-1 if e.delta > 0 else 1), "units")
