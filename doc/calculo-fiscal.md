# Cálculo Fiscal

## Flujo de cálculo

1. Carga operaciones de IBKR y Revolut.
2. Normaliza columnas comunes.
3. Convierte precios y comisiones a EUR.
4. Aplica FIFO por `(bróker, ticker)`.
5. Detecta recompras dentro de dos meses naturales.
6. Agrupa por año fiscal usando la fecha de venta.
7. Integra capital mobiliario anual si existe `rendimientos_capital.csv`.
8. Aplica pérdidas pendientes de hasta cuatro ejercicios y compensación cruzada del 25%.
9. Calcula una estimación de impuesto de la base del ahorro.
10. Genera tablas para Renta Web y gráficos de control.

## Valores de adquisición y transmisión

Para compras, la comisión aumenta el coste de adquisición.

Para ventas, la comisión reduce el valor de transmisión.

Los importes no EUR se convierten:

- Con `FX_Rate` del bróker si viene informado.
- Con histórico oficial del BCE si falta `FX_Rate`.

## FIFO

El FIFO está implementado por `(bróker, ticker)`. Esta es una limitación conocida: no consolida valores homogéneos entre brókers.

Si falta una compra previa para valorar una venta, el cálculo se detiene. Esto evita que una venta desaparezca del informe.

## Regla de los dos meses

La regla se aplica sobre ventas con pérdida. El programa marca `Perdida_Suspendida` si detecta compras del mismo ticker dentro de los dos meses naturales anteriores o posteriores a la venta.

La suspensión se prorratea por acciones. Si vendes 100 acciones con una pérdida de 1.000 € y sólo hay 40 acciones recompradas o mantenidas que bloquean la pérdida, el informe suspende 400 €.

La pérdida suspendida queda asociada a los lotes FIFO de compra que provocan el bloqueo. Cuando esos lotes se venden después, el programa marca `Perdida_Liberada` proporcionalmente a las acciones transmitidas.

## Compensación de pérdidas

El resumen anual calcula:

- `Rendimiento_Neto_Computable`: resultado de acciones después de pérdidas suspendidas y liberadas.
- `Rendimiento_Capital_Mobiliario`: saldo anual opcional cargado desde `rendimientos_capital.csv`.
- `Perdidas_Pendientes_Aplicadas`: pérdidas patrimoniales de ejercicios anteriores aplicadas contra ganancias patrimoniales.
- `Rendimientos_Negativos_Pendientes_Aplicados`: rendimientos negativos de capital mobiliario aplicados contra rendimientos positivos posteriores.
- `Compensacion_25pct_Aplicada`: compensación cruzada entre los dos compartimentos de la base del ahorro.
- `Base_Ahorro_Tras_Compensacion`: base positiva estimada después de compensaciones.

## Escala del ahorro

La estimación de impuesto usa las escalas configuradas en `src/services/tax.py`.

Hay escala específica para 2024, 2025 y 2026. Si aparece un ejercicio no configurado, se usa la escala por defecto de 2025 y la consola muestra aviso.

## Renta Web

Para acciones cotizadas, el informe usa el apartado:

```text
Ganancias y pérdidas patrimoniales derivadas de transmisiones de acciones admitidas a negociación en mercados oficiales
```

En Renta 2025 / Modelo 100, las casillas principales son:

- `0328`: denominación del valor transmitido.
- `0329`: valor de transmisión.
- `0330`: valor de adquisición.
- `0339`: ganancias patrimoniales de acciones negociadas.
- `0340`: pérdidas patrimoniales de acciones negociadas.

Las casillas pueden cambiar entre campañas. Comprueba el nombre del apartado si declaras un ejercicio distinto de 2025.
