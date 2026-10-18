import { test } from 'node:test';
import assert from 'node:assert/strict';
import { hongrois } from '../app/js/hongrois.js';

const total = (cout, a) => a.reduce((s, j, i) => s + cout[i][j], 0);

// Force brute sur toutes les permutations (petites tailles uniquement).
function optimum(cout) {
  const n = cout.length;
  let best = Infinity;
  const perm = (k, pris, s) => {
    if (s >= best) return;
    if (k === n) { best = s; return; }
    for (let j = 0; j < n; j++) if (!pris[j]) { pris[j] = true; perm(k + 1, pris, s + cout[k][j]); pris[j] = false; }
  };
  perm(0, [], 0);
  return best;
}

test('hongrois : cas simple connu', () => {
  const c = [[4, 1, 3], [2, 0, 5], [3, 2, 2]];
  const a = hongrois(c);
  assert.equal(total(c, a), 5);
  assert.deepEqual([...a].sort(), [0, 1, 2]);
});

test('hongrois : égale la force brute sur des matrices pseudo-aléatoires', () => {
  let s = 7;
  const alea = () => (s = (s * 1103515245 + 12345) % 2 ** 31) / 2 ** 31;
  for (let essai = 0; essai < 30; essai++) {
    const n = 2 + (essai % 6);
    const c = Array.from({ length: n }, () => Array.from({ length: n }, () => Math.round(alea() * 100)));
    assert.equal(total(c, hongrois(c)), optimum(c));
  }
});

test('hongrois : 36×36 renvoie une permutation et corrige un doublon', () => {
  // Diagonale presque parfaite, sauf la ligne 5 qui préfère la colonne 3 (déjà prise).
  const c = Array.from({ length: 36 }, (_, i) => Array.from({ length: 36 }, (_, j) => (i === j ? 0 : 10)));
  c[5][3] = -1;
  const a = hongrois(c);
  assert.deepEqual([...a].sort((x, y) => x - y), [...Array(36).keys()]);
  assert.equal(a[5], 5);
  assert.equal(a[3], 3);
});
