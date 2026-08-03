"""
Cumplimiento de robots.txt.

Antes de pedir cualquier URL, el recolector consulta el robots.txt del dominio
y respeta su crawl-delay. Si no se puede leer el robots.txt, asumimos que NO
tenemos permiso: para un negocio que vive de estos datos, salir a raspar a
ciegas no vale el riesgo.

Se implementa el parser a mano porque `urllib.robotparser` ignora los comodines:
para él una regla `Disallow: /empleos/aptitus/*` no bloquea nada, y hoy casi
todos los portales escriben sus reglas con `*` y `$`. Aquí se sigue la
especificación de Google: gana la regla que hace el match más largo y, a igual
longitud, gana Allow.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from urllib.parse import unquote, urlparse

from .base import PAUSA_ENTRE_PETICIONES, USER_AGENT

try:
    import requests
except ImportError:                                   # pragma: no cover
    requests = None


# --------------------------------------------------------------------------
# Parser
# --------------------------------------------------------------------------

@dataclass
class Regla:
    permitido: bool
    patron: str
    regex: re.Pattern

    @property
    def peso(self) -> int:
        return len(self.patron)


def _a_regex(patron: str) -> re.Pattern:
    """'/empleos/*.html$' -> regex. Solo '*' y '$' son especiales."""
    fin = patron.endswith("$")
    cuerpo = patron[:-1] if fin else patron
    partes = [re.escape(p) for p in cuerpo.split("*")]
    return re.compile("^" + ".*".join(partes) + ("$" if fin else ""))


@dataclass
class Reglas:
    """Las reglas que aplican a nuestro agente en un dominio."""
    reglas: list[Regla] = field(default_factory=list)
    crawl_delay: float | None = None
    sitemaps: list[str] = field(default_factory=list)
    grupo: str = "*"

    def permite(self, ruta: str) -> bool:
        ruta = unquote(ruta) or "/"
        candidatas = [r for r in self.reglas if r.regex.match(ruta)]
        if not candidatas:
            return True                                # lo no prohibido, permitido
        mejor = max(candidatas, key=lambda r: (r.peso, r.permitido))
        return mejor.permitido


def parsear_robots(texto: str, agente: str = USER_AGENT) -> Reglas:
    """
    Devuelve las reglas del grupo que nos corresponde: el que nombra a nuestro
    bot si existe, y si no el grupo '*'.
    """
    token = agente.split("/")[0].strip().lower()

    grupos: dict[str, list[tuple[bool, str]]] = {}
    demoras: dict[str, float] = {}
    sitemaps: list[str] = []
    agentes_actuales: list[str] = []
    esperando_agente = True

    for linea_cruda in texto.splitlines():
        linea = linea_cruda.split("#", 1)[0].strip()
        if not linea or ":" not in linea:
            continue
        campo, valor = linea.split(":", 1)
        campo, valor = campo.strip().lower(), valor.strip()

        if campo == "user-agent":
            if not esperando_agente:
                agentes_actuales = []
                esperando_agente = True
            agentes_actuales.append(valor.lower())
            grupos.setdefault(valor.lower(), [])
        elif campo == "sitemap":
            # Hay robots.txt que parten la URL en dos líneas. Si la anterior
            # quedó incompleta (sin ruta), se le pega esta.
            sitemaps.append(re.sub(r"\s+", "", valor))
        elif campo in ("allow", "disallow") and agentes_actuales:
            esperando_agente = False
            if valor:                                  # 'Disallow:' vacío = permite todo
                for ag in agentes_actuales:
                    grupos[ag].append((campo == "allow", valor))
            elif campo == "disallow":
                for ag in agentes_actuales:
                    grupos[ag].append((True, "/"))
        elif campo == "crawl-delay" and agentes_actuales:
            esperando_agente = False
            try:
                for ag in agentes_actuales:
                    demoras[ag] = float(valor)
            except ValueError:
                pass

    # ¿Nos nombran directamente? Si no, usamos el grupo comodín.
    elegido = next((ag for ag in grupos if ag and ag != "*" and ag in token), None)
    if elegido is None:
        elegido = "*" if "*" in grupos else None

    crudas = grupos.get(elegido, []) if elegido is not None else []
    return Reglas(
        reglas=[Regla(p, pat, _a_regex(pat)) for p, pat in crudas],
        crawl_delay=demoras.get(elegido or "*"),
        sitemaps=sitemaps,
        grupo=elegido or "(ninguno)",
    )


# --------------------------------------------------------------------------
# Política por dominio
# --------------------------------------------------------------------------

@dataclass
class Politica:
    dominio: str
    legible: bool = False            # ¿pudimos leer su robots.txt?
    reglas: Reglas | None = None
    crawl_delay: float = PAUSA_ENTRE_PETICIONES
    sitemaps: list[str] = field(default_factory=list)
    nota: str = ""

    def permite(self, url: str) -> bool:
        if not self.legible or self.reglas is None:
            return False
        partes = urlparse(url)
        ruta = partes.path or "/"
        if partes.query:
            ruta += "?" + partes.query
        return self.reglas.permite(ruta)


class Robots:
    """Cachea una política por dominio y espacia las peticiones."""

    def __init__(self, agente: str = USER_AGENT, estricto: bool = True):
        self.agente = agente
        self.estricto = estricto
        self._cache: dict[str, Politica] = {}
        self._ultimo_pedido: dict[str, float] = {}

    def politica(self, url: str) -> Politica:
        partes = urlparse(url)
        dominio = partes.netloc
        if dominio in self._cache:
            return self._cache[dominio]

        pol = Politica(dominio=dominio)
        if requests is None:
            pol.nota = "Falta la librería 'requests'"
            self._cache[dominio] = pol
            return pol

        try:
            resp = requests.get(
                f"{partes.scheme or 'https'}://{dominio}/robots.txt",
                headers={"User-Agent": self.agente},
                timeout=15,
            )
        except Exception as e:                        # noqa: BLE001
            pol.nota = f"No se pudo leer robots.txt ({e})"
            self._cache[dominio] = pol
            return pol

        texto = resp.text or ""
        if resp.status_code >= 500:
            pol.nota = f"robots.txt devolvió {resp.status_code}: se trata como NO permitido"
        elif resp.status_code == 404:
            pol.legible, pol.reglas = True, Reglas()
            pol.nota = "Sin robots.txt (404): se permite, pero vamos despacio"
        elif not texto.strip():
            pol.nota = ("robots.txt vacío o bloqueado (típico de WAF/Cloudflare): "
                        "se trata como NO permitido")
        else:
            reglas = parsear_robots(texto, self.agente)
            pol.reglas, pol.legible = reglas, True
            pol.sitemaps = reglas.sitemaps
            pol.crawl_delay = max(float(reglas.crawl_delay or 0), PAUSA_ENTRE_PETICIONES)
            pol.nota = f"OK (grupo '{reglas.grupo}', {len(reglas.reglas)} reglas)"

        self._cache[dominio] = pol
        return pol

    def permite(self, url: str) -> bool:
        pol = self.politica(url)
        if not self.estricto and not pol.legible:
            return True
        return pol.permite(url)

    def esperar_turno(self, url: str) -> None:
        """Respeta el crawl-delay del dominio entre petición y petición."""
        dominio = urlparse(url).netloc
        pol = self.politica(url)
        falta = pol.crawl_delay - (time.monotonic() - self._ultimo_pedido.get(dominio, 0.0))
        if falta > 0:
            time.sleep(falta)
        self._ultimo_pedido[dominio] = time.monotonic()

    def informe(self) -> list[str]:
        return [
            f"{p.dominio:<28} {'permite' if p.legible else 'BLOQUEA':<8} "
            f"delay {p.crawl_delay:>4.1f}s  {p.nota}"
            for p in self._cache.values()
        ]
