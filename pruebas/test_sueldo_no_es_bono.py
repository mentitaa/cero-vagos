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


class PruebaDosSueldosNoSePublican(unittest.TestCase):
    """
    Un aviso que convoca varias modalidades declara dos sueldos, y no hay
    forma de saber cuál corresponde al puesto que mostramos.

    El caso real (7/8/2026): un "Reponedor(a) Full Time" de Bumeran que en
    realidad ofrecía las dos jornadas —su propia dirección lo delata:
    `reponedora-full-time-part-time-varios-distritos`— y declaraba
    "Remuneración: S/ 1,130" y "Remuneración: S/ 565". El motor elegía el más
    bajo por prudencia y publicaba **S/ 565 bajo un título que decía Full
    Time**.

    Elegir el más bajo protege de prometer de más, pero no de mentir. Decisión
    de Mentita: no se publica. Regla 2, y el precio es perder el aviso.
    """

    DOS = ("Modalidades disponibles. Full Time: Remuneración: S/ 1,130 mensuales. "
           "Part Time: Remuneración: S/ 565 mensuales.")

    def test_se_detectan_los_dos(self):
        from motor.sueldo import declara_varios_sueldos
        self.assertTrue(declara_varios_sueldos(self.DOS))

    def test_el_mismo_monto_repetido_no_es_ambiguo(self):
        """Un aviso puede nombrar su sueldo dos veces. Eso no es un conflicto."""
        from motor.sueldo import declara_varios_sueldos
        self.assertFalse(declara_varios_sueldos(
            "Sueldo: S/ 2,000 mensuales. Se ofrece un sueldo de S/ 2,000 en planilla."))

    def test_un_sueldo_con_bonos_tampoco(self):
        from motor.sueldo import declara_varios_sueldos
        self.assertFalse(declara_varios_sueldos(
            "Sueldo base: S/.1200. Bono de asistencia: S/.200. Comisiones: S/ 500 a S/ 1000"))

    def test_el_aviso_completo_se_rechaza(self):
        """
        Y se rechaza de verdad: no basta con no leer el sueldo del texto,
        porque entonces el motor caería en la ficha del portal y publicaría
        igual. Eso pasaba, y era peor: publicaba el 565 igual.
        """
        from motor.modelos import OfertaCruda
        from motor.pipeline import procesar_cruda

        cuerpo = ("<p>Funciones</p><ul><li>Reponer productos en tienda</li>"
                  "<li>Armar plantillas y vitrinas</li>"
                  "<li>Registrar productos en el kardex</li></ul>"
                  "<p>Requisitos</p><ul><li>Secundaria completa</li>"
                  "<li>Tres meses de experiencia</li>"
                  "<li>Disponibilidad para horarios rotativos</li></ul>"
                  f"<p>Beneficios</p><ul><li>Ingreso a planilla</li><li>{self.DOS}</li></ul>")
        o = procesar_cruda(OfertaCruda(
            fuente="Bumeran", url="https://x.pe/1", puesto="Reponedor(a) Full Time",
            empresa="HRD SAC", sueldo_texto="S/ 565", descripcion_html=cuerpo))

        self.assertFalse(o.aprobada)
        self.assertIn("El aviso declara dos sueldos distintos (varias modalidades)",
                      o.motivos_rechazo)

    def test_el_motivo_se_explica_solo(self):
        """
        "No declara sueldo" mandaría a buscar en el lugar equivocado: el aviso
        sí lo declara, declara dos. Quien lea el registro tiene que entenderlo
        sin preguntar.
        """
        from motor.modelos import OfertaCruda
        from motor.pipeline import procesar_cruda

        o = procesar_cruda(OfertaCruda(
            fuente="Bumeran", url="https://x.pe/1", puesto="Reponedor",
            empresa="X", descripcion_html=f"<p>{self.DOS}</p>"))
        self.assertTrue(any("dos sueldos distintos" in m for m in o.motivos_rechazo))


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


class PruebaLosCuatroAvisosQueRevisoMentita(unittest.TestCase):
    """
    12 de agosto de 2026. Al abrir la página de rubro de Ventas, Mentita revisó
    los cuatro avisos con el sueldo más bajo y desarmó cada uno.

    Su lectura fue mejor que la mía: yo había propuesto un piso por debajo del
    mínimo legal, y ese piso habría botado el ÚNICO de los cuatro que estaba
    bien. El problema no era que los sueldos fueran bajos — era que tres de
    esos números **no eran sueldos**.

    La causa: la lista de palabras que descalifican un monto solo se miraba
    ANTES del número. En el texto real de los avisos, la palabra que lo
    descalifica va detrás.
    """

    def test_1_el_part_time_de_MEYTEN_si_se_publica(self):
        """
        S/ 650 por 23.5 horas semanales. Está por debajo del mínimo legal y aun
        así es correcto: el aviso dice "Sueldo base" pegado al monto y declara
        que es part time.

        Este es el test que más protege, porque es el que se pierde al ponerse
        estricto de más.
        """
        s = extraer_sueldo(
            "Ingreso a planilla MYPE desde el primer día (essalud y SNP). "
            "Sueldo base de S/. 650 + Comisiones ilimitadas + bonos complementarios."
        )
        self.assertIsNotNone(s, "se perdió un sueldo real de medio tiempo")
        self.assertEqual(s.minimo, 650)

    def test_2_el_bono_por_referidos_de_TCONTAKTO_no_es_sueldo(self):
        """
        El aviso dice "Sueldo fijo + comisiones" sin decir cuánto es el fijo, y
        más abajo ofrece plata por traer gente. El sitio publicó ese aviso con
        un sueldo de S/ 600 — que era lo que pagan por invitar a dos personas.
        """
        s = extraer_sueldo(
            "Sueldo fijo + comisiones ILIMITADAS (sin tope). "
            "Bonos por desempeño + incentivos semanales. "
            "Bono referido: Gana S/300 por invitar a 1 persona y S/600 por invitar 02 personas."
        )
        self.assertIsNone(s, "publicó un bono por referidos como si fuera el sueldo")

    def test_3_la_movilidad_de_Qualidad_Humana_no_es_sueldo(self):
        """
        "Sueldo fijo + S/ 500 de movilidad". La palabra "sueldo" va delante del
        monto y "movilidad" detrás: mirando solo hacia adelante, los S/ 500 del
        pasaje se publicaban como el sueldo de un Ejecutivo Comercial Senior.
        """
        s = extraer_sueldo(
            "Sueldo fijo + S/ 500 de movilidad. "
            "Comisiones del 5% sobre venta (sin IGV). "
            "Bono por cada cliente nuevo o reactivado."
        )
        self.assertIsNone(s, "publicó la movilidad como si fuera el sueldo")

    def test_4_PRESTAMYPE_dice_acorde_al_mercado_y_eso_es_no_decir(self):
        """
        El aviso dice "Sueldo acorde al mercado". El motor sabía reconocer esa
        frase desde el primer día —`declara_sueldo_vago`, con su test— pero esa
        función **solo se usaba para redactar el motivo del rechazo**, nunca
        para decidir. Así que el aviso entró con un S/ 300 suelto.

        Para quien postula, "acorde al mercado" es lo mismo que no decir nada.
        """
        from motor.sueldo import declara_sueldo_vago

        texto = ("EPS opcional (Pacífico). Sueldo acorde al mercado, planilla "
                 "desde el primer día. Línea de carrera.")
        self.assertTrue(declara_sueldo_vago(texto))
        self.assertIsNone(extraer_sueldo(texto))


class PruebaNoPasarseDeListoHaciaAtras(unittest.TestCase):
    """
    Los falsos positivos que aparecieron al arreglar lo de arriba, y que hay
    que seguir cazando: mirar detrás del monto es útil, pero si la ventana se
    estira demasiado empieza a botar avisos correctos.

    La regla que resolvió las dos: solo descalifica lo que va detrás **si está
    pegado al monto con un nexo** —"de", "por", "en"— y dentro de la misma
    frase. Un concepto nuevo empieza con "+", con su propio rótulo o después de
    un punto, y ese no dice nada sobre este monto.
    """

    def test_un_bono_en_la_linea_siguiente_no_contamina(self):
        """"Sueldo base: S/.1200" seguido de "Bono de asistencia: S/.200"."""
        s = extraer_sueldo(
            "Sueldo base: S/.1200\n"
            "Bono de asistencia: S/.200 (sujeto al cumplimiento de asistencia)"
        )
        self.assertEqual(s.minimo, 1200)

    def test_las_comisiones_sumadas_con_mas_no_contaminan(self):
        s = extraer_sueldo("Sueldo base de S/. 650 + Comisiones ilimitadas")
        self.assertEqual(s.minimo, 650)

    def test_un_vale_en_otra_frase_no_contamina(self):
        s = extraer_sueldo(
            "Remuneración S/ 1,600 en planilla. Vale de S/ 200 de alimentación.")
        self.assertEqual(s.minimo, 1600)

    def test_en_planilla_sigue_siendo_un_sueldo(self):
        """El nexo "en" es legítimo y no puede volverse sospechoso."""
        s = extraer_sueldo("Sueldo de S/ 1,800 en planilla con beneficios de ley.")
        self.assertEqual(s.minimo, 1800)


class PruebaElSegundoIntentoDelMismoAviso(unittest.TestCase):
    """
    El aviso de Grupo Qualidad Humana volvió, y por otra puerta.

    Tapada la movilidad, la corrida siguiente lo publicó con **S/ 1,000** — que
    salía de esta línea de sus beneficios:

        Ingreso garantizado de $1,000 durante los primeros 3 meses,
        adicional al fijo y la movilidad.

    Dos errores encima del otro, y el segundo era el grave:

    1. No es el sueldo. El propio aviso dice que es temporal ("los primeros 3
       meses") y que va aparte ("adicional al fijo"). Ese aviso nunca declara
       cuánto paga el puesto.
    2. **Son dólares y se mostraban como soles.** El motor sí distinguía la
       moneda al leerla; la perdía al mostrarla.
    """

    AVISO = ("Sueldo fijo + S/ 500 de movilidad. "
             "Comisiones del 5% sobre venta (sin IGV). "
             "Bono por cada cliente nuevo o reactivado. "
             "Ingreso garantizado de $1,000 durante los primeros 3 meses, "
             "adicional al fijo y la movilidad.")

    def test_el_aviso_completo_no_declara_sueldo(self):
        self.assertIsNone(extraer_sueldo(self.AVISO))

    def test_un_ingreso_garantizado_temporal_no_es_el_sueldo(self):
        self.assertIsNone(extraer_sueldo(
            "Ingreso garantizado de S/ 3,000 durante los primeros 3 meses."))

    def test_lo_adicional_al_fijo_no_es_el_fijo(self):
        self.assertIsNone(extraer_sueldo(
            "Bono de S/ 800, adicional al sueldo fijo."))

    def test_pero_un_sueldo_normal_sigue_entrando(self):
        """Estas frases no pueden volverse una excusa para rechazar de más."""
        s = extraer_sueldo("Sueldo de S/ 3,000 mensuales en planilla.")
        self.assertEqual(s.minimo, 3000)


class PruebaLaMonedaLlegaHastaLaPantalla(unittest.TestCase):
    """
    Un sueldo en dólares no se escribe con S/.

    El motor distinguía la moneda al leer el aviso y la guardaba en la base
    — pero al MOSTRARLA escribía "S/" siempre, en la portada, en la ficha de
    cada oferta y en los datos que lee Google. Una oferta de US$ 1,000
    aparecía publicada como S/ 1,000: casi cuatro veces menos de lo que paga.

    No era un problema de un aviso: afectaba a todas las ofertas en dólares.
    """

    def test_el_parser_distingue_la_moneda(self):
        self.assertEqual(extraer_sueldo("Sueldo: US$ 1,200 mensuales").moneda, "USD")
        self.assertEqual(extraer_sueldo("Sueldo: S/ 1,200 mensuales").moneda, "PEN")

    def test_la_ficha_escribe_el_simbolo_correcto(self):
        from motor.sitio import _sueldo_texto

        self.assertEqual(
            _sueldo_texto({"min": 1000, "max": 1000, "moneda": "USD"}), "US$ 1,000")
        self.assertEqual(
            _sueldo_texto({"min": 1000, "max": 1000, "moneda": "PEN"}), "S/ 1,000")

    def test_sin_moneda_declarada_se_asume_soles(self):
        """Es el 99% del mercado peruano y lo que ya hay guardado."""
        from motor.sitio import _sueldo_texto

        self.assertEqual(_sueldo_texto({"min": 1500, "max": 1500}), "S/ 1,500")

    def test_la_moneda_viaja_a_la_web(self):
        """Si el exportador no la manda, la portada no puede mostrarla."""
        from pathlib import Path

        exportar = (Path(__file__).resolve().parent.parent
                    / "motor" / "exportar.py").read_text(encoding="utf-8")
        self.assertIn('"moneda"', exportar)

        portada = (Path(__file__).resolve().parent.parent
                   / "index.html").read_text(encoding="utf-8")
        self.assertIn("o.moneda", portada)

    def test_google_recibe_la_moneda_de_verdad(self):
        """
        Decirle "PEN" a Google sobre un sueldo en dólares es publicar un dato
        falso en el sitio más visible que tiene el proyecto.
        """
        import json
        from motor.sitio import jobposting

        datos = json.loads(jobposting(
            {"puesto": "Gerente", "empresa": "Acme", "huella": "ab12",
             "min": 3000, "max": 3000, "moneda": "USD", "ciudad": "Lima"},
            "https://cerovagos.com/oferta/x/"))
        self.assertEqual(datos["baseSalary"]["currency"], "USD")


class PruebaElPortalNoResucitaUnMontoDesmentido(unittest.TestCase):
    """
    La tercera puerta del mismo aviso, y la más difícil de cerrar.

    Grupo Qualidad Humana lo intentó tres veces:

      1. S/ 500 — la movilidad.            Tapada mirando detrás del monto.
      2. $1,000 — el ingreso garantizado.  Tapada con `_NO_ES_EL_FIJO`.
      3. S/ 1,000 — **la casilla de sueldo de Bumeran.**

    Contra la tercera no hay defensa mirando su contenido: es un número pelado
    que el empleador escribió en un formulario, sin ninguna palabra alrededor
    que lo delate. La defensa tiene que venir de otro lado.

    Y viene de aquí: **si el propio aviso ya dijo que ese monto no es el
    sueldo, el portal no puede resucitarlo.** Se compara contra los montos que
    el texto descartó, no contra el texto en bruto, porque "$1,000" y
    "S/ 1000" son el mismo número escrito distinto.
    """

    BENEFICIOS = ("Sueldo fijo + S/ 500 de movilidad. "
                  "Comisiones del 5% sobre venta. "
                  "Ingreso garantizado de $1,000 durante los primeros 3 meses, "
                  "adicional al fijo y la movilidad.")

    def _aviso(self, portal: str):
        from datetime import date

        from motor.modelos import OfertaCruda
        from motor.pipeline import procesar_cruda

        cuerpo = (
            "<p>Funciones</p><ul><li>Gestión de cartera</li>"
            "<li>Prospección activa de clientes</li>"
            "<li>Cotizaciones y seguimiento</li></ul>"
            "<p>Requisitos</p><ul><li>Ingeniería o carrera técnica</li>"
            "<li>3 a 5 años en ventas B2B</li><li>Dominio de CRM</li></ul>"
            f"<p>Beneficios</p><ul><li>{self.BENEFICIOS}</li>"
            "<li>Planilla completa</li></ul>"
        )
        return procesar_cruda(OfertaCruda(
            fuente="Bumeran", url="https://x.pe/1",
            puesto="Ejecutivo Comercial Senior", empresa="Acme",
            descripcion_html=cuerpo, sueldo_texto=portal,
            publicado=date.today()))

    def test_el_monto_que_el_aviso_descarto_no_entra_por_el_portal(self):
        """El caso real: la casilla decía 1000, que es el ingreso garantizado."""
        self.assertEqual(self._aviso("S/ 1000").sueldo_min, 0)

    def test_y_el_motivo_dice_lo_que_pasó_de_verdad(self):
        """
        "No declara sueldo" mandaría a buscar en el lugar equivocado: el
        problema no es que falte el dato, es que el dato del portal está
        desmentido por el propio aviso.
        """
        motivos = " ".join(self._aviso("S/ 1000").motivos_rechazo)
        self.assertIn("el propio aviso descarta", motivos)

    def test_un_sueldo_de_verdad_en_el_portal_SI_se_usa(self):
        """
        La regla no puede volverse una excusa para desconfiar del portal
        siempre. Si la casilla trae un monto que el aviso no ha descartado, se
        usa: es la última red y hace falta.
        """
        self.assertEqual(self._aviso("S/ 2500").sueldo_min, 2500)

    def test_montos_que_no_son_sueldo_ve_los_dos(self):
        from motor.sueldo import montos_que_no_son_sueldo

        self.assertEqual(sorted(montos_que_no_son_sueldo(self.BENEFICIOS)),
                         [500, 1000])

    def test_un_aviso_limpio_no_descarta_nada(self):
        from motor.sueldo import montos_que_no_son_sueldo

        self.assertEqual(montos_que_no_son_sueldo("Sueldo: S/ 2,500 mensuales."),
                         set())
