"""Punto de entrada de Ceni: `streamlit run streamlit_app.py`.

Prepara la clave y la base de datos, aplica el estilo, dibuja la barra
lateral (logo, menú y quién entra: el admin o un médico) y decide qué páginas mostrar.
"""

import base64
import os
import time
from html import escape
from pathlib import Path

import streamlit as st

from app import estilo
from backend import db

# Streamlit Cloud corre en hora UTC: a las 7 p. m. de Lima allá ya es el día
# siguiente. Fijamos la hora de Lima para que "hoy", las citas y las firmas cuadren.
os.environ["TZ"] = "America/Lima"
time.tzset()

ASSETS = Path(__file__).resolve().parent / "assets"
# El logo va dentro de la página (base64): con st.image, Streamlit Cloud a veces pierde la imagen al redibujar.
LOGO_BLANCO = base64.b64encode((ASSETS / "logo-blanco.png").read_bytes()).decode()

st.set_page_config(page_title="Ceni", page_icon=str(ASSETS / "icono.png"), layout="wide", initial_sidebar_state="auto")
estilo.aplicar()

# En Streamlit Cloud la clave vive en st.secrets. La copiamos a una variable de
# entorno para que el código de ai/ funcione igual en la laptop y en la nube.
try:
    for nombre in ("OPENAI_API_KEY", "GROQ_API_KEY", "OPENAI_MODEL"):
        if nombre in st.secrets:
            os.environ[nombre] = st.secrets[nombre]
except Exception:  # en la laptop no hay secrets.toml: se usa el .env
    pass


@st.cache_resource  # se ejecuta una vez por servidor y por versión de la base, no en cada clic
def iniciar_base(version: int) -> bool:
    db.crear_base()  # si la base es de otra versión, la vuelve a crear con la semilla
    return True


# La versión va como argumento: cuando sube (p. ej., al agregar una columna), la caché
# no sirve y la base se recrea, aunque Streamlit Cloud actualice el código sin reiniciar.
iniciar_base(db.VERSION_ESQUEMA)

# Para volver a los datos del demo antes de presentar: abrir la app con ?reiniciar
if "reiniciar" in st.query_params:
    db.crear_base(desde_cero=True)
    st.session_state.clear()
    st.query_params.clear()

# Color del avatar en la barra lateral: el admin en coral; los médicos rotan entre estos.
AVATAR_ADMIN = "#FF6F61,#C2255C"
AVATARES = ["#FFB020,#FF7A59", "#38D9A9,#4DABF7", "#B197FC,#5B47FB", "#FF8787,#F06595"]

# Quién entra. En el demo se elige en la barra lateral; en producción sería un inicio de sesión.
# "admin" es Melina (da de alta consultorios, médicos y plantillas); "m<id>" es un médico.
usuarios = {"admin": None} | {f"m{m['id']}": m for m in db.medicos()}
if st.session_state.get("usuario") not in usuarios:
    st.session_state["usuario"] = "m1"
medico = usuarios[st.session_state["usuario"]]
if medico:
    st.session_state["medico_id"] = medico["id"]  # las páginas leen este valor

if medico:
    paginas = [
        st.Page("app/agenda.py", title="Agenda", icon=":material/calendar_month:", default=True),
        st.Page("app/pacientes.py", title="Pacientes", icon=":material/groups:"),
        st.Page("app/ficha.py", title="Ficha del paciente", icon=":material/folder_shared:"),
        st.Page("app/metricas.py", title="Mis métricas", icon=":material/insights:"),
    ]
else:
    paginas = [st.Page("app/admin.py", title="Panel de admin", icon=":material/admin_panel_settings:", default=True)]
pagina = st.navigation(paginas, position="hidden")  # el menú lo dibujamos abajo, debajo del logo


def nombre_usuario(clave: str) -> str:
    if clave == "admin":
        return f"{db.admin()['nombre']} · Admin"
    return f"{usuarios[clave]['nombre']} · {usuarios[clave]['consultorio']}"


with st.sidebar:
    estilo.html(f'<img src="data:image/png;base64,{LOGO_BLANCO}" alt="Ceni" width="200">')  # el logo en blanco
    estilo.html('<p class="ceni-lema">Tú atiendes. Ceni escribe la historia clínica y la receta.</p>')
    st.write("")
    for p in paginas:
        st.page_link(p, width="stretch")
    st.write("")
    st.selectbox("Entrar como", list(usuarios), format_func=nombre_usuario, key="usuario")
    if medico:
        nombre = medico["nombre"].split()
        iniciales, titulo, detalle = f"{nombre[1][0]}{nombre[-1][0]}", medico["nombre"], medico["especialidad"]
        color = AVATARES[(medico["id"] - 1) % len(AVATARES)]
    else:
        nombre = db.admin()["nombre"].split()
        iniciales, titulo, detalle = f"{nombre[0][0]}{nombre[-1][0]}", db.admin()["nombre"], db.admin()["rol"]
        color = AVATAR_ADMIN
    estilo.html(
        '<div class="ceni-medico">'
        f'<div class="ceni-avatar" style="background:linear-gradient(135deg,{color})">{iniciales}</div>'
        f'<div><div class="ceni-nombre" style="font-size:.98rem">{escape(titulo)}</div>'
        f'<div class="ceni-meta">{escape(detalle)}</div></div></div>'
    )

pagina.run()
