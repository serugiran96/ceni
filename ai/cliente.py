"""Conexión con los proveedores de IA.

- Groq transcribe el audio con Whisper large-v3-turbo: es el mismo Whisper,
  unas 9 veces más barato que whisper-1 de OpenAI.
- OpenAI arma la nota con gpt-4.1-mini. También transcribe con whisper-1 si no
  hay clave de Groq o si Groq falla, para que la consulta no se pierda.

Las claves nunca están en el código: se leen de las variables de entorno
GROQ_API_KEY y OPENAI_API_KEY. En la laptop vienen del archivo .env (que Git
ignora); en Streamlit Cloud, streamlit_app.py las copia desde st.secrets.
"""

import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()  # lee el .env si existe; si no, no hace nada

GROQ_URL = "https://api.groq.com/openai/v1"  # la API de Groq funciona igual que la de OpenAI
TRANSCRIPCION_GROQ = "whisper-large-v3-turbo"  # Whisper, la herramienta de voz a texto del curso
TRANSCRIPCION_OPENAI = "whisper-1"  # respaldo
MODELO_POR_DEFECTO = "gpt-4.1-mini"  # rápido y barato; acepta salidas estructuradas


def modelo_texto() -> str:
    """Modelo para la nota y el informe. Se puede cambiar con OPENAI_MODEL."""
    return os.getenv("OPENAI_MODEL") or MODELO_POR_DEFECTO


def hay_clave() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def hay_groq() -> bool:
    return bool(os.getenv("GROQ_API_KEY"))


def cliente_groq() -> OpenAI:
    """El mismo SDK de OpenAI, apuntando a Groq."""
    return OpenAI(api_key=os.getenv("GROQ_API_KEY"), base_url=GROQ_URL, timeout=60, max_retries=1)


def cliente() -> OpenAI:
    if not hay_clave():
        raise RuntimeError("Falta OPENAI_API_KEY: ponla en .env (local) o en los secrets de Streamlit.")
    return OpenAI(timeout=60, max_retries=1)
