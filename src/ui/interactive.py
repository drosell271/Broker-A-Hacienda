from pathlib import Path

import pandas as pd
from rich import box
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from src.services.fiscal_report import generar_informe_fiscal
from src.services.forex import asegurar_historico_bce
from src.ui.console import console, imprimir_resumen_rich


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
    cache = Path(config["fx_cache"])
    if actualizar or not cache.exists():
        with console.status("[cyan]Descargando historico de divisas del BCE...[/]", spinner="dots"):
            asegurar_historico_bce(cache, actualizar=True)


def _ejecutar_calculo_ui(config, exportar=True, actualizar_fx=False):
    try:
        _preparar_fx_para_ui(config, actualizar=actualizar_fx)
        with console.status("[cyan]Calculando FIFO, divisas e informe fiscal...[/]", spinner="dots"):
            resultado = generar_informe_fiscal(
                directorio_datos=config["data_dir"],
                ruta_salida=config["output"],
                exportar=exportar,
                ruta_cache_bce=config["fx_cache"],
                actualizar_fx=False,
            )
    except Exception as exc:
        console.print(Panel(str(exc), title="Error", border_style="red"))
        return

    imprimir_resumen_rich(resultado)
    if resultado["ruta_salida"] is not None:
        console.print(f"[bold green]Informe guardado en:[/] {resultado['ruta_salida']}")


def _mostrar_estado_ui(config):
    data_dir = Path(config["data_dir"])
    fx_cache = Path(config["fx_cache"])

    tabla = Table(box=box.ROUNDED, header_style="bold cyan")
    tabla.add_column("Elemento")
    tabla.add_column("Estado")
    tabla.add_column("Detalle")

    if data_dir.exists():
        archivos_ibkr = list(data_dir.rglob("ibkr_trades.csv"))
        archivos_revolut = list(data_dir.rglob("revolut_trades.csv"))
        archivos_rendimientos = list(data_dir.rglob("rendimientos_capital.csv"))
        tabla.add_row("Datos", "[green]OK[/]", str(data_dir))
        tabla.add_row("CSVs IBKR", str(len(archivos_ibkr)), "ibkr_trades.csv")
        tabla.add_row("CSVs Revolut", str(len(archivos_revolut)), "revolut_trades.csv")
        tabla.add_row("CSVs capital mobiliario", str(len(archivos_rendimientos)), "rendimientos_capital.csv")
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
    data_dir = Prompt.ask("Directorio de datos", default=str(config["data_dir"]))
    output = Prompt.ask("Informe de salida", default=str(config["output"]))
    fx_cache = Prompt.ask("Cache BCE", default=str(config["fx_cache"]))
    config["data_dir"] = data_dir
    config["output"] = output
    config["fx_cache"] = fx_cache
    console.print("[green]Rutas actualizadas.[/]")


def _mostrar_ayuda_ui():
    texto = (
        "[bold]Flujo recomendado[/]\n"
        "1. Guarda los CSV como data/raw/<anio>/ibkr_trades.csv y data/raw/<anio>/revolut_trades.csv.\n"
        "   Incluye tambien compras historicas necesarias para valorar ventas por FIFO.\n"
        "2. Usa la opcion 4 para comprobar que la app los detecta.\n"
        "3. Usa la opcion 1 para generar informe_fiscal.md.\n\n"
        "[bold]Capital mobiliario[/]\n"
        "Opcional: anade data/raw/<anio>/rendimientos_capital.csv con Anio_Fiscal,Rendimiento_Capital_Mobiliario.\n\n"
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
        "data_dir": args.data_dir,
        "output": args.output,
        "fx_cache": args.fx_cache,
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
