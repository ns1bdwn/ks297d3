# src/intelligence/collectors/senado/senado_facade.py
"""
Fachada unificada para o sistema de coleta de dados do Senado.
Esta classe provê uma interface simplificada, mantendo compatibilidade
com o código existente que usa o senado_api.py.
"""
import logging
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple

from .api_base import SenadoAPIBase
from .materias_collector import MateriasCollector
from .tramitacao_collector import TramitacaoCollector
from .relatoria_collector import RelatoriaCollector
from .autoria_collector import AutoriaCollector
from .votacao_collector import VotacaoCollector
from .texto_collector import TextoCollector

# Configuração de logging
logger = logging.getLogger("senado_api")

class SenadoAPI:
    """
    Fachada que unifica o acesso a todos os coletores específicos 
    do sistema de coleta de dados do Senado.
    
    Mantém compatibilidade com o código existente, direcionando
    chamadas para os coletores especializados.
    """
    
    def __init__(self, cache_dir: str = None):
        """
        Inicializa a fachada para o sistema de coleta de dados do Senado.
        
        Args:
            cache_dir: Diretório para cache. Se None, usa o padrão.
        """
        self.cache_dir = cache_dir
        
        # Instanciar todos os coletores
        self.materias = MateriasCollector(self.cache_dir)
        self.tramitacao = TramitacaoCollector(self.cache_dir)
        self.relatoria = RelatoriaCollector(self.cache_dir)
        self.autoria = AutoriaCollector(self.cache_dir)
        self.votacao = VotacaoCollector(self.cache_dir)
        self.texto = TextoCollector(self.cache_dir)
    
    def get_pl_by_id(self, sigla: str, numero: str, ano: str) -> Dict[str, Any]:
        """
        Obtém detalhes básicos de um PL específico.
        Mantém compatibilidade com o código existente.
        
        Args:
            sigla: Sigla do PL (ex: PL, PEC)
            numero: Número do PL
            ano: Ano do PL
            
        Returns:
            Dicionário com detalhes do PL
        """
        return self.materias.get_pl_by_id(sigla, numero, ano)
    
    def get_pl_relatores(self, codigo_materia: str) -> List[Dict]:
        """
        Obtém os relatores de um PL.
        
        Args:
            codigo_materia: Código da matéria
            
        Returns:
            Lista de relatores
        """
        return self.relatoria.get_relatores(codigo_materia)
    
    def get_pl_tramitacao(self, sigla: str, numero: str, ano: str, codigo_materia: str = None) -> List[Dict]:
        """
        Obtém o histórico de tramitação de um PL.
        
        Args:
            sigla: Sigla do PL (ex: PL, PEC)
            numero: Número do PL
            ano: Ano do PL
            codigo_materia: Código da matéria (opcional)
            
        Returns:
            Lista de eventos da tramitação
        """
        # Se não temos o código da matéria, tentamos obter
        if not codigo_materia:
            pl_details = self.materias.get_pl_by_id(sigla, numero, ano)
            codigo_materia = pl_details.get('CodigoMateria')
        
        if codigo_materia:
            return self.tramitacao.get_tramitacao(codigo_materia)
        else:
            logger.warning(f"Não foi possível obter o código da matéria para {sigla} {numero}/{ano}")
            return []
    
    def search_pls(self, keywords: List[str] = None, date_from: str = None, 
                  date_to: str = None, author: str = None, limit: int = 20) -> List[Dict]:
        """
        Busca PLs por palavras-chave, autor ou situação.
        
        Args:
            keywords: Lista de palavras-chave para buscar
            date_from: Data inicial no formato YYYYMMDD
            date_to: Data final no formato YYYYMMDD
            author: Nome do autor para filtrar
            limit: Número máximo de resultados
            
        Returns:
            Lista de PLs encontrados
        """
        return self.materias.search_pls(keywords, date_from, date_to, author, limit)
    
    def search_multiple_keywords(self, keywords: List[str], 
                               start_date: str = None, 
                               end_date: str = None,
                               limit: int = 50) -> pd.DataFrame:
        """
        Realiza busca com múltiplas palavras-chave e consolida os resultados.
        
        Args:
            keywords: Lista de palavras-chave para buscar
            start_date: Data inicial no formato YYYYMMDD
            end_date: Data final no formato YYYYMMDD
            limit: Limite de resultados por palavra-chave
            
        Returns:
            DataFrame com os resultados consolidados
        """
        return self.materias.search_multiple_keywords(keywords, start_date, end_date, limit)
    
    def get_recent_pls(self, limit: int = 10) -> List[Dict]:
        """
        Retorna os PLs mais recentes.
        
        Args:
            limit: Número máximo de PLs a retornar
            
        Returns:
            Lista com os PLs mais recentes
        """
        return self.materias.get_recent_pls(limit)
    
    def get_additional_pl_details(self, sigla: str, numero: str, ano: str) -> Dict[str, Any]:
        """
        Obtém detalhes completos de um PL, combinando dados de todos os coletores.
        
        Args:
            sigla: Sigla do PL (ex: PL, PEC)
            numero: Número do PL
            ano: Ano do PL
            
        Returns:
            Dicionário com todos os detalhes disponíveis do PL
        """
        logger.info(f"Buscando detalhes completos do PL {sigla} {numero}/{ano}")
        
        # Buscar detalhes básicos
        pl_details = self.materias.get_pl_by_id(sigla, numero, ano)
        if not pl_details:
            logger.warning(f"PL {sigla} {numero}/{ano} não encontrado")
            return {}
        
        # Se temos o código da matéria, buscar informações adicionais
        codigo_materia = pl_details.get('CodigoMateria')
        if codigo_materia:
            # Buscar tramitação detalhada
            pl_details["Tramitacao_Detalhada"] = self.tramitacao.get_tramitacao(codigo_materia)
            
            # Buscar situação atual
            pl_details["Situacao"] = self.tramitacao.get_situacao_atual(codigo_materia)
            
            # Buscar relatores (usando endpoint correto)
            pl_details["Relatores"] = self.relatoria.get_relatores(codigo_materia)
            
            # Buscar texto completo
            pl_details["Texto"] = self.texto.get_texto_completo(codigo_materia)
            
            # Buscar votações
            pl_details["Votacoes"] = self.votacao.get_votacoes(codigo_materia)
            
            # Buscar votações em comissões (endpoint alternativo)
            pl_details["VotacoesComissao"] = self.votacao.get_votacoes_comissao(sigla, numero, ano)
            
            # Buscar emendas
            pl_details["Emendas"] = self.texto.get_emendas(codigo_materia)
            
            # Buscar autoria detalhada
            pl_details["detalhes_adicionais"] = {
                "autoria_detalhada": self.autoria.get_autoria_detalhada(codigo_materia),
                # Informações extras podem ser adicionadas aqui
                "estatisticas_votacao": self.votacao.get_estatisticas_votacoes(codigo_materia),
                "prazos": self.tramitacao.get_prazos(codigo_materia),
                "atualizacoes_recentes": self.tramitacao.get_ultimas_atualizacoes(codigo_materia)
            }
        
        return pl_details
    
    def set_cache_policy(self, use_cache: bool, expiration_hours: int = 12):
        """
        Define a política de cache para todos os coletores.
        
        Args:
            use_cache: Se True, usa cache quando disponível
            expiration_hours: Tempo em horas para expiração do cache
        """
        # Configurar política de cache em todos os coletores
        self.materias.set_cache_policy(use_cache, expiration_hours)
        self.tramitacao.set_cache_policy(use_cache, expiration_hours)
        self.relatoria.set_cache_policy(use_cache, expiration_hours)
        self.autoria.set_cache_policy(use_cache, expiration_hours)
        self.votacao.set_cache_policy(use_cache, expiration_hours)
        self.texto.set_cache_policy(use_cache, expiration_hours)
        
        logger.info(f"Política de cache definida em todos os coletores: {'usar cache' if use_cache else 'não usar cache'}, "
                   f"expiração em {expiration_hours} horas")