"""
Interfaces abstratas para provedores de dados legislativos.
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("legislative_provider")

class LegislativeProvider(ABC):
    """
    Interface abstrata para qualquer provedor de dados legislativos.
    Define métodos comuns que todos os provedores específicos devem implementar.
    """
    
    @abstractmethod
    def get_pl_details(self, pl_id_info: Dict[str, str]) -> Dict[str, Any]:
        """
        Obtém detalhes completos de um PL específico.
        
        Args:
            pl_id_info: Dicionário com identificadores do PL (sigla, numero, ano)
            
        Returns:
            Dicionário com todos os detalhes disponíveis do PL
        """
        pass
    
    @abstractmethod
    def search_pls(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Busca PLs com base em critérios.
        
        Args:
            criteria: Dicionário com critérios de busca (palavras-chave, autor, datas)
            
        Returns:
            Lista de PLs encontrados
        """
        pass
    
    @abstractmethod
    def get_recent_pls(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Obtém os PLs mais recentes.
        
        Args:
            limit: Número máximo de PLs a retornar
            
        Returns:
            Lista de PLs recentes
        """
        pass
    
    @abstractmethod
    def parse_pl_id(self, pl_id: str) -> Dict[str, str]:
        """
        Converte um ID de PL (ex: "PL 1234/2023") em um dicionário com seus componentes.
        
        Args:
            pl_id: ID do PL no formato "SIGLA NUMERO/ANO"
            
        Returns:
            Dicionário com 'sigla', 'numero' e 'ano'
        """
        pass
    
    @abstractmethod
    def format_pl_id(self, pl_id_info: Dict[str, str]) -> str:
        """
        Formata os componentes de ID de um PL em uma string padronizada.
        
        Args:
            pl_id_info: Dicionário com 'sigla', 'numero' e 'ano'
            
        Returns:
            ID formatado como "SIGLA NUMERO/ANO"
        """
        pass