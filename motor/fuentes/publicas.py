"""
Convocatorias del Estado peruano.

Por qué esta fuente va primera:
  · Es HTML server-side: se lee con `requests`, sin navegador headless.
  · Su robots.txt permite la lectura y declara sitemap.
  · **Siempre dice el sueldo.** En el sector público la remuneración mensual es
    parte obligatoria de la convocatoria, así que casi ningún aviso muere en el
    primer filtro de Cero Vagos.
  · Los requisitos vienen desglosados (formación, experiencia general y
    específica, cursos).

Lo que hay que saber antes de confiar en ella:
  · Muchas convocatorias no publican las FUNCIONES en el aviso: están en el PDF
    de las bases. Esas se rechazan, y está bien: si no dice qué vas a hacer,
    no es una oferta completa. Leer el PDF de las bases es el siguiente paso.
  · Los beneficios no se listan porque están fijados por ley según el régimen
    (CAS, 728 o 276). El motor los completa con lo que la norma garantiza, y lo
    deja marcado como tal: no es invento, es el marco legal del contrato.
"""
from __future__ import annotations

import re
from datetime import date
from urllib.parse import urlparse

from ..modelos import OfertaCruda
from .jsonld import extraer_jobposting
from .portal_web import PortalWeb

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "setiembre": 9, "septiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}

# Beneficios garantizados por norma en cada régimen laboral público.
# No son promesas del aviso: son lo que la ley reconoce al contrato.
BENEFICIOS_POR_REGIMEN: dict[str, list[str]] = {
    "CAS": [
        "Régimen CAS (D. Leg. 1057): afiliación a EsSalud a cargo de la entidad",
        "Afiliación a un régimen pensionario (ONP o AFP) a elección",
        "30 días calendario de vacaciones al año",
        "Aguinaldos por Fiestas Patrias y Navidad según la ley de presupuesto",
        "Jornada máxima de 48 horas semanales",
    ],
    "728": [
        "Régimen laboral privado (D. Leg. 728): planilla con todos los beneficios de ley",
        "Gratificaciones de julio y diciembre",
        "Compensación por Tiempo de Servicios (CTS)",
        "30 días calendario de vacaciones al año",
        "Seguro de salud EsSalud y afiliación pensionaria",
    ],
    "276": [
        "Régimen de carrera administrativa (D. Leg. 276): nombramiento o contrato en planilla",
        "Aguinaldos por Fiestas Patrias y Navidad",
        "30 días calendario de vacaciones al año",
        "Seguro de salud EsSalud y afiliación pensionaria",
        "Escala remunerativa y línea de carrera del sector público",
    ],
}


def _fecha_es(texto: str) -> date | None:
    """'21 de julio de 2026' / '10 ago. 2026' -> date"""
    if not texto:
        return None
    plano = texto.lower().strip()

    m = re.search(r"(\d{1,2})\s*de\s*([a-záéíóú]+)\s*de\s*(\d{4})", plano)
    if m:
        mes = MESES.get(m.group(2))
        if mes:
            try:
                return date(int(m.group(3)), mes, int(m.group(1)))
            except ValueError:
                return None

    m = re.search(r"(\d{1,2})\s+([a-z]{3})\.?\s*(\d{4})", plano)
    if m:
        for nombre, num in MESES.items():
            if nombre.startswith(m.group(2)):
                try:
                    return date(int(m.group(3)), num, int(m.group(1)))
                except ValueError:
                    return None
    return None


def _valor_junto_a(lineas: list[str], etiqueta: str) -> str:
    """
    Lee un par etiqueta/valor de la ficha. Hay tres maquetados en circulación:

        Ubicación               (etiqueta y valor en líneas separadas)
        Cusco - San Jeronimo

        Ubicación: Cusco        (en la misma línea, con dos puntos)
        Ubicación Cusco         (en la misma línea, porque van en <span> pegados)
    """
    objetivo = etiqueta.lower().rstrip(":")
    patron = re.compile(rf"^{re.escape(objetivo)}\s*[:\-–—]?\s*(.+)$", re.I)

    for i, linea in enumerate(lineas):
        limpia = linea.strip()
        if limpia.rstrip(":").lower() == objetivo:
            return lineas[i + 1].strip() if i + 1 < len(lineas) else ""
        m = patron.match(limpia)
        if m:
            valor = m.group(1).strip(" :-–—")
            if valor:
                return valor
    return ""


def _meta(html: str, nombre: str) -> str:
    m = re.search(
        rf'<meta[^>]+(?:name|property)=["\']{re.escape(nombre)}["\'][^>]*content=["\']([^"\']*)["\']',
        html, re.I,
    )
    if m:
        return m.group(1)
    m = re.search(
        rf'<meta[^>]+content=["\']([^"\']*)["\'][^>]*(?:name|property)=["\']{re.escape(nombre)}["\']',
        html, re.I,
    )
    return m.group(1) if m else ""


def _regimen(texto: str) -> str:
    plano = texto.upper()
    if re.search(r"\bCAS\b|1057", plano):
        return "CAS"
    if "728" in plano:
        return "728"
    if "276" in plano:
        return "276"
    return ""


def parsear_convocatoria(html: str, url: str, fuente: str) -> OfertaCruda | None:
    """
    Lee la ficha de una convocatoria pública.

    Estrategia en capas, de lo más fiable a lo más frágil:
      1. JSON-LD, si el sitio lo publica.
      2. Etiquetas <meta> (título, y el sueldo que suele ir en la descripción).
      3. Pares etiqueta/valor de la ficha.
    """
    from ..normalizar import html_a_lineas

    # El JSON-LD, cuando existe, es la fuente más confiable para los datos de
    # cabecera (título, entidad, fecha, sueldo). Pero su `description` suele ser
    # un párrafo de resumen, sin funciones ni requisitos.
    # Por eso NO se devuelve tal cual: se usa como refuerzo y el cuerpo del
    # aviso se arma siempre con la página completa.
    directo = extraer_jobposting(html, url, fuente)

    lineas = html_a_lineas(html)
    descripcion_meta = _meta(html, "description") or _meta(html, "og:description")

    # ---- puesto y entidad ----
    titulo_meta = _meta(html, "og:title")
    m_h1 = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S | re.I)
    titulo = re.sub(r"<[^>]+>", " ", m_h1.group(1)).strip() if m_h1 else ""
    if not titulo and directo:
        titulo = directo.puesto
    if not titulo and titulo_meta:
        titulo = titulo_meta.split(" - ")[0].strip()
    if not titulo:
        return None

    entidad = directo.empresa if directo else ""
    if not entidad and titulo_meta and " - " in titulo_meta:
        entidad = titulo_meta.split(" - ", 1)[1].split("|")[0].strip()
    if not entidad:
        entidad = _valor_junto_a(lineas, "Entidad") or _valor_junto_a(lineas, "Institución")

    # ---- sueldo ----
    sueldo_texto = _valor_junto_a(lineas, "Sueldo") or _valor_junto_a(lineas, "Remuneración")
    if not sueldo_texto and directo:
        sueldo_texto = directo.sueldo_texto
    if not sueldo_texto:
        m = re.search(r"(?:sueldo|remuneraci[oó]n(?:\s+mensual)?)[:\s]*((?:S/|US\$)\s*[\d.,]+)",
                      descripcion_meta, re.I)
        if m:
            sueldo_texto = m.group(1)

    # ---- resto de la ficha ----
    ubicacion = _valor_junto_a(lineas, "Ubicación") or _valor_junto_a(lineas, "Lugar de trabajo")
    if not ubicacion and directo:
        ubicacion = directo.ubicacion_texto
    modalidad = _valor_junto_a(lineas, "Modalidad")
    contrato = _valor_junto_a(lineas, "Contrato") or _valor_junto_a(lineas, "Régimen")
    publicado = (_fecha_es(_valor_junto_a(lineas, "Publicación"))
                 or _fecha_es(_valor_junto_a(lineas, "Fecha de publicación"))
                 or (directo.publicado if directo else None))
    vence = (_fecha_es(_valor_junto_a(lineas, "Fecha límite"))
             or _fecha_es(_valor_junto_a(lineas, "Cierre de postulación"))
             or _fecha_es(_meta(html, "description")[-60:]))   # "...antes del 24 jul. 2026"

    regimen = _regimen(f"{contrato} {titulo_meta} {url}")

    # ---- beneficios por ley ----
    # El aviso no los lista porque son los del régimen. Se agregan al cuerpo
    # bajo su propio encabezado para que el normalizador los recoja igual que
    # cualquier otro bloque, y quede claro de dónde salen.
    beneficios = BENEFICIOS_POR_REGIMEN.get(regimen, [])
    extra_html = ""
    if beneficios:
        items = "".join(f"<li>{b}</li>" for b in beneficios)
        extra_html = f"<p>Beneficios</p><ul>{items}</ul>"

    return OfertaCruda(
        fuente=fuente,
        url=url,
        puesto=titulo,
        empresa=entidad,
        # Se junta todo lo que se sabe del aviso, en orden de utilidad:
        #   1. la meta descripción, que suele ser el mejor resumen
        #   2. la descripción del JSON-LD, si la hay
        #   3. la página completa, de donde salen requisitos y funciones
        #   4. los beneficios del régimen
        descripcion_html=(
            f"<p>{descripcion_meta}</p>"
            f"{directo.descripcion_html if directo else ''}"
            f"{html}{extra_html}"
        ),
        ubicacion_texto=f"{ubicacion} {modalidad}".strip(),
        sueldo_texto=sueldo_texto,
        publicado=publicado,
        extra={"perfil": "publico", "regimen": regimen, "contrato": contrato,
               "beneficios_de_ley": bool(beneficios),
               "vence": vence.isoformat() if vence else ""},
    )


# --------------------------------------------------------------------------

def _bloque_funciones(items: str) -> str:
    """
    Pega la sección de funciones al final del aviso, con un salto POR DELANTE.

    Ese `<br>` no es adorno. El cuerpo que traía el aviso puede terminar en
    cualquier cosa —un enlace, un `</a>`— y al normalizar, la última línea del
    texto anterior y la palabra "Funciones" quedaban en el mismo renglón:

        Ver aquí Bases Funciones

    Así el encabezado deja de reconocerse, y las funciones que tanto costó
    sacar del PDF terminan contadas como requisitos. El aviso pasa de tener
    funciones a no tenerlas sin que nada falle a la vista.
    """
    return f"<br><p>Funciones</p><ul>{items}</ul>"


def enriquecer_con_bases(cruda: OfertaCruda, html: str, bajar) -> str:
    """
    Abre el PDF de las bases y le saca las funciones del puesto.

    Este es el paso que ningún portal peruano da. El Estado publica qué vas a
    hacer, pero dentro de un PDF adjunto; por eso los agregadores muestran
    "funciones no especificadas". Aquí se abre ese PDF.

    Devuelve un aviso de texto si algo falló (para el registro), o "" si todo
    salió bien o si no había nada que hacer.

    Ese aviso distingue TRES fracasos distintos, y la diferencia importa:

      · el servidor de la entidad no contestó   → no sabemos si nos dejaría
      · la entidad contestó que no              → nos dijo que no
      · el PDF se bajó pero no se dejó leer     → problema nuestro o del PDF

    Antes los tres salían con el mismo texto y era imposible saber cuál
    dominaba. El 6/8/2026 la primera corrida dejó 48 avisos sin funciones y no
    hubo forma de repartir ese número: se veía igual una entidad que nos
    bloquea que una cuyo servidor no responde desde el extranjero.
    """
    from ..bases_pdf import (
        desde_cache, enlaces_pdf, extraer_funciones, guardar_en_cache,
        hay_ocr, texto_de_pdf, texto_por_ocr, MAX_BYTES,
    )
    from ..normalizar import extraer_bloques
    from .base import ErrorFuente

    # Si la página ya trae funciones, no hay que abrir nada.
    if len(extraer_bloques(cruda.cuerpo())["funciones"]) >= 3:
        return ""

    partes = urlparse(cruda.url)
    base = f"{partes.scheme}://{partes.netloc}"

    # Qué salió mal, y con qué PDF, para poder contarlo después.
    motivos: dict[str, str] = {}

    def intentar(urls_pdf: list[str]) -> bool:
        for url_pdf in urls_pdf[:2]:        # el mejor y su suplente, no más
            datos = desde_cache(url_pdf)
            if datos is None:
                try:
                    datos = bajar(url_pdf, MAX_BYTES)
                except ErrorFuente as e:
                    motivos.setdefault(_por_que_no(e), url_pdf)
                    continue
                guardar_en_cache(url_pdf, datos)

            texto = texto_de_pdf(datos)
            funciones = extraer_funciones(texto)

            # Último recurso: leerle las letras a la imagen.
            #
            # Va DESPUÉS de haber fallado por lo normal, nunca antes: cuesta
            # segundos por página, mientras que sacar el texto que el PDF ya
            # trae es instantáneo. Y se intenta aunque el PDF sí tuviera texto,
            # porque el caso más común no es el PDF vacío sino el PDF cuyo
            # texto está roto — ahí la imagen original es mejor fuente que lo
            # que el archivo dice traer.
            por_ocr = False
            if len(funciones) < 3 and hay_ocr():
                funciones = extraer_funciones(texto_por_ocr(datos))
                por_ocr = len(funciones) >= 3

            if len(funciones) >= 3:
                items = "".join(f"<li>{f}</li>" for f in funciones)
                cruda.descripcion_html += _bloque_funciones(items)
                cruda.extra["funciones_desde_pdf"] = url_pdf
                cruda.extra["funciones_desde"] = url_pdf
                # Queda anotado para poder contar cuántas convocatorias salvó
                # el OCR. Si ese número es bajo, no valía la pena el gasto.
                cruda.extra["funciones_por_ocr"] = por_ocr
                if por_ocr:
                    motivos["rescatado_por_ocr"] = url_pdf
                return True

            # Otros dos fracasos que parecen uno solo y no lo son:
            #
            #   escaneado      → el PDF es una FOTO del documento. No tiene
            #                    texto dentro, así que no hay nada que buscar.
            #                    Se arregla con OCR, que es caro y lento.
            #   sin_encabezado → el PDF sí trae texto, pero la sección de
            #                    funciones no se llamó como esperábamos. Se
            #                    arregla mirando UN PDF y agregando el
            #                    encabezado que use.
            #
            # Un PDF de bases con texto pasa de largo los miles de caracteres;
            # un escaneado devuelve vacío o cuatro letras sueltas de la
            # carátula. 200 separa los dos casos sin acercarse a ninguno.
            motivos.setdefault(
                "escaneado" if len(texto) < 200 else "sin_encabezado", url_pdf)
        return False

    def rescate() -> str:
        """
        Se salió bien, pero conviene decir CÓMO. Cuando las funciones salieron
        de la imagen y no del texto, se anota: ese contador es lo único que
        dice si el OCR se está ganando el tiempo que cuesta.
        """
        if "rescatado_por_ocr" in motivos:
            return ("Las funciones se sacaron leyéndole las letras a la imagen "
                    "(OCR): las bases venían escaneadas o mal digitalizadas. "
                    f"Ejemplo: {motivos['rescatado_por_ocr']}")
        return ""

    # 1) ¿El PDF está enlazado en el propio aviso?
    if intentar(enlaces_pdf(html, base)):
        return rescate()

    # 2) Si no, se sigue el enlace al anuncio oficial de la entidad. Ahí es
    #    donde suelen vivir las bases: el agregador solo enlaza a la página.
    for url_oficial in enlaces_oficiales(html, partes.netloc)[:2]:
        try:
            pagina = bajar(url_oficial, MAX_BYTES).decode("utf-8", errors="replace")
        except Exception:                               # noqa: BLE001
            continue                                    # la entidad no siempre deja entrar

        # 2a) A veces la propia entidad publica las funciones en HTML.
        propias = extraer_bloques(pagina)["funciones"]
        if len(propias) >= 3:
            items = "".join(f"<li>{f}</li>" for f in propias)
            cruda.descripcion_html += _bloque_funciones(items)
            cruda.extra["funciones_desde"] = url_oficial
            return ""

        # 2b) Si no, se buscan las bases en PDF dentro de esa página.
        if intentar(enlaces_pdf(pagina, url_oficial)):
            cruda.extra["via_anuncio_oficial"] = url_oficial
            return rescate()

    # Cada mensaje lleva un ejemplo de PDF, y eso es a propósito: el registro
    # agrupa los avisos reemplazando la dirección, así que los tres motivos
    # salen como TRES líneas contadas, cada una con una muestra. Es lo que
    # permite decir "38 de 48 fueron servidores que no contestaron" en vez de
    # un solo número sin repartir.
    if "sin_respuesta" in motivos:
        return ("No se llegó a las funciones: el servidor de la entidad no "
                "contestó, así que por la regla 6 no se le pidió el PDF. "
                f"Ejemplo: {motivos['sin_respuesta']}")
    if "sin_permiso" in motivos:
        return ("No se llegó a las funciones: la entidad contestó que no se "
                f"puede leer ese PDF. Ejemplo: {motivos['sin_permiso']}")
    # Si el sistema tiene con qué leer imágenes, entonces el OCR ya se intentó
    # y también falló. Decirlo cambia el diagnóstico: no es que falte una
    # herramienta, es que ese PDF no hay por dónde agarrarlo.
    tambien_ocr = " Ni siquiera leyendo la imagen." if hay_ocr() else \
                  " Falta instalar tesseract para poder leer la imagen."
    if "sin_encabezado" in motivos:
        return ("No se llegó a las funciones: el PDF de las bases trae texto, "
                "pero no se reconoció dónde empieza la lista de funciones."
                f"{tambien_ocr} Ejemplo: {motivos['sin_encabezado']}")
    if "escaneado" in motivos:
        return ("No se llegó a las funciones: el PDF de las bases está escaneado "
                f"(es una foto, no trae texto).{tambien_ocr} "
                f"Ejemplo: {motivos['escaneado']}")
    return ("No se llegó a las funciones: el aviso no enlaza ningún PDF de "
            "bases, ni en el propio aviso ni en la página de la entidad")


def _por_que_no(e: Exception) -> str:
    """
    Traduce el fallo de una descarga a uno de dos casos, y la diferencia no es
    cosmética.

    `sin_respuesta` es que el servidor de la entidad nunca contestó: no llegamos
    a saber si nos dejaría o no. `sin_permiso` es que sí contestó, y la
    respuesta fue que no.

    Las dos terminan igual —no se baja el PDF, porque la regla 6 dice que sin
    robots.txt legible se asume que no hay permiso— pero significan cosas
    distintas. Un 'no contestó' repetido en decenas de entidades apunta a un
    problema de red nuestro, no a que el Estado peruano nos esté cerrando la
    puerta.
    """
    texto = str(e).lower()
    if "no se pudo leer robots.txt" in texto:
        return "sin_respuesta"
    return "sin_permiso"


# Enlaces que salen del agregador hacia la entidad que convoca.
_EXTERNO = re.compile(r'<a[^>]+href=["\'](https?://[^"\']+)["\'][^>]*>(.*?)</a>', re.I | re.S)
_PISTAS_OFICIAL = ("oficial", "anuncio", "postular", "bases", "convocatoria",
                   "trabaja con nosotros", "ver mas")


def enlaces_oficiales(html: str, dominio_actual: str) -> list[str]:
    """
    Enlaces que apuntan a la entidad convocante (normalmente *.gob.pe).
    Se prioriza lo que huele a anuncio oficial.
    """
    from urllib.parse import urlparse as _url

    candidatos: list[tuple[int, str]] = []
    for href, etiqueta in _EXTERNO.findall(html or ""):
        host = _url(href).netloc
        if not host or host == dominio_actual:
            continue
        texto = _sin_tildes(f"{href} {re.sub(r'<[^>]+>', ' ', etiqueta)}")
        puntaje = 6 if ".gob.pe" in host else 0
        puntaje += sum(3 for p in _PISTAS_OFICIAL if p in texto)
        if any(x in host for x in ("facebook", "twitter", "wa.me", "instagram",
                                   "linkedin", "google", "youtube")):
            continue
        if puntaje > 0:
            candidatos.append((puntaje, href))

    vistos, salida = set(), []
    for _, url in sorted(candidatos, key=lambda c: -c[0]):
        if url not in vistos:
            vistos.add(url)
            salida.append(url)
    return salida


def _sin_tildes(texto: str) -> str:
    import unicodedata
    base = unicodedata.normalize("NFD", texto or "")
    return "".join(c for c in base if unicodedata.category(c) != "Mn").lower()


def convocatorias_estado() -> list[PortalWeb]:
    """
    Fuente de arranque del proyecto.

    Nota de uso: este sitio agrega convocatorias que ya son información pública
    del Estado, y su robots.txt permite la lectura. Aun así, conviene revisar
    sus términos de uso y —mejor todavía— escribirles: sale más barato un
    acuerdo que un bloqueo. Cada oferta enlaza siempre al anuncio oficial de la
    entidad.
    """
    return [
        PortalWeb(
            "Convocatorias del Estado", "https://www.convocape.com",
            # El listado va primero: muestra lo que está abierto y ordenado por
            # fecha. El sitemap es el archivo completo y sirve de respaldo.
            listados=("https://www.convocape.com/",),
            sitemaps=("https://www.convocape.com/sitemap.xml",),
            patron_aviso=r"/convocatorias/[^\"'\s]+",
            ordenar_por_id=True,     # el sitemap no trae fechas: se toma lo más nuevo
            parser=parsear_convocatoria,
            enriquecer=enriquecer_con_bases,
            nota=("HTML server-side, robots permite /, sitemap declarado. "
                  "Sueldo siempre presente; las funciones se sacan del PDF de las bases."),
        ),
    ]
