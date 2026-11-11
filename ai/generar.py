"""De la transcripción a datos, con un LLM de OpenAI y salidas estructuradas.

`chat.completions.parse` le pasa al modelo el esquema Pydantic (ai/esquemas.py)
y la API garantiza que la respuesta tenga exactamente esos campos. Pydantic la
vuelve a validar al recibirla. Así la app nunca recibe texto suelto.
"""

from ai.cliente import cliente, modelo_texto
from ai.esquemas import CampoEspecialidad, HistoriaClinica, Plantilla, ResultadoAtencion
from ai.prompts import ATENCION_SISTEMA


def _campos_plantilla(plantilla: Plantilla | None) -> str:
    if not plantilla or not plantilla.campos:
        return "Plantilla: sin campos de especialidad (deja campos_especialidad vacío)."
    lineas = "\n".join(f"- {c.nombre}: {c.descripcion}" for c in plantilla.campos)
    return f"Plantilla de la especialidad ({plantilla.nombre}). Campos:\n{lineas}"


def _alinear(campos: list[CampoEspecialidad], plantilla: Plantilla | None) -> list[CampoEspecialidad]:
    """Deja exactamente los campos de la plantilla, en su orden, aunque el modelo haya omitido o agregado alguno."""
    if not plantilla:
        return []
    valores = {c.nombre.strip().lower(): c.valor for c in campos}
    return [CampoEspecialidad(nombre=c.nombre, valor=valores.get(c.nombre.strip().lower(), "")) for c in plantilla.campos]


def procesar_atencion(transcripcion: str, paciente: dict, historia: HistoriaClinica, profesional: dict) -> ResultadoAtencion:
    """Una sola llamada al modelo: nota de la atención + receta + lo nuevo de la historia."""
    usuario = (
        f"Profesional que atiende: {profesional['nombre']} ({profesional['especialidad']}).\n"
        f"{_campos_plantilla(profesional.get('plantilla'))}\n\n"
        f"Paciente: {paciente['nombre']}, {paciente['edad']}, {paciente['sexo']}. "
        f"Apoderado: {paciente['apoderado']}.\n\n"
        f"Historia clínica actual (JSON):\n{historia.model_dump_json(indent=1)}\n\n"
        f"Transcripción de la consulta:\n\"\"\"{transcripcion}\"\"\""
    )
    modelo = modelo_texto()
    # Poca creatividad: queremos fidelidad a lo dicho. Los modelos de
    # razonamiento (gpt-5, o3...) no aceptan temperature, por eso el if.
    extra = {"temperature": 0.2} if modelo.startswith("gpt-4") else {}
    respuesta = cliente().chat.completions.parse(
        model=modelo,
        messages=[
            {"role": "system", "content": ATENCION_SISTEMA},
            {"role": "user", "content": usuario},
        ],
        response_format=ResultadoAtencion,
        **extra,
    )
    mensaje = respuesta.choices[0].message
    if mensaje.parsed is None:  # el modelo se negó o no terminó
        raise RuntimeError(mensaje.refusal or "El modelo no devolvió una respuesta válida.")
    resultado = mensaje.parsed
    resultado.atencion.campos_especialidad = _alinear(resultado.atencion.campos_especialidad, profesional.get("plantilla"))
    return resultado
