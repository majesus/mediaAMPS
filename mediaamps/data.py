"""Carga y definición de la referencia de recencia."""
import json
import re
from pathlib import Path
import numpy as np
import pandas as pd

PWD = 5 / 7
NWIN = (None, 5, 10, 20)

def weighted_mean(a, w):
    a, w = np.asarray(a), np.asarray(w)
    if a.shape[0] != len(w) or not np.isfinite(w).all() or np.any(w < 0) or w.sum() <= 0:
        raise ValueError('Pesos no válidos o incompatibles con los datos')
    return (a * w.reshape((-1,) + (1,) * (a.ndim - 1))).sum(0) / w.sum()

def load_amps(data_dir):
    path = Path(data_dir)
    content = (path / 'catalog.js').read_text(encoding='utf-8')
    match = re.search(r'const ampsCatalog = (\[.*?\]);', content, re.S)
    if match is None:
        raise ValueError('No se encuentra ampsCatalog en catalog.js')
    cat = [a for a in json.loads(match[1]) if a['group'] == 'Diarios']
    if not cat:
        raise ValueError('No hay diarios en el catálogo')
    d = pd.read_csv(path / 'lectura.csv', usecols=['qn'] + [v for a in cat for v in a['columns']])
    w = pd.read_csv(path / 'pesos.csv')
    if set(d.qn) != set(w.qn):
        raise ValueError('Las claves qn no coinciden entre lectura y pesos')
    d = d.merge(w, on='qn', validate='one_to_one')
    W = d.pwgt.to_numpy()
    if not np.isfinite(W).all() or np.any(W <= 0):
        raise ValueError('Los factores de elevación deben ser positivos y finitos')
    X = np.column_stack([d[a['columns'][1]].fillna(-1) for a in cat]).astype(int)
    if np.any((X < -1) | (X > 5)):
        raise ValueError('Frecuencias fuera del intervalo -1 a 5')
    code = np.column_stack([d[a['columns'][2]].fillna(99) for a in cat]).astype(int)
    observed = np.stack([code == 1, code <= 7, code <= 8, code <= 9], axis=-1)
    return W, X, observed, [a['name'] for a in cat]
