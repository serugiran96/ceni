"""Pequeñas ayudas para mostrar fechas, notas, recetas e historias en la app."""

from datetime import date, datetime

import streamlit as st

from ai.esquemas import Diagnostico, HistoriaClinica, Medicamento, NotaAtencion
from backend.pdf import linea_medicamento

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]

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


def dia_texto(fecha: str | date) -> str:
    """'2026-11-11' -> 'miércoles 11 de noviembre'."""
    d = date.fromisoformat(fecha) if isinstance(fecha, str) else fecha
    return f"{DIAS[d.weekday()]} {d.day} de {MESES[d.month - 1]}"


def momento_texto(iso: str | None) -> str:
    """'2026-11-09T16:05:00' -> '9 de noviembre de 2026, 16:05'."""
    if not iso:
        return "no registrado"
    m = datetime.fromisoformat(iso)
    return f"{fecha_texto(m.date())}, {m:%H:%M}"


def diagnostico_texto(d: Diagnostico) -> str:
    return f"{d.descripcion} ({d.cie10})" if d.cie10 else d.descripcion


def _lista(titulo: str, items: list[str]) -> None:
    if items:
        st.markdown(f"**{titulo}**\n" + "\n".join(f"- {i}" for i in items))


def mostrar_receta(receta: list[Medicamento], titulo: str = "Receta") -> None:
    if not receta:
        st.markdown(f"**{titulo}:** sin medicamentos.")
        return
    st.markdown(
        f"**{titulo}**\n"
        + "\n".join(
            f"- **{m.medicamento}**: {linea_medicamento(m)}" + (f" _{m.indicaciones}_" if m.indicaciones else "")
            for m in receta
        )
    )


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
        _lista("Diagnósticos", [diagnostico_texto(d) for d in nota.diagnosticos])
    with col2:
        mostrar_receta(receta)
        _lista("Plan", nota.plan)
        if nota.proximo_control:
            st.markdown(f"**Próximo control:** {nota.proximo_control}")


def mostrar_historia(historia: HistoriaClinica) -> None:
    """Dibuja la historia clínica acumulada (pestaña Historia clínica)."""
    col1, col2 = st.columns(2)
    for i, (campo, titulo) in enumerate(TITULOS_HISTORIA.items()):
        valor = getattr(historia, campo)
        if campo == "diagnosticos":
            valor = [diagnostico_texto(d) for d in valor]
        with col1 if i % 2 == 0 else col2:
            if isinstance(valor, list) and valor:
                _lista(titulo, valor)
            elif isinstance(valor, list):
                st.markdown(f"**{titulo}:** sin registro")
            else:
                st.markdown(f"**{titulo}:** {valor or 'sin registro'}")
