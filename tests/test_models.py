import unittest
import numpy as np
from scipy.stats import binom
from mediaamps.models import canex, person_a, sim
from mediaamps.data import weighted_mean
from mediaamps.validation import paired_bootstrap, H3, BASELINES


class TestCoverage(unittest.TestCase):
    def test_weighted_mean(self):
        self.assertAlmostEqual(weighted_mean(np.array([0, 1]), np.array([1, 3])), .75)
        with self.assertRaises(ValueError):
            weighted_mean([1, 0], [1, -1])

    def test_canex_two_bernoulli(self):
        p = np.array([.3, .25]); co = np.array([[.3, .1], [.1, .25]])
        f, stats = canex(p, co, [1, 1], [0, 0], full=True)
        np.testing.assert_allclose(f, [.55, .35, .10], atol=1e-12)
        self.assertAlmostEqual(stats['mean_returned'], .55)
        self.assertAlmostEqual(canex(p, co, [1, 1], [0, 0]), f[0])

    def test_canex_independent_binomial(self):
        f, stats = canex([.25], [[.25]], [5], [.25**2], full=True)
        np.testing.assert_allclose(f, binom.pmf(np.arange(6), 5, .25), atol=1e-12)
        self.assertAlmostEqual(stats['mean_returned'], 1.25)

    def test_canex_truncation(self):
        p = np.full(4, .5); co = np.full((4,4), .48); np.fill_diagonal(co, p)
        f, stats = canex(p, co, [1]*4, [0]*4, full=True)
        self.assertGreater(stats['negative_mass'], 0)
        self.assertTrue(np.all(f >= 0))
        self.assertAlmostEqual(f.sum(), 1.)

    def test_simulation_reproducible_and_nested(self):
        x = np.array([[0, 5], [3, -1], [2, 4]])
        ac = (np.linspace(.2, .9, 6), np.linspace(1., 5., 6))
        a, c = person_a(x, ac, np.array([1., 1.]))
        self.assertEqual(a[1, 1], 0)
        self.assertTrue(np.all((a >= 0) & (a <= 1)))
        r = sim(x, ac, np.ones(2), .5, .3, 10, 42)
        np.testing.assert_array_equal(r, sim(x, ac, np.ones(2), .5, .3, 10, 42))
        self.assertTrue(np.all(r[..., :-1] <= r[..., 1:]))

    def test_bootstrap_identical_predictions(self):
        y = [np.array([0,1])] * 3
        p = [{H3: .5, **{b:.5 for b in BASELINES}}] * 3
        diffs = paired_bootstrap(y, p, np.ones(2), 10, np.random.default_rng(1))
        np.testing.assert_array_equal(diffs, np.zeros((10,3,3)))


if __name__ == '__main__':
    unittest.main()
