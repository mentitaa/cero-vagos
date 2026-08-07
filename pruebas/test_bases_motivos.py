"""
Por qué no se llegó a las funciones: los tres fracasos, separados.

Esto existe por un número que no se pudo repartir. La primera corrida de
Convocatorias CAS (6/8/2026) dejó **48 avisos sin funciones**, y como los tres
motivos salían con el mismo texto, no había forma de saber cuál mandaba:

  · ¿las entidades nos bloquean?
  · ¿sus servidores no contestan desde los servidores de GitHub?
  · ¿los avisos simplemente no enlazan bases?

Cada una lleva a una decisión distinta, y sin el reparto no se puede elegir.
Ahora cada motivo sale con su propio texto, así que el registro los cuenta por
separado.

La distinción que más importa es entre «no contestó» y «contestó que no». Las
dos terminan igual —no se baja el PDF, porque la regla 6 dice que sin
robots.txt legible se asume que no hay permiso— pero significan cosas
opuestas. Un «no contestó» repetido en decenas de entidades apunta a un
problema de red nuestro; un «contestó que no» es el Estado cerrando la puerta.
"""
from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from motor import bases_pdf
from motor.fuentes.base import ErrorFuente
from motor.fuentes.publicas import _por_que_no, enriquecer_con_bases
from motor.modelos import OfertaCruda

PDF = "https://munisurquillo.gob.pe/cas/UPLOADS/BASES.PDF"

AVISO = f"""
<p>Convocatoria CAS de la Municipalidad de Surquillo.</p>
<p>Requisitos</p>
<ul><li>Secundaria completa</li><li>Un año de experiencia</li></ul>
<p><a href="{PDF}">Ver aquí Bases (convocatoria completa y cronograma)</a></p>
"""

SIN_PDF = """
<p>Convocatoria CAS de la Municipalidad de Surquillo.</p>
<p>Requisitos</p>
<ul><li>Secundaria completa</li><li>Un año de experiencia</li></ul>
"""


def cruda(html: str = AVISO) -> OfertaCruda:
    return OfertaCruda(
        fuente="Convocatorias CAS",
        url="https://www.convocatoriascas.com/proceso-de-seleccion-CAS-x-1-plazas-1.html",
        puesto="Ayudante de poda",
        empresa="MUNICIPALIDAD SURQUILLO",
        descripcion_html=html,
    )


class CachePropio(unittest.TestCase):
    """
    Los PDF descargados se guardan en `datos/pdfs/` para no volver a bajarlos.
    Sin desviar esa carpeta, dos cosas malas pasan a la vez: los tests escriben
    en el caché de verdad, y el PDF que deja un test se lo encuentra el
    siguiente, que entonces ni llama a la descarga y comprueba otra cosa
    distinta de la que dice comprobar. Pasó al escribir este archivo.
    """

    def setUp(self):
        self._real = bases_pdf.CACHE
        self._tmp = Path(tempfile.mkdtemp())
        bases_pdf.CACHE = self._tmp

    def tearDown(self):
        bases_pdf.CACHE = self._real
        shutil.rmtree(self._tmp, ignore_errors=True)


class PruebaClasificacion(unittest.TestCase):

    def test_un_servidor_que_no_contesta_es_sin_respuesta(self):
        e = ErrorFuente(
            "No se pidió https://munisurquillo.gob.pe/x.pdf\n"
            "      motivo: No se pudo leer robots.txt (ConnectTimeoutError)"
        )
        self.assertEqual(_por_que_no(e), "sin_respuesta")

    def test_un_disallow_explicito_es_sin_permiso(self):
        e = ErrorFuente(
            "No se pidió https://x.gob.pe/y.pdf\n"
            "      motivo: robots.txt no lo permite"
        )
        self.assertEqual(_por_que_no(e), "sin_permiso")

    def test_un_waf_que_devuelve_vacio_es_sin_permiso(self):
        """El servidor sí contestó; contestó de forma defensiva."""
        e = ErrorFuente(
            "No se pidió https://x.gob.pe/y.pdf\n"
            "      motivo: robots.txt vacío o bloqueado (típico de WAF/Cloudflare)"
        )
        self.assertEqual(_por_que_no(e), "sin_permiso")


class PruebaMensajes(CachePropio):
    """
    Cada motivo tiene que salir con un texto distinto. Si dos comparten texto,
    el registro los suma en una sola línea y se pierde el reparto — que es
    justo el problema que esto vino a arreglar.
    """

    def _aviso(self, bajar, html: str = AVISO) -> str:
        return enriquecer_con_bases(cruda(html), html, bajar)

    def test_servidor_que_no_contesta(self):
        def bajar(url, _max=0):
            raise ErrorFuente(f"No se pidió {url}\n motivo: No se pudo leer "
                              f"robots.txt (ConnectTimeoutError)")
        aviso = self._aviso(bajar)
        self.assertIn("no contestó", aviso)
        self.assertIn("regla 6", aviso)
        self.assertIn(PDF, aviso, "el aviso tiene que traer un ejemplo")

    def test_entidad_que_dice_que_no(self):
        def bajar(url, _max=0):
            raise ErrorFuente(f"No se pidió {url}\n motivo: robots.txt no lo permite")
        aviso = self._aviso(bajar)
        self.assertIn("contestó que no", aviso)

    def test_pdf_escaneado(self):
        """
        Una foto del documento. No hay texto que leer, así que no es culpa del
        buscador de encabezados. El 6/8/2026 este resultó ser el caso más común.

        El aviso además tiene que decir si ya se intentó leer la imagen o si
        falta instalar la herramienta: son dos diagnósticos distintos y llevan
        a cosas distintas.
        """
        from motor.bases_pdf import hay_ocr

        def bajar(_url, _max=0):
            return b"%PDF-1.4 una foto, sin capa de texto"
        aviso = self._aviso(bajar)
        self.assertIn("escaneado", aviso)
        self.assertIn("leyendo la imagen" if hay_ocr() else "tesseract", aviso)

    def test_pdf_con_texto_pero_sin_encabezado_reconocido(self):
        """
        Este sí es nuestro: el PDF trae texto y no supimos dónde empieza la
        lista. Se arregla mirando el PDF y agregando el encabezado que usa.
        """
        largo = ("BASES DEL CONCURSO CAS N° 006-2026\n"
                 "TAREAS ENCOMENDADAS AL SERVIDOR\n"
                 + "a) Redactar informes tecnicos del area correspondiente.\n" * 30)
        self.assertGreaterEqual(len(largo), 200)

        original = bases_pdf.texto_de_pdf
        bases_pdf.texto_de_pdf = lambda *_a, **_k: largo
        try:
            aviso = self._aviso(lambda _u, _m=0: b"%PDF-1.4 con texto")
        finally:
            bases_pdf.texto_de_pdf = original

        self.assertIn("no se reconoció dónde empieza", aviso)

    def test_aviso_que_no_enlaza_ningun_pdf(self):
        def bajar(_url, _max=0):
            raise AssertionError("no debería descargarse nada")
        aviso = self._aviso(bajar, SIN_PDF)
        self.assertIn("no enlaza ningún PDF", aviso)

    def test_los_cinco_mensajes_son_distintos(self):
        def sin_respuesta(url, _max=0):
            raise ErrorFuente(f"No se pidió {url}\n motivo: No se pudo leer robots.txt (x)")

        def sin_permiso(url, _max=0):
            raise ErrorFuente(f"No se pidió {url}\n motivo: robots.txt no lo permite")

        def escaneado(_url, _max=0):
            return b"%PDF-1.4 una foto"

        def nunca(_url, _max=0):
            raise AssertionError

        avisos = [
            self._aviso(sin_respuesta),
            self._aviso(sin_permiso),
            self._aviso(escaneado),
            self._aviso(nunca, SIN_PDF),
        ]

        largo = "BASES\n" + "a) Redactar informes del area.\n" * 30
        original = bases_pdf.texto_de_pdf
        bases_pdf.texto_de_pdf = lambda *_a, **_k: largo
        try:
            avisos.append(self._aviso(lambda _u, _m=0: b"%PDF-1.4 con texto"))
        finally:
            bases_pdf.texto_de_pdf = original

        self.assertEqual(len(set(avisos)), 5, "dos motivos comparten texto")


class PruebaNoRompeLoQueYaFuncionaba(CachePropio):

    def test_si_la_pagina_ya_trae_funciones_no_se_baja_nada(self):
        html = ("<p>Funciones</p><ul>"
                "<li>Realizar la poda de árboles del distrito</li>"
                "<li>Recoger los residuos vegetales generados</li>"
                "<li>Apoyar en el mantenimiento de las áreas verdes</li></ul>")

        def nunca(_url, _max=0):
            raise AssertionError("no había que abrir ningún PDF")

        self.assertEqual(enriquecer_con_bases(cruda(html), html, nunca), "")

    def test_un_error_de_descarga_no_tumba_el_aviso(self):
        """
        El aviso se sigue publicando si alcanza sin funciones. Que no se pueda
        leer el PDF es una incidencia, no una excepción que se escape y corte
        la corrida.
        """
        def bajar(url, _max=0):
            raise ErrorFuente(f"No se pidió {url}\n motivo: No se pudo leer robots.txt (x)")

        c = cruda()
        aviso = enriquecer_con_bases(c, AVISO, bajar)
        self.assertTrue(aviso)
        self.assertNotIn("funciones_desde_pdf", c.extra)


class PruebaLasFuncionesLleganEnteras(CachePropio):
    """
    Sacar las funciones del PDF no sirve de nada si después no se reconocen.

    El fallo, encontrado el 6/8/2026 probando el motor completo: la sección se
    pegaba al final del aviso sin salto de línea, así que al normalizar el
    texto la última línea de antes y la palabra "Funciones" quedaban juntas:

        Ver aquí Bases Funciones

    El encabezado dejaba de reconocerse y las funciones terminaban contadas
    como requisitos. El aviso pasaba de tener funciones a no tenerlas **sin que
    nada fallara a la vista**: ni un error, ni una incidencia. Solo un score
    más bajo y un aviso que no se publica.
    """

    # El cuerpo termina en un enlace, que es lo que rompía el caso.
    CUERPO = ('<p>Requisitos</p><ul>'
              '<li>Título profesional de Contador Público colegiado</li>'
              '<li>Experiencia general: dos años en el sector público</li>'
              '<li>Experiencia específica: un año en el cargo o afines</li></ul>'
              '<a href="https://x.gob.pe/bases.pdf">Ver aquí Bases</a>')

    BUENAS = ("Principales funciones a desarrollar:\n"
              "a) Contabilizar las operaciones economicas de la entidad.\n"
              "b) Formular los estados financieros mensuales del pliego.\n"
              "c) Revisar y conciliar los anexos del balance de comprobacion.\n")

    def _con_funciones(self):
        from motor import bases_pdf
        from motor.modelos import OfertaCruda

        c = OfertaCruda(fuente="Convocatorias CAS", url="https://x.com/a-1-plazas-1.html",
                        puesto="Contador", empresa="UGEL", descripcion_html=self.CUERPO)
        real = bases_pdf.texto_de_pdf
        bases_pdf.texto_de_pdf = lambda *_a, **_k: self.BUENAS
        try:
            enriquecer_con_bases(c, self.CUERPO, lambda _u, _m=0: b"%PDF-1.4 x")
        finally:
            bases_pdf.texto_de_pdf = real
        return c

    def test_las_funciones_se_reconocen_como_funciones(self):
        from motor.normalizar import extraer_bloques

        bloques = extraer_bloques(self._con_funciones().cuerpo())
        self.assertGreaterEqual(len(bloques["funciones"]), 3)

    def test_no_terminan_contadas_como_requisitos(self):
        from motor.normalizar import extraer_bloques

        requisitos = " ".join(extraer_bloques(self._con_funciones().cuerpo())["requisitos"])
        self.assertNotIn("contabilizar", requisitos.lower(),
                         "una función se coló entre los requisitos")

    def test_la_oferta_terminada_las_muestra(self):
        from motor.pipeline import procesar_cruda

        oferta = procesar_cruda(self._con_funciones())
        self.assertGreaterEqual(len(oferta.funciones), 3)


if __name__ == "__main__":
    unittest.main()
