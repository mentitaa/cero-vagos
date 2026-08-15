"""
El lector de Trabajos Diarios.

La fuente trae los datos en el formato de Google (JSON-LD) y de ahí sale todo
bien —puesto, empresa, ciudad, sueldo, fecha de publicación y de cierre— menos
una cosa: **la descripción que ponen ahí es el resumen corto**, el que sale
recortado con "…" en los resultados de búsqueda.

Con eso el motor leía una sola línea y los avisos se caían todos por vacíos.
Los doce del sondeo salieron en 0 funciones / 0 requisitos / 0 beneficios, un
patrón demasiado parejo para venir de los avisos: si fuera culpa de ellos
habría variación.

El HTML de abajo es el del aviso real que lo destapó (Auxiliar de Almacén y
Despacho, Velax, S/ 1,200, 12/8/2026), recortado a lo que importa.
"""
from __future__ import annotations

import unittest

from motor.fuentes.trabajos_diarios import cuerpo_del_aviso, parsear
from motor.pipeline import procesar_cruda

URL = ("https://pe.trabajosdiarios.com/trabajo/3075258/"
       "auxiliar-de-almacen-y-despacho-en-lima")

# El resumen corto que la propia página publica en su JSON-LD: una frase, y
# encima cortada.
RESUMEN_CORTO = ("Empresa ferretera y logística busca auxiliar de almacén "
                 "y despacho con experiencia mínima de 3 meses, disponibilidad "
                 "inmediata y para laborar lunes a vi...")

PAGINA = """
<html><head>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "JobPosting",
  "title": "Auxiliar de Almac\\u00e9n y Despacho",
  "description": "%s",
  "datePosted": "2026-08-12",
  "validThrough": "2026-10-11",
  "hiringOrganization": {"@type": "Organization", "name": "Velax"},
  "jobLocation": {"@type": "Place", "address": {
      "@type": "PostalAddress", "addressLocality": "Lima",
      "addressRegion": "Lima", "addressCountry": "PE"}},
  "baseSalary": {"@type": "MonetaryAmount", "currency": "PEN",
      "value": {"@type": "QuantitativeValue", "value": 1200,
                "unitText": "MONTH"}}
}
</script>
</head><body>
  <h1>Auxiliar de Almac&oacute;n y Despacho</h1>
  <h2>Descripci&oacute;n del empleo</h2>
  <p>Hola !</p>
  <p>Importante empresa del rubro ferretero y logistico, desea incluir en su
     equipo de trabajo a :</p>
  <p>Auxiliar de almac&eacute;n y despacho</p>
  <p>Requisitos:</p>
  <ul>
    <li>Residir en zona sur, de preferencia en Villa El Salvador</li>
    <li>Disponibilidad inmediata</li>
    <li>Disponibilidad para laborar de Lunes a Viernes de 7am a 4:20pm</li>
    <li>Disponibilidad para realizar horas extras</li>
    <li>Trabajo en equipo y responsabilidad</li>
    <li>Experiencia de minimo 3 meses en almac&eacute;n</li>
  </ul>
  <p>Funciones:</p>
  <ul>
    <li>Recepcionar y verificar la mercaderia que ingresa al almacen</li>
    <li>Preparar y despachar los pedidos de los clientes</li>
    <li>Mantener el orden y el inventario del almacen</li>
  </ul>
  <p>Beneficios:</p>
  <ul>
    <li>Planilla Regimen General desde el 1er dia (contrato indeterminado)</li>
    <li>Desayuno y almuerzo cubierto por la empresa</li>
    <li>Beneficios acorde a ley (vacaciones, gratificacion, CTS, utilidades)</li>
  </ul>
  <h2>Resumen de empleo</h2>
  <p>Tipo de Contrato: Tiempo Completo</p>
  <h2>Acerca de la empresa</h2>
  <p>En VELAX tenemos m&aacute;s de 30 a&ntilde;os dedicados a la
     comercializaci&oacute;n de art&iacute;culos de iluminaci&oacute;n.</p>
</body></html>
""" % RESUMEN_CORTO


class PruebaElCuerpoDeVerdad(unittest.TestCase):

    def setUp(self):
        self.cuerpo = cuerpo_del_aviso(PAGINA)

    def test_encuentra_el_cuerpo_completo(self):
        self.assertIn("Residir en zona sur", self.cuerpo)
        self.assertIn("Planilla Regimen General", self.cuerpo)

    def test_corta_antes_de_lo_que_no_es_el_aviso(self):
        """
        La sección "Acerca de la empresa" es propaganda del empleador y está
        en TODOS sus avisos. Si entrara, el motor la contaría como parte de la
        oferta y hasta podría sacar de ahí un requisito inventado.
        """
        self.assertNotIn("30 a", self.cuerpo)
        self.assertNotIn("Tipo de Contrato", self.cuerpo)

    def test_aguanta_la_tilde_escrita_de_las_tres_formas(self):
        """
        "Descripción" aparece con tilde, sin tilde o con la tilde escapada
        (`&oacute;`) según cómo esté armada la página. Cortar por el título es
        más estable que cortar por el maquetado, pero solo si se reconocen las
        tres formas.
        """
        for variante in ("Descripción del empleo", "Descripcion del empleo",
                         "Descripci&oacute;n del empleo"):
            with self.subTest(variante=variante):
                html = f"<h2>{variante}</h2><p>Requisitos:</p><ul><li>Uno</li></ul>"
                self.assertIn("Uno", cuerpo_del_aviso(html))

    def test_si_no_encuentra_el_titulo_devuelve_vacio(self):
        self.assertEqual(cuerpo_del_aviso("<html><p>otra cosa</p></html>"), "")


class PruebaElAvisoCompletoPasaElFiltro(unittest.TestCase):
    """
    La prueba que importa: con el lector, este aviso se publica; sin él, se
    caía con 37/100.
    """

    def setUp(self):
        self.cruda = parsear(PAGINA, URL, "Trabajos Diarios")
        self.oferta = procesar_cruda(self.cruda)

    def test_lee_las_tres_listas(self):
        self.assertGreaterEqual(len(self.oferta.requisitos), 3)
        self.assertGreaterEqual(len(self.oferta.funciones), 3)
        self.assertGreaterEqual(len(self.oferta.beneficios), 2)

    def test_conserva_lo_que_el_json_ld_traia_bien(self):
        """
        El lector cambia SOLO la descripción. El sueldo, la moneda y las dos
        fechas ya venían correctos y no hay que volver a deducirlos — deducir
        el periodo de un sueldo es lo que produjo el aviso de S/ 33,800.
        """
        self.assertEqual(self.oferta.sueldo_min, 1200)
        self.assertEqual(self.oferta.moneda, "PEN")
        self.assertEqual(str(self.oferta.publicado), "2026-08-12")
        self.assertEqual(self.cruda.extra.get("vence"), "2026-10-11")

    def test_ahora_si_se_publica(self):
        self.assertTrue(self.oferta.aprobada,
                        f"seguiría rechazada: {self.oferta.motivos_rechazo}")


class PruebaSiLaPaginaCambia(unittest.TestCase):

    def test_sin_el_titulo_se_queda_con_el_resumen_corto(self):
        """
        Si un día le cambian los títulos a la página, el aviso tiene que
        quedarse con lo poco que traiga y **caerse por incompleto** — que es
        el error correcto y visible— en vez de quedarse sin descripción o,
        peor, publicarse a medias.
        """
        sin_titulo = PAGINA.replace("Descripci&oacute;n del empleo", "Detalle")
        cruda = parsear(sin_titulo, URL, "Trabajos Diarios")

        self.assertIsNotNone(cruda)
        self.assertIn("Empresa ferretera", cruda.descripcion_html)
        self.assertFalse(procesar_cruda(cruda).aprobada)

    def test_sin_datos_estructurados_no_inventa_nada(self):
        self.assertIsNone(parsear("<html><body>nada</body></html>", URL,
                                  "Trabajos Diarios"))


class PruebaEstaEnchufada(unittest.TestCase):

    def test_la_fuente_esta_en_la_lista_y_usa_su_lector(self):
        from motor.fuentes.portal_web import portales_peru
        from motor.fuentes.trabajos_diarios import parsear as suyo

        fuente = next((f for f in portales_peru()
                       if f.nombre == "Trabajos Diarios"), None)
        self.assertIsNotNone(fuente, "la fuente no quedó registrada")
        self.assertIs(fuente.parser, suyo,
                      "quedó con el lector genérico, que es el que fallaba")

    def test_no_necesita_navegador(self):
        """
        Comprobado: su HTML llega completo por HTTP simple. Marcarla con
        navegador costaría veinte veces más tiempo por aviso para nada.
        """
        from motor.fuentes.portal_web import portales_peru
        fuente = next(f for f in portales_peru() if f.nombre == "Trabajos Diarios")
        self.assertFalse(fuente.necesita_render)

    def test_el_patron_reconoce_sus_avisos(self):
        import re
        from motor.fuentes.portal_web import portales_peru
        fuente = next(f for f in portales_peru() if f.nombre == "Trabajos Diarios")

        self.assertTrue(re.search(fuente.patron_aviso, URL))
        # Y no confunde el menú con un aviso.
        for otra in ("/candidatos", "/empresas/publicar-trabajo-gratis",
                     "/ofertas-trabajo?page=2"):
            with self.subTest(otra=otra):
                self.assertFalse(re.search(fuente.patron_aviso, otra))


if __name__ == "__main__":
    unittest.main()
