import pandas as pd
import argparse
import sys
from pathlib import Path

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from src.config.settings import cargar_settings
from src.parsers.ibkr import cargar_y_limpiar_ibkr
from src.parsers.revolut import cargar_y_limpiar_revolut
from src.services.forex import DEFAULT_ECB_CACHE_PATH, aplicar_forex_a_trades, asegurar_historico_bce
from src.services.fifo_engine import calcular_renta

console = Console()

TRAMOS_AHORRO_POR_ANIO = {
    2024: [(6000, 0.19), (50000, 0.21), (200000, 0.23), (300000, 0.27), (float('inf'), 0.28)],
    2025: [(6000, 0.19), (50000, 0.21), (200000, 0.23), (300000, 0.27), (float('inf'), 0.30)],
    2026: [(6000, 0.19), (50000, 0.21), (200000, 0.23), (300000, 0.27), (float('inf'), 0.30)],
}

ANIO_ESCALA_DEFECTO = 2025


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


def _periodo_fiscal(anio):
    anio = int(anio)
    return f"{anio}-01-01 a {anio}-12-31"


def exportar_a_markdown(
    resumen_anual,
    datos_declaracion_valor,
    datos_declaracion_broker,
    bloqueos_df,
    df_cartera,
    ruta_salida="informe_fiscal.md",
):
    ruta_salida = Path(ruta_salida)
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)

    with open(ruta_salida, "w", encoding="utf-8") as f:
        f.write("# Informe Fiscal de Inversiones (IRPF España)\n\n")
        f.write("> Informe auxiliar generado automáticamente. Revisa los supuestos de divisa, FIFO y regla de recompra antes de usarlo en Renta Web.\n\n")
        f.write("## 1. Resumen por Año Fiscal (Renta Web)\n\n")
        f.write("| Año Fiscal | Periodo fiscal considerado | Valor Adquisición | Valor Transmisión | Resultado Bruto | Pérdidas Suspendidas | Pérdidas Liberadas | Rendimiento del Año | Pérdidas Previas Aplicadas | Base tras Compensación | Pérdida Pendiente 4 Años | Est. Impuestos |\n")
        f.write("| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n")
        
        if resumen_anual.empty:
            f.write("| _Sin ventas computables_ | - | - | - | - | - | - | - | - | - | - | - |\n")
        else:
            for _, fila in resumen_anual.iterrows():
                periodo = _periodo_fiscal(fila["Anio_Fiscal"])
                f.write(f"| **{int(fila['Anio_Fiscal'])}** "
                        f"| {periodo} "
                        f"| {fila['Valor_Adquisicion']:,.2f} € "
                        f"| {fila['Valor_Transmision']:,.2f} € "
                        f"| {fila['Resultado_Bruto']:,.2f} € "
                        f"| {fila['Perdidas_Suspendidas']:,.2f} € "
                        f"| {fila['Perdidas_Liberadas']:,.2f} € "
                        f"| **{fila['Rendimiento_Neto_Computable']:,.2f} €** "
                        f"| {fila['Perdidas_Pendientes_Aplicadas']:,.2f} € "
                        f"| **{fila['Base_Ahorro_Tras_Compensacion']:,.2f} €** "
                        f"| {fila['Perdida_Pendiente_Compensar_4Anios']:,.2f} € "
                        f"| **{fila['Impuesto_Estimado']:,.2f} €** |\n")
                    
        def escribir_tabla_declaracion(datos, texto_vacio):
            if datos.empty:
                f.write(f"{texto_vacio}\n\n")
                return

            for anio, grupo in datos.groupby("Anio_Fiscal", sort=True):
                f.write(f"### Año {int(anio)} ({_periodo_fiscal(anio)})\n\n")
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

        f.write("\n## 2. Datos para Renta Web - Modo por Valor\n\n")
        f.write("Renta Web 2025: en el apartado F2 de acciones negociadas, usa **0328** para el valor/ticker, **0329** para **Valor Transmisión** y **0330** para **Valor Adquisición**. **Resultado Computable** queda como comprobación después de pérdidas suspendidas o liberadas; las sumas finales del bloque son **0339** para ganancias y **0340** para pérdidas.\n\n")
        escribir_tabla_declaracion(datos_declaracion_valor, "Sin ventas computables por valor.")

        f.write("\n## 3. Datos para Renta Web - Modo por Bróker\n\n")
        f.write("Vista agregada por bróker. En **0328** se usa el bróker como concepto que engloba todos los valores de ese bróker en el año. La compensación de pérdidas pendientes se aplica a nivel anual en el resumen anterior.\n\n")
        escribir_tabla_declaracion(datos_declaracion_broker, "Sin ventas computables por bróker.")

        f.write("\n## 4. Detalle de Bloqueos Vigentes en Cartera Activa\n")
        f.write("Pérdidas retenidas que siguen congeladas porque mantienes acciones compradas a día de hoy:\n\n")
        
        if not bloqueos_df.empty:
            f.write("| Ticker | Pérdida Retenida |\n")
            f.write("| :--- | :---: |\n")
            for _, fila in bloqueos_df.iterrows():
                f.write(f"| **{fila['Ticker']}** | {fila['Perdida_Suspendida']:,.2f} € |\n")
        else:
            f.write("✅ **Ninguno.** Todas las pérdidas de los tickers cerrados han sido liberadas por liquidación total.\n\n")
            
        f.write("## 5. Cartera Abierta Real\n")
        if not df_cartera.empty:
            f.write("| Bróker | Ticker | Acciones | Precio Medio | Coste Total |\n")
            f.write("| :--- | :--- | :---: | :---: | :---: |\n")
            for _, fila in df_cartera.iterrows():
                f.write(f"| {fila['Broker']} | **{fila['Ticker']}** | {fila['Acciones']} | {fila['Precio_Medio (€)']:,.2f} € | {fila['Coste_Total (€)']:,.2f} € |\n")
        else:
            f.write("Sin posiciones abiertas.\n")
        
    return ruta_salida


def _contar_operaciones_con_fx_bce(df_all):
    if df_all.empty or 'CurrencyPrimary' not in df_all or 'FX_Rate' not in df_all:
        return 0

    fx_rate = pd.to_numeric(df_all['FX_Rate'], errors='coerce')
    precio_no_eur = df_all['CurrencyPrimary'].astype(str).str.upper() != 'EUR'
    if 'IBCommissionCurrency' in df_all:
        comision_no_eur = df_all['IBCommissionCurrency'].astype(str).str.upper() != 'EUR'
    else:
        comision_no_eur = False
    sin_fx_broker = fx_rate.isna() | (fx_rate <= 0)
    return int(((precio_no_eur | comision_no_eur) & sin_fx_broker).sum())


def aplicar_compensacion_perdidas_pendientes(resumen_anual):
    if resumen_anual.empty:
        return resumen_anual, pd.DataFrame()

    resumen = resumen_anual.sort_values("Anio_Fiscal").reset_index(drop=True).copy()
    perdidas_pendientes = []
    aplicadas = []
    bases_compensadas = []
    pendientes_cierre = []

    for _, fila in resumen.iterrows():
        anio = int(fila["Anio_Fiscal"])
        perdidas_pendientes = [
            perdida for perdida in perdidas_pendientes
            if perdida["Anio_Limite"] >= anio and perdida["Importe_Pendiente"] > 0.005
        ]

        rendimiento = float(fila["Rendimiento_Neto_Computable"])
        perdida_aplicada = 0.0

        if rendimiento > 0:
            base_compensada = rendimiento
            for perdida in perdidas_pendientes:
                if base_compensada <= 0:
                    break
                importe = min(perdida["Importe_Pendiente"], base_compensada)
                perdida["Importe_Pendiente"] -= importe
                base_compensada -= importe
                perdida_aplicada += importe
        else:
            base_compensada = 0.0
            if rendimiento < 0:
                perdidas_pendientes.append({
                    "Anio_Origen": anio,
                    "Anio_Limite": anio + 4,
                    "Importe_Pendiente": abs(rendimiento),
                })

        perdidas_pendientes = [
            perdida for perdida in perdidas_pendientes
            if perdida["Importe_Pendiente"] > 0.005
        ]

        aplicadas.append(perdida_aplicada)
        bases_compensadas.append(base_compensada)
        pendientes_cierre.append(sum(perdida["Importe_Pendiente"] for perdida in perdidas_pendientes))

    resumen["Perdidas_Pendientes_Aplicadas"] = aplicadas
    resumen["Base_Ahorro_Tras_Compensacion"] = bases_compensadas
    resumen["Perdida_Pendiente_Compensar_4Anios"] = pendientes_cierre

    detalle_pendientes = pd.DataFrame(perdidas_pendientes)
    return resumen, detalle_pendientes


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
    df_all = pd.concat([df_ibkr, df_revolut], ignore_index=True)
    operaciones_fx_bce = _contar_operaciones_con_fx_bce(df_all)

    df_con_eur = aplicar_forex_a_trades(
        df_all,
        ruta_cache_bce=ruta_cache_bce,
        actualizar_fx=actualizar_fx,
    )
    df_ventas, cartera_final = calcular_renta(df_con_eur)
    datos_declaracion_valor = construir_datos_declaracion(df_ventas, modo="valor")
    datos_declaracion_broker = construir_datos_declaracion(df_ventas, modo="broker")

    resumen_anual, bloqueos_df = pd.DataFrame(), pd.DataFrame()
    
    if not df_ventas.empty:
        df_ventas['Anio_Fiscal'] = df_ventas['Fecha_Venta'].dt.year
        resumen_anual = df_ventas.groupby('Anio_Fiscal').agg(
            Valor_Adquisicion=('Valor_Adquisicion', 'sum'),
            Valor_Transmision=('Valor_Transmision', 'sum'),
            Resultado_Bruto=('Resultado', 'sum'),
            Perdidas_Suspendidas=('Perdida_Suspendida', 'sum'),
            Perdidas_Liberadas=('Perdida_Liberada', 'sum')
        ).reset_index()

        # El rendimiento computable neto ahora resta las pérdidas que han sido liberadas
        resumen_anual['Rendimiento_Neto_Computable'] = (
            resumen_anual['Resultado_Bruto'] + 
            resumen_anual['Perdidas_Suspendidas'] - 
            resumen_anual['Perdidas_Liberadas']
        )

        resumen_anual, detalle_perdidas_pendientes = aplicar_compensacion_perdidas_pendientes(resumen_anual)
        resumen_anual['Impuesto_Estimado'] = resumen_anual.apply(
            lambda fila: calcular_impuesto_ahorro(
                fila['Base_Ahorro_Tras_Compensacion'],
                int(fila['Anio_Fiscal'])
            ),
            axis=1
        )
    else:
        detalle_perdidas_pendientes = pd.DataFrame()

    posiciones_abiertas = []
    for (broker, ticker), lotes in cartera_final.items():
        cantidad_total = sum(lote['cantidad'] for lote in lotes)
        if round(cantidad_total, 6) > 0:
            coste_total = sum(lote['cantidad'] * lote['coste_unitario'] for lote in lotes)
            posiciones_abiertas.append({
                'Broker': broker, 'Ticker': ticker, 'Acciones': round(cantidad_total, 6),
                'Precio_Medio (€)': coste_total / cantidad_total, 'Coste_Total (€)': coste_total
            })
    df_cartera = pd.DataFrame(posiciones_abiertas)

    # Identificar si queda algún bloqueo real (solo si el ticker está en cartera activa)
    if not df_cartera.empty and not df_ventas.empty:
        tickers_activos = df_cartera['Ticker'].unique()
        df_bloqueos_reales = df_ventas[(df_ventas['Perdida_Suspendida'] > 0) & (df_ventas['Ticker'].isin(tickers_activos))]
        if not df_bloqueos_reales.empty:
            bloqueos_df = df_bloqueos_reales.groupby('Ticker').agg({'Perdida_Suspendida': 'sum'}).reset_index()

    ruta_generada = exportar_a_markdown(
        resumen_anual,
        datos_declaracion_valor,
        datos_declaracion_broker,
        bloqueos_df,
        df_cartera,
        ruta_salida,
    ) if exportar else None
    anios_sin_escala = []
    if not resumen_anual.empty:
        anios_sin_escala = sorted(set(resumen_anual['Anio_Fiscal'].astype(int)) - set(TRAMOS_AHORRO_POR_ANIO))

    return {
        'df_operaciones': df_all,
        'df_ventas': df_ventas,
        'resumen_anual': resumen_anual,
        'datos_declaracion_valor': datos_declaracion_valor,
        'datos_declaracion_broker': datos_declaracion_broker,
        'bloqueos_df': bloqueos_df,
        'detalle_perdidas_pendientes': detalle_perdidas_pendientes,
        'df_cartera': df_cartera,
        'ruta_salida': ruta_generada,
        'conteos': {
            'IBKR': len(df_ibkr),
            'Revolut': len(df_revolut),
            'Total': len(df_all),
            'Operaciones_FX_BCE': operaciones_fx_bce,
        },
        'anios_sin_escala': anios_sin_escala,
    }


def _formatear_eur(valor):
    return f"{valor:,.2f} €"


def imprimir_resumen_consola(resultado):
    conteos = resultado['conteos']
    resumen_anual = resultado['resumen_anual']
    df_operaciones = resultado['df_operaciones']
    df_cartera = resultado['df_cartera']
    bloqueos_df = resultado['bloqueos_df']
    datos_declaracion_valor = resultado['datos_declaracion_valor']
    datos_declaracion_broker = resultado['datos_declaracion_broker']

    print("\nResumen de carga")
    print(f"- Operaciones IBKR: {conteos['IBKR']}")
    print(f"- Operaciones Revolut: {conteos['Revolut']}")
    print(f"- Total operaciones: {conteos['Total']}")

    if not df_operaciones.empty:
        print(f"- Rango de fechas en CSVs: {df_operaciones['TradeDate'].min().date()} a {df_operaciones['TradeDate'].max().date()}")

    if conteos['Operaciones_FX_BCE'] > 0:
        print(
            f"\nFX: {conteos['Operaciones_FX_BCE']} operaciones no EUR sin FX_Rate del broker "
            "se han convertido con tipos historicos oficiales del BCE."
        )

    if resultado['anios_sin_escala']:
        anios = ", ".join(str(anio) for anio in resultado['anios_sin_escala'])
        print(f"AVISO: no hay escala de ahorro configurada para {anios}; se usa la escala {ANIO_ESCALA_DEFECTO}.")

    print("\nResumen fiscal")
    if resumen_anual.empty:
        print("Sin ventas computables.")
    else:
        tabla = resumen_anual[
            [
                'Anio_Fiscal',
                'Resultado_Bruto',
                'Perdidas_Suspendidas',
                'Perdidas_Liberadas',
                'Rendimiento_Neto_Computable',
                'Perdidas_Pendientes_Aplicadas',
                'Base_Ahorro_Tras_Compensacion',
                'Perdida_Pendiente_Compensar_4Anios',
                'Impuesto_Estimado',
            ]
        ].copy()
        tabla['Periodo_Fiscal'] = tabla['Anio_Fiscal'].map(_periodo_fiscal)
        tabla.columns = [
            'Año',
            'Resultado bruto',
            'Pérdidas suspendidas',
            'Pérdidas liberadas',
            'Rendimiento año',
            'Pérdidas previas aplicadas',
            'Base tras compensación',
            'Pérdida pendiente 4 años',
            'Impuesto estimado',
            'Periodo fiscal',
        ]
        tabla = tabla[
            [
                'Año',
                'Periodo fiscal',
                'Resultado bruto',
                'Pérdidas suspendidas',
                'Pérdidas liberadas',
                'Rendimiento año',
                'Pérdidas previas aplicadas',
                'Base tras compensación',
                'Pérdida pendiente 4 años',
                'Impuesto estimado',
            ]
        ]
        for columna in tabla.columns[1:]:
            if columna != 'Periodo fiscal':
                tabla[columna] = tabla[columna].map(_formatear_eur)
        print(tabla.to_string(index=False))

    def imprimir_tabla_declaracion(titulo, datos, texto_vacio):
        print(f"\n{titulo}")
        if datos.empty:
            print(texto_vacio)
            return

        tabla_declaracion = datos[
            [
                'Anio_Fiscal',
                'Broker',
                'Concepto_0328',
                'Valor_Transmision',
                'Valor_Adquisicion',
                'Resultado_Computable',
            ]
        ].copy()
        for anio, grupo in tabla_declaracion.groupby('Anio_Fiscal', sort=True):
            tabla_anio = grupo[
                [
                    'Broker',
                    'Concepto_0328',
                    'Valor_Transmision',
                    'Valor_Adquisicion',
                    'Resultado_Computable',
                ]
            ].copy()
            tabla_anio.columns = [
                'Bróker',
                'Concepto (0328)',
                'Valor transmisión (0329)',
                'Valor adquisición (0330)',
                'Resultado computable',
            ]
            for columna in ['Valor transmisión (0329)', 'Valor adquisición (0330)', 'Resultado computable']:
                tabla_anio[columna] = tabla_anio[columna].map(_formatear_eur)
            print(f"\nAño {int(anio)} ({_periodo_fiscal(anio)})")
            print(tabla_anio.to_string(index=False))

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

    print("\nCartera abierta")
    print(f"- Posiciones abiertas: {len(df_cartera)}")
    print(f"- Tickers con pérdidas bloqueadas vigentes: {len(bloqueos_df)}")
    if df_cartera.empty:
        print("Sin posiciones abiertas.")
    else:
        tabla_cartera = df_cartera[
            [
                'Broker',
                'Ticker',
                'Acciones',
                'Precio_Medio (€)',
                'Coste_Total (€)',
            ]
        ].copy()
        tabla_cartera.columns = [
            'Bróker',
            'Ticker',
            'Acciones',
            'Precio medio',
            'Coste total',
        ]
        for columna in ['Precio medio', 'Coste total']:
            tabla_cartera[columna] = tabla_cartera[columna].map(_formatear_eur)
        print(tabla_cartera.to_string(index=False))

    if not bloqueos_df.empty:
        tabla_bloqueos = bloqueos_df.copy()
        tabla_bloqueos.columns = ['Ticker', 'Pérdida retenida']
        tabla_bloqueos['Pérdida retenida'] = tabla_bloqueos['Pérdida retenida'].map(_formatear_eur)
        print("\nPérdidas bloqueadas vigentes")
        print(tabla_bloqueos.to_string(index=False))


def _estilo_importe(valor):
    if valor > 0:
        return "green"
    if valor < 0:
        return "red"
    return "white"


def imprimir_resumen_rich(resultado):
    conteos = resultado['conteos']
    resumen_anual = resultado['resumen_anual']
    df_operaciones = resultado['df_operaciones']
    df_cartera = resultado['df_cartera']
    bloqueos_df = resultado['bloqueos_df']
    datos_declaracion_valor = resultado['datos_declaracion_valor']
    datos_declaracion_broker = resultado['datos_declaracion_broker']

    carga = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    carga.add_column("Dato", style="cyan")
    carga.add_column("Valor", style="white")
    carga.add_row("Operaciones IBKR", str(conteos['IBKR']))
    carga.add_row("Operaciones Revolut", str(conteos['Revolut']))
    carga.add_row("Total operaciones", str(conteos['Total']))
    if not df_operaciones.empty:
        carga.add_row(
            "Rango de fechas en CSVs",
            f"{df_operaciones['TradeDate'].min().date()} a {df_operaciones['TradeDate'].max().date()}",
        )
    carga.add_row("FX via BCE", str(conteos['Operaciones_FX_BCE']))
    console.print(Panel(carga, title="Carga de datos", border_style="cyan"))

    if conteos['Operaciones_FX_BCE'] > 0:
        console.print(
            Panel(
                f"{conteos['Operaciones_FX_BCE']} operaciones no EUR sin FX_Rate del broker "
                "se han convertido con tipos historicos oficiales del BCE.",
                title="Divisas",
                border_style="green",
            )
        )

    if resultado['anios_sin_escala']:
        anios = ", ".join(str(anio) for anio in resultado['anios_sin_escala'])
        console.print(
            Panel(
                f"No hay escala de ahorro configurada para {anios}; se usa la escala {ANIO_ESCALA_DEFECTO}.",
                title="Aviso fiscal",
                border_style="yellow",
            )
        )

    if resumen_anual.empty:
        console.print(Panel("Sin ventas computables.", title="Resumen fiscal", border_style="yellow"))
    else:
        tabla = Table(title="Resumen fiscal", box=box.ROUNDED, header_style="bold cyan")
        tabla.add_column("Año", justify="right")
        tabla.add_column("Periodo fiscal")
        tabla.add_column("Resultado bruto", justify="right")
        tabla.add_column("Pérdidas susp.", justify="right")
        tabla.add_column("Pérdidas lib.", justify="right")
        tabla.add_column("Rend. año", justify="right")
        tabla.add_column("Pérd. previas", justify="right")
        tabla.add_column("Base compensada", justify="right")
        tabla.add_column("Pendiente 4 años", justify="right")
        tabla.add_column("Impuesto est.", justify="right")
        for _, fila in resumen_anual.iterrows():
            resultado_bruto = float(fila['Resultado_Bruto'])
            rendimiento = float(fila['Rendimiento_Neto_Computable'])
            base_compensada = float(fila['Base_Ahorro_Tras_Compensacion'])
            tabla.add_row(
                str(int(fila['Anio_Fiscal'])),
                _periodo_fiscal(fila['Anio_Fiscal']),
                f"[{_estilo_importe(resultado_bruto)}]{_formatear_eur(resultado_bruto)}[/]",
                _formatear_eur(float(fila['Perdidas_Suspendidas'])),
                _formatear_eur(float(fila['Perdidas_Liberadas'])),
                f"[{_estilo_importe(rendimiento)}]{_formatear_eur(rendimiento)}[/]",
                _formatear_eur(float(fila['Perdidas_Pendientes_Aplicadas'])),
                f"[{_estilo_importe(base_compensada)}]{_formatear_eur(base_compensada)}[/]",
                _formatear_eur(float(fila['Perdida_Pendiente_Compensar_4Anios'])),
                _formatear_eur(float(fila['Impuesto_Estimado'])),
            )
        console.print(tabla)

    def imprimir_tabla_declaracion_rich(titulo, datos, texto_vacio):
        if datos.empty:
            console.print(Panel(texto_vacio, title=titulo, border_style="yellow"))
            return

        for anio, grupo in datos.groupby('Anio_Fiscal', sort=True):
            tabla_declaracion = Table(
                title=f"{titulo} - Año {int(anio)} ({_periodo_fiscal(anio)})",
                box=box.ROUNDED,
                header_style="bold cyan",
            )
            tabla_declaracion.add_column("Bróker")
            tabla_declaracion.add_column("Concepto (0328)")
            tabla_declaracion.add_column("Valor transmisión (0329)", justify="right")
            tabla_declaracion.add_column("Valor adquisición (0330)", justify="right")
            tabla_declaracion.add_column("Resultado computable", justify="right")
            for _, fila in grupo.iterrows():
                resultado_computable = float(fila['Resultado_Computable'])
                tabla_declaracion.add_row(
                    fila['Broker'],
                    fila['Concepto_0328'],
                    _formatear_eur(float(fila['Valor_Transmision'])),
                    _formatear_eur(float(fila['Valor_Adquisicion'])),
                    f"[{_estilo_importe(resultado_computable)}]{_formatear_eur(resultado_computable)}[/]",
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
                fila['Broker'],
                fila['Ticker'],
                str(fila['Acciones']),
                _formatear_eur(float(fila['Precio_Medio (€)'])),
                _formatear_eur(float(fila['Coste_Total (€)'])),
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
                fila['Ticker'],
                _formatear_eur(float(fila['Perdida_Suspendida'])),
            )
        console.print(tabla_bloqueos)


def _mostrar_cabecera():
    console.print()
    console.print(
        Panel.fit(
            "[bold white]IBKR a Hacienda[/]\n[cyan]Informe fiscal auxiliar para IBKR y Revolut[/]",
            border_style="cyan",
        )
    )


def _mostrar_menu(config):
    tabla = Table(box=box.ROUNDED, show_header=False, padding=(0, 1))
    tabla.add_column("Opcion", style="bold cyan", justify="right")
    tabla.add_column("Accion", style="white")
    tabla.add_row("1", "Generar informe Markdown")
    tabla.add_row("2", "Calcular y ver resumen sin exportar")
    tabla.add_row("3", "Actualizar tipos historicos del BCE")
    tabla.add_row("4", "Ver estado de datos y cache")
    tabla.add_row("5", "Cambiar rutas")
    tabla.add_row("6", "Ayuda rapida")
    tabla.add_row("0", "Salir")
    console.print(
        Panel(
            tabla,
            title=f"Menu principal | datos: {config['data_dir']} | salida: {config['output']}",
            border_style="blue",
        )
    )


def _pausa():
    Prompt.ask("\n[dim]Pulsa Enter para continuar[/]", default="")


def _preparar_fx_para_ui(config, actualizar=False):
    cache = Path(config['fx_cache'])
    if actualizar or not cache.exists():
        with console.status("[cyan]Descargando historico de divisas del BCE...[/]", spinner="dots"):
            asegurar_historico_bce(cache, actualizar=True)


def _ejecutar_calculo_ui(config, exportar=True, actualizar_fx=False):
    try:
        _preparar_fx_para_ui(config, actualizar=actualizar_fx)
        with console.status("[cyan]Calculando FIFO, divisas e informe fiscal...[/]", spinner="dots"):
            resultado = generar_informe_fiscal(
                directorio_datos=config['data_dir'],
                ruta_salida=config['output'],
                exportar=exportar,
                ruta_cache_bce=config['fx_cache'],
                actualizar_fx=False,
            )
    except Exception as exc:
        console.print(Panel(str(exc), title="Error", border_style="red"))
        return

    imprimir_resumen_rich(resultado)
    if resultado['ruta_salida'] is not None:
        console.print(f"[bold green]Informe guardado en:[/] {resultado['ruta_salida']}")


def _mostrar_estado_ui(config):
    data_dir = Path(config['data_dir'])
    fx_cache = Path(config['fx_cache'])

    tabla = Table(box=box.ROUNDED, header_style="bold cyan")
    tabla.add_column("Elemento")
    tabla.add_column("Estado")
    tabla.add_column("Detalle")

    if data_dir.exists():
        archivos_ibkr = list(data_dir.rglob("ibkr_trades.csv"))
        archivos_revolut = list(data_dir.rglob("revolut_trades.csv"))
        tabla.add_row("Datos", "[green]OK[/]", str(data_dir))
        tabla.add_row("CSVs IBKR", str(len(archivos_ibkr)), "ibkr_trades.csv")
        tabla.add_row("CSVs Revolut", str(len(archivos_revolut)), "revolut_trades.csv")
    else:
        tabla.add_row("Datos", "[red]No existe[/]", str(data_dir))

    if fx_cache.exists():
        modificado = pd.to_datetime(fx_cache.stat().st_mtime, unit="s").strftime("%Y-%m-%d %H:%M")
        tabla.add_row("Cache BCE", "[green]Descargado[/]", f"{fx_cache} ({modificado})")
    else:
        tabla.add_row("Cache BCE", "[yellow]No descargado[/]", f"Se descargara automaticamente en {fx_cache}")

    console.print(Panel(tabla, title="Estado", border_style="cyan"))


def _cambiar_rutas_ui(config):
    console.print(Panel("Deja el campo vacio para mantener el valor actual.", title="Rutas", border_style="cyan"))
    data_dir = Prompt.ask("Directorio de datos", default=str(config['data_dir']))
    output = Prompt.ask("Informe de salida", default=str(config['output']))
    fx_cache = Prompt.ask("Cache BCE", default=str(config['fx_cache']))
    config['data_dir'] = data_dir
    config['output'] = output
    config['fx_cache'] = fx_cache
    console.print("[green]Rutas actualizadas.[/]")


def _mostrar_ayuda_ui():
    texto = (
        "[bold]Flujo recomendado[/]\n"
        "1. Guarda los CSV como data/raw/<anio>/ibkr_trades.csv y data/raw/<anio>/revolut_trades.csv.\n"
        "2. Usa la opcion 4 para comprobar que la app los detecta.\n"
        "3. Usa la opcion 1 para generar informe_fiscal.md.\n\n"
        "[bold]Divisas[/]\n"
        "Si falta FX_Rate, la app descarga automaticamente el historico oficial del BCE.\n"
        "La opcion 3 fuerza una actualizacion manual del cache.\n\n"
        "[bold]Modo directo[/]\n"
        "python main.py --directo\n"
        "python main.py --no-exportar\n"
        "python main.py --actualizar-fx"
    )
    console.print(Panel(texto, title="Ayuda rapida", border_style="cyan"))


def ejecutar_app_interactiva(args):
    config = {
        'data_dir': args.data_dir,
        'output': args.output,
        'fx_cache': args.fx_cache,
    }

    while True:
        console.clear()
        _mostrar_cabecera()
        _mostrar_menu(config)
        opcion = Prompt.ask("Elige una opcion", choices=["1", "2", "3", "4", "5", "6", "0"], default="1")

        if opcion == "0":
            console.print("[cyan]Saliendo.[/]")
            return 0
        if opcion == "1":
            _ejecutar_calculo_ui(config, exportar=True)
            _pausa()
        elif opcion == "2":
            _ejecutar_calculo_ui(config, exportar=False)
            _pausa()
        elif opcion == "3":
            try:
                _preparar_fx_para_ui(config, actualizar=True)
                console.print(f"[green]Historico BCE actualizado:[/] {config['fx_cache']}")
            except Exception as exc:
                console.print(Panel(str(exc), title="Error actualizando FX", border_style="red"))
            _pausa()
        elif opcion == "4":
            _mostrar_estado_ui(config)
            _pausa()
        elif opcion == "5":
            _cambiar_rutas_ui(config)
            _pausa()
        elif opcion == "6":
            _mostrar_ayuda_ui()
            _pausa()


def construir_parser(settings=None):
    settings = settings or cargar_settings()
    parser = argparse.ArgumentParser(
        description="Genera un informe fiscal auxiliar de operaciones IBKR/Revolut para IRPF España."
    )
    parser.add_argument(
        "--data-dir",
        default=settings["data_dir"],
        help=f"Directorio raíz donde están los CSV por año. Por defecto: {settings['data_dir']}",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=settings["output"],
        help=f"Ruta del informe Markdown a generar. Por defecto: {settings['output']}",
    )
    parser.add_argument(
        "--no-exportar",
        action="store_true",
        help="Calcula y muestra el resumen sin escribir el informe Markdown.",
    )
    parser.add_argument(
        "--sin-resumen",
        action="store_true",
        help="No imprime el resumen por consola.",
    )
    parser.add_argument(
        "--fx-cache",
        default=settings["fx_cache"],
        help=f"Ruta del CSV cacheado del BCE. Por defecto: {settings['fx_cache']}",
    )
    parser.add_argument(
        "--actualizar-fx",
        action="store_true",
        help="Fuerza la descarga del historico de tipos del BCE antes de calcular.",
    )
    parser.add_argument(
        "--directo",
        action="store_true",
        help="Genera el informe directamente sin abrir el menu interactivo.",
    )
    parser.add_argument(
        "--menu",
        action="store_true",
        help="Abre el menu interactivo.",
    )
    return parser


def main(argv=None):
    argumentos = sys.argv[1:] if argv is None else argv
    settings = cargar_settings()
    parser = construir_parser(settings)
    args = parser.parse_args(argumentos)

    if args.menu or not argumentos:
        return ejecutar_app_interactiva(args)

    try:
        resultado = generar_informe_fiscal(
            directorio_datos=args.data_dir,
            ruta_salida=args.output,
            exportar=not args.no_exportar,
            ruta_cache_bce=args.fx_cache,
            actualizar_fx=args.actualizar_fx,
        )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if not args.sin_resumen:
        imprimir_resumen_consola(resultado)

    if resultado['ruta_salida'] is not None:
        print(f"\nInforme guardado en: {resultado['ruta_salida']}")

    return 0

if __name__ == '__main__':
    raise SystemExit(main())
