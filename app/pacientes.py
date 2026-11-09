"""Página 1: lista de pacientes y registro de pacientes nuevos."""

from datetime import date

import streamlit as st

from app.formato import diagnostico_texto, fecha_texto
from backend import db

medico = db.medico()
st.title("Pacientes")
st.caption(f"{medico['nombre']} · {medico['especialidad']}")

with st.expander("Registrar paciente nuevo", icon=":material/person_add:"):
    with st.form("nuevo_paciente", clear_on_submit=True):
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
        if st.form_submit_button("Registrar", type="primary"):
            if not (nombre.strip() and nacimiento and apoderado.strip()):
                st.error("Completa al menos el nombre, la fecha de nacimiento y el apoderado.")
            else:
                st.session_state["paciente_id"] = db.crear_paciente(
                    {
                        "nombre": nombre.strip(), "fecha_nacimiento": nacimiento.isoformat(), "sexo": sexo,
                        "apoderado": apoderado.strip(), "distrito": distrito.strip(),
                        "colegio": colegio.strip(), "seguro": seguro,
                    }
                )
                st.switch_page("app/ficha.py")

buscar = st.text_input("Buscar paciente", placeholder="Nombre o apellido", icon=":material/search:")
pacientes = db.listar_pacientes(buscar)
if not pacientes:
    st.info("No hay pacientes con ese nombre.")
for p in pacientes:
    with st.container(border=True):
        datos, clinica, accion = st.columns([3, 5, 1.4], vertical_alignment="center")
        datos.markdown(f"**{p['nombre']}** · {p['edad']}")
        datos.caption(f"Apoderado: {p['apoderado']}")
        clinica.markdown(" · ".join(diagnostico_texto(d) for d in p["diagnosticos"]) or "Sin diagnóstico registrado")
        clinica.caption(f"{p['n_atenciones']} atenciones · última: {fecha_texto(p['ultima_atencion'])}")
        if accion.button("Abrir", key=f"abrir_{p['id']}", type="primary"):
            st.session_state["paciente_id"] = p["id"]  # la ficha lee este valor
            st.switch_page("app/ficha.py")
