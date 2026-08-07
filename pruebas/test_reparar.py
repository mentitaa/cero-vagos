"""
Reparar: volver a leer lo que YA está publicado.

Existe por una tarde entera perdida el 7/8/2026. Se arregló la lectura del
sueldo y de la categoría, se subió el código, y tres avisos siguieron mostrando
el dato viejo **tres corridas seguidas**. No fallaba nada:

  · Un aviso guardado conserva lo que se le leyó el día que entró, y
    `reevaluar` no lo vuelve a leer — solo lo repuntúa con el número guardado.
  · Para releerlo hay que volver a DESCARGARLO.
  · Pero cada fuente descubre direcciones en su sitemap y **se detiene al
    llegar a su cupo**: Bumeran lee 120 avisos y para, aunque queden miles.
    Que un aviso guardado caiga dentro de ese corte es cuestión de suerte.

Se intentó con `rehacer`, y con `rehacer` más la ventana de días abierta. Las
tres veces el cupo se llenó antes de llegar a esos avisos. Desde afuera la
corrida se veía perfecta: agregaba ofertas nuevas mientras las viejas seguían
mal.

`--reparar` quita el azar: le pide las direcciones a la base en vez de salir a
descubrirlas. Se relee exactamente lo que está publicado, ni más ni menos.
"""
from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

from motor.almacen import Almacen
from motor.fuentes.portal_web import PortalWeb
from motor.modelos import Oferta, OfertaCruda


def oferta(huella: str, fuente: str, url: str, aprobada: bool = True,
           vigente: bool = True) -> Oferta:
    return Oferta(
        huella=huella, fuente=fuente, url=url, puesto="Analista",
        empresa="Acme", ciudad="Lima", sueldo_min=2000, sueldo_max=2000,
        funciones=["Analizar"], score=90, aprobada=aprobada,
        publicado=date.today(),
    )


class PruebaLasDireccionesSalenDeLaBase(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.al = Almacen(self.tmp.name)

    def tearDown(self):
        import os
        self.al.cerrar()
        os.unlink(self.tmp.name)

    def test_se_agrupan_por_fuente(self):
        self.al.guardar(oferta("a" * 16, "Bumeran", "https://bum.pe/1"))
        self.al.guardar(oferta("b" * 16, "Bumeran", "https://bum.pe/2"))
        self.al.guardar(oferta("c" * 16, "Laborum", "https://lab.pe/1"))

        publicadas = self.al.urls_publicadas()
        self.assertEqual({k: len(v) for k, v in publicadas.items()},
                         {"Bumeran": 2, "Laborum": 1})

    def test_solo_lo_que_esta_publicado(self):
        """
        Reparar es para lo que la gente está viendo. Un aviso rechazado no
        muestra ningún dato equivocado, así que no hay nada que corregir en él.
        """
        self.al.guardar(oferta("a" * 16, "Bumeran", "https://bum.pe/1"))
        self.al.guardar(oferta("b" * 16, "Bumeran", "https://bum.pe/2", aprobada=False))

        publicadas = self.al.urls_publicadas()
        self.assertEqual(publicadas["Bumeran"], ["https://bum.pe/1"])

    def test_una_base_vacia_no_devuelve_nada(self):
        self.assertEqual(self.al.urls_publicadas(), {})


class PruebaLaFuenteReleeSinBuscar(unittest.TestCase):
    """
    Lo que hace que reparar sea fiable: cuando hay direcciones fijas, la fuente
    **no sale a descubrir**. Si volviera a buscar, volveríamos al azar del cupo
    que causó el problema.
    """

    def fuente_de_mentira(self, urls: list[str]) -> PortalWeb:
        p = PortalWeb("Bumeran", "https://bum.pe", sitemaps=("https://bum.pe/s.xml",))
        p.urls_fijas = urls
        p._bajar_html = lambda url: f"<html>{url}</html>"
        p.parser = lambda html, url, fuente: OfertaCruda(
            fuente=fuente, url=url, puesto="Analista", empresa="Acme",
            sueldo_texto="S/ 2,000", descripcion_html="<p>x</p>")
        return p

    def test_relee_exactamente_las_direcciones_dadas(self):
        urls = [f"https://bum.pe/{i}" for i in range(5)]
        fuente = self.fuente_de_mentira(urls)
        leidas = [c.url for c in fuente.recolectar(limite=100)]
        self.assertEqual(leidas, urls)

    def test_no_se_sale_a_descubrir(self):
        fuente = self.fuente_de_mentira(["https://bum.pe/1"])

        def no_deberia(*_a, **_k):
            raise AssertionError("salió a buscar direcciones estando en reparación")

        fuente.urls_de_avisos = no_deberia
        self.assertEqual(len(list(fuente.recolectar(limite=100))), 1)

    def test_sin_direcciones_fijas_todo_sigue_como_siempre(self):
        """Reparar es una excepción, no el camino normal."""
        fuente = PortalWeb("Bumeran", "https://bum.pe")
        self.assertEqual(fuente.urls_fijas, [])

        llamadas = []
        fuente.urls_de_avisos = lambda limite=100: llamadas.append(limite) or []
        list(fuente.recolectar(limite=10))
        self.assertTrue(llamadas, "no salió a descubrir cuando debía")


class PruebaLaBanderaExisteYSeExplica(unittest.TestCase):

    def test_recolectar_acepta_reparar(self):
        import subprocess
        import sys

        r = subprocess.run([sys.executable, "-m", "motor", "recolectar", "--help"],
                           capture_output=True, text=True,
                           cwd=Path(__file__).resolve().parent.parent)
        self.assertIn("--reparar", r.stdout)
        self.assertIn("YA PUBLICADAS", r.stdout)


if __name__ == "__main__":
    unittest.main()
