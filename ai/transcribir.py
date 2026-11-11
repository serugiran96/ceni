"""Voz a texto con Whisper: primero en Groq y, si no se puede, en OpenAI.

Una consulta completa puede durar 30 minutos o más, y la API acepta archivos de
hasta 25 MB (unos 13 minutos en el WAV que graba el navegador). Por eso, si el
audio es WAV y es grande, lo partimos en trozos de 10 minutos, los
transcribimos a la vez y unimos el texto.
"""

import io
import wave
from concurrent.futures import ThreadPoolExecutor

from ai.cliente import TRANSCRIPCION_GROQ, TRANSCRIPCION_OPENAI, cliente, cliente_groq, hay_groq

LIMITE_API_MB = 24  # la API acepta hasta 25 MB por archivo; dejamos margen
MINUTOS_POR_PARTE = 10
MAX_MINUTOS = 60  # una consulta más larga que esto probablemente es un error


PROVEEDORES = {  # nombre que se muestra: (cliente, modelo, largo máximo del vocabulario)
    "Groq": (cliente_groq, TRANSCRIPCION_GROQ, 500),  # Groq acepta un vocabulario más corto
    "OpenAI": (cliente, TRANSCRIPCION_OPENAI, 800),
}


def _pedir(proveedor: str, audio: bytes, nombre_archivo: str, vocabulario: str) -> str:
    crear_cliente, modelo, largo = PROVEEDORES[proveedor]
    archivo = io.BytesIO(audio)
    archivo.name = nombre_archivo  # la API usa la extensión para saber el formato
    respuesta = crear_cliente().audio.transcriptions.create(
        model=modelo,
        file=archivo,
        language="es",
        prompt=vocabulario[:largo],  # nombres y términos para que los escriba bien
    )
    return respuesta.text.strip()


def _whisper(audio: bytes, nombre_archivo: str, vocabulario: str, proveedor: str | None) -> tuple[str, str]:
    """Transcribe un trozo. Sin proveedor fijo: Groq y, si no hay clave o falla, OpenAI."""
    if proveedor:  # para comparar proveedores en la evaluación
        return _pedir(proveedor, audio, nombre_archivo, vocabulario), proveedor
    if hay_groq():
        try:
            return _pedir("Groq", audio, nombre_archivo, vocabulario), "Groq"
        except Exception:  # Groq caído, límite de uso o clave inválida: la consulta no se pierde
            pass
    return _pedir("OpenAI", audio, nombre_archivo, vocabulario), "OpenAI"


def _partir_wav(audio: bytes) -> list[bytes]:
    """Corta un WAV en trozos de MINUTOS_POR_PARTE (sin programas externos)."""
    with wave.open(io.BytesIO(audio)) as entrada:
        parametros = entrada.getparams()
        minutos = entrada.getnframes() / entrada.getframerate() / 60
        if minutos > MAX_MINUTOS:
            raise ValueError(f"El audio dura {minutos:.0f} minutos; el máximo es {MAX_MINUTOS}.")
        cuadros_por_parte = entrada.getframerate() * 60 * MINUTOS_POR_PARTE
        partes = []
        while cuadros := entrada.readframes(cuadros_por_parte):
            salida = io.BytesIO()
            with wave.open(salida, "wb") as trozo:
                trozo.setparams(parametros)
                trozo.writeframes(cuadros)
            partes.append(salida.getvalue())
    return partes


def transcribir(audio: bytes, nombre_archivo: str, vocabulario: str = "", proveedor: str | None = None) -> tuple[str, str]:
    """Devuelve el texto de un audio en español y quién lo transcribió ("Groq" u "OpenAI")."""
    es_wav = nombre_archivo.lower().endswith(".wav")
    if es_wav:
        partes = _partir_wav(audio) if len(audio) > LIMITE_API_MB * 1024 * 1024 else [audio]
    elif len(audio) > LIMITE_API_MB * 1024 * 1024:
        raise ValueError(f"El archivo pesa más de {LIMITE_API_MB} MB. Súbelo en WAV o en un MP3 más liviano.")
    else:
        partes = [audio]
    with ThreadPoolExecutor(max_workers=4) as hilos:  # los trozos se transcriben a la vez
        resultados = list(hilos.map(lambda parte: _whisper(parte, nombre_archivo, vocabulario, proveedor), partes))
    quienes = sorted({quien for _, quien in resultados})
    return " ".join(texto for texto, _ in resultados), " y ".join(quienes)
