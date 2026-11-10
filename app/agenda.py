"""Página de inicio: la agenda del médico.

Desde aquí empieza el día: el médico ve sus citas, presiona "Atender" y entra
a la ficha del paciente con la cita enlazada. Al firmar la atención, la cita
queda como atendida.
"""

from datetime import date, time, timedelta
from html import escape

import streamlit as st

from app import estilo
from app.formato import chips_paciente, cuando_texto, dia_texto, fecha_corta
from backend import db

ESTADOS = {  # color e ícono de la etiqueta de las citas que ya pasaron
    "Atendida": ("green", ":material/check:"),
    "No asistió": ("gray", ":material/close:"),
}
TONO_TIPO = {"Control": "cielo", "Primera vez": "durazno"}


def abrir_ficha(paciente_id: int, cita_id: int | None = None) -> None:
    st.session_state["paciente_id"] = paciente_id
    st.session_state["cita_id"] = cita_id  # la ficha enlaza la atención con esta cita
    st.session_state["ir_a_pestana"] = "Nueva atención" if cita_id else "Historia clínica"
    st.switch_page("app/ficha.py")


medico = db.medico()
nombre = medico["nombre"].split()
hoy = date.today()

estilo.encabezado(
    f"Hola, {nombre[0]} {nombre[-1]}",
    "Presiona «Atender» para abrir la ficha del paciente y grabar la consulta.",
    dia_texto(hoy),
)
if aviso := st.session_state.pop("aviso_agenda", None):
    st.success(aviso, icon=":material/check_circle:")

principal, lateral = st.columns([2.4, 1], gap="large")

with principal:
    elegir, resumen = st.columns([1, 2.2], vertical_alignment="bottom")
    dia = elegir.date_input("Día", value=hoy, format="DD/MM/YYYY")
    citas = db.citas_entre(dia, dia)
    with resumen:
        estilo.html(estilo.cifras([
            (str(len(citas)), "", "citas", "cielo"),
            (str(sum(c["estado"] == "Programada" for c in citas)), "", "por atender", "durazno"),
            (str(sum(c["estado"] == "Atendida" for c in citas)), "", "atendidas", "salvia"),
        ]))
    estilo.html(f'<div class="ceni-subtitulo" style="margin-top:1rem">{escape(cuando_texto(dia).capitalize())}</div>')
    if not citas:
        st.info("No hay citas este día.", icon=":material/event_busy:")

    for c in citas:
        apagada = "" if c["estado"] == "Programada" else "-apagada"
        with st.container(key=f"tarjeta-cita-{c['id']}{apagada}"):
            hora, quien, acciones = st.columns([0.95, 4.6, 2], vertical_alignment="center")
            hora.html(
                f'<div class="ceni-hora" style="{estilo.tono_css(TONO_TIPO.get(c["tipo"], "cielo"))}">'
                f'{c["hora"]}<small>{escape(c["tipo"])}</small></div>'
            )
            quien.html(estilo.persona(
                c["nombre"], c["paciente_id"], f"{c['edad']} · {c['hc']}",
                chips_paciente(c["diagnosticos"], c["alergias"]),
            ))
            with acciones:
                if c["estado"] == "Programada":
                    if st.button("Atender", key=f"atender_{c['id']}", type="primary", icon=":material/mic:", width="stretch"):
                        abrir_ficha(c["paciente_id"], c["id"])
                    if st.button("No asistió", key=f"falta_{c['id']}", type="tertiary", width="stretch"):
                        db.cambiar_estado_cita(c["id"], "No asistió")
                        st.rerun()
                else:  # atendida o no asistió: la etiqueta del estado y el acceso a la ficha
                    color, icono = ESTADOS[c["estado"]]
                    st.badge(c["estado"], color=color, icon=icono, width="stretch")
                    if st.button("Ver ficha", key=f"ver_{c['id']}", icon=":material/folder_shared:", width="stretch"):
                        abrir_ficha(c["paciente_id"])

with lateral:
    with st.container(key="tarjeta-agendar"):
        estilo.html('<div class="ceni-subtitulo">Agendar una cita</div>')
        pacientes = db.listar_pacientes()
        nombres = {p["id"]: p["nombre"] for p in pacientes}
        with st.form("nueva_cita", clear_on_submit=True, border=False):
            paciente_id = st.selectbox("Paciente", list(nombres), format_func=nombres.get)
            fecha = st.date_input("Fecha", value=max(dia, hoy), min_value=hoy, format="DD/MM/YYYY")
            a_las = st.time_input("Hora", value=time(9, 0), step=timedelta(minutes=20))
            tipo = st.segmented_control("Tipo", ["Control", "Primera vez"], default="Control")
            if st.form_submit_button("Agendar", type="primary", icon=":material/event_available:", width="stretch"):
                db.crear_cita(paciente_id, fecha, a_las.strftime("%H:%M"), tipo or "Control")
                st.session_state["aviso_agenda"] = (
                    f"Cita agendada: {nombres[paciente_id]}, {dia_texto(fecha)} a las {a_las:%H:%M}."
                )
                st.rerun()

    with st.container(key="tarjeta-proximas"):
        estilo.html('<div class="ceni-subtitulo">Próximos 7 días</div>')
        proximas = db.citas_entre(dia + timedelta(days=1), dia + timedelta(days=7))
        filas = "".join(
            f'<div class="ceni-persona" style="margin-bottom:.7rem">'
            f'<div class="ceni-hora" style="{estilo.tono_css(TONO_TIPO.get(c["tipo"], "cielo"))};font-size:.95rem;min-width:62px">'
            f'{escape(fecha_corta(c["fecha"]))}<small>{c["hora"]}</small></div>'
            f'<div><div class="ceni-nombre" style="font-size:.95rem">{escape(c["nombre"])}</div>'
            f'<div class="ceni-meta">{escape(c["tipo"])} · {escape(cuando_texto(c["fecha"]))}</div></div></div>'
            for c in proximas
        )
        estilo.html(filas or '<p class="ceni-vacio">Sin citas programadas.</p>')
