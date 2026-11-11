"""Panel de admin: consultorios, médicos y plantillas de especialidad.

Así se da de alta un cliente nuevo: se crea su consultorio, se le agregan sus
médicos y a cada médico se le asigna la plantilla de su especialidad. Todas
las plantillas comparten el formato de consulta externa del MINSA; una
plantilla solo agrega los campos propios de la especialidad.
"""

import pandas as pd
import streamlit as st

from ai.esquemas import CampoPlantilla, Plantilla
from app import estilo
from app.formato import duracion_texto
from backend import db

# Lo que tienen todas las atenciones, sea cual sea la especialidad (formato de consulta externa del MINSA).
FORMATO_MINSA = [
    "Anamnesis: motivo, tiempo de enfermedad y relato",
    "Funciones biológicas",
    "Funciones vitales y antropometría",
    "Examen físico",
    "Diagnósticos CIE-10 (definitivo, presuntivo o repetitivo)",
    "Tratamiento: receta según la Ley 29459",
    "Plan de trabajo: exámenes, interconsultas e indicaciones",
    "Próximo control",
]


def leer_campos(texto: str) -> list[CampoPlantilla]:
    """Un campo por línea, con el formato 'Nombre: qué debe ir'."""
    campos = []
    for linea in texto.splitlines():
        if not linea.strip():
            continue
        nombre, _, descripcion = linea.partition(":")
        campos.append(CampoPlantilla(nombre=nombre.strip(), descripcion=descripcion.strip()))
    return campos


@st.dialog("Nuevo consultorio")
def nuevo_consultorio() -> None:
    with st.form("form_consultorio", border=False):
        nombre = st.text_input("Nombre del consultorio o centro")
        distrito = st.text_input("Distrito")
        if st.form_submit_button("Crear consultorio", type="primary", icon=":material/add_business:", width="stretch"):
            if not nombre.strip():
                st.error("Escribe el nombre del consultorio.")
                return
            db.crear_consultorio(nombre.strip(), distrito.strip())
            st.session_state["aviso_admin"] = f"Consultorio creado: {nombre.strip()}. Ahora agrégale sus médicos."
            st.rerun()


@st.dialog("Nuevo médico")
def nuevo_medico() -> None:
    consultorios = {c["id"]: c["nombre"] for c in db.consultorios()}
    plantillas = {i: p.nombre for i, p in db.plantillas()}
    with st.form("form_medico", border=False):
        nombre = st.text_input("Nombre, con su título", placeholder="Dra. Ana Torres")
        consultorio_id = st.selectbox("Consultorio", list(consultorios), format_func=consultorios.get)
        especialidad = st.text_input("Especialidad (se muestra en su perfil)", placeholder="Dermatología")
        colegiatura = st.text_input("Colegiatura", placeholder="CMP 000000 · RNE 000000")
        plantilla_id = st.selectbox("Plantilla de su especialidad", [None, *plantillas],
                                    format_func=lambda i: plantillas[i] if i else "Solo el formato MINSA")
        if st.form_submit_button("Crear médico", type="primary", icon=":material/person_add:", width="stretch"):
            if not (nombre.strip() and especialidad.strip()):
                st.error("Completa al menos el nombre y la especialidad.")
                return
            db.crear_medico({"consultorio_id": consultorio_id, "nombre": nombre.strip(),
                             "especialidad": especialidad.strip(), "colegiatura": colegiatura.strip(),
                             "plantilla_id": plantilla_id})
            st.session_state["aviso_admin"] = (f"Listo: {nombre.strip()} ya puede entrar desde «Entrar como», "
                                               "en la barra lateral.")
            st.rerun()


@st.dialog("Nueva plantilla de especialidad", width="large")
def nueva_plantilla() -> None:
    st.caption("Todas las plantillas ya traen el formato de consulta externa del MINSA. Aquí agregas solo los campos "
               "propios de la especialidad.")
    with st.form("form_plantilla", border=False):
        nombre = st.text_input("Especialidad", placeholder="Dermatología pediátrica")
        campos = st.text_area("Campos de la especialidad: uno por línea, con «Nombre: qué debe ir»", height=180,
                              placeholder="Tipo de lesión: mácula, pápula, placa, vesícula...\n"
                                          "Localización y extensión: dónde están las lesiones y cuánto cubren")
        vocabulario = st.text_input("Términos y medicamentos frecuentes (ayudan a transcribir bien)",
                                    placeholder="Dermatitis atópica, emolientes, mometasona...")
        if st.form_submit_button("Crear plantilla", type="primary", icon=":material/note_add:", width="stretch"):
            lista = leer_campos(campos)
            if not (nombre.strip() and lista):
                st.error("Escribe la especialidad y al menos un campo.")
                return
            db.crear_plantilla(Plantilla(nombre=nombre.strip(), campos=lista, vocabulario=vocabulario.strip()))
            st.session_state["aviso_admin"] = f"Plantilla creada: {nombre.strip()}, con {len(lista)} campos."
            st.rerun()


admin = db.admin()
consultorios = db.consultorios()
medicos = db.medicos()
plantillas = db.plantillas()
metricas = {m["id"]: db.metricas_medico(m["id"]) for m in medicos}

estilo.encabezado("Panel de", "Da de alta consultorios y médicos, y arma las plantillas de cada especialidad.",
                  f"Admin · {admin['nombre']}", resaltado="Ceni")
if aviso := st.session_state.pop("aviso_admin", None):
    st.success(aviso, icon=":material/check_circle:")

atenciones_ia = sum(m["atenciones"] for m in metricas.values())
acertados = sum(m["acierto"].acertados for m in metricas.values())
datos = sum(m["acierto"].total for m in metricas.values())
estilo.html(estilo.cifras([
    (str(len(consultorios)), "", "consultorios", "violeta"),
    (str(len(medicos)), "", "médicos", "coral"),
    (str(sum(c["n_pacientes"] for c in consultorios)), "", "pacientes", "menta"),
    (str(atenciones_ia), "", "atenciones con Ceni (30 días)", "sol"),
    (f"{acertados / datos:.0%}" if datos else "—", "", "acierto de Ceni (30 días)", "cielo"),
]))
st.write("")

clientes, plantillas_tab, uso = st.tabs(["Consultorios y médicos", "Plantillas", "Uso por médico"])

with clientes:
    with st.container(horizontal=True):
        if st.button("Nuevo consultorio", icon=":material/add_business:", type="primary"):
            nuevo_consultorio()
        if st.button("Nuevo médico", icon=":material/person_add:"):
            nuevo_medico()
    for c in consultorios:
        with st.container(key=f"tarjeta-consultorio-{c['id']}"):
            medicos_txt = f"{c['n_medicos']} médico" + ("s" if c["n_medicos"] != 1 else "")
            pacientes_txt = f"{c['n_pacientes']} paciente" + ("s" if c["n_pacientes"] != 1 else "")
            estilo.html(estilo.titulo(c["nombre"], "apartment", "violeta",
                                      f"{c['distrito']} · {medicos_txt} · {pacientes_txt}"))
            del_consultorio = [m for m in medicos if m["consultorio_id"] == c["id"]]
            if not del_consultorio:
                estilo.html('<p class="ceni-vacio">Todavía no tiene médicos. Agrégalos con «Nuevo médico».</p>')
            for m in del_consultorio:
                plantilla = m["plantilla"].nombre if m["plantilla"] else "solo el formato MINSA"
                estilo.html(estilo.persona(m["nombre"], m["id"], f"{m['especialidad']} · Plantilla: {plantilla}"))

with plantillas_tab:
    if st.button("Nueva plantilla", icon=":material/note_add:", type="primary"):
        nueva_plantilla()
    with st.container(key="tarjeta-formato-minsa"):
        estilo.html(estilo.titulo("Formato de consulta externa del MINSA", "verified", "menta", "lo tienen todas")
                    + estilo.items([("check", "menta", campo) for campo in FORMATO_MINSA]))
    for i, p in plantillas:
        usan = [m["nombre"] for m in medicos if m["plantilla_id"] == i]
        with st.container(key=f"tarjeta-plantilla-{i}"):
            estilo.html(
                estilo.titulo(p.nombre, "stethoscope", "coral", f"{len(p.campos)} campos · la usan: "
                              + (", ".join(usan) if usan else "nadie todavía"))
                + estilo.items([("add_circle", "coral", f"{c.nombre}: {c.descripcion}") for c in p.campos])
                + estilo.bloque("Vocabulario para la transcripción", estilo.texto(p.vocabulario, "Sin vocabulario"))
            )
    st.caption("Lo que viene: el médico sube su formato en PDF y Ceni arma la plantilla, alineada al formato del "
               "MINSA, para que tú la revises y la apruebes.")

with uso:
    st.dataframe(
        pd.DataFrame([{
            "Médico": m["nombre"], "Consultorio": m["consultorio"],
            "Atenciones con Ceni (30 días)": metricas[m["id"]]["atenciones"],
            "Ceni tarda": duracion_texto(metricas[m["id"]]["segundos_ia"]) if metricas[m["id"]]["atenciones"] else "—",
            "Revisión del médico": (duracion_texto(metricas[m["id"]]["segundos_revision"])
                                    if metricas[m["id"]]["atenciones"] else "—"),
            "Acierto": (f"{metricas[m['id']]['acierto'].porcentaje:.0%}"
                        if metricas[m["id"]]["acierto"].total else "—"),
        } for m in medicos]),
        hide_index=True, width="stretch",
    )
