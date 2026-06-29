# Instalación y Uso

## Requisitos

- Python 3.12 o superior.
- Acceso a internet si necesitas descargar tipos históricos del BCE.

## Instalación

```bash
python -m venv .venv
```

Activar entorno en Windows PowerShell:

```bash
.\.venv\Scripts\Activate.ps1
```

Activar entorno en macOS/Linux:

```bash
source .venv/bin/activate
```

Instalar dependencias:

```bash
python -m pip install -r requirements.txt
```

## Comandos principales

Abrir menú interactivo:

```bash
python main.py
```

Generar el informe directamente:

```bash
python main.py --directo
```

Calcular y mostrar resumen sin escribir Markdown:

```bash
python main.py --no-exportar
```

Ejecutar sin resumen por consola:

```bash
python main.py --directo --sin-resumen
```

Actualizar tipos históricos del BCE:

```bash
python main.py --actualizar-fx
```

## Configuración

Las rutas por defecto se configuran en `src/config/settings.json`:

```json
{
  "data_dir": "data/raw",
  "output": "output/informe_fiscal.md",
  "fx_cache": "cache/eurofxref-hist.csv"
}
```

También puedes pasar rutas por CLI:

```bash
python main.py --directo --data-dir data/raw --output output/informe_fiscal.md --fx-cache data/cache/ecb/eurofxref-hist.csv
```

## Salida

La salida principal es `output/informe_fiscal.md`. Incluye:

- Resumen por ejercicio fiscal.
- Gráficos de control incrustados como PNG generados con `matplotlib`.
- Evolución mensual con sombreado verde sobre cero y rojo bajo cero.
- Acumulado mensual del resultado computable.
- Resumen anual por ejercicio, top valores por impacto fiscal y cartera abierta por coste.
- Datos para Renta Web por valor y por bróker.
- Detalle de pérdidas bloqueadas vigentes.
- Cartera abierta.

Los gráficos se guardan junto al informe:

```text
output/charts/resumen_anual.png
output/charts/evolucion_mensual.png
output/charts/acumulado_mensual.png
output/charts/top_valores.png
output/charts/cartera_abierta.png
```

La salida por consola y el menú interactivo se agrupan en secciones:

- Datos cargados.
- Resumen fiscal.
- Gráficos.
- Datos Hacienda.
- Cartera y bloqueos.
