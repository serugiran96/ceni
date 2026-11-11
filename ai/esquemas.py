"""Esquemas de datos de Ceni (Pydantic).

Son el "contrato" entre la IA y la app: el modelo de OpenAI tiene que devolver
exactamente estos campos (salida estructurada) y Pydantic lo valida antes de
guardar. Los mismos esquemas validan los datos semilla.
"""

from typing import Literal

from pydantic import BaseModel, Field

# Códigos CIE-10 (OMS) frecuentes en el centro de neurodesarrollo del demo. Sirven para
# mostrar el nombre del diagnóstico; la IA puede usar cualquier código CIE-10, así Ceni
# sirve para cualquier especialidad.
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


TipoDiagnostico = Literal["D", "P", "R"]  # Definitivo, Presuntivo, Repetitivo (como en el HIS del MINSA)
TIPOS_DIAGNOSTICO = {"D": "Definitivo", "P": "Presuntivo", "R": "Repetitivo"}


class Diagnostico(BaseModel):
    descripcion: str = Field(description="El diagnóstico tal como lo dijo el médico.")
    cie10: str = Field(description="Código CIE-10 (OMS) que corresponde, p. ej. 'F84.0' o 'L20.9'. Vacío si no estás seguro.")
    tipo: TipoDiagnostico = Field(
        description="D = definitivo (confirmado hoy), P = presuntivo (sospecha, 'probable', 'descartar'), "
        "R = repetitivo (ya era definitivo en una atención anterior y se mantiene)."
    )


class HistoriaClinica(BaseModel):
    """Historia clínica acumulada del paciente (se actualiza en cada atención)."""

    antecedentes_perinatales: str = Field(description="Embarazo, parto, edad gestacional, peso al nacer, APGAR, complicaciones.")
    desarrollo_psicomotor: str = Field(description="Edad en que se sentó, caminó, dijo sus primeras palabras; hitos.")
    inmunizaciones: str = Field(description="Estado de las vacunas según el carné.")
    antecedentes_personales: list[str] = Field(description="Enfermedades, hospitalizaciones, cirugías, exámenes previos.")
    antecedentes_familiares: list[str] = Field(description="Condiciones relevantes en la familia.")
    alergias: list[str] = Field(description="Alergias a medicamentos o alimentos.")
    diagnosticos: list[Diagnostico] = Field(description="Diagnósticos establecidos por el médico.")
    terapias: list[str] = Field(description="Terapias que recibe el paciente.")


class Medicamento(BaseModel):
    """Una línea de la receta, con lo que exige la Ley 29459 (y la receta única estandarizada)."""

    medicamento: str = Field(description="Denominación Común Internacional (DCI) y concentración, p. ej. 'Melatonina 3 mg'.")
    forma_farmaceutica: str = Field(description="Tableta, jarabe, gotas, cápsula... Vacío si no se dijo.")
    via: str = Field(description="Vía de administración (oral, sublingual...). Vacío si no se dijo.")
    dosis: str = Field(description="Cuánto toma cada vez, como lo dijo el médico, p. ej. '1.5 mg (media tableta)' o '1 tableta'.")
    frecuencia: str = Field(description="Cada cuánto y a qué hora.")
    duracion: str = Field(description="Por cuánto tiempo. Vacío si no se dijo.")
    cantidad: str = Field(description="Cantidad total a dispensar, p. ej. '30 tabletas'. Vacío si no se dijo.")
    indicaciones: str = Field(description="Indicaciones especiales. Vacío si no hay.")


class FuncionesBiologicas(BaseModel):
    """Las funciones biológicas del formato de consulta externa del MINSA."""

    apetito: str = Field(description="Cómo come. Vacío si no se habló.")
    sed: str = Field(description="Vacío si no se habló.")
    sueno: str = Field(description="Cómo duerme: hora, despertares. Vacío si no se habló.")
    orina: str = Field(description="Incluye control de esfínteres. Vacío si no se habló.")
    deposiciones: str = Field(description="Frecuencia, estreñimiento. Vacío si no se habló.")
    estado_de_animo: str = Field(description="Ánimo, irritabilidad, crisis. Vacío si no se habló.")


class SignosVitales(BaseModel):
    """Funciones vitales y antropometría. null si no se dijo en la consulta."""

    peso_kg: float | None = Field(description="Peso en kilos.")
    talla_cm: float | None = Field(description="Talla en centímetros (1.28 m = 128).")
    perimetro_cefalico_cm: float | None = Field(description="Perímetro cefálico en centímetros.")
    temperatura_c: float | None = Field(description="Temperatura en grados Celsius.")
    frecuencia_cardiaca: int | None = Field(description="Latidos por minuto.")
    frecuencia_respiratoria: int | None = Field(description="Respiraciones por minuto.")


def imc(signos: SignosVitales) -> float | None:
    """Índice de masa corporal; lo calcula el código, no la IA (como en el SIHCE del MINSA)."""
    if signos.peso_kg and signos.talla_cm:
        return round(signos.peso_kg / (signos.talla_cm / 100) ** 2, 1)
    return None


class CampoPlantilla(BaseModel):
    """Un campo propio de una especialidad, que el admin agrega a una plantilla."""

    nombre: str = Field(description="Nombre del campo, p. ej. 'Escalas aplicadas'.")
    descripcion: str = Field(description="Qué debe ir en el campo, para el médico y para la IA.")


class Plantilla(BaseModel):
    """Campos que una especialidad suma al formato de consulta externa del MINSA (que es igual para todos)."""

    nombre: str = Field(description="Especialidad, p. ej. 'Dermatología pediátrica'.")
    campos: list[CampoPlantilla] = Field(description="Campos propios de la especialidad, sin repetir los del formato MINSA.")
    vocabulario: str = Field(description="Términos y medicamentos frecuentes, para que la transcripción los escriba bien.")


class CampoEspecialidad(BaseModel):
    nombre: str = Field(description="El nombre exacto del campo de la plantilla.")
    valor: str = Field(description="Lo que se dijo para ese campo. Vacío si no se habló de él.")


class NotaAtencion(BaseModel):
    """Lo que pasó en una atención, en el orden del formato de consulta externa."""

    resumen: str = Field(description="Dos o tres oraciones con lo principal de la consulta.")
    motivo: str = Field(description="Motivo de consulta de hoy (primera vez, control, problema nuevo).")
    tiempo_enfermedad: str = Field(description="Desde cuándo tiene el problema, p. ej. '2 años'. Vacío si no se dijo.")
    relato: list[str] = Field(description="Lo que contaron la familia, el colegio o las terapeutas.")
    funciones_biologicas: FuncionesBiologicas
    signos_vitales: SignosVitales
    examen: list[str] = Field(description="Examen físico: lo que observó o examinó el profesional.")
    diagnosticos: list[Diagnostico] = Field(description="Diagnósticos o impresiones que dijo el médico hoy.")
    examenes_auxiliares: list[str] = Field(description="Exámenes pedidos: laboratorio, imágenes, EEG, audiometría, escalas.")
    interconsultas: list[str] = Field(description="Interconsultas, derivaciones y terapias indicadas.")
    indicaciones: list[str] = Field(description="Indicaciones sin medicamentos para la familia y el colegio.")
    proximo_control: str = Field(description="Cuándo es el próximo control, como lo dijo el médico. Vacío si no se dijo.")
    proximo_control_semanas: int = Field(description="El próximo control en semanas (2 meses = 8). 0 si no se dijo.")
    por_confirmar: list[str] = Field(
        description="Datos que no se entendieron bien en el audio y el médico debe confirmar (sobre todo dosis)."
    )
    campos_especialidad: list[CampoEspecialidad] = Field(
        default_factory=list,
        description="Un elemento por cada campo de la plantilla de la especialidad, en el mismo orden y con el nombre exacto.",
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


def _clave(item: Diagnostico | str) -> str:
    """Para no duplicar: un diagnóstico se reconoce por su código CIE-10 (o su texto)."""
    if isinstance(item, Diagnostico):
        return item.cie10 or item.descripcion.lower()
    return item.lower()


def _fusionar_diagnosticos(actuales: list[Diagnostico], nuevos: list[Diagnostico]) -> list[Diagnostico]:
    """Agrega los diagnósticos nuevos. Si un presuntivo se confirma, pasa a definitivo."""
    resultado = [d.model_copy() for d in actuales]
    for nuevo in nuevos:
        igual = next((d for d in resultado if _clave(d) == _clave(nuevo)), None)
        if igual is None:
            # En la historia solo hay definitivos o presuntivos ("repetitivo" es de la atención).
            resultado.append(nuevo.model_copy(update={"tipo": "P" if nuevo.tipo == "P" else "D"}))
        elif igual.tipo == "P" and nuevo.tipo != "P":
            igual.tipo = "D"
    return resultado


def fusionar_historia(actual: HistoriaClinica, nueva: HistoriaClinica) -> HistoriaClinica:
    """Añade lo nuevo a la historia sin borrar nada de lo anterior.

    La IA solo propone lo nuevo; este código lo agrega. Así una respuesta mala
    del modelo nunca puede borrar antecedentes ya registrados.
    """
    datos = {}
    for campo in HistoriaClinica.model_fields:
        viejo, nuevo = getattr(actual, campo), getattr(nueva, campo)
        if campo == "diagnosticos":
            datos[campo] = _fusionar_diagnosticos(viejo, nuevo)
        elif isinstance(viejo, list):
            existentes = {_clave(v) for v in viejo}
            datos[campo] = viejo + [v for v in nuevo if v and _clave(v) not in existentes]
        else:
            datos[campo] = f"{viejo} {nuevo}".strip() if nuevo and nuevo not in viejo else viejo
    return HistoriaClinica(**datos)


HISTORIA_VACIA = HistoriaClinica(
    antecedentes_perinatales="", desarrollo_psicomotor="", inmunizaciones="", antecedentes_personales=[],
    antecedentes_familiares=[], alergias=[], diagnosticos=[], terapias=[],
)
