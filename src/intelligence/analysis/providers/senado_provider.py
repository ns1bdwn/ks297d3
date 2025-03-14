"""
Adaptador para a API do Senado Federal.
"""
import re
import logging
import json
import os
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
        
        # Caminho para cache de API
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(script_dir, "../../../.."))
        self.cache_dir = os.path.join(project_root, "data", "api_cache", "senado")
    
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
            
            # Verificar cache de API diretamente
            success, details = self._check_api_cache(sigla, numero, ano)
            if success and details:
                logger.info(f"Detalhes do PL {sigla} {numero}/{ano} obtidos do cache de API")
                return details
            
            # Se não encontrou no cache, buscar detalhes usando a API do Senado
            details = self.api.get_additional_pl_details(sigla, numero, ano)
            
            # Verificar se os detalhes são válidos
            if not isinstance(details, dict):
                logger.error(f"API do Senado retornou um tipo inválido para detalhes do PL: {type(details)}")
                return {}
            
            return details
        except Exception as e:
            logger.error(f"Erro ao obter detalhes do PL {pl_id_info}: {str(e)}")
            return {}
    
    def _check_api_cache(self, sigla: str, numero: str, ano: str) -> tuple[bool, Optional[Dict[str, Any]]]:
        """
        Verifica o cache da API diretamente para buscar detalhes do PL.
        
        Args:
            sigla: Sigla do PL
            numero: Número do PL
            ano: Ano do PL
            
        Returns:
            Tupla (boolean indicando sucesso, dicionário com detalhes ou None)
        """
        try:
            # Primeiro, tentar encontrar o arquivo de detalhes da matéria
            materia_pattern = f"materia_{sigla}_{numero}_{ano}_*.json"
            
            import glob
            materia_files = glob.glob(os.path.join(self.cache_dir, materia_pattern))
            
            if not materia_files:
                return False, None
            
            # Usar o arquivo mais recente
            materia_file = sorted(materia_files)[-1]
            
            with open(materia_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
            
            if not cached_data or 'data' not in cached_data:
                return False, None
            
            # Construir detalhes completos
            details = {}
            
            # Informações básicas da matéria
            materia_data = cached_data['data']
            if 'DetalheMateria' in materia_data:
                materia = materia_data['DetalheMateria'].get('Materia', {})
                
                if materia:
                    # Extrair código da matéria
                    codigo_materia = materia.get('IdentificacaoMateria', {}).get('CodigoMateria')
                    
                    # Dados básicos
                    dados_basicos = materia.get('DadosBasicosMateria', {})
                    
                    details = {
                        "Sigla": sigla,
                        "Numero": numero,
                        "Ano": ano,
                        "CodigoMateria": codigo_materia,
                        "Título": dados_basicos.get('EmentaMateria', ''),
                        "Data": dados_basicos.get('DataApresentacao', ''),
                        "Autor": self._extract_autor_from_materia(materia),
                        "Status": "Em tramitação",  # Será atualizado com situação
                        "URL": self._build_pl_url(sigla, numero, ano, codigo_materia),
                        "Palavras-chave": dados_basicos.get('IndexacaoMateria', '')
                    }
            
            # Buscar situação atual
            situacao_pattern = f"materia_situacaoatual_*.json"
            situacao_files = glob.glob(os.path.join(self.cache_dir, situacao_pattern))
            
            situacao = {
                "Local": "",
                "Situacao": "",
                "Data": ""
            }
            
            if situacao_files:
                situacao_file = sorted(situacao_files)[-1]
                
                with open(situacao_file, 'r', encoding='utf-8') as f:
                    situacao_data = json.load(f)
                
                if 'data' in situacao_data:
                    situacao_info = situacao_data['data'].get('SituacaoAtualMateria', {}).get('Materia', {})
                    
                    if situacao_info:
                        local = situacao_info.get('Local', {}).get('NomeLocal', '')
                        situacao_desc = situacao_info.get('Situacao', {}).get('DescricaoSituacao', '')
                        data_situacao = situacao_info.get('Situacao', {}).get('DataSituacao', '')
                        
                        situacao = {
                            "Local": local,
                            "Situacao": situacao_desc,
                            "Data": data_situacao
                        }
                        
                        # Atualizar status
                        if local or situacao_desc:
                            details["Status"] = f"{situacao_desc} - {local}" if situacao_desc and local else (situacao_desc or local or "Em tramitação")
            
            details["Situacao"] = situacao
            
            # Buscar tramitação
            try:
                tramitacao_pattern = f"materia_movimentacoes_*.json"
                tramitacao_files = glob.glob(os.path.join(self.cache_dir, tramitacao_pattern))
                
                tramitacao = []
                
                if tramitacao_files:
                    tramitacao_file = sorted(tramitacao_files)[-1]
                    
                    with open(tramitacao_file, 'r', encoding='utf-8') as f:
                        tramitacao_data = json.load(f)
                    
                    if 'data' in tramitacao_data:
                        movimentacoes = tramitacao_data['data'].get('MovimentacaoMateria', {}).get('Movimentacoes', {}).get('Movimentacao', [])
                        
                        # Garantir que seja uma lista
                        if not isinstance(movimentacoes, list):
                            movimentacoes = [movimentacoes]
                        
                        # Processar cada evento
                        for evento in movimentacoes:
                            tramitacao.append({
                                "Data": evento.get('DataMovimentacao', ''),
                                "Local": evento.get('Local', {}).get('NomeLocal', ''),
                                "SiglaLocal": evento.get('Local', {}).get('SiglaLocal', ''),
                                "Situacao": evento.get('Situacao', {}).get('DescricaoSituacao', ''),
                                "Texto": evento.get('TextoMovimentacao', '')
                            })
                        
                        # Ordenar por data (mais recente primeiro)
                        tramitacao.sort(key=lambda x: x.get('Data', ''), reverse=True)
                
                details["Tramitacao_Detalhada"] = tramitacao
            except Exception as e:
                logger.error(f"Erro ao processar tramitação do cache: {str(e)}")
            
            # Buscar relatores
            try:
                relatoria_pattern = f"materia_relatorias_*.json"
                relatoria_files = glob.glob(os.path.join(self.cache_dir, relatoria_pattern))
                
                relatores = []
                
                if relatoria_files:
                    relatoria_file = sorted(relatoria_files)[-1]
                    
                    with open(relatoria_file, 'r', encoding='utf-8') as f:
                        relatoria_data = json.load(f)
                    
                    if 'data' in relatoria_data:
                        # Processar relatoria atual
                        relatoria_atual = relatoria_data['data'].get('RelatoriaMateria', {}).get('RelatoriaAtual', {})
                        if relatoria_atual:
                            relator = self._processar_relator(relatoria_atual.get('Relator', {}), "Atual")
                            if relator:
                                relatores.append(relator)
                        
                        # Processar relatorias encerradas
                        relatorias_encerradas = relatoria_data['data'].get('RelatoriaMateria', {}).get('RelatoriasEncerradas', {}).get('Relatoria', [])
                        
                        # Garantir que seja uma lista
                        if not isinstance(relatorias_encerradas, list):
                            relatorias_encerradas = [relatorias_encerradas]
                        
                        for relatoria in relatorias_encerradas:
                            relator = self._processar_relator(relatoria.get('Relator', {}), "Encerrada")
                            if relator:
                                relatores.append(relator)
                
                details["Relatores"] = relatores
            except Exception as e:
                logger.error(f"Erro ao processar relatores do cache: {str(e)}")
            
            # Adicionar detalhes adicionais
            details["detalhes_adicionais"] = {
                "autoria_detalhada": self._extract_autoria_detalhada(materia_data)
            }
            
            return True, details
        except Exception as e:
            logger.error(f"Erro ao verificar cache de API para {sigla} {numero}/{ano}: {str(e)}")
            return False, None
    
    def _processar_relator(self, relator_data: Dict, tipo_relatoria: str) -> Optional[Dict[str, Any]]:
        """
        Processa dados de um relator.
        
        Args:
            relator_data: Dados do relator
            tipo_relatoria: Tipo de relatoria (Atual ou Encerrada)
            
        Returns:
            Dicionário com informações processadas do relator ou None se dados inválidos
        """
        if not relator_data:
            return None
        
        try:
            # Extrair identificação do parlamentar
            identificacao = relator_data.get('IdentificacaoParlamentar', {})
            
            if not identificacao:
                return None
            
            # Verificar se tem informações mínimas
            nome = identificacao.get('NomeParlamentar', '')
            codigo = identificacao.get('CodigoParlamentar', '')
            
            if not nome and not codigo:
                return None
            
            # Organizar resultado
            resultado = {
                "Nome": nome,
                "NomeCompleto": identificacao.get('NomeCompletoParlamentar', nome),
                "CodigoParlamentar": codigo,
                "SiglaPartido": identificacao.get('SiglaPartidoParlamentar', ''),
                "UF": identificacao.get('UfParlamentar', ''),
                "Comissao": relator_data.get('IdentificacaoComissao', {}).get('NomeComissao', ''),
                "SiglaComissao": relator_data.get('IdentificacaoComissao', {}).get('SiglaComissao', ''),
                "TipoRelatoria": tipo_relatoria
            }
            
            # Garantir que partido/UF não sejam None
            if resultado["SiglaPartido"] is None:
                resultado["SiglaPartido"] = ""
            if resultado["UF"] is None:
                resultado["UF"] = ""
            
            return resultado
        except Exception as e:
            logger.error(f"Erro ao processar dados do relator: {str(e)}")
            return None
    
    def _extract_autoria_detalhada(self, materia_data: Dict) -> List[Dict[str, Any]]:
        """
        Extrai detalhes de autoria da matéria.
        
        Args:
            materia_data: Dados da matéria
            
        Returns:
            Lista de autores com detalhes
        """
        autores = []
        
        try:
            # Verificar se há dados de autoria
            if 'DetalheMateria' in materia_data:
                materia = materia_data['DetalheMateria'].get('Materia', {})
                
                if not materia:
                    return autores
                
                autoria = materia.get('Autoria', {})
                if not autoria:
                    return autores
                
                autor_data = autoria.get('Autor', [])
                
                # Garantir que seja uma lista
                if not isinstance(autor_data, list):
                    autor_data = [autor_data]
                
                for autor in autor_data:
                    nome = autor.get('NomeAutor', '')
                    
                    if not nome:
                        continue
                    
                    # Extrair tipo de autor
                    tipo_autor = "Parlamentar"  # Valor padrão
                    
                    # Determinar tipo de autor com base no nome ou atributos
                    if "Senador" in nome or "Senadora" in nome:
                        tipo_autor = "Parlamentar"
                    elif "Comissão" in nome:
                        tipo_autor = "Comissão"
                    elif "Executivo" in nome or "Presidente" in nome or "Ministério" in nome:
                        tipo_autor = "Poder Executivo"
                    elif "Judiciário" in nome or "Supremo" in nome or "Tribunal" in nome:
                        tipo_autor = "Poder Judiciário"
                    elif "Popular" in nome:
                        tipo_autor = "Iniciativa Popular"
                    
                    # Extrair partido/UF
                    partido = ""
                    uf = ""
                    
                    # Para parlamentares, tentar extrair partido/UF do nome
                    if tipo_autor == "Parlamentar":
                        partido_uf_match = re.search(r'\(([A-Z]+)[\/\-]([A-Z]{2})\)', nome)
                        if partido_uf_match:
                            partido = partido_uf_match.group(1)
                            uf = partido_uf_match.group(2)
                            
                            # Remover parte do partido/UF do nome
                            nome_limpo = re.sub(r'\([A-Z]+[\/\-][A-Z]{2}\)', '', nome).strip()
                            nome = nome_limpo
                    
                    # Adicionar autor à lista
                    autores.append({
                        "nome": nome,
                        "tipo": tipo_autor,
                        "partido": partido,
                        "uf": uf,
                        "primeiro_autor": autor.get('IndicadorAutorPrincipal', 'Não') == 'Sim'
                    })
        except Exception as e:
            logger.error(f"Erro ao extrair autoria detalhada: {str(e)}")
        
        return autores
    
    def _extract_autor_from_materia(self, materia: Dict) -> str:
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
            return f"https://www25.senado.leg.br/web/atividade/materias/-/materia/busca?b_pesquisaMaterias=proposicao_{sigla}_{numero}_{ano}"
    
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
    
    def get_basic_pl_info(self, pl_id_info: Dict[str, str]) -> Dict[str, Any]:
        """
        Obtém informações básicas de um PL para uso em fallback.
        
        Args:
            pl_id_info: Dicionário com identificadores do PL (sigla, numero, ano)
            
        Returns:
            Dicionário com informações básicas do PL
        """
        try:
            sigla = pl_id_info.get('sigla', '')
            numero = pl_id_info.get('numero', '')
            ano = pl_id_info.get('ano', '')
            
            if not sigla or not numero or not ano:
                logger.error(f"Identificadores incompletos para o PL: {pl_id_info}")
                return {}
            
            # Buscar informações básicas usando a API do Senado
            basic_details = self.api.get_pl_by_id(sigla, numero, ano)
            
            return basic_details
        except Exception as e:
            logger.error(f"Erro ao obter informações básicas do PL {pl_id_info}: {str(e)}")
            return {}