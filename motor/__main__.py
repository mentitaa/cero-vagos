"""
CLI del motor de Cero Vagos.

    python -m motor recolectar --demo         # corre el filtro sin tocar internet
    python -m motor recolectar --limite 50    # corre contra los portales reales
    python -m motor exportar                  # genera datos/ofertas.js para el sitio
    python -m motor stats                     # cómo va la base
    python -m motor probar "S/ 2,800 a 3,400" # prueba el parser de sueldos
    python -m motor rechazos                  # qué se está botando y por qué
"""
from __future__ import annotations

import argparse
import sys

from .almacen import Almacen
from .exportar import exportar
from .fuentes import (
    HAY_PLAYWRIGHT, FuenteDemo, como_conectar, empresas_peru, fuentes_de_arranque,
    fuentes_por_verificar, parsear_convocatoria, portales_peru,
)
from .fuentes.base import USER_AGENT, ErrorFuente
from .fuentes.jsonld import extraer_jobposting
from .fuentes.publicas import enriquecer_con_bases
from .fuentes.robots import Robots
from .pipeline import Pipeline, imprimir_resumen, procesar_cruda
from .score import explicar
from .sueldo import extraer_sueldo


def _fuentes(args) -> list:
    if args.demo:
        return [FuenteDemo()]
    if getattr(args, "publicas", False):
        return fuentes_de_arranque()
    if getattr(args, "empresas", False):
        return empresas_peru()
    return portales_peru()


def cmd_conectar(args) -> None:
    """Dice cómo leer la bolsa de trabajo de una empresa antes de programar nada."""
    print(como_conectar(args.url))


def cmd_probar_url(args) -> None:
    """
    Lee UNA oferta real y muestra qué entendió el motor y si aprobaría.
    Es la forma rápida de saber si un portal nuevo se puede leer.
    """
    try:
        import requests
    except ImportError:
        print("Falta 'requests':  pip install requests")
        return

    robots = Robots()
    if not robots.permite(args.url):
        pol = robots.politica(args.url)
        print(f"robots.txt de {pol.dominio} no permite leer esa URL ({pol.nota})")
        return
    robots.esperar_turno(args.url)

    resp = requests.get(args.url, headers={"User-Agent": USER_AGENT,
                                           "Accept-Language": "es-PE,es;q=0.9"}, timeout=25)
    resp.raise_for_status()
    html = resp.text

    cruda = (extraer_jobposting(html, args.url, "Prueba")
             if args.parser == "jsonld"
             else parsear_convocatoria(html, args.url, "Prueba"))

    if cruda is not None and args.parser != "jsonld" and not args.sin_pdf:
        def bajar(url: str, max_bytes: int = 15 * 1024 * 1024) -> bytes:
            if not robots.permite(url):
                raise ErrorFuente(f"robots.txt no permite {url}")
            robots.esperar_turno(url)
            r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=40)
            r.raise_for_status()
            return r.content

        aviso = enriquecer_con_bases(cruda, html, bajar)
        if aviso:
            print(f"(PDF de las bases: {aviso})")
        elif cruda.extra.get("funciones_desde_pdf"):
            print(f"(Funciones tomadas del PDF: {cruda.extra['funciones_desde_pdf']})")

    if cruda is None:
        print("No se pudo leer la oferta.")
        if "enable JavaScript" in html or len(html) < 2000:
            print("La página llega vacía: es una SPA, hace falta Playwright.")
        return

    o = procesar_cruda(cruda)
    from datetime import date as _date
    vence = cruda.extra.get("vence") or "—"
    estado = ""
    if vence != "—":
        try:
            estado = " (VENCIDA)" if _date.fromisoformat(vence) < _date.today() else " (vigente)"
        except ValueError:
            estado = " (no se pudo leer la fecha)"

    print(f"\nPuesto      {o.puesto}")
    print(f"Entidad     {o.empresa}")
    print(f"Ubicación   {o.ciudad or '—'} ({o.modalidad})")
    print(f"Categoría   {o.categoria}")
    print(f"Sueldo      {o.sueldo_texto}")
    print(f"Publicado   {o.publicado or '—'}")
    print(f"Vence       {vence}{estado}        [hoy es {_date.today()}]")
    if cruda.extra.get("funciones_desde"):
        print(f"Funciones   tomadas de {cruda.extra['funciones_desde']}")
    for titulo, items in (("Funciones", o.funciones),
                          ("Requisitos", o.requisitos),
                          ("Beneficios", o.beneficios)):
        print(f"\n{titulo} ({len(items)})")
        for it in items[:6]:
            print(f"  · {it[:110]}")
    print()
    from .score import Resultado
    r = Resultado(total=o.score, detalle=o.detalle_score, motivos=o.motivos_rechazo)
    print(explicar(r))


def cmd_diagnostico(args) -> None:
    """Revisa cada portal antes de dejarlo corriendo solo."""
    from .bases_pdf import backends_disponibles

    print("Revisando fuentes (esto pide robots.txt y un aviso de muestra)\n")

    lectores = backends_disponibles()
    if lectores:
        print(f"Lectura de PDF: {', '.join(lectores)}\n")
    else:
        print("Aviso: no hay con qué leer PDFs, así que no se podrán sacar las")
        print("       funciones de las bases.  →  pip install pdfplumber\n")

    if not HAY_PLAYWRIGHT:
        print("Aviso: Playwright no está instalado, los portales SPA no se podrán leer.")
        print("       pip install playwright && playwright install chromium\n")

    fuentes = fuentes_de_arranque()
    if args.todas:
        fuentes += portales_peru() + fuentes_por_verificar() + empresas_peru()
    for fuente in fuentes:
        print(fuente.diagnosticar())
        print()


def cmd_recolectar(args) -> None:
    fuentes = _fuentes(args)

    # Corrida diaria: solo mira lo publicado en los últimos días. Mucho más
    # rápido, porque lo viejo ya está en la base.
    if args.dias:
        for f in fuentes:
            if hasattr(f, "dias_publicado"):
                f.dias_publicado = args.dias
        print(f"Buscando solo avisos publicados en los últimos {args.dias} días.\n")

    if getattr(args, "sin_pdf", False):
        for f in fuentes:
            f.enriquecer = None
    else:
        from .bases_pdf import backends_disponibles
        if not backends_disponibles() and any(getattr(f, "enriquecer", None) for f in fuentes):
            print("Aviso: falta con qué leer PDFs, no se podrán sacar las funciones "
                  "de las bases.\n       pip install pdfplumber\n")
    if not args.demo and not any(f.activa for f in fuentes):
        print("Ninguna fuente activa. Instala requests:  pip install requests")
        print("Mientras tanto puedes correr:  python -m motor recolectar --demo")
        sys.exit(1)

    pipeline = Pipeline(fuentes, retomar=not args.rehacer)
    resumen = pipeline.correr(limite_por_fuente=args.limite)
    imprimir_resumen(resumen)

    if args.exportar:
        info = exportar(pipeline.almacen)
        for motivo, n in info.get("quitadas", {}).items():
            print(f"  − {n} ofertas salieron de la web: {motivo}")
        print(f"\n→ {info['ofertas']} ofertas exportadas a {info['archivo']}")


def cmd_exportar(_args) -> None:
    info = exportar()
    print(f"{info['ofertas']} ofertas exportadas a {info['archivo']}")
    print(f"Tasa de aprobación histórica: {info['stats']['tasa_aprobacion']}%")


def cmd_stats(_args) -> None:
    s = Almacen().estadisticas()
    print(f"Procesadas en total   {s['total_procesadas']}")
    print(f"Aprobadas vigentes    {s['aprobadas_vigentes']}")
    print(f"Tasa de aprobación    {s['tasa_aprobacion']}%")
    if s["por_fuente"]:
        print("\nPor fuente:")
        for fuente, n in s["por_fuente"].items():
            print(f"  {n:>5}  {fuente}")


def cmd_rechazos(args) -> None:
    for f in Almacen().rechazadas(args.limite):
        motivo = f["motivos_rechazo"][0] if f["motivos_rechazo"] else "—"
        print(f"[{f['score']:>3}] {f['puesto'][:44]:<44} {motivo}")


def cmd_probar(args) -> None:
    s = extraer_sueldo(args.texto)
    if not s:
        print("Sin sueldo detectable → este aviso se rechazaría.")
        return
    print(f"Detectado: {s.minimo:,} – {s.maximo:,} {s.moneda} {s.periodo}")
    print(f"Literal:   '{s.literal}'   Confianza: {s.confianza}")


def main() -> None:
    p = argparse.ArgumentParser(prog="motor", description="Motor recolector de Cero Vagos")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("recolectar", help="recolectar y filtrar avisos")
    r.add_argument("--demo", action="store_true", help="usar avisos de ejemplo, sin red")
    r.add_argument("--publicas", action="store_true",
                   help="usar las fuentes de arranque (convocatorias del Estado, sin navegador)")
    r.add_argument("--empresas", action="store_true",
                   help="usar las bolsas de trabajo de empresas")
    r.add_argument("--limite", type=int, default=100, help="avisos por fuente")
    r.add_argument("--dias", type=int, default=0,
                   help="solo avisos publicados en los últimos N días (2 para la corrida diaria)")
    r.add_argument("--rehacer", action="store_true",
                   help="volver a revisar todo, incluso lo ya visto hoy")
    r.add_argument("--sin-pdf", dest="sin_pdf", action="store_true",
                   help="no abrir el PDF de las bases (más rápido, menos completo)")
    r.add_argument("--exportar", action="store_true", help="exportar al sitio al terminar")
    r.set_defaults(func=cmd_recolectar)

    d = sub.add_parser("diagnostico", help="revisar robots.txt, sitemaps y lectura por portal")
    d.add_argument("--todas", action="store_true",
                   help="incluir los portales privados y las fuentes sin verificar")
    d.set_defaults(func=cmd_diagnostico)

    u = sub.add_parser("probar-url", help="leer una oferta real y ver si pasaría el filtro")
    u.add_argument("url")
    u.add_argument("--parser", choices=("auto", "jsonld"), default="auto")
    u.add_argument("--sin-pdf", dest="sin_pdf", action="store_true",
                   help="no abrir el PDF de las bases")
    u.set_defaults(func=cmd_probar_url)

    c = sub.add_parser("conectar", help="ver cómo leer la bolsa de trabajo de una empresa")
    c.add_argument("url", help="URL de la página 'trabaja con nosotros'")
    c.set_defaults(func=cmd_conectar)

    e = sub.add_parser("exportar", help="generar datos/ofertas.js")
    e.set_defaults(func=cmd_exportar)

    s = sub.add_parser("stats", help="estado de la base")
    s.set_defaults(func=cmd_stats)

    x = sub.add_parser("rechazos", help="ver qué se rechazó y por qué")
    x.add_argument("--limite", type=int, default=30)
    x.set_defaults(func=cmd_rechazos)

    t = sub.add_parser("probar", help="probar el parser de sueldos con un texto")
    t.add_argument("texto")
    t.set_defaults(func=cmd_probar)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
