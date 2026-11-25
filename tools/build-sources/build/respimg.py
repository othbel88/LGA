"""
Génération d'images responsives (bandeaux de page et vignettes de la grille des chambres)
pour corriger le LCP mobile (cf. COMPARATIF-AVANT-APRES.md / NOTE-POUR-AUDITEUR.md — le
préchargement seul (phase 5/N puis correctif du 25/11) ne suffisait pas : le bandeau fait
338 Ko et partage une bande passante mobile simulée (1,6 Mbit/s) avec les 14 vignettes de
la grille qui, elles, se chargent à 900 px de large alors qu'elles s'affichent à ~170-360 px
selon le format. Mesuré par trace réseau réelle (CDP), pas seulement par le score Lighthouse.

Toutes les images sont dérivées des fichiers sources sans jamais modifier ni remplacer les
originaux (pleine résolution conservée en fiche/lightbox, cf. consigne explicite). Les
variantes sont mises en cache sur le disque (régénérées seulement si absentes ou si la
source a changé), pour ne pas ralentir les builds répétés.
"""
import os
import hashlib
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
BAND_CACHE_DIR = os.path.join(HERE, '_bandcache')
os.makedirs(BAND_CACHE_DIR, exist_ok=True)


def _mtime_tag(disk_path):
    try:
        return str(int(os.path.getmtime(disk_path)))
    except OSError:
        return '0'


def make_variant(disk_path, width, quality, out_path, fmt='jpeg'):
    """Écrit (si absent ou source plus récente) une variante redimensionnée/recompressée de
    disk_path à out_path. Retourne (out_path, largeur, hauteur). La variante est régénérée
    seulement si out_path n'existe pas ou est plus ancienne que la source (cache persistant
    sur disque, basé sur les chemins finaux eux-mêmes — pas de dossier séparé)."""
    if os.path.isfile(out_path) and os.path.getmtime(out_path) >= os.path.getmtime(disk_path):
        with Image.open(out_path) as im:
            return out_path, im.width, im.height
    with Image.open(disk_path) as im:
        im = im.convert('RGB')
        if im.width > width:
            new_h = round(im.height * width / im.width)
            im = im.resize((width, new_h), Image.LANCZOS)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        if fmt == 'webp':
            im.save(out_path, 'WEBP', quality=quality, method=6)
        else:
            im.save(out_path, 'JPEG', quality=quality, optimize=True, progressive=True)
        return out_path, im.width, im.height


def band_variants(disk_path):
    """Pour un bandeau de page (background-image, cover) : variante mobile (≤960px, q68)
    et variante desktop (≤1920px, q74), mises en cache sous build/_bandcache/ (persistant
    entre builds, régénéré seulement si la source a changé). Retourne un dict de chemins."""
    base = os.path.splitext(os.path.basename(disk_path))[0]
    tag = _mtime_tag(disk_path)
    mobile_out = os.path.join(BAND_CACHE_DIR, f'{base}-{tag}-mobile.jpg')
    desktop_out = os.path.join(BAND_CACHE_DIR, f'{base}-{tag}-desktop.jpg')
    mobile, mw, mh = make_variant(disk_path, 960, 68, mobile_out, 'jpeg')
    desktop, dw, dh = make_variant(disk_path, 1920, 74, desktop_out, 'jpeg')
    return {'mobile': mobile, 'desktop': desktop}


def card_variants(disk_path, out_dir, base_name):
    """Pour une vignette de la grille des chambres (object-fit:cover, 4:5) : deux largeurs
    (420px pour mobile/2 colonnes, 720px pour desktop/3 colonnes) en JPEG et WebP, écrites
    directement dans out_dir (le dossier build/rooms/<slug>/ de la chambre), aux côtés de
    1-card.jpg — copiées vers la sortie du site par le même mécanisme que ce dernier."""
    out = {}
    for w in (420, 720):
        jpg_out = os.path.join(out_dir, f'{base_name}-{w}.jpg')
        webp_out = os.path.join(out_dir, f'{base_name}-{w}.webp')
        jpg, jw, jh = make_variant(disk_path, w, 72, jpg_out, 'jpeg')
        webp, ww, wh = make_variant(disk_path, w, 70, webp_out, 'webp')
        out[w] = {'jpg': jpg, 'webp': webp, 'w': jw, 'h': jh}
    return out
