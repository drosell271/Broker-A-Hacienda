from pathlib import Path

from src.reporting.charts import (
    guardar_acumulado_mensual_png,
    guardar_barras_horizontales_png,
    guardar_linea_mensual_png,
    guardar_resumen_anual_png,
    preparar_cartera_por_coste,
    preparar_resultado_mensual,
    preparar_resultado_mensual_acumulado,
    preparar_resultado_por_valor,
)
from src.utils.formatting import periodo_fiscal


def escribir_graficos_markdown(f, ruta_salida, resumen_anual, datos_declaracion_valor, df_cartera, df_ventas):
    carpeta_graficos = ruta_salida.parent / "charts"

    graficos = {
        "Resumen anual por ejercicio": carpeta_graficos / "resumen_anual.png",
        "Evolución mensual del resultado computable": carpeta_graficos / "evolucion_mensual.png",
        "Acumulado mensual del resultado computable": carpeta_graficos / "acumulado_mensual.png",
        "Top valores por impacto fiscal": carpeta_graficos / "top_valores.png",
        "Cartera abierta por coste fiscal": carpeta_graficos / "cartera_abierta.png",
    }

    guardar_resumen_anual_png(resumen_anual, graficos["Resumen anual por ejercicio"])
    guardar_linea_mensual_png(
        preparar_resultado_mensual(df_ventas),
        graficos["Evolución mensual del resultado computable"],
    )
    guardar_acumulado_mensual_png(
        preparar_resultado_mensual_acumulado(df_ventas),
        graficos["Acumulado mensual del resultado computable"],
    )
    guardar_barras_horizontales_png(
        preparar_resultado_por_valor(datos_declaracion_valor),
        graficos["Top valores por impacto fiscal"],
        "Top valores por impacto fiscal",
        "Sin ventas por valor.",
    )
    guardar_barras_horizontales_png(
        preparar_cartera_por_coste(df_cartera),
        graficos["Cartera abierta por coste fiscal"],
        "Cartera abierta por coste fiscal",
        "Sin cartera abierta.",
    )

    for titulo, ruta_grafico in graficos.items():
        ruta_relativa = ruta_grafico.relative_to(ruta_salida.parent).as_posix()
        f.write(f"### {titulo}\n\n")
        f.write(f"![{titulo}]({ruta_relativa})\n\n")


def exportar_a_markdown(
    resumen_anual,
    datos_declaracion_valor,
    datos_declaracion_broker,
    bloqueos_df,
    df_cartera,
    df_ventas=None,
    ruta_salida="informe_fiscal.md",
):
    ruta_salida = Path(ruta_salida)
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)

    with open(ruta_salida, "w", encoding="utf-8") as f:
        f.write("# Informe Fiscal de Inversiones (IRPF España)\n\n")
        f.write("> Informe auxiliar generado automáticamente. Revisa los supuestos de divisa, FIFO y regla de recompra antes de usarlo en Renta Web.\n\n")
        f.write("## 1. Resumen por Año Fiscal (Renta Web)\n\n")
        f.write("| Año Fiscal | Periodo fiscal considerado | Valor Adquisición | Valor Transmisión | Resultado Bruto Acciones | Capital mobiliario | Pérdidas Suspendidas | Pérdidas Liberadas | Rendimiento Acciones | Pérdidas Previas Aplicadas | Rend. Negativos Aplicados | Comp. 25% | Base tras Compensación | Pérdida Pendiente 4 Años | Rend. Negativo Pendiente 4 Años | Est. Impuestos |\n")
        f.write("| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n")

        if resumen_anual.empty:
            f.write("| _Sin ventas computables_ | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - |\n")
        else:
            for _, fila in resumen_anual.iterrows():
                periodo = periodo_fiscal(fila["Anio_Fiscal"])
                f.write(f"| **{int(fila['Anio_Fiscal'])}** "
                        f"| {periodo} "
                        f"| {fila['Valor_Adquisicion']:,.2f} € "
                        f"| {fila['Valor_Transmision']:,.2f} € "
                        f"| {fila['Resultado_Bruto']:,.2f} € "
                        f"| {fila.get('Rendimiento_Capital_Mobiliario', 0.0):,.2f} € "
                        f"| {fila['Perdidas_Suspendidas']:,.2f} € "
                        f"| {fila['Perdidas_Liberadas']:,.2f} € "
                        f"| **{fila['Rendimiento_Neto_Computable']:,.2f} €** "
                        f"| {fila['Perdidas_Pendientes_Aplicadas']:,.2f} € "
                        f"| {fila.get('Rendimientos_Negativos_Pendientes_Aplicados', 0.0):,.2f} € "
                        f"| {fila.get('Compensacion_25pct_Aplicada', 0.0):,.2f} € "
                        f"| **{fila['Base_Ahorro_Tras_Compensacion']:,.2f} €** "
                        f"| {fila['Perdida_Pendiente_Compensar_4Anios']:,.2f} € "
                        f"| {fila.get('Rendimiento_Negativo_Pendiente_Compensar_4Anios', 0.0):,.2f} € "
                        f"| **{fila['Impuesto_Estimado']:,.2f} €** |\n")

        f.write("\n## 2. Gráficos de Control\n\n")
        escribir_graficos_markdown(
            f,
            ruta_salida,
            resumen_anual,
            datos_declaracion_valor,
            df_cartera,
            df_ventas,
        )

        def escribir_tabla_declaracion(datos, texto_vacio):
            if datos.empty:
                f.write(f"{texto_vacio}\n\n")
                return

            for anio, grupo in datos.groupby("Anio_Fiscal", sort=True):
                f.write(f"### Año {int(anio)} ({periodo_fiscal(anio)})\n\n")
                f.write("| Bróker | Concepto (0328) | Apartado Renta Web | Valor Transmisión (0329) | Valor Adquisición (0330) | Resultado Bruto | Pérdidas Suspendidas | Pérdidas Liberadas | Resultado Computable |\n")
                f.write("| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |\n")
                for _, fila in grupo.iterrows():
                    f.write(
                        f"| {fila['Broker']} "
                        f"| {fila['Concepto_0328']} "
                        f"| {fila['Apartado_Renta_Web']} "
                        f"| {fila['Valor_Transmision']:,.2f} € "
                        f"| {fila['Valor_Adquisicion']:,.2f} € "
                        f"| {fila['Resultado_Bruto']:,.2f} € "
                        f"| {fila['Perdidas_Suspendidas']:,.2f} € "
                        f"| {fila['Perdidas_Liberadas']:,.2f} € "
                        f"| **{fila['Resultado_Computable']:,.2f} €** |\n"
                    )
                f.write("\n")

        f.write("\n## 3. Datos para Renta Web - Modo por Valor\n\n")
        f.write("Renta Web 2025: en el apartado F2 de acciones negociadas, usa **0328** para el valor/ticker, **0329** para **Valor Transmisión** y **0330** para **Valor Adquisición**. **Resultado Computable** queda como comprobación después de pérdidas suspendidas o liberadas; las sumas finales del bloque son **0339** para ganancias y **0340** para pérdidas.\n\n")
        escribir_tabla_declaracion(datos_declaracion_valor, "Sin ventas computables por valor.")

        f.write("\n## 4. Datos para Renta Web - Modo por Bróker\n\n")
        f.write("Vista agregada por bróker. En **0328** se usa el bróker como concepto que engloba todos los valores de ese bróker en el año. La compensación de pérdidas pendientes se aplica a nivel anual en el resumen anterior.\n\n")
        escribir_tabla_declaracion(datos_declaracion_broker, "Sin ventas computables por bróker.")

        f.write("\n## 5. Detalle de Bloqueos Vigentes en Cartera Activa\n")
        f.write("Pérdidas retenidas que siguen congeladas porque mantienes acciones compradas a día de hoy:\n\n")

        if not bloqueos_df.empty:
            f.write("| Ticker | Pérdida Retenida |\n")
            f.write("| :--- | :---: |\n")
            for _, fila in bloqueos_df.iterrows():
                f.write(f"| **{fila['Ticker']}** | {fila['Perdida_Suspendida']:,.2f} € |\n")
        else:
            f.write("**Ninguno.** Todas las pérdidas de los tickers cerrados han sido liberadas por liquidación total.\n\n")

        f.write("## 6. Cartera Abierta Real\n")
        if not df_cartera.empty:
            f.write("| Bróker | Ticker | Acciones | Precio Medio | Coste Total |\n")
            f.write("| :--- | :--- | :---: | :---: | :---: |\n")
            for _, fila in df_cartera.iterrows():
                f.write(f"| {fila['Broker']} | **{fila['Ticker']}** | {fila['Acciones']} | {fila['Precio_Medio (€)']:,.2f} € | {fila['Coste_Total (€)']:,.2f} € |\n")
        else:
            f.write("Sin posiciones abiertas.\n")

    return ruta_salida
