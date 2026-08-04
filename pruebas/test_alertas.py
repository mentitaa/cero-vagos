"""
Pruebas del formulario de alertas de la portada.

Por qué existen: durante un tiempo este formulario fue una maqueta. Pedía
nombre y número de WhatsApp y al enviarlo solo cambiaba el texto del botón a
"¡Listo! Te avisamos ✓". El dato no se guardaba en ningún lado y nadie recibía
nada nunca.

Pedirle el número a alguien y tirarlo a la basura no es un detalle de diseño:
es una promesa rota, y además la Ley 29733 exige consentimiento y decir para
qué se usa el dato. Estas pruebas están para que esa maqueta no vuelva.

El comportamiento del JavaScript se probó aparte con un navegador simulado.
Acá se vigila lo que se puede leer del HTML, que es lo que se rompe al editar.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


class PruebaFormularioDeAlertas(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.html = (RAIZ / "index.html").read_text(encoding="utf-8")
        bloque = re.search(r'<form class="form" id="formAlertas".*?</form>',
                           cls.html, flags=re.S)
        assert bloque, "no se encontró el formulario de alertas en index.html"
        cls.form = bloque.group(0)

    def test_el_formulario_no_finge_que_funciona(self):
        """El corazón del asunto: nada de confirmar el envío en el propio HTML."""
        self.assertNotIn("onsubmit=", self.form,
                         "el formulario volvió a confirmar el envío sin enviar nada")
        self.assertNotRegex(
            self.form, r"textContent\s*=\s*['\"]¡Listo",
            "el botón vuelve a decir «¡Listo!» sin que el dato haya salido")

    def test_pide_consentimiento_antes_de_guardar_el_numero(self):
        """Ley 29733: el consentimiento es obligatorio y tiene que ser explícito."""
        self.assertIn('name="consentimiento"', self.form)
        self.assertIn("required", self.form)
        casilla = re.search(r'<label class="consiento">.*?</label>', self.form, flags=re.S)
        self.assertIsNotNone(casilla, "falta la casilla de consentimiento")
        self.assertIn('type="checkbox"', casilla.group(0))

    def test_enlaza_la_politica_de_privacidad(self):
        """De nada sirve pedir permiso si no se dice a qué se está aceptando."""
        self.assertIn('href="privacidad/"', self.form)

    def test_tiene_trampa_para_robots(self):
        """Un campo invisible que una persona nunca llena y un robot sí."""
        self.assertIn('name="apellido_materno"', self.form)
        self.assertIn('class="trampa"', self.form)
        self.assertRegex(self.html, r"\.trampa\{[^}]*left:-9999px",
                         "la trampa tiene que estar fuera de pantalla, no en display:none")

    def test_el_destino_de_los_datos_esta_en_un_solo_lugar(self):
        """
        Para activar las alertas se pega una sola dirección. Si algún día
        aparece repartida por el archivo, cambiarla se vuelve una cacería.
        """
        self.assertEqual(self.html.count("ALERTAS_ENDPOINT ="), 1)

    def test_sin_servicio_configurado_el_formulario_lo_admite(self):
        """
        Mientras no haya a dónde mandar los datos, el formulario tiene que
        decirlo. Callarse y aceptar el número es exactamente el problema que
        estas pruebas existen para evitar.
        """
        vacio = re.search(r"const ALERTAS_ENDPOINT = '([^']*)'", self.html)
        self.assertIsNotNone(vacio)
        if not vacio.group(1):
            self.assertIn("todavía no están activas", self.html)

    def test_el_prefijo_pais_no_se_puede_editar(self):
        """
        El +51 va como texto fijo, no como un campo que se pueda borrar. Si
        algún día se convierte en un <input>, alguien manda un número de otro
        país y el mensaje nunca llega.
        """
        caja = re.search(r'<div class="tel">.*?</div>', self.form, flags=re.S).group(0)
        prefijo = re.search(r'<span class="tel__pais">.*?</span>', caja, flags=re.S).group(0)
        self.assertIn("+51", prefijo)
        self.assertNotIn("<input", prefijo, "el prefijo dejó de ser fijo")

    def test_el_numero_sale_con_el_prefijo_puesto(self):
        """Para poder pegarlo en WhatsApp sin arreglarlo uno por uno."""
        self.assertIn("datos.set('whatsapp', '+51' + whatsapp)", self.html)

    def test_valida_celulares_peruanos(self):
        """9 dígitos y empieza con 9. Sin esto entra cualquier cosa."""
        self.assertIn(r"/^9\d{8}$/", self.html)


if __name__ == "__main__":
    unittest.main()
