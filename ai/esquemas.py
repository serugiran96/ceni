"""Esquemas de datos de Ceni (Pydantic).

Son el "contrato" entre la IA y la app: el modelo de OpenAI tiene que devolver
exactamente estos campos (salida estructurada) y Pydantic lo valida antes de
guardar. Los mismos esquemas validan las notas de los datos semilla.
"""

from typing import Literal

from pydantic import BaseModel, Field

# Escala simple de avance por objetivo (la usa la terapeuta y el gráfico).
ESCALA = {
    1: "Inicio: lo logra con mucha ayuda",
    2: "En proceso: lo logra con ayuda",
    3: "Casi logrado: lo logra con poca ayuda",
    4: "Logrado: lo hace solo",
}


class AvanceObjetivo(BaseModel):
    objetivo_id: int = Field(description="El id del objetivo del plan del paciente.")
    nivel: Literal[1, 2, 3, 4] = Field(
        description="1 = inicio (mucha ayuda), 2 = en proceso (con ayuda), "
        "3 = casi logrado (poca ayuda), 4 = logrado (lo hace solo)."
    )
    comentario: str = Field(description="Una frase con la evidencia que dio la terapeuta.")


class NotaSesion(BaseModel):
    """Nota de evolución de una sesión de terapia."""

    resumen: str = Field(description="Una o dos oraciones sobre cómo fue la sesión.")
    actividades: list[str] = Field(description="Actividades que se hicieron.")
    logros: list[str] = Field(description="Lo que el niño o la niña logró hoy.")
    dificultades: list[str] = Field(description="Lo que le costó hoy.")
    avances: list[AvanceObjetivo] = Field(
        description="Solo los objetivos del plan que se trabajaron hoy."
    )
    tareas_para_casa: list[str] = Field(description="Indicaciones para la familia.")
    observaciones: str = Field(
        description="Conducta, ánimo o coordinación con la familia o el colegio. "
        "Texto vacío si la terapeuta no dijo nada."
    )


class InformePadres(BaseModel):
    """Informe en lenguaje simple para la familia."""

    saludo: str = Field(description="Saludo cálido a la familia, con el nombre de quien recibe el informe.")
    como_va: str = Field(description="Un párrafo corto sobre cómo va el niño o la niña, sin términos técnicos.")
    logros: list[str] = Field(description="Avances concretos de las últimas sesiones.")
    seguimos_trabajando: list[str] = Field(description="Lo que todavía se está trabajando, dicho en positivo.")
    en_casa: list[str] = Field(description="Ideas concretas y fáciles para apoyar en casa.")
    cierre: str = Field(description="Una frase de cierre, firmada por la terapeuta.")
