"""Página 2: ficha del paciente.

Arriba, la nueva atención: el médico graba la consulta y, al terminar, la IA
arma el resumen, la receta y lo nuevo de la historia clínica; el médico lo
revisa y lo guarda. Abajo, tres pestañas: datos personales, historia clínica
y atenciones.
"""

import json
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from ai.cliente import hay_clave
from ai.esquemas import HistoriaClinica, Medicamento, NotaAtencion, fusionar_historia
from ai.generar import procesar_atencion
from ai.transcribir import transcribir
from app.formato import TITULOS_HISTORIA, fecha_texto, mostrar_atencion, mostrar_historia, mostrar_receta
from backend import db
from backend.pdf import receta_a_pdf

PESTANAS = ["Datos personales", "Historia clínica", "Atenciones"]
CARPETA_EJEMPLOS = Path(__file__).resolve().parent.parent / "data" / "audios_demo"
MAX_USOS_POR_VISITANTE = 20  # segundo seguro para el saldo de la API en la URL pública
COLUMNAS_RECETA = {"medicamento": "Medicamento", "dosis": "Dosis", "frecuencia": "Frecuencia",
                   "duracion": "Duración", "indicaciones": "Indicaciones"}


def lineas(texto: str) -> list[str]:
    """Convierte un cuadro de texto (un ítem por línea) en lista."""
    return [l.strip(" -•\t") for l in texto.splitlines() if l.strip(" -•\t")]


def puede_procesar(paciente_id: int) -> bool:
    """Aplica los dos límites: 10 por paciente en 7 días y 20 por visitante."""
    if db.transcripciones_semana(paciente_id) >= db.LIMITE_SEMANAL:
        st.error(f"Este paciente ya tiene {db.LIMITE_SEMANAL} transcripciones en los últimos 7 días. Es el máximo.")
        return False
    if st.session_state.get("usos_ia", 0) >= MAX_USOS_POR_VISITANTE:
        st.error("Llegaste al límite de usos de IA de este demo. Vuelve a intentarlo más tarde.")
        return False
    return True


# --- Elegir paciente ---------------------------------------------------------
pacientes = db.listar_pacientes()
nombres = {p["id"]: p["nombre"] for p in pacientes}
if st.session_state.get("paciente_id") not in nombres:
    st.session_state["paciente_id"] = pacientes[0]["id"]
paciente_id = st.selectbox("Paciente", list(nombres), format_func=nombres.get, key="paciente_id")

paciente = db.obtener_paciente(paciente_id)
historia, actualizada = db.historia_de(paciente_id)
atenciones = db.atenciones_de(paciente_id)  # de la más reciente a la más antigua
medico = db.medico()

st.title(paciente["nombre"])
st.caption(
    f"{paciente['edad']} · {paciente['sexo']} · Apoderado: {paciente['apoderado']} · "
    f"{len(atenciones)} atenciones · última: {fecha_texto(atenciones[0]['fecha'] if atenciones else None)}"
)
if aviso := st.session_state.pop("aviso", None):
    st.success(aviso, icon=":material/check_circle:")

# --- Nueva atención -----------------------------------------------------------
with st.container(border=True):
    st.markdown("#### Nueva atención")
    st.caption(
        "Graba la consulta completa. Al terminar, Ceni transcribe el audio con Whisper y arma el resumen, "
        "la receta y lo nuevo de la historia clínica para que lo revises. "
        f"Transcripciones de este paciente en los últimos 7 días: "
        f"{db.transcripciones_semana(paciente_id)} de {db.LIMITE_SEMANAL}."
    )
    if not hay_clave():
        st.warning("Falta la clave de OpenAI (OPENAI_API_KEY). Sin ella no se puede transcribir.")

    autorizado = st.checkbox("La familia autorizó grabar la consulta", key=f"autorizado_{paciente_id}")
    grabado = st.audio_input("Grabar la consulta", key=f"audio_{paciente_id}", disabled=not autorizado)
    with st.expander("¿Sin micrófono? Sube un audio, usa uno de ejemplo o pega la transcripción"):
        subido = st.file_uploader(
            "Sube un audio", type=["wav", "mp3", "m4a", "ogg", "webm", "mp4"], key=f"subido_{paciente_id}"
        )
        ejemplos = sorted(CARPETA_EJEMPLOS.glob("*.mp3"))
        ejemplo = st.selectbox(
            "Audio de ejemplo (consulta inventada)", [None, *ejemplos],
            format_func=lambda p: "Ninguno" if p is None else p.stem.replace("-", " ").capitalize(),
            key=f"ejemplo_{paciente_id}",
        )
        if ejemplo:
            st.audio(str(ejemplo))
        escrito = st.text_area("O pega la transcripción", key=f"escrito_{paciente_id}")

    if st.button("Terminar atención y procesar", type="primary", icon=":material/auto_awesome:", key=f"procesar_{paciente_id}"):
        hay_audio = bool(grabado or subido or ejemplo)
        if not autorizado:
            st.error("Primero marca que la familia autorizó la grabación.")
        elif not (hay_audio or escrito.strip()):
            st.error("Primero graba la consulta, sube un audio o pega la transcripción.")
        elif puede_procesar(paciente_id):
            st.session_state["usos_ia"] = st.session_state.get("usos_ia", 0) + 1
            db.registrar_transcripcion(paciente_id)
            try:
                with st.status("Ceni está trabajando…", expanded=True) as estado:
                    if hay_audio:
                        st.write("Transcribiendo la consulta con Whisper…")
                        if ejemplo:
                            audio, nombre_archivo = ejemplo.read_bytes(), ejemplo.name
                        else:
                            archivo = grabado or subido
                            audio, nombre_archivo = archivo.getvalue(), archivo.name
                        vocabulario = (
                            f"Consulta de neuropediatría de {paciente['nombre']} con {medico['nombre']}. "
                            f"Diagnósticos: {', '.join(historia.diagnosticos)}. "
                            "Melatonina, metilfenidato, risperidona, TEA, TDAH, terapia ocupacional, pictogramas."
                        )
                        texto = transcribir(audio, nombre_archivo, vocabulario)
                    else:
                        texto = escrito.strip()
                    st.write("Armando el resumen, la receta y la historia clínica…")
                    resultado = procesar_atencion(texto, paciente, historia)
                    estado.update(label="Listo. Revisa antes de guardar.", state="complete", expanded=False)
                st.session_state["borrador"] = {
                    "id": st.session_state["usos_ia"],  # cambia en cada proceso: reinicia el formulario
                    "paciente_id": paciente_id,
                    "transcripcion": texto,
                    "resultado": resultado,
                }
            except Exception as error:  # clave inválida, sin saldo, audio dañado...
                st.error(f"No se pudo procesar la atención: {error}")

    # --- Revisión del médico antes de guardar ---------------------------------
    borrador = st.session_state.get("borrador")
    if borrador and borrador["paciente_id"] == paciente_id:
        resultado, b = borrador["resultado"], borrador["id"]
        nota = resultado.atencion
        propuesta = fusionar_historia(historia, resultado.historia_nueva)
        with st.expander("Ver la transcripción"):
            st.write(borrador["transcripcion"])
        with st.form(f"revision_{b}"):
            st.markdown("##### Revisa y corrige: al guardar, queda en la historia del paciente")
            if nota.por_confirmar:
                st.warning("Por confirmar: " + "; ".join(nota.por_confirmar), icon=":material/help:")
            fecha = st.date_input("Fecha de la atención", value=date.today(), format="DD/MM/YYYY")
            resumen = st.text_area("Resumen", nota.resumen, height=90)
            izq, der = st.columns(2)
            motivo = izq.text_input("Motivo", nota.motivo)
            proximo = der.text_input("Próximo control", nota.proximo_control)
            relato = izq.text_area("Relato de la familia (uno por línea)", "\n".join(nota.relato))
            examen = der.text_area("Examen (uno por línea)", "\n".join(nota.examen))
            diagnosticos = izq.text_area("Diagnósticos (uno por línea)", "\n".join(nota.diagnosticos))
            plan = der.text_area("Plan (uno por línea)", "\n".join(nota.plan))
            por_confirmar = st.text_area("Por confirmar (bórralo cuando lo hayas revisado)", "\n".join(nota.por_confirmar))

            st.markdown("**Receta** (puedes agregar o borrar filas)")
            receta_editada = st.data_editor(
                pd.DataFrame([m.model_dump() for m in resultado.receta], columns=list(COLUMNAS_RECETA)),
                num_rows="dynamic", hide_index=True, width="stretch", key=f"receta_{b}",
                column_config={c: st.column_config.TextColumn(t) for c, t in COLUMNAS_RECETA.items()},
            )

            st.markdown("**Historia clínica actualizada** (incluye lo nuevo de esta consulta)")
            nueva = resultado.historia_nueva.model_dump()
            campos_historia = {}
            hc_izq, hc_der = st.columns(2)
            for i, (campo, titulo) in enumerate(TITULOS_HISTORIA.items()):
                valor = getattr(propuesta, campo)
                etiqueta = titulo + (" · actualizado hoy" if nueva[campo] else "")
                columna = hc_izq if i % 2 == 0 else hc_der
                if isinstance(valor, list):
                    campos_historia[campo] = lineas(columna.text_area(f"{etiqueta} (uno por línea)", "\n".join(valor)))
                else:
                    campos_historia[campo] = columna.text_area(etiqueta, valor).strip()

            guardar = st.form_submit_button("Guardar atención", type="primary", icon=":material/save:")
        if guardar:
            receta = [
                Medicamento(**{c: ("" if pd.isna(v) else str(v)).strip() for c, v in fila.items()})
                for fila in receta_editada.to_dict("records")
                if not pd.isna(fila["medicamento"]) and str(fila["medicamento"]).strip()
            ]
            nota_final = NotaAtencion(
                resumen=resumen.strip(), motivo=motivo.strip(), relato=lineas(relato), examen=lineas(examen),
                diagnosticos=lineas(diagnosticos), plan=lineas(plan), proximo_control=proximo.strip(),
                por_confirmar=lineas(por_confirmar),
            )
            db.guardar_atencion(
                paciente_id, fecha, borrador["transcripcion"], nota_final, receta, HistoriaClinica(**campos_historia)
            )
            del st.session_state["borrador"]
            st.session_state["aviso"] = (
                f"Atención del {fecha_texto(fecha)} guardada. La historia clínica se actualizó y la receta está en Atenciones."
            )
            st.session_state["ir_a_pestana"] = "Historia clínica"
            st.rerun()

# --- Pestañas -------------------------------------------------------------------
# Después de guardar saltamos a otra pestaña; hay que fijarlo antes de dibujarlas.
if "ir_a_pestana" in st.session_state:
    st.session_state["pestana"] = st.session_state.pop("ir_a_pestana")
datos_tab, historia_tab, atenciones_tab = st.tabs(PESTANAS, key="pestana")

with datos_tab:
    st.markdown(
        f"- **Nombre:** {paciente['nombre']}\n"
        f"- **Fecha de nacimiento:** {fecha_texto(paciente['fecha_nacimiento'])} ({paciente['edad']})\n"
        f"- **Sexo:** {paciente['sexo']}\n"
        f"- **Apoderado:** {paciente['apoderado']}\n"
        f"- **Distrito:** {paciente['distrito'] or '—'}\n"
        f"- **Colegio:** {paciente['colegio'] or '—'}\n"
        f"- **Seguro:** {paciente['seguro']}"
    )

with historia_tab:
    st.caption(f"Actualizada el {fecha_texto(actualizada)}.")
    mostrar_historia(historia)
    st.divider()
    if atenciones:
        st.markdown(f"**Medicación actual** (receta del {fecha_texto(atenciones[0]['fecha'])})")
        mostrar_receta(atenciones[0]["receta"])
    st.markdown("**Evolución**")
    if not atenciones:
        st.markdown("Todavía no hay atenciones.")
    for a in atenciones:
        st.markdown(f"- **{fecha_texto(a['fecha'])}.** {a['nota'].resumen}")
    expediente = {
        "paciente": paciente,
        "historia_clinica": historia.model_dump(),
        "atenciones": [
            {"fecha": a["fecha"], "nota": a["nota"].model_dump(), "receta": [m.model_dump() for m in a["receta"]]}
            for a in atenciones
        ],
    }
    st.download_button(
        "Descargar historia completa (JSON)", json.dumps(expediente, ensure_ascii=False, indent=2),
        file_name=f"historia-{paciente_id}.json", mime="application/json", icon=":material/download:",
        on_click="ignore",
    )

with atenciones_tab:
    if not atenciones:
        st.info("Este paciente todavía no tiene atenciones.")
    for i, a in enumerate(atenciones):
        with st.expander(f"{fecha_texto(a['fecha'])} · {a['nota'].motivo}", expanded=(i == 0)):
            mostrar_atencion(a["nota"], a["receta"])
            if a["receta"]:
                st.download_button(
                    "Receta en PDF",
                    receta_a_pdf(a["receta"], paciente, medico, fecha_texto(a["fecha"]), a["nota"].plan),
                    file_name=f"receta-{paciente_id}-{a['fecha']}.pdf", mime="application/pdf",
                    icon=":material/picture_as_pdf:", key=f"pdf_{a['id']}", on_click="ignore",
                )
            if a["transcripcion"]:
                with st.popover("Ver transcripción"):
                    st.write(a["transcripcion"])
