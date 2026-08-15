"""
Lector de Trabajos Diarios (pe.trabajosdiarios.com).

POR QUÉ ESTA FUENTE VALE EL TRABAJO
-----------------------------------
Sondeada el 13/8/2026, y es la mejor fuente privada que ha aparecido:

- **67% de sus avisos declara el sueldo.** Bumeran y Laborum están en 23%.
- **Y lo declaran con el periodo pegado**: "S/ 1,200 / Mensual", "S/ 100 /
  Diario". Eso no es un detalle: el sueldo de S/ 33,800 que se publicó por
  error salió justo de deducir si un monto era diario o mensual.
- **Traen fecha de cierre.** Casi ningún portal peruano la da, y sin ella hay
  que adivinar cuándo caduca una oferta.
- Se lee sin navegador, es HTML servido de una, y tiene 2,837 avisos activos.
- **No es un agregador**: las empresas publican ahí directamente y el botón de
  postular se queda en su sitio. Cumple la regla 5.
- Su robots.txt nos deja entrar (`Allow: /`, `Crawl-delay: 2`). Lo que bloquea
  son los bots de entrenamiento de IA; su propia etiqueta dice `search=yes,
  use=reference`, que es exactamente lo que hacemos: indexar y enlazar al
  aviso original.

QUÉ ARREGLA ESTE ARCHIVO
------------------------
Sus avisos SÍ traen los datos en el formato de Google (JSON-LD), y de ahí
salen bien el puesto, la empresa, la ciudad, el sueldo y las dos fechas. Pero
la descripción que ponen ahí es **el resumen corto**, el que sale recortado con
"…" en los resultados de búsqueda. Una sola línea.

Con eso el motor leía "Hola ! Importante empresa del rubro ferretero…" y nada
más: cero funciones, cero requisitos, cero beneficios, y los avisos se caían
sin excepción. Los doce del sondeo salieron en 0/0/0 — un patrón demasiado
parejo para venir de los avisos, que es lo que delató que el problema era del
lector y no de la fuente.

El cuerpo completo sí está en la página, bajo el título "Descripción del
empleo". Este lector toma todo lo bueno del JSON-LD y le cambia solo la
descripción por la de verdad.
"""
from __future__ import annotations

import re

from ..modelos import OfertaCruda
from .jsonld import extraer_jobposting

# Los dos títulos que encierran el cuerpo del aviso. Se aceptan con tilde, sin
# tilde y con la tilde escapada (`&oacute;`), porque las tres formas aparecen
# según cómo esté escrita la página.
_O = r"(?:ó|&oacute;|&#243;|o)"
_INICIO = re.compile(rf"Descripci{_O}n\s+del\s+empleo", re.I)
_FIN = re.compile(rf"Resumen\s+de\s+empleo|Acerca\s+de\s+la\s+empresa|"
                  rf"Empleos\s+Relacionados", re.I)


def cuerpo_del_aviso(html: str) -> str:
    """
    Devuelve el HTML que va entre "Descripción del empleo" y el siguiente
    título de la página.

    Se corta por los TÍTULOS y no por las etiquetas del maquetado a propósito.
    Un rediseño cambia las etiquetas cada tanto; el título "Descripción del
    empleo" es lo que lee la persona que entra, y ese no lo mueven sin querer.
    """
    if not html:
        return ""
    abre = _INICIO.search(html)
    if not abre:
        return ""
    resto = html[abre.end():]
    cierra = _FIN.search(resto)
    return resto[:cierra.start()] if cierra else resto


def parsear(html: str, url: str, fuente: str) -> OfertaCruda | None:
    """
    JSON-LD para los datos, la página para el texto.

    No se reemplaza el JSON-LD entero: de ahí salen el sueldo con su moneda,
    la fecha de publicación y la de cierre, todos ya normalizados. Lo único
    que ese bloque tiene mal es la descripción.
    """
    cruda = extraer_jobposting(html, url, fuente)
    if cruda is None:
        return None

    completo = cuerpo_del_aviso(html)
    # Solo se pisa si lo que se encontró es MÁS que lo que ya había. Si un día
    # cambian los títulos de la página, el aviso se queda con el resumen corto
    # —y se caerá por incompleto, que es el error correcto— en vez de quedarse
    # sin ninguna descripción.
    if len(completo) > len(cruda.descripcion_html or ""):
        cruda.descripcion_html = completo

    cruda.extra.setdefault("perfil", "privado")
    return cruda
