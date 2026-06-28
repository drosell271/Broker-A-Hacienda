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
	"fx_cache": "cache/eurofxref-hist.csv"
}
```

## Estructura

```text
main.py              # entrada de consola
src/config/          # configuración
src/parsers/         # lectura de CSVs
src/services/        # divisas BCE, FIFO y cálculo fiscal
tests/               # pruebas de regresión del cálculo fiscal
data/raw/            # CSVs de entrada
output/              # informes generados
```

## Datos

El programa busca los archivos por nombre dentro de `data/raw`:

```text
data/raw/2025/ibkr_trades.csv
data/raw/2025/revolut_trades.csv
```

Puedes crear una carpeta por ejercicio y repetir el mismo nombre de archivo en cada una:

```text
data/raw/2024/ibkr_trades.csv
data/raw/2024/revolut_trades.csv
data/raw/2025/ibkr_trades.csv
data/raw/2025/revolut_trades.csv
```

### IBKR

En Client Portal:

1. Entra en `Performance & Reports > Flex Queries`.
2. Crea una `Trade Confirmation Flex Query` o una `Activity Flex Query`.
3. Elige formato `CSV`.
4. Añade la sección de operaciones/trades.
5. Incluye estas columnas:

```csv
Buy/Sell,AssetClass,Symbol,Quantity,TradePrice,CurrencyPrimary,IBCommission,IBCommissionCurrency,DateTime
```

6. Usa fechas con formato `yyyyMMdd`, hora `HHmmss` y separador `;` para que `DateTime` quede como `20250131;153000`.
7. Ejecuta la consulta para el año fiscal (01-01-20XX a 31-12-20XX).
8. Guarda el archivo como:

```text
data/raw/<año>/ibkr_trades.csv
```

La columna `FX_Rate` es opcional. Si no está, el programa usa el histórico del BCE.

### Revolut

En la app de Revolut:

1. Abre `Invest`.
2. Entra en `More` / `Más`.
3. Entra en `Documents`.
4. Selecciona `Stocks`.
5. Descarga el `Account statement` para el año fiscal (01-01-20XX a 31-12-20XX).
6. Si Revolut lo entrega en Excel, ábrelo y guárdalo como CSV.
7. El CSV final debe llamarse:

```text
data/raw/<año>/revolut_trades.csv
```

Columnas esperadas:

```csv
Date,Ticker,Type,Quantity,Price per share,Total Amount,Currency,FX Rate
```

Si una operación no trae `FX_Rate`, se usa el histórico oficial del BCE cacheado en `data/cache/ecb/eurofxref-hist.csv`.

## Renta Web

Para acciones cotizadas, usa el apartado:

```text
Ganancias y pérdidas patrimoniales derivadas de transmisiones de acciones admitidas a negociación en mercados oficiales
```

En Renta 2025 / Modelo 100, ese bloque aparece dentro de F2 y usa estas casillas principales:

- `0328`: denominación del valor transmitido. Usa el ticker o nombre del valor.
- `0329`: importe global de las transmisiones. Copia aquí `Valor Transmisión`.
- `0330`: valor de adquisición global. Copia aquí `Valor Adquisición`.
- `0339`: suma de ganancias patrimoniales derivadas de transmisiones de acciones negociadas.
- `0340`: suma de pérdidas patrimoniales derivadas de transmisiones de acciones negociadas.

El informe deja dos formas de preparar esos datos:

Cada ejercicio se calcula como año natural completo

El informe muestra `Periodo fiscal considerado` en el resumen anual y agrupa las tablas de Renta Web por año. La fecha de venta se usa internamente para asignar cada operación al ejercicio fiscal. Las compras anteriores pueden seguir afectando al coste por FIFO.

### Modo por valor

Usa la sección `Datos para Renta Web - Modo por Valor` si vas a introducir una ficha por cada valor/ticker:

- `Concepto (0328)` -> ticker o nombre del valor.
- `Valor Transmisión (0329)` -> importe global de transmisiones.
- `Valor Adquisición (0330)` -> valor de adquisición global.
- `Resultado Computable` -> comprobación después de pérdidas suspendidas o liberadas.

### Modo por bróker

Usa la sección `Datos para Renta Web - Modo por Bróker` si vas a meter una sola ficha por bróker englobando todos sus valores:

- `Concepto (0328)` -> bróker, por ejemplo `IBKR - todos los valores`.
- `Valor Transmisión (0329)` -> suma de transmisiones de ese bróker.
- `Valor Adquisición (0330)` -> suma de adquisiciones de ese bróker.
- `Resultado Computable` -> comprobación agregada del bróker.

Si una fila tiene `Pérdidas Suspendidas`, revisa esa operación en Renta Web: AEAT indica que la pérdida se declara y se cuantifica, pero no se integra hasta que proceda. La compensación de pérdidas pendientes de ejercicios anteriores se revisa en el resumen anual del informe, no en una línea separada por bróker.

Las casillas pueden cambiar entre campañas. Comprueba el nombre del apartado si declaras un ejercicio distinto de 2025.

## Cálculo

1. Carga operaciones de IBKR y Revolut.
2. Normaliza columnas.
3. Convierte precios y comisiones a EUR.
4. Aplica FIFO por bróker y ticker.
5. Aplica detección básica de recompras en la ventana de dos meses.
6. Agrupa por año fiscal usando la fecha de venta.
7. Aplica pérdidas pendientes contra bases positivas posteriores.
8. Muestra el periodo fiscal completo de cada ejercicio.
9. Agrupa las tablas de Renta Web por año y en dos modos: por valor y por bróker.
10. Muestra cartera abierta y pérdidas bloqueadas vigentes.
11. Genera `output/informe_fiscal.md`.

La compensación de pérdidas pendientes de la base del ahorro sigue el plazo de cuatro ejercicios indicado por AEAT.

### Regla de los dos meses

La regla se aplica sobre ventas con pérdida. El programa marca una pérdida como `Perdida_Suspendida` si detecta compras del mismo ticker dentro de la ventana de riesgo de 60 días antes o después de la venta, según la lógica básica implementada.

La suspensión se prorratea por acciones. Si vendes 100 acciones con una pérdida de 1.000 € y sólo hay 40 acciones recompradas o mantenidas que bloquean la pérdida, el informe suspende 400 €, no los 1.000 € completos.

La pérdida suspendida queda asociada a los lotes FIFO de compra que provocan el bloqueo. Cuando esos lotes se venden después, el programa marca `Perdida_Liberada` de forma proporcional a las acciones transmitidas. Si sólo se vende parte de la recompra, sólo se libera esa parte de la pérdida. Si al cierre del histórico quedan acciones bloqueantes abiertas, la pérdida pendiente neta aparece en `Detalle de Bloqueos Vigentes en Cartera Activa`.

Por eso `Pérdidas Suspendidas` y `Pérdidas Liberadas` no tienen por qué coincidir en un mismo año. También pueden coincidir dentro del mismo ejercicio si las acciones recompradas se transmiten posteriormente durante ese mismo año.

## Pruebas

Ejecutar las pruebas de regresión:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

## Referencias

- AEAT, acciones admitidas a negociación: https://sede.agenciatributaria.gob.es/Sede/Ayuda/25Presentacion/100/7_6_6_2/ganancias_perdidas_patrimoniales_derivadas_acciones.html
- Hacienda, Modelo 100 Renta 2025: https://www.hacienda.gob.es/sgt/normativadoctrina/proyectos/26012026-anexo-i-y-ii-renta-2025.pdf
- AEAT, integración y compensación de rentas: https://sede.agenciatributaria.gob.es/Sede/ayuda/manuales-videos-folletos/manuales-practicos/irpf-2025/c12-integracion-compensacion-rentas/reglas-integracion-compensacion-rentas/integracion-compensacion-rentas-base-imponible-ahorro.html
- IBKR, Flex Queries: https://www.ibkrguides.com/orgportal/performanceandstatements/flex.htm
- IBKR, crear Activity Flex Query: https://www.ibkrguides.com/orgportal/performanceandstatements/activityflex.htm
- Revolut, statements de inversión: https://help.revolut.com/help/profile-and-plan/managing-my-account/trading-statements-and-reports/
- Revolut, consolidated statement: https://help.revolut.com/help/profile-and-plan/more-help-with-my-account/tax-declaration/question-what-is-the-consolidated-statement/

## Limitaciones

- FIFO por `(bróker, ticker)`, no consolidado entre brokers.
- Detección básica de recompras con prorrateo por acciones y liberación por venta posterior de los lotes bloqueantes según el histórico cargado.
- No incluye dividendos, intereses, retenciones, fondos, ETFs, opciones, criptomonedas ni divisas como activo independiente.
- Las pérdidas pendientes solo incluyen lo que aparece en los CSV cargados.

## Disclaimer

Este proyecto prepara un informe de apoyo a partir de los CSV cargados. No sustituye la revisión fiscal ni garantiza que todos los casos particulares estén cubiertos.

## Licencia

MIT. Ver `LICENSE`.
