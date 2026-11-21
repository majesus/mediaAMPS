"""Experimento de referencia reproducible."""
import time
import numpy as np
import pandas as pd
from .data import load_amps, weighted_mean as wm, NWIN
from .models import calib, person_a, sim, fit_dyn, canex

H3 = 'H3 actividad persistente (x entrenamiento)'
BASELINES = ('CanEx calibrado (q=E[p^2])', 'Empírico (entrenamiento)', 'Independiente entre ediciones')

def paired_bootstrap(outcomes, predictions, weights, n_boot, rng):
    """Remuestrea personas con los mismos multiplicadores en todos los planes."""
    weights = np.asarray(weights, float)
    y = np.column_stack(outcomes).astype(float)
    multiplicity = rng.multinomial(len(weights), np.full(len(weights), 1 / len(weights)), size=n_boot)
    bw = multiplicity * weights
    truth = (bw @ y) / bw.sum(axis=1, keepdims=True)
    h = np.array([p[H3] for p in predictions])
    result = []
    for base in BASELINES:
        b = np.array([p.get(base) if p.get(base) is not None else np.nan for p in predictions])
        delta = 100 * (np.abs(h - truth) - np.abs(b - truth))
        result.append(np.stack([np.nanmean(delta[:, k::3], axis=1) for k in range(3)], axis=1))
    return np.stack(result, axis=-1)

def run(data_dir, output, n_boot=0, bootstrap_output=None):
    W, XM, OBS, names = load_amps(data_dir)
    N, J = XM.shape
    # ---------------- evaluación ----------------
    rng = np.random.default_rng(2011)
    plans = [np.sort(rng.choice(J, 3 + i % 2, replace=False)) for i in range(60)]
    folds = np.array_split(rng.permutation(N), 5); rows = []; t0 = time.time(); NP = 5000
    boot = []; brng = np.random.default_rng(20261121)
    for fi, te in enumerate(folds):
        outcomes, predictions = [], []
        tr = np.concatenate([s for k, s in enumerate(folds) if k != fi])
        a_x, s, mu = calib(tr, XM, OBS, W); phi_a, rho_c = fit_dyn(tr, a_x, s, rng, XM, OBS, W)
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
                nw = NWIN[k]; outcome = OBS[te][:, plan, k].any(1); truth = wm(outcome.astype(float), W[te]); res = {}
                emp = wm(OBS[tr][:, plan, k].any(1).astype(float), wt); res["Empírico (entrenamiento)"] = emp
                res["Independiente entre ediciones"] = wm(1 - np.prod((1 - pe[:, plan]) ** nw, axis=1), wt)
                for lab, (p_, c_, q_) in {"CanEx (entradas benchmark)": (pb, cb, qb), "CanEx calibrado (q=E[p^2])": (pc, cc, qc)}.items():
                    f0 = canex(p_[plan], c_[np.ix_(plan, plan)], np.full(len(plan), nw), q_[plan]); res[lab] = None if f0 is None else 1 - f0
                for lab, (r, w_) in sims.items(): res[lab] = wm(r[:, :, plan, k].any(-1).mean(0).astype(float), w_)
                for lab, v in res.items():
                    if v is not None: rows.append([fi, pi, ("7d", "14d", "28d")[k - 1], lab, abs(v - truth) * 100, (v - truth) * 100])
                if n_boot:
                    outcomes.append(outcome); predictions.append(res)
        if n_boot:
            boot.append(paired_bootstrap(outcomes, predictions, W[te], n_boot, brng))
        print(f"pliegue {fi} listo ({time.time()-t0:.0f}s) phi_a={phi_a} rho_c={rho_c} a_x={np.round(a_x[0],2)} c+={np.round(a_x[1],2)}", flush=True)
    df = pd.DataFrame(rows, columns=["fold", "plan", "ventana", "modelo", "err_abs_pp", "sesgo_pp"]); df.to_csv(output, index=False)
    t = df.pivot_table(index="modelo", columns="ventana", values="err_abs_pp", aggfunc="mean")[["7d", "14d", "28d"]]
    b = df.pivot_table(index="modelo", columns="ventana", values="sesgo_pp", aggfunc="mean")[["7d", "14d", "28d"]]
    n = df.groupby("modelo").size() / 3
    print("\nError absoluto medio de la cobertura (pp), 300 comparaciones por ventana (n válidas = columna n/3):"); print(t.assign(n=n).round(2).to_string())
    print("\nSesgo medio (pp; positivo = sobrestima):"); print(b.round(2).to_string())
    if n_boot:
        samples = np.mean(boot, axis=0)
        paired = df.pivot(index=['fold', 'plan', 'ventana'], columns='modelo', values='err_abs_pp')
        intervals = []
        for k, window in enumerate(('7d', '14d', '28d')):
            for j, base in enumerate(BASELINES):
                diff = (paired[H3] - paired[base]).xs(window, level='ventana').dropna()
                lo, hi = np.quantile(samples[:, k, j], [.025, .975])
                intervals.append([window, H3, base, diff.mean(), lo, hi, len(diff), n_boot])
        pd.DataFrame(intervals, columns=['ventana', 'modelo', 'referencia', 'delta_mae_pp', 'ic95_inf', 'ic95_sup', 'n_pareadas', 'remuestras']).to_csv(bootstrap_output, index=False)
    return df
