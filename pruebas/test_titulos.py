"""
Pruebas de la deducción del puesto.

El problema que resuelven: hay avisos completos —con sueldo, funciones,
requisitos y beneficios— cuyo título no dice qué es el trabajo. Dice la marca
("Papa Johns"), el local ("Primax Cerro Azul") o un gancho ("Trabaja cerca al
Parque de la Amistad"). Publicar eso es exactamente la oferta vaga que el
motor existe para rechazar, solo que en el titular.

La regla es deducir el oficio **del texto del propio aviso**, y si el aviso no
lo nombra en ninguna parte, rechazarlo. Lo que estas pruebas más vigilan es la
segunda mitad: que el motor **no invente** un cargo cuando no lo sabe.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from motor.normalizar import deducir_puesto, titulo_nombra_el_puesto  # noqa: E402


class PruebaReconocerTitulos(unittest.TestCase):

    def test_reconoce_titulos_que_si_dicen_el_oficio(self):
        for titulo in ("Asistente Contable", "Operario de Producción",
                       "Analista de Datos", "Practicante de Marketing",
                       "Jefe de Tienda", "Despachador de Combustible"):
            with self.subTest(titulo=titulo):
                self.assertTrue(titulo_nombra_el_puesto(titulo))

    def test_reconoce_cargos_de_varias_palabras(self):
        """
        "Customer Service" y "Back Office" son el nombre real del puesto
        aunque no contengan ninguna palabra de oficio suelta. Sin esto se
        rechazaban avisos perfectamente claros.
        """
        for titulo in ("Customer Service", "Back Office", "Atención al Cliente",
                       "Call Center", "Community Manager"):
            with self.subTest(titulo=titulo):
                self.assertTrue(titulo_nombra_el_puesto(titulo))

    def test_detecta_los_titulos_que_no_dicen_nada(self):
        for titulo in ("Papa Johns", "Primax Cerro Azul", "Apparka",
                       "Trabaja cerca al Parque de la Amistad", "Básico",
                       "Planta Papa Johns"):
            with self.subTest(titulo=titulo):
                self.assertFalse(titulo_nombra_el_puesto(titulo))


class PruebaDeducirElPuesto(unittest.TestCase):

    def test_saca_el_oficio_de_las_funciones(self):
        puesto = deducir_puesto(
            resumen="",
            funciones=["Anfitrión de estacionamientos: recibir a los clientes"],
            requisitos=["Secundaria completa"])
        self.assertIn("Anfitrión", puesto)

    def test_conserva_el_complemento_del_cargo(self):
        """«Despachador» solo es peor que «Despachador de Combustible»."""
        puesto = deducir_puesto(
            funciones=["Despachador de combustible en estación de servicio"])
        self.assertEqual(puesto.lower(), "despachador de combustible")

    def test_no_mira_los_beneficios(self):
        """
        Ahí viven "seguro médico" y "servicio de limpieza". Mirándolos, un
        puesto de call center se deducía como médico. Un beneficio nunca dice
        cuál es el trabajo, así que no se le pregunta.
        """
        puesto = deducir_puesto(
            resumen="", funciones=["Gestionar solicitudes de baja del servicio móvil"],
            requisitos=["Disponibilidad para horarios rotativos"])
        self.assertNotIn("dic", puesto.lower())   # médico / medicas

    # ------------------------------------------------------------------
    # Lo más importante: negarse a inventar.
    # ------------------------------------------------------------------

    def test_devuelve_vacio_si_el_aviso_no_nombra_ningun_oficio(self):
        self.assertEqual(deducir_puesto(
            resumen="Impulsa tu carrera con nosotros",
            funciones=["Preparar la masa para pizzas según las indicaciones"],
            requisitos=["Experiencia mínima de 3 meses en plantas de alimentos"]), "")

    def test_no_inventa_con_el_aviso_vacio(self):
        self.assertEqual(deducir_puesto(), "")
        self.assertEqual(deducir_puesto(resumen="", funciones=[], requisitos=[]), "")

    def test_no_devuelve_media_oracion_como_cargo(self):
        """Un cargo son pocas palabras, no una frase entera."""
        puesto = deducir_puesto(
            funciones=["El asistente que buscamos deberá encargarse de coordinar "
                       "con proveedores, revisar facturas y archivar documentos"])
        self.assertTrue(puesto == "" or len(puesto.split()) <= 4, puesto)


class PruebaElMotorRechazaLoQueNoSabe(unittest.TestCase):
    """La regla completa, tal como corre en el motor."""

    def _aviso(self, titulo: str, funciones: list[str]) -> object:
        from datetime import date
        from motor.modelos import OfertaCruda
        from motor.pipeline import procesar_cruda

        cuerpo = ("<h3>Funciones</h3><ul>"
                  + "".join(f"<li>{f}</li>" for f in funciones) + "</ul>"
                  "<h3>Requisitos</h3><ul><li>Secundaria completa</li>"
                  "<li>Un año de experiencia en el rubro</li>"
                  "<li>Disponibilidad inmediata para trabajar</li></ul>"
                  "<h3>Beneficios</h3><ul><li>Planilla completa desde el primer día</li>"
                  "<li>Seguro médico EPS y bonos por cumplimiento</li></ul>")
        return procesar_cruda(OfertaCruda(
            fuente="Bumeran", url="https://origen.pe/x", puesto=titulo,
            empresa="Empresa", ubicacion_texto="Lima", sueldo_texto="S/ 1,500 mensual",
            descripcion_html=cuerpo, publicado=date.today()))

    def test_un_aviso_con_titulo_de_marca_sale_publicado_con_el_oficio(self):
        oferta = self._aviso("Primax Cerro Azul",
                             ["Despachador de combustible y atención al cliente"])
        self.assertNotEqual(oferta.puesto, "Primax Cerro Azul")
        self.assertTrue(titulo_nombra_el_puesto(oferta.puesto), oferta.puesto)

    def test_un_aviso_que_nunca_dice_el_oficio_se_rechaza(self):
        oferta = self._aviso("Papa Johns",
                             ["Preparar la masa para pizzas",
                              "Cargar el saco de harina para cernir y mezclar"])
        self.assertFalse(oferta.aprobada)
        self.assertIn("El aviso no dice qué puesto es", oferta.motivos_rechazo)

    def test_un_titulo_que_ya_esta_bien_no_se_toca(self):
        oferta = self._aviso("Asistente Contable",
                             ["Registrar las operaciones contables del día"])
        self.assertEqual(oferta.puesto, "Asistente Contable")


if __name__ == "__main__":
    unittest.main()
