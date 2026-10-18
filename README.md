# AquaScore — compteur de bancs (compatible Aqualin, non officiel)

Application web qui photographie un plateau 6×6 en fin de partie et calcule le score des bancs.

Application en ligne : https://aqua-score.github.io/AquaScore/

Projet non officiel, sans lien avec l'éditeur du jeu. Cahier des charges : [aqualin-compteur-score.md](aqualin-compteur-score.md).

## Structure

- `app/` : la PWA publiée sur GitHub Pages
  - `index.html` : la page unique : bouton Share (QR code), cadre « Prendre une photo » qui ouvre la caméra, contour du plateau et grille en surimpression, bouton « Calculer le score », score des deux joueurs, récapitulatif des bancs et correction case par case
  - `js/score.js` : moteur de score (flood-fill orthogonal, barème n(n−1)/2)
  - `js/modele.js` : reconnaissance des 36 tuiles dans le navigateur (ONNX Runtime Web)
  - `js/hongrois.js` : affectation hongroise (chaque tuile est unique)
  - `js/homographie.js` : homographie 4 points en JS pur (pour une future détection automatique du plateau)
  - `model/` : modèle de reconnaissance des tuiles (ONNX) produit par `training/entrainer.py`
  - `img/` : fond de l'accueil (photo de partie) et QR code de partage
- `tests/` : tests unitaires JS (`npm test`, Node ≥ 22)
- `training/` : pipeline Python (développeur uniquement)
  - `etiquettes.json` : étiquettes des photos de `img/` (une grille par partie), coins manuels si la détection échoue
  - `plateau.py` : détection du plateau, redressement, découpe des vignettes
  - `extraire.py` : photos → vignettes étiquetées + images de contrôle (`training/controle/`)
  - `entrainer.py` : validation croisée par partie, modèle final, export ONNX fp32 et int8
- `img/` : photos d'entraînement, **jamais publiées** (ignorées par git)

## Entraîner le modèle

```bash
.venv/Scripts/python training/extraire.py
.venv/Scripts/python training/entrainer.py
```

Pour ajouter des photos : les mettre dans `img/`, ajouter leur grille dans `training/etiquettes.json`
relancer les deux commandes, et vérifier `training/controle/`.

## En local

```bash
npm test
npm run serve   # http://localhost:8080
```

## Publication

Le workflow `.github/workflows/pages.yml` lance les tests puis publie `app/`.
Réglage à faire une fois : Settings → Pages → Source : « GitHub Actions ».
