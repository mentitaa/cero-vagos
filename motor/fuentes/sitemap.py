"""
Lector de sitemaps.

Es la forma más limpia de descubrir avisos: el propio portal declara sus URLs
y cuándo se actualizaron. Nada de paginar resultados de búsqueda.

Soporta índices de sitemaps (sitemapindex), archivos .gz y el filtro por
lastmod para no volver a mirar avisos viejos.
"""
from __future__ import annotations

import gzip
import io
import re
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta

NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def _texto_de(contenido: bytes) -> str:
    if contenido[:2] == b"\x1f\x8b":                  # gzip
        with gzip.GzipFile(fileobj=io.BytesIO(contenido)) as f:
            contenido = f.read()
    return contenido.decode("utf-8", errors="replace")


def _limpiar_url(valor: str | None) -> str:
    """
    Quita TODOS los espacios en blanco, no solo los de los extremos.

    Hay generadores de sitemap que parten la URL en dos líneas:

        <loc>https://ejemplo.pe
        /convocatorias/algo</loc>

    Un simple .strip() deja el salto de línea en medio y el resultado es un
    dominio inválido ('ejemplo.pe%0a'). Esto lo une de nuevo.
    """
    return re.sub(r"\s+", "", valor or "")


def _fecha(valor: str | None) -> date | None:
    if not valor:
        return None
    try:
        return datetime.fromisoformat(valor.strip().replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return datetime.strptime(valor.strip()[:10], "%Y-%m-%d").date()
        except ValueError:
            return None


def parsear(contenido: bytes | str) -> dict[str, list]:
    """
    Devuelve {'urls': [(loc, lastmod), ...], 'sitemaps': [loc, ...]}
    Funciona tanto con <urlset> como con <sitemapindex>.
    """
    texto = _texto_de(contenido) if isinstance(contenido, bytes) else contenido
    salida: dict[str, list] = {"urls": [], "sitemaps": []}

    try:
        raiz = ET.fromstring(texto.strip())
    except ET.ParseError:
        # Algunos portales sirven el sitemap con basura antes del XML.
        recorte = texto[texto.find("<"):]
        try:
            raiz = ET.fromstring(recorte)
        except ET.ParseError:
            # Último recurso: sacar los <loc> con regex.
            salida["urls"] = [
                (_limpiar_url(u), None) for u in re.findall(r"<loc>(.*?)</loc>", texto, re.S)
            ]
            return salida

    etiqueta = raiz.tag.split("}")[-1]
    if etiqueta == "sitemapindex":
        for nodo in raiz.findall("sm:sitemap", NS) or raiz:
            loc = nodo.find("sm:loc", NS)
            if loc is not None and _limpiar_url(loc.text):
                salida["sitemaps"].append(_limpiar_url(loc.text))
    else:
        for nodo in raiz.findall("sm:url", NS) or raiz:
            loc = nodo.find("sm:loc", NS)
            mod = nodo.find("sm:lastmod", NS)
            if loc is not None and _limpiar_url(loc.text):
                salida["urls"].append(
                    (_limpiar_url(loc.text), _fecha(mod.text if mod is not None else None))
                )

    return salida


def filtrar_recientes(
    urls: list[tuple[str, date | None]],
    dias: int = 30,
    incluir_sin_fecha: bool = True,
) -> list[str]:
    """
    Deja solo los avisos actualizados dentro de la ventana que publicamos, y los
    devuelve **del más reciente al más viejo**.

    Lo segundo importa tanto como lo primero. Un sitemap grande trae decenas de
    miles de direcciones y de ahí solo se revisan las primeras doscientas y
    pico: si vienen en el orden en que el portal las escribió, esas doscientas
    son las más antiguas del archivo. Es lo que le pasaba a Laborum — el
    5/8/2026 revisó 240 avisos y 237 salieron con más de 3 días de publicados,
    así que la corrida diaria no traía ni uno.

    Ojo con qué se hace con el `lastmod`: sirve para **priorizar**, nunca para
    decidir. Dice cuándo el portal tocó la página, no cuándo se publicó el
    aviso; usarlo como veredicto es lo que una vez dejó la corrida en cero. La
    fecha de verdad se lee después, en la propia página.

    Las direcciones sin fecha van al final, no se descartan: no saber cuándo se
    tocó una página no es lo mismo que saber que es vieja.
    """
    corte = date.today() - timedelta(days=dias)
    con_fecha: list[tuple[str, date]] = []
    sin_fecha: list[str] = []
    for loc, mod in urls:
        if mod is None:
            if incluir_sin_fecha:
                sin_fecha.append(loc)
        elif mod >= corte:
            con_fecha.append((loc, mod))

    con_fecha.sort(key=lambda par: par[1], reverse=True)
    return [loc for loc, _ in con_fecha] + sin_fecha
