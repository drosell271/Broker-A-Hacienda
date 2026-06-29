# Arquitectura del Código

El código está organizado para que `main.py` sea sólo el punto de entrada y la lógica viva en módulos pequeños.

## Entrada y CLI

```text
main.py
src/cli.py
```

- `main.py`: wrapper mínimo que llama a `src.cli.main`.
- `src/cli.py`: define argumentos, decide entre menú interactivo y ejecución directa, y gestiona errores de CLI.

## Configuración

```text
src/config/settings.py
src/config/settings.json
```

- Carga rutas por defecto.
- Permite mantener configuración local sencilla.

## Parsers

```text
src/parsers/ibkr.py
src/parsers/revolut.py
src/parsers/capital.py
```

- `ibkr.py`: normaliza CSVs de operaciones de IBKR.
- `revolut.py`: normaliza CSVs de operaciones de Revolut.
- `capital.py`: carga saldos anuales opcionales de capital mobiliario.

## Servicios

```text
src/services/forex.py
src/services/fifo_engine.py
src/services/tax.py
src/services/fiscal_report.py
```

- `forex.py`: descarga/cachea tipos del BCE y convierte precios/comisiones a EUR.
- `fifo_engine.py`: procesa compras/ventas FIFO y regla básica de recompra.
- `tax.py`: escala del ahorro y compensación de pérdidas pendientes.
- `fiscal_report.py`: orquesta el cálculo completo y devuelve los DataFrames finales.

## Reporting

```text
src/reporting/charts.py
src/reporting/markdown.py
```

- `charts.py`: prepara datasets, barras de consola e imágenes PNG con `matplotlib` para los gráficos del informe.
- `markdown.py`: escribe el informe final `output/informe_fiscal.md` e incrusta los PNG de `output/charts/`.

## UI

```text
src/ui/console.py
src/ui/interactive.py
```

- `console.py`: tablas Rich, gráficos en consola, salida plana y separación visual por secciones.
- `interactive.py`: menú, estado de datos, cambio de rutas y actualización de FX.

## Tests

```text
tests/test_fifo_regla_dos_meses.py
```

Incluye pruebas de:

- Regla de dos meses.
- Liberación proporcional de pérdidas suspendidas.
- Error por histórico insuficiente.
- Compensación del 25% en la base del ahorro.
