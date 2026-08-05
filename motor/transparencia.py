"""
La página de transparencia salarial.

Es el mejor contenido que tiene el proyecto y sale gratis de datos que ya
están en la base: de todos los avisos que el motor revisó, cuántos dicen
cuánto pagan y cuántos no. Después, quién.

Sirve para tres cosas a la vez:
  · atrae búsquedas ("qué empresas publican el sueldo en Perú")
  · da material para compartir en redes y grupos de empleo
  · demuestra el argumento de la marca con datos propios, no con una opinión

Reglas que se respetan al publicarla, porque señalar empresas exige cuidado:
  · Solo se cuenta lo que el motor revisó, y se dice el periodo exacto.
  · Ninguna empresa aparece con menos de N avisos: con dos no se afirma nada.
  · No se califica a nadie de mentiroso. Se publica un conteo verificable.
"""
from __future__ import annotations

import html
from datetime import date
from pathlib import Path

from .almacen import Almacen

MINIMO_AVISOS = 3


def _e(t) -> str:
    return html.escape(str(t or ""), quote=True)


def _fecha_larga(iso: str) -> str:
    meses = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
             "agosto", "setiembre", "octubre", "noviembre", "diciembre")
    try:
        d = date.fromisoformat(iso[:10])
        return f"{d.day} de {meses[d.month - 1]} de {d.year}"
    except (ValueError, IndexError):
        return iso


def _barra(pct: int) -> str:
    color = "var(--lima)" if pct >= 80 else "var(--amarillo)" if pct >= 30 else "var(--rojo)"
    return (f'<div class="barra"><div class="barra__i" '
            f'style="width:{max(pct, 2)}%;background:{color}"></div></div>')


def _tabla(titulo: str, filas: list[dict], columna: str = "Empresa") -> str:
    if not filas:
        return ""
    cuerpo = "".join(
        f"<tr><td>{_e(f['nombre'])}</td>"
        f"<td class=\"num\">{f['total']}</td>"
        f"<td class=\"num\">{f['con_sueldo']}</td>"
        f"<td class=\"pct\">{_barra(f['pct'])}<b>{f['pct']}%</b></td></tr>"
        for f in filas
    )
    return f"""
    <h3>{_e(titulo)}</h3>
    <div class="tabla-envoltura">
      <table>
        <thead><tr><th>{_e(columna)}</th><th class="num">Avisos</th>
          <th class="num">Con sueldo</th><th>Transparencia</th></tr></thead>
        <tbody>{cuerpo}</tbody>
      </table>
    </div>"""


ESTILOS = """
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
.wrap{max-width:900px;margin:0 auto;padding:0 18px}
.barra-sup{background:var(--rojo);color:#fff;border-bottom:var(--bd);padding:12px 0;
font-family:var(--display);font-size:12px;letter-spacing:.06em;text-transform:uppercase}
.barra-sup a{text-decoration:none}
/* El logo solo no se entiende como "volver": mucha gente no sabe que se le
   puede dar clic. El texto al lado lo dice sin ambigüedad. */
.barra-sup .volver{display:inline-flex;align-items:center;gap:14px}
.barra-sup .volver img{width:auto;height:34px;display:block;flex:0 0 auto}
.barra-sup .volver span{font-family:var(--display);font-size:12.5px;
letter-spacing:.05em;text-transform:uppercase;border-bottom:2px solid rgba(255,255,255,.55);
padding-bottom:2px}
.barra-sup .volver:hover span{border-bottom-color:#fff}
@media(max-width:560px){.barra-sup .volver img{height:27px}
.barra-sup .volver span{font-size:11px}}
.hero{border-bottom:var(--bd);background:var(--negro);color:#fff;padding:52px 0 46px}
/* Título a la izquierda, el dato a la derecha. En pantallas angostas se
   apilan solos: el dato queda debajo, que es donde se lee mejor. */
.hero__reja{display:flex;align-items:center;justify-content:space-between;gap:38px;flex-wrap:wrap}
.hero__reja>div:first-child{flex:1 1 380px;min-width:0}
.hero h1{font-size:clamp(30px,6vw,58px);color:#fff;margin-bottom:18px}
.hero p{font-size:17px;font-weight:500;line-height:1.5;max-width:640px;opacity:.9}
/* El recuadro se ajusta al número: antes ocupaba todo el ancho y quedaba
   medio vacío. Ahora el porcentaje y su explicación van uno al lado del otro. */
.cifra{display:inline-flex;align-items:center;gap:22px;border:3px solid #fff;
background:var(--rojo);color:#fff;box-shadow:9px 9px 0 #fff;
padding:20px 28px;flex:0 0 auto;max-width:100%}
.cifra b{font-family:var(--display);font-size:clamp(46px,9vw,76px);line-height:.85}
.cifra span{font-size:14.5px;font-weight:700;text-transform:uppercase;
letter-spacing:.03em;line-height:1.35;max-width:230px}
@media(max-width:520px){.cifra{gap:14px;padding:16px 20px}.cifra span{font-size:13px}}
section{padding:40px 0;border-bottom:var(--bd)}
section h2{font-size:clamp(22px,3.4vw,34px);margin-bottom:8px}
section .sub{font-size:15px;font-weight:500;line-height:1.5;margin-bottom:22px;max-width:640px}
h3{font-size:15px;margin:26px 0 12px}
.tabla-envoltura{border:var(--bd);background:var(--blanco);box-shadow:5px 5px 0 var(--negro);overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:14px}
th{background:var(--negro);color:#fff;font-family:var(--display);font-size:11px;
text-transform:uppercase;letter-spacing:.04em;padding:10px 12px;text-align:left}
td{padding:9px 12px;border-bottom:2px solid #e8e0d4;font-weight:500}
tr:last-child td{border-bottom:none}
.num{text-align:right;white-space:nowrap}
.pct{white-space:nowrap;display:flex;align-items:center;gap:9px;min-width:150px}
.pct b{font-family:var(--display);font-size:13px}
.barra{flex:1;height:11px;border:2px solid var(--negro);background:var(--blanco);min-width:56px}
.barra__i{height:100%}
.nota{border:var(--bd);background:var(--blanco);padding:20px 22px;margin-top:26px;
font-size:14.5px;line-height:1.55;font-weight:500}
.compartir{background:var(--amarillo)}
.compartir .caja{border:var(--bd);background:var(--blanco);padding:18px 20px;margin-bottom:14px;
font-size:15px;line-height:1.5;font-weight:500}
.btn{display:inline-block;border:var(--bd);background:var(--rojo);color:#fff;
font-family:var(--display);font-size:14px;text-transform:uppercase;padding:14px 22px;
text-decoration:none;box-shadow:4px 4px 0 var(--negro);margin-top:8px}
footer{padding:26px 0;font-size:13px;font-weight:500}
@media(max-width:600px){.cifra{box-shadow:5px 5px 0 #fff}}
"""


def pagina(datos: dict, sitio: str) -> str:
    url = f"{sitio}/transparencia/"
    periodo = (f"entre el {_fecha_larga(datos['desde'])} y el {_fecha_larga(datos['hasta'])}"
               if datos["desde"] and datos["desde"] != datos["hasta"]
               else f"el {_fecha_larga(datos['hasta'])}")

    titulo = (f"{datos['pct_sin_sueldo']}% de las ofertas de trabajo en Perú "
              f"no dice cuánto paga")
    descripcion = (f"Revisamos {datos['total']:,} avisos de empleo en portales peruanos: "
                   f"{datos['sin_sueldo']:,} no declaran sueldo. Ranking de qué empresas "
                   f"sí publican cuánto pagan y cuáles no.").replace(",", ",")

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
<link rel="icon" href="{_e(sitio)}/assets/icono-32.png" sizes="32x32" type="image/png">
<link rel="apple-touch-icon" href="{_e(sitio)}/assets/icono-180.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo+Black&family=Space+Grotesk:wght@400;500;700&display=swap" rel="stylesheet">
<style>{ESTILOS}</style>
</head>
<body>

<div class="barra-sup"><div class="wrap">
  <a href="{_e(sitio)}/" class="volver">
    <img src="{_e(sitio)}/assets/logo-mono.svg" alt="Cero Vagos">
    <span>← Volver a las ofertas</span>
  </a>
</div></div>

<header class="hero">
  <div class="wrap hero__reja">
    <div>
      <h1>¿Quién dice<br>cuánto paga?</h1>
      <p>Nuestro motor revisa cada día los avisos de empleo publicados en el Perú.
      Este es el conteo de cuántos declaran el sueldo y cuántos lo esconden, empresa
      por empresa. No es una opinión: es contar.</p>
    </div>
    <div class="cifra">
      <b>{datos['pct_sin_sueldo']}%</b>
      <span>de los avisos revisados no dice cuánto paga</span>
    </div>
  </div>
</header>

<section>
  <div class="wrap">
    <h2>Las que sí lo dicen</h2>
    <p class="sub">Empresas cuyos avisos declaran el sueldo en al menos 8 de cada 10 casos.
    Si estás buscando trabajo, empieza por acá.</p>
    {_tabla("", datos["transparentes"]) or "<p class='sub'>Todavía no hay suficientes datos.</p>"}
  </div>
</section>

<section>
  <div class="wrap">
    <h2>Las que nunca lo dicen</h2>
    <p class="sub">Empresas con {datos['minimo_avisos']} o más avisos revisados, ninguno con
    el monto a la vista. Postular ahí es aceptar una entrevista sin saber si el sueldo
    te alcanza.</p>
    {_tabla("", datos["opacas"]) or "<p class='sub'>Todavía no hay suficientes datos.</p>"}
  </div>
</section>

<section>
  <div class="wrap">
    <h2>Por sector y por portal</h2>
    <p class="sub">Dónde se esconde más el sueldo.</p>
    {_tabla("Por rubro", datos["por_categoria"], "Rubro")}
    {_tabla("Por portal de origen", datos["por_fuente"], "Portal")}
    {_tabla("Por ciudad", datos["por_ciudad"], "Ciudad")}
  </div>
</section>

<section>
  <div class="wrap">
    <h2>Cómo se hizo</h2>
    <div class="nota">
      <p><b>Qué se contó.</b> {datos['total']:,} avisos de empleo recolectados {periodo}
      de portales peruanos. De cada uno se revisó si declaraba un monto en soles.
      Un aviso que dice "sueldo a convenir" o "acorde al mercado" cuenta como
      <i>no declara</i>, porque para quien postula es lo mismo que no decir nada.</p>
      <p style="margin-top:12px"><b>Quién aparece.</b> Solo empresas con
      {datos['minimo_avisos']} o más avisos revisados. Con uno o dos no se puede
      afirmar nada de nadie.</p>
      <p style="margin-top:12px"><b>Qué NO dice esto.</b> Que una empresa no publique
      el sueldo no significa que pague mal ni que sea un mal lugar para trabajar.
      Significa que no lo dice antes de que mandes tu CV.</p>
      <p style="margin-top:12px">¿Eres una empresa de esta lista y quieres cambiar de
      columna? Publica el sueldo en tu próximo aviso. Aparecerás al día siguiente.</p>
    </div>
  </div>
</section>

<section class="compartir">
  <div class="wrap">
    <h2>Para compartir</h2>
    <p class="sub">Copia y pega donde quieras.</p>
    <div class="caja">Revisamos {datos['total']:,} ofertas de trabajo publicadas en el Perú.
    {datos['pct_sin_sueldo']}% no dice cuánto paga. Si vas a pedirle a alguien su CV, su tiempo
    y tres entrevistas, lo mínimo es decirle cuánto vas a pagarle.</div>
    <div class="caja">Buscar trabajo en Perú es postular a ciegas: de cada 10 avisos,
    {round(datos['pct_sin_sueldo'] / 10)} esconden el sueldo. Hicimos un buscador que
    solo muestra los que sí lo dicen.</div>
    <div class="caja">Ya sabemos qué empresas publican cuánto pagan y cuáles nunca.
    La lista completa, actualizada cada día 👇</div>
    <a class="btn" href="{_e(sitio)}/#ofertas">Ver las ofertas con sueldo →</a>
  </div>
</section>

<footer><div class="wrap">
  <b>Cero Vagos</b> — el buscador que solo muestra ofertas laborales completas del Perú.
  Datos actualizados cada día.
</div></footer>

</body>
</html>
"""


def generar(almacen: Almacen | None = None, sitio: str = "", raiz: Path | None = None) -> dict:
    from .sitio import RAIZ, sitio_publicado

    raiz = raiz or RAIZ
    sitio = (sitio or sitio_publicado(raiz)).rstrip("/")
    al = almacen or Almacen()

    datos = al.transparencia(MINIMO_AVISOS)
    destino = raiz / "transparencia"
    destino.mkdir(parents=True, exist_ok=True)
    (destino / "index.html").write_text(pagina(datos, sitio), encoding="utf-8")

    return {"archivo": str(destino / "index.html"), **datos}
