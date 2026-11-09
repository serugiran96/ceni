"""Página 2: ficha del paciente.

Arriba, los datos del niño o la niña y su plan de objetivos. Abajo, pestañas
con el historial, la nueva sesión por voz, la evolución y el informe.
"""

import streamlit as st

from app.formato import fecha_texto, mostrar_nota, nivel_texto
from backend import db

PESTANAS = ["Historial", "Nueva sesión", "Evolución", "Informe para la familia"]

# --- Elegir paciente ---------------------------------------------------------
pacientes = db.listar_pacientes()
nombres = {p["id"]: p["nombre"] for p in pacientes}
if st.session_state.get("paciente_id") not in nombres:
    st.session_state["paciente_id"] = pacientes[0]["id"]
paciente_id = st.selectbox("Paciente", list(nombres), format_func=nombres.get, key="paciente_id")

paciente = db.obtener_paciente(paciente_id)
objetivos = db.objetivos_de(paciente_id)
sesiones = db.sesiones_de(paciente_id)  # de la más reciente a la más antigua
nombre_objetivo = {o["id"]: o["descripcion"] for o in objetivos}

# --- Cabecera ----------------------------------------------------------------
st.title(paciente["nombre"])
st.caption(
    f"{paciente['edad']} · {paciente['especialidad']} · {paciente['terapeuta']} · "
    f"Sede {paciente['sede']} · Apoderado: {paciente['apoderado']}"
)
st.markdown(f"**Motivo de consulta:** {paciente['motivo_consulta']}")

ultimo_nivel = {}
for s in reversed(sesiones):  # de la más antigua a la más reciente: gana la última
    for a in s["nota"].avances:
        ultimo_nivel[a.objetivo_id] = a.nivel
st.markdown("**Plan de objetivos** (nivel en la última sesión en que se trabajó)")
st.markdown(
    "\n".join(
        f"- {o['descripcion']}: "
        + (f"**{nivel_texto(ultimo_nivel[o['id']])}** ({ultimo_nivel[o['id']]}/4)" if o["id"] in ultimo_nivel else "sin registro")
        for o in objetivos
    )
)

# Después de guardar una sesión saltamos a otra pestaña; hay que fijarlo antes
# de dibujar las pestañas.
if "ir_a_pestana" in st.session_state:
    st.session_state["pestana"] = st.session_state.pop("ir_a_pestana")
historial, nueva, evolucion, informe = st.tabs(PESTANAS, key="pestana")

# --- Historial ---------------------------------------------------------------
with historial:
    if not sesiones:
        st.info("Este paciente todavía no tiene sesiones.")
    for i, s in enumerate(sesiones):
        with st.expander(f"{fecha_texto(s['fecha'])} · {s['nota'].resumen}", expanded=(i == 0)):
            mostrar_nota(s["nota"], nombre_objetivo)
            if s["transcripcion"]:
                st.caption(f"Dictado original: “{s['transcripcion']}”")

with nueva:
    st.info("Próximo paso: dictar la sesión.")

with evolucion:
    st.info("Próximo paso: gráfico de evolución.")

with informe:
    st.info("Próximo paso: informe para la familia.")
