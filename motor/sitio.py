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

# --------------------------------------------------------------------------
# Medición de visitas
#
# Cloudflare Web Analytics. Se eligió por lo que NO hace: no pone cookies, no
# sigue a nadie entre sitios y no guarda nada que identifique a una persona.
# Por eso el sitio no necesita cartel de consentimiento y la política de
# privacidad sigue siendo cierta tal como está escrita — que es media razón de
# ser del proyecto.
#
# El token no es un secreto: viaja en el HTML de cada página, a la vista de
# cualquiera. Solo dice a qué sitio pertenecen las visitas; no da acceso a la
# cuenta ni permite leer los datos.
#
# Vive acá, en un solo lugar, y de acá sale para la portada y para la página de
# cada oferta. Si alguna vez cambia, se cambia una vez.
#
# Al agregarlo hubo que sumar dos direcciones a la lista blanca de seguridad de
# las tres plantillas: de una se baja el archivo y a la otra se le mandan las
# visitas. Sin eso el navegador lo bloquea y no avisa a nadie.
ANALITICA_TOKEN = "8025c1f703514128a4b665979e0ee8d3"
ANALITICA_ORIGEN = "https://static.cloudflareinsights.com"
ANALITICA_ENVIO = "https://cloudflareinsights.com"

INICIO_ANALITICA = "<!-- ANALITICA:INICIO -->"
FIN_ANALITICA = "<!-- ANALITICA:FIN -->"


def bloque_analitica() -> str:
    """El fragmento que cuenta las visitas. Vacío si no hay token configurado."""
    if not ANALITICA_TOKEN:
        return ""
    return (f'<script defer src="{ANALITICA_ORIGEN}/beacon.min.js" '
            f"data-cf-beacon='{{\"token\": \"{ANALITICA_TOKEN}\"}}'></script>")


def csp(*, con_formulario: bool = False) -> str:
    """
    La lista blanca de la página: qué se permite cargar y a dónde se permite
    hablar. Todo lo que no esté acá, el navegador lo bloquea.

    Está en una sola función para que las tres plantillas no se desincronicen:
    antes eran tres textos copiados y bastaba con actualizar dos para dejar un
    agujero —o para romper algo— sin que se notara.
    """
    # La portada lleva su JavaScript escrito dentro del propio HTML y manda el
    # formulario de alertas; las páginas de oferta no hacen ni lo uno ni lo
    # otro, y conviene que sigan siendo las más cerradas de las dos.
    if con_formulario:
        guiones = "'self' 'unsafe-inline' " + ANALITICA_ORIGEN
        conectar = "'self' https://formspree.io " + ANALITICA_ENVIO
        formulario = "'self'"
    else:
        guiones = "'self' " + ANALITICA_ORIGEN
        conectar = ANALITICA_ENVIO
        formulario = "'none'"

    return (
        "default-src 'self'; "
        f"script-src {guiones}; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src https://fonts.gstatic.com; "
        "img-src 'self'; "
        f"connect-src {conectar}; "
        f"form-action {formulario}; "
        "base-uri 'none'; object-src 'none'"
    )
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


def _soles(n: int, moneda: str = "PEN") -> str:
    """El monto con SU símbolo. Un sueldo en dólares no se escribe con S/."""
    return f"{'US$' if moneda == 'USD' else 'S/'} {n:,}"


def _sueldo_texto(o: dict) -> str:
    lo, hi = o.get("min") or 0, o.get("max") or 0
    if not lo:
        return "Sin sueldo declarado"
    m = o.get("moneda") or "PEN"
    return (_soles(lo, m) if not hi or hi == lo
            else f"{_soles(lo, m)} – {_soles(hi, m)}")


def _lo_que_tiene(o: dict) -> str:
    """
    Las cuatro cosas que el aviso SÍ trae, marcadas una por una.

    Reemplaza al "Score de completitud 92/100" que salía acá. El score se
    quitó de la tarjeta el 7/8/2026 y esta ficha se quedó atrás: seguía
    mostrándolo, que es exactamente lo que el focus group leyó mal (lo tomaban
    por una nota AL TRABAJO) y además deja ver la fórmula, que no se publica.

    Las convocatorias del Estado sin funciones muestran tres marcas en vez de
    cuatro, y está bien: es honesto, y más abajo la ficha explica dónde
    buscarlas. Es el mismo criterio de `loQueTiene` en `index.html`.
    """
    marcas = [
        ("Sueldo", (o.get("min") or 0) > 0),
        ("Funciones", bool(o.get("funciones"))),
        ("Requisitos", bool(o.get("requisitos"))),
        ("Beneficios", bool(o.get("beneficios"))),
    ]
    tiene = "".join(f"<span>✓ {n}</span>" for n, hay in marcas if hay)
    return f'<div class="tiene">{tiene}</div>' if tiene else ""


# --------------------------------------------------------------------------
# Datos estructurados: lo que lee Google Empleos
# --------------------------------------------------------------------------

def _direccion(o: dict) -> dict:
    """
    La dirección del puesto para Google Empleos.

    Google pide cinco campos y nosotros llenamos tres, a propósito:

      · `addressCountry`  — siempre PE.
      · `addressLocality` — la ciudad que el aviso nombra.
      · `addressRegion`   — el departamento. Sirve para que la oferta salga en
        "trabajos en Cusco" aunque la persona no escriba el nombre del
        distrito, y es lo que más ayuda a la oferta de provincia. El motor ya
        lo deduce y lo guarda (`detectar_ubicacion`); solo faltaba pasarlo.

      · `streetAddress` y `postalCode` van **vacíos y así se quedan**. Los
        avisos de empleo peruanos no dicen la calle ni el código postal, y
        Google los pide igual: Search Console los marca en naranja, como
        "podría presentarse mejor". Es un aviso, no un error.

        Inventarlos —poner la dirección fiscal de la empresa, o el código
        postal del centro de la ciudad— sería exactamente lo que la regla 2
        prohíbe: rellenar un dato que nadie escribió. Alguien iría a una
        dirección que no es. Se prefiere el aviso naranja.
    """
    direccion = {
        "@type": "PostalAddress",
        "addressLocality": o.get("ciudad") or "Lima",
        "addressCountry": "PE",
    }
    if o.get("departamento"):
        direccion["addressRegion"] = o["departamento"]
    return direccion


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
        "jobLocation": {"@type": "Place", "address": _direccion(o)},
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
            # La moneda de verdad. Decirle "PEN" a Google sobre un sueldo en
            # dólares es publicar un dato falso en el sitio más visible.
            "@type": "MonetaryAmount", "currency": o.get("moneda") or "PEN",
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
:root{color-scheme:light;
/* LA PALETA. Es ley: fuera de aquí no se escribe ningún color.
   La misma que index.html — si cambia allá, cambia aquí. Elegida el
   13/8/2026 para que los colores dejen de parecer puestos por poner. */
--marca:#FF1E1E;      /* rojo: identidad y acción, nada más */
--marca-osc:#C7150F;
--tinta:#101B2D;      /* azul tinta: texto, bordes y bloques oscuros */
--fondo:#F5F1E8;      /* hueso: el fondo de todo */
--blanco:#fff;
--acento:#FFB703;     /* ámbar, y uno solo: marca lo que el aviso SÍ trae */
--tinta-suave:#5A6B85;
--gris:#E8E0D4;
--ok:#2A9D5C;         /* solo /transparencia: las que sí publican */
--alerta:#A81409;     /* solo /transparencia: NO es el rojo de marca */
--bd:3px solid var(--tinta);
--display:'Archivo Black','Arial Black',system-ui,sans-serif;
--body:'Space Grotesk',system-ui,-apple-system,sans-serif}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:var(--body);background:var(--fondo);color:var(--tinta);
background-image:linear-gradient(rgba(16,27,45,.05) 1px,transparent 1px),
linear-gradient(90deg,rgba(16,27,45,.05) 1px,transparent 1px);background-size:44px 44px}
h1,h2,h3{font-family:var(--display);text-transform:uppercase;letter-spacing:-.02em;line-height:1}
a{color:inherit}
.wrap{max-width:820px;margin:0 auto;padding:0 18px}
.barra{background:var(--marca);color:#fff;border-bottom:var(--bd);padding:12px 0;
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
.ficha{border:var(--bd);background:var(--blanco);box-shadow:9px 9px 0 var(--tinta);margin:26px 0 40px}
.cab{background:var(--marca);color:#fff;padding:26px 24px;border-bottom:var(--bd)}
.cab h1{font-size:clamp(24px,4.6vw,38px)}
.cab p{font-weight:700;margin-top:9px;font-size:15px}
.pill{display:inline-block;border:2px solid var(--tinta);background:var(--blanco);
color:var(--tinta);padding:5px 11px;font-size:12px;font-weight:700;text-transform:uppercase;margin-top:11px}
.pago{background:var(--acento);border-bottom:var(--bd);padding:19px 24px;
display:flex;justify-content:space-between;align-items:center;gap:14px;flex-wrap:wrap}
.pago b{font-family:var(--display);font-size:29px;display:block}
.pago span{font-size:12px;font-weight:700;text-transform:uppercase}
/* Lo mismo que en la tarjeta de la portada: las cuatro cosas que el aviso SÍ
   trae, en vez del score. Ver .job__tiene en index.html. */
.tiene{display:flex;flex-wrap:wrap;gap:6px;justify-content:flex-end}
.tiene span{background:var(--acento);border:2px solid var(--tinta);padding:5px 9px;
font-weight:700;font-size:11px;text-transform:uppercase;letter-spacing:.03em;white-space:nowrap}
.bloque{padding:22px 24px;border-bottom:var(--bd)}
.bloque:last-of-type{border-bottom:none}
.bases{background:var(--fondo)}
.bases p{font-size:15px;line-height:1.5;font-weight:500;margin-bottom:10px}
.bases a{font-weight:700}
.bloque h2{font-size:16px;margin-bottom:13px}
.bloque ul{list-style:none;display:grid;gap:9px}
.bloque li{font-size:15px;line-height:1.45;font-weight:500;padding-left:19px;position:relative}
.bloque li::before{content:"";position:absolute;left:0;top:7px;width:9px;height:9px;background:var(--tinta)}
.beneficios{background:var(--acento)}
.pie{padding:22px 24px;display:flex;gap:12px;flex-wrap:wrap;align-items:center}
.btn{display:inline-block;border:var(--bd);background:var(--marca);color:#fff;
font-family:var(--display);font-size:14px;text-transform:uppercase;padding:14px 22px;
text-decoration:none;box-shadow:4px 4px 0 var(--tinta)}
.btn--blanco{background:var(--blanco);color:var(--tinta)}
.nota{font-size:12.5px;font-weight:700;opacity:.6}
footer{border-top:var(--bd);padding:22px 0;font-size:13px;font-weight:500}
@media(max-width:600px){.ficha{box-shadow:5px 5px 0 var(--tinta)}.cab,.pago,.bloque,.pie{padding-left:16px;padding-right:16px}}
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
<!-- Esta página está diseñada en claro y no tiene versión oscura. Sin
     esta línea, los navegadores con modo oscuro automático (Brave, y
     Chrome en Android) la "arreglan" solos: invierten los colores y el
     crema sale marrón, el amarillo verde oliva y el texto resaltado.
     Declarándolo, el navegador respeta el diseño. Reportado el 8/8/2026. -->
<meta name="color-scheme" content="light">
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
<meta http-equiv="Content-Security-Policy" content="{csp()}">
<link rel="icon" href="{_e(sitio)}/assets/icono.svg" type="image/svg+xml">
<link rel="icon" href="{_e(sitio)}/assets/icono-32.png" sizes="32x32" type="image/png">
<link rel="apple-touch-icon" href="{_e(sitio)}/assets/icono-180.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo+Black&family=Space+Grotesk:wght@400;500;700&display=swap" rel="stylesheet">
<style>{_ESTILOS}</style>
<script type="application/ld+json">
{jobposting(o, url)}
</script>
{bloque_analitica()}
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
      {_lo_que_tiene(o)}
    </div>

    {f'<section class="bloque"><h2>De qué se trata</h2><p style="font-size:15px;line-height:1.5;font-weight:500">{_e(o["resumen"])}</p></section>' if o.get("resumen") else ""}
    {_lista("Qué vas a hacer", o.get("funciones") or []) or _funciones_en_las_bases(o)}
    {_lista("Qué piden", o.get("requisitos") or [])}
    {_lista("Qué te dan", o.get("beneficios") or [], "beneficios")}

    <div class="pie">
      <a class="btn" href="{_e(sitio)}/{CARPETA_SALIDA}/{o['slug']}/" target="_blank" rel="noopener">Postular en {_e(o.get('fuente') or 'el portal')} →</a>
      <a class="btn btn--blanco" href="{_e(sitio)}/#ofertas">Ver más ofertas</a>
      {f'<a class="btn btn--blanco" href="{_e(sitio)}/{o["lugar"]}/">Más trabajos en {_e(o.get("departamento") or "")} →</a>' if o.get("lugar") else ""}
      <span class="nota">Te llevamos al <a href="{_e(o.get('url') or '#')}" target="_blank" rel="noopener nofollow">aviso original</a>. Cero Vagos nunca te pide pagar.</span>
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

def sitemap(ofertas: list[dict], sitio: str, lugares: list[str] = (),
            rubros: list[str] = ()) -> str:
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
    # Las páginas por departamento van alto: son contenido de búsqueda ("trabajo
    # en Arequipa con sueldo") y cambian cada día con la oferta.
    from .lugares import ruta as ruta_lugar, ruta_rubro
    for nombre, ruta_de in [(l, ruta_lugar) for l in lugares] + \
                           [(r, ruta_rubro) for r in rubros]:
        entradas.append(
            f"  <url><loc>{sitio}/{ruta_de(nombre)}/</loc><lastmod>{hoy}</lastmod>"
            f"<changefreq>daily</changefreq><priority>0.9</priority></url>"
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
<!-- Esta página está diseñada en claro y no tiene versión oscura. Sin
     esta línea, los navegadores con modo oscuro automático (Brave, y
     Chrome en Android) la "arreglan" solos: invierten los colores y el
     crema sale marrón, el amarillo verde oliva y el texto resaltado.
     Declarándolo, el navegador respeta el diseño. Reportado el 8/8/2026. -->
<meta name="color-scheme" content="light">
<title>Esta oferta ya cerró | Cero Vagos</title>
<meta name="robots" content="noindex">
<meta http-equiv="Content-Security-Policy" content="{csp()}">
<link rel="icon" href="{_e(sitio)}/assets/icono.svg" type="image/svg+xml">
<link rel="icon" href="{_e(sitio)}/assets/icono-32.png" sizes="32x32" type="image/png">
<link rel="apple-touch-icon" href="{_e(sitio)}/assets/icono-180.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo+Black&family=Space+Grotesk:wght@400;500;700&display=swap" rel="stylesheet">
<style>{_ESTILOS}
.centro{{max-width:620px;margin:0 auto;padding:70px 18px}}
.caja{{border:var(--bd);background:var(--blanco);box-shadow:9px 9px 0 var(--tinta)}}
.caja .cab{{background:var(--tinta)}}
.caja .cab h1{{font-size:clamp(26px,5vw,40px)}}
.cuerpo{{padding:24px}}
.cuerpo p{{font-size:16px;line-height:1.55;font-weight:500;margin-bottom:14px}}
</style>
{bloque_analitica()}
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
            "Allow: /\n"
            # Las páginas de salida son un trámite de medio segundo, no
            # contenido. Indexarlas mandaría a la gente desde Google a una
            # pantalla de paso, y a Google le diría que el sitio tiene cientos
            # de páginas sin nada dentro.
            f"Disallow: /{CARPETA_SALIDA}/\n\n"
            f"Sitemap: {sitio}/sitemap.xml\n")


# --------------------------------------------------------------------------
# Páginas de salida: contar los clics hacia el aviso original
#
# El botón de postular ya no va derecho al portal: pasa por una página nuestra
# que redirige sola. Como esa página cuenta como una visita, el medidor nos
# dice cuántas personas hicieron clic en CADA aviso — que es el único número
# que le interesa a una empresa cuando le ofrezcas publicar contigo.
#
# Tres decisiones que van juntas y conviene no tocar por separado:
#
#   · Redirige con `meta refresh`, no con JavaScript. La lista blanca de las
#     páginas internas prohíbe el JavaScript escrito dentro del HTML, y no se
#     va a aflojar por esto: la etiqueta hace exactamente lo mismo, funciona
#     con el JavaScript desactivado y no obliga a abrir esa puerta.
#
#   · Espera un segundo. Suena a lo contrario de lo que uno quiere, pero el
#     medidor necesita ese momento para mandar el dato; redirigiendo al
#     instante se perdería justo el clic que queríamos contar. Aun así habrá
#     algún clic sin contar en conexiones lentas: el número real siempre será
#     un poco mayor que el que veas.
#
#   · Lleva el enlace a la vista y la dirección escrita. No se esconde a dónde
#     va la persona, y quien no quiera esperar hace clic y ya.
# --------------------------------------------------------------------------

CARPETA_SALIDA = "ir"


def pagina_salida(o: dict, sitio: str) -> str:
    destino = o.get("url") or ""
    ficha = f"{sitio}/{CARPETA_OFERTAS}/{o['slug']}/"
    portal = o.get("fuente") or "el portal"
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<!-- Esta página está diseñada en claro y no tiene versión oscura. Sin
     esta línea, los navegadores con modo oscuro automático (Brave, y
     Chrome en Android) la "arreglan" solos: invierten los colores y el
     crema sale marrón, el amarillo verde oliva y el texto resaltado.
     Declarándolo, el navegador respeta el diseño. Reportado el 8/8/2026. -->
<meta name="color-scheme" content="light">
<title>Te llevamos al aviso | Cero Vagos</title>
<meta name="robots" content="noindex, nofollow">
<meta http-equiv="refresh" content="1;url={_e(destino)}">
<meta http-equiv="Content-Security-Policy" content="{csp()}">
<link rel="icon" href="{_e(sitio)}/assets/icono.svg" type="image/svg+xml">
<link rel="icon" href="{_e(sitio)}/assets/icono-32.png" sizes="32x32" type="image/png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo+Black&family=Space+Grotesk:wght@400;500;700&display=swap" rel="stylesheet">
<style>{_ESTILOS}
.salida{{max-width:560px;margin:0 auto;padding:90px 18px;text-align:center}}
.salida h1{{font-size:clamp(24px,5vw,34px);margin-bottom:14px}}
.salida p{{font-size:16px;font-weight:500;line-height:1.55;margin-bottom:10px}}
.salida .destino{{font-size:13px;word-break:break-all;opacity:.65;margin:18px 0 26px}}
.salida .btn{{margin-bottom:22px}}
.salida .volver{{display:inline-block;font-size:14px;font-weight:700;text-decoration:underline}}
</style>
{bloque_analitica()}
</head>
<body>
<main class="salida">
  <h1>Te llevamos al aviso</h1>
  <p>Esta oferta se publicó en <b>{_e(portal)}</b> y ahí es donde se postula.
     Cero Vagos no recibe tu CV ni cobra por postular.</p>
  <p class="destino">{_e(destino)}</p>
  <a class="btn btn--rojo" href="{_e(destino)}" rel="noopener nofollow">Ir ahora →</a>
  <div><a class="volver" href="{_e(ficha)}">Volver a la oferta</a></div>
</main>
</body>
</html>
"""


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
    # El departamento no se manda a la web (la tarjeta muestra la ciudad y con
    # eso basta), pero Google Empleos lo usa para ubicar la oferta en su mapa.
    o["departamento"] = fila.get("departamento") or ""

    # La dirección se arma con la huella de la oferta, NO con su posición en la
    # lista. Si se usara la posición, al retirarse una oferta cambiarían las
    # direcciones de todas las demás: Google perdería lo indexado y quien haya
    # guardado un enlace llegaría a un puesto distinto.
    o["huella"] = fila.get("huella") or ""
    o["slug"] = slug(f"{o['puesto']}-{o.get('empresa') or ''}", o["huella"][:8])
    # Se llena en `generar` si el departamento tiene página propia. Enlazar
    # cada oferta con su departamento es lo que le dice a Google que esas
    # páginas son parte del sitio y no islas sueltas.
    o["lugar"] = ""
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

    # Qué departamentos tienen página propia hoy. Se calcula ANTES de escribir
    # las fichas porque cada una enlaza a la suya, y un enlace a una página que
    # no existe es peor que ningún enlace.
    from .lugares import MINIMO_OFERTAS, ruta as ruta_lugar
    con_pagina = {d["departamento"] for d in al.por_departamento(MINIMO_OFERTAS)}
    for o in ofertas:
        depa = o.get("departamento") or ""
        o["lugar"] = ruta_lugar(depa) if depa in con_pagina else ""

    carpeta = raiz / CARPETA_OFERTAS
    carpeta.mkdir(parents=True, exist_ok=True)

    # La página de salida por la que pasa el botón de postular. Va en su propia
    # carpeta y con el mismo nombre que la oferta, para que al mirar el medidor
    # se sepa de un vistazo qué aviso recibió los clics.
    salidas = raiz / CARPETA_SALIDA
    salidas.mkdir(parents=True, exist_ok=True)

    vigentes = {o["slug"] for o in ofertas}
    for o in ofertas:
        destino = carpeta / o["slug"]
        destino.mkdir(parents=True, exist_ok=True)
        (destino / "index.html").write_text(pagina_oferta(o, sitio), encoding="utf-8")

        paso = salidas / o["slug"]
        paso.mkdir(parents=True, exist_ok=True)
        (paso / "index.html").write_text(pagina_salida(o, sitio), encoding="utf-8")

    # Se borran las páginas de ofertas que ya salieron de la web. Una oferta
    # vencida que sigue indexada en Google es peor que no tenerla nunca.
    # Las de salida se borran con ellas: si la oferta ya no está, su página de
    # paso llevaría a un aviso cerrado y encima seguiría contando clics.
    retiradas = 0
    for lugar in (carpeta, salidas):
        for vieja in lugar.iterdir():
            if vieja.is_dir() and vieja.name not in vigentes:
                shutil.rmtree(vieja, ignore_errors=True)
                if lugar is carpeta:
                    retiradas += 1

    # El ranking de transparencia salarial: contenido propio que atrae
    # búsquedas y da material para compartir.
    from .transparencia import generar as generar_transparencia
    informe = generar_transparencia(al, sitio, raiz)

    # Una página por departamento con oferta suficiente ("Trabajos en Junín").
    # Se le pasa el mapa de huella→dirección porque la dirección de cada oferta
    # se arma acá (regla 3) y las dos no pueden desincronizarse.
    from .lugares import generar as generar_lugares
    slugs = {o["huella"]: o["slug"] for o in ofertas if o.get("huella")}
    listados = generar_lugares(al, sitio, raiz, slugs)
    lugares, rubros = listados["lugares"], listados["rubros"]

    # Términos, privacidad, reclamaciones y cómo trabajamos.
    from .legales import generar as generar_legales
    legales = generar_legales(sitio, raiz)

    (raiz / "sitemap.xml").write_text(sitemap(ofertas, sitio, lugares, rubros), encoding="utf-8")
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
        # Los enlaces a las páginas por departamento, en el pie.
        from .lugares import (
            FIN_LUGARES, INICIO_LUGARES, bloque_para_la_portada,
        )
        if INICIO_LUGARES in texto and FIN_LUGARES in texto:
            bloque = bloque_para_la_portada(lugares, sitio, rubros)
            texto = re.sub(
                re.escape(INICIO_LUGARES) + r".*?" + re.escape(FIN_LUGARES),
                lambda _: bloque, texto, flags=re.S,
            )
        if INICIO_OG in texto and FIN_OG in texto:
            og = bloque_compartir(sitio, informe.get("pct_sin_sueldo"))
            texto = re.sub(
                re.escape(INICIO_OG) + r".*?" + re.escape(FIN_OG),
                lambda _: og, texto, flags=re.S,
            )
        if texto != original:
            portada.write_text(texto, encoding="utf-8")

    return {"paginas": len(ofertas), "retiradas": retiradas, "sitio": sitio,
            "lugares": lugares, "rubros": rubros,
            "titulos_limpiados": titulos, "titulos_vagos": vagos, "legales": legales,
            "pct_sin_sueldo": informe["pct_sin_sueldo"],
            "empresas_analizadas": len(informe["empresas"]),
            "generado": datetime.now().isoformat(timespec="seconds")}
