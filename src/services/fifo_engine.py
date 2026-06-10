import pandas as pd
from collections import deque

PRECISION = 8 

def _procesar_compra(cartera, registro_compras, broker, ticker, fecha, cantidad, precio_eur, comision_eur):
    clave = (broker, ticker)
    coste_total = (cantidad * precio_eur) + comision_eur
    coste_unitario = coste_total / cantidad if cantidad > 0 else 0
    
    if clave not in cartera:
        cartera[clave] = deque()
        
    cartera[clave].append({
        'fecha': fecha, 
        'cantidad': cantidad, 
        'coste_unitario': coste_unitario
    })
    
    registro_compras.append({
        'ticker': ticker, 
        'fecha': fecha, 
        'cantidad': cantidad
    })

def _procesar_venta(cartera, ventas_realizadas, broker, ticker, fecha, cantidad_a_vender, precio_eur, comision_eur):
    clave = (broker, ticker)
    ingreso_total_neto_eur = (cantidad_a_vender * precio_eur) - comision_eur
    ingreso_unitario_neto = ingreso_total_neto_eur / cantidad_a_vender if cantidad_a_vender > 0 else 0
    
    if clave not in cartera or len(cartera[clave]) == 0:
        print(f"⚠️ ADVERTENCIA: Venta sin stock previo de {ticker} en {broker}. Ignorando...")
        return
        
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
            'Valor_Adquisicion': val_adquisicion, 
            'Valor_Transmision': val_transmision,
            'Resultado': resultado_neto, 
            'Perdida_Suspendida': 0.0,
            'Perdida_Liberada': 0.0
        })

def _aplicar_regla_dos_meses(df_ventas, df_todas_operaciones):
    """
    Aplica la regla de los 2 meses de forma estricta. Solo suspende si hay una 
    RECOMPRA posterior o si se mantienen acciones homogéneas concurrentes.
    """
    if df_ventas.empty:
        return df_ventas

    # Agrupamos todas las compras reales del histórico para comprobar recompras verdaderas
    compras_reales = df_todas_operaciones[df_todas_operaciones['Buy/Sell'] == 'BUY'].copy()

    for idx, venta in df_ventas.iterrows():
        if venta['Resultado'] < -0.01:  
            t_ticker = venta['Ticker']
            f_venta = venta['Fecha_Venta']
            cant_vendida = venta['Cantidad_Vendida']
            
            fecha_limite_atras = f_venta - pd.Timedelta(days=60)
            fecha_limite_adelante = f_venta + pd.Timedelta(days=60)
            
            # Buscamos compras en la ventana de riesgo (+/- 60 días)
            compras_en_ventana = compras_reales[
                (compras_reales['Symbol'] == t_ticker) & 
                (compras_reales['TradeDate'] >= fecha_limite_atras) & 
                (compras_reales['TradeDate'] <= fecha_limite_adelante)
            ]
            
            # FISCALIDAD REAL: Solo hay recompra si el total comprado en la ventana de 120 días
            # supera las acciones vendidas, o si hay compras posteriores a la venta.
            total_comprado_en_ventana = compras_en_ventana['Quantity'].sum()
            
            # Si el total comprado es igual o menor a lo vendido y no hay compras posteriores a la fecha de venta,
            # significa que es el mismo lote que entra y sale (Day trade / Swing trade cerrado). No se suspende.
            compras_posteriores = compras_en_ventana[compras_en_ventana['TradeDate'] > f_venta]
            
            if not compras_posteriores.empty or total_comprado_en_ventana > cant_vendida:
                # Existe una recompra real que bloquea la pérdida
                monto_perdida = abs(venta['Resultado'])
                df_ventas.at[idx, 'Perdida_Suspendida'] = monto_perdida
                
                # Desbloqueo: Al final del histórico sabemos que la posición está a 0 para este ticker.
                # Buscamos la última venta de este ticker en el histórico. Esa venta libera la pérdida.
                ultima_venta_idx = df_ventas[df_ventas['Ticker'] == t_ticker]['Fecha_Venta'].idxmax()
                # La liberamos en el año de la liquidación definitiva
                df_ventas.at[ultima_venta_idx, 'Perdida_Liberada'] += monto_perdida
                
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
    df_ventas = _aplicar_regla_dos_meses(df_ventas, df)
    
    cartera_limpia = {k: v for k, v in cartera.items() if len(v) > 0}
    
    return df_ventas, cartera_limpia
