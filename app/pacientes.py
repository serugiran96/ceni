"""Página 1: lista de pacientes del centro."""

import streamlit as st

from app.formato import fecha_texto
from backend import db

st.title("Pacientes")
st.caption("Centro de terapia infantil de demostración · 3 sedes en Lima")

for p in db.listar_pacientes():
    with st.container(border=True):
        datos, motivo, accion = st.columns([3, 5, 1.4], vertical_alignment="center")
        datos.markdown(f"**{p['nombre']}** · {p['edad']}")
        datos.caption(f"{p['especialidad']} · {p['terapeuta']} · Sede {p['sede']}")
        motivo.markdown(p["motivo_consulta"])
        motivo.caption(f"{p['n_sesiones']} sesiones · última: {fecha_texto(p['ultima_sesion'])}")
        if accion.button("Abrir ficha", key=f"abrir_{p['id']}", type="primary"):
            st.session_state["paciente_id"] = p["id"]  # la ficha lee este valor
            st.switch_page("app/ficha.py")
