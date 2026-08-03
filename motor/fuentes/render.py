"""
Renderizado de portales hechos en JavaScript.

Bumeran, Laborum y varios más son aplicaciones React: el HTML que llega por
HTTP viene vacío ("You need to enable JavaScript to run this app") y el aviso
recién aparece cuando el navegador ejecuta el JS. Para esos casos hace falta
un navegador de verdad.

Playwright es opcional: si no está instalado, las fuentes que lo necesitan se
marcan inactivas y el pipeline sigue con las demás.

    pip install playwright
    playwright install chromium
"""
from __future__ import annotations

from .base import USER_AGENT

try:
    from playwright.sync_api import sync_playwright
    HAY_PLAYWRIGHT = True
except ImportError:                                   # pragma: no cover
    sync_playwright = None
    HAY_PLAYWRIGHT = False


class Navegador:
    """
    Navegador reutilizable. Abrir Chromium cuesta ~1s, así que se abre una vez
    por corrida y se reutiliza para todos los avisos.

    Uso:
        with Navegador() as nav:
            html = nav.html("https://...")
    """

    def __init__(self, espera_selector: str = "", timeout_ms: int = 25_000):
        self.espera_selector = espera_selector
        self.timeout_ms = timeout_ms
        self._pw = None
        self._navegador = None
        self._contexto = None

    def __enter__(self) -> "Navegador":
        if not HAY_PLAYWRIGHT:
            raise RuntimeError(
                "Falta Playwright. Instálalo con:\n"
                "  pip install playwright && playwright install chromium"
            )
        self._pw = sync_playwright().start()
        self._navegador = self._pw.chromium.launch(headless=True)
        self._contexto = self._navegador.new_context(
            user_agent=USER_AGENT,
            locale="es-PE",
            viewport={"width": 1280, "height": 900},
        )
        # Solo queremos el texto: se bloquea todo lo que no aporte contenido.
        # Esto es la diferencia entre 6 segundos y 2 por aviso, y en una
        # corrida de 60 avisos son cuatro minutos menos.
        _BASURA = ("image", "font", "media", "stylesheet")
        _RASTREADORES = ("google-analytics", "googletagmanager", "doubleclick",
                         "facebook.net", "hotjar", "clarity.ms", "segment.io",
                         "criteo", "taboola", "newrelic", "optimizely")

        def filtrar(ruta):
            pedido = ruta.request
            if pedido.resource_type in _BASURA:
                return ruta.abort()
            if any(r in pedido.url for r in _RASTREADORES):
                return ruta.abort()
            return ruta.continue_()

        self._contexto.route("**/*", filtrar)
        return self

    def __exit__(self, *_) -> None:
        for recurso in (self._contexto, self._navegador):
            try:
                recurso and recurso.close()
            except Exception:                          # noqa: BLE001
                pass
        try:
            self._pw and self._pw.stop()
        except Exception:                              # noqa: BLE001
            pass

    def html(self, url: str) -> str:
        pagina = self._contexto.new_page()
        try:
            pagina.goto(url, timeout=self.timeout_ms, wait_until="domcontentloaded")
            if self.espera_selector:
                try:
                    pagina.wait_for_selector(self.espera_selector, timeout=self.timeout_ms)
                except Exception:                      # noqa: BLE001
                    pass                               # seguimos con lo que haya
            else:
                pagina.wait_for_timeout(1200)
            return pagina.content()
        finally:
            pagina.close()
