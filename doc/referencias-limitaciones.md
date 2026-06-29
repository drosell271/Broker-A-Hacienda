# Referencias y Limitaciones

## Referencias

- AEAT, acciones admitidas a negociación: https://sede.agenciatributaria.gob.es/Sede/Ayuda/25Presentacion/100/7_6_6_2/ganancias_perdidas_patrimoniales_derivadas_acciones.html
- Hacienda, Modelo 100 Renta 2025: https://www.hacienda.gob.es/sgt/normativadoctrina/proyectos/26012026-anexo-i-y-ii-renta-2025.pdf
- AEAT, integración y compensación de rentas: https://sede.agenciatributaria.gob.es/Sede/ayuda/manuales-videos-folletos/manuales-practicos/irpf-2025/c12-integracion-compensacion-rentas/reglas-integracion-compensacion-rentas/integracion-compensacion-rentas-base-imponible-ahorro.html
- IBKR, Flex Queries: https://www.ibkrguides.com/orgportal/performanceandstatements/flex.htm
- IBKR, crear Activity Flex Query: https://www.ibkrguides.com/orgportal/performanceandstatements/activityflex.htm
- Revolut, statements de inversión: https://help.revolut.com/help/profile-and-plan/managing-my-account/trading-statements-and-reports/
- Revolut, consolidated statement: https://help.revolut.com/help/profile-and-plan/more-help-with-my-account/tax-declaration/question-what-is-the-consolidated-statement/

## Limitaciones fiscales

- FIFO por `(bróker, ticker)`, no consolidado entre brókers.
- Identificación por ticker, no por ISIN ni por definición completa de valores homogéneos.
- Detección básica de recompras con prorrateo por acciones y liberación por venta posterior de los lotes bloqueantes.
- No calcula dividendos, intereses ni retenciones operación por operación. Sólo puede integrar un saldo anual de capital mobiliario mediante `rendimientos_capital.csv`.
- No incluye fondos, ETFs, opciones, criptomonedas ni divisas como activo independiente.
- Las pérdidas pendientes sólo incluyen lo que aparece en los CSV cargados.
- No contempla eventos corporativos complejos como splits, contrasplits, fusiones, spin-offs o cambios de ticker.

## Limitaciones operativas

- El informe depende de que el histórico de compras cargado sea suficiente para valorar ventas por FIFO.
- Si falta una compra previa, el cálculo se detiene.
- Las casillas de Renta Web pueden cambiar entre campañas.

## Aviso

Este proyecto prepara un informe de apoyo a partir de los CSV cargados. No sustituye la revisión fiscal ni garantiza que todos los casos particulares estén cubiertos.
