"""Modelos de cobertura y calibración por recencia."""
import numpy as np
from itertools import product
from scipy.stats import norm, binom, betabinom
from .data import weighted_mean as wm, NWIN, PWD

def calib(idx, X, OBS, W):
    w = W[idx]; x = X[idx]; y = OBS[idx, :, 0]
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
    n, J = x.shape; out = np.zeros((S, n, J, 4), bool)
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
def fit_dyn(idx, a_x, s, rng, X, OBS, W, n_sub=2500, S=4):
    sub = rng.choice(idx, n_sub, replace=False); w = W[sub]; x = X[sub]
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
def canex(p, co, n, q, full=False):
    """P(0 contactos), o distribución y diagnóstico si full=True.

    Expansión canónica truncada: las celdas negativas se ponen a cero y se
    renormaliza. Por ello la media final puede diferir de sum(n*p).
    """
    p, co, n, q = map(np.asarray, (p, co, n, q))
    if np.any((p <= 0) | (p >= 1)) or np.any(n < 1) or np.any(n != n.astype(int)):
        return None
    n = n.astype(int)
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
    signed = base * (1 + np.sum((zz @ (cor - np.eye(len(n)))) * zz, axis=1) / 2)
    raw = np.maximum(signed, 0)
    if not full:
        return raw[0] / raw.sum()
    pmf = np.bincount(grid.sum(axis=1), weights=raw, minlength=int(n.sum()) + 1) / raw.sum()
    return pmf, {'negative_mass': float(-np.minimum(signed, 0).sum()),
                 'mean_expected': float(n @ p), 'mean_returned': float(np.arange(len(pmf)) @ pmf)}

