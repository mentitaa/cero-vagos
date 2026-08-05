"""
Pruebas del archivo que gobierna la corrida automática de GitHub.

Por qué existen: el 5 de agosto de 2026 la web pasó de 68 ofertas a 33 y la
corrida salió **en verde**. Dos cosas se juntaron para que nadie se enterara:

1. Bumeran y Laborum compartían un mismo paso, siempre en ese orden. Cuando el
   reloj se acababa, el que quedaba a medias era siempre Laborum. Ese día ni
   siquiera llegó a correr.
2. Los pasos llevan `continue-on-error`, que es correcto —un portal caído no
   debe tumbar el resto— pero hace que un fallo salga con check verde.

Nada de esto es código Python, así que ningún test lo miraba. Se lee el archivo
como texto a propósito, sin pyyaml: no hace falta instalar nada nuevo para
correr las pruebas.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FLUJO = RAIZ / ".github" / "workflows" / "actualizar.yml"


class PruebaCorridaAutomatica(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.yml = FLUJO.read_text(encoding="utf-8")
        # (nombre del paso, minutos de su reloj)
        cls.pasos = re.findall(
            r"- name:\s*(.+?)\n(?:.*?\n)??\s*timeout-minutes:\s*(\d+)", cls.yml)

    def test_cada_portal_privado_tiene_su_propio_reloj(self):
        """
        Lo que falló. Si vuelven a compartir un paso, el segundo se queda sin
        tiempo y su desaparición no se nota: la corrida sigue saliendo verde.
        """
        con_reloj = {n.strip() for n, _ in self.pasos}
        for portal in ("Bumeran", "Laborum"):
            self.assertIn(portal, con_reloj,
                          f"{portal} debe correr en su propio paso, con su propio reloj")

    def test_los_relojes_caben_en_el_tiempo_del_trabajo(self):
        """
        Si la suma de los pasos pasa del tope del trabajo entero, el último no
        llega a correr nunca y nadie lo ve.
        """
        m = re.search(r"timeout-minutes:\s*(\d+)", self.yml)
        self.assertIsNotNone(m, "el trabajo debe declarar su propio tope")
        total = int(m.group(1))
        suma = sum(int(v) for _, v in self.pasos)
        self.assertLessEqual(
            suma, total,
            f"los pasos suman {suma} min y el trabajo solo aguanta {total}")

    def test_la_recoleccion_nunca_pierde_lo_ya_juntado(self):
        """
        El paso que guarda va con `if: always()`. Sin eso, una corrida que se
        corta a las tres horas tira a la basura todo lo recolectado: vive en el
        servidor de GitHub y se borra con él.
        """
        guardar = self.yml[self.yml.index("Guardar las ofertas nuevas"):]
        self.assertRegex(guardar[:200], r"if:\s*always\(\)")

    def test_el_motor_sabe_correr_una_sola_fuente(self):
        """El flujo pide `--fuente`; si el motor deja de aceptarlo, falla mudo."""
        import subprocess
        import sys
        ayuda = subprocess.run(
            [sys.executable, "-m", "motor", "recolectar", "--help"],
            capture_output=True, text=True, cwd=RAIZ).stdout
        self.assertIn("--fuente", ayuda)


if __name__ == "__main__":
    unittest.main()
