# src/intelligence/collectors/senado/api_base.py
"""
Cliente base para a API do Senado com funções de cache e requisições HTTP.
"""
import os
import requests
import json
import logging
import xmltodict
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("senado_api_base")

class SenadoAPIBase:
    """Cliente base com funcionalidades comuns: cache, requisições HTTP"""
    BASE_URL = "https://legis.senado.leg.br/dadosabertos"
    
    def __init__(self, cache_dir: str = None):
        """
        Inicializa o cliente base da API do Senado.
        
        Args:
            cache_dir: Diretório para cache de respostas. Se None, usa o padrão.
        """
        # Definir diretório de cache
        if cache_dir is None:
            self.cache_dir = os.path.join(os.getcwd(), "data", "api_cache", "senado")
        else:
            self.cache_dir = cache_dir
        
        # Garantir que o diretório existe
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Configuração do cliente
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Regulatory Suite/0.1 (Analise de Impacto Regulatorio)"
        })
        
        # Flag para controle de uso de cache
        self.use_cache = True
        
        # Tempo de expiração do cache em segundos (12 horas)
        self.cache_expiration = 12 * 60 * 60
    
    def set_cache_policy(self, use_cache: bool, expiration_hours: int = 12):
        """
        Define a política de uso de cache.
        
        Args:
            use_cache: Se True, usa cache quando disponível
            expiration_hours: Tempo em horas para expiração do cache
        """
        self.use_cache = use_cache
        self.cache_expiration = expiration_hours * 60 * 60
        logger.info(f"Política de cache definida: {'usar cache' if use_cache else 'não usar cache'}, "
                   f"expiração em {expiration_hours} horas")
    
    def _get_cache_path(self, endpoint: str, params: Dict) -> str:
        """
        Retorna o caminho para um arquivo de cache específico.
        
        Args:
            endpoint: Endpoint da API
            params: Parâmetros da requisição
            
        Returns:
            Caminho completo para o arquivo de cache
        """
        # Criar uma chave única para o cache
        params_str = json.dumps(params, sort_keys=True)
        import hashlib
        params_hash = hashlib.md5(params_str.encode()).hexdigest()
        
        # Criar nome do arquivo sanitizado
        safe_endpoint = endpoint.replace('/', '_').replace('\\', '_')
        return os.path.join(self.cache_dir, f"{safe_endpoint}_{params_hash}.json")
    
    def _load_from_cache(self, endpoint: str, params: Dict) -> Optional[Dict]:
        """
        Carrega dados do cache se disponível e não expirado.
        
        Args:
            endpoint: Endpoint da API
            params: Parâmetros da requisição
            
        Returns:
            Dados do cache ou None se não disponível ou expirado
        """
        if not self.use_cache:
            return None
        
        cache_path = self._get_cache_path(endpoint, params)
        
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                
                # Verificar se o cache expirou
                cache_time = cached_data.get('_cache_time', 0)
                now = datetime.now().timestamp()
                
                if now - cache_time <= self.cache_expiration:
                    logger.info(f"Dados carregados do cache para {endpoint}")
                    return cached_data.get('data')
                else:
                    logger.info(f"Cache expirado para {endpoint}")
            except Exception as e:
                logger.error(f"Erro ao carregar do cache para {endpoint}: {str(e)}")
        
        return None
    
    def _save_to_cache(self, endpoint: str, params: Dict, data: Dict) -> bool:
        """
        Salva dados no cache.
        
        Args:
            endpoint: Endpoint da API
            params: Parâmetros da requisição
            data: Dados a serem salvos
            
        Returns:
            True se salvou com sucesso, False caso contrário
        """
        if not self.use_cache:
            return False
        
        cache_path = self._get_cache_path(endpoint, params)
        
        try:
            # Adicionar timestamp para expiração
            cache_data = {
                '_cache_time': datetime.now().timestamp(),
                'data': data
            }
            
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=4)
            
            logger.info(f"Dados salvos no cache para {endpoint}")
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar no cache para {endpoint}: {str(e)}")
            return False
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Tuple[Dict, bool]:
        """
        Faz uma requisição à API do Senado, com suporte a cache.
        
        Args:
            endpoint: Endpoint da API
            params: Parâmetros da requisição
            
        Returns:
            Tupla (dados da resposta, booleano indicando se veio do cache)
        """
        if params is None:
            params = {}
        
        # Verificar se existe no cache
        cached_data = self._load_from_cache(endpoint, params)
        if cached_data is not None:
            return cached_data, True
        
        # Construir URL
        url = f"{self.BASE_URL}/{endpoint}"
        
        try:
            # Fazer requisição
            response = self.session.get(url, params=params, timeout=30)
            
            # Verificar resposta
            if response.status_code == 200:
                try:
                    # Verificar se é XML (o formato padrão da API do Senado)
                    if 'xml' in response.headers.get('Content-Type', '').lower():
                        # Converter XML para dicionário
                        data = xmltodict.parse(response.content)
                    else:
                        # Tentar como JSON
                        data = response.json()
                    
                    # Salvar no cache
                    self._save_to_cache(endpoint, params, data)
                    
                    return data, False
                except Exception as e:
                    logger.error(f"Erro ao processar resposta para {endpoint}: {str(e)}")
                    logger.debug(f"Conteúdo da resposta: {response.text[:500]}...")
                    return {}, False
            else:
                logger.error(f"Erro {response.status_code} ao acessar {endpoint}: {response.text}")
                return {}, False
        except requests.exceptions.Timeout:
            logger.error(f"Timeout ao acessar {endpoint}")
            return {}, False
        except Exception as e:
            logger.error(f"Erro ao fazer requisição para {endpoint}: {str(e)}")
            return {}, False
    
    def _extract_codigo_materia(self, sigla: str, numero: str, ano: str) -> Optional[str]:
        """
        Extrai o código da matéria a partir de sigla, número e ano.
        
        Args:
            sigla: Sigla do PL (ex: PL, PEC)
            numero: Número do PL
            ano: Ano do PL
            
        Returns:
            Código da matéria ou None se não encontrado
        """
        # Endpoint para detalhes da matéria
        endpoint = f"materia/{sigla}/{numero}/{ano}"
        
        # Fazer requisição
        detalhes, from_cache = self._make_request(endpoint)
        
        if detalhes:
            try:
                return detalhes.get('DetalheMateria', {}).get('Materia', {}).get('IdentificacaoMateria', {}).get('CodigoMateria')
            except Exception as e:
                logger.error(f"Erro ao extrair código da matéria: {str(e)}")
        
        return None
