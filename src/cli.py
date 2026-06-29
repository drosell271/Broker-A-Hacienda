import argparse
import sys

from src.config.settings import cargar_settings
from src.services.fiscal_report import generar_informe_fiscal
from src.ui.console import imprimir_resumen_consola
from src.ui.interactive import ejecutar_app_interactiva


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

    if resultado["ruta_salida"] is not None:
        print(f"\nInforme guardado en: {resultado['ruta_salida']}")

    return 0
