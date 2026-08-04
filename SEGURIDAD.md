# Auditoría de seguridad

Revisión hecha el **4 de agosto de 2026** sobre todo el código publicado:
`index.html`, el motor, las páginas generadas y los dos workflows de GitHub.

Va escrito para que se entienda sin saber programar, porque el punto es que
puedas decidir qué arreglar y responder si alguien pregunta.

---

## Resumen

Cero Vagos es un sitio **estático**: archivos que se sirven tal cual, sin
servidor propio ni base de datos en línea. Eso elimina de un plumazo la mayoría
de las formas en que se hackea una web. No hay dónde entrar.

Se encontró **un hueco real** (ya arreglado en su momento) y **un riesgo
práctico**, que quedó cerrado el mismo día restringiendo el dominio en
Formspree. No queda nada abierto.

| | Estado |
|---|---|
| Código inyectado en las ofertas (XSS) | Arreglado |
| Falta de política de contenido | Arreglado en esta revisión |
| Abuso del formulario de alertas | Cerrado el 4/8/2026 |
| Robo de la pestaña al salir a otro portal | Correcto de antes |
| Inyección en la base de datos | No aplica |
| Claves o contraseñas expuestas | Ninguna |
| Caída por sobrecarga (DDoS) | Cubierto por GitHub |

---

## Lo que se revisó, uno por uno

### 1. Código inyectado a través de una oferta — **arreglado**

**El riesgo.** Los avisos los escriben terceros y nosotros los mostramos. Si
alguien publicaba en Bumeran un aviso cuyo título fuera código en vez de texto,
ese código se ejecutaba en el navegador de quien visitara Cero Vagos. Desde ahí
se puede redirigir a la gente a una web falsa o robarle lo que escriba.

**Qué se hizo.** Todo dato que viene de fuera pasa por una función que
convierte los caracteres peligrosos en texto inofensivo antes de mostrarlo. Y
las direcciones a las que enlazamos pasan por otra que solo acepta las que
empiezan por `http://` o `https://`.

Se probaron los engaños habituales contra esa segunda función —
`javascript:`, `JaVaScRiPt:` con mayúsculas mezcladas, con un espacio delante,
direcciones `data:` con código dentro. Los bloqueó todos.

### 2. Política de contenido — **arreglado en esta revisión**

**El riesgo.** No existía. Una política de contenido es la lista de los únicos
sitios de los que la página tiene permiso de cargar algo. Sin ella, si alguna
vez se cuela código, ese código puede traer lo que quiera de donde quiera y
mandar a donde quiera.

**Qué se hizo.** Ahora cada página declara su lista blanca. La portada solo
puede: cargarse a sí misma, la letra de Google, y hablar con Formspree para las
alertas. Nada más. Las páginas de oferta ni siquiera pueden mandar formularios.

Es una segunda muralla: aunque el punto 1 fallara algún día, el navegador se
niega a colaborar.

**Ojo al agregar cosas.** Si más adelante se pone un contador de visitas o
cualquier servicio externo, hay que sumarlo a esa lista o simplemente no
funcionará. Las pruebas en `pruebas/test_seguridad.py` avisan si algo que la
web usa quedó bloqueado por error — que es el modo silencioso en que esto
suele salir mal.

### 3. Abuso del formulario de alertas — **cerrado**

**Era el punto más probable de todos.**

El plan gratuito de Formspree aguanta **50 registros al mes**. El formulario
tiene una trampa que descarta robots, pero esa trampa vive en la página: nada
impide que alguien mande datos directamente a la dirección de Formspree
saltándose la web entera. Con un rato de aburrimiento, cualquiera agota tu
cuota del mes.

**Lo malo no es el gasto, es el silencio.** Una vez llena la cuota, los
registros de gente real dejan de llegar y la web sigue diciendo "¡Listo! Te
avisamos". Nadie se entera.

**Qué se hizo** (en el panel de Formspree, ajustes del *proyecto*):

1. **Restricción de dominio a `mentitaa.github.io`.** Los envíos que no salgan
   de esa web se marcan como spam. Es lo que corta el ataque.
2. **Formshield encendido**, el filtro antispam incluido.

Ninguna de las dos se puede hacer desde el código: son ajustes de la cuenta.
El detalle y las trampas de esta opción están en `ALERTAS.md`.

### 4. Enlaces a otros portales — **correcto**

Cuando alguien hace clic en "Postular en Bumeran" se abre una pestaña nueva.
Sin una precaución concreta (`rel="noopener"`), la página que se abre puede
cambiar la pestaña de Cero Vagos por una copia falsa mientras la persona está
distraída. Como enlazamos a sitios que no controlamos, esto importa.

Ya estaba puesto en todos los enlaces. Hay una prueba que lo vigila.

### 5. La base de datos — **no aplica**

La base vive en el repositorio y **nunca se expone a internet**: nadie puede
hacerle preguntas desde fuera. Aun así se revisó cómo se le habla desde el
motor, y todas las consultas usan la forma correcta, que separa la instrucción
de los datos. No hay ninguna armada pegando texto.

### 6. Claves y contraseñas — **ninguna expuesta**

Se buscaron claves, contraseñas y llaves de servicios en todo el repositorio.
No hay ninguna, porque el proyecto no usa ninguna.

La dirección de Formspree que está en `index.html` **no es un secreto**: es un
buzón público, como una dirección de correo. Cualquiera que vea tu web la
puede leer, y así es como funciona. Lo que la protege es el punto 3.

### 7. Los workflows de GitHub — **correcto**

El robot que corre cada madrugada tiene permiso para escribir en el
repositorio y nada más. Solo usa herramientas oficiales de GitHub. No maneja
ninguna clave.

### 8. Caída por sobrecarga (DDoS) — **cubierto**

El sitio lo sirve GitHub, que reparte el contenido desde su propia red y
absorbe ataques de este tipo mucho mejor de lo que podría cualquier servidor
que alquilaras. No hay nada que puedas hacer mejor por tu cuenta.

Lo único a tener en mente: GitHub Pages tiene un límite blando de 100 GB de
tráfico al mes. Para un sitio de texto son millones de visitas. Si algún día
se pasa, GitHub avisa antes de cortar.

### 9. Los PDF de las convocatorias — **riesgo bajo, anotado**

El motor abre PDF que descarga de portales del Estado. Abrir un archivo que
otro escribió siempre tiene un riesgo teórico. Lo tranquilizador es que eso
pasa en un servidor de GitHub que se destruye al terminar la corrida, no en tu
laptop, y ahí no hay nada que robar.

---

## Lo que NO se revisó

Para que sepas dónde están los límites de esto:

- **Tu cuenta de GitHub y tu correo.** Son la llave de todo el proyecto. Si
  alguien entra ahí, nada de lo anterior importa. Ten verificación en dos
  pasos activada en las dos.
- **Formspree como empresa.** Les estás confiando los números de teléfono de
  la gente. Es un servicio serio, pero es un tercero.
- **Revisión legal.** Los textos legales los escribimos con cuidado, pero no
  los ha visto un abogado.

---

## Si algún día pasa algo

Como todo el sitio son archivos y el historial está en GitHub, **cualquier
desastre se deshace volviendo a una versión anterior**. No hay forma de perder
el proyecto salvo perder la cuenta.
