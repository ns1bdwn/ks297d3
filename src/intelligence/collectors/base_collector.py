# src/intelligence/collectors/base_collector.py
"""
Classe base para coletores de dados regulatórios.
Define a interface comum para diferentes fontes de dados.
"""
import os
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("base_collector")

class BaseCollector(ABC):
    """
    Classe base abstrata para coletores de dados regulatórios.
    Define a interface comum que deve ser implementada pelos coletores específicos.
    """
    
    def __init__(self, cache_dir: str = None):
        """
        Inicializa o coletor base.
        
        Args:
            cache_dir: Diretório para cache de dados. Se None, usa o padrão.
        """
        # Diretório base do projeto
        self.base_dir = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "..", ".."
        ))
        
        # Definir diretório de cache
        if cache_dir is None:
            self.cache_dir = os.path.join(self.base_dir, "data", "cache")
        else:
            self.cache_dir = cache_dir
        
        # Garantir que o diretório de cache existe
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Flag para controle de uso de cache
        self.use_cache = True
    
    def set_cache_policy(self, use_cache: bool):
        """
        Define a política de uso de cache.
        
        Args:
            use_cache: Se True, usa cache quando disponível
        """
        self.use_cache = use_cache
        logger.info(f"Política de cache definida: {'usar cache' if use_cache else 'não usar cache'}")
    
    @abstractmethod
    def get_pl_by_id(self, sigla: str, numero: str, ano: str) -> Dict[str, Any]:
        """
        Busca detalhes de um PL específico.
        
        Args:
            sigla: Sigla do PL (ex: PL, PEC)
            numero: Número do PL
            ano: Ano do PL
            
        Returns:
            Dicionário com detalhes do PL ou vazio se não encontrado
        """
        pass
    
    @abstractmethod
    def search_pls(self, keywords: List[str] = None, date_from: str = None, 
                  date_to: str = None, author: str = None) -> List[Dict[str, Any]]:
        """
        Busca PLs que correspondem aos critérios.
        
        Args:
            keywords: Lista de palavras-chave para buscar
            date_from: Data inicial no formato YYYY-MM-DD
            date_to: Data final no formato YYYY-MM-DD
            author: Nome do autor para filtrar
            
        Returns:
            Lista de PLs que correspondem aos critérios
        """
        pass
    
    @abstractmethod
    def get_recent_pls(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retorna os PLs mais recentes.
        
        Args:
            limit: Número máximo de PLs a retornar
            
        Returns:
            Lista com os PLs mais recentes
        """
        pass
    
    def _get_cache_path(self, key: str) -> str:
        """
        Retorna o caminho para um arquivo de cache específico.
        
        Args:
            key: Chave única para o arquivo de cache
            
        Returns:
            Caminho completo para o arquivo de cache
        """
        # Sanitizar a chave para uso como nome de arquivo
        safe_key = key.replace('/', '_').replace('\\', '_').replace(' ', '_')
        return os.path.join(self.cache_dir, f"{safe_key}.json")
    
    def _load_from_cache(self, key: str) -> Optional[Any]:
        """
        Carrega dados do cache se disponível.
        
        Args:
            key: Chave única para o cache
            
        Returns:
            Dados do cache ou None se não disponível
        """
        if not self.use_cache:
            return None
        
        cache_path = self._get_cache_path(key)
        
        if os.path.exists(cache_path):
            try:
                import json
                with open(cache_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                logger.info(f"Dados carregados do cache: {key}")
                return data
            except Exception as e:
                logger.error(f"Erro ao carregar do cache {key}: {str(e)}")
        
        return None
    
    def _save_to_cache(self, key: str, data: Any) -> bool:
        """
        Salva dados no cache.
        
        Args:
            key: Chave única para o cache
            data: Dados a serem salvos
            
        Returns:
            True se salvou com sucesso, False caso contrário
        """
        if not self.use_cache:
            return False
        
        cache_path = self._get_cache_path(key)
        
        try:
            import json
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            logger.info(f"Dados salvos no cache: {key}")
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar no cache {key}: {str(e)}")
            return False


# Exemplo de uso (não será executado diretamente, pois é uma classe abstrata)
if __name__ == "__main__":
    logger.info("BaseCollector é uma classe abstrata e não pode ser instanciada diretamente.")
    logger.info("Implemente uma classe concreta que herda de BaseCollector.")