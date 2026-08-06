# La primera corrida de Convocatorias CAS

El lector está escrito y los 268 tests pasan, pero **todavía no ha salido a la
red ni una sola vez**. Se programó leyendo el sitio y con muestras guardadas.

El orden importa: **primero subes el código, después miras.** Y hay una regla
que no se puede saltar, explicada abajo.

---

## Antes que nada: qué se sube y qué NO

Desde que el bot corre solo en GitHub, **la carpeta de tu laptop dejó de
mandar**. El bot escribe cada madrugada en `datos/`, `oferta/` y `sitemap.xml`.
Si subes tu copia local de esas carpetas, borras lo que recolectó esa noche.
Ya pasó el 4/8/2026 y se perdieron 118 avisos.

**Se sube (esto es código, es tuyo):**

```
motor/fuentes/cas.py              ← nuevo, el lector
motor/fuentes/__init__.py         ← registra la fuente
motor/exportar.py                 ← "sin fecha" ya no es "hoy"
index.html                        ← la web se calla cuando no hay fecha
pruebas/test_cas.py               ← nuevo, 27 tests
pruebas/muestras/cas_una_plaza.html      ← nuevo
pruebas/muestras/cas_varias_plazas.html  ← nuevo
.github/workflows/actualizar.yml  ← el paso nuevo, con su propio reloj
CLAUDE.md  README.md  PRIMERA-CORRIDA-CAS.md
```

**No se sube, pase lo que pase:** `datos/`, `oferta/`, `ir/`, `sitemap.xml`.

## 1. Subir el código

Nombra los archivos uno por uno. **No uses `git add .`** — eso es exactamente
lo que arrastra `datos/` sin que te des cuenta.

```bash
cd ~/Desktop/cero-vagos

python3 -m unittest discover pruebas          # que los 268 pasen antes de subir

git add motor/fuentes/cas.py motor/fuentes/__init__.py motor/exportar.py \
        index.html \
        pruebas/test_cas.py \
        pruebas/muestras/cas_una_plaza.html \
        pruebas/muestras/cas_varias_plazas.html \
        .github/workflows/actualizar.yml \
        CLAUDE.md README.md PRIMERA-CORRIDA-CAS.md

git status                                    # revisa la lista antes de seguir
```

En `git status`, lo verde es lo que se va a subir. **Si ahí aparece algo de
`datos/`, `oferta/`, `ir/` o `sitemap.xml`, sácalo:**

```bash
git restore --staged datos oferta ir sitemap.xml
```

Cuando la lista esté limpia:

```bash
git commit -m "Lector de Convocatorias CAS: solo convocatorias de una plaza"
git push
```

Subir algo de `motor/` dispara solo el flujo *Publicar el sitio*. Es normal y
tarda menos de un minuto: solo regenera las páginas con lo que ya está en la
base, no recolecta nada.

## 2. Que la fuente se pueda leer

Estos dos comandos **solo leen**: no tocan la base ni escriben nada, así que
son seguros de correr en tu laptop.

```bash
pip install requests pdfplumber
python3 -m motor diagnostico
```

Tiene que aparecer una línea así:

```
Convocatorias CAS      robots: permite    urls: 5     JSON-LD: sí
    · Muestra: Ayudante de poda — MUNICIPALIDAD SURQUILLO [S/ 1800.00]
```

**Lo que importa es la muestra**: un cargo de verdad y un sueldo de verdad. Si
sale vacía, el sitio cambió de forma desde el 6 de agosto.

## 3. Probar un aviso suelto

Agarra cualquier convocatoria de **una plaza** del sitio (la dirección termina
en `-1-plazas-` y un número) y pásasela al motor:

```bash
python3 -m motor probar-url "https://www.convocatoriascas.com/proceso-de-seleccion-CAS-municipalidad-surquillo-agosto-2026-1-plazas-67463.html"
```

Lo que hay que revisar, y es lo más importante de todo:

- **Que el sueldo sea el mismo que ves en la página.** Este es el terreno donde
  nació el error de los S/ 33,800. Si el motor dice otro número, para todo.
- Que el título sea el oficio ("Ayudante de poda"), no la municipalidad.
- Que aparezcan funciones. Si no aparecen, el PDF de las bases no se dejó leer,
  y eso es el punto 4.

## 4. El número que decide si esta fuente sirve

Una convocatoria CAS leída **solo de la página** saca **69 sobre 100**. El
umbral para publicar es 70. Es decir: **no entra por un punto.**

No es un error del filtro. Al Estado no se le exige la lista de funciones, pero
los 25 puntos de ese bloque se pierden enteros y el aviso tiene que
compensarlos con todo lo demás. Con un sueldo de monto único y tres requisitos,
no alcanza.

Con las funciones sacadas del PDF de las bases, el mismo aviso pasa de 69 a más
de 90.

**O sea que esta fuente vive del PDF.** Si en el punto 3 no salieron funciones,
revisa en este orden:

1. ¿Está instalado `pdfplumber`? (`pip install pdfplumber`)
2. ¿La entidad deja bajar su PDF, o pide iniciar sesión?

Si las entidades no dejan bajar las bases, la fuente aporta poco, y conviene
saberlo ahora y no dentro de un mes.

## 5. La corrida de verdad: en GitHub, no en tu laptop

Aquí está la parte que cuesta caro si se hace al revés. La recolección
**escribe** en `datos/`, así que corre donde vive la base buena: en GitHub.

> Actions → **Recolección diaria** → Run workflow

No hace falta esperar a la madrugada ni tocar ninguna casilla. Tampoco hay que
marcar *reevaluar*: la fuente es nueva, el filtro no cambió.

Cuando termine, abre el paso **Convocatorias CAS** del registro y busca dos
cosas:

- **Cuántas ofertas entregó.** Si son cero *y el check salió en verde*, no es
  que no haya trabajo: es la trampa de siempre. Los pasos llevan
  `continue-on-error` a propósito, así que el verde no dice que funcionó. Lee
  el bloque *Fuentes que no entregaron nada* del resumen, no el color.
- **Cuántas convocatorias se saltaron por traer más de una plaza.** Sale una
  línea así:

  > *N convocatorias saltadas por traer más de una plaza (M plazas en total).*

  Ese número es el precio de la decisión que tomaste. Si resulta mucho más
  grande de lo esperado, vale la pena volver a mirar si conviene entrar a la
  página de cada puesto.

Si todo salió bien, el sitio queda actualizado solo y puedes borrar este
archivo.

## Si de todas formas quieres correrlo en tu laptop

Se puede, para ver las tarjetas antes de subir nada, pero con una precaución:

```bash
export CEROVAGOS_DB=~/cerovagos-prueba.db     # base aparte, no la buena
python3 -m motor recolectar --fuente "Convocatorias CAS" --publicas --limite 20
```

Con la base aparte, la de verdad (`datos/cerovagos.db`) no se toca. Y aunque
uses `--exportar`, **`datos/ofertas.js` cambiado no se sube nunca**: eso lo
escribe el bot.
