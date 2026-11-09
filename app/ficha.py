"""Página: ficha del paciente.

Arriba, la nueva atención: el médico graba la consulta y, al terminar, la IA
arma el resumen, la receta y lo nuevo de la historia clínica; el médico lo
revisa, lo firma y lo guarda. Abajo, tres pestañas: datos personales,
historia clínica y atenciones.
"""

import json
from datetime import date, datetime, time, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

from ai.cliente import hay_clave
from ai.esquemas import (CIE10, HISTORIA_VACIA, Diagnostico, HistoriaClinica, Medicamento, NotaAtencion,
                         fusionar_historia)
from ai.generar import procesar_atencion
from ai.transcribir import transcribir
from app.formato import (TITULOS_HISTORIA, dia_texto, diagnostico_texto, fecha_texto, momento_texto,
                         mostrar_atencion, mostrar_historia, mostrar_receta)
from backend import db
from backend.pdf import receta_a_pdf
from backend.reglas import alertas_receta

PESTANAS = ["Datos personales", "Historia clínica", "Atenciones"]
CARPETA_EJEMPLOS = Path(__file__).resolve().parent.parent / "data" / "audios_demo"
MAX_USOS_POR_VISITANTE = 20  # segundo seguro para el saldo de la API en la URL pública
COLUMNAS_RECETA = {"medicamento": "Medicamento (DCI y concentración)", "forma_farmaceutica": "Forma",
                   "via": "Vía", "dosis": "Dosis", "frecuencia": "Frecuencia", "duracion": "Duración",
                   "indicaciones": "Indicaciones"}


def lineas(texto: str) -> list[str]:
    """Convierte un cuadro de texto (un ítem por línea) en lista."""
    return [l.strip(" -•\t") for l in texto.splitlines() if l.strip(" -•\t")]


def filas(tabla: pd.DataFrame, columna_clave: str) -> list[dict]:
    """Filas de una tabla editable, sin las vacías y con textos limpios."""
    resultado = []
    for fila in tabla.to_dict("records"):
        limpia = {c: ("" if pd.isna(v) else str(v)).strip() for c, v in fila.items()}
        if limpia[columna_clave]:
            resultado.append(limpia)
    return resultado


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
proxima = db.proxima_cita_de(paciente_id)

# Si venimos de "Atender" en la agenda, la atención queda enlazada a esa cita.
cita = db.obtener_cita(st.session_state["cita_id"]) if st.session_state.get("cita_id") else None
if not cita or cita["paciente_id"] != paciente_id or cita["estado"] != "Programada":
    cita = None

st.title(paciente["nombre"])
st.caption(
    f"{paciente['edad']} · {paciente['sexo']} · Apoderado: {paciente['apoderado']} · "
    f"{len(atenciones)} atenciones · última: {fecha_texto(atenciones[0]['fecha'] if atenciones else None)}"
    + (f" · próxima cita: {dia_texto(proxima['fecha'])}, {proxima['hora']}" if proxima else "")
)
if aviso := st.session_state.pop("aviso", None):
    st.success(aviso, icon=":material/check_circle:")
for alerta in st.session_state.pop("alertas_guardadas", []):
    st.warning(alerta, icon=":material/medication:")

# --- Nueva atención -----------------------------------------------------------
with st.container(border=True):
    st.markdown("#### Nueva atención")
    if cita:
        st.info(f"Atendiendo la cita de las {cita['hora']} ({cita['tipo'].lower()}).", icon=":material/event_available:")
    st.caption(
        "Graba la consulta completa. Al terminar, Ceni transcribe el audio con Whisper y arma el resumen, "
        "la receta y lo nuevo de la historia clínica para que lo revises y lo firmes. "
        "El audio no se guarda: solo la transcripción. "
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
                            f"Diagnósticos: {', '.join(d.descripcion for d in historia.diagnosticos)}. "
                            "Melatonina, metilfenidato, risperidona, TEA, TDAH, terapia ocupacional, pictogramas."
                        )
                        texto = transcribir(audio, nombre_archivo, vocabulario)
                    else:
                        texto = escrito.strip()
                    st.write("Armando el resumen, la receta y la historia clínica…")
                    resultado = procesar_atencion(texto, paciente, historia)
                    estado.update(label="Listo. Revisa y firma.", state="complete", expanded=False)
                st.session_state["borrador"] = {
                    "id": st.session_state["usos_ia"],  # cambia en cada proceso: reinicia el formulario
                    "paciente_id": paciente_id,
                    "transcripcion": texto,
                    "resultado": resultado,
                    "consentimiento_en": datetime.now().isoformat(timespec="seconds"),
                }
            except Exception as error:  # clave inválida, sin saldo, audio dañado...
                st.error(f"No se pudo procesar la atención: {error}")

    # --- Revisión y firma del médico ------------------------------------------
    borrador = st.session_state.get("borrador")
    if borrador and borrador["paciente_id"] == paciente_id:
        resultado, b = borrador["resultado"], borrador["id"]
        nota = resultado.atencion
        propuesta = fusionar_historia(historia, resultado.historia_nueva)
        with st.expander("Ver la transcripción"):
            st.write(borrador["transcripcion"])
        with st.form(f"revision_{b}"):
            st.markdown("##### Revisa, corrige y firma")
            if nota.por_confirmar:
                st.warning("Por confirmar: " + "; ".join(nota.por_confirmar), icon=":material/help:")
            fecha = st.date_input("Fecha de la atención", value=date.today(), format="DD/MM/YYYY")
            resumen = st.text_area("Resumen", nota.resumen, height=90)
            izq, der = st.columns(2)
            motivo = izq.text_input("Motivo", nota.motivo)
            proximo = der.text_input("Próximo control", nota.proximo_control)
            relato = izq.text_area("Relato de la familia (uno por línea)", "\n".join(nota.relato))
            examen = der.text_area("Examen (uno por línea)", "\n".join(nota.examen))
            plan = st.text_area("Plan (uno por línea)", "\n".join(nota.plan))

            st.markdown("**Diagnósticos** (con código CIE-10)")
            diagnosticos_editados = st.data_editor(
                pd.DataFrame([d.model_dump() for d in nota.diagnosticos], columns=["descripcion", "cie10"]),
                num_rows="dynamic", hide_index=True, width="stretch", key=f"dx_{b}",
                column_config={
                    "descripcion": st.column_config.TextColumn("Diagnóstico"),
                    "cie10": st.column_config.SelectboxColumn(
                        "CIE-10", options=["", *CIE10], format_func=lambda c: f"{c} · {CIE10[c]}" if c else "Sin código"
                    ),
                },
            )

            st.markdown("**Receta** (puedes agregar o borrar filas)")
            for alerta in alertas_receta(resultado.receta, propuesta):
                st.warning(alerta, icon=":material/medication:")
            receta_editada = st.data_editor(
                pd.DataFrame([m.model_dump() for m in resultado.receta], columns=list(COLUMNAS_RECETA)),
                num_rows="dynamic", hide_index=True, width="stretch", key=f"receta_{b}",
                column_config={c: st.column_config.TextColumn(t) for c, t in COLUMNAS_RECETA.items()},
            )

            st.markdown("**Historia clínica actualizada** (incluye lo nuevo de esta consulta)")
            st.caption("Los diagnósticos de esta atención se agregan solos a la historia si no estaban.")
            nueva = resultado.historia_nueva.model_dump()
            campos_historia = {}
            hc_izq, hc_der = st.columns(2)
            editables = [c for c in TITULOS_HISTORIA if c != "diagnosticos"]
            for i, campo in enumerate(editables):
                valor = getattr(propuesta, campo)
                etiqueta = TITULOS_HISTORIA[campo] + (" · actualizado hoy" if nueva[campo] else "")
                columna = hc_izq if i % 2 == 0 else hc_der
                if isinstance(valor, list):
                    campos_historia[campo] = lineas(columna.text_area(f"{etiqueta} (uno por línea)", "\n".join(valor)))
                else:
                    campos_historia[campo] = columna.text_area(etiqueta, valor).strip()

            st.markdown("**Próximo control**")
            semanas = nota.proximo_control_semanas
            agendar_col, fecha_col, hora_col = st.columns([2, 2, 1.4], vertical_alignment="bottom")
            agendar = agendar_col.checkbox("Agendar el próximo control", value=semanas > 0)
            fecha_control = fecha_col.date_input(
                "Fecha", value=date.today() + timedelta(weeks=semanas or 4), format="DD/MM/YYYY"
            )
            hora_control = hora_col.time_input("Hora", value=time(9, 0), step=timedelta(minutes=20))
            por_confirmar = st.text_area("Por confirmar (bórralo cuando lo hayas revisado)", "\n".join(nota.por_confirmar))

            st.caption(f"Al firmar, la atención queda registrada a nombre de {medico['nombre']}, con fecha y hora.")
            firmar = st.form_submit_button("Firmar y guardar", type="primary", icon=":material/signature:")
        if firmar:
            receta = [Medicamento(**fila) for fila in filas(receta_editada, "medicamento")]
            diagnosticos = [Diagnostico(**fila) for fila in filas(diagnosticos_editados, "descripcion")]
            nota_final = NotaAtencion(
                resumen=resumen.strip(), motivo=motivo.strip(), relato=lineas(relato), examen=lineas(examen),
                diagnosticos=diagnosticos, plan=lineas(plan), proximo_control=proximo.strip(),
                proximo_control_semanas=semanas, por_confirmar=lineas(por_confirmar),
            )
            # La historia editada por el médico + los diagnósticos de hoy que no estaban.
            historia_final = fusionar_historia(
                HistoriaClinica(**campos_historia, diagnosticos=propuesta.diagnosticos),
                HISTORIA_VACIA.model_copy(update={"diagnosticos": diagnosticos}),
            )
            db.guardar_atencion(
                paciente_id, fecha, borrador["transcripcion"], nota_final, receta, historia_final,
                firmado_por=medico["nombre"], consentimiento_en=borrador["consentimiento_en"],
                cita_id=cita["id"] if cita else None,
                proxima_cita=(fecha_control, hora_control.strftime("%H:%M")) if agendar else None,
            )
            del st.session_state["borrador"]
            st.session_state.pop("cita_id", None)
            st.session_state["aviso"] = (
                f"Atención del {fecha_texto(fecha)} firmada y guardada. La historia clínica se actualizó"
                + (f" y el próximo control quedó agendado para el {dia_texto(fecha_control)}." if agendar else ".")
            )
            st.session_state["alertas_guardadas"] = alertas_receta(receta, historia_final)
            st.session_state["ir_a_pestana"] = "Historia clínica"
            st.rerun()

# --- Pestañas -------------------------------------------------------------------
# Después de guardar saltamos a otra pestaña; hay que fijarlo antes de dibujarlas.
if "ir_a_pestana" in st.session_state:
    st.session_state["pestana"] = st.session_state.pop("ir_a_pestana")
datos_tab, historia_tab, atenciones_tab = st.tabs(PESTANAS, key="pestana")

with datos_tab:
    proxima_texto = f"{dia_texto(proxima['fecha'])}, {proxima['hora']}" if proxima else "sin cita programada"
    st.markdown(
        f"- **Nombre:** {paciente['nombre']}\n"
        f"- **Fecha de nacimiento:** {fecha_texto(paciente['fecha_nacimiento'])} ({paciente['edad']})\n"
        f"- **Sexo:** {paciente['sexo']}\n"
        f"- **Apoderado:** {paciente['apoderado']}\n"
        f"- **Distrito:** {paciente['distrito'] or '—'}\n"
        f"- **Colegio:** {paciente['colegio'] or '—'}\n"
        f"- **Seguro:** {paciente['seguro']}\n"
        f"- **Próxima cita:** {proxima_texto}"
    )

with historia_tab:
    st.caption(f"Actualizada el {fecha_texto(actualizada)}.")
    mostrar_historia(historia)
    st.divider()
    if atenciones:
        mostrar_receta(atenciones[0]["receta"], f"Medicación actual (receta del {fecha_texto(atenciones[0]['fecha'])})")
    st.markdown("**Evolución**")
    if not atenciones:
        st.markdown("Todavía no hay atenciones.")
    for a in atenciones:
        st.markdown(f"- **{fecha_texto(a['fecha'])}.** {a['nota'].resumen}")
    expediente = {
        "paciente": paciente,
        "historia_clinica": historia.model_dump(),
        "atenciones": [
            {"fecha": a["fecha"], "nota": a["nota"].model_dump(), "receta": [m.model_dump() for m in a["receta"]],
             "firmado_por": a["firmado_por"], "firmado_en": a["firmado_en"]}
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
        dx = ", ".join(d.cie10 for d in a["nota"].diagnosticos if d.cie10)
        with st.expander(f"{fecha_texto(a['fecha'])} · {a['nota'].motivo}" + (f" · {dx}" if dx else ""), expanded=(i == 0)):
            mostrar_atencion(a["nota"], a["receta"])
            st.caption(
                f"Firmado por {a['firmado_por']} el {momento_texto(a['firmado_en'])}. "
                f"La familia autorizó la grabación: {momento_texto(a['consentimiento_en'])}."
            )
            for alerta in alertas_receta(a["receta"], historia):
                st.warning(alerta, icon=":material/medication:")
            botones = st.columns([1, 1, 3])
            if a["receta"]:
                botones[0].download_button(
                    "Receta en PDF",
                    receta_a_pdf(a["receta"], paciente, medico, fecha_texto(a["fecha"]),
                                 a["nota"].diagnosticos, a["nota"].plan, a["firmado_en"]),
                    file_name=f"receta-{paciente_id}-{a['fecha']}.pdf", mime="application/pdf",
                    icon=":material/picture_as_pdf:", key=f"pdf_{a['id']}", on_click="ignore",
                )
            if a["transcripcion"]:
                with botones[1].popover("Transcripción"):
                    st.write(a["transcripcion"])
