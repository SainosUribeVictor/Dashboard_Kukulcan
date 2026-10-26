"""Carga de los archivos .parquet que están en esta misma carpeta (src)."""
from pathlib import Path

import pandas as pd
import streamlit as st

CARPETA = Path(__file__).resolve().parent


@st.cache_data
def cargar(nombre):
    """Lee src/<nombre>.parquet; regresa None si no existe."""
    ruta = CARPETA / f"{nombre}.parquet"
    if not ruta.exists():
        return None
    return pd.read_parquet(ruta)