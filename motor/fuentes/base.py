"""
Contrato que cumple toda fuente de avisos.

Cada portal es un adaptador: sabe listar URLs de avisos y convertir cada aviso
en una OfertaCruda. El pipeline no sabe nada de HTML ni de portales.

NOTA LEGAL: antes de activar una fuente real, revisa su robots.txt y sus
términos de uso. Prioriza siempre, en este orden:
    1. Feed oficial / API pública del portal
    2. Sitemap o RSS declarado
    3. Datos estructurados JSON-LD (schema.org/JobPosting) de la página pública
Usa un User-Agent identificable, respeta un ritmo bajo de peticiones y guarda
solo lo necesario, enlazando siempre al aviso original.
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections.abc import Iterator

from ..modelos import OfertaCruda

USER_AGENT = "CeroVagosBot/0.1 (+https://cerovagos.pe/bot; contacto@cerovagos.pe)"
PAUSA_ENTRE_PETICIONES = 2.0   # segundos


class Fuente(ABC):
    """Adaptador de un portal de empleo."""

    nombre: str = "Fuente"
    activa: bool = True
    pausa: float = PAUSA_ENTRE_PETICIONES

    @abstractmethod
    def recolectar(self, limite: int = 100) -> Iterator[OfertaCruda]:
        """Entrega avisos crudos, de más reciente a más antiguo."""

    # -------- utilidades compartidas --------

    def esperar(self) -> None:
        time.sleep(self.pausa)

    def __repr__(self) -> str:
        return f"<Fuente {self.nombre}{'' if self.activa else ' (inactiva)'}>"


class ErrorFuente(Exception):
    """Falla recuperable de una fuente: el pipeline la registra y sigue."""
