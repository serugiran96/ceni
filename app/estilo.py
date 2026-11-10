"""Estilo visual de Ceni: CSS y pequeños componentes HTML (etiquetas, avatares, títulos).

Los colores base están en .streamlit/config.toml. Aquí va lo que el tema de
Streamlit no cubre: degradados, tarjetas, etiquetas de colores, avatares con
iniciales, títulos con ícono, la línea de tiempo y los pasos de la consulta.

Las tarjetas son contenedores de Streamlit con `key`: Streamlit les pone la
clase CSS `st-key-<key>`, y aquí les damos estilo según cómo empieza la key:
- "tarjeta-...": tarjeta blanca.
- "heroe-...": tarjeta con el degradado de la marca y texto blanco.
- "listo-...": tarjeta verde menta (la atención quedó firmada).

Todo texto que viene de la base de datos pasa por html.escape antes de entrar al HTML.
"""

from html import escape

import streamlit as st

# Tonos: (fondo claro, texto oscuro, color vivo). El texto oscuro sobre el fondo
# claro siempre se lee bien; el color vivo es para íconos, bordes y números.
TONOS = {
    "violeta": ("#EEEBFF", "#4331D6", "#7C5CFF"),
    "coral": ("#FFE8E1", "#B33A1C", "#FF7A59"),
    "menta": ("#DCF7EC", "#087F5B", "#12B886"),
    "sol": ("#FFF3D6", "#8F5B00", "#FFB020"),
    "cielo": ("#E0F0FF", "#1864AB", "#339AF0"),
    "rosa": ("#FFE3EB", "#B4234D", "#F03E6E"),
    "gris": ("#EEEEF6", "#55536E", "#8A88A8"),
    "vidrio": ("rgba(255,255,255,.2)", "#FFFFFF", "#FFFFFF"),  # sobre el degradado
    "alerta": ("#FF5C7A", "#FFFFFF", "#FF5C7A"),  # alergias sobre el degradado
}
# Avatares: un degradado por paciente (texto blanco).
AVATARES = [
    ("#6D4CFF", "#A78BFA"), ("#FF6B4A", "#FFA26B"), ("#0CA678", "#38D9A9"),
    ("#1C7ED6", "#4DABF7"), ("#D6336C", "#F783AC"), ("#E8590C", "#FFA94D"),
]

CSS = """
<style>
:root {
  --tinta: #1D1A3A; --suave: #6B6890; --violeta: #5B47FB; --borde: #E3E0F8;
  --degradado: linear-gradient(120deg, #4F3BF5 0%, #8E4DF0 52%, #FF6F61 100%);
  --sombra: 0 1px 2px rgba(29,26,58,.04), 0 14px 34px -18px rgba(76,59,245,.28);
}
.block-container { padding-top: 2.2rem; padding-bottom: 4rem; max-width: 1240px; }
header[data-testid="stHeader"] { background: transparent; }
h1, h2, h3, h4 { color: var(--tinta); letter-spacing: -0.02em; }
.ceni-icono { font-family: "Material Symbols Rounded"; font-weight: normal; font-style: normal; line-height: 1;
  letter-spacing: normal; text-transform: none; white-space: nowrap; direction: ltr; -webkit-font-smoothing: antialiased; }

/* --- Barra lateral oscura con degradado --- */
section[data-testid="stSidebar"] { background: linear-gradient(180deg, #1E1258 0%, #2D1A8C 55%, #5B47FB 130%); }
section[data-testid="stSidebar"] > div { padding-top: .6rem; }
section[data-testid="stSidebar"] [data-testid="stPageLink"] a { border-radius: 14px; padding: .55rem .8rem; }
section[data-testid="stSidebar"] [data-testid="stPageLink"] a p { font-weight: 600; font-size: 1rem; color: #E9E5FF; }
section[data-testid="stSidebar"] [data-testid="stPageLink"] a:hover { background: rgba(255,255,255,.08); }
section[data-testid="stSidebar"] [data-testid="stPageLink"] a[aria-current="page"],
section[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"][aria-current="page"] {
  background: rgba(255,255,255,.16); box-shadow: inset 3px 0 0 #FFB020; }
section[data-testid="stSidebar"] [data-testid="stPageLink"] a[aria-current="page"] p { color: #FFFFFF; }
.ceni-medico { display: flex; gap: .7rem; align-items: center; background: rgba(255,255,255,.1);
  border: 1px solid rgba(255,255,255,.16); border-radius: 18px; padding: .75rem .85rem; }
.ceni-medico .ceni-nombre { color: #FFFFFF; }
.ceni-medico .ceni-meta { color: #CFC8FF; }
.ceni-lema { color: #CFC8FF; font-size: .8rem; line-height: 1.45; margin: .3rem .2rem 0; }

/* --- Tarjetas --- */
div[class*="st-key-tarjeta"] {
  background: #FFFFFF; border: 1px solid var(--borde); border-radius: 22px;
  padding: 1.15rem 1.35rem; box-shadow: var(--sombra);
}
div[class*="st-key-tarjeta"][class*="-apagada"] { background: #FBFAFF; box-shadow: none; }
div[class*="st-key-tarjeta"][class*="-apagada"] .ceni-persona { opacity: .6; }
div[class*="st-key-tarjeta-cita"] { transition: transform .15s ease, box-shadow .15s ease; }
div[class*="st-key-tarjeta-cita"]:hover { transform: translateY(-2px); box-shadow: 0 18px 38px -20px rgba(76,59,245,.45); }

/* Héroe: el degradado de la marca, con dos círculos de luz */
div[class*="st-key-heroe"] {
  background: radial-gradient(circle at 96% 0%, rgba(255,255,255,.22) 0 110px, transparent 111px),
              radial-gradient(circle at 78% 135%, rgba(255,255,255,.14) 0 150px, transparent 151px),
              var(--degradado);
  border-radius: 28px; padding: 1.5rem 1.7rem; color: #FFFFFF;
  box-shadow: 0 24px 48px -24px rgba(91,71,251,.75);
}
div[class*="st-key-heroe"] .ceni-nombre, div[class*="st-key-heroe"] .ceni-texto,
div[class*="st-key-heroe"] .ceni-lista, div[class*="st-key-heroe"] .ceni-titulo { color: #FFFFFF; }
div[class*="st-key-heroe"] .ceni-meta, div[class*="st-key-heroe"] .ceni-etiqueta,
div[class*="st-key-heroe"] .ceni-vacio { color: rgba(255,255,255,.82); }
div[class*="st-key-heroe"] label p { color: rgba(255,255,255,.9); }
div[class*="st-key-heroe"] .ceni-avatar { box-shadow: 0 0 0 4px rgba(255,255,255,.35); }
div[class*="st-key-heroe"] .ceni-panel { background: rgba(255,255,255,.14); border: 1px solid rgba(255,255,255,.22); }
div[class*="st-key-heroe"] .ceni-item .ceni-icono { color: #FFFFFF !important; opacity: .95; }
div[class*="st-key-heroe"] .ceni-chip { white-space: normal; }
div[class*="st-key-heroe"] button[data-testid="stBaseButton-primary"] {
  background: #FFFFFF; color: #4331D6; border: none; box-shadow: 0 10px 24px -10px rgba(20,10,80,.6); }
div[class*="st-key-heroe"] button[data-testid="stBaseButton-primary"] p { color: #4331D6; font-weight: 800; }
div[class*="st-key-heroe"] button[data-testid="stBaseButton-secondary"] {
  background: rgba(255,255,255,.14); color: #FFFFFF; border-color: rgba(255,255,255,.4); }
div[class*="st-key-heroe"] button[data-testid="stBaseButton-tertiary"] p { color: #FFFFFF; }
div[class*="st-key-heroe"] [data-testid="stPopover"] button { background: rgba(255,255,255,.16); border: 1px solid rgba(255,255,255,.55); }
div[class*="st-key-heroe"] [data-testid="stPopover"] button p,
div[class*="st-key-heroe"] [data-testid="stPopover"] button span { color: #FFFFFF; }

/* Listo: la atención quedó firmada */
div[class*="st-key-listo"] {
  background: radial-gradient(circle at 97% 0%, rgba(255,255,255,.3) 0 100px, transparent 101px),
              linear-gradient(120deg, #0CA678 0%, #20C997 55%, #4DABF7 100%);
  border-radius: 28px; padding: 1.4rem 1.7rem; box-shadow: 0 24px 48px -24px rgba(12,166,120,.7);
}
div[class*="st-key-listo"] .ceni-titulo, div[class*="st-key-listo"] .ceni-texto { color: #FFFFFF; }
div[class*="st-key-listo"] .ceni-meta { color: rgba(255,255,255,.9); }
div[class*="st-key-listo"] button[data-testid^="stBaseButton-primary"] { background: #FFFFFF; border: none; }
div[class*="st-key-listo"] button[data-testid^="stBaseButton-primary"] p { color: #087F5B; font-weight: 800; }
div[class*="st-key-listo"] button[data-testid="stBaseButton-secondary"] {
  background: rgba(255,255,255,.16); border-color: rgba(255,255,255,.55); }
div[class*="st-key-listo"] button[data-testid="stBaseButton-secondary"] p { color: #FFFFFF; }

/* Panel translúcido o suave dentro de una tarjeta */
.ceni-panel { background: #F7F6FF; border: 1px solid var(--borde); border-radius: 18px; padding: .85rem 1rem; }

/* --- Botones: el principal con el degradado --- */
button[data-testid^="stBaseButton-primary"] {
  background: var(--degradado); border: none; box-shadow: 0 10px 22px -12px rgba(91,71,251,.9);
  transition: transform .12s ease, box-shadow .12s ease;
}
button[data-testid^="stBaseButton-primary"] p { font-weight: 700; }
button[data-testid^="stBaseButton-primary"]:hover { transform: translateY(-1px); box-shadow: 0 14px 26px -12px rgba(91,71,251,.95); }
div[class*="st-key-grande"] button, div[class*="st-key-procesar"] button { min-height: 3.1rem; padding: 0 1.4rem; }
div[class*="st-key-grande"] button p, div[class*="st-key-procesar"] button p { font-size: 1.06rem; }

/* --- Etiquetas --- */
.ceni-chips { display: flex; flex-wrap: wrap; gap: .35rem; margin: .2rem 0; }
.ceni-chip {
  display: inline-block; padding: .18rem .66rem; border-radius: 999px; font-size: .78rem; font-weight: 700;
  line-height: 1.55; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%;
}
.ceni-chip b { font-weight: 800; }

/* --- Persona (avatar + nombre + datos) --- */
.ceni-persona { display: flex; gap: .9rem; align-items: center; }
.ceni-avatar {
  width: 48px; height: 48px; border-radius: 16px; flex: none; display: inline-flex; color: #FFFFFF;
  align-items: center; justify-content: center; font-family: "Bricolage Grotesque", sans-serif;
  font-weight: 800; font-size: 1.05rem; letter-spacing: .02em; text-shadow: 0 1px 2px rgba(0,0,0,.15);
}
.ceni-avatar.grande { width: 84px; height: 84px; border-radius: 26px; font-size: 1.9rem; }
.ceni-nombre { font-family: "Bricolage Grotesque", sans-serif; font-weight: 700; font-size: 1.12rem; color: var(--tinta); line-height: 1.2; }
.ceni-nombre.grande { font-size: 2rem; line-height: 1.1; letter-spacing: -0.02em; }
.ceni-meta { color: var(--suave); font-size: .87rem; line-height: 1.5; }

/* --- Hora de una cita --- */
.ceni-hora {
  border-radius: 18px; padding: .55rem .3rem; text-align: center; font-family: "Bricolage Grotesque", sans-serif;
  font-weight: 800; font-size: 1.25rem; line-height: 1.1;
}
.ceni-hora small { display: block; font-family: "Plus Jakarta Sans", sans-serif; font-size: .64rem; font-weight: 800;
  text-transform: uppercase; letter-spacing: .07em; opacity: .9; margin-top: .15rem; }

/* --- Encabezado de página --- */
.ceni-encabezado { margin-bottom: .5rem; }
.ceni-encabezado .sobre { display: inline-block; color: #4331D6; background: #EEEBFF; font-weight: 800; font-size: .74rem;
  text-transform: uppercase; letter-spacing: .08em; padding: .2rem .65rem; border-radius: 999px; }
.ceni-encabezado h1 { font-family: "Bricolage Grotesque", sans-serif; font-size: 2.4rem; font-weight: 800;
  margin: .35rem 0 .15rem; padding: 0; color: var(--tinta); letter-spacing: -0.03em; }
.ceni-encabezado h1 em { font-style: normal; background: var(--degradado); -webkit-background-clip: text;
  background-clip: text; color: transparent; }
.ceni-encabezado p { color: var(--suave); margin: 0; font-size: 1rem; }

/* --- Títulos con ícono, etiquetas pequeñas y datos --- */
.ceni-titulo { display: flex; align-items: center; gap: .6rem; font-family: "Bricolage Grotesque", sans-serif;
  font-weight: 700; font-size: 1.18rem; color: var(--tinta); margin: 0 0 .7rem; }
.ceni-titulo .burbuja { width: 34px; height: 34px; border-radius: 11px; flex: none; display: inline-flex;
  align-items: center; justify-content: center; font-size: 20px; }
.ceni-titulo small { font-family: "Plus Jakarta Sans", sans-serif; font-weight: 600; font-size: .8rem; color: var(--suave); margin-left: auto; }
.ceni-etiqueta { font-size: .7rem; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; color: var(--suave); margin: 0 0 .3rem; }
.ceni-subtitulo { font-family: "Bricolage Grotesque", sans-serif; font-weight: 700; font-size: 1.15rem; color: var(--tinta); margin: 0 0 .5rem; }
.ceni-datos { display: grid; grid-template-columns: repeat(auto-fill, minmax(210px, 1fr)); gap: 1.1rem 1.6rem; }
.ceni-dato .valor { color: var(--tinta); font-size: .97rem; line-height: 1.45; font-weight: 500; }
.ceni-lista { margin: 0; padding-left: 1.05rem; color: var(--tinta); font-size: .95rem; line-height: 1.6; }
.ceni-texto { color: var(--tinta); font-size: .95rem; line-height: 1.6; margin: 0; }
.ceni-vacio { color: #9A98B5; font-size: .92rem; font-style: italic; margin: 0; }
.ceni-bloque { margin-bottom: 1rem; }
.ceni-dx { display: flex; align-items: flex-start; gap: .55rem; margin-bottom: .45rem; }
.ceni-dx .ceni-chip { flex: none; margin-top: .1rem; }

/* Lista con ícono (lo que quedó pendiente, la medicación) */
.ceni-items { display: flex; flex-direction: column; gap: .45rem; margin: 0; }
.ceni-item { display: flex; gap: .55rem; align-items: flex-start; font-size: .93rem; line-height: 1.45; }
.ceni-item .ceni-icono { font-size: 18px; margin-top: .05rem; flex: none; }

/* --- Cifras (resumen del día, signos vitales) --- */
.ceni-cifras { display: grid; grid-template-columns: repeat(auto-fit, minmax(118px, 1fr)); gap: .6rem; }
.ceni-cifra { border-radius: 18px; padding: .7rem .85rem; position: relative; overflow: hidden; }
.ceni-cifra .num { font-family: "Bricolage Grotesque", sans-serif; font-weight: 800; font-size: 1.55rem; line-height: 1.1; }
.ceni-cifra .num small { font-size: .8rem; font-weight: 600; margin-left: .15rem; }
.ceni-cifra .que { font-size: .74rem; font-weight: 700; opacity: .9; }
.ceni-cifra::after { content: ""; position: absolute; right: -14px; top: -14px; width: 46px; height: 46px;
  border-radius: 50%; background: currentColor; opacity: .08; }

/* --- Línea de tiempo (evolución) --- */
.ceni-linea { border-left: 3px solid #E3E0F8; margin: .3rem 0 0 .45rem; padding-left: 1.25rem; }
.ceni-hito { position: relative; padding-bottom: 1.05rem; }
.ceni-hito::before { content: ""; position: absolute; left: -1.83rem; top: .2rem; width: 14px; height: 14px;
  border-radius: 50%; background: var(--degradado); box-shadow: 0 0 0 4px #EEEBFF; }
.ceni-hito .fecha { font-size: .72rem; font-weight: 800; color: #4331D6; text-transform: uppercase; letter-spacing: .06em; }

/* --- Pasos de la consulta --- */
.ceni-pasos { display: flex; gap: .5rem; flex-wrap: wrap; margin: .1rem 0 .8rem; }
.ceni-paso { display: flex; align-items: center; gap: .5rem; padding: .35rem .95rem .35rem .4rem; border-radius: 999px;
  background: #FFFFFF; border: 1px solid var(--borde); color: var(--suave); font-size: .86rem; font-weight: 700; }
.ceni-paso span { width: 24px; height: 24px; border-radius: 50%; background: #EEEEF6; display: inline-flex;
  align-items: center; justify-content: center; font-size: .76rem; font-weight: 800; }
.ceni-paso.activo { background: var(--degradado); color: #FFFFFF; border-color: transparent;
  box-shadow: 0 10px 22px -12px rgba(91,71,251,.9); }
.ceni-paso.activo span { background: #FFFFFF; color: #4331D6; }
.ceni-paso.hecho { background: #DCF7EC; color: #087F5B; border-color: #B7EBD6; }
.ceni-paso.hecho span { background: #12B886; color: #FFFFFF; }

/* --- Secciones del formulario de revisión --- */
.ceni-seccion { display: flex; align-items: center; gap: .65rem; font-family: "Bricolage Grotesque", sans-serif; font-weight: 700;
  font-size: 1.12rem; color: var(--tinta); margin: 1.2rem 0 .15rem; padding-top: 1rem; border-top: 1px dashed var(--borde); }
.ceni-seccion span { width: 30px; height: 30px; border-radius: 10px; flex: none; color: #FFFFFF;
  display: inline-flex; align-items: center; justify-content: center; font-size: .88rem; font-weight: 800; }
.ceni-seccion small { font-family: "Plus Jakarta Sans", sans-serif; font-weight: 600; font-size: .8rem; color: var(--suave); }

/* --- Pestañas tipo píldora, expansores, formularios y grabadora --- */
[data-testid="stTabs"] [role="tablist"] { gap: .35rem; background: #FFFFFF; border: 1px solid var(--borde); padding: .35rem;
  border-radius: 999px; width: fit-content; max-width: 100%; box-shadow: var(--sombra); margin-bottom: .6rem; }
[data-testid="stTab"] { padding: .5rem 1.15rem; border-radius: 999px; height: auto; transition: background .15s ease; }
[data-testid="stTab"] p { font-family: "Bricolage Grotesque", sans-serif; font-weight: 700; font-size: 1rem; color: var(--suave); }
[data-testid="stTab"]:hover { background: #F3F1FF; }
[data-testid="stTab"][aria-selected="true"] { background: var(--degradado); box-shadow: 0 8px 18px -10px rgba(91,71,251,.9); }
[data-testid="stTab"][aria-selected="true"] p { color: #FFFFFF; }
[data-testid="stTabs"] .react-aria-SelectionIndicator { display: none; }
[data-testid="stExpander"] details { background: #FFFFFF; border-radius: 20px; border-color: var(--borde); box-shadow: var(--sombra); }
[data-testid="stExpander"] summary p { font-family: "Bricolage Grotesque", sans-serif; font-weight: 700; font-size: 1.04rem; }
[data-testid="stForm"] { background: #FFFFFF; border-color: var(--borde); border-radius: 24px; box-shadow: var(--sombra); padding: 1.4rem 1.6rem; }
[data-testid="stAudioInput"] > div { border-radius: 20px; border: 2px dashed #C9C0FF; background: #FAF9FF; min-height: 4.2rem; }
[data-testid="stAlert"] > div { border-radius: 16px; }
</style>
"""


def aplicar() -> None:
    """Inyecta el CSS de Ceni (st.html con solo <style> no ocupa espacio)."""
    st.html(CSS)


def html(contenido: str) -> None:
    st.html(contenido)


def icono(nombre: str, color: str = "") -> str:
    """Un ícono de Material Symbols (los mismos que usa Streamlit), p. ej. 'mic' o 'medication'."""
    estilo = f' style="color:{color}"' if color else ""
    return f'<span class="ceni-icono"{estilo}>{escape(nombre)}</span>'


def tono_css(nombre: str) -> str:
    """El estilo CSS (fondo claro y texto oscuro) de un tono."""
    fondo, texto, _ = TONOS[nombre]
    return f"background:{fondo};color:{texto};"


def chip(texto: str, tono: str = "violeta", titulo: str = "", crudo: bool = False) -> str:
    """Una etiqueta de color. `crudo=True` si el texto ya es HTML seguro."""
    contenido = texto if crudo else escape(texto)
    title = f' title="{escape(titulo)}"' if titulo else ""
    return f'<span class="ceni-chip" style="{tono_css(tono)}"{title}>{contenido}</span>'


def chips(lista: list[str]) -> str:
    return f'<div class="ceni-chips">{"".join(lista)}</div>' if lista else ""


def iniciales(nombre: str) -> str:
    partes = nombre.split()
    return (partes[0][0] + (partes[1][0] if len(partes) > 1 else "")).upper()


def avatar(nombre: str, paciente_id: int, grande: bool = False) -> str:
    """Cuadro redondeado con las iniciales; cada paciente tiene su degradado."""
    desde, hasta = AVATARES[(paciente_id - 1) % len(AVATARES)]
    clase = "ceni-avatar grande" if grande else "ceni-avatar"
    return (f'<div class="{clase}" style="background:linear-gradient(135deg,{desde},{hasta})">'
            f"{escape(iniciales(nombre))}</div>")


def persona(nombre: str, paciente_id: int, meta: str, extra: str = "", grande: bool = False) -> str:
    """Avatar + nombre + una línea de datos (+ HTML extra debajo, p. ej. etiquetas)."""
    clase = "ceni-nombre grande" if grande else "ceni-nombre"
    return (
        f'<div class="ceni-persona">{avatar(nombre, paciente_id, grande)}<div style="min-width:0">'
        f'<div class="{clase}">{escape(nombre)}</div><div class="ceni-meta">{escape(meta)}</div>{extra}</div></div>'
    )


def encabezado(titulo: str, subtitulo: str = "", sobretitulo: str = "", resaltado: str = "") -> None:
    """Título de página. `resaltado` se agrega al título con el degradado de la marca."""
    extra = f" <em>{escape(resaltado)}</em>" if resaltado else ""
    html(
        '<div class="ceni-encabezado">'
        + (f'<div class="sobre">{escape(sobretitulo)}</div>' if sobretitulo else "")
        + f"<h1>{escape(titulo)}{extra}</h1>"
        + (f"<p>{escape(subtitulo)}</p>" if subtitulo else "")
        + "</div>"
    )


def titulo(texto: str, nombre_icono: str, tono: str = "violeta", detalle: str = "") -> str:
    """Título de tarjeta con un ícono en una burbuja de color."""
    fondo, color, _ = TONOS[tono]
    return (
        f'<div class="ceni-titulo"><span class="burbuja" style="background:{fondo}">{icono(nombre_icono, color)}</span>'
        f"{escape(texto)}" + (f"<small>{escape(detalle)}</small>" if detalle else "") + "</div>"
    )


def seccion(numero: int, texto: str, ayuda: str = "", tono: str = "violeta") -> None:
    """Título numerado de una sección del formulario de revisión."""
    primera = ' style="border-top:none;margin-top:0;padding-top:0"' if numero == 1 else ""
    html(
        f'<div class="ceni-seccion"{primera}><span style="background:{TONOS[tono][2]}">{numero}</span>{escape(texto)}'
        + (f"<small>· {escape(ayuda)}</small>" if ayuda else "")
        + "</div>"
    )


def etiqueta(texto: str) -> str:
    return f'<div class="ceni-etiqueta">{escape(texto)}</div>'


def lista(items: list[str], vacio: str = "Sin registro") -> str:
    if not items:
        return f'<p class="ceni-vacio">{escape(vacio)}</p>'
    return '<ul class="ceni-lista">' + "".join(f"<li>{escape(i)}</li>" for i in items) + "</ul>"


def items(filas: list[tuple[str, str, str]], vacio: str = "Nada pendiente") -> str:
    """Lista con un ícono de color por fila: (ícono, tono, texto)."""
    if not filas:
        return f'<p class="ceni-vacio">{escape(vacio)}</p>'
    return '<div class="ceni-items">' + "".join(
        f'<div class="ceni-item">{icono(nombre, TONOS[tono][2])}<span>{escape(texto)}</span></div>'
        for nombre, tono, texto in filas
    ) + "</div>"


def texto(valor: str, vacio: str = "Sin registro") -> str:
    return f'<p class="ceni-texto">{escape(valor)}</p>' if valor else f'<p class="ceni-vacio">{escape(vacio)}</p>'


def bloque(titulo_bloque: str, contenido: str) -> str:
    """Etiqueta pequeña + contenido (lista o texto)."""
    return f'<div class="ceni-bloque">{etiqueta(titulo_bloque)}{contenido}</div>'


def cifras(filas: list[tuple[str, str, str, str]]) -> str:
    """Fichas con un número grande: (número, unidad, qué es, tono)."""
    return '<div class="ceni-cifras">' + "".join(
        f'<div class="ceni-cifra" style="{tono_css(tono)}"><div class="num">{escape(num)}<small>{escape(unidad)}</small></div>'
        f'<div class="que">{escape(que)}</div></div>'
        for num, unidad, que, tono in filas
    ) + "</div>"


def pasos(nombres: list[str], actual: int) -> str:
    """Indicador de pasos: los anteriores a `actual` salen como hechos."""
    partes = []
    for i, nombre in enumerate(nombres):
        clase = "hecho" if i < actual else "activo" if i == actual else ""
        marca = "✓" if i < actual else str(i + 1)
        partes.append(f'<div class="ceni-paso {clase}"><span>{marca}</span>{escape(nombre)}</div>')
    return '<div class="ceni-pasos">' + "".join(partes) + "</div>"
