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

---

# Réalisation — état au 19 octobre 2026

## En bref
- **Application en ligne : https://aqua-score.github.io/AquaScore/**
- **Dépôt public** : https://github.com/Aqua-Score/AquaScore (organisation GitHub « Aqua-Score », dépôt « AquaScore »).
- **QR code statique** : `AquaScore-qr.png` sur le bureau, et dans l'app via le bouton « Share ».
- Le site fonctionne de bout en bout : photo → reconnaissance des 36 tuiles sur le téléphone → score des deux joueurs → récapitulatif → correction éventuelle.

## Parcours utilisateur réalisé
1. Scan du QR code → page **AquaScore** (mention « Compatible Aqualin — application non officielle »).
2. Un cadre « **Prendre une photo** » (icône appareil photo sur une photo de tuiles en gros plan, légèrement désaturée). Toucher le cadre ouvre la caméra arrière.
3. Surimpression de cadrage : **contour du plateau** (cadre clair) + **grille 6×6** des tuiles.
4. Bouton **« Calculer le score »** (pleine largeur) : l'image est figée, analysée en ~0,2 s, puis s'affichent :
   - le **score final** des deux joueurs (Espèces / Couleurs) avec Gagnant, Perdant ou Égalité ;
   - le **plateau reconnu** case par case (vignette photo + espèce + pastille de couleur) ; les cases incertaines sont en orange, avec un avertissement si elles sont nombreuses ;
   - le **récapitulatif des bancs** de chaque joueur (ex. « Tortue : 5 tuiles → 10 pts »).
5. **Correction case par case** : toucher une case ouvre un tableau des 36 tuiles. Chaque tuile étant unique, si la tuile choisie est déjà ailleurs, les deux cases sont échangées ; elles passent en vert et le score se recalcule.
6. Toucher la photo figée permet d'en reprendre une autre.
7. Bouton **Share** à droite du titre : QR code + lien (et partage natif du lien sur téléphone).

## Écarts par rapport au cahier des charges
| Cahier des charges | Réalisé | Raison |
|---|---|---|
| Pas de correction par l'utilisateur | Correction case par case possible | Demandé en cours de projet ; filet de sécurité utile tant que le modèle n'a vu que peu de parties |
| Détection automatique des 4 coins (OpenCV.js) | Cadrage par le guide à l'écran (contour + grille) | Plus simple et fiable pour l'instant ; aucune dépendance de 8–10 Mo |
| Classifieur 36 classes | Un modèle à **deux têtes** (6 espèces + 6 couleurs) | 6 fois plus d'exemples par classe ; score d'une tuile = P(espèce) × P(couleur) |
| Modèle quantifié ~2–5 Mo | Modèle **fp32 de 4,3 Mo** | La version int8 (1,4 Mo) perdait trop en précision |
| Import d'une photo existante | Non fait | Caméra en direct uniquement, à la demande |
| PWA hors ligne (manifest + service worker) | Non fait | Le premier chargement nécessite le réseau (modèle + ONNX Runtime depuis un CDN) |
| Domaine personnalisé | Organisation GitHub « Aqua-Score » | Gratuit, le lien ne contient plus le nom du compte personnel |

## Architecture technique réalisée
- **PWA statique** (HTML/JS, sans framework) dans `app/`, publiée par **GitHub Pages** via un workflow GitHub Actions (`.github/workflows/pages.yml`) : à chaque push sur `main`, les tests tournent puis le site est publié.
- **Caméra** : `getUserMedia`, caméra arrière. La zone de la grille est découpée directement dans l'image vidéo (en tenant compte du recadrage à l'écran), puis en 36 vignettes avec 12 % de marge (les tuiles débordent souvent de leur case).
- **Reconnaissance** (`app/js/modele.js`) : **ONNX Runtime Web** 1.20.1 (WebAssembly), modèle `app/model/tuiles_fp32.onnx`, entrée 96×96 px.
- **Fiabilisation** (`app/js/hongrois.js`) : **algorithme hongrois** en JS sur la matrice 36×36 des coûts −log P(espèce) − log P(couleur) : chaque combinaison est attribuée une seule fois.
- **Score** (`app/js/score.js`) : flood-fill orthogonal, une passe par espèce et une par couleur, barème n(n−1)/2.
- `app/js/homographie.js` : homographie 4 points et redressement en JS pur (sans OpenCV), conservé pour une future détection automatique du plateau.

## Entraînement du modèle
- **Données** : 7 photos de fin de partie dans `img/` (non publiées), étiquetées à la main dans `training/etiquettes.json` → **252 vignettes**.
  - En réalité **3 parties distinctes** : deux photos sont des rotations d'autres parties (180° et 90°), ce qui a servi de vérification croisée des étiquettes.
- **Détection du plateau** (`training/plateau.py`, prototype phase 2) : contour bleuté du plateau, puis profils du masque « tuiles » pour trouver la zone des 36 tuiles. Réussite **4 photos sur 7** (échecs : plateau coupé par le bord de la photo, ombre de main, forte perspective) ; coins saisis à la main pour les 3 autres.
- **Modèle** : MobileNetV3-Small pré-entraîné (ImageNet), deux têtes, augmentations (rotations 90°, recadrages, luminosité/contraste, légère dérive de teinte, flou), 60 époques sur CPU.
- **Validation** : une partie entière mise de côté à chaque fois (jamais de photo d'une partie vue à l'entraînement) :

| Mesure (parties jamais vues) | Résultat |
|---|---|
| Tuiles correctes, modèle seul | 95,2 % |
| Tuiles correctes après affectation hongroise | **97,2 %** (245 / 252) |
| Score exact de la photo | 5 photos sur 7 |

- Les erreurs restantes étaient des confusions de **forme** (crabe / étoile / méduse) sur 2 photos ; aucune confusion de couleur, y compris rose / violet.
- Ces chiffres restent indicatifs avec seulement 3 parties ; une quinzaine de parties les rendrait fiables.

## Organisation du projet (dossier `Desktop\Aqualin`)
```
aqualin-compteur-score.md   ce document (cahier des charges + réalisation)
README.md                   présentation du dépôt
app/                        site publié
  index.html                page unique
  js/                       score.js, modele.js, hongrois.js, homographie.js
  model/                    tuiles_fp32.onnx + modele.json (paramètres d'entrée)
  img/                      fond d'accueil + QR code
tests/                      tests unitaires JS (15 tests)
training/                   pipeline Python : plateau.py, extraire.py, entrainer.py, etiquettes.json
img/                        photos d'entraînement (privées, jamais publiées)
.venv/                      environnement Python (PyTorch CPU, OpenCV, ONNX)
```

## Commandes utiles
```bash
npm test                                   # tests du moteur de score, de l'affectation et de l'homographie
.venv/Scripts/python training/extraire.py  # photos de img/ -> vignettes étiquetées + images de contrôle
.venv/Scripts/python training/entrainer.py # validation par partie, modèle final, export ONNX dans app/model
git push                                   # publie le site (tests puis déploiement automatique)
```
Pour enrichir le modèle : ajouter les photos dans `img/`, leurs grilles dans `training/etiquettes.json`, vérifier `training/controle/`, relancer les deux scripts, puis pousser.

## Points de vigilance (mis à jour)
- **Cadrage** : l'app suppose que les tuiles sont alignées sur la grille ; un plateau mal cadré donne des cases orange ou des erreurs.
- **Propriété intellectuelle** : le fond d'accueil et le QR code sont publiés dans le dépôt ; le fond montre des tuiles du jeu, ce qui s'écarte de la règle « ni illustrations officielles » ci-dessus. Les photos d'entraînement restent privées.
- **Ancienne adresse** : `…github.io/compteur-de-bancs` ne fonctionne plus depuis le transfert ; les QR codes imprimés avant doivent être remplacés.
- **Confidentialité** : les commits utilisent l'adresse e-mail « noreply » de GitHub.

## Prochaines étapes possibles
1. Photographier 10 à 15 parties de plus (lumières variées, disposition de référence) et réentraîner.
2. Mode hors ligne : manifest + service worker, et ONNX Runtime hébergé dans le dépôt plutôt que sur un CDN.
3. Détection automatique du plateau dans le navigateur, pour tolérer un cadrage approximatif.
4. Import d'une photo existante (repli iOS).
5. Quantification int8 avec plus de données de calibration, pour alléger le modèle.
6. Éventuellement : domaine personnalisé, app Android (TWA), demande d'accord à l'éditeur.
