"""
Pipeline: de aviso crudo a oferta publicable.

    fuente -> OfertaCruda -> normalizar -> puntuar -> filtrar -> almacén
"""
from __future__ import annotations

import re
from collections import Counter
from datetime import date, datetime

from .almacen import Almacen
from .fuentes.base import ErrorFuente, Fuente
from .modelos import Oferta, OfertaCruda
from .normalizar import (
    armar_resumen, deducir_puesto, detectar_categoria, detectar_modalidad,
    detectar_ubicacion, extraer_bloques, html_a_lineas, limpiar_puesto,
    titulo_nombra_el_puesto,
)
from .score import evaluar
from .sueldo import extraer_sueldo


def _fecha_iso(valor) -> date | None:
    if isinstance(valor, date):
        return valor
    try:
        return date.fromisoformat(str(valor)[:10]) if valor else None
    except ValueError:
        return None


def procesar_cruda(cruda: OfertaCruda) -> Oferta:
    """Normaliza y puntúa un aviso. No decide dónde guardarlo."""
    cuerpo = cruda.cuerpo()
    bloques = extraer_bloques(cuerpo)
    texto_plano = " ".join(html_a_lineas(cuerpo))

    # De dónde sale el sueldo, en orden, y el orden importa:
    #
    #   1. El TEXTO DEL AVISO cuando lo nombra: "Sueldo base: S/ 1,200",
    #      "Remuneración: S/ 1,130". Eso lo escribió el empleador con todas
    #      sus letras y no admite otra lectura.
    #   2. La ficha de datos del portal (`baseSalary` del JSON-LD).
    #   3. Cualquier monto del cuerpo, como último recurso.
    #
    # El 1 manda sobre el 2 por decisión de Mentita (7/8/2026), y la razón está
    # en los avisos que lo destaparon: un asesor de cobranza salía con
    # S/ 500 – S/ 1,000 y un promotor con S/ 600, mientras el propio aviso
    # decía "Sueldo base: S/.1200" y "Sueldo básico: S/ 1,130". El empleador
    # había metido sus COMISIONES en el campo de sueldo del portal.
    #
    # No es aflojar la regla 1, es afinarla: entre dos números que dicen ser el
    # sueldo, gana el que viene con la palabra "sueldo" pegada.
    sueldo = (extraer_sueldo(texto_plano, solo_etiquetado=True)
              or extraer_sueldo(cruda.sueldo_texto)
              or extraer_sueldo(texto_plano))

    ciudad, departamento = detectar_ubicacion(cruda.ubicacion_texto, texto_plano)
    modalidad = detectar_modalidad(f"{cruda.ubicacion_texto} {texto_plano}")
    categoria = detectar_categoria(cruda.puesto, texto_plano)

    resultado = evaluar(
        sueldo=sueldo,
        funciones=bloques["funciones"],
        requisitos=bloques["requisitos"],
        beneficios=bloques["beneficios"],
        empresa=cruda.empresa,
        ciudad=ciudad,
        modalidad=modalidad,
        publicado=cruda.publicado,
        vence=_fecha_iso(cruda.extra.get("vence")),
        texto_completo=f"{cruda.sueldo_texto} {texto_plano}",  # noqa: E501
        # El Estado y el sector privado no publican igual: cada uno tiene su
        # vara. Ver PERFILES en score.py.
        perfil=cruda.extra.get("perfil", "privado"),
    )

    vence = _fecha_iso(cruda.extra.get("vence"))
    # El título viene con publicidad encima; se guarda solo el puesto.
    puesto = limpiar_puesto(cruda.puesto)

    # Hay títulos que dicen dónde queda el trabajo o para qué marca es, pero
    # no qué se hace: "Papa Johns", "Primax Cerro Azul", "Trabaja cerca al
    # Parque de la Amistad". Publicar eso sería exactamente la oferta vaga que
    # este motor existe para rechazar, solo que en el titular.
    #
    # Se intenta deducir el oficio del texto del propio aviso. Si el aviso no
    # lo nombra en ninguna parte, el aviso se cae: es preferible perderlo a
    # inventarle un cargo a una empresa.
    if not titulo_nombra_el_puesto(puesto):
        deducido = deducir_puesto(
            armar_resumen(bloques, cruda.puesto),
            bloques["funciones"],
            bloques["requisitos"],
        )
        if deducido:
            puesto = deducido
        else:
            # Basta con anotar el motivo: un aviso con motivos no se aprueba,
            # por definición (ver Resultado.aprobada en score.py).
            resultado.motivos.append("El aviso no dice qué puesto es")

    return Oferta(
        huella=Oferta.calcular_huella(puesto, cruda.empresa, ciudad),
        fuente=cruda.fuente,
        url=cruda.url,
        puesto=puesto,
        empresa=cruda.empresa.strip(),
        ciudad=ciudad,
        departamento=departamento,
        modalidad=modalidad,
        categoria=categoria,
        sueldo_min=sueldo.minimo if sueldo else 0,
        sueldo_max=sueldo.maximo if sueldo else 0,
        moneda=sueldo.moneda if sueldo else "PEN",
        resumen=armar_resumen(bloques, cruda.puesto),
        funciones=bloques["funciones"],
        requisitos=bloques["requisitos"],
        beneficios=bloques["beneficios"],
        publicado=cruda.publicado,
        vence=vence,
        score=resultado.total,
        detalle_score=resultado.detalle,
        motivos_rechazo=resultado.motivos,
        aprobada=resultado.aprobada,
    )


class Pipeline:
    def __init__(self, fuentes: list[Fuente], almacen: Almacen | None = None,
                 verboso: bool = True, retomar: bool = True):
        self.fuentes = fuentes
        self.almacen = almacen or Almacen()
        self.verboso = verboso
        # Retomar = saltarse lo ya revisado hoy. Es lo que hace que una corrida
        # interrumpida (la laptop se suspendió, se cortó la luz) siga donde
        # quedó en vez de empezar de cero.
        self.retomar = retomar

    def _log(self, msg: str) -> None:
        if self.verboso:
            print(msg)

    def correr(self, limite_por_fuente: int = 100) -> dict:
        resumen = {"leidas": 0, "aprobadas": 0, "rechazadas": 0,
                   "nuevas": 0, "duplicadas": 0, "motivos": Counter(),
                   "fuentes_sin_datos": []}
        vistas: set[str] = set()

        urls_previas: set[str] = self.almacen.urls_a_saltar() if self.retomar else set()
        if urls_previas:
            self._log(f"{len(urls_previas)} avisos ya revisados se saltarán "
                      f"(rechazados hace menos de {self.almacen.DIAS_RECHAZADAS} días, "
                      f"aprobados hace menos de {self.almacen.DIAS_APROBADAS}).")

        for fuente in self.fuentes:
            if hasattr(fuente, "ya_visto"):
                fuente.ya_visto = urls_previas.__contains__
            if hasattr(fuente, "avisar"):
                fuente.avisar = lambda m: self._log(f"  {m}")

            if not fuente.activa:
                self._log(f"\n▸ {fuente.nombre}\n  ! Inactiva: {_por_que_inactiva(fuente)}")
                resumen["fuentes_sin_datos"].append(fuente.nombre)
                continue

            inicio = datetime.now()
            leidas = aprobadas = rechazadas = 0
            self._log(f"\n▸ {fuente.nombre}")

            # Se procesa aviso por aviso, según van llegando, en vez de esperar
            # a tenerlos todos. En un portal que hay que renderizar con
            # navegador, esperar significa quince minutos de pantalla en blanco
            # sin saber si el proceso sigue vivo.
            try:
                avisos = fuente.recolectar(limite_por_fuente)
            except ErrorFuente as e:
                self._log(f"  ! {e}")
                resumen["fuentes_sin_datos"].append(fuente.nombre)
                continue

            for cruda in avisos:
                leidas += 1
                oferta = procesar_cruda(cruda)

                if oferta.huella in vistas:
                    resumen["duplicadas"] += 1
                    continue
                vistas.add(oferta.huella)

                estado = self.almacen.guardar(oferta)
                if estado == "nueva":
                    resumen["nuevas"] += 1

                if oferta.aprobada:
                    aprobadas += 1
                    self._log(f"  ✓ [{oferta.score:>3}] {oferta.puesto} — "
                              f"{oferta.empresa} ({oferta.sueldo_texto})")
                else:
                    rechazadas += 1
                    motivos = oferta.motivos_rechazo or ["sin motivo"]
                    # Se cuentan TODOS los motivos, no solo el primero: si un
                    # aviso falla en tres cosas, hay que verlas todas para saber
                    # dónde está el cuello de botella real.
                    for m in motivos:
                        resumen["motivos"][re.sub(r"\d+", "N", m)] += 1
                    self._log(f"  ✗ [{oferta.score:>3}] {oferta.puesto} — {motivos[0]}")

            # Cero avisos no es un resultado: es un síntoma. Hay que explicarlo.
            if not leidas:
                resumen["fuentes_sin_datos"].append(fuente.nombre)
                self._log("  ! No se obtuvo ningún aviso. Motivo:")
                sin_datos = list(getattr(fuente, "errores", []) or ["sin detalle"])
                for problema in sin_datos[:5]:
                    self._log(f"      · {problema}")
                if len(sin_datos) > 5:
                    self._log(f"      · … y {len(sin_datos) - 5} problemas más")
                continue

            # Los tropiezos también se cuentan cuando SÍ hubo avisos: un PDF que
            # no se pudo abrir explica un rechazo, y hay que poder verlo.
            problemas = list(getattr(fuente, "errores", []))
            if problemas:
                self._log("  Incidencias:")
                for p in problemas[:5]:
                    self._log(f"      · {p}")
                if len(problemas) > 5:
                    self._log(f"      · … y {len(problemas) - 5} más")

            resumen["leidas"] += leidas
            resumen["aprobadas"] += aprobadas
            resumen["rechazadas"] += rechazadas
            self.almacen.registrar_corrida(
                inicio, fuente.nombre, leidas, aprobadas, rechazadas,
                {"limite": limite_por_fuente},
            )

        vencidas = self.almacen.vencer_antiguas()
        resumen["vencidas"] = vencidas
        resumen["motivos"] = dict(resumen["motivos"])
        return resumen


def _por_que_inactiva(fuente) -> str:
    from .fuentes.render import HAY_PLAYWRIGHT
    try:
        import requests  # noqa: F401
    except ImportError:
        return "falta la librería 'requests'  →  pip install requests"
    if getattr(fuente, "necesita_render", False) and not HAY_PLAYWRIGHT:
        return ("este portal carga por JavaScript y falta Playwright  →  "
                "pip install playwright && playwright install chromium")
    return "sin motivo declarado"


def imprimir_resumen(r: dict) -> None:
    tasa = round(r["aprobadas"] / r["leidas"] * 100, 1) if r["leidas"] else 0
    print("\n" + "═" * 58)
    print("  RESUMEN DE LA CORRIDA")
    print("═" * 58)
    print(f"  Avisos leídos      {r['leidas']:>6}")
    print(f"  Pasaron el filtro  {r['aprobadas']:>6}   ({tasa}%)")
    print(f"  Rechazados         {r['rechazadas']:>6}")
    print(f"  Nuevos en la base  {r['nuevas']:>6}")
    print(f"  Duplicados         {r['duplicadas']:>6}")
    print(f"  Marcados vencidos  {r.get('vencidas', 0):>6}")
    if r["motivos"]:
        print("\n  Por qué se rechazaron (un aviso puede fallar en varias):")
        for motivo, n in sorted(r["motivos"].items(), key=lambda kv: -kv[1]):
            print(f"    {n:>4}×  {motivo}")
    if r.get("fuentes_sin_datos"):
        print("\n  Fuentes que no entregaron nada:")
        for nombre in r["fuentes_sin_datos"]:
            print(f"    · {nombre}")
        print("\n  Revisa el detalle de cada una más arriba, o corre:")
        print("    python3 -m motor diagnostico")
    print("═" * 58)
