from pathlib import Path

import pandas as pd

from src.parsers.capital import cargar_rendimientos_capital_mobiliario
from src.parsers.ibkr import cargar_y_limpiar_ibkr
from src.parsers.revolut import cargar_y_limpiar_revolut
from src.reporting.markdown import exportar_a_markdown
from src.services.fifo_engine import calcular_renta
from src.services.forex import DEFAULT_ECB_CACHE_PATH, aplicar_forex_a_trades
from src.services.tax import (
    TRAMOS_AHORRO_POR_ANIO,
    aplicar_compensacion_perdidas_pendientes,
    calcular_impuesto_ahorro,
)


def contar_operaciones_con_fx_bce(df_all):
    if df_all.empty or "CurrencyPrimary" not in df_all or "FX_Rate" not in df_all:
        return 0

    fx_rate = pd.to_numeric(df_all["FX_Rate"], errors="coerce")
    precio_no_eur = df_all["CurrencyPrimary"].astype(str).str.upper() != "EUR"
    if "IBCommissionCurrency" in df_all:
        comision_no_eur = df_all["IBCommissionCurrency"].astype(str).str.upper() != "EUR"
    else:
        comision_no_eur = False
    sin_fx_broker = fx_rate.isna() | (fx_rate <= 0)
    return int(((precio_no_eur | comision_no_eur) & sin_fx_broker).sum())


def construir_datos_declaracion(df_ventas, modo):
    if df_ventas.empty:
        return pd.DataFrame()

    datos = df_ventas.copy()
    datos["Anio_Fiscal"] = datos["Fecha_Venta"].dt.year

    if modo == "valor":
        columnas_grupo = ["Anio_Fiscal", "Broker", "Ticker"]
        orden = ["Anio_Fiscal", "Broker", "Concepto_0328"]
    elif modo == "broker":
        columnas_grupo = ["Anio_Fiscal", "Broker"]
        orden = ["Anio_Fiscal", "Broker"]
    else:
        raise ValueError(f"Modo de declaracion no soportado: {modo}")

    resumen = datos.groupby(columnas_grupo).agg(
        Valor_Transmision=("Valor_Transmision", "sum"),
        Valor_Adquisicion=("Valor_Adquisicion", "sum"),
        Resultado_Bruto=("Resultado", "sum"),
        Perdidas_Suspendidas=("Perdida_Suspendida", "sum"),
        Perdidas_Liberadas=("Perdida_Liberada", "sum"),
    ).reset_index()

    if modo == "valor":
        resumen["Concepto_0328"] = resumen["Ticker"]
    else:
        resumen["Concepto_0328"] = resumen["Broker"] + " - todos los valores"

    resumen["Resultado_Computable"] = (
        resumen["Resultado_Bruto"]
        + resumen["Perdidas_Suspendidas"]
        - resumen["Perdidas_Liberadas"]
    )
    resumen["Apartado_Renta_Web"] = "Acciones admitidas a negociación"

    columnas = [
        "Anio_Fiscal",
        "Broker",
        "Concepto_0328",
        "Apartado_Renta_Web",
        "Valor_Transmision",
        "Valor_Adquisicion",
        "Resultado_Bruto",
        "Perdidas_Suspendidas",
        "Perdidas_Liberadas",
        "Resultado_Computable",
    ]
    return resumen[columnas].sort_values(orden).reset_index(drop=True)


def _construir_cartera_abierta(cartera_final):
    posiciones_abiertas = []
    for (broker, ticker), lotes in cartera_final.items():
        cantidad_total = sum(lote["cantidad"] for lote in lotes)
        if round(cantidad_total, 6) > 0:
            coste_total = sum(lote["cantidad"] * lote["coste_unitario"] for lote in lotes)
            posiciones_abiertas.append({
                "Broker": broker,
                "Ticker": ticker,
                "Acciones": round(cantidad_total, 6),
                "Precio_Medio (€)": coste_total / cantidad_total,
                "Coste_Total (€)": coste_total,
            })
    return pd.DataFrame(posiciones_abiertas)


def _construir_bloqueos_vigentes(df_cartera, df_ventas):
    if df_cartera.empty or df_ventas.empty:
        return pd.DataFrame()

    tickers_activos = df_cartera["Ticker"].unique()
    df_bloqueos_reales = df_ventas[df_ventas["Ticker"].isin(tickers_activos)].copy()
    if df_bloqueos_reales.empty:
        return pd.DataFrame()

    bloqueos_df = df_bloqueos_reales.groupby("Ticker").agg(
        Perdida_Suspendida=("Perdida_Suspendida", "sum"),
        Perdida_Liberada=("Perdida_Liberada", "sum"),
    ).reset_index()
    bloqueos_df["Perdida_Suspendida"] = (
        bloqueos_df["Perdida_Suspendida"] - bloqueos_df["Perdida_Liberada"]
    )
    bloqueos_df = bloqueos_df[bloqueos_df["Perdida_Suspendida"] > 0.005]
    return bloqueos_df[["Ticker", "Perdida_Suspendida"]].reset_index(drop=True)


def _construir_resumen_anual(df_ventas, df_rendimientos_capital):
    columnas_resumen = [
        "Anio_Fiscal",
        "Valor_Adquisicion",
        "Valor_Transmision",
        "Resultado_Bruto",
        "Perdidas_Suspendidas",
        "Perdidas_Liberadas",
    ]
    resumen_anual = pd.DataFrame(columns=columnas_resumen)

    if not df_ventas.empty:
        df_ventas["Anio_Fiscal"] = df_ventas["Fecha_Venta"].dt.year
        resumen_anual = df_ventas.groupby("Anio_Fiscal").agg(
            Valor_Adquisicion=("Valor_Adquisicion", "sum"),
            Valor_Transmision=("Valor_Transmision", "sum"),
            Resultado_Bruto=("Resultado", "sum"),
            Perdidas_Suspendidas=("Perdida_Suspendida", "sum"),
            Perdidas_Liberadas=("Perdida_Liberada", "sum"),
        ).reset_index()

    if not df_rendimientos_capital.empty:
        resumen_anual = resumen_anual.merge(
            df_rendimientos_capital,
            on="Anio_Fiscal",
            how="outer",
        )
    else:
        resumen_anual["Rendimiento_Capital_Mobiliario"] = 0.0

    if resumen_anual.empty:
        return resumen_anual, pd.DataFrame()

    resumen_anual["Anio_Fiscal"] = resumen_anual["Anio_Fiscal"].astype(int)
    for columna in columnas_resumen[1:] + ["Rendimiento_Capital_Mobiliario"]:
        resumen_anual[columna] = pd.to_numeric(
            resumen_anual[columna],
            errors="coerce",
        ).fillna(0.0)

    resumen_anual["Rendimiento_Neto_Computable"] = (
        resumen_anual["Resultado_Bruto"]
        + resumen_anual["Perdidas_Suspendidas"]
        - resumen_anual["Perdidas_Liberadas"]
    )

    resumen_anual, detalle_perdidas_pendientes = aplicar_compensacion_perdidas_pendientes(
        resumen_anual
    )
    resumen_anual["Impuesto_Estimado"] = resumen_anual.apply(
        lambda fila: calcular_impuesto_ahorro(
            fila["Base_Ahorro_Tras_Compensacion"],
            int(fila["Anio_Fiscal"]),
        ),
        axis=1,
    )
    return resumen_anual, detalle_perdidas_pendientes


def generar_informe_fiscal(
    directorio_datos="data/raw",
    ruta_salida="informe_fiscal.md",
    exportar=True,
    ruta_cache_bce=DEFAULT_ECB_CACHE_PATH,
    actualizar_fx=False,
):
    directorio = Path(directorio_datos)
    if not directorio.exists():
        raise FileNotFoundError(f"No existe el directorio de datos: {directorio}")

    df_ibkr = cargar_y_limpiar_ibkr(directorio)
    df_revolut = cargar_y_limpiar_revolut(directorio)
    df_rendimientos_capital = cargar_rendimientos_capital_mobiliario(directorio)
    df_all = pd.concat([df_ibkr, df_revolut], ignore_index=True)
    operaciones_fx_bce = contar_operaciones_con_fx_bce(df_all)

    df_con_eur = aplicar_forex_a_trades(
        df_all,
        ruta_cache_bce=ruta_cache_bce,
        actualizar_fx=actualizar_fx,
    )
    df_ventas, cartera_final = calcular_renta(df_con_eur)
    datos_declaracion_valor = construir_datos_declaracion(df_ventas, modo="valor")
    datos_declaracion_broker = construir_datos_declaracion(df_ventas, modo="broker")

    resumen_anual, detalle_perdidas_pendientes = _construir_resumen_anual(
        df_ventas,
        df_rendimientos_capital,
    )
    df_cartera = _construir_cartera_abierta(cartera_final)
    bloqueos_df = _construir_bloqueos_vigentes(df_cartera, df_ventas)

    ruta_generada = exportar_a_markdown(
        resumen_anual,
        datos_declaracion_valor,
        datos_declaracion_broker,
        bloqueos_df,
        df_cartera,
        df_ventas,
        ruta_salida,
    ) if exportar else None

    anios_sin_escala = []
    if not resumen_anual.empty:
        anios_sin_escala = sorted(
            set(resumen_anual["Anio_Fiscal"].astype(int)) - set(TRAMOS_AHORRO_POR_ANIO)
        )

    return {
        "df_operaciones": df_all,
        "df_ventas": df_ventas,
        "resumen_anual": resumen_anual,
        "datos_declaracion_valor": datos_declaracion_valor,
        "datos_declaracion_broker": datos_declaracion_broker,
        "bloqueos_df": bloqueos_df,
        "detalle_perdidas_pendientes": detalle_perdidas_pendientes,
        "df_cartera": df_cartera,
        "ruta_salida": ruta_generada,
        "conteos": {
            "IBKR": len(df_ibkr),
            "Revolut": len(df_revolut),
            "Total": len(df_all),
            "Rendimientos_Capital": len(df_rendimientos_capital),
            "Operaciones_FX_BCE": operaciones_fx_bce,
        },
        "anios_sin_escala": anios_sin_escala,
    }
