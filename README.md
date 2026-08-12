# Cero Vagos

Buscador de ofertas laborales peruanas que **solo publica avisos completos**:
sueldo en soles, funciones, requisitos y beneficios. Si al aviso le falta uno,
no entra.

```
cero-vagos/
├── index.html          Sitio (prototipo funcional, un solo archivo)
├── motor/              Recolector, filtro y score
├── datos/              Base SQLite y export para el sitio (se genera solo)
├── pruebas/            Tests del motor
└── requirements.txt
```

## Correr el motor

Sin instalar nada, con avisos de ejemplo:

```bash
python3 -m motor recolectar --demo --exportar
```

Eso recolecta, filtra, guarda en SQLite y escribe `datos/ofertas.js`. Abre
`index.html` y el sitio ya muestra esas ofertas (si el archivo no existe, cae
en las ofertas de ejemplo que trae el HTML).

Con ofertas reales (convocatorias del Estado, sin navegador headless):

```bash
pip install requests pdfplumber
python3 -m motor recolectar --publicas --limite 60 --exportar
```

Después abre `index.html`: ya no verás ejemplos, sino chamba de verdad.

Para los portales que son aplicaciones React (ver *Estado de las fuentes*):

```bash
pip install playwright && playwright install chromium
```

## Que Google encuentre las ofertas

```bash
python3 -m motor publicar --sitio https://mentitaa.github.io/cero-vagos
```

Genera una página propia por oferta en `oferta/<direccion>/`, el `sitemap.xml`
y el `robots.txt`, y mete en la portada una lista de enlaces reales.

Por qué hace falta: la portada dibuja las tarjetas con JavaScript, así que un
buscador puede no verlas, y todas las ofertas comparten una sola dirección.
Con esto cada oferta tiene su URL, su título, su descripción y sus datos
estructurados `JobPosting` — los mismos que este motor lee de otros portales,
ahora publicados por nosotros. Es lo que permite aparecer en Google Empleos.

Dos decisiones que conviene no tocar:

- **La dirección se arma con la huella de la oferta, no con su posición.** Si
  dependiera de la posición, al retirarse una oferta cambiarían las direcciones
  de todas las demás y Google perdería lo indexado.
- **Las ofertas retiradas pierden su página.** Una convocatoria cerrada que
  sigue indexada es peor que no tenerla.

Falta un paso manual, una sola vez: registrar el sitio en
[Google Search Console](https://search.google.com/search-console) y enviar el
`sitemap.xml`.

## Dos automatismos, y no hay que confundirlos

| | Qué hace | Cuánto tarda | Cuándo corre |
|---|---|---|---|
| **Recolección diaria** | Sale a los portales a buscar ofertas nuevas | 20-30 min | Cada medianoche, o a mano |
| **Publicar el sitio** | Regenera las páginas con lo que ya está en la base | menos de 1 min | Solo, al subir un cambio a `index.html` o `motor/` |

Si cambiaste un texto, un color o el código de las páginas, **no hace falta
recolectar**: con publicar basta. Y ni siquiera hay que lanzarlo — se dispara
solo cuando subes el archivo.

## En piloto automático (sin tu laptop)

Lo recomendado: que el motor corra solo cada madrugada en los servidores de
GitHub, gratis, y que ahí mismo se publique el sitio.

Ver **`DESPLIEGUE.md`** — son unos 20 minutos la primera vez y después no se
toca más. La automatización ya está escrita en
`.github/workflows/actualizar.yml`.

Todo lo que sigue (correr el motor en tu Mac) queda como herramienta de prueba,
no como el día a día.

## La corrida larga (de madrugada)

Para llenar la base de una sentada:

```bash
./noche.sh
```

Recolecta las convocatorias del Estado y después los portales privados, exporta
al sitio y deja todo en `datos/noche-FECHA.log`. Toma entre dos y tres horas.

Envuelve todo en `caffeinate`, que viene con macOS: mientras corre, la Mac no se
duerme por inactividad. **Pero si cierras la tapa se suspende igual**, y el
proceso queda congelado hasta que la abras. Déjala enchufada y con la tapa
abierta.

Se puede cortar con Ctrl-C sin problema: cada oferta se guarda apenas se
procesa, así que lo recolectado no se pierde. Volver a correrlo tampoco duplica
nada — las ofertas se identifican por una huella de puesto, empresa y ciudad.

## La corrida diaria

La idea es que el sitio se refresque solo una vez al día, a medianoche hora de
Perú, buscando lo publicado el día anterior:

```bash
chmod +x actualizar.sh     # una sola vez
./actualizar.sh            # probarlo a mano
```

Ese script recolecta lo de los últimos 2 días, exporta al sitio, saca de la web
lo que ya pasó los 2 meses y deja todo anotado en `datos/actualizacion.log`.

Son 2 días y no 1 a propósito: si una noche falla la corrida o la computadora
estaba apagada, al día siguiente se recupera lo perdido.

Para que corra solo:

```bash
crontab -e          # abre un editor (vim). Se pulsa i para escribir.
```

Se pega esta línea **dentro del editor**, no en la terminal:

```
0 0 * * * cd ~/Desktop/cero-vagos && ./actualizar.sh
```

Y se guarda con `Esc`, luego `:wq` y Enter. Para confirmar que quedó:
`crontab -l`.

La computadora tiene que estar encendida a esa hora. Cuando el sitio salga a
producción, esto se muda al servidor y el problema desaparece.

Otros comandos:

```bash
python3 -m motor diagnostico                    # revisar si cada fuente se puede leer
python3 -m motor probar-url "https://..."       # leer UNA oferta y ver si pasaría el filtro
python3 -m motor stats                          # cómo va la base
python3 -m motor rechazos                       # qué se botó y por qué
python3 -m motor probar "S/ 2,800 a S/ 3,400"   # probar el parser de sueldos
python3 -m unittest discover pruebas -v         # tests (408)
```

Si el proyecto vive en una carpeta sincronizada (iCloud, Drive, Dropbox),
SQLite puede fallar al tomar bloqueos. Mueve la base:

```bash
export CEROVAGOS_DB=~/cerovagos.db
```

## El filtro

Todo aviso se puntúa de 0 a 100. Se publica solo si llega a **70** y además
pasa los eliminatorios.

| Bloque | Puntos | Eliminatorio |
|---|---|---|
| Sueldo mensual detectado | 30 | sí — sin monto, se bota |
| Qué vas a hacer | 25 | sí — mínimo según el perfil |
| Qué piden | 20 | sí — mínimo 3 requisitos |
| Qué te dan | 15 | sí — mínimo 2 beneficios concretos |
| Empresa, ciudad, modalidad, frescura | 10 | vencido o de más de 30 días, se bota |

### Dos varas: público y privado

El Estado y las empresas no publican igual, así que no se les puede exigir
igual (`PERFILES` en `motor/score.py`):

| | Funciones mínimas | Plazo cerrado | Por qué |
|---|---|---|---|
| **privado** | 3 | rechaza | La empresa escribe el aviso completo y pone la fecha. No hay excusa. |
| **público** | 1 | no decide | Las funciones suelen quedar en el PDF de las bases, y la fecha de cierre muchas veces ni se publica. |

Con cero funciones no pasa ninguno de los dos. Si no dice nada de lo que vas a
hacer, no es una oferta.

### Las fechas

Una oferta cerrada no sirve. La regla tiene dos ramas:

- **Si el aviso dice hasta cuándo postular** y esa fecha ya pasó, se bota. Sin
  matices: mostrarla es hacer perder el tiempo.
- **Si no lo dice**, manda la antigüedad. Una convocatoria CAS dura entre 5 y 15
  días, así que a las tres semanas está cerrada aunque nadie lo escriba
  (`dias_sin_cierre`: 21 en el sector público, 45 en el privado).

Encima de las dos, un tope absoluto: **más de 60 días publicada y sale de la
web**, siga abierta o no.

Se aplica en tres momentos: al recolectar (para no gastar tiempo abriendo el PDF
de un aviso cerrado), al puntuar, y como limpieza de la base en cada corrida.

El sitio muestra el plazo en cada tarjeta —"Cierra en 6 días", en rojo si quedan
3 o menos— y dice explícitamente cuando el aviso no trae fecha de cierre.

Cuidado con dos fechas que parecen la misma y no lo son:

- El **`lastmod` del sitemap** dice cuándo el portal tocó esa página. No es
  cuándo se publicó el aviso. Filtrar el descubrimiento con esa fecha deja la
  corrida en cero (`dias_ventana`, va holgado).
- La **fecha de publicación** se lee de la página del aviso. Esa es la que
  decide (`dias_publicado`, la que cambia `--dias`).

Cuando las URLs traen correlativo, el motor las ordena por ahí y corta la
búsqueda apenas encuentra 25 avisos viejos seguidos: si el correlativo baja,
las fechas también.

Cuando el plazo cerró y aun así se publica, el dato no se esconde: queda
registrado en las notas de la oferta para poder mostrarlo en el sitio.

### El sueldo no se negocia

Un aviso sin monto no se publica, venga de donde venga. Sin excepciones por
"empresa verificada" ni etiquetas que lo suavicen.

No existe una opción para desactivar esta regla, y es a propósito: una regla que
se apaga con una línea termina apagada. Está fijada además con un test
(`test_el_sueldo_sigue_siendo_eliminatorio_en_ambos`), así que si alguien la
toca, las pruebas avisan.

El parser de sueldos (`motor/sueldo.py`) entiende `S/ 3,500`,
`S/ 2,800 a S/ 3,400`, `entre 4000 y 5500 soles`, `US$ 1,200`,
`S/ 54,000 anuales` (lo pasa a mensual) y la RMV. Ignora números que están
cerca de frases como *a convenir*, *acorde al mercado* o *según experiencia*,
y descarta montos fuera de rango razonable. **Ante la duda, devuelve nada**:
es preferible perder un aviso que publicar un sueldo inventado.

Los beneficios solo cuentan si mencionan algo concreto (planilla, EPS, bono,
CTS, movilidad, EPS, home office...). "Excelente ambiente laboral" no es un
beneficio.

## Cómo se recolecta

`motor/fuentes/`:

- **`robots.py`** — parser de robots.txt propio. Se escribió a mano porque
  `urllib.robotparser` ignora los comodines: para él `Disallow: /empleos/x/*`
  no bloquea nada, y hoy casi todos los portales escriben así sus reglas.
  Sigue la especificación de Google (gana el match más largo, empate a favor
  de Allow) y respeta el `Crawl-delay` de cada dominio.
- **`sitemap.py`** — descubre avisos desde el sitemap del portal, con soporte
  para índices, `.gz` y filtro por `lastmod`. Es más limpio que paginar
  resultados de búsqueda: el portal mismo declara sus URLs y cuándo cambiaron.
- **`jsonld.py`** — extrae el bloque `schema.org/JobPosting` que los portales
  publican porque Google Jobs se los exige. Mucho más estable que raspar HTML.
- **`render.py`** — Playwright opcional, para los portales que son SPA.
- **`portal_web.py`** — junta todo lo anterior y trae la configuración de los
  portales.
- **`demo.py`** — avisos de ejemplo para correr sin internet.

Deduplicación: el mismo aviso publicado en Computrabajo, Bumeran y LinkedIn
colapsa en uno solo mediante una huella de `puesto + empresa + ciudad`
normalizada (sin tildes, sin palabras de relleno como "urgente").

## Estado de las fuentes

Verificado el **2 de agosto de 2026**. Vuelve a correr `python3 -m motor
diagnostico` cada cierto tiempo: los portales cambian de arquitectura sin avisar.

| Portal | robots.txt | Descubrimiento | Lectura del aviso |
|---|---|---|---|
| **Convocatorias CAS** | ✅ Sin restricciones (solo trae las *content signals* de Cloudflare) | ✅ `sitemap.xml`, ~170 convocatorias con `lastmod` real | ✅ HTML server-side. Sueldo etiquetado y plazo de postulación declarado. **Solo se publican las de una plaza** |
| **Convocatorias del Estado** | ✅ Permite `/`, bloquea `/api/`, `/admin/` | ✅ `sitemap.xml` | ✅ HTML server-side, sin navegador. **Sueldo siempre presente**. Resultó ser un archivo: 413 de sus 512 direcciones ya cerraron |
| **Bumeran** | Permite `/empleos/*`; bloquea `/empleos/aptitus/*` y filtros de query | ✅ `sitemap_avisos_bum.xml` con `lastmod` | ⚠️ SPA en React: por HTTP llega *"You need to enable JavaScript"*. Necesita Playwright |
| **Laborum** | Permite todo salvo rutas de cuenta | ✅ índice en `/api/v1/sitemaps/index` | ⚠️ SPA, igual que Bumeran |
| **Computrabajo** | ❌ Responde vacío detrás de un WAF | — | Bloqueado. El motor lo salta solo |

### Una página, varios puestos: por qué se dejan pasar convocatorias

`convocatoriascas.com` tiene un problema de forma: **una misma dirección puede
traer varios puestos con sueldos distintos.** La Municipalidad de Surquillo
lista 6 plazas en 2 puestos, a S/ 1,350 y S/ 2,800; la de Arequipa dice 283
plazas. El motor asume una dirección, un aviso.

Se eligió la opción más conservadora (Mentita, 5/8/2026): **publicar solo las
convocatorias de UNA plaza.** No toca la pieza central del motor, y lo que no se
puede partir bien no se publica. Publicar uno de los dos puestos sería elegir
por el postulante; publicar los dos bajo una sola dirección sería mentir sobre
el sueldo.

Filtrar sale gratis porque el número de plazas viene en la propia dirección
(`…-1-plazas-67463.html`), así que las de varias plazas ni se descargan. Pero
**se cuentan**, y el número sale en el resumen de la corrida: sin eso, la fuente
se vería sana entregando la mitad de lo que hay. Si ese número crece mucho, toca
volver a mirar la decisión.

Las otras dos opciones quedaron descartadas por ahora, no por malas: que el
motor acepte varias ofertas por dirección (toca la pieza por la que pasa todo,
incluidas Bumeran y Laborum) o entrar a la página de cada puesto (más lento y
más frágil).

### Cuánto pesa el PDF de las bases

Vale tenerlo escrito porque es contraintuitivo. Una convocatoria CAS típica,
leída **solo de la página**, saca **69 sobre 100**. El umbral es 70: no se
publica por un punto.

No es un error de cálculo. Al Estado no se le exige la lista de funciones, pero
los 25 puntos de ese bloque **se pierden enteros**, y el aviso tiene que
compensarlos en todo lo demás. Con un sueldo de monto único (27 de 30) y tres
requisitos (17 de 20), no llega.

Con las funciones sacadas del PDF de las bases, el mismo aviso pasa de 69 a más
de 90. O sea: **esta fuente depende de que se pueda leer el PDF.** Si un día
entrega cero, lo primero que hay que revisar no es el lector, es si
`pdfplumber` está instalado y si las entidades siguen dejando bajar sus bases.
Lo vigila `pruebas/test_cas.py`.

### Por qué las convocatorias del Estado van primero

En el sector público la remuneración mensual es parte obligatoria del aviso, así
que casi ninguno muere en el primer filtro. Los requisitos vienen desglosados
(formación, experiencia general y específica, cursos). Y los beneficios no se
listan porque los fija la ley según el régimen: el motor los completa con lo que
la norma garantiza —EsSalud, 30 días de vacaciones, aguinaldos, afiliación
pensionaria— y lo deja marcado como beneficio de ley. No es invento: es el marco
legal del contrato (`BENEFICIOS_POR_REGIMEN` en `motor/fuentes/publicas.py`).

### El PDF que nadie abre

Lo que no aparece en la página son las **funciones**. Y no es que estén mal
escritas: no están. El Estado las publica dentro del PDF de las bases del
concurso, enlazado al pie del aviso. Por eso los agregadores muestran
"funciones no especificadas" y por eso ningún portal peruano te dice qué vas a
hacer en un puesto público.

Cero Vagos abre ese PDF (`motor/bases_pdf.py`). El recolector detecta el enlace
de las bases —priorizando "Base del Concurso" sobre cronogramas y anexos—,
descarga el archivo respetando el robots.txt de la entidad, busca la sección
"FUNCIONES DEL PUESTO" y reconstruye los ítems, uniendo las líneas que el ancho
de la hoja partió en dos.

Con eso, una convocatoria que se rechazaba pasa a aprobarse. Es el paso que
convierte al proyecto en algo que no existe hoy en el mercado peruano.

No funciona siempre: hay entidades que escanean las bases como imagen y otras
que las estructuran distinto. Cuando el PDF no se deja leer, **el aviso se
rechaza igual**. Nunca se inventa una función.

Los PDFs se guardan en `datos/pdfs/` para no volver a descargarlos.

```bash
python3 -m motor recolectar --publicas --sin-pdf   # más rápido, menos completo
python3 -m motor recolectar --publicas --dias 2    # solo lo de los últimos 2 días
```

Una nota de prudencia: la fuente configurada agrega información que ya es
pública del Estado y su robots.txt permite la lectura, pero conviene revisar sus
términos de uso y, mejor todavía, escribirles. Sale más barato un acuerdo que un
bloqueo. Cada oferta enlaza siempre al anuncio oficial de la entidad.

Lo que esto significa para el negocio:

1. **Los sitemaps sí se leen por HTTP simple.** Descubrir avisos frescos es
   barato; lo caro es abrir cada aviso.
2. **Los portales grandes exigen un navegador headless.** Presupuesta
   Playwright y tiempo de CPU, no solo `requests`.
3. **Computrabajo no se raspa.** Su WAF ya lo dice. El camino es un acuerdo de
   sindicación, o vivir sin él.
4. **Arranca por lo público.** Convocatorias del Estado, bolsas universitarias
   y webs de empresa son HTML plano, sin fricción legal, y sus avisos suelen
   traer el sueldo explícito — justo lo que el filtro necesita.

```bash
python3 -m motor diagnostico --todas     # revisa cada portal antes de activarlo
python3 -m motor recolectar --recomendadas --exportar
```

## Ofertas exclusivas de bolsas aliadas

Una oferta puede llegar con el campo `exclusiva`:

```js
exclusiva: { universidad: "la Universidad Privada del Norte",
             siglas: "UPN",
             url: "https://empleabilidad.upn.edu.pe/" }
```

Cuando está presente, la tarjeta se muestra distinta: puesto y empresa visibles,
el resto difuminado, sello de la universidad y un botón que lleva a su portal.
El detalle no se publica porque no es nuestro.

Esto existe para poder trabajar **con** las bolsas universitarias en vez de
raspar lo que tienen detrás de un login. Ver `PROPUESTA-UNIVERSIDADES.md`.

## Bolsas de trabajo de las empresas

Sale de la web oficial: sin intermediario, sin consultora que esconda para quién
es el puesto, sin avisos colgados seis meses.

El detalle que cambia la estrategia: **las empresas grandes no programan su
bolsa de trabajo**, contratan un sistema de reclutamiento (un ATS). En el Perú
los que más se ven son Workday, SAP SuccessFactors, Greenhouse, Lever y Avature.
Entonces no se escribe un lector por empresa —que se rompe cada vez que
rediseñan la web— sino uno por ATS: cinco lectores cubren cientos de empresas.

Ya están escritos los de **Greenhouse** y **Lever** (API pública, JSON limpio).
Para los demás se usa el JSON-LD que publican para Google Jobs.

Antes de escribir una línea de código para una empresa nueva:

```bash
python3 -m motor conectar "https://www.empresa.com.pe/trabaja-con-nosotros"
```

Ese comando revisa el robots.txt, detecta qué ATS usa y te dice exactamente qué
lector agregar (`motor/fuentes/empresas.py`). Rubros que valen la pena por
volumen y por sueldos publicados: banca y seguros, retail y consumo masivo,
minería, agroexportación, telecom y tecnología.

```bash
python3 -m motor recolectar --empresas --exportar
```

### Reglas de la casa

1. Si no se puede leer el `robots.txt`, se asume que **no** hay permiso.
2. Se prefiere feed o sitemap oficial antes que raspar páginas.
3. El bot va identificado (`CeroVagosBot`) y respeta el `Crawl-delay`.
4. Siempre se enlaza al aviso original: no reemplazamos al portal, lo ordenamos.

## Siguientes pasos sugeridos

1. Configurar y validar cada portal real en `portales_peru()`.
2. Programar la corrida cada 6 horas (cron o GitHub Actions).
3. Pasar el sitio a Next.js + Postgres cuando el volumen lo pida.
4. Alertas por WhatsApp con la API de Meta.
5. Detectar avisos caídos (404) para bajarlos antes de los 30 días.
