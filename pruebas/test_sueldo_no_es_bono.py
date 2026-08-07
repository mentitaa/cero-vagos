"""
El monto que se publica tiene que ser el SUELDO, no la comisión ni el bono.

Reportado por Mentita el 7/8/2026 con tres avisos que estaban en la web. El
más claro, un promotor de ventas:

    Sueldo básico: S/ 1,130.
    Comisiones de hasta S/ 600.

y el sitio mostraba **S/ 600**.

Es el hermano del error de los S/ 33,800, y por la misma causa de fondo: algo
que califica a un monto —ahí el periodo, aquí la etiqueta— se buscaba en una
ventana de texto tan ancha que alcanzaba al monto vecino. La ventana de 40
caracteres que busca la palabra "sueldo" antes del 600 llegaba hasta el
"básico:" del 1,130. Los dos salían etiquetados, empataban en confianza, y el
desempate —que elige el más bajo por prudencia— se quedaba con la comisión.

Por qué importa más que un número mal puesto: quien busca chamba compara
sueldos. Publicar la comisión como si fuera el sueldo es exactamente el tipo
de aviso engañoso que Cero Vagos existe para rechazar, hecho por nosotros.
"""
from __future__ import annotations

import unittest

from motor.sueldo import _ventana_de_etiqueta, extraer_sueldo


class PruebaAvisosRealesQueSalieronMal(unittest.TestCase):
    """Los textos son los de los avisos que Mentita encontró publicados."""

    def test_promotor_de_ventas_retail(self):
        """Grupo Tawa. Mostraba S/ 600, que es el tope de comisiones."""
        s = extraer_sueldo(
            "Planilla completa con todos tus beneficios de ley.\n"
            "Sueldo basico: S/ 1,130.\n"
            "Comisiones de hasta S/ 600.\n"
            "Tarjeta de alimentos: S/ 200."
        )
        self.assertEqual(s.minimo, 1130)

    def test_asesor_de_cobranza(self):
        """
        Grafton Latam. Mostraba S/ 500 – S/ 1,000, que es el RANGO DE
        COMISIONES. Este además demuestra por qué no bastaba con mirar la
        etiqueta: un rango se busca antes que un monto suelto, así que la
        comisión ganaba por orden de patrón, no por confianza.
        """
        s = extraer_sueldo(
            "Sueldo base: S/.1200\n"
            "Bono de asistencia: S/.200 (sujeto al cumplimiento de asistencia)\n"
            "Bono de Banco: S/.300\n"
            "Comisiones : S/ 500 a S/ 1000"
        )
        self.assertEqual(s.minimo, 1200)
        self.assertFalse(s.es_rango, "publicó el rango de comisiones como sueldo")


class PruebaLaEtiquetaEsDelMontoQueEstaPegado(unittest.TestCase):
    """
    La regla de fondo, la misma que ya se aplicó al periodo tras los S/ 33,800:
    lo que califica a un monto tiene que estar pegado a él.
    """

    def test_la_ventana_se_corta_en_el_punto_anterior(self):
        ventana = _ventana_de_etiqueta("o basico: s/ 1,130. comisiones de hasta ")
        self.assertNotIn("basico", ventana)
        self.assertIn("comisiones", ventana)

    def test_la_ventana_se_corta_en_el_monto_anterior(self):
        ventana = _ventana_de_etiqueta("sueldo base s/ 1200 mas un extra de ")
        self.assertNotIn("sueldo", ventana)

    def test_una_etiqueta_propia_sobrevive(self):
        self.assertIn("sueldo basico", _ventana_de_etiqueta("de ley. sueldo basico: "))

    def test_un_segundo_monto_sin_nombre_conocido_tampoco_hereda_la_etiqueta(self):
        """
        Este es el caso que SOLO salva el corte de ventana.

        En los avisos de Mentita el segundo monto se llamaba "comisión" o
        "bono", y esas palabras ya lo descalifican por su cuenta. Pero un aviso
        puede decir "Adicional de S/ 600" —que no está en ninguna lista— y sin
        cortar la ventana ese 600 heredaría el "básico:" del monto anterior,
        empataría en confianza y ganaría el desempate por ser más bajo.

        Sin este test, alguien podría quitar el corte y los tests seguirían en
        verde tapados por la otra defensa.
        """
        s = extraer_sueldo("Sueldo basico: S/ 1,130. "
                           "Adicional de S/ 600 por cumplimiento de metas.")
        self.assertEqual(s.minimo, 1130)


class PruebaLoQueNoEsSueldoNoSePublica(unittest.TestCase):

    def test_una_comision_sola_no_es_un_sueldo(self):
        """
        Si lo ÚNICO que declara el aviso es una comisión, no declara sueldo y
        no se publica. Perder el aviso es lo correcto: la regla 1 pide el
        sueldo, no cualquier monto.
        """
        self.assertIsNone(extraer_sueldo("Comisiones de hasta S/ 3,000 mensuales"))

    def test_un_bono_solo_tampoco(self):
        self.assertIsNone(extraer_sueldo("Bono de productividad: S/ 800"))

    def test_ni_el_vale_de_alimentos(self):
        self.assertIsNone(extraer_sueldo("Tarjeta de alimentos: S/ 200 al mes"))

    def test_la_subvencion_de_una_practica_SI_es_el_pago(self):
        """
        A propósito fuera de la lista: así se llama el pago de una práctica
        preprofesional. Ahí el monto sí es lo que te llevas, y dejarlo fuera
        borraría del sitio todas las prácticas.
        """
        s = extraer_sueldo("Subvención económica de S/ 1,200 mensuales")
        self.assertIsNotNone(s)
        self.assertEqual(s.minimo, 1200)


class PruebaElAvisoLeGanaAlPortal(unittest.TestCase):
    """
    Cuando el texto NOMBRA su sueldo, eso manda sobre la ficha de datos del
    portal. Decisión de Mentita (7/8/2026).

    Hizo falta porque el primer arreglo se quedó corto y ella lo vio enseguida:
    yo bloqueé las comisiones en el TEXTO del aviso, pero los portales publican
    además una ficha de datos con el sueldo aparte, y el motor le hacía más
    caso a esa ficha. Si el empleador metió ahí sus comisiones, en ese campo no
    hay ninguna palabra que diga "comisión" — solo un número pelado.

    La regla no afloja la regla 1, la afina: entre dos números que dicen ser el
    sueldo, gana el que viene con la palabra "sueldo" pegada.
    """

    CUERPO = ("<p>Funciones</p><ul><li>Atender a los clientes del local</li>"
              "<li>Ordenar la mercadería en tienda</li>"
              "<li>Registrar las ventas en el sistema</li></ul>"
              "<p>Requisitos</p><ul><li>Secundaria completa</li>"
              "<li>Seis meses de experiencia</li>"
              "<li>Disponibilidad inmediata</li></ul>"
              "<p>Beneficios</p><ul>{}</ul>")

    def sueldo(self, ficha_del_portal: str, beneficios: str) -> tuple[int, int]:
        from motor.modelos import OfertaCruda
        from motor.pipeline import procesar_cruda

        cuerpo = self.CUERPO.format(beneficios)
        o = procesar_cruda(OfertaCruda(
            fuente="Bumeran", url="https://x.pe/1", puesto="Promotor de Ventas",
            empresa="Grupo Tawa", sueldo_texto=ficha_del_portal,
            descripcion_html=cuerpo))
        return o.sueldo_min, o.sueldo_max

    def test_el_promotor_de_ventas_real(self):
        """La ficha del portal traía la comisión; el aviso, el sueldo."""
        self.assertEqual(
            self.sueldo("S/ 600",
                        "<li>Sueldo básico: S/ 1,130.</li>"
                        "<li>Comisiones de hasta S/ 600.</li>"
                        "<li>Tarjeta de alimentos: S/ 200</li>"),
            (1130, 1130))

    def test_el_asesor_de_cobranza_real(self):
        self.assertEqual(
            self.sueldo("S/ 500 - S/ 1000",
                        "<li>Sueldo base: S/.1200</li>"
                        "<li>Bono de asistencia: S/.200</li>"
                        "<li>Comisiones : S/ 500 a S/ 1000</li>"),
            (1200, 1200))

    def test_tambien_vale_la_palabra_remuneracion(self):
        self.assertEqual(
            self.sueldo("S/ 565",
                        "<li>Ingreso a planilla desde el primer día</li>"
                        "<li>Remuneración: S/ 1,130</li>"),
            (1130, 1130))

    def test_si_el_aviso_no_lo_nombra_sigue_mandando_el_portal(self):
        """
        La ficha del portal no deja de ser la fuente normal. Solo pierde
        cuando el aviso contradice con todas sus letras.
        """
        self.assertEqual(
            self.sueldo("S/ 2,500",
                        "<li>Planilla completa</li><li>Seguro EPS</li>"),
            (2500, 2500))

    def test_una_etiqueta_debil_no_basta_para_contradecir_al_portal(self):
        """
        "base" o "básico" a secas suben la confianza, pero no alcanzan para
        desautorizar al portal: son demasiado ambiguas sueltas.
        """
        from motor.sueldo import extraer_sueldo
        self.assertIsNone(extraer_sueldo("Monto base: S/ 900", solo_etiquetado=True))
        self.assertIsNotNone(extraer_sueldo("Sueldo base: S/ 900", solo_etiquetado=True))


class PruebaNoSeRompioLoQueYaFuncionaba(unittest.TestCase):
    """
    Los casos de siempre, para que el arreglo no se lleve por delante lecturas
    que estaban bien.
    """

    def test_los_casos_de_toda_la_vida(self):
        casos = [
            ("S/ 3,500 mensuales", 3500, 3500),
            ("S/ 2,800 a S/ 3,400", 2800, 3400),
            ("Sueldo: S/ 1500", 1500, 1500),
            ("entre 4000 y 5500 soles", 4000, 5500),
            ("Remuneración mensual de S/ 2,864", 2864, 2864),
        ]
        for texto, lo, hi in casos:
            s = extraer_sueldo(texto)
            self.assertIsNotNone(s, f"dejó de leer: {texto}")
            self.assertEqual((s.minimo, s.maximo), (lo, hi), f"cambió: {texto}")

    def test_el_error_de_los_33800_sigue_sin_poder_pasar(self):
        s = extraer_sueldo("Salario base S/1,300. Remuneraciones quincenales "
                           "y pago de horas extras.")
        self.assertEqual(s.minimo, 1300)

    def test_sin_sueldo_sigue_siendo_none(self):
        self.assertIsNone(extraer_sueldo("Sueldo a convenir según experiencia"))


if __name__ == "__main__":
    unittest.main()
