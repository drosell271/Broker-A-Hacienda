import pandas as pd
from pathlib import Path

def cargar_y_limpiar_ibkr(directorio_base="data/raw"):
    ruta_base = Path(directorio_base)
    archivos = list(ruta_base.rglob('ibkr_trades.csv'))
    
    if not archivos:
        return pd.DataFrame()
        
    lista_dfs = []
    for archivo in archivos:
        try:
            df = pd.read_csv(archivo).dropna(axis=1, how="all")
            lista_dfs.append(df)
        except Exception as e:
            print(f"AVISO: error leyendo {archivo}: {e}")
            
    if not lista_dfs:
        return pd.DataFrame()
        
    df_final = pd.concat(lista_dfs, ignore_index=True)
    
    # Filtro fiscal: Solo acciones
    df_final = df_final[df_final['AssetClass'] == 'STK'].copy()
    
    # Filtro estricto de BUY/SELL
    df_final['Buy/Sell'] = df_final['Buy/Sell'].astype(str).str.strip().str.upper()
    df_final = df_final[df_final['Buy/Sell'].isin(['BUY', 'SELL'])].copy()
    
    # -----------------------------------------------------------------
    # NUEVO: Parseo exacto con hora, minuto y segundo
    # Lee '20251104;051650' y lo convierte en datetime real
    # -----------------------------------------------------------------
    df_final['TradeDate'] = pd.to_datetime(df_final['DateTime'], format='%Y%m%d;%H%M%S')
    
    df_final['Broker'] = 'IBKR'
    
    df_final['Quantity'] = pd.to_numeric(df_final['Quantity'], errors='coerce')
    df_final['TradePrice'] = pd.to_numeric(df_final['TradePrice'], errors='coerce')
    df_final['IBCommission'] = pd.to_numeric(df_final['IBCommission'], errors='coerce').fillna(0.0)
    if 'FX_Rate' in df_final.columns:
        df_final['FX_Rate'] = pd.to_numeric(df_final['FX_Rate'], errors='coerce')
    elif 'FX Rate' in df_final.columns:
        df_final['FX_Rate'] = pd.to_numeric(df_final['FX Rate'], errors='coerce')
    else:
        df_final['FX_Rate'] = float("nan")
    
    columnas_finales = [
        'Broker', 'Buy/Sell', 'Symbol', 'Quantity', 
        'TradePrice', 'CurrencyPrimary', 'IBCommission', 
        'IBCommissionCurrency', 'TradeDate', 'FX_Rate'
    ]
    
    return df_final[columnas_finales]
