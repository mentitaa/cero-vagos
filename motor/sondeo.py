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

UNA COSA QUE HAY QUE DARLE BIEN
-------------------------------
La dirección que se sondea tiene que ser la del **listado de ofertas**, no la
de la portada. Casi todas las empresas usan su portada de empleo como
propaganda —"vive el desafío", "conoce nuestra cultura"— y los avisos viven un
clic más adentro. Sondeando la portada no hay nada que descubrir, y el cero
que sale de ahí no dice nada de la bolsa.

Pasó con Falabella el 13/8/2026: se sondeó `muevete.falabella.com` y dio cero.
Sus avisos están en `/detalle-oferta/<número>/external`, un nombre que el
sondeo sí reconoce. Nunca llegó a verlos porque se le dio la puerta de calle.
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
    # Cuántas direcciones de aviso alcanzó a DESCUBRIR en la página, que es
    # distinto de cuántas alcanzó a LEER. La diferencia es la que separa "esta
    # bolsa está vacía" de "no supe dónde mirar", y confundirlas es el peor
    # error que puede cometer este comando. Ver `_veredicto`.
    enlaces_vistos: int = 0

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
#   trabajo / trabajos → portales peruanos. Ojo: "trabaja" NO cubre "trabajo",
#                        y por esa letra el sondeo no vio ni un aviso de
#                        Trabajos Diarios, que resultó ser la mejor fuente
#                        privada encontrada hasta ahora (13/8/2026).
_PATRON_AVISO = (r"/(empleo|empleos|vacante|vacantes|oportunidad|oportunidades|"
                 r"job|jobs|posting|postings|requisition|req|posicion|posiciones|"
                 r"puesto|puestos|carrera|careers|trabaja|trabajo|trabajos|"
                 r"detalle)[^\"'\s]*")


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

    # Primero DESCUBRIR, después LEER, y contar las dos cosas por separado.
    #
    # Sin esta separación un cero no se puede interpretar: no se sabe si la
    # bolsa está vacía o si el lector no supo dónde mirar. La primera versión
    # de este comando reportó "0 avisos · no escribas el lector" para Falabella
    # y Cencosud, dos portales que evidentemente tienen avisos. Un cero mal
    # leído es peor que no medir, porque viene con veredicto.
    descubrir = getattr(fuente, "urls_de_avisos", None)
    if callable(descubrir):
        try:
            s.enlaces_vistos = len(descubrir(limite))
        except Exception:                              # noqa: BLE001
            s.enlaces_vistos = 0

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

    # Los lectores de API (Greenhouse, Lever) no descubren direcciones: piden
    # la lista entera de una. Ahí lo leído ES lo descubierto.
    if not callable(descubrir):
        s.enlaces_vistos = s.cuantos

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

    lineas.append(f"  Enlaces de aviso      {s.enlaces_vistos}")
    lineas.append(f"  Avisos que pudo leer  {s.cuantos}")
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
    """
    La regla que gobierna todo esto: **un cero nunca es un veredicto.**

    Desde afuera no hay forma de distinguir "esta bolsa no tiene avisos" de
    "no supe dónde mirar", y el sondeo no puede fingir que sí. Falabella y
    Cencosud devolvieron cero y salieron con un "no escribas el lector" que
    era falso: los dos portales tienen avisos de sobra, lo que pasó es que el
    lector genérico no supo reconocer sus enlaces.

    Es la misma trampa que ya está anotada para las corridas —*una fuente que
    devuelve cero no falla, sale en verde*— y aquí es peor, porque acá el cero
    viene acompañado de un consejo. Un consejo equivocado mata una fuente
    buena y nadie vuelve a mirarla.

    Así que solo un número POSITIVO puede producir un veredicto. Con cero, lo
    único honesto es decir qué hacer para salir de la duda.
    """
    if not s.cuantos:
        if s.enlaces_vistos:
            return (f"Encontró {s.enlaces_vistos} enlaces de aviso pero no pudo "
                    f"leer ninguno.\n  Los avisos están; falta un lector que "
                    f"entienda ESE formato.\n  Mirá uno a mano:  "
                    f"python3 -m motor probar-url \"<enlace de un aviso>\"")
        return ("No supe encontrar los avisos en esa página.\n"
                "  Eso NO quiere decir que no tenga: quiere decir que el lector "
                "genérico\n  no reconoció sus enlaces. Abrila en el navegador, "
                "entrá a un aviso\n  y probá esa dirección con:  "
                "python3 -m motor probar-url \"<dirección>\"")
    if not s.con_sueldo:
        return ("NINGUNO dice el sueldo. Es la historia de las bolsas "
                "universitarias: no escribas el lector.")
    if s.porcentaje_con_sueldo < 10:
        return (f"Solo {s.porcentaje_con_sueldo}% dice el sueldo. De cada 100 "
                f"avisos saldrían {s.porcentaje_con_sueldo}. Decide si "
                f"compensa el trabajo.")
    return (f"{s.porcentaje_con_sueldo}% dice el sueldo. Vale la pena "
            f"escribirle el lector.")
