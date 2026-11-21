"""AMPS 2011 real: modelo de propensión latente con actividad semanal persistente, validado contra la
cobertura observada en ventanas de 1, 7, 14 y 28 días (códigos de última lectura 1, <=7, 8, 9)."""
import argparse, json, re, time
from pathlib import Path
import numpy as np, pandas as pd
from itertools import product
from scipy.stats import norm, binom, betabinom

parser = argparse.ArgumentParser(description='Validación de cobertura por recencia con AMPS 2011')
parser.add_argument('--data-dir', type=Path, default=Path('data/amps'), help='Carpeta con lectura.csv, pesos.csv y catalog.js')
parser.add_argument('--output', type=Path, default=Path('amps_recencia_resultados.csv'), help='CSV de resultados')
args = parser.parse_args()
A = args.data_dir
cat = [a for a in json.loads(re.search(r'const ampsCatalog = (\[.*?\]);', (A / 'catalog.js').read_text(encoding='utf-8'), re.S)[1])
       if a['group'] == 'Diarios']
d = pd.read_csv(A / 'lectura.csv', usecols=['qn'] + [v for a in cat for v in a['columns']]).merge(
    pd.read_csv(A / 'pesos.csv'), on='qn', validate='one_to_one')
W = d.pwgt.to_numpy(); N = len(d); J = len(cat); PWD = 5 / 7
rd = np.column_stack([d[a['columns'][0]].eq(1) for a in cat])
XM = np.column_stack([d[a['columns'][1]].fillna(-1) for a in cat]).astype(int)           # -1: no lector
CODE = np.column_stack([d[a['columns'][2]].fillna(99) for a in cat]).astype(int)
OBS = np.stack([CODE == 1, CODE <= 7, CODE <= 8, CODE <= 9], axis=-1)                       # (N,J,4): ayer, 7d, 14d, 28d
NWIN = (None, 5, 10, 20)                                                                    # ediciones por ventana
wm = lambda a, w: (a * w.reshape((-1,) + (1,) * (a.ndim - 1))).sum(0) / w.sum()

# ---------------- calibración a partir de 'ayer' ----------------
def calib(idx):
    w = W[idx]; x = XM[idx]; y = OBS[idx, :, 0]
    mu = np.zeros(6)
    for k in range(6):
        sel = (x == k); mu[k] = 7 * (w[:, None] * y * sel).sum() / (w[:, None] * sel).sum()
    r7 = OBS[idx, :, 1]
    a_x = np.array([(w[:, None] * r7 * (x == k)).sum() / (w[:, None] * (x == k)).sum() for k in range(6)])
    cp_x = np.clip(mu / np.maximum(a_x, 1e-9), 1, 5)
    ax_ij = np.where(x >= 0, a_x[np.clip(x, 0, 5)], 0.0); cp_ij = np.where(x >= 0, cp_x[np.clip(x, 0, 5)], 1.0)
    pred = PWD * wm(ax_ij * cp_ij / 5, w)
    s = wm(y.astype(float), w) / np.maximum(pred, 1e-12)
    return (a_x, cp_x), s, mu

def person_a(x, ac, s):
    a_x, cp_x = ac
    a = np.where(x >= 0, np.clip(a_x[np.clip(x, 0, 5)] * s[None, :], 0, 1), 0.0)
    cp = np.where(x >= 0, cp_x[np.clip(x, 0, 5)], 1.0)
    return a, cp

# ---------------- simulador ----------------
def sim(x, a_x, s, phi_a, rho_c, S, seed, mode='act', chunk=1000, Bk=5):
    n = len(x); out = np.zeros((S, n, J, 4), bool)
    a_ij, cp_ij = person_a(x, a_x, s); thr = norm.ppf(np.clip(a_ij, 1e-9, 1 - 1e-9))
    for ci, c0 in enumerate(range(0, n, chunk)):
        sl = slice(c0, min(n, c0 + chunk)); m = sl.stop - sl.start
        rng = np.random.default_rng([seed, ci])
        eps = np.sqrt(rho_c) * rng.standard_normal((S, m, 1, Bk)) + np.sqrt(1 - rho_c) * rng.standard_normal((S, m, J, Bk))
        Z = eps.copy()
        for b in range(1, Bk): Z[..., b] = phi_a * Z[..., b - 1] + np.sqrt(1 - phi_a ** 2) * eps[..., b]
        if mode == 'act':
            Act = Z < thr[None, sl, :, None]; mu = cp_ij[None, sl, :, None]
        else:                                                                # conteo fijo calibrado
            Act = np.ones(Z.shape, bool); mu = (a_ij * cp_ij)[None, sl, :, None]
        fl = np.floor(mu); cnt = fl + (rng.random(Z.shape) < (mu - fl))
        rank = np.argsort(np.argsort(rng.random((S, m, J, Bk, 5)), -1), -1)
        F = (Act[..., None] & (rank < cnt[..., None])).reshape(S, m, J, Bk * 5)
        day = rng.integers(0, 7, (S, m)); ts = 5 * (Bk - 1) + np.minimum(day, 4)
        cs = np.concatenate([np.zeros(F.shape[:-1] + (1,), np.int16), np.cumsum(F, -1, dtype=np.int16)], -1)
        g = lambda arr, t: np.take_along_axis(arr, np.broadcast_to(t[:, :, None, None], (S, m, J, 1)), -1)[..., 0]
        out[:, sl, :, 0] = g(F, ts) & (day <= 4)[:, :, None]
        for k, nw in enumerate(NWIN[1:], 1): out[:, sl, :, k] = (g(cs, ts + 1) - g(cs, ts + 1 - nw)) > 0
    return out

# ---------------- ajuste de phi_a y rho_c por momentos simulados ----------------
def fit_dyn(idx, a_x, s, rng, n_sub=2500, S=4):
    sub = rng.choice(idx, n_sub, replace=False); w = W[sub]; x = XM[sub]
    obs_S = {k: wm(OBS[idx, :, k].astype(float), W[idx]).sum() for k in (2, 3)}
    best = None
    for phi in (0.0, 0.2, 0.4, 0.6, 0.8, 0.9):
        r = sim(x, a_x, s, phi, 0.2, S, 5)
        loss = sum(((wm(r[..., k].mean(0).astype(float), w).sum() - obs_S[k]) / obs_S[k]) ** 2 for k in (2, 3))
        if best is None or loss < best[0]: best = (loss, phi)
    phi = best[1]
    yobs = OBS[idx, :, 0].astype(float); K = yobs.sum(1); d_obs = wm((K * K - K) / 2, W[idx])
    best = None
    for rho in (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6):
        r = sim(x, a_x, s, phi, rho, S, 6); K = r[..., 0].sum(-1).astype(float)
        loss = abs(wm(((K * K - K) / 2).mean(0), w) - d_obs)
        if best is None or loss < best[0]: best = (loss, rho)
    return phi, best[1]

# ---------------- CanEx (traducción de la auditoría, con q) ----------------
def canex(p, co, n, q):
    sd = np.sqrt(p * (1 - p)); cor = (co - np.outer(p, p)) / np.outer(sd, sd); np.fill_diagonal(cor, 1)
    if np.linalg.eigvalsh(cor).min() < -1e-8: return None
    fs = []; zs = []
    for j, k in enumerate(n):
        z = np.arange(k + 1); pj = p[j]
        if k == 1: f = binom.pmf(z, k, pj)
        else:
            r = (q[j] - pj ** 2) / (pj * (1 - pj))
            if r < -1e-10 or r > 1 + 1e-10: return None
            f = binom.pmf(z, k, pj) if r < 1e-10 else (np.eye(k + 1)[[0, -1]].T @ [1 - pj, pj] if r > 1 - 1e-10
                                                      else betabinom.pmf(z, k, pj * (1 / r - 1), (1 - pj) * (1 / r - 1)))
        mu = k * pj; fs.append(f); zs.append((z - mu) / np.sqrt(max(np.sum(f * (z - mu) ** 2), 1e-12)))
    grid = np.array(list(product(*[range(k + 1) for k in n])))
    base = np.prod([f[grid[:, j]] for j, f in enumerate(fs)], axis=0)
    zz = np.column_stack([a[grid[:, j]] for j, a in enumerate(zs)])
    raw = np.maximum(base * (1 + np.sum((zz @ (cor - np.eye(len(n)))) * zz, axis=1) / 2), 0)
    return raw[0] / raw.sum()                                                       # P(ningún contacto)

# ---------------- evaluación ----------------
rng = np.random.default_rng(2011)
plans = [np.sort(rng.choice(J, 3 + i % 2, replace=False)) for i in range(60)]
folds = np.array_split(rng.permutation(N), 5); rows = []; t0 = time.time(); NP = 5000
for fi, te in enumerate(folds):
    tr = np.concatenate([s for k, s in enumerate(folds) if k != fi])
    a_x, s, mu = calib(tr); phi_a, rho_c = fit_dyn(tr, a_x, s, rng)
    sub_tr = rng.choice(tr, NP, replace=False); sub_te = rng.choice(te, min(NP, len(te)), replace=False)
    sims = {"H3 actividad persistente (x entrenamiento)": (sim(XM[sub_tr], a_x, s, phi_a, rho_c, 6, 1), W[sub_tr]),
            "H3 actividad persistente (x validación)": (sim(XM[sub_te], a_x, s, phi_a, rho_c, 6, 1), W[sub_te]),
            "H3 sin persistencia (phi_a=0)": (sim(XM[sub_tr], a_x, s, 0.0, rho_c, 6, 1), W[sub_tr]),
            "Conteo fijo calibrado (tipo H2)": (sim(XM[sub_tr], a_x, s, 0.0, rho_c, 6, 1, mode='fixed'), W[sub_tr])}
    # Independiente entre ediciones (analítico, x entrenamiento) y CanEx
    xt = XM[tr]; wt = W[tr]; a_ij, cp_ij = person_a(xt, a_x, s); pe = np.clip(a_ij * cp_ij / 5, 0, 1)
    Pb = np.where(xt >= 0, xt, 0) / 5.0; pb = wm(Pb, wt); cb = (Pb.T * (wt / wt.sum())) @ Pb; qb = wm(np.where(xt >= 0, xt, 0) * (np.where(xt >= 0, xt, 0) - 1) / 20.0, wt)
    pc = wm(pe, wt); cc = (pe.T * (wt / wt.sum())) @ pe; qc = wm(pe ** 2, wt)
    for pi, plan in enumerate(plans):
        for k in (1, 2, 3):
            nw = NWIN[k]; truth = wm(OBS[te][:, plan, k].any(1).astype(float), W[te]); res = {}
            emp = wm(OBS[tr][:, plan, k].any(1).astype(float), wt); res["Empírico (entrenamiento)"] = emp
            res["Independiente entre ediciones"] = wm(1 - np.prod((1 - pe[:, plan]) ** nw, axis=1), wt)
            for lab, (p_, c_, q_) in {"CanEx (entradas benchmark)": (pb, cb, qb), "CanEx calibrado (q=E[p^2])": (pc, cc, qc)}.items():
                f0 = canex(p_[plan], c_[np.ix_(plan, plan)], np.full(len(plan), nw), q_[plan]); res[lab] = None if f0 is None else 1 - f0
            for lab, (r, w_) in sims.items(): res[lab] = wm(r[:, :, plan, k].any(-1).mean(0).astype(float), w_)
            for lab, v in res.items():
                if v is not None: rows.append([fi, pi, ("7d", "14d", "28d")[k - 1], lab, abs(v - truth) * 100, (v - truth) * 100])
    print(f"pliegue {fi} listo ({time.time()-t0:.0f}s) phi_a={phi_a} rho_c={rho_c} a_x={np.round(a_x[0],2)} c+={np.round(a_x[1],2)}", flush=True)
df = pd.DataFrame(rows, columns=["fold", "plan", "ventana", "modelo", "err_abs_pp", "sesgo_pp"]); df.to_csv(args.output, index=False)
t = df.pivot_table(index="modelo", columns="ventana", values="err_abs_pp", aggfunc="mean")[["7d", "14d", "28d"]]
b = df.pivot_table(index="modelo", columns="ventana", values="sesgo_pp", aggfunc="mean")[["7d", "14d", "28d"]]
n = df.groupby("modelo").size() / 3
print("\nError absoluto medio de la cobertura (pp), 300 comparaciones por ventana (n válidas = columna n/3):"); print(t.assign(n=n).round(2).to_string())
print("\nSesgo medio (pp; positivo = sobrestima):"); print(b.round(2).to_string())
