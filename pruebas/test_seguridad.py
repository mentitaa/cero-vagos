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
