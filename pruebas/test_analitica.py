"""
Pruebas de la medición de visitas.

Por qué existen: la política de contenido del sitio es una lista blanca. Todo
lo que no esté declarado ahí, el navegador lo bloquea **sin decir nada** — ni
un error en pantalla, ni un aviso. El sitio se ve perfecto y los datos
simplemente no llegan.

Es la peor forma de fallar que hay: uno se entera semanas después, mirando un
panel vacío y creyendo que nadie entró a la web.

Se vigilan tres cosas: que el fragmento esté puesto, que las dos direcciones
que necesita estén autorizadas, y que la portada y las páginas de oferta usen
el mismo token (viven en archivos distintos y es fácil cambiar uno solo).
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from motor.sitio import (                                          # noqa: E402
    ANALITICA_ENVIO, ANALITICA_ORIGEN, ANALITICA_TOKEN,
    bloque_analitica, csp,
)
from test_seguridad import permitido, politica                     # noqa: E402


class PruebaAnalitica(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.portada = (RAIZ / "index.html").read_text(encoding="utf-8")

    def test_la_portada_cuenta_visitas(self):
        self.assertIn("ANALITICA:INICIO", self.portada)
        self.assertIn("beacon.min.js", self.portada)

    def test_la_portada_y_las_ofertas_usan_el_mismo_token(self):
        """
        El token está escrito en dos sitios: a mano en la portada y en el motor
        para las páginas de oferta. Si se cambia uno y no el otro, media web
        deja de contar y el panel muestra menos visitas de las reales.
        """
        m = re.search(r'"token":\s*"([0-9a-f]+)"', self.portada)
        self.assertIsNotNone(m, "la portada perdió el token")
        self.assertEqual(m.group(1), ANALITICA_TOKEN)

    def test_la_lista_blanca_deja_bajar_el_contador(self):
        """Si falta esto, el archivo no se descarga y no se cuenta nada."""
        for nombre, reglas in self._politicas():
            with self.subTest(pagina=nombre):
                self.assertTrue(
                    permitido(reglas, "script-src", ANALITICA_ORIGEN),
                    f"{nombre} bloquea la descarga del contador")

    def test_la_lista_blanca_deja_mandar_la_visita(self):
        """
        Bajar el archivo no basta: después tiene que poder enviar el dato. Es
        la mitad que se olvida, porque la página se ve igual de bien sin ella.
        """
        for nombre, reglas in self._politicas():
            with self.subTest(pagina=nombre):
                self.assertTrue(
                    permitido(reglas, "connect-src", ANALITICA_ENVIO),
                    f"{nombre} deja bajar el contador pero no enviar la visita")

    def test_sin_token_no_se_escribe_nada(self):
        """
        Si algún día se quita el token, la etiqueta no debe quedar a medias
        apuntando a ninguna parte.
        """
        import motor.sitio as sitio
        original = sitio.ANALITICA_TOKEN
        try:
            sitio.ANALITICA_TOKEN = ""
            self.assertEqual(bloque_analitica(), "")
        finally:
            sitio.ANALITICA_TOKEN = original

    def test_la_pagina_de_oferta_sigue_sin_permitir_formularios(self):
        """
        Al tocar la lista blanca es fácil aflojarla de más. Las páginas de
        oferta no tienen formularios ni JavaScript propio: tienen que seguir
        siendo más cerradas que la portada.
        """
        reglas = politica(f'<meta http-equiv="Content-Security-Policy" content="{csp()}">')
        self.assertEqual(reglas.get("form-action"), ["'none'"])
        self.assertNotIn("'unsafe-inline'", reglas.get("script-src", []))

    def _politicas(self):
        interna = f'<meta http-equiv="Content-Security-Policy" content="{csp()}">'
        return [
            ("la portada", politica(self.portada)),
            ("la página de cada oferta", politica(interna)),
        ]


if __name__ == "__main__":
    unittest.main()
