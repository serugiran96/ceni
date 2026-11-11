"""Página: ficha del paciente.

Arriba, quién es el paciente. Debajo, cuatro pestañas:
- Nueva atención: el médico ve un resumen de la última consulta ("Antes de
  empezar") y graba la consulta. Al terminar, la IA arma la nota (en el orden
  del formato de consulta externa del MINSA), la receta y lo nuevo de la
  historia clínica. El médico lo revisa, lo corrige y lo firma.
- Historia clínica: la historia acumulada, la medicación actual y la evolución.
- Atenciones: todas las consultas, con su receta en PDF.
- Datos personales.

Ceni mide dos tiempos reales para mostrárselos al médico al firmar: cuánto
tardó la IA en armar el borrador y cuánto tardó el médico en revisarlo y firmarlo.
"""

import json
from datetime import date, datetime, time, timedelta
from html import escape
from pathlib import Path
from time import monotonic

import pandas as pd
import streamlit as st

from ai.cliente import hay_clave
from ai.esquemas import (HISTORIA_VACIA, CampoEspecialidad, TIPOS_DIAGNOSTICO, Diagnostico, FuncionesBiologicas, HistoriaClinica,
                         Medicamento, NotaAtencion, SignosVitales, fusionar_historia)
from ai.generar import procesar_atencion
from ai.transcribir import transcribir
from app import estilo
from app.formato import (TITULOS_FUNCIONES, TITULOS_HISTORIA, antes_de_empezar_html, chips_paciente, cuando_texto,
                         dia_texto, duracion_texto, fecha_texto, historia_html, momento_texto, mostrar_atencion,
                         receta_html, signos_html)
from backend import db
from backend.acierto import Acierto, comparar
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


def ir_a_paciente(paciente_id: int, cita_id: int | None) -> None:
    """Callback del botón "Siguiente paciente".

    Va en un callback porque el selector de paciente (key="paciente_id") ya está
    dibujado: su valor solo se puede cambiar antes de que la página se vuelva a dibujar.
    """
    st.session_state["paciente_id"] = paciente_id
    st.session_state["cita_id"] = cita_id
    st.session_state["ir_a_pestana"] = NUEVA
    st.session_state.pop("recien_firmada", None)


# --- Quién es el paciente ------------------------------------------------------
medico = db.medico(st.session_state.get("medico_id", 1))  # quién entró, elegido en la barra lateral
pacientes = db.listar_pacientes(medico["consultorio_id"])  # solo los pacientes de su consultorio
if not pacientes:
    estilo.encabezado("Ficha del paciente", "Todavía no hay pacientes en este consultorio.", medico["consultorio"])
    st.page_link("app/pacientes.py", label="Registrar el primer paciente", icon=":material/person_add:")
    st.stop()
nombres = {p["id"]: p["nombre"] for p in pacientes}
if st.session_state.get("paciente_id") not in nombres:
    st.session_state["paciente_id"] = pacientes[0]["id"]
paciente_id = st.session_state["paciente_id"]  # lo cambia el selector de abajo (key="paciente_id")

paciente = db.obtener_paciente(paciente_id)
historia, actualizada = db.historia_de(paciente_id)
atenciones = db.atenciones_de(paciente_id)  # de la más reciente a la más antigua
proxima = db.proxima_cita_de(paciente_id, medico["id"])


def acierto_texto(acierto: Acierto) -> str:
    """P. ej.: 'Ceni acertó 16 de 18 datos (89%): corregiste 1, agregaste 1.'"""
    if not acierto.total:
        return "Ceni no propuso datos en esta atención."
    cambios = [f"{verbo} {n}" for verbo, n in (("corregiste", acierto.corregidos), ("agregaste", acierto.agregados),
                                               ("borraste", acierto.borrados)) if n]
    detalle = ", ".join(cambios) if cambios else "no cambiaste nada"
    return f"Ceni acertó {acierto.acertados} de {acierto.total} datos ({acierto.porcentaje:.0%}): {detalle}."


def receta_pdf(a: dict) -> bytes:
    """La receta de una atención, en PDF."""
    return receta_a_pdf(a["receta"], paciente, medico, fecha_texto(a["fecha"]), a["nota"].diagnosticos,
                        a["nota"].indicaciones, a["firmado_en"], a["nota"].signos_vitales.peso_kg)


# Si venimos de "Atender" en la agenda, la atención queda enlazada a esa cita.
cita = db.obtener_cita(st.session_state["cita_id"]) if st.session_state.get("cita_id") else None
if not cita or cita["paciente_id"] != paciente_id or cita["estado"] != "Programada" or cita["medico_id"] != medico["id"]:
    cita = None
borrador = st.session_state.get("borrador")
# El borrador es de un paciente y de quien lo grabó: con otro paciente u otro profesional no se muestra (ni se borra).
if borrador and (borrador["paciente_id"] != paciente_id or borrador["medico_id"] != medico["id"]):
    borrador = None

with st.container(key="heroe-paciente"):
    quien, cambiar = st.columns([3, 1.1], vertical_alignment="center")
    etiquetas = chips_paciente(historia.diagnosticos, historia.alergias, sobre_color=True)
    if proxima:
        etiquetas += estilo.chips([estilo.chip(
            f"Próxima cita: {cuando_texto(proxima['fecha'])}, {proxima['hora']}", "vidrio")])
    quien.html(estilo.persona(
        paciente["nombre"], paciente_id,
        f"{paciente['edad']} · {paciente['sexo']} · {paciente['hc']} · {paciente['seguro']} · "
        f"Apoderado: {paciente['apoderado']}",
        f'<div style="margin-top:.45rem">{etiquetas}</div>', grande=True,
    ))
    cambiar.selectbox("Cambiar de paciente", list(nombres), format_func=nombres.get, key="paciente_id")

# --- Recién firmada: los tiempos, la receta y el siguiente paciente -----------------
firmada = st.session_state.get("recien_firmada")
if firmada and firmada["paciente_id"] == paciente_id:
    atencion_firmada = next((a for a in atenciones if a["id"] == firmada["atencion_id"]), None)
    siguiente = next((c for c in db.citas_entre(date.today(), date.today(), medico["id"])
                      if c["estado"] == "Programada" and c["paciente_id"] != paciente_id), None)
    with st.container(key="listo-firmada"):
        estilo.html(
            estilo.titulo("Atención firmada y guardada", "task_alt", "vidrio")
            + f'<p class="ceni-texto">Ceni armó el borrador en <b>{duracion_texto(firmada["segundos_ia"])}</b> '
            f'y tú lo revisaste y firmaste en <b>{duracion_texto(firmada["segundos_revision"])}</b>. '
            f'{escape(firmada["detalle"])}</p>'
            + f'<p class="ceni-texto" style="margin-top:.35rem"><b>{escape(firmada["acierto"])}</b>'
            + (f' Cambiaste: {escape(", ".join(firmada["cambios"]))}.' if firmada["cambios"] else "") + "</p>"
        )
        with st.container(horizontal=True):
            if atencion_firmada and atencion_firmada["receta"]:
                st.download_button(
                    "Receta en PDF", receta_pdf(atencion_firmada), file_name=f"receta-{paciente['hc']}.pdf",
                    mime="application/pdf", icon=":material/picture_as_pdf:", type="primary", on_click="ignore",
                    key="pdf_firmada",
                )
            if siguiente:
                st.button(f"Siguiente: {siguiente['nombre']} · {siguiente['hora']}", icon=":material/arrow_forward:",
                          on_click=ir_a_paciente, args=(siguiente["paciente_id"], siguiente["id"]))
            if st.button("Volver a la agenda", icon=":material/calendar_month:"):
                st.session_state.pop("recien_firmada", None)
                st.switch_page("app/agenda.py")

if aviso := st.session_state.pop("aviso", None):
    st.success(aviso, icon=":material/check_circle:")
for alerta in st.session_state.pop("alertas_guardadas", []):
    st.warning(alerta, icon=":material/medication:")

# Al venir de la agenda o después de firmar, abrimos una pestaña en particular.
# on_change="rerun" hace que las pestañas guarden su estado en st.session_state["pestana"];
# sin eso, Streamlit ignora el valor que le ponemos aquí.
if "ir_a_pestana" in st.session_state:
    st.session_state["pestana"] = st.session_state.pop("ir_a_pestana")
nueva_tab, historia_tab, atenciones_tab, datos_tab = st.tabs(
    [NUEVA, HISTORIA, ATENCIONES, DATOS], key="pestana", on_change="rerun")

# --- Nueva atención ------------------------------------------------------------
with nueva_tab:
    autorizado = st.session_state.get(f"autorizado_{paciente_id}", False)
    estilo.html(estilo.pasos(PASOS, 2 if borrador else 1 if autorizado else 0))

    # Con el borrador listo, la grabadora se pliega para que el formulario quede arriba.
    zona_grabar = (st.expander("Grabar otra vez o usar otro audio", icon=":material/mic:") if borrador
                   else st.container())
    grabar, antes = zona_grabar.columns([1.5, 1], gap="large")
    with grabar, st.container(key="tarjeta-grabar"):
        detalle = f"Cita de las {cita['hora']} · {cita['tipo'].lower()}" if cita else ""
        estilo.html(estilo.titulo("Graba la consulta", "mic", "coral", detalle))
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
        usadas = db.transcripciones_semana(paciente_id)
        estilo.html(estilo.chips([
            estilo.chip("El audio no se guarda", "menta"),
            estilo.chip("Ceni documenta; tú decides y firmas", "violeta"),
            estilo.chip(f"{usadas} de {db.LIMITE_SEMANAL} transcripciones esta semana", "gris"),
        ]))
        if not hay_clave():
            st.warning("Falta la clave de OpenAI (OPENAI_API_KEY). Sin ella no se puede transcribir.")

    with antes, st.container(key="tarjeta-antes"):
        estilo.html(estilo.titulo("Antes de empezar", "lightbulb", "sol") + antes_de_empezar_html(atenciones, historia))

    if procesar:
        hay_audio = bool(grabado or subido or ejemplo)
        if not autorizado:
            st.error("Primero marca que la familia autorizó la grabación.")
        elif not (hay_audio or escrito.strip()):
            st.error("Primero graba la consulta, sube un audio o pega la transcripción.")
        elif puede_procesar(paciente_id):
            st.session_state["usos_ia"] = st.session_state.get("usos_ia", 0) + 1
            st.session_state.pop("recien_firmada", None)
            db.registrar_transcripcion(paciente_id)
            inicio = monotonic()  # para decirle al médico cuánto tardó Ceni
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
                            f"Consulta de {medico['especialidad'].lower()} de {paciente['nombre']} con {medico['nombre']}. "
                            f"Diagnósticos: {', '.join(d.descripcion for d in historia.diagnosticos)}. "
                            f"{medico['vocabulario']}"
                        )
                        texto, quien = transcribir(audio, nombre_archivo, vocabulario)
                        st.write(f"Transcrita con Whisper en {quien}.")
                    else:
                        texto = escrito.strip()
                    st.write("Armando la nota, la receta y la historia clínica…")
                    resultado = procesar_atencion(texto, paciente, historia, medico)
                    estado.update(label="Listo. Revisa y firma.", state="complete", expanded=False)
                st.session_state["borrador"] = borrador = {
                    "id": st.session_state["usos_ia"],  # cambia en cada proceso: reinicia el formulario
                    "paciente_id": paciente_id,
                    "medico_id": medico["id"],
                    "transcripcion": texto,
                    "resultado": resultado,
                    "consentimiento_en": datetime.now().isoformat(timespec="seconds"),
                    "segundos_ia": monotonic() - inicio,
                    "listo_en": monotonic(),  # desde aquí empieza la revisión del médico
                }
            except Exception as error:  # clave inválida, sin saldo, audio dañado...
                st.error(f"No se pudo procesar la atención: {error}")

    # --- Revisión y firma del médico ------------------------------------------
    if borrador:
        resultado, b = borrador["resultado"], borrador["id"]
        nota = resultado.atencion
        propuesta = fusionar_historia(historia, resultado.historia_nueva)
        with st.container(key="heroe-borrador"):
            aviso_col, transcripcion_col = st.columns([3, 1], vertical_alignment="center")
            aviso_col.html(
                estilo.titulo("Tu borrador está listo", "auto_awesome", "vidrio")
                + f'<p class="ceni-texto">Ceni lo armó en {duracion_texto(borrador["segundos_ia"])} con lo que se habló '
                "en la consulta. Revísalo, corrige lo que haga falta y fírmalo.</p>"
            )
            with transcripcion_col.popover("Ver la transcripción", icon=":material/subject:", width="stretch"):
                st.write(borrador["transcripcion"])

        with st.form(f"revision_{b}"):
            if nota.por_confirmar:
                st.warning("Por confirmar: " + "; ".join(nota.por_confirmar), icon=":material/help:")

            estilo.seccion(1, "Anamnesis", tono="violeta")
            c1, c2, c3 = st.columns([1, 2, 1])
            fecha = c1.date_input("Fecha de la atención", value=date.today(), format="DD/MM/YYYY")
            motivo = c2.text_input("Motivo de consulta", nota.motivo)
            tiempo = c3.text_input("Tiempo de enfermedad", nota.tiempo_enfermedad)
            resumen = st.text_area("Resumen de la atención", nota.resumen, height=80)
            relato = st.text_area("Relato de la familia (uno por línea)", "\n".join(nota.relato))

            estilo.seccion(2, "Funciones biológicas", "vacío si no se habló", tono="menta")
            funciones = {}
            for i, (campo, titulo) in enumerate(TITULOS_FUNCIONES.items()):
                if i % 3 == 0:
                    columnas = st.columns(3)
                funciones[campo] = columnas[i % 3].text_input(titulo, getattr(nota.funciones_biologicas, campo)).strip()

            estilo.seccion(3, "Funciones vitales y antropometría", "el IMC lo calcula Ceni", tono="cielo")
            signos = {}
            for columna, (campo, (titulo, paso, formato)) in zip(st.columns(len(SIGNOS)), SIGNOS.items()):
                signos[campo] = columna.number_input(
                    titulo, value=getattr(nota.signos_vitales, campo), min_value=0 if paso == 1 else 0.0,
                    step=paso, format=formato,
                )

            estilo.seccion(4, "Examen físico", tono="coral")
            examen = st.text_area("Hallazgos (uno por línea)", "\n".join(nota.examen), label_visibility="collapsed")

            # Campos propios de la especialidad del médico (vienen de su plantilla, que arma el admin).
            plantilla = medico["plantilla"]
            campos_especialidad = {}
            if plantilla and plantilla.campos:
                estilo.seccion(5, plantilla.nombre, "campos de la especialidad", tono="sol")
                valores = {c.nombre: c.valor for c in nota.campos_especialidad}
                columnas_esp = st.columns(2)
                for i, campo in enumerate(plantilla.campos):
                    campos_especialidad[campo.nombre] = columnas_esp[i % 2].text_area(
                        campo.nombre, valores.get(campo.nombre, ""), help=campo.descripcion, height=90,
                    )

            estilo.seccion(6, "Diagnósticos", "CIE-10 · D definitivo, P presuntivo, R repetitivo", tono="violeta")
            diagnosticos_editados = st.data_editor(
                pd.DataFrame([d.model_dump() for d in nota.diagnosticos], columns=["tipo", "descripcion", "cie10"]),
                num_rows="dynamic", hide_index=True, width="stretch", key=f"dx_{b}",
                column_config={
                    "tipo": st.column_config.SelectboxColumn(
                        "Tipo", options=list(TIPOS_DIAGNOSTICO), format_func=TIPOS_DIAGNOSTICO.get, default="D",
                        width="small", required=True,
                    ),
                    "descripcion": st.column_config.TextColumn("Diagnóstico", width="large"),
                    "cie10": st.column_config.TextColumn("CIE-10", help="Código CIE-10 de la OMS, p. ej. F84.0"),
                },
            )

            estilo.seccion(7, "Tratamiento", "receta según la Ley 29459", tono="rosa")
            for alerta in alertas_receta(resultado.receta, propuesta):
                st.warning(alerta, icon=":material/medication:")
            receta_editada = st.data_editor(
                pd.DataFrame([m.model_dump() for m in resultado.receta], columns=list(COLUMNAS_RECETA)),
                num_rows="dynamic", hide_index=True, width="stretch", key=f"receta_{b}",
                column_config={c: st.column_config.TextColumn(t) for c, t in COLUMNAS_RECETA.items()},
            )

            estilo.seccion(8, "Plan de trabajo", "uno por línea", tono="sol")
            p1, p2, p3 = st.columns(3)
            examenes = p1.text_area("Exámenes auxiliares", "\n".join(nota.examenes_auxiliares))
            interconsultas = p2.text_area("Interconsultas y terapias", "\n".join(nota.interconsultas))
            indicaciones = p3.text_area("Indicaciones", "\n".join(nota.indicaciones))

            estilo.seccion(9, "Historia clínica", "ya incluye lo nuevo de hoy; los diagnósticos se agregan solos",
                           tono="cielo")
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

            estilo.seccion(10, "Próximo control", tono="menta")
            semanas = nota.proximo_control_semanas
            k1, k2, k3, k4 = st.columns([2, 1.3, 1.3, 1], vertical_alignment="bottom")
            proximo = k1.text_input("Como lo indicó el médico", nota.proximo_control)
            fecha_control = k2.date_input("Fecha", value=date.today() + timedelta(weeks=semanas or 4), format="DD/MM/YYYY")
            hora_control = k3.time_input("Hora", value=time(9, 0), step=timedelta(minutes=20))
            agendar = k4.checkbox("Agendar", value=semanas > 0)
            por_confirmar = st.text_area("Por confirmar (bórralo cuando lo hayas revisado)", "\n".join(nota.por_confirmar))

            st.caption(f"Al firmar, la atención queda registrada a nombre de {medico['nombre']}, con fecha y hora.")
            firmar = st.form_submit_button("Firmar y guardar", type="primary", icon=":material/signature:",
                                           key=f"grande-firmar-{b}")

        if firmar:
            receta = [Medicamento(**fila) for fila in filas(receta_editada, "medicamento")]
            diagnosticos = [Diagnostico(**fila) for fila in filas(diagnosticos_editados, "descripcion")]
            nota_final = NotaAtencion(
                resumen=resumen.strip(), motivo=motivo.strip(), tiempo_enfermedad=tiempo.strip(), relato=lineas(relato),
                funciones_biologicas=FuncionesBiologicas(**funciones), signos_vitales=SignosVitales(**signos),
                examen=lineas(examen), diagnosticos=diagnosticos, examenes_auxiliares=lineas(examenes),
                interconsultas=lineas(interconsultas), indicaciones=lineas(indicaciones),
                proximo_control=proximo.strip(), proximo_control_semanas=semanas, por_confirmar=lineas(por_confirmar),
                campos_especialidad=[CampoEspecialidad(nombre=n, valor=v.strip()) for n, v in campos_especialidad.items()],
            )
            # La historia editada por el médico + los diagnósticos de hoy (nuevos o confirmados).
            historia_final = fusionar_historia(
                HistoriaClinica(**campos_historia, diagnosticos=propuesta.diagnosticos),
                HISTORIA_VACIA.model_copy(update={"diagnosticos": diagnosticos}),
            )
            # Cuánto acertó Ceni: su borrador contra lo que firma el médico (que sabe qué se dijo).
            acierto = comparar(resultado.atencion, resultado.receta, nota_final, receta)
            segundos_revision = monotonic() - borrador["listo_en"]
            atencion_id = db.guardar_atencion(
                paciente_id, fecha, borrador["transcripcion"], nota_final, receta, historia_final,
                firmado_por=medico["nombre"], consentimiento_en=borrador["consentimiento_en"],
                cita_id=cita["id"] if cita else None,
                proxima_cita=(fecha_control, hora_control.strftime("%H:%M")) if agendar else None,
                medico_id=medico["id"], borrador=(resultado.atencion, resultado.receta),
                segundos_ia=borrador["segundos_ia"], segundos_revision=segundos_revision,
            )
            st.session_state["recien_firmada"] = {
                "paciente_id": paciente_id,
                "atencion_id": atencion_id,
                "segundos_ia": borrador["segundos_ia"],
                "segundos_revision": segundos_revision,
                "acierto": acierto_texto(acierto),
                "cambios": acierto.cambios,
                "detalle": "La historia clínica se actualizó"
                + (f" y el próximo control quedó agendado para el {dia_texto(fecha_control)}." if agendar else "."),
            }
            del st.session_state["borrador"]
            st.session_state.pop("cita_id", None)
            st.session_state["alertas_guardadas"] = alertas_receta(receta, historia_final)
            st.session_state["ir_a_pestana"] = ATENCIONES
            st.rerun()

# --- Historia clínica -----------------------------------------------------------
with historia_tab:
    izquierda, derecha = st.columns([1.45, 1], gap="medium")
    with izquierda, st.container(key="tarjeta-antecedentes"):
        estilo.html(
            estilo.titulo("Antecedentes", "history_edu", "violeta")
            + historia_html(historia, ["antecedentes_perinatales", "desarrollo_psicomotor", "inmunizaciones",
                                       "antecedentes_personales", "antecedentes_familiares"])
        )
        st.caption(f"Historia clínica actualizada el {fecha_texto(actualizada)}.")
    with derecha:
        with st.container(key="tarjeta-problemas"):
            estilo.html(estilo.titulo("Diagnósticos y terapias", "neurology", "coral")
                        + historia_html(historia, ["diagnosticos", "alergias", "terapias"]))
        with st.container(key="tarjeta-medicacion"):
            receta_actual = atenciones[0]["receta"] if atenciones else []
            desde = f"Receta del {fecha_texto(atenciones[0]['fecha'])}" if atenciones else "Sin atenciones"
            estilo.html(estilo.titulo("Medicación actual", "medication", "rosa") + estilo.etiqueta(desde)
                        + receta_html(receta_actual))
        # La atención más reciente que tenga al menos una medida registrada.
        con_signos = next((a for a in atenciones if any(a["nota"].signos_vitales.model_dump().values())), None)
        if con_signos:
            with st.container(key="tarjeta-signos"):
                estilo.html(estilo.titulo("Últimas medidas", "monitor_weight", "cielo")
                            + estilo.etiqueta(fecha_texto(con_signos["fecha"]))
                            + signos_html(con_signos["nota"].signos_vitales))

    with st.container(key="tarjeta-evolucion"):
        titulo_col, descarga = st.columns([3, 1.2], vertical_alignment="center")
        titulo_col.html(estilo.titulo("Evolución", "timeline", "menta"))
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
                        "Receta en PDF", receta_pdf(a), file_name=f"receta-{paciente['hc']}-{a['fecha']}.pdf",
                        mime="application/pdf", icon=":material/picture_as_pdf:", key=f"pdf_{a['id']}",
                        on_click="ignore", type="primary",
                    )
                if a["transcripcion"]:
                    with st.popover("Transcripción", icon=":material/subject:"):
                        st.write(a["transcripcion"])
                st.caption(
                    f"Firmado por {a['firmado_por']} el {momento_texto(a['firmado_en'])} · "
                    f"Autorización de la familia: {momento_texto(a['consentimiento_en'])}"
                    + (f" · {acierto_texto(a['acierto'])}" if a["acierto"] else "")
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
    estilo.html(estilo.titulo("Datos personales", "badge", "cielo") + '<div class="ceni-datos">' + "".join(
        f'<div class="ceni-dato">{estilo.etiqueta(k)}<div class="valor">{escape(v)}</div></div>' for k, v in datos.items()
    ) + "</div>")
