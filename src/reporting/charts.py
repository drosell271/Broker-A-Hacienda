import math

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter


COLOR_TEXTO = "#172033"
COLOR_MUTED = "#667085"
COLOR_GRID = "#e5e7eb"
COLOR_POSITIVO = "#12805c"
COLOR_NEGATIVO = "#c2410c"
COLOR_AZUL = "#2563eb"
COLOR_MORADO = "#7c3aed"
COLOR_FONDO = "#f8fafc"


def preparar_resultado_por_valor(datos_declaracion_valor, limite=10):
    if datos_declaracion_valor.empty:
        return pd.DataFrame(columns=["Etiqueta", "Importe"])

    datos = (
        datos_declaracion_valor.groupby("Concepto_0328", as_index=False)["Resultado_Computable"]
        .sum()
        .rename(columns={"Concepto_0328": "Etiqueta", "Resultado_Computable": "Importe"})
    )
    datos["_Abs"] = datos["Importe"].abs()
    return (
        datos.sort_values(["_Abs", "Etiqueta"], ascending=[False, True])
        .head(limite)
        .drop(columns=["_Abs"])
        .reset_index(drop=True)
    )


def preparar_cartera_por_coste(df_cartera, limite=10):
    if df_cartera.empty:
        return pd.DataFrame(columns=["Etiqueta", "Importe"])

    datos = df_cartera[["Ticker", "Coste_Total (€)"]].copy()
    datos.columns = ["Etiqueta", "Importe"]
    return (
        datos.sort_values(["Importe", "Etiqueta"], ascending=[False, True])
        .head(limite)
        .reset_index(drop=True)
    )


def preparar_resultado_mensual(df_ventas):
    if df_ventas is None or df_ventas.empty:
        return pd.DataFrame(columns=["Etiqueta", "Importe"])

    datos = df_ventas.copy()
    datos["Etiqueta"] = datos["Fecha_Venta"].dt.to_period("M").astype(str)
    datos["Resultado_Computable"] = (
        datos["Resultado"]
        + datos["Perdida_Suspendida"]
        - datos["Perdida_Liberada"]
    )
    return (
        datos.groupby("Etiqueta", as_index=False)["Resultado_Computable"]
        .sum()
        .rename(columns={"Resultado_Computable": "Importe"})
        .sort_values("Etiqueta")
        .reset_index(drop=True)
    )


def preparar_resultado_mensual_acumulado(df_ventas):
    datos = preparar_resultado_mensual(df_ventas)
    if datos.empty:
        return datos

    acumulado = datos.copy()
    acumulado["Importe"] = acumulado["Importe"].astype(float).cumsum()
    return acumulado


def preparar_resultado_y_base_por_anio(resumen_anual):
    if resumen_anual.empty:
        return pd.DataFrame(columns=["Etiqueta", "Importe"])

    filas = []
    for _, fila in resumen_anual.iterrows():
        anio = int(fila["Anio_Fiscal"])
        filas.append({
            "Etiqueta": f"{anio} resultado",
            "Importe": float(fila["Rendimiento_Neto_Computable"]),
        })
        filas.append({
            "Etiqueta": f"{anio} base",
            "Importe": float(fila["Base_Ahorro_Tras_Compensacion"]),
        })
    return pd.DataFrame(filas)


def barra_ascii(valor, max_abs, ancho=24):
    if max_abs <= 0:
        return ""
    longitud = int(round((abs(valor) / max_abs) * ancho))
    longitud = max(1, min(ancho, longitud)) if abs(valor) > 0.005 else 0
    simbolo = "#" if valor >= 0 else "-"
    return simbolo * longitud


def tabla_grafico_markdown(datos, titulo, texto_vacio, limite=None, ancho=28):
    if datos.empty:
        return f"### {titulo}\n\n{texto_vacio}\n\n"

    grafico = datos.copy()
    if limite is not None:
        grafico = grafico.head(limite)
    max_abs = float(grafico["Importe"].abs().max())
    if max_abs <= 0:
        return f"### {titulo}\n\n{texto_vacio}\n\n"

    lineas = [
        f"### {titulo}",
        "",
        "| Concepto | Importe | Gráfico |",
        "| :--- | ---: | :--- |",
    ]
    for _, fila in grafico.iterrows():
        importe = float(fila["Importe"])
        lineas.append(
            f"| {fila['Etiqueta']} | {importe:,.2f} € | `{barra_ascii(importe, max_abs, ancho)}` |"
        )
    lineas.append("")
    return "\n".join(lineas) + "\n"


def guardar_linea_mensual_png(datos, ruta):
    _guardar_linea_importes_png(
        datos,
        ruta,
        "Evolución mensual del resultado computable",
        "Importes tras aplicar pérdidas suspendidas y liberadas",
        "Sin ventas mensuales computables.",
    )


def guardar_acumulado_mensual_png(datos, ruta):
    _guardar_linea_importes_png(
        datos,
        ruta,
        "Acumulado mensual del resultado computable",
        "Suma acumulada de los resultados mensuales computables",
        "Sin ventas mensuales computables.",
    )


def _guardar_linea_importes_png(datos, ruta, titulo, subtitulo, texto_vacio):
    if datos.empty:
        _guardar_mensaje_vacio(ruta, titulo, texto_vacio)
        return

    valores = datos["Importe"].astype(float).tolist()
    etiquetas = datos["Etiqueta"].astype(str).tolist()
    x = list(range(len(valores)))

    fig, ax = plt.subplots(figsize=(11.5, 4.8), dpi=150)
    _preparar_figura(fig, ax)
    ax.set_title(
        titulo,
        loc="left",
        fontsize=15,
        fontweight="bold",
        color=COLOR_TEXTO,
        pad=18,
    )
    ax.text(
        0,
        1.02,
        subtitulo,
        transform=ax.transAxes,
        fontsize=10,
        color=COLOR_MUTED,
    )

    positivos = [valor if valor >= 0 else math.nan for valor in valores]
    negativos = [valor if valor < 0 else math.nan for valor in valores]
    ax.fill_between(
        x,
        0,
        valores,
        where=[valor >= 0 for valor in valores],
        color=COLOR_POSITIVO,
        alpha=0.14,
        interpolate=True,
        zorder=1,
    )
    ax.fill_between(
        x,
        0,
        valores,
        where=[valor < 0 for valor in valores],
        color=COLOR_NEGATIVO,
        alpha=0.15,
        interpolate=True,
        zorder=1,
    )
    ax.plot(x, valores, color=COLOR_AZUL, linewidth=2.8, zorder=3)
    ax.scatter(x, positivos, s=58, color=COLOR_POSITIVO, edgecolor="white", linewidth=1.4, zorder=4)
    ax.scatter(x, negativos, s=58, color=COLOR_NEGATIVO, edgecolor="white", linewidth=1.4, zorder=4)
    ax.axhline(0, color="#94a3b8", linewidth=1.1)

    ax.set_xticks(x)
    ax.set_xticklabels(etiquetas, rotation=0, ha="center", color=COLOR_MUTED)
    ax.yaxis.set_major_formatter(FuncFormatter(_formatear_eur_eje))
    ax.tick_params(axis="y", colors=COLOR_MUTED)
    _ajustar_limites_y(ax, valores)
    _anotar_puntos(ax, x, valores)

    _guardar_figura(fig, ruta)


def guardar_resumen_anual_png(resumen_anual, ruta):
    if resumen_anual.empty:
        _guardar_mensaje_vacio(ruta, "Resumen anual por ejercicio", "Sin resultado anual computable.")
        return

    datos = resumen_anual.sort_values("Anio_Fiscal").copy()
    etiquetas = datos["Anio_Fiscal"].astype(int).astype(str).tolist()
    x = list(range(len(datos)))
    ancho = 0.24

    resultado = datos["Rendimiento_Neto_Computable"].astype(float).tolist()
    base = datos["Base_Ahorro_Tras_Compensacion"].astype(float).tolist()
    impuesto = datos["Impuesto_Estimado"].astype(float).tolist()

    fig, ax = plt.subplots(figsize=(11.5, 4.9), dpi=150)
    _preparar_figura(fig, ax)
    ax.set_title(
        "Resumen anual por ejercicio",
        loc="left",
        fontsize=15,
        fontweight="bold",
        color=COLOR_TEXTO,
        pad=18,
    )
    ax.text(
        0,
        1.02,
        "Comparativa de resultado computable, base del ahorro e impuesto estimado",
        transform=ax.transAxes,
        fontsize=10,
        color=COLOR_MUTED,
    )

    colores_resultado = [COLOR_POSITIVO if valor >= 0 else COLOR_NEGATIVO for valor in resultado]
    ax.bar([pos - ancho for pos in x], resultado, ancho, label="Resultado acciones", color=colores_resultado)
    ax.bar(x, base, ancho, label="Base ahorro", color=COLOR_AZUL)
    ax.bar([pos + ancho for pos in x], impuesto, ancho, label="Impuesto estimado", color=COLOR_MORADO)
    ax.axhline(0, color="#94a3b8", linewidth=1.1)

    ax.set_xticks(x)
    ax.set_xticklabels(etiquetas, color=COLOR_MUTED)
    ax.yaxis.set_major_formatter(FuncFormatter(_formatear_eur_eje))
    ax.tick_params(axis="y", colors=COLOR_MUTED)
    ax.legend(frameon=False, loc="upper left", bbox_to_anchor=(0, -0.12), ncols=3)
    _ajustar_limites_y(ax, resultado + base + impuesto)
    _anotar_barras(ax)

    _guardar_figura(fig, ruta)


def guardar_barras_horizontales_png(datos, ruta, titulo, texto_vacio, limite=10):
    if datos.empty:
        _guardar_mensaje_vacio(ruta, titulo, texto_vacio)
        return

    grafico = datos.head(limite).copy().iloc[::-1]
    valores = grafico["Importe"].astype(float).tolist()
    etiquetas = grafico["Etiqueta"].astype(str).tolist()
    y = list(range(len(grafico)))
    alto = max(3.7, 1.4 + 0.46 * len(grafico))

    fig, ax = plt.subplots(figsize=(11.5, alto), dpi=150)
    _preparar_figura(fig, ax)
    ax.set_title(titulo, loc="left", fontsize=15, fontweight="bold", color=COLOR_TEXTO, pad=16)

    colores = [COLOR_POSITIVO if valor >= 0 else COLOR_NEGATIVO for valor in valores]
    ax.barh(y, valores, color=colores, height=0.58)
    ax.axvline(0, color="#94a3b8", linewidth=1.1)
    ax.set_yticks(y)
    ax.set_yticklabels(etiquetas, color=COLOR_TEXTO)
    ax.xaxis.set_major_formatter(FuncFormatter(_formatear_eur_eje))
    ax.tick_params(axis="x", colors=COLOR_MUTED)
    _ajustar_limites_x(ax, valores)

    margen = (max(valores) - min(valores)) * 0.015 or max(abs(valor) for valor in valores) * 0.02 or 1.0
    for pos, valor in zip(y, valores):
        if valor >= 0:
            ax.text(valor + margen, pos, _formatear_eur(valor), va="center", ha="left", fontsize=9, color=COLOR_TEXTO)
        else:
            ax.text(valor - margen, pos, _formatear_eur(valor), va="center", ha="right", fontsize=9, color=COLOR_TEXTO)

    _guardar_figura(fig, ruta)


def _preparar_figura(fig, ax):
    fig.patch.set_facecolor(COLOR_FONDO)
    ax.set_facecolor("white")
    ax.grid(True, axis="y", color=COLOR_GRID, linewidth=0.9)
    ax.set_axisbelow(True)
    for lado in ["top", "right", "left"]:
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color("#cbd5e1")
    ax.tick_params(length=0)


def _guardar_figura(fig, ruta):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(pad=1.6)
    fig.savefig(ruta, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def _guardar_mensaje_vacio(ruta, titulo, texto):
    fig, ax = plt.subplots(figsize=(11.5, 2.6), dpi=150)
    fig.patch.set_facecolor(COLOR_FONDO)
    ax.set_facecolor("white")
    ax.axis("off")
    ax.text(0.02, 0.72, titulo, transform=ax.transAxes, fontsize=15, fontweight="bold", color=COLOR_TEXTO)
    ax.text(0.02, 0.42, texto, transform=ax.transAxes, fontsize=11, color=COLOR_MUTED)
    _guardar_figura(fig, ruta)


def _formatear_eur(valor):
    return f"{valor:,.2f} €"


def _formatear_eur_eje(valor, _pos):
    if abs(valor) >= 1000:
        return f"{valor / 1000:,.1f}k €"
    return f"{valor:,.0f} €"


def _ajustar_limites_y(ax, valores):
    minimo = min(min(valores), 0.0)
    maximo = max(max(valores), 0.0)
    rango = maximo - minimo
    margen = rango * 0.18 if rango else max(abs(maximo), 1.0) * 0.25
    ax.set_ylim(minimo - margen, maximo + margen)


def _ajustar_limites_x(ax, valores):
    minimo = min(min(valores), 0.0)
    maximo = max(max(valores), 0.0)
    rango = maximo - minimo
    margen = rango * 0.12 if rango else max(abs(maximo), 1.0) * 0.25
    ax.set_xlim(minimo - margen, maximo + margen)


def _anotar_puntos(ax, x, valores):
    if len(valores) > 14:
        indices = {valores.index(min(valores)), valores.index(max(valores))}
    else:
        indices = set(range(len(valores)))

    y_min, y_max = ax.get_ylim()
    offset = (y_max - y_min) * 0.045
    for idx in indices:
        valor = valores[idx]
        va = "bottom" if valor >= 0 else "top"
        dy = offset if valor >= 0 else -offset
        ax.text(
            x[idx],
            valor + dy,
            _formatear_eur(valor),
            ha="center",
            va=va,
            fontsize=8.5,
            color=COLOR_TEXTO,
        )


def _anotar_barras(ax):
    y_min, y_max = ax.get_ylim()
    offset = (y_max - y_min) * 0.012
    for barra in ax.patches:
        valor = barra.get_height()
        x = barra.get_x() + barra.get_width() / 2
        va = "bottom" if valor >= 0 else "top"
        dy = offset if valor >= 0 else -offset
        ax.text(
            x,
            valor + dy,
            _formatear_eur(valor),
            ha="center",
            va=va,
            fontsize=8.2,
            color=COLOR_TEXTO,
            rotation=0,
        )
