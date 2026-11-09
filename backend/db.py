"""Base de datos de Ceni (SQLite).

Tablas:
- pacientes: datos personales.
- historias: la historia clínica acumulada de cada paciente (JSON validado por Pydantic).
- atenciones: cada consulta, con su transcripción, su nota y su receta (JSON).
- transcripciones: registro de cada vez que se procesa un audio (para el límite semanal).

Al arrancar, si la base no existe, se crea con los pacientes inventados de
data/semilla.json. En Streamlit Cloud el disco se borra al reiniciar, así que
el demo siempre vuelve a los datos semilla.
"""

import json
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

from ai.esquemas import HISTORIA_VACIA, HistoriaClinica, Medicamento, NotaAtencion

CARPETA_DATOS = Path(__file__).resolve().parent.parent / "data"
RUTA_DB = CARPETA_DATOS / "ceni.db"
RUTA_SEMILLA = CARPETA_DATOS / "semilla.json"

LIMITE_SEMANAL = 10  # transcripciones por paciente en los últimos 7 días

ESQUEMA_SQL = """
CREATE TABLE IF NOT EXISTS pacientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    fecha_nacimiento TEXT NOT NULL,
    sexo TEXT NOT NULL,
    apoderado TEXT NOT NULL,
    distrito TEXT NOT NULL,
    colegio TEXT NOT NULL,
    seguro TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS historias (
    paciente_id INTEGER PRIMARY KEY REFERENCES pacientes(id),
    historia_json TEXT NOT NULL,
    actualizada TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS atenciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paciente_id INTEGER NOT NULL REFERENCES pacientes(id),
    fecha TEXT NOT NULL,
    transcripcion TEXT NOT NULL DEFAULT '',
    nota_json TEXT NOT NULL,
    receta_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS transcripciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paciente_id INTEGER NOT NULL REFERENCES pacientes(id),
    creada_en TEXT NOT NULL
);
"""

CAMPOS_PACIENTE = ["nombre", "fecha_nacimiento", "sexo", "apoderado", "distrito", "colegio", "seguro"]


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
        if con.execute("SELECT COUNT(*) FROM pacientes").fetchone()[0] == 0:
            _cargar_semilla(con)


def _cargar_semilla(con: sqlite3.Connection) -> None:
    semilla = json.loads(RUTA_SEMILLA.read_text(encoding="utf-8"))
    for p in semilla["pacientes"]:
        con.execute(
            f"INSERT INTO pacientes (id, {', '.join(CAMPOS_PACIENTE)}) VALUES (?, {', '.join('?' * len(CAMPOS_PACIENTE))})",
            (p["id"], *[p[c] for c in CAMPOS_PACIENTE]),
        )
        historia = HistoriaClinica.model_validate(p["historia"])  # la semilla pasa por los mismos esquemas
        ultima = max(a["fecha"] for a in p["atenciones"])
        con.execute("INSERT INTO historias VALUES (?, ?, ?)", (p["id"], historia.model_dump_json(), ultima))
        for a in p["atenciones"]:
            nota = NotaAtencion.model_validate(a["nota"])
            receta = [Medicamento.model_validate(m) for m in a["receta"]]
            con.execute(
                "INSERT INTO atenciones (paciente_id, fecha, nota_json, receta_json) VALUES (?, ?, ?, ?)",
                (p["id"], a["fecha"], nota.model_dump_json(), _receta_json(receta)),
            )


def medico() -> dict:
    """El médico que usa el sistema (en el demo, uno inventado)."""
    return json.loads(RUTA_SEMILLA.read_text(encoding="utf-8"))["medico"]


def _receta_json(receta: list[Medicamento]) -> str:
    return json.dumps([m.model_dump() for m in receta], ensure_ascii=False)


def edad_texto(fecha_nacimiento: str, hoy: date | None = None) -> str:
    nac = date.fromisoformat(fecha_nacimiento)
    hoy = hoy or date.today()
    anios = hoy.year - nac.year - ((hoy.month, hoy.day) < (nac.month, nac.day))
    return f"{anios} años"


# --- Pacientes ----------------------------------------------------------------

def listar_pacientes() -> list[dict]:
    with conectar() as con:
        filas = con.execute(
            """
            SELECT p.*, h.historia_json, COUNT(a.id) AS n_atenciones, MAX(a.fecha) AS ultima_atencion
            FROM pacientes p
            JOIN historias h ON h.paciente_id = p.id
            LEFT JOIN atenciones a ON a.paciente_id = p.id
            GROUP BY p.id ORDER BY p.nombre
            """
        ).fetchall()
    pacientes = []
    for f in filas:
        p = dict(f)
        p["edad"] = edad_texto(p["fecha_nacimiento"])
        p["diagnosticos"] = HistoriaClinica.model_validate_json(p.pop("historia_json")).diagnosticos
        pacientes.append(p)
    return pacientes


def obtener_paciente(paciente_id: int) -> dict:
    with conectar() as con:
        fila = con.execute("SELECT * FROM pacientes WHERE id = ?", (paciente_id,)).fetchone()
    paciente = dict(fila)
    paciente["edad"] = edad_texto(paciente["fecha_nacimiento"])
    return paciente


def crear_paciente(datos: dict) -> int:
    """Registra un paciente nuevo con su historia clínica vacía. Devuelve su id."""
    with conectar() as con:
        cursor = con.execute(
            f"INSERT INTO pacientes ({', '.join(CAMPOS_PACIENTE)}) VALUES ({', '.join('?' * len(CAMPOS_PACIENTE))})",
            [datos[c] for c in CAMPOS_PACIENTE],
        )
        paciente_id = cursor.lastrowid
        con.execute(
            "INSERT INTO historias VALUES (?, ?, ?)",
            (paciente_id, HISTORIA_VACIA.model_dump_json(), date.today().isoformat()),
        )
    return paciente_id


# --- Historia clínica y atenciones -------------------------------------------

def historia_de(paciente_id: int) -> tuple[HistoriaClinica, str]:
    """La historia clínica y la fecha de su última actualización."""
    with conectar() as con:
        fila = con.execute(
            "SELECT historia_json, actualizada FROM historias WHERE paciente_id = ?", (paciente_id,)
        ).fetchone()
    return HistoriaClinica.model_validate_json(fila["historia_json"]), fila["actualizada"]


def atenciones_de(paciente_id: int) -> list[dict]:
    """Atenciones del paciente, de la más reciente a la más antigua."""
    with conectar() as con:
        filas = con.execute(
            "SELECT * FROM atenciones WHERE paciente_id = ? ORDER BY fecha DESC, id DESC", (paciente_id,)
        ).fetchall()
    atenciones = []
    for f in filas:
        a = dict(f)
        a["nota"] = NotaAtencion.model_validate_json(a.pop("nota_json"))
        a["receta"] = [Medicamento.model_validate(m) for m in json.loads(a.pop("receta_json"))]
        atenciones.append(a)
    return atenciones


def guardar_atencion(
    paciente_id: int, fecha: date, transcripcion: str,
    nota: NotaAtencion, receta: list[Medicamento], historia: HistoriaClinica,
) -> None:
    """Guarda la atención y actualiza la historia clínica en una sola transacción."""
    with conectar() as con:
        con.execute(
            "INSERT INTO atenciones (paciente_id, fecha, transcripcion, nota_json, receta_json) VALUES (?, ?, ?, ?, ?)",
            (paciente_id, fecha.isoformat(), transcripcion, nota.model_dump_json(), _receta_json(receta)),
        )
        con.execute(
            "UPDATE historias SET historia_json = ?, actualizada = ? WHERE paciente_id = ?",
            (historia.model_dump_json(), fecha.isoformat(), paciente_id),
        )


# --- Límite de transcripciones ------------------------------------------------

def transcripciones_semana(paciente_id: int) -> int:
    """Cuántas veces se procesó una consulta de este paciente en los últimos 7 días."""
    desde = (datetime.now() - timedelta(days=7)).isoformat()
    with conectar() as con:
        return con.execute(
            "SELECT COUNT(*) FROM transcripciones WHERE paciente_id = ? AND creada_en >= ?", (paciente_id, desde)
        ).fetchone()[0]


def registrar_transcripcion(paciente_id: int) -> None:
    with conectar() as con:
        con.execute(
            "INSERT INTO transcripciones (paciente_id, creada_en) VALUES (?, ?)",
            (paciente_id, datetime.now().isoformat()),
        )
