"""
Pruebas del listado de la portada: que no se pinte todo de una.

Por qué existen: mientras hubo 30 ofertas daba igual dibujarlas todas. El día
que haya 200, un solo scroll de 67 filas entierra el pie de página, y ahí es
donde están las alertas y los enlaces legales. Nadie llega nunca.

La solución fue mostrar seis filas y dejar el resto detrás de un "Ver más".
Es el tipo de cosa que alguien puede deshacer sin darse cuenta al simplificar
una función. Estas pruebas leen el HTML y avisan si vuelve.

El comportamiento en sí (que los clics sumen y que el botón desaparezca al
final) se probó con un navegador simulado el 4/8/2026: 50 ofertas, 8 clics,
la tanda se reinicia al filtrar y el mensaje de "no hay chamba" no deja botón
huérfano. Acá queda lo que se puede vigilar sin navegador.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


class PruebaLaBarraDeArribaLlegaAlBorde(unittest.TestCase):
    """
    La barra de navegación va de punta a punta, como el marquee de arriba y el
    hero de abajo.

    Estuvo limitada a 1360px y centrada, y en una pantalla más ancha quedaba
    crema vacía a la derecha del botón de alertas, sin ningún borde que la
    cerrara. Mentita lo vio enseguida: «el botón parece pegado a la izquierda».
    No estaba mal alineado — es que la barra se acababa antes que la pantalla.

    El resto de la página sí va a 1360px con `.wrap`, y así debe seguir: esas
    son columnas de texto y leerlas de borde a borde es incómodo. Lo que va al
    borde son las franjas de color.
    """

    @classmethod
    def setUpClass(cls):
        cls.html = (RAIZ / "index.html").read_text(encoding="utf-8")

    def _regla(self, selector: str) -> str:
        """Devuelve lo que hay entre llaves de una regla CSS."""
        m = re.search(re.escape(selector) + r"\{([^}]*)\}", self.html)
        self.assertIsNotNone(m, f"no se encontró la regla {selector}")
        return m.group(1)

    def test_la_barra_no_esta_limitada(self):
        self.assertNotIn("max-width", self._regla(".nav"),
                         "volvió el tope de ancho a la barra: el botón de "
                         "alertas se va a ver otra vez abandonado")

    def test_las_columnas_de_texto_si_estan_limitadas(self):
        """Lo de arriba no debe contagiarse al contenido."""
        self.assertIn("max-width:1360px", self._regla(".wrap"))


class PruebaElMenuDeCelularSeCierra(unittest.TestCase):
    """
    Al elegir una opción del menú de hamburguesa, el menú se cierra.

    Sin eso se quedaba abierto **tapando justo lo que fuiste a ver**: los tres
    primeros enlaces (Ofertas, El filtro, Fuentes) llevan a la misma página,
    así que al tocarlos la página baja y el menú sigue encima. En computadora
    no se nota, porque ese menú va en la barra y nunca se abre.

    Lo reportó Renzo el 7/8/2026.
    """

    @classmethod
    def setUpClass(cls):
        cls.html = (RAIZ / "index.html").read_text(encoding="utf-8")

    def test_los_enlaces_cierran_el_menu(self):
        self.assertIn("classList.remove('open')", self.html,
                      "nada cierra el menú al elegir una opción")

    def test_el_boton_lo_sigue_abriendo(self):
        self.assertIn("classList.toggle('open')", self.html)

    def test_los_enlaces_del_menu_llevan_a_la_misma_pagina(self):
        """
        Es la razón de ser del arreglo. Si algún día todos llevaran a otra
        página, cerrarlo dejaría de importar — pero mientras sean anclas de
        esta misma, el menú tapa el destino.
        """
        menu = re.search(r'<nav class="nav__links".*?</nav>', self.html, re.S).group(0)
        self.assertTrue(re.search(r'href="#\w+"', menu),
                        "el menú ya no tiene enlaces a esta misma página")


class PruebaListadoPorTandas(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.html = (RAIZ / "index.html").read_text(encoding="utf-8")

    def test_existe_el_hueco_donde_va_el_boton(self):
        """
        El botón NO puede vivir dentro de la grilla: sería una celda más y se
        pondría al costado de una tarjeta en vez de debajo de todas.
        """
        self.assertIn('id="masbox"', self.html)
        grid = self.html.index('id="grid"')
        mas = self.html.index('id="masbox"')
        self.assertLess(grid, mas, "el botón debe ir DESPUÉS de la grilla")

    def test_no_se_dibujan_todas_las_ofertas_de_una(self):
        """El corazón del asunto: la lista se corta antes de pintarse."""
        self.assertRegex(
            self.html, r"slice\(\s*0\s*,\s*tope\s*\)",
            "el listado volvió a pintarse entero de una sola vez",
        )

    def test_la_tanda_son_seis_filas(self):
        m = re.search(r"const FILAS_POR_TANDA\s*=\s*(\d+)", self.html)
        self.assertIsNotNone(m, "desapareció el tamaño de la tanda")
        filas = int(m.group(1))
        self.assertGreaterEqual(filas, 3, "menos de 3 filas obliga a demasiados clics")
        self.assertLessEqual(filas, 10, "más de 10 filas ya es el scroll que queríamos evitar")

    def test_las_columnas_se_le_preguntan_al_navegador(self):
        """
        Fijar la tanda en 18 tarjetas sería correcto en una laptop y absurdo en
        un teléfono, donde la grilla tiene una sola columna: 18 tarjetas serían
        18 filas, justo lo que se quería evitar.
        """
        self.assertIn("gridTemplateColumns", self.html)
        self.assertRegex(self.html, r"Math\.max\(1,\s*cols\)",
                         "si el navegador devuelve 0 columnas, la tanda quedaría vacía")

    def test_hay_aviso_visual_de_que_falta_mas(self):
        """El difuminado de la última fila. Sin él, el corte parece el final."""
        self.assertIn("grid--hay-mas", self.html)
        self.assertIn("mask-image", self.html)

    def test_el_difuminado_no_le_corta_la_cabeza_a_la_primera_fila(self):
        """
        Una máscara recorta todo lo que sobresalga de la caja del elemento, y de
        las tarjetas sobresalen la etiqueta de "cierra en N días" (11px por
        encima) y la sombra sólida (4px por la derecha).

        Al poner el difuminado, la primera fila apareció decapitada. Se arregla
        agrandando la caja con relleno y compensando con margen negativo, que
        deja las tarjetas exactamente donde estaban.
        """
        regla = re.search(r"\.grid--hay-mas\{(.*?)\}", self.html, flags=re.S)
        self.assertIsNotNone(regla, "desapareció la regla del difuminado")
        cuerpo = regla.group(1)
        arriba = re.search(r"padding:\s*(\d+)px", cuerpo)
        self.assertIsNotNone(arriba, "la grilla con máscara necesita respiro arriba")
        self.assertGreaterEqual(
            int(arriba.group(1)), 11,
            "el respiro tiene que cubrir los 11px que sobresale la etiqueta")
        self.assertIn("margin:-", cuerpo.replace(" ", ""),
                      "sin margen negativo, el relleno movería todas las tarjetas")

    def test_el_contador_no_miente(self):
        """
        Decía "Mostrando N ofertas" cuando pintaba todas. Ahora pinta seis filas,
        así que esa palabra pasó a ser falsa: dice cuántas HAY.
        """
        self.assertNotRegex(
            self.html, r"Mostrando <b>\$\{",
            "el contador volvió a decir 'Mostrando' cuando ya no las muestra todas",
        )

    def test_el_mensaje_de_lista_vacia_no_deja_boton_huerfano(self):
        vacio = re.search(r"function vacio\(\)\{.*?\n\}", self.html, flags=re.S)
        self.assertIsNotNone(vacio)
        self.assertIn("masBox.innerHTML = ''", vacio.group(0))


if __name__ == "__main__":
    unittest.main()
