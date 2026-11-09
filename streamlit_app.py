"""Punto de entrada de Ceni: `streamlit run streamlit_app.py`.

Prepara la clave y la base de datos, dibuja la barra lateral y decide qué
página mostrar (agenda, pacientes o ficha).
"""

import os

import streamlit as st

from backend import db

st.set_page_config(page_title="Ceni", page_icon=":material/graphic_eq:", layout="wide")

# En Streamlit Cloud la clave vive en st.secrets. La copiamos a una variable de
# entorno para que el código de ai/ funcione igual en la laptop y en la nube.
try:
    for nombre in ("OPENAI_API_KEY", "OPENAI_MODEL"):
        if nombre in st.secrets:
            os.environ[nombre] = st.secrets[nombre]
except Exception:  # en la laptop no hay secrets.toml: se usa el .env
    pass


@st.cache_resource  # se ejecuta una sola vez por servidor, no en cada clic
def iniciar_base() -> bool:
    db.crear_base()
    return True


iniciar_base()

with st.sidebar:
    st.markdown("## Ceni")
    st.caption("El médico graba la consulta. Ceni arma el resumen, la historia clínica y la receta para que el médico los revise.")
    st.info("Ceni documenta: no diagnostica ni receta por su cuenta. Todos los pacientes de este demo son inventados.", icon=":material/info:")
    if st.button("Restaurar datos del demo", icon=":material/restart_alt:"):
        db.crear_base(desde_cero=True)
        st.session_state.clear()
        st.rerun()

pagina = st.navigation(
    [
        st.Page("app/agenda.py", title="Agenda", icon=":material/calendar_month:", default=True),
        st.Page("app/pacientes.py", title="Pacientes", icon=":material/groups:"),
        st.Page("app/ficha.py", title="Ficha del paciente", icon=":material/folder_shared:"),
    ]
)
pagina.run()
