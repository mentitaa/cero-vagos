"""
Arma la imagen que sale cuando alguien comparte el enlace del sitio.

Cuando pegas el link en WhatsApp, Facebook o LinkedIn, esas apps entran a la
página, buscan una etiqueta llamada `og:image` y muestran esa imagen en la
vista previa. Sin ella el enlace sale como un recuadro de texto pelado.

El tamaño 1200x630 no es un capricho: es la proporción que esas apps esperan
(1.91:1). Si mandas otra, la recortan por donde quieran.

Se ejecuta solo cuando cambia el logo o la frase:

    python3 assets/generar-og.py

Necesita: pip install cairosvg --break-system-packages
"""
from __future__ import annotations

import re
from pathlib import Path

import cairosvg

AQUI = Path(__file__).resolve().parent

ANCHO, ALTO = 1200, 630

ROJO = "#FF1E1E"
NEGRO = "#0B0B0B"
CREMA = "#FFF3E4"
AMARILLO = "#FFD100"

# La tipografía del logo va incrustada como vectores, así que se ve igual en
# todos lados. La frase de abajo sí depende de una fuente instalada; se listan
# varias por si la primera no está.
TIPO = "Archivo Black, Lato Black, Lato Heavy, Arial Black, sans-serif"


def _cuerpo_del_logo(nombre: str) -> str:
    """Saca el contenido de un SVG del logo, sin su etiqueta <svg> exterior."""
    svg = (AQUI / nombre).read_text(encoding="utf-8")
    dentro = svg.split(">", 1)[1].rsplit("</svg>", 1)[0]
    return re.sub(r"<title>.*?</title>", "", dentro, flags=re.S).strip()


def construir() -> str:
    logo = _cuerpo_del_logo("logo-claro.svg")

    # El logo mide 850x381 en su propio sistema de coordenadas. Se escala y se
    # centra a mano porque un <svg> anidado no se porta igual en todos lados.
    logo_ancho = 672
    escala = logo_ancho / 850
    logo_x = (ANCHO - logo_ancho) / 2
    logo_y = 74

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{ANCHO}" height="{ALTO}"
     viewBox="0 0 {ANCHO} {ALTO}">

  <rect width="{ANCHO}" height="{ALTO}" fill="{NEGRO}"/>

  <!-- La misma cuadrícula tenue que tiene el fondo del sitio. -->
  <defs>
    <pattern id="cuadricula" width="44" height="44" patternUnits="userSpaceOnUse">
      <path d="M44 0H0V44" fill="none" stroke="#FFFFFF" stroke-opacity=".055" stroke-width="1"/>
    </pattern>
  </defs>
  <rect width="{ANCHO}" height="{ALTO}" fill="url(#cuadricula)"/>

  <g transform="translate({logo_x:.1f} {logo_y}) scale({escala:.5f})">
    {logo}
  </g>

  <!-- El gancho: el dato que resume el proyecto. Va en amarillo porque es lo
       que tiene que leerse primero cuando la miniatura sale del tamaño de una
       uña en el chat. -->
  <g>
    <rect x="90" y="436" width="1028" height="126" fill="{ROJO}"/>
    <rect x="80" y="426" width="1028" height="126" fill="{AMARILLO}"/>
    <text x="594" y="478" text-anchor="middle" font-family="{TIPO}"
          font-size="45" font-weight="900" fill="{NEGRO}"
          letter-spacing="-0.5">EL 75% DE LOS AVISOS DE EMPLEO</text>
    <text x="594" y="529" text-anchor="middle" font-family="{TIPO}"
          font-size="45" font-weight="900" fill="{NEGRO}"
          letter-spacing="-0.5">NO DICE CUÁNTO PAGA</text>
  </g>

  <text x="594" y="600" text-anchor="middle" font-family="{TIPO}"
        font-size="26" font-weight="900" fill="{CREMA}"
        letter-spacing="1.5">AQUÍ SOLO ENTRAN LOS QUE SÍ</text>

</svg>"""


def main() -> None:
    svg = construir()
    (AQUI / "compartir.svg").write_text(svg, encoding="utf-8")
    cairosvg.svg2png(bytestring=svg.encode("utf-8"),
                     write_to=str(AQUI / "compartir.png"),
                     output_width=ANCHO, output_height=ALTO)
    peso = (AQUI / "compartir.png").stat().st_size / 1024
    print(f"assets/compartir.png  {ANCHO}x{ALTO}  {peso:.0f} KB")
    if peso > 300:
        print("Ojo: WhatsApp se atora con imágenes de más de ~300 KB.")


if __name__ == "__main__":
    main()
