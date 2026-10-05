"""Informations sur le créateur de ExeForge (affichées dans l'application, les journaux et la documentation)."""

AUTEUR = {
    "nom": "LONTIO KESSEL || LONTIO RICHY",
    "whatsapp": "+237 650 196 251",
    "whatsapp_lien": "https://wa.me/237650196251",
    "email": "lontiokessel@gmail.com",
    "github": "https://github.com/LONTIo-RICHY",
}


def ligne_contact():
    a = AUTEUR
    return f"Contact : {a['nom']} | WhatsApp {a['whatsapp']} | {a['email']} | {a['github']}"
