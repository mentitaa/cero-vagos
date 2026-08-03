"""
Normalización del cuerpo del aviso.

Convierte el HTML/texto sucio de cada portal en las tres listas que Cero Vagos
exige: funciones, requisitos y beneficios. Además deduce ciudad, modalidad y
categoría.
"""
from __future__ import annotations

import html
import re

from .modelos import CATEGORIAS, sin_tildes

# --------------------------------------------------------------------------
# Encabezados que usan los portales peruanos para cada bloque
# --------------------------------------------------------------------------

ENCABEZADOS = {
    "funciones": (
        "funciones", "funciones principales", "funciones del puesto",
        "principales funciones", "responsabilidades", "responsabilidades del puesto",
        "actividades", "actividades a realizar", "principales actividades",
        "que haras", "que haras en el puesto", "tus retos", "misión del puesto",
        "mision del puesto", "descripcion del puesto", "acerca del puesto",
        "tareas", "labores a realizar", "objetivo del puesto",
    ),
    "requisitos": (
        "requisitos", "requisitos del puesto", "requisitos minimos",
        "requerimientos", "perfil", "perfil del puesto", "perfil requerido",
        "que buscamos", "buscamos", "a quien buscamos", "competencias",
        "conocimientos", "conocimientos requeridos", "experiencia requerida",
        "formacion academica", "estudios", "requisitos indispensables",
    ),
    "beneficios": (
        "beneficios", "beneficios del puesto", "que ofrecemos", "ofrecemos",
        "te ofrecemos", "que te ofrecemos", "condiciones", "condiciones laborales",
        "nuestros beneficios", "beneficios corporativos", "por que trabajar con nosotros",
        "que ganas", "compensacion", "horario y beneficios",
    ),
}

# Encabezados que marcan el fin del contenido útil del aviso. Todo lo que viene
# después (cronogramas, formularios, avisos relacionados, pie de página) se
# descarta: sin esto, el menú del portal termina contado como "funciones".
FIN_DE_BLOQUE = (
    "documentos", "documentacion",
    "cronograma", "etapas del proceso", "proceso de seleccion",
    "como postular", "postular", "postula ahora", "para postular",
    "preguntas frecuentes", "otras convocatorias", "ver mas convocatorias",
    "avisos relacionados", "empleos similares", "ofertas similares",
    "comparte", "siguenos", "suscribete", "sobre nosotros", "contacto",
    "terminos y condiciones", "politica de privacidad", "aviso legal",
)

VERBOS_FUNCION = (
    "gestionar", "elaborar", "realizar", "coordinar", "supervisar", "desarrollar",
    "atender", "registrar", "analizar", "controlar", "ejecutar", "apoyar",
    "diseñar", "implementar", "reportar", "asegurar", "planificar", "negociar",
    "capacitar", "monitorear", "administrar", "preparar", "validar", "liderar",
)

FRASES_RELLENO = (
    "excelente ambiente laboral", "buen clima laboral", "grato ambiente",
    "oportunidad de crecimiento", "linea de carrera",  # solo si van solas
    "somos una empresa lider", "unete a nuestro equipo", "postula ya",
    "empresa en crecimiento", "estabilidad laboral",
)

# --------------------------------------------------------------------------
# Geografía peruana (lo mínimo útil; ampliable)
# --------------------------------------------------------------------------

DEPARTAMENTOS = (
    "Lima", "Arequipa", "La Libertad", "Piura", "Lambayeque", "Cusco", "Junín",
    "Áncash", "Ica", "Cajamarca", "Puno", "Loreto", "Callao", "Tacna",
    "San Martín", "Ayacucho", "Huánuco", "Ucayali", "Moquegua", "Apurímac",
    "Amazonas", "Tumbes", "Pasco", "Madre de Dios", "Huancavelica",
)

CIUDAD_A_DEPARTAMENTO = {
    "lima": "Lima", "callao": "Callao", "arequipa": "Arequipa",
    "trujillo": "La Libertad", "chiclayo": "Lambayeque", "piura": "Piura",
    "cusco": "Cusco", "cuzco": "Cusco", "huancayo": "Junín", "chimbote": "Áncash",
    "huaraz": "Áncash", "ica": "Ica", "chincha": "Ica", "pisco": "Ica",
    "tacna": "Tacna", "puno": "Puno", "juliaca": "Puno", "iquitos": "Loreto",
    "pucallpa": "Ucayali", "tarapoto": "San Martín", "cajamarca": "Cajamarca",
    "ayacucho": "Ayacucho", "huanuco": "Huánuco", "tumbes": "Tumbes",
    "moquegua": "Moquegua", "ilo": "Moquegua", "sullana": "Piura",
    "talara": "Piura", "abancay": "Apurímac", "cerro de pasco": "Pasco",
}

DISTRITOS_LIMA = (
    "san isidro", "miraflores", "surco", "santiago de surco", "la molina",
    "san borja", "jesus maria", "magdalena", "lince", "barranco", "chorrillos",
    "surquillo", "san miguel", "pueblo libre", "los olivos", "san martin de porres",
    "comas", "independencia", "ate", "santa anita", "san juan de lurigancho",
    "villa el salvador", "chorrillos", "cercado de lima", "la victoria",
    "breña", "rimac", "callao", "bellavista", "la perla", "ventanilla",
)

# --------------------------------------------------------------------------
# Categorías por palabras clave del puesto
# --------------------------------------------------------------------------

PISTAS_CATEGORIA = {
    "Tecnología": ("desarrollador", "developer", "programador", "backend", "frontend",
                   "fullstack", "qa", "devops", "data", "datos", "software", "sistemas",
                   "ti ", "it ", "ciberseguridad", "soporte tecnico", "analista funcional",
                   "ux", "ui", "scrum", "cloud", "base de datos", "sre"),
    "Ventas": ("vendedor", "ventas", "comercial", "ejecutivo comercial", "asesor de ventas",
               "key account", "kam", "televentas", "promotor", "impulsador"),
    "Contabilidad": ("contable", "contador", "contabilidad", "tesoreria", "tributario",
                     "costos", "auditoria", "facturacion", "cobranzas", "finanzas"),
    "Salud": ("enfermer", "medico", "médico", "tecnico en enfermeria", "odontolog",
              "psicolog", "nutricionista", "obstetra", "farmac", "laboratorio clinico",
              "tecnologo medico", "fisioterapeuta"),
    "Prácticas": ("practicante", "practicas", "prácticas", "trainee", "pasante", "intern"),
    "Administración": ("asistente administrativ", "administrativ", "recepcionist",
                       "secretari", "asistente de gerencia", "coordinador administrativo"),
    "Logística": ("almacen", "almacén", "logistic", "logístic", "despacho", "distribucion",
                  "transporte", "conductor", "chofer", "operario de almacen", "picking",
                  "supply", "compras", "abastecimiento"),
    "Marketing": ("marketing", "community manager", "publicidad", "comunicaciones",
                  "diseñador grafico", "contenido", "redes sociales", "trade marketing",
                  "brand", "seo", "performance"),
    "Ingeniería": ("ingenier", "mantenimiento", "produccion", "producción", "planta",
                   "mecanic", "electric", "civil", "industrial", "seguridad y salud",
                   "sst", "calidad", "proyectos"),
    "Educación": ("docente", "profesor", "tutor", "auxiliar de educacion", "coordinador academico",
                  "capacitador", "instructor"),
    "Legal": ("abogad", "legal", "juridic", "jurídic", "asesor legal", "compliance"),
    "Recursos Humanos": ("recursos humanos", "rrhh", "reclutador", "reclutamiento",
                         "seleccion de personal", "gestion humana", "talento", "planilla"),
    "Atención al Cliente": ("call center", "atencion al cliente", "atención al cliente",
                            "servicio al cliente", "asesor telefonico", "back office",
                            "plataforma de atencion"),
    "Construcción": ("obra", "construccion", "construcción", "albañil", "maestro de obra",
                     "topografo", "capataz", "encofrador"),
    "Gastronomía": ("cocinero", "chef", "mozo", "barista", "bartender", "panadero",
                    "pastelero", "ayudante de cocina", "azafata"),
}


# --------------------------------------------------------------------------
# HTML -> texto con estructura
# --------------------------------------------------------------------------

def html_a_lineas(bruto: str) -> list[str]:
    """
    Convierte HTML de aviso en una lista de líneas limpias, conservando el
    salto de línea donde había <br>, </p>, </li>, etc.
    """
    if not bruto:
        return []

    t = bruto
    t = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", t)
    t = re.sub(r"(?i)<\s*br\s*/?\s*>", "\n", t)
    t = re.sub(r"(?i)</\s*(p|div|li|tr|h[1-6]|section|ul|ol)\s*>", "\n", t)
    t = re.sub(r"(?i)<\s*li[^>]*>", "\n• ", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t)
    t = t.replace("\xa0", " ").replace("​", "")

    lineas = []
    for linea in t.split("\n"):
        linea = re.sub(r"[ \t]+", " ", linea).strip()
        linea = re.sub(r"^[•\-\*•●▪·o]\s*", "", linea)
        linea = re.sub(r"^\d{1,2}[\.\)]\s*", "", linea)
        if linea and len(linea) > 1:
            lineas.append(linea)
    return lineas


def _es_encabezado(linea: str) -> str | None:
    """Si la línea es un título de bloque, devuelve el bloque; si no, None."""
    limpia = sin_tildes(linea).strip(" :.-–—¿?¡!*")
    if len(limpia) > 60:
        return None
    # Con prefijo, no exacto: "Cronograma del proceso" y "Documentos oficiales"
    # también cierran el aviso. Si no, la tabla de 17 etapas del concurso
    # termina contada como requisitos.
    if any(limpia == f or limpia.startswith(f + " ") for f in FIN_DE_BLOQUE):
        return "descartado"
    for bloque, titulos in ENCABEZADOS.items():
        for titulo in titulos:
            if limpia == titulo or limpia.startswith(titulo + " ") or limpia.rstrip("s") == titulo.rstrip("s"):
                return bloque
    return None


def partir_en_bloques(lineas: list[str]) -> dict[str, list[str]]:
    """
    Recorre las líneas y las reparte según el último encabezado visto.
    Lo que aparece antes de cualquier encabezado va a 'intro'.
    """
    bloques: dict[str, list[str]] = {
        "intro": [], "funciones": [], "requisitos": [], "beneficios": [], "descartado": [],
    }
    actual = "intro"

    for linea in lineas:
        bloque = _es_encabezado(linea)
        if bloque:
            actual = bloque
            # Caso "Funciones: gestionar la cartera..." (título y contenido en la misma línea)
            resto = re.split(r"[:：]", linea, maxsplit=1)
            if len(resto) == 2 and len(resto[1].strip()) > 15:
                bloques[actual].append(resto[1].strip())
            continue
        bloques[actual].append(linea)

    return bloques


def _limpiar_items(items: list[str], minimo: int = 12, maximo: int = 320) -> list[str]:
    """Deja solo líneas que parecen ítems reales de una lista."""
    salida, vistos = [], set()
    for it in items:
        texto = it.strip(" -–—•*:;")
        if not (minimo <= len(texto) <= maximo):
            continue
        if texto.count(" ") < 1:                       # una palabra suelta
            continue
        if re.match(r"(?i)^(av\.|jr\.|calle|telf|tel[eé]fono|correo|email|enviar cv|postula)", texto):
            continue
        # "Funciones no especificadas en la convocatoria" no es una función:
        # es la ausencia de una. Contarla sería mentirle al filtro.
        if re.search(r"(?i)no\s+(?:se\s+)?especificad", texto):
            continue
        clave = sin_tildes(texto)[:70]
        if clave in vistos:
            continue
        vistos.add(clave)
        salida.append(texto[0].upper() + texto[1:])
    return salida[:12]


def _rescatar_por_verbos(lineas: list[str]) -> list[str]:
    """Cuando el aviso no usa encabezados, buscamos líneas que empiecen con verbo."""
    candidatas = []
    for linea in lineas:
        primera = sin_tildes(linea).split(" ")[0].rstrip(",.:")
        if primera in [sin_tildes(v) for v in VERBOS_FUNCION] or primera.endswith("ar") and len(primera) > 5:
            candidatas.append(linea)
    return candidatas


def extraer_bloques(cuerpo_html: str) -> dict[str, list[str]]:
    """Punto de entrada: HTML del aviso -> funciones / requisitos / beneficios / intro."""
    lineas = html_a_lineas(cuerpo_html)
    bloques = partir_en_bloques(lineas)

    resultado = {
        "intro": bloques["intro"],
        "funciones": _limpiar_items(bloques["funciones"]),
        "requisitos": _limpiar_items(bloques["requisitos"]),
        "beneficios": _limpiar_items(bloques["beneficios"]),
    }

    if not resultado["funciones"]:
        resultado["funciones"] = _limpiar_items(_rescatar_por_verbos(bloques["intro"]))

    return resultado


def armar_resumen(bloques: dict[str, list[str]], puesto: str) -> str:
    for linea in bloques.get("intro", []):
        if 40 <= len(linea) <= 240 and not sin_tildes(linea).startswith(sin_tildes(puesto)[:12]):
            return linea
    if bloques.get("funciones"):
        return bloques["funciones"][0]
    return ""


# --------------------------------------------------------------------------
# Deducciones
# --------------------------------------------------------------------------

def detectar_modalidad(texto: str) -> str:
    plano = sin_tildes(texto)
    if re.search(r"\b(hibrido|semipresencial|mixto|3 dias en oficina|2 dias remoto)\b", plano):
        return "Híbrido"
    if re.search(r"\b(remoto|teletrabajo|home office|100% remoto|desde casa|work from home)\b", plano):
        return "Remoto"
    if re.search(r"\b(presencial|en planta|en obra|en tienda|en sede)\b", plano):
        return "Presencial"
    return "Presencial"


def detectar_ubicacion(texto_ubicacion: str, cuerpo: str = "") -> tuple[str, str]:
    """Devuelve (ciudad, departamento)."""
    fuente = f"{texto_ubicacion} {cuerpo[:1200]}"
    plano = sin_tildes(fuente)

    for ciudad, depa in CIUDAD_A_DEPARTAMENTO.items():
        if re.search(rf"\b{re.escape(ciudad)}\b", plano):
            return ciudad.title(), depa

    for distrito in DISTRITOS_LIMA:
        if re.search(rf"\b{re.escape(distrito)}\b", plano):
            return "Lima", "Lima"

    for depa in DEPARTAMENTOS:
        if re.search(rf"\b{re.escape(sin_tildes(depa))}\b", plano):
            return depa, depa

    return "", ""


def detectar_categoria(puesto: str, cuerpo: str = "") -> str:
    plano = sin_tildes(f"{puesto} {puesto} {cuerpo[:500]}")   # el puesto pesa doble
    puntajes = {}
    for categoria, pistas in PISTAS_CATEGORIA.items():
        puntaje = sum(1 for p in pistas if sin_tildes(p) in plano)
        if puntaje:
            puntajes[categoria] = puntaje
    if not puntajes:
        return "Otros"
    return max(puntajes.items(), key=lambda kv: kv[1])[0]


# --------------------------------------------------------------------------
# Limpieza del título
#
# Las consultoras escriben el título como si fuera un cartel de feria:
#   "¡GANA MÁS DE 1800 SOLES! OPERARIO DE PRODUCCIÓN — STA ANITA / PLANILLA
#    COMPLETA + ALIMENTACIÓN - INGRESO INMEDIATO + HORAS EXTRA"
# El puesto son dos palabras; el resto es publicidad. Eso se recorta.
# --------------------------------------------------------------------------

# Si un tramo del título contiene alguna de estas, deja de ser el puesto.
RUIDO_TITULO = (
    "gana", "ganaras", "ganaras hasta", "sueldo", "salario", "remuneracion",
    "planilla", "beneficios", "bono", "bonos", "pago", "pagos", "ingreso inmediato",
    "ingreso a planilla", "alimentacion", "movilidad", "horas extra", "hora extra",
    "turnos", "turno", "horario", "rotativo", "rotativos", "part time", "full time",
    "urgente", "urgentemente", "postula", "postular", "unete", "sumate", "trabaja con",
    "importante empresa", "gran empresa", "empresa lider", "reconocida empresa",
    "contratacion inmediata", "inicio inmediato", "sin experiencia", "con experiencia",
    "vacantes", "vacante", "convocatoria", "oportunidad", "capacitacion",
    "crecimiento", "linea de carrera", "desde s/", "s/", "soles", "referidos",
    "lunes a viernes", "lunes a sabado", "de lunes",
)

_SEPARADORES = re.compile(r"\s*(?:[/|]|\s[-–—]\s|(?<=\s)\+\s|,\s(?=[A-ZÁÉÍÓÚÑ]{4,}))\s*")

# Palabras que van en minúscula al reescribir un título gritado en mayúsculas.
_MINUSCULAS = {"de", "del", "la", "las", "el", "los", "y", "e", "o", "u", "en",
               "para", "por", "con", "a", "al", "sin", "sobre", "the", "of"}

# Siglas que deben quedar tal cual.
_SIGLAS = {"ti", "it", "rrhh", "sst", "sso", "ssoma", "hse", "qa", "ux", "ui",
           "sap", "erp", "crm", "bi", "seo", "sem", "kam", "b2b", "b2c", "cnc",
           "sac", "eirl", "srl", "cas", "gpt", "ia", "ai", "iso", "hvac", "pmo"}


def _tramo_es_puesto(tramo: str) -> bool:
    plano = sin_tildes(tramo).strip()
    if len(plano) < 4:
        return False
    if any(r in plano for r in RUIDO_TITULO):
        return False
    if re.search(r"\d{3,}", plano):          # montos, códigos
        return False
    return True


def _titular(texto: str) -> str:
    """Reescribe un título gritado en mayúsculas, respetando siglas."""
    if not texto.isupper():
        return texto
    palabras = []
    for i, palabra in enumerate(texto.lower().split()):
        limpia = palabra.strip("().,-")
        if limpia in _SIGLAS:
            palabras.append(palabra.upper())
        elif i > 0 and limpia in _MINUSCULAS:
            palabras.append(palabra)
        else:
            palabras.append(palabra[:1].upper() + palabra[1:])
    return " ".join(palabras)


def limpiar_puesto(titulo: str) -> str:
    """
    Deja solo el puesto. Ante la duda, devuelve el título original: es peor
    recortar de más y perder el nombre del cargo.
    """
    if not titulo:
        return ""

    texto = re.sub(r"\s+", " ", titulo).strip()

    # Fuera los ganchos entre signos de admiración: "¡GANA MÁS DE 1800 SOLES!"
    texto = re.sub(r"[¡!][^!¡]{0,80}!", " ", texto).strip(" -–—/|,")
    texto = re.sub(r"\s+", " ", texto)

    tramos = [t.strip(" -–—/|,.") for t in _SEPARADORES.split(texto) if t.strip()]
    puesto = next((t for t in tramos if _tramo_es_puesto(t)), "")

    if not puesto:
        puesto = tramos[0] if tramos else texto

    # Restos comunes al final: "(Lurigancho)", "- Trujillo", "para Lima"
    puesto = re.sub(r"\s*\((?:[^)]{0,40})\)\s*$", "", puesto).strip(" -–—/|,.")
    puesto = _titular(puesto)

    return puesto or titulo.strip()


def es_relleno(texto: str) -> bool:
    """True si la línea es puro adorno corporativo sin información."""
    plano = sin_tildes(texto)
    return any(sin_tildes(f) in plano for f in FRASES_RELLENO) and len(texto) < 60
