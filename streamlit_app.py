"""Punto de entrada de Ceni: `streamlit run streamlit_app.py`.

Prepara la clave y la base de datos, aplica el estilo, dibuja la barra
lateral (logo, menú y médico) y decide qué página mostrar.
"""

import os
from pathlib import Path

import streamlit as st

from app import estilo
from backend import db

ASSETS = Path(__file__).resolve().parent / "assets"

st.set_page_config(page_title="Ceni", page_icon=str(ASSETS / "icono.png"), layout="wide", initial_sidebar_state="expanded")
estilo.aplicar()

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

# Para volver a los datos del demo antes de presentar: abrir la app con ?reiniciar
if "reiniciar" in st.query_params:
    db.crear_base(desde_cero=True)
    st.session_state.clear()
    st.query_params.clear()

paginas = [
    st.Page("app/agenda.py", title="Agenda", icon=":material/calendar_month:", default=True),
    st.Page("app/pacientes.py", title="Pacientes", icon=":material/groups:"),
    st.Page("app/ficha.py", title="Ficha del paciente", icon=":material/folder_shared:"),
]
pagina = st.navigation(paginas, position="hidden")  # el menú lo dibujamos abajo, debajo del logo

with st.sidebar:
    st.image(str(ASSETS / "logo-blanco.png"), width=200)  # el logo en blanco, sobre la barra oscura
    estilo.html('<p class="ceni-lema">Tú atiendes. Ceni escribe la historia clínica y la receta.</p>')
    st.write("")
    for p in paginas:
        st.page_link(p, width="stretch")
    st.write("")
    medico = db.medico()
    nombre = medico["nombre"].split()
    estilo.html(
        '<div class="ceni-medico">'
        '<div class="ceni-avatar" style="background:linear-gradient(135deg,#FFB020,#FF7A59)">'
        f'{nombre[1][0]}{nombre[-1][0]}</div>'
        f'<div><div class="ceni-nombre" style="font-size:.98rem">{medico["nombre"]}</div>'
        f'<div class="ceni-meta">{medico["especialidad"]}</div></div></div>'
    )

pagina.run()
