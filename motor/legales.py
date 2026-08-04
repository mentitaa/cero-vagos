"""
Las páginas legales del sitio.

Se generan desde el motor, igual que las ofertas, por dos razones: quedan con
el mismo diseño sin duplicar estilos, y el día que se conecte el dominio propio
todas las direcciones cambian solas.

Son cuatro:
    /como-trabajamos/   la posición del proyecto: qué hacemos y de qué respondemos
    /terminos/          términos y condiciones de uso
    /privacidad/        política de privacidad
    /reclamaciones/     libro de reclamaciones

Ojo: esto es la posición del proyecto redactada con cuidado, no asesoría legal.
Antes de que el sitio tenga tráfico serio conviene que un abogado los revise.
"""
from __future__ import annotations

import html
from datetime import date
from pathlib import Path

from .transparencia import ESTILOS

# Un correo que sí existe. Las páginas legales prometen que se puede pedir
# la baja de un dato o reportar un aviso: si la dirección rebota, esa
# promesa es papel mojado. Cambiar por contacto@cerovagos.com el día que
# se compre el dominio.
CORREO = "cerovagos.alertas@gmail.com"

# Se agregan al sitemap desde sitio.py.
PAGINAS = ("como-trabajamos", "terminos", "privacidad", "reclamaciones")


def _e(t) -> str:
    return html.escape(str(t or ""), quote=True)


def _envoltura(titulo: str, descripcion: str, ruta: str, sitio: str,
               cuerpo: str, indexable: bool = True) -> str:
    url = f"{sitio}/{ruta}/"
    return f"""<!DOCTYPE html>
<html lang="es-PE">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_e(titulo)} | Cero Vagos</title>
<meta name="description" content="{_e(descripcion)}">
<link rel="canonical" href="{_e(url)}">
{'' if indexable else '<meta name="robots" content="noindex">'}
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src 'self'; connect-src 'none'; form-action 'none'; base-uri 'none'; object-src 'none'">
<link rel="icon" href="{_e(sitio)}/assets/icono.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo+Black&family=Space+Grotesk:wght@400;500;700&display=swap" rel="stylesheet">
<style>{ESTILOS}
.doc{{max-width:760px}}
.doc h2{{font-size:19px;margin:34px 0 10px}}
.doc h3{{font-size:15px;margin:22px 0 8px}}
.doc p,.doc li{{font-size:15.5px;line-height:1.6;font-weight:500}}
.doc p{{margin-bottom:12px}}
.doc ul{{margin:0 0 14px 20px}}
.doc li{{margin-bottom:7px}}
.doc .caja{{border:var(--bd);background:var(--blanco);padding:20px 22px;margin:24px 0;
box-shadow:5px 5px 0 var(--negro)}}
.doc .destacado{{background:var(--lima)}}
.doc .fecha{{font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:.04em;opacity:.6}}
.doc a{{font-weight:700}}
</style>
</head>
<body>

<div class="barra-sup"><div class="wrap">
  <a href="{_e(sitio)}/" class="volver">
    <img src="{_e(sitio)}/assets/logo-mono.svg" alt="Cero Vagos">
    <span>← Volver a las ofertas</span>
  </a>
</div></div>

<header class="hero">
  <div class="wrap"><h1>{_e(titulo)}</h1></div>
</header>

<section>
  <div class="wrap doc">
    <p class="fecha">Actualizado el {date.today().strftime('%d/%m/%Y')}</p>
    {cuerpo}
  </div>
</section>

<footer><div class="wrap">
  <b>Cero Vagos</b> ·
  <a href="{_e(sitio)}/como-trabajamos/">Cómo trabajamos</a> ·
  <a href="{_e(sitio)}/terminos/">Términos</a> ·
  <a href="{_e(sitio)}/privacidad/">Privacidad</a> ·
  <a href="{_e(sitio)}/reclamaciones/">Libro de reclamaciones</a>
</div></footer>

</body>
</html>
"""


# --------------------------------------------------------------------------

def como_trabajamos(sitio: str) -> str:
    cuerpo = f"""
    <p>Cero Vagos es un buscador de ofertas de trabajo. No somos una empresa que
    contrata, ni una agencia de empleo, ni el portal donde se publicó el aviso.
    Esta página explica exactamente qué hacemos y de qué respondemos.</p>

    <div class="caja destacado">
      <p style="margin:0"><b>En una línea:</b> encontramos avisos de empleo publicados
      en otros sitios, nos quedamos solo con los que están completos, los ordenamos
      y te mandamos al aviso original para que postules ahí.</p>
    </div>

    <h2>Qué hacemos</h2>
    <ul>
      <li>Revisamos avisos de empleo publicados públicamente en portales peruanos.</li>
      <li>Descartamos los que no dicen cuánto pagan, qué vas a hacer, qué piden o qué te dan.</li>
      <li>Reorganizamos la información: separamos funciones, requisitos y beneficios,
      y extraemos el sueldo para que se vea de una.</li>
      <li>Enlazamos siempre al aviso original, en el sitio donde se publicó.</li>
      <li>Retiramos los avisos vencidos todos los días.</li>
    </ul>

    <h2>Qué NO hacemos</h2>
    <ul>
      <li><b>No publicamos ofertas propias.</b> Todo lo que ves lo publicó una empresa
      en otro sitio.</li>
      <li><b>No recibimos tu CV</b> ni tenemos formulario de postulación. Para postular
      te vas al portal original.</li>
      <li><b>No intermediamos la contratación.</b> No hablamos con las empresas por ti.</li>
      <li><b>No te cobramos nada, nunca.</b> Si alguien te pide dinero diciendo que es
      de Cero Vagos, no lo es.</li>
    </ul>

    <h2>De qué respondemos</h2>
    <p>Respondemos por cómo mostramos la información: que el sueldo que leas sea el que
    dice el aviso, que las funciones sean las que la empresa escribió, y que el enlace
    te lleve a la oferta correcta. Si algo de eso está mal, escríbenos y lo corregimos.</p>

    <p>No respondemos por el contenido del aviso en sí. La veracidad de lo que una
    empresa promete —el sueldo, las condiciones, la existencia misma del puesto— es
    responsabilidad de quien lo publicó y del portal donde lo publicó. Nosotros
    mostramos lo que ese aviso dice y te damos el enlace para que lo verifiques.</p>

    <h2>Cómo tratamos a los portales de origen</h2>
    <p>No competimos con ellos, los ordenamos. Por eso:</p>
    <ul>
      <li>Respetamos el archivo <code>robots.txt</code> de cada sitio. Si no podemos
      leerlo, asumimos que no tenemos permiso y no entramos.</li>
      <li>Nuestro programa se identifica al pedir cada página, con datos de contacto.</li>
      <li>Respetamos el ritmo de peticiones que cada sitio indica.</li>
      <li>No accedemos a nada que esté detrás de un inicio de sesión.</li>
      <li>Cada oferta enlaza al aviso original: el tráfico vuelve a ellos.</li>
    </ul>
    <p>Si administras un portal o una empresa y quieres que dejemos de mostrar tus
    avisos, escríbenos a <a href="mailto:{CORREO}">{CORREO}</a> y los bajamos el mismo día.</p>

    <h2>Cuidado con las estafas</h2>
    <div class="caja">
      <p><b>Ningún trabajo legítimo te pide dinero por adelantado.</b> Ni por el examen
      médico, ni por el uniforme, ni por "reservar la vacante", ni por una capacitación
      previa.</p>
      <p style="margin:0">Tampoco deberías entregar copia de tu DNI, datos bancarios ni
      claves antes de firmar un contrato. Si un aviso que viste acá te lleva a algo así,
      avísanos a <a href="mailto:{CORREO}">{CORREO}</a>.</p>
    </div>
    """
    return _envoltura(
        "Cómo trabajamos",
        "Qué hace Cero Vagos, qué no hace y de qué responde. Cómo tratamos a los "
        "portales de origen y cómo reconocer una estafa laboral.",
        "como-trabajamos", sitio, cuerpo)


def terminos(sitio: str) -> str:
    cuerpo = f"""
    <p>Al usar Cero Vagos aceptas lo siguiente. Está escrito para que se entienda:
    si algo no queda claro, escríbenos.</p>

    <h2>1. Qué es este servicio</h2>
    <p>Cero Vagos es un buscador gratuito de ofertas de trabajo publicadas en otros
    sitios web. Selecciona y organiza avisos públicos, y enlaza a su fuente original.
    No es una agencia de empleo ni intermedia contrataciones.</p>

    <h2>2. El contenido de los avisos no es nuestro</h2>
    <p>Cada oferta fue redactada y publicada por una empresa en un portal de terceros.
    Cero Vagos no verifica la veracidad de lo que un aviso afirma, no garantiza que la
    vacante exista o siga abierta, ni participa en el proceso de selección.</p>
    <p>La responsabilidad por el contenido de un aviso corresponde a quien lo publicó y
    al portal que lo aloja. Mostramos la información tal como aparece y enlazamos a la
    fuente para que puedas verificarla.</p>

    <h2>3. Uso del servicio</h2>
    <ul>
      <li>El uso es gratuito y no requiere registro.</li>
      <li>Puedes consultar, compartir y enlazar nuestras páginas libremente.</li>
      <li>No está permitido usar medios automatizados para extraer masivamente el
      contenido del sitio, ni suplantar a Cero Vagos.</li>
    </ul>

    <h2>4. Disponibilidad</h2>
    <p>El servicio se ofrece tal como está. Puede haber interrupciones, errores de
    lectura de un aviso o demoras en retirar una oferta vencida. Hacemos lo posible por
    evitarlo y agradecemos que nos avises cuando ocurra.</p>

    <h2>5. Enlaces a otros sitios</h2>
    <p>Al postular sales de Cero Vagos hacia el portal de origen. Lo que ocurra allí se
    rige por los términos y la política de privacidad de ese sitio, no por los nuestros.</p>

    <h2>6. Correcciones y retiros</h2>
    <p>Si eres una empresa, un portal o una persona y quieres que corrijamos o retiremos
    una publicación, escríbenos a <a href="mailto:{CORREO}">{CORREO}</a>. Atendemos los
    pedidos el mismo día.</p>

    <h2>7. Ley aplicable</h2>
    <p>Estos términos se rigen por las leyes de la República del Perú.</p>

    <h2>8. Cambios</h2>
    <p>Si cambiamos estos términos, actualizaremos la fecha del encabezado. Los cambios
    rigen desde su publicación.</p>
    """
    return _envoltura(
        "Términos y condiciones",
        "Condiciones de uso de Cero Vagos, buscador de ofertas de trabajo completas "
        "en el Perú.",
        "terminos", sitio, cuerpo)


def privacidad(sitio: str) -> str:
    cuerpo = f"""
    <div class="caja destacado">
      <p style="margin:0"><b>La versión corta:</b> hoy Cero Vagos no te pide ningún dato
      personal, no usa cookies y no tiene sistemas de análisis de visitas. Puedes usar
      todo el sitio sin dejar rastro tuyo con nosotros.</p>
    </div>

    <h2>Qué datos recogemos</h2>
    <p>Ninguno. No hay registro de usuarios, no hay formularios activos, no instalamos
    cookies ni herramientas de medición.</p>
    <p>Nuestro sitio está alojado en GitHub Pages, que como cualquier servidor web puede
    registrar datos técnicos de la conexión (dirección IP, navegador) por motivos de
    seguridad y funcionamiento. Ese registro es de GitHub y se rige por su propia
    política de privacidad; nosotros no lo consultamos ni lo conservamos.</p>

    <h2>Cuando activemos las alertas</h2>
    <p>Tenemos previsto ofrecer alertas de nuevas ofertas. Ese servicio sí requerirá
    datos tuyos, y cuando exista funcionará así:</p>
    <ul>
      <li>Solo pediremos lo mínimo: un medio de contacto y el rubro que te interesa.</li>
      <li>Te diremos con claridad para qué los usamos: enviarte ofertas. Nada más.</li>
      <li>No los venderemos ni los cederemos a terceros.</li>
      <li>Podrás darte de baja en cualquier momento, con un solo clic.</li>
      <li>Cumpliremos la Ley 29733 de Protección de Datos Personales y su reglamento,
      incluida la inscripción del banco de datos cuando corresponda.</li>
    </ul>
    <p>Hasta entonces, esta sección es una declaración de intenciones, no una práctica
    en curso: hoy no guardamos nada.</p>

    <h2>Datos de las ofertas</h2>
    <p>La información que mostramos —empresa, puesto, sueldo, requisitos— proviene de
    avisos publicados públicamente por empresas en portales de empleo. No es información
    personal de candidatos.</p>

    <h2>Tus derechos</h2>
    <p>Cuando tengamos datos tuyos, podrás pedir acceder a ellos, corregirlos, cancelarlos
    u oponerte a su uso, escribiendo a <a href="mailto:{CORREO}">{CORREO}</a>.</p>

    <h2>Cambios</h2>
    <p>Si esto cambia —por ejemplo, el día que activemos las alertas— actualizaremos esta
    página y su fecha antes de recoger cualquier dato.</p>
    """
    return _envoltura(
        "Política de privacidad",
        "Cero Vagos no recoge datos personales, no usa cookies ni herramientas de "
        "medición. Qué pasará cuando activemos las alertas.",
        "privacidad", sitio, cuerpo)


def reclamaciones(sitio: str) -> str:
    asunto = "Reclamo%20o%20queja%20-%20Cero%20Vagos"
    cuerpo = f"""
    <p>Conforme al Código de Protección y Defensa del Consumidor (Ley 29571), ponemos a
    tu disposición este canal para presentar un reclamo o una queja.</p>

    <div class="caja destacado">
      <p style="margin:0"><b>Cómo funciona hoy.</b> Todavía no tenemos formulario
      automático: los reclamos se reciben por correo. Escribimos acuse de recibo dentro
      de las 24 horas y respondemos el fondo en un plazo máximo de 15 días hábiles.</p>
    </div>

    <h2>Qué debe incluir tu reclamo</h2>
    <ul>
      <li>Tus nombres y apellidos, documento de identidad y un medio para responderte
      (correo o teléfono).</li>
      <li>Si es un <b>reclamo</b> (disconformidad con el servicio) o una <b>queja</b>
      (malestar por la atención).</li>
      <li>El detalle de lo ocurrido, con la dirección de la página o la oferta
      involucrada si aplica.</li>
      <li>Lo que pides que hagamos.</li>
    </ul>

    <p style="margin-top:22px">
      <a class="btn" href="mailto:{CORREO}?subject={asunto}">Enviar mi reclamo por correo →</a>
    </p>

    <h2>Un aviso importante</h2>
    <p>Cero Vagos es un buscador: no somos el empleador ni el portal que publicó el
    aviso. Si tu reclamo es contra una empresa que ofreció un trabajo, o contra el portal
    donde se publicó, debes dirigirlo a ellos — nosotros podemos indicarte cuál es la
    fuente original.</p>
    <p>Sí atendemos aquí todo lo que dependa de nosotros: un sueldo mal leído, una oferta
    vencida que sigue publicada, un enlace que no corresponde, o el pedido de retirar una
    publicación.</p>

    <h2>Si no quedas conforme</h2>
    <p>Puedes acudir a INDECOPI a través de sus canales de atención al consumidor.</p>
    """
    return _envoltura(
        "Libro de reclamaciones",
        "Canal de reclamos y quejas de Cero Vagos, conforme al Código de Protección y "
        "Defensa del Consumidor.",
        "reclamaciones", sitio, cuerpo, indexable=False)


# --------------------------------------------------------------------------

def generar(sitio: str, raiz: Path) -> list[str]:
    """Escribe las cuatro páginas y devuelve sus rutas."""
    contenidos = {
        "como-trabajamos": como_trabajamos(sitio),
        "terminos": terminos(sitio),
        "privacidad": privacidad(sitio),
        "reclamaciones": reclamaciones(sitio),
    }
    for ruta, html_texto in contenidos.items():
        destino = raiz / ruta
        destino.mkdir(parents=True, exist_ok=True)
        (destino / "index.html").write_text(html_texto, encoding="utf-8")
    return list(contenidos)
