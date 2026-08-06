"""
Exportador al sitio.

Genera `datos/ofertas.js`, que el index.html carga con un <script> normal.
Se usa un .js en vez de .json a propósito: así el prototipo funciona abriendo
el archivo con doble clic, sin servidor y sin problemas de CORS.
"""
from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

from .almacen import Almacen

RAIZ = Path(__file__).resolve().parent.parent
SALIDA_JS = RAIZ / "datos" / "ofertas.js"
SALIDA_JSON = RAIZ / "datos" / "ofertas.json"


def _salidas(raiz: Path | None):
    """
    A dónde se escribe. El parámetro existe porque los tests corren sobre una
    carpeta temporal: sin esto escribían encima del archivo de verdad y
    dejaban la web con las dos ofertas de prueba. Pasó.
    """
    base = Path(raiz) if raiz else RAIZ
    return base / "datos" / "ofertas.js", base / "datos" / "ofertas.json"


def _dias_desde(valor: str | None) -> int | None:
    if not valor:
        return None
    try:
        return (date.today() - date.fromisoformat(valor[:10])).days
    except ValueError:
        return None


def _a_formato_web(fila: dict, indice: int) -> dict:
    # Ojo: `dias` puede ser None, y eso NO es lo mismo que cero.
    #
    # Antes se hacía `or 0`, y entonces un aviso sin fecha de publicación
    # aparecía en la web como "Publicada hoy". Las convocatorias CAS no dicen
    # cuándo se publicaron —dicen hasta cuándo se puede postular, que es lo que
    # de verdad importa— así que todas habrían salido con una fecha inventada.
    # Se deja en None y la web se calla en vez de mentir.
    dias = _dias_desde(fila.get("publicado"))
    restantes = _dias_desde(fila.get("vence"))
    # _dias_desde devuelve días transcurridos; para el cierre queremos los que
    # faltan, que es el mismo número al revés.
    restantes = -restantes if restantes is not None else None

    return {
        "id": indice,
        "puesto": fila["puesto"],
        "empresa": fila["empresa"] or "Empresa confidencial",
        "cat": fila["categoria"] or "Otros",
        "min": fila["sueldo_min"] or 0,
        "max": fila["sueldo_max"] or fila["sueldo_min"] or 0,
        "modalidad": fila["modalidad"] or "Presencial",
        "ciudad": fila["ciudad"] or "Perú",
        "fuente": fila["fuente"],
        "dias": max(0, dias) if dias is not None else None,
        "vence": fila.get("vence") or "",
        "restan": restantes,          # None si el aviso no dice hasta cuándo
        "score": fila["score"],
        "resumen": fila["resumen"] or "",
        "funciones": fila["funciones"],
        "requisitos": fila["requisitos"],
        "beneficios": fila["beneficios"],
        "url": fila["url"],
    }


def exportar(almacen: Almacen | None = None, limite: int = 500,
             raiz: Path | None = None) -> dict:
    al = almacen or Almacen()
    # Nunca se exporta sin depurar antes: si no, una oferta cuyo plazo cerró
    # anoche seguiría publicada hasta la próxima recolección.
    quitadas = al.depurar()
    filas = al.aprobadas(limite)
    ofertas = [_a_formato_web(f, i + 1) for i, f in enumerate(filas)]
    stats = al.estadisticas()

    payload = {
        "generado": datetime.now().isoformat(timespec="seconds"),
        "total": len(ofertas),
        "stats": stats,
        "ofertas": ofertas,
    }

    salida_js, salida_json = _salidas(raiz)
    salida_js.parent.mkdir(parents=True, exist_ok=True)
    cuerpo = json.dumps(payload, ensure_ascii=False, indent=1)

    salida_json.write_text(cuerpo, encoding="utf-8")
    salida_js.write_text(
        "/* Generado por el motor de Cero Vagos. No editar a mano. */\n"
        f"window.CERO_VAGOS = {cuerpo};\n",
        encoding="utf-8",
    )

    return {"archivo": str(SALIDA_JS), "ofertas": len(ofertas),
            "stats": stats, "quitadas": quitadas}
