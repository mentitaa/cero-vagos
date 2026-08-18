"""
La página /apoyanos/.

Cero Vagos no tiene publicidad y no le cobra a quien busca trabajo. Eso no es
una postura estética: los avisos de un buscador de empleo se pagan mostrando
más ofertas, y este sitio existe justamente para mostrar menos. Un portal que
gana por aviso mostrado tiene un incentivo a aflojar el filtro; nosotros no
podemos tener ese incentivo.

Sostenerlo tiene un costo, y esta página lo dice y deja los canales para quien
quiera ayudar.

TRES REGLAS QUE NO SE TOCAN
---------------------------
0. **Nada de cifras ni de detalles de quién paga** (decisión de Mentita,
   18/8/2026). La página dice que hay un costo mensual y ahí se queda: no
   enumera los servicios ni cuánto sale cada uno, y no cuenta que el proyecto
   lo sostiene una sola persona. Dos razones. Una, pedir apoyo desde la
   fragilidad —"esto se apaga si nadie ayuda"— presiona a quien lee, y este
   sitio no presiona a nadie. Dos, un desglose de gastos invita a discutir el
   gasto en vez de la idea, y la idea es lo que se está apoyando.
1. **Donar no compra nada.** Ni un puesto en el listado, ni una excepción al
   filtro, ni que un aviso salga más arriba. Está escrito en la página, en
   grande, porque es lo único que hace que pedir plata sea compatible con la
   promesa del sitio. El día que una donación cambie lo que se publica, Cero
   Vagos deja de valer lo que dice valer.
2. **Un canal sin configurar no se dibuja.** Nada de cuadros vacíos ni de
   direcciones de ejemplo. Una dirección de cripto de mentira en una página de
   donaciones es plata de alguien perdida para siempre.

CÓMO SE CONFIGURA
-----------------
Se editan las tres entradas de `CANALES`, aquí abajo. Lo que quede en blanco
no aparece en la web.
"""
from __future__ import annotations

import html
from pathlib import Path

from .legales import CORREO, envoltura

RUTA = "apoyanos"


# --------------------------------------------------------------------------
# Los canales. Esto es lo único que hay que editar.
# --------------------------------------------------------------------------
#
# Para Dale y Plin: exportá el QR desde la app (Cobrar / Mi QR), guardalo en
# `assets/` y poné aquí el nombre del archivo. El "titular" es el nombre que
# le va a aparecer a quien escanea, y conviene que esté escrito acá para que
# la persona confirme que le está enviando a quien cree.
#
# Para USDC hay UNA cosa que no se puede equivocar: **la red**. USDC existe
# sobre varias redes distintas y no se hablan entre ellas. Si alguien manda
# por una red que la billetera no tiene, esa plata no se recupera. Por eso la
# red se muestra siempre, en grande, y sin red no se publica la dirección.

# OJO CON LAS MAYÚSCULAS DEL NOMBRE DEL ARCHIVO. En una Mac da lo mismo
# escribir "qr-plin.png" que "QR-PLIN.PNG": encuentra el archivo igual. En los
# servidores donde vive el sitio NO da lo mismo, y una letra en mayúscula de
# más deja el QR roto en la web mientras en la laptop se ve perfecto. Por eso
# hay un test que comprueba que estos archivos existan tal cual están escritos.

CANALES = {
    "dale": {
        "titular": "",          # ej: "Nombre Apellido"
        "qr": "QR-DALE.png",    # archivo dentro de assets/
    },
    "plin": {
        "titular": "",
        "qr": "QR-PLIN.PNG",
    },
    "usdc": {
        "direccion": "",        # la dirección completa de la billetera
        "red": "",              # ej: "Solana", "Base", "Polygon". OBLIGATORIA.
    },
}


def _e(t) -> str:
    return html.escape(str(t or ""), quote=True)


def _activo(canal: dict, *claves: str) -> bool:
    """Un canal solo se dibuja si tiene TODO lo que necesita para funcionar."""
    return all(str(canal.get(c) or "").strip() for c in claves)


def hay_algun_canal() -> bool:
    return (_activo(CANALES["dale"], "qr")
            or _activo(CANALES["plin"], "qr")
            or _activo(CANALES["usdc"], "direccion", "red"))


ESTILOS_PROPIOS = """
.canales{display:flex;flex-wrap:wrap;gap:18px;margin:20px 0}
.canal{border:var(--bd);background:var(--blanco);padding:18px 20px;
box-shadow:5px 5px 0 var(--tinta);text-align:center;flex:1 1 220px}
.canal.ancho{flex:1 1 100%;text-align:left}
.canal h3{margin:0 0 12px;font-size:16px}
.canal .qr{display:block;margin:0 auto;width:100%;max-width:220px;height:auto}
.canal .titular{font-size:13px;margin:10px 0 0;opacity:.75}
.canal .red{font-size:14px;margin:0 0 8px}
.canal .direccion{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
font-size:13px;word-break:break-all;background:var(--fondo);
border:var(--bd);padding:10px 12px;margin:0 0 10px}
.canal .aviso-red{font-size:13px;margin:0;opacity:.8}
"""


# --------------------------------------------------------------------------
# Los bloques
# --------------------------------------------------------------------------

def _billetera(nombre: str, canal: dict, sitio: str) -> str:
    if not _activo(canal, "qr"):
        return ""
    titular = canal.get("titular", "")
    linea = (f'<p class="titular">A nombre de <b>{_e(titular)}</b></p>'
             if titular else "")
    return f"""
      <div class="canal">
        <h3>{_e(nombre)}</h3>
        <img class="qr" src="{_e(sitio)}/assets/{_e(canal['qr'])}"
             alt="Código QR de {_e(nombre)} para apoyar a Cero Vagos"
             width="220" height="220">
        {linea}
      </div>"""


def _cripto(canal: dict) -> str:
    if not _activo(canal, "direccion", "red"):
        return ""
    return f"""
      <div class="canal ancho">
        <h3>USDC</h3>
        <p class="red">Red: <b>{_e(canal['red'])}</b></p>
        <p class="direccion">{_e(canal['direccion'])}</p>
        <p class="aviso-red">Envía <b>solo USDC</b> y <b>solo por la red
        {_e(canal['red'])}</b>. Si lo mandas por otra red, esa plata no se
        puede recuperar — ni por ti ni por nosotros.</p>
      </div>"""


def pagina(sitio: str) -> str:
    canales = "".join([
        _billetera("Dale", CANALES["dale"], sitio),
        _billetera("Plin", CANALES["plin"], sitio),
        _cripto(CANALES["usdc"]),
    ])

    if canales:
        bloque_canales = f"""
    <h2>Dónde</h2>
    <div class="canales">{canales}</div>
    <p style="font-size:14px;opacity:.75">Aporta lo que puedas y solo si te
    sobra. Si estás buscando trabajo, no dones: usa el sitio, que para eso
    está. Ya nos ayudas si lo compartes con alguien que lo necesite.</p>"""
    else:
        bloque_canales = """
    <div class="caja">
      <p style="margin:0">Los canales para aportar todavía no están publicados.
      Si quieres apoyar el proyecto, escríbenos a
      <a href="mailto:%s">%s</a>.</p>
    </div>""" % (CORREO, CORREO)

    cuerpo = f"""
    <p>Cero Vagos es un buscador de empleo con una sola regla: <b>si el aviso no
    dice cuánto paga, no entra</b>. Ni con la empresa más grande del país, ni
    con la oferta más tentadora. El motor no busca trabajos, los rechaza.</p>

    <p>De cada 100 avisos que revisamos, <b>77 no dicen cuánto pagan</b>. Esos
    77 son los que en cualquier otro portal te hacen leer el aviso completo,
    armar tu CV y postular para recién enterarte en la entrevista.</p>

    <h2>Por qué no hay publicidad</h2>

    <div class="caja destacado">
      <p style="margin:0">Un portal que gana por aviso mostrado tiene un motivo
      para mostrar más avisos. Nosotros existimos para mostrar <b>menos</b>. Los
      dos incentivos no caben en la misma web, así que acá no hay anuncios y a
      ti no te cobramos nada, nunca.</p>
    </div>

    <p>Pero mantenerlo en pie tiene un costo fijo todos los meses, y no hay
    publicidad ni cobro que lo cubra. Por eso existe esta página.</p>

    <p>Si el proyecto te sirvió —o te parece que el Perú merece avisos de
    trabajo que digan cuánto pagan— puedes ayudar a que siga.</p>

    <h2>Qué NO compra tu aporte</h2>

    <div class="caja">
      <p><b>Nada.</b> Y esto es en serio, porque es lo único que hace que pedir
      apoyo sea compatible con lo que este sitio promete.</p>
      <ul style="margin-bottom:0">
        <li>No compra que una oferta salga publicada.</li>
        <li>No compra que una oferta salga más arriba.</li>
        <li>No compra una excepción al filtro. La regla del sueldo no tiene
        forma de apagarse: no existe el botón.</li>
        <li>No compra que se retire un aviso ni que se retire una empresa del
        <a href="{_e(sitio)}/transparencia/">ranking de transparencia</a>.</li>
      </ul>
    </div>

    <p>Si aportas y después nos pides cualquiera de esas cosas, te devolvemos
    el aporte y no la hacemos. Preferimos quedarnos sin la plata que sin el
    argumento.</p>
    {bloque_canales}

    <h2>Si prefieres ayudar sin poner plata</h2>
    <ul>
      <li><b>Compártelo.</b> Alguien que conoces está buscando trabajo ahora
      mismo.</li>
      <li><b>Repórtanos un aviso mal leído.</b> Si ves un sueldo que no calza
      con lo que dice el aviso original, escríbenos: varios de los arreglos más
      importantes del motor salieron de gente mirando y avisando.</li>
      <li><b>Si tienes una empresa</b>, publica tus avisos con el sueldo. Es
      gratis, entras al sitio si el aviso está completo, y te ahorra
      entrevistas con gente que se va a ir al enterarse del monto.</li>
    </ul>

    <p style="font-size:14px;opacity:.75">Los aportes son voluntarios y no dan
    derecho a ningún servicio, producto ni contraprestación. Para cualquier
    consulta: <a href="mailto:{CORREO}">{CORREO}</a>.</p>
    """

    return envoltura(
        "Apóyanos",
        "Cero Vagos no tiene publicidad y no le cobra a quien busca trabajo. "
        "Si quieres que siga, acá puedes aportar. Tu aporte no compra un puesto "
        "en el listado ni una excepción al filtro.",
        RUTA, sitio, cuerpo, estilos_extra=ESTILOS_PROPIOS)




def generar(sitio: str, raiz: Path) -> str:
    destino = raiz / RUTA
    destino.mkdir(parents=True, exist_ok=True)
    (destino / "index.html").write_text(pagina(sitio), encoding="utf-8")
    return RUTA
