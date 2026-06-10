# IBKR a Hacienda

App de consola para preparar un informe fiscal de operaciones de acciones de IBKR y Revolut para IRPF España.

Lee los CSV de ambos brokers, convierte importes a EUR con tipos del BCE, aplica FIFO, calcula resultados por año y genera un informe Markdown.

## Instalación

Requisitos: Python 3.12 o superior.

```bash
python -m venv .venv
```

Activar entorno:

```bash
# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# macOS/Linux
source .venv/bin/activate
```

Instalar dependencias:

```bash
python -m pip install -r requirements.txt
```

## Uso

Abrir menú:

```bash
python main.py
```

Generar informe directamente:

```bash
python main.py --directo
```

Calcular sin exportar:

```bash
python main.py --no-exportar
```

Actualizar tipos de cambio del BCE:

```bash
python main.py --actualizar-fx
```

## Configuración

Las rutas se configuran en `src/config/settings.json`:

```json
{
  "data_dir": "data/raw",
  "output": "output/informe_fiscal.md",
  "fx_cache": "data/cache/ecb/eurofxref-hist.csv"
}
```

## Estructura

```text
main.py              # entrada de consola
src/config/          # configuración
src/parsers/         # lectura de CSVs
src/services/        # divisas BCE, FIFO y cálculo fiscal
data/raw/            # CSVs de entrada
output/              # informes generados
```

## Datos

El programa busca los archivos por nombre dentro de `data/raw`:

```text
data/raw/2025/ibkr_trades.csv
data/raw/2025/revolut_trades.csv
```

Columnas esperadas para IBKR:

```csv
Buy/Sell,AssetClass,Symbol,Quantity,TradePrice,CurrencyPrimary,IBCommission,IBCommissionCurrency,DateTime
```

Columnas esperadas para Revolut:

```csv
Date,Ticker,Type,Quantity,Price per share,Total Amount,Currency,FX Rate
```

Si una operación no trae `FX_Rate`, se usa el histórico oficial del BCE cacheado en `data/cache/ecb/eurofxref-hist.csv`.

## Cálculo

1. Carga operaciones de IBKR y Revolut.
2. Normaliza columnas.
3. Convierte precios y comisiones a EUR.
4. Aplica FIFO por bróker y ticker.
5. Aplica detección básica de recompras en la ventana de dos meses.
6. Agrupa por año fiscal.
7. Aplica pérdidas pendientes contra bases positivas posteriores.
8. Genera `output/informe_fiscal.md`.

La compensación de pérdidas pendientes de la base del ahorro sigue el plazo de cuatro ejercicios indicado por AEAT.

Referencia AEAT: https://sede.agenciatributaria.gob.es/Sede/ayuda/manuales-videos-folletos/manuales-practicos/irpf-2025/c12-integracion-compensacion-rentas/reglas-integracion-compensacion-rentas/integracion-compensacion-rentas-base-imponible-ahorro.html

## Limitaciones

- FIFO por `(bróker, ticker)`, no consolidado entre brokers.
- Detección básica de recompras.
- No incluye dividendos, intereses, retenciones, fondos, ETFs, opciones, criptomonedas ni divisas como activo independiente.
- Las pérdidas pendientes solo incluyen lo que aparece en los CSV cargados.

## Licencia

MIT. Ver `LICENSE`.
