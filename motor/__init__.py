"""
Cero Vagos — motor recolector.

Recolecta avisos de los portales de empleo peruanos, los normaliza, les aplica
el filtro de completitud y publica solo los que lo pasan.

Uso rápido:
    python -m motor recolectar --demo
    python -m motor exportar
"""
from .modelos import Oferta, OfertaCruda
from .pipeline import Pipeline, procesar_cruda
from .score import UMBRAL_PUBLICACION, evaluar, explicar
from .sueldo import extraer_sueldo

__version__ = "0.1.0"

__all__ = [
    "Oferta", "OfertaCruda", "Pipeline", "procesar_cruda",
    "evaluar", "explicar", "extraer_sueldo", "UMBRAL_PUBLICACION",
]
