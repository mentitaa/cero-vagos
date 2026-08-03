"""
Adaptador universal basado en datos estructurados.

Casi todos los portales serios (Bumeran, Laborum, los agregadores de
convocatorias y las webs propias de las empresas) publican cada aviso con un
bloque JSON-LD de tipo schema.org/JobPosting, porque Google Jobs lo exige.

Leer ese bloque es más estable y más limpio que raspar el HTML: los selectores
CSS cambian cada dos meses, el JSON-LD casi nunca.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime
from typing import Any

from ..modelos import OfertaCruda

_BLOQUE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.S | re.I,
)


def _aplanar(nodo: Any) -> list[dict]:
    """JSON-LD viene como dict, lista o @graph. Lo dejamos en una lista plana."""
    salida: list[dict] = []
    if isinstance(nodo, list):
        for n in nodo:
            salida += _aplanar(n)
    elif isinstance(nodo, dict):
        if "@graph" in nodo:
            salida += _aplanar(nodo["@graph"])
        else:
            salida.append(nodo)
    return salida


def _fecha(valor: Any) -> date | None:
    if not valor or not isinstance(valor, str):
        return None
    texto = valor.strip().replace("Z", "+00:00")
    for parser in (datetime.fromisoformat, lambda t: datetime.strptime(t[:10], "%Y-%m-%d")):
        try:
            return parser(texto).date()
        except (ValueError, TypeError):
            continue
    return None


def _texto(valor: Any) -> str:
    if isinstance(valor, str):
        return valor
    if isinstance(valor, dict):
        return str(valor.get("name") or valor.get("value") or "")
    if isinstance(valor, list) and valor:
        return _texto(valor[0])
    return ""


def _ubicacion(nodo: dict) -> str:
    lugar = nodo.get("jobLocation")
    if isinstance(lugar, list):
        lugar = lugar[0] if lugar else {}
    if not isinstance(lugar, dict):
        return _texto(lugar)
    direccion = lugar.get("address", {})
    if isinstance(direccion, str):
        return direccion
    partes = [
        direccion.get("addressLocality", ""),
        direccion.get("addressRegion", ""),
    ]
    return ", ".join(p for p in partes if p)


def _sueldo_texto(nodo: dict) -> str:
    """
    baseSalary de schema.org, cuando existe, es la fuente más confiable.
    Lo devolvemos como texto para que lo lea el parser de sueldos.
    """
    bs = nodo.get("baseSalary")
    if not isinstance(bs, dict):
        return _texto(bs)

    moneda = bs.get("currency") or bs.get("currencyCode") or "PEN"
    valor = bs.get("value", {})
    if isinstance(valor, (int, float, str)):
        return f"{'S/' if moneda == 'PEN' else 'US$'} {valor}"
    if not isinstance(valor, dict):
        return ""

    unidad = str(valor.get("unitText", "MONTH")).upper()
    periodo = {"HOUR": "por hora", "DAY": "diario", "WEEK": "semanal",
               "MONTH": "mensual", "YEAR": "anual"}.get(unidad, "mensual")
    simbolo = "S/" if moneda == "PEN" else "US$"

    minimo, maximo = valor.get("minValue"), valor.get("maxValue")
    if minimo and maximo:
        return f"{simbolo} {minimo} a {simbolo} {maximo} {periodo}"
    unico = valor.get("value") or minimo or maximo
    return f"{simbolo} {unico} {periodo}" if unico else ""


def _modalidad_texto(nodo: dict) -> str:
    tipo = _texto(nodo.get("jobLocationType"))
    return "remoto" if "TELECOMMUTE" in tipo.upper() else ""


def extraer_jobposting(html: str, url: str, fuente: str) -> OfertaCruda | None:
    """Lee la página de un aviso y devuelve la OfertaCruda, o None si no hay JSON-LD."""
    for bruto in _BLOQUE.findall(html or ""):
        try:
            datos = json.loads(bruto.strip())
        except json.JSONDecodeError:
            # Algunos portales meten comentarios o comas colgantes.
            limpio = re.sub(r",\s*([}\]])", r"\1", bruto.strip())
            try:
                datos = json.loads(limpio)
            except json.JSONDecodeError:
                continue

        for nodo in _aplanar(datos):
            if str(nodo.get("@type", "")).lower() != "jobposting":
                continue

            empresa = nodo.get("hiringOrganization", {})
            empresa = empresa.get("name", "") if isinstance(empresa, dict) else _texto(empresa)

            return OfertaCruda(
                fuente=fuente,
                url=url,
                puesto=_texto(nodo.get("title")).strip(),
                empresa=str(empresa).strip(),
                descripcion_html=nodo.get("description", "") or "",
                ubicacion_texto=f"{_ubicacion(nodo)} {_modalidad_texto(nodo)}".strip(),
                sueldo_texto=_sueldo_texto(nodo),
                publicado=_fecha(nodo.get("datePosted")),
                id_externo=str(nodo.get("identifier", {}).get("value", "")
                               if isinstance(nodo.get("identifier"), dict)
                               else nodo.get("identifier", "")),
                extra={
                    "tipo_empleo": _texto(nodo.get("employmentType")),
                    "vence": nodo.get("validThrough", ""),
                },
            )
    return None
