"""
Pruebas del navegador que lee los portales hechos en JavaScript.

Por qué existen: el 5 de agosto de 2026 la corrida de Bumeran alcanzó a revisar
100 de 240 avisos en 50 minutos —unos 30 segundos por aviso— mientras el propio
programa anunciaba "~3 s cada una".

La causa estaba en una línea: se esperaba a que apareciera
`script[type='application/ld+json'], h1` con el modo por defecto de Playwright,
que es "visible". Una etiqueta `<script>` no es visible nunca, así que esa mitad
del selector no podía cumplirse jamás; la espera solo terminaba si aparecía un
`h1` visible, y en las páginas sin uno se agotaban los 25 segundos completos.

No hace falta un navegador de verdad para vigilarlo: se le pasa una página de
mentira que apunta lo que le pidieron.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from motor.fuentes.render import Navegador                    # noqa: E402


class PaginaFalsa:
    """Anota cómo la llamaron, sin abrir nada."""

    def __init__(self):
        self.esperas = []
        self.cerrada = False

    def goto(self, url, timeout=None, wait_until=None):
        self.url = url

    def wait_for_selector(self, selector, **kw):
        self.esperas.append((selector, kw))

    def wait_for_timeout(self, ms):
        self.esperas.append(("(sin selector)", {"ms": ms}))

    def content(self):
        return "<html>ok</html>"

    def close(self):
        self.cerrada = True


class ContextoFalso:
    def __init__(self, pagina):
        self._pagina = pagina

    def new_page(self):
        return self._pagina


class PruebaEsperaDelNavegador(unittest.TestCase):

    def _navegar(self, **kw):
        pagina = PaginaFalsa()
        nav = Navegador(espera_selector="script[type='application/ld+json'], h1", **kw)
        nav._contexto = ContextoFalso(pagina)
        html = nav.html("https://ejemplo.pe/aviso")
        return pagina, html

    def test_espera_a_que_el_nodo_exista_no_a_que_se_vea(self):
        """
        El corazón del asunto. Con el modo "visible" se esperaban 25 segundos
        en cada aviso que no tuviera un h1, y eso multiplicado por cientos de
        avisos es lo que hacía que la corrida no terminara nunca.
        """
        pagina, _ = self._navegar()
        self.assertEqual(len(pagina.esperas), 1)
        _, opciones = pagina.esperas[0]
        self.assertEqual(opciones.get("state"), "attached",
                         "volvió a esperar a que el <script> fuera visible, y nunca lo es")

    def test_la_espera_del_contenido_es_mucho_mas_corta_que_la_del_servidor(self):
        """
        Son dos relojes distintos y conviene que sigan siéndolo: uno es "cuánto
        aguanto a que el servidor responda", el otro "cuánto aguanto a que
        aparezca el aviso". Si el segundo se iguala al primero, una página sin
        aviso vuelve a costar lo mismo que una caída.
        """
        pagina, _ = self._navegar()
        _, opciones = pagina.esperas[0]
        nav = Navegador()
        self.assertLessEqual(opciones["timeout"], 10_000)
        self.assertLess(nav.espera_ms, nav.timeout_ms)

    def test_la_pagina_siempre_se_cierra(self):
        """Una pestaña que no se cierra deja memoria tomada toda la corrida."""
        pagina, html = self._navegar()
        self.assertTrue(pagina.cerrada)
        self.assertIn("ok", html)


if __name__ == "__main__":
    unittest.main()
