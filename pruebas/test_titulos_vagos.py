"""
Los títulos que no dicen qué es el trabajo: "Técnico", "Jefe", "Especialista".

EL AGUJERO DE LA REGLA 8
------------------------
La regla 8 dice que el título tiene que decir qué es el trabajo, y existe para
cazar avisos como "Papa Johns" o "Trabaja cerca al Parque de la Amistad", que
dicen la marca o el lugar pero no el oficio.

Lo que se le escapaba: **"Técnico" también pasaba**, porque "tecnico" está en
la lista de oficios. Pero un rango solo no es un puesto. "Enfermera" dice qué
vas a hacer; "Especialista" obliga a preguntar en qué.

Esa es la distinción que resuelve el asunto: hay palabras que nombran un
OFICIO y palabras que nombran un RANGO.

QUÉ SE DECIDIÓ, Y QUÉ NO
------------------------
**No se rechazan** (Mentita, 13/8/2026). Se miden, y salen en `motor stats`
separados en dos grupos, porque son dos casos distintos:

  · Del **Estado** no esconden nada: "Técnico I" es el cargo tal como figura
    en la escala normada.
  · Del **privado** sí es una elección: nadie obliga a una consultora a
    titular su aviso "Asesor" a secas.

Si el número del privado crece, hay motivo para endurecer solo ese lado.

TAMPOCO SE COMPLETAN SOLOS
--------------------------
Se probó deducir el cargo del texto del aviso y **no se puede con honestidad**.
El requisito "Título de técnico en enfermería" dice lo que hay que SER, no lo
que es el puesto; y con "Jefe" + "Título en Ingeniería Civil" saldría
"Ingeniero Civil", que puede no ser el cargo. Eso es inventar, y la regla 8 lo
prohíbe expresamente.
"""
from __future__ import annotations

import unittest
from datetime import date, timedelta

from motor.almacen import Almacen
from motor.modelos import Oferta
from motor.normalizar import titulo_nombra_el_puesto, titulo_vago


class PruebaQueEsUnTituloVago(unittest.TestCase):

    def test_un_rango_solo_no_dice_nada(self):
        for titulo in ("Técnico", "Jefe", "Especialista", "Auxiliar",
                       "Analista", "Asistente", "Supervisor", "Asesor"):
            with self.subTest(titulo=titulo):
                self.assertTrue(titulo_vago(titulo))

    def test_el_numero_de_escala_no_es_una_especialidad(self):
        """"Técnico I" dice el nivel, no el oficio. Sigue sin decir de qué."""
        self.assertTrue(titulo_vago("Técnico I"))
        self.assertTrue(titulo_vago("Especialista II"))

    def test_un_oficio_se_basta_solo(self):
        """
        Y esto es lo que evita pasarse de estricto: "Enfermera" o "Chofer"
        son títulos de una palabra y perfectamente claros.
        """
        for titulo in ("Enfermera", "Chofer", "Docente", "Secretaria",
                       "Almacenero", "Contador I", "Cocinero"):
            with self.subTest(titulo=titulo):
                self.assertFalse(titulo_vago(titulo))

    def test_el_rango_con_especialidad_esta_bien(self):
        for titulo in ("Técnico en Enfermería", "Especialista en Calidad",
                       "Jefe de Oficina de Cooperación", "Asistente Legal",
                       "Asesor de Cobranza", "Operario de Producción",
                       "Especialista Administrativo-Recursos Humanos"):
            with self.subTest(titulo=titulo):
                self.assertFalse(titulo_vago(titulo))

    def test_es_MAS_estricto_que_la_regla_8(self):
        """
        El punto de todo esto. La regla 8 daba por bueno "Técnico" porque es un
        oficio conocido; este detector ve que le falta el de qué.
        """
        self.assertTrue(titulo_nombra_el_puesto("Técnico"))
        self.assertTrue(titulo_vago("Técnico"))


class PruebaSeMidenSeparados(unittest.TestCase):
    """
    El reparto Estado/privado es todo el valor de esta medición: sin él, el
    número junta dos cosas que no se deciden igual.
    """

    def setUp(self):
        self.al = Almacen(":memory:")
        for puesto, empresa, fuente in (
            ("Tecnico", "HOSPITAL EL CARMEN", "Convocatorias CAS"),
            ("Auxiliar", "HOSPITAL EL CARMEN", "Convocatorias CAS"),
            ("Especialista", "UGEL TAYACAJA", "Convocatorias del Estado"),
            ("Asesor", "Impulsate", "Bumeran"),
            ("Supervisor", "EsTalent", "Laborum"),
            ("Tecnico en Enfermeria", "HOSPITAL EL CARMEN", "Convocatorias CAS"),
            ("Operario de Produccion", "CYL", "Laborum"),
        ):
            self.al.guardar(Oferta(
                huella=Oferta.calcular_huella(puesto, empresa, "Lima"),
                fuente=fuente, url=f"https://x.pe/{puesto}", puesto=puesto,
                empresa=empresa, ciudad="Lima", departamento="Lima",
                sueldo_min=2000, sueldo_max=2000,
                funciones=["a", "b", "c"], requisitos=["a", "b", "c"],
                beneficios=["x", "y"], publicado=date.today(),
                vence=date.today() + timedelta(days=10), aprobada=True, score=80))

    def test_solo_cuenta_los_vagos(self):
        vagos = [v["puesto"] for v in self.al.titulos_vagos()]
        self.assertNotIn("Tecnico en Enfermeria", vagos)
        self.assertNotIn("Operario de Produccion", vagos)
        self.assertEqual(len(vagos), 5)

    def test_separa_el_Estado_del_privado(self):
        vagos = self.al.titulos_vagos()
        del_estado = {v["puesto"] for v in vagos if v["del_estado"]}
        privados = {v["puesto"] for v in vagos if not v["del_estado"]}

        self.assertEqual(del_estado, {"Tecnico", "Auxiliar", "Especialista"})
        self.assertEqual(privados, {"Asesor", "Supervisor"})

    def test_solo_mira_lo_publicado(self):
        """Un aviso rechazado no molesta a nadie: no está en la web."""
        self.al.con.execute("UPDATE ofertas SET vigente = 0 WHERE puesto = 'Asesor'")
        self.al.con.commit()
        self.assertNotIn("Asesor", [v["puesto"] for v in self.al.titulos_vagos()])


if __name__ == "__main__":
    unittest.main()
