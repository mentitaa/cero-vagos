# Las alertas por WhatsApp

**Ya están activas.** Los registros llegan a `cerovagos.alertas@gmail.com` y
quedan guardados en el panel de Formspree.

La dirección que los recibe está en `index.html`, en una sola línea:

```js
const ALERTAS_ENDPOINT = 'https://formspree.io/f/xrpzzoln';
```

---

## Cómo se conectó (por si hay que rehacerlo)

1. Entra a **formspree.io** y crea una cuenta gratis con tu correo.
2. Dale a **+ New form**. Ponle de nombre `Alertas Cero Vagos`.
3. Te va a mostrar una dirección así:

   ```
   https://formspree.io/f/xdkovbqz
   ```

   Cópiala. Esas ocho letras del final son tuyas y de nadie más.

4. Abre `index.html` y busca esta línea (está sola, es la única en todo el
   archivo):

   ```js
   const ALERTAS_ENDPOINT = '';
   ```

5. Pega tu dirección entre las comillas:

   ```js
   const ALERTAS_ENDPOINT = 'https://formspree.io/f/xdkovbqz';
   ```

6. Sube el `index.html` a GitHub. Listo.

Formspree te manda un correo por cada persona que se registre, y además los
guarda todos en su panel para que los descargues cuando quieras.

**El plan gratis aguanta 50 registros al mes.** Para empezar sobra. Si algún
día se llena, ahí recién toca pensar en otra cosa.

---

## Cómo está protegido

Dos cosas, las dos en el panel de Formspree:

**Restricción de dominio** (ajustes del *proyecto*, no del formulario):
`mentitaa.github.io`. Solo se aceptan envíos que salgan de esa web. Sin esto,
cualquiera podía mandar datos directo a la dirección de Formspree saltándose
el sitio y agotar los 50 registros del mes en un rato.

Ojo con dos trampas de esta opción:

- **Si pusieras solo `github.io`**, cualquier web de GitHub Pages del mundo
  podría enviarte datos. Tiene que ir el subdominio completo.
- **El día que se conecte `cerovagos.com` hay que agregarlo ahí.** Si no, los
  registros que lleguen del dominio nuevo se van todos a spam **sin avisar**.
  Está anotado también en `DOMINIO.md`.

**Formshield**, el filtro antispam de Formspree: encendido.

El CAPTCHA queda **apagado a propósito**. Existe y es gratis, pero este
formulario envía los datos por detrás sin recargar la página, y cuando el
CAPTCHA se activa Formspree espera mandar a la persona a otra pantalla. Eso
puede chocar y fallar en silencio. Si algún día llega spam de verdad, se
enciende y se adapta el código para que convivan.

---

## Y después, ¿cómo mando las alertas?

A mano, y eso está bien.

Con los primeros veinte o treinta registrados, mandar los WhatsApps tú misma
no es una tarea pesada — es la mejor fuente de información que vas a tener.
Vas a descubrir qué buscan de verdad, qué ofertas les sirven y cuáles no, y
por qué dejan de responder. Eso no sale de ningún panel de estadísticas.

Automatizarlo antes de saber eso es construir a ciegas. Cuando la lista pase
de cien y ya sepas qué mandar, hablamos de automatizarlo.

---

## Lo que hace el formulario por dentro

Para que sepas qué estás publicando:

- **Valida el celular.** Nueve dígitos y empieza con 9, como todos los
  celulares peruanos. Sin eso entra cualquier cosa.
- **Pide consentimiento explícito.** Una casilla que hay que marcar, con
  enlace a la política de privacidad. Lo exige la Ley 29733, y es lo correcto
  aunque no lo exigiera.
- **Tiene una trampa para robots.** Un campo invisible que una persona nunca
  ve. Si viene lleno, el envío se descarta sin decir nada — avisarle al robot
  que lo detectaste solo le enseña a evitarlo la próxima vez.
- **No miente si falla.** Si el envío no sale, lo dice y deja reintentar. No
  hay ningún camino donde el botón diga "¡Listo!" sin que el dato haya salido.

Todo esto está fijado con pruebas en `pruebas/test_alertas.py`.

---

## Si algún día quieres borrar a alguien

La política de privacidad promete que cualquiera puede pedir que borres su
número. Cuando pase, entra al panel de Formspree, busca el registro y bórralo.
No hay más ciencia, pero tienes que cumplirlo: es lo que firmaste al publicar
esa página.
