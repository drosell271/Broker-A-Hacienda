import pandas as pd


TRAMOS_AHORRO_POR_ANIO = {
    2024: [(6000, 0.19), (50000, 0.21), (200000, 0.23), (300000, 0.27), (float("inf"), 0.28)],
    2025: [(6000, 0.19), (50000, 0.21), (200000, 0.23), (300000, 0.27), (float("inf"), 0.30)],
    2026: [(6000, 0.19), (50000, 0.21), (200000, 0.23), (300000, 0.27), (float("inf"), 0.30)],
}

ANIO_ESCALA_DEFECTO = 2025
LIMITE_COMPENSACION_CRUZADA_AHORRO = 0.25


def calcular_impuesto_ahorro(rendimiento_computable, anio=None):
    if rendimiento_computable <= 0:
        return 0.0

    tramos = TRAMOS_AHORRO_POR_ANIO.get(anio, TRAMOS_AHORRO_POR_ANIO[ANIO_ESCALA_DEFECTO])
    impuesto, anterior, restante = 0.0, 0, rendimiento_computable
    for limite, tarifa in tramos:
        ancho_tramo = limite - anterior
        if restante > ancho_tramo:
            impuesto += ancho_tramo * tarifa
            restante -= ancho_tramo
            anterior = limite
        else:
            impuesto += restante * tarifa
            break
    return impuesto


def aplicar_compensacion_perdidas_pendientes(resumen_anual):
    if resumen_anual.empty:
        return resumen_anual, pd.DataFrame()

    resumen = resumen_anual.sort_values("Anio_Fiscal").reset_index(drop=True).copy()
    if "Rendimiento_Capital_Mobiliario" not in resumen:
        resumen["Rendimiento_Capital_Mobiliario"] = 0.0

    perdidas_patrimoniales_pendientes = []
    rendimientos_negativos_pendientes = []
    aplicadas = []
    rendimientos_aplicados = []
    compensaciones_25 = []
    bases_compensadas = []
    pendientes_cierre = []
    rendimientos_pendientes_cierre = []

    def filtrar_pendientes(pendientes, anio):
        return [
            perdida for perdida in pendientes
            if perdida["Anio_Limite"] >= anio and perdida["Importe_Pendiente"] > 0.005
        ]

    def aplicar_pendientes(pendientes, importe_disponible):
        aplicado = 0.0
        for perdida in pendientes:
            if importe_disponible <= 0:
                break
            importe = min(perdida["Importe_Pendiente"], importe_disponible)
            perdida["Importe_Pendiente"] -= importe
            importe_disponible -= importe
            aplicado += importe
        pendientes[:] = [p for p in pendientes if p["Importe_Pendiente"] > 0.005]
        return aplicado, importe_disponible

    for _, fila in resumen.iterrows():
        anio = int(fila["Anio_Fiscal"])
        perdidas_patrimoniales_pendientes = filtrar_pendientes(
            perdidas_patrimoniales_pendientes,
            anio,
        )
        rendimientos_negativos_pendientes = filtrar_pendientes(
            rendimientos_negativos_pendientes,
            anio,
        )

        rendimiento_patrimonial = float(fila["Rendimiento_Neto_Computable"])
        rendimiento_capital = float(fila["Rendimiento_Capital_Mobiliario"])

        if rendimiento_patrimonial < 0:
            perdidas_patrimoniales_pendientes.append({
                "Tipo": "Perdida patrimonial",
                "Anio_Origen": anio,
                "Anio_Limite": anio + 4,
                "Importe_Pendiente": abs(rendimiento_patrimonial),
            })
            base_patrimonial = 0.0
        else:
            base_patrimonial = rendimiento_patrimonial

        if rendimiento_capital < 0:
            rendimientos_negativos_pendientes.append({
                "Tipo": "Rendimiento capital negativo",
                "Anio_Origen": anio,
                "Anio_Limite": anio + 4,
                "Importe_Pendiente": abs(rendimiento_capital),
            })
            base_capital = 0.0
        else:
            base_capital = rendimiento_capital

        perdida_aplicada, base_patrimonial = aplicar_pendientes(
            perdidas_patrimoniales_pendientes,
            base_patrimonial,
        )
        rendimiento_aplicado, base_capital = aplicar_pendientes(
            rendimientos_negativos_pendientes,
            base_capital,
        )

        compensacion_25 = 0.0
        if base_capital > 0 and perdidas_patrimoniales_pendientes:
            limite = base_capital * LIMITE_COMPENSACION_CRUZADA_AHORRO
            importe, _ = aplicar_pendientes(perdidas_patrimoniales_pendientes, limite)
            base_capital -= importe
            compensacion_25 += importe

        if base_patrimonial > 0 and rendimientos_negativos_pendientes:
            limite = base_patrimonial * LIMITE_COMPENSACION_CRUZADA_AHORRO
            importe, _ = aplicar_pendientes(rendimientos_negativos_pendientes, limite)
            base_patrimonial -= importe
            compensacion_25 += importe

        aplicadas.append(perdida_aplicada)
        rendimientos_aplicados.append(rendimiento_aplicado)
        compensaciones_25.append(compensacion_25)
        bases_compensadas.append(base_patrimonial + base_capital)
        pendientes_cierre.append(
            sum(perdida["Importe_Pendiente"] for perdida in perdidas_patrimoniales_pendientes)
        )
        rendimientos_pendientes_cierre.append(
            sum(perdida["Importe_Pendiente"] for perdida in rendimientos_negativos_pendientes)
        )

    resumen["Perdidas_Pendientes_Aplicadas"] = aplicadas
    resumen["Rendimientos_Negativos_Pendientes_Aplicados"] = rendimientos_aplicados
    resumen["Compensacion_25pct_Aplicada"] = compensaciones_25
    resumen["Base_Ahorro_Tras_Compensacion"] = bases_compensadas
    resumen["Perdida_Pendiente_Compensar_4Anios"] = pendientes_cierre
    resumen["Rendimiento_Negativo_Pendiente_Compensar_4Anios"] = rendimientos_pendientes_cierre

    detalle_pendientes = pd.DataFrame(
        perdidas_patrimoniales_pendientes + rendimientos_negativos_pendientes
    )
    return resumen, detalle_pendientes
