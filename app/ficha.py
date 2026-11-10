"""Página: ficha del paciente.

Arriba, quién es el paciente. Debajo, cuatro pestañas:
- Nueva atención: el médico graba la consulta y, al terminar, la IA arma la
  nota (en el orden del formato de consulta externa del MINSA), la receta y lo
  nuevo de la historia clínica. El médico lo revisa, lo corrige y lo firma.
- Historia clínica: la historia acumulada, la medicación actual y la evolución.
- Atenciones: todas las consultas, con su receta en PDF.
- Datos personales.
"""

import json
from datetime import date, datetime, time, timedelta
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

from ai.cliente import hay_clave
from ai.esquemas import (CIE10, HISTORIA_VACIA, TIPOS_DIAGNOSTICO, Diagnostico, FuncionesBiologicas, HistoriaClinica,
                         Medicamento, NotaAtencion, SignosVitales, fusionar_historia)
from ai.generar import procesar_atencion
from ai.transcribir import transcribir
from app import estilo
from app.formato import (TITULOS_FUNCIONES, TITULOS_HISTORIA, chips_paciente, cuando_texto, dia_texto, fecha_texto,
                         historia_html, momento_texto, mostrar_atencion, receta_html, signos_html)
from backend import db
from backend.pdf import receta_a_pdf
from backend.reglas import alertas_receta

NUEVA, HISTORIA, ATENCIONES, DATOS = "Nueva atención", "Historia clínica", "Atenciones", "Datos personales"
PASOS = ["La familia autoriza", "Graba la consulta", "Revisa y firma"]
CARPETA_EJEMPLOS = Path(__file__).resolve().parent.parent / "data" / "audios_demo"
MAX_USOS_POR_VISITANTE = 20  # segundo seguro para el saldo de la API en la URL pública
COLUMNAS_RECETA = {"medicamento": "Medicamento (DCI y concentración)", "forma_farmaceutica": "Forma",
                   "via": "Vía", "dosis": "Dosis", "frecuencia": "Frecuencia", "duracion": "Duración",
                   "cantidad": "Cantidad", "indicaciones": "Indicaciones"}
SIGNOS = {  # campo: (etiqueta, paso, formato)
    "peso_kg": ("Peso (kg)", 0.1, "%.1f"), "talla_cm": ("Talla (cm)", 0.5, "%.1f"),
    "perimetro_cefalico_cm": ("Perímetro cefálico (cm)", 0.1, "%.1f"), "temperatura_c": ("Temperatura (°C)", 0.1, "%.1f"),
    "frecuencia_cardiaca": ("FC (lpm)", 1, "%d"), "frecuencia_respiratoria": ("FR (rpm)", 1, "%d"),
}


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


# --- Quién es el paciente ------------------------------------------------------
pacientes = db.listar_pacientes()
nombres = {p["id"]: p["nombre"] for p in pacientes}
if st.session_state.get("paciente_id") not in nombres:
    st.session_state["paciente_id"] = pacientes[0]["id"]
paciente_id = st.session_state["paciente_id"]  # lo cambia el selector de abajo (key="paciente_id")

paciente = db.obtener_paciente(paciente_id)
historia, actualizada = db.historia_de(paciente_id)
atenciones = db.atenciones_de(paciente_id)  # de la más reciente a la más antigua
medico = db.medico()
proxima = db.proxima_cita_de(paciente_id)

# Si venimos de "Atender" en la agenda, la atención queda enlazada a esa cita.
cita = db.obtener_cita(st.session_state["cita_id"]) if st.session_state.get("cita_id") else None
if not cita or cita["paciente_id"] != paciente_id or cita["estado"] != "Programada":
    cita = None
borrador = st.session_state.get("borrador")
if borrador and borrador["paciente_id"] != paciente_id:
    borrador = None

with st.container(key="tarjeta-encabezado"):
    quien, cambiar = st.columns([3, 1.1], vertical_alignment="center")
    etiquetas = chips_paciente(historia.diagnosticos, historia.alergias)
    if proxima:
        etiquetas += estilo.chips([estilo.chip(
            f"Próxima cita: {cuando_texto(proxima['fecha'])}, {proxima['hora']}", "cielo")])
    quien.html(estilo.persona(
        paciente["nombre"], paciente_id,
        f"{paciente['edad']} · {paciente['sexo']} · {paciente['hc']} · {paciente['seguro']} · "
        f"Apoderado: {paciente['apoderado']}",
        f'<div style="margin-top:.4rem">{etiquetas}</div>', grande=True,
    ))
    cambiar.selectbox("Cambiar de paciente", list(nombres), format_func=nombres.get, key="paciente_id")

if aviso := st.session_state.pop("aviso", None):
    st.success(aviso, icon=":material/check_circle:")
for alerta in st.session_state.pop("alertas_guardadas", []):
    st.warning(alerta, icon=":material/medication:")

# Al venir de la agenda o después de firmar, abrimos una pestaña en particular.
if "ir_a_pestana" in st.session_state:
    st.session_state["pestana"] = st.session_state.pop("ir_a_pestana")
nueva_tab, historia_tab, atenciones_tab, datos_tab = st.tabs([NUEVA, HISTORIA, ATENCIONES, DATOS], key="pestana")

# --- Nueva atención ------------------------------------------------------------
with nueva_tab:
    autorizado = st.session_state.get(f"autorizado_{paciente_id}", False)
    estilo.html(estilo.pasos(PASOS, 2 if borrador else 1 if autorizado else 0))
    if cita:
        st.info(f"Atendiendo la cita de las {cita['hora']} ({cita['tipo'].lower()}).", icon=":material/event_available:")

    grabar, ayuda = st.columns([1.6, 1], gap="large")
    with grabar, st.container(key="tarjeta-grabar"):
        autorizado = st.toggle("La familia autorizó grabar la consulta", key=f"autorizado_{paciente_id}")
        grabado = st.audio_input("Graba la consulta completa", key=f"audio_{paciente_id}", disabled=not autorizado)
        with st.container(horizontal=True, vertical_alignment="center"):
            procesar = st.button("Terminar y procesar", type="primary", icon=":material/auto_awesome:",
                                 key=f"procesar_{paciente_id}")
            with st.popover("¿Sin micrófono?", icon=":material/upload:", type="tertiary"):
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
    with ayuda:
        usadas = db.transcripciones_semana(paciente_id)
        estilo.html(
            estilo.bloque("Cómo funciona", '<p class="ceni-texto">Graba toda la consulta. Al terminar, Ceni la '
                          "transcribe con Whisper y arma la nota, la receta y lo nuevo de la historia clínica. "
                          "Tú revisas, corriges y firmas.</p>")
            + estilo.chips([
                estilo.chip("El audio no se guarda", "salvia"),
                estilo.chip(f"{usadas} de {db.LIMITE_SEMANAL} transcripciones esta semana", "gris"),
            ])
        )
        if not hay_clave():
            st.warning("Falta la clave de OpenAI (OPENAI_API_KEY). Sin ella no se puede transcribir.")

    if procesar:
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
                    st.write("Armando la nota, la receta y la historia clínica…")
                    resultado = procesar_atencion(texto, paciente, historia)
                    estado.update(label="Listo. Revisa y firma.", state="complete", expanded=False)
                st.session_state["borrador"] = borrador = {
                    "id": st.session_state["usos_ia"],  # cambia en cada proceso: reinicia el formulario
                    "paciente_id": paciente_id,
                    "transcripcion": texto,
                    "resultado": resultado,
                    "consentimiento_en": datetime.now().isoformat(timespec="seconds"),
                }
            except Exception as error:  # clave inválida, sin saldo, audio dañado...
                st.error(f"No se pudo procesar la atención: {error}")

    # --- Revisión y firma del médico ------------------------------------------
    if borrador:
        resultado, b = borrador["resultado"], borrador["id"]
        nota = resultado.atencion
        propuesta = fusionar_historia(historia, resultado.historia_nueva)
        aviso_col, transcripcion_col = st.columns([3, 1], vertical_alignment="center")
        aviso_col.success("Ceni armó el borrador. Revísalo, corrígelo y fírmalo.", icon=":material/auto_awesome:")
        with transcripcion_col.popover("Ver la transcripción", icon=":material/subject:", width="stretch"):
            st.write(borrador["transcripcion"])

        with st.form(f"revision_{b}"):
            if nota.por_confirmar:
                st.warning("Por confirmar: " + "; ".join(nota.por_confirmar), icon=":material/help:")

            estilo.seccion(1, "Anamnesis")
            c1, c2, c3 = st.columns([1, 2, 1])
            fecha = c1.date_input("Fecha de la atención", value=date.today(), format="DD/MM/YYYY")
            motivo = c2.text_input("Motivo de consulta", nota.motivo)
            tiempo = c3.text_input("Tiempo de enfermedad", nota.tiempo_enfermedad)
            resumen = st.text_area("Resumen de la atención", nota.resumen, height=80)
            relato = st.text_area("Relato de la familia (uno por línea)", "\n".join(nota.relato))

            estilo.seccion(2, "Funciones biológicas", "vacío si no se habló")
            funciones = {}
            for i, (campo, titulo) in enumerate(TITULOS_FUNCIONES.items()):
                if i % 3 == 0:
                    columnas = st.columns(3)
                funciones[campo] = columnas[i % 3].text_input(titulo, getattr(nota.funciones_biologicas, campo)).strip()

            estilo.seccion(3, "Funciones vitales y antropometría", "el IMC lo calcula Ceni")
            signos = {}
            for columna, (campo, (titulo, paso, formato)) in zip(st.columns(len(SIGNOS)), SIGNOS.items()):
                signos[campo] = columna.number_input(
                    titulo, value=getattr(nota.signos_vitales, campo), min_value=0 if paso == 1 else 0.0,
                    step=paso, format=formato,
                )

            estilo.seccion(4, "Examen físico y neurológico")
            examen = st.text_area("Hallazgos (uno por línea)", "\n".join(nota.examen), label_visibility="collapsed")

            estilo.seccion(5, "Diagnósticos", "CIE-10 · D definitivo, P presuntivo, R repetitivo")
            diagnosticos_editados = st.data_editor(
                pd.DataFrame([d.model_dump() for d in nota.diagnosticos], columns=["tipo", "descripcion", "cie10"]),
                num_rows="dynamic", hide_index=True, width="stretch", key=f"dx_{b}",
                column_config={
                    "tipo": st.column_config.SelectboxColumn(
                        "Tipo", options=list(TIPOS_DIAGNOSTICO), format_func=TIPOS_DIAGNOSTICO.get, default="D",
                        width="small", required=True,
                    ),
                    "descripcion": st.column_config.TextColumn("Diagnóstico", width="large"),
                    "cie10": st.column_config.SelectboxColumn(
                        "CIE-10", options=["", *CIE10], format_func=lambda c: f"{c} · {CIE10[c]}" if c else "Sin código"
                    ),
                },
            )

            estilo.seccion(6, "Tratamiento", "receta según la Ley 29459")
            for alerta in alertas_receta(resultado.receta, propuesta):
                st.warning(alerta, icon=":material/medication:")
            receta_editada = st.data_editor(
                pd.DataFrame([m.model_dump() for m in resultado.receta], columns=list(COLUMNAS_RECETA)),
                num_rows="dynamic", hide_index=True, width="stretch", key=f"receta_{b}",
                column_config={c: st.column_config.TextColumn(t) for c, t in COLUMNAS_RECETA.items()},
            )

            estilo.seccion(7, "Plan de trabajo", "uno por línea")
            p1, p2, p3 = st.columns(3)
            examenes = p1.text_area("Exámenes auxiliares", "\n".join(nota.examenes_auxiliares))
            interconsultas = p2.text_area("Interconsultas y terapias", "\n".join(nota.interconsultas))
            indicaciones = p3.text_area("Indicaciones", "\n".join(nota.indicaciones))

            estilo.seccion(8, "Historia clínica", "ya incluye lo nuevo de hoy; los diagnósticos se agregan solos")
            nueva = resultado.historia_nueva.model_dump()
            campos_historia = {}
            hc_izq, hc_der = st.columns(2)
            editables = [c for c in TITULOS_HISTORIA if c != "diagnosticos"]
            for i, campo in enumerate(editables):
                valor = getattr(propuesta, campo)
                titulo = TITULOS_HISTORIA[campo] + (" · nuevo hoy" if nueva[campo] else "")
                columna = hc_izq if i % 2 == 0 else hc_der
                if isinstance(valor, list):
                    campos_historia[campo] = lineas(columna.text_area(f"{titulo} (uno por línea)", "\n".join(valor)))
                else:
                    campos_historia[campo] = columna.text_area(titulo, valor).strip()

            estilo.seccion(9, "Próximo control")
            semanas = nota.proximo_control_semanas
            k1, k2, k3, k4 = st.columns([2, 1.3, 1.3, 1], vertical_alignment="bottom")
            proximo = k1.text_input("Como lo indicó el médico", nota.proximo_control)
            fecha_control = k2.date_input("Fecha", value=date.today() + timedelta(weeks=semanas or 4), format="DD/MM/YYYY")
            hora_control = k3.time_input("Hora", value=time(9, 0), step=timedelta(minutes=20))
            agendar = k4.checkbox("Agendar", value=semanas > 0)
            por_confirmar = st.text_area("Por confirmar (bórralo cuando lo hayas revisado)", "\n".join(nota.por_confirmar))

            st.caption(f"Al firmar, la atención queda registrada a nombre de {medico['nombre']}, con fecha y hora.")
            firmar = st.form_submit_button("Firmar y guardar", type="primary", icon=":material/signature:")

        if firmar:
            receta = [Medicamento(**fila) for fila in filas(receta_editada, "medicamento")]
            diagnosticos = [Diagnostico(**fila) for fila in filas(diagnosticos_editados, "descripcion")]
            nota_final = NotaAtencion(
                resumen=resumen.strip(), motivo=motivo.strip(), tiempo_enfermedad=tiempo.strip(), relato=lineas(relato),
                funciones_biologicas=FuncionesBiologicas(**funciones), signos_vitales=SignosVitales(**signos),
                examen=lineas(examen), diagnosticos=diagnosticos, examenes_auxiliares=lineas(examenes),
                interconsultas=lineas(interconsultas), indicaciones=lineas(indicaciones),
                proximo_control=proximo.strip(), proximo_control_semanas=semanas, por_confirmar=lineas(por_confirmar),
            )
            # La historia editada por el médico + los diagnósticos de hoy (nuevos o confirmados).
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
            st.session_state["ir_a_pestana"] = ATENCIONES
            st.rerun()

# --- Historia clínica -----------------------------------------------------------
with historia_tab:
    izquierda, derecha = st.columns([1.45, 1], gap="medium")
    with izquierda, st.container(key="tarjeta-antecedentes"):
        estilo.html(
            '<div class="ceni-subtitulo">Antecedentes</div>'
            + historia_html(historia, ["antecedentes_perinatales", "desarrollo_psicomotor", "inmunizaciones",
                                       "antecedentes_personales", "antecedentes_familiares"])
        )
        st.caption(f"Historia clínica actualizada el {fecha_texto(actualizada)}.")
    with derecha:
        with st.container(key="tarjeta-problemas"):
            estilo.html('<div class="ceni-subtitulo">Diagnósticos y terapias</div>'
                        + historia_html(historia, ["diagnosticos", "alergias", "terapias"]))
        with st.container(key="tarjeta-medicacion"):
            receta_actual = atenciones[0]["receta"] if atenciones else []
            desde = f"Receta del {fecha_texto(atenciones[0]['fecha'])}" if atenciones else "Sin atenciones"
            estilo.html('<div class="ceni-subtitulo">Medicación actual</div>' + estilo.etiqueta(desde)
                        + receta_html(receta_actual))
        # La atención más reciente que tenga al menos una medida registrada.
        con_signos = next((a for a in atenciones if any(a["nota"].signos_vitales.model_dump().values())), None)
        if con_signos:
            with st.container(key="tarjeta-signos"):
                estilo.html('<div class="ceni-subtitulo">Últimas medidas</div>'
                            + estilo.etiqueta(fecha_texto(con_signos["fecha"]))
                            + signos_html(con_signos["nota"].signos_vitales))

    with st.container(key="tarjeta-evolucion"):
        titulo, descarga = st.columns([3, 1.2], vertical_alignment="center")
        titulo.html('<div class="ceni-subtitulo">Evolución</div>')
        expediente = {
            "paciente": paciente,
            "historia_clinica": historia.model_dump(),
            "atenciones": [
                {"fecha": a["fecha"], "nota": a["nota"].model_dump(), "receta": [m.model_dump() for m in a["receta"]],
                 "firmado_por": a["firmado_por"], "firmado_en": a["firmado_en"]}
                for a in atenciones
            ],
        }
        descarga.download_button(
            "Descargar historia (JSON)", json.dumps(expediente, ensure_ascii=False, indent=2),
            file_name=f"historia-{paciente['hc']}.json", mime="application/json", icon=":material/download:",
            on_click="ignore", type="tertiary",
        )
        hitos = "".join(
            f'<div class="ceni-hito"><div class="fecha">{escape(fecha_texto(a["fecha"]))} · {escape(a["nota"].motivo)}</div>'
            f'<p class="ceni-texto">{escape(a["nota"].resumen)}</p></div>'
            for a in atenciones
        )
        estilo.html(f'<div class="ceni-linea">{hitos}</div>' if hitos else '<p class="ceni-vacio">Todavía no hay atenciones.</p>')

# --- Atenciones -------------------------------------------------------------------
with atenciones_tab:
    if not atenciones:
        st.info("Este paciente todavía no tiene atenciones.", icon=":material/info:")
    for i, a in enumerate(atenciones):
        codigos = ", ".join(d.cie10 for d in a["nota"].diagnosticos if d.cie10)
        titulo = f"{fecha_texto(a['fecha'])} · {a['nota'].motivo}" + (f" · {codigos}" if codigos else "")
        with st.expander(titulo, expanded=(i == 0), icon=":material/stethoscope:"):
            mostrar_atencion(a["nota"], a["receta"])
            for alerta in alertas_receta(a["receta"], historia):
                st.warning(alerta, icon=":material/medication:")
            with st.container(horizontal=True, vertical_alignment="center"):
                if a["receta"]:
                    st.download_button(
                        "Receta en PDF",
                        receta_a_pdf(a["receta"], paciente, medico, fecha_texto(a["fecha"]), a["nota"].diagnosticos,
                                     a["nota"].indicaciones, a["firmado_en"], a["nota"].signos_vitales.peso_kg),
                        file_name=f"receta-{paciente['hc']}-{a['fecha']}.pdf", mime="application/pdf",
                        icon=":material/picture_as_pdf:", key=f"pdf_{a['id']}", on_click="ignore", type="primary",
                    )
                if a["transcripcion"]:
                    with st.popover("Transcripción", icon=":material/subject:"):
                        st.write(a["transcripcion"])
                st.caption(
                    f"Firmado por {a['firmado_por']} el {momento_texto(a['firmado_en'])} · "
                    f"Autorización de la familia: {momento_texto(a['consentimiento_en'])}"
                )

# --- Datos personales ----------------------------------------------------------------
with datos_tab, st.container(key="tarjeta-datos"):
    proxima_texto = f"{dia_texto(proxima['fecha'])}, {proxima['hora']}" if proxima else "Sin cita programada"
    datos = {
        "Nombre": paciente["nombre"],
        "N.º de historia clínica": paciente["hc"],
        "Fecha de nacimiento": f"{fecha_texto(paciente['fecha_nacimiento'])} ({paciente['edad']})",
        "Sexo": paciente["sexo"],
        "Apoderado": paciente["apoderado"],
        "Distrito": paciente["distrito"] or "—",
        "Colegio": paciente["colegio"] or "—",
        "Seguro": paciente["seguro"],
        "Próxima cita": proxima_texto,
    }
    estilo.html('<div class="ceni-datos">' + "".join(
        f'<div class="ceni-dato">{estilo.etiqueta(k)}<div class="valor">{escape(v)}</div></div>' for k, v in datos.items()
    ) + "</div>")
