"""Estilo visual de Ceni: CSS y pequeños componentes HTML (etiquetas, avatares, títulos).

Los colores base están en .streamlit/config.toml. Aquí va lo que el tema de
Streamlit no cubre: tarjetas, etiquetas pastel, avatares con iniciales, la
línea de tiempo y los pasos de la consulta. Todo texto que viene de la base
de datos pasa por html.escape antes de entrar al HTML.
"""

from html import escape

import streamlit as st

# Pasteles (fondo, texto). Los tres primeros salen del logo.
TONOS = {
    "cielo": ("#DCE8F0", "#2F5568"),
    "salvia": ("#DDEEDF", "#2F6138"),
    "pizarra": ("#4F7487", "#FFFFFF"),
    "durazno": ("#FBE3D3", "#8A4A22"),
    "lavanda": ("#E6E0F4", "#54448A"),
    "mantequilla": ("#FAF0CF", "#6E520A"),
    "rosa": ("#F8DDE4", "#8C3150"),
    "gris": ("#E9EEF1", "#4F606A"),
}
TONOS_AVATAR = ["cielo", "salvia", "durazno", "lavanda", "mantequilla", "rosa"]

CSS = """
<style>
:root {
  --tinta: #263B47; --suave: #5E7380; --pizarra: #4F7487; --borde: #DCE6EC;
  --sombra: 0 1px 2px rgba(38,59,71,.04), 0 10px 28px -16px rgba(38,59,71,.18);
}
.block-container { padding-top: 2.4rem; padding-bottom: 4rem; max-width: 1200px; }
header[data-testid="stHeader"] { background: transparent; }
h1, h2, h3, h4 { color: var(--tinta); letter-spacing: -0.01em; }

/* Tarjetas: contenedores con key que empieza con "tarjeta" */
div[class*="st-key-tarjeta"] {
  background: #FFFFFF; border: 1px solid var(--borde); border-radius: 20px;
  padding: 1.1rem 1.3rem; box-shadow: var(--sombra);
}
div[class*="st-key-tarjeta"][class*="-apagada"] { background: #FBFCFD; box-shadow: none; }
div[class*="st-key-tarjeta"][class*="-apagada"] .ceni-persona { opacity: .7; }

/* Etiquetas pastel */
.ceni-chips { display: flex; flex-wrap: wrap; gap: .35rem; margin: .15rem 0; }
.ceni-chip {
  display: inline-block; padding: .16rem .62rem; border-radius: 999px; font-size: .78rem; font-weight: 600;
  line-height: 1.55; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%;
}
.ceni-chip b { font-weight: 800; }

/* Persona (avatar + nombre + datos) */
.ceni-persona { display: flex; gap: .85rem; align-items: center; }
.ceni-avatar {
  width: 46px; height: 46px; border-radius: 50%; flex: none; display: inline-flex;
  align-items: center; justify-content: center; font-family: Outfit, sans-serif;
  font-weight: 600; font-size: 1.02rem; letter-spacing: .02em;
}
.ceni-avatar.grande { width: 76px; height: 76px; font-size: 1.7rem; }
.ceni-nombre { font-family: Outfit, sans-serif; font-weight: 600; font-size: 1.06rem; color: var(--tinta); line-height: 1.25; }
.ceni-nombre.grande { font-size: 1.75rem; line-height: 1.15; }
.ceni-meta { color: var(--suave); font-size: .86rem; line-height: 1.45; }

/* Hora de una cita */
.ceni-hora {
  border-radius: 16px; padding: .5rem .3rem; text-align: center; font-family: Outfit, sans-serif;
  font-weight: 600; font-size: 1.2rem; line-height: 1.15;
}
.ceni-hora small { display: block; font-family: Figtree, sans-serif; font-size: .66rem; font-weight: 700;
  text-transform: uppercase; letter-spacing: .06em; opacity: .85; }

/* Encabezado de página */
.ceni-encabezado { margin-bottom: .4rem; }
.ceni-encabezado .sobre { color: var(--pizarra); font-weight: 700; font-size: .8rem; text-transform: uppercase; letter-spacing: .08em; }
.ceni-encabezado h1 { font-family: Outfit, sans-serif; font-size: 2.1rem; font-weight: 700; margin: .1rem 0 .15rem; padding: 0; color: var(--tinta); }
.ceni-encabezado p { color: var(--suave); margin: 0; font-size: .98rem; }

/* Títulos pequeños y datos */
.ceni-etiqueta { font-size: .7rem; font-weight: 700; letter-spacing: .07em; text-transform: uppercase; color: var(--suave); margin: 0 0 .3rem; }
.ceni-subtitulo { font-family: Outfit, sans-serif; font-weight: 600; font-size: 1.12rem; color: var(--tinta); margin: 0 0 .5rem; }
.ceni-datos { display: grid; grid-template-columns: repeat(auto-fill, minmax(210px, 1fr)); gap: 1.1rem 1.6rem; }
.ceni-dato .valor { color: var(--tinta); font-size: .97rem; line-height: 1.45; }
.ceni-lista { margin: 0; padding-left: 1.05rem; color: var(--tinta); font-size: .95rem; line-height: 1.55; }
.ceni-texto { color: var(--tinta); font-size: .95rem; line-height: 1.55; margin: 0; }
.ceni-vacio { color: #8A9AA3; font-size: .92rem; font-style: italic; margin: 0; }
.ceni-bloque { margin-bottom: 1rem; }
.ceni-dx { display: flex; align-items: baseline; gap: .45rem; flex-wrap: wrap; margin-bottom: .35rem; }
.ceni-dx .ceni-chip { flex: none; }

/* Cifras (signos vitales, resumen del día) */
.ceni-cifras { display: grid; grid-template-columns: repeat(auto-fill, minmax(112px, 1fr)); gap: .5rem; }
.ceni-cifra { border-radius: 14px; padding: .55rem .75rem; }
.ceni-cifra .num { font-family: Outfit, sans-serif; font-weight: 600; font-size: 1.3rem; line-height: 1.2; }
.ceni-cifra .num small { font-size: .78rem; font-weight: 500; margin-left: .1rem; }
.ceni-cifra .que { font-size: .72rem; font-weight: 600; opacity: .85; }

/* Línea de tiempo (evolución) */
.ceni-linea { border-left: 2px solid var(--borde); margin: .3rem 0 0 .35rem; padding-left: 1.15rem; }
.ceni-hito { position: relative; padding-bottom: 1rem; }
.ceni-hito::before { content: ""; position: absolute; left: -1.62rem; top: .3rem; width: 12px; height: 12px;
  border-radius: 50%; background: #DDEEDF; border: 2px solid #5E9A68; }
.ceni-hito .fecha { font-size: .72rem; font-weight: 700; color: var(--suave); text-transform: uppercase; letter-spacing: .05em; }

/* Pasos de la consulta */
.ceni-pasos { display: flex; gap: .45rem; flex-wrap: wrap; margin: .1rem 0 .6rem; }
.ceni-paso { display: flex; align-items: center; gap: .45rem; padding: .3rem .85rem .3rem .35rem; border-radius: 999px;
  background: #F1F5F7; color: var(--suave); font-size: .84rem; font-weight: 600; }
.ceni-paso span { width: 22px; height: 22px; border-radius: 50%; background: #FFFFFF; display: inline-flex;
  align-items: center; justify-content: center; font-size: .74rem; font-weight: 700; }
.ceni-paso.activo { background: #DCE8F0; color: #2F5568; }
.ceni-paso.hecho { background: #DDEEDF; color: #2F6138; }

/* Secciones del formulario de revisión */
.ceni-seccion { display: flex; align-items: center; gap: .6rem; font-family: Outfit, sans-serif; font-weight: 600;
  font-size: 1.08rem; color: var(--tinta); margin: 1.1rem 0 .1rem; padding-top: .9rem; border-top: 1px solid var(--borde); }
.ceni-seccion span { width: 28px; height: 28px; border-radius: 50%; background: #DCE8F0; color: #2F5568; flex: none;
  display: inline-flex; align-items: center; justify-content: center; font-size: .85rem; }
.ceni-seccion small { font-family: Figtree, sans-serif; font-weight: 500; font-size: .82rem; color: var(--suave); }

/* Barra lateral */
section[data-testid="stSidebar"] .block-container, section[data-testid="stSidebar"] > div { padding-top: 1rem; }
section[data-testid="stSidebar"] [data-testid="stPageLink"] a { border-radius: 12px; padding: .45rem .7rem; }
section[data-testid="stSidebar"] [data-testid="stPageLink"] a p { font-weight: 600; font-size: 1rem; }
.ceni-medico { display: flex; gap: .65rem; align-items: center; background: #FFFFFF; border: 1px solid #D3E0E8;
  border-radius: 16px; padding: .7rem .8rem; }

/* Pestañas, expansores y formularios */
.stTabs [data-baseweb="tab"] { font-family: Outfit, sans-serif; font-weight: 600; font-size: 1.02rem; }
[data-testid="stExpander"] details { background: #FFFFFF; border-radius: 18px; border-color: var(--borde); }
[data-testid="stExpander"] summary p { font-family: Outfit, sans-serif; font-weight: 600; font-size: 1.02rem; }
[data-testid="stForm"] { background: #FFFFFF; border-color: var(--borde); border-radius: 20px; }
[data-testid="stAudioInput"] > div { border-radius: 18px; }
</style>
"""


def aplicar() -> None:
    """Inyecta el CSS de Ceni (st.html con solo <style> no ocupa espacio)."""
    st.html(CSS)


def html(contenido: str) -> None:
    st.html(contenido)


def tono_css(nombre: str) -> str:
    """El estilo CSS (fondo y color de texto) de un tono pastel."""
    fondo, texto = TONOS[nombre]
    return f"background:{fondo};color:{texto};"


def chip(texto: str, tono: str = "cielo", titulo: str = "", crudo: bool = False) -> str:
    """Una etiqueta pastel. `crudo=True` si el texto ya es HTML seguro."""
    contenido = texto if crudo else escape(texto)
    title = f' title="{escape(titulo)}"' if titulo else ""
    return f'<span class="ceni-chip" style="{tono_css(tono)}"{title}>{contenido}</span>'


def chips(lista: list[str]) -> str:
    return f'<div class="ceni-chips">{"".join(lista)}</div>' if lista else ""


def iniciales(nombre: str) -> str:
    partes = nombre.split()
    return (partes[0][0] + (partes[1][0] if len(partes) > 1 else "")).upper()


def avatar(nombre: str, paciente_id: int, grande: bool = False) -> str:
    tono = TONOS_AVATAR[(paciente_id - 1) % len(TONOS_AVATAR)]
    clase = "ceni-avatar grande" if grande else "ceni-avatar"
    return f'<div class="{clase}" style="{tono_css(tono)}">{escape(iniciales(nombre))}</div>'


def persona(nombre: str, paciente_id: int, meta: str, extra: str = "", grande: bool = False) -> str:
    """Avatar + nombre + una línea de datos (+ HTML extra debajo, p. ej. etiquetas)."""
    clase = "ceni-nombre grande" if grande else "ceni-nombre"
    return (
        f'<div class="ceni-persona">{avatar(nombre, paciente_id, grande)}<div>'
        f'<div class="{clase}">{escape(nombre)}</div><div class="ceni-meta">{escape(meta)}</div>{extra}</div></div>'
    )


def encabezado(titulo: str, subtitulo: str = "", sobretitulo: str = "") -> None:
    html(
        '<div class="ceni-encabezado">'
        + (f'<div class="sobre">{escape(sobretitulo)}</div>' if sobretitulo else "")
        + f"<h1>{escape(titulo)}</h1>"
        + (f"<p>{escape(subtitulo)}</p>" if subtitulo else "")
        + "</div>"
    )


def seccion(numero: int, titulo: str, ayuda: str = "") -> None:
    """Título numerado de una sección del formulario de revisión."""
    html(
        f'<div class="ceni-seccion"><span>{numero}</span>{escape(titulo)}'
        + (f"<small>· {escape(ayuda)}</small>" if ayuda else "")
        + "</div>"
    )


def etiqueta(texto: str) -> str:
    return f'<div class="ceni-etiqueta">{escape(texto)}</div>'


def lista(items: list[str], vacio: str = "Sin registro") -> str:
    if not items:
        return f'<p class="ceni-vacio">{escape(vacio)}</p>'
    return '<ul class="ceni-lista">' + "".join(f"<li>{escape(i)}</li>" for i in items) + "</ul>"


def texto(valor: str, vacio: str = "Sin registro") -> str:
    return f'<p class="ceni-texto">{escape(valor)}</p>' if valor else f'<p class="ceni-vacio">{escape(vacio)}</p>'


def bloque(titulo: str, contenido: str) -> str:
    """Etiqueta pequeña + contenido (lista o texto)."""
    return f'<div class="ceni-bloque">{etiqueta(titulo)}{contenido}</div>'


def cifras(items: list[tuple[str, str, str, str]]) -> str:
    """Fichas con un número grande: (número, unidad, qué es, tono)."""
    return '<div class="ceni-cifras">' + "".join(
        f'<div class="ceni-cifra" style="{tono_css(tono)}"><div class="num">{escape(num)}<small>{escape(unidad)}</small></div>'
        f'<div class="que">{escape(que)}</div></div>'
        for num, unidad, que, tono in items
    ) + "</div>"


def pasos(nombres: list[str], actual: int) -> str:
    """Indicador de pasos: los anteriores a `actual` salen como hechos."""
    partes = []
    for i, nombre in enumerate(nombres):
        clase = "hecho" if i < actual else "activo" if i == actual else ""
        marca = "✓" if i < actual else str(i + 1)
        partes.append(f'<div class="ceni-paso {clase}"><span>{marca}</span>{escape(nombre)}</div>')
    return '<div class="ceni-pasos">' + "".join(partes) + "</div>"
