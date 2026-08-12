"""
Almacén SQLite.

Guarda todo lo que se procesa —aprobado y rechazado— porque los rechazos son
el mejor material para afinar el filtro. El sitio solo lee las aprobadas y
vigentes.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import date, datetime
from pathlib import Path

from .modelos import Oferta

# Se puede mover la base con la variable de entorno CEROVAGOS_DB (útil si el
# proyecto vive en una carpeta sincronizada o en una unidad de red, donde
# SQLite no puede tomar bloqueos).
RUTA_BD = Path(
    os.environ.get("CEROVAGOS_DB")
    or Path(__file__).resolve().parent.parent / "datos" / "cerovagos.db"
)

ESQUEMA = """
CREATE TABLE IF NOT EXISTS ofertas (
    huella          TEXT PRIMARY KEY,
    fuente          TEXT NOT NULL,
    url             TEXT NOT NULL,
    puesto          TEXT NOT NULL,
    empresa         TEXT,
    ciudad          TEXT,
    departamento    TEXT,
    modalidad       TEXT,
    categoria       TEXT,
    sueldo_min      INTEGER DEFAULT 0,
    sueldo_max      INTEGER DEFAULT 0,
    moneda          TEXT DEFAULT 'PEN',
    resumen         TEXT,
    funciones       TEXT,
    requisitos      TEXT,
    beneficios      TEXT,
    publicado       TEXT,
    vence           TEXT,
    capturado       TEXT,
    visto_ultima_vez TEXT,
    score           INTEGER DEFAULT 0,
    detalle_score   TEXT,
    motivos_rechazo TEXT,
    aprobada        INTEGER DEFAULT 0,
    vigente         INTEGER DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_aprobadas ON ofertas(aprobada, vigente, publicado);
CREATE INDEX IF NOT EXISTS idx_categoria ON ofertas(categoria);
CREATE INDEX IF NOT EXISTS idx_sueldo    ON ofertas(sueldo_min);

CREATE TABLE IF NOT EXISTS corridas (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    inicio      TEXT,
    fin         TEXT,
    fuente      TEXT,
    leidas      INTEGER,
    aprobadas   INTEGER,
    rechazadas  INTEGER,
    detalle     TEXT
);
"""


class Almacen:
    def __init__(self, ruta: Path | str = RUTA_BD):
        self.ruta = Path(ruta)
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(self.ruta)
        self.con.row_factory = sqlite3.Row
        self.con.executescript(ESQUEMA)
        self._migrar()
        self.con.commit()

    def _migrar(self) -> None:
        """
        Agrega columnas nuevas a bases que ya existen, para no obligar a borrar
        todo lo recolectado cada vez que el modelo crece.
        """
        columnas = {f["name"] for f in self.con.execute("PRAGMA table_info(ofertas)")}
        for nombre, tipo in (("vence", "TEXT"),):
            if nombre not in columnas:
                self.con.execute(f"ALTER TABLE ofertas ADD COLUMN {nombre} {tipo}")

    # ---------------- escritura ----------------

    def guardar(self, o: Oferta) -> str:
        """Inserta o actualiza. Devuelve 'nueva' o 'actualizada'."""
        existe = self.con.execute(
            "SELECT 1 FROM ofertas WHERE huella = ?", (o.huella,)
        ).fetchone()

        # Se nombran las columnas en vez de confiar en su orden: una base creada
        # hace dos versiones tiene las columnas nuevas al final, y un INSERT
        # posicional guardaría cada dato en la casilla equivocada.
        valores = {
            "huella": o.huella, "fuente": o.fuente, "url": o.url,
            "puesto": o.puesto, "empresa": o.empresa, "ciudad": o.ciudad,
            "departamento": o.departamento, "modalidad": o.modalidad,
            "categoria": o.categoria, "sueldo_min": o.sueldo_min,
            "sueldo_max": o.sueldo_max, "moneda": o.moneda, "resumen": o.resumen,
            "funciones": json.dumps(o.funciones, ensure_ascii=False),
            "requisitos": json.dumps(o.requisitos, ensure_ascii=False),
            "beneficios": json.dumps(o.beneficios, ensure_ascii=False),
            "publicado": o.publicado.isoformat() if o.publicado else None,
            "vence": o.vence.isoformat() if o.vence else None,
            "capturado": o.capturado.isoformat(),
            "visto_ultima_vez": datetime.now().isoformat(),
            "score": o.score,
            "detalle_score": json.dumps(o.detalle_score, ensure_ascii=False),
            "motivos_rechazo": json.dumps(o.motivos_rechazo, ensure_ascii=False),
            "aprobada": int(o.aprobada), "vigente": 1,
        }
        columnas = ", ".join(valores)
        marcas = ", ".join(f":{c}" for c in valores)
        # Todo se refresca salvo la huella y la fecha de captura original.
        refrescar = ", ".join(
            f"{c}=excluded.{c}" for c in valores if c not in ("huella", "capturado")
        )

        # Se refresca TODO el contenido, no solo el puntaje.
        #
        # Antes solo se actualizaban score y aprobada, y eso producía ofertas
        # fantasma: un aviso guardado en una corrida vieja (sin funciones)
        # quedaba aprobado con el puntaje nuevo pero mostrando el contenido
        # viejo. En la web se veía una oferta con score 95 y cero funciones.
        self.con.execute(
            f"INSERT INTO ofertas ({columnas}) VALUES ({marcas}) "
            f"ON CONFLICT(huella) DO UPDATE SET {refrescar}",
            valores,
        )
        self.con.commit()
        return "actualizada" if existe else "nueva"

    def registrar_corrida(self, inicio: datetime, fuente: str,
                          leidas: int, aprobadas: int, rechazadas: int,
                          detalle: dict) -> None:
        self.con.execute(
            "INSERT INTO corridas (inicio, fin, fuente, leidas, aprobadas, rechazadas, detalle)"
            " VALUES (?,?,?,?,?,?,?)",
            (inicio.isoformat(), datetime.now().isoformat(), fuente,
             leidas, aprobadas, rechazadas, json.dumps(detalle, ensure_ascii=False)),
        )
        self.con.commit()

    def depurar(self) -> dict[str, int]:
        """
        Saca de la web lo que ya no sirve, con las mismas reglas del filtro.

        Es imprescindible que exista aparte del filtro: una oferta guardada la
        semana pasada seguía publicándose aunque su plazo hubiera cerrado ayer,
        porque nadie la volvía a mirar. Esto se ejecuta en cada corrida y en
        cada exportación.
        """
        from .score import MAX_DIAS_ANTIGUEDAD, PERFILES

        hoy = date.today().isoformat()
        quitadas = {}

        # Un aviso es del Estado o es privado, y se decide igual que en el
        # filtro: por el nombre de la fuente. No se guarda en la base para no
        # tener dos versiones de la misma verdad.
        ES_ESTADO = "LOWER(COALESCE(fuente,'')) LIKE '%estado%'"

        # 1. Dijo hasta cuándo, y ya pasó.
        quitadas["plazo cerrado"] = self.con.execute(
            "UPDATE ofertas SET vigente = 0 WHERE vigente = 1 "
            "AND vence IS NOT NULL AND vence != '' AND vence < ?", (hoy,),
        ).rowcount

        # 2. No dijo hasta cuándo y ya lleva demasiado publicada.
        #
        # Cada perfil tiene su propia paciencia: 21 días al Estado, 45 al
        # privado. Antes esta consulta aplicaba 21 a TODO el mundo —la vara del
        # Estado a los avisos privados—, así que un aviso de Bumeran sin fecha
        # de cierre desaparecía de la web 24 días antes de tiempo, en silencio
        # y sin aparecer en ningún rechazo.
        quitadas["sin fecha y vieja"] = 0
        for perfil, negar in (("publico", ""), ("privado", "NOT ")):
            tope = int(PERFILES[perfil]["dias_sin_cierre"])
            quitadas["sin fecha y vieja"] += self.con.execute(
                "UPDATE ofertas SET vigente = 0 WHERE vigente = 1 "
                "AND (vence IS NULL OR vence = '') AND publicado IS NOT NULL "
                f"AND {negar}({ES_ESTADO}) "
                "AND julianday(?) - julianday(publicado) > ?", (hoy, tope),
            ).rowcount

        # 3. Tope absoluto.
        quitadas["más de dos meses"] = self.con.execute(
            "UPDATE ofertas SET vigente = 0 WHERE vigente = 1 "
            "AND publicado IS NOT NULL "
            "AND julianday(?) - julianday(publicado) > ?", (hoy, MAX_DIAS_ANTIGUEDAD),
        ).rowcount

        self.con.commit()
        return {k: v for k, v in quitadas.items() if v}

    def vencer_antiguas(self, dias: int | None = None) -> int:
        """Compatibilidad: devuelve cuántas ofertas salieron de la web."""
        return sum(self.depurar().values())

    # ---------------- lectura ----------------

    def aprobadas(self, limite: int = 500) -> list[dict]:
        filas = self.con.execute(
            "SELECT * FROM ofertas WHERE aprobada = 1 AND vigente = 1 "
            "ORDER BY publicado DESC, score DESC LIMIT ?",
            (limite,),
        ).fetchall()
        return [self._a_dict(f) for f in filas]

    def rechazadas(self, limite: int = 200) -> list[dict]:
        filas = self.con.execute(
            "SELECT * FROM ofertas WHERE aprobada = 0 ORDER BY capturado DESC LIMIT ?",
            (limite,),
        ).fetchall()
        return [self._a_dict(f) for f in filas]

    # Cada cuánto vale la pena volver a mirar un aviso que ya se revisó.
    #
    # Un aviso RECHAZADO casi nunca cambia: una empresa que no puso el sueldo
    # no vuelve a entrar a ponerlo. Revisarlo cada noche es gastar por gusto.
    #
    # Uno APROBADO sí conviene mirarlo de vez en cuando, por si lo bajaron o le
    # cambiaron la fecha de cierre.
    DIAS_RECHAZADAS = 30
    DIAS_APROBADAS = 7

    def urls_publicadas(self) -> dict[str, list[str]]:
        """
        Las direcciones de lo que está publicado ahora mismo, por fuente.

        Existe para poder REPARAR. Cuando se arregla la lectura de un dato —un
        sueldo, una categoría— lo ya guardado conserva el valor viejo, y la
        única forma de corregirlo es volver a descargar el aviso.

        Hasta el 7/8/2026 eso se intentaba subiendo el límite de la corrida y
        cruzando los dedos: cada fuente descubre direcciones en su sitemap y se
        detiene al llegar a su cupo, así que **que un aviso guardado caiga
        dentro de ese corte es cuestión de suerte**. Se corrió tres veces con
        `rehacer` y los mismos tres avisos quedaron fuera las tres.

        Pidiendo las direcciones a la base el asunto deja de ser aleatorio: se
        vuelve a leer exactamente lo que está publicado, ni más ni menos.
        """
        # DISTINCT porque una convocatoria del Estado con varios puestos deja
        # varias ofertas con el MISMO enlace. Sin esto se descargaría la misma
        # página tres veces para releer los tres puestos que ya salen juntos.
        filas = self.con.execute(
            "SELECT DISTINCT fuente, url FROM ofertas "
            "WHERE aprobada = 1 AND vigente = 1 AND url IS NOT NULL AND url != ''"
        ).fetchall()
        por_fuente: dict[str, list[str]] = {}
        for f in filas:
            por_fuente.setdefault(f["fuente"], []).append(f["url"])
        return por_fuente

    def urls_a_saltar(self) -> set[str]:
        """
        URLs que no hace falta volver a descargar en esta corrida.

        Esto es lo que hace que la recolección diaria sea barata: después de
        unos días, cada noche solo se bajan los avisos NUEVOS. También permite
        retomar una corrida que se cortó a la mitad.
        """
        # El instante se calcula en Python y se pasa como dato. SQLite usa UTC
        # y Python la hora local: en Perú, después de las 7 de la tarde ya no
        # son el mismo día, y mezclarlos hacía que las cuentas salieran
        # corridas por 24 horas.
        ahora = datetime.now().isoformat(sep=" ", timespec="seconds")
        filas = self.con.execute(
            "SELECT url FROM ofertas WHERE visto_ultima_vez IS NOT NULL AND ("
            "  (aprobada = 0 AND julianday(?) - julianday(visto_ultima_vez) < ?)"
            "  OR"
            "  (aprobada = 1 AND julianday(?) - julianday(visto_ultima_vez) < ?)"
            ")",
            (ahora, self.DIAS_RECHAZADAS, ahora, self.DIAS_APROBADAS),
        ).fetchall()
        return {f["url"] for f in filas if f["url"]}

    def urls_vistas(self, horas: int = 20) -> set[str]:
        """URLs revisadas en las últimas N horas. Se mantiene para pruebas."""
        ahora = datetime.now().isoformat(sep=" ", timespec="seconds")
        filas = self.con.execute(
            "SELECT url FROM ofertas WHERE visto_ultima_vez IS NOT NULL "
            "AND (julianday(?) - julianday(visto_ultima_vez)) * 24 < ?",
            (ahora, horas),
        ).fetchall()
        return {f["url"] for f in filas if f["url"]}

    def estadisticas(self) -> dict:
        q = lambda sql: self.con.execute(sql).fetchone()[0]  # noqa: E731
        total = q("SELECT COUNT(*) FROM ofertas")
        aprob = q("SELECT COUNT(*) FROM ofertas WHERE aprobada = 1 AND vigente = 1")
        # Cuántos avisos ocultan el sueldo. No es una métrica interna: es el
        # argumento de venta del proyecto, y conviene tenerlo medido.
        sin_sueldo = q(
            "SELECT COUNT(*) FROM ofertas WHERE motivos_rechazo LIKE '%ueldo%'"
        )
        return {
            "total_procesadas": total,
            "aprobadas_vigentes": aprob,
            "tasa_aprobacion": round(aprob / total * 100, 1) if total else 0.0,
            "sin_sueldo": sin_sueldo,
            "pct_sin_sueldo": round(sin_sueldo / total * 100) if total else 0,
            "sueldo_mediano": q(
                "SELECT COALESCE(sueldo_min, 0) FROM ofertas WHERE aprobada = 1 AND vigente = 1"
                " ORDER BY sueldo_min LIMIT 1 OFFSET (SELECT COUNT(*)/2 FROM ofertas"
                " WHERE aprobada = 1 AND vigente = 1)"
            ) if aprob else 0,
            "por_fuente": {
                f["fuente"]: f["n"] for f in self.con.execute(
                    "SELECT fuente, COUNT(*) n FROM ofertas WHERE aprobada = 1 AND vigente = 1"
                    " GROUP BY fuente ORDER BY n DESC"
                ).fetchall()
            },
            # Cuántas ofertas PUBLICADAS hay en cada departamento. Es el número
            # que decide si una página "Trabajos en Arequipa con sueldo" tiene
            # con qué llenarse: una página casi vacía le dice a Google que el
            # sitio es de baja calidad, así que conviene mirarlo antes de
            # hacerlas, no después.
            #
            # Va por departamento y no por ciudad a propósito: la gente busca
            # "trabajo en Cusco", no "trabajo en Wanchaq", y agrupando así una
            # provincia junta lo que suelto no alcanzaría para nada.
            "por_departamento": {
                f["depa"]: f["n"] for f in self.con.execute(
                    "SELECT COALESCE(NULLIF(departamento, ''), '(sin ubicación)') depa,"
                    " COUNT(*) n FROM ofertas WHERE aprobada = 1 AND vigente = 1"
                    " GROUP BY depa ORDER BY n DESC, depa"
                ).fetchall()
            },
        }

    def limpiar_titulos(self) -> int:
        """
        Vuelve a pasar el limpiador de títulos por lo ya guardado.

        Hace falta porque las mejoras al limpiador no alcanzan a los avisos que
        ya estaban en la base: solo se reescriben cuando el motor los vuelve a
        visitar, y eso puede tardar semanas. Esto los arregla de una.
        """
        from .normalizar import limpiar_puesto

        arreglados = 0
        for fila in self.con.execute("SELECT huella, puesto FROM ofertas").fetchall():
            limpio = limpiar_puesto(fila["puesto"])
            if limpio and limpio != fila["puesto"]:
                self.con.execute("UPDATE ofertas SET puesto = ? WHERE huella = ?",
                                 (limpio, fila["huella"]))
                arreglados += 1
        if arreglados:
            self.con.commit()
        return arreglados

    def reevaluar(self) -> dict:
        """
        Vuelve a puntuar lo que ya está guardado, con las reglas de hoy.

        Hace falta cada vez que cambia el filtro. Un aviso guardado conserva
        el veredicto del día en que se leyó, y el motor no vuelve a mirar un
        aviso rechazado hasta pasados 30 días — así que sin esto, un cambio de
        regla tarda un mes en notarse.

        A propósito NO se ejecuta sola en cada publicación. Cambiar el filtro
        es un acto deliberado y repararlo también debe serlo: una reevaluación
        automática y silenciosa podría despublicar el sitio entero si alguien
        introduce un error en la rúbrica, y nadie se enteraría hasta mirar.
        Se lanza a mano:  python3 -m motor reevaluar

        Solo se re-puntúa: no se vuelve a descargar nada. Todo lo que la
        rúbrica necesita (sueldo, funciones, requisitos, beneficios, fechas)
        ya está en la base.

        Devuelve cuántos avisos cambiaron de veredicto, en cada dirección.
        """
        from datetime import date as _date

        from .score import evaluar
        from .sueldo import Sueldo

        def _fecha(v):
            try:
                return _date.fromisoformat(str(v)[:10]) if v else None
            except ValueError:
                return None

        entraron = salieron = 0
        filas = self.con.execute(
            "SELECT huella, fuente, empresa, ciudad, modalidad, sueldo_min, sueldo_max, "
            "moneda, resumen, funciones, requisitos, beneficios, publicado, vence, aprobada "
            "FROM ofertas").fetchall()

        for f in filas:
            # El perfil no se guarda: se deduce de la fuente, igual que en la
            # recolección. Solo las convocatorias del Estado usan la vara
            # pública (ver PERFILES en score.py).
            perfil = "publico" if "estado" in (f["fuente"] or "").lower() else "privado"
            sueldo = (Sueldo(minimo=f["sueldo_min"], maximo=f["sueldo_max"] or f["sueldo_min"],
                             moneda=f["moneda"] or "PEN", periodo="mensual")
                      if f["sueldo_min"] else None)

            r = evaluar(
                sueldo=sueldo,
                funciones=json.loads(f["funciones"] or "[]"),
                requisitos=json.loads(f["requisitos"] or "[]"),
                beneficios=json.loads(f["beneficios"] or "[]"),
                empresa=f["empresa"] or "",
                ciudad=f["ciudad"] or "",
                modalidad=f["modalidad"] or "",
                publicado=_fecha(f["publicado"]),
                vence=_fecha(f["vence"]),
                texto_completo=f["resumen"] or "",
                perfil=perfil,
            )
            if bool(r.aprobada) == bool(f["aprobada"]):
                continue

            self.con.execute(
                "UPDATE ofertas SET aprobada = ?, score = ?, motivos_rechazo = ? "
                "WHERE huella = ?",
                (int(r.aprobada), r.total,
                 json.dumps(r.motivos, ensure_ascii=False), f["huella"]))
            if r.aprobada:
                entraron += 1
            else:
                salieron += 1

        if entraron or salieron:
            self.con.commit()
        return {"entraron": entraron, "salieron": salieron}

    def revisar_titulos_vagos(self) -> dict:
        """
        Pasa la regla del título por lo que ya está publicado.

        La regla nueva (deducir el oficio, y si no se sabe rechazar) solo actúa
        sobre avisos recién recolectados. Los que ya estaban en la base seguirían
        publicados con "Papa Johns" de título durante semanas, hasta que el motor
        volviera a verlos. Esto los arregla ahora.

        Devuelve cuántos se reescribieron y cuántos se bajaron.
        """
        from .normalizar import deducir_puesto, titulo_nombra_el_puesto

        reescritos = retirados = 0
        filas = self.con.execute(
            "SELECT huella, puesto, resumen, funciones, requisitos, motivos_rechazo "
            "FROM ofertas WHERE aprobada = 1").fetchall()

        for fila in filas:
            if titulo_nombra_el_puesto(fila["puesto"]):
                continue

            deducido = deducir_puesto(
                fila["resumen"] or "",
                json.loads(fila["funciones"] or "[]"),
                json.loads(fila["requisitos"] or "[]"),
            )
            if deducido:
                self.con.execute("UPDATE ofertas SET puesto = ? WHERE huella = ?",
                                 (deducido, fila["huella"]))
                reescritos += 1
            else:
                motivos = json.loads(fila["motivos_rechazo"] or "[]")
                motivos.append("El aviso no dice qué puesto es")
                self.con.execute(
                    "UPDATE ofertas SET aprobada = 0, motivos_rechazo = ? WHERE huella = ?",
                    (json.dumps(motivos, ensure_ascii=False), fila["huella"]))
                retirados += 1

        if reescritos or retirados:
            self.con.commit()
        return {"reescritos": reescritos, "retirados": retirados}

    # ---------------- transparencia salarial ----------------

    def transparencia(self, minimo_avisos: int = 3) -> dict:
        """
        Quién dice cuánto paga y quién no.

        Sale de los avisos que el motor ya revisó, publicados y rechazados por
        igual. No es una opinión: es contar cuántos de sus avisos traían un
        monto y cuántos no.

        Se exige un mínimo de avisos por empresa a propósito. Con uno o dos no
        se puede afirmar nada de nadie, y señalar a alguien con una muestra
        pequeña sería injusto además de flojo.
        """
        def agrupar(campo: str, minimo: int = 1) -> list[dict]:
            filas = self.con.execute(
                f"SELECT {campo} AS nombre, COUNT(*) AS total, "
                f"       SUM(CASE WHEN sueldo_min > 0 THEN 1 ELSE 0 END) AS con_sueldo "
                f"FROM ofertas WHERE {campo} IS NOT NULL AND TRIM({campo}) != '' "
                f"GROUP BY LOWER(TRIM({campo})) HAVING total >= ? "
                f"ORDER BY total DESC",
                (minimo,),
            ).fetchall()
            salida = []
            for f in filas:
                total, con = f["total"], f["con_sueldo"] or 0
                salida.append({
                    "nombre": f["nombre"], "total": total, "con_sueldo": con,
                    "sin_sueldo": total - con,
                    "pct": round(con / total * 100) if total else 0,
                })
            return salida

        total = self.con.execute("SELECT COUNT(*) FROM ofertas").fetchone()[0]
        con_sueldo = self.con.execute(
            "SELECT COUNT(*) FROM ofertas WHERE sueldo_min > 0").fetchone()[0]

        periodo = self.con.execute(
            "SELECT MIN(date(capturado)), MAX(date(capturado)) FROM ofertas").fetchone()

        # Las tablas se ordenan por transparencia, que es de lo que hablan.
        # A igual porcentaje manda el volumen: 100% sobre 12 avisos dice más
        # que 100% sobre 3.
        def por_transparencia(filas, ascendente=False):
            return sorted(filas, key=lambda e: (e["pct"] if ascendente else -e["pct"],
                                                -e["total"]))

        empresas = agrupar("empresa", minimo_avisos)
        return {
            "total": total,
            "con_sueldo": con_sueldo,
            "sin_sueldo": total - con_sueldo,
            "pct_con_sueldo": round(con_sueldo / total * 100) if total else 0,
            "pct_sin_sueldo": round((total - con_sueldo) / total * 100) if total else 0,
            "desde": periodo[0] or "", "hasta": periodo[1] or "",
            "minimo_avisos": minimo_avisos,
            "empresas": empresas,
            "transparentes": por_transparencia([e for e in empresas if e["pct"] >= 80])[:20],
            "opacas": por_transparencia([e for e in empresas if e["pct"] == 0], True)[:20],
            "por_fuente": por_transparencia(agrupar("fuente")),
            "por_categoria": por_transparencia(agrupar("categoria", 3)),
            "por_ciudad": por_transparencia(agrupar("ciudad", 3)),
        }

    def por_departamento(self, minimo: int = 5) -> list[dict]:
        """
        Lo que hace falta para armar la página de cada departamento.

        Va por departamento y no por ciudad porque la gente busca "trabajo en
        Cusco", no "trabajo en Wanchaq" — y agrupando así una provincia junta
        lo que suelto no alcanzaría para llenar una página.

        Solo salen los que llegan a `minimo` ofertas publicadas. Una página
        casi vacía le dice a Google que el sitio es de baja calidad, y esa
        señal mancha al resto: es peor que no tenerla.

        De cada uno se devuelve también **cuántos avisos se revisaron ahí y
        cuántos declaraban sueldo**. Ese es el dato que hace que la página
        valga por sí sola: nadie más en el Perú lo tiene, y es lo que la
        distingue de ser un listado más.
        """
        publicadas = self.con.execute(
            "SELECT departamento AS depa, COUNT(*) AS n "
            "FROM ofertas WHERE aprobada = 1 AND vigente = 1 "
            "  AND departamento IS NOT NULL AND TRIM(departamento) != '' "
            "GROUP BY departamento HAVING n >= ? ORDER BY n DESC, departamento",
            (minimo,),
        ).fetchall()

        salida = []
        for fila in publicadas:
            depa = fila["depa"]
            revision = self.con.execute(
                "SELECT COUNT(*) AS total, "
                "       SUM(CASE WHEN sueldo_min > 0 THEN 1 ELSE 0 END) AS con_sueldo "
                "FROM ofertas WHERE departamento = ?", (depa,),
            ).fetchone()
            revisados = revision["total"] or 0
            con_sueldo = revision["con_sueldo"] or 0

            ofertas = self.con.execute(
                "SELECT * FROM ofertas WHERE aprobada = 1 AND vigente = 1 "
                "  AND departamento = ? ORDER BY publicado DESC, score DESC",
                (depa,),
            ).fetchall()

            salida.append({
                "departamento": depa,
                "ofertas": [self._a_dict(o) for o in ofertas],
                "total": fila["n"],
                "revisados": revisados,
                "con_sueldo": con_sueldo,
                "sin_sueldo": revisados - con_sueldo,
                "pct_sin_sueldo": (round((revisados - con_sueldo) / revisados * 100)
                                   if revisados else 0),
            })
        return salida

    @staticmethod
    def _a_dict(fila: sqlite3.Row) -> dict:
        d = dict(fila)
        for campo in ("funciones", "requisitos", "beneficios", "detalle_score", "motivos_rechazo"):
            try:
                d[campo] = json.loads(d[campo]) if d[campo] else []
            except (TypeError, json.JSONDecodeError):
                d[campo] = []
        return d

    def cerrar(self) -> None:
        self.con.close()
