"""
Pruebas del generador del sitio.

Lo que vigilan: que cada oferta tenga página propia, que los datos
estructurados sean los que Google Empleos necesita, y —lo más importante— que
las ofertas retiradas dejen de estar publicadas.
"""
from __future__ import annotations

import json
import re
import shutil
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from motor.almacen import Almacen                       # noqa: E402
from motor.modelos import Oferta                        # noqa: E402
from motor.sitio import generar, jobposting, slug       # noqa: E402

SITIO = "https://ejemplo.pe/cero-vagos"


class TestSlug(unittest.TestCase):

    def test_direcciones_legibles(self):
        self.assertEqual(slug("Asistente Contable", "3"), "asistente-contable-3")
        self.assertEqual(slug("Ingeniero/a de Producción — Ate"),
                         "ingeniero-a-de-produccion-ate")

    def test_sin_tildes_ni_simbolos(self):
        s = slug("¡GANA MÁS! Operario (Sta. Anita)", "9")
        self.assertRegex(s, r"^[a-z0-9-]+$")
        self.assertTrue(s.endswith("-9"))


class TestDireccionDelSitio(unittest.TestCase):
    """
    El día que se compre el dominio, todo debe salir con él sin tocar código.
    GitHub crea un archivo CNAME al conectar un dominio propio; de ahí se lee.
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_sin_dominio_usa_la_direccion_de_github(self):
        from motor.sitio import SITIO_GITHUB, sitio_publicado
        self.assertEqual(sitio_publicado(self.tmp), SITIO_GITHUB)

    def test_con_cname_usa_el_dominio_propio(self):
        from motor.sitio import sitio_publicado
        (self.tmp / "CNAME").write_text("cerovagos.com\n", encoding="utf-8")
        self.assertEqual(sitio_publicado(self.tmp), "https://cerovagos.com")

    def test_el_cname_manda_en_todo_el_sitio(self):
        (self.tmp / "CNAME").write_text("cerovagos.com\n", encoding="utf-8")
        (self.tmp / "index.html").write_text(
            "<!-- OFERTAS-ESTATICAS:INICIO -->\n<!-- OFERTAS-ESTATICAS:FIN -->",
            encoding="utf-8")
        almacen = Almacen(self.tmp / "p.db")
        almacen.guardar(Oferta(
            huella="a" * 16, fuente="Bumeran", url="https://origen.pe/1",
            puesto="Asistente Contable", empresa="Acme", ciudad="Lima",
            sueldo_min=2000, sueldo_max=2500,
            funciones=["Registrar las operaciones del día"],
            requisitos=["Un año de experiencia"],
            beneficios=["Planilla completa desde el primer día"],
            publicado=date.today(), vence=date.today() + timedelta(days=5),
            score=88, aprobada=True))

        info = generar(almacen, raiz=self.tmp)          # sin pasarle dirección
        almacen.cerrar()

        self.assertEqual(info["sitio"], "https://cerovagos.com")
        mapa = (self.tmp / "sitemap.xml").read_text(encoding="utf-8")
        self.assertIn("https://cerovagos.com/oferta/", mapa)
        self.assertNotIn("github.io", mapa)

        pagina = next((self.tmp / "oferta").glob("*/index.html")).read_text(encoding="utf-8")
        self.assertIn('rel="canonical" href="https://cerovagos.com/', pagina)
        self.assertNotIn("github.io", pagina)


class TestDatosEstructurados(unittest.TestCase):

    OFERTA = {
        "id": 1, "puesto": "Asistente Contable", "empresa": "Ferreycorp",
        "ciudad": "Lima", "modalidad": "Presencial", "min": 2800, "max": 3400,
        "resumen": "Apoyo en el cierre contable mensual.",
        "funciones": ["Registrar comprobantes en SAP"],
        "requisitos": ["Bachiller en Contabilidad"],
        "beneficios": ["Planilla completa"],
        "publicado_iso": "2026-08-01", "vence": "2026-08-20",
        "score": 94, "fuente": "Bumeran", "url": "https://origen.pe/1",
    }

    def setUp(self):
        self.datos = json.loads(jobposting(self.OFERTA, f"{SITIO}/oferta/x/"))

    def test_tiene_lo_que_google_exige(self):
        for campo in ("@context", "@type", "title", "description",
                      "datePosted", "hiringOrganization", "jobLocation"):
            with self.subTest(campo=campo):
                self.assertIn(campo, self.datos)
        self.assertEqual(self.datos["@type"], "JobPosting")

    def test_publica_el_sueldo(self):
        """El sueldo es la marca: también va en los datos estructurados."""
        salario = self.datos["baseSalary"]
        self.assertEqual(salario["currency"], "PEN")
        self.assertEqual(salario["value"]["minValue"], 2800)
        self.assertEqual(salario["value"]["maxValue"], 3400)
        self.assertEqual(salario["value"]["unitText"], "MONTH")

    def test_sin_sueldo_no_inventa_el_campo(self):
        sin = dict(self.OFERTA, min=0, max=0)
        self.assertNotIn("baseSalary", json.loads(jobposting(sin, "u")))

    def test_marca_el_trabajo_remoto(self):
        remoto = dict(self.OFERTA, modalidad="Remoto")
        self.assertEqual(json.loads(jobposting(remoto, "u"))["jobLocationType"],
                         "TELECOMMUTE")

    def test_la_descripcion_lleva_las_tres_listas(self):
        d = self.datos["description"]
        for palabra in ("Funciones", "Requisitos", "Beneficios",
                        "Registrar comprobantes", "Bachiller", "Planilla"):
            self.assertIn(palabra, d)


class TestGeneracion(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.bd = self.tmp / "prueba.db"
        self.almacen = Almacen(self.bd)
        (self.tmp / "index.html").write_text(
            "<html><body>"
            "<!-- OFERTAS-ESTATICAS:INICIO -->\n<!-- OFERTAS-ESTATICAS:FIN -->"
            "</body></html>", encoding="utf-8")

    def tearDown(self):
        self.almacen.cerrar()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _guardar(self, huella, puesto, dias_vence=8):
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

    def test_una_pagina_por_oferta(self):
        self._guardar("a" * 16, "Asistente Contable")
        self._guardar("b" * 16, "Analista de Datos")

        info = generar(self.almacen, SITIO, self.tmp)
        self.assertEqual(info["paginas"], 2)

        paginas = list((self.tmp / "oferta").glob("*/index.html"))
        self.assertEqual(len(paginas), 2)
        self.assertTrue(any("asistente-contable" in str(p) for p in paginas))

    def test_el_sitemap_lista_todo(self):
        self._guardar("a" * 16, "Asistente Contable")
        generar(self.almacen, SITIO, self.tmp)

        mapa = (self.tmp / "sitemap.xml").read_text(encoding="utf-8")
        self.assertIn(f"{SITIO}/</loc>", mapa)
        self.assertIn("asistente-contable", mapa)
        self.assertIn("<lastmod>", mapa)

    def test_robots_apunta_al_sitemap(self):
        generar(self.almacen, SITIO, self.tmp)
        robots = (self.tmp / "robots.txt").read_text(encoding="utf-8")
        self.assertIn(f"Sitemap: {SITIO}/sitemap.xml", robots)

    def test_la_portada_queda_con_enlaces_reales(self):
        """
        Las tarjetas las dibuja JavaScript; estos enlaces sí se rastrean.
        No se muestran en pantalla, pero están en el HTML y son los mismos
        destinos que las tarjetas: nada oculto ni engañoso.
        """
        self._guardar("a" * 16, "Asistente Contable")
        generar(self.almacen, SITIO, self.tmp)

        portada = (self.tmp / "index.html").read_text(encoding="utf-8")
        enlaces = re.findall(r'href="(oferta/[^"]+)"', portada)
        self.assertEqual(len(enlaces), 1)
        self.assertIn("asistente-contable", enlaces[0])
        self.assertIn('aria-label="Todas las ofertas"', portada)

    def test_la_oferta_retirada_deja_de_estar_publicada(self):
        """
        Lo más importante de todo: si una oferta sale de la web, su página se
        borra. Una convocatoria cerrada indexada en Google es peor que nada.
        """
        self._guardar("a" * 16, "Asistente Contable")
        self._guardar("b" * 16, "Cajero de Tienda", dias_vence=8)
        info = generar(self.almacen, SITIO, self.tmp)
        self.assertEqual(info["paginas"], 2)

        # La segunda cierra su plazo.
        self.almacen.con.execute(
            "UPDATE ofertas SET vence = ? WHERE huella = ?",
            ((date.today() - timedelta(days=1)).isoformat(), "b" * 16))
        self.almacen.con.commit()

        info = generar(self.almacen, SITIO, self.tmp)
        self.assertEqual(info["paginas"], 1)
        self.assertEqual(info["retiradas"], 1)

        quedan = [p.name for p in (self.tmp / "oferta").iterdir() if p.is_dir()]
        self.assertEqual(len(quedan), 1)
        self.assertIn("asistente-contable", quedan[0])

        mapa = (self.tmp / "sitemap.xml").read_text(encoding="utf-8")
        self.assertNotIn("puesto-que-vencera", mapa)

    def test_la_direccion_de_una_oferta_no_cambia_nunca(self):
        """
        Si la dirección dependiera de la posición en la lista, al retirarse una
        oferta cambiarían las de todas las demás: Google perdería lo indexado y
        quien guardó un enlace llegaría a otro puesto.
        """
        self._guardar("a" * 16, "Asistente Contable")
        self._guardar("b" * 16, "Analista de Datos")
        self._guardar("c" * 16, "Vendedor de Tienda")
        generar(self.almacen, SITIO, self.tmp)

        def direccion(parte):
            return next(p.name for p in (self.tmp / "oferta").iterdir()
                        if p.is_dir() and parte in p.name)

        antes = direccion("asistente-contable")

        # Se retiran las otras dos.
        self.almacen.con.execute(
            "UPDATE ofertas SET vence = ? WHERE huella != ?",
            ((date.today() - timedelta(days=1)).isoformat(), "a" * 16))
        self.almacen.con.commit()
        generar(self.almacen, SITIO, self.tmp)

        self.assertEqual(direccion("asistente-contable"), antes)

    def test_las_paginas_legales_se_generan(self):
        info = generar(self.almacen, SITIO, self.tmp)
        self.assertEqual(set(info["legales"]),
                         {"como-trabajamos", "terminos", "privacidad", "reclamaciones"})
        for ruta in info["legales"]:
            with self.subTest(pagina=ruta):
                self.assertTrue((self.tmp / ruta / "index.html").exists())

    def test_el_libro_de_reclamaciones_no_se_indexa(self):
        """Es un canal de atención, no contenido para buscadores."""
        generar(self.almacen, SITIO, self.tmp)
        libro = (self.tmp / "reclamaciones" / "index.html").read_text(encoding="utf-8")
        self.assertIn('name="robots" content="noindex"', libro)
        mapa = (self.tmp / "sitemap.xml").read_text(encoding="utf-8")
        self.assertNotIn("/reclamaciones/", mapa)
        # Las otras tres sí van al sitemap.
        for ruta in ("como-trabajamos", "terminos", "privacidad"):
            self.assertIn(f"{SITIO}/{ruta}/", mapa)

    def test_las_legales_dicen_lo_que_deben_decir(self):
        generar(self.almacen, SITIO, self.tmp)
        leer = lambda r: (self.tmp / r / "index.html").read_text(encoding="utf-8")  # noqa: E731

        # La posición del proyecto, que es lo que protege a Mentita.
        como = leer("como-trabajamos")
        self.assertIn("No publicamos ofertas propias", como)
        self.assertIn("No te cobramos nada", como)
        self.assertIn("responsabilidad de quien lo publicó", como)
        self.assertIn("dinero por adelantado", como)      # aviso de estafas

        # Privacidad: hoy no se recoge nada, y se dice.
        priv = leer("privacidad")
        self.assertIn("no te pide ningún dato", priv)
        self.assertIn("no usa cookies", priv)
        self.assertIn("29733", priv)

        # Reclamaciones: la ley y el plazo.
        libro = leer("reclamaciones")
        self.assertIn("29571", libro)
        self.assertIn("15 días hábiles", libro)
        self.assertIn("INDECOPI", libro)

    def test_las_legales_usan_el_dominio_correcto(self):
        (self.tmp / "CNAME").write_text("cerovagos.com\n", encoding="utf-8")
        generar(self.almacen, raiz=self.tmp)
        terminos = (self.tmp / "terminos" / "index.html").read_text(encoding="utf-8")
        self.assertIn('rel="canonical" href="https://cerovagos.com/terminos/"', terminos)
        self.assertNotIn("github.io", terminos)

    def test_hay_pagina_para_el_enlace_viejo(self):
        """
        Quien llega con un enlace guardado o compartido debe encontrar una
        explicación, no un error genérico. Y esa página no se indexa.
        """
        generar(self.almacen, SITIO, self.tmp)
        pagina = (self.tmp / "404.html").read_text(encoding="utf-8")
        self.assertIn("ya cerró", pagina)
        self.assertIn('name="robots" content="noindex"', pagina)
        self.assertIn(f"{SITIO}/#ofertas", pagina)

    def test_la_pagina_enlaza_al_aviso_original(self):
        self._guardar("a" * 16, "Asistente Contable")
        generar(self.almacen, SITIO, self.tmp)
        pagina = next((self.tmp / "oferta").glob("*/index.html")).read_text(encoding="utf-8")
        self.assertIn("https://origen.pe/", pagina)
        self.assertIn("canonical", pagina)
        self.assertIn("application/ld+json", pagina)


if __name__ == "__main__":
    unittest.main(verbosity=2)


class PruebaCompartir(unittest.TestCase):
    """
    La tarjeta que sale al pegar el enlace en WhatsApp.

    El error clásico acá es dejar la imagen como ruta relativa
    ("assets/compartir.png"). Se ve bien en el navegador y no sale nada en
    WhatsApp, que no resuelve rutas relativas. Por eso se vigila.
    """

    SITIO = "https://cerovagos.com"

    def test_las_direcciones_de_compartir_son_absolutas(self):
        from motor.sitio import bloque_compartir

        bloque = bloque_compartir(self.SITIO, 75)
        for etiqueta in ("og:image", "og:url", "twitter:image"):
            valor = re.search(
                rf'(?:property|name)="{etiqueta}" content="([^"]*)"', bloque).group(1)
            self.assertTrue(
                valor.startswith("https://"),
                f"{etiqueta} tiene que ser una dirección completa, no «{valor}»")

    def test_la_imagen_de_compartir_existe_y_mide_lo_declarado(self):
        from motor.sitio import IMAGEN_COMPARTIR

        imagen = RAIZ / IMAGEN_COMPARTIR
        self.assertTrue(imagen.exists(), f"falta {IMAGEN_COMPARTIR}")

        # Ancho y alto salen de la cabecera del PNG, sin instalar nada.
        cabecera = imagen.read_bytes()[:24]
        ancho = int.from_bytes(cabecera[16:20], "big")
        alto = int.from_bytes(cabecera[20:24], "big")
        self.assertEqual((ancho, alto), (1200, 630),
                         "WhatsApp y Facebook esperan 1200x630")

        # Más pesada que esto y algunas apps no la muestran.
        self.assertLess(imagen.stat().st_size, 300 * 1024,
                        "la imagen pesa demasiado para una vista previa")

    def test_el_porcentaje_de_la_descripcion_sale_de_la_base(self):
        from motor.sitio import bloque_compartir

        self.assertIn("El 88% de los avisos", bloque_compartir(self.SITIO, 88))


class PruebaAislamiento(unittest.TestCase):
    """
    Los tests no pueden tocar los archivos de verdad.

    Esto no es purismo: pasó. `generar()` recibía una carpeta temporal para
    las páginas, pero por dentro llamaba al exportador, que escribía siempre
    en `datos/ofertas.js` sin mirar la carpeta. Resultado: correr los tests
    dejaba la portada del sitio con dos ofertas inventadas ("Analista de
    Datos — Acme"), y se subía así sin que nadie lo notara.
    """

    def test_generar_no_toca_el_archivo_de_ofertas_de_verdad(self):
        from motor.sitio import generar

        real = RAIZ / "datos" / "ofertas.js"
        antes = real.read_bytes() if real.exists() else None

        with tempfile.TemporaryDirectory() as tmp:
            al = Almacen(":memory:")
            al.guardar(Oferta(
                huella="z" * 16, fuente="Bumeran", url="https://origen.pe/9",
                puesto="Analista de Prueba", empresa="Empresa de Prueba",
                ciudad="Lima", sueldo_min=2000, sueldo_max=2500,
                funciones=["Una función"], requisitos=["Un requisito"],
                beneficios=["Un beneficio"],
                publicado=date.today(), vence=date.today() + timedelta(days=5),
                score=88, aprobada=True))
            generar(al, "https://ejemplo.test", Path(tmp))
            al.cerrar()

            copia = Path(tmp) / "datos" / "ofertas.js"
            self.assertTrue(copia.exists(),
                            "el exportador ni siquiera escribió en la carpeta temporal")

        despues = real.read_bytes() if real.exists() else None
        self.assertEqual(antes, despues,
                         "los tests sobrescribieron datos/ofertas.js del proyecto")
