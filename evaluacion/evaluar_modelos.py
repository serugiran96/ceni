"""Evaluación de modelos de IA para Ceni: cuál da mejores resultados por su costo.

Uso (en la Mac, con OPENAI_API_KEY y GROQ_API_KEY en .env):
    .venv/bin/python evaluacion/evaluar_modelos.py

Qué hace:
1. Audios de prueba: lee en voz alta los 2 guiones de data/audios_demo/guiones.md
   con las voces en español de la Mac (una voz por persona). Se guardan en
   evaluacion/audios/ y se reutilizan.
2. Transcripción: cada modelo transcribe los mismos audios. Medimos los términos
   clínicos que escribe bien (medicamentos, dosis, tiempos), el error por
   palabra (WER) contra el guion, el tiempo y el costo.
3. Nota de la atención: cada modelo de texto recibe el mismo texto (el guion) y
   arma la nota con salidas estructuradas. Contamos los datos que acierta de una
   lista y los datos que NO debió inventar.
4. Escribe los resultados en docs/evaluacion.md.

Los precios son de lista (noviembre de 2026, fuentes secundarias) y el costo se
calcula con los tokens que reporta la API en cada llamada.
"""

import io
import os
import re
import subprocess
import sys
import tempfile
import time
import wave
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
os.chdir(RAIZ)

from dotenv import load_dotenv  # noqa: E402

load_dotenv(RAIZ / ".env")

from openai import OpenAI  # noqa: E402

from ai.esquemas import ResultadoAtencion  # noqa: E402
from ai.generar import _alinear, _campos_plantilla  # noqa: E402
from ai.prompts import ATENCION_SISTEMA  # noqa: E402
from backend import db  # noqa: E402

AUDIOS = RAIZ / "evaluacion" / "audios"
CAMBIO = 3.75  # soles por dólar, de referencia

# --- Los casos de prueba: guion, paciente, médico y lo que debe salir ----------------

def _num(texto: str) -> str:
    return texto.replace(",", ".")


CASOS = [
    {
        "nombre": "Control de neuropediatría (Fabricio)",
        "titulo": "## control-de-fabricio.mp3", "hasta": "## control-de-antonella",
        "paciente_id": 1, "medico_id": 1,
        "voces": {"Doctora": "Paulina", "Mamá": "Mónica"},
        # Términos que la transcripción debe escribir bien (cualquiera de las variantes).
        "terminos": [["melatonina"], ["1,5", "1.5", "uno coma cinco"], ["media tableta"], ["cada noche"],
                     ["un mes", "1 mes"], ["dos meses", "2 meses"], ["lenguaje"], ["ocupacional"], ["otitis"],
                     ["agenda visual"], ["examen neurológico"], ["fabricio"]],
        # Lo que la nota debe tener...
        "aciertos": {
            "Receta: melatonina": lambda r: any("melatonina" in m.medicamento.lower() for m in r.receta),
            "Dosis: 1.5 mg": lambda r: any("1.5" in _num(m.dosis + m.medicamento) for m in r.receta),
            "Frecuencia: cada noche": lambda r: any("noche" in m.frecuencia.lower() for m in r.receta),
            "Duración: un mes": lambda r: any("mes" in m.duracion.lower() for m in r.receta),
            "Control en 8 semanas": lambda r: r.atencion.proximo_control_semanas == 8,
            "Terapia de lenguaje": lambda r: any("lenguaje" in x.lower() for x in r.atencion.interconsultas),
            "Terapia ocupacional": lambda r: any("ocupacional" in x.lower() for x in r.atencion.interconsultas),
            "Pide el informe de la terapeuta": lambda r: any(
                "informe" in x.lower() for x in r.atencion.examenes_auxiliares + r.atencion.interconsultas
                + r.atencion.indicaciones),
            "Otitis en el relato": lambda r: any("otitis" in x.lower() for x in r.atencion.relato),
            "Diagnóstico F84.0": lambda r: any(d.cie10.startswith("F84") for d in r.atencion.diagnosticos),
        },
        # ...y lo que NO debe inventar.
        "inventos": {
            "Sed (nadie habló de sed)": lambda r: bool(r.atencion.funciones_biologicas.sed.strip()),
            "Tiempo de enfermedad (no se dijo)": lambda r: bool(r.atencion.tiempo_enfermedad.strip()),
            "Otro medicamento (el antibiótico fue de otra clínica)": lambda r: len(r.receta) > 1,
            "Signos vitales (no se dijeron)": lambda r: any(v is not None for v in r.atencion.signos_vitales.model_dump().values()),
        },
    },
    {
        "nombre": "Odontología para pacientes especiales (Antonella)",
        "titulo": "## odontologia-de-antonella.mp3", "hasta": None,
        "paciente_id": 2, "medico_id": 2,
        "voces": {"Doctor": "Eddy (Español (México))", "Papá": "Reed (Español (México))"},
        "terminos": [["amoxicilina"], ["250", "doscientos cincuenta"], ["cada ocho horas", "cada 8 horas"],
                     ["cinco días", "5 días"], ["paracetamol"], ["barniz de flúor"], ["caries"], ["molar"],
                     ["tres semanas", "3 semanas"], ["antonella"]],
        "aciertos": {
            "Receta: amoxicilina": lambda r: any("amoxicilina" in m.medicamento.lower() for m in r.receta),
            "Amoxicilina 250 mg": lambda r: any("250" in m.medicamento + m.dosis for m in r.receta
                                                if "amoxicilina" in m.medicamento.lower()),
            "Cada 8 horas": lambda r: any("8" in m.frecuencia or "ocho" in m.frecuencia.lower() for m in r.receta),
            "Por 5 días": lambda r: any("5" in m.duracion or "cinco" in m.duracion.lower() for m in r.receta),
            "Receta: paracetamol": lambda r: any("paracetamol" in m.medicamento.lower() for m in r.receta),
            "Procedimiento: barniz de flúor": lambda r: any("flúor" in c.valor.lower() or "fluor" in c.valor.lower()
                                                          for c in r.atencion.campos_especialidad
                                                          if c.nombre == "Procedimiento realizado"),
            "Pieza: molar": lambda r: any("molar" in c.valor.lower() for c in r.atencion.campos_especialidad
                                          if c.nombre == "Piezas tratadas"),
            "Manejo de conducta": lambda r: any(c.valor.strip() for c in r.atencion.campos_especialidad
                                                if c.nombre == "Manejo de conducta"),
            "Control en 3 semanas": lambda r: r.atencion.proximo_control_semanas == 3,
            "Diagnóstico de caries (K02)": lambda r: any(d.cie10.startswith("K02") for d in r.atencion.diagnosticos),
        },
        "inventos": {
            "Tiempo de enfermedad (no se dijo)": lambda r: bool(r.atencion.tiempo_enfermedad.strip()),
            "Signos vitales (no se dijeron)": lambda r: any(v is not None for v in r.atencion.signos_vitales.model_dump().values()),
            "Medicamentos de más": lambda r: len(r.receta) > 2,
        },
    },
]

# --- Modelos a comparar ------------------------------------------------------------

TRANSCRIPCION = [  # nombre, proveedor, modelo, US$ por minuto
    ("Whisper large-v3-turbo", "Groq", "whisper-large-v3-turbo", 0.04 / 60),
    ("Whisper large-v3", "Groq", "whisper-large-v3", 0.111 / 60),
    ("whisper-1", "OpenAI", "whisper-1", 0.006),
    ("gpt-4o-mini-transcribe", "OpenAI", "gpt-4o-mini-transcribe", 0.003),
    ("gpt-4o-transcribe", "OpenAI", "gpt-4o-transcribe", 0.006),
]
TEXTO = [  # modelo, US$ por millón de tokens de entrada y de salida
    ("gpt-4.1-mini", 0.40, 1.60),
    ("gpt-4o-mini", 0.15, 0.60),
    ("gpt-5-nano", 0.05, 0.40),
    ("gpt-5-mini", 0.25, 2.00),
    ("gpt-4.1", 2.00, 8.00),
]


def cliente(proveedor: str) -> OpenAI:
    if proveedor == "Groq":
        return OpenAI(api_key=os.getenv("GROQ_API_KEY"), base_url="https://api.groq.com/openai/v1", timeout=120)
    return OpenAI(timeout=120)


def guion(caso: dict) -> list[tuple[str, str]]:
    """Las líneas del guion como (quién habla, qué dice)."""
    texto = (RAIZ / "data" / "audios_demo" / "guiones.md").read_text(encoding="utf-8")
    bloque = texto.split(caso["titulo"])[1]
    if caso["hasta"]:
        bloque = bloque.split(caso["hasta"])[0]
    return [(m.group(1), m.group(2).strip()) for m in re.finditer(r"\*\*([^*]+):\*\*\s*(.+)", bloque)]


def referencia(caso: dict) -> str:
    return " ".join(frase for _, frase in guion(caso))


# --- 1. Audios de prueba -----------------------------------------------------------

def audio_de(caso: dict) -> Path:
    """Arma (una sola vez) el audio del guion con una voz de la Mac por persona."""
    destino = AUDIOS / f"{caso['titulo'][3:].replace('.mp3', '')}.m4a"
    if destino.exists():
        return destino
    AUDIOS.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        partes = []
        for i, (quien, frase) in enumerate(guion(caso)):
            aiff, wav = Path(tmp) / f"{i}.aiff", Path(tmp) / f"{i}.wav"
            subprocess.run(["say", "-v", caso["voces"].get(quien, "Paulina"), "-o", str(aiff), frase], check=True)
            subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@16000", "-c", "1", str(aiff), str(wav)], check=True)
            partes.append(wav)
        junto = Path(tmp) / "junto.wav"
        with wave.open(str(junto), "wb") as salida:
            for i, parte in enumerate(partes):
                with wave.open(str(parte)) as entrada:
                    if i == 0:
                        salida.setparams(entrada.getparams())
                    salida.writeframes(entrada.readframes(entrada.getnframes()))
                    salida.writeframes(b"\x00\x00" * 8000)  # medio segundo de pausa entre frases
        subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", str(junto), str(destino)], check=True)
    return destino


def minutos(ruta: Path) -> float:
    salida = subprocess.run(["afinfo", str(ruta)], capture_output=True, text=True).stdout
    return float(re.search(r"estimated duration: ([\d.]+)", salida).group(1)) / 60


# --- 2. Transcripción --------------------------------------------------------------

def palabras(texto: str) -> list[str]:
    return re.sub(r"[^\w\s]", " ", texto.lower()).split()


def wer(ref: str, hip: str) -> float:
    """Error por palabra: cambios, borrados e inserciones sobre las palabras del guion."""
    r, h = palabras(ref), palabras(hip)
    fila = list(range(len(h) + 1))
    for i in range(1, len(r) + 1):
        anterior, fila[0] = fila[0], i
        for j in range(1, len(h) + 1):
            actual = min(fila[j] + 1, fila[j - 1] + 1, anterior + (r[i - 1] != h[j - 1]))
            anterior, fila[j] = fila[j], actual
    return fila[-1] / len(r)


def terminos_ok(caso: dict, texto: str) -> int:
    texto = " ".join(texto.lower().split())
    return sum(any(v in texto for v in variantes) for variantes in caso["terminos"])


def evaluar_transcripcion() -> list[dict]:
    filas = []
    for nombre, proveedor, modelo, usd_min in TRANSCRIPCION:
        total_ok = total_terminos = segundos = costo = wer_suma = 0
        for caso in CASOS:
            ruta = audio_de(caso)
            archivo = io.BytesIO(ruta.read_bytes())
            archivo.name = ruta.name
            inicio = time.monotonic()
            texto = cliente(proveedor).audio.transcriptions.create(model=modelo, file=archivo, language="es").text
            segundos += time.monotonic() - inicio
            total_ok += terminos_ok(caso, texto)
            total_terminos += len(caso["terminos"])
            wer_suma += wer(referencia(caso), texto)
            costo += usd_min * minutos(ruta)
        filas.append({"modelo": nombre, "proveedor": proveedor, "terminos": f"{total_ok} de {total_terminos}",
                      "wer": wer_suma / len(CASOS), "segundos": segundos / len(CASOS),
                      "costo_20min_soles": usd_min * 20 * CAMBIO, "costo_prueba_usd": costo})
        print(filas[-1])
    return filas


# --- 3. Nota de la atención ----------------------------------------------------------

def evaluar_texto() -> list[dict]:
    db.crear_base()
    filas = []
    for modelo, usd_in, usd_out in TEXTO:
        aciertos = total_aciertos = inventos = total_inventos = segundos = costo = 0
        fallas = []
        for caso in CASOS:
            paciente = db.obtener_paciente(caso["paciente_id"])
            historia, _ = db.historia_de(caso["paciente_id"])
            medico = db.medico(caso["medico_id"])
            usuario = (
                f"Profesional que atiende: {medico['nombre']} ({medico['especialidad']}).\n"
                f"{_campos_plantilla(medico.get('plantilla'))}\n\n"
                f"Paciente: {paciente['nombre']}, {paciente['edad']}, {paciente['sexo']}. "
                f"Apoderado: {paciente['apoderado']}.\n\n"
                f"Historia clínica actual (JSON):\n{historia.model_dump_json(indent=1)}\n\n"
                f"Transcripción de la consulta:\n\"\"\"{referencia(caso)}\"\"\""
            )
            extra = {"temperature": 0.2} if modelo.startswith("gpt-4") else {"reasoning_effort": "low"}
            inicio = time.monotonic()
            respuesta = OpenAI(timeout=180).chat.completions.parse(
                model=modelo, response_format=ResultadoAtencion,
                messages=[{"role": "system", "content": ATENCION_SISTEMA}, {"role": "user", "content": usuario}], **extra,
            )
            segundos += time.monotonic() - inicio
            r = respuesta.choices[0].message.parsed
            r.atencion.campos_especialidad = _alinear(r.atencion.campos_especialidad, medico.get("plantilla"))
            uso = respuesta.usage
            costo += (uso.prompt_tokens * usd_in + uso.completion_tokens * usd_out) / 1e6
            for nombre, prueba in caso["aciertos"].items():
                ok = bool(prueba(r))
                aciertos += ok
                fallas += [] if ok else [f"falta: {nombre}"]
            for nombre, prueba in caso["inventos"].items():
                malo = bool(prueba(r))
                inventos += malo
                fallas += [f"inventó: {nombre}"] if malo else []
            total_aciertos += len(caso["aciertos"])
            total_inventos += len(caso["inventos"])
        filas.append({"modelo": modelo, "aciertos": f"{aciertos} de {total_aciertos}", "inventos": inventos,
                      "segundos": segundos / len(CASOS), "costo_consulta_soles": costo / len(CASOS) * CAMBIO,
                      "fallas": fallas})
        print(filas[-1])
    return filas


# --- 4. Informe --------------------------------------------------------------------

def escribir_informe(trans: list[dict], texto: list[dict]) -> None:
    lineas = [
        "# Evaluación de modelos de IA",
        "",
        f"Hecha el {date.today():%d/%m/%Y} con `evaluacion/evaluar_modelos.py`, que cualquiera puede volver a correr.",
        "Casos: los 2 guiones de `data/audios_demo/guiones.md` (control de neuropediatría y odontología para pacientes "
        "especiales), leídos con las voces en español de la Mac, una por persona.",
        "",
        "## 1. Transcripción (voz a texto)",
        "",
        "| Modelo | Proveedor | Términos clínicos bien escritos | Error por palabra (WER) | Tiempo por audio | "
        "Costo de una consulta de 20 min |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for f in trans:
        lineas.append(f"| {f['modelo']} | {f['proveedor']} | {f['terminos']} | {f['wer']:.0%} | {f['segundos']:.1f} s | "
                      f"S/ {f['costo_20min_soles']:.3f} |")
    lineas += [
        "",
        "El error por palabra cuenta también diferencias de forma (por ejemplo, «1,5» frente a «uno coma cinco»), "
        "por eso los términos clínicos son la medida principal.",
        "",
        "## 2. Nota de la atención (texto a datos, con salidas estructuradas)",
        "",
        "| Modelo | Datos correctos | Datos inventados | Tiempo por nota | Costo por consulta |",
        "|---|---:|---:|---:|---:|",
    ]
    for f in texto:
        lineas.append(f"| {f['modelo']} | {f['aciertos']} | {f['inventos']} | {f['segundos']:.1f} s | "
                      f"S/ {f['costo_consulta_soles']:.4f} |")
    lineas += ["", "Lo que falló en cada modelo:", ""]
    for f in texto:
        lineas.append(f"- **{f['modelo']}:** " + ("; ".join(f["fallas"]) if f["fallas"] else "nada"))
    lineas += [
        "",
        "## Límites",
        "",
        "- Son 2 casos, con voces sintéticas y sin ruido: sirven para comparar modelos entre sí, no para prometer el "
        "acierto en una consulta real. El piloto lo mide con la tasa de corrección de los médicos.",
        "- Cada modelo corrió una vez por caso; los modelos pueden variar entre corridas.",
        "- Precios de lista de noviembre de 2026, de fuentes secundarias; tipo de cambio de S/ 3.75.",
    ]
    (RAIZ / "docs" / "evaluacion.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")


if __name__ == "__main__":
    trans = evaluar_transcripcion()
    texto = evaluar_texto()
    escribir_informe(trans, texto)
    print("Listo: docs/evaluacion.md")
