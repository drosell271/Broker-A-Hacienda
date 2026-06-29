# IBKR a Hacienda

App de consola para preparar un informe fiscal auxiliar de operaciones de acciones de IBKR y Revolut para IRPF España.

Lee CSVs de brokers, convierte importes a EUR, aplica FIFO, regla básica de recompra de dos meses, compensación de pérdidas de la base del ahorro y genera `output/informe_fiscal.md` con tablas y gráficos PNG de control.

## Uso rápido

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py --directo
```

Abrir menú interactivo:

```bash
python main.py
```

Calcular sin exportar:

```bash
python main.py --no-exportar
```

Actualizar tipos de cambio del BCE:

```bash
python main.py --actualizar-fx
```

## Estructura

```text
main.py                    # wrapper de entrada
src/cli.py                 # argumentos y modo directo
src/parsers/               # lectura de CSVs de brokers y capital mobiliario
src/services/              # FIFO, divisas, cálculo fiscal y orquestación
src/reporting/             # informe Markdown y gráficos
src/ui/                    # consola Rich y menú interactivo
src/utils/                 # formato y utilidades compartidas
doc/                       # documentación extendida
tests/                     # pruebas de regresión
```

## Documentación

- [Instalación y uso](doc/instalacion-y-uso.md)
- [Datos de entrada](doc/datos-entrada.md)
- [Cálculo fiscal](doc/calculo-fiscal.md)
- [Arquitectura del código](doc/arquitectura.md)
- [Referencias y limitaciones](doc/referencias-limitaciones.md)

## Aviso

Este proyecto prepara un informe de apoyo a partir de los CSV cargados. No sustituye la revisión fiscal ni garantiza que todos los casos particulares estén cubiertos.
