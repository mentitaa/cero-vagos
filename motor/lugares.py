"""
Las páginas de listado: por departamento y por rubro.

    /trabajos-en/junin/     "Trabajos en Junín con sueldo a la vista"
    /trabajos-de/ventas/    "Trabajos de Ventas con sueldo a la vista"

(El archivo se llama `lugares` porque nació con las de departamento. Se le
sumaron las de rubro en vez de duplicar la plantilla entera: son la misma
página con otro eje, y tenerlas juntas evita que se desincronicen.)

POR QUÉ EXISTEN
---------------
Es lo que la gente escribe en Google —"trabajo en Arequipa", "empleos en
Cusco"— y hasta ahora el sitio no tenía nada que pudiera aparecer para eso. La
portada compite por "ofertas de trabajo Perú", que es una pelea contra
Computrabajo y Bumeran; "trabajos en Huancavelica con sueldo" no la pelea
nadie.

POR QUÉ NO EXISTÍAN ANTES
-------------------------
Porque no había con qué llenarlas. Al 8 de agosto solo Lima pasaba de cinco
ofertas publicadas y las páginas de provincia habrían nacido vacías — y una
página casi vacía le dice a Google que el sitio es de baja calidad, señal que
mancha al resto. Era peor que no tenerlas.

Lo que cambió fue partir las convocatorias CAS de varios puestos (8/8/2026):
la oferta de provincia pasó de 24 a 73 ofertas en un día, y de un departamento
con volumen a cuatro.

LAS DOS REGLAS QUE LAS GOBIERNAN
--------------------------------
1. **Aparecen y desaparecen solas.** Un departamento con menos de
   `MINIMO_OFERTAS` no tiene página, y si baja de ahí la suya se borra. No es
   opcional: las convocatorias CAS duran una o dos semanas, así que un
   departamento puede pasar de 29 ofertas a 6 en quince días. Es la misma
   regla 4 de las ofertas vencidas — lo que ya no tiene contenido no se queda
   indexado.

2. **Cada página trae algo que solo nosotros tenemos.** Además de la lista de
   ofertas, dice cuántos avisos se revisaron en ese departamento y cuántos
   declaraban sueldo. Sin eso sería un listado más, y un listado más no merece
   existir.
"""
from __future__ import annotations

import html
from pathlib import Path

from .almacen import Almacen
from .modelos import sin_tildes

# Cuántas ofertas publicadas necesita un departamento para tener página propia.
# Es el mismo número que reporta `motor stats` con sus ✓.
MINIMO_OFERTAS = 5

CARPETA = "trabajos-en"

# Los rubros llevan piso más alto, y no es capricho: una página de "trabajos de
# ventas" compite contra todas las bolsas del Perú, mientras que "trabajos en
# Huancavelica" no compite con casi nadie. Donde la pelea es dura hay que
# llegar con más que cinco avisos.
MINIMO_RUBRO = 8
CARPETA_RUBROS = "trabajos-de"


def _e(t) -> str:
    return html.escape(str(t or ""), quote=True)


def _soles(n: int) -> str:
    return f"S/ {n:,}"


def _plano(nombre: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "-", sin_tildes(nombre)).strip("-")


def ruta(departamento: str) -> str:
    """'San Martín' -> 'trabajos-en/san-martin'"""
    return f"{CARPETA}/{_plano(departamento)}"


def ruta_rubro(rubro: str) -> str:
    """'Atención al Cliente' -> 'trabajos-de/atencion-al-cliente'"""
    return f"{CARPETA_RUBROS}/{_plano(rubro)}"


def _mediano(ofertas: list[dict]) -> int:
    montos = sorted(o["sueldo_min"] for o in ofertas if o.get("sueldo_min"))
    return montos[len(montos) // 2] if montos else 0


def _tarjeta(o: dict, sitio: str, slug: str) -> str:
    sueldo = _soles(o["sueldo_min"]) if o.get("sueldo_min") else ""
    if o.get("sueldo_max") and o["sueldo_max"] != o["sueldo_min"]:
        sueldo += f" – {_soles(o['sueldo_max'])}"
    lugar = " · ".join(x for x in (o.get("ciudad"), o.get("modalidad")) if x)
    return (
        f'<li class="oferta">'
        f'<a href="{_e(sitio)}/oferta/{_e(slug)}/">'
        f'<b>{_e(o["puesto"])}</b>'
        f'<span class="empresa">{_e(o.get("empresa") or "Empresa confidencial")}</span>'
        f'<span class="donde">{_e(lugar)}</span>'
        f'<span class="pago">{_e(sueldo)}</span>'
        f"</a></li>"
    )


# Lo único que distingue una página de departamento de una de rubro: la
# preposición del titular, la carpeta y cómo se nombra al conjunto. Todo lo
# demás —la plantilla, el dato de transparencia, los vecinos— es igual, y por
# eso viven juntas.
EJES = {
    "lugar": {"preposicion": "en", "ruta": ruta,
              "carpeta": CARPETA, "vecinos": "departamentos"},
    "rubro": {"preposicion": "de", "ruta": ruta_rubro,
              "carpeta": CARPETA_RUBROS, "vecinos": "rubros"},
}


def pagina(datos: dict, sitio: str, slugs: dict[str, str],
           otros: list[str], eje: str = "lugar") -> str:
    """
    La página de un departamento o de un rubro.

    `slugs` traduce la huella de cada oferta a la dirección de su ficha; se
    calcula en `sitio.py`, que es quien manda en eso, para que las dos no se
    desincronicen (regla 3: la dirección sale de la huella, no de la posición).
    """
    from .sitio import bloque_analitica, csp

    forma = EJES[eje]
    ruta_de = forma["ruta"]
    prep = forma["preposicion"]

    depa = datos.get("nombre") or datos["departamento"]
    total = datos["total"]
    url = f"{sitio}/{ruta_de(depa)}/"
    mediano = _mediano(datos["ofertas"])

    titulo = f"Trabajos {prep} {depa} con sueldo a la vista"
    descripcion = (
        f"{total} ofertas de trabajo {prep} {depa}, todas con el sueldo "
        f"publicado, funciones y requisitos. Revisamos {datos['revisados']} "
        f"avisos: {datos['pct_sin_sueldo']}% no dice cuánto paga."
    )

    filas = "".join(
        _tarjeta(o, sitio, slugs[o["huella"]])
        for o in datos["ofertas"] if o.get("huella") in slugs
    )

    vecinos = ""
    if otros:
        enlaces = " · ".join(
            f'<a href="{_e(sitio)}/{ruta_de(d)}/">{_e(d)}</a>' for d in otros)
        vecinos = (f'<p class="vecinos">Trabajos con sueldo en otros '
                   f'{forma["vecinos"]}: {enlaces}</p>')

    return f"""<!DOCTYPE html>
<html lang="es-PE">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<title>{_e(titulo)} | Cero Vagos</title>
<meta name="description" content="{_e(descripcion)}">
<link rel="canonical" href="{_e(url)}">
<meta property="og:type" content="website">
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
<style>{ESTILOS}</style>
{bloque_analitica()}
</head>
<body>

<div class="barra"><div class="wrap">
  <a href="{_e(sitio)}/" class="volver">
    <img src="{_e(sitio)}/assets/logo-mono.svg" alt="Cero Vagos">
    <span>← Volver a las ofertas</span>
  </a>
</div></div>

<header class="hero">
  <div class="wrap">
    <h1>Trabajos {prep}<br>{_e(depa)}</h1>
    <p>{total} ofertas con el sueldo a la vista. Ninguna dice "a convenir":
    si un aviso no publica cuánto paga, no entra a Cero Vagos.</p>
    <div class="cifras">
      <div><b>{total}</b><span>ofertas publicadas</span></div>
      {f'<div><b>{_soles(mediano)}</b><span>sueldo mediano</span></div>' if mediano else ''}
      <div><b>{datos['pct_sin_sueldo']}%</b><span>de los avisos {prep} {_e(depa)} no dice cuánto paga</span></div>
    </div>
  </div>
</header>

<section>
  <div class="wrap">
    <h2>Las {total} ofertas</h2>
    <ul class="ofertas">{filas}</ul>
  </div>
</section>

<section class="dato">
  <div class="wrap">
    <h2>Lo que encontramos {prep} {_e(depa)}</h2>
    <p>Nuestro motor revisó <b>{datos['revisados']} avisos de empleo</b>
    {prep} {_e(depa)}. Solo <b>{datos['con_sueldo']}</b> decían cuánto pagan — el resto
    pide tu CV, tu tiempo y tres entrevistas sin decirte el sueldo.</p>
    <p>Los {total} que ves arriba son los que además traen requisitos y
    beneficios escritos. <a href="{_e(sitio)}/transparencia/">Mira el conteo
    completo, empresa por empresa →</a></p>
    {vecinos}
  </div>
</section>

<footer><div class="wrap">
  <b>Cero Vagos</b> — el buscador que solo muestra ofertas laborales completas
  del Perú. <a href="{_e(sitio)}/#ofertas">Ver todas las ofertas →</a>
</div></footer>

</body>
</html>
"""


ESTILOS = """
:root{color-scheme:light;--rojo:#FF1E1E;--negro:#0B0B0B;--crema:#FFF3E4;--blanco:#fff;
--amarillo:#FFD100;--lima:#B8FF2E;--bd:3px solid var(--negro);
--display:'Archivo Black','Arial Black',system-ui,sans-serif;
--body:'Space Grotesk',system-ui,-apple-system,sans-serif}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:var(--body);background:var(--crema);color:var(--negro);
background-image:linear-gradient(rgba(11,11,11,.045) 1px,transparent 1px),
linear-gradient(90deg,rgba(11,11,11,.045) 1px,transparent 1px);background-size:44px 44px}
h1,h2{font-family:var(--display);text-transform:uppercase;letter-spacing:-.02em;line-height:1}
a{color:inherit}
.wrap{max-width:900px;margin:0 auto;padding:0 18px}
.barra{background:var(--rojo);color:#fff;border-bottom:var(--bd);padding:12px 0}
.barra a{text-decoration:none}
.barra .volver{display:inline-flex;align-items:center;gap:14px}
.barra .volver img{width:auto;height:34px;display:block;flex:0 0 auto}
.barra .volver span{font-family:var(--display);font-size:12.5px;letter-spacing:.05em;
text-transform:uppercase;border-bottom:2px solid rgba(255,255,255,.55);padding-bottom:2px}
@media(max-width:560px){.barra .volver img{height:27px}.barra .volver span{font-size:11px}}
.hero{border-bottom:var(--bd);background:var(--negro);color:#fff;padding:52px 0 40px}
.hero h1{font-size:clamp(32px,7vw,62px);color:#fff;margin-bottom:18px}
.hero p{font-size:17px;font-weight:500;line-height:1.5;max-width:620px;opacity:.9}
.cifras{display:flex;flex-wrap:wrap;gap:14px;margin-top:26px}
.cifras div{border:3px solid #fff;padding:14px 18px;flex:0 1 auto;max-width:100%}
.cifras b{font-family:var(--display);font-size:30px;display:block;line-height:1}
.cifras span{font-size:12.5px;font-weight:700;text-transform:uppercase;
letter-spacing:.03em;display:block;margin-top:6px;max-width:220px;line-height:1.3}
section{padding:40px 0;border-bottom:var(--bd)}
section h2{font-size:clamp(20px,3.2vw,30px);margin-bottom:20px}
.ofertas{list-style:none;display:grid;gap:12px}
.oferta a{display:grid;gap:4px;border:var(--bd);background:var(--blanco);
padding:15px 18px;text-decoration:none;box-shadow:4px 4px 0 var(--negro)}
.oferta a:hover{background:var(--amarillo)}
.oferta b{font-family:var(--display);font-size:16px;line-height:1.2}
.oferta .empresa{font-size:14px;font-weight:700}
.oferta .donde{font-size:13px;font-weight:500;opacity:.7}
.oferta .pago{font-family:var(--display);font-size:19px;margin-top:4px}
.dato{background:var(--amarillo)}
.dato p{font-size:16px;line-height:1.6;font-weight:500;margin-bottom:12px;max-width:680px}
.vecinos{font-size:14.5px;margin-top:22px}
.vecinos a{font-weight:700}
footer{padding:26px 0;font-size:14px;font-weight:500}
footer a{font-weight:700}
"""


INICIO_LUGARES = "<!-- LUGARES:INICIO -->"
FIN_LUGARES = "<!-- LUGARES:FIN -->"


def bloque_para_la_portada(departamentos: list[str], sitio: str,
                           rubros: list[str] = ()) -> str:
    """
    Los enlaces del pie de la portada hacia cada página de departamento.

    No es decoración: sin un enlace desde la portada, Google llega a estas
    páginas solo por el sitemap —que es una invitación, no una orden— y les da
    menos peso. Y quien entra buscando trabajo en provincia no se entera de que
    existen.

    Se escribe entre marcadores porque **cuáles existen cambia cada día**: un
    departamento que baja de 5 ofertas pierde su página, y un enlace escrito a
    mano quedaría apuntando a un 404.
    """
    if not departamentos and not rubros:
        return f"{INICIO_LUGARES}\n{FIN_LUGARES}"

    def columna(titulo: str, nombres, ruta_de, prep: str) -> str:
        if not nombres:
            return ""
        filas = "\n".join(
            f'          <li><a href="{_e(sitio)}/{ruta_de(n)}/">'
            f'Trabajos {prep} {_e(n)}</a></li>'
            for n in nombres
        )
        return f"        <h4>{titulo}</h4>\n        <ul>\n{filas}\n        </ul>\n"

    return (f"{INICIO_LUGARES}\n"
            + columna("Por departamento", departamentos, ruta, "en")
            + columna("Por rubro", rubros, ruta_rubro, "de")
            + f"        {FIN_LUGARES}")


def _escribir(grupos: list[dict], sitio: str, raiz: Path,
              slugs: dict[str, str], eje: str) -> list[str]:
    """
    Escribe una página por grupo y borra las de los que ya no llegan al mínimo.

    Ese borrado NO es opcional. Las convocatorias CAS duran una o dos semanas,
    así que un departamento con 29 ofertas puede quedar en 3 quince días
    después. Una página indexada sin contenido le dice a Google que el sitio es
    de baja calidad, y esa señal mancha al resto: es la misma regla 4 de las
    ofertas vencidas.
    """
    import shutil

    forma = EJES[eje]
    ruta_de = forma["ruta"]
    nombres = [g["nombre"] for g in grupos]
    # La carpeta sale de la constante del eje, NO del primer grupo. Sacándola
    # del primero, una corrida sin ningún grupo que llegue al mínimo no tenía
    # carpeta que limpiar y las páginas viejas se quedaban publicadas para
    # siempre — que es justo el caso que la limpieza existe para cubrir.
    carpeta = raiz / forma["carpeta"]

    for datos in grupos:
        nombre = datos["nombre"]
        # Los vecinos son enlaces internos entre páginas hermanas: ayudan a que
        # Google las encuentre y a que quien entra por una vea que hay más.
        otros = [n for n in nombres if n != nombre][:8]
        destino = raiz / ruta_de(nombre)
        destino.mkdir(parents=True, exist_ok=True)
        (destino / "index.html").write_text(
            pagina(datos, sitio, slugs, otros, eje), encoding="utf-8")

    if carpeta.exists():
        vigentes = {ruta_de(n).split("/")[-1] for n in nombres}
        for vieja in carpeta.iterdir():
            if vieja.is_dir() and vieja.name not in vigentes:
                shutil.rmtree(vieja, ignore_errors=True)

    return nombres


def generar(almacen: Almacen, sitio: str, raiz: Path,
            slugs: dict[str, str]) -> dict[str, list[str]]:
    """
    Escribe las páginas de listado: por departamento y por rubro.

    Devuelve los NOMBRES publicados de cada eje, de más a menos ofertas. La
    dirección de cada uno se saca con `ruta()` o `ruta_rubro()`, para que no
    haya dos formas de armarla.
    """
    # Con las ofertas al día, Lima es el 77% del sitio. Su página igual se
    # publica: apunta a otra búsqueda que la portada ("trabajos en Lima con
    # sueldo" frente a "ofertas de trabajo Perú"), tiene su propio título y
    # trae un dato que no está en ningún otro lado — cuántos avisos de Lima
    # revisamos y cuántos escondían el sueldo.
    lugares = _escribir(almacen.por_departamento(MINIMO_OFERTAS),
                        sitio, raiz, slugs, "lugar")
    # "Otros" no entra: es el cajón de lo que el motor no supo clasificar, y
    # nadie busca "trabajos de otros". Lo filtra `por_rubro`.
    rubros = _escribir(almacen.por_rubro(MINIMO_RUBRO),
                       sitio, raiz, slugs, "rubro")
    return {"lugares": lugares, "rubros": rubros}
