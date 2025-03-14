"""
Pacote com adaptadores para diferentes provedores de dados legislativos.
"""
from .base import LegislativeProvider
from .senado_provider import SenadoProvider

__all__ = ['LegislativeProvider', 'SenadoProvider']