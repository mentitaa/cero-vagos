"""
Pruebas del ranking de transparencia salarial.

Aquí se señala a empresas con nombre propio, así que las reglas de juego
importan tanto como el cálculo: nadie aparece con una muestra insuficiente y
el conteo tiene que ser exacto.
"""
from __future__ import annotations

import re
import shutil
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from motor.almacen import Almacen                       # noqa: E402
from motor.modelos import Oferta                        # noqa: E402
from motor.transparencia import generar, pagina         # noqa: E402


class TestRanking(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.almacen = Almacen(self.tmp / "p.db")
        self.n = 0

    def tearDown(self):
        self.almacen.cerrar()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _avisos(self, empresa, total, con_sueldo, categoria="Ventas", ciudad="Lima"):
        for i in range(total):
            self.n += 1
            tiene = i < con_sueldo
            self.almacen.guardar(Oferta(
                huella=f"h{self.n:015d}", fuente="Bumeran", url=f"https://x.pe/{self.n}",
                puesto=f"Puesto {self.n}", empresa=empresa, ciudad=ciudad,
                categoria=categoria, sueldo_min=2000 if tiene else 0,
                publicado=date.today(), aprobada=tiene))

    def test_cuenta_bien_quien_declara_el_sueldo(self):
        self._avisos("Transparente SAC", 4, 4)
        self._avisos("Opaca SAC", 6, 0)

        d = self.almacen.transparencia(minimo_avisos=3)
        self.assertEqual(d["total"], 10)
        self.assertEqual(d["con_sueldo"], 4)
        self.assertEqual(d["pct_sin_sueldo"], 60)

        por_nombre = {e["nombre"]: e for e in d["empresas"]}
        self.assertEqual(por_nombre["Transparente SAC"]["pct"], 100)
        self.assertEqual(por_nombre["Opaca SAC"]["pct"], 0)

    def test_nadie_aparece_con_muestra_insuficiente(self):
        """Señalar a una empresa por un solo aviso sería injusto."""
        self._avisos("Con Historial SAC", 5, 0)
        self._avisos("Un Solo Aviso SAC", 1, 0)

        nombres = [e["nombre"] for e in self.almacen.transparencia(3)["empresas"]]
        self.assertIn("Con Historial SAC", nombres)
        self.assertNotIn("Un Solo Aviso SAC", nombres)

    def test_las_listas_separan_bien(self):
        self._avisos("Siempre SAC", 5, 5)          # 100%
        self._avisos("Casi Siempre SAC", 5, 4)     # 80%
        self._avisos("A Medias SAC", 4, 2)         # 50%
        self._avisos("Nunca SAC", 4, 0)            # 0%

        d = self.almacen.transparencia(3)
        transparentes = {e["nombre"] for e in d["transparentes"]}
        opacas = {e["nombre"] for e in d["opacas"]}

        self.assertEqual(transparentes, {"Siempre SAC", "Casi Siempre SAC"})
        self.assertEqual(opacas, {"Nunca SAC"})
        # La del medio no está en ninguna lista: no es ejemplo de nada.
        self.assertNotIn("A Medias SAC", transparentes | opacas)

    def test_las_tablas_se_ordenan_por_transparencia(self):
        """
        Cada tabla habla de transparencia, así que se ordena por eso. A igual
        porcentaje manda el volumen: 100% sobre 12 avisos dice más que sobre 3.
        """
        self._avisos("Media SAC", 12, 10)      # 83%, mucho volumen
        self._avisos("Perfecta SAC", 5, 5)     # 100%
        self._avisos("Grande SAC", 8, 8)       # 100%, más volumen
        self._avisos("Cero Grande SAC", 9, 0)  # 0%, mucho volumen
        self._avisos("Cero Chica SAC", 4, 0)   # 0%

        d = self.almacen.transparencia(3)

        self.assertEqual([e["nombre"] for e in d["transparentes"]],
                         ["Grande SAC", "Perfecta SAC", "Media SAC"])
        # Las opacas van de 0% hacia arriba, y entre iguales primero la grande.
        self.assertEqual([e["nombre"] for e in d["opacas"]],
                         ["Cero Grande SAC", "Cero Chica SAC"])

    def test_los_rubros_tambien_van_ordenados(self):
        self._avisos("A SAC", 4, 0, categoria="Opaco")
        self._avisos("B SAC", 4, 4, categoria="Claro")
        self._avisos("C SAC", 4, 2, categoria="Medio")

        rubros = [e["nombre"] for e in self.almacen.transparencia(3)["por_categoria"]]
        self.assertEqual(rubros, ["Claro", "Medio", "Opaco"])

    def test_agrupa_por_rubro_ciudad_y_portal(self):
        self._avisos("A SAC", 4, 4, categoria="Contabilidad", ciudad="Cusco")
        self._avisos("B SAC", 4, 0, categoria="Ventas", ciudad="Lima")

        d = self.almacen.transparencia(3)
        rubros = {e["nombre"]: e["pct"] for e in d["por_categoria"]}
        ciudades = {e["nombre"]: e["pct"] for e in d["por_ciudad"]}
        self.assertEqual(rubros["Contabilidad"], 100)
        self.assertEqual(rubros["Ventas"], 0)
        self.assertEqual(ciudades["Cusco"], 100)

    def test_el_reloj_es_siempre_el_mismo(self):
        """
        SQLite usa UTC y Python la hora local. En Perú, después de las 7 de la
        tarde ya no son el mismo día: mezclarlos corría las cuentas 24 horas.
        """
        from datetime import datetime, timedelta

        self._avisos("Acme SAC", 3, 0)
        ayer = (datetime.now() - timedelta(hours=25)).isoformat(sep=" ", timespec="seconds")
        self.almacen.con.execute("UPDATE ofertas SET visto_ultima_vez = ?", (ayer,))
        self.almacen.con.commit()

        # Rechazadas hace 25 horas: siguen dentro de la ventana de 30 días.
        self.assertEqual(len(self.almacen.urls_a_saltar()), 3)
        # Y fuera de una ventana de 20 horas.
        self.assertEqual(self.almacen.urls_vistas(horas=20), set())

    def test_base_vacia_no_revienta(self):
        d = self.almacen.transparencia(3)
        self.assertEqual(d["total"], 0)
        self.assertEqual(d["pct_sin_sueldo"], 0)
        self.assertEqual(d["empresas"], [])


class TestPagina(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.almacen = Almacen(self.tmp / "p.db")
        for i in range(5):
            self.almacen.guardar(Oferta(
                huella=f"h{i:015d}", fuente="Bumeran", url=f"https://x.pe/{i}",
                puesto=f"Puesto {i}", empresa="Opaca SAC", ciudad="Lima",
                categoria="Ventas", sueldo_min=0, publicado=date.today(),
                aprobada=False))

    def tearDown(self):
        self.almacen.cerrar()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_publica_la_cifra_y_el_metodo(self):
        info = generar(self.almacen, "https://ejemplo.pe", self.tmp)
        html = (self.tmp / "transparencia" / "index.html").read_text(encoding="utf-8")

        self.assertIn("100%", html)                     # la cifra grande
        self.assertIn("Opaca SAC", html)                # la empresa señalada
        self.assertIn("Cómo se hizo", html)             # la metodología
        self.assertIn("no significa que pague mal", html)   # la aclaración justa
        self.assertIn("Publica el sueldo en tu próximo aviso", html)  # cómo salir

    def test_lleva_lo_necesario_para_buscadores(self):
        generar(self.almacen, "https://ejemplo.pe", self.tmp)
        html = (self.tmp / "transparencia" / "index.html").read_text(encoding="utf-8")
        self.assertIn('rel="canonical" href="https://ejemplo.pe/transparencia/"', html)
        self.assertRegex(html, r"<title>.*no dice cuánto paga.*</title>")
        self.assertIn('property="og:description"', html)

    def test_los_nombres_de_empresa_se_limpian(self):
        """Los nombres vienen de portales ajenos: no pueden inyectar código."""
        self.almacen.guardar(Oferta(
            huella="x" * 16, fuente="Bumeran", url="https://x.pe/9",
            puesto="P", empresa='<img src=x onerror="alert(1)">SAC', ciudad="Lima",
            categoria="Ventas", sueldo_min=0, publicado=date.today(), aprobada=False))
        for i in range(3):
            self.almacen.guardar(Oferta(
                huella=f"y{i:015d}", fuente="Bumeran", url=f"https://x.pe/y{i}",
                puesto="P", empresa='<img src=x onerror="alert(1)">SAC', ciudad="Lima",
                categoria="Ventas", sueldo_min=0, publicado=date.today(), aprobada=False))

        generar(self.almacen, "https://ejemplo.pe", self.tmp)
        html = (self.tmp / "transparencia" / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("<img src=x", html)
        self.assertIn("&lt;img src=x", html)


if __name__ == "__main__":
    unittest.main(verbosity=2)
