"""Página de inicio: la agenda del médico.

Arriba está el siguiente paciente, con lo que el médico necesita recordar antes
de verlo (la última atención, lo que quedó pendiente y su medicación). Al
presionar "Atender" entra a la ficha con la cita enlazada; al firmar la
atención, la cita queda como atendida.
"""

from datetime import date, time, timedelta
from html import escape

import streamlit as st

from app import estilo
from app.formato import antes_de_empezar_html, chips_paciente, cuando_texto, dia_texto, fecha_corta
from backend import db

ESTADOS = {  # color e ícono de la etiqueta de las citas que ya pasaron
    "Atendida": ("green", ":material/check:"),
    "No asistió": ("gray", ":material/close:"),
}
TONO_TIPO = {"Control": "violeta", "Primera vez": "coral"}


def abrir_ficha(paciente_id: int, cita_id: int | None = None) -> None:
    st.session_state["paciente_id"] = paciente_id
    st.session_state["cita_id"] = cita_id  # la ficha enlaza la atención con esta cita
    st.session_state["ir_a_pestana"] = "Nueva atención" if cita_id else "Historia clínica"
    st.switch_page("app/ficha.py")


@st.dialog("Agendar una cita")
def agendar(dia_sugerido: date) -> None:
    pacientes = db.listar_pacientes()
    nombres = {p["id"]: p["nombre"] for p in pacientes}
    with st.form("nueva_cita", border=False):
        paciente_id = st.selectbox("Paciente", list(nombres), format_func=nombres.get)
        fecha_col, hora_col = st.columns(2)
        fecha = fecha_col.date_input("Fecha", value=dia_sugerido, min_value=date.today(), format="DD/MM/YYYY")
        a_las = hora_col.time_input("Hora", value=time(9, 0), step=timedelta(minutes=20))
        tipo = st.segmented_control("Tipo", ["Control", "Primera vez"], default="Control")
        if st.form_submit_button("Agendar", type="primary", icon=":material/event_available:", width="stretch"):
            db.crear_cita(paciente_id, fecha, a_las.strftime("%H:%M"), tipo or "Control")
            st.session_state["aviso_agenda"] = (
                f"Cita agendada: {nombres[paciente_id]}, {dia_texto(fecha)} a las {a_las:%H:%M}."
            )
            st.rerun()


st.session_state.pop("recien_firmada", None)  # el aviso de "atención firmada" solo se ve en la ficha
medico = db.medico()
nombre = medico["nombre"].split()
hoy = date.today()

principal, lateral = st.columns([2.35, 1], gap="large")

# --- Columna lateral: el día que se mira, agendar y los próximos días ----------------
with lateral:
    with st.container(key="tarjeta-dia"):
        estilo.html(estilo.titulo("Calendario", "calendar_month", "cielo"))
        dia = st.date_input("Día", value=hoy, format="DD/MM/YYYY", label_visibility="collapsed")
        if st.button("Agendar una cita", icon=":material/add:", width="stretch"):
            agendar(max(dia, hoy))

    with st.container(key="tarjeta-proximas"):
        estilo.html(estilo.titulo("Próximos 7 días", "upcoming", "sol"))
        proximas = db.citas_entre(dia + timedelta(days=1), dia + timedelta(days=7))
        filas = "".join(
            f'<div class="ceni-persona" style="margin-bottom:.75rem">'
            f'<div class="ceni-hora" style="{estilo.tono_css(TONO_TIPO.get(c["tipo"], "violeta"))};font-size:.95rem;min-width:64px">'
            f'{escape(fecha_corta(c["fecha"]))}<small>{c["hora"]}</small></div>'
            f'<div><div class="ceni-nombre" style="font-size:.98rem">{escape(c["nombre"])}</div>'
            f'<div class="ceni-meta">{escape(c["tipo"])} · {escape(cuando_texto(c["fecha"]))}</div></div></div>'
            for c in proximas
        )
        estilo.html(filas or '<p class="ceni-vacio">Sin citas programadas.</p>')

# --- Columna principal: saludo, siguiente paciente y citas del día --------------------
with principal:
    citas = db.citas_entre(dia, dia)
    siguiente = next((c for c in citas if c["estado"] == "Programada"), None)
    por_atender = sum(c["estado"] == "Programada" for c in citas)
    estilo.encabezado(
        "Hola,",
        f"{cuando_texto(dia).capitalize()} tienes {len(citas)} citas y te faltan {por_atender} por atender."
        if citas else f"No tienes citas {cuando_texto(dia)}.",
        dia_texto(hoy), resaltado=f"{nombre[0]} {nombre[-1]}",
    )
    if aviso := st.session_state.pop("aviso_agenda", None):
        st.success(aviso, icon=":material/check_circle:")

    if siguiente:
        historia_siguiente, _ = db.historia_de(siguiente["paciente_id"])
        with st.container(key="heroe-siguiente"):
            quien, resumen = st.columns([1.3, 1], gap="large", vertical_alignment="center")
            with quien:
                estilo.html(
                    f'<div class="ceni-etiqueta">Siguiente paciente · {cuando_texto(dia)} {siguiente["hora"]} · '
                    f'{escape(siguiente["tipo"])}</div>'
                    + estilo.persona(
                        siguiente["nombre"], siguiente["paciente_id"], f"{siguiente['edad']} · {siguiente['hc']}",
                        chips_paciente(siguiente["diagnosticos"], siguiente["alergias"], sobre_color=True), grande=True,
                    )
                )
                with st.container(key="grande-atender"):
                    if st.button("Atender ahora", key="atender_siguiente", type="primary", icon=":material/mic:"):
                        abrir_ficha(siguiente["paciente_id"], siguiente["id"])
            resumen.html('<div class="ceni-panel">' + antes_de_empezar_html(
                db.atenciones_de(siguiente["paciente_id"]), historia_siguiente, maximo=3) + "</div>")
    elif citas:
        st.success("Atendiste todas las citas de este día.", icon=":material/celebration:")

    st.write("")
    estilo.html(estilo.cifras([
        (str(len(citas)), "", "citas", "violeta"),
        (str(por_atender), "", "por atender", "coral"),
        (str(sum(c["estado"] == "Atendida" for c in citas)), "", "atendidas", "menta"),
        (str(len(proximas)), "", "en los próximos 7 días", "sol"),
    ]))
    st.write("")
    estilo.html(estilo.titulo(f"Agenda de {cuando_texto(dia)}", "event_note", "violeta", f"{len(citas)} citas"))
    if not citas:
        st.info("No hay citas este día.", icon=":material/event_busy:")

    for c in citas:
        apagada = "" if c["estado"] == "Programada" else "-apagada"
        with st.container(key=f"tarjeta-cita-{c['id']}{apagada}"):
            hora, quien, acciones = st.columns([0.95, 4.4, 2], vertical_alignment="center")
            hora.html(
                f'<div class="ceni-hora" style="{estilo.tono_css(TONO_TIPO.get(c["tipo"], "violeta"))}">'
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
