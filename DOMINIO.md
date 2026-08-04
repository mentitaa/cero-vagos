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

### 1. Comprar el dominio

Donde prefieras (Namecheap, GoDaddy, Cloudflare). `.com` cuesta entre 40 y 60
soles al año.

### 2. Apuntar el dominio a GitHub

En el panel de tu proveedor, sección **DNS**, agrega estos registros:

| Tipo | Nombre | Valor |
|---|---|---|
| A | @ | 185.199.108.153 |
| A | @ | 185.199.109.153 |
| A | @ | 185.199.110.153 |
| A | @ | 185.199.111.153 |
| CNAME | www | mentitaa.github.io |

Los cuatro registros A son de GitHub y son siempre los mismos.

### 3. Conectarlo en GitHub

1. Tu repositorio → **Settings** → **Pages**
2. En *Custom domain*, escribe `cerovagos.com` → **Save**
3. GitHub crea solo el archivo `CNAME` en el repositorio
4. Espera a que verifique el DNS (de minutos a un par de horas)
5. Marca **Enforce HTTPS** cuando se habilite la casilla

### 4. Regenerar el sitio

No hace falta esperar: entra a **Actions** → **Recolección diaria** →
**Run workflow**. Al terminar, todo el sitio está con el dominio nuevo.

Si prefieres hacerlo desde tu Mac:

```bash
python3 -m motor publicar     # lee el CNAME solo
```

---

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

Aprovecha y cambia también el correo de contacto: hoy las páginas legales dan
`cerovagos.alertas@gmail.com`. Cuando tengas `contacto@cerovagos.com`, se
cambia en `motor/legales.py` (constante `CORREO`) y en el pie de `index.html`,
y el motor lo reescribe en todas las páginas de una.

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
