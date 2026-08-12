"""
Mantener vivas las fechas de las muestras.

EL PROBLEMA QUE ESTO RESUELVE
-----------------------------
Las muestras de `pruebas/muestras/` son copias de páginas reales, y una
convocatoria real trae una fecha límite escrita: "10 de agosto de 2026".

El motor descarta lo que ya cerró — es su trabajo, y bien hecho. Pero un test
que use esa muestra tal cual **pasa hasta el 10 de agosto y falla para siempre
desde el 11**. No porque algo se rompiera: porque pasó el tiempo.

Ocurrió: el 12 de agosto de 2026 tres tests llevaban dos días en rojo y nadie
lo había notado, porque el fallo no coincidió con ningún cambio de código. Ese
es el peor tipo de test roto — el que se rompe solo y hace dudar de lo que sí
está bien.

La regla, entonces: **una muestra con fecha no se usa cruda.** Se le reescribe
el plazo respecto de hoy, y así el test comprueba lo que dice comprobar en vez
de comprobar qué día es.
"""
from __future__ import annotations

import re
from datetime import date, timedelta

MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "setiembre", "octubre", "noviembre", "diciembre")

# "10 de agosto de 2026" y "17 de Agosto del 2026" — las dos formas que usan
# los portales de convocatorias.
_FECHA_LARGA = r"\d{1,2}\s+de\s+[A-Za-zÁÉÍÓÚáéíóú]+\s+de[l]?\s+\d{4}"

# Solo se toca la fecha que va DETRÁS de una etiqueta de plazo. Una muestra
# trae también la fecha de publicación —"21 de julio de 2026"— y reescribirla
# rompería los tests que comprueban justo ese dato. La primera versión de este
# archivo cambiaba todas las fechas y eso fue exactamente lo que pasó.
_PLAZO = re.compile(
    r"(fecha\s+l[íi]mite|plazo\s+para\s+postular)(.{0,160}?)(" + _FECHA_LARGA + ")",
    re.I | re.S)


def _escrita(cuando: date) -> str:
    return f"{cuando.day} de {MESES[cuando.month - 1]} de {cuando.year}"


def con_plazo(html: str, cuando: date) -> str:
    """Reescribe la fecha límite de la muestra con la que se le pida."""
    nueva = _escrita(cuando)
    return _PLAZO.sub(lambda m: m.group(1) + m.group(2) + nueva, html)


def abierto(html: str, dias: int = 10) -> str:
    """La muestra, con su plazo vigente. Es la que se usa casi siempre."""
    return con_plazo(html, date.today() + timedelta(days=dias))


def cerrado(html: str, dias: int = 1) -> str:
    """La muestra, con el plazo ya vencido. Para probar que NO se publica."""
    return con_plazo(html, date.today() - timedelta(days=dias))
