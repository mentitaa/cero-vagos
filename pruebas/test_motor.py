"""
Pruebas del motor. Correr desde la raíz del proyecto:

    python -m unittest discover pruebas -v
"""
from __future__ import annotations

import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from motor.fuentes.demo import FuenteDemo                 # noqa: E402
from motor.fuentes.jsonld import extraer_jobposting       # noqa: E402
from motor.normalizar import (                            # noqa: E402
    detectar_categoria, detectar_modalidad, detectar_ubicacion, extraer_bloques,
)
from motor.pipeline import procesar_cruda                 # noqa: E402
from motor.score import UMBRAL_PUBLICACION, evaluar       # noqa: E402
from motor.sueldo import declara_sueldo_vago, extraer_sueldo  # noqa: E402


class TestSueldo(unittest.TestCase):

    def test_monto_simple(self):
        for texto, esperado in [
            ("S/ 3,500", 3500),
            ("S/. 2500.00 mensuales", 2500),
            ("S/2800", 2800),
            ("4500 soles mensuales", 4500),
            ("Sueldo: 1,800 soles", 1800),
        ]:
            with self.subTest(texto=texto):
                s = extraer_sueldo(texto)
                self.assertIsNotNone(s, texto)
                self.assertEqual(s.minimo, esperado)

    def test_rangos(self):
        for texto, lo, hi in [
            ("S/ 2,800 a S/ 3,400", 2800, 3400),
            ("S/7000 - S/9500", 7000, 9500),
            ("entre 4000 y 5500 soles", 4000, 5500),
            ("S/ 3.800,00 - S/ 4.500,00 al mes", 3800, 4500),
        ]:
            with self.subTest(texto=texto):
                s = extraer_sueldo(texto)
                self.assertIsNotNone(s, texto)
                self.assertEqual((s.minimo, s.maximo), (lo, hi))
                self.assertTrue(s.es_rango)

    def test_dolares(self):
        s = extraer_sueldo("US$ 1,200 mensual")
        self.assertIsNotNone(s)
        self.assertEqual(s.moneda, "USD")
        self.assertEqual(s.minimo, 1200)

    def test_anual_se_convierte_a_mensual(self):
        s = extraer_sueldo("S/ 54,000 anuales")
        self.assertIsNotNone(s)
        self.assertEqual(s.minimo, 4500)

    def test_rmv(self):
        s = extraer_sueldo("Se ofrece la remuneración mínima vital")
        self.assertIsNotNone(s)
        self.assertEqual(s.minimo, 1130)

    def test_vagos_no_pasan(self):
        for texto in [
            "Sueldo a convenir",
            "Remuneración acorde al mercado",
            "Salario competitivo según experiencia",
            "El sueldo se conversará en la entrevista",
            "Buscamos personal proactivo",
            "",
        ]:
            with self.subTest(texto=texto):
                self.assertIsNone(extraer_sueldo(texto))

    def test_numero_cerca_de_frase_vaga_se_ignora(self):
        # El 29783 de la ley y el 2 de "2 años" no deben leerse como sueldo.
        self.assertIsNone(extraer_sueldo("Conocimiento de la Ley 29783 y 2 años de experiencia"))

    def test_montos_absurdos_se_descartan(self):
        self.assertIsNone(extraer_sueldo("S/ 12"))
        self.assertIsNone(extraer_sueldo("S/ 950000 mensuales"))

    def test_declara_sueldo_vago(self):
        self.assertTrue(declara_sueldo_vago("Sueldo A CONVENIR según perfil"))
        self.assertFalse(declara_sueldo_vago("Sueldo S/ 3,000"))


class TestSueldoPeriodo(unittest.TestCase):
    """
    Casos reales que rompieron el motor: una palabra suelta como "quincenales"
    o "horas extras" en otra frase hacía que un sueldo de S/ 1,300 se publicara
    como S/ 33,800.
    """

    AVISO_REAL = """Salario base S/1,300. Bono de movilidad fijo: S/100.
    Bono de asistencia perfecta: S/100. Bono de cumplimiento: S/ 200.
    Asignación familiar: S/113. Ingreso a planilla desde el 1°er. día.
    Remuneraciones quincenales. Pago de horas extras."""

    def test_no_multiplica_un_sueldo_mensual(self):
        s = extraer_sueldo(self.AVISO_REAL)
        self.assertIsNotNone(s)
        self.assertEqual(s.minimo, 1300)

    def test_horas_extra_no_convierten_en_pago_por_hora(self):
        s = extraer_sueldo("Sueldo de S/1130 en planilla completa + horas extra de aprox S/.473")
        self.assertEqual(s.minimo, 1130)

    def test_el_periodo_solo_cuenta_si_esta_pegado_al_monto(self):
        casos = {
            "S/ 50 diarios": 1300,
            "S/ 15 por hora": 3120,
            "Remuneración quincenal de S/ 900": 1800,
            "S/ 2,500 mensuales": 2500,
            "S/ 54,000 anuales": 4500,
        }
        for texto, esperado in casos.items():
            with self.subTest(texto=texto):
                self.assertEqual(extraer_sueldo(texto).minimo, esperado)

    def test_montos_imposibles_para_su_periodo_se_descartan(self):
        """1,300 no puede ser un pago diario: lo mal leído es el periodo."""
        self.assertIsNone(extraer_sueldo("S/ 1,300 diarios"))
        self.assertIsNone(extraer_sueldo("S/ 9,000 por hora"))

    def test_ante_la_duda_gana_el_monto_conservador(self):
        s = extraer_sueldo("Sueldo S/ 1,200. Bono anual de hasta S/ 12,000.")
        self.assertEqual(s.minimo, 1200)


class TestLimpiarPuesto(unittest.TestCase):
    """El título es el puesto, no un cartel de feria."""

    def test_corta_el_gancho_publicitario(self):
        from motor.normalizar import limpiar_puesto
        casos = {
            "¡GANA MÁS DE 1800 SOLES! OPERARIO DE PRODUCCIÓN — STA ANITA / "
            "PLANILLA COMPLETA + ALIMENTACIÓN": "Operario de Producción",
            "OPERARIO DE PLANTA/ SUELDO FIJO + BONO FIJO MENSUAL + PLANILLA COMPLETA":
                "Operario de Planta",
            "ASISTENTE DE DESPACHO/TURNOS ROTATIVOS/HUACHIPA - HUACHIPA (LURIGANCHO)":
                "Asistente de Despacho",
            "¡ÚNETE A NUESTRO EQUIPO! ASESOR COMERCIAL": "Asesor Comercial",
        }
        for bruto, esperado in casos.items():
            with self.subTest(bruto=bruto[:40]):
                self.assertEqual(limpiar_puesto(bruto), esperado)

    def test_respeta_los_titulos_que_ya_estan_bien(self):
        from motor.normalizar import limpiar_puesto
        for bueno in ("Desarrollador Backend Node.js",
                      "Promotor de Servicios BCP Abancay",
                      "Analista de Costos para Licitaciones y Proyectos en Minería"):
            with self.subTest(bueno=bueno):
                self.assertEqual(limpiar_puesto(bueno), bueno)

    def test_conserva_las_siglas(self):
        from motor.normalizar import limpiar_puesto
        self.assertEqual(limpiar_puesto("INGENIERO DE SEGURIDAD SSOMA"),
                         "Ingeniero de Seguridad SSOMA")

    def test_nunca_devuelve_vacio(self):
        from motor.normalizar import limpiar_puesto
        self.assertEqual(limpiar_puesto("¡POSTULA YA!"), "¡POSTULA YA!")
        self.assertEqual(limpiar_puesto(""), "")

    def test_quita_los_arranques_que_no_dicen_el_cargo(self):
        from motor.normalizar import limpiar_puesto
        casos = {
            "IMPORTANTE EMPRESA REQUIERE PERSONAL PARA EL AREA DE ALMACEN CON "
            "EXPERIENCIA MINIMA DE 6 MESES": "Personal para el Area de Almacen",
            "SE NECESITA COCINERO CON EXPERIENCIA PARA RESTAURANTE": "Cocinero",
            "Buscamos un Analista de Sistemas": "Analista de Sistemas",
            "GANA HASTA S/2500 - ASESOR DE VENTAS CALL CENTER":
                "Asesor de Ventas Call Center",
        }
        for bruto, esperado in casos.items():
            with self.subTest(bruto=bruto[:40]):
                self.assertEqual(limpiar_puesto(bruto), esperado)

    def test_ningun_titulo_queda_como_un_cartel(self):
        """
        Red de seguridad: pase lo que pase, un puesto no tiene doce palabras.
        Pero un cargo largo de verdad se respeta.
        """
        from motor.normalizar import limpiar_puesto, MAX_PALABRAS_PUESTO

        parrafada = ("OPORTUNIDAD LABORAL EXCELENTE PARA PERSONAS DINAMICAS QUE DESEEN "
                     "INTEGRAR NUESTRO GRAN EQUIPO DE TRABAJO EN LA MEJOR EMPRESA DEL RUBRO")
        self.assertLessEqual(len(limpiar_puesto(parrafada).split()), MAX_PALABRAS_PUESTO)

        largo_legitimo = "Analista de Costos para Licitaciones y Proyectos en Minería Subterránea"
        self.assertEqual(limpiar_puesto(largo_legitimo), largo_legitimo)


class TestNormalizar(unittest.TestCase):

    HTML = """
    <p>Buscamos un analista para el área comercial.</p>
    <p><b>Funciones:</b></p>
    <ul><li>Elaborar reportes semanales de venta</li>
        <li>Coordinar con el equipo de campo las visitas</li>
        <li>Analizar la data de cobertura por zona</li></ul>
    <p><b>Requisitos:</b></p>
    <ul><li>2 años de experiencia en análisis comercial</li>
        <li>Excel avanzado y Power BI intermedio</li>
        <li>Bachiller en Administración o Ingeniería</li></ul>
    <p><b>Beneficios:</b></p>
    <ul><li>Planilla completa desde el primer día</li>
        <li>EPS cubierta al 70% para el titular</li></ul>
    """

    def test_extrae_los_tres_bloques(self):
        b = extraer_bloques(self.HTML)
        self.assertEqual(len(b["funciones"]), 3)
        self.assertEqual(len(b["requisitos"]), 3)
        self.assertEqual(len(b["beneficios"]), 2)
        self.assertIn("Elaborar reportes", b["funciones"][0])

    def test_encabezados_alternativos(self):
        html = ("<p>Responsabilidades</p><ul><li>Gestionar la cartera de clientes activos</li>"
                "<li>Reportar avances al jefe comercial cada semana</li></ul>"
                "<p>¿Qué buscamos?</p><ul><li>3 años de experiencia en ventas</li></ul>"
                "<p>Te ofrecemos</p><ul><li>Ingreso a planilla con beneficios de ley</li></ul>")
        b = extraer_bloques(html)
        self.assertEqual(len(b["funciones"]), 2)
        self.assertEqual(len(b["requisitos"]), 1)
        self.assertEqual(len(b["beneficios"]), 1)

    def test_modalidad(self):
        self.assertEqual(detectar_modalidad("Trabajo 100% remoto desde casa"), "Remoto")
        self.assertEqual(detectar_modalidad("Modalidad híbrida, 3 días en oficina"), "Híbrido")
        self.assertEqual(detectar_modalidad("Trabajo presencial en planta"), "Presencial")

    def test_ubicacion(self):
        self.assertEqual(detectar_ubicacion("San Isidro, Lima"), ("Lima", "Lima"))
        self.assertEqual(detectar_ubicacion("Trujillo")[1], "La Libertad")
        self.assertEqual(detectar_ubicacion("Miraflores"), ("Lima", "Lima"))
        self.assertEqual(detectar_ubicacion("Sin datos"), ("", ""))

    def test_categoria(self):
        self.assertEqual(detectar_categoria("Desarrollador Backend Node.js"), "Tecnología")
        self.assertEqual(detectar_categoria("Asistente Contable"), "Contabilidad")
        self.assertEqual(detectar_categoria("Practicante de Marketing"), "Prácticas")
        self.assertEqual(detectar_categoria("Enfermera de emergencia"), "Salud")


class TestScore(unittest.TestCase):

    COMPLETA = dict(
        sueldo=extraer_sueldo("S/ 3,000 a S/ 4,000"),
        funciones=["Elaborar los reportes mensuales de gestión del área comercial",
                   "Coordinar con las jefaturas el plan de visitas a clientes",
                   "Analizar la data de cobertura y proponer mejoras concretas",
                   "Supervisar el cumplimiento de la cuota del equipo de campo"],
        requisitos=["2 años de experiencia en el puesto o similar",
                    "Excel avanzado y manejo de Power BI",
                    "Bachiller en Administración, Ingeniería o afines"],
        beneficios=["Planilla completa con todos los beneficios de ley",
                    "EPS cubierta al 70% para el titular",
                    "Bono trimestral por cumplimiento de metas"],
        empresa="Alicorp", ciudad="Lima", modalidad="Híbrido",
        publicado=date.today(),
    )

    def test_oferta_completa_aprueba(self):
        r = evaluar(**self.COMPLETA)
        self.assertTrue(r.aprobada, r.motivos)
        self.assertGreaterEqual(r.total, UMBRAL_PUBLICACION)

    def test_sin_sueldo_se_rechaza_aunque_todo_lo_demas_este(self):
        datos = dict(self.COMPLETA, sueldo=None)
        r = evaluar(**datos)
        self.assertFalse(r.aprobada)
        self.assertEqual(r.detalle["sueldo"], 0)

    def test_pocas_funciones_se_rechaza(self):
        datos = dict(self.COMPLETA, funciones=["Apoyar en labores del área"])
        r = evaluar(**datos)
        self.assertFalse(r.aprobada)
        self.assertTrue(any("funciones" in m for m in r.motivos))

    def test_beneficios_genericos_se_rechazan(self):
        datos = dict(self.COMPLETA,
                     beneficios=["Excelente ambiente laboral", "Oportunidad de crecimiento"])
        r = evaluar(**datos)
        self.assertFalse(r.aprobada)

    def test_aviso_muy_antiguo_se_rechaza(self):
        """Más de dos meses publicado y sale de la web, siga abierto o no."""
        datos = dict(self.COMPLETA, publicado=date.today() - timedelta(days=75))
        r = evaluar(**datos)
        self.assertFalse(r.aprobada)
        self.assertTrue(any("días" in m for m in r.motivos))

    def test_aviso_de_un_mes_sigue_vigente(self):
        datos = dict(self.COMPLETA, publicado=date.today() - timedelta(days=30))
        self.assertTrue(evaluar(**datos).aprobada)

    def test_score_nunca_pasa_de_100(self):
        r = evaluar(**self.COMPLETA)
        self.assertLessEqual(r.total, 100)


class TestJsonLd(unittest.TestCase):

    PAGINA = """
    <html><head>
    <script type="application/ld+json">
    {"@context":"https://schema.org","@type":"JobPosting",
     "title":"Analista de Datos","datePosted":"2026-07-30",
     "hiringOrganization":{"@type":"Organization","name":"Interbank"},
     "jobLocation":{"@type":"Place","address":{"addressLocality":"San Isidro","addressRegion":"Lima"}},
     "baseSalary":{"@type":"MonetaryAmount","currency":"PEN",
        "value":{"@type":"QuantitativeValue","minValue":5500,"maxValue":7200,"unitText":"MONTH"}},
     "description":"<p>Funciones:</p><ul><li>Construir dashboards en Power BI</li></ul>"}
    </script></head><body>x</body></html>
    """

    def test_lee_jobposting(self):
        c = extraer_jobposting(self.PAGINA, "https://x.pe/aviso/1", "LinkedIn")
        self.assertIsNotNone(c)
        self.assertEqual(c.puesto, "Analista de Datos")
        self.assertEqual(c.empresa, "Interbank")
        self.assertEqual(c.publicado, date(2026, 7, 30))
        self.assertIn("5500", c.sueldo_texto)
        s = extraer_sueldo(c.sueldo_texto)
        self.assertEqual((s.minimo, s.maximo), (5500, 7200))

    def test_pagina_sin_jsonld(self):
        self.assertIsNone(extraer_jobposting("<html><body>nada</body></html>", "u", "f"))


class TestAlmacen(unittest.TestCase):
    """
    Una oferta que se vuelve a ver tiene que quedar COMPLETA en la base.
    El bug que esto vigila: se guardaba el puntaje nuevo sobre el contenido
    viejo, y la web mostraba ofertas con score 95 y cero funciones.
    """

    def setUp(self):
        import tempfile
        from motor.almacen import Almacen
        from motor.modelos import Oferta

        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.almacen = Almacen(self.tmp.name)
        self.Oferta = Oferta

    def tearDown(self):
        import os
        self.almacen.cerrar()
        os.unlink(self.tmp.name)

    def _oferta(self, **kw):
        base = dict(
            huella=self.Oferta.calcular_huella("Trabajador Social", "Inabif", "Huancavelica"),
            fuente="Estado", url="https://x.pe/1", puesto="Trabajador Social",
            empresa="Inabif", ciudad="Huancavelica", categoria="Salud",
            sueldo_min=3000, sueldo_max=3000, publicado=date.today(),
        )
        base.update(kw)
        return self.Oferta(**base)

    def test_la_segunda_vez_refresca_el_contenido(self):
        # Primera pasada: sin funciones, rechazada.
        self.assertEqual(self.almacen.guardar(self._oferta(
            funciones=[], requisitos=["Título profesional"], score=61, aprobada=False,
        )), "nueva")

        # Segunda: el PDF entregó las funciones y ahora aprueba.
        self.assertEqual(self.almacen.guardar(self._oferta(
            funciones=["Atender a las familias derivadas por la unidad de protección"],
            requisitos=["Título profesional de trabajador social", "2 años de experiencia"],
            beneficios=["Planilla CAS con EsSalud", "30 días de vacaciones"],
            resumen="Convocatoria CAS para trabajador social",
            score=95, aprobada=True,
        )), "actualizada")

        guardadas = self.almacen.aprobadas()
        self.assertEqual(len(guardadas), 1)
        fila = guardadas[0]
        self.assertEqual(fila["score"], 95)
        self.assertEqual(len(fila["funciones"]), 1)       # ← el bug vivía aquí
        self.assertEqual(len(fila["requisitos"]), 2)
        self.assertEqual(len(fila["beneficios"]), 2)
        self.assertIn("trabajador social", fila["resumen"])

    def test_depurar_saca_lo_que_ya_no_sirve(self):
        """
        Sin esto, una oferta guardada la semana pasada se seguía publicando
        aunque su plazo hubiera cerrado ayer: nadie la volvía a mirar.
        """
        from datetime import timedelta

        buena = self._oferta(
            huella="a" * 16, puesto="Vigente", funciones=["Atender casos"],
            score=85, aprobada=True, publicado=date.today() - timedelta(days=2),
            vence=date.today() + timedelta(days=5))
        cerrada = self._oferta(
            huella="b" * 16, puesto="Cerrada", funciones=["Atender casos"],
            score=85, aprobada=True, publicado=date.today() - timedelta(days=10),
            vence=date.today() - timedelta(days=1))
        sin_fecha_vieja = self._oferta(
            huella="c" * 16, puesto="Sin fecha y vieja", funciones=["Atender casos"],
            score=85, aprobada=True, publicado=date.today() - timedelta(days=40))
        sin_fecha_nueva = self._oferta(
            huella="d" * 16, puesto="Sin fecha reciente", funciones=["Atender casos"],
            score=85, aprobada=True, publicado=date.today() - timedelta(days=3))

        for o in (buena, cerrada, sin_fecha_vieja, sin_fecha_nueva):
            self.almacen.guardar(o)
        self.assertEqual(len(self.almacen.aprobadas()), 4)

        quitadas = self.almacen.depurar()
        self.assertEqual(quitadas["plazo cerrado"], 1)
        self.assertEqual(quitadas["sin fecha y vieja"], 1)

        vigentes = {f["puesto"] for f in self.almacen.aprobadas()}
        self.assertEqual(vigentes, {"Vigente", "Sin fecha reciente"})

    def test_depurar_dos_veces_no_cuenta_de_nuevo(self):
        from datetime import timedelta
        self.almacen.guardar(self._oferta(
            funciones=["Atender casos"], score=85, aprobada=True,
            publicado=date.today() - timedelta(days=10),
            vence=date.today() - timedelta(days=1)))
        self.assertEqual(self.almacen.depurar()["plazo cerrado"], 1)
        self.assertEqual(self.almacen.depurar(), {})

    def test_recuerda_las_urls_ya_revisadas(self):
        """
        Lo que permite retomar una corrida cortada: si la laptop se suspendió a
        mitad de camino, al reanudar no se vuelve a descargar lo ya visto.
        """
        self.almacen.guardar(self._oferta(url="https://x.pe/aviso-1",
                                          funciones=["Atender casos"], aprobada=True))
        self.almacen.guardar(self._oferta(huella="z" * 16, url="https://x.pe/aviso-2",
                                          puesto="Otro", aprobada=False))

        vistas = self.almacen.urls_vistas()
        # También las rechazadas: revisarlas de nuevo sería perder el tiempo igual.
        self.assertEqual(vistas, {"https://x.pe/aviso-1", "https://x.pe/aviso-2"})
        self.assertNotIn("https://x.pe/aviso-3", vistas)

    def test_la_corrida_diaria_no_repite_trabajo(self):
        """
        El caso que importa: la corrida es cada 24 horas. Si la memoria durara
        menos que eso, cada noche se volvería a descargar todo.
        """
        self.almacen.guardar(self._oferta(
            huella="a" * 16, url="https://x.pe/rechazada", puesto="Sin sueldo",
            aprobada=False))
        self.almacen.guardar(self._oferta(
            huella="b" * 16, url="https://x.pe/aprobada", puesto="Con sueldo",
            funciones=["Atender casos"], aprobada=True))

        # Al día siguiente, las dos siguen sin necesidad de revisarse.
        self.almacen.con.execute(
            "UPDATE ofertas SET visto_ultima_vez = datetime('now', '-25 hours')")
        self.almacen.con.commit()
        self.assertEqual(len(self.almacen.urls_a_saltar()), 2)

    def test_una_aprobada_se_revisa_cada_semana(self):
        self.almacen.guardar(self._oferta(
            huella="b" * 16, url="https://x.pe/aprobada",
            funciones=["Atender casos"], aprobada=True))
        self.almacen.con.execute(
            "UPDATE ofertas SET visto_ultima_vez = datetime('now', '-9 days')")
        self.almacen.con.commit()
        self.assertEqual(self.almacen.urls_a_saltar(), set())

    def test_una_rechazada_se_deja_en_paz_un_mes(self):
        """Una empresa que no puso el sueldo no vuelve a entrar a ponerlo."""
        self.almacen.guardar(self._oferta(
            huella="a" * 16, url="https://x.pe/rechazada", aprobada=False))
        for dias, esperado in ((9, 1), (40, 0)):
            with self.subTest(dias=dias):
                self.almacen.con.execute(
                    f"UPDATE ofertas SET visto_ultima_vez = datetime('now', '-{dias} days')")
                self.almacen.con.commit()
                self.assertEqual(len(self.almacen.urls_a_saltar()), esperado)

    def test_lo_visto_hace_mucho_se_vuelve_a_revisar(self):
        self.almacen.guardar(self._oferta(url="https://x.pe/viejo", aprobada=True))
        self.almacen.con.execute(
            "UPDATE ofertas SET visto_ultima_vez = datetime('now', '-3 days')")
        self.almacen.con.commit()
        self.assertEqual(self.almacen.urls_vistas(horas=20), set())

    def test_repara_los_titulos_ya_guardados(self):
        """
        Las mejoras al limpiador no alcanzan a lo que ya está en la base: solo
        se reescribe cuando el motor vuelve a ver el aviso, y eso tarda semanas.
        """
        sucio = ("¡GANA MÁS DE 1800 SOLES! OPERARIO DE PRODUCCIÓN — STA ANITA / "
                 "PLANILLA COMPLETA + ALIMENTACIÓN")
        self.almacen.guardar(self._oferta(huella="s" * 16, puesto=sucio,
                                          funciones=["Atender"], aprobada=True))

        self.assertEqual(self.almacen.limpiar_titulos(), 1)
        self.assertEqual(self.almacen.aprobadas()[0]["puesto"], "Operario de Producción")
        # Correrlo de nuevo no cambia nada: es idempotente.
        self.assertEqual(self.almacen.limpiar_titulos(), 0)

    def test_no_se_duplica_la_misma_oferta(self):
        for _ in range(3):
            self.almacen.guardar(self._oferta(funciones=["Atender a las familias"],
                                              score=80, aprobada=True))
        self.assertEqual(self.almacen.estadisticas()["total_procesadas"], 1)


class TestPipelineDemo(unittest.TestCase):

    def setUp(self):
        self.ofertas = [procesar_cruda(c) for c in FuenteDemo().recolectar()]

    def test_aprueba_las_completas_y_bota_las_vagas(self):
        aprobadas = [o for o in self.ofertas if o.aprobada]
        rechazadas = [o for o in self.ofertas if not o.aprobada]
        self.assertEqual(len(aprobadas), 5, [o.puesto for o in aprobadas])
        self.assertEqual(len(rechazadas), 3, [o.puesto for o in rechazadas])

    def test_toda_aprobada_tiene_sueldo_y_los_tres_bloques(self):
        for o in (x for x in self.ofertas if x.aprobada):
            with self.subTest(puesto=o.puesto):
                self.assertGreater(o.sueldo_min, 0)
                self.assertGreaterEqual(len(o.funciones), 3)
                self.assertGreaterEqual(len(o.requisitos), 3)
                self.assertGreaterEqual(len(o.beneficios), 2)
                self.assertTrue(o.categoria)
                self.assertTrue(o.ciudad)

    def test_motivos_de_rechazo_son_los_esperados(self):
        por_puesto = {o.puesto: o for o in self.ofertas}
        self.assertIn("convenir", " ".join(por_puesto["Analista de Recursos Humanos"].motivos_rechazo).lower())
        self.assertTrue(por_puesto["Operario de Producción"].motivos_rechazo)
        self.assertTrue(any("días" in m for m in por_puesto["Jefe de Tienda"].motivos_rechazo))

    def test_huella_colapsa_el_mismo_aviso_en_dos_portales(self):
        from motor.modelos import Oferta
        a = Oferta.calcular_huella("Asistente Contable", "Ferreycorp", "Lima")
        b = Oferta.calcular_huella("ASISTENTE CONTABLE (urgente)", "ferreycorp", "lima")
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main(verbosity=2)
