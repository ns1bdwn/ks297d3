"""
Adaptador para a API do Senado Federal.
"""
import re
import logging
from typing import Dict, List, Any, Optional

from .base import LegislativeProvider
from src.intelligence.collectors.senado import SenadoAPI

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("senado_provider")

class SenadoProvider(LegislativeProvider):
    """
    Adaptador para a API do Senado Federal.
    Implementa a interface LegislativeProvider.
    """
    
    def __init__(self):
        """
        Inicializa o adaptador com a API do Senado.
        """
        self.api = SenadoAPI()
    
    def get_pl_details(self, pl_id_info: Dict[str, str]) -> Dict[str, Any]:
        """
        Obtém detalhes completos de um PL específico.
        
        Args:
            pl_id_info: Dicionário com identificadores do PL (sigla, numero, ano)
            
        Returns:
            Dicionário com todos os detalhes disponíveis do PL
        """
        try:
            sigla = pl_id_info.get('sigla', '')
            numero = pl_id_info.get('numero', '')
            ano = pl_id_info.get('ano', '')
            
            if not sigla or not numero or not ano:
                logger.error(f"Identificadores incompletos para o PL: {pl_id_info}")
                return {}
            
            # Buscar detalhes usando a API do Senado
            details = self.api.get_additional_pl_details(sigla, numero, ano)
            
            # Verificar se os detalhes são válidos
            if not isinstance(details, dict):
                logger.error(f"API do Senado retornou um tipo inválido para detalhes do PL: {type(details)}")
                return {}
            
            return details
        except Exception as e:
            logger.error(f"Erro ao obter detalhes do PL {pl_id_info}: {str(e)}")
            return {}
    
    def search_pls(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Busca PLs com base em critérios.
        
        Args:
            criteria: Dicionário com critérios de busca (palavras-chave, autor, datas)
            
        Returns:
            Lista de PLs encontrados
        """
        try:
            keywords = criteria.get('keywords', [])
            author = criteria.get('author', '')
            date_from = criteria.get('date_from', '')
            date_to = criteria.get('date_to', '')
            limit = criteria.get('limit', 20)
            
            # Chamar a API do Senado
            results = self.api.search_pls(
                keywords=keywords,
                date_from=date_from,
                date_to=date_to,
                author=author,
                limit=limit
            )
            
            # Verificar se os resultados são válidos
            if not isinstance(results, list):
                logger.error(f"API do Senado retornou um tipo inválido para busca de PLs: {type(results)}")
                return []
            
            return results
        except Exception as e:
            logger.error(f"Erro ao buscar PLs: {str(e)}")
            return []
    
    def get_recent_pls(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Obtém os PLs mais recentes.
        
        Args:
            limit: Número máximo de PLs a retornar
            
        Returns:
            Lista de PLs recentes
        """
        try:
            # Chamar a API do Senado
            results = self.api.get_recent_pls(limit=limit)
            
            # Verificar se os resultados são válidos
            if not isinstance(results, list):
                logger.error(f"API do Senado retornou um tipo inválido para PLs recentes: {type(results)}")
                return []
            
            return results
        except Exception as e:
            logger.error(f"Erro ao obter PLs recentes: {str(e)}")
            return []
    
    def parse_pl_id(self, pl_id: str) -> Dict[str, str]:
        """
        Converte um ID de PL (ex: "PL 1234/2023") em um dicionário com seus componentes.
        
        Args:
            pl_id: ID do PL no formato "SIGLA NUMERO/ANO"
            
        Returns:
            Dicionário com 'sigla', 'numero' e 'ano'
        """
        try:
            # Padrão regex para extrair componentes do ID
            pattern = r"^([A-Za-z]+)\s+(\d+)\/(\d+)$"
            match = re.match(pattern, pl_id)
            
            if match:
                sigla, numero, ano = match.groups()
                return {
                    'sigla': sigla.upper(),
                    'numero': numero,
                    'ano': ano
                }
            else:
                logger.error(f"Formato de ID de PL inválido: {pl_id}")
                return {}
        except Exception as e:
            logger.error(f"Erro ao analisar ID de PL {pl_id}: {str(e)}")
            return {}
    
    def format_pl_id(self, pl_id_info: Dict[str, str]) -> str:
        """
        Formata os componentes de ID de um PL em uma string padronizada.
        
        Args:
            pl_id_info: Dicionário com 'sigla', 'numero' e 'ano'
            
        Returns:
            ID formatado como "SIGLA NUMERO/ANO"
        """
        try:
            sigla = pl_id_info.get('sigla', '')
            numero = pl_id_info.get('numero', '')
            ano = pl_id_info.get('ano', '')
            
            if not sigla or not numero or not ano:
                logger.error(f"Componentes de ID de PL incompletos: {pl_id_info}")
                return ""
            
            return f"{sigla} {numero}/{ano}"
        except Exception as e:
            logger.error(f"Erro ao formatar ID de PL {pl_id_info}: {str(e)}")
            return ""