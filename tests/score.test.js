import { test } from 'node:test';
import assert from 'node:assert/strict';
import { score, valider, points, grilleDepuisTexte, ESPECES, COULEURS } from '../app/js/score.js';

// Plateau de la photo training/photos/OIP-2178420076.jpg, transcrit à la main
// (scores attendus calculés à la main eux aussi).
const PHOTO_OIP = grilleDepuisTexte(`
  poisson/rouge  hippocampe/violet etoile/violet  poisson/jaune  poisson/rose   meduse/rouge
  tortue/rouge   poisson/violet    tortue/violet  tortue/jaune   poisson/bleu   crabe/jaune
  crabe/rouge    hippocampe/rouge  etoile/rose    tortue/bleu    tortue/rose    tortue/vert
  crabe/violet   crabe/vert        etoile/bleu    etoile/rouge   poisson/vert   etoile/vert
  crabe/bleu     hippocampe/rose   hippocampe/bleu crabe/rose    meduse/violet  meduse/vert
  etoile/jaune   hippocampe/jaune  hippocampe/vert meduse/jaune  meduse/rose    meduse/bleu
`);

// Disposition de référence : ligne = espèce, colonne = couleur.
const REFERENCE = ESPECES.map((espece) => COULEURS.map((couleur) => ({ espece, couleur })));

// Réordonne une grille par un mélange déterministe (pas de Math.random dans les tests).
function melange(seed) {
  const tuiles = REFERENCE.flat();
  let s = seed;
  for (let i = tuiles.length - 1; i > 0; i--) {
    s = (s * 1103515245 + 12345) % 2 ** 31;
    const j = s % (i + 1);
    [tuiles[i], tuiles[j]] = [tuiles[j], tuiles[i]];
  }
  return Array.from({ length: 6 }, (_, r) => tuiles.slice(r * 6, r * 6 + 6));
}

const transpose = (g) => g[0].map((_, c) => g.map((l) => l[c]));
const rotation90 = (g) => transpose(g).map((l) => l.reverse());

test('barème n(n-1)/2', () => {
  assert.deepEqual([1, 2, 3, 4, 5, 6].map(points), [0, 1, 3, 6, 10, 15]);
});

test('photo OIP : la transcription est un plateau valide', () => {
  assert.deepEqual(valider(PHOTO_OIP), []);
});

test('photo OIP : 38 (espèces) contre 21 (couleurs)', () => {
  const s = score(PHOTO_OIP);
  assert.equal(s.especes, 38);
  assert.equal(s.couleurs, 21);
  assert.equal(s.resultat, 'especes');
});

test('photo OIP : détail des bancs', () => {
  const s = score(PHOTO_OIP);
  const tailles = (type, valeur) => s.bancs.filter((b) => b.type === type && b.valeur === valeur).map((b) => b.taille);
  assert.deepEqual(tailles('espece', 'tortue'), [5]);
  assert.deepEqual(tailles('espece', 'hippocampe'), [4]);
  assert.deepEqual(tailles('couleur', 'rose'), []); // tuiles roses toutes isolées
  assert.deepEqual(tailles('couleur', 'jaune').sort(), [2, 2]);
});

test('disposition de référence : 6 bancs de 6 de chaque côté, 90 partout', () => {
  // Lignes = espèce, colonnes = couleur : chaque ligne et chaque colonne forme un banc complet.
  for (const g of [REFERENCE, transpose(REFERENCE)]) {
    const s = score(g);
    assert.equal(s.especes, 90);
    assert.equal(s.couleurs, 90);
    assert.equal(s.resultat, 'egalite');
    assert.equal(s.bancs.length, 12);
  }
});

test('tuiles toutes isolées : 0 partout, égalité', () => {
  // s = r+2c, couleur = 3r+c (déterminant 5, inversible mod 6) : 36 combinaisons, aucun voisin orthogonal ne partage espèce ou couleur.
  const g = Array.from({ length: 6 }, (_, r) => Array.from({ length: 6 }, (_, c) => ({
    espece: ESPECES[(r + 2 * c) % 6], couleur: COULEURS[(3 * r + c) % 6],
  })));
  assert.deepEqual(valider(g), []);
  const s = score(g);
  assert.equal(s.especes, 0);
  assert.equal(s.couleurs, 0);
  assert.equal(s.resultat, 'egalite');
});

test('la rotation du plateau ne change pas le score', () => {
  for (const g of [PHOTO_OIP, melange(1), melange(42)]) {
    const s0 = score(g);
    let r = g;
    for (let i = 0; i < 3; i++) {
      r = rotation90(r);
      const s = score(r);
      assert.equal(s.especes, s0.especes);
      assert.equal(s.couleurs, s0.couleurs);
    }
  }
});

test('plateaux mélangés : chaque tuile appartient à exactement un banc par attribut', () => {
  for (let seed = 1; seed <= 50; seed++) {
    const g = melange(seed);
    assert.deepEqual(valider(g), []);
    const s = score(g);
    for (const type of ['espece', 'couleur']) {
      const couvertes = s.bancs.filter((b) => b.type === type).reduce((n, b) => n + b.taille, 0);
      assert.ok(couvertes <= 36);
      const total = s.bancs.filter((b) => b.type === type).reduce((n, b) => n + b.points, 0);
      assert.equal(total, type === 'espece' ? s.especes : s.couleurs);
    }
  }
});

test('valider détecte doublons et valeurs inconnues', () => {
  const g = REFERENCE.map((l) => l.map((t) => ({ ...t })));
  g[0][1] = { espece: 'poisson', couleur: 'rouge' };
  g[5][5] = { espece: 'dauphin', couleur: 'rose' };
  const e = valider(g);
  assert.ok(e.some((m) => m.includes('doublon')));
  assert.ok(e.some((m) => m.includes('dauphin')));
  assert.deepEqual(valider([[1]]), ['la grille doit faire 6x6']);
});
