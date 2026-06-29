def formatear_eur(valor):
    return f"{valor:,.2f} €"


def periodo_fiscal(anio):
    anio = int(anio)
    return f"{anio}-01-01 a {anio}-12-31"
