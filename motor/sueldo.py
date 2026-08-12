"""
Parser de sueldos peruanos.

Este es el módulo más importante del negocio: si no logramos leer un sueldo
real, el aviso no se publica. Prefiere fallar (devolver None) antes que
inventar un monto.

Casos que resuelve:
    S/ 3,500                      -> 3500
    S/. 2500.00 mensuales         -> 2500
    S/2,800 a S/3,400             -> 2800 – 3400
    entre 4000 y 5500 soles       -> 4000 – 5500
    1,500 - 1,800 soles           -> 1500 – 1800
    US$ 1,200 mensual             -> 1200 USD
    S/ 54,000 anuales             -> 4500 mensual
    sueldo a convenir             -> None
    acorde al mercado             -> None
    RMV / sueldo mínimo           -> 1130
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Remuneración Mínima Vital vigente (actualizar cuando cambie por decreto).
RMV = 1130

# Rangos de cordura para un sueldo MENSUAL. Fuera de esto asumimos error de lectura.
MIN_RAZONABLE_PEN = 500        # prácticas cortas / medio tiempo
MAX_RAZONABLE_PEN = 80_000
MIN_RAZONABLE_USD = 200
MAX_RAZONABLE_USD = 25_000

TIPO_CAMBIO_REFERENCIAL = 3.75  # solo para ordenar y filtrar, no se muestra

# Frases que anulan cualquier número que aparezca cerca.
FRASES_VAGAS = (
    "a convenir", "a tratar", "por convenir", "según experiencia",
    "segun experiencia", "acorde al mercado", "acorde a mercado",
    "de acuerdo al mercado", "sueldo competitivo", "salario competitivo",
    "remuneración competitiva", "remuneracion competitiva",
    "acorde a la experiencia", "sueldo atractivo", "salario atractivo",
    "según perfil", "segun perfil", "a coordinar en la entrevista",
    "se conversará en la entrevista", "no especificado", "confidencial",
)

# Palabras que indican que el número NO es un sueldo.
RUIDO = (
    "ley 29783", "ley 30036", "iso 9001", "iso 45001", "d.s.", "art.",
    "ruc", "dni", "whatsapp", "celular", "anexo", "código", "codigo",
)

# Número de sueldo: primero la forma con separador de miles (3.800,00 / 3,500),
# luego la forma llana (2500 / 2500.00). Los lookarounds evitan cortar cifras
# a la mitad, que es el error clásico: leer "950000" como "950".
_NUM = (
    r"(?<!\d)(?:"
    r"\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{1,2})?"
    # Desde dos dígitos, para poder leer "S/ 50 diarios" o "S/ 15 por hora".
    # Que un número pequeño no se cuele como sueldo mensual lo garantiza el
    # rango mínimo de cada periodo, no la cantidad de dígitos.
    r"|\d{2,6}(?:[.,]\d{1,2})?"
    r")(?!\d)"
)

_MONEDA_PEN = r"(?:s/\.?|soles?|pen\b|nuevos soles)"
_MONEDA_USD = r"(?:us\$|usd\b|d[oó]lares?|\$)"

# El periodo se busca SOLO pegado al monto, no en todo el párrafo.
#
# Este fue un error caro: un aviso decía "Salario base S/1,300" y más abajo
# "Remuneraciones quincenales" y "pago de horas extras". Como se miraba una
# ventana amplia de texto, el motor creía que 1,300 era un pago diario y
# publicaba un sueldo de S/ 33,800. Una palabra suelta a treinta caracteres de
# distancia no dice nada sobre ese número.
_PERIODOS = {
    "anual": (r"anual(?:es)?", r"al\s+a[ñn]o", r"por\s+a[ñn]o"),
    "quincenal": (r"quincenal(?:es)?", r"por\s+quincena", r"a\s+la\s+quincena"),
    "semanal": (r"semanal(?:es)?", r"por\s+semana", r"a\s+la\s+semana"),
    "diario": (r"diarios?", r"por\s+d[ií]a", r"al\s+d[ií]a", r"jornal"),
    # Ojo: "hora" y "mes" a secas están fuera a propósito. "S/1130 + horas
    # extra" hacía que 1,130 se leyera como pago por hora.
    "por hora": (r"por\s+hora", r"la\s+hora", r"x\s+hora", r"/\s*hora"),
    "mensual": (r"mensual(?:es)?", r"al\s+mes", r"por\s+mes"),
}

# Cuánto puede valer un pago en cada periodo antes de que deje de ser creíble.
# Si un "sueldo diario" es de 1,300 soles, lo que está mal es la lectura del
# periodo, no el aviso.
_RANGOS_POR_PERIODO = {
    "por hora": (6, 150),
    "diario": (30, 700),
    "semanal": (200, 3_000),
    "quincenal": (400, 10_000),
    "mensual": (MIN_RAZONABLE_PEN, MAX_RAZONABLE_PEN),
    "anual": (8_000, 900_000),
}

# Palabras que, justo antes del número, confirman que ese monto es el sueldo.
_ETIQUETAS_SUELDO = (
    "sueldo", "salario", "remuneracion", "remuneración", "basico", "básico",
    "base", "haber", "ingreso mensual", "pago mensual", "renta",
)

# Palabras que, justo antes del número, dicen que ese monto NO es el sueldo.
#
# Este es el error que reportó Mentita el 7/8/2026, y es hermano del de los
# S/ 33,800. Un aviso de promotor de ventas decía:
#
#     Sueldo básico: S/ 1,130.
#     Comisiones de hasta S/ 600.
#
# y el sitio publicaba **S/ 600**. Una comisión, un bono o un vale de alimentos
# son plata que puedes ganar, pero no son el sueldo: quien busca chamba compara
# sueldos, y publicar la comisión como si lo fuera es exactamente el tipo de
# aviso engañoso que Cero Vagos existe para rechazar.
#
# Ojo con lo que NO está en esta lista: "subvención" se queda fuera a propósito,
# porque es como se llama el pago de una práctica preprofesional. Ahí el monto
# sí es lo que te llevas.
_NO_ES_SUELDO = (
    "comision", "comisiones", "bono", "bonific", "incentivo", "premio",
    "movilidad", "alimentacion", "tarjeta de alimentos", "vale", "canasta",
    "asignacion familiar", "gratificacion", "cts", "utilidades", "aguinaldo",
    "descuento", "afiliacion", "seguro", "eps", "refrigerio", "viatico",
    # Bonos por traer gente. Un call center ofrecía "Gana S/300 por invitar a 1
    # persona y S/600 por invitar 02 personas" y el sitio publicó ese aviso con
    # un sueldo de S/ 600 — cuando el aviso NUNCA dijo cuánto paga el puesto.
    "invitar", "invita", "referido", "referir", "recomendar", "recomienda",
)

# Las mismas palabras, pero buscadas DETRÁS del monto.
#
# Es el agujero que dejó pasar tres avisos que revisó Mentita el 12/8/2026: la
# lista de arriba solo se miraba ANTES del número, y en el texto real la
# palabra que lo descalifica suele ir después.
#
#     Sueldo fijo + S/ 500 de movilidad.
#     ^^^^^^ dice "sueldo"        ^^^^^^^^^ pero el monto es la movilidad
#
#     Gana S/600 por invitar 02 personas.
#                ^^^^^^^^^^ es un bono por traer gente, no un sueldo
#
# Lo delicado es no pasarse de listo. Estos DOS avisos son correctos y no
# pueden perder su sueldo:
#
#     Sueldo base de S/. 650 + Comisiones ilimitadas
#     Sueldo base: S/.1200   Bono de asistencia: S/.200
#
# En los dos, la palabra "comisión" o "bono" viene después del monto bueno —
# pero como OTRO concepto, no como su descripción. La diferencia está en el
# nexo: un monto que se describe va pegado con "de", "por", "en"…, mientras
# que un concepto nuevo empieza con "+", con su propio rótulo o en otra línea.
#
# Así que solo se descalifica cuando detrás del número viene un nexo Y después
# la palabra. Es la misma lección de siempre —lo que califica a un monto tiene
# que estar pegado a él— aplicada al otro lado.
_NEXOS = ("de", "por", "en", "como", "para", "correspondiente", "concepto")

_PEGADO_ATRAS = re.compile(
    r"^\s*(?:" + "|".join(_NEXOS) + r")\b(.{0,40})", re.S)


def _lo_que_describe_al_monto(despues: str) -> str:
    """
    Lo que va detrás del monto SOLO si lo está describiendo.

    Devuelve texto vacío cuando lo que sigue es otro concepto —un "+", un
    rótulo nuevo, otra frase—, porque entonces no dice nada sobre este monto.

    Y aun habiendo nexo, la ventana se corta en el punto o en el monto
    siguiente. Sin ese corte pasaba esto:

        Remuneración S/ 1,600 en planilla. Vale de S/ 200 de alimentación.

    El "en" es un nexo legítimo, pero cuarenta caracteres después aparece
    "vale" —que es de OTRO monto, en otra frase— y el aviso perdía su sueldo
    de S/ 1,600 siendo correcto.
    """
    m = _PEGADO_ATRAS.match(despues or "")
    if not m:
        return ""
    trozo = m.group(1)
    corte = len(trozo)
    for marca in (".", ";", "+", "s/", "us$"):
        pos = trozo.find(marca)
        if pos >= 0:
            corte = min(corte, pos)
    return trozo[:corte]


def _ventana_de_etiqueta(antes: str) -> str:
    """
    Recorta lo que va antes del monto para que la etiqueta sea SUYA.

    El error, con el texto real de un aviso:

        Sueldo básico: S/ 1,130. Comisiones de hasta S/ 600.

    Al mirar los 40 caracteres previos al 600, la ventana llegaba hasta el
    "básico:" del monto anterior. Los dos montos salían "etiquetados como
    sueldo", empataban en confianza, y el desempate —que elige el más bajo por
    prudencia— se quedaba con la comisión.

    La regla es la misma que ya se aplicó al PERIODO después del error de los
    S/ 33,800: **lo que califica a un monto tiene que estar pegado a él.** Se
    corta en el último punto, punto y coma, o monto anterior, lo que venga
    después.
    """
    corte = 0
    for marca in (".", ";", "s/", "us$"):
        pos = antes.rfind(marca)
        if pos >= 0:
            corte = max(corte, pos + len(marca))
    return antes[corte:]


@dataclass
class Sueldo:
    minimo: int
    maximo: int
    moneda: str = "PEN"
    periodo: str = "mensual"
    literal: str = ""       # el texto exacto de donde se extrajo
    confianza: int = 100    # 0-100, baja si tuvimos que convertir o adivinar

    @property
    def es_rango(self) -> bool:
        return self.maximo > self.minimo

    def a_mensual_pen(self) -> int:
        """Valor comparable para ordenar y filtrar."""
        base = self.minimo
        if self.moneda == "USD":
            base = int(base * TIPO_CAMBIO_REFERENCIAL)
        return base


# --------------------------------------------------------------------------

def _a_entero(bruto: str) -> int | None:
    """'3,500.00' / '3.500' / '3500' -> 3500"""
    t = bruto.strip()
    # Quita separador de miles y decimales, quedándonos con la parte entera.
    if "," in t and "." in t:
        t = t.replace(",", "") if t.rfind(".") > t.rfind(",") else t.replace(".", "").replace(",", ".")
    elif t.count(",") == 1 and len(t.split(",")[-1]) <= 2:
        t = t.replace(",", ".")          # 3500,50 -> decimal
    else:
        t = t.replace(",", "").replace(".", "") if re.search(r"[.,]\d{3}\b", t) else t.replace(",", "")
    try:
        valor = int(float(t))
    except ValueError:
        return None
    return valor if valor > 0 else None


def _detectar_periodo(despues: str, antes: str = "") -> str:
    """
    Lee el periodo pegado al monto: primero lo que viene justo después
    ("S/ 50 diarios"), y si no hay nada, lo que viene justo antes
    ("remuneración quincenal de S/ 900").

    Si no hay nada claro cerca, se asume mensual: así se habla de sueldos en el
    Perú, y suponer otra cosa multiplica el monto por 26.
    """
    recorte = despues[:28]
    for periodo, marcas in _PERIODOS.items():
        for marca in marcas:
            if re.search(rf"^[\s,.:;)\-–—]*(?:{marca})\b", recorte):
                return periodo
    # Nada de buscar "un poco más lejos": en "S/ 1,200. Bono anual de hasta
    # S/ 12,000" la palabra "anual" está a diez caracteres del primer monto y
    # no tiene nada que ver con él.
    #
    # Lo último que se mira es lo que estaba justo antes del número.
    previo = antes[-30:]
    for periodo, marcas in _PERIODOS.items():
        for marca in marcas:
            if re.search(rf"\b(?:{marca})\b[\s\w]{{0,12}}$", previo):
                return periodo
    return "mensual"


def _a_mensual(valor: int, periodo: str) -> int:
    factores = {
        "anual": 1 / 12, "quincenal": 2, "semanal": 4.33,
        "diario": 26, "por hora": 208, "mensual": 1,
    }
    return int(round(valor * factores.get(periodo, 1)))


def _en_rango(valor: int, moneda: str) -> bool:
    if moneda == "USD":
        return MIN_RAZONABLE_USD <= valor <= MAX_RAZONABLE_USD
    return MIN_RAZONABLE_PEN <= valor <= MAX_RAZONABLE_PEN


# --------------------------------------------------------------------------

# Las palabras con las que un aviso NOMBRA su sueldo. Decisión de Mentita
# (7/8/2026): cuando el texto dice una de estas justo antes del monto, eso es
# el sueldo y le gana a cualquier otra fuente, incluida la ficha del portal.
#
# Son deliberadamente pocas. "base" o "básico" a secas no entran: valen como
# refuerzo de confianza, pero no bastan para contradecir al portal. Sí entran
# combinadas ("sueldo base", "sueldo básico"), porque llevan "sueldo" dentro.
_ETIQUETAS_EXPLICITAS = ("sueldo", "salario", "remuneracion", "remuneración")


def _reunir_candidatos(plano: str, solo_etiquetado: bool) -> list[Sueldo]:
    """
    Todas las lecturas posibles del texto, ya validadas.

    Está separado de `extraer_sueldo` para que se pueda preguntar otra cosa
    distinta de "cuál es el sueldo": también hace falta saber si el aviso
    declara DOS, que es motivo de rechazo. Ver `declara_varios_sueldos`.
    """
    candidatos: list[Sueldo] = []

    patrones = [
        # rango con moneda al inicio: S/ 2,800 a S/ 3,400  |  S/2800-3400
        (rf"{_MONEDA_PEN}\s*({_NUM})\s*(?:a|-|–|hasta|y)\s*(?:{_MONEDA_PEN}\s*)?({_NUM})", "PEN", 2),
        (rf"{_MONEDA_USD}\s*({_NUM})\s*(?:a|-|–|hasta|y)\s*(?:{_MONEDA_USD}\s*)?({_NUM})", "USD", 2),
        # rango con moneda al final: entre 4000 y 5500 soles | 1500 - 1800 soles
        (rf"({_NUM})\s*(?:a|-|–|hasta|y)\s*({_NUM})\s*{_MONEDA_PEN}", "PEN", 2),
        (rf"({_NUM})\s*(?:a|-|–|hasta|y)\s*({_NUM})\s*{_MONEDA_USD}", "USD", 2),
        # monto único
        (rf"{_MONEDA_PEN}\s*({_NUM})", "PEN", 1),
        (rf"{_MONEDA_USD}\s*({_NUM})", "USD", 1),
        (rf"({_NUM})\s*{_MONEDA_PEN}", "PEN", 1),
        (rf"({_NUM})\s*{_MONEDA_USD}", "USD", 1),
    ]

    for patron, moneda, n_grupos in patrones:
        for m in re.finditer(patron, plano):
            ini, fin = m.span()
            antes = plano[max(0, ini - 70): ini]
            despues = plano[fin: fin + 60]
            contexto = antes + m.group(0) + despues

            if any(f in contexto for f in FRASES_VAGAS):
                continue
            if any(r in contexto for r in RUIDO):
                continue

            valores = [_a_entero(g) for g in m.groups()[:n_grupos]]
            if any(v is None for v in valores):
                continue

            periodo = _detectar_periodo(despues, antes)

            # El monto tiene que ser creíble PARA ESE PERIODO. Si dice que son
            # 1,300 diarios, lo que se leyó mal es el periodo.
            if moneda == "PEN":
                minimo, maximo = _RANGOS_POR_PERIODO.get(periodo, (0, 10**9))
                if not all(minimo <= v <= maximo for v in valores):
                    continue

            mensuales = [_a_mensual(v, periodo) for v in valores]
            if not all(_en_rango(v, moneda) for v in mensuales):
                continue

            lo, hi = min(mensuales), max(mensuales)
            if n_grupos == 2 and hi > lo * 6:      # rango absurdo: 1500 a 90000
                continue

            # La ventana se recorta para que la etiqueta sea de ESTE monto y no
            # se contagie del anterior. Ver `_ventana_de_etiqueta`.
            ventana = _ventana_de_etiqueta(antes)[-40:]

            # Si lo que precede al monto dice que es una comisión, un bono o un
            # vale, no es el sueldo y no se usa. Perder el aviso es preferible a
            # publicar como sueldo algo que no lo es (regla 2).
            if any(n in ventana for n in _NO_ES_SUELDO):
                continue

            # Y lo mismo con lo que viene DETRÁS. "S/ 500 de movilidad" tiene
            # la palabra "sueldo" delante (de la frase "Sueldo fijo + …") y la
            # que lo descalifica atrás. Mirando solo adelante, ese monto se
            # publicaba como si fuera el sueldo del puesto.
            detras = _lo_que_describe_al_monto(despues)
            if any(n in detras for n in _NO_ES_SUELDO):
                continue

            etiquetado = any(e in ventana for e in _ETIQUETAS_SUELDO)

            # El filtro va ANTES de guardar el candidato, no después: si no,
            # el `break` de más abajo cortaría la búsqueda con candidatos sin
            # etiqueta y luego se quedarían fuera todos, devolviendo None.
            if solo_etiquetado and not any(e in ventana for e in _ETIQUETAS_EXPLICITAS):
                continue

            confianza = 100
            if periodo != "mensual":
                confianza -= 25            # convertir siempre es más frágil
            if moneda == "USD":
                confianza -= 5
            if n_grupos == 1:
                confianza -= 5
            if etiquetado:
                confianza += 5

            candidatos.append(
                Sueldo(lo, hi, moneda, "mensual", m.group(0).strip(),
                       min(confianza, 100))
            )

        if candidatos:      # los patrones están ordenados de más a menos fiable
            break

    return candidatos


def declara_varios_sueldos(texto: str) -> bool:
    """
    ¿El aviso nombra DOS sueldos distintos?

    Pasa cuando una sola publicación convoca varias modalidades. El caso que
    lo destapó (7/8/2026): un "Reponedor(a) Full Time" que en realidad ofrecía
    las dos jornadas y declaraba "Remuneración: S/ 1,130" y "Remuneración:
    S/ 565". No hay forma de saber cuál corresponde al puesto que mostramos,
    así que el aviso no se publica — regla 2.

    Que el mismo monto aparezca repetido no cuenta: eso no es ambigüedad.
    """
    if not texto:
        return False
    plano = re.sub(r"\s+", " ", texto.lower())
    candidatos = _reunir_candidatos(plano, solo_etiquetado=True)
    return len({(s.minimo, s.maximo) for s in candidatos}) > 1


def extraer_sueldo(texto: str, solo_etiquetado: bool = False) -> Sueldo | None:
    """
    Devuelve el sueldo mensual detectado o None si el aviso no lo declara.
    Ante la duda, None: preferimos perder un aviso a publicar un monto falso.

    Con `solo_etiquetado=True` se queda únicamente con montos que el texto
    llama sueldo por su nombre. Sirve para creerle al aviso por encima de la
    ficha de datos del portal — ver `procesar_cruda` en `pipeline.py`.
    """
    if not texto:
        return None

    plano = re.sub(r"\s+", " ", texto.lower())

    # 1) Sueldo mínimo declarado explícitamente
    if re.search(r"\b(rmv|remuneraci[oó]n m[ií]nima vital|sueldo m[ií]nimo)\b", plano):
        return Sueldo(RMV, RMV, "PEN", "mensual", "RMV", confianza=85)

    candidatos = _reunir_candidatos(plano, solo_etiquetado)
    if not candidatos:
        return None

    # Gana el de mayor confianza; a igual confianza, el monto más bajo. Entre
    # varias lecturas posibles conviene la conservadora: es peor prometer un
    # sueldo que no existe que quedarse corto.
    return sorted(candidatos, key=lambda s: (-s.confianza, s.minimo))[0]


def declara_sueldo_vago(texto: str) -> bool:
    """True si el aviso dice explícitamente 'a convenir' y similares."""
    plano = re.sub(r"\s+", " ", (texto or "").lower())
    return any(f in plano for f in FRASES_VAGAS)
