"""Página: lista de pacientes (con buscador) y registro de pacientes nuevos."""

from datetime import date
from html import escape

import streamlit as st

from app import estilo
from app.formato import chips_paciente, cuando_texto, fecha_corta
from backend import db

COLUMNAS = 3


@st.dialog("Registrar paciente nuevo", width="large")
def registrar() -> None:
    with st.form("nuevo_paciente", border=False):
        izquierda, derecha = st.columns(2)
        nombre = izquierda.text_input("Nombre completo")
        nacimiento = derecha.date_input(
            "Fecha de nacimiento", value=None, min_value=date(2005, 1, 1), max_value=date.today(), format="DD/MM/YYYY"
        )
        sexo = izquierda.selectbox("Sexo", ["Femenino", "Masculino"])
        apoderado = derecha.text_input("Apoderado (nombre y parentesco)", placeholder="Ana Pérez (mamá)")
        distrito = izquierda.text_input("Distrito")
        colegio = derecha.text_input("Colegio o nivel", placeholder="2.º grado de primaria")
        seguro = izquierda.selectbox("Seguro", ["Particular", "EPS", "EsSalud", "SIS"])
        st.caption("En este demo usa solo datos inventados.")
        if st.form_submit_button("Registrar y abrir la ficha", type="primary", icon=":material/person_add:"):
            if not (nombre.strip() and nacimiento and apoderado.strip()):
                st.error("Completa al menos el nombre, la fecha de nacimiento y el apoderado.")
            else:
                st.session_state["paciente_id"] = db.crear_paciente({
                    "nombre": nombre.strip(), "fecha_nacimiento": nacimiento.isoformat(), "sexo": sexo,
                    "apoderado": apoderado.strip(), "distrito": distrito.strip(),
                    "colegio": colegio.strip(), "seguro": seguro,
                })
                st.session_state["ir_a_pestana"] = "Nueva atención"
                st.switch_page("app/ficha.py")


todos = db.listar_pacientes()
titulo, boton = st.columns([3, 1], vertical_alignment="bottom")
with titulo:
    estilo.encabezado("Pacientes", f"{len(todos)} pacientes en seguimiento", "Neuropediatría")
if boton.button("Paciente nuevo", type="primary", icon=":material/person_add:", width="stretch"):
    registrar()

buscar = st.text_input("Buscar paciente", placeholder="Nombre o apellido", icon=":material/search:",
                       label_visibility="collapsed")
pacientes = db.listar_pacientes(buscar)
if not pacientes:
    st.info("No hay pacientes con ese nombre.", icon=":material/search_off:")

for inicio in range(0, len(pacientes), COLUMNAS):
    for columna, p in zip(st.columns(COLUMNAS), pacientes[inicio:inicio + COLUMNAS]):
        with columna, st.container(key=f"tarjeta-paciente-{p['id']}", height="stretch"):
            estilo.html(estilo.persona(p["nombre"], p["id"], f"{p['edad']} · {p['sexo']} · {p['hc']}"))
            estilo.html(chips_paciente(p["diagnosticos"], p["alergias"]) or '<p class="ceni-vacio">Sin diagnóstico registrado</p>')
            ultima = fecha_corta(p["ultima_atencion"]) if p["ultima_atencion"] else "—"
            proxima = p["proxima_cita"]
            proxima_texto = f"{cuando_texto(proxima[:10]).capitalize()}, {proxima[11:]}" if proxima else "Sin cita"
            estilo.html(
                '<div class="ceni-datos" style="grid-template-columns:1fr 1fr;gap:.6rem;margin:.3rem 0 .2rem">'
                f'<div class="ceni-dato">{estilo.etiqueta("Atenciones")}<div class="valor">{p["n_atenciones"]} · última {escape(ultima)}</div></div>'
                f'<div class="ceni-dato">{estilo.etiqueta("Próxima cita")}<div class="valor">{escape(proxima_texto)}</div></div>'
                "</div>"
            )
            if st.button("Abrir ficha", key=f"abrir_{p['id']}", icon=":material/folder_shared:", width="stretch"):
                st.session_state["paciente_id"] = p["id"]  # la ficha lee este valor
                st.session_state["cita_id"] = None
                st.session_state["ir_a_pestana"] = "Historia clínica"
                st.switch_page("app/ficha.py")
