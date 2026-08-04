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
        sin_cierre = int(PERFILES["publico"]["dias_sin_cierre"])
        quitadas = {}

        # 1. Dijo hasta cuándo, y ya pasó.
        quitadas["plazo cerrado"] = self.con.execute(
            "UPDATE ofertas SET vigente = 0 WHERE vigente = 1 "
            "AND vence IS NOT NULL AND vence != '' AND vence < ?", (hoy,),
        ).rowcount

        # 2. No dijo hasta cuándo y ya lleva demasiado publicada.
        quitadas["sin fecha y vieja"] = self.con.execute(
            "UPDATE ofertas SET vigente = 0 WHERE vigente = 1 "
            "AND (vence IS NULL OR vence = '') AND publicado IS NOT NULL "
            "AND julianday(?) - julianday(publicado) > ?", (hoy, sin_cierre),
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
        }

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
            "transparentes": [e for e in empresas if e["pct"] >= 80][:20],
            "opacas": [e for e in empresas if e["pct"] == 0][:20],
            "por_fuente": agrupar("fuente"),
            "por_categoria": agrupar("categoria", 3),
            "por_ciudad": agrupar("ciudad", 3),
        }

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
