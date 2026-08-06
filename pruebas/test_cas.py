"""
El lector de Convocatorias CAS (convocatoriascas.com).

Lo que estos tests cuidan, en orden de importancia:

  1. Que el sueldo publicado sea el que dice el aviso. Es el terreno donde
     nació el error de los S/ 33,800.
  2. Que solo entren las convocatorias de UNA plaza (decisión del 5/8/2026,
     opción 1) y que las de varias se cuenten en vez de desaparecer.
  3. Que nunca se invente un cargo (regla 8).
  4. Que una convocatoria con el plazo cerrado no llegue a la web.

Las muestras de `pruebas/muestras/cas_*.html` están copiadas de páginas reales
del sitio. Aun así, un test que pasa NO prueba que el sitio siga igual: para
eso está `python3 -m motor diagnostico`, que sí sale a la red.
"""
from __future__ import annotations

import unittest
from datetime import date, timedelta
from pathlib import Path

from motor.fuentes.cas import (
    ConvocatoriasCAS, campo, convocatorias_cas, fecha_cas, parsear_cas,
    plazas_en_url,
)
from motor.normalizar import html_a_lineas
from motor.pipeline import procesar_cruda

MUESTRAS = Path(__file__).parent / "muestras"

URL_UNA = ("https://www.convocatoriascas.com/proceso-de-seleccion-CAS-"
           "municipalidad-surquillo-agosto-2026-1-plazas-67463.html")
URL_VARIAS = ("https://www.convocatoriascas.com/proceso-de-seleccion-CAS-"
              "municipalidad-surquillo-agosto-2026-6-plazas-67476.html")


def muestra(nombre: str) -> str:
    return (MUESTRAS / nombre).read_text(encoding="utf-8")


def con_plazo(html: str, cuando: date) -> str:
    """Reescribe el plazo de la muestra para no depender de la fecha de hoy."""
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
             "agosto", "setiembre", "octubre", "noviembre", "diciembre"]
    nuevo = f"{cuando.day} de {meses[cuando.month - 1].capitalize()} del {cuando.year}"
    import re
    return re.sub(r"Plazo para postular: [^<]+", f"Plazo para postular: {nuevo}", html)


class PruebaPiezasSueltas(unittest.TestCase):

    def test_las_plazas_se_leen_de_la_direccion(self):
        self.assertEqual(plazas_en_url(URL_UNA), 1)
        self.assertEqual(plazas_en_url(URL_VARIAS), 6)
        self.assertEqual(plazas_en_url("https://www.convocatoriascas.com/"), 0)

    def test_fecha_con_de_y_con_del(self):
        self.assertEqual(fecha_cas("17 de Agosto del 2026"), date(2026, 8, 17))
        self.assertEqual(fecha_cas("3 de setiembre de 2026"), date(2026, 9, 3))
        self.assertIsNone(fecha_cas("cuando se publique"))
        self.assertIsNone(fecha_cas(""))

    def test_campo_lee_la_etiqueta_con_su_decoracion(self):
        lineas = html_a_lineas(muestra("cas_una_plaza.html"))
        # El sitio antepone un '►' a cada etiqueta del resumen.
        self.assertEqual(campo(lineas, "Institución"), "MUNICIPALIDAD SURQUILLO")
        self.assertEqual(campo(lineas, "Lugar de trabajo"), "Lima")
        # Etiqueta con paréntesis pegado.
        self.assertEqual(campo(lineas, "Formación académica"), "Ayudante de poda")


class PruebaUnaSolaPlaza(unittest.TestCase):

    def test_una_plaza_se_lee_completa(self):
        html = con_plazo(muestra("cas_una_plaza.html"), date.today() + timedelta(days=10))
        cruda = parsear_cas(html, URL_UNA, "Convocatorias CAS")

        self.assertIsNotNone(cruda)
        self.assertEqual(cruda.puesto, "Ayudante de poda")
        self.assertEqual(cruda.empresa, "MUNICIPALIDAD SURQUILLO")
        self.assertEqual(cruda.ubicacion_texto, "Lima")
        self.assertEqual(cruda.extra["perfil"], "publico")
        self.assertEqual(cruda.extra["regimen"], "CAS")
        self.assertEqual(cruda.extra["plazas"], 1)

    def test_varias_plazas_no_se_publican(self):
        """La decisión, fijada: lo que no se puede partir bien, no entra."""
        html = muestra("cas_varias_plazas.html")
        self.assertIsNone(parsear_cas(html, URL_VARIAS, "Convocatorias CAS"))

    def test_la_pagina_manda_sobre_la_direccion(self):
        """
        Si la dirección dice 1 plaza pero la página lista dos puestos, se
        descarta. La URL es solo texto y no vale como garantía.
        """
        html = muestra("cas_varias_plazas.html")
        mentirosa = URL_VARIAS.replace("-6-plazas-", "-1-plazas-")
        self.assertIsNone(parsear_cas(html, mentirosa, "Convocatorias CAS"))


class PruebaSueldo(unittest.TestCase):

    def test_el_sueldo_es_el_que_dice_el_aviso(self):
        html = con_plazo(muestra("cas_una_plaza.html"), date.today() + timedelta(days=10))
        oferta = procesar_cruda(parsear_cas(html, URL_UNA, "Convocatorias CAS"))
        self.assertEqual(oferta.sueldo_min, 1800)
        self.assertEqual(oferta.sueldo_max, 1800)
        self.assertEqual(oferta.moneda, "PEN")

    def test_el_sueldo_se_lee_mensual_y_no_diario(self):
        """
        El error de los S/ 33,800 salió de leer un monto mensual como diario.
        Aquí el monto viene etiquetado y solo, pero el periodo se sigue
        buscando pegado al número.
        """
        from motor.sueldo import extraer_sueldo
        s = extraer_sueldo("Salario: S/ 1800.00")
        self.assertEqual(s.periodo, "mensual")
        self.assertEqual(s.minimo, 1800)

    def test_si_los_dos_montos_no_coinciden_no_se_publica(self):
        """
        El resumen dice un sueldo y la ficha del puesto dice otro. No se elige
        uno: se descarta. Regla 2, ante la duda el motor no publica.
        """
        html = con_plazo(muestra("cas_una_plaza.html"), date.today() + timedelta(days=10))
        torcida = html.replace("Salario: S/ 1800.00", "Salario: S/ 2500.00")
        self.assertIsNone(parsear_cas(torcida, URL_UNA, "Convocatorias CAS"))

    def test_sin_sueldo_no_hay_aviso(self):
        html = con_plazo(muestra("cas_una_plaza.html"), date.today() + timedelta(days=10))
        sin = (html.replace("Salario: S/ 1800.00", "Salario: a convenir")
                   .replace("S/. 1800 Soles", "seg&uacute;n escala"))
        cruda = parsear_cas(sin, URL_UNA, "Convocatorias CAS")
        if cruda is not None:                       # si se leyó, el filtro lo bota
            oferta = procesar_cruda(cruda)
            self.assertFalse(oferta.aprobada)
            self.assertEqual(oferta.sueldo_min, 0)


class PruebaPlazo(unittest.TestCase):

    def test_plazo_cerrado_no_entra(self):
        html = con_plazo(muestra("cas_una_plaza.html"), date.today() - timedelta(days=1))
        self.assertIsNone(parsear_cas(html, URL_UNA, "Convocatorias CAS"))

    def test_sin_plazo_legible_no_entra(self):
        """
        La página no publica fecha de publicación. Si tampoco se puede leer
        hasta cuándo postular, no queda con qué saber si sigue abierta.
        """
        html = muestra("cas_una_plaza.html").replace(
            "Plazo para postular: 17 de Agosto del 2026", "Plazo para postular: ver bases")
        self.assertIsNone(parsear_cas(html, URL_UNA, "Convocatorias CAS"))

    def test_el_plazo_llega_hasta_la_oferta(self):
        cierre = date.today() + timedelta(days=10)
        html = con_plazo(muestra("cas_una_plaza.html"), cierre)
        oferta = procesar_cruda(parsear_cas(html, URL_UNA, "Convocatorias CAS"))
        self.assertEqual(oferta.vence, cierre)
        self.assertEqual(oferta.dias_restantes, 10)


class PruebaTitulo(unittest.TestCase):

    def test_el_titulo_es_el_puesto_y_no_la_entidad(self):
        """
        'Municipalidad de Surquillo' dice para quién es el trabajo, no qué es.
        El título tiene que nombrar el oficio (regla 8).
        """
        html = con_plazo(muestra("cas_una_plaza.html"), date.today() + timedelta(days=10))
        oferta = procesar_cruda(parsear_cas(html, URL_UNA, "Convocatorias CAS"))
        self.assertEqual(oferta.puesto, "Ayudante de poda")
        self.assertNotIn("municipalidad", oferta.puesto.lower())

    def test_sin_puesto_nombrado_no_se_inventa_uno(self):
        html = con_plazo(muestra("cas_una_plaza.html"), date.today() + timedelta(days=10))
        anonima = (html.replace("<h4><a href=\"/concurso-publico-proceso-municipalidad-"
                                "surquillo-agosto-2026-ayudante-poda-274908.html\">"
                                "Ayudante de poda</a></h4>", "<h4></h4>")
                       .replace("&#9658; Formaci&oacute;n acad&eacute;mica(seg&uacute;n "
                                "puesto):</strong> Ayudante de poda",
                                "&#9658; Formaci&oacute;n acad&eacute;mica(seg&uacute;n "
                                "puesto):</strong>"))
        cruda = parsear_cas(anonima, URL_UNA, "Convocatorias CAS")
        if cruda is not None:
            oferta = procesar_cruda(cruda)
            self.assertFalse(oferta.aprobada)


class PruebaCuerpoDelAviso(unittest.TestCase):

    def test_el_menu_y_el_pie_no_se_cuelan_como_requisitos(self):
        """
        Se arma el cuerpo a mano en vez de pasar la página entera. Si se pasara
        entera, 'Departamentos', 'Quienes somos' y el aviso de WhatsApp
        terminarían contados como requisitos del puesto.
        """
        html = con_plazo(muestra("cas_una_plaza.html"), date.today() + timedelta(days=10))
        oferta = procesar_cruda(parsear_cas(html, URL_UNA, "Convocatorias CAS"))
        todo = " ".join(oferta.requisitos).lower()
        for basura in ("whatsapp", "quienes somos", "departamentos",
                       "términos y condiciones", "mesa de partes"):
            self.assertNotIn(basura, todo, f"se coló «{basura}» en los requisitos")

    def test_los_requisitos_son_los_del_puesto(self):
        html = con_plazo(muestra("cas_una_plaza.html"), date.today() + timedelta(days=10))
        oferta = procesar_cruda(parsear_cas(html, URL_UNA, "Convocatorias CAS"))
        self.assertGreaterEqual(len(oferta.requisitos), 3)
        self.assertTrue(any("experiencia" in r.lower() for r in oferta.requisitos))

    def test_los_beneficios_son_los_del_regimen_CAS(self):
        """
        El aviso no los lista porque los fija la ley. No es invento: es el
        marco legal del D. Leg. 1057, y queda marcado como tal.
        """
        html = con_plazo(muestra("cas_una_plaza.html"), date.today() + timedelta(days=10))
        cruda = parsear_cas(html, URL_UNA, "Convocatorias CAS")
        self.assertTrue(cruda.extra["beneficios_de_ley"])
        oferta = procesar_cruda(cruda)
        self.assertGreaterEqual(len(oferta.beneficios), 2)
        self.assertTrue(any("essalud" in b.lower() for b in oferta.beneficios))


class PruebaDependeDeLasBases(unittest.TestCase):
    """
    El número más importante de esta fuente, y conviene tenerlo escrito.

    Una convocatoria CAS típica, leída SOLO de la página, saca 69 sobre 100.
    El umbral es 70. O sea: **no se publica por un punto.**

    No es un error de cálculo ni algo que haya que ajustar bajando el umbral.
    Es la rúbrica funcionando: al Estado no se le exige la lista de funciones,
    pero los 25 puntos de ese bloque se pierden enteros, y el aviso tiene que
    compensarlos en todo lo demás. Con un sueldo de monto único (27 de 30) y
    tres requisitos (17 de 20), no alcanza.

    Lo que sí alcanza es abrir el PDF de las bases, que es justo lo que la
    convocatoria enlaza en el dominio de la entidad. Con las funciones dentro,
    el mismo aviso pasa de 69 a más de 90.

    Conclusión operativa: **esta fuente depende de que se pueda leer el PDF.**
    Si un día se ve entregando cero, lo primero que hay que revisar no es el
    lector, es si `pdfplumber` está instalado y si las entidades siguen
    dejando bajar sus bases.
    """

    def _cruda(self):
        html = con_plazo(muestra("cas_una_plaza.html"), date.today() + timedelta(days=10))
        return parsear_cas(html, URL_UNA, "Convocatorias CAS")

    def test_sin_las_funciones_de_las_bases_se_queda_corta(self):
        oferta = procesar_cruda(self._cruda())
        self.assertFalse(oferta.aprobada)
        self.assertGreaterEqual(oferta.score, 65,
                                "si baja de aquí, algo más se rompió")
        self.assertLess(oferta.score, 70)

    def test_con_las_funciones_de_las_bases_se_publica(self):
        cruda = self._cruda()
        funciones = [
            "Realizar la poda de árboles y arbustos en parques y bermas del distrito.",
            "Recoger y trasladar los residuos vegetales generados por la poda.",
            "Apoyar en el mantenimiento de las áreas verdes asignadas.",
            "Reportar al supervisor el estado de los árboles intervenidos.",
        ]
        cruda.descripcion_html += ("<p>Funciones</p><ul>"
                                   + "".join(f"<li>{f}</li>" for f in funciones)
                                   + "</ul>")
        oferta = procesar_cruda(cruda)
        self.assertTrue(oferta.aprobada, f"score {oferta.score}: {oferta.motivos_rechazo}")
        self.assertGreaterEqual(oferta.score, 85)

    def test_la_fuente_pide_abrir_las_bases(self):
        """Si alguien le quita el enriquecido, la fuente deja de entregar."""
        self.assertIsNotNone(convocatorias_cas()[0].enriquecer)


class PruebaSinFechaDePublicacion(unittest.TestCase):
    """
    La página no dice cuándo se publicó la convocatoria. Dice hasta cuándo se
    puede postular, que para el postulante es lo que importa.

    Eso obliga a que la web sepa callarse: antes el exportador convertía
    'sin fecha' en cero días y la tarjeta salía con un 'Publicada hoy' que
    nadie había escrito.
    """

    def test_la_oferta_sale_sin_fecha_de_publicacion(self):
        html = con_plazo(muestra("cas_una_plaza.html"), date.today() + timedelta(days=10))
        self.assertIsNone(parsear_cas(html, URL_UNA, "Convocatorias CAS").publicado)

    def test_sin_fecha_el_exportador_no_inventa_un_cero(self):
        from motor.exportar import _a_formato_web
        fila = {"puesto": "Ayudante de poda", "empresa": "MUNICIPALIDAD SURQUILLO",
                "categoria": "Otros", "sueldo_min": 1800, "sueldo_max": 1800,
                "modalidad": "Presencial", "ciudad": "Lima",
                "fuente": "Convocatorias CAS", "score": 92, "resumen": "",
                "funciones": [], "requisitos": [], "beneficios": [],
                "url": URL_UNA, "publicado": None,
                "vence": (date.today() + timedelta(days=10)).isoformat()}
        web = _a_formato_web(fila, 1)
        self.assertIsNone(web["dias"], "'sin fecha' no es lo mismo que 'hoy'")
        self.assertEqual(web["restan"], 10)

    def test_la_web_se_calla_cuando_no_hay_fecha(self):
        """En index.html, `cuando(null)` tiene que dar cadena vacía."""
        from pathlib import Path
        indice = (Path(__file__).parent.parent / "index.html").read_text(encoding="utf-8")
        self.assertIn("const cuando = d => (d===null || d===undefined) ? ''", indice)
        # La frase 'Publicada …' solo puede salir a través del ayudante, que
        # devuelve vacío cuando no hay fecha. Si vuelve a escribirse suelta en
        # una tarjeta o en la ficha, el 'Publicada hoy' inventado regresa.
        self.assertEqual(indice.count("Publicada ${cuando(o.dias).toLowerCase()}"), 1,
                         "'Publicada …' se escribió a mano en vez de usar publicada(o)")
        self.assertEqual(indice.count("${publicada(o)}"), 2)


class PruebaLaFuente(unittest.TestCase):

    def test_no_necesita_navegador(self):
        """Si algún día necesitara Playwright, la corrida se volvería lenta."""
        fuente = convocatorias_cas()[0]
        self.assertFalse(fuente.necesita_render)
        self.assertIsInstance(fuente, ConvocatoriasCAS)

    def test_esta_en_las_fuentes_de_arranque(self):
        from motor.fuentes import fuentes_de_arranque
        nombres = [f.nombre for f in fuentes_de_arranque()]
        self.assertIn("Convocatorias CAS", nombres)

    def test_las_de_varias_plazas_se_cuentan_al_descubrir(self):
        """
        No basta con saltarlas: hay que saber CUÁNTAS se están dejando. Sin ese
        número, la fuente se ve sana entregando la mitad de lo que hay.
        """
        fuente = convocatorias_cas()[0]
        descubiertas = [
            URL_UNA,
            URL_VARIAS,
            URL_UNA.replace("-1-plazas-67463", "-1-plazas-67464"),
            URL_VARIAS.replace("-6-plazas-67476", "-283-plazas-67478"),
        ]
        fuente._reiniciar_problemas()
        fuente.urls_de_avisos = lambda limite=100: ConvocatoriasCAS.urls_de_avisos(fuente, limite)
        PortalWebOriginal = type(fuente).__mro__[1]
        fuente.__dict__["_finge"] = descubiertas

        # Se reemplaza el descubrimiento real por la lista de arriba.
        original = PortalWebOriginal.urls_de_avisos
        try:
            PortalWebOriginal.urls_de_avisos = lambda self, limite=100: descubiertas
            salida = ConvocatoriasCAS.urls_de_avisos(fuente, 100)
        finally:
            PortalWebOriginal.urls_de_avisos = original

        self.assertEqual(len(salida), 2)
        self.assertEqual(fuente.saltadas_por_plazas, 2)
        self.assertEqual(fuente.plazas_perdidas, 289)
        self.assertTrue(any("más de una plaza" in e for e in fuente.errores))


if __name__ == "__main__":
    unittest.main()
