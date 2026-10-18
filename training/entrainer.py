"""Entraîne le classifieur de tuiles (MobileNetV3-Small, deux têtes espèce/couleur).

    python training/extraire.py      # d'abord : photos -> vignettes
    python training/entrainer.py     # validation croisée par partie, puis modèle final + export ONNX

Validation : on met de côté une partie entière à la fois (toutes ses photos), on entraîne
sur le reste, et on mesure la précision par tuile, avant et après l'affectation hongroise,
ainsi que l'exactitude du score final de chaque photo.
"""
import argparse
import json
import random
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn as nn
from scipy.optimize import linear_sum_assignment
from torchvision import models, transforms as T

from plateau import ESPECES, COULEURS

ICI = Path(__file__).parent
ENTREE = 96
MOY, ECART = [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]


class Modele(nn.Module):
    def __init__(self, pretrained=True):
        super().__init__()
        poids = models.MobileNet_V3_Small_Weights.IMAGENET1K_V1 if pretrained else None
        base = models.mobilenet_v3_small(weights=poids)
        self.features, self.pool = base.features, nn.AdaptiveAvgPool2d(1)
        self.cou = nn.Sequential(nn.Flatten(), nn.Linear(576, 256), nn.Hardswish(), nn.Dropout(0.3))
        self.espece, self.couleur = nn.Linear(256, 6), nn.Linear(256, 6)

    def forward(self, x):
        z = self.cou(self.pool(self.features(x)))
        return self.espece(z), self.couleur(z)


class Rot90:
    def __call__(self, x):
        return torch.rot90(x, random.randint(0, 3), (1, 2))


AUGMENT = T.Compose([
    T.ToTensor(),
    T.RandomResizedCrop(ENTREE, scale=(0.7, 1.0), ratio=(0.9, 1.1), antialias=True),
    T.RandomRotation(12, fill=0.2),
    Rot90(),
    T.ColorJitter(brightness=0.4, contrast=0.35, saturation=0.3, hue=0.02),
    T.RandomApply([T.GaussianBlur(5, (0.1, 1.5))], p=0.3),
    T.Normalize(MOY, ECART),
])
TEST = T.Compose([T.ToTensor(), T.Resize(ENTREE, antialias=True), T.Normalize(MOY, ECART)])


def charger(dossier):
    index = json.loads((dossier / 'index.json').read_text(encoding='utf-8'))
    for e in index:
        img = cv2.imread(str(dossier / e['fichier']))
        e['img'] = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        e['y'] = (ESPECES.index(e['espece']), COULEURS.index(e['couleur']))
    return index


def entrainer(exemples, epoques, graine=0, journal=True):
    torch.manual_seed(graine); random.seed(graine)
    m = Modele()
    opt = torch.optim.AdamW([
        {'params': m.features.parameters(), 'lr': 5e-4},
        {'params': [*m.cou.parameters(), *m.espece.parameters(), *m.couleur.parameters()], 'lr': 2e-3},
    ], weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=[5e-4, 2e-3], total_steps=epoques * ((len(exemples) + 31) // 32))
    perte = nn.CrossEntropyLoss(label_smoothing=0.05)
    for ep in range(epoques):
        m.train()
        random.shuffle(exemples)
        total = 0
        for i in range(0, len(exemples), 32):
            lot = exemples[i:i + 32]
            x = torch.stack([AUGMENT(e['img']) for e in lot])
            ys = torch.tensor([e['y'][0] for e in lot]); yc = torch.tensor([e['y'][1] for e in lot])
            ls, lc = m(x)
            l = perte(ls, ys) + perte(lc, yc)
            opt.zero_grad(); l.backward(); opt.step(); sched.step()
            total += l.item() * len(lot)
        if journal and (ep + 1) % 10 == 0:
            print(f'  époque {ep + 1:3d}  perte {total / len(exemples):.3f}')
    return m.eval()


@torch.no_grad()
def probas(m, imgs):
    x = torch.stack([TEST(i) for i in imgs])
    ls, lc = m(x)
    return ls.softmax(1).numpy(), lc.softmax(1).numpy()


def affecter(ps, pc):
    """Affectation hongroise : chaque combinaison espèce×couleur utilisée une seule fois."""
    cout = -(np.log(ps + 1e-9)[:, :, None] + np.log(pc + 1e-9)[:, None, :]).reshape(len(ps), 36)
    lignes, cols = linear_sum_assignment(cout)
    res = np.zeros(len(ps), int)
    res[lignes] = cols
    return res // 6, res % 6


def score(grille):
    """Port Python de app/js/score.js (pour l'évaluation)."""
    tot = {}
    for k in (0, 1):
        vu, pts = set(), 0
        for r in range(6):
            for c in range(6):
                if (r, c) in vu:
                    continue
                pile, n = [(r, c)], 0
                vu.add((r, c))
                while pile:
                    y, x = pile.pop(); n += 1
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        q = (y + dy, x + dx)
                        if 0 <= q[0] < 6 and 0 <= q[1] < 6 and q not in vu and grille[q[0]][q[1]][k] == grille[y][x][k]:
                            vu.add(q); pile.append(q)
                pts += n * (n - 1) // 2
        tot[k] = pts
    return tot[0], tot[1]


def evaluer(m, exemples):
    stats = {'brut': 0, 'hongrois': 0, 'n': 0, 'photos_ok': 0, 'photos': 0, 'erreurs': []}
    for photo in sorted({e['photo'] for e in exemples}):
        ex = sorted([e for e in exemples if e['photo'] == photo], key=lambda e: e['fichier'])
        ps, pc = probas(m, [e['img'] for e in ex])
        ys = np.array([e['y'][0] for e in ex]); yc = np.array([e['y'][1] for e in ex])
        hs, hc = affecter(ps, pc)
        stats['brut'] += int(((ps.argmax(1) == ys) & (pc.argmax(1) == yc)).sum())
        ok = (hs == ys) & (hc == yc)
        stats['hongrois'] += int(ok.sum())
        stats['n'] += len(ex)
        vrai = score([[ (ys[r * 6 + c], yc[r * 6 + c]) for c in range(6)] for r in range(6)])
        pred = score([[ (hs[r * 6 + c], hc[r * 6 + c]) for c in range(6)] for r in range(6)])
        stats['photos'] += 1
        stats['photos_ok'] += vrai == pred
        for i in np.flatnonzero(~ok):
            stats['erreurs'].append(f"{ex[i]['fichier']}: {ex[i]['espece']}/{ex[i]['couleur']} -> {ESPECES[hs[i]]}/{COULEURS[hc[i]]}")
        print(f'    {photo}: {ok.sum()}/36 tuiles, score vrai {vrai} prédit {pred} {"OK" if vrai == pred else "FAUX"}')
    return stats


def exporter(m, exemples, dossier):
    dossier.mkdir(parents=True, exist_ok=True)
    fp32 = dossier / 'tuiles_fp32.onnx'

    class Sortie(nn.Module):           # sorties = probabilités, plus simple côté JS
        def __init__(self, m):
            super().__init__(); self.m = m

        def forward(self, x):
            s, c = self.m(x)
            return s.softmax(1), c.softmax(1)

    torch.onnx.export(Sortie(m).eval(), torch.zeros(1, 3, ENTREE, ENTREE), str(fp32),
                      input_names=['image'], output_names=['espece', 'couleur'],
                      dynamic_axes={'image': {0: 'n'}, 'espece': {0: 'n'}, 'couleur': {0: 'n'}},
                      opset_version=17, dynamo=False)
    from onnxruntime.quantization import quantize_static, CalibrationDataReader, QuantType, QuantFormat
    from onnxruntime.quantization.shape_inference import quant_pre_process

    class Calib(CalibrationDataReader):
        def __init__(self):
            self.it = iter([{'image': TEST(e['img'])[None].numpy()} for e in exemples[:120]])

        def get_next(self):
            return next(self.it, None)

    pre = dossier / '_pre.onnx'
    quant_pre_process(str(fp32), str(pre))
    int8 = dossier / 'tuiles_int8.onnx'
    quantize_static(str(pre), str(int8), Calib(), quant_format=QuantFormat.QDQ,
                    activation_type=QuantType.QUInt8, weight_type=QuantType.QInt8, per_channel=True)
    pre.unlink()
    return fp32, int8


def verifier_onnx(chemin, exemples):
    import onnxruntime as ort
    s = ort.InferenceSession(str(chemin), providers=['CPUExecutionProvider'])
    ok = n = 0
    for photo in sorted({e['photo'] for e in exemples}):
        ex = sorted([e for e in exemples if e['photo'] == photo], key=lambda e: e['fichier'])
        x = np.stack([TEST(e['img']).numpy() for e in ex])
        ps, pc = s.run(None, {'image': x})
        hs, hc = affecter(ps, pc)
        ok += sum((hs[i], hc[i]) == e['y'] for i, e in enumerate(ex)); n += len(ex)
    return ok, n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--epoques', type=int, default=60)
    ap.add_argument('--sans-validation', action='store_true')
    a = ap.parse_args()
    torch.set_num_threads(max(1, torch.get_num_threads()))
    exemples = charger(ICI / 'vignettes')
    etiq = json.loads((ICI / 'etiquettes.json').read_text(encoding='utf-8'))
    # Parties identiques photographiées sous un autre angle : à garder ensemble.
    groupes = etiq.get('memes_parties', [[p] for p in etiq['parties']])
    print(f'{len(exemples)} vignettes, {len({e["photo"] for e in exemples})} photos, groupes de validation : {groupes}')

    rapport = {'validation': []}
    if not a.sans_validation:
        cumul = {'brut': 0, 'hongrois': 0, 'n': 0, 'photos_ok': 0, 'photos': 0}
        for g in groupes:
            print(f'\n== Validation : partie(s) {"+".join(g)} mise(s) de côté ==')
            train = [e for e in exemples if e['partie'] not in g]
            test = [e for e in exemples if e['partie'] in g]
            m = entrainer(list(train), a.epoques)
            s = evaluer(m, test)
            for k in cumul:
                cumul[k] += s[k]
            print(f'  tuiles : {s["brut"]}/{s["n"]} brut, {s["hongrois"]}/{s["n"]} après hongrois ; '
                  f'scores exacts : {s["photos_ok"]}/{s["photos"]}')
            for err in s['erreurs']:
                print('   ', err)
            rapport['validation'].append({'mis_de_cote': g, **s})
        print(f'\n== TOTAL validation : {cumul["brut"]}/{cumul["n"]} brut '
              f'({100 * cumul["brut"] / cumul["n"]:.1f} %), {cumul["hongrois"]}/{cumul["n"]} après hongrois '
              f'({100 * cumul["hongrois"] / cumul["n"]:.1f} %), scores exacts {cumul["photos_ok"]}/{cumul["photos"]} ==')
        rapport['total'] = cumul

    print('\n== Modèle final (toutes les données) ==')
    m = entrainer(list(exemples), a.epoques)
    sortie = ICI.parent / 'app' / 'model'
    fp32, int8 = exporter(m, exemples, sortie)
    justes = {}
    for f in (fp32, int8):
        justes[f] = verifier_onnx(f, exemples)[0]
        print(f'  {f.name} : {f.stat().st_size / 1e6:.2f} Mo, {justes[f]}/{len(exemples)} sur les données d\'entraînement')
    # La quantification int8 ne sert que si elle ne dégrade pas la reconnaissance.
    if justes[int8] < justes[fp32]:
        print('  int8 moins précis que fp32 : on publie fp32')
        int8.unlink()
        retenu = fp32
    else:
        fp32.unlink()
        retenu = int8
    (sortie / 'modele.json').write_text(json.dumps({
        'entree': ENTREE, 'moyenne': MOY, 'ecart': ECART, 'especes': ESPECES, 'couleurs': COULEURS,
        'marge_case': 0.12, 'fichier': retenu.name,
    }, indent=1), encoding='utf-8')
    (ICI / 'rapport.json').write_text(json.dumps(rapport, ensure_ascii=False, indent=1, default=int), encoding='utf-8')


if __name__ == '__main__':
    main()
