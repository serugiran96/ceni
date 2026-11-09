"""Voz a texto con Whisper (API de OpenAI)."""

import io

from ai.cliente import MODELO_TRANSCRIPCION, cliente

MAX_MB = 10  # tope por audio: unos 5 minutos en WAV; protege el saldo de la API


def transcribir(audio: bytes, nombre_archivo: str, vocabulario: str = "") -> str:
    """Devuelve el texto de un audio en español.

    `vocabulario` va como "prompt" de Whisper: le damos el nombre del paciente y
    términos de terapia para que los escriba bien (Whisper acepta ~200 palabras).
    """
    if len(audio) > MAX_MB * 1024 * 1024:
        raise ValueError(f"El audio pesa más de {MAX_MB} MB. Dicta un resumen más corto (máximo 3 minutos).")
    archivo = io.BytesIO(audio)
    archivo.name = nombre_archivo  # OpenAI usa la extensión para saber el formato
    respuesta = cliente().audio.transcriptions.create(
        model=MODELO_TRANSCRIPCION,
        file=archivo,
        language="es",
        prompt=vocabulario[:800],
    )
    return respuesta.text.strip()
