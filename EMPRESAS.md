# De dónde salen las ofertas de empresas

Revisado el **3 de agosto de 2026**.

## La regla que ahorra meses de trabajo

**Las marcas no contratan. Contratan los grupos.**

McDonald's Perú no tiene bolsa de trabajo: la tiene Arcos Dorados. KFC tampoco:
la tiene Delosi, que además opera Pizza Hut, Burger King y Starbucks. Sodimac y
Tottus comparten portal porque los dos son Falabella. Metro y Wong comparten
portal porque los dos son Cencosud.

Perseguir cuarenta marcas es tocar cuarenta puertas que llevan a diez casas.
Conviene ir directo a las diez casas.

### Mapa de grupos

| Grupo | Marcas que opera | Dónde publica |
|---|---|---|
| **Falabella** | Sodimac, Tottus, Falabella, Banco Falabella, Mallplaza | `muevete.falabella.com` (portal propio) |
| **Cencosud** | Metro, Wong | `cencosud.csod.com` (Cornerstone, careersite 10 = Perú) |
| **Intercorp** | Plaza Vea, Vivanda, Oechsle, Promart, Interbank, Bembos, Papa John's, Popeyes | portales del grupo y de cada retail |
| **Delosi** | KFC, Pizza Hut, Burger King, Starbucks, Chili's, Madam Tusan, Pinkberry | sobre todo Computrabajo |
| **Arcos Dorados** | McDonald's | portal regional del operador |
| **Credicorp** | BCP, Pacífico, Prima AFP, Mibanco | portal corporativo |
| **Breca** | Rimac, Minsur, Tasa, Aenza | portal corporativo |
| **Romero** | Alicorp, Primax, Ransa, Caja Arequipa | portal corporativo |
| **Backus (AB InBev)** | Cristal, Pilsen, Cusqueña | portal global del grupo |

En agroexportación no hay grupos tan concentrados: Camposol, Danper, Virú,
Agrokasa, Ecosac y Beta publican cada una por su lado, casi siempre en webs
sencillas. Son buen terreno justamente por eso.

## La segunda regla: tampoco programan su bolsa

Casi ninguna empresa grande programa su portal de empleo. Contrata un sistema de
reclutamiento —un ATS— y ese sistema publica los avisos. Los que aparecen en el
Perú y la región:

| ATS | Cómo se reconoce | Qué tan fácil es leerlo |
|---|---|---|
| **Greenhouse** | `boards.greenhouse.io` | Fácil. API pública. **Lector ya escrito** |
| **Lever** | `jobs.lever.co` | Fácil. API pública. **Lector ya escrito** |
| **Gupy** | `empresa.gupy.io` | Fácil. Devuelve JSON. Muy usado en Brasil y creciendo acá |
| **Cornerstone** | `empresa.csod.com` | Medio. API interna, hay que mirar qué pide la página |
| **Workday** | `empresa.myworkdayjobs.com` | Medio. Endpoint interno por POST |
| **SuccessFactors** | `career*.successfactors.com` | Medio. Suele traer JSON-LD |
| **Avature, iCIMS, Taleo, SmartRecruiters** | el dominio los delata | Variable |

Por eso conviene escribir **un lector por ATS y no uno por empresa**: cinco
lectores cubren cientos de compañías, y no se rompen cuando alguien rediseña la
web.

## Antes de nada: sondear

**Ninguna bolsa se conecta sin sondearla primero.** No es una recomendación,
es la lección de los dos únicos errores caros que dio esta lista.

- **BuscoTrabajo** estuvo semanas acá como "la gran fuente privada que falta".
  Su `robots.txt` nos deja entrar y es la única peruana fuera de Jobint. Nadie
  contó los avisos: tiene **4 empleos activos**, tres de la misma empresa.
- **Las bolsas universitarias** tenían 501 empresas y 8,287 vacantes, y se
  cayeron igual: **ninguna publica el sueldo**.

Los dos habrían muerto en veinte minutos con esto:

```bash
python3 -m motor sondear "https://la-url-que-encontraste"
```

Contesta las tres preguntas que deciden una fuente, en orden: **¿nos dejan
entrar?**, **¿cuántos avisos hay?** y **¿cuántos dicen el sueldo?**. La
tercera la contesta con el filtro de verdad —cada aviso de la muestra pasa por
el mismo código que decide qué se publica cada madrugada— así que el número
que da no puede prometer más de lo que la corrida real va a entregar.

No guarda nada ni toca la base: se puede correr las veces que haga falta.

Si de la muestra no sale ni un solo aviso con sueldo, se acabó. No importa
cuántas vacantes tenga ni qué empresas sean.

## Cómo dar de alta una empresa nueva

1. Busca en Google `nombre de la empresa` + `trabaja con nosotros` o `careers`.
   Si la empresa es una marca, busca primero a qué grupo pertenece.
2. Sondéala (arriba). Si pasa, corre:

   ```bash
   python3 -m motor conectar "https://la-url-que-encontraste"
   ```

   Eso revisa el robots.txt, detecta el ATS y te dice qué lector agregar.
3. Si dice que ya hay lector (Greenhouse o Lever), agrégala en
   `empresas_peru()` dentro de `motor/fuentes/empresas.py`. Una línea.
4. Si es web propia con JSON-LD, usa `portal_propio(...)` y también es una línea.
5. Si es una aplicación en JavaScript, marca `necesita_render=True` (necesita
   Playwright instalado).
6. Confirma con `python3 -m motor diagnostico --todas` antes de dejarla activa.

## Estado de lo revisado

| Empresa / grupo | robots.txt | Tecnología | Estado |
|---|---|---|---|
| **Grupo Falabella** (Sodimac, Tottus) | ✅ Permite todo | Portal propio en React | Configurado, necesita Playwright |
| **Cencosud** (Metro, Wong) | por confirmar | Cornerstone OnDemand | Configurado, sin verificar |
| **Delosi** (KFC, Pizza Hut, BK) | — | Publica en Computrabajo | Sin acceso: Computrabajo nos bloquea |
| **Camposol** | — | La URL probada no respondió | Hay que ubicar su bolsa real |

## Bolsas universitarias: la puerta está cerrada, y con razón

Revisado el 3 de agosto de 2026 sobre el Portal de Empleo de la Universidad
Autónoma del Perú.

Lo bueno que se encontró:

- Su `robots.txt` permite todo (`Disallow:` vacío).
- La página es HTML server-side, se lee sin navegador.
- El volumen es real: **501 empresas y 8,287 vacantes** en el último año.
- Y las empresas son serias: Falabella, Cencosud, Rimac, Mibanco, Las Bambas,
  Cosapi, San Fernando, Ransa, Promart, Delosi, NTT Data.
- Casi todas las bolsas universitarias peruanas corren sobre la misma
  plataforma, **Reqlut** ("su cuenta en reqlut es única… en todos los portales
  de la comunidad"). O sea que un solo lector serviría para muchas
  universidades, igual que pasa con los ATS.

Y el problema, que es definitivo:

**El listado de ofertas redirige a `/login`.** No es un descuido técnico: son
"ofertas exclusivas para estudiantes y titulados" de esa universidad. La empresa
las publica ahí justamente porque quiere ese público, y la universidad las ofrece
como beneficio a sus egresados.

Sacar esas ofertas y republicarlas rompería ese trato. No es un muro que haya
que sortear: es el producto que la universidad le vende a sus alumnos. Aunque se
tuviera una cuenta de egresado, usarla para alimentar un buscador público es
otra cosa muy distinta a buscar trabajo.

### Lo que sí se puede hacer

1. **Ir por el mismo valor a otra puerta.** Lo que atrae de estas bolsas
   —prácticas, trainee, empresas formales— también se publica en Bumeran,
   Laborum y en los ATS de esas mismas empresas. Sin muro y sin conflicto.
2. **Tocar la puerta de frente.** A una universidad le conviene que sus egresados
   se coloquen. Un acuerdo donde Cero Vagos reciba un feed —o publique las
   ofertas *no exclusivas*— es una conversación razonable. Eso se gana con un
   correo, no con código.

## LinkedIn: por qué no

Es la pregunta obvia —ahí están las empresas serias y hay más sueldos
publicados— y la respuesta es que no se puede, con tres candados:

1. **Su robots.txt bloquea las rutas de empleos** (`/jobs?runSearch*`,
   `/jobs/view/externalApply/`, entre otras).
2. **Su acuerdo de usuario lo prohíbe explícitamente.** La sección 8.22 prohíbe
   desarrollar, apoyar o usar software, scripts o robots para extraer datos del
   servicio. No es una zona gris.
3. **Lo hacen cumplir.** En marzo de 2026 bloquearon públicamente a HeyReach por
   operar sesiones automatizadas. Han litigado el tema por años.

Su API oficial (Talent Solutions) tampoco sirve: está hecha para que un ATS
**publique** avisos EN LinkedIn, no para sacarlos.

### Pero la observación era correcta, y hay una puerta

LinkedIn es, en su mayoría, **un espejo**. Las empresas grandes no escriben el
aviso ahí: lo publican en su ATS y de ahí se replica. Por eso tantos avisos
tienen el botón "Postular en el sitio web de la empresa" — ese enlace apunta a
Greenhouse, Lever, Workday o SuccessFactors.

O sea que **las mismas ofertas están disponibles en su fuente original**, con
más detalle, en formato estructurado y sin pisar los términos de nadie.

La forma sana de usar LinkedIn es como investigación de mercado, a mano:

1. Buscas en LinkedIn empleos en Perú que sí publican sueldo.
2. Anotas qué empresas son.
3. Por cada una: `python3 -m motor conectar "<su página de empleos>"`.
4. Si usa Greenhouse o Lever, ya tienes el lector escrito.

Eso es una persona mirando una web, que es justamente lo que LinkedIn permite.

## Una advertencia sobre el sueldo

La mayoría de estas empresas **no publica el monto**. Eso significa que muchas de
sus ofertas no van a pasar el filtro, y está bien: la regla no se toca. Sirven
igual, por dos razones. Primero, las que sí publican sueldo son oro y nadie las
tiene juntas. Segundo, saber qué empresas nunca publican el monto es, en sí
mismo, información que a tus usuarios les interesa.
