# Poner Cero Vagos en piloto automático

Para que la recolección corra sola cada madrugada y el sitio se actualice sin
que tengas que prender la laptop ni tocar la terminal.

Se usa **GitHub**, que es gratis para esto. Dos cosas al mismo tiempo:

- **GitHub Actions** ejecuta el motor cada día en sus servidores.
- **GitHub Pages** publica tu web con una dirección propia.

Tiempo: unos 20 minutos la primera vez. Después, nunca más.

---

## 1. Crear la cuenta y el repositorio

1. Entra a [github.com](https://github.com) y crea una cuenta si no tienes.
2. Arriba a la derecha, **+** → **New repository**.
3. Nombre: `cero-vagos`.
4. Elige **Public**. Importante: en repositorios públicos las corridas
   automáticas son ilimitadas y gratis; en privados hay un tope mensual.
5. **Create repository**.

## 2. Subir el proyecto

En la página del repositorio recién creado, clic en **uploading an existing
file**. Arrastra ahí **todo el contenido** de la carpeta `cero-vagos`.

Un detalle que se escapa: la carpeta `.github` empieza con punto y el Finder de
Mac la esconde. Para verla, en el Finder pulsa **Cmd + Shift + .** (punto).
Tiene que subir, porque ahí vive la automatización.

Abajo, **Commit changes**.

## 3. Darle permiso de escritura al robot

**Esto es lo primero, y es lo que más se olvida.** Si no lo haces, la corrida
revisa los 1,200 avisos, tarda su hora larga, y falla en el último paso al
intentar guardar. Verás un error rojo que dice `403` o *permission denied*.

1. Pestaña **Settings** del repositorio.
2. Menú izquierdo: **Actions** → **General**.
3. Baja hasta **Workflow permissions**.
4. Marca **Read and write permissions**.
5. **Save**.

GitHub deja esto en solo lectura por defecto. El robot necesita escribir para
guardar las ofertas que recolectó.

## 4. Encender la automatización

1. Pestaña **Actions** del repositorio.
2. Si aparece un aviso pidiendo permiso, clic en **I understand my workflows,
   go ahead and enable them**.
3. En la lista de la izquierda verás **Recolección diaria**.
4. Para probarla ahora mismo: **Run workflow** → **Run workflow**.

Va a tardar un rato. Puedes cerrar la pestaña y volver después; corre en los
servidores de GitHub, no en tu Mac. Al terminar, un check verde.

Desde ahí en adelante corre sola a la **medianoche hora de Perú**.

## 5. Publicar la web

1. Pestaña **Settings** → menú izquierdo, **Pages**.
2. En *Source*, elige **Deploy from a branch**.
3. Branch: **main**, carpeta: **/ (root)**. **Save**.

En un par de minutos tu web estará en:

```
https://TU-USUARIO.github.io/cero-vagos/
```

Esa dirección ya se puede compartir. Cuando compres un dominio propio
(cerovagos.com), se conecta desde esa misma pantalla.

---

## Cómo saber que está funcionando

**Pestaña Actions.** Cada corrida aparece con su fecha. Verde salió bien, rojo
falló. Entrando a cualquiera ves exactamente lo mismo que veías en tu terminal:
las ofertas aprobadas, las rechazadas y por qué.

**Pestaña Code.** Si hubo ofertas nuevas, verás un commit reciente que dice
"Ofertas del 04/08/2026".

## Correrla cuando quieras

Actions → **Recolección diaria** → **Run workflow**. Ahí puedes cambiar dos
cosas para esa corrida:

- **Avisos por portal**: cuántos revisar. 120 por defecto; súbelo si quieres
  una pasada más grande. Ojo: la corrida tiene 150 minutos de tope y una
  pasada completa de 1,200 avisos tardó más de tres horas.
- **Días**: solo avisos publicados en los últimos N días. 3 por defecto, que es
  lo lógico para una corrida diaria. Pon 0 para revisar todo lo de los últimos
  dos meses.

## Cosas que conviene saber

**Se apaga sola si abandonas el repositorio.** GitHub desactiva las tareas
programadas cuando un repositorio público pasa 60 días sin ningún movimiento.
Basta con entrar y lanzar una corrida a mano para reactivarla.

**Puede atrasarse.** Si los servidores están cargados, la corrida de medianoche
puede arrancar 20 o 30 minutos después. Para una bolsa de trabajo da igual.

**Un portal caído no tumba el resto.** Si Bumeran no responde, la corrida sigue
con los demás y guarda lo que consiguió.

**Tu laptop queda libre.** Los comandos locales siguen funcionando igual si
quieres probar algo, pero ya no son necesarios para el día a día.

## La trampa: quién manda a partir de ahora

Esta es la única forma real de perder trabajo, y conviene entenderla antes de
encender nada.

Hasta hoy tu carpeta era la verdad y GitHub la copia. **Desde que la corrida
automática arranca, se invierte:** cada madrugada el bot recolecta ofertas
nuevas, regenera las páginas y las guarda en GitHub. Tu carpeta se queda
congelada en donde la dejaste.

Si al día siguiente subes tu copia de `datos/`, `oferta/`, `sitemap.xml` o
`index.html` por el navegador, **borras lo que el bot recolectó esa noche**. Y
como la base de datos también se pisa, el motor olvida qué avisos ya había
revisado y vuelve a descargarlos todos.

La regla, en corto:

| Carpeta | Quién manda |
|---|---|
| `datos/`, `oferta/`, `sitemap.xml` | **El bot.** No las subas nunca a mano. |
| `index.html`, `motor/`, `assets/`, los `.md` | **Tú.** El bot no las inventa. |

Si alguna vez necesitas volver a trabajar sobre lo que hay en GitHub, primero
**descarga el repositorio** (botón verde *Code* → *Download ZIP*) y reemplaza
tu carpeta con eso. Nunca al revés.

## Y si prefieres no usar GitHub

La alternativa es alquilar un servidor pequeño (unos 5 dólares al mes en
DigitalOcean o Hetzner) y programar ahí el `actualizar.sh` con cron. Es más
control y más trabajo. Para el tamaño actual del proyecto, GitHub Actions sobra
y no cuesta nada.
