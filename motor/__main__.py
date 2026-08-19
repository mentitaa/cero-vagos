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


def cmd_sondear(args) -> None:
    """
    Cuenta lo que una bolsa tiene DENTRO antes de escribirle un lector.

    `conectar` contesta si nos dejan entrar y con qué está hecha. Eso nunca
    alcanzó: BuscoTrabajo dejaba entrar y tenía 4 avisos, y las bolsas
    universitarias tenían 8,287 vacantes y ni un solo sueldo. Este comando
    contesta las otras dos preguntas —cuántos hay y cuántos dicen cuánto
    pagan— y las contesta con el filtro de verdad.
    """
    from .sondeo import informe, sondear
    print(informe(sondear(args.url, args.limite, args.nombre)))


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

    # Los portales grandes son aplicaciones que se arman solas en el navegador:
    # por HTTP simple devuelven "You need to enable JavaScript" y este comando
    # no puede leer nada. Con --navegador se abre Chromium y se lee lo que ve
    # una persona. Es más lento y por eso no es lo normal, pero sin esta opción
    # `probar-url` era inútil justo para los portales que hay que decidir.
    if getattr(args, "navegador", False):
        from .fuentes.render import HAY_PLAYWRIGHT, Navegador
        if not HAY_PLAYWRIGHT:
            print("Falta el navegador. Instálalo con:\n"
                  "  pip3 install playwright && python3 -m playwright install chromium")
            return
        with Navegador() as nav:
            html = nav.html(args.url)
    else:
        resp = requests.get(args.url, headers={"User-Agent": USER_AGENT,
                                               "Accept-Language": "es-PE,es;q=0.9"},
                            timeout=25)
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
            print("La página llega vacía: se arma sola en el navegador.")
            print("Probá otra vez agregando  --navegador  al final.")
        elif not getattr(args, "navegador", False):
            print("La página sí llegó, pero no trae los datos del aviso en el "
                  "formato que pide Google (JSON-LD).")
        else:
            # Con navegador la página se vio entera. Si aun así no hay datos
            # estructurados, no los publica y punto: habría que leerla a mano.
            print("Ni con navegador trae los datos del aviso en el formato que "
                  "pide Google (JSON-LD).")
            print("Esa bolsa necesitaría un lector escrito a medida.")
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
    # Cuando un bloque sale vacío hay dos explicaciones y son opuestas: o el
    # aviso no lo trae, o el motor no supo leerlo. Desde el resultado no se
    # distinguen, y confundirlas manda a arreglar lo que no está roto — con
    # Trabajos Diarios los doce avisos salieron en 0/0/0, un patrón demasiado
    # parejo para venir de los avisos.
    #
    # Así que cuando falta algo, se muestra lo que el motor SÍ leyó. Si el
    # texto está y aun así no se separó en bloques, el problema es de acá.
    if not (o.funciones and o.requisitos and o.beneficios):
        from .normalizar import html_a_lineas
        lineas = html_a_lineas(cruda.cuerpo())
        print(f"\nLo que el motor alcanzó a leer del aviso ({len(lineas)} líneas)")
        if not lineas:
            print("  (nada: el cuerpo del aviso llegó vacío)")
        for linea in lineas[:18]:
            print(f"  | {linea[:100]}")
        if len(lineas) > 18:
            print(f"  | … y {len(lineas) - 18} líneas más")

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
    if not args.demo and not fuentes:
        # No es lo mismo "no hay ninguna fuente" que "las fuentes no arrancan",
        # y decir lo segundo cuando pasa lo primero manda a instalar cosas que
        # ya están. Pasó al vaciarse la lista de empresas el 13/8/2026, cuando
        # Falabella y Cencosud se descartaron por no publicar sueldos.
        print("Esa lista no tiene ninguna fuente configurada.")
        print("No es un error: las bolsas de empresa quedaron vacías tras "
              "descartar\nFalabella y Cencosud. El porqué está en Notion.")
        sys.exit(1)
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

    # Los títulos que no dicen qué es el trabajo. No se rechazan: se miden.
    # Ver `Almacen.titulos_vagos` para por qué el reparto Estado/privado es lo
    # que importa aquí.
    vagos = Almacen().titulos_vagos()
    if vagos:
        del_estado = [v for v in vagos if v["del_estado"]]
        privados = [v for v in vagos if not v["del_estado"]]
        print(f"\nTítulos que no dicen qué es el trabajo:  {len(vagos)}")
        print(f"  {len(del_estado):>4}  del Estado   (cargo normado, no esconden nada)")
        print(f"  {len(privados):>4}  privados     (aquí sí fue una elección)")
        if privados:
            print("\n  Los privados, uno por uno:")
            for v in privados[:15]:
                print(f"    · {v['puesto']} — {v['empresa']}")
            if len(privados) > 15:
                print(f"    · … y {len(privados) - 15} más")


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
    u.add_argument("--navegador", action="store_true",
                   help="abrir la página en Chromium (para portales que se "
                        "arman solos, como Falabella o Bumeran)")
    u.set_defaults(func=cmd_probar_url)

    c = sub.add_parser("conectar", help="ver cómo leer la bolsa de trabajo de una empresa")
    c.add_argument("url", help="URL de la página 'trabaja con nosotros'")
    c.set_defaults(func=cmd_conectar)

    so = sub.add_parser("sondear",
                        help="contar cuántos avisos tiene una bolsa y cuántos dicen el sueldo")
    so.add_argument("url", help="URL del LISTADO de ofertas (no la portada del "
                                "portal: ahí suele no haber avisos)")
    so.add_argument("--limite", type=int, default=25,
                    help="cuántos avisos leer para la muestra (por defecto 25)")
    so.add_argument("--nombre", default="", help="cómo se llama la empresa")
    so.set_defaults(func=cmd_sondear)

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
