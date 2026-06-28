import unittest
import pandas as pd

from src.services.fifo_engine import _aplicar_regla_dos_meses


class ReglaDosMesesTests(unittest.TestCase):
    def test_no_liberar_perdida_si_hay_posicion_abierta_al_final(self):
        ventas = pd.DataFrame([
            {
                "Broker": "IBKR",
                "Ticker": "TEST",
                "Fecha_Venta": pd.Timestamp("2025-01-10"),
                "Cantidad_Vendida": 10,
                "Resultado": -100.0,
                "Perdida_Suspendida": 0.0,
                "Perdida_Liberada": 0.0,
            }
        ])

        operaciones = pd.DataFrame([
            {
                "Buy/Sell": "BUY",
                "Symbol": "TEST",
                "TradeDate": pd.Timestamp("2025-01-01"),
                "Quantity": 10,
            },
            {
                "Buy/Sell": "SELL",
                "Symbol": "TEST",
                "TradeDate": pd.Timestamp("2025-01-10"),
                "Quantity": 10,
            },
            {
                "Buy/Sell": "BUY",
                "Symbol": "TEST",
                "TradeDate": pd.Timestamp("2025-03-01"),
                "Quantity": 5,
            },
        ])

        cartera_final = {
            ("IBKR", "TEST"): [{"cantidad": 5.0, "coste_unitario": 100.0}]
        }

        resultado = _aplicar_regla_dos_meses(ventas, operaciones, cartera_final)

        self.assertEqual(resultado.loc[0, "Perdida_Suspendida"], 100.0)
        self.assertEqual(resultado.loc[0, "Perdida_Liberada"], 0.0)

    def test_liberar_perdida_en_venta_posterior_que_cierra_posicion(self):
        ventas = pd.DataFrame([
            {
                "Broker": "IBKR",
                "Ticker": "TEST",
                "Fecha_Venta": pd.Timestamp("2025-01-10"),
                "Cantidad_Vendida": 10,
                "Resultado": -100.0,
                "Perdida_Suspendida": 0.0,
                "Perdida_Liberada": 0.0,
            },
            {
                "Broker": "IBKR",
                "Ticker": "TEST",
                "Fecha_Venta": pd.Timestamp("2026-03-05"),
                "Cantidad_Vendida": 5,
                "Resultado": 20.0,
                "Perdida_Suspendida": 0.0,
                "Perdida_Liberada": 0.0,
            },
        ])

        operaciones = pd.DataFrame([
            {
                "Buy/Sell": "BUY",
                "Symbol": "TEST",
                "TradeDate": pd.Timestamp("2025-01-01"),
                "Quantity": 10,
            },
            {
                "Buy/Sell": "SELL",
                "Symbol": "TEST",
                "TradeDate": pd.Timestamp("2025-01-10"),
                "Quantity": 10,
            },
            {
                "Buy/Sell": "BUY",
                "Symbol": "TEST",
                "TradeDate": pd.Timestamp("2025-03-01"),
                "Quantity": 5,
            },
            {
                "Buy/Sell": "SELL",
                "Symbol": "TEST",
                "TradeDate": pd.Timestamp("2026-03-05"),
                "Quantity": 5,
            },
        ])

        cartera_final = {("IBKR", "TEST"): []}

        resultado = _aplicar_regla_dos_meses(ventas, operaciones, cartera_final)

        self.assertEqual(resultado.loc[0, "Perdida_Suspendida"], 100.0)
        self.assertEqual(resultado.loc[0, "Perdida_Liberada"], 0.0)
        self.assertEqual(resultado.loc[1, "Perdida_Suspendida"], 0.0)
        self.assertEqual(resultado.loc[1, "Perdida_Liberada"], 100.0)


if __name__ == "__main__":
    unittest.main()
