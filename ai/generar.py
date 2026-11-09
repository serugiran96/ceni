"""De la transcripción a datos, con un LLM de OpenAI y salidas estructuradas.

`chat.completions.parse` le pasa al modelo el esquema Pydantic (ai/esquemas.py)
y la API garantiza que la respuesta tenga exactamente esos campos. Pydantic la
vuelve a validar al recibirla. Así la app nunca recibe texto suelto.
"""

from ai.cliente import cliente, modelo_texto
from ai.esquemas import HistoriaClinica, ResultadoAtencion
from ai.prompts import ATENCION_SISTEMA


def procesar_atencion(transcripcion: str, paciente: dict, historia: HistoriaClinica) -> ResultadoAtencion:
    """Una sola llamada al modelo: nota de la atención + receta + lo nuevo de la historia."""
    usuario = (
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
    return mensaje.parsed
