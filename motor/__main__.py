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

# Cuántas ofertas necesita un departamento para merecer su propia página
# ("Trabajos en Arequipa con sueldo"). Por debajo de esto la página nace casi
# vacía, y una página casi vacía le dice a Google que el sitio es de baja
# calidad — hace más daño que bien. Es un piso prudente, no una ley: si un
# departamento se queda en 4 durante semanas, el problema es de fuentes.
MINIMO_PARA_PAGINA = 5


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

    # Correr una sola fuente. Existe porque Bumeran y Laborum compartían un
    # mismo paso de la corrida automática y siempre se recorrían en ese orden:
    # cuando el reloj se acababa, el que se quedaba a medias era SIEMPRE
    # Laborum. Por eso llevaba 327 avisos revisados contra 779 de Bumeran, y
    # por eso el día que el paso se cortó, Laborum no llegó a correr.
    # Separarlas en dos pasos con su propio reloj hace que una no se coma el
    # tiempo de la otra.
    if getattr(args, "fuente", None):
        pedida = args.fuente.strip().lower()
        elegidas = [f for f in fuentes if pedida in f.nombre.lower()]
        if not elegidas:
            disponibles = ", ".join(f.nombre for f in fuentes)
            print(f"No hay ninguna fuente que se llame «{args.fuente}».")
            print(f"Las de esta corrida son: {disponibles}")
            sys.exit(1)
        fuentes = elegidas
        print(f"Solo esta corrida: {', '.join(f.nombre for f in fuentes)}\n")

    # Corrida diaria: solo mira lo publicado en los últimos días. Mucho más
    # rápido, porque lo viejo ya está en la base.
    if args.dias:
        for f in fuentes:
            if hasattr(f, "dias_publicado"):
                f.dias_publicado = args.dias
        print(f"Buscando solo avisos publicados en los últimos {args.dias} días.\n")

    # Reparar: releer exactamente lo que está publicado.
    #
    # Cada fuente descubre direcciones en su sitemap y se detiene al llegar a
    # su cupo, así que que un aviso guardado caiga dentro de ese corte es
    # cuestión de suerte. El 7/8/2026 se corrió tres veces con `rehacer` para
    # corregir tres avisos y los tres quedaron fuera las tres veces — no por un
    # fallo, sino porque el cupo se llenó antes de llegar a ellos.
    #
    # Pidiéndole las direcciones a la base, deja de ser aleatorio.
    if getattr(args, "reparar", False):
        guardadas = Almacen().urls_publicadas()
        total = 0
        for f in fuentes:
            f.urls_fijas = guardadas.get(f.nombre, [])
            total += len(f.urls_fijas)
        if not total:
            print("No hay nada publicado que reparar.")
            sys.exit(0)
        args.rehacer = True          # reparar implica no saltarse nada
        # El cupo de la corrida no puede dejar avisos fuera: reparar a medias
        # es justo el problema que esto viene a resolver.
        args.limite = max(args.limite, max(len(u) for u in guardadas.values()))

        # Y la ventana de días tampoco. Reparar con `--dias 3` descartaba por
        # viejo justo lo que se estaba reparando: el 7/8/2026 se releyeron 49
        # avisos de Bumeran y 29 se tiraron como "vencidos" antes de guardarse.
        # Un aviso publicado ya pasó el filtro de antigüedad el día que entró;
        # de sacarlo de la web cuando toque se encarga `depurar`, no esto.
        for f in fuentes:
            if hasattr(f, "dias_publicado"):
                from .score import MAX_DIAS_ANTIGUEDAD
                f.dias_publicado = MAX_DIAS_ANTIGUEDAD
        args.dias = 0
        print(f"REPARAR: se vuelven a leer las {total} ofertas publicadas, "
              f"sin buscar direcciones nuevas.")
        for f in fuentes:
            if f.urls_fijas:
                print(f"  · {f.nombre}: {len(f.urls_fijas)}")
        print()

    # Se dice EN VOZ ALTA si esta corrida repara o solo agrega.
    #
    # Hizo falta porque reparar un dato mal leído necesita DOS cosas a la vez y
    # es fácil poner solo una: `rehacer` para no saltarse lo ya visto, y
    # `--dias 0` para que la fuente vuelva a descubrir avisos viejos. El
    # 7/8/2026 se corrió tres veces sin las dos, y desde afuera la corrida se
    # veía perfecta: agregaba ofertas nuevas mientras las viejas seguían con el
    # dato equivocado. Nada fallaba; simplemente no se estaba reparando.
    if args.rehacer:
        if args.dias:
            print(f"REHACER activado, pero con ventana de {args.dias} días: se "
                  f"volverán a leer solo los avisos publicados en ese plazo.\n"
                  f"Para reparar avisos más viejos hace falta además --dias 0.\n")
        else:
            print("REHACER activado: se vuelven a leer TODOS los avisos, "
                  "incluidos los que ya estaban guardados.\n")
    else:
        print("Corrida normal: los avisos ya vistos se saltan y conservan lo "
              "que se les leyó el día que entraron.\n"
              "Para reparar un dato mal leído: --rehacer y --dias 0.\n")

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


def cmd_publicar(args) -> None:
    """Genera una página por oferta, el sitemap y el robots.txt."""
    from .sitio import generar, sitio_publicado

    destino = (args.sitio or sitio_publicado()).rstrip("/")
    info = generar(sitio=destino)

    print(f"Dirección del sitio: {info['sitio']}")
    print(f"{info['paginas']} páginas de oferta generadas en oferta/")
    if info.get("retiradas"):
        print(f"{info['retiradas']} páginas retiradas (ofertas que ya cerraron)")
    print("sitemap.xml y robots.txt actualizados")
    print("\nFalta un paso manual, una sola vez: registrar el sitio en")
    print("Google Search Console y enviar el sitemap.")


def cmd_stats(_args) -> None:
    s = Almacen().estadisticas()
    print(f"Procesadas en total   {s['total_procesadas']}")
    print(f"Aprobadas vigentes    {s['aprobadas_vigentes']}")
    print(f"Tasa de aprobación    {s['tasa_aprobacion']}%")
    if s["por_fuente"]:
        print("\nPor fuente:")
        for fuente, n in s["por_fuente"].items():
            print(f"  {n:>5}  {fuente}")

    # El reparto por departamento decide cuándo hacer las páginas por lugar.
    # Con menos de MINIMO_PARA_PAGINA ofertas la página nacería casi vacía, y
    # eso le dice a Google que el sitio es de baja calidad: es peor que no
    # tenerla. Por eso se marca cuáles ya aguantan y cuáles no.
    if s.get("por_departamento"):
        listos = [(d, n) for d, n in s["por_departamento"].items()
                  if n >= MINIMO_PARA_PAGINA and d != "(sin ubicación)"]
        print(f"\nPor departamento  (✓ = ya aguanta página propia, "
              f"{MINIMO_PARA_PAGINA} ofertas o más):")
        for depa, n in s["por_departamento"].items():
            marca = "✓" if (depa, n) in listos else " "
            print(f"  {marca} {n:>4}  {depa}")
        print(f"\n  {len(listos)} departamento(s) con página posible hoy.")


def cmd_reevaluar(args) -> None:
    """
    Vuelve a puntuar lo guardado con las reglas de hoy.

    Se corre a mano después de cambiar el filtro. Sin esto, un cambio de regla
    tarda semanas en notarse: el motor no vuelve a mirar un aviso rechazado
    hasta pasados 30 días, así que conservaría el veredicto viejo.
    """
    al = Almacen()
    antes = al.estadisticas()["aprobadas_vigentes"]
    r = al.reevaluar()
    despues = al.estadisticas()["aprobadas_vigentes"]

    if not r["entraron"] and not r["salieron"]:
        print("Nada cambió: las reglas de hoy dan el mismo veredicto que antes.")
        return

    print(f"{r['entraron']} avisos pasaron a publicarse")
    print(f"{r['salieron']} avisos dejaron de publicarse")
    print(f"\nPublicadas: {antes} → {despues}")
    print("\nFalta regenerar el sitio:  python3 -m motor publicar")


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
    r.add_argument("--fuente", help="correr solo esta fuente, por nombre (ej: Laborum)")
    r.add_argument("--dias", type=int, default=0,
                   help="solo avisos publicados en los últimos N días (2 para la corrida diaria)")
    r.add_argument("--rehacer", action="store_true",
                   help="volver a revisar todo, incluso lo ya visto hoy")
    r.add_argument("--reparar", action="store_true",
                   help="releer las ofertas YA PUBLICADAS para corregir un dato "
                        "mal leído, en vez de buscar avisos nuevos")
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

    pub = sub.add_parser("publicar", help="generar una página por oferta + sitemap")
    pub.add_argument("--sitio", default="",
                     help="dirección del sitio (si se omite, se lee del CNAME)")
    pub.set_defaults(func=cmd_publicar)

    s = sub.add_parser("stats", help="estado de la base")
    s.set_defaults(func=cmd_stats)

    rv = sub.add_parser("reevaluar",
                        help="volver a puntuar lo guardado con las reglas de hoy")
    rv.set_defaults(func=cmd_reevaluar)

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
