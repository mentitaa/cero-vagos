# Contexto del proyecto

Este archivo se lee al empezar cualquier conversación sobre esta carpeta. Es el
puente entre un chat y el siguiente: lo que hay que saber para no volver a
explicarlo, y lo que no se debe romper por no haber preguntado.

Si algo de aquí queda desactualizado, actualízalo. Un contexto viejo es peor
que ninguno.

---

## Qué es Cero Vagos

Buscador de empleo peruano que **solo publica avisos completos**: sueldo en
soles, funciones, requisitos y beneficios. Si falta uno, no entra.

El motor no busca empleos, los rechaza. Esa es la única propuesta de valor y
todo lo demás está subordinado a ella.

Dueña del proyecto: **Mentita**. Repositorio de GitHub bajo el usuario
`mentitaa`. El sitio se publica con GitHub Pages.

**El sitio en vivo: https://cerovagos.com/**

Conectado el 4 de agosto de 2026: dominio en Squarespace, correo
`info@cerovagos.com` con Google Workspace, HTTPS forzado.
`mentitaa.github.io/cero-vagos/` redirige aquí (`DOMINIO.md`).

## Cómo hablarle a Mentita

- **En español, y sin jerga.** No es programadora. "Parser", "pipeline",
  "regex" y "SPA" no se usan sin explicarlos. Cuando pide algo para una reunión
  o un inversionista, el nivel es cero técnico.
- **Directo y corto.** Prefiere respuestas concisas, sin preámbulo ni relleno.
- **Explicar el porqué, no solo el qué.** Las decisiones del proyecto tienen
  razones y ella las quiere entender para poder defenderlas frente a otros.
- **Los comandos van completos y copiables**, con el paso previo si hace falta
  (`chmod +x`, `pip install`).

## Dónde vive cada cosa

| | |
|---|---|
| `README.md` | Manual completo: comandos, filtro, fuentes. La referencia larga. |
| `CLAUDE.md` | Este archivo. Contexto y reglas. |
| `DESPLIEGUE.md` | Poner el motor en piloto automático con GitHub Actions. |
| `DOMINIO.md` | Cómo se conectó el dominio y qué revisar si vuelve a cambiar. |
| `ALERTAS.md` | Las alertas: cómo están conectadas y cómo se mandan. |
| `SEGURIDAD.md` | Auditoría de seguridad: qué se revisó y qué queda abierto. |
| `EMPRESAS.md` | Estrategia de bolsas de trabajo de empresas. |
| `PRIMERA-CORRIDA-CAS.md` | Los cuatro comandos para estrenar Convocatorias CAS. Se borra cuando ya corrió bien. |
| `PROPUESTA-UNIVERSIDADES.md` | Correos listos para las bolsas universitarias. |
| Bitácora en Notion | Historia del proyecto, ideas pendientes, errores que costaron caro, glosario. Ahí va lo narrativo; aquí va lo operativo. |

Código: `motor/` (recolección, filtro, score, publicación), `datos/` (SQLite,
se genera solo), `pruebas/` (los tests), `index.html` (el sitio, un solo
archivo), `oferta/` (una página por oferta, generada), `ir/` (una página de
salida por oferta, generada).

Las visitas se miden con **Cloudflare Web Analytics**: sin cookies, así que no
hace falta cartel de consentimiento y la política de privacidad sigue siendo
cierta. El token vive en `ANALITICA_TOKEN` (`motor/sitio.py`) y también, a
mano, en `index.html`; un test vigila que digan lo mismo.

El botón de postular no va derecho al portal: pasa un segundo por `ir/<slug>/`,
que redirige sola. Ese rodeo existe para **contar cuántos clics recibe cada
aviso**, que es el número que le va a interesar a una empresa. El segundo de
espera no es un descuido: sin él, el medidor no alcanza a mandar el dato.

**El score ya no se muestra en la web** (7/8/2026). Sigue decidiendo qué se
publica y en qué orden, pero dejó de salir en la tarjeta y en la ficha. Salió
de un focus group improvisado: varias personas lo leyeron como una nota al
TRABAJO, veían S/ 4.000 con 89 al lado de S/ 500 con 98 y no entendían nada.
Y el número nunca pudo servirles de nada, porque **todo lo que se publica ya
pasó el filtro**: su único efecto posible era invitar a comparar en una
dimensión que significa otra cosa. En su lugar van las cuatro cosas que el
aviso SÍ trae —sueldo, funciones, requisitos, beneficios— marcadas una por una
(`loQueTiene` en `index.html`). Es el mismo score dicho en lo que significa, y
no revela la fórmula. Las convocatorias del Estado sin funciones muestran tres
marcas en vez de cuatro, y **está bien**: es honesto y la ficha explica dónde
buscarlas. Lo vigila `pruebas/test_tarjeta.py`.

De paso se quitó la inicial de la empresa del recuadro izquierdo. Nadie sabía
qué era, y no identificaba nada: el color salía de la POSICIÓN de la tarjeta,
así que la misma empresa cambiaba de color al filtrar o al dar "Ver más".

El logo vive en `assets/`, en tres versiones que existen por una razón:
`logo-oscuro.svg` (rojo + negro) para fondos claros, `logo-claro.svg`
(rojo + blanco) para fondos oscuros, y `logo-mono.svg` (todo blanco) para la
franja roja de las páginas internas, donde un logo con rojo desaparecería.
Más `icono.svg`, el cuadrado de la pestaña del navegador, y `compartir.png`
(1200×630), la imagen que sale al pegar el enlace en WhatsApp o Facebook. Esa
última no se edita a mano: la arma `assets/generar-og.py` a partir del logo.
Si el logo cambia, se reemplazan los cuatro SVG y se vuelve a correr ese
script.

Las etiquetas que leen WhatsApp y Facebook (`og:image`, `og:title`…) las
escribe el motor entre los marcadores `<!-- COMPARTIR:INICIO -->` de
`index.html`. Tienen que llevar la dirección **completa**: con ruta relativa
WhatsApp no muestra nada. Hay un test que lo vigila.

Los tests son **341** y pasan todos.

## Las reglas que no se tocan

Estas se decidieron con una razón. Si algo obliga a cambiarlas, **hay que
preguntar antes**, no decidirlo en el camino.

1. **Sin sueldo, no se publica.** Sin excepción por empresa verificada ni
   etiqueta que lo suavice. A propósito **no existe** una opción para
   desactivarlo: una regla que se apaga con una línea termina apagada. Está
   fijada con un test (`test_el_sueldo_sigue_siendo_eliminatorio_en_ambos`).
2. **Ante la duda, el motor no publica.** Es preferible perder un aviso bueno
   que publicar un sueldo inventado o una función que nadie escribió. Si un PDF
   no se deja leer, el aviso se rechaza; no se rellena.
3. **La dirección de cada oferta se arma con su huella, no con su posición.**
   Si dependiera de la posición, al retirarse una oferta cambiarían las
   direcciones de todas las demás y Google perdería lo indexado.
4. **Las ofertas retiradas pierden su página.** Una convocatoria cerrada que
   sigue indexada es peor que no tenerla.
5. **Siempre se enlaza al aviso original.** No reemplazamos al portal, lo
   ordenamos.
6. **Si no se puede leer el `robots.txt`, se asume que no hay permiso.** El bot
   va identificado (`CeroVagosBot`) y respeta el `Crawl-delay`.
7. **Al cambiar el filtro hay que reevaluar, y se hace EN GITHUB:** Actions →
   *Publicar el sitio* → Run workflow → marcar la casilla `reevaluar`.
   Hace falta porque los avisos guardados conservan el veredicto del día en
   que se leyeron, y el motor no vuelve a mirar un rechazado hasta pasados 30
   días: sin esto un cambio de regla tarda un mes en notarse.
   **No corre sola en cada publicación a propósito** — una reevaluación
   silenciosa podría despublicar el sitio entero si alguien mete un error en
   la rúbrica. Y **nunca en local**: reevaluar en la laptop y subir `datos/`
   pisa lo que el bot recolectó esa noche. Pasó el 4/8/2026 y borró 118
   avisos (`DESPLIEGUE.md`).
8. **El título tiene que decir qué es el trabajo.** "Papa Johns" o "Primax
   Cerro Azul" dicen la marca o el local, no el oficio: es una oferta vaga en
   el titular. El motor deduce el cargo del texto del propio aviso
   (`deducir_puesto`) y, si el aviso no lo nombra en ninguna parte, lo
   rechaza. **Nunca se inventa un cargo.** Fijado en `pruebas/test_titulos.py`.

## El filtro, en corto

Score de 0 a 100. Se publica con **70** y además hay que pasar los
eliminatorios — no se puede tapar un vacío con puntos de otro lado.

| Bloque | Puntos | Eliminatorio |
|---|---|---|
| Sueldo mensual detectado | 30 | sí |
| Funciones | 25 | **solo privado** (mínimo 3). Al Estado no |
| Requisitos | 20 | sí (mínimo 3) |
| Beneficios | 15 | sí (mínimo 2, y concretos) |
| Empresa, ciudad, modalidad, frescura | 10 | vencido o +60 días, se bota |

Dos varas distintas (`PERFILES` en `motor/score.py`), y esto es deliberado:

**Al Estado no se le exige la lista de funciones** (decidido el 4/8/2026). Una
convocatoria CAS trae puesto normado, sueldo exacto, requisitos detallados y
beneficios fijados por ley — pero sus funciones viven en el PDF de las bases,
que el portal no enlaza. Se verificó: la propia página dice "Funciones no
especificadas en la convocatoria extraída".

La vara del privado se diseñó contra otra cosa: el aviso que dice "apoyar en
labores del área" para no comprometerse. Ese sí esconde algo.

**Que no sea eliminatorio no es salir gratis.** Los 25 puntos se pierden
enteros, así que el aviso tiene que compensarlos en todo lo demás para llegar
a 70. La vara la pone el umbral, no una excepción. Y la ficha lo dice de
frente: en vez de un hueco, explica que las funciones están en las bases y
enlaza al aviso oficial.

Detalle completo en `README.md` › *El filtro*.

## Estado real (5 de agosto de 2026, noche)

**2,201 avisos revisados · 63 publicadas · 77% no dice cuánto paga.**
Sueldo mediano de lo publicado: **S/ 1,300**.

Tras estrenar Convocatorias CAS el 6/8/2026 el sitio quedó en **94 ofertas**.

| Fuente | Publicadas |
|---|---|
| Bumeran | 45 |
| Laborum | 17 |
| Convocatorias del Estado | **1** ← es un archivo, casi todo cerrado |
| Convocatorias CAS | **30** en su primera corrida (38,5% de aprobación) |

La primera corrida de CAS, en números: 174 direcciones en el sitemap, 94
saltadas por traer más de una plaza (1.263 plazas), 78 avisos leídos, 30
publicados. Casi todo provincia: Melgar, Pacucha, Tayacaja, Utcubamba, Padre
Abad, Huaytará, San Martín.

Cómo se llegó aquí en un día, porque las tres cosas se tapaban entre sí:

- El paso de privados **se cortaba a los 60 minutos** y Laborum, que iba
  segundo, no llegaba a correr. Ahora cada portal tiene su propio paso y su
  propio reloj.
- Cada aviso costaba **30 segundos en vez de 3**: se esperaba a que una
  etiqueta `<script>` se hiciera *visible*, cosa que no pasa nunca. La corrida
  entera pasó de 1 h 2 min a **15 minutos**.
- Laborum se quedaba en cero porque su sitemap devuelve un trozo cualquiera de
  sus 50 mil avisos y **casi ninguno tenía menos de 3 días**. Va sin ventana de
  días y con el doble de límite.

Ojo: el bot corre solo cada madrugada y estos números se mueven.

Una tasa de aprobación baja es señal de que el filtro funciona, no de que falte
oferta. No hay que "aflojar el filtro para tener más avisos": eso es
exactamente lo que hacen los portales que queremos reemplazar. Si hacen falta
más ofertas, la respuesta es **más fuentes**, no menos exigencia.

Una tasa de aprobación baja es señal de que el filtro funciona, no de que falte
oferta. No hay que "aflojar el filtro para tener más avisos": eso es
exactamente lo que hacen los portales que queremos reemplazar. Si hacen falta
más ofertas, la respuesta es **más fuentes**, no menos exigencia.

## Pendientes

Lo que está esperando, en orden aproximado de impacto:

0. **Decidir qué pasa con las convocatorias CAS sin funciones.** Es la
   pregunta abierta más importante, y es de Mentita, no técnica.

   *Lo que se sabe.* En la primera corrida, **48 de 78 avisos no llegaron a
   sus funciones** porque el PDF de las bases no se pudo abrir. Se comprobó el
   6/8/2026: `munisurquillo.gob.pe` **carga al instante desde Perú y no
   contesta desde los servidores de GitHub**. No es un bloqueo de la entidad ni
   un fallo del lector — es desde dónde se pregunta. La regla 6 hace lo
   correcto (sin robots.txt legible, no se pide nada), pero el efecto es que
   la fuente rinde mucho menos en la nube que en una laptop peruana.

   *El reparto, medido el 6/8/2026 (y la sorpresa).* Con los motivos separados
   en el registro y una corrida forzada con `rehacer`, los ~54 fallos salieron
   así:

   | Motivo | Veces |
   |---|---|
   | El PDF se bajó pero no se le pudieron sacar funciones | **31** |
   | El aviso no enlaza ningún PDF de bases | 14 |
   | El servidor de la entidad no contestó | 9 |

   **La hipótesis del bloqueo geográfico era falsa.** Se dio por hecho que el
   problema era que las webs `.gob.pe` no responden desde la nube, y eso explica
   solo 9 casos. El grueso —31— son PDF que **sí se descargaron** y de los que
   no supimos sacar las funciones. Ese problema es nuestro y se arregla sin
   tocar ninguna regla.

   *El segundo reparto, y por qué se construyó el OCR.* Al partir ese 31 en dos
   salieron **11 PDF sin nada de texto** (una foto escaneada) y **20 con texto
   roto**. Los 20 no usan otro encabezado: usan el correcto, mal escrito. De las
   bases de la UGEL San Pablo, copiado tal cual:

       Pr¡ncipales funciones a desanollar:

   Debería decir «Principales funciones a desarrollar». La `i` salió `¡` y las
   dos `rr` se volvieron `n`; el contenido viene además desordenado. Alguien ya
   les pasó un lector de letras antes de subirlas y le salió mal.

   O sea que los 11 y los 20 son **el mismo problema**: bases que son imágenes.
   Ensanchar el patrón de encabezados habría sido peor que no hacer nada —
   encontraría el título y publicaría renglones ilegibles, contra la regla 2.

   *Lo que se hizo (6/8/2026, decisión de Mentita).* Se construyó el OCR:
   rasterizar la página y leerle las letras nosotros, partiendo de la imagen en
   vez del texto roto. Vive en `motor/bases_pdf.py` (`texto_por_ocr`), entra
   **solo cuando el camino normal ya falló**, mira 5 páginas y tiene tope de
   tiempo. Cuesta segundo y medio por página.

   Y lleva guardián: `parece_ilegible` bota las funciones que salgan rotas, así
   que un OCR malo no ensucia el sitio. **Falta la primera corrida con esto**:
   el registro dirá «Las funciones se sacaron leyéndole las letras a la imagen»
   con su contador, y ese número dice si valió la pena el gasto.

   *La incoherencia que hay que resolver, la reparta como la reparta.* Hoy, de
   dos avisos igual de incompletos, se publica el que trae cinco requisitos y
   se rechaza el que trae tres:

   - *Ayudante de poda*, Surquillo, S/ 1.800 → 69, **rechazada**
   - *Jefe*, Municipalidad de Pacucha, S/ 2.200 → 72, **publicada**

   Ninguna de las dos dice qué vas a hacer. La que entró, además, tiene un
   título que no dice qué es el trabajo ("Jefe", "Técnico", "Especialista",
   "Asistente"), que es justo lo que la regla 8 existe para evitar. Osea que
   el sitio está publicando avisos del Estado sin funciones — una de las cuatro
   cosas que Cero Vagos promete. La decisión del 4/8 de no exigírselas al
   Estado se tomó con el argumento "las funciones están en el PDF y nosotros lo
   abrimos"; ahora se sabe que muchas veces no se puede.

   Los caminos, sin que ninguno sea obviamente el correcto: endurecer (sin
   funciones no se publica, y se caen también las de 72), aflojar (aceptar y
   arreglar los títulos vagos y la ficha), o recolectar desde Perú (choca con
   que la carpeta local no debe pisar lo del bot).

1. **Más fuentes.** 63 ofertas siguen siendo pocas para que alguien vuelva al
   día siguiente. Nunca aflojar el filtro. Revisado el mercado el 4/8/2026,
   quedan tres caminos y en este orden:

   - **Pasada de recuperación.** La corrida diaria solo mira lo publicado en
     los últimos 3 días, y nunca se leyó lo de entre 3 y 60 días atrás. No
     necesita código: una corrida con `dias = 0` y el límite privado en 400.
   - **BuscoTrabajo** (`buscotrabajo.pe`). Verificada: robots permite y
     descubre avisos. Es la única bolsa privada peruana que no es de Jobient.
     Necesita lector propio porque no trae JSON-LD — o sea, hay que sacarle el
     sueldo del texto corrido, que es exactamente donde nació el error de los
     S/ 33,800. Es el trabajo delicado.
   - **Convocatorias del Estado** y las bolsas de empresas (`EMPRESAS.md`).
2. **Ver si la corrida ya alcanza.** El 4/8 se reequilibró: el trabajo pasó de
   150 a 180 minutos, el paso de privados de 60 a 100, y al Estado se le subió
   el límite de 120 a 300 avisos. Revisar en la siguiente corrida si el aviso
   de tiempo agotado desapareció.
3. **Enviar los correos a las universidades** (`PROPUESTA-UNIVERSIDADES.md`).
   No depende de código y las respuestas tardan días.
4. **Páginas por ciudad y rubro** ("Trabajos en Arequipa con sueldo"). Es lo
   que la gente busca en Google y hoy no hay nada que aparezca para eso.
   **Todavía no hay volumen**: al 4 de agosto solo Lima pasa de 5 ofertas
   publicadas (53 de 60). Hacer páginas casi vacías le dice a Google que el
   sitio es de baja calidad. Primero más fuentes, después las páginas.
5. **Detector de requisitos discriminatorios** (Ley 26772). Se encontró un
   aviso pidiendo "Edad: entre 20 y 45 años".

## Trampas conocidas

Cosas que ya nos costaron caro. Casi todas vinieron de suponer en vez de
verificar.

- **Cuando el aviso NOMBRA su sueldo, le gana al portal.** Los portales
  publican una ficha de datos con el sueldo aparte del texto, y el motor le
  hacía más caso a esa ficha — razonable, salvo cuando el empleador metió ahí
  sus comisiones. En ese campo no hay ninguna palabra que diga "comisión",
  solo un número pelado, así que la defensa del texto no lo alcanzaba. Ahora
  un monto precedido de "sueldo", "salario" o "remuneración" en el cuerpo
  manda sobre la ficha (`solo_etiquetado` en `sueldo.py`, orden en
  `procesar_cruda`). No afloja la regla 1: entre dos números que dicen ser el
  sueldo, gana el que trae la palabra pegada.
- **Para reparar avisos viejos no basta `rehacer`: hay que abrir `dias` a 0.**
  `rehacer` hace que no se salten los avisos ya vistos, pero antes hay que
  DESCUBRIRLOS, y Bumeran solo busca lo publicado en los últimos 3 días. Un
  aviso de hace 7 días nunca entra en la búsqueda y conserva lo que se le leyó
  el día que llegó. Para repararlos: `dias = 0` **y** `rehacer` marcado.
- **Lo que califica a un monto tiene que estar PEGADO a él.** Es la misma
  lección dos veces. Primero con el periodo (los S/ 33,800, abajo). Y el
  7/8/2026 otra vez con la etiqueta: un aviso decía *"Sueldo básico: S/ 1,130.
  Comisiones de hasta S/ 600"* y el sitio publicaba **S/ 600**, porque la
  ventana de 40 caracteres que busca la palabra "sueldo" alcanzaba el
  "básico:" del monto anterior. Ahora la ventana se corta en el punto o en el
  monto previo (`_ventana_de_etiqueta`), y además hay una lista de palabras
  —comisión, bono, vale, movilidad— que dicen que ese monto NO es el sueldo
  (`_NO_ES_SUELDO`). Vigilado en `pruebas/test_sueldo_no_es_bono.py`.
- **Una pista buscada como pedazo de texto calza dentro de otra palabra.**
  «Asesor de Cobranza» salía como **Construcción**, porque la pista `obra`
  está dentro de «c-obra-nza»; e `intern` está dentro de «interna», así que
  cualquier auditoría interna se iba a Prácticas. No da error y no se ve
  leyendo el código: solo se nota mirando una tarjeta. Ahora las pistas se
  buscan al inicio de palabra (`\b`) y `intern` exige la palabra entera.
- **Arreglar el motor NO arregla lo ya publicado.** Un aviso guardado conserva
  el sueldo que se le leyó el día que entró, y `reevaluar` **no lo vuelve a
  leer**: solo lo vuelve a puntuar con el número ya guardado (el texto original
  no se guarda). Para reparar un dato mal leído hay que volver a DESCARGAR el
  aviso: Actions → *Recolección diaria* → Run workflow → marcar `rehacer`.
- **Un sueldo de S/ 33,800 publicado por error.** El motor leyó "S/ 1,300" y
  una frase suelta a treinta caracteres de distancia lo convirtió en pago
  diario. Por eso el periodo (mensual, diario, anual) solo se busca **pegado**
  al monto, nunca en el párrafo entero.
- **`lastmod` del sitemap ≠ fecha de publicación.** El primero dice cuándo el
  portal tocó la página. Filtrar el descubrimiento con esa fecha deja la
  corrida en cero.
- **Cuarenta avisos viejos seguidos cortan la búsqueda.** Cuando una fuente se
  recorre de lo más nuevo a lo más viejo (`ordenar_por_id`), el motor supone
  que si ya van 40 seguidos fuera de la ventana, lo que queda también lo está,
  y para. Es correcto — salvo cuando la ventana está mal puesta. A las
  Convocatorias del Estado las paró en la dirección 100 de 512 y las dejó en
  cero, en verde y en minuto y medio.
- **Cada portal necesita su propia ventana de días, y Laborum va sin ninguna.**
  Su sitemap trae 50 mil direcciones sin orden de fecha, así que las 240 que se
  alcanzan a mirar son un trozo cualquiera del archivo. Con la ventana de 3
  días se descartaban 239 de 240 antes de leerlas y la fuente aportaba **cero
  todas las noches, en verde y sin un solo error**. Sin ventana, de esas mismas
  240 pasa el filtro un 4%. No entra nada viejo por esto: el filtro sigue
  botando todo lo de más de 60 días. Bumeran sí funciona con 3 días porque su
  sitemap viene con lo nuevo primero.
- **Una fuente que devuelve cero no falla: sale en verde.** Los pasos llevan
  `continue-on-error` a propósito (un portal caído no debe tumbar la corrida),
  así que el check verde no dice que haya funcionado. Lo que hay que mirar es
  el bloque *Fuentes que no entregaron nada* del resumen.
- **Bumeran y Laborum cargan por JavaScript**: por HTTP simple devuelven "You
  need to enable JavaScript". Necesitan Playwright.
- **Computrabajo está detrás de un WAF** y no se raspa. El motor lo salta solo.
  El camino es un acuerdo, o vivir sin él.
- **Bumeran y Laborum son la misma empresa.** Las dos son del grupo **Jobint**
  (que además opera ZonaJobs, Konzerta y Multitrabajos). Y **Aptitus**, el otro
  portal grande del Perú, lo compró Bumeran y lo absorbió bajo su marca. Parece
  que hubiera dos fuentes privadas: es una casa con dos puertas. Por eso sus
  tasas de aprobación se parecen tanto, y por eso agregar Aptitus no sumaría
  nada. Fuera de Jobint solo quedan Computrabajo (bloqueado) y BuscoTrabajo.
- **Muchas webs `.gob.pe` no contestan desde los servidores de GitHub.**
  Comprobado el 6/8/2026: `munisurquillo.gob.pe` carga al instante desde una
  conexión peruana y da tiempo de espera agotado desde la nube. Como el motor
  pide el `robots.txt` antes de bajar nada y la regla 6 dice que sin respuesta
  no hay permiso, el PDF de las bases no se descarga y el aviso se queda sin
  funciones. **Un "no contestó" no es un "no nos dejan"**, y el registro ahora
  los distingue. Antes de culpar al lector, mirar ese reparto.
- **Los tests escribían en el caché de PDF de verdad** (`datos/pdfs/`), y peor:
  el PDF que dejaba un test se lo encontraba el siguiente, que entonces ni
  llamaba a la descarga y comprobaba otra cosa distinta de la que decía. Se
  desvía `bases_pdf.CACHE` a una carpeta temporal (`CachePropio` en
  `test_bases_motivos.py`). Es el mismo error que ya había pasado con
  `datos/ofertas.js`.
- **GitHub sirve archivos viejos por unos minutos.** Al revisar si un cambio
  llegó, `raw.githubusercontent.com` puede devolver la versión de antes durante
  varios minutos y hacer creer que la subida falló. Pasó el 6/8/2026 y costó
  media hora de dar vueltas. Lo que sí manda es la página del archivo en
  `github.com`, que muestra el commit y la hora. Para leerlo sin caché, se pide
  por el número del commit en vez de por `main`.
- **Una dirección de Convocatorias CAS puede traer varios puestos.** Con
  sueldos distintos: Surquillo lista 6 plazas en 2 puestos (S/ 1,350 y
  S/ 2,800). El motor asume una dirección, un aviso, así que publicar una de
  las dos sería elegir por el postulante. Por eso solo entran las de UNA plaza
  y las demás se cuentan (`motor/fuentes/cas.py`).
- **Buscar una etiqueta por simple prefijo agarra el menú.** Al leer
  «Institución» de la ficha, el enlace «Instituciones» de la barra de arriba
  calzaba primero y la entidad terminaba siendo «es». La etiqueta tiene que
  terminar donde corresponde: detrás solo puede venir ':' o un paréntesis
  (`tras_etiqueta` en `cas.py`).
- **«Sin fecha de publicación» no es «hoy».** El exportador convertía la
  ausencia de fecha en cero días y la tarjeta salía diciendo «Publicada hoy».
  Las convocatorias CAS no dicen cuándo se publicaron —dicen hasta cuándo se
  puede postular— así que todas habrían salido con una fecha inventada. Ahora
  el dato viaja en `null` y la web se calla.
- **Los agregadores no sirven aquí.** Jora, Indeed y Jooble no publican oferta
  propia: repiten la de otros portales y mandan al usuario a un tercer sitio.
  Eso choca de frente con la regla 5. Jora además tiene el `robots.txt` caído
  (502), o sea que por la regla 6 ni se toca.
- **SQLite falla en carpetas sincronizadas** (iCloud, Drive, Dropbox) al tomar
  bloqueos. Salida: `export CEROVAGOS_DB=~/cerovagos.db`.
- **El formulario de alertas está restringido a `cerovagos.com`** en Formspree.
  Si el dominio cambia, hay que cambiarlo ahí el mismo día o todos los
  registros se van a spam en silencio (`ALERTAS.md`).
- **El correo del proyecto es `info@cerovagos.com`** (Google Workspace) y sale publicado
  en las páginas legales. No inventar direcciones: la política de privacidad
  promete que se puede pedir la baja de un dato, y si el correo rebota esa
  promesa no vale nada.
- **La política de contenido de las páginas es una lista blanca.** Al agregar
  cualquier servicio externo (otro formulario, un contador de visitas) hay que
  sumarlo a la etiqueta `Content-Security-Policy` o no funcionará, y falla en
  silencio. `pruebas/test_seguridad.py` avisa.
- **Los tests escribían en `datos/` de verdad.** `generar()` recibía carpeta
  temporal pero por dentro llamaba a `exportar()`, que escribía siempre en
  `datos/ofertas.js`. Correr los tests dejaba la portada con dos ofertas
  falsas ("Analista de Datos — Acme"). Arreglado; lo vigila
  `PruebaAislamiento` en `test_sitio.py`.
- **Nunca correr dos recolecciones a la vez** ni tocar el repositorio mientras
  una corre: al final ella misma guarda cambios y chocan.
- **Cuando GitHub Actions esté encendido, la carpeta local deja de mandar.**
  El bot escribe cada madrugada en `datos/`, `oferta/` y `sitemap.xml`. Subir
  la copia local de esas carpetas borra lo recolectado esa noche y, al pisar
  la base, obliga al motor a redescargar todo. Lo que sigue siendo de ella:
  `index.html`, `motor/`, `assets/` y los `.md`. Detalle en `DESPLIEGUE.md`.

## Comandos que más se usan

```bash
python3 -m motor recolectar --publicas --limite 60 --exportar
python3 -m motor recolectar --fuente "Convocatorias CAS" --publicas --limite 60
python3 -m motor publicar --sitio https://mentitaa.github.io/cero-vagos
python3 -m motor diagnostico                 # ¿cada fuente se puede leer?
python3 -m motor stats                       # cómo va la base
python3 -m motor rechazos                    # qué se botó y por qué
python3 -m motor reevaluar                   # repuntuar lo guardado tras cambiar el filtro
python3 -m motor probar-url "https://..."    # probar UN aviso contra el filtro
python3 -m unittest discover pruebas -v      # los 341 tests
./noche.sh                                   # corrida larga (2-3 horas)
./actualizar.sh                              # corrida diaria
```
