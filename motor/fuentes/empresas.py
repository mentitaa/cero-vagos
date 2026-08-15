"""
Portales de empleo de las propias empresas.

La idea es buena: si la oferta sale de la web oficial de Interbank, Alicorp o
una minera, no hay intermediario, no hay aviso vencido colgado seis meses y no
hay consultora que esconda para quién es el puesto.

El detalle que casi nadie nota: **la mayoría de empresas grandes no programa su
bolsa de trabajo**. Contrata un sistema de reclutamiento (un ATS) y ese sistema
publica los avisos. Los más usados en el Perú son Workday, SAP SuccessFactors,
Greenhouse, Lever y Avature.

Eso cambia la estrategia por completo: en vez de escribir un lector por empresa
—que se rompe cada vez que rediseñan la web— se escribe uno por ATS y sirve
para todas las empresas que usen ese ATS. Cinco lectores cubren cientos de
empresas.

Greenhouse y Lever tienen API pública documentada y devuelven JSON limpio.
Workday y SuccessFactors se leen por su endpoint interno o por el JSON-LD que
publican para Google Jobs.
"""
from __future__ import annotations

import json
import re
from collections.abc import Iterator
from datetime import date, datetime

from ..modelos import OfertaCruda
from .base import USER_AGENT, ErrorFuente, Fuente
from .jsonld import extraer_jobposting
from .portal_web import PortalWeb
from .robots import Robots

try:
    import requests
except ImportError:                                   # pragma: no cover
    requests = None


# --------------------------------------------------------------------------
# Detección del ATS
# --------------------------------------------------------------------------

HUELLAS_ATS = {
    "greenhouse": ("boards.greenhouse.io", "greenhouse.io/embed", "grnhse"),
    "lever": ("jobs.lever.co", "lever.co/postings"),
    "workday": ("myworkdayjobs.com", "wd1.myworkday", "wd3.myworkday", "wd5.myworkday"),
    "successfactors": ("successfactors.com", "career_ns=job_listing", "sfcareer"),
    "cornerstone": (".csod.com", "cornerstoneondemand"),
    "gupy": (".gupy.io",),
    "avature": ("avature.net",),
    "smartrecruiters": ("smartrecruiters.com",),
    "icims": ("icims.com",),
    "taleo": ("taleo.net",),
}


def detectar_ats(html_o_url: str) -> str:
    """Devuelve el nombre del ATS detectado, o '' si parece web propia."""
    texto = (html_o_url or "").lower()
    for ats, huellas in HUELLAS_ATS.items():
        if any(h in texto for h in huellas):
            return ats
    return ""


# --------------------------------------------------------------------------
# Greenhouse y Lever: API pública, JSON limpio
# --------------------------------------------------------------------------

def _pedir_json(url: str, robots: Robots) -> object:
    if requests is None:
        raise ErrorFuente("Falta 'requests' (pip install requests)")
    if not robots.permite(url):
        raise ErrorFuente(f"robots.txt no permite {url}")
    robots.esperar_turno(url)
    resp = requests.get(url, headers={"User-Agent": USER_AGENT,
                                      "Accept": "application/json"}, timeout=25)
    resp.raise_for_status()
    return resp.json()


def _fecha(valor) -> date | None:
    if not valor:
        return None
    try:
        if isinstance(valor, (int, float)):            # Lever usa milisegundos
            return datetime.fromtimestamp(valor / 1000).date()
        return datetime.fromisoformat(str(valor).replace("Z", "+00:00")).date()
    except (ValueError, OSError, OverflowError):
        return None


class Greenhouse(Fuente):
    """
    API: https://boards-api.greenhouse.io/v1/boards/<empresa>/jobs?content=true
    El 'content' viene como HTML con las secciones del aviso ya separadas.
    """

    def __init__(self, empresa: str, nombre: str = "", pausa: float = 1.5):
        self.tablero = empresa
        self.nombre = nombre or empresa.title()
        self.pausa = pausa
        self.robots = Robots()
        self.errores: list[str] = []

    @property
    def activa(self) -> bool:                          # type: ignore[override]
        return requests is not None

    @activa.setter
    def activa(self, _v: bool) -> None:
        pass

    def recolectar(self, limite: int = 100) -> Iterator[OfertaCruda]:
        url = f"https://boards-api.greenhouse.io/v1/boards/{self.tablero}/jobs?content=true"
        try:
            datos = _pedir_json(url, self.robots)
        except Exception as e:                         # noqa: BLE001
            self.errores.append(f"{self.nombre}: {e}")
            return

        import html as _html
        for puesto in (datos or {}).get("jobs", [])[:limite]:
            yield OfertaCruda(
                fuente=self.nombre,
                url=puesto.get("absolute_url", ""),
                puesto=puesto.get("title", "").strip(),
                empresa=self.nombre,
                descripcion_html=_html.unescape(puesto.get("content", "")),
                ubicacion_texto=(puesto.get("location") or {}).get("name", ""),
                publicado=_fecha(puesto.get("updated_at")),
                id_externo=str(puesto.get("id", "")),
                extra={"ats": "greenhouse"},
            )


class Lever(Fuente):
    """API: https://api.lever.co/v0/postings/<empresa>?mode=json"""

    def __init__(self, empresa: str, nombre: str = "", pausa: float = 1.5):
        self.tablero = empresa
        self.nombre = nombre or empresa.title()
        self.pausa = pausa
        self.robots = Robots()
        self.errores: list[str] = []

    @property
    def activa(self) -> bool:                          # type: ignore[override]
        return requests is not None

    @activa.setter
    def activa(self, _v: bool) -> None:
        pass

    def recolectar(self, limite: int = 100) -> Iterator[OfertaCruda]:
        url = f"https://api.lever.co/v0/postings/{self.tablero}?mode=json"
        try:
            datos = _pedir_json(url, self.robots)
        except Exception as e:                         # noqa: BLE001
            self.errores.append(f"{self.nombre}: {e}")
            return

        for puesto in (datos or [])[:limite]:
            partes = [puesto.get("descriptionPlain", "")]
            for bloque in puesto.get("lists", []):
                partes.append(f"<p>{bloque.get('text','')}</p>{bloque.get('content','')}")
            yield OfertaCruda(
                fuente=self.nombre,
                url=puesto.get("hostedUrl", ""),
                puesto=puesto.get("text", "").strip(),
                empresa=self.nombre,
                descripcion_html="".join(partes),
                ubicacion_texto=(puesto.get("categories") or {}).get("location", ""),
                sueldo_texto=(puesto.get("salaryRange") or {}).get("min", "") and
                             f"{(puesto.get('salaryRange') or {}).get('currency','')} "
                             f"{(puesto.get('salaryRange') or {}).get('min','')} a "
                             f"{(puesto.get('salaryRange') or {}).get('max','')}",
                publicado=_fecha(puesto.get("createdAt")),
                id_externo=str(puesto.get("id", "")),
                extra={"ats": "lever"},
            )


# --------------------------------------------------------------------------
# Web propia de la empresa (sin ATS conocido)
# --------------------------------------------------------------------------

def portal_propio(nombre: str, base: str, **kw) -> PortalWeb:
    """
    Bolsa de trabajo hecha a medida por la empresa. Se lee con el mismo
    mecanismo que los portales: sitemap o listado + JSON-LD.
    """
    kw.setdefault("patron_aviso", r"/(empleo|empleos|vacante|vacantes|oportunidad|"
                                  r"oportunidades|job|jobs|carrera|careers|trabaja)[^\"'\s]*")
    kw.setdefault("nota", "SIN VERIFICAR. Bolsa propia de la empresa.")
    return PortalWeb(nombre, base, **kw)


# --------------------------------------------------------------------------
# Empresas candidatas
# --------------------------------------------------------------------------

def empresas_peru() -> list[Fuente]:
    """
    Bolsas de trabajo del sector privado, revisadas el 3 de agosto de 2026.

    Lo importante no es esta lista sino el criterio con que se arma: en el Perú
    las marcas no contratan, contratan los GRUPOS. McDonald's es Arcos Dorados,
    KFC y Pizza Hut son Delosi, Sodimac y Tottus son Falabella, Metro y Wong son
    Cencosud. Perseguir marcas es perseguir cuarenta puertas que llevan a diez
    casas. Ver EMPRESAS.md para el mapa completo.
    """
    return [
        # Grupo Falabella NO está acá, y no es un olvido.
        #
        # Se revisó su portal a ojo el 13/8/2026 y se cae por tres razones
        # independientes: ningún aviso declara el sueldo (regla 1), todos
        # dicen "5 Months Ago" —el filtro bota lo de más de 60 días, así que
        # no entraría ni uno— y los títulos nombran la tienda y hasta la hora
        # de la entrevista, pero no el oficio (regla 8).
        #
        # Dejarlo configurado "por si acaso" costaría veinte minutos de
        # navegador cada madrugada para traer cero. Ver EMPRESAS.md.
        # Cencosud (Metro, Wong) tampoco, y por lo mismo: revisado a ojo el
        # 13/8/2026, no publica sueldos.
        #
        # Con Falabella y Cencosud caídos el mismo día —más Delosi, que publica
        # en Computrabajo y nos bloquea— el retail corporativo del Perú queda
        # cerrado. La lección no es sobre estos dos portales sino sobre el eje:
        # ir por GRUPOS busca volumen, y el volumen nunca fue lo escaso. Una
        # marca fuerte no compite por sueldo, así que no lo publica. Ver
        # EMPRESAS.md › El retail corporativo se cierra.
    ]


# --------------------------------------------------------------------------
# Ayuda para dar de alta una empresa nueva
# --------------------------------------------------------------------------

def como_conectar(url_bolsa: str) -> str:
    """
    Dice qué lector usar para la bolsa de trabajo de una empresa.
    Pensado para correrse desde el CLI antes de escribir una línea de código.
    """
    if requests is None:
        return "Falta 'requests' (pip install requests)"

    robots = Robots()
    if not robots.permite(url_bolsa):
        pol = robots.politica(url_bolsa)
        return f"No se puede leer: {pol.nota}"

    robots.esperar_turno(url_bolsa)
    try:
        html = requests.get(url_bolsa, headers={"User-Agent": USER_AGENT},
                            timeout=25).text
    except Exception as e:                             # noqa: BLE001
        return f"No respondió: {e}"

    ats = detectar_ats(url_bolsa) or detectar_ats(html)
    if ats == "greenhouse":
        m = re.search(r"greenhouse\.io/(?:embed/job_board\?for=|boards/)?([a-z0-9_-]+)", html, re.I)
        cuenta = m.group(1) if m else "<cuenta>"
        return f"Usa Greenhouse. Agrega:  Greenhouse('{cuenta}', 'Nombre de la empresa')"
    if ats == "lever":
        m = re.search(r"lever\.co/([a-z0-9_-]+)", html, re.I)
        cuenta = m.group(1) if m else "<cuenta>"
        return f"Usa Lever. Agrega:  Lever('{cuenta}', 'Nombre de la empresa')"
    if ats == "cornerstone":
        m = re.search(r"careersite/(\d+)", html) or re.search(r"careersite/(\d+)", url_bolsa)
        sitio = m.group(1) if m else "<n>"
        return (f"Usa Cornerstone OnDemand (careersite {sitio}). Los avisos se piden "
                f"por su API interna; revisá qué llama la página antes de raspar.")
    if ats == "gupy":
        m = re.search(r"https?://([a-z0-9-]+)\.gupy\.io", url_bolsa + html, re.I)
        cuenta = m.group(1) if m else "<cuenta>"
        return (f"Usa Gupy ({cuenta}.gupy.io). Expone los avisos en JSON; "
                f"vale la pena escribirle un lector, sirve para varias empresas.")
    if ats:
        return (f"Usa {ats}. No hay lector directo todavía; probá si la página del "
                f"aviso trae JSON-LD (motor probar-url --parser jsonld <url del aviso>).")

    if extraer_jobposting(html, url_bolsa, "prueba"):
        return "Web propia con JSON-LD. Usa portal_propio(...) y funcionará sin más."
    if "enable JavaScript" in html or len(html) < 2000:
        return "Web propia hecha en JavaScript: necesita Playwright (necesita_render=True)."
    return ("Web propia sin JSON-LD: hay que revisar el HTML a mano y escribirle "
            "un parser, o pedirle a la empresa un feed.")
