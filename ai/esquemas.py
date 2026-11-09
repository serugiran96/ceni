"""Esquemas de datos de Ceni (Pydantic).

Son el "contrato" entre la IA y la app: el modelo de OpenAI tiene que devolver
exactamente estos campos (salida estructurada) y Pydantic lo valida antes de
guardar. Los mismos esquemas validan los datos semilla.
"""

from typing import Literal

from pydantic import BaseModel, Field

# Subconjunto del CIE-10 (OMS) para neuropediatría y neurodesarrollo.
# La IA solo puede elegir uno de estos códigos (o "" si ninguno corresponde).
CIE10 = {
    "F70": "Retraso mental leve",
    "F80.1": "Trastorno del lenguaje expresivo",
    "F80.2": "Trastorno de la recepción del lenguaje",
    "F81.0": "Trastorno específico de la lectura",
    "F81.2": "Trastorno específico de las habilidades aritméticas",
    "F81.3": "Trastorno mixto de las habilidades escolares",
    "F82": "Trastorno específico del desarrollo de la función motriz",
    "F84.0": "Autismo en la niñez",
    "F84.5": "Síndrome de Asperger",
    "F84.9": "Trastorno generalizado del desarrollo, no especificado",
    "F88": "Otros trastornos del desarrollo psicológico",
    "F90.0": "Perturbación de la actividad y de la atención",
    "F90.1": "Trastorno hipercinético de la conducta",
    "F90.9": "Trastorno hipercinético, no especificado",
    "F91.3": "Trastorno opositor desafiante",
    "F93.0": "Trastorno de ansiedad de separación en la niñez",
    "F95.2": "Trastorno por tics motores y vocales múltiples combinados [de la Tourette]",
    "F98.0": "Enuresis no orgánica",
    "F98.2": "Trastorno de la ingestión alimentaria en la infancia y la niñez",
    "F98.8": "Otros trastornos del comportamiento de la niñez (incluye déficit de atención sin hiperactividad)",
    "G40.9": "Epilepsia, tipo no especificado",
    "G43.9": "Migraña, no especificada",
    "G47.0": "Trastornos del inicio y del mantenimiento del sueño [insomnios]",
    "G80.9": "Parálisis cerebral, sin otra especificación",
    "Q90.9": "Síndrome de Down, no especificado",
    "R56.0": "Convulsiones febriles",
    "R62.0": "Retardo del desarrollo",
}
CodigoCIE10 = Literal[("", *CIE10)]  # "" = sin código en el catálogo


class Diagnostico(BaseModel):
    descripcion: str = Field(description="El diagnóstico tal como lo dijo el médico.")
    cie10: CodigoCIE10 = Field(description="Código CIE-10 del catálogo que corresponde; vacío si ninguno.")


class HistoriaClinica(BaseModel):
    """Historia clínica acumulada del paciente (se actualiza en cada atención)."""

    antecedentes_perinatales: str = Field(description="Embarazo, parto, peso al nacer, complicaciones.")
    desarrollo_psicomotor: str = Field(description="Edad en que caminó, habló, hitos del desarrollo.")
    antecedentes_personales: list[str] = Field(description="Enfermedades, hospitalizaciones, cirugías, exámenes previos.")
    antecedentes_familiares: list[str] = Field(description="Condiciones relevantes en la familia.")
    alergias: list[str] = Field(description="Alergias a medicamentos o alimentos.")
    diagnosticos: list[Diagnostico] = Field(description="Diagnósticos establecidos por el médico.")
    terapias: list[str] = Field(description="Terapias que recibe el paciente.")


class Medicamento(BaseModel):
    """Una línea de la receta, con lo que exige la Ley 29459."""

    medicamento: str = Field(description="Denominación Común Internacional (DCI) y concentración, p. ej. 'Melatonina 3 mg'.")
    forma_farmaceutica: str = Field(description="Tableta, jarabe, gotas, cápsula... Vacío si no se dijo.")
    via: str = Field(description="Vía de administración (oral, sublingual...). Vacío si no se dijo.")
    dosis: str = Field(description="Cuánto toma cada vez, p. ej. '1 tableta'.")
    frecuencia: str = Field(description="Cada cuánto y a qué hora.")
    duracion: str = Field(description="Por cuánto tiempo. Vacío si no se dijo.")
    indicaciones: str = Field(description="Indicaciones especiales. Vacío si no hay.")


class NotaAtencion(BaseModel):
    """Lo que pasó en una atención (una consulta)."""

    resumen: str = Field(description="Dos o tres oraciones con lo principal de la consulta.")
    motivo: str = Field(description="Motivo de la consulta de hoy (primera vez, control, problema nuevo).")
    relato: list[str] = Field(description="Lo que contaron la familia, el colegio o las terapeutas.")
    examen: list[str] = Field(description="Lo que observó o examinó el médico en la consulta.")
    diagnosticos: list[Diagnostico] = Field(description="Diagnósticos o impresiones que dijo el médico hoy.")
    plan: list[str] = Field(description="Indicaciones sin medicamentos: terapias, exámenes pedidos, recomendaciones.")
    proximo_control: str = Field(description="Cuándo es el próximo control, como lo dijo el médico. Vacío si no se dijo.")
    proximo_control_semanas: int = Field(description="El próximo control en semanas (2 meses = 8). 0 si no se dijo.")
    por_confirmar: list[str] = Field(
        description="Datos que no se entendieron bien en el audio y el médico debe confirmar (sobre todo dosis)."
    )


class ResultadoAtencion(BaseModel):
    """Lo que devuelve la IA al terminar una atención."""

    atencion: NotaAtencion
    receta: list[Medicamento] = Field(
        description="Solo los medicamentos que el médico indicó en la consulta. Lista vacía si no indicó ninguno."
    )
    historia_nueva: HistoriaClinica = Field(
        description="SOLO la información NUEVA para la historia clínica que apareció en esta consulta. "
        "Campos vacíos si no hay nada nuevo. No repitas lo que ya está en la historia."
    )


def _clave(item) -> str:
    """Para no duplicar: un diagnóstico se reconoce por su código CIE-10 (o su texto)."""
    if isinstance(item, dict):
        return item.get("cie10") or item.get("descripcion", "").lower()
    return str(item).lower()


def fusionar_historia(actual: HistoriaClinica, nueva: HistoriaClinica) -> HistoriaClinica:
    """Añade lo nuevo a la historia sin borrar nada de lo anterior.

    La IA solo propone lo nuevo; este código lo agrega. Así una respuesta mala
    del modelo nunca puede borrar antecedentes ya registrados.
    """
    datos = actual.model_dump()
    for campo, valor in nueva.model_dump().items():
        if isinstance(valor, list):
            existentes = {_clave(v) for v in datos[campo]}
            datos[campo] += [v for v in valor if v and _clave(v) not in existentes]
        elif valor and valor not in datos[campo]:
            datos[campo] = f"{datos[campo]} {valor}".strip()
    return HistoriaClinica(**datos)


HISTORIA_VACIA = HistoriaClinica(
    antecedentes_perinatales="", desarrollo_psicomotor="", antecedentes_personales=[],
    antecedentes_familiares=[], alergias=[], diagnosticos=[], terapias=[],
)
