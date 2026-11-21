import json
import tempfile
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
from mediaamps.data import load_amps
from mediaamps.models import canex


def write_synthetic(folder, n=60, seed=0):
    """Escribe un extracto sintético con la estructura de AMPS (3 diarios)."""
    rng = np.random.default_rng(seed)
    cat, cols = [], {'qn': np.arange(1, n + 1)}
    for j in range(3):
        f, x, c = f'flag{j}', f'x{j}', f'code{j}'
        lee = rng.random(n) < .5
        cols[f] = lee.astype(int)
        cols[x] = np.where(lee, rng.integers(1, 6, n), np.nan)
        cols[c] = np.where(lee, rng.integers(1, 14, n), np.nan)
        cat.append({'name': f'Diario {j}', 'group': 'Diarios', 'columns': [f, x, c]})
    cat.append({'name': 'Revista', 'group': 'Revistas', 'columns': ['a', 'b', 'c']})
    (folder / 'catalog.js').write_text('const ampsCatalog = ' + json.dumps(cat) + ';', encoding='utf-8')
    pd.DataFrame(cols).to_csv(folder / 'lectura.csv', index=False)
    pd.DataFrame({'qn': cols['qn'], 'pwgt': rng.uniform(.5, 2, n)}).to_csv(folder / 'pesos.csv', index=False)


class TestLoad(unittest.TestCase):
    def test_carga_sintetica(self):
        with tempfile.TemporaryDirectory() as d:
            write_synthetic(Path(d))
            W, X, obs, names = load_amps(d)
        self.assertEqual(names, ['Diario 0', 'Diario 1', 'Diario 2'])
        self.assertEqual(X.shape, (60, 3)); self.assertEqual(obs.shape, (60, 3, 4))
        # las ventanas son anidadas: ayer ⊆ 7 días ⊆ 14 días ⊆ 28 días
        self.assertTrue(np.all(obs[..., 0] <= obs[..., 1]) and np.all(obs[..., 1] <= obs[..., 2])
                        and np.all(obs[..., 2] <= obs[..., 3]))
        self.assertTrue(np.all(W > 0))

    def test_faltan_archivos(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(FileNotFoundError, 'Descargar los datos'):
                load_amps(d)

    def test_pesos_invalidos(self):
        with tempfile.TemporaryDirectory() as d:
            write_synthetic(Path(d))
            w = pd.read_csv(Path(d) / 'pesos.csv'); w.loc[0, 'pwgt'] = -1
            w.to_csv(Path(d) / 'pesos.csv', index=False)
            with self.assertRaises(ValueError):
                load_amps(d)


class TestGuarda(unittest.TestCase):
    def test_canex_rechaza_enumeraciones_enormes(self):
        p = np.full(6, .2); co = np.full((6, 6), .05); np.fill_diagonal(co, p)
        with self.assertRaisesRegex(ValueError, 'celdas'):
            canex(p, co, [20] * 6, [.05] * 6)


if __name__ == '__main__':
    unittest.main()
