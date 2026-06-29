import unittest

from src.reporting.charts import barra_ascii


class BarraAsciiTests(unittest.TestCase):
    def test_usa_linea_para_importes_positivos_y_negativos(self):
        self.assertEqual(barra_ascii(50, 100, ancho=10), "-----")
        self.assertEqual(barra_ascii(-50, 100, ancho=10), "-----")


if __name__ == "__main__":
    unittest.main()
