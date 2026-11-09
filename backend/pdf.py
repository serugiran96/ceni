"""Informe para la familia en PDF (fpdf2)."""

from fpdf import FPDF

from ai.esquemas import InformePadres

# Las fuentes básicas del PDF solo traen el alfabeto latino (tildes y ñ sí);
# cambiamos comillas tipográficas y guiones largos por sus versiones simples.
REEMPLAZOS = {"“": '"', "”": '"', "‘": "'", "’": "'", "—": "-", "–": "-", "…": "...", "•": "-", "→": "->"}


def _limpio(texto: str) -> str:
    for viejo, nuevo in REEMPLAZOS.items():
        texto = texto.replace(viejo, nuevo)
    return texto.encode("latin-1", "replace").decode("latin-1")


class _PDF(FPDF):
    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120)
        self.cell(0, 5, _limpio("Este informe resume el trabajo en terapia; no es un diagnóstico. Hecho con Ceni."), align="C")


def informe_a_pdf(informe: InformePadres, paciente: dict, periodo: str, objetivos: list[str]) -> bytes:
    """Arma el PDF. `objetivos` son líneas tipo 'Pedir con frases: En proceso -> Casi logrado'."""
    pdf = _PDF(format="A4")
    pdf.set_margins(20, 18, 20)
    pdf.set_auto_page_break(True, margin=20)
    pdf.add_page()

    def texto(t: str, tam: int = 11, estilo: str = "", alto: float = 6, color: int = 30):
        pdf.set_font("Helvetica", estilo, tam)
        pdf.set_text_color(color)
        pdf.multi_cell(0, alto, _limpio(t), new_x="LMARGIN", new_y="NEXT")

    def titulo(t: str):
        pdf.ln(3)
        texto(t, 12, "B", 7)

    def lista(items: list[str]):
        for i in items:
            texto(f"-  {i}")

    texto("CENI", 9, "B", 5, 120)
    texto("Informe para la familia", 20, "B", 10)
    texto(f"{paciente['nombre']} · {paciente['edad']}", 12, "B", 7)
    texto(
        f"{paciente['especialidad']} con {paciente['terapeuta']} · Sede {paciente['sede']} · {periodo}",
        10, "", 6, 90,
    )
    pdf.ln(4)

    texto(informe.saludo)
    pdf.ln(2)
    texto(informe.como_va)
    titulo("Lo que logró")
    lista(informe.logros)
    titulo("En qué seguimos trabajando")
    lista(informe.seguimos_trabajando)
    titulo("Cómo va cada objetivo")
    lista(objetivos)
    titulo("Ideas para casa")
    lista(informe.en_casa)
    pdf.ln(4)
    texto(informe.cierre)
    return bytes(pdf.output())
