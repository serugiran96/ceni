"""Cómo se muestran las fechas, la atención, la receta y la historia clínica en la app."""

from datetime import date, datetime
from html import escape

import streamlit as st

from ai.esquemas import CIE10, TIPOS_DIAGNOSTICO, Diagnostico, FuncionesBiologicas, HistoriaClinica, Medicamento, NotaAtencion, SignosVitales, imc
from app import estilo
from backend.pdf import linea_medicamento
from backend.reglas import requiere_receta_especial

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]

TITULOS_HISTORIA = {
    "antecedentes_perinatales": "Antecedentes perinatales",
    "desarrollo_psicomotor": "Desarrollo psicomotor",
    "inmunizaciones": "Inmunizaciones",
    "antecedentes_personales": "Antecedentes personales",
    "antecedentes_familiares": "Antecedentes familiares",
    "alergias": "Alergias",
    "diagnosticos": "Diagnósticos",
    "terapias": "Terapias",
}
TITULOS_FUNCIONES = {"apetito": "Apetito", "sed": "Sed", "sueno": "Sueño", "orina": "Orina",
                     "deposiciones": "Deposiciones", "estado_de_animo": "Estado de ánimo"}


# --- Fechas ----------------------------------------------------------------------

def _fecha(valor: str | date) -> date:
    return date.fromisoformat(valor) if isinstance(valor, str) else valor


def fecha_texto(fecha: str | date | None) -> str:
    """'2026-11-03' -> '3 de noviembre de 2026'."""
    if not fecha:
        return "sin atenciones"
    d = _fecha(fecha)
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def fecha_corta(fecha: str | date) -> str:
    """'2026-10-07' -> '7 oct.'; si no es de este año, '7 oct. 2025'."""
    d = _fecha(fecha)
    texto = f"{d.day} {MESES[d.month - 1][:3]}."
    return texto if d.year == date.today().year else f"{texto} {d.year}"


def dia_texto(fecha: str | date) -> str:
    """'2026-11-11' -> 'miércoles 11 de noviembre' (o 'hoy' / 'mañana')."""
    d = _fecha(fecha)
    return f"{DIAS[d.weekday()]} {d.day} de {MESES[d.month - 1]}"


def cuando_texto(fecha: str | date) -> str:
    """'hoy', 'mañana' o 'miércoles 11 de noviembre'."""
    dias = (_fecha(fecha) - date.today()).days
    return {0: "hoy", 1: "mañana"}.get(dias, dia_texto(fecha))


def momento_texto(iso: str | None) -> str:
    """'2026-11-09T16:05:00' -> '9 de noviembre de 2026, 16:05'."""
    if not iso:
        return "no registrado"
    m = datetime.fromisoformat(iso)
    return f"{fecha_texto(m.date())}, {m:%H:%M}"


# --- Diagnósticos y alergias -------------------------------------------------------

def diagnostico_texto(d: Diagnostico) -> str:
    return f"{d.descripcion} ({d.cie10})" if d.cie10 else d.descripcion


def chip_diagnostico(d: Diagnostico, con_tipo: bool = True, sobre_color: bool = False) -> str:
    codigo = f"<b>{escape(d.cie10)}</b> " if d.cie10 else ""
    tipo = f" · {d.tipo}" if con_tipo else ""
    tono = "vidrio" if sobre_color else "violeta"
    return estilo.chip(f"{codigo}{escape(d.descripcion)}{tipo}", tono, TIPOS_DIAGNOSTICO[d.tipo], crudo=True)


def alergias_reales(alergias: list[str]) -> list[str]:
    """Quita 'No conocidas', 'Niega alergias'... para no mostrar una alerta vacía."""
    return [a for a in alergias if not a.lower().startswith(("no ", "niega", "ninguna", "sin "))]


def chips_paciente(diagnosticos: list[Diagnostico], alergias: list[str], sobre_color: bool = False) -> str:
    """Etiquetas de diagnósticos y alergias. `sobre_color=True` dentro de una tarjeta con degradado."""
    return estilo.chips(
        [chip_diagnostico(d, con_tipo=False, sobre_color=sobre_color) for d in diagnosticos]
        + [estilo.chip(f"⚠ Alergia: {a}", "alerta" if sobre_color else "rosa") for a in alergias_reales(alergias)]
    )


# --- Signos, funciones biológicas y receta -------------------------------------

def _num(valor: float) -> str:
    return f"{valor:g}"


def signos_html(signos: SignosVitales) -> str:
    items = []
    if signos.peso_kg:
        items.append((_num(signos.peso_kg), "kg", "Peso", "cielo"))
    if signos.talla_cm:
        items.append((_num(signos.talla_cm), "cm", "Talla", "menta"))
    if valor := imc(signos):
        items.append((_num(valor), "", "IMC", "violeta"))
    if signos.perimetro_cefalico_cm:
        items.append((_num(signos.perimetro_cefalico_cm), "cm", "Perímetro cefálico", "coral"))
    if signos.temperatura_c:
        items.append((_num(signos.temperatura_c), "°C", "Temperatura", "sol"))
    if signos.frecuencia_cardiaca:
        items.append((str(signos.frecuencia_cardiaca), "lpm", "Frec. cardiaca", "rosa"))
    if signos.frecuencia_respiratoria:
        items.append((str(signos.frecuencia_respiratoria), "rpm", "Frec. respiratoria", "gris"))
    return estilo.cifras(items) if items else '<p class="ceni-vacio">No se registraron.</p>'


def funciones_html(funciones: FuncionesBiologicas) -> str:
    datos = [(TITULOS_FUNCIONES[c], v) for c, v in funciones.model_dump().items() if v]
    if not datos:
        return '<p class="ceni-vacio">No se registraron.</p>'
    return "".join(f'<p class="ceni-texto"><b>{t}:</b> {escape(v)}</p>' for t, v in datos)


def diagnosticos_html(diagnosticos: list[Diagnostico]) -> str:
    """Una fila por diagnóstico: código CIE-10, descripción y tipo (definitivo, presuntivo...)."""
    if not diagnosticos:
        return '<p class="ceni-vacio">Sin diagnóstico registrado.</p>'
    return "".join(
        '<div class="ceni-dx">'
        + (estilo.chip(d.cie10, "violeta", CIE10[d.cie10]) if d.cie10 else estilo.chip("Sin código", "gris"))
        + f'<div class="ceni-texto">{escape(d.descripcion)} '
        f'<span class="ceni-meta">· {TIPOS_DIAGNOSTICO[d.tipo]}</span></div></div>'
        for d in diagnosticos
    )


def receta_html(receta: list[Medicamento]) -> str:
    if not receta:
        return '<p class="ceni-vacio">Sin medicamentos.</p>'
    partes = []
    for m in receta:
        extras = []
        if m.cantidad:
            extras.append(estilo.chip(f"Cantidad: {m.cantidad}", "menta"))
        if requiere_receta_especial(m.medicamento):
            extras.append(estilo.chip("Psicotrópico · recetario especial", "sol"))
        partes.append(
            f'<div class="ceni-bloque"><div class="ceni-texto"><b>{escape(m.medicamento)}</b></div>'
            f'<div class="ceni-texto">{escape(linea_medicamento(m))}</div>'
            + (f'<div class="ceni-meta">{escape(m.indicaciones)}</div>' if m.indicaciones else "")
            + estilo.chips(extras) + "</div>"
        )
    return "".join(partes)


# --- Atención e historia ------------------------------------------------------------

def mostrar_atencion(nota: NotaAtencion, receta: list[Medicamento]) -> None:
    """Una atención completa, en el orden del formato de consulta externa."""
    estilo.html(f'<p class="ceni-texto" style="font-size:1.02rem">{escape(nota.resumen)}</p>')
    if nota.por_confirmar:
        st.warning("Por confirmar: " + "; ".join(nota.por_confirmar), icon=":material/help:")
    izquierda, derecha = st.columns(2, gap="large")
    with izquierda:
        anamnesis = nota.motivo + (f" · Tiempo de enfermedad: {nota.tiempo_enfermedad}" if nota.tiempo_enfermedad else "")
        estilo.html(
            estilo.bloque("Motivo de consulta", estilo.texto(anamnesis))
            + estilo.bloque("Relato", estilo.lista(nota.relato))
            + estilo.bloque("Funciones biológicas", funciones_html(nota.funciones_biologicas))
            + estilo.bloque("Examen físico y neurológico", estilo.lista(nota.examen))
        )
    with derecha:
        estilo.html(
            estilo.bloque("Signos vitales y antropometría", signos_html(nota.signos_vitales))
            + estilo.bloque("Diagnósticos", diagnosticos_html(nota.diagnosticos))
            + estilo.bloque("Tratamiento", receta_html(receta))
            + estilo.bloque("Exámenes auxiliares", estilo.lista(nota.examenes_auxiliares, "Ninguno"))
            + estilo.bloque("Interconsultas y terapias", estilo.lista(nota.interconsultas, "Ninguna"))
            + estilo.bloque("Indicaciones", estilo.lista(nota.indicaciones, "Ninguna"))
            + estilo.bloque("Próximo control", estilo.texto(nota.proximo_control, "No se indicó"))
        )


def historia_html(historia: HistoriaClinica, campos: list[str]) -> str:
    partes = []
    for campo in campos:
        valor = getattr(historia, campo)
        if campo == "diagnosticos":
            contenido = diagnosticos_html(valor)
        elif isinstance(valor, list):
            contenido = estilo.lista(valor)
        else:
            contenido = estilo.texto(valor)
        partes.append(estilo.bloque(TITULOS_HISTORIA[campo], contenido))
    return "".join(partes)


# --- Antes de empezar: lo que el médico necesita ver antes de grabar ----------------

def pendientes(nota: NotaAtencion) -> list[tuple[str, str, str]]:
    """Lo que quedó pendiente en una atención: exámenes, interconsultas y dudas por confirmar."""
    return (
        [("biotech", "cielo", f"Examen: {e}") for e in nota.examenes_auxiliares]
        + [("diversity_3", "violeta", f"Interconsulta: {i}") for i in nota.interconsultas]
        + [("help", "sol", f"Por confirmar: {p}") for p in nota.por_confirmar]
    )


def medicacion(receta: list[Medicamento]) -> list[tuple[str, str, str]]:
    """Medicación en una línea corta por medicamento: nombre, dosis y frecuencia."""
    return [
        ("medication", "coral", " · ".join(x for x in (m.medicamento, m.dosis, m.frecuencia) if x))
        for m in receta
    ]


def antes_de_empezar_html(atenciones: list[dict], historia: HistoriaClinica, maximo: int = 0) -> str:
    """Resumen previo: la última atención, lo que quedó pendiente, la medicación y las alergias.

    `atenciones` va de la más reciente a la más antigua. `maximo` limita cuántos
    pendientes se muestran (0 = todos), para la versión corta de la agenda.
    """
    if not atenciones:
        partes = [estilo.bloque("Primera consulta", estilo.texto(
            "Todavía no hay atenciones. Ceni armará la historia clínica con lo que se hable hoy."))]
    else:
        ultima = atenciones[0]
        lista_pendientes = pendientes(ultima["nota"])
        if maximo and len(lista_pendientes) > maximo:
            lista_pendientes = lista_pendientes[:maximo] + [("more_horiz", "gris", f"y {len(lista_pendientes) - maximo} más")]
        partes = [
            estilo.bloque(f"Última atención · {fecha_corta(ultima['fecha'])}", estilo.texto(ultima["nota"].resumen)),
            estilo.bloque("Quedó pendiente", estilo.items(lista_pendientes)),
            estilo.bloque("Medicación actual", estilo.items(medicacion(ultima["receta"]), "Sin medicación")),
        ]
    alergias = alergias_reales(historia.alergias)
    if alergias:
        partes.append(estilo.bloque("Alergias", estilo.items([("warning", "rosa", a) for a in alergias])))
    return "".join(partes)


def duracion_texto(segundos: float) -> str:
    """42 -> '42 s'; 102 -> '1 min 42 s'."""
    segundos = max(1, round(segundos))
    minutos, resto = divmod(segundos, 60)
    return f"{minutos} min {resto} s" if minutos else f"{resto} s"
