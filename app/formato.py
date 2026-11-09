"""Pequeñas ayudas para mostrar fechas, notas, recetas e historias en la app."""

from datetime import date

import streamlit as st

from ai.esquemas import HistoriaClinica, Medicamento, NotaAtencion

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

TITULOS_HISTORIA = {
    "antecedentes_perinatales": "Antecedentes perinatales",
    "desarrollo_psicomotor": "Desarrollo psicomotor",
    "antecedentes_personales": "Antecedentes personales",
    "antecedentes_familiares": "Antecedentes familiares",
    "alergias": "Alergias",
    "diagnosticos": "Diagnósticos",
    "terapias": "Terapias",
}


def fecha_texto(fecha: str | date | None) -> str:
    """'2026-11-03' -> '3 de noviembre de 2026'."""
    if not fecha:
        return "sin atenciones"
    d = date.fromisoformat(fecha) if isinstance(fecha, str) else fecha
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def _lista(titulo: str, items: list[str]) -> None:
    if items:
        st.markdown(f"**{titulo}**\n" + "\n".join(f"- {i}" for i in items))


def mostrar_receta(receta: list[Medicamento]) -> None:
    if not receta:
        st.markdown("**Receta:** sin medicamentos.")
        return
    st.markdown("**Receta**")
    for m in receta:
        detalle = f"{m.dosis}, {m.frecuencia[:1].lower()}{m.frecuencia[1:]}" + (f", por {m.duracion}" if m.duracion else "")
        st.markdown(f"- **{m.medicamento}**: {detalle}." + (f" _{m.indicaciones}_" if m.indicaciones else ""))


def mostrar_atencion(nota: NotaAtencion, receta: list[Medicamento]) -> None:
    """Dibuja una atención completa (pestaña Atenciones)."""
    st.markdown(nota.resumen)
    if nota.por_confirmar:
        st.warning("Por confirmar: " + "; ".join(nota.por_confirmar), icon=":material/help:")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Motivo:** {nota.motivo}")
        _lista("Relato de la familia", nota.relato)
        _lista("Examen", nota.examen)
        _lista("Diagnósticos", nota.diagnosticos)
    with col2:
        mostrar_receta(receta)
        _lista("Plan", nota.plan)
        if nota.proximo_control:
            st.markdown(f"**Próximo control:** {nota.proximo_control}")


def mostrar_historia(historia: HistoriaClinica) -> None:
    """Dibuja la historia clínica acumulada (pestaña Historia clínica)."""
    datos = historia.model_dump()
    col1, col2 = st.columns(2)
    for i, (campo, titulo) in enumerate(TITULOS_HISTORIA.items()):
        valor = datos[campo]
        with col1 if i % 2 == 0 else col2:
            if isinstance(valor, list) and valor:
                _lista(titulo, valor)
            elif isinstance(valor, list):
                st.markdown(f"**{titulo}:** sin registro")
            else:
                st.markdown(f"**{titulo}:** {valor or 'sin registro'}")
