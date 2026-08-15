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
| `GOOGLE.md` | Search Console: verificar el sitio y mandar el sitemap, paso a paso. |
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

**El score ya no se muestra en la web** (7/8/2026), ni en la tarjeta ni en la
ficha de cada oferta. Sigue decidiendo qué se publica y en qué orden, pero
dejó de verse. Salió de un focus group improvisado: varias personas lo leyeron como una nota al
TRABAJO, veían S/ 4.000 con 89 al lado de S/ 500 con 98 y no entendían nada.
Y el número nunca pudo servirles de nada, porque **todo lo que se publica ya
pasó el filtro**: su único efecto posible era invitar a comparar en una
dimensión que significa otra cosa. En su lugar van las cuatro cosas que el
aviso SÍ trae —sueldo, funciones, requisitos, beneficios— marcadas una por una
(`loQueTiene` en `index.html`, `_lo_que_tiene` en `motor/sitio.py` — son dos
archivos distintos y hay que tocar los dos: la página de cada oferta se generó
durante un día entero mostrando todavía el score, porque solo se arregló
`index.html`). Es el mismo score dicho en lo que significa, y
no revela la fórmula. Las convocatorias del Estado sin funciones muestran tres
marcas en vez de cuatro, y **está bien**: es honesto y la ficha explica dónde
buscarlas. Lo vigila `pruebas/test_tarjeta.py`.

De paso se quitó la inicial de la empresa del recuadro izquierdo. Nadie sabía
qué era, y no identificaba nada: el color salía de la POSICIÓN de la tarjeta,
así que la misma empresa cambiaba de color al filtrar o al dar "Ver más".

## La paleta (13/8/2026)

Vive en el `:root` de `index.html` y se repite igual en las tres plantillas
generadas (`sitio.py`, `transparencia.py`, `lugares.py`). **Fuera de ahí no se
escribe ningún color**, y hay un test que lo vigila.

| | | Su único trabajo |
|---|---|---|
| `--marca` | `#FF1E1E` | Identidad y acción: barra de arriba, hero, botón de postular. |
| `--tinta` | `#101B2D` | Texto, bordes, sombras y bloques oscuros. |
| `--fondo` | `#F5F1E8` | El fondo de todo el sitio. |
| `--acento` | `#FFB703` | Marcar lo que el aviso SÍ trae, y el sueldo. Nada más. |
| `--ok` / `--alerta` | | **Solo** en `/transparencia`. No son de marca. |

**Por qué se hizo.** El feedback fue que los colores parecían puestos por
poner — y lo parecían porque lo estaban: había **siete** tonos saturados (rojo,
amarillo, lima, cyan, magenta, azul, crema) sin ninguna regla de quién manda.
El amarillo se usaba 17 veces y el rojo 13: el color de marca no era el que más
aparecía en su propia web.

**Tres decisiones que conviene no deshacer:**

- **El negro puro pasó a azul tinta.** Sobre tinta el rojo golpea más y vibra
  menos, y separa el sitio de Laborum, que es rojo y blanco.
- **Un solo acento.** Amarillo, lima, cyan y magenta eran cuatro decoraciones;
  ahora son un ámbar con un trabajo. Las cuatro tarjetas del filtro van del
  MISMO color a propósito: son cuatro reglas que valen lo mismo, y pintarlas
  distinto insinuaba una jerarquía que no existe.
- **El rojo de marca no significa "mal".** En `/transparencia` la peor nota
  usa `--alerta`, otro rojo. Si la marca calificara de malo a alguien, el color
  más presente de la web sería el de la peor calificación.

El logo va sobre el fondo hueso, sobre la tinta o sobre blanco. **Nunca sobre
el ámbar**: rojo sobre naranja vibra y se lee mal.

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

Los tests son **482** y pasan todos.

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
| Trabajos Diarios | recién conectada (13/8/2026) |

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

## Las convocatorias del Estado sin funciones (decidido el 7/8/2026)

Estuvo abierto tres días y lo cerró Mentita: **se quedan como están.** Del
Estado se publica lo que traiga, aunque no diga qué vas a hacer, y **no se
cambia nada más**: ni la promesa de las cuatro cosas, ni el umbral, ni el
título de la portada.

En la práctica esas convocatorias muestran **tres marcas de cuatro** (sueldo,
requisitos, beneficios) y en «Qué vas a hacer» va el párrafo que explica que
las funciones viven en las bases del concurso. Nada más: ni disculpa, ni
etiqueta, ni advertencia. Se vio en la ficha de *Especialista en Salud
Ambiental II* (Huancavelica, S/ 3,000) y quedó aprobada tal cual.

**Por qué es defendible.** Cero Vagos no promete que el aviso sea perfecto:
promete no esconderte lo que falta. Un portal cualquiera te haría postular sin
enterarte; acá el hueco está señalado, dice dónde buscar y enlaza al documento
oficial. La convocatoria además trae sueldo exacto, requisitos detallados y
beneficios de ley, que es más de lo que trae el 95% de los avisos privados.

**Qué se descartó, y por qué.**

- *Endurecer* (sin funciones no se publica) habría botado casi todas las CAS,
  que hoy son la fuente con mejor tasa de aprobación y casi toda la oferta de
  provincia del sitio. Se habría perdido el aviso completo por no tener una
  lista que la entidad nunca publicó.
- *Recolectar desde Perú* arregla 9 casos de 54 y obliga a que la laptop
  escriba donde escribe el bot. Mucho riesgo para poco.

**Lo que queda vivo de esto.** Los títulos que no dicen qué es el trabajo
—«Jefe», «Técnico», «Especialista»— son un problema de la regla 8, no de esta
decisión. Ver abajo.

*El detalle de cómo se llegó acá —los 54 fallos repartidos por motivo, la
hipótesis del bloqueo geográfico que resultó falsa, y por qué se construyó el
OCR— está en la bitácora de Notion.*

## Las páginas de listado: por departamento y por rubro (12/8/2026)

`/trabajos-en/junin/`, `/trabajos-en/huancavelica/`… Una por departamento que
tenga **5 ofertas publicadas o más** (`MINIMO_OFERTAS` en `motor/lugares.py`).
Es lo que la gente escribe en Google y lo que la portada no puede cubrir: la
portada compite por "ofertas de trabajo Perú", que es pelear contra
Computrabajo; "trabajos en Huancavelica con sueldo" no lo pelea nadie.

No se pudieron hacer antes porque no había con qué llenarlas: al 8/8 solo Lima
pasaba de cinco. Lo que lo destrabó fue partir las convocatorias CAS de varios
puestos — la provincia pasó de 24 a 73 ofertas y de 1 departamento con volumen
a 4.

**Aparecen y desaparecen solas, y esto no es opcional.** Una convocatoria CAS
dura una o dos semanas, así que un departamento con 29 ofertas puede quedar en
3 quince días después. Si baja del mínimo, su página se borra — la misma regla
4 de las ofertas vencidas. Una página indexada sin contenido le dice a Google
que el sitio es de baja calidad, y esa señal mancha al resto.

**Cada página trae un dato que no tiene nadie más**: cuántos avisos se
revisaron en ese departamento y cuántos declaraban sueldo. Sin eso sería un
listado más, y un listado más no merece existir ni posicionar.

**Lima sí tiene página**, aunque sea el 77% del sitio: apunta a otra búsqueda
que la portada, tiene su propio título y su propio dato local.

**Las de rubro son la misma página con otro eje**: `/trabajos-de/ventas/`,
`/trabajos-de/salud/`. Viven en el mismo archivo para que no se
desincronicen. Dos diferencias, las dos deliberadas:

- **Piso más alto** (`MINIMO_RUBRO` = 8 contra 5). Una página de "trabajos de
  ventas" compite contra todas las bolsas del Perú; "trabajos en Huancavelica"
  no compite con casi nadie. Donde la pelea es dura hay que llegar con más.
- **"Otros" nunca tiene página.** No es un rubro: es el cajón de lo que el
  motor no supo clasificar. Nadie busca "trabajos de otros", y publicarlo diría
  que el sitio no sabe lo que publica.

Los enlaces del pie de la portada los escribe el motor entre los marcadores
`<!-- LUGARES:INICIO -->`, porque cuáles existen cambia cada día. Cada ficha de
oferta enlaza además a la página de su departamento. Vigilado en
`pruebas/test_lugares.py`.

**La trampa del refactor, anotada porque casi pasa:** al generalizar la
plantilla para los dos ejes, la carpeta a limpiar se dedujo del PRIMER grupo
publicado. Con cero grupos no había primer grupo, así que no se limpiaba nada y
las páginas viejas se quedaban publicadas para siempre — justo el caso extremo
que la limpieza existe para cubrir. Lo cazó un test que ya estaba escrito.

## Los títulos que solo dicen un rango (13/8/2026)

La regla 8 tenía un agujero: daba por bueno **«Técnico»** porque "tecnico"
está en la lista de oficios. Pero un rango solo no es un puesto — «Enfermera»
dice qué vas a hacer, «Especialista» obliga a preguntar en qué.

Esa es la distinción, y está en `titulo_vago` (`motor/normalizar.py`): hay
palabras que nombran un **oficio** y palabras que nombran un **rango**. Un
número de escala tampoco cuenta: «Técnico I» es tan vago como «Técnico».

**No se rechazan. Se miden** (decisión de Mentita). `motor stats` los cuenta
separados en dos grupos, porque son dos casos que no se deciden igual:

- **Del Estado no esconden nada.** «Técnico I» es el cargo tal como figura en
  la escala normada. La entidad no está siendo evasiva.
- **Del privado sí es una elección.** Nadie obliga a una consultora a titular
  su aviso «Asesor» a secas. Esos son primos hermanos de «Papa Johns».

Si el número del privado crece, hay motivo para endurecer **solo ese lado**.

**Completarlos solos no se puede**, y se probó: el requisito «Título de técnico
en enfermería» dice lo que hay que SER, no cuál es el puesto. Con «Jefe» y
«Título en Ingeniería Civil» saldría «Ingeniero Civil», que puede no ser el
cargo. Eso es inventar, y la regla 8 lo prohíbe. Vigilado en
`pruebas/test_titulos_vagos.py`.

## Pendientes

Lo que está esperando, en orden aproximado de impacto:

1. **Más fuentes.** 63 ofertas siguen siendo pocas para que alguien vuelva al
   día siguiente. Nunca aflojar el filtro. Revisado el mercado el 4/8/2026,
   quedan tres caminos y en este orden:

   - **Pasada de recuperación.** La corrida diaria solo mira lo publicado en
     los últimos 3 días, y nunca se leyó lo de entre 3 y 60 días atrás. No
     necesita código: una corrida con `dias = 0` y el límite privado en 400.
   - ~~Las convocatorias CAS de varias plazas~~. **Hecho el 8/8/2026**: ahora
     cada puesto sale como un aviso propio. Ver abajo.
   - **Convocatorias del Estado** y las bolsas de empresas (`EMPRESAS.md`).

   **BuscoTrabajo está descartado** (8/8/2026): tiene **4 empleos activos y 10
   empresas registradas** en todo el portal. Ver la trampa de abajo.
2. **Ver si la corrida ya alcanza.** El 4/8 se reequilibró: el trabajo pasó de
   150 a 180 minutos, el paso de privados de 60 a 100, y al Estado se le subió
   el límite de 120 a 300 avisos. Revisar en la siguiente corrida si el aviso
   de tiempo agotado desapareció.
3. ~~Enviar los correos a las universidades~~ **DESCARTADO el 13/8/2026.**
   Mentita revisó bolsas universitarias de Trujillo y Lima: **ninguna publica
   el sueldo**. Eso mata la idea dos veces. La propuesta ya pedía publicar esas
   ofertas con solo puesto, empresa y enlace —un agujero en la regla 1— con la
   excusa de que el detalle se veía haciendo clic; ahora se sabe que al hacer
   clic tampoco está el sueldo. Se rompía la promesa del sitio y encima no
   servía. `PROPUESTA-UNIVERSIDADES.md` se conserva por si algún día una
   universidad cambia de práctica.
4. ~~Páginas por ciudad y por rubro~~ **Hechas el 12/8/2026**. Ver abajo.
5. **Detector de requisitos discriminatorios** (Ley 26772). Se encontró un
   aviso pidiendo "Edad: entre 20 y 45 años".

## Trampas conocidas

Cosas que ya nos costaron caro. Casi todas vinieron de suponer en vez de
verificar.

- **Un aviso con DOS sueldos no se publica.** Pasa cuando una sola
  publicación convoca varias modalidades: un "Reponedor(a) Full Time" que en
  realidad ofrecía las dos jornadas declaraba "Remuneración: S/ 1,130" y
  "Remuneración: S/ 565", y el motor elegía el más bajo por prudencia —
  publicando un sueldo de medio tiempo bajo un título de tiempo completo.
  Elegir el más bajo protege de prometer de más, pero no de mentir
  (`declara_varios_sueldos`). El mismo monto repetido no cuenta como conflicto.
- **`--reparar` ignora la ventana de días, y tiene que ser así.** Reparar con
  `--dias 3` releía los avisos y después los tiraba por viejos: el 7/8/2026 se
  releyeron 49 de Bumeran y 29 se descartaron como "vencidos" antes de
  guardarse, justo el que había que corregir entre ellos. Un aviso publicado ya
  pasó el filtro de antigüedad el día que entró; de sacarlo de la web se
  encarga `depurar`.
- **Cuando el aviso NOMBRA su sueldo, le gana al portal.** Los portales
  publican una ficha de datos con el sueldo aparte del texto, y el motor le
  hacía más caso a esa ficha — razonable, salvo cuando el empleador metió ahí
  sus comisiones. En ese campo no hay ninguna palabra que diga "comisión",
  solo un número pelado, así que la defensa del texto no lo alcanzaba. Ahora
  un monto precedido de "sueldo", "salario" o "remuneración" en el cuerpo
  manda sobre la ficha (`solo_etiquetado` en `sueldo.py`, orden en
  `procesar_cruda`). No afloja la regla 1: entre dos números que dicen ser el
  sueldo, gana el que trae la palabra pegada.
- **Para reparar un dato mal leído está `--reparar`, no `rehacer`.** `rehacer`
  solo dice "no te saltes lo ya visto", pero la fuente sigue descubriendo
  direcciones en su sitemap y **se detiene al llegar a su cupo** (Bumeran lee
  120 avisos y para, aunque queden miles). Que un aviso guardado caiga dentro
  de ese corte es cuestión de suerte: el 7/8/2026 se corrió tres veces para
  corregir tres avisos y los tres quedaron fuera las tres. `--reparar` le pide
  las direcciones a la base (`urls_publicadas`) y relee exactamente lo que está
  publicado. En GitHub es la casilla *"¿Releer las ofertas YA PUBLICADAS?"*.
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
- **Lo que descalifica a un monto también va DETRÁS de él.** Hasta el
  12/8/2026 la lista de "esto no es sueldo" (comisión, bono, movilidad) solo se
  miraba antes del número, y en el texto real suele ir después: *"Sueldo fijo
  + S/ 500 **de movilidad**"* publicaba el pasaje como sueldo, y *"Gana S/600
  **por invitar** 02 personas"* publicaba un bono por referidos. Lo cazó
  Mentita revisando la página de Ventas. **Pero cuidado con pasarse**: en
  *"Sueldo base de S/. 650 + Comisiones"* y en *"Sueldo base: S/.1200 / Bono de
  asistencia: S/.200"* la palabra también va detrás y los dos montos SON
  correctos. La regla que separa los casos: descalifica solo si va pegado con
  un nexo —"de", "por", "en"— y dentro de la misma frase. Un concepto nuevo
  empieza con "+", con su rótulo o tras un punto.
- **El motor sabía la moneda y la perdía al mostrarla.** `US$ 1,000` salía
  publicado como `S/ 1,000` — casi cuatro veces menos de lo que paga— en la
  tarjeta, en la ficha y en los datos que lee Google. El parser SÍ distingue
  soles de dólares y lo guardaba en la base; lo que faltaba era llevarlo hasta
  la pantalla (12/8/2026). Van cuatro sitios y hay que tocarlos todos:
  `exportar.py` (para que viaje), `index.html` (`monto()`), `sitio.py`
  (`_sueldo_texto` y el `currency` del JobPosting) y `lugares.py`. La mediana
  de las páginas de listado se calcula **solo sobre las ofertas en soles**:
  mezclar S/ 1,800 con US$ 1,000 daría un número sin significado.
- **La casilla de sueldo del portal puede resucitar un monto ya descartado.**
  Es la tercera puerta del mismo aviso de Grupo Qualidad Humana: tapada la
  movilidad de S/ 500 y el ingreso garantizado de $1,000, el sitio seguía
  publicando S/ 1,000 porque ese era el número que el empleador había escrito
  en el formulario de Bumeran. Contra esa casilla no hay defensa mirando su
  contenido —es un número pelado, sin palabras alrededor—, así que la defensa
  es otra: **si el propio aviso ya dijo que ese monto no es el sueldo, el
  portal no puede resucitarlo** (`montos_que_no_son_sueldo`). Se compara por
  NÚMERO y no por texto, porque "$1,000" y "S/ 1000" son el mismo monto
  escrito distinto.
- **Un aviso que enumera cinco formas de pago y ninguna es el sueldo va a
  seguir ofreciendo candidatos hasta que se acaben.** Ese mismo aviso lo
  intentó tres veces por tres caminos distintos. Con esos conviene mirar el
  penúltimo número con la misma desconfianza que el último.
- **Un monto puede decir de frente que NO es el sueldo.** "Ingreso garantizado
  de $1,000 durante los primeros 3 meses, **adicional al fijo**". El aviso
  mismo avisa de que es temporal y que va aparte, y aun así nunca declara el
  fijo. Es el mismo aviso que ya había colado la movilidad: tapada una puerta,
  el motor se fue por la otra. Está en `_NO_ES_EL_FIJO` y se busca en la frase
  entera del monto, no pegado, porque "adicional al fijo" suele ir al final.
- **"Acorde al mercado" estaba detectado pero desconectado.**
  `declara_sueldo_vago` existía desde el primer día, con su test, y solo se
  usaba para REDACTAR el motivo del rechazo — nunca para decidir. Un aviso de
  PRESTAMYPE que decía literalmente "Sueldo acorde al mercado" salió publicado
  con un S/ 300 que el motor encontró suelto en otra parte. Ahora, si el aviso
  lo dice y no hay un monto etiquetado, no se publica. Moraleja: una función
  probada no sirve de nada si nadie la llama.
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
- **El JSON-LD puede traer el RESUMEN, no el aviso.** Trabajos Diarios publica
  sus datos en el formato de Google y de ahí salen bien el puesto, la empresa,
  el sueldo y las dos fechas — pero su `description` es el resumen corto, el
  que sale recortado con "…" en los resultados de búsqueda. **Una línea.** Con
  eso los doce avisos del sondeo salieron en 0 funciones / 0 requisitos / 0
  beneficios y se cayeron todos. Ese patrón tan parejo es la señal: si fueran
  los avisos los incompletos habría variación. El cuerpo sí está en la página,
  bajo el título "Descripción del empleo", y se corta por el TÍTULO y no por
  el maquetado, porque el título es lo que lee la persona y no lo mueven sin
  querer (`motor/fuentes/trabajos_diarios.py`).
- **`findall` con paréntesis devuelve el paréntesis, no el enlace.** Los
  patrones que descubren avisos usan alternativas —`/(trabajo|empleo|oferta)…`—
  porque cada portal le puso otro nombre a la página de un aviso. Al buscarlos
  con `findall`, Python devolvía SOLO lo de adentro del paréntesis: "trabajo",
  no "/trabajo/3075258/auxiliar-de-almacen". Todos los enlaces de una página se
  reducían a la misma palabra, se deduplicaban entre sí y una página con 165
  avisos aportaba **un** enlace, que encima no llevaba a ningún lado. Y no
  fallaba con un cero —que invita a mirar— sino con un uno, que parece que algo
  funcionó. Afectaba a TODAS las fuentes que descubren por listado. Se arregla
  con `finditer` + `group(0)` (`pruebas/test_descubrir_enlaces.py`).
- **Un cero de `motor sondear` tampoco es un cero.** Es la misma trampa de
  arriba y con la agravante de que el sondeo da un consejo. Falabella y
  Cencosud devolvieron "0 avisos · no escribas el lector", y los dos portales
  tienen avisos de sobra: lo que falló fue que el lector genérico no reconoció
  sus enlaces. Desde afuera no hay forma de distinguir "está vacía" de "no supe
  dónde mirar", así que **solo un número positivo produce veredicto**. El
  informe muestra por separado los enlaces DESCUBIERTOS y los avisos LEÍDOS,
  que es lo que permite saber cuál de los dos problemas es.
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
- **El retail corporativo grande no publica sueldos, y perseguirlo era el eje
  equivocado.** Falabella y Cencosud cayeron el mismo día (13/8/2026) por lo
  mismo, y Delosi ya estaba fuera por publicar en Computrabajo: el retail
  grande del Perú, completo. La estrategia de ir por GRUPOS —un portal, muchas
  marcas— optimiza volumen, y **el volumen nunca fue lo escaso**: Bumeran y
  Laborum ya traen miles de avisos y el 77% se cae por no decir cuánto pagan.
  El eje que sirve es **a quién le conviene declarar el sueldo**: al Estado
  (escala normada), al trabajo por campaña (el jornal ES la oferta) y a quien
  pelea por gente escasa. Una marca fuerte compite con la marca, no con el
  sueldo, y no va a cambiar porque le escribamos un lector mejor. Por eso las
  CAS son hoy la mejor fuente y no fue casualidad. Detalle en `EMPRESAS.md`.
- **La verificación más barata son los ojos, y va primero.** Con la bolsa de
  Falabella se gastaron tres rondas de herramienta —sondeo, navegador, lector
  genérico— y ninguna dio el dato que la decidió. Mentita abrió el portal,
  leyó diez avisos y lo cerró en cinco minutos: **ninguno dice el sueldo**, y
  de paso todos tenían cinco meses de publicados (el filtro bota lo de más de
  60 días, así que no habría entrado ni uno). Antes de programar nada para una
  fuente nueva, hay que MIRARLA. El sondeo sirve para lo que los ojos no
  pueden —pasar 25 avisos por el filtro y contar—, no para reemplazarlos.
- **"Permite el rastreo" no es lo mismo que "tiene avisos suficientes".**
  BuscoTrabajo estuvo semanas en la lista de pendientes como la gran fuente
  privada que faltaba. Era cierto que su `robots.txt` permite entrar y que es
  la única peruana fuera de Jobint — pero nadie contó los avisos. Tiene **4
  empleos activos y 10 empresas registradas** en todo el portal, 3 de los 4 de
  la misma empresa. No es un portal chico: está recién arrancando. Verificarlo
  costó veinte minutos; escribir el lector habría costado un día. **Antes de
  escribir una fuente hay que sondearla**, y para eso está
  `motor sondear <url>`: cuenta cuántos avisos tiene y cuántos dicen el
  sueldo, pasándolos por el filtro de verdad. Es obligatorio (`EMPRESAS.md`).
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
- **Una dirección de Convocatorias CAS trae varios puestos, y cada uno es un
  aviso.** Desde el 8/8/2026 la página se parte en una ficha por puesto. Tres
  cosas que van juntas y no se tocan por separado: **un aviso por PUESTO, no
  por plaza** (5 vacantes son un aviso que dice "5 vacantes", no cinco
  tarjetas); **el sueldo tiene que estar dentro de la ficha del puesto** —el
  del resumen no se reparte, porque en Surquillo dice S/ 1,350 y ese es el del
  operario, no el del especialista de S/ 2,800—; y **dos puestos que se llaman
  igual con sueldos distintos no entran ninguno**, porque comparten huella y
  uno pisaría al otro dejando un aviso con el nombre de uno y el sueldo del
  otro. El puesto sin sueldo legible se cae solo y no arrastra a los demás
  (decisión de Mentita). Las de varios puestos **no se enriquecen con el PDF
  de las bases**: trae las funciones de todos mezcladas y no se sabe cuáles son
  de cuál. Vigilado en `PruebaVariosPuestosEnUnaPagina`.
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
- **Ponerle `display:flex` a una celda de tabla la saca de la tabla.** En
  `/transparencia` las barras verdes se pegaban ARRIBA en las filas de dos o
  tres líneas ("Municipalidad Provincial De Yarowilca") en vez de quedar a la
  altura de su empresa. La celda tenía `display:flex` encima, y eso hace que el
  navegador deje de tratarla como celda. Se arregla metiendo el contenido en un
  recuadro adentro y dejándole el flex a ese. Lo reportó Renzo el 7/8/2026.
- **El menú de celular tapaba justo lo que ibas a ver.** Los enlaces de arriba
  llevan a la misma página, así que al tocarlos la página bajaba pero el menú
  se quedaba encima. En computadora no se nota porque ese menú nunca se abre.
- **Google pide la calle y el código postal, y no se los vamos a inventar.**
  En Search Console salen tres avisos naranjas en «Ofertas de trabajo»:
  faltan `streetAddress`, `addressRegion` y `postalCode`. De los tres solo el
  departamento se podía llenar con un dato real, y se llenó (`_direccion` en
  `motor/sitio.py`, 7/8/2026). Los otros dos **se quedan vacíos**: los avisos
  peruanos no dicen la calle, y poner la dirección fiscal de la empresa
  mandaría a alguien a un sitio que no es. Son avisos, no errores: las ofertas
  cuentan como válidas igual. Vigilado en `pruebas/test_google_empleos.py`.
- **Un navegador con modo oscuro reescribe los colores del sitio si no le
  dices que no.** En Brave la portada salía irreconocible: el crema en marrón,
  el amarillo en verde oliva, el texto con recuadros de resalte. En Chrome se
  veía bien. No era el CSS: era el navegador "arreglando" la página. Se
  declara `color-scheme:light` en el `:root` y `<meta name="color-scheme">` en
  el `<head>` — y va en las **cinco** plantillas (`index.html`, ficha, salida,
  404, transparencia/legales), no solo en la portada. Reportado el 8/8/2026,
  vigilado en `pruebas/test_modo_oscuro.py`.
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
python3 -m motor sondear "https://..."       # ¿cuántos avisos tiene y cuántos dicen el sueldo?
python3 -m unittest discover pruebas -v      # los 482 tests
./noche.sh                                   # corrida larga (2-3 horas)
./actualizar.sh                              # corrida diaria
```
