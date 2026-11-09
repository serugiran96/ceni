"""Receta en PDF (fpdf2), con los datos que exige la Ley 29459."""

from fpdf import FPDF

from ai.esquemas import Diagnostico, Medicamento
from backend.reglas import requiere_receta_especial

# Las fuentes básicas del PDF solo traen el alfabeto latino (tildes y ñ sí);
# cambiamos comillas tipográficas, guiones largos y flechas por versiones simples.
REEMPLAZOS = {"“": '"', "”": '"', "‘": "'", "’": "'", "—": "-", "–": "-", "…": "...", "•": "-", "→": "->",
              "«": '"', "»": '"'}


def _limpio(texto: str) -> str:
    for viejo, nuevo in REEMPLAZOS.items():
        texto = texto.replace(viejo, nuevo)
    return texto.encode("latin-1", "replace").decode("latin-1")


def linea_medicamento(m: Medicamento) -> str:
    """'1 tableta, vía oral, cada noche, por 1 mes.' (también se usa en la app)."""
    partes = [m.dosis]
    if m.forma_farmaceutica and m.forma_farmaceutica.lower() not in m.dosis.lower():
        partes[0] = f"{m.dosis} ({m.forma_farmaceutica.lower()})"
    if m.via:
        partes.append(f"vía {m.via.lower()}")
    partes.append(m.frecuencia[:1].lower() + m.frecuencia[1:])
    if m.duracion:
        partes.append(f"por {m.duracion}")
    return ", ".join(p for p in partes if p) + "."


class _PDF(FPDF):
    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120)
        self.cell(0, 5, _limpio("Demo de Ceni con datos inventados. No es una receta válida."), align="C")


def receta_a_pdf(
    receta: list[Medicamento], paciente: dict, medico: dict, fecha: str,
    diagnosticos: list[Diagnostico], plan: list[str], firmado_en: str,
) -> bytes:
    pdf = _PDF(format=(148, 210))  # A5 en milímetros
    pdf.set_margins(14, 12, 14)
    pdf.set_auto_page_break(True, margin=18)
    pdf.add_page()

    def texto(t: str, tam: int = 10, estilo: str = "", alto: float = 5.5, color: int = 30):
        pdf.set_font("Helvetica", estilo, tam)
        pdf.set_text_color(color)
        pdf.multi_cell(0, alto, _limpio(t), new_x="LMARGIN", new_y="NEXT", align="L")

    texto(medico["nombre"], 13, "B", 7)
    texto(f"{medico['especialidad']} · {medico['colegiatura']}", 8, "", 5, 110)
    pdf.ln(3)
    pdf.set_draw_color(200)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(3)
    texto(f"Paciente: {paciente['nombre']} · {paciente['edad']}", 10, "B")
    texto(f"Fecha: {fecha}", 9, "", 5, 90)
    if diagnosticos:
        texto("Dx: " + "; ".join(f"{d.cie10} {d.descripcion}".strip() for d in diagnosticos), 9, "", 5, 90)
    pdf.ln(3)
    texto("Rp/", 14, "B", 8)
    for i, m in enumerate(receta, start=1):
        texto(f"{i}. {m.medicamento}", 11, "B", 6)
        texto(linea_medicamento(m))
        if m.indicaciones:
            texto(m.indicaciones, 9, "I", 5, 90)
        if lista := requiere_receta_especial(m.medicamento):
            texto(f"Psicotrópico de la {lista}: se dispensa solo con el recetario especial de DIGEMID.", 8, "B", 4.5, 150)
        pdf.ln(2)
    if plan:
        pdf.ln(2)
        texto("Indicaciones", 11, "B", 6)
        for p in plan:
            texto(f"-  {p}", 9)
    pdf.ln(10)
    texto("_______________________", 10, "", 5, 120)
    texto(f"{medico['nombre']} · firmado en Ceni el {firmado_en.replace('T', ' a las ')[:-3]}", 8, "", 5, 90)
    return bytes(pdf.output())
