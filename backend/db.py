"""Base de datos de Ceni (SQLite).

Tablas:
- pacientes: datos personales.
- historias: la historia clínica acumulada de cada paciente (JSON validado por Pydantic).
- atenciones: cada consulta, con su transcripción, su nota, su receta (JSON),
  quién la firmó y cuándo, y cuándo autorizó la familia la grabación.
- citas: la agenda del médico.
- transcripciones: registro de cada vez que se procesa una consulta (para el límite semanal).

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

VERSION_ESQUEMA = 2  # súbela cuando cambien las tablas o los esquemas: la base se vuelve a crear
LIMITE_SEMANAL = 10  # transcripciones por paciente en los últimos 7 días
ESTADOS_CITA = ["Programada", "Atendida", "No asistió"]

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
    cita_id INTEGER REFERENCES citas(id),
    fecha TEXT NOT NULL,
    transcripcion TEXT NOT NULL DEFAULT '',
    nota_json TEXT NOT NULL,
    receta_json TEXT NOT NULL,
    consentimiento_en TEXT,        -- cuándo marcó el médico que la familia autorizó grabar
    firmado_por TEXT NOT NULL,
    firmado_en TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS citas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paciente_id INTEGER NOT NULL REFERENCES pacientes(id),
    fecha TEXT NOT NULL,
    hora TEXT NOT NULL,
    tipo TEXT NOT NULL,            -- Primera vez / Control
    estado TEXT NOT NULL DEFAULT 'Programada'
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


def _semilla() -> dict:
    return json.loads(RUTA_SEMILLA.read_text(encoding="utf-8"))


def _version_guardada() -> int:
    with conectar() as con:
        return con.execute("PRAGMA user_version").fetchone()[0]


def crear_base(desde_cero: bool = False) -> None:
    """Crea las tablas y carga la semilla si la base está vacía o es de una versión anterior."""
    if RUTA_DB.exists() and (desde_cero or _version_guardada() != VERSION_ESQUEMA):
        RUTA_DB.unlink()
    with conectar() as con:
        con.executescript(ESQUEMA_SQL)
        con.execute(f"PRAGMA user_version = {VERSION_ESQUEMA}")
        if con.execute("SELECT COUNT(*) FROM pacientes").fetchone()[0] == 0:
            _cargar_semilla(con)


def _cargar_semilla(con: sqlite3.Connection) -> None:
    semilla = _semilla()
    medico = semilla["medico"]["nombre"]
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
            hora = f"{a['fecha']}T10:00:00"
            con.execute(
                """INSERT INTO atenciones (paciente_id, fecha, nota_json, receta_json, consentimiento_en, firmado_por, firmado_en)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (p["id"], a["fecha"], nota.model_dump_json(), _receta_json(receta), hora, medico, hora),
            )
    hoy = date.today()
    for c in semilla["citas"]:  # relativas a hoy, para que la agenda del demo nunca esté vacía
        con.execute(
            "INSERT INTO citas (paciente_id, fecha, hora, tipo) VALUES (?, ?, ?, ?)",
            (c["paciente_id"], (hoy + timedelta(days=c["en_dias"])).isoformat(), c["hora"], c["tipo"]),
        )


def medico() -> dict:
    """El médico que usa el sistema (en el demo, uno inventado)."""
    return _semilla()["medico"]


def _receta_json(receta: list[Medicamento]) -> str:
    return json.dumps([m.model_dump() for m in receta], ensure_ascii=False)


def numero_hc(paciente_id: int) -> str:
    """Número de historia clínica que se muestra, p. ej. 'HC-00012'."""
    return f"HC-{paciente_id:05d}"


def edad_texto(fecha_nacimiento: str, hoy: date | None = None) -> str:
    nac = date.fromisoformat(fecha_nacimiento)
    hoy = hoy or date.today()
    anios = hoy.year - nac.year - ((hoy.month, hoy.day) < (nac.month, nac.day))
    return f"{anios} año" if anios == 1 else f"{anios} años"


# --- Pacientes ----------------------------------------------------------------

def listar_pacientes(buscar: str = "") -> list[dict]:
    with conectar() as con:
        filas = con.execute(
            """
            SELECT p.*, h.historia_json, COUNT(a.id) AS n_atenciones, MAX(a.fecha) AS ultima_atencion,
                   (SELECT c.fecha || ' ' || c.hora FROM citas c
                    WHERE c.paciente_id = p.id AND c.estado = 'Programada' AND c.fecha >= date('now', 'localtime')
                    ORDER BY c.fecha, c.hora LIMIT 1) AS proxima_cita
            FROM pacientes p
            JOIN historias h ON h.paciente_id = p.id
            LEFT JOIN atenciones a ON a.paciente_id = p.id
            WHERE p.nombre LIKE ?
            GROUP BY p.id ORDER BY p.nombre
            """,
            (f"%{buscar.strip()}%",),
        ).fetchall()
    return [_con_historia(dict(f)) for f in filas]


def _con_historia(fila: dict) -> dict:
    """Agrega edad, número de HC, diagnósticos y alergias a una fila que trae historia_json."""
    historia = HistoriaClinica.model_validate_json(fila.pop("historia_json"))
    fila["edad"] = edad_texto(fila["fecha_nacimiento"])
    fila["hc"] = numero_hc(fila["paciente_id"] if "paciente_id" in fila else fila["id"])
    fila["diagnosticos"] = historia.diagnosticos
    fila["alergias"] = historia.alergias
    return fila


def obtener_paciente(paciente_id: int) -> dict:
    with conectar() as con:
        fila = con.execute("SELECT * FROM pacientes WHERE id = ?", (paciente_id,)).fetchone()
    paciente = dict(fila)
    paciente["edad"] = edad_texto(paciente["fecha_nacimiento"])
    paciente["hc"] = numero_hc(paciente["id"])
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
    paciente_id: int, fecha: date, transcripcion: str, nota: NotaAtencion, receta: list[Medicamento],
    historia: HistoriaClinica, firmado_por: str, consentimiento_en: str | None, cita_id: int | None = None,
    proxima_cita: tuple[date, str] | None = None,
) -> None:
    """Guarda la atención firmada, actualiza la historia y la agenda, todo en una sola transacción."""
    ahora = datetime.now().isoformat(timespec="seconds")
    with conectar() as con:
        con.execute(
            """INSERT INTO atenciones (paciente_id, cita_id, fecha, transcripcion, nota_json, receta_json,
                                       consentimiento_en, firmado_por, firmado_en)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (paciente_id, cita_id, fecha.isoformat(), transcripcion, nota.model_dump_json(),
             _receta_json(receta), consentimiento_en, firmado_por, ahora),
        )
        con.execute(
            "UPDATE historias SET historia_json = ?, actualizada = ? WHERE paciente_id = ?",
            (historia.model_dump_json(), fecha.isoformat(), paciente_id),
        )
        if cita_id:
            con.execute("UPDATE citas SET estado = 'Atendida' WHERE id = ?", (cita_id,))
        if proxima_cita:
            con.execute(
                "INSERT INTO citas (paciente_id, fecha, hora, tipo) VALUES (?, ?, ?, 'Control')",
                (paciente_id, proxima_cita[0].isoformat(), proxima_cita[1]),
            )


# --- Agenda -----------------------------------------------------------------------

def citas_entre(desde: date, hasta: date) -> list[dict]:
    """Citas entre dos fechas (incluidas), con el nombre, la edad y los diagnósticos del paciente."""
    with conectar() as con:
        filas = con.execute(
            """SELECT c.*, p.nombre, p.fecha_nacimiento, h.historia_json
               FROM citas c JOIN pacientes p ON p.id = c.paciente_id JOIN historias h ON h.paciente_id = p.id
               WHERE c.fecha BETWEEN ? AND ? ORDER BY c.fecha, c.hora""",
            (desde.isoformat(), hasta.isoformat()),
        ).fetchall()
    return [_con_historia(dict(f)) for f in filas]


def obtener_cita(cita_id: int) -> dict | None:
    with conectar() as con:
        fila = con.execute("SELECT * FROM citas WHERE id = ?", (cita_id,)).fetchone()
    return dict(fila) if fila else None


def crear_cita(paciente_id: int, fecha: date, hora: str, tipo: str) -> None:
    with conectar() as con:
        con.execute(
            "INSERT INTO citas (paciente_id, fecha, hora, tipo) VALUES (?, ?, ?, ?)",
            (paciente_id, fecha.isoformat(), hora, tipo),
        )


def cambiar_estado_cita(cita_id: int, estado: str) -> None:
    with conectar() as con:
        con.execute("UPDATE citas SET estado = ? WHERE id = ?", (estado, cita_id))


def proxima_cita_de(paciente_id: int) -> dict | None:
    """La próxima cita programada del paciente, desde hoy."""
    with conectar() as con:
        fila = con.execute(
            """SELECT * FROM citas WHERE paciente_id = ? AND estado = 'Programada' AND fecha >= ?
               ORDER BY fecha, hora LIMIT 1""",
            (paciente_id, date.today().isoformat()),
        ).fetchone()
    return dict(fila) if fila else None


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
