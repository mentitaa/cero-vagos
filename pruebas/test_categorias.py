"""
La categoría tiene que decir de qué es el trabajo.

Reportado por Mentita el 7/8/2026: dos avisos que no son prácticas estaban
catalogados como **Prácticas**.

  · "Especialista en Fiscalización de Establecimientos Farmacéuticos", porque
    el aviso habla de "buenas prácticas de almacenamiento".
  · "Supervisor(a) de Energías Renovables", porque su resumen dice
    "supervisar a pasantes estudiantes o profesionales".

Al ir a mirarlo aparecieron TRES fallos distintos, y el tercero era el que
nadie habría encontrado leyendo el código:

1. **Prácticas no es un tema, es un tipo de contrato.** La palabra puede
   aparecer en el cuerpo de cualquier aviso sin que el puesto sea una práctica.
   Ahora solo cuenta si está en el título.

2. **Las pistas repetidas puntuaban doble.** "practicas" y "prácticas" son la
   misma palabra una vez quitadas las tildes, así que una sola aparición sumaba
   dos puntos y ganaba los desempates. Le pasaba a media docena de categorías:
   medico/médico, almacen/almacén, produccion/producción, juridic/jurídic.

3. **Las pistas se buscaban como pedazo de texto, no como palabra.** Por eso
   "Asesor de Cobranza" salía como **Construcción**: la pista "obra" está
   dentro de "c-obra-nza". Y "intern" está dentro de "interna", así que
   cualquier "Asistente de Auditoría Interna" se iba a Prácticas.

El tercero es el que más vale tener vigilado: no da error, no se nota leyendo,
y solo aparece cuando alguien mira una tarjeta y dice "esto no es eso".
"""
from __future__ import annotations

import unittest

from motor.normalizar import PISTAS_CATEGORIA, detectar_categoria
from motor.modelos import CATEGORIAS, sin_tildes


class PruebaAvisosRealesMalCatalogados(unittest.TestCase):

    def test_fiscalizar_buenas_practicas_no_es_una_practica(self):
        cat = detectar_categoria(
            "Especialista en Fiscalización de Establecimientos Farmaceuticos",
            "Fiscalizar el cumplimiento de las buenas prácticas de almacenamiento "
            "y dispensación en establecimientos farmacéuticos.")
        self.assertNotEqual(cat, "Prácticas")
        self.assertEqual(cat, "Salud")

    def test_supervisar_pasantes_no_es_una_practica(self):
        cat = detectar_categoria(
            "Supervisor(a) de Energías Renovables",
            "Supervisar a pasantes estudiantes o profesionales extranjeros que "
            "trabajan con la ONG en campo.")
        self.assertNotEqual(cat, "Prácticas")

    def test_una_practica_de_verdad_si_se_reconoce(self):
        self.assertEqual(
            detectar_categoria("Practicante de Marketing", "Apoyar en campañas."),
            "Prácticas")

    def test_un_trainee_tambien(self):
        """
        Toca Ventas por "comercial", pero quien filtra por Prácticas lo está
        buscando a él. El tipo de contrato manda sobre el tema.
        """
        self.assertEqual(
            detectar_categoria("Trainee Comercial", "Programa para egresados."),
            "Prácticas")


class PruebaLasPistasSonPalabras(unittest.TestCase):
    """
    El fallo silencioso: buscar la pista en cualquier parte del texto en vez
    de al inicio de una palabra.
    """

    def test_cobranza_no_es_construccion(self):
        """'obra' está dentro de 'c-obra-nza'."""
        cat = detectar_categoria(
            "Asesor de Cobranza",
            "Realizar llamadas de cobranza a clientes con obligaciones pendientes.")
        self.assertNotEqual(cat, "Construcción")
        self.assertEqual(cat, "Contabilidad")

    def test_auditoria_interna_no_es_una_practica(self):
        """'intern' está dentro de 'interna'."""
        cat = detectar_categoria(
            "Asistente de Auditoría Interna", "Revisar procesos internos.")
        self.assertNotEqual(cat, "Prácticas")

    def test_un_puesto_internacional_tampoco(self):
        self.assertNotEqual(
            detectar_categoria("Coordinador Internacional de Ventas",
                               "Gestionar clientes del exterior."),
            "Prácticas")

    def test_las_raices_siguen_funcionando(self):
        """
        Muchas pistas son raíces a propósito: tienen que calzar con la palabra
        entera aunque cambie de género o de número.
        """
        casos = [
            ("Enfermera Asistencial", "Atención de pacientes.", "Salud"),
            ("Ingeniero de Producción", "Supervisar la planta.", "Ingeniería"),
            ("Maestro de Obra", "Dirigir la cuadrilla.", "Construcción"),
            ("Abogada Corporativa", "Contratos y litigios.", "Legal"),
        ]
        for puesto, cuerpo, esperada in casos:
            self.assertEqual(detectar_categoria(puesto, cuerpo), esperada, puesto)


class PruebaNingunaPistaSeCuentaDosVeces(unittest.TestCase):

    def test_no_quedan_pistas_duplicadas_al_quitar_tildes(self):
        """
        Vigila el origen del problema, no solo su efecto. Si alguien vuelve a
        escribir la misma pista con y sin tilde, esa categoría empezaría otra
        vez a puntuar doble y a ganar desempates que no le tocan.
        """
        for categoria, pistas in PISTAS_CATEGORIA.items():
            planas = [sin_tildes(p) for p in pistas]
            repetidas = {p for p in planas if planas.count(p) > 1}
            self.assertEqual(repetidas, set(),
                             f"{categoria} repite {repetidas} con y sin tilde")


class PruebaElCatalogoEsCoherente(unittest.TestCase):

    def test_toda_categoria_con_pistas_existe_en_el_catalogo(self):
        for categoria in PISTAS_CATEGORIA:
            self.assertIn(categoria, CATEGORIAS)

    def test_lo_que_no_calza_con_nada_es_Otros(self):
        """Preferible a colgarle una categoría inventada."""
        self.assertEqual(detectar_categoria("Puesto Sin Nombre Claro", ""), "Otros")


if __name__ == "__main__":
    unittest.main()
