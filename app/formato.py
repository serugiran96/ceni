"""Pequeñas ayudas para mostrar fechas y notas en la app."""

from datetime import date

import streamlit as st

from ai.esquemas import ESCALA, NotaSesion

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def fecha_texto(fecha: str | date | None) -> str:
    """'2026-11-03' -> '3 de noviembre de 2026'."""
    if not fecha:
        return "sin sesiones"
    d = date.fromisoformat(fecha) if isinstance(fecha, str) else fecha
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def nivel_texto(nivel: int) -> str:
    """4 -> 'Logrado'."""
    return ESCALA[nivel].split(":")[0]


def _lista(titulo: str, items: list[str]) -> None:
    if items:
        st.markdown(f"**{titulo}**")
        st.markdown("\n".join(f"- {i}" for i in items))


def mostrar_nota(nota: NotaSesion, objetivos: dict[int, str]) -> None:
    """Dibuja una nota de sesión (en el historial y en la vista previa)."""
    st.markdown(nota.resumen)
    col1, col2 = st.columns(2)
    with col1:
        _lista("Actividades", nota.actividades)
        _lista("Logros", nota.logros)
        _lista("Dificultades", nota.dificultades)
    with col2:
        if nota.avances:
            st.markdown("**Avance por objetivo**")
            for a in nota.avances:
                st.markdown(
                    f"- {objetivos.get(a.objetivo_id, 'Objetivo')}: **{nivel_texto(a.nivel)}** ({a.nivel}/4). {a.comentario}"
                )
        _lista("Tareas para casa", nota.tareas_para_casa)
    if nota.observaciones:
        st.markdown(f"**Observaciones:** {nota.observaciones}")
