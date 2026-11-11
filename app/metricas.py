"""Página del médico: cómo le va con Ceni en los últimos 30 días.

Cuánto tarda Ceni en armar el borrador, cuánto tarda el médico en revisarlo y
firmarlo, y cuánto acierta Ceni (lo que el médico dejó igual al firmar).
"""

import pandas as pd
import streamlit as st

from app import estilo
from app.formato import duracion_texto, momento_texto
from backend import db

medico = db.medico(st.session_state.get("medico_id", 1))
metricas = db.metricas_medico(medico["id"])
estilo.encabezado("Mis métricas", "Cuánto tardan Ceni y tú en cada atención, y cuánto acierta Ceni. Últimos 30 días.",
                  medico["consultorio"])

if not metricas["atenciones"]:
    st.info("Todavía no hay atenciones con Ceni en los últimos 30 días. Atiende a un paciente desde la agenda "
            "y aquí verás tus tiempos y el acierto.", icon=":material/insights:")
    st.stop()

acierto = metricas["acierto"]
estilo.html(estilo.cifras([
    (str(metricas["atenciones"]), "", "atenciones con Ceni", "violeta"),
    (duracion_texto(metricas["segundos_ia"]), "", "tarda Ceni en armar el borrador (promedio)", "cielo"),
    (duracion_texto(metricas["segundos_revision"]), "", "tardas tú en revisar y firmar (promedio)", "coral"),
    (f"{acierto.porcentaje:.0%}", "", f"acierto de Ceni ({acierto.acertados} de {acierto.total} datos)", "menta"),
]))
st.write("")
estilo.html(estilo.titulo("Cada atención", "receipt_long", "violeta", f"{metricas['atenciones']} atenciones"))
st.dataframe(
    pd.DataFrame([{
        "Paciente": d["paciente"],
        "Firmada": momento_texto(d["firmado_en"]),
        "Ceni tardó": duracion_texto(d["segundos_ia"] or 0),
        "Tu revisión": duracion_texto(d["segundos_revision"] or 0),
        "Acierto": f"{d['acierto'].acertados} de {d['acierto'].total} ({d['acierto'].porcentaje:.0%})",
        "Corregiste": d["acierto"].corregidos, "Agregaste": d["acierto"].agregados, "Borraste": d["acierto"].borrados,
    } for d in metricas["detalle"]]),
    hide_index=True, width="stretch",
)
st.caption("El acierto compara el borrador de Ceni con lo que firmaste, dato por dato. Lo que dejaste igual cuenta "
           "como acierto; lo que corregiste, agregaste o borraste, no.")
