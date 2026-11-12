"""
src/eda_clima.py
Pestaña "Clima" de 1_EDA: viento, temperatura y humedad frente a las variables objetivo.
Usa los archivos que genera eda_resumen.py:
    eda_clima_agregado.parquet, eda_goles_campo.parquet y partidos.parquet (con columnas de clima).
"""
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

# Asegura que la carpeta raíz del dashboard (la que contiene src/) esté en el path,
# sin importar desde dónde se ejecute.
_RAIZ = str(Path(__file__).resolve().parents[1])
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

from src.datos import cargar  # noqa: E402
from src.estilo import AZUL, COLORES_TIPO, VERDE  # noqa: E402

NOMBRES = {"pass": "Pase", "run": "Carrera"}
MIN_JUGADAS = 100     # pases por grupo para mostrar un valor
MIN_INTENTOS = 15     # goles de campo o despejes por grupo

# Deben coincidir con los rangos de eda_resumen.py
CONDICIONES = {
    "Viento": ("cat_viento", "viento_kmh", ["0–10", "10–20", "20–30", "30+"], "Viento (km/h)"),
    "Temperatura": ("cat_temp", "temp_c", ["< 0", "0–10", "10–20", "20–30", "30+"], "Temperatura (°C)"),
    "Humedad": ("cat_humedad", "humedad", ["< 40%", "40–60%", "60–80%", "80%+"], "Humedad relativa (%)"),
}
ORDEN_DIST_FG = ["< 30", "30–39", "40–49", "50+"]
ORDEN_PROFUNDIDAD = ["Corto (< 10)", "Medio (10–19)", "Profundo (20+)"]
PROFUNDO = "Profundo (20+)"

# Para la comparación directa: (nivel de referencia, nivel extremo, nombre extremo, nombre referencia)
COMPARACION = {
    "Viento": ("0–10", "30+", "Viento fuerte (30+ km/h)", "calma (0–10 km/h)"),
    "Temperatura": ("10–20", "< 0", "Bajo cero (< 0 °C)", "templado (10–20 °C)"),
    "Humedad": ("40–60%", "80%+", "Humedad alta (80%+)", "humedad media (40–60%)"),
}
Z95 = 1.96

COLORES_COBERTURA = ["#2a78d6", "#eb6834", "#1baf7a"]


def tasas_clima(df: pd.DataFrame, por: list[str]) -> pd.DataFrame:
    cols = ["n", "exitos", "yardas", "n_yardas", "air_yards", "n_air", "epa", "fumbles"]
    g = df.groupby(por, observed=True)[cols].sum().reset_index()
    g["tasa_exito"] = g["exitos"] / g["n"]
    g["yardas_prom"] = g["yardas"] / g["n_yardas"].replace(0, np.nan)
    g["air_prom"] = g["air_yards"] / g["n_air"].replace(0, np.nan)
    g["epa_prom"] = g["epa"] / g["n"]
    g["fumbles_100"] = g["fumbles"] / g["n"] * 100
    return g


def _p_valor(z: float) -> float:
    """p-valor bilateral con la normal estándar."""
    return math.erfc(abs(z) / math.sqrt(2))


def proporcion(df: pd.DataFrame, por: list[str], num: str, den: str, min_n: int) -> pd.DataFrame:
    """Proporción num/den por grupo con intervalo de confianza del 95%."""
    g = df.groupby(por, observed=True)[[num, den]].sum().reset_index()
    g = g[g[den] >= min_n].copy()
    g["pct"] = g[num] / g[den]
    g["ic"] = Z95 * np.sqrt(g["pct"] * (1 - g["pct"]) / g[den])
    return g


def media_despeje(df: pd.DataFrame, por: list[str], min_n: int) -> pd.DataFrame:
    """Distancia media de despeje por grupo con intervalo de confianza del 95%."""
    g = df.groupby(por, observed=True)[["despejes", "distancia", "distancia2"]].sum().reset_index()
    g = g[g["despejes"] >= max(min_n, 2)].copy()
    n = g["despejes"]
    g["media"] = g["distancia"] / n
    var = (g["distancia2"] - g["distancia"] ** 2 / n) / (n - 1)
    g["ic"] = Z95 * np.sqrt(var.clip(lower=0) / n)
    return g


def comparar_proporcion(col, etiqueta, df, cat, base, ext, num, den, min_n, nombres) -> bool:
    """Tarjeta: valor en la condición extrema y diferencia contra la referencia."""
    e, b = df[df[cat] == ext], df[df[cat] == base]
    n_e, n_b = e[den].sum(), b[den].sum()
    if n_e < min_n or n_b < min_n:
        col.metric(etiqueta, "–", help=f"Pocos datos (mínimo {min_n} por grupo).")
        return False
    p_e, p_b = e[num].sum() / n_e, b[num].sum() / n_b
    p = (e[num].sum() + b[num].sum()) / (n_e + n_b)
    z = (p_e - p_b) / math.sqrt(p * (1 - p) * (1 / n_e + 1 / n_b)) if 0 < p < 1 else 0.0
    col.metric(etiqueta, f"{p_e:.1%}", delta=f"{(p_e - p_b) * 100:+.1f} pp",
               help=(f"{nombres[0]}: {p_e:.1%} (n = {n_e:,}) · {nombres[1]}: {p_b:.1%} "
                     f"(n = {n_b:,}) · p-valor = {_p_valor(z):.3f}"))
    return True


def comparar_despeje(col, df, cat, base, ext, min_n, nombres) -> bool:
    g = media_despeje(df, [cat], min_n).set_index(cat)
    if ext not in g.index or base not in g.index:
        col.metric("Despeje", "–", help=f"Pocos datos (mínimo {min_n} por grupo).")
        return False
    e, b = g.loc[ext], g.loc[base]
    se = math.hypot(e["ic"] / Z95, b["ic"] / Z95)
    z = (e["media"] - b["media"]) / se if se else 0.0
    col.metric("Despeje", f"{e['media']:.1f} yd",
               delta=f"{e['media'] - b['media']:+.1f} yd",
               help=(f"{nombres[0]}: {e['media']:.1f} yd (n = {int(e['despejes']):,}) · {nombres[1]}: "
                     f"{b['media']:.1f} yd (n = {int(b['despejes']):,}) · p-valor = {_p_valor(z):.3f}"))
    return True


def mostrar_balon(filtrar, cond_lbl: str) -> None:
    """Vista 'Balón': lo que pasa cuando el balón viaja por el aire."""
    cat, _, orden, etq = CONDICIONES[cond_lbl]

    def preparar(nombre):
        df = cargar(nombre)
        if df is None or cat not in df:
            return None
        df = filtrar(df)
        return df[df["estadio"] == "Aire libre"].dropna(subset=[cat])

    pa, de, fg = preparar("eda_clima_pases"), preparar("eda_despejes"), preparar("eda_goles_campo")
    if pa is None:
        st.info("Faltan eda_clima_pases.parquet o eda_despejes.parquet. Vuelve a correr eda_resumen.py.")
        return
    pa = pa.assign(profundos=np.where(pa["profundidad"] == PROFUNDO, pa["intentos"], 0))
    hay_completos = "completos" in pa

    # --- Comparación directa ---
    base, ext, ext_lbl, base_lbl = COMPARACION[cond_lbl]
    nombres = (ext_lbl, base_lbl.capitalize())
    st.markdown(f"#### {ext_lbl} vs {base_lbl}")
    fg_largos = fg[fg["cat_dist"].isin(["40–49", "50+"])] if fg is not None else None
    k = st.columns(5)
    ok = [comparar_proporcion(k[0], "Pases 20+ yd", pa, cat, base, ext,
                              "profundos", "intentos", MIN_JUGADAS, nombres)]
    if hay_completos:
        ok.append(comparar_proporcion(k[1], "Completos", pa, cat, base, ext,
                                      "completos", "intentos", MIN_JUGADAS, nombres))
        ok.append(comparar_proporcion(k[2], "Completos 20+", pa[pa["profundidad"] == PROFUNDO],
                                      cat, base, ext, "completos", "intentos", MIN_INTENTOS * 5, nombres))
    if de is not None:
        ok.append(comparar_despeje(k[3], de, cat, base, ext, MIN_INTENTOS, nombres))
    if fg_largos is not None:
        ok.append(comparar_proporcion(k[4], "Goles 40+ yd", fg_largos,
                                      cat, base, ext, "anotados", "intentos", MIN_INTENTOS, nombres))
    if not all(ok):
        st.info(f"Con estos filtros hay muy pocas jugadas en {ext_lbl[0].lower() + ext_lbl[1:]} o en {base_lbl} para "
                "comparar (las tarjetas con «–»). En postemporada pasa seguido: son pocos partidos. "
                "Usa «Ambas» en Tipo de temporada o amplía las temporadas.")
    st.caption(
        "**Pases 20+ yd:** % de pases que viajan 20 yardas o más por aire.  \n"
        "**Completos:** % de pases que atrapa el receptor.  \n"
        "**Completos 20+:** % de pases largos (20+ yardas) que se atrapan.  \n"
        "**Despeje:** yardas promedio que recorre un despeje.  \n"
        "**Goles 40+ yd:** % de goles de campo de 40 yardas o más que entran.  \n"
        f"El número grande es el valor con {ext_lbl[0].lower() + ext_lbl[1:]}; el de abajo es cuánto cambia contra "
        f"{base_lbl} (pp = puntos porcentuales; verde sube, rojo baja)."
    )

    # --- Gráficas ---
    col1, col2 = st.columns(2)
    if hay_completos:
        g = proporcion(pa, [cat, "profundidad"], "completos", "intentos", MIN_INTENTOS * 5)
        col1.plotly_chart(_puntos(g, cat, orden, etq, "Pases completos por profundidad",
                                  "% completos", ".1%", "intentos", color="profundidad",
                                  orden_color=ORDEN_PROFUNDIDAD), width="stretch")
    else:
        col1.info("Tu CSV no trae `complete_pass`: no se puede calcular el % de pases completos.")

    g = proporcion(pa, [cat], "profundos", "intentos", MIN_JUGADAS)
    col2.plotly_chart(_puntos(g, cat, orden, etq, "Pases que viajan 20+ yardas por aire",
                              "% de pases", ".1%", "intentos", colores=[AZUL]), width="stretch")

    col1, col2 = st.columns(2)
    if de is not None:
        g = media_despeje(de, [cat], MIN_INTENTOS).rename(columns={"media": "pct"})
        col1.plotly_chart(_puntos(g, cat, orden, etq, "Distancia promedio de despeje",
                                  "Yardas", ".1f", "despejes", colores=[VERDE]), width="stretch")

    if fg is not None:
        fg = fg.dropna(subset=["cat_dist"])
        fg = fg.assign(Distancia=np.where(fg["cat_dist"].isin(["40–49", "50+"]), "40+ yardas", "Menos de 40"))
        g = proporcion(fg, [cat, "Distancia"], "anotados", "intentos", MIN_INTENTOS)
        col2.plotly_chart(_puntos(g, cat, orden, etq, "Goles de campo anotados",
                                  "% anotados", ".1%", "intentos", color="Distancia",
                                  orden_color=["Menos de 40", "40+ yardas"]), width="stretch")



def _puntos(g, x, orden, etq, titulo, eje_y, fmt, n_col, color=None, orden_color=None, colores=None):
    """Puntos unidos con intervalo de confianza (columna 'pct' ± 'ic')."""
    orden_cat = {x: orden}
    if color:
        orden_cat[color] = orden_color
    # Plotly une los puntos en el orden de las filas: hay que ordenarlas por categoría
    # (si no, "< 0" queda al final y la línea regresa al inicio).
    g = g.copy()
    g[x] = pd.Categorical(g[x], categories=orden, ordered=True)
    g = g.sort_values(([color] if color else []) + [x])
    fig = px.line(g, x=x, y="pct", color=color, error_y="ic", markers=True,
                  category_orders=orden_cat, color_discrete_sequence=colores or COLORES_COBERTURA,
                  custom_data=["ic", n_col], title=titulo,
                  labels={"pct": eje_y, x: etq, **({color: ""} if color else {})})
    fig.update_traces(hovertemplate=(f"{etq}: %{{x}}<br>{eje_y}: %{{y:{fmt}}} ± %{{customdata[0]:{fmt}}}"
                                     "<br>n = %{customdata[1]:,}<extra>%{fullData.name}</extra>"))
    if fmt.endswith("%"):
        rango = (g["pct"] + g["ic"]).max() - (g["pct"] - g["ic"]).min() if len(g) else 1
        fig.update_yaxes(tickformat=".1%" if rango < 0.08 else ".0%")
    fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0),
                      margin=dict(t=90))
    return fig


def mostrar(filtrar, equipos) -> None:
    """Dibuja la pestaña. Recibe la función `filtrar` y la lista `equipos` de EDA."""
    agr = cargar("eda_clima_agregado")
    partidos = cargar("partidos")
    if agr is None or partidos is None or "estadio" not in partidos:
        st.info("Faltan los archivos de clima. Vuelve a correr eda_resumen.py y copia los "
                ".parquet a src (si sigue sin aparecer, limpia la caché: menú ⋮ → Clear cache).")
        return
    a = filtrar(agr)
    if a.empty:
        st.warning("No hay datos con estos filtros.")
        return

    # ---- Tipo de estadio ------------------------------------------------------
    st.subheader("Tipo de estadio")
    g = tasas_clima(a, ["estadio", "play_type"])
    g["Tipo"] = g["play_type"].map(NOMBRES)
    col1, col2 = st.columns([3, 2])
    fig = px.bar(g, x="estadio", y="epa_prom", color="Tipo", barmode="group",
                 color_discrete_map=COLORES_TIPO, custom_data=["n"],
                 category_orders={"estadio": ["Aire libre", "Techo cerrado"], "Tipo": ["Pase", "Carrera"]},
                 labels={"epa_prom": "EPA por jugada", "estadio": "", "Tipo": ""},
                 title="EPA por jugada: aire libre vs techo cerrado")
    fig.update_traces(hovertemplate="%{x} · %{fullData.name}<br>EPA por jugada: %{y:+.3f}"
                                    "<br>n = %{customdata[0]:,}<extra></extra>")
    col1.plotly_chart(fig, width="stretch")

    t = g.set_index(["estadio", "play_type"])["epa_prom"]
    try:
        brecha = {e: t[(e, "pass")] - t[(e, "run")] for e in ["Aire libre", "Techo cerrado"]}
        col2.markdown(
            f"**Ventaja del pase sobre la carrera** (EPA por jugada)\n\n"
            f"- Aire libre: **{brecha['Aire libre']:+.3f}**\n"
            f"- Techo cerrado: **{brecha['Techo cerrado']:+.3f}**\n\n"
        )
    except KeyError:
        col2.info("No hay jugadas de los dos tipos de estadio con estos filtros.")

    # ---- Clima ------------------------------------------------------------------
    st.divider()
    con_datos = [k for k, v in CONDICIONES.items() if partidos[v[1]].notna().any()]
    if not con_datos:
        st.info("No hay datos de temperatura, viento ni humedad en partidos.parquet.")
        return
    c = st.columns([3, 1])
    c[0].subheader("Clima: el balón en el aire")
    cond_lbl = c[1].selectbox("Condición", con_datos, key="clima_condicion")
    mostrar_balon(filtrar, cond_lbl)