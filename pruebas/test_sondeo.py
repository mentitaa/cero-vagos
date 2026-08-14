"""
El sondeo: contar antes de programar.

Estas pruebas están escritas contra los dos errores reales del proyecto, que
fueron el mismo error dos veces — dar por buena una fuente sin mirar adentro:

- **BuscoTrabajo.** Su robots.txt nos deja entrar y es la única bolsa peruana
  fuera del grupo Jobint. Estuvo semanas en pendientes como la fuente que
  faltaba. Tiene **4 empleos activos**, tres de la misma empresa.
- **Las bolsas universitarias.** 501 empresas y 8,287 vacantes, y se
  descartaron igual: **ninguna publica el sueldo**.

Los dos habrían muerto en veinte minutos con este comando. Por eso lo que se
prueba acá no es que el sondeo "funcione", sino que **diga que no** en los dos
casos donde decir que sí costaría una semana de trabajo perdido.
"""
from __future__ import annotations

import unittest

from motor.sondeo import Aviso, Sondeo, informe


def _aviso(puesto: str, sueldo: int = 0, aprobada: bool = False,
           motivos: list[str] | None = None, moneda: str = "PEN") -> Aviso:
    return Aviso(puesto=puesto, sueldo=sueldo, moneda=moneda, aprobada=aprobada,
                 motivos=motivos or [])


class PruebaLosTresNumerosQueDeciden(unittest.TestCase):
    """
    Un sondeo sirve para contestar tres preguntas, y ninguna de las tres es
    "¿nos dejan entrar?". Esa la contestaba `conectar` y no alcanzó nunca.
    """

    def test_cuenta_cuantos_dicen_el_sueldo(self):
        s = Sondeo(url="https://ejemplo.pe", permite=True, avisos=[
            _aviso("Analista", 3000, aprobada=True),
            _aviso("Cajero"),
            _aviso("Vendedor"),
            _aviso("Jefe de Tienda"),
        ])
        self.assertEqual(s.cuantos, 4)
        self.assertEqual(len(s.con_sueldo), 1)
        self.assertEqual(s.porcentaje_con_sueldo, 25)

    def test_publicables_no_es_lo_mismo_que_con_sueldo(self):
        """
        Decir el sueldo es necesario y no es suficiente: todavía hay que traer
        funciones, requisitos y beneficios. Si el sondeo mezclara las dos
        cosas prometería más avisos de los que la corrida real va a entregar,
        que es exactamente la clase de optimismo que este archivo existe para
        evitar.
        """
        s = Sondeo(url="https://ejemplo.pe", permite=True, avisos=[
            _aviso("Analista", 3000, aprobada=True),
            _aviso("Practicante", 1200, aprobada=False,
                   motivos=["No detalla los beneficios"]),
        ])
        self.assertEqual(len(s.con_sueldo), 2)
        self.assertEqual(len(s.publicables), 1)

    def test_agrupa_por_que_se_caen_los_demas(self):
        s = Sondeo(url="https://ejemplo.pe", permite=True, avisos=[
            _aviso("A", motivos=["El aviso no declara sueldo"]),
            _aviso("B", motivos=["El aviso no declara sueldo"]),
            _aviso("C", motivos=["El aviso no declara sueldo", "Faltan requisitos"]),
        ])
        self.assertEqual(s.motivos_mas_comunes[0], ("El aviso no declara sueldo", 3))


class PruebaLosDosErroresQueYaPasaron(unittest.TestCase):

    def test_la_bolsa_universitaria_ninguno_dice_el_sueldo(self):
        """
        El caso de verdad: mucho volumen, empresas serias, y cero sueldos. El
        sondeo tiene que decirlo con todas sus letras, porque el volumen por
        sí solo es convincente y ahí estuvo la trampa.
        """
        s = Sondeo(url="https://bolsa.universidad.pe", permite=True,
                   avisos=[_aviso(f"Practicante {i}") for i in range(20)])

        self.assertFalse(s.vale_la_pena)
        texto = informe(s)
        self.assertIn("NINGUNO dice el sueldo", texto)
        self.assertIn("no escribas el lector", texto)

    def test_buscotrabajo_deja_entrar_y_no_tiene_avisos(self):
        """
        Permiso concedido, cero contenido. `conectar` habría dicho que sí.
        """
        s = Sondeo(url="https://buscotrabajo.pe", permite=True,
                   como_esta_hecha="Web propia, se lee sin navegador",
                   avisos=[_aviso("Vendedor"), _aviso("Cajero"),
                           _aviso("Asesor"), _aviso("Repartidor")])

        texto = informe(s)
        self.assertIn("4", texto)
        self.assertIn("no escribas el lector", texto.lower())

    def test_una_bolsa_que_si_vale_la_pena_lo_dice(self):
        s = Sondeo(url="https://empresa.pe/careers", permite=True, avisos=(
            [_aviso(f"Con sueldo {i}", 2500, aprobada=True) for i in range(6)]
            + [_aviso(f"Sin sueldo {i}") for i in range(4)]))

        self.assertTrue(s.vale_la_pena)
        self.assertIn("Vale la pena", informe(s))


class PruebaCuandoNoSePuedeNiEntrar(unittest.TestCase):

    def test_sin_permiso_no_inventa_numeros(self):
        """
        La regla 6: si no se puede leer el robots.txt, se asume que no hay
        permiso. El informe no debe rellenar el hueco con ceros que parezcan
        una medición.
        """
        s = Sondeo(url="https://cerrado.pe", permite=False,
                   problema="No se puede entrar: robots.txt no responde")
        texto = informe(s)

        self.assertIn("NO", texto)
        self.assertIn("No se pudo contar nada", texto)
        self.assertNotIn("Vale la pena", texto)

    def test_si_necesita_navegador_lo_dice_y_no_finge_haber_contado(self):
        s = Sondeo(url="https://muevete.falabella.com", permite=True,
                   problema="Aplicación en JavaScript: hace falta navegador (Playwright)",
                   como_esta_hecha="Aplicación en JavaScript: hace falta navegador (Playwright)")
        texto = informe(s)

        self.assertIn("navegador", texto)
        self.assertIn("No se pudo contar nada", texto)


class PruebaElSondeoNoTocaLaBase(unittest.TestCase):

    def test_no_importa_el_almacen(self):
        """
        Un sondeo es una pregunta, no una recolección. Si importara el almacén
        alguien terminaría guardando lo que sondeó, y una muestra de prueba
        entraría al sitio como si fuera oferta real.
        """
        import pathlib
        fuente = (pathlib.Path(__file__).resolve().parent.parent
                  / "motor" / "sondeo.py").read_text(encoding="utf-8")
        self.assertNotIn("Almacen", fuente)
        self.assertNotIn("guardar(", fuente)


if __name__ == "__main__":
    unittest.main()
