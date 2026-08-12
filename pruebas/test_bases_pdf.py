"""
Pruebas del lector de bases en PDF.

La extracción del texto depende de librerías externas, así que se prueba por
separado la parte que sí controlamos: encontrar la sección de funciones dentro
del texto y convertirla en ítems limpios.

Los textos de ejemplo imitan cómo redactan las bases las entidades peruanas.
"""
from __future__ import annotations

import sys
import unittest

from pruebas.plazos import abierto
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from motor.bases_pdf import (                          # noqa: E402
    enlaces_pdf, extraer_funciones, texto_de_pdf,
)

BASES_MUNICIPALIDAD = """
MUNICIPALIDAD DISTRITAL DE SAN JERÓNIMO
PROCESO CAS N° 004-2026

I. GENERALIDADES
1.1 Objeto de la convocatoria
Contratar los servicios de un Abogado para la DEMUNA.

II. PERFIL DEL PUESTO
Título profesional de abogado, colegiado y habilitado.

III. FUNCIONES DEL PUESTO
a) Brindar atención legal a los usuarios de la Defensoría Municipal del Niño y
   del Adolescente del distrito.
b) Elaborar y tramitar las actas de conciliación extrajudicial en materia
   familiar, conforme a la normativa vigente.
c) Coordinar con la Policía Nacional del Perú y el Ministerio Público los casos
   de riesgo o desprotección familiar.
d) Realizar el seguimiento de los expedientes derivados a la instancia judicial.
e) Otras funciones que le asigne la Gerencia de Desarrollo Social.

IV. CONDICIONES ESENCIALES DEL CONTRATO
Lugar de prestación del servicio: Municipalidad Distrital de San Jerónimo.
Remuneración mensual: S/ 3,300.00 (Tres mil trescientos con 00/100 soles).
"""

BASES_HOSPITAL = """
GOBIERNO REGIONAL DE HUANCAVELICA
BASES DEL CONCURSO CAS N° 012-2026

FUNCIONES ESPECÍFICAS:
1. Realizar la atención integral de enfermería a los pacientes hospitalizados
   del servicio de medicina.
2. Administrar los medicamentos según la indicación médica registrada.
3. Registrar en la historia clínica la evolución del paciente por turno.
4. Participar en las actividades de prevención y promoción de la salud.

REQUISITOS MÍNIMOS
Título de licenciada en enfermería con colegiatura vigente.
"""

BASES_SIN_FUNCIONES = """
PROCESO DE SELECCIÓN CAS N° 087-2026
I. OBJETO
Contratar un técnico administrativo.
II. REQUISITOS
Título técnico, un año de experiencia.
III. CRONOGRAMA
Publicación: del 10 al 24 de julio.
"""

PAGINA_CON_PDFS = """
<a href="/repositoriopsep/14419_Cronograma.pdf">Cronograma del Concurso</a>
<a href="/repositoriopsep/14419_BasesConcurso.pdf">Base del Concurso</a>
<a href="/repositoriopsep/14419_AnuncioConvocatoria.pdf">Detalles del Proceso de Selección</a>
<a href="/repositoriopsep/14419_Anexo1.pdf">Anexo I - Declaración jurada</a>
"""


class TestExtraerFunciones(unittest.TestCase):

    def test_bases_con_numeracion_romana_y_letras(self):
        funciones = extraer_funciones(BASES_MUNICIPALIDAD)
        self.assertEqual(len(funciones), 5)
        self.assertTrue(funciones[0].startswith("Brindar atención legal"))
        # Las líneas partidas por el ancho de página se unen.
        self.assertIn("del Adolescente del distrito", funciones[0])

    def test_no_se_pasa_a_la_siguiente_seccion(self):
        funciones = extraer_funciones(BASES_MUNICIPALIDAD)
        todo = " ".join(funciones)
        self.assertNotIn("Remuneración mensual", todo)
        self.assertNotIn("Lugar de prestación", todo)
        self.assertNotIn("colegiado y habilitado", todo)

    def test_encabezado_con_dos_puntos_y_numeros(self):
        funciones = extraer_funciones(BASES_HOSPITAL)
        self.assertEqual(len(funciones), 4)
        self.assertTrue(funciones[1].startswith("Administrar los medicamentos"))
        self.assertNotIn("Título de licenciada", " ".join(funciones))

    def test_sin_seccion_de_funciones_devuelve_vacio(self):
        self.assertEqual(extraer_funciones(BASES_SIN_FUNCIONES), [])

    def test_texto_vacio(self):
        self.assertEqual(extraer_funciones(""), [])
        self.assertEqual(extraer_funciones("   \n  \n"), [])

    def test_nunca_inventa(self):
        """Si el PDF es ilegible (escaneado), no hay funciones. Punto."""
        self.assertEqual(extraer_funciones("ÿØÿà JFIF basura binaria"), [])


class TestTextoDePdf(unittest.TestCase):

    def test_datos_que_no_son_pdf(self):
        self.assertEqual(texto_de_pdf(b"esto no es un pdf"), "")
        self.assertEqual(texto_de_pdf(b""), "")

    def test_pdf_de_verdad(self):
        """Sobre un PDF real, con el mismo formato que usan las municipalidades."""
        from motor.bases_pdf import backends_disponibles
        if not backends_disponibles():
            self.skipTest("no hay con qué leer PDFs (pip install pdfplumber)")

        datos = (Path(__file__).parent / "muestras" / "bases_ejemplo.pdf").read_bytes()
        texto = texto_de_pdf(datos)
        self.assertIn("FUNCIONES DEL PUESTO", texto)

        funciones = extraer_funciones(texto)
        self.assertEqual(len(funciones), 5)
        self.assertTrue(funciones[0].startswith("Brindar atencion legal"))
        # Las líneas partidas por el ancho de la hoja se reconstruyen.
        self.assertIn("Adolescente del distrito", funciones[0])
        # Y no se cuela la sección siguiente.
        self.assertNotIn("Remuneracion mensual", " ".join(funciones))


class TestCicloCompleto(unittest.TestCase):
    """
    La cadena entera sin red: ficha sin funciones + PDF de bases -> oferta
    aprobada. Esto es lo que ningún portal peruano hace.
    """

    def test_el_pdf_rescata_una_oferta_que_seria_rechazada(self):
        from motor.bases_pdf import backends_disponibles
        if not backends_disponibles():
            self.skipTest("no hay con qué leer PDFs")

        from motor.fuentes.publicas import enriquecer_con_bases, parsear_convocatoria
        from motor.pipeline import procesar_cruda

        muestras = Path(__file__).parent / "muestras"
        html = abierto((muestras / "convocatoria_publica.html").read_text(encoding="utf-8"))
        pdf = (muestras / "bases_ejemplo.pdf").read_bytes()

        # Se le quitan las funciones a la ficha: queda como las reales.
        sin_funciones = html.split("<h2>Funciones</h2>")[0] + """
            <h2>Documentos oficiales</h2>
            <ul><li><a href="https://munisanjeronimo.gob.pe/bases/14419_BasesConcurso.pdf">Base del Concurso</a></li></ul>
            </main></body></html>"""

        url = "https://www.convocape.com/convocatorias/abogado-de-demuna-cas-2026-07-797413"
        cruda = parsear_convocatoria(sin_funciones, url, "Estado")

        antes = procesar_cruda(cruda)
        self.assertFalse(antes.aprobada)
        self.assertEqual(len(antes.funciones), 0)

        aviso = enriquecer_con_bases(cruda, sin_funciones, lambda u, max_bytes=0: pdf)
        self.assertEqual(aviso, "")
        self.assertIn("BasesConcurso", cruda.extra["funciones_desde_pdf"])

        despues = procesar_cruda(cruda)
        self.assertTrue(despues.aprobada, despues.motivos_rechazo)
        self.assertGreaterEqual(len(despues.funciones), 3)
        self.assertGreater(despues.score, antes.score)

    def test_sigue_el_enlace_al_anuncio_oficial(self):
        """
        Caso más común: el agregador no enlaza el PDF, solo la página de la
        entidad. Hay que dar un salto más para llegar a las bases.
        """
        from motor.bases_pdf import backends_disponibles
        if not backends_disponibles():
            self.skipTest("no hay con qué leer PDFs")

        from motor.fuentes.publicas import enriquecer_con_bases, parsear_convocatoria
        from motor.pipeline import procesar_cruda

        muestras = Path(__file__).parent / "muestras"
        html = abierto((muestras / "convocatoria_publica.html").read_text(encoding="utf-8"))
        pdf = (muestras / "bases_ejemplo.pdf").read_bytes()

        aviso = html.split("<h2>Funciones</h2>")[0] + """
            <a href="https://www.munisanjeronimocusco.gob.pe/trabaja-con-nosotros/">Ver anuncio oficial</a>
            </main></body></html>"""

        pagina_entidad = """<html><body>
            <a href="/docs/14419_BasesConcurso.pdf">Bases del concurso CAS 004-2026</a>
            </body></html>"""

        def bajar(url, max_bytes=0):
            return pdf if url.endswith(".pdf") else pagina_entidad.encode()

        cruda = parsear_convocatoria(aviso, "https://www.convocape.com/convocatorias/x-cas-1", "Estado")
        self.assertEqual(enriquecer_con_bases(cruda, aviso, bajar), "")
        self.assertIn("munisanjeronimocusco", cruda.extra["via_anuncio_oficial"])
        self.assertTrue(procesar_cruda(cruda).aprobada)

    def test_ignora_redes_sociales_al_buscar_el_anuncio(self):
        from motor.fuentes.publicas import enlaces_oficiales
        html = """
            <a href="https://www.facebook.com/algo">Síguenos</a>
            <a href="https://wa.me/51999">WhatsApp</a>
            <a href="https://www.munisanjeronimo.gob.pe/convocatorias">Ver anuncio oficial</a>
        """
        urls = enlaces_oficiales(html, "www.convocape.com")
        self.assertEqual(len(urls), 1)
        self.assertIn("gob.pe", urls[0])

    def test_si_no_hay_pdf_no_pasa_nada(self):
        from motor.fuentes.publicas import enriquecer_con_bases, parsear_convocatoria
        html = abierto((Path(__file__).parent / "muestras" / "convocatoria_publica.html").read_text(encoding="utf-8"))
        cruda = parsear_convocatoria(html, "https://x.pe/c/1", "Estado")
        self.assertEqual(enriquecer_con_bases(cruda, "<p>sin enlaces</p>", lambda u, **k: b""), "")
        self.assertNotIn("funciones_desde_pdf", cruda.extra)


class TestEnlacesPdf(unittest.TestCase):

    def test_prioriza_las_bases_del_concurso(self):
        urls = enlaces_pdf(PAGINA_CON_PDFS, base="https://aplicativo.pj.gob.pe")
        self.assertIn("BasesConcurso", urls[0])

    def test_manda_al_final_cronogramas_y_anexos(self):
        urls = enlaces_pdf(PAGINA_CON_PDFS, base="https://aplicativo.pj.gob.pe")
        self.assertIn("Cronograma", urls[-1] + urls[-2])
        self.assertIn("Anexo", urls[-1] + urls[-2])

    def test_completa_urls_relativas(self):
        urls = enlaces_pdf(PAGINA_CON_PDFS, base="https://aplicativo.pj.gob.pe")
        self.assertTrue(all(u.startswith("https://aplicativo.pj.gob.pe/") for u in urls))

    def test_pagina_sin_pdfs(self):
        self.assertEqual(enlaces_pdf("<p>nada</p>"), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
