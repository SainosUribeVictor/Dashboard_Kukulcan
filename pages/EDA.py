import pandas as pd
import plotly.express as px
import streamlit as st

from src.datos import cargar
from src.estilo import (AZUL, COLORES_PLAYOFF, COLORES_TEMPORADA, COLORES_TIPO,
                        ESCALA_PASE, CARRERA, PASE, VERDE)

COLORES = {"pass": PASE, "run": CARRERA}
NOMBRES = {"pass": "Pase", "run": "Carrera"}
ORDEN = {
    "distancia": ["Corta (1-3)", "Media (4-6)", "Larga (7-10)", "Muy larga (11+)"],
    "marcador": ["Pierde 9+", "Pierde 1-8", "Empate", "Gana 1-8", "Gana 9+"],
    "campo": ["Fondo propio (81-99)", "Campo propio (51-80)",
              "Campo rival (21-50)", "Zona roja (1-20)"],
}
DIMENSIONES = {
    "Down": "down", "Distancia por avanzar": "distancia",
    "Marcador (equipo ofensivo)": "marcador", "Posición en el campo": "campo",
    "Temporada": "season",
}

# ---------------------------------------------------------------------------
# Datos
# ---------------------------------------------------------------------------
agr = cargar("eda_jugadas_agregado")
mues = cargar("eda_jugadas_muestra")
partidos = cargar("partidos")
temp = cargar("equipo_temporada")

if agr is None:
    st.error("No se encontraron los archivos .prarquet en la carpeta src. "
             "Correr primero el script eda_resumen.")
    st.stop()

# ---------------------------------------------------------------------------
# Filtros globales (barra lateral)
# ---------------------------------------------------------------------------
st.sidebar.header("Filtros")
t_min, t_max = int(agr["season"].min()), int(agr["season"].max())
temporadas = st.sidebar.slider("Temporadas", t_min, t_max, (t_min, t_max)) if t_min < t_max else (t_min, t_max)
tipo_temp = st.sidebar.radio("Tipo de temporada", ["Regular", "Postemporada", "Ambas"], horizontal=True)
equipos = st.sidebar.multiselect("Equipos (vacío = todos)", sorted(agr["posteam"].dropna().unique()))

codigo_tipo = {"Regular": ["REG"], "Postemporada": ["POST"], "Ambas": ["REG", "POST"]}[tipo_temp]


def filtrar(df: pd.DataFrame, col_equipo: str | None = "posteam") -> pd.DataFrame:
    m = df["season"].between(*temporadas)
    if "season_type" in df:
        m &= df["season_type"].isin(codigo_tipo)
    if equipos and col_equipo and col_equipo in df:
        m &= df[col_equipo].isin(equipos)
    return df[m]


agr_f = filtrar(agr)
mues_f = filtrar(mues) if mues is not None else None

st.title("Análisis exploratorio")
st.caption(f"Temporadas {temporadas[0]}–{temporadas[1]} · {tipo_temp.lower()}"
           + (f" · equipos: {', '.join(equipos)}" if equipos else ""))

if agr_f.empty:
    st.warning("No hay jugadas con estos filtros.")
    st.stop()

tab_datos, tab_jugada, tab_partido, tab_temp = st.tabs(
    ["Datos", "Jugada", "Partido", "Temporada"])


def tasas(df: pd.DataFrame, por: list[str]) -> pd.DataFrame:
    g = df.groupby(por, observed=True)[["n", "exitos", "yardas", "air_yards", "epa"]].sum().reset_index()
    g["tasa_exito"] = g["exitos"] / g["n"]
    g["yardas_prom"] = g["yardas"] / g["n"]
    g["epa_prom"] = g["epa"] / g["n"]
    return g


def ordenar(fig, dim: str):
    if dim in ORDEN:
        fig.update_xaxes(categoryorder="array", categoryarray=ORDEN[dim])
    elif dim == "down":
        fig.update_xaxes(type="category", categoryorder="category ascending")
    elif dim == "season":
        fig.update_xaxes(dtick=1)
    return fig


# ===========================================================================
# DATOS
# ===========================================================================
with tab_datos:
    TIPO_NOMBRE = {"REG": "Regular", "POST": "Postemporada"}
    st.caption("Desde 2021 la temporada regular tiene 17 juegos (antes 16); por eso, al comparar "
               "temporadas.")

    p = filtrar(partidos, col_equipo=None) if partidos is not None else None
    if p is not None and equipos:
        p = p[p["home_team"].isin(equipos) | p["away_team"].isin(equipos)]

    tipos = cargar("eda_tipos_jugada")
    if tipos is not None and "season" in tipos:
        tipos = filtrar(tipos)

    c = st.columns(4)
    if tipos is not None:
        c[0].metric("Jugadas", f"{int(tipos['n'].sum()):,}")
    if p is not None:
        c[1].metric("Partidos", f"{len(p):,}")
        c[2].metric("Temporadas", p["season"].nunique())
        c[3].metric("Semanas", p["week"].nunique())

    if p is not None and not p.empty:
        p = p.assign(Tipo=p["season_type"].map(TIPO_NOMBRE))
        col1, col2 = st.columns(2)

        g = p.groupby(["season", "Tipo"]).size().reset_index(name="partidos")
        fig = px.bar(g, x="season", y="partidos", color="Tipo", color_discrete_map=COLORES_TEMPORADA,
                     title="Partidos por temporada",
                     labels={"season": "Temporada", "partidos": "Partidos", "Tipo": ""})
        fig.update_xaxes(dtick=1)
        col1.plotly_chart(fig, width="stretch")

        g = p.groupby(["week", "Tipo"]).size().reset_index(name="partidos")
        fig = px.bar(g, x="week", y="partidos", color="Tipo", color_discrete_map=COLORES_TEMPORADA,
                     title="Partidos por semana",
                     labels={"week": "Semana", "partidos": "Partidos", "Tipo": ""})
        fig.update_xaxes(dtick=1)
        col2.plotly_chart(fig, width="stretch")

    if p is not None and not p.empty:
        st.subheader("Resumen por temporada")
        res = (p.assign(puntos=p["home_score"] + p["away_score"])
               .groupby("season")
               .agg(partidos_regular=("season_type", lambda s: (s == "REG").sum()),
                    partidos_postemporada=("season_type", lambda s: (s == "POST").sum()),
                    puntos_por_partido=("puntos", "mean"),
                    pct_gana_local=("gana_local", "mean")))
        pj = agr_f.groupby(["season", "play_type"])["n"].sum().unstack(fill_value=0)
        res["jugadas_pase_carrera"] = pj.sum(axis=1)
        res["pct_pases"] = pj.get("pass", 0) / pj.sum(axis=1)
        res["pct_pases"] *= 100
        res["pct_gana_local"] *= 100
        res = res.reset_index().sort_values("season", ascending=False)
        st.dataframe(
            res, hide_index=True, width="stretch",
            column_config={
                "season": st.column_config.NumberColumn("Temporada", format="%d"),
                "partidos_regular": "Partidos regular",
                "partidos_postemporada": "Partidos postemporada",
                "jugadas_pase_carrera": st.column_config.NumberColumn("Jugadas (pase/carrera)", format="%d"),
                "pct_pases": st.column_config.ProgressColumn("% pases", format="%.1f%%", min_value=0, max_value=100),
                "puntos_por_partido": st.column_config.NumberColumn("Puntos por partido", format="%.1f"),
                "pct_gana_local": st.column_config.ProgressColumn("% gana local", format="%.1f%%", min_value=0, max_value=100),
            },
            column_order=["season", "partidos_regular", "partidos_postemporada", "jugadas_pase_carrera",
                          "pct_pases", "puntos_por_partido", "pct_gana_local"],
        )

    if tipos is not None and not tipos.empty:
        t = tipos.groupby("play_type")["n"].sum().reset_index()
        fig = px.bar(t, x="n", y="play_type", orientation="h", title="Jugadas por tipo",
                     color_discrete_sequence=[AZUL],
                     labels={"n": "Jugadas", "play_type": ""})
        fig.update_yaxes(categoryorder="total ascending")
        st.plotly_chart(fig, width="stretch")

# ===========================================================================
# JUGADA
# ===========================================================================
with tab_jugada:
    objetivo = st.radio("Variable objetivo",
                        ["Pase vs carrera", "Éxito de la jugada", "Yardas ganadas", "Yardas por aire"],
                        horizontal=True)

    # ---- Pase vs carrera --------------------------------------------------
    if objetivo == "Pase vs carrera":
        tot = agr_f.groupby("play_type")["n"].sum()
        pct_pase = tot.get("pass", 0) / tot.sum()
        c = st.columns(3)
        c[0].metric("% pases", f"{pct_pase:.1%}")
        c[1].metric("% carreras", f"{1 - pct_pase:.1%}")
        c[2].metric("Jugadas", f"{int(tot.sum()):,}")

        dim_lbl = st.selectbox("¿Cómo cambia la decisión según…?", list(DIMENSIONES))
        dim = DIMENSIONES[dim_lbl]
        g = agr_f.groupby([dim, "play_type"], observed=True)["n"].sum().reset_index()
        g["pct"] = g["n"] / g.groupby(dim)["n"].transform("sum")
        g["Tipo"] = g["play_type"].map(NOMBRES)

        fig = px.bar(g, x=dim, y="pct", color="Tipo", barmode="stack",
                     color_discrete_map=COLORES_TIPO,
                     title=f"Proporción pase/carrera por {dim_lbl.lower()}",
                     labels={"pct": "Proporción", dim: dim_lbl},
                     hover_data={"n": ":,"})
        ordenar(fig, dim)
        fig.update_yaxes(tickformat=".0%")
        st.plotly_chart(fig, width="stretch")

        # Mapa de calor: down × la dimensión elegida (si eligen down, se cruza con distancia)
        dim2, dim2_lbl = (("distancia", "Distancia por avanzar") if dim == "down" else (dim, dim_lbl))
        st.subheader(f"Mapa de decisión: down × {dim2_lbl.lower()}")
        h = agr_f.groupby(["down", dim2, "play_type"], observed=True)["n"].sum().unstack(fill_value=0)
        h["pct_pase"] = h.get("pass", 0) / h.drop(columns="pct_pase", errors="ignore").sum(axis=1)
        mapa = h["pct_pase"].unstack(dim2)
        if dim2 in ORDEN:
            mapa = mapa.reindex(columns=ORDEN[dim2])
        mapa.columns = mapa.columns.astype(str)
        mapa.index = mapa.index.astype(str)
        fig = px.imshow(mapa, text_auto=".0%", color_continuous_scale=ESCALA_PASE, zmin=0, zmax=1,
                        labels={"x": dim2_lbl, "y": "Down", "color": "% pases"}, aspect="auto")
        fig.update_xaxes(type="category")
        fig.update_yaxes(type="category")
        st.plotly_chart(fig, width="stretch")

    # ---- Éxito -----------------------------------------------------------
    elif objetivo == "Éxito de la jugada":
        t = tasas(agr_f, ["play_type"]).set_index("play_type")
        c = st.columns(3)
        c[0].metric("Tasa de éxito global", f"{agr_f['exitos'].sum() / agr_f['n'].sum():.1%}")
        if "pass" in t.index:
            c[1].metric("Éxito en pases", f"{t.loc['pass', 'tasa_exito']:.1%}")
        if "run" in t.index:
            c[2].metric("Éxito en carreras", f"{t.loc['run', 'tasa_exito']:.1%}")

        dim_lbl = st.selectbox("Tasa de éxito según…", list(DIMENSIONES))
        dim = DIMENSIONES[dim_lbl]
        g = tasas(agr_f, [dim, "play_type"])
        g["Tipo"] = g["play_type"].map(NOMBRES)
        cmap = {"Pase": COLORES["pass"], "Carrera": COLORES["run"]}
        if dim == "season":
            fig = px.line(g, x=dim, y="tasa_exito", color="Tipo", markers=True,
                          color_discrete_map=cmap, labels={"tasa_exito": "Tasa de éxito", dim: dim_lbl})
        else:
            fig = px.bar(g, x=dim, y="tasa_exito", color="Tipo", barmode="group",
                         color_discrete_map=cmap, hover_data={"n": ":,"},
                         labels={"tasa_exito": "Tasa de éxito", dim: dim_lbl})
            ordenar(fig, dim)
        fig.update_yaxes(tickformat=".0%")
        fig.update_layout(title=f"Tasa de éxito por {dim_lbl.lower()} y tipo de jugada")
        st.plotly_chart(fig, width="stretch")
        st.caption("En nflfastR una jugada es exitosa cuando su EPA es positivo.")

    # ---- Yardas ganadas ----------------------------------------------------
    elif objetivo == "Yardas ganadas":
        if mues_f is None or mues_f.empty:
            st.info("No hay muestra de jugadas con estos filtros.")
        else:
            c = st.columns(4)
            y = mues_f["yards_gained"]
            c[0].metric("Media", f"{y.mean():.2f}")
            c[1].metric("Mediana", f"{y.median():.0f}")
            c[2].metric("Desv. estándar", f"{y.std():.2f}")
            c[3].metric("% jugadas de 20+ yardas", f"{(y >= 20).mean():.1%}")

            col1, col2 = st.columns([3, 1])
            rango = col2.slider("Rango de yardas", -20, 99, (-10, 40))
            separar = col2.checkbox("Separar pase / carrera", True)
            d = mues_f[mues_f["yards_gained"].between(*rango)].copy()
            d["Tipo"] = d["play_type"].map(NOMBRES)
            fig = px.histogram(d, x="yards_gained", color="Tipo" if separar else None,
                               barmode="overlay", opacity=0.65, nbins=rango[1] - rango[0] + 1,
                               histnorm="probability",
                               color_discrete_map=COLORES_TIPO,
                               labels={"yards_gained": "Yardas ganadas"},
                               title="Distribución de yardas ganadas")
            fig.update_yaxes(title="Proporción", tickformat=".0%")
            col1.plotly_chart(fig, width="stretch")
            st.caption(f"Basado en una muestra de {len(mues_f):,} jugadas. "
                       "La distribución es asimétrica con cola larga a la derecha "
                       "(jugadas explosivas), lo que conviene considerar al modelar.")

            dim_lbl = st.selectbox("Yardas promedio según…", list(DIMENSIONES))
            dim = DIMENSIONES[dim_lbl]
            g = tasas(agr_f, [dim, "play_type"])
            g["Tipo"] = g["play_type"].map(NOMBRES)
            fig = px.bar(g, x=dim, y="yardas_prom", color="Tipo", barmode="group",
                         color_discrete_map=COLORES_TIPO,
                         labels={"yardas_prom": "Yardas promedio", dim: dim_lbl},
                         title=f"Yardas promedio por {dim_lbl.lower()}")
            ordenar(fig, dim)
            st.plotly_chart(fig, width="stretch")

    # ---- Yardas por aire ---------------------------------------------------
    else:
        pases = mues_f[(mues_f["play_type"] == "pass") & mues_f["air_yards"].notna()] if mues_f is not None else None
        if pases is None or pases.empty:
            st.info("No hay pases en la muestra con estos filtros.")
        else:
            st.info("`air_yards` solo existe en pases: el modelo de esta variable se entrena "
                    "únicamente con jugadas de pase.")
            c = st.columns(4)
            a = pases["air_yards"]
            c[0].metric("Media", f"{a.mean():.2f}")
            c[1].metric("Mediana", f"{a.median():.0f}")
            c[2].metric("% pases detrás de la línea", f"{(a < 0).mean():.1%}")
            c[3].metric("% pases profundos (20+)", f"{(a >= 20).mean():.1%}")

            col1, col2 = st.columns(2)
            fig = px.histogram(pases, x="air_yards", nbins=70, histnorm="probability",
                               color_discrete_sequence=[COLORES["pass"]],
                               labels={"air_yards": "Yardas por aire"},
                               title="Distribución de yardas por aire")
            fig.update_yaxes(title="Proporción", tickformat=".0%")
            col1.plotly_chart(fig, width="stretch")

            d = pases.dropna(subset=["down"]).copy()
            d["down"] = d["down"].astype(int).astype(str)
            fig = px.box(d.sort_values("down"), x="down", y="air_yards", points=False,
                         color_discrete_sequence=[COLORES["pass"]],
                         labels={"air_yards": "Yardas por aire", "down": "Down"},
                         title="Yardas por aire según down")
            col2.plotly_chart(fig, width="stretch")

            g = agr_f[agr_f["play_type"] == "pass"].groupby("season")[["air_yards", "n"]].sum().reset_index()
            g["air_prom"] = g["air_yards"] / g["n"]
            fig = px.line(g, x="season", y="air_prom", markers=True, color_discrete_sequence=[PASE],
                          labels={"air_prom": "Yardas por aire promedio", "season": "Temporada"},
                          title="Yardas por aire promedio por temporada")
            st.plotly_chart(fig, width="stretch")

# ===========================================================================
# PARTIDO
# ===========================================================================
with tab_partido:
    if partidos is None:
        st.info("Falta el archivo partidos.parquet.")
    else:
        p = filtrar(partidos, col_equipo=None)
        if equipos:
            p = p[p["home_team"].isin(equipos) | p["away_team"].isin(equipos)]
        if p.empty:
            st.warning("No hay partidos con estos filtros.")
        else:
            c = st.columns(4)
            c[0].metric("Partidos", f"{len(p):,}")
            c[1].metric("% gana local", f"{p['gana_local'].mean():.1%}")
            c[2].metric("% empates", f"{(p['resultado'] == 'Empate').mean():.1%}")
            c[3].metric("Diferencia media (local − visita)", f"{p['diferencia'].mean():+.2f}")

            col1, col2 = st.columns(2)
            g = p.groupby("season").agg(pct=("gana_local", "mean"), n=("gana_local", "size")).reset_index()
            fig = px.line(g, x="season", y="pct", markers=True, hover_data={"n": True},
                          color_discrete_sequence=[VERDE],
                          labels={"pct": "% victorias del local", "season": "Temporada"},
                          title="Ventaja de local por temporada")
            fig.add_hline(y=0.5, line_dash="dot", annotation_text="50%")
            fig.update_yaxes(tickformat=".0%")
            col1.plotly_chart(fig, width="stretch")

            fig = px.histogram(p, x="diferencia", nbins=60, color_discrete_sequence=[VERDE],
                               labels={"diferencia": "Puntos local − visitante"},
                               title="Distribución de la diferencia de puntos")
            fig.add_vline(x=0, line_dash="dot")
            col2.plotly_chart(fig, width="stretch")
            st.caption("Los picos en ±3 y ±7 reflejan los márgenes típicos de un gol de campo o un touchdown.")

            with st.expander("Ver tabla de partidos"):
                st.dataframe(p.sort_values(["season", "week"], ascending=False)
                             [["season", "week", "season_type", "home_team", "home_score",
                               "away_score", "away_team", "resultado"]],
                             width="stretch", hide_index=True)

# ===========================================================================
# TEMPORADA
# ===========================================================================
with tab_temp:
    if temp is None:
        st.info("Falta el archivo equipo_temporada.parquet.")
    else:
        t = temp[temp["season"].between(*temporadas)]
        if equipos:
            t = t[t["equipo"].isin(equipos)]
        if t.empty:
            st.warning("No hay equipos con estos filtros.")
        else:
            st.caption("Calculado con temporada regular. Playoffs = el equipo jugó al menos un partido de postemporada.")
            t = t.assign(Playoffs=t["clasifica_playoffs"].map({1: "Sí", 0: "No"}))
            pmap = COLORES_PLAYOFF

            c = st.columns(3)
            c[0].metric("Equipo-temporadas", len(t))
            c[1].metric("% clasifica a playoffs", f"{t['clasifica_playoffs'].mean():.1%}")
            c[2].metric("Victorias promedio de quien clasifica",
                        f"{t.loc[t['clasifica_playoffs'] == 1, 'victorias'].mean():.1f}")

            usar_pct = st.toggle("Usar % de victorias", True)
            yv, ylab = ("pct_victorias", "% de victorias") if usar_pct else ("victorias", "Victorias")

            col1, col2 = st.columns(2)
            fig = px.histogram(t, x=yv, color="Playoffs", barmode="stack", nbins=18,
                               color_discrete_map=pmap, labels={yv: ylab},
                               title=f"Distribución de {ylab.lower()}")
            if usar_pct:
                fig.update_xaxes(tickformat=".0%")
            col1.plotly_chart(fig, width="stretch")

            metricas = {"Diferencia de puntos": "dif_puntos", "Puntos a favor": "puntos_favor",
                        "Puntos en contra": "puntos_contra", "EPA ofensiva por jugada": "epa_ofensiva",
                        "EPA permitida por jugada": "epa_permitida", "Tasa de éxito ofensiva": "exito_ofensivo",
                        "Yardas por jugada": "yardas_jugada", "% de pases": "pct_pase"}
            x_lbl = col2.selectbox("Relación con…", list(metricas))
            xv = metricas[x_lbl]
            fig = px.scatter(t, x=xv, y=yv, color="Playoffs", color_discrete_map=pmap,
                             hover_data=["equipo", "season", "victorias", "derrotas"],
                             trendline=None, labels={xv: x_lbl, yv: ylab},
                             title=f"{ylab} vs {x_lbl.lower()}")
            corr = t[[xv, yv]].corr().iloc[0, 1]
            col2.plotly_chart(fig, width="stretch")
            col2.caption(f"Correlación: **{corr:.2f}**")

            st.subheader("Clasificación por temporada")
            temporada_sel = st.selectbox("Temporada", sorted(t["season"].unique(), reverse=True))
            r = t[t["season"] == temporada_sel].sort_values(yv)
            fig = px.bar(r, x=yv, y="equipo", color="Playoffs", orientation="h",
                         color_discrete_map=pmap, labels={yv: ylab, "equipo": ""},
                         hover_data=["victorias", "derrotas", "dif_puntos"],
                         height=max(300, 22 * len(r)))
            fig.update_yaxes(categoryorder="array", categoryarray=r["equipo"].tolist())
            if usar_pct:
                fig.update_xaxes(tickformat=".0%")
            st.plotly_chart(fig, width="stretch")