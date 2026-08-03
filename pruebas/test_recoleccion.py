"""
Pruebas de la capa de recolección: sitemaps, robots y configuración de fuentes.
Todo offline: se usan respuestas reales guardadas como texto.

    python -m unittest discover pruebas -v
"""
from __future__ import annotations

import gzip
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from motor.fuentes.portal_web import (                                    # noqa: E402
    PortalWeb, fuentes_por_verificar, portales_peru,
)
from motor.fuentes.robots import Politica, parsear_robots                 # noqa: E402
from motor.fuentes.sitemap import filtrar_recientes, parsear              # noqa: E402

HOY = date.today().isoformat()
VIEJO = (date.today() - timedelta(days=120)).isoformat()

# Recorte real del sitemap de avisos de Bumeran.
SITEMAP_AVISOS = f"""<?xml version="1.0" encoding="utf-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://www.bumeran.com.pe/empleos/jefe-e-commerce-1118325784.html</loc>
    <lastmod>{HOY}</lastmod>
    <changefreq>daily</changefreq>
  </url>
  <url>
    <loc>https://www.bumeran.com.pe/empleos/demand-planner-topitop-1118325570.html</loc>
    <lastmod>{VIEJO}</lastmod>
  </url>
  <url>
    <loc>https://www.bumeran.com.pe/empleos/sin-fecha-1118325999.html</loc>
  </url>
</urlset>"""

SITEMAP_INDICE = """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>https://ejemplo.pe/sitemap_avisos_1.xml</loc></sitemap>
  <sitemap><loc>https://ejemplo.pe/sitemap_avisos_2.xml.gz</loc></sitemap>
</sitemapindex>"""

# robots.txt real de Bumeran (recortado).
ROBOTS_BUMERAN = """User-agent: LinkedInBot
Allow: /empleos/*
Disallow: /

User-agent: *
Disallow: /*recientes=true
Disallow: /empleos/aptitus/*

Sitemap: https://www.bumeran.com.pe/sitemap_avisos_bum.xml
Sitemap: https://www.bumeran.com.pe/sitemap_core_bum.xml"""


class TestSitemap(unittest.TestCase):

    def test_urlset(self):
        d = parsear(SITEMAP_AVISOS)
        self.assertEqual(len(d["urls"]), 3)
        self.assertEqual(d["sitemaps"], [])
        self.assertEqual(d["urls"][0][1], date.today())

    def test_indice(self):
        d = parsear(SITEMAP_INDICE)
        self.assertEqual(len(d["sitemaps"]), 2)
        self.assertEqual(d["urls"], [])

    def test_gzip(self):
        d = parsear(gzip.compress(SITEMAP_AVISOS.encode()))
        self.assertEqual(len(d["urls"]), 3)

    def test_xml_con_basura_adelante(self):
        d = parsear("﻿\n  " + SITEMAP_AVISOS)
        self.assertEqual(len(d["urls"]), 3)

    def test_url_partida_en_dos_lineas(self):
        """
        Caso real: el generador del portal parte la URL después del dominio.
        Sin unirla, el dominio queda como 'ejemplo.pe%0a' y no resuelve.
        """
        partido = """<?xml version="1.0" encoding="utf-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
          <url><loc>https://www.convocape.com
/convocatorias/abogado-de-demuna-cas-2026-07-797413</loc></url>
        </urlset>"""
        d = parsear(partido)
        self.assertEqual(
            d["urls"][0][0],
            "https://www.convocape.com/convocatorias/abogado-de-demuna-cas-2026-07-797413",
        )
        self.assertNotIn("\n", d["urls"][0][0])

    def test_indice_con_url_partida(self):
        partido = """<?xml version="1.0" encoding="UTF-8"?>
        <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
          <sitemap><loc>https://ejemplo.pe
/sitemap_1.xml</loc></sitemap>
        </sitemapindex>"""
        self.assertEqual(parsear(partido)["sitemaps"], ["https://ejemplo.pe/sitemap_1.xml"])

    def test_filtra_por_lastmod(self):
        urls = parsear(SITEMAP_AVISOS)["urls"]
        recientes = filtrar_recientes(urls, dias=30)
        self.assertEqual(len(recientes), 2)                      # el de hoy y el sin fecha
        self.assertNotIn("demand-planner", " ".join(recientes))

        sin_dudosos = filtrar_recientes(urls, dias=30, incluir_sin_fecha=False)
        self.assertEqual(len(sin_dudosos), 1)


class TestRobots(unittest.TestCase):

    def _politica(self, texto: str) -> Politica:
        reglas = parsear_robots(texto)
        return Politica(dominio="www.bumeran.com.pe", legible=True,
                        reglas=reglas, sitemaps=reglas.sitemaps)

    def test_permite_avisos(self):
        pol = self._politica(ROBOTS_BUMERAN)
        self.assertTrue(pol.permite("https://www.bumeran.com.pe/empleos/jefe-1118.html"))

    def test_respeta_disallow_con_comodin(self):
        """urllib.robotparser falla justo aquí: ignora el '*' del patrón."""
        pol = self._politica(ROBOTS_BUMERAN)
        self.assertFalse(pol.permite("https://www.bumeran.com.pe/empleos/aptitus/algo.html"))

    def test_disallow_en_query_string(self):
        pol = self._politica(ROBOTS_BUMERAN)
        self.assertFalse(pol.permite("https://www.bumeran.com.pe/empleos.html?recientes=true"))

    def test_no_toma_el_grupo_de_otro_bot(self):
        """El grupo de LinkedInBot dice 'Disallow: /', pero no es el nuestro."""
        reglas = parsear_robots(ROBOTS_BUMERAN)
        self.assertEqual(reglas.grupo, "*")
        self.assertTrue(reglas.permite("/blog/nota"))

    def test_gana_la_regla_mas_especifica(self):
        reglas = parsear_robots("User-agent: *\nDisallow: /empleos/\nAllow: /empleos/publicos/")
        self.assertFalse(reglas.permite("/empleos/privado"))
        self.assertTrue(reglas.permite("/empleos/publicos/aviso-1"))

    def test_disallow_vacio_permite_todo(self):
        reglas = parsear_robots("User-agent: *\nDisallow:")
        self.assertTrue(reglas.permite("/lo-que-sea"))

    def test_crawl_delay(self):
        reglas = parsear_robots("User-agent: *\nCrawl-delay: 10\nDisallow: /admin")
        self.assertEqual(reglas.crawl_delay, 10.0)

    def test_lee_sitemaps_declarados(self):
        pol = self._politica(ROBOTS_BUMERAN)
        self.assertEqual(len(pol.sitemaps), 2)
        self.assertIn("sitemap_avisos_bum.xml", pol.sitemaps[0])

    def test_sitemap_sin_espacios_raros(self):
        reglas = parsear_robots("User-agent: *\nAllow: /\nSitemap: https://ejemplo.pe /s.xml")
        self.assertEqual(reglas.sitemaps, ["https://ejemplo.pe/s.xml"])

    def test_sin_robots_legible_no_se_pide_nada(self):
        """Si no pudimos leer el robots.txt, no asumimos permiso."""
        pol = Politica(dominio="pe.computrabajo.com", legible=False)
        self.assertFalse(pol.permite("https://pe.computrabajo.com/ofertas-de-trabajo/x"))


class TestPortalesQueNecesitanNavegador(unittest.TestCase):
    """
    En los portales hechos en JavaScript, la página de resultados TAMBIÉN hay
    que renderizarla. Si el navegador se abre después de descubrir, la fuente
    muere en el primer paso con 'navegador no iniciado'.
    """

    def _correr(self):
        from motor.fuentes import portal_web as pw
        from motor.modelos import OfertaCruda

        eventos = []

        class NavegadorFalso:
            def __init__(self, *a, **k): pass
            def __enter__(self_): eventos.append("abre"); return self_
            def __exit__(self_, *a): eventos.append("cierra")
            def html(self_, url):
                eventos.append(f"render:{url.rsplit('/', 1)[-1]}")
                return '<a href="/empleos/analista-123.html">Analista</a>'

        original_nav, original_flag = pw.Navegador, pw.HAY_PLAYWRIGHT
        pw.Navegador, pw.HAY_PLAYWRIGHT = NavegadorFalso, True
        try:
            p = pw.PortalWeb(
                "SPA", "https://ejemplo.pe",
                listados=("https://ejemplo.pe/empleos",),
                patron_aviso=r"/empleos/[^\"'\s]+\.html",
                necesita_render=True,
                parser=lambda h, u, f: OfertaCruda(fuente=f, url=u, puesto="Analista"),
            )
            p.robots.permite = lambda url: True
            p.robots.esperar_turno = lambda url: None
            avisos = list(p.recolectar(2))
            return avisos, eventos, p
        finally:
            pw.Navegador, pw.HAY_PLAYWRIGHT = original_nav, original_flag

    def test_el_navegador_se_abre_antes_de_descubrir(self):
        avisos, eventos, p = self._correr()
        self.assertEqual(eventos[0], "abre")
        self.assertTrue(eventos[1].startswith("render:empleos"))
        self.assertEqual(len(avisos), 1)
        self.assertEqual(p.errores, [])

    def test_el_navegador_siempre_se_cierra(self):
        _, eventos, _ = self._correr()
        self.assertEqual(eventos[-1], "cierra")


class TestConfiguracionFuentes(unittest.TestCase):

    def test_todos_los_portales_tienen_nota_y_patron(self):
        for f in portales_peru() + fuentes_por_verificar():
            with self.subTest(portal=f.nombre):
                self.assertTrue(f.nota, "cada fuente debe documentar su estado")
                self.assertTrue(f.sitemaps or f.listados or f.patron_aviso)

    def test_no_hay_fuentes_con_el_mismo_nombre(self):
        from motor.fuentes import fuentes_de_arranque
        nombres = [f.nombre for f in fuentes_de_arranque()]
        self.assertEqual(len(nombres), len(set(nombres)), nombres)

    def test_las_sin_verificar_estan_marcadas(self):
        for f in fuentes_por_verificar():
            with self.subTest(portal=f.nombre):
                self.assertIn("SIN VERIFICAR", f.nota)

    def test_las_spa_quedan_inactivas_sin_playwright(self):
        from motor.fuentes.render import HAY_PLAYWRIGHT
        for f in portales_peru():
            if f.necesita_render and not HAY_PLAYWRIGHT:
                self.assertFalse(f.activa, f"{f.nombre} debería estar inactiva")

    def test_computrabajo_esta_marcado_como_no_permitido(self):
        ct = next(f for f in portales_peru() if f.nombre == "Computrabajo")
        self.assertIn("permiso", ct.nota.lower())


class TestErroresVisibles(unittest.TestCase):
    """
    Una fuente que devuelve cero avisos tiene que decir por qué.
    Fallar en silencio es peor que fallar.
    """

    def _portal(self, **kw) -> PortalWeb:
        p = PortalWeb("Falsa", "https://ejemplo.pe",
                      sitemaps=("https://ejemplo.pe/sitemap.xml",), **kw)
        p._bajar_bytes = lambda url: SITEMAP_AVISOS.encode()   # sin red
        return p

    def test_avisa_si_el_patron_no_coincide(self):
        p = self._portal(patron_aviso=r"/esto-no-existe/")
        self.assertEqual(p.urls_de_avisos(10), [])
        self.assertTrue(any("patrón" in e for e in p.errores), p.errores)

    def test_avisa_si_todo_esta_fuera_de_la_ventana(self):
        solo_viejos = f"""<?xml version="1.0" encoding="utf-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
          <url><loc>https://ejemplo.pe/empleos/a.html</loc><lastmod>{VIEJO}</lastmod></url>
          <url><loc>https://ejemplo.pe/empleos/b.html</loc><lastmod>{VIEJO}</lastmod></url>
        </urlset>"""
        p = self._portal(patron_aviso=r"/empleos/", dias_ventana=30)
        p._bajar_bytes = lambda url: solo_viejos.encode()
        self.assertEqual(p.urls_de_avisos(10), [])
        self.assertTrue(any("últimos" in e for e in p.errores), p.errores)

    def test_limpia_las_urls_del_listado(self):
        """
        Los sitios modernos incrustan JSON en el HTML con las comillas
        escapadas. Sin limpiar, cada enlace arrastra una barra invertida y
        devuelve 404.
        """
        from motor.fuentes.portal_web import _limpiar_enlace
        casos = {
            r"/convocatorias/abogado-797491\\": "https://ejemplo.pe/convocatorias/abogado-797491",
            "/convocatorias/abogado-797491": "https://ejemplo.pe/convocatorias/abogado-797491",
            r"https:\/\/ejemplo.pe\/convocatorias\/x": "https://ejemplo.pe/convocatorias/x",
            "/buscar?q=a&amp;p=2": "https://ejemplo.pe/buscar?q=a&p=2",
            '/convocatorias/x",': "https://ejemplo.pe/convocatorias/x",
        }
        for bruto, esperado in casos.items():
            with self.subTest(bruto=bruto):
                self.assertEqual(_limpiar_enlace(bruto, "https://ejemplo.pe"), esperado)

    def test_un_enlace_escapado_no_rompe_la_recoleccion(self):
        from motor.fuentes.portal_web import PortalWeb
        p = PortalWeb("Falsa", "https://ejemplo.pe",
                      listados=("https://ejemplo.pe/",),
                      patron_aviso=r"/convocatorias/[^\"'\s]+")
        p._bajar_html = lambda url: r'{"url":"\/convocatorias\/abogado-797491"}'
        urls = p.urls_de_avisos(5)
        self.assertTrue(urls)
        self.assertFalse(any("\\" in u for u in urls), urls)

    def test_el_listado_manda_sobre_el_sitemap(self):
        """
        El listado del portal trae lo abierto; el sitemap, todo su archivo.
        Si se empieza por el sitemap, se recolectan convocatorias cerradas.
        """
        listado = ('<a href="/convocatorias/nueva-cas-2026-08-999001">Nueva</a>'
                   '<a href="/convocatorias/nueva-cas-2026-08-999002">Otra</a>')
        archivo = """<?xml version="1.0"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
          <url><loc>https://ejemplo.pe/convocatorias/vieja-cas-2025-01-100001</loc></url>
        </urlset>"""

        p = PortalWeb("Falsa", "https://ejemplo.pe",
                      listados=("https://ejemplo.pe/",),
                      sitemaps=("https://ejemplo.pe/sitemap.xml",),
                      patron_aviso=r"/convocatorias/[^\"'\s]+")
        p._bajar_bytes = lambda url, max_bytes=0: archivo.encode()
        p._bajar_html = lambda url: listado

        urls = p.urls_de_avisos(10)
        self.assertIn("999001", urls[0])
        self.assertIn("999002", urls[1])
        # El sitemap completa, no reemplaza.
        self.assertTrue(any("100001" in u for u in urls))

    def test_cuando_si_encuentra_no_anota_errores(self):
        p = self._portal(patron_aviso=r"/empleos/")
        self.assertTrue(p.urls_de_avisos(10))
        self.assertEqual(p.errores, [])

    def test_el_lastmod_del_sitemap_no_filtra_cuando_hay_correlativo(self):
        """
        El lastmod dice cuándo el portal tocó la página, no cuándo se publicó
        el aviso. Filtrar el descubrimiento con esa fecha dejaba la corrida en
        cero: 1475 URLs y ninguna "reciente".
        """
        viejo_lastmod = f"""<?xml version="1.0" encoding="utf-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
          <url><loc>https://ejemplo.pe/convocatorias/a-cas-2026-07-797999</loc>
               <lastmod>{VIEJO}</lastmod></url>
          <url><loc>https://ejemplo.pe/convocatorias/b-cas-2026-07-797998</loc>
               <lastmod>{VIEJO}</lastmod></url>
        </urlset>"""
        p = self._portal(patron_aviso=r"/convocatorias/", ordenar_por_id=True,
                         dias_ventana=2)
        p._bajar_bytes = lambda url: viejo_lastmod.encode()
        self.assertEqual(len(p.urls_de_avisos(10)), 2)
        self.assertEqual(p.errores, [])

    def test_las_dos_ventanas_son_independientes(self):
        p = PortalWeb("Falsa", "https://ejemplo.pe", dias_ventana=120, dias_publicado=2)
        self.assertEqual(p.dias_ventana, 120)
        self.assertEqual(p.dias_publicado, 2)

    def test_por_defecto_la_antiguedad_es_la_del_filtro(self):
        from motor.score import MAX_DIAS_ANTIGUEDAD
        p = PortalWeb("Falsa", "https://ejemplo.pe")
        self.assertEqual(p.dias_publicado, MAX_DIAS_ANTIGUEDAD)

    def test_ordena_por_correlativo_cuando_no_hay_fechas(self):
        """
        Si el sitemap no trae lastmod, el número final de la URL hace de fecha:
        el correlativo más alto es el aviso más nuevo.
        """
        sin_fechas = """<?xml version="1.0" encoding="utf-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
          <url><loc>https://ejemplo.pe/convocatorias/viejo-cas-2026-01-100200</loc></url>
          <url><loc>https://ejemplo.pe/convocatorias/nuevo-cas-2026-07-797999</loc></url>
          <url><loc>https://ejemplo.pe/convocatorias/medio-cas-2026-05-400500</loc></url>
        </urlset>"""
        p = PortalWeb("Falsa", "https://ejemplo.pe",
                      sitemaps=("https://ejemplo.pe/sitemap.xml",),
                      patron_aviso=r"/convocatorias/", ordenar_por_id=True)
        p._bajar_bytes = lambda url: sin_fechas.encode()
        urls = p.urls_de_avisos(10)
        self.assertIn("797999", urls[0])
        self.assertIn("100200", urls[-1])

    def test_agrupa_el_mismo_fallo_repetido(self):
        """60 URLs con el mismo problema son una línea, no sesenta."""
        p = self._portal(patron_aviso=r"/empleos/")
        for i in range(60):
            p._anotar(f"falló https://ejemplo.pe/aviso-{i} (timeout)")
        self.assertEqual(len(p.errores), 1)
        self.assertIn("se repitió 60 veces", p.errores[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
