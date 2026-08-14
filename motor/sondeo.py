"""
Sondear una bolsa de trabajo ANTES de escribirle un lector.

Este archivo existe por dos errores que costaron tiempo y que fueron el mismo
error dos veces: dar por buena una fuente sin contar lo que tiene dentro.

- **BuscoTrabajo** estuvo semanas en la lista de pendientes como "la gran
  fuente privada que falta". Era verdad que su robots.txt nos deja entrar y que
  es la única peruana fuera del grupo Jobint. Nadie contó los avisos: tiene
  **4 empleos activos**, tres de ellos de la misma empresa.
- **Las bolsas universitarias** tenían 501 empresas y 8,287 vacantes, y se
  descartaron igual: **ninguna publica el sueldo**. Verificarlo tomó una tarde;
  escribir el lector habría tomado una semana.

De ahí salen las tres preguntas que decide toda fuente nueva, en este orden:

    1. ¿Nos dejan entrar?          (robots.txt — la regla 6)
    2. ¿Cuántos avisos hay?        (una fuente con 4 avisos no es una fuente)
    3. ¿Cuántos dicen el sueldo?   (la regla 1: sin sueldo no hay nada que hacer)

`motor conectar` contesta la primera. Este archivo contesta las tres, y la
tercera la contesta **con el filtro de verdad**, no con una aproximación: cada
aviso que baja pasa por `procesar_cruda`, el mismo código que decide qué se
publica cada madrugada. Así el sondeo no puede prometer más de lo que la
corrida real va a entregar.

No guarda nada. No toca la base. Se puede correr las veces que haga falta.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .fuentes.base import Fuente
from .fuentes.empresas import Greenhouse, Lever, detectar_ats, portal_propio
from .fuentes.render import HAY_PLAYWRIGHT
from .fuentes.robots import Robots
from .pipeline import procesar_cruda

try:
    import requests
except ImportError:                                   # pragma: no cover
    requests = None


# --------------------------------------------------------------------------
# El resultado
# --------------------------------------------------------------------------

@dataclass
class Aviso:
    """Un aviso del sondeo, ya pasado por el filtro de verdad."""
    puesto: str
    sueldo: int
    moneda: str
    aprobada: bool
    motivos: list[str] = field(default_factory=list)

    @property
    def dice_sueldo(self) -> bool:
        return self.sueldo > 0


@dataclass
class Sondeo:
    url: str
    permite: bool = False
    nota_robots: str = ""
    ats: str = ""
    como_esta_hecha: str = ""
    avisos: list[Aviso] = field(default_factory=list)
    problema: str = ""

    # --- los tres números que deciden ---------------------------------------

    @property
    def cuantos(self) -> int:
        return len(self.avisos)

    @property
    def con_sueldo(self) -> list[Aviso]:
        return [a for a in self.avisos if a.dice_sueldo]

    @property
    def publicables(self) -> list[Aviso]:
        return [a for a in self.avisos if a.aprobada]

    @property
    def porcentaje_con_sueldo(self) -> int:
        return round(100 * len(self.con_sueldo) / self.cuantos) if self.cuantos else 0

    @property
    def vale_la_pena(self) -> bool:
        """
        El sondeo NO decide por nadie: decide Mentita. Pero hay un caso en el
        que no hay nada que decidir, y es el de BuscoTrabajo y el de las
        universidades: si de una muestra razonable no sale ni un solo aviso
        con sueldo, escribir el lector es trabajo perdido antes de empezar.
        """
        return bool(self.con_sueldo)

    @property
    def motivos_mas_comunes(self) -> list[tuple[str, int]]:
        from collections import Counter
        cuenta = Counter(m for a in self.avisos for m in a.motivos)
        return cuenta.most_common(5)


# --------------------------------------------------------------------------
# Armar el lector que corresponda, sin escribir código nuevo
# --------------------------------------------------------------------------

def _cuenta_de(patron: str, texto: str) -> str:
    m = re.search(patron, texto, re.I)
    return m.group(1) if m else ""


# Cómo se llama la página de UN aviso, según quién armó la bolsa. La lista
# larga es a propósito: cada sistema de reclutamiento le puso otro nombre a la
# misma cosa, y si el sondeo no reconoce el nombre no encuentra ni un aviso y
# reporta un cero que parece una medición y no lo es.
#   requisition / req  → Cornerstone, Taleo
#   job / jobs         → Greenhouse, Lever, SmartRecruiters
#   posting            → Workday
#   vacante / puesto   → webs peruanas a medida
_PATRON_AVISO = (r"/(empleo|empleos|vacante|vacantes|oportunidad|oportunidades|"
                 r"job|jobs|posting|postings|requisition|req|posicion|posiciones|"
                 r"puesto|puestos|carrera|careers|trabaja|detalle)[^\"'\s]*")


def _generico(url: str, nombre: str, con_navegador: bool) -> Fuente:
    base = re.match(r"https?://[^/]+", url)
    return portal_propio(nombre, base.group(0) if base else url,
                         listados=(url,), necesita_render=con_navegador,
                         patron_aviso=_PATRON_AVISO)


def elegir_lector(url: str, html: str, nombre: str = "") -> tuple[Fuente | None, str]:
    """
    Devuelve el lector que sirve para esa bolsa y una frase que explica cómo
    está hecha. Si no hay forma de mirar adentro, devuelve (None, explicación).

    La primera versión de esto se rendía en dos casos —"está hecha en
    JavaScript" y "ese sistema no tiene lector escrito"— y con eso se negó a
    contar Falabella y Cencosud, que son justamente las dos bolsas grandes que
    había que medir. Era un sondeo que solo sabía sondear lo fácil.

    Y era un error tonto, porque **el navegador ya estaba**: Bumeran y Laborum
    se leen con Playwright todas las madrugadas. Lo que falta no es la
    herramienta sino usarla acá.

    Para mirar adentro no hace falta el lector definitivo. Un aviso de empleo
    bien hecho publica sus datos en el formato que pide Google (JSON-LD), y eso
    se lee igual venga de Cornerstone, de Workday o de una web a medida. Si el
    sondeo alcanza a contar los avisos y ver los sueldos, ya contestó la
    pregunta; el lector rápido y prolijo se escribe DESPUÉS, y solo si la
    respuesta fue que sí.
    """
    nombre = nombre or "Sondeo"
    ats = detectar_ats(url) or detectar_ats(html)
    necesita_js = "enable JavaScript" in html or len(html) < 2000

    if ats == "greenhouse":
        cuenta = _cuenta_de(r"greenhouse\.io/(?:embed/job_board\?for=|boards/)?"
                            r"([a-z0-9_-]+)", url + " " + html)
        if cuenta:
            return Greenhouse(cuenta, nombre), "Greenhouse (API pública)"

    if ats == "lever":
        cuenta = _cuenta_de(r"lever\.co/([a-z0-9_-]+)", url + " " + html)
        if cuenta:
            return Lever(cuenta, nombre), "Lever (API pública)"

    if not ats and not necesita_js:
        return _generico(url, nombre, False), "Web propia, se lee sin navegador"

    # Todo lo demás —un ATS sin lector propio, o una página que se arma sola en
    # el navegador— se mira con Playwright y JSON-LD.
    como = (f"{ats.title()}: sin lector propio todavía, se mira con navegador"
            if ats else "Aplicación en JavaScript, se mira con navegador")

    if not HAY_PLAYWRIGHT:
        return None, (f"{como.split(',')[0]}. Falta el navegador. Instalalo con:\n"
                      f"       pip3 install playwright && python3 -m playwright "
                      f"install chromium")

    return _generico(url, nombre, True), como


# --------------------------------------------------------------------------
# El sondeo
# --------------------------------------------------------------------------

def sondear(url: str, limite: int = 25, nombre: str = "") -> Sondeo:
    s = Sondeo(url=url)

    if requests is None:
        s.problema = "Falta 'requests' (pip install requests)"
        return s

    robots = Robots()
    s.permite = robots.permite(url)
    politica = robots.politica(url)
    s.nota_robots = getattr(politica, "nota", "") or ""
    if not s.permite:
        # La regla 6: si no se puede leer el robots.txt, se asume que no hay
        # permiso. Un "no contestó" tampoco es un "sí".
        s.problema = f"No se puede entrar: {s.nota_robots}"
        return s

    robots.esperar_turno(url)
    try:
        from .fuentes.base import USER_AGENT
        html = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=25).text
    except Exception as e:                             # noqa: BLE001
        s.problema = f"No respondió: {e}"
        return s

    s.ats = detectar_ats(url) or detectar_ats(html)
    fuente, s.como_esta_hecha = elegir_lector(url, html, nombre)
    if fuente is None:
        s.problema = s.como_esta_hecha
        return s

    try:
        for cruda in fuente.recolectar(limite):
            oferta = procesar_cruda(cruda)
            s.avisos.append(Aviso(
                puesto=oferta.puesto or cruda.puesto,
                sueldo=oferta.sueldo_min,
                moneda=oferta.moneda,
                aprobada=oferta.aprobada,
                motivos=list(oferta.motivos_rechazo),
            ))
    except Exception as e:                             # noqa: BLE001
        s.problema = f"Se pudo entrar pero no leer los avisos: {e}"

    return s


# --------------------------------------------------------------------------
# Cómo se cuenta en pantalla
# --------------------------------------------------------------------------

def _plata(a: Aviso) -> str:
    simbolo = "US$" if a.moneda == "USD" else "S/"
    return f"{simbolo} {a.sueldo:,}" if a.sueldo else "no dice"


def informe(s: Sondeo) -> str:
    """El sondeo dicho en una pantalla, sin jerga."""
    lineas = [f"Sondeo de {s.url}", ""]

    lineas.append(f"  ¿Nos dejan entrar?    {'sí' if s.permite else 'NO'}")
    if s.como_esta_hecha:
        lineas.append(f"  Cómo está hecha       {s.como_esta_hecha}")

    if s.problema:
        lineas += ["", f"  ⚠  {s.problema}", ""]
        if not s.avisos:
            lineas.append("  No se pudo contar nada. Antes de escribir un lector,")
            lineas.append("  hay que resolver esto.")
            return "\n".join(lineas)

    lineas.append(f"  Avisos que encontró   {s.cuantos}")
    lineas.append(f"  Dicen el sueldo       {len(s.con_sueldo)} de {s.cuantos}"
                  f"  ({s.porcentaje_con_sueldo}%)")
    lineas.append(f"  Se publicarían        {len(s.publicables)}")

    if s.con_sueldo:
        lineas += ["", "  Los que sí dicen cuánto pagan:"]
        for a in s.con_sueldo[:8]:
            marca = "publicable" if a.aprobada else "le falta algo más"
            lineas.append(f"    · {a.puesto[:48]:48}  {_plata(a):>12}   {marca}")

    if s.motivos_mas_comunes:
        lineas += ["", "  Por qué se caen los demás:"]
        for motivo, veces in s.motivos_mas_comunes:
            lineas.append(f"    {veces:3}  {motivo}")

    lineas += ["", "  " + _veredicto(s)]
    return "\n".join(lineas)


def _veredicto(s: Sondeo) -> str:
    if not s.cuantos:
        return "No hay avisos que contar. No escribas el lector."
    if not s.con_sueldo:
        return ("NINGUNO dice el sueldo. Es la historia de las bolsas "
                "universitarias: no escribas el lector.")
    if s.porcentaje_con_sueldo < 10:
        return (f"Solo {s.porcentaje_con_sueldo}% dice el sueldo. De cada 100 "
                f"avisos saldrían {s.porcentaje_con_sueldo}. Decide si "
                f"compensa el trabajo.")
    return (f"{s.porcentaje_con_sueldo}% dice el sueldo. Vale la pena "
            f"escribirle el lector.")
