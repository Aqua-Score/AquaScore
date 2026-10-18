# Compteur de score Aqualin — Cahier des charges

## Objectif
Page web qui calcule automatiquement le score d'une partie d'Aqualin à partir d'une photo du plateau en fin de partie.

- Gratuite, sans publicité, sans microtransaction, sans compte.
- Traitement 100 % sur le téléphone, aucune donnée envoyée.
- Fonctionne hors ligne après le premier chargement.

## Règles utiles au calcul
- Plateau 6×6, 36 tuiles.
- 6 espèces : crabe, poisson, tortue, hippocampe, étoile de mer, méduse.
- 6 couleurs : jaune, rouge, bleu, rose, vert, violet.
- Chaque combinaison espèce + couleur est unique.
- Deux joueurs : « Espèces » regroupe les tuiles de même espèce, « Couleurs » celles de même couleur.
- **Banc** : groupe de tuiles adjacentes orthogonalement (pas en diagonale) partageant la caractéristique du joueur. Une tuile isolée ne rapporte rien.
- **Barème** : n×(n−1)/2 points pour un banc de n tuiles.

| Taille du banc | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|
| Points | 1 | 3 | 6 | 10 | 15 |

- Le plus de points gagne.

## Parcours utilisateur
1. Scan d'un QR code → ouverture de la page web.
2. Caméra avec grille 6×6 en surimpression, **guide de cadrage uniquement**.
3. Prise de photo, ou import d'une photo existante.
4. Analyse par le modèle, puis affichage du résultat, ex. :
   « Joueur Espèces : 34 pts — Gagnant / Joueur Couleurs : 27 pts — Perdant ». Égalité signalée le cas échéant.
5. Détail par banc en option.

Pas de correction ni de réentraînement par l'utilisateur : le modèle est figé et fourni avec l'app.

## Architecture technique
- **Type** : PWA statique (HTML/JS), installable, avec manifest + service worker pour le cache hors ligne.
- **Hébergement** : dépôt GitHub publié via GitHub Pages (HTTPS obligatoire pour la caméra).
- **QR code** : vers l'URL de la page ; domaine personnalisé redirigé conseillé pour une URL stable.
- **Caméra** : `getUserMedia`, caméra arrière.
- **Import photo** : `<input type="file" accept="image/*" capture="environment">` (repli sur iOS).
- **Traitement image** (OpenCV.js) :
  1. Détection automatique des 4 coins du plateau.
  2. Redressement de perspective (homographie). La distorsion d'objectif est négligeable sur l'objectif principal ; le vrai enjeu est la perspective.
  3. Découpe en 36 vignettes.
- **Reconnaissance** : classifieur 36 classes (une par tuile), dans le navigateur via TensorFlow.js ou ONNX Runtime Web ; modèle quantifié (~2 à 5 Mo).
- **Fiabilisation** : chaque tuile étant unique, affectation globale (algorithme hongrois) sur les scores de confiance pour corriger les erreurs isolées.
- **Score** : flood-fill des groupes connexes, une passe par espèce et une par couleur, puis barème.

## Entraînement du modèle (développeur uniquement)
- **Données** : photos du plateau complet sous ambiances variées.
  - Lumière du jour, ampoule chaude, néon, pénombre, flash, ombres, reflets.
  - Plusieurs téléphones, angles, distances ; tuiles tournées.
- **Étiquetage automatique** :
  - Disposition de référence connue (ex. ligne = espèce, colonne = couleur).
  - Le pipeline redresse et découpe : chaque vignette est étiquetée par sa position.
  - 1 photo = 36 exemples ; ~40 photos pour démarrer (~1 400 vignettes).
  - Quelques dispositions aléatoires pour éviter l'apprentissage des positions.
- **Augmentation** : luminosité, contraste, flou, bruit, rotations de 90°, petits décalages. Dérive de teinte modérée (risque de confusion rose/violet).
- **Modèle** : apprentissage par transfert sur MobileNetV3 ou EfficientNet-Lite.
- **Outils** : Teachable Machine (prototype rapide) ou Python + Keras/PyTorch (GPU local ou Colab), export TF.js ou ONNX.
- **Validation** : mettre de côté des ambiances entières (ex. toutes les photos sous néon), pas des vignettes au hasard.
- **Publication** : modèle versionné dans le dépôt GitHub, mis à jour par simple push.

## Points de vigilance
- **OpenCV.js** : 8 à 10 Mo, premier chargement lent puis en cache. Une compilation limitée aux modules utiles réduit la taille.
- **iOS / Safari** : cache PWA parfois vidé, caméra capricieuse en mode installé ; l'import photo sert de repli.
- **Propriété intellectuelle** : Aqualin est une marque de Kosmos, éditée en France par Iello.
  - Ni logo ni illustrations officielles dans l'app ou le dépôt public ; publier seulement les poids du modèle, pas les photos d'entraînement.
  - Nom descriptif + mention « app non officielle » ; idéalement, demander leur accord.
- **Évolution possible** : emballage en app Android (TWA via PWABuilder ou Bubblewrap) pour le Play Store.
