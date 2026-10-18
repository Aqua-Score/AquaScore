// Reconnaissance des 36 tuiles dans le navigateur (ONNX Runtime Web) + affectation hongroise.
import { hongrois } from './hongrois.js';

const ORT = 'https://cdn.jsdelivr.net/npm/onnxruntime-web@1.20.1/dist/';

let session = null, config = null;

function chargerScript(src) {
  return new Promise((ok, ko) => {
    const s = document.createElement('script');
    s.src = src; s.onload = ok; s.onerror = () => ko(new Error(`chargement impossible : ${src}`));
    document.head.appendChild(s);
  });
}

export async function chargerModele() {
  if (session) return config;
  const [cfg] = await Promise.all([fetch('model/modele.json').then((r) => r.json()), chargerScript(`${ORT}ort.min.js`)]);
  window.ort.env.wasm.wasmPaths = ORT;
  window.ort.env.wasm.numThreads = 1;
  session = await window.ort.InferenceSession.create(`model/${cfg.fichier}`, { executionProviders: ['wasm'] });
  config = cfg;
  return cfg;
}

// Découpe les 36 vignettes d'une zone carrée (x, y, cote) de `source` (vidéo, image ou canvas),
// avec la même marge autour de chaque case qu'à l'entraînement.
export function decouper(source, x, y, cote) {
  const { entree, marge_case: marge } = config;
  const c = cote / 6;
  const cv = document.createElement('canvas');
  cv.width = cv.height = entree;
  const ctx = cv.getContext('2d', { willReadFrequently: true });
  ctx.imageSmoothingQuality = 'high';
  const vignettes = [];
  for (let r = 0; r < 6; r++) {
    for (let col = 0; col < 6; col++) {
      ctx.drawImage(source, x + col * c - marge * c, y + r * c - marge * c, c * (1 + 2 * marge), c * (1 + 2 * marge), 0, 0, entree, entree);
      vignettes.push(ctx.getImageData(0, 0, entree, entree));
    }
  }
  return vignettes;
}

// vignettes (36 ImageData) → grille 6×6 de { espece, couleur, confiance }.
export async function reconnaitre(vignettes) {
  const { entree: n, moyenne, ecart, especes, couleurs } = config;
  const plan = n * n;
  const x = new Float32Array(vignettes.length * 3 * plan);
  vignettes.forEach((img, k) => {
    const d = img.data, base = k * 3 * plan;
    for (let i = 0; i < plan; i++) {
      for (let ch = 0; ch < 3; ch++) x[base + ch * plan + i] = (d[i * 4 + ch] / 255 - moyenne[ch]) / ecart[ch];
    }
  });
  const sortie = await session.run({ image: new window.ort.Tensor('float32', x, [vignettes.length, 3, n, n]) });
  const ps = sortie.espece.data, pc = sortie.couleur.data;
  // Coût de « tuile i = combinaison s×6+c » : −log P(espèce) − log P(couleur).
  const cout = vignettes.map((_, i) => Array.from({ length: 36 }, (_, k) =>
    -Math.log(ps[i * 6 + Math.floor(k / 6)] + 1e-9) - Math.log(pc[i * 6 + (k % 6)] + 1e-9)));
  const aff = hongrois(cout);
  const grille = [];
  for (let r = 0; r < 6; r++) {
    grille.push([]);
    for (let col = 0; col < 6; col++) {
      const i = r * 6 + col, s = Math.floor(aff[i] / 6), c = aff[i] % 6;
      grille[r].push({ espece: especes[s], couleur: couleurs[c], confiance: ps[i * 6 + s] * pc[i * 6 + c] });
    }
  }
  return grille;
}
