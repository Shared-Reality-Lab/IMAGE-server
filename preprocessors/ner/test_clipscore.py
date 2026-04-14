import unittest

import numpy as np

from clipscore import normalize_rows


class NormalizeRowsTest(unittest.TestCase):
    def test_normalizes_rows(self):
        values = np.array([[3.0, 4.0], [5.0, 12.0]])
        normalized = normalize_rows(values)
        expected = np.array([[0.6, 0.8], [5.0 / 13.0, 12.0 / 13.0]])
        np.testing.assert_allclose(normalized, expected)

    def test_preserves_zero_rows(self):
        values = np.array([[0.0, 0.0], [0.0, 2.0]])
        normalized = normalize_rows(values)
        expected = np.array([[0.0, 0.0], [0.0, 1.0]])
        np.testing.assert_allclose(normalized, expected)


if __name__ == "__main__":
    unittest.main()
