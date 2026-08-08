# Google Search Console

**Ya está configurado.** El sitio se verificó y el sitemap se mandó el 4 de
agosto de 2026, con la cuenta `info@cerovagos.com`. Al 7 de agosto:

| | |
|---|---|
| Estado del sitemap | **Correcto** |
| Páginas descubiertas | **151** |
| Última lectura de Google | 7 de agosto de 2026 |

El sitemap se regenera solo cada noche, así que no hay que volver a mandarlo
nunca: Google lo relee por su cuenta y ve las ofertas nuevas y las que se
retiraron.

Esta parte no requiere nada más. **Lo que queda es leer los informes**, que es
donde está el valor.

---

## Descubierta no es lo mismo que indexada

Es la confusión más común y conviene tenerla clara:

- **Descubierta** — Google sabe que la página existe. Son las 151.
- **Indexada** — Google la guardó y puede mostrarla a alguien que busque.

Solo las indexadas traen visitas. Que las 151 estén descubiertas no dice nada
todavía sobre cuántas se van a mostrar.

Para verlo: menú de la izquierda → **Indexación** → **Páginas**. Ahí sale el
reparto entre indexadas y no indexadas, y el motivo de cada exclusión.

Con ofertas que caducan en semanas es normal que Google no las tome todas. Lo
que sí hay que mirar es **el motivo**: si dice "Rastreada, actualmente sin
indexar" en casi todas, es que Google no las considera lo bastante valiosas —
y eso sí es accionable. Si dice "Página alternativa con etiqueta canónica" o
cosas por el estilo, hay un problema técnico que arreglar.

---

## Los tres informes que importan, en orden

### 1. Mejoras → Ofertas de trabajo

**Este es el más importante y es exclusivo de este proyecto.** El motor
publica en cada ficha los datos estructurados de `JobPosting`, que es el
formato que lee **Google Empleos** — el recuadro de ofertas que sale arriba de
los resultados cuando alguien busca trabajo.

Ese informe dice si Google los está leyendo bien. Si hay errores, salen ahí
con el nombre del campo que falla, y se arreglan en `motor/sitio.py`.

Entrar a Google Empleos vale mucho más que salir en los resultados normales:
es el sitio donde la gente que busca chamba mira primero.

### 2. Rendimiento → Consultas

Por qué palabras te encuentran, cuántas veces saliste y cuántas te dieron
clic.

De acá salen las **páginas por ciudad y por rubro** que están anotadas como
pendientes. En vez de adivinar qué busca la gente, se hacen las páginas de lo
que ya te está buscando. Sin este dato, es tirar al aire.

### 3. Indexación → Páginas

El reparto de arriba. Se mira una vez por semana, no todos los días.

---

## Qué NO hay que hacer

**No volver a mandar el sitemap.** Está mandado y Google lo relee solo.
Mandarlo otra vez no acelera nada.

**No pedir indexación de las ofertas una por una.** Hay un límite diario y
para eso está el sitemap. Se justifica solo para la portada,
`/transparencia` y `/como-trabajamos`, y una sola vez.

**No borrar el archivo de verificación** de la raíz del repositorio. Google lo
revisa cada tanto; si desaparece, se pierde la verificación y con ella el
histórico. No lo toca el bot: la recolección nocturna solo escribe en `datos/`,
`oferta/`, `ir/`, `sitemap.xml` y `robots.txt`.

---

## Si algún día cambia el dominio

La propiedad de Search Console está atada a `https://cerovagos.com/`. Si el
dominio cambiara, hay que crear una propiedad nueva y volver a verificar — el
histórico de la vieja no se traslada. Ver `DOMINIO.md`.
