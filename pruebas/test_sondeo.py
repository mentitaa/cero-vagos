"""
El sondeo: contar antes de programar.

Estas pruebas están escritas contra los dos errores reales del proyecto, que
fueron el mismo error dos veces — dar por buena una fuente sin mirar adentro:

- **BuscoTrabajo.** Su robots.txt nos deja entrar y es la única bolsa peruana
  fuera del grupo Jobint. Estuvo semanas en pendientes como la fuente que
  faltaba. Tiene **4 empleos activos**, tres de la misma empresa.
- **Las bolsas universitarias.** 501 empresas y 8,287 vacantes, y se
  descartaron igual: **ninguna publica el sueldo**.

Los dos habrían muerto en veinte minutos con este comando. Por eso lo que se
prueba acá no es que el sondeo "funcione", sino que **diga que no** en los dos
casos donde decir que sí costaría una semana de trabajo perdido.
"""
from __future__ import annotations

import unittest
from unittest import mock

from motor.sondeo import Aviso, Sondeo, elegir_lector, informe


def _aviso(puesto: str, sueldo: int = 0, aprobada: bool = False,
           motivos: list[str] | None = None, moneda: str = "PEN") -> Aviso:
    return Aviso(puesto=puesto, sueldo=sueldo, moneda=moneda, aprobada=aprobada,
                 motivos=motivos or [])


class PruebaLosTresNumerosQueDeciden(unittest.TestCase):
    """
    Un sondeo sirve para contestar tres preguntas, y ninguna de las tres es
    "¿nos dejan entrar?". Esa la contestaba `conectar` y no alcanzó nunca.
    """

    def test_cuenta_cuantos_dicen_el_sueldo(self):
        s = Sondeo(url="https://ejemplo.pe", permite=True, avisos=[
            _aviso("Analista", 3000, aprobada=True),
            _aviso("Cajero"),
            _aviso("Vendedor"),
            _aviso("Jefe de Tienda"),
        ])
        self.assertEqual(s.cuantos, 4)
        self.assertEqual(len(s.con_sueldo), 1)
        self.assertEqual(s.porcentaje_con_sueldo, 25)

    def test_publicables_no_es_lo_mismo_que_con_sueldo(self):
        """
        Decir el sueldo es necesario y no es suficiente: todavía hay que traer
        funciones, requisitos y beneficios. Si el sondeo mezclara las dos
        cosas prometería más avisos de los que la corrida real va a entregar,
        que es exactamente la clase de optimismo que este archivo existe para
        evitar.
        """
        s = Sondeo(url="https://ejemplo.pe", permite=True, avisos=[
            _aviso("Analista", 3000, aprobada=True),
            _aviso("Practicante", 1200, aprobada=False,
                   motivos=["No detalla los beneficios"]),
        ])
        self.assertEqual(len(s.con_sueldo), 2)
        self.assertEqual(len(s.publicables), 1)

    def test_agrupa_por_que_se_caen_los_demas(self):
        s = Sondeo(url="https://ejemplo.pe", permite=True, avisos=[
            _aviso("A", motivos=["El aviso no declara sueldo"]),
            _aviso("B", motivos=["El aviso no declara sueldo"]),
            _aviso("C", motivos=["El aviso no declara sueldo", "Faltan requisitos"]),
        ])
        self.assertEqual(s.motivos_mas_comunes[0], ("El aviso no declara sueldo", 3))


class PruebaLosDosErroresQueYaPasaron(unittest.TestCase):

    def test_la_bolsa_universitaria_ninguno_dice_el_sueldo(self):
        """
        El caso de verdad: mucho volumen, empresas serias, y cero sueldos. El
        sondeo tiene que decirlo con todas sus letras, porque el volumen por
        sí solo es convincente y ahí estuvo la trampa.
        """
        s = Sondeo(url="https://bolsa.universidad.pe", permite=True,
                   avisos=[_aviso(f"Practicante {i}") for i in range(20)])

        self.assertFalse(s.vale_la_pena)
        texto = informe(s)
        self.assertIn("NINGUNO dice el sueldo", texto)
        self.assertIn("no escribas el lector", texto)

    def test_buscotrabajo_deja_entrar_y_no_tiene_avisos(self):
        """
        Permiso concedido, cero contenido. `conectar` habría dicho que sí.
        """
        s = Sondeo(url="https://buscotrabajo.pe", permite=True,
                   como_esta_hecha="Web propia, se lee sin navegador",
                   enlaces_vistos=4,
                   avisos=[_aviso("Vendedor"), _aviso("Cajero"),
                           _aviso("Asesor"), _aviso("Repartidor")])

        texto = informe(s)
        self.assertIn("4", texto)
        self.assertIn("no escribas el lector", texto.lower())


class PruebaUnCeroNuncaEsUnVeredicto(unittest.TestCase):
    """
    El error más caro que puede cometer este comando, y ya lo cometió.

    Falabella y Cencosud devolvieron **0 avisos** y el informe los despachó con
    un "No hay avisos que contar. No escribas el lector." Los dos portales
    tienen avisos de sobra: lo que pasó es que el lector genérico no reconoció
    sus enlaces.

    Desde afuera no hay forma de distinguir "está vacía" de "no supe dónde
    mirar". Como no se puede distinguir, no se opina. Es la misma trampa de las
    corridas —*una fuente que devuelve cero sale en verde*— pero peor, porque
    acá el cero venía con un consejo, y un consejo equivocado mata una fuente
    buena y nadie vuelve a mirarla.
    """

    def test_cero_avisos_NO_dice_que_no_escribas_el_lector(self):
        s = Sondeo(url="https://muevete.falabella.com", permite=True,
                   como_esta_hecha="Aplicación en JavaScript, se mira con navegador")
        texto = informe(s)

        self.assertNotIn("No escribas el lector", texto)
        self.assertNotIn("No hay avisos", texto)
        self.assertIn("No supe encontrar los avisos", texto)

    def test_con_cero_dice_QUE_HACER_para_salir_de_la_duda(self):
        """Rendirse sin decir el siguiente paso deja la fuente muerta."""
        s = Sondeo(url="https://muevete.falabella.com", permite=True)
        self.assertIn("probar-url", informe(s))

    def test_distingue_no_encontrarlos_de_no_poder_leerlos(self):
        """
        Son dos problemas distintos y se arreglan distinto. Si encontró 30
        enlaces y no leyó ninguno, los avisos están y falta el lector. Si no
        encontró ni un enlace, ni siquiera supo dónde mirar.
        """
        ciego = informe(Sondeo(url="https://x.pe", permite=True))
        mudo = informe(Sondeo(url="https://x.pe", permite=True, enlaces_vistos=30))

        self.assertIn("No supe encontrar", ciego)
        self.assertIn("30 enlaces", mudo)
        self.assertIn("Los avisos están", mudo)

    def test_el_informe_muestra_los_dos_numeros_por_separado(self):
        """
        Descubrir y leer no son lo mismo, y el informe tiene que dejar ver la
        diferencia sin que haya que interpretarla.
        """
        s = Sondeo(url="https://x.pe", permite=True, enlaces_vistos=25,
                   avisos=[_aviso("Analista", 3000, aprobada=True)])
        texto = informe(s)

        self.assertIn("Enlaces de aviso      25", texto)
        self.assertIn("Avisos que pudo leer  1", texto)

    def test_una_bolsa_que_si_vale_la_pena_lo_dice(self):
        s = Sondeo(url="https://empresa.pe/careers", permite=True, avisos=(
            [_aviso(f"Con sueldo {i}", 2500, aprobada=True) for i in range(6)]
            + [_aviso(f"Sin sueldo {i}") for i in range(4)]))

        self.assertTrue(s.vale_la_pena)
        self.assertIn("Vale la pena", informe(s))


class PruebaSabeMirarLoDificil(unittest.TestCase):
    """
    La primera versión del sondeo se rendía ante dos cosas: "está hecha en
    JavaScript" y "ese sistema no tiene lector escrito". Con eso se negó a
    contar **Falabella y Cencosud** — las dos bolsas grandes, o sea las dos
    únicas que había que medir. Un sondeo que solo sondea lo fácil no sirve
    para decidir nada.

    Y lo tonto del caso: el navegador ya estaba. Bumeran y Laborum se leen con
    Playwright todas las madrugadas.
    """

    def _lector(self, url, html, con_navegador=True):
        with mock.patch("motor.sondeo.HAY_PLAYWRIGHT", con_navegador):
            return elegir_lector(url, html, "Prueba")

    def test_una_pagina_en_javascript_se_mira_con_navegador(self):
        """El caso Falabella."""
        fuente, como = self._lector("https://muevete.falabella.com",
                                    "You need to enable JavaScript to run this app.")
        self.assertIsNotNone(fuente, "se rindió ante una página que sí se puede mirar")
        self.assertTrue(fuente.necesita_render)
        self.assertIn("navegador", como)

    def test_un_ats_sin_lector_propio_tambien(self):
        """
        El caso Cencosud. Para CONTAR no hace falta el lector definitivo: un
        aviso bien hecho publica sus datos en el formato que pide Google, y eso
        se lee igual venga de Cornerstone o de Workday. El lector prolijo se
        escribe después, y solo si el sondeo dijo que valía la pena.
        """
        fuente, como = self._lector(
            "https://cencosud.csod.com/ux/ats/careersite/10/home?c=cencosud",
            "<html>" + "x" * 5000 + "</html>")
        self.assertIsNotNone(fuente)
        self.assertTrue(fuente.necesita_render)
        self.assertIn("Cornerstone", como)

    def test_sin_navegador_instalado_dice_como_instalarlo(self):
        """
        Rendirse está bien; rendirse sin decir qué hacer, no. El comando va
        completo, para copiar y pegar.
        """
        fuente, como = self._lector("https://muevete.falabella.com",
                                    "You need to enable JavaScript to run this app.",
                                    con_navegador=False)
        self.assertIsNone(fuente)
        self.assertIn("pip3 install playwright", como)

    def test_lo_que_ya_tiene_lector_NO_abre_el_navegador(self):
        """
        Greenhouse y Lever tienen API pública: abrir un navegador para leer un
        JSON sería tardarse veinte veces más para el mismo dato.
        """
        fuente, como = self._lector("https://boards.greenhouse.io/acme", "")
        self.assertIn("Greenhouse", como)
        self.assertFalse(getattr(fuente, "necesita_render", False))

    def test_una_web_normal_sigue_leyendose_sin_navegador(self):
        fuente, como = self._lector("https://empresa.pe/trabaja-con-nosotros",
                                    "<html>" + "x" * 5000 + "</html>")
        self.assertFalse(fuente.necesita_render)
        self.assertIn("sin navegador", como)


class PruebaReconoceLosEnlacesDeVerdad(unittest.TestCase):
    """
    Cada bolsa le puso otro nombre a la página de un aviso. Si el sondeo no
    reconoce el nombre, no descubre ni un enlace y reporta un cero — que ya
    sabemos que no es un cero.

    Las direcciones de acá son reales, no inventadas.
    """

    def _encuentra(self, url_de_aviso: str) -> bool:
        import re
        from motor.sondeo import _PATRON_AVISO
        return bool(re.search(_PATRON_AVISO, url_de_aviso))

    def test_falabella(self):
        # La que mandó Mentita el 13/8/2026.
        self.assertTrue(self._encuentra(
            "https://muevete.falabella.com/detalle-oferta/615876/external"))

    def test_trabajos_diarios(self):
        """
        Una letra. El patrón decía "trabaja" y sus avisos viven en /trabajo/,
        así que no calzaba ni uno — y esta resultó ser la mejor fuente privada
        que se ha encontrado. Un cero por una vocal.
        """
        self.assertTrue(self._encuentra(
            "https://pe.trabajosdiarios.com/trabajo/3075258/"
            "auxiliar-de-almacen-y-despacho-en-lima"))

    def test_los_nombres_de_cada_sistema(self):
        for url in ("https://x.csod.com/ux/ats/careersite/10/requisition/4821",
                    "https://x.myworkdayjobs.com/es/carreras/job/Lima/Analista_R-9",
                    "https://boards.greenhouse.io/acme/jobs/5512",
                    "https://empresa.pe/vacantes/asistente-de-almacen",
                    "https://empresa.pe/oportunidades/practicante-legal"):
            with self.subTest(url=url):
                self.assertTrue(self._encuentra(url))

    def test_no_confunde_el_menu_con_un_aviso(self):
        """
        Al descubrir por nombre, media web calza. Lo que NO puede pasar es que
        el sondeo cuente la página de contacto como si fuera una oferta: sería
        un número inflado, que es la otra forma de mentir.
        """
        for url in ("https://empresa.pe/nosotros",
                    "https://empresa.pe/contacto",
                    "https://empresa.pe/politica-de-privacidad"):
            with self.subTest(url=url):
                self.assertFalse(self._encuentra(url))


class PruebaCuandoNoSePuedeNiEntrar(unittest.TestCase):

    def test_sin_permiso_no_inventa_numeros(self):
        """
        La regla 6: si no se puede leer el robots.txt, se asume que no hay
        permiso. El informe no debe rellenar el hueco con ceros que parezcan
        una medición.
        """
        s = Sondeo(url="https://cerrado.pe", permite=False,
                   problema="No se puede entrar: robots.txt no responde")
        texto = informe(s)

        self.assertIn("NO", texto)
        self.assertIn("No se pudo contar nada", texto)
        self.assertNotIn("Vale la pena", texto)

    def test_si_necesita_navegador_lo_dice_y_no_finge_haber_contado(self):
        s = Sondeo(url="https://muevete.falabella.com", permite=True,
                   problema="Aplicación en JavaScript: hace falta navegador (Playwright)",
                   como_esta_hecha="Aplicación en JavaScript: hace falta navegador (Playwright)")
        texto = informe(s)

        self.assertIn("navegador", texto)
        self.assertIn("No se pudo contar nada", texto)


class PruebaElSondeoNoTocaLaBase(unittest.TestCase):

    def test_no_importa_el_almacen(self):
        """
        Un sondeo es una pregunta, no una recolección. Si importara el almacén
        alguien terminaría guardando lo que sondeó, y una muestra de prueba
        entraría al sitio como si fuera oferta real.
        """
        import pathlib
        fuente = (pathlib.Path(__file__).resolve().parent.parent
                  / "motor" / "sondeo.py").read_text(encoding="utf-8")
        self.assertNotIn("Almacen", fuente)
        self.assertNotIn("guardar(", fuente)


if __name__ == "__main__":
    unittest.main()
