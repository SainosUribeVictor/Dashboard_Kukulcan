"""Colores de las gráficas y dibujos de "cuaderno de jugadas" en los costados."""
from urllib.parse import quote

import streamlit as st

# ---------------------------------------------------------------------------
# Colores de las gráficas (tomados de la paleta predeterminada de Streamlit).
# Así cada categoría tiene siempre el mismo color en todas las gráficas.
# ---------------------------------------------------------------------------
AZUL = "#0068C9"
NARANJA = "#FF8700"
VERDE = "#29B09D"
GRIS = "#7D8590"

MORADO = "#C77DFF"

# Pestaña Jugada: verde y morado
PASE, CARRERA = VERDE, MORADO
COLORES_TIPO = {"Pase": PASE, "Carrera": CARRERA}
COLORES_TEMPORADA = {"Regular": AZUL, "Postemporada": NARANJA}
COLORES_PLAYOFF = {"Sí": VERDE, "No": GRIS}
ESCALA_PASE = [[0, MORADO], [0.5, "#262730"], [1, VERDE]]   # % de pases en el mapa de calor

# Colores de los dibujos
TRAZO = "#31333F"   # X, O y bloqueos (gris oscuro, para fondo claro)
OPACIDAD = 0.18     # sube este número para que se vean más

_FLECHA = ("<defs><marker id='f' markerWidth='10' markerHeight='10' refX='7' refY='5' "
           "orient='auto'><path d='M1,1 L8,5 L1,9' fill='none' stroke='{c}' stroke-width='2'/></marker></defs>")


def _x(cx, cy, s=11):
    return f"<path d='M{cx-s} {cy-s} L{cx+s} {cy+s} M{cx+s} {cy-s} L{cx-s} {cy+s}'/>"


def _svg_izq():
    c, r = TRAZO, TRAZO
    return (
        "<svg xmlns='http://www.w3.org/2000/svg' width='230' height='1100' viewBox='0 0 230 1100' "
        f"fill='none' stroke='{c}' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'>"
        + _FLECHA.format(c=r) + "<g opacity='"+str(OPACIDAD)+"'>"
        # jugada 1: tres O con rutas
        + "<circle cx='50' cy='200' r='14'/><circle cx='110' cy='200' r='14'/><circle cx='170' cy='200' r='14'/>"
        + f"<path stroke='{r}' d='M50 184 L50 110 Q50 80 82 80 L135 80' marker-end='url(#f)'/>"
        + f"<path stroke='{r}' d='M170 184 L170 130 L205 95' marker-end='url(#f)'/>"
        + f"<path stroke='{r}' d='M110 184 L110 140 Q110 120 95 128' marker-end='url(#f)'/>"
        # defensa
        + _x(45, 360) + _x(115, 340) + _x(185, 360)
        # movimiento previo (punteado)
        + f"<path stroke='{r}' stroke-dasharray='7 10' d='M30 470 C80 430 140 520 195 470' marker-end='url(#f)'/>"
        # bloqueo
        + "<path d='M115 580 L115 640 M95 580 L135 580'/>"
        # jugada 2
        + _x(60, 760) + _x(160, 760)
        + "<circle cx='60' cy='900' r='14'/><circle cx='160' cy='900' r='14'/>"
        + f"<path stroke='{r}' d='M60 884 C60 820 120 820 120 770 L120 720' marker-end='url(#f)'/>"
        + f"<path stroke='{r}' d='M160 884 L160 830 L95 800' marker-end='url(#f)'/>"
        + "<path d='M40 1010 L190 1010' stroke-dasharray='2 12'/>"
        + "</g></svg>"
    )


def _svg_der():
    c, r = TRAZO, TRAZO
    return (
        "<svg xmlns='http://www.w3.org/2000/svg' width='230' height='1100' viewBox='0 0 230 1100' "
        f"fill='none' stroke='{c}' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'>"
        + _FLECHA.format(c=r) + "<g opacity='"+str(OPACIDAD)+"'>"
        + _x(60, 120) + _x(170, 120) + _x(115, 180)
        + f"<path stroke='{r}' d='M60 135 Q60 230 140 240' marker-end='url(#f)'/>"
        + "<circle cx='60' cy='380' r='14'/><circle cx='115' cy='380' r='14'/><circle cx='170' cy='380' r='14'/>"
        + "<path d='M100 410 L130 410'/>"
        + f"<path stroke='{r}' d='M170 364 L170 300 Q170 270 140 270 L95 270' marker-end='url(#f)'/>"
        + f"<path stroke='{r}' d='M60 364 L60 290' marker-end='url(#f)'/>"
        + f"<path stroke='{r}' stroke-dasharray='7 10' d='M200 520 C150 560 90 480 35 530' marker-end='url(#f)'/>"
        + "<circle cx='115' cy='680' r='14'/>"
        + f"<path stroke='{r}' d='M115 664 L115 600 Q115 570 145 575 Q175 585 170 615' marker-end='url(#f)'/>"
        + _x(50, 820) + _x(180, 820)
        + "<path d='M50 840 L50 900 M35 900 L65 900'/>"
        + "<circle cx='115' cy='980' r='14'/><path d='M101 966 L129 994 M129 966 L101 994' stroke-width='1.5'/>"
        + "</g></svg>"
    )


def _uri(svg):
    return "url(\"data:image/svg+xml;utf8," + quote(svg) + "\")"


def aplicar_estilo():
    """Agrega solo los dibujos; no cambia ningún color de Streamlit."""
    izq, der = _uri(_svg_izq()), _uri(_svg_der())
    st.markdown(
        f"""
<style>
[data-testid="stMain"], section.main {{
    background-image: {izq}, {der};
    background-repeat: repeat-y, repeat-y;
    background-position: left 10px top 60px, right 10px top 60px;
    background-size: 140px auto, 140px auto;
}}
@media (min-width: 1200px) {{
    [data-testid="stMainBlockContainer"], .block-container {{ padding-left: 170px; padding-right: 170px; }}
}}
</style>
""",
        unsafe_allow_html=True,
    )