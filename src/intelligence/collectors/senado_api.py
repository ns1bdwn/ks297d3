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
    
    def get_pl_by_id(self, sigla: str, numero: str, ano: str) -> Dict:
        """
        Obtém detalhes de um PL específico.
        
        Args:
            sigla: Sigla do PL (ex: PL, PEC)
            numero: Número do PL
            ano: Ano do PL
            
        Returns:
            Dicionário com detalhes do PL
        """
        logger.info(f"Buscando PL {sigla} {numero}/{ano} na API do Senado")
        
        # Endpoint para matéria legislativa
        endpoint = f"materia/{sigla}/{numero}/{ano}"
        
        # Fazer requisição
        data, from_cache = self._make_request(endpoint)
        
        if not data:
            logger.warning(f"PL {sigla} {numero}/{ano} não encontrado na API do Senado")
            return {}
        
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
                    "URL": self._build_pl_url(sigla, numero, ano, codigo_materia),
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
                
                # Buscar tramitação detalhada
                tramitacao_data = self.get_pl_tramitacao(sigla, numero, ano, codigo_materia)
                if tramitacao_data:
                    processed_data["Tramitacao"] = tramitacao_data
                
                # Adicionar o código da matéria para uso futuro
                processed_data["CodigoMateria"] = codigo_materia
                
                # Buscar relatores
                if codigo_materia:
                    relatores = self.get_pl_relatores(codigo_materia)
                    if relatores:
                        processed_data["Relatores"] = relatores
                
                return processed_data
            except Exception as e:
                logger.error(f"Erro ao processar dados do PL {sigla} {numero}/{ano}: {str(e)}")
                return {}
        else:
            # Se veio do cache, retorna diretamente
            return data
            
    def get_additional_pl_details(self, sigla: str, numero: str, ano: str) -> Dict[str, Any]:
        """
        Obtém detalhes adicionais de um PL específico, formatados para análise de risco.
        Este método é um wrapper compatível para o PLRiskAnalyzer.
        
        Args:
            sigla: Sigla do PL (ex: PL, PEC)
            numero: Número do PL
            ano: Ano do PL
            
        Returns:
            Dicionário com detalhes do PL formatados para análise de risco
        """
        # Chamar o método existente para obter detalhes básicos
        basic_details = self.get_pl_by_id(sigla, numero, ano)
        
        if not basic_details:
            return {}
        
        # Adicionar campos extras que o analisador de risco espera
        details = {
            **basic_details,  # Manter todos os campos existentes
            "detalhes_adicionais": {
                "autoria_detalhada": self._extract_autoria_details(basic_details),
                "projetos_relacionados": self._find_related_projects(sigla, numero, ano)
            }
        }
        
        # Garantir que a estrutura está completa com campos esperados pelo analisador
        if "Tramitacao" not in details:
            details["Tramitacao"] = []
        
        if "Tramitacao_Detalhada" not in details:
            details["Tramitacao_Detalhada"] = details["Tramitacao"]
        
        return details
    
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
        logger.info(f"Buscando tramitação do {sigla} {numero}/{ano} na API do Senado")
        
        # Se não temos o código da matéria, tentamos obter
        if not codigo_materia:
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
        
        # Caso o método acima falhe, tentamos a URL direta de tramitação
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

    def get_pl_relatores(self, codigo_materia: str) -> List[Dict]:
        """
        Obtém os relatores designados para um PL.
        
        Args:
            codigo_materia: Código da matéria
            
        Returns:
            Lista de relatores com informações detalhadas
        """
        logger.info(f"Buscando relatores para matéria {codigo_materia}")
        
        # Endpoint para relatoria
        endpoint = f"materia/relatoria/{codigo_materia}"
        
        # Fazer requisição
        data, from_cache = self._make_request(endpoint)
        
        # Processar resposta
        if not from_cache:
            try:
                relatoria = data.get('RelatoriaMateria', {}).get('Materia', {}).get('Relatoria', [])
                
                # Garantir que seja uma lista
                if not isinstance(relatoria, list):
                    relatoria = [relatoria]
                
                # Extrair dados relevantes
                relatores = []
                for rel in relatoria:
                    parlamentar = rel.get('Parlamentar', {})
                    comissao = rel.get('Comissao', {})
                    
                    relatores.append({
                        "Nome": parlamentar.get('NomeParlamentar', ''),
                        "Partido": parlamentar.get('SiglaPartidoParlamentar', ''),
                        "UF": parlamentar.get('UfParlamentar', ''),
                        "Comissao": comissao.get('NomeComissao', ''),
                        "SiglaComissao": comissao.get('SiglaComissao', ''),
                        "DataDesignacao": rel.get('DataDesignacao', ''),
                        "DataDestituicao": rel.get('DataDestituicao', '')
                    })
                
                return relatores
            except Exception as e:
                logger.error(f"Erro ao processar relatores da matéria {codigo_materia}: {str(e)}")
                return []
        else:
            # Se veio do cache, retorna diretamente
            return data
    
    def search_pls(self, keywords: List[str] = None, date_from: str = None, 
                  date_to: str = None, author: str = None, limit: int = 20) -> List[Dict]:
        """
        Busca PLs por palavras-chave, autor ou situação.
        
        Args:
            keywords: Lista de palavras-chave para buscar no título/ementa
            date_from: Data inicial no formato YYYYMMDD
            date_to: Data final no formato YYYYMMDD
            author: Nome do autor para filtrar
            limit: Número máximo de resultados
            
        Returns:
            Lista de PLs encontrados
        """
        logger.info(f"Buscando PLs por: keywords={keywords}, author={author}")
        
        # Endpoint para pesquisa
        endpoint = "materia/pesquisa/lista"
        
        # Parâmetros da busca
        params = {
            "sigla": "PL",  # Tipo de matéria: Projeto de Lei
            "numero": "",
            "ano": "",
            "palavras": " ".join(keywords) if keywords else "",
            "autor": author or "",
            "dataInicio": date_from or "",
            "dataFim": date_to or "",
            "catalogo": "",
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
                    codigo = identificacao.get('CodigoMateria', '')
                    
                    processed_data.append({
                        "ID": f"{sigla} {numero}/{ano}",
                        "Sigla": sigla,
                        "Numero": numero,
                        "Ano": ano,
                        "CodigoMateria": codigo,
                        "Título": materia.get('EmentaMateria', ''),
                        "Data": materia.get('DataApresentacao', ''),
                        "Autor": self._extract_autor_from_search(materia),
                        "Status": self._extract_status_from_search(materia),
                        "URL": self._build_pl_url(sigla, numero, ano, codigo),
                        "Palavras-chave": ""  # A API de pesquisa não retorna palavras-chave diretamente
                    })
                
                return processed_data
            except Exception as e:
                logger.error(f"Erro ao processar resultados da busca: {str(e)}")
                return []
        else:
            # Se veio do cache, retorna diretamente
            return data
    
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
        import pandas as pd
        logger.info(f"Buscando PLs para {len(keywords)} palavras-chave")
        
        all_results = []
        matched_keywords = {}
        
        # Buscar para cada palavra-chave
        for keyword in keywords:
            try:
                results = self.search_pls(
                    keywords=[keyword], 
                    date_from=start_date, 
                    date_to=end_date,
                    limit=limit
                )
                
                # Registrar correspondências de palavras-chave
                for result in results:
                    pl_id = result['ID']
                    if pl_id not in matched_keywords:
                        matched_keywords[pl_id] = []
                    matched_keywords[pl_id].append(keyword)
                
                all_results.extend(results)
            except Exception as e:
                logger.error(f"Erro ao buscar PLs para palavra-chave '{keyword}': {str(e)}")
        
        # Remover duplicatas (mesmo PL encontrado por palavras-chave diferentes)
        unique_results = {}
        for result in all_results:
            pl_id = result['ID']
            if pl_id not in unique_results:
                unique_results[pl_id] = result
                
                # Adicionar palavras-chave correspondidas
                if pl_id in matched_keywords:
                    result['Palavras-chave Correspondidas'] = ', '.join(matched_keywords[pl_id])
        
        # Converter para DataFrame
        if unique_results:
            df = pd.DataFrame(list(unique_results.values()))
            
            # Tentar buscar palavras-chave para cada resultado
            try:
                self._enrich_with_keywords(df)
                logger.info(f"Resultados da busca enriquecidos com palavras-chave para {len(df)} PLs")
            except Exception as e:
                logger.error(f"Erro ao enriquecer resultados com palavras-chave: {str(e)}")
            
            return df
        else:
            # Retornar DataFrame vazio com colunas esperadas
            return pd.DataFrame(columns=[
                'ID', 'Sigla', 'Numero', 'Ano', 'CodigoMateria', 'Título', 'Data', 
                'Autor', 'Status', 'URL', 'Palavras-chave', 'Palavras-chave Correspondidas'
            ])

    def _enrich_with_keywords(self, df: pd.DataFrame) -> None:
        """
        Enriquece o DataFrame de resultados com palavras-chave buscando detalhes adicionais.
        
        Args:
            df: DataFrame com resultados de busca
        """
        # Para cada PL, tentar buscar suas palavras-chave
        for i, row in df.iterrows():
            try:
                sigla = row['Sigla']
                numero = row['Numero']
                ano = row['Ano']
                
                # Buscar detalhes apenas se não tivermos palavras-chave
                if not row.get('Palavras-chave'):
                    details = self.get_pl_by_id(sigla, numero, ano)
                    if details and 'Palavras-chave' in details:
                        df.at[i, 'Palavras-chave'] = details['Palavras-chave']
            except Exception as e:
                logger.warning(f"Erro ao enriquecer PL {row['ID']} com palavras-chave: {str(e)}")
    
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
            "sigla": "PL",  # Tipo de matéria: Projeto de Lei
            "ordenacao": "DTAPRES_DESC",  # Ordenação por data de apresentação (mais recentes primeiro)
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
                    codigo = identificacao.get('CodigoMateria', '')
                    
                    processed_data.append({
                        "ID": f"{sigla} {numero}/{ano}",
                        "Sigla": sigla,
                        "Numero": numero,
                        "Ano": ano,
                        "CodigoMateria": codigo,
                        "Título": materia.get('EmentaMateria', ''),
                        "Data": materia.get('DataApresentacao', ''),
                        "Autor": self._extract_autor_from_search(materia),
                        "Status": self._extract_status_from_search(materia),
                        "URL": self._build_pl_url(sigla, numero, ano, codigo)
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
        Extrai o nome do autor de uma matéria detalhada.
        
        Args:
            materia: Dados da matéria
            
        Returns:
            Nome do autor
        """
        try:
            # Primeiro, tentar pegar do DadosBasicosMateria
            autor_basico = materia.get('DadosBasicosMateria', {}).get('NomeAutor', '')
            if autor_basico:
                return autor_basico
            
            # Se não tiver lá, tentar na Autoria
            autoria = materia.get('Autoria', {})
            if isinstance(autoria, dict):
                autores = autoria.get('Autor', [])
                
                # Garantir que seja uma lista
                if not isinstance(autores, list):
                    autores = [autores]
                
                # Extrair nomes dos autores
                nomes_autores = []
                for autor in autores:
                    nome = autor.get('NomeAutor', '')
                    if nome:
                        nomes_autores.append(nome)
                
                # Retornar string com autores separados por vírgula
                return ", ".join(nomes_autores) if nomes_autores else "Não informado"
            
            return "Não informado"
        except Exception as e:
            logger.error(f"Erro ao extrair autor: {str(e)}")
            return "Não informado"
    
    def _extract_autor_from_search(self, materia: Dict) -> str:
        """
        Extrai o nome do autor de uma matéria retornada pela pesquisa.
        
        Args:
            materia: Dados da matéria da pesquisa
            
        Returns:
            Nome do autor
        """
        try:
            # Na pesquisa, o autor pode estar em formato diferente
            autor = materia.get('AutoriaMateria', {})
            if autor:
                autor_nome = autor.get('Autor', {}).get('NomeAutor', '')
                if autor_nome:
                    return autor_nome
            
            return "Não informado"
        except Exception as e:
            logger.error(f"Erro ao extrair autor da pesquisa: {str(e)}")
            return "Não informado"
    
    def _extract_status_from_search(self, materia: Dict) -> str:
        """
        Extrai o status atual de uma matéria retornada pela pesquisa.
        
        Args:
            materia: Dados da matéria da pesquisa
            
        Returns:
            Status atual
        """
        try:
            situacao = materia.get('SituacaoAtual', {})
            if situacao:
                situacao_desc = situacao.get('Descricao', {}).get('DescricaoSituacao', '')
                local = situacao.get('Local', {}).get('NomeLocal', '')
                
                if situacao_desc and local:
                    return f"{situacao_desc} - {local}"
                elif situacao_desc:
                    return situacao_desc
                elif local:
                    return f"Em tramitação - {local}"
            
            return "Status não informado"
        except Exception as e:
            logger.error(f"Erro ao extrair status da pesquisa: {str(e)}")
            return "Status não informado"
    
    def _build_pl_url(self, sigla: str, numero: str, ano: str, codigo_materia: str = None) -> str:
        """
        Constrói a URL para acessar o PL no site do Senado.
        
        Args:
            sigla: Sigla do PL
            numero: Número do PL
            ano: Ano do PL
            codigo_materia: Código da matéria (para URL mais precisa)
            
        Returns:
            URL para acessar o PL
        """
        if codigo_materia:
            return f"https://www25.senado.leg.br/web/atividade/materias/-/materia/{codigo_materia}"
        else:
            return f"https://www25.senado.leg.br/web/atividade/materias/-/materia/busca?b_pesquisaMaterias=proposicao_PL_Projeto+de+Lei_{numero}_{ano}"
    
    def _extract_autoria_details(self, pl_details: Dict) -> List[Dict]:
        """
        Extrai detalhes de autoria de um PL.
        
        Args:
            pl_details: Detalhes do PL
            
        Returns:
            Lista com informações dos autores
        """
        autores = []
        autor_principal = pl_details.get('Autor', '')
        
        if autor_principal:
            # Tentar extrair partido/UF do nome do autor (formato comum: "Nome (Partido/UF)")
            import re
            partido_uf_match = re.search(r'\((.*?)\)', autor_principal)
            if partido_uf_match:
                partido_uf = partido_uf_match.group(1)
                # Tentar separar partido e UF
                if '/' in partido_uf:
                    partido, uf = partido_uf.split('/')
                else:
                    partido, uf = partido_uf, ""
                    
                # Limpar nome do autor (remover partido/UF)
                nome = autor_principal.replace(f"({partido_uf})", "").strip()
            else:
                nome = autor_principal
                partido, uf = "", ""
            
            # Determinar tipo de autor
            tipo = "Parlamentar"  # Tipo padrão
            if "Senador" in nome or "Senadora" in nome:
                tipo = "Parlamentar"
            elif "Executivo" in nome or "Presidente" in nome:
                tipo = "Poder Executivo"
            elif "Comissão" in nome:
                tipo = "Comissão"
            
            autores.append({
                "nome": nome,
                "tipo": tipo,
                "partido": partido,
                "uf": uf
            })
        
        return autores

    def _find_related_projects(self, sigla: str, numero: str, ano: str) -> List[Dict]:
        """
        Busca projetos de lei relacionados com o PL atual.
        
        Args:
            sigla: Sigla do PL 
            numero: Número do PL
            ano: Ano do PL
            
        Returns:
            Lista de projetos relacionados
        """
        # Implementação simplificada - em produção isso usaria
        # algoritmos de similaridade, palavras-chave comuns, etc.
        try:
            # Buscar PLs recentes para simular relacionados
            related_pls = self.get_recent_pls(limit=5)
            
            # Filtrar o próprio PL
            current_id = f"{sigla} {numero}/{ano}"
            related_pls = [pl for pl in related_pls if pl.get('ID') != current_id]
            
            # Limitar a 2-3 projetos relacionados
            return related_pls[:3]
        except Exception as e:
            logger.error(f"Erro ao buscar projetos relacionados: {str(e)}")
            return []

# Testes básicos
if __name__ == "__main__":
    api = SenadoAPI()
    
    # Teste: buscar PL específico
    pl = api.get_pl_by_id("PL", "2234", "2022")
    print(f"Detalhes do PL 2234/2022:")
    if pl:
        print(f"  Título: {pl.get('Título', '')[:100]}...")
        print(f"  Autor: {pl.get('Autor', '')}")
        print(f"  Status: {pl.get('Status', '')}")
        print(f"  URL: {pl.get('URL', '')}")
        
        # Verificar se tem relatores
        if 'Relatores' in pl:
            print("\nRelatores:")
            for relator in pl['Relatores']:
                print(f"  {relator.get('Nome', '')} ({relator.get('Partido', '')}/{relator.get('UF', '')}) - {relator.get('Comissao', '')}")
    else:
        print("PL não encontrado")
    
    # Teste: buscar por palavras-chave
    print("\nBusca por 'apostas':")
    results = api.search_pls(keywords=["apostas"], limit=5)
    for i, res in enumerate(results):
        print(f"{i+1}. {res['ID']}: {res['Título'][:100]}...")