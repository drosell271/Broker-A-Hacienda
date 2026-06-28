import unittest

import pandas as pd

from src.services.fifo_engine import _aplicar_regla_dos_meses


def _operaciones_base(incluir_venta_final=False, cantidad_venta_final=5):
    operaciones = [
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
    ]
    if incluir_venta_final:
        operaciones.append({
            "Buy/Sell": "SELL",
            "Symbol": "TEST",
            "TradeDate": pd.Timestamp("2026-03-05"),
            "Quantity": cantidad_venta_final,
        })
    return pd.DataFrame(operaciones)


def _compras_base():
    return pd.DataFrame([
        {
            "Broker": "IBKR",
            "Ticker": "TEST",
            "Fecha_Compra": pd.Timestamp("2025-01-01"),
            "Cantidad_Comprada": 10,
            "Lote_Compra_ID": 0,
        },
        {
            "Broker": "IBKR",
            "Ticker": "TEST",
            "Fecha_Compra": pd.Timestamp("2025-03-01"),
            "Cantidad_Comprada": 5,
            "Lote_Compra_ID": 1,
        },
    ])


def _venta_perdida_inicial():
    return {
        "Broker": "IBKR",
        "Ticker": "TEST",
        "Fecha_Venta": pd.Timestamp("2025-01-10"),
        "Cantidad_Vendida": 10,
        "Fecha_Compra": pd.Timestamp("2025-01-01"),
        "Lote_Compra_ID": 0,
        "Resultado": -100.0,
        "Perdida_Suspendida": 0.0,
        "Perdida_Liberada": 0.0,
    }


class ReglaDosMesesTests(unittest.TestCase):
    def test_prorratea_perdida_si_la_recompra_es_parcial_y_sigue_abierta(self):
        ventas = pd.DataFrame([_venta_perdida_inicial()])

        resultado = _aplicar_regla_dos_meses(
            ventas,
            _operaciones_base(),
            {("IBKR", "TEST"): [{"cantidad": 5.0, "coste_unitario": 100.0}]},
            _compras_base(),
        )

        self.assertEqual(resultado.loc[0, "Perdida_Suspendida"], 50.0)
        self.assertEqual(resultado.loc[0, "Perdida_Liberada"], 0.0)

    def test_liberar_perdida_en_venta_posterior_que_cierra_posicion(self):
        ventas = pd.DataFrame([
            _venta_perdida_inicial(),
            {
                "Broker": "IBKR",
                "Ticker": "TEST",
                "Fecha_Venta": pd.Timestamp("2026-03-05"),
                "Cantidad_Vendida": 5,
                "Fecha_Compra": pd.Timestamp("2025-03-01"),
                "Lote_Compra_ID": 1,
                "Resultado": 20.0,
                "Perdida_Suspendida": 0.0,
                "Perdida_Liberada": 0.0,
            },
        ])

        resultado = _aplicar_regla_dos_meses(
            ventas,
            _operaciones_base(incluir_venta_final=True),
            {("IBKR", "TEST"): []},
            _compras_base(),
        )

        self.assertEqual(resultado.loc[0, "Perdida_Suspendida"], 50.0)
        self.assertEqual(resultado.loc[0, "Perdida_Liberada"], 0.0)
        self.assertEqual(resultado.loc[1, "Perdida_Suspendida"], 0.0)
        self.assertEqual(resultado.loc[1, "Perdida_Liberada"], 50.0)

    def test_prorratea_liberacion_si_la_recompra_se_vende_parcialmente(self):
        ventas = pd.DataFrame([
            _venta_perdida_inicial(),
            {
                "Broker": "IBKR",
                "Ticker": "TEST",
                "Fecha_Venta": pd.Timestamp("2025-04-01"),
                "Cantidad_Vendida": 3,
                "Fecha_Compra": pd.Timestamp("2025-03-01"),
                "Lote_Compra_ID": 1,
                "Resultado": 15.0,
                "Perdida_Suspendida": 0.0,
                "Perdida_Liberada": 0.0,
            },
        ])

        resultado = _aplicar_regla_dos_meses(
            ventas,
            _operaciones_base(incluir_venta_final=True, cantidad_venta_final=3),
            {("IBKR", "TEST"): [{"cantidad": 2.0, "coste_unitario": 100.0}]},
            _compras_base(),
        )

        self.assertEqual(resultado.loc[0, "Perdida_Suspendida"], 50.0)
        self.assertEqual(resultado.loc[1, "Perdida_Liberada"], 30.0)
        self.assertAlmostEqual(
            resultado["Perdida_Suspendida"].sum() - resultado["Perdida_Liberada"].sum(),
            20.0,
        )


if __name__ == "__main__":
    unittest.main()
