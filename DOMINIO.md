# Conectar el dominio cerovagos.com

Cuando compres el dominio, esto es todo lo que hay que hacer. El sitio se
reescribe solo con la dirección nueva: no hay que tocar código ni pedirle nada
a nadie.

---

## Por qué no hay trabajo técnico

El generador no lleva la dirección escrita a mano. La averigua sola, en este
orden:

1. La variable de entorno `CERO_VAGOS_SITIO`, si existe.
2. **El archivo `CNAME`**, que GitHub crea automáticamente al conectar un
   dominio propio.
3. Si no hay ninguno, la dirección de `github.io`.

Entonces basta con conectar el dominio en GitHub: el archivo aparece solo y en
la siguiente corrida todas las páginas, el sitemap, los enlaces y las etiquetas
canónicas salen con `cerovagos.com`.

## Los pasos

El dominio está comprado en **Squarespace** y el correo `info@cerovagos.com`
funciona con **Google Workspace**. Esas dos cosas cambian el orden y añaden un
cuidado que no aparece en las guías genéricas.

### ⚠️ Antes de tocar nada: no borres los registros del correo

Tu dominio tiene dos trabajos a la vez: **apuntar a la web** y **recibir el
correo**. Los dos viven en la misma pantalla de DNS.

Los registros del correo son los de tipo **MX**, y también unos **TXT** que
Google usa para verificar que el dominio es tuyo. **No los toques.** Si los
borras, `info@cerovagos.com` deja de recibir mensajes y no te enteras hasta que
alguien te reclame que te escribió y nunca respondiste.

Solo vas a agregar registros nuevos y a borrar los que Squarespace puso para
su propia página de "sitio en construcción".

### 1. Reservar el dominio en GitHub (esto va primero)

GitHub pide hacerlo en este orden por seguridad: si apuntas el DNS antes de
reclamar el dominio, hay una ventana en la que otra persona podría publicar su
web en tu dirección.

1. Tu repositorio → **Settings** → menú izquierdo **Pages**
2. En *Custom domain*, escribe `cerovagos.com` → **Save**
3. GitHub crea solo un archivo llamado `CNAME` en el repositorio. **Ese
   archivo es el que hace que todo el sitio se mude solo**: el motor lo lee y
   reescribe las páginas, el sitemap y los enlaces con la dirección nueva.

Va a aparecer un aviso rojo de que el DNS no está configurado. Es normal:
todavía no lo has hecho.

### 2. Los registros en Squarespace

En Squarespace: **Settings** → **Domains** → `cerovagos.com` → **DNS Settings**
(o *DNS*, según la versión).

**Primero borra** los registros de tipo `A` y `CNAME` que apunten a
Squarespace. Suelen ser un `A` con nombre `@` y un `CNAME` con nombre `www`.
GitHub lo pide explícitamente: si queda el registro por defecto del proveedor,
el sitio no carga.

**Después agrega** estos cinco:

| Tipo | Nombre | Valor |
|---|---|---|
| A | @ | `185.199.108.153` |
| A | @ | `185.199.109.153` |
| A | @ | `185.199.110.153` |
| A | @ | `185.199.111.153` |
| CNAME | www | `mentitaa.github.io` |

Las cuatro direcciones son de GitHub y son siempre las mismas. Ese `CNAME` del
`www` es lo que hace que `www.cerovagos.com` lleve al mismo sitio en vez de dar
error.

Ojo: el valor del CNAME es `mentitaa.github.io`, **sin** `/cero-vagos` al
final. Es el error más común.

### 3. Esperar

El cambio tarda de unos minutos a 24 horas en llegar a todo internet. No hay
nada que hacer mientras tanto.

Cuando `cerovagos.com` empiece a mostrar tu web, vuelve a **Settings → Pages**
y marca la casilla **Enforce HTTPS**. Puede tardar hasta un día en habilitarse.
Sin eso, el candado del navegador no aparece y Chrome avisa que el sitio no es
seguro.

### 4. Regenerar el sitio con la dirección nueva

Sube los cambios de código que están pendientes (`index.html`, `motor/`, los
`.md` y los dos archivos de `.github/workflows/`). Eso dispara solo el
workflow **Publicar el sitio**, que tarda menos de un minuto y reescribe todo
con el dominio nuevo.

Si quieres lanzarlo a mano: **Actions** → **Publicar el sitio** →
**Run workflow**. No hace falta volver a recolectar.

## No te olvides de Formspree

**Esto es lo único del cambio de dominio que no se arregla solo, y falla en
silencio.**

El formulario de alertas está restringido a `mentitaa.github.io`: Formspree
solo acepta envíos que salgan de esa dirección. En cuanto el sitio empiece a
responder en `cerovagos.com`, los registros van a llegar desde el dominio
nuevo, Formspree no lo va a reconocer y **los va a mandar todos a spam sin
avisarte**. La web seguirá diciendo "¡Listo! Te avisamos".

Antes de conectar el dominio, o el mismo día:

1. Entra a Formspree → tu **proyecto** (no el formulario) → **Settings**.
2. En **Restrict to Domain**, cambia `mentitaa.github.io` por `cerovagos.com`.
3. Prueba el formulario desde el dominio nuevo y confirma que llega el correo.

Detalle completo en `ALERTAS.md`.

El correo del proyecto ya es `info@cerovagos.com` (Google Workspace) y está
puesto en `motor/legales.py` (constante `CORREO`), en el pie de `index.html`,
en la firma del bot de GitHub Actions y en cómo el bot se presenta ante los
portales (`motor/fuentes/base.py`, `USER_AGENT`).

---

## Lo que pasa con lo ya indexado

Nada se pierde. GitHub redirige automáticamente las direcciones viejas de
`mentitaa.github.io/cero-vagos/...` al dominio nuevo, y Google traslada solo el
posicionamiento que hayas ganado.

Aun así, después de mudarte:

1. Entra a **Google Search Console** y registra `cerovagos.com` como una
   propiedad nueva.
2. Envía el `sitemap.xml` otra vez, ahora con el dominio nuevo.

## Un consejo sobre cuándo comprarlo

Cómpralo pronto aunque no lo conectes todavía. Un dominio con más meses de
antigüedad transmite algo más de confianza a los buscadores, cuesta poco, y
evita que alguien lo tome si el nombre empieza a sonar.
