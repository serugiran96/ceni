"""Texto a datos con un LLM de OpenAI y salidas estructuradas.

`chat.completions.parse` le pasa al modelo el esquema Pydantic (ai/esquemas.py)
y la API garantiza que la respuesta tenga exactamente esos campos. Pydantic la
vuelve a validar al recibirla. Así la app nunca recibe texto suelto.
"""

import json

from ai.cliente import cliente, modelo_texto
from ai.esquemas import ESCALA, InformePadres, NotaSesion
from ai.prompts import INFORME_SISTEMA, NOTA_SISTEMA


def _pedir(sistema: str, usuario: str, esquema):
    modelo = modelo_texto()
    # Poca creatividad: queremos fidelidad a lo dictado. Los modelos de
    # razonamiento (gpt-5, o3...) no aceptan temperature, por eso el if.
    extra = {"temperature": 0.2} if modelo.startswith("gpt-4") else {}
    respuesta = cliente().chat.completions.parse(
        model=modelo,
        messages=[
            {"role": "system", "content": sistema},
            {"role": "user", "content": usuario},
        ],
        response_format=esquema,
        **extra,
    )
    mensaje = respuesta.choices[0].message
    if mensaje.parsed is None:  # el modelo se negó o no terminó
        raise RuntimeError(mensaje.refusal or "El modelo no devolvió una respuesta válida.")
    return mensaje.parsed


def generar_nota(transcripcion: str, paciente: dict, objetivos: list[dict]) -> NotaSesion:
    """Convierte el dictado de la terapeuta en una nota de evolución."""
    plan = "\n".join(f"- id {o['id']}: {o['descripcion']}" for o in objetivos)
    usuario = (
        f"Paciente: {paciente['nombre']}, {paciente['edad']}.\n"
        f"Especialidad: {paciente['especialidad']}. Terapeuta: {paciente['terapeuta']}.\n"
        f"Objetivos del plan:\n{plan}\n\n"
        f"Transcripción del dictado:\n\"\"\"{transcripcion}\"\"\""
    )
    nota = _pedir(NOTA_SISTEMA, usuario, NotaSesion)
    # Defensa extra: descartamos avances de objetivos que no son de este paciente.
    ids_validos = {o["id"] for o in objetivos}
    nota.avances = [a for a in nota.avances if a.objetivo_id in ids_validos]
    return nota


def generar_informe(paciente: dict, objetivos: list[dict], sesiones: list[dict]) -> InformePadres:
    """Resume las últimas sesiones (de la más antigua a la más reciente) para la familia."""
    nombres = {o["id"]: o["descripcion"] for o in objetivos}
    historial = []
    for s in sesiones:
        nota = s["nota"].model_dump()
        for a in nota["avances"]:
            a["objetivo"] = nombres.get(a.pop("objetivo_id"), "")
            a["nivel"] = ESCALA[a["nivel"]]
        historial.append({"fecha": s["fecha"], **nota})
    usuario = (
        f"Niño o niña: {paciente['nombre']}, {paciente['edad']}.\n"
        f"Recibe el informe: {paciente['apoderado']}.\n"
        f"Terapia: {paciente['especialidad']}, con {paciente['terapeuta']}.\n"
        f"Motivo de consulta: {paciente['motivo_consulta']}\n\n"
        f"Notas de las últimas sesiones:\n{json.dumps(historial, ensure_ascii=False, indent=1)}"
    )
    return _pedir(INFORME_SISTEMA, usuario, InformePadres)
