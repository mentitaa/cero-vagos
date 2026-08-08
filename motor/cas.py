"""
Convocatorias CAS (convocatoriascas.com).

Segunda fuente pública, y la que reemplaza a convocape.com — que resultó ser
un archivo: de sus 512 direcciones, 413 tenían el plazo cerrado.

Qué la hace buena:
  · HTML server-side. Se lee con `requests`, sin navegador.
  · El sueldo viene ETIQUETADO y como número único ("Salario: S/ 1800.00"),
    no perdido en un párrafo. Es el terreno donde nació el error de los
    S/ 33,800, así que aquí el riesgo es bajo — pero igual el periodo se busca
    pegado al monto, como en todo el motor.
  · Dice hasta cuándo se puede postular ("Plazo para postular: 17 de Agosto
    del 2026"). Eso vale más que una fecha de publicación: una convocatoria
    CAS dura una o dos semanas.
  · Enlaza las bases en el dominio de la propia entidad (munisurquillo.gob.pe),
    que es de donde se sacan las funciones.
  · Es casi todo provincia: Andahuaylas, Moquegua, Tacna, Cusco, Puno,
    Tambopata. El mapa que hoy falta en la web.

VARIOS PUESTOS EN UNA MISMA PÁGINA
----------------------------------
Una convocatoria puede sacar a concurso varios puestos a la vez, con sueldos
distintos: Surquillo lista 6 plazas en 2 puestos, uno de S/ 1,350 y otro de
S/ 2,800.

Al estrenar la fuente (5/8/2026) esas se descartaban enteras, porque el motor
asumía una dirección igual a un aviso. En la primera corrida eso dejó fuera
**94 convocatorias y 1.263 vacantes**, casi todas de provincia — la oferta que
más falta le hace al sitio.

Desde el 8/8/2026 la página se parte en una ficha por puesto y cada una sale
como un aviso propio. Tres decisiones que van juntas:

  · **Un aviso por PUESTO, no por plaza.** Un puesto con 5 vacantes es un solo
    aviso que dice "5 vacantes". Cinco tarjetas idénticas serían basura.

  · **El sueldo tiene que estar dentro de la ficha del puesto.** En Surquillo
    el resumen de arriba dice S/ 1,350, que es el del operario de limpieza:
    pegárselo también al especialista, que gana S/ 2,800, sería publicar un
    sueldo falso. El puesto que no declara el suyo **no se publica, y los demás
    de esa convocatoria sí** (decisión de Mentita, 8/8/2026).

  · **Comparten el enlace al aviso original, y está bien**: la convocatoria de
    verdad cubre a todos. En Cero Vagos cada uno tiene página propia porque su
    dirección se arma con su huella, no con su posición (regla 3). La ficha
    dice de frente que la convocatoria incluye más puestos.

Las de varios puestos NO se enriquecen con el PDF de las bases: ese documento
trae las funciones de todos mezcladas y no hay forma segura de saber cuáles son
de cuál. Se quedan sin funciones, que para el Estado está permitido, y la ficha
explica dónde buscarlas.

LO QUE ESTE LECTOR NO HACE
--------------------------
No deduce el sueldo, no deduce el puesto y no rellena huecos. Si una ficha
declara dos montos distintos, ese puesto se descarta en vez de elegir uno.
Ante la duda, no se publica.
"""
from __future__ import annotations

import re
from collections.abc import Iterator
from datetime import date

from ..modelos import OfertaCruda, sin_tildes
from .portal_web import PortalWeb
from .publicas import BENEFICIOS_POR_REGIMEN, enriquecer_con_bases

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "setiembre": 9, "septiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}

# El número de plazas va en la dirección: '...-agosto-2026-1-plazas-67463.html'
PLAZAS_EN_URL = re.compile(r"-(\d+)-plazas-\d+\.html$", re.I)

# Etiquetas que cierran la LISTA DE REQUISITOS de un puesto. Todo lo que viene
# después (el sueldo, el cómo postular, las bases, el cronograma) ya no es un
# requisito.
#
# Ojo: esto no es lo mismo que el final de la ficha del puesto. "Salario" corta
# los requisitos pero está DENTRO de la ficha — de hecho es el dato que más
# falta hace, porque en las convocatorias de varios puestos cada uno trae el
# suyo. Confundir las dos cosas dejaba el sueldo fuera de su propio bloque.
_FIN_DE_REQUISITOS = (
    "lugar de labores", "salario", "plazo para postular", "como postular",
    "remuneracion", "ver aqui bases", "descargar aqui",
)

# Compatibilidad: el nombre viejo apuntaba a esta misma lista.
_FIN_DE_PUESTO = _FIN_DE_REQUISITOS

# Lo que cierra la ficha ENTERA de un puesto: el pie de la convocatoria, que es
# común a todos los puestos y no pertenece a ninguno.
_FIN_DE_FICHA = (
    "plazo para postular", "como postular", "ver aqui bases", "descargar aqui",
    "cronograma", "documentos", "informes",
)


def _limpiar_etiqueta(linea: str) -> str:
    """
    Quita la decoración de adelante:

        '► Institución:'      -> 'Institución:'
        '¿Cómo Postular?: …'  -> 'Cómo Postular?: …'
    """
    return re.sub(r"^[^\w]+", "", linea or "").strip()


def tras_etiqueta(linea: str, etiqueta: str) -> str | None:
    """
    Si la línea es «etiqueta: valor», devuelve el valor. Si no, None.

    La etiqueta tiene que terminar donde corresponde, y esto NO es un detalle:
    buscando 'Institución' por simple prefijo, el menú del sitio
    ('Instituciones') calzaba primero y la entidad de la convocatoria terminaba
    siendo «es». Detrás de la etiqueta solo puede venir ':' o un paréntesis:

        ► Institución: MUNICIPALIDAD SURQUILLO        -> 'MUNICIPALIDAD SURQUILLO'
        ► Formación académica(según puesto): Ayudante -> 'Ayudante'
        Salario:                                      -> ''  (el valor va abajo)
        Instituciones                                 -> None
        Experiencia General: mínima de un año         -> None  para 'Experiencia'
    """
    limpia = _limpiar_etiqueta(linea)
    objetivo = sin_tildes(etiqueta).rstrip(":").strip()
    plano = sin_tildes(limpia)
    if not plano.startswith(objetivo):
        return None

    resto = limpia[len(objetivo):]
    # Paréntesis pegado a la etiqueta: "…académica(según puesto):"
    if resto.startswith("("):
        cerrado = resto.split(")", 1)
        if len(cerrado) != 2:
            return None
        resto = cerrado[1]
    resto = resto.lstrip()
    # El sitio escribe una de sus etiquetas como pregunta: "Cómo Postular?:"
    if resto.startswith("?"):
        resto = resto[1:].lstrip()
    if resto.startswith(":"):
        return resto[1:].strip()
    return "" if not resto else None


def campo(lineas: list[str], etiqueta: str) -> str:
    """
    Lee un par etiqueta/valor de la ficha.

    El sitio los escribe de dos formas y las dos aparecen en la misma página:

        ► Remuneración: S/. 1800 Soles      (en la misma línea)
        Salario:                            (etiqueta sola…)
        S/ 1800.00                          (…y el valor en la siguiente)
    """
    for i, bruta in enumerate(lineas):
        valor = tras_etiqueta(bruta, etiqueta)
        if valor is None:
            continue
        if valor:
            return valor
        # Etiqueta sola: el valor está en la línea siguiente.
        return _limpiar_etiqueta(lineas[i + 1]) if i + 1 < len(lineas) else ""
    return ""


def fecha_cas(texto: str) -> date | None:
    """'17 de Agosto del 2026' / '3 de setiembre de 2026' -> date"""
    if not texto:
        return None
    m = re.search(r"(\d{1,2})\s+de\s+([a-záéíóú]+)\s+de[l]?\s+(\d{4})",
                  sin_tildes(texto))
    if not m:
        return None
    mes = MESES.get(sin_tildes(m.group(2)))
    if not mes:
        return None
    try:
        return date(int(m.group(3)), mes, int(m.group(1)))
    except ValueError:
        return None


def plazas_en_url(url: str) -> int:
    """Cuántas plazas declara la dirección. 0 si no lo dice."""
    m = PLAZAS_EN_URL.search(url or "")
    return int(m.group(1)) if m else 0


def _monto(texto: str) -> int | None:
    """El sueldo que declara un texto, o None. No adivina: usa el parser común."""
    from ..sueldo import extraer_sueldo
    s = extraer_sueldo(texto or "")
    return s.minimo if s else None


def _empieza_con(linea: str, *etiquetas: str) -> bool:
    plano = sin_tildes(_limpiar_etiqueta(linea))
    return any(plano.startswith(e) for e in etiquetas)


def fichas_de_puesto(lineas: list[str]) -> list[tuple[int, int]]:
    """
    Dónde empieza y dónde termina la ficha de cada puesto de la convocatoria.

    Una convocatoria puede sacar a concurso varios puestos en la misma página:
    Surquillo lista 6 plazas en 2 puestos, uno de S/ 1,350 y otro de S/ 2,800.
    Cada puesto es un aviso distinto y necesita su propio pedazo de página —
    sobre todo su propio sueldo.

    El corte se hace en «Vacantes», que es lo que encabeza cada ficha, y cada
    una termina donde empieza la siguiente. La última se corta en el pie de la
    convocatoria (cómo postular, bases, cronograma), que es común a todos los
    puestos y no pertenece a ninguno.

    Devuelve pares (inicio, fin) con el índice del «Vacantes» de cada ficha.
    """
    inicios = [i for i, l in enumerate(lineas) if _empieza_con(l, "vacantes")]
    if not inicios:
        return []

    # Dónde empieza el pie común. Se busca DESPUÉS del último puesto para no
    # confundirlo con un "Ver aquí bases" que aparezca antes.
    pie = len(lineas)
    for i in range(inicios[-1] + 1, len(lineas)):
        if _empieza_con(lineas[i], *_FIN_DE_FICHA):
            pie = i
            break

    fines = inicios[1:] + [pie]
    return list(zip(inicios, fines))


def _requisitos_del_puesto(lineas: list[str], desde: int,
                           hasta: int | None = None) -> list[str]:
    """
    Lo que la ficha del puesto pide, en orden: primero la formación
    ('Profesiones/Oficios'), después la experiencia.

    Se recorre hacia abajo desde el puesto y se corta en la primera etiqueta
    que ya no es un requisito. Sin ese corte, el 'cómo postular' y la dirección
    de la mesa de partes terminarían contados como requisitos.

    `hasta` es dónde empieza el puesto siguiente. En una convocatoria de varios
    puestos hace falta: sin él, los requisitos del primero se comerían los del
    segundo y quien postulara al de limpieza vería que le piden un título en
    Derecho.
    """
    salida: list[str] = []
    dentro = False
    for linea in lineas[desde:hasta]:
        limpia = _limpiar_etiqueta(linea)

        if any(tras_etiqueta(limpia, f) is not None for f in _FIN_DE_REQUISITOS):
            break
        if tras_etiqueta(limpia, "Vacantes") is not None:
            continue

        # Ojo con el corte de etiqueta: 'Experiencia:' es un rótulo, pero
        # 'Experiencia General: mínima de un año…' es el requisito en sí. Si se
        # tratara igual a las dos, el aviso perdería la palabra 'experiencia'
        # justo donde el filtro la busca para saber si el requisito es
        # verificable.
        rotulo = next(
            (tras_etiqueta(limpia, e)
             for e in ("Profesiones/Oficios", "Profesiones", "Oficios",
                       "Experiencia", "Formación académica", "Requisitos")
             if tras_etiqueta(limpia, e) is not None),
            None,
        )
        if rotulo is not None:
            dentro = True
            if len(rotulo) > 10:          # "Experiencia: mínima de un año…"
                salida.append(rotulo)
            continue

        if dentro and limpia:
            salida.append(limpia)
    return salida


def _sueldo_de_la_ficha(bloque: list[str]) -> str:
    """
    El sueldo que declara la ficha de ESTE puesto. Vacío si no lo declara.

    Es la pieza que hace posible publicar una convocatoria de varios puestos
    sin mentir. El monto tiene que estar dentro del bloque del puesto, no en el
    resumen de arriba: en Surquillo el resumen dice S/ 1,350 y ese es el sueldo
    del operario de limpieza — pegárselo también al especialista, que gana
    S/ 2,800, sería publicar un sueldo falso.

    Es el mismo principio que ya costó caro dos veces (el periodo en los
    S/ 33,800, la etiqueta en las comisiones de S/ 600): lo que califica a un
    monto tiene que estar pegado al monto.
    """
    salario = campo(bloque, "Salario")
    remuneracion = campo(bloque, "Remuneración")
    a, b = _monto(salario), _monto(remuneracion)
    if a and b and a != b:
        return ""              # se contradice a sí misma: no se publica
    return salario or remuneracion


def parsear_cas(html: str, url: str, fuente: str) -> list[OfertaCruda]:
    """
    Lee una convocatoria CAS y devuelve UN AVISO POR PUESTO.

    Hasta el 8/8/2026 devolvía como mucho uno y descartaba entera cualquier
    convocatoria de más de una plaza. Eso dejaba fuera 94 convocatorias y 1.263
    vacantes en una sola corrida, casi todas de provincia — la oferta que más
    falta le hace al sitio.

    Ahora la página se parte en una ficha por puesto. Un puesto con 5 vacantes
    sigue siendo UN aviso que dice "5 vacantes": publicar cinco tarjetas
    idénticas sería basura para quien busca.

    Los avisos comparten el enlace al aviso original, y está bien: la
    convocatoria de verdad cubre a todos. En Cero Vagos cada uno tiene página
    propia porque su dirección se arma con su huella —puesto, entidad y
    ciudad—, no con su posición (regla 3).

    Se descarta un puesto —no la convocatoria— cuando no se le puede leer el
    sueldo (decisión de Mentita, 8/8/2026: los demás sí se publican). Y se
    descarta la convocatoria entera cuando no nombra sus puestos o cuando el
    plazo de postulación ya cerró o no se pudo leer.
    """
    from ..normalizar import html_a_lineas

    lineas = html_a_lineas(html)
    if not lineas:
        return []

    fichas = fichas_de_puesto(lineas)
    if not fichas:
        return []

    # ---- lo que es común a toda la convocatoria ----
    vence = fecha_cas(campo(lineas, "Plazo para postular"))
    if not vence or vence < date.today():
        return []

    entidad = campo(lineas, "Institución")
    ubicacion = campo(lineas, "Lugar de trabajo") or campo(lineas, "Lugar de labores")
    beneficios = BENEFICIOS_POR_REGIMEN["CAS"]
    del_resumen = campo(lineas, "Formación académica")

    salida: list[OfertaCruda] = []
    for inicio, fin in fichas:
        bloque = lineas[inicio:fin]

        # ---- puesto ----
        # El encabezado es la línea justo antes de "Vacantes". Si no sirve, se
        # cae al campo del resumen — pero solo cuando hay un puesto: con varios
        # ese campo describe a la convocatoria, no a este puesto en particular,
        # y ponérselo sería inventarle el cargo (regla 8).
        encabezado = _limpiar_etiqueta(lineas[inicio - 1]) if inicio else ""
        puesto = encabezado if 3 < len(encabezado) <= 90 else (
            del_resumen if len(fichas) == 1 else "")
        if not puesto or len(puesto) < 4:
            continue

        # ---- sueldo: el suyo, o este puesto no va ----
        if len(fichas) == 1:
            # Con un solo puesto no hay ambigüedad posible: el sueldo del
            # resumen es suyo. Y se mira la página entera a propósito, porque
            # así el resumen y la ficha se contrastan: si declaran montos
            # distintos, la convocatoria se contradice y no se publica.
            sueldo_texto = _sueldo_de_la_ficha(lineas)
        else:
            # Con varios puestos el monto tiene que estar dentro de SU ficha.
            # El del resumen no se reparte: en Surquillo dice S/ 1,350, que es
            # el del operario de limpieza, y dárselo también al especialista
            # —que gana S/ 2,800— sería publicar un sueldo falso.
            sueldo_texto = _sueldo_de_la_ficha(bloque)
        if not sueldo_texto:
            continue

        # ---- cuántas vacantes ----
        vacantes = 0
        m = re.match(r"^\s*(\d+)", campo(bloque, "Vacantes") or "")
        if m:
            vacantes = int(m.group(1))

        requisitos = _requisitos_del_puesto(lineas, inicio, fin)

        # ---- el cuerpo del aviso, armado a mano ----
        # No se pasa la página entera como hacen otros lectores: el menú, el pie
        # y el aviso de WhatsApp terminarían contados como requisitos. Se arma
        # solo con lo que sí es del puesto, bajo encabezados que el normalizador
        # conoce.
        cuantas = (f"{vacantes} vacantes" if vacantes > 1
                   else "Una vacante" if vacantes == 1 else "")
        # Se dice de frente que la convocatoria trae más puestos. Sin esto, la
        # persona hace clic en "Postular" y se encuentra un documento con seis
        # plazas sin entender por qué.
        companeros = (f" La convocatoria incluye {len(fichas)} puestos; este es"
                      f" uno de ellos." if len(fichas) > 1 else "")
        partes = [f"<p>Convocatoria CAS de {entidad or 'una entidad del Estado'}"
                  f"{f' en {ubicacion}' if ubicacion else ''}."
                  f"{f' {cuantas}.' if cuantas else ''}{companeros}</p>"]
        if requisitos:
            partes.append("<p>Requisitos</p><ul>"
                          + "".join(f"<li>{r}</li>" for r in requisitos) + "</ul>")
        partes.append("<p>Beneficios</p><ul>"
                      + "".join(f"<li>{b}</li>" for b in beneficios) + "</ul>")

        salida.append(OfertaCruda(
            fuente=fuente,
            url=url,
            puesto=puesto,
            empresa=entidad,
            descripcion_html="".join(partes),
            ubicacion_texto=ubicacion,
            sueldo_texto=sueldo_texto,
            # La página no publica fecha de publicación, y el `lastmod` del
            # sitemap dice cuándo se tocó la página, no cuándo salió el aviso.
            # Se deja vacía a propósito: el plazo de postulación ya cumple esa
            # función y es un dato que el propio aviso declara.
            publicado=None,
            extra={
                "perfil": "publico",
                "regimen": "CAS",
                "beneficios_de_ley": True,
                "plazas": vacantes or 1,
                "puestos_en_la_convocatoria": len(fichas),
                "vence": vence.isoformat(),
            },
        ))

    return _sin_puestos_ambiguos(salida)


def _sin_puestos_ambiguos(avisos: list[OfertaCruda]) -> list[OfertaCruda]:
    """
    Quita los puestos que se llaman igual dentro de la misma convocatoria.

    Es el agujero que quedaba abierto. La dirección de cada oferta se arma con
    su huella —puesto, entidad y ciudad—, así que **dos fichas con el mismo
    nombre producen la misma huella**: la segunda pisaría a la primera y en la
    web quedaría un solo aviso, con el nombre de uno y el sueldo del otro. Es
    exactamente el error que este trabajo existe para evitar, entrando por la
    puerta de atrás.

    Si los dos declaran el mismo sueldo no hay problema y se juntan en uno: es
    el mismo puesto listado dos veces. Si declaran sueldos distintos, no hay
    forma de distinguirlos para quien lee y se van los dos (regla 2).
    """
    from ..sueldo import extraer_sueldo

    por_nombre: dict[str, list[OfertaCruda]] = {}
    for a in avisos:
        por_nombre.setdefault(sin_tildes(a.puesto).lower(), []).append(a)

    salida = []
    for grupo in por_nombre.values():
        if len(grupo) == 1:
            salida.append(grupo[0])
            continue
        montos = {(_monto(a.sueldo_texto) or 0) for a in grupo}
        if len(montos) == 1:
            salida.append(grupo[0])       # el mismo puesto listado dos veces
    return salida


# --------------------------------------------------------------------------

class ConvocatoriasCAS(PortalWeb):
    """
    Igual que cualquier portal, salvo por el conteo de plazas.

    Hasta el 8/8/2026 descartaba aquí mismo las convocatorias de más de una
    plaza, antes de descargarlas. Ya no: ahora se leen todas y la página se
    parte en un aviso por puesto (ver `parsear_cas`). El conteo se queda porque
    sigue diciendo de qué tamaño es lo que entra.
    """

    def urls_de_avisos(self, limite: int = 100) -> list[str]:
        todas = super().urls_de_avisos(limite)
        varias, plazas = 0, 0
        for u in todas:
            n = plazas_en_url(u)
            if n > 1:
                varias += 1
                plazas += n

        self.de_varias_plazas = varias
        self.plazas_en_juego = plazas
        # Nombres viejos, por si algo los mira: ya no se salta ninguna.
        self.saltadas_por_plazas = 0
        self.plazas_perdidas = 0
        if varias:
            self._anotar(
                f"{varias} convocatorias traen más de una plaza "
                f"({plazas} plazas en total). Se leen: cada puesto sale como "
                f"un aviso propio, y el que no declare su sueldo se cae solo."
            )
        return todas[:limite]

    def recolectar(self, limite: int = 100) -> Iterator[OfertaCruda]:
        self.de_varias_plazas = 0
        self.plazas_en_juego = 0
        self.saltadas_por_plazas = 0
        self.plazas_perdidas = 0
        yield from super().recolectar(limite)


def convocatorias_cas() -> list[PortalWeb]:
    """
    convocatoriascas.com — convocatorias CAS de todo el país.

    Verificado el 6 de agosto de 2026: el robots.txt no pone ninguna
    restricción (solo trae las 'content signals' de Cloudflare, que no
    prohíben la lectura), el sitemap trae ~170 convocatorias con `lastmod`
    real y fresco, y cada ficha enlaza las bases en el dominio de la entidad.
    """
    return [
        ConvocatoriasCAS(
            "Convocatorias CAS", "https://www.convocatoriascas.com",
            sitemaps=("https://www.convocatoriascas.com/sitemap.xml",),
            patron_aviso=r"/proceso-de-seleccion-CAS-[^\"'\s]+\.html",
            # El sitemap sí trae fechas reales, así que la ventana sirve. Va
            # holgada igual: el `lastmod` dice cuándo se tocó la página.
            dias_ventana=45,
            parser=parsear_cas,
            # Las funciones viven en el PDF de las bases, en el dominio de la
            # entidad. Es el mismo trabajo que ya se hace con el otro portal
            # público, así que se reutiliza tal cual.
            enriquecer=enriquecer_con_bases,
            nota=("HTML server-side, sin navegador. Solo se publican las "
                  "convocatorias de UNA plaza; las de varias se cuentan y se "
                  "saltan. Sueldo etiquetado y plazo de postulación declarado."),
        ),
    ]
