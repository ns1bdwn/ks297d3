# src/intelligence/collectors/senado/relatoria_collector.py
"""
Coletor especializado em relatores de PLs.
Usa o endpoint específico de relatorias no Senado.
"""
import logging
import re
from typing import Dict, List, Any, Optional

from .api_base import SenadoAPIBase

# Configuração de logging
logger = logging.getLogger("senado_relatoria_collector")

class RelatoriaCollector(SenadoAPIBase):
    """Especializado em obter informações de relatores de PLs"""
    
    def get_relatores(self, codigo_materia: str) -> List[Dict[str, Any]]:
        """
        Obtém a lista completa de relatores (atuais e anteriores) de um PL.
        
        Args:
            codigo_materia: Código da matéria
            
        Returns:
            Lista de relatores com informações detalhadas
        """
        logger.info(f"Buscando relatores para matéria {codigo_materia}")
        
        # Endpoint específico para relatorias
        endpoint = f"materia/relatorias/{codigo_materia}"
        
        # Fazer requisição
        data, from_cache = self._make_request(endpoint)
        
        if not data:
            logger.warning(f"Relatorias não encontradas para matéria {codigo_materia}")
            return []
        
        # Processar relatores
        if not from_cache:
            try:
                resultado = []
                # Pegar relatoria atual
                relatoria_atual = data.get('RelatoriaMateria', {}).get('RelatoriaAtual', {})
                if relatoria_atual:
                    relator_atual = self._processar_relator(relatoria_atual.get('Relator', {}), "Atual")
                    if relator_atual:
                        resultado.append(relator_atual)
                
                # Pegar relatorias encerradas
                relatorias_encerradas = data.get('RelatoriaMateria', {}).get('RelatoriasEncerradas', {}).get('Relatoria', [])
                
                # Garantir que seja uma lista
                if not isinstance(relatorias_encerradas, list):
                    relatorias_encerradas = [relatorias_encerradas]
                
                # Processar cada relatoria encerrada
                for relatoria in relatorias_encerradas:
                    relator = self._processar_relator(relatoria.get('Relator', {}), "Encerrada")
                    if relator:
                        # Adicionar datas específicas de relatoria encerrada
                        relator["DataDesignacao"] = relatoria.get('DataDesignacao', '')
                        relator["DataDestituicao"] = relatoria.get('DataDestituicao', '')
                        resultado.append(relator)
                
                logger.info(f"Encontrados {len(resultado)} relatores para matéria {codigo_materia}")
                return resultado
            except Exception as e:
                logger.error(f"Erro ao processar relatores da matéria {codigo_materia}: {str(e)}")
                # Tentar backup a partir das movimentações
                return self._get_relatores_from_movimentacoes(codigo_materia)
        else:
            # Se veio do cache, retorna diretamente
            return data
    
    def get_relator_atual(self, codigo_materia: str) -> Optional[Dict[str, Any]]:
        """
        Obtém apenas o relator atual de um PL.
        
        Args:
            codigo_materia: Código da matéria
            
        Returns:
            Dicionário com informações do relator atual ou None se não houver
        """
        logger.info(f"Buscando relator atual para matéria {codigo_materia}")
        
        # Endpoint específico para relatorias
        endpoint = f"materia/relatorias/{codigo_materia}"
        
        # Fazer requisição
        data, from_cache = self._make_request(endpoint)
        
        if not data:
            logger.warning(f"Relatorias não encontradas para matéria {codigo_materia}")
            return None
        
        # Processar relator atual
        if not from_cache:
            try:
                # Pegar relatoria atual
                relatoria_atual = data.get('RelatoriaMateria', {}).get('RelatoriaAtual', {})
                if relatoria_atual:
                    return self._processar_relator(relatoria_atual.get('Relator', {}), "Atual")
                else:
                    logger.info(f"Não há relator atual para matéria {codigo_materia}")
                    return None
            except Exception as e:
                logger.error(f"Erro ao processar relator atual da matéria {codigo_materia}: {str(e)}")
                return None
        else:
            # Se veio do cache, retorna diretamente o primeiro item (relator atual)
            if isinstance(data, list) and data:
                return data[0]
            return data
    
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
                "TipoRelatoria": tipo_relatoria,
                "Fonte": "API Senado - Endpoint Relatorias"
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
    
    def _get_relatores_from_movimentacoes(self, codigo_materia: str) -> List[Dict[str, Any]]:
        """
        Método alternativo para obter relatores a partir das movimentações,
        caso o endpoint principal de relatorias falhe.
        
        Args:
            codigo_materia: Código da matéria
            
        Returns:
            Lista de relatores extraídos das movimentações
        """
        logger.info(f"Tentando extrair relatores das movimentações para matéria {codigo_materia}")
        
        # Endpoint para movimentações
        endpoint = f"materia/movimentacoes/{codigo_materia}"
        
        # Fazer requisição
        data, from_cache = self._make_request(endpoint)
        
        if not data:
            logger.warning(f"Movimentações não encontradas para matéria {codigo_materia}")
            return []
        
        # Set para evitar relatores duplicados
        relatores_encontrados = set()
        
        # Lista para armazenar relatores
        relatores = []
        
        try:
            # Verificar se temos dados de movimentação
            movimentacoes = data.get('MovimentacaoMateria', {}).get('Movimentacoes', {}).get('Movimentacao', [])
            
            # Garantir que seja uma lista
            if not isinstance(movimentacoes, list):
                movimentacoes = [movimentacoes]
            
            # Procurar por designações de relatores na movimentação
            for evento in movimentacoes:
                texto = evento.get('TextoMovimentacao', '').lower()
                
                # Buscar por menções a designação de relatores
                if 'relator' in texto and ('designad' in texto or 'indicad' in texto):
                    # Tentar extrair o nome do relator usando expressões regulares
                    # Padrões comuns para encontrar nomes de relatores
                    patterns = [
                        r"[Dd]esignad[oa] [Rr]elator[,]?\s+[oa]?\s+[Ss]enador[a]?\s+([A-ZÀ-Ú][a-zà-ú]+(?: [A-ZÀ-Ú][a-zà-ú]+)*)",
                        r"[Dd]esignad[oa] [Rr]elator[,]?\s+[Ss]en[.]?\s+([A-ZÀ-Ú][a-zà-ú]+(?: [A-ZÀ-Ú][a-zà-ú]+)*)",
                        r"[Rr]elator[:]?\s+[Ss]enador[a]?\s+([A-ZÀ-Ú][a-zà-ú]+(?: [A-ZÀ-Ú][a-zà-ú]+)*)",
                        r"[Rr]elator[:]?\s+[Ss]en[.]?\s+([A-ZÀ-Ú][a-zà-ú]+(?: [A-ZÀ-Ú][a-zà-ú]+)*)",
                        r"senador[a]?\s+([A-ZÀ-Ú][a-zà-ú]+(?: [A-ZÀ-Ú][a-zà-ú]+)*)\s+(?:para|como)\s+relator"
                    ]
                    
                    nome_relator = None
                    for pattern in patterns:
                        match = re.search(pattern, texto)
                        if match:
                            nome_relator = match.group(1)
                            break
                    
                    # Se não encontrou com os padrões regulares, tentar outras abordagens
                    if not nome_relator:
                        # Verificar se temos palavras-chave de designação seguidas por nomes próprios
                        keywords = ["relator", "senador", "relatoria"]
                        words = texto.split()
                        for i, word in enumerate(words):
                            if any(keyword in word for keyword in keywords) and i < len(words) - 1:
                                # Verificar se a próxima palavra é um possível nome (inicial maiúscula)
                                if i+1 < len(words):
                                    next_word = words[i+1]
                                    if len(next_word) > 0 and next_word[0].isupper() and len(next_word) > 3:
                                        # Possível início de nome
                                        nome_parts = []
                                        for j in range(i+1, min(i+6, len(words))):
                                            if j < len(words) and len(words[j]) > 0 and words[j][0].isupper() and len(words[j]) > 1:
                                                nome_parts.append(words[j])
                                            else:
                                                break
                                        if nome_parts:
                                            nome_relator = " ".join(nome_parts)
                                            break
                    
                    if nome_relator and nome_relator not in relatores_encontrados:
                        relatores_encontrados.add(nome_relator)
                        
                        # Extrair informações adicionais quando disponíveis
                        partido = ""
                        uf = ""
                        
                        # Buscar por padrões de partido/UF: (PARTIDO-UF) ou (PARTIDO/UF)
                        partido_uf_pattern = r"\(([A-Z]+)[\/\-]([A-Z]{2})\)"
                        partido_uf_match = re.search(partido_uf_pattern, texto)
                        
                        if partido_uf_match:
                            partido = partido_uf_match.group(1)
                            uf = partido_uf_match.group(2)
                        
                        # Adicionar à lista de relatores
                        relatores.append({
                            "Nome": nome_relator,
                            "NomeCompleto": nome_relator,
                            "CodigoParlamentar": "",
                            "SiglaPartido": partido,
                            "UF": uf,
                            "Comissao": evento.get('Local', {}).get('NomeLocal', ''),
                            "SiglaComissao": evento.get('Local', {}).get('SiglaLocal', ''),
                            "TipoRelatoria": "Identificado via Movimentação",
                            "DataDesignacao": evento.get('DataMovimentacao', ''),
                            "DataDestituicao": "",
                            "Fonte": "Extraído da movimentação"
                        })
        
            # Informar sobre o resultado
            if relatores:
                logger.info(f"Encontrados {len(relatores)} relatores nas movimentações para matéria {codigo_materia}")
            else:
                logger.info(f"Nenhum relator encontrado nas movimentações para matéria {codigo_materia}")
                
            return relatores
                
        except Exception as e:
            logger.error(f"Erro ao processar relatores das movimentações da matéria {codigo_materia}: {str(e)}")
            return []