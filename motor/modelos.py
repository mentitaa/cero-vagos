"""
Modelos de datos de Cero Vagos.

Todo aviso, venga del portal que venga, termina convertido en un OfertaCruda
(lo que logramos leer) y luego en una Oferta (normalizada y puntuada).
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from typing import Any


# --------------------------------------------------------------------------
# Catálogos
# --------------------------------------------------------------------------

MONEDAS = ("PEN", "USD")

MODALIDADES = ("Presencial", "Híbrido", "Remoto")

CATEGORIAS = (
    "Tecnología", "Ventas", "Contabilidad", "Salud", "Prácticas",
    "Administración", "Logística", "Marketing", "Ingeniería", "Educación",
    "Legal", "Recursos Humanos", "Atención al Cliente", "Construcción",
    "Gastronomía", "Otros",
)


def sin_tildes(texto: str) -> str:
    """'Ingeniería' -> 'ingenieria'. Útil para comparar y armar slugs."""
    base = unicodedata.normalize("NFD", texto or "")
    return "".join(c for c in base if unicodedata.category(c) != "Mn").lower()


# --------------------------------------------------------------------------
# Oferta cruda: lo que devuelve cada adaptador de fuente
# --------------------------------------------------------------------------

@dataclass
class OfertaCruda:
    """Lo que se logró leer del portal, sin interpretar todavía."""
    fuente: str                       # "Computrabajo", "Bumeran", ...
    url: str
    puesto: str
    empresa: str = ""
    descripcion_html: str = ""        # cuerpo completo del aviso
    texto_plano: str = ""             # alternativa si no hay HTML
    ubicacion_texto: str = ""
    sueldo_texto: str = ""            # campo de sueldo del portal, si existe
    publicado: date | None = None
    id_externo: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def cuerpo(self) -> str:
        return self.descripcion_html or self.texto_plano or ""


# --------------------------------------------------------------------------
# Oferta normalizada: lo que Cero Vagos publica (si pasa el filtro)
# --------------------------------------------------------------------------

@dataclass
class Oferta:
    huella: str                       # id estable para deduplicar
    fuente: str
    url: str
    puesto: str
    empresa: str
    ciudad: str = ""
    departamento: str = ""
    modalidad: str = ""
    categoria: str = "Otros"

    sueldo_min: int = 0
    sueldo_max: int = 0
    moneda: str = "PEN"
    sueldo_periodo: str = "mensual"

    resumen: str = ""
    funciones: list[str] = field(default_factory=list)
    requisitos: list[str] = field(default_factory=list)
    beneficios: list[str] = field(default_factory=list)

    publicado: date | None = None
    vence: date | None = None          # hasta cuándo se puede postular
    capturado: datetime = field(default_factory=datetime.now)

    score: int = 0
    detalle_score: dict[str, int] = field(default_factory=dict)
    motivos_rechazo: list[str] = field(default_factory=list)
    aprobada: bool = False

    # ---------------- helpers ----------------

    @staticmethod
    def calcular_huella(puesto: str, empresa: str, ciudad: str) -> str:
        """
        Huella estable: el mismo aviso publicado en 3 portales colapsa en uno solo.
        Se ignoran tildes, mayúsculas y palabras de relleno del título.
        """
        relleno = {"para", "de", "del", "la", "el", "los", "las", "en", "con",
                   "urgente", "importante", "empresa", "gran", "oportunidad",
                   "sr", "sra", "srta", "sac", "eirl", "srl", "y", "o"}
        palabras = [
            p for p in re.findall(r"[a-z0-9+#]+", sin_tildes(puesto))
            if p not in relleno
        ]
        clave = f"{' '.join(sorted(palabras))}|{sin_tildes(empresa)}|{sin_tildes(ciudad)}"
        return hashlib.sha1(clave.encode()).hexdigest()[:16]

    @property
    def sueldo_texto(self) -> str:
        simbolo = "S/" if self.moneda == "PEN" else "US$"
        if not self.sueldo_min:
            return "Sin sueldo"
        if self.sueldo_max and self.sueldo_max != self.sueldo_min:
            return f"{simbolo} {self.sueldo_min:,} – {simbolo} {self.sueldo_max:,}".replace(",", ",")
        return f"{simbolo} {self.sueldo_min:,}"

    @property
    def dias_restantes(self) -> int | None:
        """Días que quedan para postular, o None si el aviso no lo dice."""
        return (self.vence - date.today()).days if self.vence else None

    def a_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["publicado"] = self.publicado.isoformat() if self.publicado else None
        d["vence"] = self.vence.isoformat() if self.vence else None
        d["capturado"] = self.capturado.isoformat()
        return d

    def a_json_web(self, indice: int = 0) -> dict[str, Any]:
        """Formato exacto que consume el prototipo index.html."""
        dias = (date.today() - self.publicado).days if self.publicado else 0
        return {
            "id": indice,
            "puesto": self.puesto,
            "empresa": self.empresa or "Empresa confidencial",
            "cat": self.categoria,
            "min": self.sueldo_min,
            "max": self.sueldo_max or self.sueldo_min,
            "modalidad": self.modalidad or "Presencial",
            "ciudad": self.ciudad or "Perú",
            "fuente": self.fuente,
            "dias": max(0, dias),
            "score": self.score,
            "resumen": self.resumen,
            "funciones": self.funciones,
            "requisitos": self.requisitos,
            "beneficios": self.beneficios,
            "url": self.url,
        }
