"""
Pruebas de seguridad del sitio publicado.

Una política de contenido mal escrita no da error: la página simplemente
deja de cargar la tipografía, o el formulario deja de enviar, y nadie se
entera hasta que alguien se queja. Por eso acá no se comprueba que la
política "exista", sino que **todo lo que las páginas realmente usan está
permitido**, y que lo que no debería poder cargarse, no puede.

Si mañana se agrega un servicio nuevo (un contador de visitas, otro
formulario), estas pruebas fallan hasta que se le abra la puerta a mano.
Eso es lo que se quiere: que agregar terceros sea una decisión consciente.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def politica(html: str) -> dict[str, list[str]]:
    """Lee la etiqueta de política y la deja como diccionario."""
    m = re.search(r'http-equiv="Content-Security-Policy" content="([^"]+)"', html)
    if not m:
        return {}
    reglas = {}
    for parte in m.group(1).split(";"):
        piezas = parte.split()
        if piezas:
            reglas[piezas[0]] = piezas[1:]
    return reglas


def permitido(reglas: dict, clave: str, origen: str) -> bool:
    """¿La política deja cargar algo de ese origen?"""
    fuentes = reglas.get(clave, reglas.get("default-src", []))
    if "'none'" in fuentes:
        return False
    if origen == "propio":
        return "'self'" in fuentes
    return any(origen.startswith(f) for f in fuentes if f.startswith("http"))


class PruebaPoliticaDeContenido(unittest.TestCase):

    PAGINAS = ("index.html", "transparencia/index.html", "terminos/index.html",
               "privacidad/index.html", "404.html")

    def _paginas(self):
        for nombre in self.PAGINAS:
            ruta = RAIZ / nombre
            if ruta.exists():
                yield nombre, ruta.read_text(encoding="utf-8")
        for carpeta in sorted((RAIZ / "oferta").glob("*/"))[:1]:
            yield "una oferta", (carpeta / "index.html").read_text(encoding="utf-8")

    def test_todas_las_paginas_tienen_politica(self):
        for nombre, html in self._paginas():
            with self.subTest(pagina=nombre):
                self.assertTrue(politica(html), f"{nombre} salió sin política")

    def test_la_tipografia_sigue_permitida(self):
        """El error más fácil: la web queda con la letra del sistema."""
        for nombre, html in self._paginas():
            reglas = politica(html)
            if "fonts.googleapis.com" not in html:
                continue
            with self.subTest(pagina=nombre):
                self.assertTrue(permitido(reglas, "style-src", "https://fonts.googleapis.com"),
                                f"{nombre}: la hoja de estilos de Google quedaría bloqueada")
                self.assertTrue(permitido(reglas, "font-src", "https://fonts.gstatic.com"),
                                f"{nombre}: la letra quedaría bloqueada")

    def test_el_logo_sigue_permitido(self):
        for nombre, html in self._paginas():
            with self.subTest(pagina=nombre):
                self.assertTrue(permitido(politica(html), "img-src", "propio"),
                                f"{nombre}: el logo quedaría bloqueado")

    def test_el_formulario_puede_hablar_con_formspree(self):
        html = (RAIZ / "index.html").read_text(encoding="utf-8")
        destino = re.search(r"const ALERTAS_ENDPOINT = '(https://[^/]+)", html)
        self.assertIsNotNone(destino, "no se encontró el destino de las alertas")
        self.assertTrue(
            permitido(politica(html), "connect-src", destino.group(1)),
            "las alertas no se podrían enviar: falta autorizar ese destino en la política")

    def test_nadie_puede_cargar_codigo_de_otro_sitio(self):
        """El punto de todo esto: aunque alguien colara una etiqueta, no carga."""
        for nombre, html in self._paginas():
            reglas = politica(html)
            with self.subTest(pagina=nombre):
                self.assertFalse(permitido(reglas, "script-src", "https://sitio-malicioso.com"),
                                 f"{nombre}: se podría cargar código de fuera")
                self.assertIn("'none'", reglas.get("object-src", []),
                              f"{nombre}: faltan bloquear los objetos incrustados")
                self.assertIn("'none'", reglas.get("base-uri", []),
                              f"{nombre}: se podría reescribir a dónde apuntan los enlaces")

    def test_las_paginas_generadas_no_mandan_datos_a_ningun_lado(self):
        """Solo la portada tiene formulario. Las demás no piden nada a nadie."""
        for nombre, html in self._paginas():
            if nombre == "index.html":
                continue
            with self.subTest(pagina=nombre):
                self.assertIn("'none'", politica(html).get("form-action", []),
                              f"{nombre}: podría enviar un formulario a otro sitio")


class PruebaEnlacesExternos(unittest.TestCase):

    def test_los_enlaces_a_otros_portales_no_dejan_puerta_abierta(self):
        """
        Un enlace con target="_blank" y sin rel="noopener" le da a la página de
        destino permiso para cambiar la pestaña de origen por una copia falsa.
        Como enlazamos a portales que no controlamos, esto no es teórico.
        """
        for ruta in [RAIZ / "index.html", *sorted((RAIZ / "oferta").glob("*/index.html"))[:3]]:
            html = ruta.read_text(encoding="utf-8")
            for enlace in re.findall(r"<a\b[^>]*>", html):
                if 'target="_blank"' not in enlace:
                    continue
                with self.subTest(archivo=ruta.name, enlace=enlace[:80]):
                    self.assertIn("noopener", enlace)


if __name__ == "__main__":
    unittest.main()


class PruebaLaPaletaEsLey(unittest.TestCase):
    """
    La paleta se define en un solo sitio y nadie escribe colores por su cuenta.

    Elegida el 13/8/2026, después de que el feedback dijera que los colores
    parecían puestos por poner. Y lo parecían porque lo estaban: había SIETE
    tonos saturados —rojo, amarillo, lima, cyan, magenta, azul y crema— sin
    ninguna regla de quién manda. El amarillo se usaba 17 veces y el rojo 13:
    el color de marca no era el que más aparecía en su propia web.

    Estas pruebas no juzgan el gusto. Vigilan lo único que se puede vigilar:
    que la regla siga en pie cuando alguien toque el CSS dentro de seis meses.
    """

    ARCHIVOS = ("index.html", "motor/sitio.py",
                "motor/transparencia.py", "motor/lugares.py")

    # Los siete de antes. Si alguno reaparece, es que volvió el desorden.
    MUERTOS = ("--rojo", "--negro", "--crema", "--amarillo",
               "--lima", "--cyan", "--magenta", "--azul")

    def texto(self, archivo: str) -> str:
        return (RAIZ / archivo).read_text(encoding="utf-8")

    def test_ningun_archivo_usa_los_colores_viejos(self):
        for archivo in self.ARCHIVOS:
            texto = self.texto(archivo)
            for muerto in self.MUERTOS:
                with self.subTest(archivo=archivo, color=muerto):
                    self.assertNotIn(f"var({muerto})", texto)

    def test_las_cuatro_plantillas_declaran_la_misma_paleta(self):
        """
        Son cuatro archivos distintos y ya nos pasó con el score y con el modo
        oscuro: uno se queda atrás y nadie lo nota hasta que alguien abre esa
        página. Los valores tienen que coincidir exactamente.
        """
        import re

        esperado = {"--marca": "#FF1E1E", "--tinta": "#101B2D",
                    "--fondo": "#F5F1E8", "--acento": "#FFB703"}
        for archivo in self.ARCHIVOS:
            texto = self.texto(archivo)
            for nombre, valor in esperado.items():
                with self.subTest(archivo=archivo, color=nombre):
                    m = re.search(re.escape(nombre) + r"\s*:\s*(#[0-9A-Fa-f]{6})", texto)
                    self.assertIsNotNone(m, f"{archivo} no declara {nombre}")
                    self.assertEqual(m.group(1).upper(), valor,
                                     f"{archivo} tiene otro {nombre}")

    def test_el_rojo_de_marca_no_significa_MAL(self):
        """
        En /transparencia hay que decir "bien" y "mal", y el rojo de la marca
        no puede ser el "mal": sería la identidad del sitio calificando de
        malo a alguien, y haría que el color más presente de la web fuera el
        de la peor nota. Por eso existe `--alerta`, que es otro rojo.
        """
        texto = self.texto("motor/transparencia.py")
        self.assertIn("--alerta", texto)
        self.assertIn('"baja": "var(--alerta)"', texto)
        self.assertNotIn('"baja": "var(--marca)"', texto)

    def test_no_quedan_colores_escritos_a_mano_en_la_portada(self):
        """
        Un color suelto en mitad del CSS es como se deshace una paleta: nadie
        lo ve, no rompe nada, y al cabo de un año hay siete otra vez.
        """
        import re

        html = self.texto("index.html")
        raiz = html.index(":root{")
        fuera = html[html.index("}", raiz):]
        # El negro de una máscara no es un color: es un recorte.
        fuera = fuera.replace("#000", "")
        sueltos = re.findall(r"#[0-9A-Fa-f]{3,8}\b", fuera)
        self.assertEqual(sueltos, [], f"colores fuera de la paleta: {sueltos}")
