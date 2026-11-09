"""Página 2: ficha del paciente.

Arriba, los datos del niño o la niña y su plan de objetivos. Abajo, pestañas
con el historial, la nueva sesión por voz, la evolución y el informe.
"""

from datetime import date
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from ai.cliente import hay_clave
from ai.esquemas import ESCALA, AvanceObjetivo, NotaSesion
from ai.generar import generar_informe, generar_nota
from ai.transcribir import transcribir
from app.formato import MESES, fecha_texto, mostrar_nota, nivel_texto
from backend import db
from backend.pdf import informe_a_pdf

PESTANAS = ["Historial", "Nueva sesión", "Evolución", "Informe para la familia"]
CARPETA_EJEMPLOS = Path(__file__).resolve().parent.parent / "data" / "audios_demo"
MAX_USOS_IA = 20  # por visitante: protege el saldo de la API en la URL pública
N_SESIONES_INFORME = 4  # el informe resume más o menos el último mes
COLORES = ["#2a78d6", "#eb6834", "#1baf7a"]  # azul, naranja, aqua: distinguibles con daltonismo


def usar_ia() -> bool:
    """Cuenta los usos de IA de este visitante y avisa si pasó el límite."""
    usos = st.session_state.get("usos_ia", 0)
    if usos >= MAX_USOS_IA:
        st.error("Llegaste al límite de usos de IA de este demo. Recarga más tarde.")
        return False
    st.session_state["usos_ia"] = usos + 1
    return True


def lineas(texto: str) -> list[str]:
    """Convierte un cuadro de texto (un ítem por línea) en lista."""
    return [l.strip(" -•\t") for l in texto.splitlines() if l.strip(" -•\t")]


def grafico_evolucion(avances, objetivos: list[dict]) -> go.Figure:
    """Un panel por objetivo (así las líneas no se tapan), mismo eje de fechas."""
    fig = make_subplots(
        rows=len(objetivos), cols=1, shared_xaxes=True, vertical_spacing=0.12,
        subplot_titles=[o["descripcion"] for o in objetivos],
    )
    for fila, (o, color) in enumerate(zip(objetivos, COLORES), start=1):
        datos = avances[avances["objetivo"] == o["descripcion"]]
        fig.add_trace(
            go.Scatter(
                x=datos["fecha"], y=datos["nivel"], mode="lines+markers", name=o["descripcion"],
                line={"color": color, "width": 2}, marker={"size": 9, "color": color},
                customdata=datos["nivel"].map(nivel_texto),
                hovertemplate="%{x|%d/%m/%Y}<br><b>%{customdata}</b> (%{y}/4)<extra></extra>",
            ),
            row=fila, col=1,
        )
        fig.update_yaxes(
            row=fila, col=1, range=[0.6, 4.4], tickvals=[1, 2, 3, 4],
            ticktext=[nivel_texto(n) for n in (1, 2, 3, 4)], gridcolor="rgba(128,128,128,0.15)",
        )
    fechas = sorted(avances["fecha"].unique())  # una marca por sesión, con el mes en español
    fig.update_xaxes(
        tickvals=fechas, ticktext=[f"{f.day} {MESES[f.month - 1][:3]}" for f in pd.to_datetime(fechas)],
        gridcolor="rgba(128,128,128,0.15)",
    )
    fig.update_layout(
        height=190 * len(objetivos) + 40, showlegend=False, hovermode="closest",
        margin={"l": 10, "r": 10, "t": 40, "b": 10},
    )
    fig.update_annotations(font_size=14, xanchor="left", x=0)  # títulos de panel a la izquierda
    return fig


def progreso_objetivos(sesiones_orden: list[dict], objetivos: list[dict]) -> list[str]:
    """'Objetivo: En proceso -> Casi logrado' entre la primera y la última sesión del periodo."""
    resultado = []
    for o in objetivos:
        niveles = [a.nivel for s in sesiones_orden for a in s["nota"].avances if a.objetivo_id == o["id"]]
        if not niveles:
            continue
        cambio = nivel_texto(niveles[-1]) if niveles[0] == niveles[-1] else f"{nivel_texto(niveles[0])} → {nivel_texto(niveles[-1])}"
        resultado.append(f"{o['descripcion']}: {cambio}")
    return resultado

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
if aviso := st.session_state.pop("aviso", None):
    st.success(aviso, icon=":material/check_circle:")
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

# --- Nueva sesión: voz -> Whisper -> nota estructurada -> revisión -> guardar --
with nueva:
    st.markdown(
        "Al terminar la sesión, cuenta en uno o dos minutos qué trabajaron, cómo le fue "
        "y qué queda para casa. Ceni lo convierte en la nota de evolución."
    )
    if not hay_clave():
        st.warning("Falta la clave de OpenAI (OPENAI_API_KEY). Sin ella no se puede transcribir ni generar la nota.")

    fecha = st.date_input("Fecha de la sesión", value=date.today(), format="DD/MM/YYYY", key=f"fecha_{paciente_id}")
    grabado = st.audio_input("Dicta la sesión", key=f"audio_{paciente_id}")
    with st.expander("¿Sin micrófono? Sube un audio, usa uno de ejemplo o escribe el dictado"):
        subido = st.file_uploader(
            "Sube un audio", type=["wav", "mp3", "m4a", "ogg", "webm", "mp4"], key=f"subido_{paciente_id}"
        )
        ejemplos = sorted(CARPETA_EJEMPLOS.glob("*.mp3"))
        ejemplo = st.selectbox(
            "Audio de ejemplo (casos inventados)", [None, *ejemplos],
            format_func=lambda p: "Ninguno" if p is None else p.stem.replace("-", " ").capitalize(),
            key=f"ejemplo_{paciente_id}",
        )
        if ejemplo:
            st.audio(str(ejemplo))
        escrito = st.text_area("O escribe el dictado", key=f"escrito_{paciente_id}")

    if st.button("Generar nota", type="primary", icon=":material/auto_awesome:", key=f"generar_{paciente_id}"):
        if not (grabado or subido or ejemplo or escrito.strip()):
            st.error("Primero graba, sube o escribe el dictado.")
        elif usar_ia():
            try:
                with st.status("Ceni está trabajando…", expanded=True) as estado:
                    if grabado or subido or ejemplo:
                        st.write("Transcribiendo el audio con Whisper…")
                        if ejemplo:
                            audio, nombre_archivo = ejemplo.read_bytes(), ejemplo.name
                        else:
                            archivo = grabado or subido
                            audio, nombre_archivo = archivo.getvalue(), archivo.name
                        vocabulario = (
                            f"Sesión de {paciente['especialidad']} con {paciente['nombre']}. "
                            f"Terapeuta: {paciente['terapeuta']}. Objetivos: "
                            + "; ".join(o["descripcion"] for o in objetivos)
                        )
                        texto = transcribir(audio, nombre_archivo, vocabulario)
                    else:
                        texto = escrito.strip()
                    st.write("Armando la nota con salidas estructuradas…")
                    nota = generar_nota(texto, paciente, objetivos)
                    estado.update(label="Nota lista. Revísala antes de guardar.", state="complete", expanded=False)
                st.session_state["borrador"] = {
                    "id": st.session_state.get("usos_ia", 0),  # cambia en cada nota: reinicia el formulario
                    "paciente_id": paciente_id,
                    "fecha": fecha,
                    "transcripcion": texto,
                    "nota": nota,
                }
            except Exception as error:  # clave inválida, sin saldo, audio dañado...
                st.error(f"No se pudo generar la nota: {error}")

    borrador = st.session_state.get("borrador")
    if borrador and borrador["paciente_id"] == paciente_id:
        nota, b = borrador["nota"], borrador["id"]
        st.caption(f"Transcripción: “{borrador['transcripcion']}”")
        with st.form(f"form_nota_{b}"):
            st.markdown(f"#### Nota del {fecha_texto(borrador['fecha'])}: revisa y corrige")
            resumen = st.text_area("Resumen", nota.resumen, height=80)
            izquierda, derecha = st.columns(2)
            actividades = izquierda.text_area("Actividades (una por línea)", "\n".join(nota.actividades))
            logros = izquierda.text_area("Logros (uno por línea)", "\n".join(nota.logros))
            dificultades = izquierda.text_area("Dificultades (una por línea)", "\n".join(nota.dificultades))
            tareas = derecha.text_area("Tareas para casa (una por línea)", "\n".join(nota.tareas_para_casa))
            observaciones = derecha.text_area("Observaciones", nota.observaciones)

            st.markdown("**Avance por objetivo**")
            sugeridos = {a.objetivo_id: a for a in nota.avances}
            elegidos = []
            for o in objetivos:
                a = sugeridos.get(o["id"])
                col_nivel, col_evidencia = st.columns([2, 3])
                nivel = col_nivel.selectbox(
                    o["descripcion"], [0, 1, 2, 3, 4], index=a.nivel if a else 0,
                    format_func=lambda n: "No se trabajó hoy" if n == 0 else f"{n} · {ESCALA[n]}",
                    key=f"nivel_{b}_{o['id']}",
                )
                evidencia = col_evidencia.text_input(
                    "Evidencia", a.comentario if a else "", key=f"evidencia_{b}_{o['id']}"
                )
                if nivel:
                    elegidos.append(AvanceObjetivo(objetivo_id=o["id"], nivel=nivel, comentario=evidencia))

            guardar = st.form_submit_button("Guardar en la ficha", type="primary", icon=":material/save:")
        if guardar:
            nota_final = NotaSesion(
                resumen=resumen.strip(),
                actividades=lineas(actividades),
                logros=lineas(logros),
                dificultades=lineas(dificultades),
                avances=elegidos,
                tareas_para_casa=lineas(tareas),
                observaciones=observaciones.strip(),
            )
            db.guardar_sesion(paciente_id, borrador["fecha"], borrador["transcripcion"], nota_final)
            del st.session_state["borrador"]
            st.session_state["aviso"] = f"Sesión del {fecha_texto(borrador['fecha'])} guardada en el historial."
            st.session_state["ir_a_pestana"] = "Evolución"
            st.rerun()

# --- Evolución: un panel por objetivo -----------------------------------------
with evolucion:
    avances = db.avances_de(paciente_id)
    if avances.empty:
        st.info("Todavía no hay avances registrados.")
    else:
        st.plotly_chart(grafico_evolucion(avances, objetivos), width="stretch", config={"displayModeBar": False})
        with st.expander("Ver los datos en tabla"):
            tabla = avances.assign(fecha=avances["fecha"].dt.strftime("%d/%m/%Y"), nivel=avances["nivel"].map(nivel_texto))
            st.dataframe(tabla, hide_index=True, width="stretch")

# --- Informe para la familia ---------------------------------------------------
with informe:
    ultimas = sesiones[:N_SESIONES_INFORME][::-1]  # las más recientes, en orden de fecha
    if not ultimas:
        st.info("Hace falta al menos una sesión para armar el informe.")
    else:
        periodo = f"del {fecha_texto(ultimas[0]['fecha'])} al {fecha_texto(ultimas[-1]['fecha'])}"
        st.markdown(
            f"Resumen en lenguaje simple de las últimas {len(ultimas)} sesiones ({periodo}), "
            f"para {paciente['apoderado']}."
        )
        if st.button("Generar informe", type="primary", icon=":material/description:", key=f"informe_{paciente_id}"):
            if usar_ia():
                try:
                    with st.spinner("Escribiendo el informe…"):
                        st.session_state["informe"] = {
                            "paciente_id": paciente_id,
                            "periodo": periodo,
                            "contenido": generar_informe(paciente, objetivos, ultimas),
                        }
                except Exception as error:
                    st.error(f"No se pudo generar el informe: {error}")

        guardado = st.session_state.get("informe")
        if guardado and guardado["paciente_id"] == paciente_id:
            inf = guardado["contenido"]
            progreso = progreso_objetivos(ultimas, objetivos)
            with st.container(border=True):
                st.markdown(inf.saludo)
                st.markdown(inf.como_va)
                st.markdown("**Lo que logró**\n" + "\n".join(f"- {x}" for x in inf.logros))
                st.markdown("**En qué seguimos trabajando**\n" + "\n".join(f"- {x}" for x in inf.seguimos_trabajando))
                st.markdown("**Cómo va cada objetivo**\n" + "\n".join(f"- {x}" for x in progreso))
                st.markdown("**Ideas para casa**\n" + "\n".join(f"- {x}" for x in inf.en_casa))
                st.markdown(inf.cierre)
            st.download_button(
                "Descargar PDF",
                data=informe_a_pdf(inf, paciente, guardado["periodo"], progreso),
                file_name=f"informe-{paciente['nombre'].split()[0].lower()}-{date.today().isoformat()}.pdf",
                mime="application/pdf",
                icon=":material/download:",
                on_click="ignore",
            )
