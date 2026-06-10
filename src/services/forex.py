import pandas as pd
import io
import zipfile
from pathlib import Path

import requests

ECB_HISTORICAL_RATES_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.zip"
DEFAULT_ECB_CACHE_PATH = Path("data/cache/ecb/eurofxref-hist.csv")


def _descargar_historico_bce(ruta_cache=DEFAULT_ECB_CACHE_PATH):
    ruta_cache = Path(ruta_cache)
    ruta_cache.parent.mkdir(parents=True, exist_ok=True)

    respuesta = requests.get(ECB_HISTORICAL_RATES_URL, timeout=30)
    respuesta.raise_for_status()

    with zipfile.ZipFile(io.BytesIO(respuesta.content)) as archivo_zip:
        nombre_csv = next(
            (nombre for nombre in archivo_zip.namelist() if nombre.lower().endswith(".csv")),
            None,
        )
        if nombre_csv is None:
            raise ValueError("El ZIP del BCE no contiene ningun CSV de tipos historicos.")
        ruta_cache.write_bytes(archivo_zip.read(nombre_csv))

    return ruta_cache


def asegurar_historico_bce(ruta_cache=DEFAULT_ECB_CACHE_PATH, actualizar=False):
    ruta_cache = Path(ruta_cache)
    if actualizar or not ruta_cache.exists():
        return _descargar_historico_bce(ruta_cache)
    return ruta_cache


def _cargar_historico_bce(ruta_cache=DEFAULT_ECB_CACHE_PATH, actualizar=False):
    ruta_cache = Path(ruta_cache)

    asegurar_historico_bce(ruta_cache, actualizar)

    try:
        historico = pd.read_csv(ruta_cache)
    except Exception:
        _descargar_historico_bce(ruta_cache)
        historico = pd.read_csv(ruta_cache)

    if "Date" not in historico.columns:
        raise ValueError(f"El historico del BCE en {ruta_cache} no contiene columna Date.")

    historico["Date"] = pd.to_datetime(historico["Date"], errors="coerce").dt.normalize()
    historico = historico.dropna(subset=["Date"]).sort_values("Date").reset_index(drop=True)
    return historico


def _obtener_tipo_bce(historico_bce, fecha, divisa):
    divisa = str(divisa).upper().strip()
    if divisa == "EUR":
        return 1.0

    if divisa not in historico_bce.columns:
        raise ValueError(f"El BCE no publica tipo historico para la divisa {divisa}.")

    fecha_operacion = pd.to_datetime(fecha).normalize()
    tipos_disponibles = historico_bce.loc[
        historico_bce["Date"] <= fecha_operacion,
        ["Date", divisa],
    ].dropna(subset=[divisa])

    if tipos_disponibles.empty:
        raise ValueError(
            f"No hay tipo BCE disponible para {divisa} en o antes de {fecha_operacion.date()}."
        )

    return float(tipos_disponibles.iloc[-1][divisa])


def aplicar_forex_a_trades(df_all, ruta_cache_bce=DEFAULT_ECB_CACHE_PATH, actualizar_fx=False):
    """
    Convierte operaciones y comisiones a euros usando FX real.

    Si el broker aporta FX_Rate, se usa ese tipo. Si no, se consulta el
    historico oficial del BCE. Nunca se inventa un tipo de cambio.
    """
    if df_all.empty:
        return pd.DataFrame()
        
    df = df_all.copy()
    
    # Inicializar columnas de destino
    df['TradePrice_EUR'] = 0.0
    df['IBCommission_EUR'] = 0.0
    
    necesita_bce = False
    for _, fila in df.iterrows():
        divisa_precio = str(fila.get('CurrencyPrimary', 'EUR')).upper()
        divisa_comision = str(fila.get('IBCommissionCurrency', 'EUR')).upper()
        fx_rate = pd.to_numeric(fila.get('FX_Rate'), errors='coerce')
        if (divisa_precio != 'EUR' or divisa_comision != 'EUR') and (pd.isna(fx_rate) or fx_rate <= 0):
            necesita_bce = True
            break

    historico_bce = _cargar_historico_bce(ruta_cache_bce, actualizar_fx) if necesita_bce else None

    for idx, fila in df.iterrows():
        divisa_precio = str(fila.get('CurrencyPrimary', 'EUR')).upper()
        divisa_comision = str(fila.get('IBCommissionCurrency', 'EUR')).upper()
        
        precio_original = float(fila['TradePrice']) if pd.notnull(fila['TradePrice']) else 0.0
        comision_original = abs(float(fila['IBCommission'])) if pd.notnull(fila['IBCommission']) else 0.0
        
        # --- CONVERSIÓN DEL PRECIO DE LA ACCIÓN ---
        if divisa_precio == 'EUR':
            df.at[idx, 'TradePrice_EUR'] = precio_original
        else:
            # Si el bróker nos dio el FX Rate (ej. Revolut), lo usamos
            if pd.notnull(fila.get('FX_Rate')) and float(fila['FX_Rate']) > 0:
                df.at[idx, 'TradePrice_EUR'] = precio_original / float(fila['FX_Rate'])
            else:
                tasa_bce = _obtener_tipo_bce(historico_bce, fila['TradeDate'], divisa_precio)
                df.at[idx, 'TradePrice_EUR'] = precio_original / tasa_bce
                
        # --- CONVERSIÓN DE LA COMISIÓN ---
        if divisa_comision == 'EUR':
            df.at[idx, 'IBCommission_EUR'] = comision_original
        else:
            if pd.notnull(fila.get('FX_Rate')) and float(fila['FX_Rate']) > 0:
                df.at[idx, 'IBCommission_EUR'] = comision_original / float(fila['FX_Rate'])
            else:
                tasa_bce = _obtener_tipo_bce(historico_bce, fila['TradeDate'], divisa_comision)
                df.at[idx, 'IBCommission_EUR'] = comision_original / tasa_bce
                
    return df
