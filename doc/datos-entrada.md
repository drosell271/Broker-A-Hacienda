# Datos de Entrada

El programa busca archivos por nombre dentro de `data/raw`. Puedes crear una carpeta por ejercicio:

```text
data/raw/2025/ibkr_trades.csv
data/raw/2025/revolut_trades.csv
data/raw/2025/rendimientos_capital.csv
```

También puedes cargar varios ejercicios:

```text
data/raw/2024/ibkr_trades.csv
data/raw/2025/ibkr_trades.csv
data/raw/2026/ibkr_trades.csv
```

## Histórico necesario

El cálculo FIFO necesita compras previas suficientes para cada venta. Si una venta no tiene stock cargado, el programa detiene el cálculo con un error explícito en vez de ignorarla.

Para declarar un ejercicio concreto, carga también las compras históricas anteriores que sigan afectando al coste fiscal de ventas del ejercicio.

## IBKR

En Client Portal:

1. Entra en `Performance & Reports > Flex Queries`.
2. Crea una `Trade Confirmation Flex Query` o una `Activity Flex Query`.
3. Elige formato `CSV`.
4. Añade la sección de operaciones/trades.
5. Incluye estas columnas:

```csv
Buy/Sell,AssetClass,Symbol,Quantity,TradePrice,CurrencyPrimary,IBCommission,IBCommissionCurrency,DateTime
```

Usa fechas con formato `yyyyMMdd`, hora `HHmmss` y separador `;` para que `DateTime` quede como `20250131;153000`.

Guarda el archivo como:

```text
data/raw/<año>/ibkr_trades.csv
```

La columna `FX_Rate` es opcional. Si no está, se usa el histórico oficial del BCE.

## Revolut

En la app de Revolut:

1. Abre `Invest`.
2. Entra en `More` / `Más`.
3. Entra en `Documents`.
4. Selecciona `Stocks`.
5. Descarga el `Account statement`.
6. Si Revolut lo entrega en Excel, guárdalo como CSV.

Columnas esperadas:

```csv
Date,Ticker,Type,Quantity,Price per share,Total Amount,Currency,FX Rate
```

Guarda el archivo como:

```text
data/raw/<año>/revolut_trades.csv
```

Si una operación no trae `FX_Rate`, se usa el histórico oficial del BCE.

## Capital mobiliario opcional

Para integrar un saldo anual de capital mobiliario en la base del ahorro, añade `rendimientos_capital.csv` en cualquier carpeta dentro de `data/raw`.

Formato recomendado:

```csv
Anio_Fiscal,Rendimiento_Capital_Mobiliario
2025,350.25
2026,-80.00
```

El importe debe ser el saldo neto anual que quieras integrar. El programa no calcula dividendos, intereses ni retenciones operación por operación; sólo usa este saldo anual opcional para aplicar compensación del 25% y pérdidas pendientes.
