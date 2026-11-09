"""Reglas de seguridad de la receta (no usan IA: son reglas fijas y explicables).

1. Psicotrópicos: en el Perú, ciertos medicamentos se recetan en el recetario
   especial de DIGEMID (D.S. 023-2001-SA). El metilfenidato, el más usado en
   TDAH, está en la lista IIIA. Ampliar esta lista con la normativa vigente.
2. Alergias: si un medicamento de la receta coincide con una alergia
   registrada en la historia clínica, se avisa.
"""

import re

from ai.esquemas import HistoriaClinica, Medicamento

PSICOTROPICOS = {
    "metilfenidato": "lista IIIA (D.S. 023-2001-SA)",
}

SIN_ALERGIAS = {"no", "conocidas", "niega", "ninguna", "refiere", "alergias"}


def requiere_receta_especial(medicamento: str) -> str | None:
    """Devuelve la lista de psicotrópicos si el medicamento la tiene, o None."""
    nombre = medicamento.lower()
    for droga, lista in PSICOTROPICOS.items():
        if droga in nombre:
            return lista
    return None


def alertas_receta(receta: list[Medicamento], historia: HistoriaClinica) -> list[str]:
    alertas = []
    for m in receta:
        if lista := requiere_receta_especial(m.medicamento):
            alertas.append(
                f"{m.medicamento}: psicotrópico de la {lista}. Se receta en el recetario especial de DIGEMID; "
                "la receta de Ceni sirve como indicación para la familia, no para la farmacia."
            )
        for alergia in historia.alergias:
            # Primera palabra significativa de la alergia, p. ej. "Amoxicilina (ronchas)" -> "amoxicilina"
            palabras = [p for p in re.findall(r"\w+", alergia.lower()) if p not in SIN_ALERGIAS and len(p) > 3]
            if palabras and palabras[0] in m.medicamento.lower():
                alertas.append(f"{m.medicamento}: el paciente tiene registrada alergia a «{alergia}».")
    return alertas
