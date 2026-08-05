"""
Pruebas del lector de convocatorias del Estado, contra una muestra real
guardada en pruebas/muestras/.

Si un portal cambia su maquetado, estos tests son los que avisan.
"""
from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from motor.fuentes.publicas import (                    # noqa: E402
    BENEFICIOS_POR_REGIMEN, _fecha_es, _regimen, parsear_convocatoria,
)
from motor.normalizar import extraer_bloques            # noqa: E402
from motor.pipeline import procesar_cruda               # noqa: E402

MUESTRA = (RAIZ / "pruebas" / "muestras" / "convocatoria_publica.html").read_text(encoding="utf-8")
URL = "https://www.convocape.com/convocatorias/abogado-de-demuna-cas-2026-07-797413"


class TestFechaEspanol(unittest.TestCase):

    def test_formato_largo(self):
        self.assertEqual(_fecha_es("21 de julio de 2026"), date(2026, 7, 21))
        self.assertEqual(_fecha_es("1 de setiembre de 2026"), date(2026, 9, 1))

    def test_formato_corto(self):
        self.assertEqual(_fecha_es("10 ago. 2026"), date(2026, 8, 10))

    def test_basura(self):
        self.assertIsNone(_fecha_es("próximamente"))
        self.assertIsNone(_fecha_es(""))


class TestRegimen(unittest.TestCase):

    def test_detecta(self):
        self.assertEqual(_regimen("CAS"), "CAS")
        self.assertEqual(_regimen("D.LEG 1057"), "CAS")
        self.assertEqual(_regimen("Régimen 728"), "728")
        self.assertEqual(_regimen("DL 276"), "276")
        self.assertEqual(_regimen("locación de servicios"), "")


class TestParseoDeLaFicha(unittest.TestCase):

    def setUp(self):
        self.cruda = parsear_convocatoria(MUESTRA, URL, "Convocatorias del Estado")
        self.assertIsNotNone(self.cruda)

    def test_datos_principales(self):
        c = self.cruda
        self.assertEqual(c.puesto, "Abogado De Demuna")
        self.assertIn("Municipalidad Distrital De San Jeronimo", c.empresa)
        self.assertIn("3,300", c.sueldo_texto)
        self.assertEqual(c.publicado, date(2026, 7, 21))
        self.assertEqual(c.extra["regimen"], "CAS")

    def test_agrega_los_beneficios_del_regimen(self):
        self.assertTrue(self.cruda.extra["beneficios_de_ley"])
        bloques = extraer_bloques(self.cruda.cuerpo())
        self.assertGreaterEqual(len(bloques["beneficios"]), 4)
        self.assertTrue(any("EsSalud" in b for b in bloques["beneficios"]))

    def test_no_cuenta_el_pie_de_pagina_como_funciones(self):
        """'Documentos necesarios' corta el aviso: lo de abajo no es contenido."""
        bloques = extraer_bloques(self.cruda.cuerpo())
        todo = " ".join(bloques["funciones"] + bloques["requisitos"] + bloques["beneficios"])
        self.assertNotIn("Guía para postular", todo)
        self.assertNotIn("Todos los derechos reservados", todo)
        self.assertNotIn("Curriculum vitae", todo)

    def test_la_convocatoria_completa_aprueba(self):
        o = procesar_cruda(self.cruda)
        self.assertTrue(o.aprobada, o.motivos_rechazo)
        self.assertEqual(o.sueldo_min, 3300)
        self.assertEqual(o.ciudad, "Cusco")
        self.assertEqual(o.categoria, "Legal")
        self.assertGreaterEqual(len(o.funciones), 3)
        self.assertGreaterEqual(len(o.requisitos), 3)
        self.assertGreaterEqual(len(o.beneficios), 2)

    def test_resumen_util(self):
        """El resumen sale de la meta descripción, no del menú del sitio."""
        o = procesar_cruda(self.cruda)
        self.assertIn("Abogado De Demuna", o.resumen)
        self.assertNotIn("Convocape", o.resumen)
        self.assertLess(len(o.resumen), 250)


class TestConvocatoriaSinFunciones(unittest.TestCase):
    """
    Muchas convocatorias no publican funciones (están en el PDF de las bases).
    Esas TIENEN que rechazarse: es exactamente lo que promete la marca.
    """

    def setUp(self):
        recortada = MUESTRA.replace(
            "<li>Brindar atención legal a los usuarios de la Demuna del distrito</li>", ""
        ).replace(
            "<li>Elaborar y tramitar las actas de conciliación extrajudicial en materia familiar</li>", ""
        ).replace(
            "<li>Coordinar con la Policía Nacional y el Ministerio Público los casos de riesgo</li>", ""
        ).replace(
            "<li>Realizar el seguimiento de los expedientes derivados a la instancia judicial</li>",
            "<li>Funciones no especificadas en la convocatoria</li>",
        )
        self.cruda = parsear_convocatoria(recortada, URL, "Convocatorias del Estado")

    def test_se_publica_aunque_no_liste_funciones(self):
        """
        Cambió el 4 de agosto de 2026. Antes se rechazaba; ahora al Estado no
        se le exige la lista, porque sus funciones viven en el PDF de las
        bases y el portal no lo enlaza. Lo demás sí se le exige igual.
        """
        o = procesar_cruda(self.cruda)
        self.assertNotIn("funciones", " ".join(o.motivos_rechazo).lower())
        self.assertGreater(o.sueldo_min, 0)      # el sueldo sí se leyó


class TestConvocatoriaDelPoderJudicial(unittest.TestCase):
    """
    Caso real que rompía el motor: requisitos en sub-secciones, una tabla de
    cronograma gigante, sin funciones y con el plazo ya cerrado.
    """

    def setUp(self):
        html = (RAIZ / "pruebas" / "muestras" / "convocatoria_sin_funciones.html").read_text(encoding="utf-8")
        self.cruda = parsear_convocatoria(html, URL, "Convocatorias del Estado")
        self.oferta = procesar_cruda(self.cruda)

    def test_lee_los_datos_de_cabecera(self):
        self.assertEqual(self.oferta.puesto, "Técnico En Diseño Gráfico")
        self.assertEqual(self.oferta.sueldo_min, 4000)
        self.assertEqual(self.oferta.ciudad, "Lima")

    def test_junta_los_requisitos_de_las_sub_secciones(self):
        self.assertGreaterEqual(len(self.oferta.requisitos), 4)
        self.assertTrue(any("Experiencia general" in q for q in self.oferta.requisitos))
        self.assertTrue(any("Título profesional" in q for q in self.oferta.requisitos))

    def test_el_cronograma_no_es_contenido(self):
        todo = " ".join(self.oferta.requisitos + self.oferta.funciones + self.oferta.beneficios)
        self.assertNotIn("Aprobación de la Convocatoria", todo)
        self.assertNotIn("Evaluación técnica", todo)
        self.assertNotIn("Base del Concurso", todo)
        self.assertNotIn("derechos reservados", todo)

    def test_detecta_que_el_plazo_cerro(self):
        self.assertEqual(self.cruda.extra["vence"], "2026-07-24")

    def test_se_rechaza_por_el_plazo_no_por_las_funciones(self):
        """
        Esta convocatoria cerró el 24/07. Se cae por eso, y ya no por no
        listar funciones: al Estado eso dejó de ser eliminatorio.
        """
        self.assertFalse(self.oferta.aprobada)
        motivos = " ".join(self.oferta.motivos_rechazo).lower()
        self.assertIn("plazo", motivos)
        self.assertNotIn("funciones", motivos)


class TestCatalogoDeBeneficios(unittest.TestCase):

    def test_los_tres_regimenes_estan_cubiertos(self):
        for regimen in ("CAS", "728", "276"):
            with self.subTest(regimen=regimen):
                self.assertGreaterEqual(len(BENEFICIOS_POR_REGIMEN[regimen]), 4)


if __name__ == "__main__":
    unittest.main(verbosity=2)
