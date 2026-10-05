"""Conversion de n'importe quelle image en icône Windows (.ico) aux bonnes résolutions."""

from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageOps

RESAMPLE = Image.Resampling.LANCZOS
TAILLES = (16, 24, 32, 48, 64, 96, 128, 256)       # résolutions standard d'un .ico Windows
MODES = {"ajuster": "Ajuster (image entière)", "remplir": "Remplir (recadrer)", "etirer": "Étirer"}
ARRONDIS = {"aucun": 0.0, "leger": 0.14, "fort": 0.30}


def ouvrir_image(chemin):
    """Ouvre une image (png, jpg, bmp, gif, webp, tiff, ico...) en RGBA."""
    chemin = Path(chemin)
    if chemin.suffix.lower() in (".svg", ".svgz"):
        raise ValueError("Le format SVG n'est pas pris en charge : exporte-le d'abord en PNG.")
    try:
        img = Image.open(chemin)
        if img.format == "ICO":                      # on prend la plus grande taille de l'icône
            try:
                img.size = max(img.ico.sizes())
            except Exception:
                pass
        img.load()
    except Exception as e:
        raise ValueError(f"Image illisible : {e}") from e
    try:
        img = ImageOps.exif_transpose(img) or img    # respecte l'orientation des photos
    except Exception:
        pass
    return img.convert("RGBA")


def adapter_carre(img, mode="ajuster", arrondi=0.0, taille=256):
    """Image quelconque -> carré taille x taille (transparent autour si besoin), coins éventuellement arrondis."""
    w, h = img.size
    if mode == "remplir":
        sortie = ImageOps.fit(img, (taille, taille), RESAMPLE, centering=(0.5, 0.5))
    elif mode == "etirer":
        sortie = img.resize((taille, taille), RESAMPLE)
    else:
        ratio = min(taille / w, taille / h)           # agrandit aussi les petites images
        nw, nh = max(1, round(w * ratio)), max(1, round(h * ratio))
        reduite = img.resize((nw, nh), RESAMPLE)
        sortie = Image.new("RGBA", (taille, taille), (0, 0, 0, 0))
        sortie.paste(reduite, ((taille - nw) // 2, (taille - nh) // 2), reduite)
    if arrondi > 0:
        g = taille * 4                                # sur-échantillonné : bords lissés
        masque = Image.new("L", (g, g), 0)
        ImageDraw.Draw(masque).rounded_rectangle((0, 0, g - 1, g - 1), radius=int(g * arrondi), fill=255)
        masque = masque.resize((taille, taille), RESAMPLE)
        sortie.putalpha(ImageChops.multiply(sortie.getchannel("A"), masque))
    return sortie


def convertir_en_ico(source, sortie, mode="ajuster", arrondi=0.0, tailles=TAILLES):
    """Écrit le .ico ; retourne la liste des tailles réellement enregistrées."""
    base = adapter_carre(ouvrir_image(source), mode, arrondi, 256)
    sortie = Path(sortie)
    sortie.parent.mkdir(parents=True, exist_ok=True)
    base.save(sortie, format="ICO", sizes=[(s, s) for s in tailles])
    with Image.open(sortie) as verif:
        return sorted(s[0] for s in verif.ico.sizes())


def damier(taille, case=8):
    img = Image.new("RGBA", (taille, taille), (232, 235, 242, 255))
    d = ImageDraw.Draw(img)
    for y in range(0, taille, case):
        for x in range(0, taille, case):
            if (x // case + y // case) % 2:
                d.rectangle((x, y, x + case - 1, y + case - 1), fill=(190, 196, 212, 255))
    return img


def sur_damier(img, taille):
    """Aperçu : l'image redimensionnée posée sur un damier (montre la transparence)."""
    return Image.alpha_composite(damier(taille, max(4, taille // 12)), img.resize((taille, taille), RESAMPLE))
