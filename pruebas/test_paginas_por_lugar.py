"""
El dato que decide cuándo hacer las páginas por lugar.

"Trabajos en Arequipa con sueldo" es lo que la gente escribe en Google, y hoy
el sitio no tiene nada que aparezca para eso. Es de los pendientes con más
posible retorno.

Pero hay una condición previa: **una página casi vacía hace más daño que no
tenerla.** Google la lee como señal de sitio de baja calidad, y esa señal
mancha al resto. Así que antes de hacerlas hay que saber cuántas ofertas
publicadas tiene cada departamento — y ese número no estaba a la vista en
ningún lado. Había que correr una recolección de 45 minutos para enterarse.

Ahora sale en `motor stats`, que también corre en el flujo de publicar (que
tarda menos de un minuto).

Va **por departamento y no por ciudad** a propósito: la gente busca "trabajo
en Cusco", no "trabajo en Wanchaq", y agrupando así una provincia junta lo que
suelto no alcanzaría para nada.
"""
from __future__ import annotations

import unittest
from datetime import date

from motor.almacen import Almacen
from motor.modelos import Oferta


def _oferta(puesto: str, ciudad: str, departamento: str,
            aprobada: bool = True) -> Oferta:
    return Oferta(
        huella=Oferta.calcular_huella(puesto, "Acme", ciudad),
        url=f"https://ejemplo.pe/{puesto}-{ciudad}".lower().replace(" ", "-"),
        puesto=puesto, empresa="Acme", fuente="Bumeran",
        ciudad=ciudad, departamento=departamento,
        sueldo_min=1500, sueldo_max=1500,
        funciones=["a", "b", "c"], requisitos=["a", "b", "c"],
        beneficios=["planilla", "eps"],
        publicado=date.today(), aprobada=aprobada, score=80,
    )


class PruebaRepartoPorDepartamento(unittest.TestCase):

    def setUp(self):
        self.al = Almacen(":memory:")

    def guardar(self, *ofertas):
        for o in ofertas:
            self.al.guardar(o)

    def test_agrupa_las_ciudades_de_un_mismo_departamento(self):
        """
        Cusco capital y Urubamba son dos ciudades, pero quien busca escribe
        "trabajo en Cusco". Separadas no alcanzarían para nada; juntas sí.
        """
        self.guardar(
            _oferta("Cajero", "Cusco", "Cusco"),
            _oferta("Mozo", "Urubamba", "Cusco"),
            _oferta("Vendedor", "Lima", "Lima"),
        )
        reparto = self.al.estadisticas()["por_departamento"]
        self.assertEqual(reparto["Cusco"], 2)
        self.assertEqual(reparto["Lima"], 1)

    def test_solo_cuenta_lo_publicado(self):
        """
        Lo rechazado no llena una página. Contarlo daría un falso "ya hay
        suficiente" y la página nacería vacía, que es justo lo que se quiere
        evitar.
        """
        self.guardar(
            _oferta("Cajero", "Arequipa", "Arequipa"),
            _oferta("Mozo", "Arequipa", "Arequipa", aprobada=False),
        )
        self.assertEqual(self.al.estadisticas()["por_departamento"]["Arequipa"], 1)

    def test_las_que_no_tienen_ubicación_no_se_reparten_a_dedo(self):
        """
        Una oferta sin departamento no se manda a Lima por descarte: una oferta
        de provincia contada como Lima es peor que una sin contar. Se agrupan
        aparte, a la vista.
        """
        self.guardar(_oferta("Cajero", "", ""))
        reparto = self.al.estadisticas()["por_departamento"]
        self.assertIn("(sin ubicación)", reparto)
        self.assertNotIn("Lima", reparto)

    def test_van_de_mayor_a_menor(self):
        """Para que la respuesta —cuáles ya aguantan— se lea de un vistazo."""
        self.guardar(
            _oferta("A", "Cusco", "Cusco"),
            _oferta("B", "Lima", "Lima"),
            _oferta("C", "Callao", "Lima"),
        )
        self.assertEqual(list(self.al.estadisticas()["por_departamento"]),
                         ["Lima", "Cusco"])


class PruebaElPisoParaHacerUnaPagina(unittest.TestCase):

    def test_el_minimo_es_prudente(self):
        """
        No es una ley, pero sí tiene que existir y no puede ser 1. Si alguien
        lo baja a 2 "para tener más páginas", vuelve el problema que el número
        existe para evitar.
        """
        from motor.__main__ import MINIMO_PARA_PAGINA

        self.assertGreaterEqual(MINIMO_PARA_PAGINA, 5)


if __name__ == "__main__":
    unittest.main()
