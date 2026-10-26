import streamlit as st

from src.estilo import aplicar_estilo

st.set_page_config(page_title="Kukulcán", layout="wide")
aplicar_estilo()

pagina = st.navigation([
    st.Page("inicio.py", title="Kukulcán", default=True),
    st.Page("pages/EDA.py", title="Análisis exploratorio"),
])
pagina.run()