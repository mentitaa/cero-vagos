"""
La página /apoyanos/.

Pedir plata en un sitio cuya única propuesta de valor es "no te escondemos
nada" es delicado, y todo lo que se prueba acá existe para que no se rompa esa
promesa por descuido.

Tres cosas que no pueden fallar:

1. **Que quede escrito que el aporte no compra nada.** Es lo único que hace
   compatible pedir apoyo con la regla 1. Si esa frase desaparece de la
   página, el sitio pasa a ser un portal que cobra por publicar sin decirlo.
2. **Que un canal a medio configurar no se dibuje.** Un QR que no está o una
   dirección de cripto de ejemplo es plata de alguien perdida para siempre.
3. **Que la dirección de cripto nunca salga sin decir la red.** USDC existe
   sobre varias redes que no se hablan entre ellas: mandarlo por la que no es
   no se puede deshacer.
"""
from __future__ import annotations

import re
import shutil
import tempfile
import unittest
from pathlib import Path

from motor import apoyanos
from motor.apoyanos import CANALES, RUTA, hay_algun_canal, pagina

SITIO = "https://cerovagos.com"


class ConCanales(unittest.TestCase):
    """Deja los canales como quedarían configurados de verdad, y los repone."""

    canales: dict = {}

    def setUp(self):
        self._copia = {k: dict(v) for k, v in CANALES.items()}
        for nombre, valores in self.canales.items():
            CANALES[nombre].update(valores)

    def tearDown(self):
        for nombre, valores in self._copia.items():
            CANALES[nombre].clear()
            CANALES[nombre].update(valores)


class PruebaLaPromesaNoSeRompe(ConCanales):
    """
    Lo que la página tiene que decir SIEMPRE, con canales o sin ellos.
    """

    def setUp(self):
        super().setUp()
        self.html = pagina(SITIO)

    def test_dice_que_el_aporte_no_compra_nada(self):
        texto = self.html.lower()
        self.assertIn("no compra", texto)
        for promesa in ("no compra que una oferta salga publicada",
                        "no compra que una oferta salga más arriba",
                        "no compra una excepción al filtro"):
            with self.subTest(promesa=promesa):
                self.assertIn(promesa, texto)

    def test_repite_que_al_usuario_no_se_le_cobra(self):
        self.assertIn("no te cobramos nada", self.html.lower())

    def test_ofrece_ayudar_sin_plata(self):
        self.assertIn("sin poner plata", self.html.lower())

    def test_aclara_que_no_da_derecho_a_nada(self):
        """Para que quede claro que es una donación y no una compra."""
        texto = self.html.lower()
        self.assertIn("voluntarios", texto)
        self.assertIn("contraprestación", texto)


class PruebaSinConfigurarNoSeDibuja(ConCanales):
    """Con todos los canales en blanco, como queda un proyecto recién clonado."""

    canales = {
        "dale": {"titular": "", "qr": ""},
        "plin": {"titular": "", "qr": ""},
        "usdc": {"direccion": "", "red": ""},
    }

    def test_no_hay_canales(self):
        self.assertFalse(hay_algun_canal())

    def test_no_dibuja_cuadros_vacios(self):
        html = pagina(SITIO)
        self.assertNotIn('class="canal"', html)
        self.assertNotIn("<h2>Dónde</h2>", html)

    def test_avisa_y_deja_el_correo(self):
        self.assertIn("todavía no están publicados", pagina(SITIO))

    def test_la_pagina_igual_se_genera(self):
        """
        Sin canales la página sigue existiendo y sigue explicando por qué no
        hay publicidad. Ese texto vale por sí solo.
        """
        self.assertIn("Por qué no hay publicidad", pagina(SITIO))


class PruebaUnCanalAMedias(ConCanales):

    def test_billetera_sin_QR_no_sale(self):
        CANALES["dale"].update({"titular": "Nombre Apellido", "qr": ""})
        self.assertNotIn("Nombre Apellido", pagina(SITIO))

    def test_cripto_sin_RED_no_sale(self):
        """
        El caso que puede costar plata de verdad. Una dirección publicada sin
        decir por qué red se envía es una invitación a perder el dinero.
        """
        CANALES["usdc"].update({"direccion": "0xABC123", "red": ""})
        html = pagina(SITIO)
        self.assertNotIn("0xABC123", html)

    def test_cripto_sin_DIRECCION_no_sale(self):
        CANALES["usdc"].update({"direccion": "", "red": "Solana"})
        self.assertNotIn("<h3>USDC</h3>", pagina(SITIO))


class PruebaConTodoConfigurado(ConCanales):

    canales = {
        "dale": {"titular": "Nombre Apellido", "qr": "qr-dale.png"},
        "plin": {"titular": "Nombre Apellido", "qr": "qr-plin.png"},
        "usdc": {"direccion": "0xAbC0000000000000000000000000000000000001",
                 "red": "Base"},
    }

    def setUp(self):
        super().setUp()
        self.html = pagina(SITIO)
        # El texto va partido en varias líneas dentro del HTML; para buscar
        # frases hay que aplanarlo o los saltos de línea dan falsos fallos.
        self.plano = " ".join(self.html.split()).lower()

    def test_le_dice_al_que_busca_trabajo_que_NO_done(self):
        """
        El usuario del sitio está desempleado. Pedirle plata sin esta línea
        sería, además de inútil, feo. Va junto a los canales: es ahí donde la
        persona está a punto de hacerlo.
        """
        self.assertIn("si estás buscando trabajo, no dones", self.plano)

    def test_salen_los_tres(self):
        self.assertIn("<h3>Dale</h3>", self.html)
        self.assertIn("<h3>Plin</h3>", self.html)
        self.assertIn("<h3>USDC</h3>", self.html)

    def test_los_QR_salen_de_assets_del_propio_sitio(self):
        """
        Con ruta completa y desde nuestro dominio: la política de seguridad de
        la página solo permite imágenes propias ('img-src self'), así que un QR
        alojado afuera no se vería y nadie se enteraría.
        """
        for archivo in ("qr-dale.png", "qr-plin.png"):
            self.assertIn(f'src="{SITIO}/assets/{archivo}"', self.html)

    def test_la_red_se_muestra_junto_a_la_direccion(self):
        self.assertIn("Red: <b>Base</b>", self.html)
        self.assertIn("0xAbC0000000000000000000000000000000000001", self.html)
        self.assertIn("no se puede recuperar", self.plano)

    def test_dice_a_nombre_de_quien(self):
        """Quien escanea tiene que poder confirmar que le manda a quien cree."""
        self.assertIn("Nombre Apellido", self.html)


class PruebaLosQRQueEstanConfigurados(unittest.TestCase):
    """
    Lo que está puesto AHORA en `CANALES`, no un ejemplo.

    El error que esto evita no se ve en una Mac: ahí `qr-plin.png` y
    `QR-PLIN.PNG` son el mismo archivo. En el servidor donde vive el sitio no
    lo son, así que una letra mal deja el QR roto en la web mientras en la
    laptop se ve perfecto. Y un QR roto en la página de donaciones es la única
    imagen que de verdad importa que cargue.
    """

    ASSETS = Path(__file__).resolve().parent.parent / "assets"

    def test_los_archivos_existen_tal_como_estan_escritos(self):
        import os
        for nombre in ("dale", "plin"):
            archivo = CANALES[nombre].get("qr", "")
            if not archivo:
                continue
            with self.subTest(canal=nombre):
                # `os.listdir` compara con mayúsculas y minúsculas de verdad,
                # aunque el disco de la Mac no lo haga.
                self.assertIn(archivo, os.listdir(self.ASSETS),
                              f"assets/{archivo} no existe con ese nombre exacto")

    def test_los_QR_no_pesan_de_mas(self):
        """
        Se muestran a 220 píxeles. El de Dale llegó pesando 588 KB: media hoja
        de descarga en un celular con datos, para una imagen del tamaño de una
        estampilla. Quien entra a este sitio está buscando trabajo, no le sobra
        el megabyte.
        """
        for nombre in ("dale", "plin"):
            archivo = CANALES[nombre].get("qr", "")
            if not archivo:
                continue
            with self.subTest(canal=nombre):
                peso = (self.ASSETS / archivo).stat().st_size
                self.assertLess(peso, 150_000,
                                f"{archivo} pesa {peso // 1024} KB")


class PruebaEstaEnchufada(unittest.TestCase):

    def setUp(self):
        self.carpeta = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.carpeta, ignore_errors=True)

    def test_se_escribe_donde_corresponde(self):
        self.assertEqual(apoyanos.generar(SITIO, self.carpeta), RUTA)
        self.assertTrue((self.carpeta / RUTA / "index.html").exists())

    def test_entra_al_sitemap(self):
        from motor.sitio import sitemap
        self.assertIn(f"{SITIO}/{RUTA}/", sitemap([], SITIO))

    def test_la_enlazan_la_portada_y_las_paginas_internas(self):
        from motor.legales import como_trabajamos
        raiz = Path(__file__).resolve().parent.parent

        portada = (raiz / "index.html").read_text(encoding="utf-8")
        self.assertIn('href="apoyanos/"', portada)
        self.assertIn(f'href="{SITIO}/apoyanos/"', como_trabajamos(SITIO))

    def test_como_trabajamos_aclara_que_no_se_venden_puestos(self):
        """
        Esa página promete "no te cobramos nada, nunca". Al abrir donaciones
        hay que decir ahí mismo qué cambia y qué no, o las dos páginas se
        contradicen y gana la desconfianza.
        """
        from motor.legales import como_trabajamos
        self.assertIn("No vendemos puestos en el listado",
                      como_trabajamos(SITIO))


class PruebaLosColoresQueUsaExisten(unittest.TestCase):
    """
    La paleta es ley, y hay un test que vigila que no se escriban colores
    crudos. Pero nadie vigilaba lo contrario: usar un `var(--algo)` que ya no
    existe. No da error, no se ve leyendo el código y el navegador
    simplemente ignora la línea.

    Pasó de verdad: las páginas legales seguían pidiendo `--negro` y `--lima`,
    dos colores que se eliminaron en el cambio de paleta del 13/8/2026. Las
    sombras y el resaltado de sus recuadros llevaban días sin dibujarse.
    """

    def _paginas(self) -> dict[str, str]:
        from motor.legales import (como_trabajamos, privacidad, reclamaciones,
                                   terminos)
        return {"apoyanos": pagina(SITIO),
                "como-trabajamos": como_trabajamos(SITIO),
                "terminos": terminos(SITIO),
                "privacidad": privacidad(SITIO),
                "reclamaciones": reclamaciones(SITIO)}

    def test_ningun_color_inventado(self):
        for nombre, html in self._paginas().items():
            definidas = set(re.findall(r"(--[a-z-]+)\s*:", html))
            usadas = set(re.findall(r"var\((--[a-z-]+)\)", html))
            with self.subTest(pagina=nombre):
                self.assertEqual(usadas - definidas, set(),
                                 "usa variables de color que no están definidas")


if __name__ == "__main__":
    unittest.main()
