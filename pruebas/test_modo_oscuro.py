"""
El sitio se ve como está diseñado, también en los navegadores con modo oscuro.

Reportado el 8/8/2026: en **Brave** la portada salía irreconocible — el fondo
crema en marrón, el amarillo en verde oliva, el texto con recuadros de resalte
encima. En Chrome se veía bien. No era un fallo del CSS: era el navegador
"arreglando" la página por su cuenta.

Los navegadores con modo oscuro automático (Brave, y Chrome en Android)
invierten los colores de cualquier página que **no diga** que solo existe en
claro. La forma de decirlo son dos líneas:

    <meta name="color-scheme" content="light">     en el <head>
    :root{color-scheme:light}                      en el CSS

Con eso el navegador respeta el diseño. Y son dos porque el CSS es lo que
manda de verdad; la etiqueta la leen los navegadores viejos y llega antes de
que se descargue la hoja de estilos, así que evita el parpadeo.

Esto importa más de lo que parece: **la marca es el diseño.** Un sitio que
promete honestidad y se ve roto en el navegador de quien lo abre no arranca
con el pie derecho.
"""
from __future__ import annotations

import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


class PruebaLaPortada(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.html = (RAIZ / "index.html").read_text(encoding="utf-8")

    def test_declara_que_solo_existe_en_claro(self):
        self.assertIn('name="color-scheme" content="light"', self.html)

    def test_y_tambien_en_el_css_que_es_el_que_manda(self):
        self.assertIn("color-scheme:light", self.html.replace("color-scheme: light", "color-scheme:light"))


class PruebaLasPaginasGeneradas(unittest.TestCase):
    """
    Las páginas de oferta, la de transparencia, las legales, el 404 y la de
    salida se generan con código. Son cinco plantillas distintas y ninguna
    puede quedarse atrás — ya pasó con el score, que se quitó de la portada y
    siguió saliendo un día entero en las fichas.
    """

    def paginas(self) -> dict[str, str]:
        from motor.legales import como_trabajamos, privacidad, reclamaciones, terminos
        from motor.sitio import pagina_404, pagina_oferta, pagina_salida
        from motor.transparencia import pagina as pagina_transparencia

        sitio = "https://cerovagos.com"
        oferta = {"slug": "x-y-ab12cd34", "puesto": "Asistente", "empresa": "Acme",
                  "ciudad": "Lima", "departamento": "Lima", "huella": "ab12cd34",
                  "min": 1500, "max": 1500, "fuente": "Bumeran",
                  "url": "https://ejemplo.pe/a", "requisitos": ["a"], "beneficios": ["b"]}
        datos = {"total": 100, "sin_sueldo": 75, "pct_sin_sueldo": 75,
                 "desde": "2026-08-03", "hasta": "2026-08-08", "minimo_avisos": 3,
                 "transparentes": [], "opacas": [], "por_categoria": [],
                 "por_ciudad": [], "por_fuente": []}

        return {
            "la ficha de una oferta": pagina_oferta(oferta, sitio),
            "la página de salida": pagina_salida(oferta, sitio),
            "el 404": pagina_404(sitio),
            "transparencia": pagina_transparencia(datos, sitio),
            "cómo trabajamos": como_trabajamos(sitio),
            "términos": terminos(sitio),
            "privacidad": privacidad(sitio),
            "reclamaciones": reclamaciones(sitio),
        }

    def test_todas_declaran_el_modo_claro(self):
        for nombre, html in self.paginas().items():
            with self.subTest(pagina=nombre):
                self.assertIn('name="color-scheme" content="light"', html,
                              f"a {nombre} le falta la etiqueta")
                self.assertIn("color-scheme:light", html,
                              f"a {nombre} le falta la propiedad CSS")


if __name__ == "__main__":
    unittest.main()
