// Moteur de score — compteur de bancs (compatible Aqualin, non officiel).
// Une grille est un tableau 6x6 de tuiles { espece, couleur }.

export const ESPECES = ['poisson', 'hippocampe', 'etoile', 'tortue', 'crabe', 'meduse'];
export const COULEURS = ['rouge', 'jaune', 'vert', 'bleu', 'violet', 'rose'];
export const TAILLE = 6;

// Barème : un banc de n tuiles rapporte n(n-1)/2 (1→0, 2→1, 3→3, 4→6, 5→10, 6→15).
export const points = (n) => (n * (n - 1)) / 2;

const VOISINS = [[1, 0], [-1, 0], [0, 1], [0, -1]];

// Flood-fill orthogonal sur un attribut ('espece' ou 'couleur').
function bancs(grille, attribut) {
  const vu = grille.map((ligne) => ligne.map(() => false));
  const res = [];
  for (let r = 0; r < TAILLE; r++) {
    for (let c = 0; c < TAILLE; c++) {
      if (vu[r][c]) continue;
      const valeur = grille[r][c][attribut];
      const cases = [];
      const pile = [[r, c]];
      vu[r][c] = true;
      while (pile.length) {
        const [y, x] = pile.pop();
        cases.push([y, x]);
        for (const [dy, dx] of VOISINS) {
          const ny = y + dy, nx = x + dx;
          if (ny < 0 || nx < 0 || ny >= TAILLE || nx >= TAILLE || vu[ny][nx]) continue;
          if (grille[ny][nx][attribut] !== valeur) continue;
          vu[ny][nx] = true;
          pile.push([ny, nx]);
        }
      }
      cases.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
      res.push({ type: attribut, valeur, taille: cases.length, points: points(cases.length), cases });
    }
  }
  return res;
}

// Vérifie qu'une grille est un plateau de fin de partie valide :
// 6x6, valeurs connues, et chacune des 36 combinaisons présente une seule fois.
export function valider(grille) {
  const erreurs = [];
  if (!Array.isArray(grille) || grille.length !== TAILLE || grille.some((l) => !Array.isArray(l) || l.length !== TAILLE)) {
    return ['la grille doit faire 6x6'];
  }
  const vues = new Set();
  grille.forEach((ligne, r) => ligne.forEach((t, c) => {
    if (!t || !ESPECES.includes(t.espece)) erreurs.push(`(${r},${c}) espèce inconnue : ${t && t.espece}`);
    if (!t || !COULEURS.includes(t.couleur)) erreurs.push(`(${r},${c}) couleur inconnue : ${t && t.couleur}`);
    const cle = t && `${t.espece}/${t.couleur}`;
    if (vues.has(cle)) erreurs.push(`(${r},${c}) doublon : ${cle}`);
    vues.add(cle);
  }));
  return erreurs;
}

// score(grille) → { especes, couleurs, bancs[], resultat }
// resultat vaut 'especes', 'couleurs' ou 'egalite' (le camp qui marque le plus).
export function score(grille) {
  const tous = [...bancs(grille, 'espece'), ...bancs(grille, 'couleur')];
  const total = (type) => tous.filter((b) => b.type === type).reduce((s, b) => s + b.points, 0);
  const especes = total('espece');
  const couleurs = total('couleur');
  const resultat = especes > couleurs ? 'especes' : couleurs > especes ? 'couleurs' : 'egalite';
  return { especes, couleurs, bancs: tous.filter((b) => b.taille > 1), resultat };
}

// Raccourci pour écrire une grille en texte : "poisson/rouge hippocampe/violet ...".
export function grilleDepuisTexte(texte) {
  return texte.trim().split('\n').map((ligne) =>
    ligne.trim().split(/\s+/).map((tok) => {
      const [espece, couleur] = tok.split('/');
      return { espece, couleur };
    }));
}
