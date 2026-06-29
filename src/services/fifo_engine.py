import pandas as pd
from collections import deque

PRECISION = 8 


class DatosInsuficientesError(ValueError):
    """Se lanza cuando faltan compras para valorar una venta por FIFO."""


def _procesar_compra(cartera, registro_compras, broker, ticker, fecha, cantidad, precio_eur, comision_eur):
    clave = (broker, ticker)
    coste_total = (cantidad * precio_eur) + comision_eur
    coste_unitario = coste_total / cantidad if cantidad > 0 else 0
    lote_id = len(registro_compras)
    
    if clave not in cartera:
        cartera[clave] = deque()
        
    cartera[clave].append({
        'fecha': fecha, 
        'cantidad': cantidad, 
        'coste_unitario': coste_unitario,
        'lote_id': lote_id
    })
    
    registro_compras.append({
        'Broker': broker,
        'Ticker': ticker,
        'Fecha_Compra': fecha,
        'Cantidad_Comprada': cantidad,
        'Lote_Compra_ID': lote_id
    })

def _procesar_venta(cartera, ventas_realizadas, broker, ticker, fecha, cantidad_a_vender, precio_eur, comision_eur):
    clave = (broker, ticker)
    ingreso_total_neto_eur = (cantidad_a_vender * precio_eur) - comision_eur
    ingreso_unitario_neto = ingreso_total_neto_eur / cantidad_a_vender if cantidad_a_vender > 0 else 0

    cantidad_disponible = 0.0
    if clave in cartera:
        cantidad_disponible = round(sum(lote['cantidad'] for lote in cartera[clave]), PRECISION)

    if round(cantidad_disponible - cantidad_a_vender, PRECISION) < 0:
        cantidad_faltante = round(cantidad_a_vender - cantidad_disponible, PRECISION)
        raise DatosInsuficientesError(
            "Faltan compras previas para valorar una venta por FIFO: "
            f"{broker} {ticker}, fecha {fecha}, venta {cantidad_a_vender}, "
            f"disponible {cantidad_disponible}, faltante {cantidad_faltante}. "
            "Carga tambien las compras historicas anteriores al ejercicio o una posicion inicial con coste fiscal."
        )
        
    while round(cantidad_a_vender, PRECISION) > 0 and len(cartera[clave]) > 0:
        lote_mas_antiguo = cartera[clave][0]
        cant_lote = round(lote_mas_antiguo['cantidad'], PRECISION)
        
        if cant_lote <= round(cantidad_a_vender, PRECISION):
            cant_procesada = cant_lote
            cartera[clave].popleft() 
        else:
            cant_procesada = round(cantidad_a_vender, PRECISION)
            lote_mas_antiguo['cantidad'] = round(cant_lote - cant_procesada, PRECISION)
            
        cantidad_a_vender = round(cantidad_a_vender - cant_procesada, PRECISION)
        
        val_adquisicion = cant_procesada * lote_mas_antiguo['coste_unitario']
        val_transmision = cant_procesada * ingreso_unitario_neto
        resultado_neto = val_transmision - val_adquisicion
        
        ventas_realizadas.append({
            'Broker': broker, 
            'Ticker': ticker, 
            'Fecha_Venta': fecha,
            'Cantidad_Vendida': cant_procesada,
            'Fecha_Compra': lote_mas_antiguo['fecha'],
            'Lote_Compra_ID': lote_mas_antiguo['lote_id'],
            'Valor_Adquisicion': val_adquisicion, 
            'Valor_Transmision': val_transmision,
            'Resultado': resultado_neto, 
            'Perdida_Suspendida': 0.0,
            'Perdida_Liberada': 0.0
        })


def _cantidad_vendida_de_lote_hasta_fecha(df_ventas, lote_id, fecha):
    ventas_lote = df_ventas[
        (df_ventas['Lote_Compra_ID'] == lote_id) &
        (df_ventas['Fecha_Venta'] <= fecha)
    ]
    if ventas_lote.empty:
        return 0.0
    return float(ventas_lote['Cantidad_Vendida'].sum())


def _aplicar_regla_dos_meses_basica(df_ventas, df_todas_operaciones):
    compras_reales = df_todas_operaciones[df_todas_operaciones['Buy/Sell'] == 'BUY'].copy()

    for idx, venta in df_ventas.iterrows():
        if venta['Resultado'] >= -0.01:
            continue

        t_ticker = venta['Ticker']
        f_venta = venta['Fecha_Venta']
        cant_vendida = float(venta['Cantidad_Vendida'])
        if cant_vendida <= 0:
            continue

        fecha_limite_atras = f_venta - pd.DateOffset(months=2)
        fecha_limite_adelante = f_venta + pd.DateOffset(months=2)
        compras_en_ventana = compras_reales[
            (compras_reales['Symbol'] == t_ticker) &
            (compras_reales['TradeDate'] >= fecha_limite_atras) &
            (compras_reales['TradeDate'] <= fecha_limite_adelante)
        ]

        compras_posteriores = compras_en_ventana[compras_en_ventana['TradeDate'] > f_venta]
        cantidad_bloqueada = min(cant_vendida, float(compras_posteriores['Quantity'].abs().sum()))
        if cantidad_bloqueada <= 0:
            cantidad_bloqueada = min(
                cant_vendida,
                max(0.0, float(compras_en_ventana['Quantity'].abs().sum()) - cant_vendida)
            )

        if cantidad_bloqueada > 0:
            perdida_unitaria = abs(float(venta['Resultado'])) / cant_vendida
            df_ventas.at[idx, 'Perdida_Suspendida'] = cantidad_bloqueada * perdida_unitaria

    return df_ventas


def _aplicar_regla_dos_meses(df_ventas, df_todas_operaciones, cartera=None, df_compras=None):
    """
    Aplica la regla de los 2 meses con prorrateo por acciones.
    La pérdida se suspende sólo por las acciones recompradas o mantenidas
    en la ventana, y se libera proporcionalmente cuando se venden esos lotes.
    """
    if df_ventas.empty:
        return df_ventas

    df_ventas = df_ventas.copy()
    df_ventas['Perdida_Suspendida'] = 0.0
    df_ventas['Perdida_Liberada'] = 0.0

    columnas_lotes = {'Lote_Compra_ID', 'Fecha_Compra'}
    if df_compras is None or not columnas_lotes.issubset(df_ventas.columns):
        return _aplicar_regla_dos_meses_basica(df_ventas, df_todas_operaciones)

    df_compras = df_compras.copy()
    bloqueos = []
    cantidad_asignada_por_lote = {}

    ventas_ordenadas = df_ventas.assign(_Orden_Original=range(len(df_ventas)))
    ventas_ordenadas = ventas_ordenadas.sort_values(['Fecha_Venta', '_Orden_Original']).copy()

    for idx, venta in ventas_ordenadas.iterrows():
        if venta['Resultado'] >= -0.01:
            continue

        broker = venta.get('Broker', 'Desconocido')
        ticker = venta['Ticker']
        fecha_venta = venta['Fecha_Venta']
        cantidad_vendida = float(venta['Cantidad_Vendida'])
        if cantidad_vendida <= 0:
            continue

        perdida_unitaria = abs(float(venta['Resultado'])) / cantidad_vendida
        cantidad_pendiente = cantidad_vendida
        fecha_limite_atras = fecha_venta - pd.DateOffset(months=2)
        fecha_limite_adelante = fecha_venta + pd.DateOffset(months=2)

        compras_ticker = df_compras[
            (df_compras['Broker'] == broker) &
            (df_compras['Ticker'] == ticker)
        ].sort_values(['Fecha_Compra', 'Lote_Compra_ID'])

        compras_previas = compras_ticker[
            (compras_ticker['Fecha_Compra'] >= fecha_limite_atras) &
            (compras_ticker['Fecha_Compra'] <= fecha_venta)
        ].copy()
        compras_posteriores = compras_ticker[
            (compras_ticker['Fecha_Compra'] > fecha_venta) &
            (compras_ticker['Fecha_Compra'] <= fecha_limite_adelante)
        ].copy()

        candidatos = []
        for _, compra in compras_previas.iterrows():
            lote_id = compra['Lote_Compra_ID']
            vendida_hasta_venta = _cantidad_vendida_de_lote_hasta_fecha(df_ventas, lote_id, fecha_venta)
            cantidad_en_patrimonio = max(0.0, float(compra['Cantidad_Comprada']) - vendida_hasta_venta)
            cantidad_ya_asignada = cantidad_asignada_por_lote.get(lote_id, 0.0)
            cantidad_disponible = max(0.0, cantidad_en_patrimonio - cantidad_ya_asignada)
            if cantidad_disponible > 0.00000001:
                candidatos.append((compra, cantidad_disponible))

        for _, compra in compras_posteriores.iterrows():
            lote_id = compra['Lote_Compra_ID']
            cantidad_ya_asignada = cantidad_asignada_por_lote.get(lote_id, 0.0)
            cantidad_disponible = max(0.0, float(compra['Cantidad_Comprada']) - cantidad_ya_asignada)
            if cantidad_disponible > 0.00000001:
                candidatos.append((compra, cantidad_disponible))

        for compra, cantidad_disponible in candidatos:
            if cantidad_pendiente <= 0.00000001:
                break

            cantidad_bloqueada = min(cantidad_pendiente, cantidad_disponible)
            lote_id = compra['Lote_Compra_ID']
            perdida_bloqueada = cantidad_bloqueada * perdida_unitaria

            df_ventas.at[idx, 'Perdida_Suspendida'] += perdida_bloqueada
            cantidad_asignada_por_lote[lote_id] = (
                cantidad_asignada_por_lote.get(lote_id, 0.0) + cantidad_bloqueada
            )
            bloqueos.append({
                'Lote_Compra_ID': lote_id,
                'Fecha_Bloqueo': fecha_venta,
                'Cantidad_Pendiente': cantidad_bloqueada,
                'Perdida_Unitaria': perdida_unitaria,
            })
            cantidad_pendiente -= cantidad_bloqueada

    bloqueos_por_lote = {}
    for bloqueo in bloqueos:
        bloqueos_por_lote.setdefault(bloqueo['Lote_Compra_ID'], []).append(bloqueo)

    for idx, venta in ventas_ordenadas.iterrows():
        lote_id = venta.get('Lote_Compra_ID')
        if lote_id not in bloqueos_por_lote:
            continue

        cantidad_disponible_venta = float(venta['Cantidad_Vendida'])
        for bloqueo in bloqueos_por_lote[lote_id]:
            if cantidad_disponible_venta <= 0.00000001:
                break
            if bloqueo['Cantidad_Pendiente'] <= 0.00000001:
                continue
            if venta['Fecha_Venta'] <= bloqueo['Fecha_Bloqueo']:
                continue

            cantidad_liberada = min(cantidad_disponible_venta, bloqueo['Cantidad_Pendiente'])
            df_ventas.at[idx, 'Perdida_Liberada'] += cantidad_liberada * bloqueo['Perdida_Unitaria']
            bloqueo['Cantidad_Pendiente'] -= cantidad_liberada
            cantidad_disponible_venta -= cantidad_liberada

    return df_ventas

def calcular_renta(df_con_eur):
    if df_con_eur.empty: 
        return pd.DataFrame(), {}
    
    df_con_eur['Buy/Sell'] = df_con_eur['Buy/Sell'].astype(str).str.strip().str.upper()
    df_con_eur['Es_Compra_Bool'] = df_con_eur['Buy/Sell'].apply(lambda x: True if 'BUY' in x else False)
    
    df = df_con_eur.sort_values(by=['TradeDate', 'Es_Compra_Bool'], ascending=[True, False]).reset_index(drop=True)
    
    cartera = {} 
    ventas_realizadas = []
    registro_compras = []

    for _, fila in df.iterrows():
        broker = fila.get('Broker', 'Desconocido')
        ticker = fila['Symbol']
        fecha = fila['TradeDate']
        es_compra = fila['Es_Compra_Bool']
        
        cantidad = round(abs(float(fila['Quantity'])), PRECISION)
        precio_eur = float(fila['TradePrice_EUR'])
        comision_eur = float(fila['IBCommission_EUR'])

        if es_compra:
            _procesar_compra(cartera, registro_compras, broker, ticker, fecha, cantidad, precio_eur, comision_eur)
        else:
            _procesar_venta(cartera, ventas_realizadas, broker, ticker, fecha, cantidad, precio_eur, comision_eur)

    df_ventas = pd.DataFrame(ventas_realizadas)
    df_compras = pd.DataFrame(registro_compras)
    cartera_limpia = {k: v for k, v in cartera.items() if len(v) > 0}
    df_ventas = _aplicar_regla_dos_meses(df_ventas, df, cartera, df_compras)

    return df_ventas, cartera_limpia
