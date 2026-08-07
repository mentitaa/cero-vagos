"""
Fuente genérica para portales de empleo.

Flujo:
    robots.txt -> sitemap (o listados) -> descarga (HTTP o navegador) ->
    JSON-LD JobPosting -> OfertaCruda

Dos cosas verificadas en campo, que definen el diseño:

1. Los portales grandes del Perú son aplicaciones React. El HTML que llega por
   HTTP simple viene vacío. Para esos hace falta `necesita_render=True`
   (Playwright). Los sitios server-side (webs de empresa, portales públicos,
   bolsas universitarias) funcionan con HTTP a secas.

2. Los sitemaps sí funcionan por HTTP y traen `lastmod`, así que sirven para
   descubrir avisos frescos sin abrir un navegador.
"""
from __future__ import annotations

import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field

from ..modelos import OfertaCruda
from .base import USER_AGENT, ErrorFuente, Fuente
from .jsonld import extraer_jobposting
from .render import HAY_PLAYWRIGHT, Navegador
from .robots import Robots
from .sitemap import filtrar_recientes, parsear

try:
    import requests
except ImportError:                                   # pragma: no cover
    requests = None


def _limpiar_enlace(bruto: str, base: str) -> str:
    """
    Deja una URL utilizable a partir de lo que se sacó del HTML.

    Los sitios modernos incrustan sus datos como JSON dentro del HTML, con las
    comillas escapadas. Al extraer un enlace se arrastra la barra invertida y
    queda '.../aviso-797491\\', que devuelve 404. Un solo carácter de más
    tumbaba la mitad de las descargas.
    """
    url = (bruto or "").strip().strip("\\\"'`,;)]}")
    url = url.replace("\\/", "/").replace("&amp;", "&")
    if not url:
        return ""
    if not url.startswith("http"):
        url = f"{base.rstrip('/')}/{url.lstrip('/')}"
    return url


def _plazo_cerrado(cruda: OfertaCruda) -> bool:
    """El aviso declara su fecha de cierre y ya pasó."""
    from datetime import date as _date
    valor = str(cruda.extra.get("vence") or "")[:10]
    if not valor:
        return False
    try:
        return _date.fromisoformat(valor) < _date.today()
    except ValueError:
        return False


def _demasiado_antigua(cruda: OfertaCruda, dias_maximo: int) -> bool:
    """
    Se descarta por FECHA DE PUBLICACIÓN, no por plazo de postulación.

    En el sector público la fecha de cierre muchas veces no se publica o no se
    puede leer, así que sirve de poco. Lo que sí es confiable es cuándo salió
    el aviso, y con eso basta para no llenar la web de cosas viejas.
    """
    from datetime import date as _date
    if not cruda.publicado:
        return False
    return (_date.today() - cruda.publicado).days > dias_maximo


@dataclass
class Diagnostico:
    """Resultado de revisar una fuente antes de dejarla corriendo sola."""
    portal: str
    robots: str = "?"
    urls_descubiertas: int = 0
    muestra_con_jsonld: bool | None = None
    detalle: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        jsonld = {True: "sí", False: "NO", None: "—"}[self.muestra_con_jsonld]
        lineas = [f"{self.portal:<22} robots: {self.robots:<10} "
                  f"urls: {self.urls_descubiertas:<5} JSON-LD: {jsonld}"]
        lineas += [f"    · {d}" for d in self.detalle]
        return "\n".join(lineas)


class PortalWeb(Fuente):

    def __init__(
        self,
        nombre: str,
        base: str,
        *,
        sitemaps: tuple[str, ...] = (),
        listados: tuple[str, ...] = (),
        patron_aviso: str = "",
        necesita_render: bool = False,
        espera_selector: str = "",
        dias_ventana: int = 120,
        dias_publicado: int = 0,
        ordenar_por_id: bool = False,
        nota: str = "",
        parser: Callable[[str, str, str], OfertaCruda | None] | None = None,
        enriquecer: Callable[..., str] | None = None,
    ):
        self.nombre = nombre
        self.base = base.rstrip("/")
        self.sitemaps = sitemaps
        self.listados = listados
        self.patron_aviso = patron_aviso
        self.necesita_render = necesita_render
        self.espera_selector = espera_selector
        # Dos ventanas distintas, y confundirlas cuesta caro:
        #
        #   dias_ventana    → filtra el SITEMAP por su lastmod. Esa fecha dice
        #                     cuándo el portal tocó la página, que no es cuándo
        #                     se publicó el aviso. Va holgada a propósito.
        #   dias_publicado  → filtra por la fecha de publicación REAL del aviso,
        #                     leída de la página. Esta es la que importa.
        self.dias_ventana = dias_ventana
        from ..score import MAX_DIAS_ANTIGUEDAD
        self.dias_publicado = dias_publicado or MAX_DIAS_ANTIGUEDAD
        # Cuando el sitemap no trae fechas útiles, el número al final de la URL
        # suele ser un correlativo: el más alto es el aviso más nuevo.
        self.ordenar_por_id = ordenar_por_id
        self.nota = nota
        # Por defecto se lee el JSON-LD. Un portal con formato propio pasa aquí
        # su propia función (html, url, fuente) -> OfertaCruda | None.
        self.parser = parser or extraer_jobposting
        # Paso opcional posterior al parseo: por ejemplo, abrir el PDF de las
        # bases para sacar las funciones que la página no publica.
        self.enriquecer = enriquecer
        # Lo pone el pipeline: devuelve True si esa URL ya se revisó hace poco.
        # Permite retomar una corrida cortada sin repetir el trabajo.
        self.ya_visto = None
        # Direcciones concretas a releer, en vez de salir a descubrirlas.
        # Lo llena `--reparar` con lo que ya está publicado. Ver
        # `Almacen.urls_publicadas`.
        self.urls_fijas: list[str] = []
        # Lo pone el pipeline para poder contar qué está pasando. Sin esto, el
        # motor puede tardar minutos en descubrir direcciones o en abrir el
        # navegador sin escribir una sola línea, y desde afuera parece colgado.
        self.avisar = None
        self.robots = Robots()
        self._navegador: Navegador | None = None
        # Todo lo que salió mal durante la corrida. Sin esto, una fuente que
        # devuelve cero avisos no se distingue de una que no encontró nada.
        self._problemas: dict[str, list] = {}

    def _avisar(self, mensaje: str) -> None:
        if self.avisar:
            self.avisar(mensaje)

    def _anotar(self, mensaje) -> None:
        """
        Agrupa los problemas por tipo. El mismo fallo repetido en 60 URLs es un
        solo problema con 60 casos, no 60 líneas en pantalla.
        """
        texto = " ".join(str(mensaje).split())
        clave = re.sub(r"https?://\S+", "<url>", texto)
        if clave in self._problemas:
            self._problemas[clave][1] += 1
        else:
            self._problemas[clave] = [texto, 1]

    def _reiniciar_problemas(self) -> None:
        self._problemas = {}

    @property
    def errores(self) -> list[str]:
        salida = []
        for texto, veces in self._problemas.values():
            recorte = texto if len(texto) <= 300 else texto[:300] + "…"
            salida.append(f"{recorte}" + (f"   [se repitió {veces} veces]" if veces > 1 else ""))
        return salida

    @property
    def activa(self) -> bool:                          # type: ignore[override]
        if requests is None:
            return False
        if self.necesita_render and not HAY_PLAYWRIGHT:
            return False
        return True

    @activa.setter
    def activa(self, _valor: bool) -> None:
        pass                                           # se deduce, no se fija

    # ---------------- descarga ----------------

    def _bajar_bytes(self, url: str, max_bytes: int = 25 * 1024 * 1024) -> bytes:
        if requests is None:
            raise ErrorFuente("Falta 'requests' (pip install requests)")
        if not self.robots.permite(url):
            pol = self.robots.politica(url)
            raise ErrorFuente(
                f"No se pidió {url}\n      motivo: {pol.nota or 'robots.txt no lo permite'}"
            )
        self.robots.esperar_turno(url)
        try:
            resp = requests.get(
                url,
                headers={"User-Agent": USER_AGENT, "Accept-Language": "es-PE,es;q=0.9"},
                timeout=25,
            )
            resp.raise_for_status()
            largo = int(resp.headers.get("Content-Length") or 0)
            if largo > max_bytes or len(resp.content) > max_bytes:
                raise ErrorFuente(f"Archivo demasiado grande, se omite: {url}")
            return resp.content
        except ErrorFuente:
            raise
        except Exception as e:                         # noqa: BLE001
            raise ErrorFuente(f"{self.nombre}: falló {url} ({e})") from e

    def _bajar_html(self, url: str) -> str:
        if not self.necesita_render:
            return self._bajar_bytes(url).decode("utf-8", errors="replace")

        if not self.robots.permite(url):
            raise ErrorFuente(f"robots.txt no permite {url}")
        self.robots.esperar_turno(url)
        if self._navegador is None:
            raise ErrorFuente(f"{self.nombre}: navegador no iniciado")
        return self._navegador.html(url)

    # ---------------- descubrimiento ----------------

    def _urls_de_sitemap(self, limite: int) -> list[str]:
        pendientes = list(self.sitemaps)
        if not pendientes:
            pol = self.robots.politica(self.base + "/")
            pendientes = list(pol.sitemaps)

        encontradas: list[tuple[str, object]] = []
        vistos: set[str] = set()

        while pendientes and len(encontradas) < limite * 3:
            actual = pendientes.pop(0)
            if actual in vistos:
                continue
            vistos.add(actual)
            try:
                datos = parsear(self._bajar_bytes(actual))
            except ErrorFuente as e:
                self._anotar(e)
                continue
            if not datos["urls"] and not datos["sitemaps"]:
                self._anotar(f"El sitemap {actual} se leyó pero no trae URLs")
            encontradas += datos["urls"]
            pendientes += [s for s in datos["sitemaps"] if s not in vistos][:8]

        if not encontradas:
            if not pendientes and not vistos:
                self._anotar("No hay sitemap configurado ni declarado en robots.txt")
            return []

        if self.ordenar_por_id:
            # El correlativo ordena mejor que el lastmod: filtrar por fecha aquí
            # solo descartaría avisos buenos por una fecha que no es la suya.
            urls = [u for u, _ in encontradas]
        else:
            urls = filtrar_recientes(encontradas, self.dias_ventana)  # type: ignore[arg-type]
            if not urls:
                self._anotar(f"El sitemap trae {len(encontradas)} URLs, pero ninguna "
                             f"tocada en los últimos {self.dias_ventana} días")
                return []

        if self.patron_aviso:
            patron = re.compile(self.patron_aviso)
            filtradas = [u for u in urls if patron.search(u)]
            if not filtradas:
                self._anotar(f"Ninguna de las {len(urls)} URLs del sitemap coincide con "
                             f"el patrón '{self.patron_aviso}'. Ejemplo: {urls[0]}")
            urls = filtradas

        if self.ordenar_por_id:
            def correlativo(u: str) -> int:
                numeros = re.findall(r"(\d{4,})", u)
                return max((int(n) for n in numeros), default=0)
            urls = sorted(urls, key=correlativo, reverse=True)

        return urls[:limite]

    def _urls_de_listados(self, limite: int) -> list[str]:
        if not self.patron_aviso:
            return []
        patron = re.compile(self.patron_aviso)
        encontradas: list[str] = []
        for origen in self.listados:
            try:
                html = self._bajar_html(origen)
            except ErrorFuente as e:
                self._anotar(e)
                continue
            # Se deshacen los escapes del JSON incrustado antes de buscar: en un
            # sitio moderno los enlaces viven dentro de un bloque JSON como
            # "\/convocatorias\/abogado", y así el patrón nunca los encontraría.
            html = html.replace("\\/", "/")

            if not patron.search(html):
                self._anotar(f"En {origen} no hay enlaces que coincidan con "
                             f"'{self.patron_aviso}' (¿la página carga por JavaScript?)")
            for cruda in patron.findall(html):
                url = _limpiar_enlace(cruda, self.base)
                if url and url not in encontradas:
                    encontradas.append(url)
                if len(encontradas) >= limite:
                    return encontradas
        return encontradas

    def urls_de_avisos(self, limite: int = 100) -> list[str]:
        """
        Primero la página de resultados, después el sitemap.

        El orden importa: el listado del portal muestra lo que está ABIERTO y
        ordenado por fecha, mientras que el sitemap es su archivo histórico
        completo. Empezar por el sitemap traía convocatorias de hace un mes,
        todas cerradas.
        """
        urls: list[str] = []
        if self.listados:
            urls = self._urls_de_listados(limite)

        # El sitemap solo se consulta si hay uno: pedirlo cuando la fuente
        # trabaja con listados solo generaba una queja falsa en el registro.
        if len(urls) < limite and (self.sitemaps or not self.listados):
            for u in self._urls_de_sitemap(limite - len(urls)):
                if u not in urls:
                    urls.append(u)

        return urls[:limite]

    # ---------------- interfaz Fuente ----------------

    def recolectar(self, limite: int = 100) -> Iterator[OfertaCruda]:
        if not self.activa:
            return

        self._reiniciar_problemas()

        # El navegador se abre ANTES de descubrir, no después: cuando las URLs
        # se sacan de una página de resultados (y no de un sitemap), esa página
        # también hay que renderizarla.
        if self.necesita_render:
            self._avisar("abriendo el navegador (tarda unos segundos)…")
            self._navegador = Navegador(self.espera_selector).__enter__()
        try:
            # Se exploran más URLs de las que se necesitan, porque buena parte
            # estará vencida. Con navegador cada página cuesta segundos, así
            # que ahí se explora menos.
            # Reparar: en vez de salir a descubrir, se releen las direcciones
            # que ya están publicadas. Va ANTES de `urls_de_avisos` a propósito,
            # para saltarse también los filtros de descubrimiento de cada
            # fuente — al reparar no queremos criterios, queremos estas y ya.
            if self.urls_fijas:
                self._avisar(f"reparando: {len(self.urls_fijas)} avisos ya "
                             f"publicados, sin buscar direcciones nuevas")
                urls = self.urls_fijas[:limite]
            else:
                self._avisar("buscando direcciones de avisos…")
                urls = self.urls_de_avisos(limite * (2 if self.necesita_render else 4))
            if not urls:
                return
            # El aviso de tiempo va con un rango y no con un número redondo:
            # decía "~3 s cada una" cuando en la práctica iban 30, y sobre esa
            # cifra se calcularon los límites de la corrida automática.
            self._avisar(f"{len(urls)} direcciones por revisar"
                         + (" (con navegador, entre 2 y 8 s cada una)"
                            if self.necesita_render else ""))
            ilegibles = antiguos = cerrados = entregados = seguidos = 0
            repetidos = 0
            for revisadas, url in enumerate(urls, start=1):
                if entregados >= limite:
                    break

                # Señal de vida cada 20 direcciones: puede haber tramos largos
                # donde todo se descarta y no se imprime ni una oferta.
                if revisadas % 20 == 0:
                    self._avisar(f"… {revisadas}/{len(urls)} revisadas · "
                                 f"{entregados} avisos · {repetidos} ya vistas · "
                                 f"{cerrados + antiguos} vencidas")

                # Ya revisada hace poco: se salta sin descargarla. Esto es lo
                # que permite retomar una corrida que se cortó a medias.
                if self.ya_visto and self.ya_visto(url):
                    repetidos += 1
                    continue

                try:
                    html = self._bajar_html(url)
                except ErrorFuente as e:
                    self._anotar(e)
                    continue
                cruda = self.parser(html, url, self.nombre)

                # Descartar lo viejo ANTES de enriquecer: abrir el PDF de un
                # aviso de hace tres meses es tiempo tirado a la basura.
                if cruda:
                    vieja = _demasiado_antigua(cruda, self.dias_publicado)
                    cerrada = _plazo_cerrado(cruda)
                    if vieja or cerrada:
                        if vieja:
                            antiguos += 1
                            seguidos += 1
                            # Solo la ANTIGÜEDAD indica que pasamos la ventana.
                            # Que un aviso reciente ya haya cerrado no dice nada
                            # sobre los siguientes: van entremezclados.
                            if self.ordenar_por_id and seguidos >= 40:
                                self._anotar(
                                    f"Se cortó la búsqueda: {seguidos} avisos seguidos "
                                    f"con más de {self.dias_publicado} días publicados"
                                )
                                break
                        else:
                            cerrados += 1
                            seguidos = 0
                        continue
                    seguidos = 0

                if cruda and cruda.puesto:
                    entregados += 1
                    if self.enriquecer:
                        try:
                            aviso = self.enriquecer(cruda, html, self._bajar_bytes)
                            if aviso:
                                self._anotar(aviso)
                        except ErrorFuente as e:
                            self._anotar(e)
                        except Exception as e:          # noqa: BLE001
                            self._anotar(f"Falló el enriquecido: {e}")
                    yield cruda
                else:
                    ilegibles += 1
                    if ilegibles == 1:
                        pista = ("la página llega vacía: es una SPA y necesita Playwright"
                                 if "enable JavaScript" in html or len(html) < 2000
                                 else "el HTML llegó completo pero el parser no encontró el aviso")
                        self._anotar(f"No se pudo leer el aviso ({pista}). Ejemplo: {url}")
            if repetidos:
                self._anotar(f"{repetidos} avisos ya revisados hoy, se saltaron")
            if cerrados:
                self._anotar(f"{cerrados} avisos saltados porque su plazo ya cerró")
            if antiguos:
                self._anotar(f"{antiguos} avisos saltados por tener más de "
                             f"{self.dias_publicado} días publicados")
            if ilegibles:
                self._anotar(f"{ilegibles} de {len(urls)} avisos no se pudieron leer")
        finally:
            if self._navegador is not None:
                self._navegador.__exit__()
                self._navegador = None

    # ---------------- revisión previa ----------------

    def diagnosticar(self) -> Diagnostico:
        """
        Revisa la fuente sin recolectar: qué dice robots.txt, si el sitemap
        responde y si un aviso de muestra trae JSON-LD. Correr esto antes de
        dejar el portal activo en producción.
        """
        d = Diagnostico(self.nombre)
        if self.nota:
            d.detalle.append(self.nota)

        if requests is None:
            d.robots = "sin red"
            d.detalle.append("Falta 'requests' (pip install requests)")
            return d

        pol = self.robots.politica(self.base + "/")
        d.robots = "permite" if pol.legible else "bloquea"
        d.detalle.append(pol.nota)
        if pol.sitemaps and not self.sitemaps:
            d.detalle.append(f"Sitemaps declarados: {len(pol.sitemaps)}")
        if not pol.legible:
            return d

        if self.necesita_render and not HAY_PLAYWRIGHT:
            d.detalle.append("Este portal carga por JavaScript y falta Playwright: "
                             "pip install playwright && playwright install chromium")
            return d

        # Igual que en la recolección: el navegador primero, porque la página de
        # resultados también puede necesitarlo.
        if self.necesita_render:
            self._navegador = Navegador(self.espera_selector).__enter__()
        try:
            try:
                urls = self.urls_de_avisos(limite=5)
            except ErrorFuente as e:
                d.detalle.append(str(e))
                return d
            d.urls_descubiertas = len(urls)
            if not urls:
                d.detalle.append("No se descubrieron avisos: revisar sitemap o patrón")
                return d

            html = self._bajar_html(urls[0])
            cruda = self.parser(html, urls[0], self.nombre)
            d.muestra_con_jsonld = cruda is not None
            if cruda:
                d.detalle.append(f"Muestra: {cruda.puesto} — {cruda.empresa} "
                                 f"[{cruda.sueldo_texto or 'sin campo de sueldo'}]")
            elif "enable JavaScript" in html or len(html) < 2000:
                d.detalle.append("La página llega vacía: es una SPA, marcar necesita_render=True")
            else:
                d.detalle.append("HTML completo pero sin JSON-LD: hay que escribir un parser propio")
        except ErrorFuente as e:
            d.detalle.append(str(e))
        finally:
            if self._navegador is not None:
                self._navegador.__exit__()
                self._navegador = None

        return d


# --------------------------------------------------------------------------
# Portales configurados
#
# Estado verificado el 2 de agosto de 2026 (revisar cada cierto tiempo:
# los portales cambian de arquitectura sin avisar).
# --------------------------------------------------------------------------

def portales_peru() -> list[PortalWeb]:
    return [
        PortalWeb(
            "Bumeran", "https://www.bumeran.com.pe",
            sitemaps=("https://www.bumeran.com.pe/sitemap_avisos_bum.xml",),
            patron_aviso=r"/empleos/.+\.html$",
            necesita_render=True,
            espera_selector="script[type='application/ld+json'], h1",
            nota=("robots.txt permite /empleos/* y declara sitemap de avisos con lastmod. "
                  "El aviso es React: sin navegador el HTML llega vacío."),
        ),
        PortalWeb(
            "Laborum", "https://www.laborum.pe",
            sitemaps=("https://laborum.pe/api/v1/sitemaps/index",),
            # Sus avisos viven en /job/<empresa>/<puesto>/<id>, no en /empleos/.
            patron_aviso=r"/job/[^/]+/[^/]+/[0-9a-f]+",
            necesita_render=True,
            espera_selector="script[type='application/ld+json'], h1",
            nota=("robots.txt solo bloquea rutas de cuenta. Sitemap en "
                  "/api/v1/sitemaps/index, con 50 mil avisos."),
        ),
        PortalWeb(
            "Computrabajo", "https://pe.computrabajo.com",
            sitemaps=(),
            patron_aviso=r"/ofertas-de-trabajo/oferta-de-trabajo-de-",
            necesita_render=True,
            nota=("Su robots.txt responde vacío detrás de un WAF, así que el motor lo "
                  "trata como NO permitido y lo salta. Antes de activarlo hay que "
                  "conseguir permiso o un acuerdo de sindicación."),
        ),
    ]


def fuentes_por_verificar() -> list[PortalWeb]:
    """
    Candidatas que TODAVÍA NO están confirmadas. No entran en la corrida normal
    a propósito: una fuente sin verificar solo aporta ruido y ceros.

    Confírmalas una por una con `python3 -m motor diagnostico --todas` y, cuando
    alguna funcione, muévela a `fuentes_de_arranque()`.
    """
    return [
        # Las bolsas universitarias peruanas corren sobre la plataforma Reqlut y
        # su listado exige login: son ofertas exclusivas para estudiantes de esa
        # casa de estudios. No se recolectan a propósito (ver EMPRESAS.md).
        PortalWeb(
            "Empleos del MTPE", "https://www.empleosperu.gob.pe",
            patron_aviso=r"/(empleos|ofertas|vacantes)/[^\"'\s]+",
            nota="SIN VERIFICAR. Bolsa de trabajo del Ministerio de Trabajo.",
        ),
        PortalWeb(
            "Convocatorias gob.pe", "https://www.gob.pe",
            listados=("https://www.gob.pe/institucion/servir/convocatorias",),
            patron_aviso=r"/institucion/[^\"'\s]+/convocatorias/[^\"'\s]+",
            nota=("SIN VERIFICAR. gob.pe respondió vacío en la primera revisión: "
                  "puede requerir navegador o bloquear bots."),
        ),

        # --------------------------------------------------------------
        # Privados, revisión de mercado del 4 de agosto de 2026.
        #
        # Van en este orden a propósito: primero los que son dueños de su
        # propia oferta, después los agregadores. Un agregador repite
        # avisos que ya tenemos y encima manda al usuario a un tercer
        # sitio, lo que choca con la regla 5 (enlazar al aviso original).
        # --------------------------------------------------------------
        PortalWeb(
            "BuscoTrabajo", "https://buscotrabajo.pe",
            sitemaps=("https://buscotrabajo.pe/sitemap.xml",),
            patron_aviso=r"/(trabajo|empleo|oferta)[^\"'\s]*",
            necesita_render=True,
            espera_selector="script[type='application/ld+json'], h1",
            nota=("VERIFICADA 4/8/2026: robots permite, descubre avisos, HTML "
                  "completo. La única fuente privada peruana fuera de Jobint. "
                  "PERO no trae JSON-LD: hay que escribirle un lector propio "
                  "que saque sueldo y funciones del texto. Ese es el trabajo "
                  "pendiente, no la conexión."),
        ),
        PortalWeb(
            "Jora Perú", "https://pe.jora.com",
            sitemaps=("https://pe.jora.com/sitemap.xml",),
            patron_aviso=r"/job/[^\"'\s]+",
            necesita_render=True,
            nota=("DESCARTADA 4/8/2026: su robots.txt devuelve 502, así que el "
                  "motor la trata como no permitida (regla 6). Además es "
                  "agregador: repetiría avisos que ya leemos."),
        ),
        # --------------------------------------------------------------
        # Sector público, revisión del 5 de agosto de 2026.
        #
        # Hacen falta porque convocape.com resultó ser sobre todo un archivo:
        # de sus 512 direcciones, 413 son convocatorias con el plazo ya
        # cerrado. No está roto —lee bien— pero casi no tiene nada abierto, y
        # es la única fuente pública que tenemos.
        #
        # Ojo al verificarlas: son sitios con mucha publicidad, y hay que
        # confirmar que enlacen al aviso oficial de la entidad y no se queden
        # con el tráfico. Si no enlazan al original, no entran (regla 5).
        # --------------------------------------------------------------
        PortalWeb(
            "Convocatorias de Trabajo", "https://www.convocatoriasdetrabajo.com",
            listados=("https://www.convocatoriasdetrabajo.com/",),
            patron_aviso=r"/(convocatoria|empleo)[^\"'\s]+",
            nota="SIN VERIFICAR. Agregador de convocatorias públicas peruanas.",
        ),
        PortalWeb(
            "Convocatorias CAS", "https://www.convocatoriascas.com",
            listados=("https://www.convocatoriascas.com/",),
            # El patrón anterior (`.*convocatoria.*`) era tan flojo que llegó a
            # matchear el script de publicidad `convocatoriascas_20765.js`.
            # Este es el de verdad, mirado en la página el 5/8/2026.
            patron_aviso=r"/proceso-de-seleccion-CAS-[^\"'\s]+\.html",
            ordenar_por_id=True,     # el id final es correlativo: 67481, 67480…
            nota=(
                "VERIFICADA 5/8/2026 y es la mejor candidata pública, pero "
                "NECESITA LECTOR PROPIO y uno distinto a los demás.\n"
                "Lo bueno: sueldo exacto por puesto, plazo de postulación, "
                "requisitos, y enlace a las bases en el dominio de la propia "
                "entidad (munisurquillo.gob.pe), que es justo lo que pide la "
                "regla 5. Y trae provincias a montones: Quellouno, Moquegua, "
                "Melgar, Pacucha, Arequipa.\n"
                "Lo difícil: UNA PÁGINA TRAE VARIOS PUESTOS. La de Surquillo "
                "lista 6 plazas en dos puestos con sueldos distintos "
                "(S/ 1,350 y S/ 2,800). El motor asume un aviso por dirección, "
                "así que el lector tiene que partir una página en varias "
                "ofertas. Las páginas por puesto existen "
                "(`/concurso-publico-...-274991.html`) pero solo se enlazan "
                "desde dentro, y el descubrimiento no baja dos niveles."
            ),
        ),
        PortalWeb(
            "Perutrabajos", "https://www.perutrabajos.com",
            listados=("https://www.perutrabajos.com/",),
            patron_aviso=r"/(convocatoria|institucion)[^\"'\s]+",
            nota=("SIN VERIFICAR. Mezcla convocatorias del Estado con prácticas. "
                  "Publica por institución, lo que ayudaría con ciudades fuera de Lima."),
        ),

        PortalWeb(
            "Aptitus", "https://aptitus.com",
            patron_aviso=r"/(empleos|trabajo)/[^\"'\s]+",
            necesita_render=True,
            nota=("DESCARTADA 4/8/2026: no descubre ningún aviso, y de todos "
                  "modos sería redundante — Bumeran la compró y la absorbió "
                  "bajo su marca. Sus avisos ya los tenemos."),
        ),
    ]
