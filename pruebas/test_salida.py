"""
Pruebas de las páginas de salida: las que cuentan los clics hacia cada aviso.

Para qué son: el botón de postular ya no va derecho al portal, pasa medio
segundo por una página nuestra. Como esa página cuenta como visita, el medidor
dice cuántas personas hicieron clic en CADA aviso — el único número que le
interesa a una empresa cuando se le ofrezca publicar en Cero Vagos.

Lo que vigilan estas pruebas es que ese rodeo no rompa nada de lo que ya estaba
prometido: que se siga enlazando al aviso original, que Google no indexe las
páginas de paso, y que desaparezcan junto con la oferta que las creó.
"""
from __future__ import annotations

import re
import shutil
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from motor.almacen import Almacen                                  # noqa: E402
from motor.modelos import Oferta                                   # noqa: E402
from motor.sitio import CARPETA_SALIDA, generar                    # noqa: E402

SITIO = "https://ejemplo.pe"


class PruebaPaginasDeSalida(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.almacen = Almacen(self.tmp / "prueba.db")
        (self.tmp / "index.html").write_text(
            "<html><body><!-- OFERTAS-ESTATICAS:INICIO -->\n"
            "<!-- OFERTAS-ESTATICAS:FIN --></body></html>", encoding="utf-8")

    def tearDown(self):
        self.almacen.cerrar()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _guardar(self, huella="a" * 16, puesto="Asistente Contable", dias_vence=8):
        self.almacen.guardar(Oferta(
            huella=huella, fuente="Bumeran", url=f"https://origen.pe/{huella}",
            puesto=puesto, empresa="Acme", ciudad="Lima", categoria="Otros",
            sueldo_min=2000, sueldo_max=2500, resumen="Un puesto de ejemplo.",
            funciones=["Hacer una cosa concreta del área"],
            requisitos=["Un año de experiencia comprobada"],
            beneficios=["Planilla completa desde el primer día"],
            publicado=date.today() - timedelta(days=1),
            vence=date.today() + timedelta(days=dias_vence),
            score=88, aprobada=True))

    def _generar(self):
        generar(self.almacen, SITIO, self.tmp)
        salidas = list((self.tmp / CARPETA_SALIDA).glob("*/index.html"))
        return salidas

    def test_cada_oferta_tiene_su_pagina_de_salida(self):
        """Una por oferta, no una sola compartida: si no, no se sabe qué aviso
        recibió los clics, que es justo el dato que se quiere."""
        self._guardar("a" * 16, "Asistente Contable")
        self._guardar("b" * 16, "Analista de Datos")
        self.assertEqual(len(self._generar()), 2)

    def test_el_boton_de_postular_pasa_por_la_salida(self):
        self._guardar()
        self._generar()
        ficha = next((self.tmp / "oferta").glob("*/index.html")).read_text(encoding="utf-8")
        boton = re.search(r'class="btn" href="([^"]+)"', ficha)
        self.assertIsNotNone(boton)
        self.assertIn(f"/{CARPETA_SALIDA}/", boton.group(1))

    def test_se_sigue_enlazando_al_aviso_original(self):
        """
        La regla de siempre: no reemplazamos al portal, lo ordenamos. El rodeo
        no puede convertirse en esconder a dónde va la persona, así que la
        dirección va escrita y además en un enlace que se puede pulsar.
        """
        self._guardar()
        html = self._generar()[0].read_text(encoding="utf-8")
        self.assertIn("https://origen.pe/" + "a" * 16, html)
        self.assertRegex(html, r'href="https://origen\.pe/')

    def test_la_espera_existe_pero_es_corta(self):
        """
        Sin espera, el medidor no alcanza a mandar el dato y el clic que
        queríamos contar se pierde. Con espera larga, la persona se va.
        """
        self._guardar()
        html = self._generar()[0].read_text(encoding="utf-8")
        m = re.search(r'http-equiv="refresh" content="(\d+);', html)
        self.assertIsNotNone(m, "la página de salida dejó de redirigir sola")
        self.assertGreaterEqual(int(m.group(1)), 1, "sin espera no se cuenta el clic")
        self.assertLessEqual(int(m.group(1)), 3, "esperar tanto espanta a la gente")

    def test_la_salida_cuenta_la_visita(self):
        """Si no lleva el medidor, todo este rodeo no sirve para nada."""
        self._guardar()
        html = self._generar()[0].read_text(encoding="utf-8")
        self.assertIn("beacon.min.js", html)

    def test_redirige_sin_javascript_propio(self):
        """
        Con `meta refresh` y no con JavaScript escrito dentro del HTML: así no
        hay que aflojar la lista blanca de seguridad de las páginas internas,
        y funciona igual con el JavaScript desactivado.
        """
        self._guardar()
        html = self._generar()[0].read_text(encoding="utf-8")
        self.assertNotIn("<script>", html)
        self.assertNotIn("'unsafe-inline'", re.search(
            r'script-src[^;]*', html).group(0))

    def test_google_no_las_indexa(self):
        """
        Son un trámite, no contenido. Indexarlas mandaría gente desde Google a
        una pantalla de paso y le diría a Google que el sitio está lleno de
        páginas vacías.
        """
        self._guardar()
        html = self._generar()[0].read_text(encoding="utf-8")
        self.assertIn('name="robots" content="noindex', html)

        robots = (self.tmp / "robots.txt").read_text(encoding="utf-8")
        self.assertIn(f"Disallow: /{CARPETA_SALIDA}/", robots)

        mapa = (self.tmp / "sitemap.xml").read_text(encoding="utf-8")
        self.assertNotIn(f"/{CARPETA_SALIDA}/", mapa)

    def test_se_borran_con_la_oferta_que_las_creo(self):
        """
        Una página de salida huérfana seguiría llevando a un aviso cerrado y
        encima contando clics que no valen nada.
        """
        self._guardar("a" * 16, "Asistente Contable")
        self._guardar("b" * 16, "Analista de Datos")
        self.assertEqual(len(self._generar()), 2)

        self.almacen.con.execute(
            "UPDATE ofertas SET vigente = 0 WHERE huella = ?", ("b" * 16,))
        self.almacen.con.commit()

        quedan = self._generar()
        self.assertEqual(len(quedan), 1)
        self.assertIn("asistente-contable", str(quedan[0]))


if __name__ == "__main__":
    unittest.main()
