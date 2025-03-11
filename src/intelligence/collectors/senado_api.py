# src/intelligence/collectors/senado_api.py
"""
Integração com a API de Dados Abertos do Senado Federal.
Este módulo fornece funções para consultar informações atualizadas sobre PLs.
"""
import requests
import logging
import json
import os
import xmltodict  # Para processar respostas XML
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("senado_api")

class SenadoAPI:
    """
    Cliente para a API de Dados Abertos do Senado Federal.
    Documentação: https://legis.senado.leg.br/dadosabertos/docs/ui/index.html
    """
    
    BASE_URL = "https://legis.senado.leg.br/dadosabertos"
    
    def __init__(self, cache_dir: str = None):
        """
        Inicializa o cliente da API do Senado.
        
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
            "User-Agent": "Regulatory Suite/0.1 (github.com/yourusername/regulatory_suite)"
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
            response = self.session.get(url, params=params)
            
            # Verificar resposta
            if response.status_code == 200:
                try:
                    # Verificar se é XML (o formato padrão da API do Senado)
                    if 'xml' in response.headers.get('Content-Type', '').lower():
                        import xmltodict
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
        except Exception as e:
            logger.error(f"Erro ao fazer requisição para {endpoint}: {str(e)}")
            return {}, False
    
    def get_pl_details(self, sigla: str, numero: str, ano: str) -> Dict:
        """
        Obtém detalhes de um PL específico.
        
        Args:
            sigla: Sigla do PL (ex: PL, PEC)
            numero: Número do PL
            ano: Ano do PL
            
        Returns:
            Dicionário com detalhes do PL
        """
        logger.info(f"Buscando detalhes do {sigla} {numero}/{ano} na API do Senado")
        
        # Endpoint para matéria legislativa
        endpoint = f"materia/{sigla}/{numero}/{ano}"
        
        # Fazer requisição
        data, from_cache = self._make_request(endpoint)
        
        # Se não veio do cache, processa os dados brutos
        if not from_cache:
            try:
                # Processar resposta
                materia = data.get('DetalheMateria', {}).get('Materia', {})
                
                if not materia:
                    logger.warning(f"PL {sigla} {numero}/{ano} não encontrado na API do Senado")
                    return {}
                
                # Extrair código da matéria (para buscar situação atual)
                codigo_materia = materia.get('IdentificacaoMateria', {}).get('CodigoMateria')
                
                # Dados básicos
                processed_data = {
                    "Título": materia.get('DadosBasicosMateria', {}).get('EmentaMateria', ''),
                    "Data": materia.get('DadosBasicosMateria', {}).get('DataApresentacao', ''),
                    "Autor": self._extract_autor(materia),
                    "Status": "Em tramitação",  # Será atualizado com dados da situação atual
                    "URL": self._build_pl_url(sigla, numero, ano),
                    "Palavras-chave": materia.get('DadosBasicosMateria', {}).get('IndexacaoMateria', ''),
                    "Situacao": {
                        "Local": "",
                        "Situacao": "",
                        "Data": ""
                    },
                    "Tramitacao": []
                }
                
                # Se temos o código da matéria, buscar situação atual (mais confiável)
                if codigo_materia:
                    situacao_endpoint = f"materia/situacaoatual/{codigo_materia}"
                    situacao_data, situacao_from_cache = self._make_request(situacao_endpoint)
                    
                    if situacao_data:
                        try:
                            situacao = situacao_data.get('SituacaoAtualMateria', {}).get('Materia', {})
                            
                            if situacao:
                                # Atualizar status e situação
                                local = situacao.get('Local', {}).get('NomeLocal', '')
                                situacao_desc = situacao.get('Situacao', {}).get('DescricaoSituacao', '')
                                data_situacao = situacao.get('Situacao', {}).get('DataSituacao', '')
                                
                                # Atualizar com dados mais precisos
                                if local or situacao_desc:
                                    processed_data["Status"] = f"{situacao_desc} - {local}" if situacao_desc and local else (situacao_desc or local or "Em tramitação")
                                
                                processed_data["Situacao"] = {
                                    "Local": local,
                                    "Situacao": situacao_desc,
                                    "Data": data_situacao
                                }
                        except Exception as e:
                            logger.error(f"Erro ao processar situação atual do PL {sigla} {numero}/{ano}: {str(e)}")
                
                # Buscar tramitação detalhada se disponível
                tramitacao_data = self.get_pl_tramitacao(sigla, numero, ano)
                if tramitacao_data:
                    processed_data["Tramitacao_Detalhada"] = tramitacao_data
                
                return processed_data
            except Exception as e:
                logger.error(f"Erro ao processar dados do PL {sigla} {numero}/{ano}: {str(e)}")
                return {}
        else:
            # Se veio do cache, retorna diretamente
            return data
    
    def get_pl_tramitacao(self, sigla: str, numero: str, ano: str) -> List[Dict]:
        """
        Obtém o histórico de tramitação de um PL.
        
        Args:
            sigla: Sigla do PL (ex: PL, PEC)
            numero: Número do PL
            ano: Ano do PL
            
        Returns:
            Lista de eventos da tramitação
        """
        logger.info(f"Buscando tramitação do {sigla} {numero}/{ano} na API do Senado")
        
        # Primeiro, tentamos obter o código da matéria (mais confiável para buscar movimentações)
        codigo_materia = None
        
        # Endpoint para detalhes da matéria
        endpoint_detalhe = f"materia/{sigla}/{numero}/{ano}"
        
        # Fazer requisição
        detalhes, from_cache = self._make_request(endpoint_detalhe)
        
        if detalhes:
            try:
                codigo_materia = detalhes.get('DetalheMateria', {}).get('Materia', {}).get('IdentificacaoMateria', {}).get('CodigoMateria')
            except Exception as e:
                logger.error(f"Erro ao extrair código da matéria: {str(e)}")
        
        # Se temos o código da matéria, usamos o endpoint de movimentações (mais confiável)
        if codigo_materia:
            # Endpoint para movimentações
            endpoint = f"materia/movimentacoes/{codigo_materia}"
            
            # Fazer requisição
            data, from_cache = self._make_request(endpoint)
            
            # Processar resposta
            if not from_cache:
                try:
                    movimentacoes = data.get('MovimentacaoMateria', {}).get('Movimentacoes', {}).get('Movimentacao', [])
                    
                    # Garantir que seja uma lista
                    if not isinstance(movimentacoes, list):
                        movimentacoes = [movimentacoes]
                    
                    # Extrair dados relevantes
                    processed_data = []
                    for evento in movimentacoes:
                        processed_data.append({
                            "Data": evento.get('DataMovimentacao', ''),
                            "Local": evento.get('Local', {}).get('NomeLocal', ''),
                            "Situacao": evento.get('Situacao', {}).get('DescricaoSituacao', ''),
                            "Texto": evento.get('TextoMovimentacao', '')
                        })
                    
                    # Ordenar por data (mais recente primeiro)
                    processed_data.sort(key=lambda x: x.get('Data', ''), reverse=True)
                    
                    return processed_data
                except Exception as e:
                    logger.error(f"Erro ao processar movimentações do PL {sigla} {numero}/{ano}: {str(e)}")
            else:
                # Se veio do cache, retorna diretamente
                return data
        
        # Caso o método acima falhe, tentamos a URL direta de tramitação (método original)
        endpoint_tramitacao = f"materia/tramitacao/{sigla}/{numero}/{ano}"
        
        # Fazer requisição
        data, from_cache = self._make_request(endpoint_tramitacao)
        
        # Processar resposta
        if not from_cache:
            try:
                tramitacao = data.get('TramitacaoMateria', {}).get('Tramitacoes', {}).get('Tramitacao', [])
                
                # Garantir que seja uma lista
                if not isinstance(tramitacao, list):
                    tramitacao = [tramitacao]
                
                # Extrair dados relevantes
                processed_data = []
                for evento in tramitacao:
                    processed_data.append({
                        "Data": evento.get('DataTramitacao', ''),
                        "Local": evento.get('IdentificacaoLocal', ''),
                        "Situacao": evento.get('SituacaoTramitacao', {}).get('DescricaoSituacao', ''),
                        "Texto": evento.get('TextoTramitacao', '')
                    })
                
                # Ordenar por data (mais recente primeiro)
                processed_data.sort(key=lambda x: x.get('Data', ''), reverse=True)
                
                return processed_data
            except Exception as e:
                logger.error(f"Erro ao processar tramitação do PL {sigla} {numero}/{ano}: {str(e)}")
                # Retornar lista vazia em caso de erro
                return []
        else:
            # Se veio do cache, retorna diretamente
            return data
    
    def search_pls(self, keywords: List[str] = None, autor: str = None, 
                  situacao: str = None, limit: int = 20) -> List[Dict]:
        """
        Busca PLs por palavras-chave, autor ou situação.
        
        Args:
            keywords: Lista de palavras-chave para buscar no título/ementa
            autor: Nome do autor para filtrar
            situacao: Situação do PL (ex: "Em tramitação")
            limit: Número máximo de resultados
            
        Returns:
            Lista de PLs encontrados
        """
        logger.info(f"Buscando PLs por: keywords={keywords}, autor={autor}, situacao={situacao}")
        
        # Endpoint para pesquisa
        endpoint = "materia/pesquisa/lista"
        
        # Parâmetros da busca
        params = {
            "tipomateria": "PL",  # Tipo de matéria: Projeto de Lei
            "numero": "",
            "ano": "",
            "palavraschave": " ".join(keywords) if keywords else "",
            "autor": autor or "",
            "situacao": situacao or "",
            "limit": limit
        }
        
        # Fazer requisição
        data, from_cache = self._make_request(endpoint, params)
        
        # Processar resposta
        if not from_cache:
            try:
                materias = data.get('PesquisaBasicaMateria', {}).get('Materias', {}).get('Materia', [])
                
                # Garantir que seja uma lista
                if not isinstance(materias, list):
                    materias = [materias]
                
                # Extrair dados relevantes
                processed_data = []
                for materia in materias:
                    # Extrair sigla, número e ano do IdentificacaoMateria
                    identificacao = materia.get('IdentificacaoMateria', {})
                    sigla = identificacao.get('SiglaSubtipoMateria', '')
                    numero = identificacao.get('NumeroMateria', '')
                    ano = identificacao.get('AnoMateria', '')
                    
                    processed_data.append({
                        "ID": f"{sigla} {numero}/{ano}",
                        "Sigla": sigla,
                        "Numero": numero,
                        "Ano": ano,
                        "Título": materia.get('EmentaMateria', ''),
                        "Data": materia.get('DataApresentacao', ''),
                        "Autor": self._extract_autor(materia),
                        "Status": self._extract_status(materia),
                        "URL": self._build_pl_url(sigla, numero, ano)
                    })
                
                return processed_data
            except Exception as e:
                logger.error(f"Erro ao processar resultados da busca: {str(e)}")
                return []
        else:
            # Se veio do cache, retorna diretamente
            return data
    
    def get_recent_pls(self, limit: int = 10) -> List[Dict]:
        """
        Retorna os PLs mais recentes.
        
        Args:
            limit: Número máximo de PLs a retornar
            
        Returns:
            Lista com os PLs mais recentes
        """
        logger.info(f"Buscando os {limit} PLs mais recentes")
        
        # Endpoint para materias recentes
        endpoint = "materia/pesquisa/lista"
        
        # Parâmetros da busca
        params = {
            "tipomateria": "PL",  # Tipo de matéria: Projeto de Lei
            "ordenacao": "ULTALT_DESC",  # Ordenação por data de apresentação (mais recentes primeiro)
            "limit": limit
        }
        
        # Fazer requisição
        data, from_cache = self._make_request(endpoint, params)
        
        # Processar resposta
        if not from_cache:
            try:
                materias = data.get('PesquisaBasicaMateria', {}).get('Materias', {}).get('Materia', [])
                
                # Garantir que seja uma lista
                if not isinstance(materias, list):
                    materias = [materias]
                
                # Extrair dados relevantes
                processed_data = []
                for materia in materias:
                    # Extrair sigla, número e ano do IdentificacaoMateria
                    identificacao = materia.get('IdentificacaoMateria', {})
                    sigla = identificacao.get('SiglaSubtipoMateria', '')
                    numero = identificacao.get('NumeroMateria', '')
                    ano = identificacao.get('AnoMateria', '')
                    
                    processed_data.append({
                        "ID": f"{sigla} {numero}/{ano}",
                        "Sigla": sigla,
                        "Numero": numero,
                        "Ano": ano,
                        "Título": materia.get('EmentaMateria', ''),
                        "Data": materia.get('DataApresentacao', ''),
                        "Autor": self._extract_autor(materia),
                        "Status": self._extract_status(materia),
                        "URL": self._build_pl_url(sigla, numero, ano)
                    })
                
                return processed_data
            except Exception as e:
                logger.error(f"Erro ao processar PLs recentes: {str(e)}")
                return []
        else:
            # Se veio do cache, retorna diretamente
            return data
    
    def _extract_autor(self, materia: Dict) -> str:
        """
        Extrai o nome do autor de uma matéria.
        
        Args:
            materia: Dados da matéria
            
        Returns:
            Nome do autor
        """
        try:
            # Primeiro, tentar pegar do DadosBasicosMateria
            autor_basico = materia.get('DadosBasicosMateria', {}).get('Autor', '')
            if autor_basico:
                return autor_basico
            
            # Se não tiver lá, tentar na Autoria
            autoria = materia.get('Autoria', {}).get('Autor', [])
            
            # Garantir que seja uma lista
            if not isinstance(autoria, list):
                autoria = [autoria]
            
            # Extrair nomes dos autores
            autores = []
            for autor in autoria:
                nome = autor.get('NomeAutor', '')
                if nome:
                    autores.append(nome)
            
            # Retornar string com autores separados por vírgula
            return ", ".join(autores) if autores else "Não informado"
        except Exception as e:
            logger.error(f"Erro ao extrair autor: {str(e)}")
            return "Não informado"
    
    def _extract_status(self, materia: Dict) -> str:
        """
        Extrai o status atual de uma matéria.
        
        Args:
            materia: Dados da matéria
            
        Returns:
            Status atual
        """
        try:
            situacao = materia.get('SituacaoAtual', {}).get('Situacao', {})
            local = materia.get('SituacaoAtual', {}).get('Local', {})
            
            descricao = situacao.get('DescricaoSituacao', '')
            nome_local = local.get('NomeLocal', '')
            
            if descricao and nome_local:
                return f"{descricao} - {nome_local}"
            elif descricao:
                return descricao
            elif nome_local:
                return f"Em tramitação - {nome_local}"
            else:
                return "Status não informado"
        except Exception as e:
            logger.error(f"Erro ao extrair status: {str(e)}")
            return "Status não informado"
    
    def _extract_keywords(self, materia: Dict) -> str:
        """
        Extrai palavras-chave de uma matéria.
        
        Args:
            materia: Dados da matéria
            
        Returns:
            String com palavras-chave separadas por vírgula
        """
        try:
            # Extrair da indexação na estrutura correta
            indexacao = materia.get('DadosBasicosMateria', {}).get('IndexacaoMateria', '')
            return indexacao
        except Exception as e:
            logger.error(f"Erro ao extrair palavras-chave: {str(e)}")
            return ""
    
    def _extract_tramitacao(self, materia: Dict) -> List[Dict]:
        """
        Extrai os últimos eventos da tramitação de uma matéria.
        
        Args:
            materia: Dados da matéria
            
        Returns:
            Lista com os últimos eventos da tramitação
        """
        try:
            # Os dados básicos da matéria geralmente não incluem tramitação detalhada
            # Este método é um placeholder para quando a API retornar tramitação no detalhe da matéria
            return []
        except Exception as e:
            logger.error(f"Erro ao extrair tramitação: {str(e)}")
            return []
    
    def _build_pl_url(self, sigla: str, numero: str, ano: str) -> str:
        """
        Constrói a URL para acessar o PL no site do Senado.
        
        Args:
            sigla: Sigla do PL
            numero: Número do PL
            ano: Ano do PL
            
        Returns:
            URL para acessar o PL
        """
        return f"https://www25.senado.leg.br/web/atividade/materias/-/materia/{numero}{ano}"


# Exemplo de uso
if __name__ == "__main__":
    import sys
    
    api = SenadoAPI()
    
    # Se for fornecido um PL específico
    if len(sys.argv) == 4:
        sigla = sys.argv[1]
        numero = sys.argv[2]
        ano = sys.argv[3]
        
        print(f"Buscando detalhes do {sigla} {numero}/{ano}...")
        pl_details = api.get_pl_details(sigla, numero, ano)
        
        # Exibir detalhes
        if pl_details:
            print("\nDetalhes do PL:")
            print(f"Título: {pl_details.get('Título', 'N/A')}")
            print(f"Data: {pl_details.get('Data', 'N/A')}")
            print(f"Autor: {pl_details.get('Autor', 'N/A')}")
            print(f"Status: {pl_details.get('Status', 'N/A')}")
            print(f"URL: {pl_details.get('URL', 'N/A')}")
            
            # Situação atual
            situacao = pl_details.get('Situacao', {})
            print("\nSituação Atual:")
            print(f"Local: {situacao.get('Local', 'N/A')}")
            print(f"Situação: {situacao.get('Situacao', 'N/A')}")
            print(f"Data: {situacao.get('Data', 'N/A')}")
            
            # Tramitação detalhada
            tramitacao = pl_details.get('Tramitacao_Detalhada', [])
            if tramitacao:
                print("\nÚltimos eventos da tramitação:")
                for i, evento in enumerate(tramitacao[:5], 1):
                    print(f"{i}. {evento.get('Data', 'N/A')} - {evento.get('Situacao', 'N/A')} ({evento.get('Local', 'N/A')})")
                    if evento.get('Texto', ''):
                        print(f"   {evento.get('Texto', '')}")
        else:
            print(f"PL {sigla} {numero}/{ano} não encontrado!")
    
    else:
        # Buscar PLs recentes
        print("Buscando PLs recentes...")
        recent_pls = api.get_recent_pls(limit=5)
        
        if recent_pls:
            print("\nPLs recentes:")
            for i, pl in enumerate(recent_pls, 1):
                print(f"{i}. {pl.get('ID', 'N/A')} - {pl.get('Título', 'N/A')[:100]}...")
                print(f"   Status: {pl.get('Status', 'N/A')}")
        else:
            print("Nenhum PL recente encontrado!")
        
        # Buscar PLs por palavra-chave
        print("\nBuscando PLs relacionados a 'apostas'...")
        pls_apostas = api.search_pls(keywords=["apostas"], limit=5)
        
        if pls_apostas:
            print("\nPLs relacionados a 'apostas':")
            for i, pl in enumerate(pls_apostas, 1):
                print(f"{i}. {pl.get('ID', 'N/A')} - {pl.get('Título', 'N/A')[:100]}...")
                print(f"   Status: {pl.get('Status', 'N/A')}")
        else:
            print("Nenhum PL relacionado a 'apostas' encontrado!")