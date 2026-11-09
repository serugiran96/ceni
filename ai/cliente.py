"""Conexión con OpenAI.

La clave nunca está en el código: se lee de la variable de entorno
OPENAI_API_KEY. En la laptop viene del archivo .env (que Git ignora); en
Streamlit Cloud, streamlit_app.py la copia desde st.secrets al arrancar.
"""

import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()  # lee el .env si existe; si no, no hace nada

MODELO_TRANSCRIPCION = "whisper-1"  # Whisper, la herramienta de voz a texto del curso
MODELO_POR_DEFECTO = "gpt-4.1-mini"  # rápido y barato; acepta salidas estructuradas


def modelo_texto() -> str:
    """Modelo para la nota y el informe. Se puede cambiar con OPENAI_MODEL."""
    return os.getenv("OPENAI_MODEL") or MODELO_POR_DEFECTO


def hay_clave() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def cliente() -> OpenAI:
    if not hay_clave():
        raise RuntimeError("Falta OPENAI_API_KEY: ponla en .env (local) o en los secrets de Streamlit.")
    return OpenAI(timeout=60, max_retries=1)
