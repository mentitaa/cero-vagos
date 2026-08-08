"""
Lo que Google Empleos lee de cada ficha.

Cada página de oferta lleva un bloque de datos en formato `JobPosting`. Es lo
que hace que la oferta pueda salir en el recuadro de trabajos que Google pone
arriba de los resultados — que es donde mira primero quien busca chamba, y vale
mucho más que aparecer en los resultados normales.

Search Console lo revisó el 7/8/2026: **50 ofertas válidas, 0 errores**. Y tres
avisos naranjas, los tres del mismo bloque de la dirección:

    Falta el campo "streetAddress"   (en "jobLocation.address")   50
    Falta el campo "addressRegion"   (en "jobLocation.address")   50
    Falta el campo "postalCode"      (en "jobLocation.address")   50

De los tres, **solo uno se podía llenar con datos de verdad**: el
departamento. El motor ya lo deducía y lo guardaba desde siempre; simplemente
no llegaba hasta acá.

Los otros dos se quedan vacíos a propósito y estas pruebas existen sobre todo
para eso: para que nadie los "arregle" más adelante inventándolos.
"""
from __future__ import annotations

import json
import unittest

from motor.sitio import jobposting

OFERTA = {
    "puesto": "Asistente Contable",
    "empresa": "Acme",
    "ciudad": "Cusco",
    "departamento": "Cusco",
    "modalidad": "Presencial",
    "huella": "ab12cd34",
    "min": 2500,
    "max": 2500,
    "resumen": "Llevar la contabilidad del área.",
    "funciones": ["Registrar comprobantes"],
    "requisitos": ["Bachiller en Contabilidad"],
    "beneficios": ["Planilla completa"],
}

URL = "https://cerovagos.com/oferta/asistente-contable-acme-ab12cd34/"


def direccion(oferta: dict) -> dict:
    return json.loads(jobposting(oferta, URL))["jobLocation"]["address"]


class PruebaLaDireccionQueLeeGoogle(unittest.TestCase):

    def test_va_el_departamento(self):
        """
        El arreglo del 7/8/2026. Sin esto, una oferta de Cusco no salía en
        "trabajos en Cusco" salvo que la persona nombrara el distrito exacto.
        Es lo que más ayuda a la oferta de provincia, que es casi toda la que
        aportan las convocatorias CAS.
        """
        self.assertEqual(direccion(OFERTA)["addressRegion"], "Cusco")

    def test_van_la_ciudad_y_el_pais(self):
        d = direccion(OFERTA)
        self.assertEqual(d["addressLocality"], "Cusco")
        self.assertEqual(d["addressCountry"], "PE")

    def test_la_calle_y_el_codigo_postal_NO_se_inventan(self):
        """
        Google los pide y Search Console los marca en naranja. Es un aviso, no
        un error, y así se queda.

        Los avisos de empleo peruanos no dicen la calle ni el código postal.
        Poner la dirección fiscal de la empresa, o el código postal del centro
        de la ciudad, mandaría a alguien a un sitio que no es — que es
        exactamente lo que prohíbe la regla 2: ante la duda, no se rellena.
        """
        d = direccion(OFERTA)
        self.assertNotIn("streetAddress", d)
        self.assertNotIn("postalCode", d)

    def test_sin_departamento_no_se_pone_uno_cualquiera(self):
        """
        Hoy las 63 ofertas publicadas tienen departamento, pero si alguna
        llegara sin él, el campo se omite. Nunca se cae a "Lima" por descarte:
        una oferta de provincia marcada como Lima es peor que una sin marcar.
        """
        sin_depa = dict(OFERTA, departamento="")
        self.assertNotIn("addressRegion", direccion(sin_depa))


class PruebaLoQueGoogleNecesitaSiempre(unittest.TestCase):
    """Los campos sin los cuales la oferta ni siquiera cuenta como válida."""

    def setUp(self):
        self.datos = json.loads(jobposting(OFERTA, URL))

    def test_es_un_jobposting(self):
        self.assertEqual(self.datos["@type"], "JobPosting")
        self.assertEqual(self.datos["@context"], "https://schema.org")

    def test_lleva_titulo_empresa_y_direccion_propia(self):
        self.assertEqual(self.datos["title"], "Asistente Contable")
        self.assertEqual(self.datos["hiringOrganization"]["name"], "Acme")
        self.assertEqual(self.datos["url"], URL)

    def test_el_sueldo_viaja_en_soles_y_por_mes(self):
        """
        Es el dato que distingue a Cero Vagos, y el formato importa: si el
        periodo no dijera MONTH, Google podría mostrar S/ 2,500 como si fuera
        el pago de un año.
        """
        pago = self.datos["baseSalary"]
        self.assertEqual(pago["currency"], "PEN")
        self.assertEqual(pago["value"]["unitText"], "MONTH")
        self.assertEqual(pago["value"]["minValue"], 2500)

    def test_las_tres_listas_llegan_a_la_descripcion(self):
        for titulo in ("Funciones", "Requisitos", "Beneficios"):
            self.assertIn(titulo, self.datos["description"])


if __name__ == "__main__":
    unittest.main()
