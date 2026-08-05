"""
El filtro Cero Vagos: score de completitud 0–100.

Regla de oro: sin sueldo, no hay score que valga. Un aviso sin monto se rechaza
aunque tenga funciones, requisitos y beneficios perfectos.

Rúbrica
    Sueldo .............. 30 pts   (eliminatorio)
    Qué vas a hacer ..... 25 pts   (eliminatorio: mínimo 3 funciones)
    Qué piden ........... 20 pts   (eliminatorio: mínimo 3 requisitos)
    Qué te dan .......... 15 pts   (eliminatorio: mínimo 2 beneficios)
    Metadata ............ 10 pts   (empresa, ciudad, modalidad, frescura)
                         -----
                          100

UMBRAL_PUBLICACION = 70 y además debe pasar los cuatro eliminatorios.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from .modelos import sin_tildes
from .normalizar import es_relleno
from .sueldo import Sueldo, declara_sueldo_vago

UMBRAL_PUBLICACION = 70

# Dos meses. Pasado ese punto el aviso sale de la web, aunque siga abierto:
# una bolsa de trabajo llena de avisos viejos deja de ser útil.
MAX_DIAS_ANTIGUEDAD = 60

# ---------------------------------------------------------------------------
# Perfiles
#
# El sector público y el privado no publican igual, así que no se les puede
# exigir igual.
#
#   funciones  → en el Estado las funciones suelen quedar en el PDF de las
#                bases, así que basta con una. En el privado se exigen tres:
#                ahí no hay excusa.
#   plazo      → si el aviso DICE hasta cuándo se puede postular y esa fecha ya
#                pasó, se bota: mostrar una convocatoria cerrada es hacer
#                perder el tiempo. Si no lo dice, se usa la antigüedad como
#                sustituto, y ahí cada sector tiene su ritmo.
#
#   dias_sin_cierre → cuántos días aguanta un aviso QUE NO DECLARA su fecha de
#                cierre. Una convocatoria CAS suele estar abierta entre 5 y 15
#                días, así que a las tres semanas ya está cerrada aunque no lo
#                diga. En el privado los procesos duran más.
# ---------------------------------------------------------------------------

PERFILES: dict[str, dict[str, object]] = {
    "privado": {"funciones": 3, "requisitos": 3, "beneficios": 2,
                "dias_sin_cierre": 45},
    # Al Estado NO se le exige la lista de funciones. No es una concesión:
    # es reconocer que publica distinto. Una convocatoria CAS trae el puesto
    # normado ("Técnico Administrativo I"), el sueldo exacto, los requisitos
    # detallados y el régimen laboral que fija los beneficios por ley — pero
    # las funciones viven en el PDF de las bases, que el portal no enlaza.
    #
    # La vara del privado se diseñó contra otra cosa: el aviso que dice
    # "apoyar en labores del área" para no comprometerse. Ese sí esconde.
    #
    # Ojo: dejar de ser eliminatorio no es salir gratis. Los 25 puntos de
    # funciones se pierden enteros, así que el aviso tiene que compensarlos
    # en todo lo demás para llegar al umbral de 70. Quien no llega, no entra.
    "publico": {"funciones": 0, "requisitos": 3, "beneficios": 2,
                "dias_sin_cierre": 21},
}

# ---------------------------------------------------------------------------
# El sueldo no se negocia
#
# Decisión tomada y cerrada: un aviso sin monto no se publica, venga de donde
# venga. No hay excepción por "empresa verificada" ni etiqueta que lo suavice.
# Es lo único que distingue a Cero Vagos de cualquier otro portal, y quien
# llega por esa promesa y encuentra avisos sin monto, no vuelve.
#
# A propósito no existe una opción para desactivarlo: una regla que se puede
# apagar con una línea termina apagada.
# ---------------------------------------------------------------------------

# Señales de que los beneficios son reales y no adorno.
BENEFICIOS_CONCRETOS = (
    "planilla", "eps", "essalud", "seguro", "sctr", "bono", "utilidades",
    "gratificacion", "cts", "afp", "movilidad", "alimentacion", "almuerzo",
    "comedor", "asignacion familiar", "vacaciones", "capacitacion",
    "descuento", "home office", "dia libre", "horario flexible", "convenio",
    "subvencion", "aguinaldo", "canasta", "linea de carrera", "vale",
)

# Señales de que los requisitos son verificables.
REQUISITOS_CONCRETOS = (
    "años", "anos", "año", "experiencia", "titulado", "bachiller", "egresado",
    "estudiante", "tecnico", "universitario", "licencia", "colegiatura",
    "certificacion", "excel", "ingles", "manejo de", "conocimiento en",
    "dominio de", "disponibilidad",
)


@dataclass
class Resultado:
    total: int = 0
    detalle: dict[str, int] = field(default_factory=dict)
    motivos: list[str] = field(default_factory=list)   # por qué se rechaza
    notas: list[str] = field(default_factory=list)     # observaciones no fatales
    perfil: str = "privado"

    @property
    def aprobada(self) -> bool:
        return not self.motivos and self.total >= UMBRAL_PUBLICACION


# --------------------------------------------------------------------------

def _puntuar_sueldo(sueldo: Sueldo | None, texto_completo: str, r: Resultado) -> int:
    if sueldo is None:
        r.motivos.append("Sueldo declarado como 'a convenir' o similar"
                         if declara_sueldo_vago(texto_completo) else "No declara sueldo")
        return 0

    pts = 20                                  # base por declarar un monto
    if sueldo.es_rango:
        pts += 6                              # un rango es más honesto que un número suelto
    else:
        pts += 3
    if sueldo.confianza >= 95:
        pts += 4
    elif sueldo.confianza >= 85:
        pts += 2

    if sueldo.moneda == "PEN" and sueldo.minimo < 1130:
        r.notas.append("Sueldo por debajo de la RMV: revisar si es part-time o práctica")

    return min(pts, 30)


def _puntuar_funciones(funciones: list[str], minimo: int, r: Resultado) -> int:
    utiles = [f for f in funciones if not es_relleno(f)]
    if len(utiles) < minimo:
        r.motivos.append(f"Solo {len(utiles)} funciones detalladas (mínimo {minimo})")
        return len(utiles) * 4

    if not utiles:
        # El perfil permite publicar sin lista de funciones (hoy solo el
        # Estado, ver PERFILES). Se pierden los 25 puntos completos y queda
        # anotado, para que la ficha pueda decir dónde encontrarlas en vez de
        # mostrar un hueco.
        r.notas.append("Las funciones están en las bases del concurso")
        return 0

    # Con menos de tres funciones se aprueba, pero no se premia igual.
    pts = 14 if len(utiles) >= 3 else 9
    if len(utiles) >= 5:
        pts += 5
    elif len(utiles) >= 4:
        pts += 3

    largo_medio = sum(len(f) for f in utiles) / len(utiles)
    if largo_medio >= 60:
        pts += 6
    elif largo_medio >= 40:
        pts += 3

    return min(pts, 25)


def _puntuar_requisitos(requisitos: list[str], minimo: int, r: Resultado) -> int:
    utiles = [q for q in requisitos if not es_relleno(q)]
    if len(utiles) < minimo:
        r.motivos.append(f"Solo {len(utiles)} requisitos (mínimo {minimo})")
        return len(utiles) * 3

    pts = 11
    if len(utiles) >= 5:
        pts += 3

    concretos = sum(
        1 for q in utiles if any(s in sin_tildes(q) for s in REQUISITOS_CONCRETOS)
    )
    proporcion = concretos / len(utiles)
    if proporcion >= 0.6:
        pts += 6
    elif proporcion >= 0.35:
        pts += 3
    else:
        r.notas.append("Requisitos poco verificables (sin años, estudios ni herramientas)")

    return min(pts, 20)


def _puntuar_beneficios(beneficios: list[str], minimo: int, r: Resultado) -> int:
    utiles = [b for b in beneficios if not es_relleno(b)]
    if len(utiles) < minimo:
        r.motivos.append(f"Solo {len(utiles)} beneficios listados (mínimo {minimo})")
        return len(utiles) * 3

    pts = 8
    concretos = sum(
        1 for b in utiles if any(s in sin_tildes(b) for s in BENEFICIOS_CONCRETOS)
    )
    if concretos == 0:
        r.motivos.append("Beneficios genéricos: ninguno menciona planilla, seguro, bono ni similar")
        return 4

    if concretos >= 3:
        pts += 7
    elif concretos == 2:
        pts += 5
    else:
        pts += 2

    return min(pts, 15)


def _puntuar_metadata(
    empresa: str, ciudad: str, modalidad: str, publicado: date | None,
    vence: date | None, dias_sin_cierre: int, r: Resultado,
) -> int:
    pts = 0
    hoy = date.today()

    if vence:
        # El aviso dice hasta cuándo. Si ya pasó, no hay nada que discutir.
        if vence < hoy:
            r.motivos.append(f"El plazo cerró el {vence.strftime('%d/%m/%Y')}")
        else:
            quedan = (vence - hoy).days
            pts += 2 if quedan >= 2 else 1
    elif publicado:
        # No dice hasta cuándo. Se usa la antigüedad como sustituto: pasado
        # cierto punto, la convocatoria está cerrada aunque nadie lo escriba.
        dias = (hoy - publicado).days
        if dias > dias_sin_cierre:
            r.motivos.append(
                f"No dice hasta cuándo postular y se publicó hace {dias} días "
                f"(máximo {dias_sin_cierre} sin fecha de cierre)"
            )

    plano = sin_tildes(empresa)
    if empresa and not any(x in plano for x in ("confidencial", "importante empresa",
                                                "empresa lider", "reconocida empresa",
                                                "prestigiosa empresa")):
        pts += 4
    else:
        r.notas.append("Empresa no identificada")

    if ciudad:
        pts += 3
    else:
        r.notas.append("Sin ubicación clara")

    if modalidad:
        pts += 1

    if publicado:
        dias = (date.today() - publicado).days
        if dias > MAX_DIAS_ANTIGUEDAD:
            r.motivos.append(
                f"Publicado hace {dias} días (máximo {MAX_DIAS_ANTIGUEDAD})"
            )
        elif dias <= 3:
            pts += 2
        elif dias <= 10:
            pts += 1
    else:
        r.notas.append("Sin fecha de publicación")

    return min(pts, 10)


# --------------------------------------------------------------------------

def evaluar(
    *,
    sueldo: Sueldo | None,
    funciones: list[str],
    requisitos: list[str],
    beneficios: list[str],
    empresa: str = "",
    ciudad: str = "",
    modalidad: str = "",
    publicado: date | None = None,
    vence: date | None = None,
    texto_completo: str = "",
    perfil: str = "privado",
) -> Resultado:
    """Aplica la rúbrica completa y devuelve el resultado con su detalle."""
    r = Resultado()
    minimos = PERFILES.get(perfil, PERFILES["privado"])
    r.perfil = perfil

    r.detalle["sueldo"] = _puntuar_sueldo(sueldo, texto_completo, r)
    r.detalle["funciones"] = _puntuar_funciones(funciones, int(minimos["funciones"]), r)
    r.detalle["requisitos"] = _puntuar_requisitos(requisitos, int(minimos["requisitos"]), r)
    r.detalle["beneficios"] = _puntuar_beneficios(beneficios, int(minimos["beneficios"]), r)
    r.detalle["metadata"] = _puntuar_metadata(
        empresa, ciudad, modalidad, publicado, vence,
        int(minimos.get("dias_sin_cierre", 45)), r,
    )

    r.total = sum(r.detalle.values())

    if not r.motivos and r.total < UMBRAL_PUBLICACION:
        r.motivos.append(f"Score {r.total} por debajo del umbral {UMBRAL_PUBLICACION}")

    return r


def explicar(r: Resultado) -> str:
    """Salida legible para el CLI y para depurar el filtro."""
    lineas = [f"Score: {r.total}/100  ->  {'APROBADA' if r.aprobada else 'RECHAZADA'}"]
    for clave, valor in r.detalle.items():
        lineas.append(f"  {clave:<12} {valor:>3}")
    for m in r.motivos:
        lineas.append(f"  ✗ {m}")
    for n in r.notas:
        lineas.append(f"  · {n}")
    return "\n".join(lineas)
