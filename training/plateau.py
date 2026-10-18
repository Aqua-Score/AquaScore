"""Détection du plateau, redressement et découpe des 36 vignettes (prototype phase 2)."""
import cv2
import numpy as np

ESPECES = ['poisson', 'hippocampe', 'etoile', 'tortue', 'crabe', 'meduse']
COULEURS = ['rouge', 'jaune', 'vert', 'bleu', 'violet', 'rose']

COTE = 600          # côté du plateau redressé (100 px par case)
MARGE = 0.12        # marge autour de chaque case, les tuiles débordent souvent
VIGNETTE = 112      # taille des vignettes envoyées au modèle


def lire(chemin):
    # cv2.imread ne gère pas les chemins non ASCII sous Windows.
    return cv2.imdecode(np.fromfile(str(chemin), dtype=np.uint8), cv2.IMREAD_COLOR)


def masque_tuiles(img):
    """Pixels « bleu marine » des tuiles (le fond du plateau est bleu clair, la table brune)."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    m = ((h >= 95) & (h <= 130) & (s >= 70) & (v >= 25) & (v <= 150)).astype(np.uint8) * 255
    k = max(3, img.shape[1] // 200)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((k, k), np.uint8))   # bouche les motifs clairs
    return cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((k, k), np.uint8))


def ordonner(pts):
    pts = np.asarray(pts, dtype=np.float32)
    s, d = pts.sum(1), pts[:, 0] - pts[:, 1]
    return np.array([pts[s.argmin()], pts[d.argmax()], pts[s.argmax()], pts[d.argmin()]], np.float32)


def coins_plateau(petit):
    """Contour du plateau entier : plus grande zone bleutée (tuiles marine + fond bleu clair)."""
    hsv = cv2.cvtColor(petit, cv2.COLOR_BGR2HSV)
    h, s, _ = cv2.split(hsv)
    m = ((h >= 88) & (h <= 135) & (s >= 20)).astype(np.uint8) * 255
    k = max(5, petit.shape[1] // 60)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((k, k), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((k, k), np.uint8))
    contours, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    c = max(contours, key=cv2.contourArea)
    if cv2.contourArea(c) < 0.1 * m.size:
        return None
    hull = cv2.convexHull(c)
    peri = cv2.arcLength(hull, True)
    for eps in np.linspace(0.01, 0.1, 19):
        quad = cv2.approxPolyDP(hull, eps * peri, True)
        if len(quad) == 4:
            return ordonner(quad.reshape(-1, 2))
    return ordonner(cv2.boxPoints(cv2.minAreaRect(hull)))


def bornes(profil, seuil):
    """Premier et dernier indice où le profil dépasse le seuil (ignore les pics isolés)."""
    idx = np.flatnonzero(np.convolve(profil > seuil, np.ones(5) / 5, 'same') > 0.6)
    return (idx[0], idx[-1] + 1) if len(idx) else None


def detecter_coins(img):
    """Renvoie les 4 coins (HG, HD, BD, BG) de la zone des tuiles dans `img`, ou None.

    1. On trouve le plateau entier (grand quadrilatère bleuté, contrasté avec la table).
    2. On le redresse, puis les profils ligne/colonne du masque « tuile marine » donnent
       les limites de la zone des 36 tuiles (les décors du bord ne pèsent presque pas).
    """
    echelle = 1000 / max(img.shape[:2])
    petit = cv2.resize(img, None, fx=echelle, fy=echelle, interpolation=cv2.INTER_AREA)
    quad = coins_plateau(petit)
    if quad is None:
        return None
    N = 600
    dst = np.array([[0, 0], [N, 0], [N, N], [0, N]], np.float32)
    H = cv2.getPerspectiveTransform(quad, dst)
    m = masque_tuiles(cv2.warpPerspective(petit, H, (N, N))) > 0
    bx, by = bornes(m.mean(0), 0.3), bornes(m.mean(1), 0.3)
    if bx is None or by is None or (bx[1] - bx[0]) < N / 2 or (by[1] - by[0]) < N / 2:
        return None
    zone = np.array([[bx[0], by[0]], [bx[1], by[0]], [bx[1], by[1]], [bx[0], by[1]]], np.float32)
    retour = cv2.perspectiveTransform(zone[None], np.linalg.inv(H))[0]
    return retour / echelle


def redresser(img, coins, cote=COTE):
    dst = np.array([[0, 0], [cote, 0], [cote, cote], [0, cote]], np.float32)
    H = cv2.getPerspectiveTransform(ordonner(coins), dst)
    return cv2.warpPerspective(img, H, (cote, cote), flags=cv2.INTER_AREA)


def vignettes(plateau, marge=MARGE, taille=VIGNETTE):
    """36 vignettes [ligne][colonne], chacune avec une marge autour de sa case."""
    case = plateau.shape[0] / 6
    m = int(case * marge)
    bord = cv2.copyMakeBorder(plateau, m, m, m, m, cv2.BORDER_REPLICATE)
    res = []
    for r in range(6):
        ligne = []
        for c in range(6):
            y0, x0 = int(r * case), int(c * case)
            v = bord[y0:y0 + int(case) + 2 * m, x0:x0 + int(case) + 2 * m]
            ligne.append(cv2.resize(v, (taille, taille), interpolation=cv2.INTER_AREA))
        res.append(ligne)
    return res


def grille_texte(lignes):
    return [[tuple(t.split('/')) for t in l.split()] for l in lignes]
