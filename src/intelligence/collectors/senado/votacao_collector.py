# src/intelligence/collectors/senado/votacao_collector.py
"""
Coletor especializado em votações de PLs.
"""
import logging
from typing import Dict, List, Any, Optional

from .api_base import SenadoAPIBase

# Configuração de logging
logger = logging.getLogger("senado_votacao_collector")

class VotacaoCollector(SenadoAPIBase):
    """Especializado em obter informações sobre votações de PLs"""
    
    def get_votacoes(self, codigo_materia: str) -> List[Dict[str, Any]]:
        """
        Obtém informações sobre as votações da matéria.
        
        Args:
            codigo_materia: Código da matéria
            
        Returns:
            Lista de votações com informações detalhadas
        """
        logger.info(f"Buscando votações para matéria {codigo_materia}")
        
        # Endpoint específico para votações
        endpoint = f"materia/votacoes/{codigo_materia}"
        
        # Fazer requisição
        data, from_cache = self._make_request(endpoint)
        
        if not data:
            logger.warning(f"Votações não encontradas para matéria {codigo_materia}")
            return []
        
        # Processar votações
        if not from_cache:
            try:
                # Extrair dados de votação
                votacoes = data.get('VotacaoMateria', {}).get('Votacoes', {}).get('Votacao', [])
                
                # Garantir que seja uma lista
                if not isinstance(votacoes, list):
                    votacoes = [votacoes]
                
                # Processar cada votação
                resultado = []
                for votacao in votacoes:
                    votacao_processada = self._processar_votacao(votacao)
                    if votacao_processada:
                        resultado.append(votacao_processada)
                
                logger.info(f"Encontradas {len(resultado)} votações para matéria {codigo_materia}")
                return resultado
            except Exception as e:
                logger.error(f"Erro ao processar votações da matéria {codigo_materia}: {str(e)}")
                return []
        else:
            # Se veio do cache, retorna diretamente
            return data
    
    def _processar_votacao(self, votacao_data: Dict) -> Optional[Dict[str, Any]]:
        """
        Processa dados de uma votação.
        
        Args:
            votacao_data: Dados da votação
            
        Returns:
            Dicionário com informações processadas da votação ou None se dados inválidos
        """
        if not votacao_data:
            return None
        
        try:
            # Extrair informações básicas
            data_votacao = votacao_data.get('DataSessao', '')
            descricao = votacao_data.get('DescricaoVotacao', '')
            
            # Se não tiver data ou descrição, considerar inválido
            if not data_votacao and not descricao:
                return None
            
            # Extrair informações da sessão
            sessao = votacao_data.get('SessaoPlenaria', {})
            
            # Extrair votos
            votos_sim = int(votacao_data.get('VotosSimNaoAbstencao', {}).get('VotosSim', 0) or 0)
            votos_nao = int(votacao_data.get('VotosSimNaoAbstencao', {}).get('VotosNao', 0) or 0)
            abstencoes = int(votacao_data.get('VotosSimNaoAbstencao', {}).get('Abstencao', 0) or 0)
            
            # Calcular total de votos e percentual de aprovação
            total_votos = votos_sim + votos_nao + abstencoes
            percentual_aprovacao = (votos_sim / (votos_sim + votos_nao)) * 100 if (votos_sim + votos_nao) > 0 else 0
            
            # Determinar resultado
            resultado_votacao = "Aprovado" if votos_sim > votos_nao else "Rejeitado" if votos_nao > votos_sim else "Empate"
            
            # Organizar detalhes dos votos por parlamentar
            votos_parlamentares = []
            
            # Verificar se temos votos detalhados
            votos_parlamentar = votacao_data.get('Votos', {}).get('VotoParlamentar', [])
            
            # Garantir que seja uma lista
            if not isinstance(votos_parlamentar, list):
                votos_parlamentar = [votos_parlamentar]
                
            # Processar votos dos parlamentares
            for voto in votos_parlamentar:
                parlamentar = voto.get('IdentificacaoParlamentar', {})
                
                voto_parlamentar = {
                    "Nome": parlamentar.get('NomeParlamentar', ''),
                    "Partido": parlamentar.get('SiglaPartidoParlamentar', ''),
                    "UF": parlamentar.get('UfParlamentar', ''),
                    "CodigoParlamentar": parlamentar.get('CodigoParlamentar', ''),
                    "Voto": voto.get('VotoTexto', '')
                }
                
                votos_parlamentares.append(voto_parlamentar)
            
            # Organizar resultado
            return {
                "Data": data_votacao,
                "Horario": votacao_data.get('HoraSessao', ''),
                "Descricao": descricao,
                "NumeroSessao": sessao.get('NumeroSessao', ''),
                "TipoSessao": sessao.get('TipoSessao', {}).get('DescricaoTipoSessao', ''),
                "Resultado": resultado_votacao,
                "VotosSim": votos_sim,
                "VotosNao": votos_nao,
                "Abstencoes": abstencoes,
                "TotalVotos": total_votos,
                "PercentualAprovacao": percentual_aprovacao,
                "Local": votacao_data.get('Tramitacao', {}).get('Local', {}).get('NomeLocal', ''),
                "SiglaLocal": votacao_data.get('Tramitacao', {}).get('Local', {}).get('SiglaLocal', ''),
                "VotosParlamentares": votos_parlamentares
            }
        except Exception as e:
            logger.error(f"Erro ao processar dados da votação: {str(e)}")
            return None
    
    def get_estatisticas_votacoes(self, codigo_materia: str) -> Dict[str, Any]:
        """
        Calcula estatísticas agregadas de todas as votações da matéria.
        
        Args:
            codigo_materia: Código da matéria
            
        Returns:
            Dicionário com estatísticas das votações
        """
        # Obter todas as votações
        votacoes = self.get_votacoes(codigo_materia)
        
        if not votacoes:
            return {
                "TotalVotacoes": 0,
                "Aprovacoes": 0,
                "Rejeicoes": 0,
                "PercentualAprovacao": 0,
                "MediaVotosSim": 0,
                "MediaVotosNao": 0,
                "TotalVotosSim": 0,
                "TotalVotosNao": 0,
                "MaiorAprovacao": None,
                "UltimaVotacao": None
            }
        
        # Calcular estatísticas
        total_votacoes = len(votacoes)
        aprovacoes = sum(1 for v in votacoes if v.get('Resultado') == 'Aprovado')
        rejeicoes = sum(1 for v in votacoes if v.get('Resultado') == 'Rejeitado')
        
        total_votos_sim = sum(v.get('VotosSim', 0) for v in votacoes)
        total_votos_nao = sum(v.get('VotosNao', 0) for v in votacoes)
        
        media_votos_sim = total_votos_sim / total_votacoes if total_votacoes > 0 else 0
        media_votos_nao = total_votos_nao / total_votacoes if total_votacoes > 0 else 0
        
        percentual_aprovacao = (aprovacoes / total_votacoes) * 100 if total_votacoes > 0 else 0
        
        # Encontrar votação com maior percentual de aprovação
        maior_aprovacao = max(votacoes, key=lambda v: v.get('PercentualAprovacao', 0)) if votacoes else None
        
        # Ordenar por data e obter a última
        votacoes_ordenadas = sorted(votacoes, key=lambda v: v.get('Data', ''), reverse=True)
        ultima_votacao = votacoes_ordenadas[0] if votacoes_ordenadas else None
        
        # Construir relatório
        return {
            "TotalVotacoes": total_votacoes,
            "Aprovacoes": aprovacoes,
            "Rejeicoes": rejeicoes,
            "PercentualAprovacao": percentual_aprovacao,
            "MediaVotosSim": media_votos_sim,
            "MediaVotosNao": media_votos_nao,
            "TotalVotosSim": total_votos_sim,
            "TotalVotosNao": total_votos_nao,
            "MaiorAprovacao": maior_aprovacao,
            "UltimaVotacao": ultima_votacao
        }
    
    def get_votacoes_comissao(self, sigla: str, numero: str, ano: str) -> List[Dict[str, Any]]:
        """
        Obtém votações específicas de comissões para uma matéria.
        Usa endpoint diferente que pode conter informações adicionais.
        
        Args:
            sigla: Sigla do PL
            numero: Número do PL
            ano: Ano do PL
            
        Returns:
            Lista de votações em comissões
        """
        logger.info(f"Buscando votações em comissões para {sigla} {numero}/{ano}")
        
        # Endpoint para votações de comissão (formato diferente)
        endpoint = f"votacaoComissao/materia/{sigla}/{numero}/{ano}"
        
        # Fazer requisição
        data, from_cache = self._make_request(endpoint)
        
        if not data:
            logger.warning(f"Votações de comissão não encontradas para {sigla} {numero}/{ano}")
            return []
        
        # Processar votações
        if not from_cache:
            try:
                # Extrair dados de votação
                votacoes = data.get('VotacaoComissaoMateria', {}).get('Materia', {}).get('Votacoes', {}).get('Votacao', [])
                
                # Garantir que seja uma lista
                if not isinstance(votacoes, list):
                    votacoes = [votacoes]
                
                # Processar cada votação
                resultado = []
                for votacao in votacoes:
                    # Processar diferentemente, pois a estrutura é diferente
                    votacao_processada = self._processar_votacao_comissao(votacao)
                    if votacao_processada:
                        resultado.append(votacao_processada)
                
                logger.info(f"Encontradas {len(resultado)} votações de comissão para {sigla} {numero}/{ano}")
                return resultado
            except Exception as e:
                logger.error(f"Erro ao processar votações de comissão para {sigla} {numero}/{ano}: {str(e)}")
                return []
        else:
            # Se veio do cache, retorna diretamente
            return data
    
    def _processar_votacao_comissao(self, votacao_data: Dict) -> Optional[Dict[str, Any]]:
        """
        Processa dados de uma votação de comissão.
        
        Args:
            votacao_data: Dados da votação
            
        Returns:
            Dicionário com informações processadas da votação ou None se dados inválidos
        """
        # A implementação depende da estrutura retornada pelo endpoint
        # Este é um esqueleto básico, ajuste conforme necessário
        if not votacao_data:
            return None
        
        try:
            # Extrair informações básicas
            data_votacao = votacao_data.get('DataVotacao', '')
            resultado = votacao_data.get('Resultado', '')
            
            # Se não tiver data ou resultado, considerar inválido
            if not data_votacao and not resultado:
                return None
            
            # Extrair comissão
            comissao = votacao_data.get('Comissao', {})
            
            # Organizar resultado
            return {
                "Data": data_votacao,
                "Resultado": resultado,
                "Comissao": comissao.get('NomeComissao', ''),
                "SiglaComissao": comissao.get('SiglaComissao', ''),
                "TipoVotacao": votacao_data.get('DescricaoTipoVotacao', ''),
                "Observacao": votacao_data.get('Observacao', '')
            }
        except Exception as e:
            logger.error(f"Erro ao processar dados da votação de comissão: {str(e)}")
            return None