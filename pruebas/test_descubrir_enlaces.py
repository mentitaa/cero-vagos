"""
Descubrir los enlaces de una página de resultados.

Este archivo existe por un error de una línea que se comía fuentes enteras sin
dar la cara.

El descubrimiento por listado usa una expresión con alternativas, porque cada
portal le puso otro nombre a la página de un aviso:

    /(trabajo|empleo|oferta)[^"'\\s]*

Se buscaba con `findall`, y `findall` **devuelve solo lo que está entre
paréntesis**. O sea "trabajo", no "/trabajo/3075258/auxiliar-de-almacen". Todos
los enlaces de la página quedaban reducidos a la misma palabra, se
deduplicaban entre sí, y una página con 165 avisos aportaba UN enlace, que
además no llevaba a ninguna parte.

Lo peor es cómo fallaba: no daba error y tampoco daba cero. Daba uno. Un cero
invita a mirar; un uno parece que algo funcionó.

Se descubrió el 13/8/2026 sondeando Trabajos Diarios, pero el error no era de
esa fuente: afectaba a **todas** las que se leen por listado con un patrón con
paréntesis, que son casi todas.
"""
from __future__ import annotations

import unittest

from motor.fuentes.portal_web import PortalWeb

# Una página de resultados como las de verdad: varios avisos, y alrededor los
# enlaces de menú que NO son avisos.
PAGINA = """
<html><body>
  <a href="/candidatos">Candidatos</a>
  <a href="/trabajo/3075258/auxiliar-de-almacen-y-despacho-en-lima">Auxiliar</a>
  <a href="/trabajo/3074866/asistente-de-creditos-y-cobranzas-en-lima">Asistente</a>
  <a href="/trabajo/3066649/ejecutivo-de-operaciones-en-loreto">Ejecutivo</a>
  <a href="/contactanos">Contáctanos</a>
</body></html>
"""


class PortalDePrueba(PortalWeb):
    """Un portal que no sale a la red: devuelve la página de arriba."""

    def _bajar_html(self, url: str) -> str:
        return PAGINA


def _portal(patron: str) -> PortalDePrueba:
    return PortalDePrueba("Prueba", "https://ejemplo.pe",
                          listados=("https://ejemplo.pe/ofertas-trabajo",),
                          patron_aviso=patron)


class PruebaConParentesis(unittest.TestCase):
    """
    El caso que falló. El patrón tiene alternativas entre paréntesis, que es
    la forma natural de escribirlo y la que usan casi todas las fuentes.
    """

    def setUp(self):
        self.urls = _portal(r"/(trabajo|empleo|oferta)/[^\"'\s]+").urls_de_avisos(50)

    def test_encuentra_TODOS_los_avisos(self):
        self.assertEqual(len(self.urls), 3,
                         f"se perdieron enlaces por el camino: {self.urls}")

    def test_devuelve_la_direccion_entera_no_la_palabra(self):
        """
        El síntoma exacto del error: en vez de la dirección salía "trabajo",
        que convertido en enlace daba https://ejemplo.pe/trabajo — una página
        que no existe.
        """
        for url in self.urls:
            with self.subTest(url=url):
                self.assertIn("/trabajo/", url)
                self.assertTrue(url.rstrip("/").split("/")[-1],
                                "la dirección quedó sin la parte final")
        self.assertNotIn("https://ejemplo.pe/trabajo", self.urls)

    def test_son_las_direcciones_de_verdad(self):
        self.assertIn("https://ejemplo.pe/trabajo/3075258/"
                      "auxiliar-de-almacen-y-despacho-en-lima", self.urls)

    def test_no_recoge_el_menu(self):
        for url in self.urls:
            self.assertNotIn("/contactanos", url)
            self.assertNotIn("/candidatos", url)


class PruebaSinParentesis(unittest.TestCase):
    """Los patrones sin alternativas ya funcionaban, y tienen que seguir igual."""

    def test_sigue_funcionando(self):
        urls = _portal(r"/trabajo/[^\"'\s]+").urls_de_avisos(50)
        self.assertEqual(len(urls), 3)
        self.assertIn("https://ejemplo.pe/trabajo/3074866/"
                      "asistente-de-creditos-y-cobranzas-en-lima", urls)


class PruebaElLimiteSigueMandando(unittest.TestCase):
    def test_no_trae_mas_de_lo_pedido(self):
        self.assertEqual(len(_portal(r"/(trabajo|empleo)/[^\"'\s]+")
                             .urls_de_avisos(2)), 2)


if __name__ == "__main__":
    unittest.main()
