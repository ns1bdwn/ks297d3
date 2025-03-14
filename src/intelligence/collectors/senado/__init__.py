"""
Pacote para coleta de dados da API do Senado Federal.
Exporta a classe principal SenadoAPI para uso nos módulos consumidores.
"""
from .senado_facade import SenadoAPI

__all__ = ['SenadoAPI']