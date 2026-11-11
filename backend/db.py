"""Base de datos de Ceni (SQLite).

Tablas:
- consultorios: cada cliente de Ceni (un consultorio o centro, con uno o varios médicos).
- plantillas: los campos que cada especialidad suma al formato de consulta externa del MINSA.
- medicos: cada profesional, con su consultorio y su plantilla.
- pacientes: datos personales; cada paciente es de un consultorio.
- historias: la historia clínica acumulada de cada paciente (JSON validado por Pydantic).
- atenciones: cada consulta, con su transcripción, su nota, su receta (JSON),
  quién la firmó y cuándo, cuándo autorizó la familia la grabación y el
  borrador que propuso la IA (para medir cuánto acertó Ceni), quién la atendió
  y cuánto tardaron la IA y el médico.
- citas: la agenda de cada profesional del centro (medico_id).
- transcripciones: registro de cada vez que se procesa una consulta (para el límite semanal).

Al arrancar, si la base no existe, se crea con los pacientes inventados de
data/semilla.json. En Streamlit Cloud el disco se borra al reiniciar, así que
el demo siempre vuelve a los datos semilla.
"""

import json
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

from ai.esquemas import HISTORIA_VACIA, HistoriaClinica, Medicamento, NotaAtencion, Plantilla
from backend.acierto import Acierto, comparar

CARPETA_DATOS = Path(__file__).resolve().parent.parent / "data"
RUTA_DB = CARPETA_DATOS / "ceni.db"
RUTA_SEMILLA = CARPETA_DATOS / "semilla.json"

VERSION_ESQUEMA = 6  # súbela cuando cambien las tablas, los esquemas o la semilla: la base se vuelve a crear
LIMITE_SEMANAL = 10  # transcripciones por paciente en los últimos 7 días
ESTADOS_CITA = ["Programada", "Atendida", "No asistió"]

ESQUEMA_SQL = """
CREATE TABLE IF NOT EXISTS consultorios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    distrito TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS plantillas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plantilla_json TEXT NOT NULL   -- nombre, campos y vocabulario (validado por Pydantic)
);
CREATE TABLE IF NOT EXISTS medicos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    consultorio_id INTEGER NOT NULL REFERENCES consultorios(id),
    nombre TEXT NOT NULL,
    especialidad TEXT NOT NULL,    -- solo se muestra; los campos vienen de la plantilla
    colegiatura TEXT NOT NULL,
    plantilla_id INTEGER REFERENCES plantillas(id)
);
CREATE TABLE IF NOT EXISTS pacientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    consultorio_id INTEGER NOT NULL DEFAULT 1 REFERENCES consultorios(id),
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
    firmado_en TEXT NOT NULL,
    borrador_json TEXT,            -- lo que propuso la IA antes de que el médico corrigiera
    medico_id INTEGER REFERENCES medicos(id),
    segundos_ia REAL,              -- cuánto tardó Ceni en armar el borrador
    segundos_revision REAL         -- cuánto tardó el médico en revisar y firmar
);
CREATE TABLE IF NOT EXISTS citas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paciente_id INTEGER NOT NULL REFERENCES pacientes(id),
    fecha TEXT NOT NULL,
    hora TEXT NOT NULL,
    tipo TEXT NOT NULL,            -- Primera vez / Control
    estado TEXT NOT NULL DEFAULT 'Programada',
    medico_id INTEGER NOT NULL DEFAULT 1   -- de quién es la cita (ver "medicos" en la semilla)
);
CREATE TABLE IF NOT EXISTS transcripciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paciente_id INTEGER NOT NULL REFERENCES pacientes(id),
    creada_en TEXT NOT NULL
);
"""

CAMPOS_PACIENTE = ["consultorio_id", "nombre", "fecha_nacimiento", "sexo", "apoderado", "distrito", "colegio", "seguro"]
CAMPOS_MEDICO = ["consultorio_id", "nombre", "especialidad", "colegiatura", "plantilla_id"]


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
    for c in semilla["consultorios"]:
        con.execute("INSERT INTO consultorios (id, nombre, distrito) VALUES (?, ?, ?)", (c["id"], c["nombre"], c["distrito"]))
    for pl in semilla["plantillas"]:
        datos = Plantilla.model_validate(pl)  # la semilla pasa por los mismos esquemas
        con.execute("INSERT INTO plantillas (id, plantilla_json) VALUES (?, ?)", (pl["id"], datos.model_dump_json()))
    for m in semilla["medicos"]:
        con.execute(
            f"INSERT INTO medicos (id, {', '.join(CAMPOS_MEDICO)}) VALUES (?, {', '.join('?' * len(CAMPOS_MEDICO))})",
            (m["id"], *[m[c] for c in CAMPOS_MEDICO]),
        )
    medico = semilla["medicos"][0]  # las atenciones previas son de la neuropediatra
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
                """INSERT INTO atenciones (paciente_id, fecha, nota_json, receta_json, consentimiento_en, firmado_por,
                                          firmado_en, medico_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (p["id"], a["fecha"], nota.model_dump_json(), _receta_json(receta), hora, medico["nombre"], hora, medico["id"]),
            )
    hoy = date.today()
    for c in semilla["citas"]:  # relativas a hoy, para que la agenda del demo nunca esté vacía
        con.execute(
            "INSERT INTO citas (paciente_id, fecha, hora, tipo, medico_id) VALUES (?, ?, ?, ?, ?)",
            (c["paciente_id"], (hoy + timedelta(days=c["en_dias"])).isoformat(), c["hora"], c["tipo"], c["medico_id"]),
        )


def admin() -> dict:
    """Quien administra Ceni: da de alta consultorios, médicos y plantillas."""
    return _semilla()["admin"]


# --- Consultorios, plantillas y médicos ---------------------------------------------

def consultorios() -> list[dict]:
    """Los consultorios, con cuántos médicos y pacientes tiene cada uno."""
    with conectar() as con:
        filas = con.execute(
            """SELECT c.*,
                      (SELECT COUNT(*) FROM medicos m WHERE m.consultorio_id = c.id) AS n_medicos,
                      (SELECT COUNT(*) FROM pacientes p WHERE p.consultorio_id = c.id) AS n_pacientes
               FROM consultorios c ORDER BY c.id"""
        ).fetchall()
    return [dict(f) for f in filas]


def crear_consultorio(nombre: str, distrito: str) -> int:
    with conectar() as con:
        return con.execute("INSERT INTO consultorios (nombre, distrito) VALUES (?, ?)", (nombre, distrito)).lastrowid


def plantillas() -> list[tuple[int, Plantilla]]:
    with conectar() as con:
        filas = con.execute("SELECT * FROM plantillas ORDER BY id").fetchall()
    return [(f["id"], Plantilla.model_validate_json(f["plantilla_json"])) for f in filas]


def crear_plantilla(plantilla: Plantilla) -> int:
    with conectar() as con:
        return con.execute("INSERT INTO plantillas (plantilla_json) VALUES (?)", (plantilla.model_dump_json(),)).lastrowid


def _con_plantilla(fila: dict) -> dict:
    """Agrega al médico su plantilla (o None) y el vocabulario para la transcripción."""
    texto = fila.pop("plantilla_json", None)
    fila["plantilla"] = Plantilla.model_validate_json(texto) if texto else None
    fila["vocabulario"] = fila["plantilla"].vocabulario if fila["plantilla"] else ""
    return fila


def medicos(consultorio_id: int | None = None) -> list[dict]:
    """Los médicos, con su consultorio y su plantilla. Si se da un consultorio, solo los de ese."""
    with conectar() as con:
        filas = con.execute(
            """SELECT m.*, c.nombre AS consultorio, pl.plantilla_json
               FROM medicos m JOIN consultorios c ON c.id = m.consultorio_id
               LEFT JOIN plantillas pl ON pl.id = m.plantilla_id
               WHERE ? IS NULL OR m.consultorio_id = ? ORDER BY m.consultorio_id, m.id""",
            (consultorio_id, consultorio_id),
        ).fetchall()
    return [_con_plantilla(dict(f)) for f in filas]


def medico(medico_id: int = 1) -> dict:
    """Un médico por su id. Si no existe, el primero."""
    todos = medicos()
    return next((m for m in todos if m["id"] == medico_id), todos[0])


def crear_medico(datos: dict) -> int:
    with conectar() as con:
        return con.execute(
            f"INSERT INTO medicos ({', '.join(CAMPOS_MEDICO)}) VALUES ({', '.join('?' * len(CAMPOS_MEDICO))})",
            [datos[c] for c in CAMPOS_MEDICO],
        ).lastrowid


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

def listar_pacientes(consultorio_id: int, buscar: str = "") -> list[dict]:
    """Los pacientes de un consultorio: un consultorio nunca ve los pacientes de otro."""
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
            WHERE p.consultorio_id = ? AND p.nombre LIKE ?
            GROUP BY p.id ORDER BY p.nombre
            """,
            (consultorio_id, f"%{buscar.strip()}%"),
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
    """Registra un paciente nuevo (datos incluye su consultorio_id) con la historia vacía. Devuelve su id."""
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
        a["acierto"] = _acierto_de(a.pop("borrador_json"), a["nota"], a["receta"])
        atenciones.append(a)
    return atenciones


def guardar_atencion(
    paciente_id: int, fecha: date, transcripcion: str, nota: NotaAtencion, receta: list[Medicamento],
    historia: HistoriaClinica, firmado_por: str, consentimiento_en: str | None, cita_id: int | None = None,
    proxima_cita: tuple[date, str] | None = None, medico_id: int = 1,
    borrador: tuple[NotaAtencion, list[Medicamento]] | None = None,
    segundos_ia: float | None = None, segundos_revision: float | None = None,
) -> int:
    """Guarda la atención firmada, actualiza la historia y la agenda, todo en una sola transacción.

    Devuelve el id de la atención nueva.
    """
    ahora = datetime.now().isoformat(timespec="seconds")
    with conectar() as con:
        cursor = con.execute(
            """INSERT INTO atenciones (paciente_id, cita_id, fecha, transcripcion, nota_json, receta_json,
                                       consentimiento_en, firmado_por, firmado_en, borrador_json,
                                       medico_id, segundos_ia, segundos_revision)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (paciente_id, cita_id, fecha.isoformat(), transcripcion, nota.model_dump_json(),
             _receta_json(receta), consentimiento_en, firmado_por, ahora, _borrador_json(borrador),
             medico_id, segundos_ia, segundos_revision),
        )
        con.execute(
            "UPDATE historias SET historia_json = ?, actualizada = ? WHERE paciente_id = ?",
            (historia.model_dump_json(), fecha.isoformat(), paciente_id),
        )
        if cita_id:
            con.execute("UPDATE citas SET estado = 'Atendida' WHERE id = ?", (cita_id,))
        if proxima_cita:
            con.execute(
                "INSERT INTO citas (paciente_id, fecha, hora, tipo, medico_id) VALUES (?, ?, ?, 'Control', ?)",
                (paciente_id, proxima_cita[0].isoformat(), proxima_cita[1], medico_id),
            )
    return cursor.lastrowid


def _borrador_json(borrador: tuple[NotaAtencion, list[Medicamento]] | None) -> str | None:
    if not borrador:
        return None
    nota, receta = borrador
    return json.dumps({"nota": nota.model_dump(), "receta": [m.model_dump() for m in receta]}, ensure_ascii=False)


def _acierto_de(borrador_json: str | None, nota: NotaAtencion, receta: list[Medicamento]) -> Acierto | None:
    """Cuánto acertó Ceni en esta atención. None si no tiene borrador (p. ej., las de la semilla)."""
    if not borrador_json:
        return None
    b = json.loads(borrador_json)
    return comparar(NotaAtencion.model_validate(b["nota"]), [Medicamento.model_validate(m) for m in b["receta"]],
                    nota, receta)


def metricas_medico(medico_id: int, dias: int = 30) -> dict:
    """Lo que un médico ve de su uso de Ceni en los últimos días: atenciones con IA, tiempos y acierto."""
    desde = (date.today() - timedelta(days=dias)).isoformat()
    with conectar() as con:
        filas = con.execute(
            """SELECT a.*, p.nombre FROM atenciones a JOIN pacientes p ON p.id = a.paciente_id
               WHERE a.medico_id = ? AND a.fecha >= ? AND a.borrador_json IS NOT NULL
               ORDER BY a.firmado_en DESC""",
            (medico_id, desde),
        ).fetchall()
    total = Acierto()
    detalle = []
    for f in filas:
        acierto = _acierto_de(f["borrador_json"], NotaAtencion.model_validate_json(f["nota_json"]),
                              [Medicamento.model_validate(m) for m in json.loads(f["receta_json"])])
        total.sumar(acierto)
        detalle.append({"paciente": f["nombre"], "firmado_en": f["firmado_en"], "segundos_ia": f["segundos_ia"],
                        "segundos_revision": f["segundos_revision"], "acierto": acierto})
    promedio = lambda clave: (sum(d[clave] or 0 for d in detalle) / len(detalle)) if detalle else None  # noqa: E731
    return {"atenciones": len(detalle), "acierto": total, "segundos_ia": promedio("segundos_ia"),
            "segundos_revision": promedio("segundos_revision"), "detalle": detalle}


# --- Agenda -----------------------------------------------------------------------

def citas_entre(desde: date, hasta: date, medico_id: int) -> list[dict]:
    """Citas de un profesional entre dos fechas (incluidas), con el nombre, la edad y los diagnósticos del paciente."""
    with conectar() as con:
        filas = con.execute(
            """SELECT c.*, p.nombre, p.fecha_nacimiento, h.historia_json
               FROM citas c JOIN pacientes p ON p.id = c.paciente_id JOIN historias h ON h.paciente_id = p.id
               WHERE c.fecha BETWEEN ? AND ? AND c.medico_id = ? ORDER BY c.fecha, c.hora""",
            (desde.isoformat(), hasta.isoformat(), medico_id),
        ).fetchall()
    return [_con_historia(dict(f)) for f in filas]


def obtener_cita(cita_id: int) -> dict | None:
    with conectar() as con:
        fila = con.execute("SELECT * FROM citas WHERE id = ?", (cita_id,)).fetchone()
    return dict(fila) if fila else None


def crear_cita(paciente_id: int, fecha: date, hora: str, tipo: str, medico_id: int) -> None:
    with conectar() as con:
        con.execute(
            "INSERT INTO citas (paciente_id, fecha, hora, tipo, medico_id) VALUES (?, ?, ?, ?, ?)",
            (paciente_id, fecha.isoformat(), hora, tipo, medico_id),
        )


def cambiar_estado_cita(cita_id: int, estado: str) -> None:
    with conectar() as con:
        con.execute("UPDATE citas SET estado = ? WHERE id = ?", (estado, cita_id))


def proxima_cita_de(paciente_id: int, medico_id: int) -> dict | None:
    """La próxima cita programada del paciente con este profesional, desde hoy."""
    with conectar() as con:
        fila = con.execute(
            """SELECT * FROM citas WHERE paciente_id = ? AND medico_id = ? AND estado = 'Programada' AND fecha >= ?
               ORDER BY fecha, hora LIMIT 1""",
            (paciente_id, medico_id, date.today().isoformat()),
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
