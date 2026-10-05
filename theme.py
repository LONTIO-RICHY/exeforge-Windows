"""Couleurs, polices et utilitaires de style de ExeForge."""

import tkinter.font as tkfont

# ---------------------------------------------------------------- couleurs
FOND = "#070b1f"
PANEL = "#0b1130"
CARTE = "#111a3b"
CARTE_HAUT = "#1b2860"
BORD = "#2b3a78"
ACCENT = "#22d3ee"
ACCENT2 = "#a78bfa"
VERT = "#34d399"
VERT_BOUTON = "#10b981"
ROUGE = "#fb7185"
ROUGE_BOUTON = "#e11d48"
JAUNE = "#fbbf24"
GRIS = "#94a3b8"
BLANC = "#f8fafc"
TEXTE = "#dbe4f3"


def hex_rgb(h):
    return int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)


def melanger(a, b, t):
    """Couleur entre a (t = 0) et b (t = 1)."""
    t = max(0.0, min(1.0, t))
    ra, rb = hex_rgb(a), hex_rgb(b)
    return "#%02x%02x%02x" % tuple(int(ra[i] + (rb[i] - ra[i]) * t) for i in range(3))


# ---------------------------------------------------------------- polices
BASES = {
    "titre_app": (22, "bold"), "titre_page": (19, "bold"), "titre_carte": (12, "bold"),
    "normal": (10, "normal"), "gras": (10, "bold"), "petit": (9, "normal"),
    "petit_gras": (9, "bold"), "grand": (13, "bold"), "mono": (9, "normal"),
    "pct": (11, "bold"), "nav": (11, "bold"),
}
POL = {}
ECHELLE = 1.0       # grandit avec la fenêtre (plein écran = tout est plus grand)
DPI = 1.0           # facteur de l'écran (125 %, 150 %...)
REG = []            # widgets à recalculer quand l'échelle change


def creer_polices(root):
    global DPI
    try:
        DPI = max(1.0, root.winfo_fpixels("1i") / 96.0)
    except Exception:
        DPI = 1.0
    for nom, (taille, poids) in BASES.items():
        famille = "Consolas" if nom == "mono" else "Segoe UI"
        POL[nom] = tkfont.Font(root=root, family=famille, size=taille, weight=poids)


def appliquer_echelle(s):
    global ECHELLE
    ECHELLE = s
    for nom, (taille, _poids) in BASES.items():
        POL[nom].configure(size=max(7, round(taille * s)))


def px(n):
    """Taille en pixels adaptée à l'écran et à la taille de la fenêtre."""
    return max(1, int(round(n * DPI * ECHELLE)))
