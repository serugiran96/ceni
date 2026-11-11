"""Cuánto acertó Ceni: compara el borrador de la IA con lo que firmó el médico.

No usa IA. Nosotros no sabemos qué se dijo en la consulta, pero el médico sí:
lo que firma es la "respuesta correcta". Cada dato de la nota y cada
medicamento de la receta cuenta una vez:

- acertado: el médico lo dejó igual;
- corregido: lo cambió (por ejemplo, la dosis);
- borrado: Ceni lo puso y el médico lo quitó (probablemente lo inventó);
- agregado: Ceni no lo puso y el médico lo agregó (lo omitió).

Los datos que quedaron vacíos en los dos no cuentan. El resumen tampoco: es
un texto que Ceni redacta, no un dato que se dijo.
"""

from dataclasses import dataclass, field

from ai.esquemas import Medicamento, NotaAtencion

TEXTOS = {"motivo": "motivo", "tiempo_enfermedad": "tiempo de enfermedad", "proximo_control": "próximo control"}
LISTAS = {"relato": "relato", "examen": "examen", "examenes_auxiliares": "exámenes auxiliares",
          "interconsultas": "interconsultas", "indicaciones": "indicaciones"}
FUNCIONES = {"apetito": "apetito", "sed": "sed", "sueno": "sueño", "orina": "orina",
             "deposiciones": "deposiciones", "estado_de_animo": "estado de ánimo"}
SIGNOS = {"peso_kg": "peso", "talla_cm": "talla", "perimetro_cefalico_cm": "perímetro cefálico",
          "temperatura_c": "temperatura", "frecuencia_cardiaca": "frecuencia cardiaca",
          "frecuencia_respiratoria": "frecuencia respiratoria"}


@dataclass
class Acierto:
    acertados: int = 0
    corregidos: int = 0
    borrados: int = 0
    agregados: int = 0
    cambios: list[str] = field(default_factory=list)  # qué datos tocó el médico

    @property
    def total(self) -> int:
        return self.acertados + self.corregidos + self.borrados + self.agregados

    @property
    def porcentaje(self) -> float:
        return self.acertados / self.total if self.total else 0.0

    def sumar(self, otro: "Acierto") -> None:
        self.acertados += otro.acertados
        self.corregidos += otro.corregidos
        self.borrados += otro.borrados
        self.agregados += otro.agregados


def _normal(valor) -> str:
    """Para comparar sin que cuenten mayúsculas, espacios o un punto final."""
    if valor is None:
        return ""
    if isinstance(valor, float):
        return f"{valor:.1f}"
    return " ".join(str(valor).lower().split()).rstrip(".;, ")


def _comparar(resultado: Acierto, nombre: str, antes: list, despues: list) -> None:
    """Compara los datos de un campo: los iguales son aciertos; los demás se emparejan como correcciones."""
    ia = [x for x in map(_normal, antes) if x]
    firmado = [x for x in map(_normal, despues) if x]
    restantes = list(firmado)
    iguales = 0
    for dato in ia:
        if dato in restantes:
            restantes.remove(dato)
            iguales += 1
    solo_ia, solo_medico = len(ia) - iguales, len(restantes)
    corregidos = min(solo_ia, solo_medico)  # uno quitado y uno puesto en el mismo campo = una corrección
    resultado.acertados += iguales
    resultado.corregidos += corregidos
    resultado.borrados += solo_ia - corregidos
    resultado.agregados += solo_medico - corregidos
    if solo_ia or solo_medico:
        resultado.cambios.append(nombre)


def _medicamento(m: Medicamento) -> str:
    return " | ".join(_normal(v) for v in m.model_dump().values())


def comparar(nota_ia: NotaAtencion, receta_ia: list[Medicamento],
             nota: NotaAtencion, receta: list[Medicamento]) -> Acierto:
    """Cuánto del borrador de Ceni (nota_ia, receta_ia) quedó igual en lo que firmó el médico."""
    r = Acierto()
    for campo, nombre in TEXTOS.items():
        _comparar(r, nombre, [getattr(nota_ia, campo)], [getattr(nota, campo)])
    for campo, nombre in LISTAS.items():
        _comparar(r, nombre, getattr(nota_ia, campo), getattr(nota, campo))
    for campo, nombre in FUNCIONES.items():
        _comparar(r, nombre, [getattr(nota_ia.funciones_biologicas, campo)], [getattr(nota.funciones_biologicas, campo)])
    for campo, nombre in SIGNOS.items():
        _comparar(r, nombre, [getattr(nota_ia.signos_vitales, campo)], [getattr(nota.signos_vitales, campo)])
    clave = lambda d: f"{d.cie10 or d.descripcion} {d.tipo}"  # noqa: E731
    _comparar(r, "diagnósticos", [clave(d) for d in nota_ia.diagnosticos], [clave(d) for d in nota.diagnosticos])
    _comparar(r, "receta", [_medicamento(m) for m in receta_ia], [_medicamento(m) for m in receta])
    return r
