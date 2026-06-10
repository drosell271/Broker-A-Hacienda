import pandas as pd
from pathlib import Path

def cargar_y_limpiar_revolut(directorio_base="data/raw"):
    ruta_base = Path(directorio_base)
    archivos = list(ruta_base.rglob('revolut_trades.csv'))
    
    if not archivos:
        return pd.DataFrame()
        
    lista_dfs = []
    for archivo in archivos:
        try:
            df = pd.read_csv(archivo)
            lista_dfs.append(df)
        except Exception as e:
            print(f"⚠️ Error leyendo {archivo}: {e}")
            
    if not lista_dfs:
        return pd.DataFrame()
        
    df_final = pd.concat(lista_dfs, ignore_index=True)
    
    # Filtro operativo
    tipos_validos = ['BUY - MARKET', 'SELL - MARKET', 'BUY - LIMIT', 'SELL - LIMIT']
    df_final = df_final[df_final['Type'].isin(tipos_validos)].copy()
    
    # Estandarización de Fechas y Etiquetas
    df_final['Date'] = pd.to_datetime(df_final['Date']).dt.tz_localize(None)
    df_final['Buy/Sell'] = df_final['Type'].apply(lambda x: 'BUY' if 'BUY' in x else 'SELL')
    df_final['Broker'] = 'Revolut'
    df_final['Symbol'] = df_final['Ticker']
    df_final['TradeDate'] = df_final['Date']
    
    # Limpieza estricta de precios (quitando el texto de la moneda como "USD ")
    precio_limpio = df_final['Price per share'].astype(str).str.replace(r'[^\d.]', '', regex=True)
    
    df_final['Quantity'] = pd.to_numeric(df_final['Quantity'], errors='coerce')
    df_final['TradePrice'] = pd.to_numeric(precio_limpio, errors='coerce')
    df_final['CurrencyPrimary'] = df_final['Currency']
    
    # Comisiones en Revolut son 0 (van implícitas o en tier separado)
    df_final['IBCommission'] = 0.0
    df_final['IBCommissionCurrency'] = df_final['CurrencyPrimary']
    df_final['FX_Rate'] = pd.to_numeric(df_final['FX Rate'], errors='coerce')
    
    columnas_finales = [
        'Broker', 'Buy/Sell', 'Symbol', 'Quantity', 
        'TradePrice', 'CurrencyPrimary', 'IBCommission', 
        'IBCommissionCurrency', 'TradeDate', 'FX_Rate'
    ]
    
    return df_final[columnas_finales]
