import json
from pathlib import Path

from src.services.forex import DEFAULT_ECB_CACHE_PATH


SETTINGS_PATH = Path(__file__).with_name("settings.json")
DEFAULT_SETTINGS = {
    "data_dir": "data/raw",
    "output": "output/informe_fiscal.md",
    "fx_cache": str(DEFAULT_ECB_CACHE_PATH),
}


def cargar_settings(ruta=SETTINGS_PATH):
    ruta = Path(ruta)
    if not ruta.exists():
        return DEFAULT_SETTINGS.copy()

    with open(ruta, "r", encoding="utf-8") as archivo:
        datos = json.load(archivo)

    settings = DEFAULT_SETTINGS.copy()
    settings.update({clave: valor for clave, valor in datos.items() if valor})
    return settings
