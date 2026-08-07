"""
Leerle las letras a la imagen del PDF, y no publicar lo que salga ilegible.

Por qué existe esto. En la primera corrida de Convocatorias CAS (6/8/2026), de
78 avisos **31 no llegaron a sus funciones** porque el PDF de las bases no se
dejó leer. Ese 31 se reparte en dos casos que parecen distintos:

  · 11 PDF sin texto: son una foto escaneada del documento.
  · 20 PDF con texto, pero roto. Un ejemplo real de las bases de la UGEL San
    Pablo (Cajamarca), copiado tal cual del archivo:

        Pr¡ncipales funciones a desanollar:

    Debería decir "Principales funciones a desarrollar". Alguien ya les pasó un
    lector de letras antes de subirlas y le salió mal.

Los dos se arreglan igual: rasterizar la página y volver a leerla nosotros,
partiendo de la imagen en vez del texto roto.

**Y el guardián importa tanto como el lector.** El OCR también se equivoca. Por
la regla 2, una función que salga ilegible no se publica: es preferible un
aviso sin funciones que un aviso con funciones que nadie puede leer. Lo segundo
además parece un error nuestro, no del Estado.
"""
from __future__ import annotations

import unittest

from motor.bases_pdf import (
    descartar_ilegibles, extraer_funciones, hay_ocr, idioma_ocr,
    parece_ilegible, texto_de_pdf, texto_por_ocr,
)

# Renglones copiados del PDF de verdad (UGEL San Pablo, Cajamarca).
ROTAS = [
    "económicas, tanto de a través del módulo C.antable S/AF-SP Contab¡l¡zar las como de a",
    "b Formular Nol Contabil¡dad elaborar el análísis cuentas de Balances Mensua/es del Cierc",
    "Pr¡ncipales funciones a desanollar",
    "/ / / . , ,, ,, / . 12 3 4",
]

# Funciones sanas, con tildes, siglas y guiones: nada de esto puede caerse.
SANAS = [
    "Contabilizar las operaciones economicas de la entidad",
    "Realizar la poda de árboles y arbustos en parques y bermas del distrito",
    "Coordinar con el área de Tesorería sobre los avances de la ejecución",
    "Brindar asesoramiento en el manejo del SIAF-SP y SIGA a las instituciones",
    "Elaborar informes técnicos sobre la situación económica y financiera",
]


def pdf_escaneado(lineas: list[str]) -> bytes:
    """
    Arma un PDF que es una IMAGEN de un texto, como los que suben las
    entidades: se ve perfecto y no trae una sola letra dentro.
    """
    import io

    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (1240, 120 + 70 * len(lineas)), "white")
    dibujo = ImageDraw.Draw(img)
    try:
        letra = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 26)
    except Exception:                                  # noqa: BLE001
        letra = ImageFont.load_default()
    for i, linea in enumerate(lineas):
        dibujo.text((40, 30 + i * 70), linea, fill="black", font=letra)

    buffer = io.BytesIO()
    img.save(buffer, "PDF")
    return buffer.getvalue()


def hay_pillow() -> bool:
    try:
        import PIL  # noqa: F401
        return True
    except ImportError:
        return False


class PruebaGuardianDeLoIlegible(unittest.TestCase):
    """
    La pieza que protege la regla 2. Si esto se afloja, el sitio empieza a
    mostrar renglones indescifrables donde promete decir qué vas a hacer.
    """

    def test_el_texto_roto_de_cajamarca_se_rechaza(self):
        for rota in ROTAS:
            self.assertTrue(parece_ilegible(rota), f"debió rechazarse: {rota[:50]}")

    def test_las_funciones_sanas_sobreviven(self):
        for sana in SANAS:
            self.assertFalse(parece_ilegible(sana), f"no debió caerse: {sana[:50]}")

    def test_las_tildes_y_las_siglas_no_son_sospechosas(self):
        """
        'Gestión', 'SIAF-SP', 'S/ 2,864': el español y la jerga del Estado
        están llenos de tildes, siglas y barras. Un filtro que las tomara por
        basura dejaría al sitio sin funciones de verdad.
        """
        self.assertFalse(parece_ilegible(
            "Gestión del SIAF-SP y del SIGA en la Unidad de Administración"))

    def test_los_signos_de_apertura_pegados_a_una_letra_delatan(self):
        """En español '¡' y '¿' solo abren frase. Pegados a una letra son OCR malo."""
        self.assertTrue(parece_ilegible("Contab¡l¡zar las operaciones de la entidad"))
        self.assertFalse(parece_ilegible("¿Qué funciones tendrá que cumplir el puesto?"))

    def test_una_linea_muy_corta_no_es_una_funcion(self):
        self.assertTrue(parece_ilegible("Formular"))
        self.assertTrue(parece_ilegible(""))

    def test_descartar_ilegibles_deja_solo_las_sanas(self):
        self.assertEqual(descartar_ilegibles(ROTAS + SANAS), SANAS)


class PruebaLoRotoNoLlegaAPublicarse(unittest.TestCase):

    def test_un_bloque_de_funciones_roto_no_produce_funciones(self):
        """
        De punta a punta: aunque el encabezado se reconozca, si lo que sigue
        está roto no sale ninguna función. Vale más el hueco.
        """
        texto = "Principales funciones a desarrollar:\n" + "\n".join(
            f"{letra}) {rota}" for letra, rota in zip("abcd", ROTAS))
        self.assertEqual(extraer_funciones(texto), [])

    def test_un_bloque_sano_sí_produce_funciones(self):
        texto = "Principales funciones a desarrollar:\n" + "\n".join(
            f"{letra}) {sana}." for letra, sana in zip("abcde", SANAS))
        self.assertGreaterEqual(len(extraer_funciones(texto)), 3)

    def test_lo_roto_no_le_gana_a_lo_sano_por_cantidad(self):
        """
        El descarte va antes de elegir el mejor bloque. Si fuera después, un
        bloque con diez renglones de basura le ganaría por número al bloque
        bueno de tres, y el aviso terminaría sin funciones.
        """
        texto = (
            "Funciones del servicio:\n"
            + "\n".join(f"- {r}" for r in ROTAS * 3)
            + "\nREQUISITOS\n\nPrincipales funciones a desarrollar:\n"
            + "\n".join(f"{i}) {s}." for i, s in enumerate(SANAS, 1))
        )
        funciones = extraer_funciones(texto)
        self.assertGreaterEqual(len(funciones), 3)
        for f in funciones:
            self.assertFalse(parece_ilegible(f))


@unittest.skipUnless(hay_ocr() and hay_pillow(),
                     "hace falta tesseract, pdftoppm y Pillow")
class PruebaLeerLaImagen(unittest.TestCase):
    """
    La prueba de verdad: un PDF que es una foto, leído de punta a punta.

    Se salta sola donde no estén las herramientas, para que los tests sigan
    corriendo en una laptop sin tesseract.
    """

    LINEAS = [
        "Principales funciones a desarrollar:",
        "a) Contabilizar las operaciones economicas de la entidad.",
        "b) Formular los estados financieros mensuales del pliego.",
        "c) Revisar y conciliar los anexos del balance de comprobacion.",
        "d) Realizar la fase del devengado en el modulo administrativo.",
        "REQUISITOS DEL PUESTO",
    ]

    def setUp(self):
        self.datos = pdf_escaneado(self.LINEAS)

    def test_el_pdf_de_prueba_no_trae_texto(self):
        """Si trajera texto no estaríamos probando lo que creemos probar."""
        self.assertEqual(texto_de_pdf(self.datos).strip(), "")

    def test_el_ocr_saca_las_funciones(self):
        funciones = extraer_funciones(texto_por_ocr(self.datos))
        self.assertGreaterEqual(len(funciones), 3)
        self.assertTrue(any("contabilizar" in f.lower() for f in funciones))

    def test_el_ocr_para_donde_paran_las_funciones(self):
        """'REQUISITOS' cierra la sección: no debe colarse en la lista."""
        funciones = extraer_funciones(texto_por_ocr(self.datos))
        self.assertFalse(any("requisito" in f.lower() for f in funciones))

    def test_lo_que_saca_el_ocr_es_legible(self):
        for f in extraer_funciones(texto_por_ocr(self.datos)):
            self.assertFalse(parece_ilegible(f), f"el OCR devolvió basura: {f}")


class PruebaElOcrNoTumbaLaCorrida(unittest.TestCase):
    """
    El OCR es lo más frágil del motor: depende de dos programas del sistema y
    de un PDF que puede venir de cualquier forma. Pase lo que pase devuelve
    cadena vacía, nunca una excepción.
    """

    def test_datos_que_no_son_un_pdf(self):
        self.assertEqual(texto_por_ocr(b"esto no es un pdf"), "")

    def test_sin_datos(self):
        self.assertEqual(texto_por_ocr(b""), "")

    def test_un_pdf_roto(self):
        self.assertEqual(texto_por_ocr(b"%PDF-1.4 y aqui se corta"), "")

    def test_el_idioma_es_uno_de_los_dos(self):
        self.assertIn(idioma_ocr(), ("spa", "eng"))


class PruebaElOcrEsElUltimoRecurso(unittest.TestCase):
    """
    Esto es el presupuesto de la corrida. Leer la imagen cuesta segundos por
    página; sacar el texto que el PDF ya trae es instantáneo. Si el OCR se
    llegara a intentar SIEMPRE, la fuente pasaría de minutos a horas y el paso
    se cortaría por tiempo — que es exactamente lo que le pasó a Laborum.
    """

    def test_no_se_lee_la_imagen_si_el_texto_ya_dio_las_funciones(self):
        from motor import bases_pdf
        from motor.fuentes.publicas import enriquecer_con_bases
        from motor.modelos import OfertaCruda

        pdf = "https://x.gob.pe/bases.pdf"
        html = f'<p>Requisitos</p><ul><li>Secundaria</li></ul><a href="{pdf}">Bases</a>'
        cruda = OfertaCruda(fuente="Convocatorias CAS", url="https://y.com/a-1-plazas-1.html",
                            puesto="Contador", empresa="UGEL", descripcion_html=html)

        buenas = ("Principales funciones a desarrollar:\n"
                  + "\n".join(f"{i}) {s}." for i, s in enumerate(SANAS, 1)))

        llamadas = []
        texto_real, ocr_real = bases_pdf.texto_de_pdf, bases_pdf.texto_por_ocr
        bases_pdf.texto_de_pdf = lambda *_a, **_k: buenas
        bases_pdf.texto_por_ocr = lambda *a, **k: llamadas.append(1) or ""
        try:
            enriquecer_con_bases(cruda, html, lambda _u, _m=0: b"%PDF-1.4 x")
        finally:
            bases_pdf.texto_de_pdf, bases_pdf.texto_por_ocr = texto_real, ocr_real

        self.assertEqual(llamadas, [], "se leyó la imagen sin necesidad")
        self.assertIn("Funciones", cruda.descripcion_html)


if __name__ == "__main__":
    unittest.main()
