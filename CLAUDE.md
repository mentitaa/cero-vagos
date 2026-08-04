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

**El sitio en vivo: https://mentitaa.github.io/cero-vagos/**

Esa es la dirección de hoy. El dominio elegido es **`cerovagos.com`**, ya
decidido pero **todavía sin comprar**. Cuando se compre y se conecte en GitHub,
el sitio se muda solo: el generador lee el archivo `CNAME` y reescribe todas
las páginas, el sitemap y los enlaces (ver `DOMINIO.md`). No hay que tocar
código.

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
| `DOMINIO.md` | Conectar `cerovagos.com` cuando se compre. |
| `ALERTAS.md` | Las alertas: cómo están conectadas y cómo se mandan. |
| `SEGURIDAD.md` | Auditoría de seguridad: qué se revisó y qué queda abierto. |
| `EMPRESAS.md` | Estrategia de bolsas de trabajo de empresas. |
| `PROPUESTA-UNIVERSIDADES.md` | Correos listos para las bolsas universitarias. |
| Bitácora en Notion | Historia del proyecto, ideas pendientes, errores que costaron caro, glosario. Ahí va lo narrativo; aquí va lo operativo. |

Código: `motor/` (recolección, filtro, score, publicación), `datos/` (SQLite,
se genera solo), `pruebas/` (los tests), `index.html` (el sitio, un solo
archivo), `oferta/` (una página por oferta, generada).

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

Los tests son **207** y pasan todos. Ojo: el `README.md` todavía dice 43, quedó
viejo.

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
7. **El título tiene que decir qué es el trabajo.** "Papa Johns" o "Primax
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
| Funciones | 25 | sí (3 privado / 1 público) |
| Requisitos | 20 | sí (mínimo 3) |
| Beneficios | 15 | sí (mínimo 2, y concretos) |
| Empresa, ciudad, modalidad, frescura | 10 | vencido o +60 días, se bota |

Dos varas distintas (`PERFILES` en `motor/score.py`): al sector privado se le
exige más porque él escribe el aviso y pone la fecha; al Estado se le exige
distinto porque sus funciones están en el PDF de las bases y muchas veces no
publica fecha de cierre.

Detalle completo en `README.md` › *El filtro*.

## Estado real (4 de agosto de 2026)

Primera corrida larga completada. Números de la base (`datos/cerovagos.db`):

| Fuente | Leídos | Aprobados |
|---|---|---|
| Bumeran | 779 | 32 |
| Laborum | 327 | 30 |
| Convocatorias del Estado | 101 | 12 |
| **Total** | **1207** | **60** publicadas hoy |

Por qué se rechazaron (un aviso puede fallar en varias):

```
747×  No declara sueldo
597×  Beneficios por debajo del mínimo
491×  Funciones por debajo del mínimo
471×  Requisitos por debajo del mínimo
161×  Sueldo "a convenir" o similar
 44×  Beneficios genéricos
 24×  El plazo ya cerró
```

**El sueldo mata el 75% de los avisos.** Ese es el dato que resume el mercado
laboral peruano y la razón de ser del producto.

Una tasa de aprobación baja es señal de que el filtro funciona, no de que falte
oferta. No hay que "aflojar el filtro para tener más avisos": eso es
exactamente lo que hacen los portales que queremos reemplazar. Si hacen falta
más ofertas, la respuesta es **más fuentes**, no menos exigencia.

## Pendientes

Lo que está esperando, en orden aproximado de impacto:

1. **Encender GitHub Actions** para que el motor corra solo cada madrugada y la
   laptop deje de ser infraestructura (`DESPLIEGUE.md`). El workflow ya está
   escrito. Ojo con la trampa de quién manda sobre `datos/` y `oferta/` una vez
   encendido.
2. **Más fuentes.** 60 ofertas es poco para que alguien vuelva al día
   siguiente. El camino son las bolsas de empresas (`EMPRESAS.md`), no aflojar
   el filtro.
3. **Enviar los correos a las universidades** (`PROPUESTA-UNIVERSIDADES.md`).
   No depende de código y las respuestas tardan días.
4. **Comprar y conectar `cerovagos.com`** (`DOMINIO.md`). No hay archivo
   `CNAME` todavía. Comprarlo pronto aunque no se conecte: la antigüedad del
   dominio ayuda.
5. **Alinear el `.pe` con el `.com`.** El bot todavía se presenta como
   `cerovagos.pe` en `motor/fuentes/base.py` (`USER_AGENT`) y firma como
   `bot@cerovagos.pe` en GitHub Actions. Cambiarlos al comprar el dominio, para
   que la dirección de contacto que ven los portales exista de verdad.
6. **Páginas por ciudad y rubro** ("Trabajos en Arequipa con sueldo"). Es lo
   que la gente busca en Google y hoy no hay nada que aparezca para eso.
7. **Detector de requisitos discriminatorios** (Ley 26772). Se encontró un
   aviso pidiendo "Edad: entre 20 y 45 años".
8. Bajar el límite por portal de 150 a ~80 en las corridas nocturnas. La
   primera corrida larga tomó más de 3 horas.

## Trampas conocidas

Cosas que ya nos costaron caro. Casi todas vinieron de suponer en vez de
verificar.

- **Un sueldo de S/ 33,800 publicado por error.** El motor leyó "S/ 1,300" y
  una frase suelta a treinta caracteres de distancia lo convirtió en pago
  diario. Por eso el periodo (mensual, diario, anual) solo se busca **pegado**
  al monto, nunca en el párrafo entero.
- **`lastmod` del sitemap ≠ fecha de publicación.** El primero dice cuándo el
  portal tocó la página. Filtrar el descubrimiento con esa fecha deja la
  corrida en cero.
- **Bumeran y Laborum cargan por JavaScript**: por HTTP simple devuelven "You
  need to enable JavaScript". Necesitan Playwright.
- **Computrabajo está detrás de un WAF** y no se raspa. El motor lo salta solo.
  El camino es un acuerdo, o vivir sin él.
- **SQLite falla en carpetas sincronizadas** (iCloud, Drive, Dropbox) al tomar
  bloqueos. Salida: `export CEROVAGOS_DB=~/cerovagos.db`.
- **El formulario de alertas está restringido a `mentitaa.github.io`** en
  Formspree. Al conectar `cerovagos.com` hay que cambiarlo ahí o todos los
  registros se van a spam en silencio (`DOMINIO.md`).
- **El correo del proyecto es `cerovagos.alertas@gmail.com`** y sale publicado
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
python3 -m motor publicar --sitio https://mentitaa.github.io/cero-vagos
python3 -m motor diagnostico                 # ¿cada fuente se puede leer?
python3 -m motor stats                       # cómo va la base
python3 -m motor rechazos                    # qué se botó y por qué
python3 -m motor probar-url "https://..."    # probar UN aviso contra el filtro
python3 -m unittest discover pruebas -v      # los 154 tests
./noche.sh                                   # corrida larga (2-3 horas)
./actualizar.sh                              # corrida diaria
```
