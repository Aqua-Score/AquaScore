"""Détecte le plateau sur chaque photo étiquetée et produit les vignettes d'entraînement.

    python training/extraire.py [--img img] [--sortie training/vignettes]

Écrit aussi training/controle/<photo>.jpg (coins détectés + plateau redressé) pour vérifier à l'œil.
Des coins saisis à la main dans etiquettes.json (clé "coins") remplacent la détection.
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from plateau import detecter_coins, redresser, vignettes, grille_texte, lire

ICI = Path(__file__).parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--img', default=str(ICI.parent / 'img'))
    ap.add_argument('--sortie', default=str(ICI / 'vignettes'))
    a = ap.parse_args()

    etiq = json.loads((ICI / 'etiquettes.json').read_text(encoding='utf-8'))
    sortie, controle = Path(a.sortie), ICI / 'controle'
    sortie.mkdir(parents=True, exist_ok=True)
    controle.mkdir(exist_ok=True)
    index = []
    for photo, partie in etiq['photos'].items():
        img = lire(Path(a.img) / photo)
        if img is None:
            print(f'{photo} : introuvable')
            continue
        coins = etiq.get("coins", {}).get(photo)
        manuel = coins is not None
        coins = np.array(coins, np.float32) if coins else detecter_coins(img)
        if coins is None:
            print(f'{photo} : plateau NON détecté')
            continue
        plateau = redresser(img, coins)
        grille = grille_texte(etiq['parties'][partie])
        vig = vignettes(plateau)
        nom = Path(photo).stem
        for r in range(6):
            for c in range(6):
                f = f'{nom}_{r}{c}.png'
                cv2.imwrite(str(sortie / f), vig[r][c])
                esp, coul = grille[r][c]
                index.append({'fichier': f, 'photo': photo, 'partie': partie, 'espece': esp, 'couleur': coul})

        # Image de contrôle : photo avec le quadrilatère + plateau redressé quadrillé.
        vue = img.copy()
        cv2.polylines(vue, [coins.astype(np.int32)], True, (0, 255, 255), max(3, img.shape[1] // 300))
        vue = cv2.resize(vue, (int(600 * vue.shape[1] / vue.shape[0]), 600))
        p = plateau.copy()
        for i in range(1, 6):
            cv2.line(p, (i * 100, 0), (i * 100, 600), (0, 255, 255), 1)
            cv2.line(p, (0, i * 100), (600, i * 100), (0, 255, 255), 1)
        cv2.imwrite(str(controle / f'{nom}.jpg'), np.hstack([vue, p]))
        print(f"{photo} : OK ({'manuel' if manuel else 'auto'}), coins {coins.round().astype(int).tolist()}")

    (sortie / 'index.json').write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'{len(index)} vignettes dans {sortie}')


if __name__ == '__main__':
    main()
