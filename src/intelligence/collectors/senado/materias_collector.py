# src/intelligence/collectors/senado/materias_collector.py
"""
Coletor especializado em buscar PLs e suas informações básicas.
"""
import re
import logging
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime

from .api_base import SenadoAPIBase

# Configuração de logging
logger = logging.getLogger("senado_materias_collector")

class MateriasCollector(SenadoAPIBase):
    """Especializado em buscar PLs e suas informações básicas"""
    
    def get_pl_by_id(self, sigla: str, numero: str, ano: str) -> Dict[str, Any]:
        """
        Obtém detalhes básicos de um PL específico.
        
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
                
                # Adicionar o código da matéria para uso futuro
                processed_data["CodigoMateria"] = codigo_materia
                processed_data["Sigla"] = sigla
                processed_data["Numero"] = numero
                processed_data["Ano"] = ano
                
                return processed_data
            except Exception as e:
                logger.error(f"Erro ao processar dados do PL {sigla} {numero}/{ano}: {str(e)}")
                return {}
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
            return f"https://www25.senado.leg.br/web/atividade/materias/-/materia/busca?b_pesquisaMaterias=proposicao_{sigla}_{numero}_{ano}"
    
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
