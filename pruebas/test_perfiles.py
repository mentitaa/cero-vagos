"""
Pruebas de las dos varas de medir (sector público y privado) y de los lectores
de bolsas de trabajo de empresas.
"""
from __future__ import annotations

import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from motor.fuentes.empresas import (                   # noqa: E402
    Greenhouse, Lever, detectar_ats,
)
from motor.fuentes.publicas import parsear_convocatoria  # noqa: E402
from motor.pipeline import procesar_cruda               # noqa: E402
from motor.score import PERFILES, evaluar              # noqa: E402
from motor.sueldo import extraer_sueldo                # noqa: E402

BASE = dict(
    sueldo=extraer_sueldo("S/ 4,800"),
    requisitos=["Título profesional de ingeniero civil, colegiado y habilitado",
                "Experiencia laboral igual o mayor a 04 años",
                "Conocimiento de la Ley de Contrataciones con el Estado"],
    beneficios=["Régimen 728: planilla con todos los beneficios de ley",
                "Gratificaciones de julio y diciembre",
                "30 días calendario de vacaciones al año"],
    empresa="Gobierno Regional del Cusco", ciudad="Cusco", modalidad="Presencial",
    publicado=date.today(), vence=date(2099, 1, 1),
)


class TestPerfiles(unittest.TestCase):

    def test_el_estado_aprueba_con_una_funcion(self):
        r = evaluar(**BASE,
                    funciones=["Supervisar la ejecución de las obras del proyecto especial"],
                    perfil="publico")
        self.assertTrue(r.aprobada, r.motivos)

    def test_el_privado_no_aprueba_con_una_funcion(self):
        r = evaluar(**BASE,
                    funciones=["Supervisar la ejecución de las obras del proyecto especial"],
                    perfil="privado")
        self.assertFalse(r.aprobada)
        self.assertTrue(any("funciones" in m for m in r.motivos))

    def test_ninguno_aprueba_con_cero_funciones(self):
        for perfil in ("publico", "privado"):
            with self.subTest(perfil=perfil):
                self.assertFalse(evaluar(**BASE, funciones=[], perfil=perfil).aprobada)

    def test_pocas_funciones_puntuan_menos(self):
        una = evaluar(**BASE, funciones=["Supervisar la ejecución de las obras del proyecto"],
                      perfil="publico")
        varias = evaluar(**BASE, perfil="publico", funciones=[
            "Supervisar la ejecución de las obras del proyecto especial",
            "Elaborar los informes mensuales de avance físico y financiero",
            "Coordinar con la supervisión externa el levantamiento de observaciones",
            "Revisar los expedientes técnicos antes de su aprobación",
        ])
        self.assertLess(una.detalle["funciones"], varias.detalle["funciones"])
        self.assertTrue(una.aprobada and varias.aprobada)

    def test_el_sueldo_sigue_siendo_eliminatorio_en_ambos(self):
        for perfil in ("publico", "privado"):
            with self.subTest(perfil=perfil):
                datos = dict(BASE, sueldo=None)
                r = evaluar(**datos, funciones=["Supervisar la ejecución de las obras"] * 3,
                            perfil=perfil)
                self.assertFalse(r.aprobada)

    def test_los_perfiles_estan_definidos(self):
        """
        Al Estado no se le exige lista de funciones; al privado sí, y tres.
        Son varas distintas a propósito: el Estado publica las funciones en
        el PDF de las bases, el privado que las calla está escondiendo algo.
        """
        self.assertEqual(PERFILES["publico"]["funciones"], 0)
        self.assertEqual(PERFILES["privado"]["funciones"], 3)

    def test_al_estado_sin_funciones_se_le_quitan_los_25_puntos(self):
        """
        Que no sea eliminatorio no significa que salga gratis. El aviso
        pierde el bloque entero y tiene que compensarlo en todo lo demás.
        """
        r = evaluar(**dict(BASE, funciones=[]), perfil="publico")
        self.assertEqual(r.detalle["funciones"], 0)
        self.assertNotIn("funciones", " ".join(r.motivos).lower())

    def test_un_aviso_publico_flojo_igual_se_cae(self):
        """La vara la pone el umbral, no una excepción que deje pasar todo."""
        r = evaluar(**dict(BASE, funciones=[], beneficios=["Buen ambiente laboral"]),
                    perfil="publico")
        self.assertFalse(r.aprobada)


class TestPoliticaDeFechas(unittest.TestCase):
    """
    En el Estado la fecha de cierre no es confiable: no siempre se publica.
    Lo que decide es hace cuánto se publicó el aviso.
    """

    UNA_FUNCION = ["Supervisar la ejecución de las obras del proyecto especial"]

    def test_si_dice_que_ya_cerro_se_bota(self):
        """Publicar una convocatoria cerrada es hacer perder el tiempo."""
        for perfil, funciones in (("publico", self.UNA_FUNCION),
                                  ("privado", self.UNA_FUNCION * 3)):
            with self.subTest(perfil=perfil):
                datos = dict(BASE, vence=date.today() - timedelta(days=1),
                             publicado=date.today())
                r = evaluar(**datos, funciones=funciones, perfil=perfil)
                self.assertFalse(r.aprobada)
                self.assertTrue(any("plazo cerró" in m for m in r.motivos))

    def test_si_el_plazo_sigue_abierto_pasa(self):
        datos = dict(BASE, vence=date.today() + timedelta(days=5),
                     publicado=date.today() - timedelta(days=2))
        r = evaluar(**datos, funciones=self.UNA_FUNCION, perfil="publico")
        self.assertTrue(r.aprobada, r.motivos)

    def test_sin_fecha_de_cierre_manda_la_antiguedad(self):
        """
        Una convocatoria CAS dura entre 5 y 15 días. Si no dice hasta cuándo y
        ya lleva tres semanas publicada, está cerrada aunque no lo escriba.
        """
        r = evaluar(**dict(BASE, vence=None, publicado=date.today() - timedelta(days=30)),
                    funciones=self.UNA_FUNCION, perfil="publico")
        self.assertFalse(r.aprobada)
        self.assertTrue(any("no dice hasta cuándo" in m.lower() for m in r.motivos), r.motivos)

    def test_sin_fecha_de_cierre_pero_recien_publicada_pasa(self):
        r = evaluar(**dict(BASE, vence=None, publicado=date.today() - timedelta(days=3)),
                    funciones=self.UNA_FUNCION, perfil="publico")
        self.assertTrue(r.aprobada, r.motivos)

    def test_el_privado_aguanta_mas_sin_fecha(self):
        datos = dict(BASE, vence=None, publicado=date.today() - timedelta(days=30))
        self.assertTrue(evaluar(**datos, funciones=self.UNA_FUNCION * 3,
                                perfil="privado").aprobada)

    def test_el_tope_absoluto_de_dos_meses_sigue(self):
        r = evaluar(**dict(BASE, vence=date.today() + timedelta(days=5),
                           publicado=date.today() - timedelta(days=70)),
                    funciones=self.UNA_FUNCION, perfil="publico")
        self.assertFalse(r.aprobada)
        self.assertTrue(any("hace 70 días" in m for m in r.motivos), r.motivos)

    def test_el_limite_es_de_dos_meses(self):
        from motor.score import MAX_DIAS_ANTIGUEDAD
        self.assertEqual(MAX_DIAS_ANTIGUEDAD, 60)


class TestDescartePrevio(unittest.TestCase):
    """Lo viejo se salta antes de gastar tiempo abriendo su PDF."""

    def test_salta_por_antiguedad_no_por_vencimiento(self):
        from motor.fuentes.portal_web import _demasiado_antigua
        from motor.modelos import OfertaCruda

        vieja = OfertaCruda(fuente="x", url="u", puesto="p",
                            publicado=date.today() - timedelta(days=90))
        reciente = OfertaCruda(fuente="x", url="u", puesto="p",
                               publicado=date.today() - timedelta(days=5))
        # Plazo cerrado pero publicada ayer: se procesa igual.
        cerrada = OfertaCruda(fuente="x", url="u", puesto="p",
                              publicado=date.today() - timedelta(days=1),
                              extra={"vence": "2020-01-01"})

        self.assertTrue(_demasiado_antigua(vieja, 60))
        self.assertFalse(_demasiado_antigua(reciente, 60))
        self.assertFalse(_demasiado_antigua(cerrada, 60))

    def test_sin_fecha_de_publicacion_no_se_descarta(self):
        from motor.fuentes.portal_web import _demasiado_antigua
        from motor.modelos import OfertaCruda
        self.assertFalse(_demasiado_antigua(
            OfertaCruda(fuente="x", url="u", puesto="p"), 60))

    def test_salta_las_de_plazo_cerrado_antes_de_abrir_el_pdf(self):
        from motor.fuentes.portal_web import _plazo_cerrado
        from motor.modelos import OfertaCruda

        cerrada = OfertaCruda(fuente="x", url="u", puesto="p",
                              extra={"vence": "2020-01-01"})
        abierta = OfertaCruda(fuente="x", url="u", puesto="p",
                              extra={"vence": "2099-01-01"})
        sin_dato = OfertaCruda(fuente="x", url="u", puesto="p")

        self.assertTrue(_plazo_cerrado(cerrada))
        self.assertFalse(_plazo_cerrado(abierta))
        self.assertFalse(_plazo_cerrado(sin_dato))


class TestExportacionDelPlazo(unittest.TestCase):
    """La web tiene que poder decir cuántos días quedan para postular."""

    def test_dias_restantes(self):
        from motor.exportar import _a_formato_web
        fila = {
            "puesto": "Trabajador Social", "empresa": "Inabif", "categoria": "Salud",
            "sueldo_min": 3000, "sueldo_max": 3000, "modalidad": "Presencial",
            "ciudad": "Huancavelica", "fuente": "Estado", "score": 88,
            "resumen": "", "funciones": [], "requisitos": [], "beneficios": [],
            "url": "https://x.pe/1",
            "publicado": (date.today() - timedelta(days=2)).isoformat(),
            "vence": (date.today() + timedelta(days=6)).isoformat(),
        }
        web = _a_formato_web(fila, 1)
        self.assertEqual(web["dias"], 2)
        self.assertEqual(web["restan"], 6)

    def test_sin_fecha_de_cierre_restan_es_nulo(self):
        from motor.exportar import _a_formato_web
        fila = {
            "puesto": "X", "empresa": "Y", "categoria": "Otros", "sueldo_min": 1500,
            "sueldo_max": 1500, "modalidad": "", "ciudad": "", "fuente": "Estado",
            "score": 75, "resumen": "", "funciones": [], "requisitos": [],
            "beneficios": [], "url": "u", "publicado": date.today().isoformat(),
            "vence": "",
        }
        self.assertIsNone(_a_formato_web(fila, 1)["restan"])


class TestPerfilDesdeLaFuente(unittest.TestCase):

    def test_las_convocatorias_se_marcan_como_publicas(self):
        html = (RAIZ / "pruebas" / "muestras" / "convocatoria_sin_funciones.html").read_text(encoding="utf-8")
        cruda = parsear_convocatoria(html, "https://x.pe/c/1", "Estado")
        self.assertEqual(cruda.extra["perfil"], "publico")

    def test_con_una_funcion_del_pdf_la_convocatoria_pasa(self):
        html = (RAIZ / "pruebas" / "muestras" / "convocatoria_sin_funciones.html").read_text(encoding="utf-8")
        cruda = parsear_convocatoria(html, "https://x.pe/c/1", "Estado")
        cruda.descripcion_html += ("<p>Funciones</p><ul><li>Diseñar las piezas gráficas "
                                   "de las campañas institucionales del Poder Judicial</li></ul>")
        cruda.extra["vence"] = "2099-01-01"
        o = procesar_cruda(cruda)
        self.assertEqual(len(o.funciones), 1)
        self.assertTrue(o.aprobada, o.motivos_rechazo)


class TestDeteccionDeAts(unittest.TestCase):

    def test_reconoce_los_ats_conocidos(self):
        casos = {
            "https://boards.greenhouse.io/empresa": "greenhouse",
            "https://jobs.lever.co/empresa": "lever",
            "https://empresa.wd3.myworkdayjobs.com/es/Careers": "workday",
            "https://career8.successfactors.com/career?company=AMSAP": "successfactors",
            "https://empresa.avature.net/careers": "avature",
            # Caso real: el portal de Cencosud (Metro y Wong) enruta acá.
            "https://cencosud.csod.com/ux/ats/careersite/10/home?c=cencosud": "cornerstone",
            "https://cencosudbrasil.gupy.io/": "gupy",
        }
        for url, esperado in casos.items():
            with self.subTest(url=url):
                self.assertEqual(detectar_ats(url), esperado)

    def test_web_propia_no_es_ats(self):
        self.assertEqual(detectar_ats("https://www.camposol.com.pe/trabaja-con-nosotros/"), "")

    def test_detecta_por_el_html_embebido(self):
        html = '<div id="grnhse_app"></div><script src="https://boards.greenhouse.io/embed/job_board/js?for=acme"></script>'
        self.assertEqual(detectar_ats(html), "greenhouse")

    def test_las_empresas_configuradas_declaran_su_estado(self):
        from motor.fuentes.empresas import empresas_peru
        for f in empresas_peru():
            with self.subTest(empresa=f.nombre):
                self.assertTrue(f.nota)
                self.assertTrue(f.listados or f.sitemaps)


class TestLectoresAts(unittest.TestCase):
    """Se prueba la conversión de la respuesta del ATS, sin salir a la red."""

    def test_greenhouse(self):
        fuente = Greenhouse("acme", "Acme Perú")
        respuesta = {"jobs": [{
            "id": 123, "title": "Analista de Datos",
            "absolute_url": "https://boards.greenhouse.io/acme/jobs/123",
            "location": {"name": "Lima, Perú"},
            "updated_at": "2026-07-30T10:00:00-05:00",
            "content": "&lt;p&gt;Funciones&lt;/p&gt;&lt;ul&gt;&lt;li&gt;Construir dashboards&lt;/li&gt;&lt;/ul&gt;",
        }]}
        fuente_json = lambda url, robots: respuesta          # noqa: E731
        import motor.fuentes.empresas as mod
        original, mod._pedir_json = mod._pedir_json, fuente_json
        try:
            avisos = list(fuente.recolectar())
        finally:
            mod._pedir_json = original

        self.assertEqual(len(avisos), 1)
        self.assertEqual(avisos[0].puesto, "Analista de Datos")
        self.assertEqual(avisos[0].empresa, "Acme Perú")
        self.assertEqual(avisos[0].publicado, date(2026, 7, 30))
        self.assertIn("<li>Construir dashboards</li>", avisos[0].descripcion_html)

    def test_lever(self):
        fuente = Lever("acme", "Acme Perú")
        respuesta = [{
            "id": "abc", "text": "Ejecutivo Comercial",
            "hostedUrl": "https://jobs.lever.co/acme/abc",
            "categories": {"location": "Arequipa"},
            "createdAt": 1_785_000_000_000,
            "descriptionPlain": "Gestionar la cartera de clientes.",
            "lists": [{"text": "Requisitos", "content": "<li>2 años de experiencia</li>"}],
        }]
        import motor.fuentes.empresas as mod
        original, mod._pedir_json = mod._pedir_json, lambda url, robots: respuesta
        try:
            avisos = list(fuente.recolectar())
        finally:
            mod._pedir_json = original

        self.assertEqual(avisos[0].puesto, "Ejecutivo Comercial")
        self.assertEqual(avisos[0].ubicacion_texto, "Arequipa")
        self.assertIn("Requisitos", avisos[0].descripcion_html)

    def test_si_el_ats_falla_no_revienta(self):
        import motor.fuentes.empresas as mod

        def explotar(url, robots):
            raise RuntimeError("404")

        original, mod._pedir_json = mod._pedir_json, explotar
        try:
            fuente = Greenhouse("acme")
            self.assertEqual(list(fuente.recolectar()), [])
            self.assertTrue(fuente.errores)
        finally:
            mod._pedir_json = original


if __name__ == "__main__":
    unittest.main(verbosity=2)
