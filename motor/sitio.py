"""
Generador del sitio: una página propia para cada oferta.

Por qué existe esto: hasta ahora Cero Vagos era UNA sola página. Al hacer clic
en una oferta se abría una ventana encima, pero la dirección del navegador no
cambiaba. Para Google eso es una página, no cuarenta ofertas — y nadie que
busque "trabajo asistente contable Cusco sueldo" podía llegar.

Cada oferta pasa a tener:
  · su propia dirección    /oferta/asistente-contable-ferreycorp-12/
  · su propio título y descripción para los resultados de búsqueda
  · datos estructurados JobPosting, que es lo que lee Google Empleos

Además se genera el sitemap.xml (el índice que Google usa para descubrirlas) y
se borran las páginas de las ofertas que ya salieron de la web: una oferta
vencida indexada es peor que ninguna.
"""
from __future__ import annotations

import html
import json
import re
import shutil
from datetime import date, datetime
from pathlib import Path

from .almacen import Almacen
from .modelos import sin_tildes

RAIZ = Path(__file__).resolve().parent.parent
CARPETA_OFERTAS = "oferta"

# Mientras no haya dominio propio, la dirección que da GitHub.
SITIO_GITHUB = "https://mentitaa.github.io/cero-vagos"


def sitio_publicado(raiz: Path = RAIZ) -> str:
    """
    Averigua sola cuál es la dirección del sitio, en este orden:

      1. la variable de entorno CERO_VAGOS_SITIO
      2. el archivo CNAME, que GitHub Pages crea cuando conectas un dominio
      3. la dirección de github.io

    El paso 2 es el importante: el día que compres cerovagos.com y lo conectes
    en GitHub, ese archivo aparece solo y desde la siguiente corrida todas las
    páginas, el sitemap y los enlaces salen con el dominio nuevo. Sin tocar
    una línea de código.
    """
    import os

    del_entorno = os.environ.get("CERO_VAGOS_SITIO", "").strip()
    if del_entorno:
        return del_entorno.rstrip("/")

    cname = raiz / "CNAME"
    if cname.exists():
        dominio = cname.read_text(encoding="utf-8").strip().splitlines()
        if dominio and dominio[0].strip():
            return "https://" + dominio[0].strip().lstrip("https://").lstrip("http://").rstrip("/")

    return SITIO_GITHUB


# Compatibilidad con el código que ya lo usaba por nombre.
SITIO_POR_DEFECTO = SITIO_GITHUB


def slug(texto: str, sufijo: str = "") -> str:
    base = re.sub(r"[^a-z0-9]+", "-", sin_tildes(texto)).strip("-")
    base = re.sub(r"-{2,}", "-", base)[:70].strip("-")
    return f"{base}-{sufijo}" if sufijo else base


def _e(texto) -> str:
    """Escapa para meter texto dentro del HTML sin romperlo."""
    return html.escape(str(texto or ""), quote=True)


def _soles(n: int) -> str:
    return f"S/ {n:,}".replace(",", ",")


def _sueldo_texto(o: dict) -> str:
    lo, hi = o.get("min") or 0, o.get("max") or 0
    if not lo:
        return "Sin sueldo declarado"
    return _soles(lo) if not hi or hi == lo else f"{_soles(lo)} – {_soles(hi)}"


# --------------------------------------------------------------------------
# Datos estructurados: lo que lee Google Empleos
# --------------------------------------------------------------------------

def jobposting(o: dict, url: str) -> str:
    """
    Bloque schema.org/JobPosting. Es el mismo formato que este motor lee de
    otros portales; ahora lo publicamos nosotros.
    """
    descripcion = ["<p>" + _e(o.get("resumen", "")) + "</p>"]
    for titulo, clave in (("Funciones", "funciones"),
                          ("Requisitos", "requisitos"),
                          ("Beneficios", "beneficios")):
        items = o.get(clave) or []
        if items:
            descripcion.append(f"<p><strong>{titulo}</strong></p><ul>"
                               + "".join(f"<li>{_e(i)}</li>" for i in items) + "</ul>")

    datos = {
        "@context": "https://schema.org",
        "@type": "JobPosting",
        "title": o["puesto"],
        "description": "".join(descripcion),
        "identifier": {"@type": "PropertyValue", "name": "Cero Vagos",
                       "value": str(o.get("huella") or o.get("id", ""))},
        "hiringOrganization": {"@type": "Organization", "name": o.get("empresa") or "—"},
        "jobLocation": {
            "@type": "Place",
            "address": {"@type": "PostalAddress",
                        "addressLocality": o.get("ciudad") or "Lima",
                        "addressCountry": "PE"},
        },
        "employmentType": "FULL_TIME",
        "url": url,
    }

    publicado = o.get("publicado_iso")
    if publicado:
        datos["datePosted"] = publicado
    if o.get("vence"):
        datos["validThrough"] = o["vence"]
    if o.get("min"):
        datos["baseSalary"] = {
            "@type": "MonetaryAmount", "currency": "PEN",
            "value": {"@type": "QuantitativeValue",
                      "minValue": o["min"], "maxValue": o.get("max") or o["min"],
                      "unitText": "MONTH"},
        }
    if (o.get("modalidad") or "").lower() == "remoto":
        datos["jobLocationType"] = "TELECOMMUTE"

    return json.dumps(datos, ensure_ascii=False, indent=1)


# --------------------------------------------------------------------------
# Página de la oferta
# --------------------------------------------------------------------------

_ESTILOS = """
:root{--rojo:#FF1E1E;--negro:#0B0B0B;--crema:#FFF3E4;--blanco:#fff;
--amarillo:#FFD100;--azul:#2B37FF;--lima:#B8FF2E;--bd:3px solid var(--negro);
--display:'Archivo Black','Arial Black',system-ui,sans-serif;
--body:'Space Grotesk',system-ui,-apple-system,sans-serif}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:var(--body);background:var(--crema);color:var(--negro);
background-image:linear-gradient(rgba(11,11,11,.045) 1px,transparent 1px),
linear-gradient(90deg,rgba(11,11,11,.045) 1px,transparent 1px);background-size:44px 44px}
h1,h2,h3{font-family:var(--display);text-transform:uppercase;letter-spacing:-.02em;line-height:1}
a{color:inherit}
.wrap{max-width:820px;margin:0 auto;padding:0 18px}
.barra{background:var(--rojo);color:#fff;border-bottom:var(--bd);padding:12px 0;
font-family:var(--display);font-size:12px;letter-spacing:.06em;text-transform:uppercase}
.barra a{text-decoration:none}
/* El logo solo no se entiende como "volver": mucha gente no sabe que se le
   puede dar clic. El texto al lado lo dice sin ambigüedad. */
.barra .volver{display:inline-flex;align-items:center;gap:14px}
.barra .volver img{width:auto;height:34px;display:block;flex:0 0 auto}
.barra .volver span{font-family:var(--display);font-size:12.5px;
letter-spacing:.05em;text-transform:uppercase;border-bottom:2px solid rgba(255,255,255,.55);
padding-bottom:2px}
.barra .volver:hover span{border-bottom-color:#fff}
@media(max-width:560px){.barra .volver img{height:27px}
.barra .volver span{font-size:11px}}
.ficha{border:var(--bd);background:var(--blanco);box-shadow:9px 9px 0 var(--negro);margin:26px 0 40px}
.cab{background:var(--rojo);color:#fff;padding:26px 24px;border-bottom:var(--bd)}
.cab h1{font-size:clamp(24px,4.6vw,38px)}
.cab p{font-weight:700;margin-top:9px;font-size:15px}
.pill{display:inline-block;border:2px solid var(--negro);background:var(--blanco);
color:var(--negro);padding:5px 11px;font-size:12px;font-weight:700;text-transform:uppercase;margin-top:11px}
.pago{background:var(--amarillo);border-bottom:var(--bd);padding:19px 24px;
display:flex;justify-content:space-between;align-items:center;gap:14px;flex-wrap:wrap}
.pago b{font-family:var(--display);font-size:29px;display:block}
.pago span{font-size:12px;font-weight:700;text-transform:uppercase}
.puntaje{background:var(--negro);color:var(--lima);padding:6px 12px;font-weight:700;font-size:12px;text-transform:uppercase}
.bloque{padding:22px 24px;border-bottom:var(--bd)}
.bloque:last-of-type{border-bottom:none}
.bases{background:var(--crema)}
.bases p{font-size:15px;line-height:1.5;font-weight:500;margin-bottom:10px}
.bases a{font-weight:700}
.bloque h2{font-size:16px;margin-bottom:13px}
.bloque ul{list-style:none;display:grid;gap:9px}
.bloque li{font-size:15px;line-height:1.45;font-weight:500;padding-left:19px;position:relative}
.bloque li::before{content:"";position:absolute;left:0;top:7px;width:9px;height:9px;background:var(--negro)}
.beneficios{background:var(--lima)}
.pie{padding:22px 24px;display:flex;gap:12px;flex-wrap:wrap;align-items:center}
.btn{display:inline-block;border:var(--bd);background:var(--rojo);color:#fff;
font-family:var(--display);font-size:14px;text-transform:uppercase;padding:14px 22px;
text-decoration:none;box-shadow:4px 4px 0 var(--negro)}
.btn--blanco{background:var(--blanco);color:var(--negro)}
.nota{font-size:12.5px;font-weight:700;opacity:.6}
footer{border-top:var(--bd);padding:22px 0;font-size:13px;font-weight:500}
@media(max-width:600px){.ficha{box-shadow:5px 5px 0 var(--negro)}.cab,.pago,.bloque,.pie{padding-left:16px;padding-right:16px}}
"""


def _lista(titulo: str, items: list[str], clase: str = "") -> str:
    if not items:
        return ""
    filas = "".join(f"<li>{_e(i)}</li>" for i in items)
    return (f'<section class="bloque {clase}"><h2>{titulo}</h2>'
            f"<ul>{filas}</ul></section>")


def _funciones_en_las_bases(o: dict) -> str:
    """
    Qué se muestra cuando una convocatoria del Estado no lista sus funciones.

    Un hueco en blanco donde el diseño promete "Qué vas a hacer" se lee como
    un error del sitio. Y callarlo sería peor: la promesa de Cero Vagos es
    decir lo que hay y lo que no.

    Así que se dice dónde están, con el enlace al aviso oficial — que es el
    documento que la persona va a tener que leer igual para postular.
    """
    if o.get("funciones"):
        return ""
    return (
        '<section class="bloque bases"><h2>Qué vas a hacer</h2>'
        '<p><b>Esta convocatoria no publica la lista de funciones.</b> '
        'En el sector público las funciones van dentro de las bases del '
        'concurso, un documento aparte que la entidad publica y que vas a '
        'necesitar leer para postular.</p>'
        f'<p><a href="{_e(o.get("url") or "#")}" target="_blank" '
        'rel="noopener noreferrer">Ver la convocatoria oficial →</a></p>'
        "</section>"
    )


def pagina_oferta(o: dict, sitio: str) -> str:
    url = f"{sitio}/{CARPETA_OFERTAS}/{o['slug']}/"
    titulo = f"{o['puesto']} en {o.get('empresa') or 'empresa'} — {_sueldo_texto(o)}"
    ciudad = o.get("ciudad") or "Perú"

    descripcion = (f"{o['puesto']} en {o.get('empresa') or 'empresa'}, {ciudad}. "
                   f"Sueldo {_sueldo_texto(o)}. Funciones, requisitos y beneficios "
                   f"detallados. Oferta verificada por Cero Vagos.")

    plazo = ""
    if o.get("restan") is not None:
        r = o["restan"]
        texto = ("Cierra hoy" if r == 0 else
                 "Cierra mañana" if r == 1 else f"Cierra en {r} días")
        plazo = f'<span class="pill">{texto}</span>'

    return f"""<!DOCTYPE html>
<html lang="es-PE">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_e(titulo)} | Cero Vagos</title>
<meta name="description" content="{_e(descripcion)}">
<link rel="canonical" href="{_e(url)}">
<meta property="og:type" content="article">
<meta property="og:title" content="{_e(titulo)}">
<meta property="og:description" content="{_e(descripcion)}">
<meta property="og:url" content="{_e(url)}">
<meta property="og:site_name" content="Cero Vagos">
<meta property="og:locale" content="es_PE">
<meta property="og:image" content="{_e(sitio)}/assets/compartir.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{_e(sitio)}/assets/compartir.png">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src 'self'; connect-src 'none'; form-action 'none'; base-uri 'none'; object-src 'none'">
<link rel="icon" href="{_e(sitio)}/assets/icono.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo+Black&family=Space+Grotesk:wght@400;500;700&display=swap" rel="stylesheet">
<style>{_ESTILOS}</style>
<script type="application/ld+json">
{jobposting(o, url)}
</script>
</head>
<body>

<div class="barra"><div class="wrap">
  <a href="{_e(sitio)}/" class="volver">
    <img src="{_e(sitio)}/assets/logo-mono.svg" alt="Cero Vagos">
    <span>← Volver a las ofertas</span>
  </a>
</div></div>

<div class="wrap">
  <article class="ficha">
    <header class="cab">
      <h1>{_e(o['puesto'])}</h1>
      <p>{_e(o.get('empresa') or '—')} · {_e(ciudad)} · {_e(o.get('modalidad') or 'Presencial')}</p>
      {plazo}
    </header>

    <div class="pago">
      <div><span>Sueldo mensual</span><b>{_sueldo_texto(o)}</b></div>
      <span class="puntaje">Score de completitud {o.get('score', 0)}/100</span>
    </div>

    {f'<section class="bloque"><h2>De qué se trata</h2><p style="font-size:15px;line-height:1.5;font-weight:500">{_e(o["resumen"])}</p></section>' if o.get("resumen") else ""}
    {_lista("Qué vas a hacer", o.get("funciones") or []) or _funciones_en_las_bases(o)}
    {_lista("Qué piden", o.get("requisitos") or [])}
    {_lista("Qué te dan", o.get("beneficios") or [], "beneficios")}

    <div class="pie">
      <a class="btn" href="{_e(o.get('url') or '#')}" target="_blank" rel="noopener">Postular en {_e(o.get('fuente') or 'el portal')} →</a>
      <a class="btn btn--blanco" href="{_e(sitio)}/#ofertas">Ver más ofertas</a>
      <span class="nota">Te llevamos al aviso original. Cero Vagos nunca te pide pagar.</span>
    </div>
  </article>
</div>

<footer><div class="wrap">
  <b>Cero Vagos</b> — el buscador que solo muestra ofertas laborales completas del Perú.
  Si no dice cuánto paga, para nosotros no existe.
</div></footer>

</body>
</html>
"""


# --------------------------------------------------------------------------
# Sitemap y robots
# --------------------------------------------------------------------------

def sitemap(ofertas: list[dict], sitio: str) -> str:
    hoy = date.today().isoformat()
    entradas = [
        f"  <url><loc>{sitio}/</loc><lastmod>{hoy}</lastmod>"
        f"<changefreq>daily</changefreq><priority>1.0</priority></url>",
        # La página de transparencia va alto a propósito: es el contenido que
        # puede traer visitas por sí solo.
        f"  <url><loc>{sitio}/transparencia/</loc><lastmod>{hoy}</lastmod>"
        f"<changefreq>daily</changefreq><priority>0.9</priority></url>",
    ]

    # Las páginas fijas cambian poco, pero deben ser encontrables.
    # El libro de reclamaciones se deja fuera: es un canal, no contenido.
    for fija in ("como-trabajamos", "terminos", "privacidad"):
        entradas.append(
            f"  <url><loc>{sitio}/{fija}/</loc><lastmod>{hoy}</lastmod>"
            f"<changefreq>monthly</changefreq><priority>0.4</priority></url>"
        )
    for o in ofertas:
        mod = o.get("publicado_iso") or hoy
        entradas.append(
            f"  <url><loc>{sitio}/{CARPETA_OFERTAS}/{o['slug']}/</loc>"
            f"<lastmod>{mod}</lastmod><changefreq>daily</changefreq>"
            f"<priority>0.8</priority></url>"
        )
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + "\n".join(entradas) + "\n</urlset>\n")


def pagina_404(sitio: str) -> str:
    """
    Lo que ve quien llega con un enlace viejo.

    Pasa todos los días: alguien guarda una oferta, la comparte por WhatsApp o
    la encuentra en Google, y cuando entra el plazo ya cerró y la página se
    retiró. En vez de un error genérico, se le explica qué pasó y se le ofrece
    la salida.
    """
    return f"""<!DOCTYPE html>
<html lang="es-PE">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Esta oferta ya cerró | Cero Vagos</title>
<meta name="robots" content="noindex">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src 'self'; connect-src 'none'; form-action 'none'; base-uri 'none'; object-src 'none'">
<link rel="icon" href="{_e(sitio)}/assets/icono.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo+Black&family=Space+Grotesk:wght@400;500;700&display=swap" rel="stylesheet">
<style>{_ESTILOS}
.centro{{max-width:620px;margin:0 auto;padding:70px 18px}}
.caja{{border:var(--bd);background:var(--blanco);box-shadow:9px 9px 0 var(--negro)}}
.caja .cab{{background:var(--negro)}}
.caja .cab h1{{font-size:clamp(26px,5vw,40px)}}
.cuerpo{{padding:24px}}
.cuerpo p{{font-size:16px;line-height:1.55;font-weight:500;margin-bottom:14px}}
</style>
</head>
<body>
<div class="barra"><div class="wrap">
  <a href="{_e(sitio)}/" class="volver">
    <img src="{_e(sitio)}/assets/logo-mono.svg" alt="Cero Vagos">
    <span>← Volver a las ofertas</span>
  </a>
</div></div>

<div class="centro">
  <div class="caja">
    <header class="cab">
      <h1>Esta oferta<br>ya cerró</h1>
      <p>O nunca existió en esta dirección.</p>
    </header>
    <div class="cuerpo">
      <p>Cuando una convocatoria vence, la sacamos de la web el mismo día. Preferimos
      que no encuentres nada a que pierdas la tarde postulando a algo cerrado.</p>
      <p>Pero hay más chamba, y toda con el sueldo a la vista.</p>
      <p style="margin-top:22px">
        <a class="btn" href="{_e(sitio)}/#ofertas">Ver las ofertas de hoy →</a>
      </p>
    </div>
  </div>
</div>

<footer><div class="wrap">
  <b>Cero Vagos</b> — si no dice cuánto paga, para nosotros no existe.
</div></footer>
</body>
</html>
"""


def robots(sitio: str) -> str:
    return ("# Cero Vagos\n"
            "User-agent: *\n"
            "Allow: /\n\n"
            f"Sitemap: {sitio}/sitemap.xml\n")


# --------------------------------------------------------------------------
# Bloque de enlaces dentro de la portada
# --------------------------------------------------------------------------

INICIO_MARCA = "<!-- OFERTAS-ESTATICAS:INICIO -->"
FIN_MARCA = "<!-- OFERTAS-ESTATICAS:FIN -->"


def bloque_enlaces(ofertas: list[dict]) -> str:
    """
    Enlaces a cada oferta, dentro de la portada pero sin mostrarse.

    Las tarjetas bonitas las dibuja JavaScript y un buscador puede no verlas.
    Estos enlaces sí están en el HTML desde el primer momento, así que
    cualquier rastreador llega a todas las ofertas siguiendo la portada.

    No se muestran porque la sección visible quedaba fea y no aportaba nada a
    quien ya tiene el buscador arriba. El descubrimiento principal sigue siendo
    el sitemap; esto es el refuerzo.
    """
    if not ofertas:
        return f"{INICIO_MARCA}\n{FIN_MARCA}"

    filas = "\n".join(
        f'    <li><a href="{CARPETA_OFERTAS}/{o["slug"]}/">'
        f'{_e(o["puesto"])} — {_e(o.get("empresa") or "")}</a></li>'
        for o in ofertas
    )
    return f"""{INICIO_MARCA}
<nav class="indice-oculto" aria-label="Todas las ofertas">
  <ul>
{filas}
  </ul>
</nav>
{FIN_MARCA}"""


# --------------------------------------------------------------------------
# La tarjeta que sale al compartir el enlace
# --------------------------------------------------------------------------

INICIO_OG = "<!-- COMPARTIR:INICIO -->"
FIN_OG = "<!-- COMPARTIR:FIN -->"

IMAGEN_COMPARTIR = "assets/compartir.png"


def bloque_compartir(sitio: str, pct_sin_sueldo: int | None = None) -> str:
    """
    Las etiquetas que lee WhatsApp, Facebook y LinkedIn al pegar el enlace.

    Sin esto el enlace sale como un recuadro de texto pelado. Con esto sale
    con imagen, título y descripción.

    Dos detalles que no son opcionales:

      · Las direcciones tienen que ser **absolutas** (empezar con https://).
        WhatsApp no resuelve rutas relativas: si pones "assets/compartir.png"
        no muestra nada. Por eso este bloque lo escribe el generador y no está
        fijo en el HTML: el día que se conecte cerovagos.com se reescribe solo.

      · El ancho y alto declarados hacen que la vista previa se dibuje grande
        desde el primer momento, sin esperar a descargar la imagen.

    El porcentaje sale de la base, no de una cifra escrita a mano, para que la
    descripción no envejezca.
    """
    pct = pct_sin_sueldo if pct_sin_sueldo else 75
    titulo = "Cero Vagos — Solo ofertas de trabajo completas en Perú"
    descripcion = (
        f"El {pct}% de los avisos de empleo en el Perú no dice cuánto paga. "
        f"Aquí solo entran los que sí: con sueldo en soles, funciones, "
        f"requisitos y beneficios. Si falta uno, no se publica."
    )
    imagen = f"{sitio}/{IMAGEN_COMPARTIR}"
    return f"""{INICIO_OG}
<meta property="og:type" content="website">
<meta property="og:site_name" content="Cero Vagos">
<meta property="og:locale" content="es_PE">
<meta property="og:title" content="{_e(titulo)}">
<meta property="og:description" content="{_e(descripcion)}">
<meta property="og:url" content="{_e(sitio)}/">
<meta property="og:image" content="{_e(imagen)}">
<meta property="og:image:type" content="image/png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Cero Vagos. El {pct}% de los avisos de empleo no dice cuánto paga.">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{_e(titulo)}">
<meta name="twitter:description" content="{_e(descripcion)}">
<meta name="twitter:image" content="{_e(imagen)}">
<link rel="canonical" href="{_e(sitio)}/">
{FIN_OG}"""


# --------------------------------------------------------------------------
# Generación completa
# --------------------------------------------------------------------------

def _preparar(fila: dict, indice: int) -> dict:
    """
    Se reutiliza el mismo formato que consume la web (min, max, restan…) en vez
    de leer la fila de la base a mano: así la página y el listado nunca muestran
    cosas distintas.
    """
    from .exportar import _a_formato_web

    o = _a_formato_web(fila, indice)
    o["publicado_iso"] = fila.get("publicado") or ""

    # La dirección se arma con la huella de la oferta, NO con su posición en la
    # lista. Si se usara la posición, al retirarse una oferta cambiarían las
    # direcciones de todas las demás: Google perdería lo indexado y quien haya
    # guardado un enlace llegaría a un puesto distinto.
    o["huella"] = fila.get("huella") or ""
    o["slug"] = slug(f"{o['puesto']}-{o.get('empresa') or ''}", o["huella"][:8])
    return o


def generar(almacen: Almacen | None = None, sitio: str = "",
            raiz: Path = RAIZ) -> dict:
    sitio = (sitio or sitio_publicado(raiz)).rstrip("/")
    al = almacen or Almacen()
    al.depurar()
    # Los títulos guardados antes de la última mejora del limpiador se
    # reescriben ahora, sin esperar a que el motor vuelva a ver cada aviso.
    titulos = al.limpiar_titulos()
    # Y la regla del título: los que no dicen qué puesto es se reescriben con
    # el oficio que nombra el propio aviso, o se bajan si no lo nombra.
    vagos = al.revisar_titulos_vagos()

    # El listado de la portada vive en datos/ofertas.js y se regenera aparte.
    # Sin esto, arreglar un título o un sueldo no se veía nunca en las tarjetas:
    # las páginas de oferta salían corregidas y la portada seguía con lo viejo.
    from .exportar import exportar
    # Se le pasa la misma carpeta en la que se está generando todo lo demás.
    # Sin esto, los tests (que trabajan sobre una carpeta temporal) escribían
    # el ofertas.js de verdad y dejaban la web con dos ofertas inventadas.
    exportar(al, raiz=raiz)

    filas = al.aprobadas(1000)
    ofertas = [_preparar(f, i + 1) for i, f in enumerate(filas)]

    carpeta = raiz / CARPETA_OFERTAS
    carpeta.mkdir(parents=True, exist_ok=True)

    vigentes = {o["slug"] for o in ofertas}
    for o in ofertas:
        destino = carpeta / o["slug"]
        destino.mkdir(parents=True, exist_ok=True)
        (destino / "index.html").write_text(pagina_oferta(o, sitio), encoding="utf-8")

    # Se borran las páginas de ofertas que ya salieron de la web. Una oferta
    # vencida que sigue indexada en Google es peor que no tenerla nunca.
    retiradas = 0
    for vieja in carpeta.iterdir():
        if vieja.is_dir() and vieja.name not in vigentes:
            shutil.rmtree(vieja, ignore_errors=True)
            retiradas += 1

    # El ranking de transparencia salarial: contenido propio que atrae
    # búsquedas y da material para compartir.
    from .transparencia import generar as generar_transparencia
    informe = generar_transparencia(al, sitio, raiz)

    # Términos, privacidad, reclamaciones y cómo trabajamos.
    from .legales import generar as generar_legales
    legales = generar_legales(sitio, raiz)

    (raiz / "sitemap.xml").write_text(sitemap(ofertas, sitio), encoding="utf-8")
    (raiz / "robots.txt").write_text(robots(sitio), encoding="utf-8")
    # GitHub Pages muestra este archivo cuando alguien llega a una dirección
    # que ya no existe: el caso de la oferta retirada.
    (raiz / "404.html").write_text(pagina_404(sitio), encoding="utf-8")

    # Se inyectan los enlaces en la portada, entre los marcadores.
    portada = raiz / "index.html"
    if portada.exists():
        texto = original = portada.read_text(encoding="utf-8")
        nuevo = bloque_enlaces(ofertas)
        if INICIO_MARCA in texto and FIN_MARCA in texto:
            texto = re.sub(
                re.escape(INICIO_MARCA) + r".*?" + re.escape(FIN_MARCA),
                lambda _: nuevo, texto, flags=re.S,
            )
        # Y las etiquetas de compartir, que llevan la dirección completa del
        # sitio: si mañana cambia el dominio, se reescriben solas.
        if INICIO_OG in texto and FIN_OG in texto:
            og = bloque_compartir(sitio, informe.get("pct_sin_sueldo"))
            texto = re.sub(
                re.escape(INICIO_OG) + r".*?" + re.escape(FIN_OG),
                lambda _: og, texto, flags=re.S,
            )
        if texto != original:
            portada.write_text(texto, encoding="utf-8")

    return {"paginas": len(ofertas), "retiradas": retiradas, "sitio": sitio,
            "titulos_limpiados": titulos, "titulos_vagos": vagos, "legales": legales,
            "pct_sin_sueldo": informe["pct_sin_sueldo"],
            "empresas_analizadas": len(informe["empresas"]),
            "generado": datetime.now().isoformat(timespec="seconds")}
