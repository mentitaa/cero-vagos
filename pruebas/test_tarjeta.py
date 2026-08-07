"""
Lo que la tarjeta le dice a quien no sabe cómo funciona el motor.

Esto salió de un focus group improvisado: Mentita compartió la web con varias
personas y coincidieron en lo mismo sin ponerse de acuerdo.

**El número de score se leía como una nota al TRABAJO.** Veían una oferta de
S/ 4,000 con 89 al lado de una de S/ 500 con 98 y no entendían nada. Es
lógico: nadie que entra a una bolsa de trabajo sabe que ese número mide si el
AVISO está completo.

Y el número nunca pudo servirles de nada, porque **todo lo que se publica ya
pasó el filtro**. Su único efecto posible era invitar a comparar en una
dimensión que significa otra cosa.

Se reemplazó por las cuatro cosas que Cero Vagos promete, marcadas una por una
(7/8/2026). Es el mismo score dicho en lo que significa, se explica solo, y no
revela la fórmula: que un aviso traiga sueldo no dice cuántos puntos vale ni
dónde está el umbral.

De paso se quitó la inicial de la empresa del recuadro izquierdo. Nadie sabía
qué era —ni Mentita— y no identificaba nada: el color salía de la POSICIÓN de
la tarjeta, así que la misma empresa cambiaba de color al filtrar o al dar
"Ver más".
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


class PruebaLaTarjetaNoMuestraElScore(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.html = (RAIZ / "index.html").read_text(encoding="utf-8")

    def test_el_numero_no_aparece_en_la_tarjeta(self):
        self.assertNotIn("job__score", self.html,
                         "volvió el recuadro del score a la tarjeta")

    def test_el_numero_tampoco_aparece_al_abrir_la_oferta(self):
        self.assertNotIn("SCORE DE COMPLETITUD", self.html,
                         "el número volvió a la ficha de la oferta")

    def test_se_muestran_las_cuatro_cosas_en_su_lugar(self):
        self.assertIn("loQueTiene", self.html)
        self.assertIn("job__tiene", self.html)
        for palabra in ("Sueldo", "Funciones", "Requisitos", "Beneficios"):
            self.assertIn(f"'{palabra}'", self.html,
                          f"falta la marca de {palabra}")

    def test_las_cuatro_marcas_salen_tambien_al_abrir_la_oferta(self):
        """La tarjeta y la ficha tienen que contar lo mismo."""
        self.assertEqual(self.html.count("loQueTiene(o)"), 2)

    def test_el_score_sigue_existiendo_por_dentro(self):
        """
        Quitarlo de la vista no es quitarlo del motor: sigue decidiendo qué se
        publica y en qué orden. Solo dejó de mostrarse.
        """
        datos = json.loads((RAIZ / "datos" / "ofertas.json").read_text(encoding="utf-8"))
        if datos["ofertas"]:
            self.assertIn("score", datos["ofertas"][0])


class PruebaSeFueLaInicialDeLaEmpresa(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.html = (RAIZ / "index.html").read_text(encoding="utf-8")

    def test_no_queda_el_recuadro_de_la_inicial(self):
        self.assertNotIn("job__logo", self.html)

    def test_no_queda_la_paleta_que_pintaba_por_posicion(self):
        """
        Era lo peor del asunto: `COLORES[i % COLORES.length]` toma el color de
        la POSICIÓN de la tarjeta, no de la empresa. Parecía codificar algo y
        no codificaba nada.
        """
        self.assertNotIn("COLORES", self.html)


class PruebaLasMarcasSalenDeLosDatosReales(unittest.TestCase):
    """
    Las marcas no se escriben a mano: se deducen de lo que el aviso trae. Si un
    día el exportador deja de mandar las listas, las tarjetas se quedarían sin
    marcas y nadie se enteraría.
    """

    def marcas(self, oferta: dict) -> list[str]:
        """La misma cuenta que hace `loQueTiene` en index.html."""
        return [nombre for nombre, hay in (
            ("Sueldo", (oferta.get("min") or 0) > 0),
            ("Funciones", len(oferta.get("funciones") or []) > 0),
            ("Requisitos", len(oferta.get("requisitos") or []) > 0),
            ("Beneficios", len(oferta.get("beneficios") or []) > 0),
        ) if hay]

    def setUp(self):
        datos = json.loads((RAIZ / "datos" / "ofertas.json").read_text(encoding="utf-8"))
        self.ofertas = datos["ofertas"]

    def test_toda_oferta_publicada_declara_su_sueldo(self):
        """La regla 1, vista desde la tarjeta."""
        for o in self.ofertas:
            self.assertIn("Sueldo", self.marcas(o), f"{o['puesto']} sin sueldo")

    def test_ninguna_oferta_se_queda_sin_marcas(self):
        for o in self.ofertas:
            self.assertGreaterEqual(len(self.marcas(o)), 3,
                                    f"{o['puesto']} mostraría menos de 3 marcas")

    def test_las_que_muestran_tres_son_del_estado_y_les_faltan_funciones(self):
        """
        Decisión de Mentita (7/8/2026): que se vean tres marcas está bien. Es
        honesto — la convocatoria no publica sus funciones — y la ficha explica
        que están en las bases del concurso.

        Lo que NO estaría bien es que a una oferta privada le falte algo: esas
        pasan por la vara completa.
        """
        for o in self.ofertas:
            faltantes = set(("Sueldo", "Funciones", "Requisitos", "Beneficios")) - set(self.marcas(o))
            if not faltantes:
                continue
            self.assertEqual(faltantes, {"Funciones"},
                             f"{o['puesto']} no muestra {faltantes}")
            self.assertIn("estado", o["fuente"].lower() + o["fuente"].lower(),
                          f"{o['puesto']} es privada y le faltan funciones")


if __name__ == "__main__":
    unittest.main()
