import { test } from 'node:test';
import assert from 'node:assert/strict';
import { homographie, appliquer, ordonnerCoins } from '../app/js/homographie.js';

const proche = (a, b) => a.forEach((v, i) => assert.ok(Math.abs(v - b[i]) < 1e-6, `${a} ≠ ${b}`));

test('homographie : envoie les 4 coins sur leurs cibles', () => {
  const src = [[0, 0], [100, 0], [100, 100], [0, 100]];
  const dst = [[12, 30], [410, 8], [455, 390], [20, 440]];
  const H = homographie(src, dst);
  src.forEach((p, i) => proche(appliquer(H, ...p), dst[i]));
});

test('homographie : identité', () => {
  const pts = [[0, 0], [1, 0], [1, 1], [0, 1]];
  proche(homographie(pts, pts), [1, 0, 0, 0, 1, 0, 0, 0, 1]);
});

test('ordonnerCoins : ordre des clics indifférent', () => {
  const attendu = [[10, 12], [300, 5], [310, 290], [4, 300]];
  const melange = [attendu[2], attendu[0], attendu[3], attendu[1]];
  assert.deepEqual(ordonnerCoins(melange), attendu);
});
