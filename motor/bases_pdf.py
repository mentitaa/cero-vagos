"""
Lectura de las bases del concurso en PDF.

Aquí está el diferencial de Cero Vagos. El Estado SÍ publica qué vas a hacer en
el puesto, pero lo deja en un PDF adjunto que casi nadie abre; por eso los
portales muestran "funciones no especificadas". Este módulo abre ese PDF y saca
la sección de funciones.

No siempre va a funcionar: cada entidad arma sus bases a su manera y algunas las
escanean como imagen. Cuando no se puede leer, el aviso simplemente no pasa el
filtro. Nunca se inventa una función.

Backends de extracción, en orden de preferencia:
    1. pdfplumber   (mejor respeto del diseño de la página)
    2. pdftotext    (poppler, si está instalado en el sistema)
    3. pypdf        (último recurso, puro Python)
    4. OCR          (leer las letras de la imagen; lento, ver más abajo)

SOBRE EL OCR
------------
Medido el 6/8/2026 en la primera corrida de Convocatorias CAS: de 78 avisos,
**31 no llegaron a sus funciones porque el PDF de las bases no se dejó leer.**
Y ese 31 se parte en dos casos que parecen distintos y son el mismo:

  · 11 PDF sin nada de texto: son una foto del documento, escaneada.
  · 20 PDF *con* texto, pero con el texto roto. A esos alguien ya les pasó un
    lector de letras antes de subirlos, y le salió mal. Un ejemplo real de las
    bases de la UGEL San Pablo (Cajamarca):

        Pr¡ncipales funciones a desanollar:

    Debería decir "Principales funciones a desarrollar". La `i` salió `¡` y las
    dos `rr` se volvieron `n`. El encabezado es el correcto; está mal escrito.

Los dos casos se arreglan igual: **rasterizar la página y volver a leerla
nosotros**, partiendo de la imagen original en vez del texto roto que trae.

Dos cuidados que no son opcionales:

  · Es LENTO (segundos por página), así que solo entra cuando el camino normal
    ya falló, mira pocas páginas y tiene un tope de tiempo.
  · El OCR también se equivoca. Por la regla 2, una función que salga ilegible
    NO se publica: es preferible un aviso sin funciones que un aviso con
    funciones que nadie puede leer. De eso se encarga `parece_ilegible`.
"""
from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

CACHE = Path(__file__).resolve().parent.parent / "datos" / "pdfs"
# Hay bases escaneadas que pesan bastante. 40 MB deja pasar casi todas sin
# arriesgar una descarga eterna.
MAX_BYTES = 40 * 1024 * 1024

# Cuántas páginas mira el OCR. Las funciones van en el perfil del puesto, que
# está al principio: en las bases reales revisadas nunca pasó de la página 4.
# Cada página cuesta entre uno y tres segundos, así que este número es
# directamente el presupuesto de tiempo de la corrida.
OCR_PAGINAS = 5
# Tope duro por PDF. Si una base tarda más que esto, se abandona y el aviso se
# queda sin funciones: vale más perder uno que colgar la corrida entera.
OCR_SEGUNDOS = 90
# Resolución de rasterizado. Por debajo de 200 el OCR empieza a confundir
# letras; por encima de 300 tarda el doble sin leer mejor.
OCR_DPI = 250

# --------------------------------------------------------------------------
# Encabezados
# --------------------------------------------------------------------------

# Inicio de la sección buscada. Admite numeración romana, arábiga o nada:
#   "III. FUNCIONES DEL PUESTO"   "4.2 FUNCIONES"   "FUNCIONES ESPECÍFICAS:"
INICIO_FUNCIONES = re.compile(
    r"""^\s*
    (?:[IVXLC]+\s*[\.\)\-]\s*|\d+(?:\.\d+)*\s*[\.\)\-]?\s*)?     # numeración
    (?:principales\s+|especificas\s+|generales\s+)?
    funciones
    (?:\s+(?:y\s+responsabilidades|del\s+puesto|especificas|generales|
         principales|a\s+desarrollar|a\s+realizar|del\s+servicio))?
    \s*[:\.]?\s*$
    """,
    re.I | re.X,
)

# Encabezados que cierran la sección de funciones.
FIN_SECCION = (
    "requisitos", "perfil", "condiciones", "cronograma", "documentos",
    "evaluacion", "evaluación", "base legal", "disposiciones", "anexo",
    "remuneracion", "remuneración", "lugar de prestacion", "lugar de prestación",
    "etapas", "generalidades", "objetivo", "dependencia", "vacantes",
    "modalidad", "formacion academica", "formación académica", "experiencia",
    "conocimientos", "habilidades", "competencias", "duracion", "duración",
    "postulacion", "postulación", "declaracion jurada", "bonificaciones",
)

# Un ítem de la lista suele empezar con alguna de estas marcas.
MARCA_ITEM = re.compile(
    r"""^\s*(?:
        [a-z]\s*[\)\.\-]        |   # a)  b.  c-
        \d{1,2}\s*[\)\.\-]      |   # 1)  2.  10-
        [•●▪·\-\*–—]   |   # viñetas
        [ivxIVX]{1,4}\s*[\)\.]      # i)  ii.
    )\s+""",
    re.X,
)


def _sin_tildes_min(texto: str) -> str:
    import unicodedata
    base = unicodedata.normalize("NFD", texto or "")
    return "".join(c for c in base if unicodedata.category(c) != "Mn").lower()


# --------------------------------------------------------------------------
# PDF -> texto
# --------------------------------------------------------------------------

def backends_disponibles() -> list[str]:
    disponibles = []
    try:
        import pdfplumber  # noqa: F401
        disponibles.append("pdfplumber")
    except ImportError:
        pass
    if shutil.which("pdftotext"):
        disponibles.append("pdftotext")
    try:
        import pypdf  # noqa: F401
        disponibles.append("pypdf")
    except ImportError:
        pass
    return disponibles


def texto_de_pdf(datos: bytes, max_paginas: int = 12) -> str:
    """
    Devuelve el texto del PDF, o cadena vacía si no se pudo leer.
    Solo mira las primeras páginas: las funciones siempre van al inicio, y así
    no se gasta tiempo en anexos de 40 hojas.
    """
    if not datos or datos[:4] != b"%PDF":
        return ""

    # 1) pdfplumber
    try:
        import io

        import pdfplumber
        with pdfplumber.open(io.BytesIO(datos)) as pdf:
            partes = [(p.extract_text() or "") for p in pdf.pages[:max_paginas]]
        texto = "\n".join(partes).strip()
        if texto:
            return texto
    except Exception:                                  # noqa: BLE001
        pass

    # 2) pdftotext
    if shutil.which("pdftotext"):
        try:
            with tempfile.TemporaryDirectory() as tmp:
                origen = Path(tmp) / "b.pdf"
                origen.write_bytes(datos)
                salida = subprocess.run(
                    ["pdftotext", "-layout", "-l", str(max_paginas), str(origen), "-"],
                    capture_output=True, timeout=60,
                )
                texto = salida.stdout.decode("utf-8", errors="replace").strip()
                if texto:
                    return texto
        except Exception:                              # noqa: BLE001
            pass

    # 3) pypdf
    try:
        import io

        from pypdf import PdfReader
        lector = PdfReader(io.BytesIO(datos))
        texto = "\n".join(
            (p.extract_text() or "") for p in lector.pages[:max_paginas]
        ).strip()
        if texto:
            return texto
    except Exception:                                  # noqa: BLE001
        pass

    return ""


# --------------------------------------------------------------------------
# Leer las letras de la imagen (OCR)
# --------------------------------------------------------------------------

def hay_ocr() -> bool:
    """¿Está el sistema equipado para leer imágenes?"""
    return bool(shutil.which("pdftoppm") and shutil.which("tesseract"))


def idioma_ocr() -> str:
    """
    Español si está instalado; si no, inglés.

    No es un capricho: el paquete de español conoce las tildes y la eñe, y sin
    él "gestión" sale "gestion" o "gestién". El inglés igual sirve de red —
    comparten alfabeto— pero lee peor. Que falte se nota en la calidad, así que
    conviene instalar `tesseract-ocr-spa` donde corra el motor.
    """
    try:
        salida = subprocess.run(["tesseract", "--list-langs"],
                                capture_output=True, timeout=20)
        idiomas = salida.stdout.decode("utf-8", errors="replace").split()
    except Exception:                                  # noqa: BLE001
        return "eng"
    return "spa" if "spa" in idiomas else "eng"


def texto_por_ocr(datos: bytes, max_paginas: int = OCR_PAGINAS) -> str:
    """
    Rasteriza las primeras páginas del PDF y les lee las letras.

    Es el último recurso y el más caro. Devuelve "" si el sistema no tiene las
    herramientas, si el PDF no se deja abrir o si se acaba el tiempo — nunca
    levanta una excepción, porque un aviso sin funciones es un problema mucho
    menor que una corrida caída.
    """
    if not datos or datos[:4] != b"%PDF" or not hay_ocr():
        return ""

    idioma = idioma_ocr()
    try:
        with tempfile.TemporaryDirectory() as tmp:
            carpeta = Path(tmp)
            (carpeta / "b.pdf").write_bytes(datos)

            # Una imagen por página. `-r` es la resolución: de ella depende que
            # el OCR distinga una 'i' de una 'l'.
            subprocess.run(
                ["pdftoppm", "-r", str(OCR_DPI), "-png",
                 "-f", "1", "-l", str(max_paginas),
                 str(carpeta / "b.pdf"), str(carpeta / "pg")],
                capture_output=True, timeout=OCR_SEGUNDOS,
            )

            partes = []
            for imagen in sorted(carpeta.glob("pg*.png"))[:max_paginas]:
                leido = subprocess.run(
                    ["tesseract", str(imagen), "-", "-l", idioma],
                    capture_output=True, timeout=OCR_SEGUNDOS,
                )
                partes.append(leido.stdout.decode("utf-8", errors="replace"))
            return "\n".join(partes).strip()
    except Exception:                                  # noqa: BLE001
        return ""


# --------------------------------------------------------------------------
# El guardián: lo ilegible no se publica
# --------------------------------------------------------------------------

# La `¡` y la `¿` solo ABREN frase en español, así que detrás de una letra no
# pintan nada: "Contab¡l¡zar", "Pr¡ncipales". Esa es la firma del texto mal
# digitalizado.
#
# Ojo con el detalle, que este test lo cazó: se mira solo lo que va DETRÁS de
# una letra. Mirar también lo que va delante rechazaba "¿Qué funciones tendrá
# el puesto?", que es español perfectamente correcto.
_SIGNO_EN_MEDIO = re.compile(r"\w[¡¿]")


def parece_ilegible(texto: str) -> bool:
    """
    ¿Este texto está tan roto que publicarlo sería peor que no publicar nada?

    Existe por la regla 2. El OCR se equivoca, y los PDF que llegan ya mal
    digitalizados vienen peor todavía. Una ficha que promete decir qué vas a
    hacer y muestra un renglón indescifrable rompe la promesa igual que un
    hueco, pero encima parece un error nuestro.

    Se mira lo que se puede medir sin diccionario:

      · signos de apertura pegados a una letra, que en español no existen;
      · qué proporción del renglón son letras de verdad. Un texto sano pasa
        del 80%; la basura del OCR se llena de barras, puntos y símbolos.

    A propósito NO se intenta adivinar si la frase tiene sentido. Eso sería
    inventar criterio, y el motor prefiere quedarse corto.
    """
    limpio = (texto or "").strip()
    if len(limpio) < 12:
        return True
    if _SIGNO_EN_MEDIO.search(limpio):
        return True

    utiles = sum(1 for c in limpio if c.isalpha() or c.isspace())
    return (utiles / len(limpio)) < 0.80


def descartar_ilegibles(funciones: list[str]) -> list[str]:
    """Deja solo las funciones que una persona podría leer en voz alta."""
    return [f for f in funciones if not parece_ilegible(f)]


# --------------------------------------------------------------------------
# Texto -> funciones
# --------------------------------------------------------------------------

def _es_fin_de_seccion(linea: str) -> bool:
    limpia = _sin_tildes_min(linea).strip(" :.-)")
    if not limpia or len(limpia) > 80:
        return False
    # Quita numeración inicial: "IV. REQUISITOS" -> "requisitos"
    limpia = re.sub(r"^(?:[ivxlc]+|\d+(?:\.\d+)*)\s*[\.\)\-]?\s*", "", limpia)
    return any(limpia == f or limpia.startswith(f + " ") or limpia.startswith(f + ":")
               for f in (_sin_tildes_min(x) for x in FIN_SECCION))


def _agrupar_items(lineas: list[str]) -> list[str]:
    """
    Une las líneas partidas por el ancho de página. Una línea nueva solo empieza
    un ítem si trae marca de viñeta o numeración; si no, continúa el anterior.
    """
    items: list[str] = []
    for linea in lineas:
        texto = linea.strip()
        if not texto:
            continue
        if MARCA_ITEM.match(texto) or not items:
            items.append(MARCA_ITEM.sub("", texto, count=1).strip())
        else:
            # ¿La anterior quedó cortada a media frase? Entonces es continuación.
            if items[-1].endswith((".", ";")) and texto[:1].isupper() and len(texto) > 25:
                items.append(texto)
            else:
                items[-1] = f"{items[-1]} {texto}".strip()
    return items


def _limpiar(items: list[str]) -> list[str]:
    salida, vistos = [], set()
    for it in items:
        texto = re.sub(r"\s+", " ", it).strip(" .;:-–—•*")
        texto = re.sub(r"\s*\.{3,}\s*\d*$", "", texto)      # rellenos de índice
        if not (18 <= len(texto) <= 400):
            continue
        if texto.count(" ") < 2:
            continue
        if re.match(r"(?i)^(p[aá]gina|anexo|firma|sello|nombre|dni|f\.?\s*$)", texto):
            continue
        clave = _sin_tildes_min(texto)[:60]
        if clave in vistos:
            continue
        vistos.add(clave)
        salida.append(texto[0].upper() + texto[1:])
    return salida[:12]


def extraer_funciones(texto: str) -> list[str]:
    """
    Busca la sección de funciones dentro del texto de las bases y la devuelve
    como lista de ítems. Si no la encuentra, devuelve lista vacía.
    """
    if not texto:
        return []

    lineas = [re.sub(r"[ \t]+", " ", l).strip() for l in texto.splitlines()]

    mejor: list[str] = []
    for i, linea in enumerate(lineas):
        # Se compara sin tildes: las bases escriben "ESPECÍFICAS" y "ESPECIFICAS"
        # con la misma naturalidad.
        plano = _sin_tildes_min(linea)
        if not INICIO_FUNCIONES.match(plano):
            # También vale "FUNCIONES DEL PUESTO: a) ..." todo en una línea.
            if not re.match(r"^\s*(?:[ivxlc]+\s*[\.\)]\s*)?funciones[^:]{0,30}:\s*\S", plano):
                continue

        bloque: list[str] = []
        resto = re.split(r":", linea, maxsplit=1)
        if len(resto) == 2 and len(resto[1].strip()) > 15:
            bloque.append(resto[1].strip())

        for siguiente in lineas[i + 1:]:
            if _es_fin_de_seccion(siguiente):
                break
            bloque.append(siguiente)
            if len(bloque) > 60:                       # no seguimos hasta el final del PDF
                break

        # El descarte de lo ilegible va ANTES de comparar candidatas, no
        # después: si no, un bloque lleno de basura ganaría por cantidad y
        # dejaría fuera al bueno, para terminar publicando nada.
        candidatas = descartar_ilegibles(_limpiar(_agrupar_items(bloque)))
        if len(candidatas) > len(mejor):
            mejor = candidatas

    return mejor


# --------------------------------------------------------------------------
# Caché en disco
# --------------------------------------------------------------------------

def ruta_cache(url: str) -> Path:
    return CACHE / (hashlib.sha1(url.encode()).hexdigest()[:20] + ".pdf")


def desde_cache(url: str) -> bytes | None:
    ruta = ruta_cache(url)
    return ruta.read_bytes() if ruta.exists() else None


def guardar_en_cache(url: str, datos: bytes) -> None:
    try:
        CACHE.mkdir(parents=True, exist_ok=True)
        ruta_cache(url).write_bytes(datos)
    except OSError:
        pass                                            # la caché es un lujo, no un requisito


# --------------------------------------------------------------------------
# Detección del enlace correcto dentro de la página del aviso
# --------------------------------------------------------------------------

_ENLACE = re.compile(r'<a[^>]+href=["\']([^"\']+\.pdf[^"\']*)["\'][^>]*>(.*?)</a>', re.I | re.S)

# Cuanto más alto el puntaje, más probable es que ese PDF traiga las funciones.
_PISTAS = (
    (("bases", "base del concurso", "base de concurso"), 10),
    (("perfil", "puesto"), 8),
    (("anuncio", "convocatoria"), 6),
    (("terminos de referencia", "tdr"), 6),
    (("cronograma", "resultados", "anexo", "formato", "declaracion"), -10),
)


def enlaces_pdf(html: str, base: str = "") -> list[str]:
    """Devuelve los PDFs de la página, del más prometedor al menos."""
    from urllib.parse import urljoin

    candidatos: list[tuple[int, str]] = []
    for href, etiqueta in _ENLACE.findall(html or ""):
        # urljoin resuelve los '../' y las rutas relativas como lo haría el
        # navegador. Concatenar a mano generaba URLs rotas.
        url = urljoin(base + "/" if base and not base.endswith("/") else base, href.strip())
        contexto = _sin_tildes_min(f"{href} {re.sub(r'<[^>]+>', ' ', etiqueta)}")
        puntaje = 0
        for palabras, peso in _PISTAS:
            if any(p in contexto for p in palabras):
                puntaje += peso
        candidatos.append((puntaje, url))

    vistos, salida = set(), []
    for _, url in sorted(candidatos, key=lambda c: -c[0]):
        if url not in vistos:
            vistos.add(url)
            salida.append(url)
    return salida
