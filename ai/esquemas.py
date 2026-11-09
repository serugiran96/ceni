"""Esquemas de datos de Ceni (Pydantic).

Son el "contrato" entre la IA y la app: el modelo de OpenAI tiene que devolver
exactamente estos campos (salida estructurada) y Pydantic lo valida antes de
guardar. Los mismos esquemas validan los datos semilla.
"""

from pydantic import BaseModel, Field


class HistoriaClinica(BaseModel):
    """Historia clínica acumulada del paciente (se actualiza en cada atención)."""

    antecedentes_perinatales: str = Field(description="Embarazo, parto, peso al nacer, complicaciones.")
    desarrollo_psicomotor: str = Field(description="Edad en que caminó, habló, hitos del desarrollo.")
    antecedentes_personales: list[str] = Field(description="Enfermedades, hospitalizaciones, cirugías, exámenes previos.")
    antecedentes_familiares: list[str] = Field(description="Condiciones relevantes en la familia.")
    alergias: list[str] = Field(description="Alergias a medicamentos o alimentos.")
    diagnosticos: list[str] = Field(description="Diagnósticos establecidos por el médico, tal como los dijo.")
    terapias: list[str] = Field(description="Terapias que recibe el paciente.")


class Medicamento(BaseModel):
    medicamento: str = Field(description="Nombre y concentración, por ejemplo 'Melatonina 3 mg'.")
    dosis: str = Field(description="Cuánto toma cada vez, por ejemplo '1 tableta'.")
    frecuencia: str = Field(description="Cada cuánto y a qué hora.")
    duracion: str = Field(description="Por cuánto tiempo. Texto vacío si no se dijo.")
    indicaciones: str = Field(description="Indicaciones especiales. Texto vacío si no hay.")


class NotaAtencion(BaseModel):
    """Lo que pasó en una atención (una consulta)."""

    resumen: str = Field(description="Dos o tres oraciones con lo principal de la consulta.")
    motivo: str = Field(description="Motivo de la consulta de hoy (primera vez, control, problema nuevo).")
    relato: list[str] = Field(description="Lo que contaron la familia, el colegio o las terapeutas.")
    examen: list[str] = Field(description="Lo que observó o examinó el médico en la consulta.")
    diagnosticos: list[str] = Field(description="Diagnósticos o impresiones que dijo el médico, tal cual.")
    plan: list[str] = Field(description="Indicaciones sin medicamentos: terapias, exámenes pedidos, recomendaciones.")
    proximo_control: str = Field(description="Cuándo es el próximo control. Texto vacío si no se dijo.")
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


def fusionar_historia(actual: HistoriaClinica, nueva: HistoriaClinica) -> HistoriaClinica:
    """Añade lo nuevo a la historia sin borrar nada de lo anterior.

    La IA solo propone lo nuevo; este código lo agrega. Así una respuesta mala
    del modelo nunca puede borrar antecedentes ya registrados.
    """
    datos = actual.model_dump()
    for campo, valor in nueva.model_dump().items():
        if isinstance(valor, list):
            datos[campo] += [v for v in valor if v and v not in datos[campo]]
        elif valor and valor not in datos[campo]:
            datos[campo] = f"{datos[campo]} {valor}".strip()
    return HistoriaClinica(**datos)


HISTORIA_VACIA = HistoriaClinica(
    antecedentes_perinatales="", desarrollo_psicomotor="", antecedentes_personales=[],
    antecedentes_familiares=[], alergias=[], diagnosticos=[], terapias=[],
)
