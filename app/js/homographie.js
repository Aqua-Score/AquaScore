// Homographie et redressement en JS pur (pas d'OpenCV).

// Résout A x = b (A n×n) par élimination de Gauss avec pivot partiel.
function resoudre(A, b) {
  const n = b.length;
  const M = A.map((ligne, i) => [...ligne, b[i]]);
  for (let col = 0; col < n; col++) {
    let piv = col;
    for (let r = col + 1; r < n; r++) if (Math.abs(M[r][col]) > Math.abs(M[piv][col])) piv = r;
    if (Math.abs(M[piv][col]) < 1e-12) throw new Error('points dégénérés (alignés ?)');
    [M[col], M[piv]] = [M[piv], M[col]];
    for (let r = 0; r < n; r++) {
      if (r === col) continue;
      const f = M[r][col] / M[col][col];
      for (let k = col; k <= n; k++) M[r][k] -= f * M[col][k];
    }
  }
  return M.map((ligne, i) => ligne[n] / ligne[i]);
}

// Homographie H (3x3, à plat, h33 = 1) qui envoie src[i] sur dst[i] ; 4 points [x, y].
export function homographie(src, dst) {
  const A = [], b = [];
  for (let i = 0; i < 4; i++) {
    const [x, y] = src[i], [u, v] = dst[i];
    A.push([x, y, 1, 0, 0, 0, -u * x, -u * y]); b.push(u);
    A.push([0, 0, 0, x, y, 1, -v * x, -v * y]); b.push(v);
  }
  return [...resoudre(A, b), 1];
}

export function appliquer(H, x, y) {
  const w = H[6] * x + H[7] * y + H[8];
  return [(H[0] * x + H[1] * y + H[2]) / w, (H[3] * x + H[4] * y + H[5]) / w];
}

// Remet les 4 coins dans l'ordre haut-gauche, haut-droit, bas-droit, bas-gauche.
export function ordonnerCoins(pts) {
  const somme = pts.map(([x, y]) => x + y), diff = pts.map(([x, y]) => x - y);
  const idx = (arr, f) => arr.indexOf(f(...arr));
  return [
    pts[idx(somme, Math.min)], pts[idx(diff, Math.max)],
    pts[idx(somme, Math.max)], pts[idx(diff, Math.min)],
  ];
}

// Redresse le quadrilatère `coins` de `source` (ImageData) en un carré `taille`×`taille`.
// Échantillonnage bilinéaire, mapping inverse (sortie → source).
export function redresser(source, coins, taille) {
  const carre = [[0, 0], [taille, 0], [taille, taille], [0, taille]];
  const H = homographie(carre, ordonnerCoins(coins));
  const { width: W, height: Hs, data: s } = source;
  const out = new ImageData(taille, taille);
  const d = out.data;
  for (let y = 0; y < taille; y++) {
    for (let x = 0; x < taille; x++) {
      const [sx, sy] = appliquer(H, x + 0.5, y + 0.5);
      const x0 = Math.floor(sx - 0.5), y0 = Math.floor(sy - 0.5);
      const fx = sx - 0.5 - x0, fy = sy - 0.5 - y0;
      const o = (y * taille + x) * 4;
      for (let k = 0; k < 3; k++) {
        const px = (xx, yy) => s[(Math.min(Hs - 1, Math.max(0, yy)) * W + Math.min(W - 1, Math.max(0, xx))) * 4 + k];
        d[o + k] = (px(x0, y0) * (1 - fx) + px(x0 + 1, y0) * fx) * (1 - fy)
                 + (px(x0, y0 + 1) * (1 - fx) + px(x0 + 1, y0 + 1) * fx) * fy;
      }
      d[o + 3] = 255;
    }
  }
  return out;
}
