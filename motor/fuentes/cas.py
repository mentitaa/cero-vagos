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

EL OBSTÁCULO, Y LA DECISIÓN
---------------------------
Una página puede traer VARIOS puestos con sueldos distintos. Surquillo lista 6
plazas en 2 puestos (S/ 1,350 y S/ 2,800); la Municipalidad de Arequipa dice
283 plazas. El motor asume una dirección, un aviso.

Decisión de Mentita (5/8/2026), opción 1: **se publican solo las convocatorias
de UNA plaza.** No toca la pieza central del motor, y lo que no se puede partir
bien no se publica — que es la regla 2 de siempre.

Las descartadas se CUENTAN y quedan en el registro de la corrida, para saber
qué se está dejando pasar y poder revisar la decisión con números.

Filtrar sale gratis: el número de plazas viene en la propia dirección
(`...-1-plazas-67463.html`), así que las de varias plazas ni se descargan.

LO QUE ESTE LECTOR NO HACE
--------------------------
No deduce el sueldo, no deduce el puesto y no rellena huecos. Si el resumen de
la convocatoria y la ficha del puesto declaran montos distintos, el aviso se
rechaza en vez de elegir uno. Ante la duda, no se publica.
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

# Etiquetas que cierran la ficha de un puesto. Todo lo que viene después
# (cómo postular, bases, cronograma) no es requisito.
_FIN_DE_PUESTO = (
    "lugar de labores", "salario", "plazo para postular", "como postular",
    "remuneracion", "ver aqui bases", "descargar aqui",
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


def _requisitos_del_puesto(lineas: list[str], desde: int) -> list[str]:
    """
    Lo que la ficha del puesto pide, en orden: primero la formación
    ('Profesiones/Oficios'), después la experiencia.

    Se recorre hacia abajo desde el puesto y se corta en la primera etiqueta
    que ya no es un requisito. Sin ese corte, el 'cómo postular' y la dirección
    de la mesa de partes terminarían contados como requisitos.
    """
    salida: list[str] = []
    dentro = False
    for linea in lineas[desde:]:
        limpia = _limpiar_etiqueta(linea)

        if any(tras_etiqueta(limpia, f) is not None for f in _FIN_DE_PUESTO):
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


def parsear_cas(html: str, url: str, fuente: str) -> OfertaCruda | None:
    """
    Lee la ficha de una convocatoria CAS.

    Devuelve None —es decir, el aviso se descarta— cuando:
      · la convocatoria trae más de una plaza (decisión: opción 1);
      · la página no nombra el puesto;
      · el resumen y la ficha declaran sueldos distintos;
      · el plazo de postulación ya cerró o no se pudo leer.
    """
    from ..normalizar import html_a_lineas

    if plazas_en_url(url) != 1:
        return None

    lineas = html_a_lineas(html)
    if not lineas:
        return None

    # ---- una sola plaza, verificado en la página y no solo en la URL ----
    # La dirección es una pista barata, pero es solo texto: si la página lista
    # dos puestos, publicar uno sería elegir por el postulante.
    posiciones = [i for i, l in enumerate(lineas)
                  if sin_tildes(_limpiar_etiqueta(l)).startswith("vacantes")]
    if len(posiciones) != 1:
        return None
    inicio = posiciones[0]

    vacantes = campo(lineas, "N° de vacantes") or campo(lineas, "Vacantes")
    if vacantes and not re.match(r"^\s*1\b", vacantes):
        return None

    # ---- puesto ----
    # Dos fuentes independientes: el encabezado de la ficha (la línea justo
    # antes de "Vacantes") y el campo del resumen. Se prefiere el encabezado.
    encabezado = _limpiar_etiqueta(lineas[inicio - 1]) if inicio else ""
    del_resumen = campo(lineas, "Formación académica")
    puesto = encabezado if 3 < len(encabezado) <= 90 else del_resumen
    if not puesto or len(puesto) < 4:
        return None            # nunca se inventa un cargo (regla 8)

    # ---- sueldo: los dos montos tienen que coincidir ----
    salario = campo(lineas, "Salario")
    remuneracion = campo(lineas, "Remuneración")
    a, b = _monto(salario), _monto(remuneracion)
    if a and b and a != b:
        return None            # ante la duda, no se publica (regla 2)
    sueldo_texto = salario or remuneracion
    if not sueldo_texto:
        return None

    # ---- plazo ----
    vence = fecha_cas(campo(lineas, "Plazo para postular"))
    if not vence or vence < date.today():
        return None

    entidad = campo(lineas, "Institución")
    ubicacion = campo(lineas, "Lugar de trabajo") or campo(lineas, "Lugar de labores")

    # ---- el cuerpo del aviso, armado a mano ----
    # No se pasa la página entera como hacen otros lectores: el menú, el pie y
    # el aviso de WhatsApp terminarían contados como requisitos. Se arma solo
    # con lo que sí es del puesto, bajo encabezados que el normalizador conoce.
    requisitos = _requisitos_del_puesto(lineas, inicio)
    beneficios = BENEFICIOS_POR_REGIMEN["CAS"]

    partes = [f"<p>Convocatoria CAS de {entidad or 'una entidad del Estado'}"
              f"{f' en {ubicacion}' if ubicacion else ''}. Una plaza.</p>"]
    if requisitos:
        partes.append("<p>Requisitos</p><ul>"
                      + "".join(f"<li>{r}</li>" for r in requisitos) + "</ul>")
    partes.append("<p>Beneficios</p><ul>"
                  + "".join(f"<li>{b}</li>" for b in beneficios) + "</ul>")

    return OfertaCruda(
        fuente=fuente,
        url=url,
        puesto=puesto,
        empresa=entidad,
        descripcion_html="".join(partes),
        ubicacion_texto=ubicacion,
        sueldo_texto=sueldo_texto,
        # La página no publica fecha de publicación, y el `lastmod` del sitemap
        # dice cuándo se tocó la página, no cuándo salió el aviso. Se deja
        # vacía a propósito: el plazo de postulación ya cumple esa función y es
        # un dato que el propio aviso declara.
        publicado=None,
        extra={
            "perfil": "publico",
            "regimen": "CAS",
            "beneficios_de_ley": True,
            "plazas": 1,
            "vence": vence.isoformat(),
        },
    )


# --------------------------------------------------------------------------

class ConvocatoriasCAS(PortalWeb):
    """
    Igual que cualquier portal, salvo por una cosa: descarta las convocatorias
    de varias plazas ANTES de descargarlas, y cuenta cuántas descartó.

    Ese conteo es el que dice si la opción 1 se queda corta. Sin él, la fuente
    se vería sana entregando la mitad de lo que hay.
    """

    def urls_de_avisos(self, limite: int = 100) -> list[str]:
        # Se pide de más porque unas dos de cada tres se van a descartar por
        # traer más de una plaza.
        todas = super().urls_de_avisos(limite * 3)
        de_una, saltadas, plazas_perdidas = [], 0, 0
        for u in todas:
            n = plazas_en_url(u)
            if n == 1:
                de_una.append(u)
            elif n > 1:
                saltadas += 1
                plazas_perdidas += n

        self.saltadas_por_plazas = saltadas
        self.plazas_perdidas = plazas_perdidas
        if saltadas:
            self._anotar(
                f"{saltadas} convocatorias saltadas por traer más de una plaza "
                f"({plazas_perdidas} plazas en total). Es la decisión tomada: "
                f"una página con varios puestos no se puede partir en avisos "
                f"sin inventar. Si este número crece mucho, toca revisarla."
            )
        return de_una[:limite]

    def recolectar(self, limite: int = 100) -> Iterator[OfertaCruda]:
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
