import pandas as pd
from pathlib import Path


def cargar_rendimientos_capital_mobiliario(directorio_base="data/raw"):
    """
    Carga saldos netos anuales opcionales de capital mobiliario.

    Formato recomendado: rendimientos_capital.csv con columnas
    Anio_Fiscal,Rendimiento_Capital_Mobiliario.
    """
    columnas = ["Anio_Fiscal", "Rendimiento_Capital_Mobiliario"]
    ruta_base = Path(directorio_base)
    archivos = list(ruta_base.rglob("rendimientos_capital.csv"))
    if not archivos:
        return pd.DataFrame(columns=columnas)

    equivalencias_anio = ["Anio_Fiscal", "Año", "Ano", "Anio", "Year"]
    equivalencias_importe = [
        "Rendimiento_Capital_Mobiliario",
        "Rendimiento",
        "Importe",
        "Amount",
    ]

    registros = []
    for archivo in archivos:
        try:
            datos = pd.read_csv(archivo).dropna(axis=1, how="all")
        except Exception as exc:
            raise ValueError(f"No se pudo leer {archivo}: {exc}") from exc

        columna_anio = next((col for col in equivalencias_anio if col in datos.columns), None)
        columna_importe = next((col for col in equivalencias_importe if col in datos.columns), None)
        if columna_anio is None or columna_importe is None:
            raise ValueError(
                f"{archivo} debe incluir columnas Anio_Fiscal y Rendimiento_Capital_Mobiliario."
            )

        parcial = datos[[columna_anio, columna_importe]].copy()
        parcial.columns = columnas
        parcial["Anio_Fiscal"] = pd.to_numeric(parcial["Anio_Fiscal"], errors="coerce")
        parcial["Rendimiento_Capital_Mobiliario"] = pd.to_numeric(
            parcial["Rendimiento_Capital_Mobiliario"],
            errors="coerce",
        )
        parcial = parcial.dropna(subset=columnas)
        registros.append(parcial)

    if not registros:
        return pd.DataFrame(columns=columnas)

    resultado = pd.concat(registros, ignore_index=True)
    resultado["Anio_Fiscal"] = resultado["Anio_Fiscal"].astype(int)
    return (
        resultado.groupby("Anio_Fiscal", as_index=False)["Rendimiento_Capital_Mobiliario"]
        .sum()
        .sort_values("Anio_Fiscal")
        .reset_index(drop=True)
    )
