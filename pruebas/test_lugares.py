"""
Las páginas por departamento: "Trabajos en Junín con sueldo a la vista".

Es lo que la gente escribe en Google y lo que el sitio no tenía. La portada
compite por "ofertas de trabajo Perú", que es una pelea contra Computrabajo y
Bumeran; "trabajos en Huancavelica con sueldo" no la pelea nadie.

No existían antes porque no había con qué llenarlas: al 8 de agosto solo Lima
pasaba de cinco ofertas. Lo que lo cambió fue partir las convocatorias CAS de
varios puestos — la oferta de provincia pasó de 24 a 73 en un día.

LO QUE ESTAS PRUEBAS CUIDAN, EN ORDEN
-------------------------------------
1. Que una página no nazca vacía, y que **desaparezca** si su departamento se
   queda corto. Las convocatorias CAS duran una o dos semanas: un departamento
   puede pasar de 29 ofertas a 6 en quince días, y una página indexada sin
   contenido le dice a Google que el sitio es de baja calidad.
2. Que cada página traiga el dato que solo nosotros tenemos —cuántos avisos se
   revisaron ahí y cuántos declaraban sueldo—, porque sin eso es un listado
   más y un listado más no merece existir.
3. Que estén enlazadas desde la portada y desde cada oferta. Sin enlaces,
   Google llega tarde y les da menos peso.
"""
from __future__ import annotations

import re
import shutil
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from motor.almacen import Almacen
from motor.lugares import MINIMO_OFERTAS, MINIMO_RUBRO, ruta, ruta_rubro
from motor.modelos import Oferta

RAIZ = Path(__file__).resolve().parent.parent


def _oferta(puesto: str, ciudad: str, departamento: str, sueldo: int = 2000,
            categoria: str = "Otros") -> Oferta:
    return Oferta(
        huella=Oferta.calcular_huella(puesto, "Entidad", ciudad),
        fuente="Convocatorias CAS",
        url=f"https://ejemplo.pe/{puesto}".lower().replace(" ", "-"),
        puesto=puesto, empresa="Entidad", ciudad=ciudad, departamento=departamento,
        sueldo_min=sueldo, sueldo_max=sueldo, categoria=categoria,
        funciones=["a", "b", "c"], requisitos=["a", "b", "c"],
        beneficios=["planilla", "eps"],
        publicado=date.today(), vence=date.today() + timedelta(days=10),
        aprobada=True, score=80,
    )


class Base(unittest.TestCase):

    def setUp(self):
        self.carpeta = Path(tempfile.mkdtemp())
        shutil.copy(RAIZ / "index.html", self.carpeta / "index.html")
        self.db = self.carpeta / "prueba.db"
        self.al = Almacen(str(self.db))

    def tearDown(self):
        shutil.rmtree(self.carpeta, ignore_errors=True)

    def poblar(self, departamento: str, ciudad: str, cuantas: int, sueldo: int = 2000,
               categoria: str = "Otros"):
        for i in range(cuantas):
            self.al.guardar(_oferta(f"Especialista de {ciudad}{categoria} {i + 1}",
                                    ciudad, departamento, sueldo, categoria))

    def generar(self) -> dict:
        from motor.sitio import generar
        return generar(self.al, "https://cerovagos.com", self.carpeta)

    def html(self, departamento: str) -> str:
        return (self.carpeta / ruta(departamento) / "index.html").read_text(
            encoding="utf-8")


class PruebaCuandoNaceUnaPagina(Base):

    def test_con_pocas_ofertas_no_hay_pagina(self):
        """
        Una página de "Trabajos en Tacna" con dos ofertas hace más daño que no
        tenerla: Google la lee como señal de sitio de baja calidad y esa señal
        mancha al resto.
        """
        self.poblar("Tacna", "Tacna", MINIMO_OFERTAS - 1)
        resultado = self.generar()

        self.assertNotIn("Tacna", resultado["lugares"])
        self.assertFalse((self.carpeta / ruta("Tacna")).exists())

    def test_al_llegar_al_minimo_aparece(self):
        self.poblar("Junín", "Huancayo", MINIMO_OFERTAS)
        self.assertIn("Junín", self.generar()["lugares"])

    def test_si_baja_del_minimo_la_pagina_SE_BORRA(self):
        """
        El caso que va a pasar de verdad. Las convocatorias CAS duran una o dos
        semanas: un departamento con 29 ofertas puede quedar en 3 quince días
        después. Es la misma regla 4 de las ofertas vencidas — lo que ya no
        tiene contenido no se queda indexado.
        """
        self.poblar("Junín", "Huancayo", MINIMO_OFERTAS + 2)
        self.generar()
        self.assertTrue((self.carpeta / ruta("Junín")).exists())

        # Se vencen todas menos dos.
        for fila in self.al.aprobadas(100)[2:]:
            self.al.con.execute("UPDATE ofertas SET vigente = 0 WHERE huella = ?",
                                (fila["huella"],))
        self.al.con.commit()

        resultado = self.generar()
        self.assertNotIn("Junín", resultado["lugares"])
        self.assertFalse((self.carpeta / ruta("Junín")).exists(),
                         "quedó una página indexada sin ofertas que mostrar")


class PruebaLoQueDiceLaPagina(Base):

    def setUp(self):
        super().setUp()
        self.poblar("Junín", "Huancayo", 7, sueldo=2500)
        # Tres avisos más de Junín que el motor revisó y rechazó: son los que
        # dan el dato de transparencia local.
        for i in range(3):
            o = _oferta(f"Vago de Huancayo {i}", "Huancayo", "Junín", 0)
            o.aprobada = False
            o.sueldo_min = o.sueldo_max = 0
            self.al.guardar(o)
        self.generar()
        self.pagina = self.html("Junín")

    def test_el_titulo_apunta_a_lo_que_la_gente_busca(self):
        titulo = re.search(r"<title>(.*?)</title>", self.pagina).group(1)
        self.assertIn("Trabajos en Junín", titulo)
        self.assertIn("sueldo", titulo.lower())

    def test_estan_todas_las_ofertas_del_departamento(self):
        self.assertEqual(self.pagina.count('class="oferta"'), 7)

    def test_los_enlaces_llevan_a_la_ficha_de_cada_oferta(self):
        """
        Y con la dirección de verdad, la que sale de la huella (regla 3). Si
        esta página armara las direcciones por su cuenta, un día dejarían de
        coincidir y todos los enlaces caerían en 404.
        """
        from motor.sitio import CARPETA_OFERTAS
        enlaces = re.findall(rf'href="[^"]*/{CARPETA_OFERTAS}/([^/"]+)/"', self.pagina)
        self.assertEqual(len(enlaces), 7)
        for slug in enlaces:
            self.assertTrue((self.carpeta / CARPETA_OFERTAS / slug).exists(),
                            f"la página enlaza a /{CARPETA_OFERTAS}/{slug}/, que no existe")

    def test_trae_el_dato_de_transparencia_de_ESE_departamento(self):
        """
        Es lo que hace que la página valga por sí sola. Sin esto sería un
        listado más, y un listado más no merece existir ni posicionar.
        """
        self.assertIn("10 avisos de empleo", self.pagina)   # 7 publicados + 3 sin sueldo
        self.assertIn("30%", self.pagina)                   # 3 de 10 no dicen cuánto pagan

    def test_muestra_el_sueldo_mediano(self):
        self.assertIn("S/ 2,500", self.pagina)

    def test_no_promete_lo_que_no_cumple(self):
        """La promesa del sitio, escrita en la página: sin sueldo no entra."""
        self.assertIn("a convenir", self.pagina)


class PruebaLosEnlacesInternos(Base):

    def setUp(self):
        super().setUp()
        self.poblar("Junín", "Huancayo", 6)
        self.poblar("Huancavelica", "Huancavelica", 6)
        self.generar()

    def test_la_portada_enlaza_a_cada_departamento(self):
        """
        Sin un enlace desde la portada, Google llega a estas páginas solo por
        el sitemap —que es una invitación, no una orden— y les da menos peso.
        """
        portada = (self.carpeta / "index.html").read_text(encoding="utf-8")
        bloque = re.search(r"<!-- LUGARES:INICIO -->.*?<!-- LUGARES:FIN -->",
                           portada, re.S).group(0)
        self.assertIn("trabajos-en/junin/", bloque)
        self.assertIn("trabajos-en/huancavelica/", bloque)

    def test_cada_departamento_enlaza_a_sus_vecinos(self):
        self.assertIn("trabajos-en/huancavelica/", self.html("Junín"))
        self.assertIn("trabajos-en/junin/", self.html("Huancavelica"))

    def test_la_ficha_de_una_oferta_enlaza_a_su_departamento(self):
        fichas = list((self.carpeta / "oferta").iterdir())
        alguna = (fichas[0] / "index.html").read_text(encoding="utf-8")
        self.assertRegex(alguna, r"trabajos-en/(junin|huancavelica)/")

    def test_entran_al_sitemap(self):
        mapa = (self.carpeta / "sitemap.xml").read_text(encoding="utf-8")
        self.assertIn("/trabajos-en/junin/", mapa)
        self.assertIn("/trabajos-en/huancavelica/", mapa)

    def test_la_portada_no_enlaza_a_departamentos_sin_pagina(self):
        """Un enlace a una página que no existe es peor que ningún enlace."""
        portada = (self.carpeta / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("trabajos-en/tacna/", portada)


class PruebaLasPaginasPorRubro(Base):
    """
    La otra mitad de lo mismo: `/trabajos-de/ventas/`.

    Comparten plantilla con las de departamento a propósito — son la misma
    página con otro eje— y por eso lo que se prueba aquí es lo que las
    distingue, no lo que ya cubren las de arriba.
    """

    def test_el_piso_del_rubro_es_mas_alto_que_el_del_departamento(self):
        """
        Y no es capricho. Una página de "trabajos de ventas" compite contra
        todas las bolsas del Perú; una de "trabajos en Huancavelica" no compite
        con casi nadie. Donde la pelea es dura hay que llegar con más avisos.
        """
        self.assertGreater(MINIMO_RUBRO, MINIMO_OFERTAS)

    def test_un_rubro_con_pocas_ofertas_no_tiene_pagina(self):
        self.poblar("Lima", "Lima", MINIMO_RUBRO - 1, categoria="Marketing")
        self.assertNotIn("Marketing", self.generar()["rubros"])

    def test_al_llegar_al_piso_aparece(self):
        self.poblar("Lima", "Lima", MINIMO_RUBRO, categoria="Ventas")
        resultado = self.generar()

        self.assertIn("Ventas", resultado["rubros"])
        self.assertTrue((self.carpeta / ruta_rubro("Ventas") / "index.html").exists())

    def test_OTROS_nunca_tiene_pagina(self):
        """
        "Otros" no es un rubro: es el cajón donde cae lo que el motor no supo
        clasificar. Nadie busca "trabajos de otros" en Google, y una página con
        ese título diría que el sitio no sabe lo que publica.
        """
        self.poblar("Lima", "Lima", MINIMO_RUBRO * 3, categoria="Otros")
        resultado = self.generar()

        self.assertEqual(resultado["rubros"], [])
        self.assertFalse((self.carpeta / ruta_rubro("Otros")).exists())

    def test_el_titular_dice_DE_y_no_EN(self):
        """"Trabajos de Ventas", no "Trabajos en Ventas"."""
        self.poblar("Lima", "Lima", MINIMO_RUBRO, categoria="Ventas")
        self.generar()
        html = (self.carpeta / ruta_rubro("Ventas") / "index.html").read_text(
            encoding="utf-8")

        self.assertIn("Trabajos de Ventas", re.search(
            r"<title>(.*?)</title>", html).group(1))
        self.assertNotIn("Trabajos en Ventas", html)

    def test_la_direccion_va_en_su_propia_carpeta(self):
        """
        Separada de la de los departamentos. Si compartieran carpeta, un rubro
        y un departamento que se llamaran igual se pisarían.
        """
        self.assertEqual(ruta_rubro("Atención al Cliente"),
                         "trabajos-de/atencion-al-cliente")
        self.assertTrue(ruta("Lima").startswith("trabajos-en/"))
        self.assertTrue(ruta_rubro("Ventas").startswith("trabajos-de/"))

    def test_entran_al_sitemap_y_al_pie_de_la_portada(self):
        self.poblar("Lima", "Lima", MINIMO_RUBRO, categoria="Ventas")
        self.generar()

        mapa = (self.carpeta / "sitemap.xml").read_text(encoding="utf-8")
        self.assertIn("/trabajos-de/ventas/", mapa)

        portada = (self.carpeta / "index.html").read_text(encoding="utf-8")
        bloque = re.search(r"<!-- LUGARES:INICIO -->.*?<!-- LUGARES:FIN -->",
                           portada, re.S).group(0)
        self.assertIn("trabajos-de/ventas/", bloque)


class PruebaLaLimpiezaCuandoNoQUEDA_NINGUNO(Base):
    """
    El fallo que este test cazó al generalizar la plantilla (12/8/2026).

    La carpeta a limpiar se estaba deduciendo del PRIMER grupo publicado. Con
    cero grupos no había primer grupo, así que no había carpeta que limpiar y
    las páginas viejas se quedaban publicadas para siempre — justo el caso
    extremo que la limpieza existe para cubrir.
    """

    def test_si_no_queda_ningun_rubro_igual_se_borran_las_viejas(self):
        self.poblar("Lima", "Lima", MINIMO_RUBRO, categoria="Ventas")
        self.generar()
        self.assertTrue((self.carpeta / ruta_rubro("Ventas")).exists())

        # Se vencen TODAS: no queda ningún rubro con página posible.
        self.al.con.execute("UPDATE ofertas SET vigente = 0")
        self.al.con.commit()

        resultado = self.generar()
        self.assertEqual(resultado["rubros"], [])
        self.assertFalse((self.carpeta / ruta_rubro("Ventas")).exists(),
                         "quedó una página indexada sin ofertas que mostrar")


class PruebaLaDireccion(unittest.TestCase):

    def test_los_nombres_con_tilde_y_espacio_se_arman_bien(self):
        self.assertEqual(ruta("Junín"), "trabajos-en/junin")
        self.assertEqual(ruta("San Martín"), "trabajos-en/san-martin")
        self.assertEqual(ruta("Madre de Dios"), "trabajos-en/madre-de-dios")
        self.assertEqual(ruta("Áncash"), "trabajos-en/ancash")


if __name__ == "__main__":
    unittest.main()
