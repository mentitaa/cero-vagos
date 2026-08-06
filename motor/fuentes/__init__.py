"""Adaptadores de portales de empleo."""
from .base import ErrorFuente, Fuente
from .cas import ConvocatoriasCAS, convocatorias_cas, parsear_cas, plazas_en_url
from .demo import FuenteDemo
from .jsonld import extraer_jobposting
from .empresas import (
    Greenhouse, Lever, como_conectar, detectar_ats, empresas_peru, portal_propio,
)
from .portal_web import Diagnostico, PortalWeb, fuentes_por_verificar, portales_peru
from .publicas import BENEFICIOS_POR_REGIMEN, convocatorias_estado, parsear_convocatoria
from .render import HAY_PLAYWRIGHT
from .robots import Robots, parsear_robots
from .sitemap import filtrar_recientes, parsear


def fuentes_de_arranque() -> list[PortalWeb]:
    """
    Con lo que se llena la web al inicio: solo fuentes verificadas, HTML
    server-side, sin navegador headless y con el sueldo casi siempre declarado.
    """
    fuentes, vistos = [], set()
    # Convocatorias CAS va primera a propósito: es la que trae convocatorias
    # abiertas. convocape.com resultó ser un archivo (413 de sus 512
    # direcciones con el plazo cerrado), así que aporta poco y tarda mucho.
    for f in convocatorias_cas() + convocatorias_estado():
        if f.nombre not in vistos:
            vistos.add(f.nombre)
            fuentes.append(f)
    return fuentes


__all__ = [
    "Fuente", "ErrorFuente", "FuenteDemo", "Diagnostico",
    "PortalWeb", "portales_peru", "fuentes_por_verificar", "fuentes_de_arranque",
    "convocatorias_estado", "parsear_convocatoria", "BENEFICIOS_POR_REGIMEN",
    "ConvocatoriasCAS", "convocatorias_cas", "parsear_cas", "plazas_en_url",
    "extraer_jobposting", "Robots", "parsear_robots", "parsear", "filtrar_recientes",
    "HAY_PLAYWRIGHT",
    "Greenhouse", "Lever", "empresas_peru", "portal_propio",
    "detectar_ats", "como_conectar",
]
