from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.reporting.charts import (
    barra_ascii,
    preparar_cartera_por_coste,
    preparar_resultado_mensual,
    preparar_resultado_mensual_acumulado,
    preparar_resultado_por_valor,
)
from src.services.tax import ANIO_ESCALA_DEFECTO
from src.utils.formatting import formatear_eur, periodo_fiscal


console = Console()


def _estilo_importe(valor):
    if valor > 0:
        return "green"
    if valor < 0:
        return "red"
    return "white"


def _imprimir_seccion_ascii(titulo):
    print(f"\n{'=' * 80}")
    print(titulo.upper())
    print("=" * 80)


def _imprimir_seccion_rich(titulo):
    console.print()
    console.rule(f"[bold cyan]{titulo}[/]")


def _imprimir_grafico_ascii(resumen_anual):
    if resumen_anual.empty:
        return

    max_abs = float(
        resumen_anual[[
            "Rendimiento_Neto_Computable",
            "Base_Ahorro_Tras_Compensacion",
            "Impuesto_Estimado",
        ]]
        .abs()
        .max()
        .max()
    )
    if max_abs <= 0:
        return

    print("\nGrafico anual")
    for _, fila in resumen_anual.iterrows():
        anio = int(fila["Anio_Fiscal"])
        rendimiento = float(fila["Rendimiento_Neto_Computable"])
        base = float(fila["Base_Ahorro_Tras_Compensacion"])
        print(
            f"{anio} resultado {barra_ascii(rendimiento, max_abs):<24} {formatear_eur(rendimiento):>14}"
        )
        print(
            f"{anio} base      {barra_ascii(base, max_abs):<24} {formatear_eur(base):>14}"
        )


def _crear_grafico_rich(resumen_anual):
    if resumen_anual.empty:
        return None

    max_abs = float(
        resumen_anual[["Rendimiento_Neto_Computable", "Base_Ahorro_Tras_Compensacion"]]
        .abs()
        .max()
        .max()
    )
    if max_abs <= 0:
        return None

    grafico = Table(title="Grafico anual", box=box.SIMPLE, header_style="bold cyan")
    grafico.add_column("Año", justify="right")
    grafico.add_column("Resultado")
    grafico.add_column("Base")
    grafico.add_column("Impuesto")

    for _, fila in resumen_anual.iterrows():
        anio = str(int(fila["Anio_Fiscal"]))
        celdas = []
        for columna in [
            "Rendimiento_Neto_Computable",
            "Base_Ahorro_Tras_Compensacion",
            "Impuesto_Estimado",
        ]:
            valor = float(fila[columna])
            estilo = _estilo_importe(valor)
            barra = barra_ascii(valor, max_abs, ancho=14)
            celdas.append(f"[{estilo}]{barra:<14} {formatear_eur(valor)}[/]")
        grafico.add_row(anio, *celdas)
    return grafico


def _crear_grafico_importes_rich(titulo, datos, texto_vacio, ancho=24, etiqueta_columna="Concepto"):
    if datos.empty:
        return Panel(texto_vacio, title=titulo, border_style="yellow")

    max_abs = float(datos["Importe"].abs().max())
    if max_abs <= 0:
        return Panel(texto_vacio, title=titulo, border_style="yellow")

    grafico = Table(title=titulo, box=box.SIMPLE, header_style="bold cyan")
    grafico.add_column(etiqueta_columna, max_width=18, overflow="ellipsis")
    grafico.add_column("Gráfico")
    grafico.add_column("Importe", justify="right")
    for _, fila in datos.iterrows():
        importe = float(fila["Importe"])
        estilo = _estilo_importe(importe)
        grafico.add_row(
            str(fila["Etiqueta"]),
            f"[{estilo}]{barra_ascii(importe, max_abs, ancho)}[/]",
            f"[{estilo}]{formatear_eur(importe)}[/]",
        )
    return grafico


def _graficos_detalle_rich(datos_declaracion_valor, df_cartera, df_ventas):
    datos_mensuales = preparar_resultado_mensual(df_ventas)
    datos_acumulados = preparar_resultado_mensual_acumulado(df_ventas)
    return [
        _crear_grafico_importes_rich(
            "Evolución mensual",
            datos_mensuales,
            "Sin ventas mensuales computables.",
            ancho=22,
            etiqueta_columna="Periodo",
        ),
        _crear_grafico_importes_rich(
            "Acumulado mensual",
            datos_acumulados,
            "Sin ventas mensuales computables.",
            ancho=22,
            etiqueta_columna="Periodo",
        ),
        _crear_grafico_importes_rich(
            "Top valores por impacto fiscal",
            preparar_resultado_por_valor(datos_declaracion_valor, limite=8),
            "Sin ventas por valor.",
            ancho=22,
        ),
        _crear_grafico_importes_rich(
            "Cartera abierta por coste",
            preparar_cartera_por_coste(df_cartera, limite=8),
            "Sin cartera abierta.",
            ancho=22,
        ),
    ]


def _imprimir_grafico_importes_ascii(titulo, datos, texto_vacio, ancho=24):
    print(f"\n{titulo}")
    if datos.empty:
        print(texto_vacio)
        return

    max_abs = float(datos["Importe"].abs().max())
    if max_abs <= 0:
        print(texto_vacio)
        return

    for _, fila in datos.iterrows():
        importe = float(fila["Importe"])
        etiqueta = str(fila["Etiqueta"])[:18]
        print(f"{etiqueta:<18} {barra_ascii(importe, max_abs, ancho):<24} {formatear_eur(importe):>14}")


def _imprimir_graficos_detalle_ascii(datos_declaracion_valor, df_cartera, df_ventas):
    _imprimir_grafico_importes_ascii(
        "Evolucion mensual",
        preparar_resultado_mensual(df_ventas),
        "Sin ventas mensuales computables.",
        ancho=22,
    )
    _imprimir_grafico_importes_ascii(
        "Acumulado mensual",
        preparar_resultado_mensual_acumulado(df_ventas),
        "Sin ventas mensuales computables.",
        ancho=22,
    )
    _imprimir_grafico_importes_ascii(
        "Top valores por impacto fiscal",
        preparar_resultado_por_valor(datos_declaracion_valor, limite=8),
        "Sin ventas por valor.",
    )
    _imprimir_grafico_importes_ascii(
        "Cartera abierta por coste",
        preparar_cartera_por_coste(df_cartera, limite=8),
        "Sin cartera abierta.",
    )


def imprimir_resumen_consola(resultado):
    conteos = resultado["conteos"]
    resumen_anual = resultado["resumen_anual"]
    df_ventas = resultado["df_ventas"]
    df_operaciones = resultado["df_operaciones"]
    df_cartera = resultado["df_cartera"]
    bloqueos_df = resultado["bloqueos_df"]
    datos_declaracion_valor = resultado["datos_declaracion_valor"]
    datos_declaracion_broker = resultado["datos_declaracion_broker"]

    _imprimir_seccion_ascii("Datos cargados")
    print("Resumen de carga")
    print(f"- Operaciones IBKR: {conteos['IBKR']}")
    print(f"- Operaciones Revolut: {conteos['Revolut']}")
    print(f"- Total operaciones: {conteos['Total']}")
    print(f"- Rendimientos capital mobiliario: {conteos['Rendimientos_Capital']}")

    if not df_operaciones.empty:
        print(f"- Rango de fechas en CSVs: {df_operaciones['TradeDate'].min().date()} a {df_operaciones['TradeDate'].max().date()}")

    if conteos["Operaciones_FX_BCE"] > 0:
        print(
            f"\nFX: {conteos['Operaciones_FX_BCE']} operaciones no EUR sin FX_Rate del broker "
            "se han convertido con tipos historicos oficiales del BCE."
        )

    if resultado["anios_sin_escala"]:
        anios = ", ".join(str(anio) for anio in resultado["anios_sin_escala"])
        print(f"AVISO: no hay escala de ahorro configurada para {anios}; se usa la escala {ANIO_ESCALA_DEFECTO}.")

    _imprimir_seccion_ascii("Resumen fiscal")
    if resumen_anual.empty:
        print("Sin ventas computables.")
    else:
        tabla = resumen_anual[
            [
                "Anio_Fiscal",
                "Resultado_Bruto",
                "Rendimiento_Capital_Mobiliario",
                "Perdidas_Suspendidas",
                "Perdidas_Liberadas",
                "Rendimiento_Neto_Computable",
                "Perdidas_Pendientes_Aplicadas",
                "Rendimientos_Negativos_Pendientes_Aplicados",
                "Compensacion_25pct_Aplicada",
                "Base_Ahorro_Tras_Compensacion",
                "Perdida_Pendiente_Compensar_4Anios",
                "Rendimiento_Negativo_Pendiente_Compensar_4Anios",
                "Impuesto_Estimado",
            ]
        ].copy()
        tabla["Periodo_Fiscal"] = tabla["Anio_Fiscal"].map(periodo_fiscal)
        tabla.columns = [
            "Año",
            "Resultado bruto",
            "Capital mobiliario",
            "Pérdidas suspendidas",
            "Pérdidas liberadas",
            "Rendimiento año",
            "Pérdidas previas aplicadas",
            "Rend. negativos aplicados",
            "Compensación 25%",
            "Base tras compensación",
            "Pérdida pendiente 4 años",
            "Rend. negativo pendiente 4 años",
            "Impuesto estimado",
            "Periodo fiscal",
        ]
        tabla = tabla[
            [
                "Año",
                "Periodo fiscal",
                "Resultado bruto",
                "Capital mobiliario",
                "Pérdidas suspendidas",
                "Pérdidas liberadas",
                "Rendimiento año",
                "Pérdidas previas aplicadas",
                "Rend. negativos aplicados",
                "Compensación 25%",
                "Base tras compensación",
                "Pérdida pendiente 4 años",
                "Rend. negativo pendiente 4 años",
                "Impuesto estimado",
            ]
        ]
        for columna in tabla.columns[1:]:
            if columna != "Periodo fiscal":
                tabla[columna] = tabla[columna].map(formatear_eur)
        print(tabla.to_string(index=False))

    _imprimir_seccion_ascii("Graficos")
    if resumen_anual.empty:
        print("Sin ventas computables.")
    else:
        _imprimir_grafico_ascii(resumen_anual)
        _imprimir_graficos_detalle_ascii(datos_declaracion_valor, df_cartera, df_ventas)

    def imprimir_tabla_declaracion(titulo, datos, texto_vacio):
        print(f"\n{titulo}")
        if datos.empty:
            print(texto_vacio)
            return

        tabla_declaracion = datos[
            [
                "Anio_Fiscal",
                "Broker",
                "Concepto_0328",
                "Valor_Transmision",
                "Valor_Adquisicion",
                "Resultado_Computable",
            ]
        ].copy()
        for anio, grupo in tabla_declaracion.groupby("Anio_Fiscal", sort=True):
            tabla_anio = grupo[
                [
                    "Broker",
                    "Concepto_0328",
                    "Valor_Transmision",
                    "Valor_Adquisicion",
                    "Resultado_Computable",
                ]
            ].copy()
            tabla_anio.columns = [
                "Bróker",
                "Concepto (0328)",
                "Valor transmisión (0329)",
                "Valor adquisición (0330)",
                "Resultado computable",
            ]
            for columna in ["Valor transmisión (0329)", "Valor adquisición (0330)", "Resultado computable"]:
                tabla_anio[columna] = tabla_anio[columna].map(formatear_eur)
            print(f"\nAño {int(anio)} ({periodo_fiscal(anio)})")
            print(tabla_anio.to_string(index=False))

    _imprimir_seccion_ascii("Datos Hacienda")
    imprimir_tabla_declaracion(
        "Datos para Renta Web - modo por valor",
        datos_declaracion_valor,
        "Sin ventas computables por valor.",
    )
    imprimir_tabla_declaracion(
        "Datos para Renta Web - modo por bróker",
        datos_declaracion_broker,
        "Sin ventas computables por bróker.",
    )

    _imprimir_seccion_ascii("Cartera y bloqueos")
    print("Cartera abierta")
    print(f"- Posiciones abiertas: {len(df_cartera)}")
    print(f"- Tickers con pérdidas bloqueadas vigentes: {len(bloqueos_df)}")
    if df_cartera.empty:
        print("Sin posiciones abiertas.")
    else:
        tabla_cartera = df_cartera[
            [
                "Broker",
                "Ticker",
                "Acciones",
                "Precio_Medio (€)",
                "Coste_Total (€)",
            ]
        ].copy()
        tabla_cartera.columns = [
            "Bróker",
            "Ticker",
            "Acciones",
            "Precio medio",
            "Coste total",
        ]
        for columna in ["Precio medio", "Coste total"]:
            tabla_cartera[columna] = tabla_cartera[columna].map(formatear_eur)
        print(tabla_cartera.to_string(index=False))

    if not bloqueos_df.empty:
        tabla_bloqueos = bloqueos_df.copy()
        tabla_bloqueos.columns = ["Ticker", "Pérdida retenida"]
        tabla_bloqueos["Pérdida retenida"] = tabla_bloqueos["Pérdida retenida"].map(formatear_eur)
        print("\nPérdidas bloqueadas vigentes")
        print(tabla_bloqueos.to_string(index=False))


def imprimir_resumen_rich(resultado):
    conteos = resultado["conteos"]
    resumen_anual = resultado["resumen_anual"]
    df_ventas = resultado["df_ventas"]
    df_operaciones = resultado["df_operaciones"]
    df_cartera = resultado["df_cartera"]
    bloqueos_df = resultado["bloqueos_df"]
    datos_declaracion_valor = resultado["datos_declaracion_valor"]
    datos_declaracion_broker = resultado["datos_declaracion_broker"]

    _imprimir_seccion_rich("Datos cargados")

    carga = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    carga.add_column("Dato", style="cyan")
    carga.add_column("Valor", style="white")
    carga.add_row("Operaciones IBKR", str(conteos["IBKR"]))
    carga.add_row("Operaciones Revolut", str(conteos["Revolut"]))
    carga.add_row("Total operaciones", str(conteos["Total"]))
    carga.add_row("Rendimientos capital mobiliario", str(conteos["Rendimientos_Capital"]))
    if not df_operaciones.empty:
        carga.add_row(
            "Rango de fechas en CSVs",
            f"{df_operaciones['TradeDate'].min().date()} a {df_operaciones['TradeDate'].max().date()}",
        )
    carga.add_row("FX via BCE", str(conteos["Operaciones_FX_BCE"]))
    console.print(Panel(carga, title="Carga de datos", border_style="cyan"))

    if conteos["Operaciones_FX_BCE"] > 0:
        console.print(
            Panel(
                f"{conteos['Operaciones_FX_BCE']} operaciones no EUR sin FX_Rate del broker "
                "se han convertido con tipos historicos oficiales del BCE.",
                title="Divisas",
                border_style="green",
            )
        )

    if resultado["anios_sin_escala"]:
        anios = ", ".join(str(anio) for anio in resultado["anios_sin_escala"])
        console.print(
            Panel(
                f"No hay escala de ahorro configurada para {anios}; se usa la escala {ANIO_ESCALA_DEFECTO}.",
                title="Aviso fiscal",
                border_style="yellow",
            )
        )

    _imprimir_seccion_rich("Resumen fiscal")

    if resumen_anual.empty:
        console.print(Panel("Sin ventas computables.", title="Resumen fiscal", border_style="yellow"))
    else:
        tabla = Table(title="Resumen por año", box=box.ROUNDED, header_style="bold cyan")
        tabla.add_column("Año", justify="right")
        tabla.add_column("Acciones", justify="right")
        tabla.add_column("Capital", justify="right")
        tabla.add_column("Base", justify="right")
        tabla.add_column("Impuesto", justify="right")
        tabla_compensaciones = Table(
            title="Compensaciones",
            box=box.ROUNDED,
            header_style="bold cyan",
        )
        tabla_compensaciones.add_column("Año", justify="right")
        tabla_compensaciones.add_column("Previas", justify="right")
        tabla_compensaciones.add_column("Comp. 25%", justify="right")
        tabla_compensaciones.add_column("Pendiente", justify="right")
        for _, fila in resumen_anual.iterrows():
            rendimiento = float(fila["Rendimiento_Neto_Computable"])
            base_compensada = float(fila["Base_Ahorro_Tras_Compensacion"])
            previas = (
                float(fila.get("Perdidas_Pendientes_Aplicadas", 0.0))
                + float(fila.get("Rendimientos_Negativos_Pendientes_Aplicados", 0.0))
            )
            pendiente = (
                float(fila.get("Perdida_Pendiente_Compensar_4Anios", 0.0))
                + float(fila.get("Rendimiento_Negativo_Pendiente_Compensar_4Anios", 0.0))
            )
            tabla.add_row(
                str(int(fila["Anio_Fiscal"])),
                f"[{_estilo_importe(rendimiento)}]{formatear_eur(rendimiento)}[/]",
                formatear_eur(float(fila.get("Rendimiento_Capital_Mobiliario", 0.0))),
                f"[{_estilo_importe(base_compensada)}]{formatear_eur(base_compensada)}[/]",
                formatear_eur(float(fila["Impuesto_Estimado"])),
            )
            tabla_compensaciones.add_row(
                str(int(fila["Anio_Fiscal"])),
                formatear_eur(previas),
                formatear_eur(float(fila.get("Compensacion_25pct_Aplicada", 0.0))),
                formatear_eur(pendiente),
            )
        console.print(tabla)
        console.print(tabla_compensaciones)

        _imprimir_seccion_rich("Gráficos")
        grafico = _crear_grafico_rich(resumen_anual)
        if grafico is not None:
            console.print(grafico)
        for grafico_detalle in _graficos_detalle_rich(datos_declaracion_valor, df_cartera, df_ventas):
            console.print(grafico_detalle)

    _imprimir_seccion_rich("Datos Hacienda")

    def imprimir_tabla_declaracion_rich(titulo, datos, texto_vacio):
        if datos.empty:
            console.print(Panel(texto_vacio, title=titulo, border_style="yellow"))
            return

        for anio, grupo in datos.groupby("Anio_Fiscal", sort=True):
            tabla_declaracion = Table(
                title=f"{titulo} - Año {int(anio)} ({periodo_fiscal(anio)})",
                box=box.ROUNDED,
                header_style="bold cyan",
            )
            tabla_declaracion.add_column("Bróker")
            tabla_declaracion.add_column("Concepto (0328)")
            tabla_declaracion.add_column("Valor transmisión (0329)", justify="right")
            tabla_declaracion.add_column("Valor adquisición (0330)", justify="right")
            tabla_declaracion.add_column("Resultado computable", justify="right")
            for _, fila in grupo.iterrows():
                resultado_computable = float(fila["Resultado_Computable"])
                tabla_declaracion.add_row(
                    fila["Broker"],
                    fila["Concepto_0328"],
                    formatear_eur(float(fila["Valor_Transmision"])),
                    formatear_eur(float(fila["Valor_Adquisicion"])),
                    f"[{_estilo_importe(resultado_computable)}]{formatear_eur(resultado_computable)}[/]",
                )
            console.print(tabla_declaracion)

    imprimir_tabla_declaracion_rich(
        "Renta Web - modo por valor",
        datos_declaracion_valor,
        "Sin ventas computables por valor.",
    )
    imprimir_tabla_declaracion_rich(
        "Renta Web - modo por bróker",
        datos_declaracion_broker,
        "Sin ventas computables por bróker.",
    )

    _imprimir_seccion_rich("Cartera y bloqueos")

    cartera = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    cartera.add_column("Dato", style="cyan")
    cartera.add_column("Valor")
    cartera.add_row("Posiciones abiertas", str(len(df_cartera)))
    cartera.add_row("Tickers con pérdidas bloqueadas vigentes", str(len(bloqueos_df)))
    console.print(Panel(cartera, title="Cartera abierta", border_style="cyan"))

    if not df_cartera.empty:
        tabla_cartera = Table(title="Detalle de cartera abierta", box=box.ROUNDED, header_style="bold cyan")
        tabla_cartera.add_column("Bróker")
        tabla_cartera.add_column("Ticker")
        tabla_cartera.add_column("Acciones", justify="right")
        tabla_cartera.add_column("Precio medio", justify="right")
        tabla_cartera.add_column("Coste total", justify="right")
        for _, fila in df_cartera.iterrows():
            tabla_cartera.add_row(
                fila["Broker"],
                fila["Ticker"],
                str(fila["Acciones"]),
                formatear_eur(float(fila["Precio_Medio (€)"])),
                formatear_eur(float(fila["Coste_Total (€)"])),
            )
        console.print(tabla_cartera)
    else:
        console.print(Panel("Sin posiciones abiertas.", title="Detalle de cartera abierta", border_style="yellow"))

    if not bloqueos_df.empty:
        tabla_bloqueos = Table(title="Pérdidas bloqueadas vigentes", box=box.ROUNDED, header_style="bold cyan")
        tabla_bloqueos.add_column("Ticker")
        tabla_bloqueos.add_column("Pérdida retenida", justify="right")
        for _, fila in bloqueos_df.iterrows():
            tabla_bloqueos.add_row(
                fila["Ticker"],
                formatear_eur(float(fila["Perdida_Suspendida"])),
            )
        console.print(tabla_bloqueos)
