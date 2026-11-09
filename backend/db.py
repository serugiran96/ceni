"""Base de datos de Ceni (SQLite).

Guarda pacientes, objetivos del plan y sesiones. La nota de cada sesión se
guarda como JSON tal como la validó Pydantic (ai/esquemas.py). Al arrancar,
si la base no existe, se crea y se llena con los pacientes inventados de
data/semilla.json. En Streamlit Cloud el disco se borra al reiniciar, así que
el demo siempre vuelve a los datos semilla.
"""

import json
import sqlite3
from datetime import date
from pathlib import Path

import pandas as pd

from ai.esquemas import NotaSesion

CARPETA_DATOS = Path(__file__).resolve().parent.parent / "data"
RUTA_DB = CARPETA_DATOS / "ceni.db"
RUTA_SEMILLA = CARPETA_DATOS / "semilla.json"

ESQUEMA_SQL = """
CREATE TABLE IF NOT EXISTS pacientes (
    id INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL,
    fecha_nacimiento TEXT NOT NULL,
    apoderado TEXT NOT NULL,
    motivo_consulta TEXT NOT NULL,
    especialidad TEXT NOT NULL,
    terapeuta TEXT NOT NULL,
    sede TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS objetivos (
    id INTEGER PRIMARY KEY,
    paciente_id INTEGER NOT NULL REFERENCES pacientes(id),
    descripcion TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sesiones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paciente_id INTEGER NOT NULL REFERENCES pacientes(id),
    fecha TEXT NOT NULL,
    transcripcion TEXT NOT NULL DEFAULT '',
    nota_json TEXT NOT NULL
);
"""


def conectar() -> sqlite3.Connection:
    """Abre una conexión nueva. Cada función abre y cierra la suya."""
    con = sqlite3.connect(RUTA_DB)
    con.row_factory = sqlite3.Row  # filas que se leen como diccionarios
    return con


def crear_base(desde_cero: bool = False) -> None:
    """Crea las tablas y carga la semilla si la base está vacía."""
    if desde_cero and RUTA_DB.exists():
        RUTA_DB.unlink()
    with conectar() as con:
        con.executescript(ESQUEMA_SQL)
        vacia = con.execute("SELECT COUNT(*) FROM pacientes").fetchone()[0] == 0
        if vacia:
            _cargar_semilla(con)


def _cargar_semilla(con: sqlite3.Connection) -> None:
    semilla = json.loads(RUTA_SEMILLA.read_text(encoding="utf-8"))
    for p in semilla["pacientes"]:
        con.execute(
            "INSERT INTO pacientes VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (p["id"], p["nombre"], p["fecha_nacimiento"], p["apoderado"],
             p["motivo_consulta"], p["especialidad"], p["terapeuta"], p["sede"]),
        )
        for o in p["objetivos"]:
            con.execute("INSERT INTO objetivos VALUES (?, ?, ?)", (o["id"], p["id"], o["descripcion"]))
        for s in p["sesiones"]:
            nota = NotaSesion.model_validate(s["nota"])  # la semilla pasa por el mismo esquema
            con.execute(
                "INSERT INTO sesiones (paciente_id, fecha, nota_json) VALUES (?, ?, ?)",
                (p["id"], s["fecha"], nota.model_dump_json()),
            )


def edad_texto(fecha_nacimiento: str, hoy: date | None = None) -> str:
    nac = date.fromisoformat(fecha_nacimiento)
    hoy = hoy or date.today()
    anios = hoy.year - nac.year - ((hoy.month, hoy.day) < (nac.month, nac.day))
    return f"{anios} años"


def listar_pacientes() -> list[dict]:
    with conectar() as con:
        filas = con.execute(
            """
            SELECT p.*, COUNT(s.id) AS n_sesiones, MAX(s.fecha) AS ultima_sesion
            FROM pacientes p LEFT JOIN sesiones s ON s.paciente_id = p.id
            GROUP BY p.id ORDER BY p.nombre
            """
        ).fetchall()
    pacientes = [dict(f) for f in filas]
    for p in pacientes:
        p["edad"] = edad_texto(p["fecha_nacimiento"])
    return pacientes


def obtener_paciente(paciente_id: int) -> dict:
    with conectar() as con:
        fila = con.execute("SELECT * FROM pacientes WHERE id = ?", (paciente_id,)).fetchone()
    paciente = dict(fila)
    paciente["edad"] = edad_texto(paciente["fecha_nacimiento"])
    return paciente


def objetivos_de(paciente_id: int) -> list[dict]:
    with conectar() as con:
        filas = con.execute(
            "SELECT id, descripcion FROM objetivos WHERE paciente_id = ? ORDER BY id", (paciente_id,)
        ).fetchall()
    return [dict(f) for f in filas]


def sesiones_de(paciente_id: int) -> list[dict]:
    """Sesiones del paciente, de la más reciente a la más antigua."""
    with conectar() as con:
        filas = con.execute(
            "SELECT * FROM sesiones WHERE paciente_id = ? ORDER BY fecha DESC, id DESC", (paciente_id,)
        ).fetchall()
    sesiones = []
    for f in filas:
        s = dict(f)
        s["nota"] = NotaSesion.model_validate_json(s.pop("nota_json"))
        sesiones.append(s)
    return sesiones


def guardar_sesion(paciente_id: int, fecha: date, transcripcion: str, nota: NotaSesion) -> None:
    with conectar() as con:
        con.execute(
            "INSERT INTO sesiones (paciente_id, fecha, transcripcion, nota_json) VALUES (?, ?, ?, ?)",
            (paciente_id, fecha.isoformat(), transcripcion, nota.model_dump_json()),
        )


def avances_de(paciente_id: int) -> pd.DataFrame:
    """Una fila por sesión y objetivo: fecha, objetivo, nivel. Alimenta el gráfico."""
    nombres = {o["id"]: o["descripcion"] for o in objetivos_de(paciente_id)}
    filas = []
    for s in sesiones_de(paciente_id):
        for a in s["nota"].avances:
            if a.objetivo_id in nombres:
                filas.append({"fecha": s["fecha"], "objetivo": nombres[a.objetivo_id], "nivel": a.nivel})
    df = pd.DataFrame(filas, columns=["fecha", "objetivo", "nivel"])
    df["fecha"] = pd.to_datetime(df["fecha"])
    return df.sort_values("fecha")
