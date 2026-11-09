"""Página de inicio: la agenda del médico.

Desde aquí empieza el día: el médico ve sus citas, presiona "Atender" y entra
a la ficha del paciente con la cita enlazada. Al firmar la atención, la cita
queda como atendida.
"""

from datetime import date, time, timedelta

import streamlit as st

from app.formato import dia_texto
from backend import db

COLOR_ESTADO = {"Programada": "blue", "Atendida": "green", "No asistió": "gray"}
ICONO_ESTADO = {"Programada": ":material/schedule:", "Atendida": ":material/check:", "No asistió": ":material/close:"}

medico = db.medico()
st.title("Agenda")
st.caption(f"{medico['nombre']} · {medico['especialidad']}")
if aviso := st.session_state.pop("aviso_agenda", None):
    st.success(aviso, icon=":material/check_circle:")

dia = st.date_input("Día", value=date.today(), format="DD/MM/YYYY")
citas = db.citas_entre(dia, dia)
st.markdown(f"#### {dia_texto(dia).capitalize()} · {len(citas)} citas")
if not citas:
    st.info("No hay citas este día.")

for c in citas:
    with st.container(border=True):
        hora, quien, estado, acciones = st.columns([0.8, 3.4, 1.4, 2.6], vertical_alignment="center")
        hora.markdown(f"**{c['hora']}**")
        quien.markdown(f"**{c['nombre']}**")
        quien.caption(c["tipo"])
        with estado:
            st.badge(c["estado"], color=COLOR_ESTADO[c["estado"]], icon=ICONO_ESTADO[c["estado"]])
        if c["estado"] == "Programada":
            atender, falta = acciones.columns(2)
            if atender.button("Atender", key=f"atender_{c['id']}", type="primary", width="stretch"):
                st.session_state["paciente_id"] = c["paciente_id"]
                st.session_state["cita_id"] = c["id"]  # la ficha enlaza la atención con esta cita
                st.switch_page("app/ficha.py")
            if falta.button("No asistió", key=f"falta_{c['id']}", width="stretch"):
                db.cambiar_estado_cita(c["id"], "No asistió")
                st.rerun()
        elif acciones.button("Ver ficha", key=f"ver_{c['id']}", width="stretch"):
            st.session_state["paciente_id"] = c["paciente_id"]
            st.switch_page("app/ficha.py")

with st.expander("Agendar una cita", icon=":material/event:"):
    pacientes = db.listar_pacientes()
    nombres = {p["id"]: p["nombre"] for p in pacientes}
    with st.form("nueva_cita", clear_on_submit=True):
        quien, cuando, hora, tipo = st.columns([3, 2, 1.4, 1.6])
        paciente_id = quien.selectbox("Paciente", list(nombres), format_func=nombres.get)
        fecha = cuando.date_input("Fecha", value=max(dia, date.today()), min_value=date.today(), format="DD/MM/YYYY")
        a_las = hora.time_input("Hora", value=time(9, 0), step=timedelta(minutes=20))
        clase = tipo.selectbox("Tipo", ["Control", "Primera vez"])
        if st.form_submit_button("Agendar", type="primary"):
            db.crear_cita(paciente_id, fecha, a_las.strftime("%H:%M"), clase)
            st.session_state["aviso_agenda"] = f"Cita agendada: {nombres[paciente_id]}, {dia_texto(fecha)} a las {a_las:%H:%M}."
            st.rerun()

proximas = db.citas_entre(dia + timedelta(days=1), dia + timedelta(days=7))
if proximas:
    st.markdown("#### Próximos 7 días")
    st.markdown(
        "\n".join(f"- {dia_texto(c['fecha']).capitalize()}, {c['hora']}: **{c['nombre']}** ({c['tipo'].lower()})" for c in proximas)
    )
