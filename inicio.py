import streamlit as st

from src.datos import cargar

st.title("Kukulcán")
st.markdown("#### Análisis exploratorio de jugadas de la NFL")

partidos = cargar("partidos")
tipos = cargar("eda_tipos_jugada")
temp = cargar("equipo_temporada")

if partidos is not None:
    t_min, t_max = int(partidos["season"].min()), int(partidos["season"].max())
    c = st.columns(4)
    if tipos is not None:
        c[0].metric("Jugadas", f"{int(tipos['n'].sum()):,}")
    c[1].metric("Partidos", f"{len(partidos):,}")
    c[2].metric("Temporadas", f"{t_min}–{t_max}")
    c[3].metric("Equipos", partidos["home_team"].nunique())

st.markdown(
    """
Este tablero reúne el análisis exploratorio de los datos *play-by-play* de **nflfastR**:
una fila por jugada, con la situación de juego, el resultado de cada acción y el marcador.
El objetivo es entender cómo se comportan los equipos en tres niveles —jugada, partido y
temporada— antes de construir los modelos.
"""
)

st.subheader("Qué encontrarás")
secciones = [
    ("Datos", "Cuántos partidos y jugadas hay por temporada y semana, qué tipos de jugada "
              "contiene el dataset y un resumen año por año."),
    ("Jugada", "Cómo se decide entre pase y carrera según down, distancia, marcador y posición; "
               "la tasa de éxito y la distribución de yardas ganadas y yardas por aire."),
    ("Partido", "La ventaja de jugar en casa a lo largo de las temporadas y cómo se distribuye "
                "la diferencia de puntos."),
    ("Temporada", "Victorias por equipo, su relación con el rendimiento ofensivo y defensivo, "
                  "y qué equipos llegan a playoffs."),
]
cols = st.columns(4)
for col, (titulo, texto) in zip(cols, secciones):
    with col.container(border=True):
        st.markdown(f"**{titulo}**")
        st.caption(texto)

st.markdown("")
st.page_link("pages/EDA.py", label="Ir al análisis exploratorio →")
