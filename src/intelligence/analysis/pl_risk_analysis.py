# src/intelligence/analysis/pl_risk_analysis.py
"""
Módulo para análise de risco regulatório baseado em dados reais dos PLs.
Utiliza dados da API do Senado e algoritmos de análise para avaliar o risco.
"""
import logging
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd

from src.intelligence.collectors.senado_api import SenadoAPI

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("pl_risk_analysis")

class PLRiskAnalyzer:
    """
    Analisador de risco regulatório para Projetos de Lei.
    Utiliza dados do status atual e histórico de tramitação para avaliar riscos.
    """
    
    # Comissões com maior poder de aprovação
    HIGH_POWER_COMMITTEES = [
        "CCJ", "CAE", "Plenário", "Mesa Diretora", 
        "Comissão Diretora", "Comissão de Constituição e Justiça"
    ]
    
    # Status que indicam avanço no processo legislativo
    ADVANCING_STATUS = [
        "APROVAD", "APROVAÇÃO", "VOTAÇÃO", "DESIGNADO RELATOR", 
        "INCLUÍDA NA ORDEM DO DIA", "PRONTA PARA A PAUTA", "AUDIÊNCIA PÚBLICA"
    ]
    
    # Status que indicam estagnação ou arquivamento
    STALLED_STATUS = [
        "ARQUIVAD", "PREJUDICAD", "RETIRAD", "REJEITAD", 
        "DEVOLVID", "RETIRADO PELO AUTOR"
    ]
    
    def __init__(self, data_dir: str = None):
        """
        Inicializa o analisador de risco.
        
        Args:
            data_dir: Diretório para armazenar dados de análise.
        """
        # Diretório base para dados
        if data_dir is None:
            self.data_dir = os.path.join(os.getcwd(), "data", "risk_analysis")
        else:
            self.data_dir = data_dir
        
        # Garantir que o diretório existe
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Cliente da API do Senado
        self.senado_api = SenadoAPI()
        
        # Cache de análises realizadas
        self.analysis_cache = {}
    
    def analyze_pl_risk(self, sigla: str, numero: str, ano: str, 
                       force_refresh: bool = False) -> Dict[str, Any]:
        """
        Analisa o risco regulatório de um PL.
        
        Args:
            sigla: Sigla do PL (ex: PL, PEC)
            numero: Número do PL
            ano: Ano do PL
            force_refresh: Se True, força nova análise mesmo se houver cache
            
        Returns:
            Dicionário com análise de risco
        """
        pl_id = f"{sigla} {numero}/{ano}"
        logger.info(f"Analisando risco regulatório do {pl_id}")
        
        # Verificar se já tem análise em cache
        if not force_refresh:
            # Verificar cache em memória
            if pl_id in self.analysis_cache:
                logger.info(f"Usando análise em cache para {pl_id}")
                return self.analysis_cache[pl_id]
            
            # Verificar cache em disco
            cache_file = os.path.join(self.data_dir, f"{sigla}_{numero}_{ano}_risk.json")
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        analysis = json.load(f)
                    
                    # Verificar se a análise é recente (menos de 24 horas)
                    analysis_time = analysis.get('timestamp', 0)
                    now = datetime.now().timestamp()
                    
                    if now - analysis_time < 24 * 60 * 60:
                        logger.info(f"Usando análise recente em disco para {pl_id}")
                        return analysis
                except Exception as e:
                    logger.error(f"Erro ao carregar análise do disco para {pl_id}: {str(e)}")
        
        # Buscar dados atualizados do PL
        pl_details = self.senado_api.get_pl_details(sigla, numero, ano)
        
        if not pl_details:
            logger.warning(f"Não foi possível obter dados para o PL {pl_id}")
            return {
                "pl_id": pl_id,
                "timestamp": datetime.now().timestamp(),
                "error": "Não foi possível obter dados para o PL"
            }
        
        # Extrair informações relevantes
        situacao = pl_details.get('Situacao', {})
        tramitacao = pl_details.get('Tramitacao_Detalhada', [])
        
        # Calcular o risco de aprovação
        risk_score, risk_factors = self._calculate_approval_risk(pl_details, situacao, tramitacao)
        
        # Calcular tempo estimado para aprovação
        time_estimate, time_factors = self._estimate_approval_time(pl_details, situacao, tramitacao)
        
        # Calcular próximos passos prováveis
        next_steps = self._predict_next_steps(pl_details, situacao, tramitacao)
        
        # Montar análise completa
        analysis = {
            "pl_id": pl_id,
            "timestamp": datetime.now().timestamp(),
            "data_atualizacao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "titulo": pl_details.get('Título', ''),
            "autor": pl_details.get('Autor', ''),
            "status_atual": {
                "local": situacao.get('Local', ''),
                "situacao": situacao.get('Situacao', ''),
                "data": situacao.get('Data', '')
            },
            "risco_aprovacao": {
                "score": risk_score,
                "nivel": self._risk_level_name(risk_score),
                "fatores": risk_factors
            },
            "tempo_estimado": {
                "estimativa": time_estimate,
                "fatores": time_factors
            },
            "proximos_passos": next_steps,
            "ultimos_eventos": tramitacao[:5] if tramitacao else []
        }
        
        # Salvar em cache
        self.analysis_cache[pl_id] = analysis
        
        # Salvar em disco
        try:
            cache_file = os.path.join(self.data_dir, f"{sigla}_{numero}_{ano}_risk.json")
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"Erro ao salvar análise em disco para {pl_id}: {str(e)}")
        
        return analysis
    
    def _calculate_approval_risk(self, pl_details: Dict, 
                               situacao: Dict, 
                               tramitacao: List[Dict]) -> Tuple[float, List[Dict]]:
        """
        Calcula o risco de aprovação de um PL com base no status atual e histórico.
        
        Args:
            pl_details: Detalhes do PL
            situacao: Situação atual do PL
            tramitacao: Histórico de tramitação
            
        Returns:
            Tupla com score de risco (0-100) e lista de fatores que contribuíram
        """
        # Inicializar score e fatores
        risk_score = 50.0  # Começa com 50% de chance (neutro)
        risk_factors = []
        
        # Fator 1: Status atual
        current_status = situacao.get('Situacao', '').upper()
        current_location = situacao.get('Local', '').upper()
        
        # Verificar se está em comissão de alto poder
        in_powerful_committee = False
        for committee in self.HIGH_POWER_COMMITTEES:
            if committee.upper() in current_location:
                in_powerful_committee = True
                risk_score += 10
                risk_factors.append({
                    "fator": "Localização atual",
                    "descricao": f"PL está em {situacao.get('Local', '')}",
                    "impacto": "+10 pontos",
                    "explicacao": "Comissões com maior poder de decisão aceleram a aprovação"
                })
                break
        
        if not in_powerful_committee:
            risk_score -= 5
            risk_factors.append({
                "fator": "Localização atual",
                "descricao": f"PL está em {situacao.get('Local', '')}",
                "impacto": "-5 pontos",
                "explicacao": "Comissões de menor influência tendem a atrasar o processo"
            })
        
        # Verificar status de avanço
        advancing = False
        for status in self.ADVANCING_STATUS:
            if status.upper() in current_status:
                advancing = True
                risk_score += 15
                risk_factors.append({
                    "fator": "Status atual",
                    "descricao": f"Status: {situacao.get('Situacao', '')}",
                    "impacto": "+15 pontos",
                    "explicacao": "Status indica avanço no processo legislativo"
                })
                break
        
        # Verificar status de estagnação
        stalled = False
        for status in self.STALLED_STATUS:
            if status.upper() in current_status:
                stalled = True
                risk_score -= 40
                risk_factors.append({
                    "fator": "Status atual",
                    "descricao": f"Status: {situacao.get('Situacao', '')}",
                    "impacto": "-40 pontos",
                    "explicacao": "Status indica estagnação ou arquivamento"
                })
                break
        
        if not advancing and not stalled:
            risk_factors.append({
                "fator": "Status atual",
                "descricao": f"Status: {situacao.get('Situacao', '')}",
                "impacto": "Neutro",
                "explicacao": "Status atual não indica claramente avanço ou estagnação"
            })
        
        # Fator 2: Tempo desde a apresentação
        try:
            presentation_date = datetime.strptime(pl_details.get('Data', ''), "%Y-%m-%d")
            today = datetime.now()
            days_since_presentation = (today - presentation_date).days
            
            if days_since_presentation < 30:
                # Muito recente, ainda em fase inicial
                risk_score -= 5
                risk_factors.append({
                    "fator": "Tempo desde apresentação",
                    "descricao": f"{days_since_presentation} dias",
                    "impacto": "-5 pontos",
                    "explicacao": "PL muito recente, ainda em fase inicial"
                })
            elif days_since_presentation > 365:
                # Mais de um ano, pode indicar baixa prioridade
                risk_score -= 10
                risk_factors.append({
                    "fator": "Tempo desde apresentação",
                    "descricao": f"{days_since_presentation} dias",
                    "impacto": "-10 pontos",
                    "explicacao": "PL com mais de um ano sem aprovação, possível baixa prioridade"
                })
        except Exception:
            # Se não conseguir calcular, ignora este fator
            pass
        
        # Fator 3: Velocidade de tramitação
        if len(tramitacao) >= 2:
            try:
                # Calcular o tempo médio entre eventos
                dates = []
                for event in tramitacao:
                    if event.get('Data'):
                        try:
                            dates.append(datetime.strptime(event.get('Data'), "%Y-%m-%d"))
                        except ValueError:
                            continue
                
                if len(dates) >= 2:
                    # Ordenar datas
                    dates.sort(reverse=True)
                    
                    # Calcular diferenças em dias
                    intervals = [(dates[i] - dates[i+1]).days for i in range(len(dates)-1)]
                    avg_interval = sum(intervals) / len(intervals)
                    
                    if avg_interval < 15:
                        # Tramitação rápida
                        risk_score += 10
                        risk_factors.append({
                            "fator": "Velocidade de tramitação",
                            "descricao": f"Média de {avg_interval:.1f} dias entre eventos",
                            "impacto": "+10 pontos",
                            "explicacao": "Tramitação rápida indica prioridade e maior chance de aprovação"
                        })
                    elif avg_interval > 60:
                        # Tramitação lenta
                        risk_score -= 10
                        risk_factors.append({
                            "fator": "Velocidade de tramitação",
                            "descricao": f"Média de {avg_interval:.1f} dias entre eventos",
                            "impacto": "-10 pontos",
                            "explicacao": "Tramitação lenta indica baixa prioridade"
                        })
                    else:
                        # Tramitação média
                        risk_factors.append({
                            "fator": "Velocidade de tramitação",
                            "descricao": f"Média de {avg_interval:.1f} dias entre eventos",
                            "impacto": "Neutro",
                            "explicacao": "Velocidade de tramitação normal"
                        })
            except Exception as e:
                logger.warning(f"Erro ao calcular velocidade de tramitação: {str(e)}")
        
        # Fator 4: Última movimentação
        if tramitacao and tramitacao[0].get('Data'):
            try:
                last_event_date = datetime.strptime(tramitacao[0].get('Data'), "%Y-%m-%d")
                days_since_last_event = (datetime.now() - last_event_date).days
                
                if days_since_last_event > 90:
                    # Sem movimentação recente
                    risk_score -= 15
                    risk_factors.append({
                        "fator": "Última movimentação",
                        "descricao": f"{days_since_last_event} dias desde o último evento",
                        "impacto": "-15 pontos",
                        "explicacao": "PL sem movimentação recente, possível estagnação"
                    })
                elif days_since_last_event < 15:
                    # Movimentação recente
                    risk_score += 5
                    risk_factors.append({
                        "fator": "Última movimentação",
                        "descricao": f"{days_since_last_event} dias desde o último evento",
                        "impacto": "+5 pontos",
                        "explicacao": "PL com movimentação recente, indica atividade"
                    })
            except Exception:
                pass
        
        # Fator 5: Relevância do autor
        autor = pl_details.get('Autor', '')
        if "Poder Executivo" in autor or "Presidente" in autor:
            risk_score += 15
            risk_factors.append({
                "fator": "Relevância do autor",
                "descricao": f"Autor: {autor}",
                "impacto": "+15 pontos",
                "explicacao": "PLs do Poder Executivo têm maior prioridade e chance de aprovação"
            })
        elif "Mesa Diretora" in autor or "Comissão" in autor:
            risk_score += 10
            risk_factors.append({
                "fator": "Relevância do autor",
                "descricao": f"Autor: {autor}",
                "impacto": "+10 pontos",
                "explicacao": "PLs de Comissões ou da Mesa Diretora têm boa chance de aprovação"
            })
        
        # Limitar score entre 0 e 100
        risk_score = max(0, min(100, risk_score))
        
        return risk_score, risk_factors
    
    def _estimate_approval_time(self, pl_details: Dict, 
                             situacao: Dict, 
                             tramitacao: List[Dict]) -> Tuple[str, List[Dict]]:
        """
        Estima o tempo para aprovação de um PL.
        
        Args:
            pl_details: Detalhes do PL
            situacao: Situação atual do PL
            tramitacao: Histórico de tramitação
            
        Returns:
            Tupla com estimativa de tempo e lista de fatores que contribuíram
        """
        # Inicializar fatores
        time_factors = []
        
        # Verificar se está arquivado ou prejudicado
        current_status = situacao.get('Situacao', '').upper()
        for status in self.STALLED_STATUS:
            if status.upper() in current_status:
                time_factors.append({
                    "fator": "Status atual",
                    "descricao": f"Status: {situacao.get('Situacao', '')}",
                    "impacto": "Não aplicável",
                    "explicacao": "PL arquivado, prejudicado ou retirado"
                })
                return "Não aplicável (PL não está em tramitação ativa)", time_factors
        
        # Estimativa baseada na localização atual
        current_location = situacao.get('Local', '').upper()
        if "PLENÁRIO" in current_location:
            estimate = "3-6 meses"
            time_factors.append({
                "fator": "Localização atual",
                "descricao": f"PL está em {situacao.get('Local', '')}",
                "impacto": "3-6 meses",
                "explicacao": "PLs em Plenário geralmente têm tramitação mais rápida se houver prioridade"
            })
        elif "CCJ" in current_location or "CONSTITUIÇÃO E JUSTIÇA" in current_location:
            estimate = "6-12 meses"
            time_factors.append({
                "fator": "Localização atual",
                "descricao": f"PL está em {situacao.get('Local', '')}",
                "impacto": "6-12 meses",
                "explicacao": "A CCJ é uma comissão crucial e pode demandar análise detalhada"
            })
        elif any(committee in current_location for committee in self.HIGH_POWER_COMMITTEES):
            estimate = "6-18 meses"
            time_factors.append({
                "fator": "Localização atual",
                "descricao": f"PL está em {situacao.get('Local', '')}",
                "impacto": "6-18 meses",
                "explicacao": "Comissões importantes tendem a analisar com mais cuidado"
            })
        else:
            estimate = "12-24 meses"
            time_factors.append({
                "fator": "Localização atual",
                "descricao": f"PL está em {situacao.get('Local', '')}",
                "impacto": "12-24 meses",
                "explicacao": "Comissões de menor influência tendem a ter tramitação mais lenta"
            })
        
        # Ajustar com base na velocidade de tramitação
        if len(tramitacao) >= 2:
            try:
                # Calcular o tempo médio entre eventos
                dates = []
                for event in tramitacao:
                    if event.get('Data'):
                        try:
                            dates.append(datetime.strptime(event.get('Data'), "%Y-%m-%d"))
                        except ValueError:
                            continue
                
                if len(dates) >= 2:
                    # Ordenar datas
                    dates.sort(reverse=True)
                    
                    # Calcular diferenças em dias
                    intervals = [(dates[i] - dates[i+1]).days for i in range(len(dates)-1)]
                    avg_interval = sum(intervals) / len(intervals)
                    
                    if avg_interval < 15:
                        # Tramitação rápida
                        adjustment = "redução no tempo estimado"
                        time_factors.append({
                            "fator": "Velocidade de tramitação",
                            "descricao": f"Média de {avg_interval:.1f} dias entre eventos",
                            "impacto": adjustment,
                            "explicacao": "Tramitação rápida indica prioridade e pode acelerar o processo"
                        })
                        
                        # Ajustar estimativa
                        if "3-6 meses" in estimate:
                            estimate = "1-3 meses"
                        elif "6-12 meses" in estimate:
                            estimate = "3-6 meses"
                        elif "6-18 meses" in estimate:
                            estimate = "4-12 meses"
                        elif "12-24 meses" in estimate:
                            estimate = "6-18 meses"
                        
                    elif avg_interval > 60:
                        # Tramitação lenta
                        adjustment = "aumento no tempo estimado"
                        time_factors.append({
                            "fator": "Velocidade de tramitação",
                            "descricao": f"Média de {avg_interval:.1f} dias entre eventos",
                            "impacto": adjustment,
                            "explicacao": "Tramitação lenta indica baixa prioridade e pode estender o processo"
                        })
                        
                        # Ajustar estimativa
                        if "3-6 meses" in estimate:
                            estimate = "6-12 meses"
                        elif "6-12 meses" in estimate:
                            estimate = "12-24 meses"
                        elif "6-18 meses" in estimate:
                            estimate = "12-30 meses"
                        elif "12-24 meses" in estimate:
                            estimate = "18-36 meses"
                    else:
                        # Tramitação média, mantém estimativa
                        time_factors.append({
                            "fator": "Velocidade de tramitação",
                            "descricao": f"Média de {avg_interval:.1f} dias entre eventos",
                            "impacto": "Neutro",
                            "explicacao": "Velocidade de tramitação normal"
                        })
            except Exception as e:
                logger.warning(f"Erro ao calcular velocidade de tramitação: {str(e)}")
        
        # Última movimentação
        if tramitacao and tramitacao[0].get('Data'):
            try:
                last_event_date = datetime.strptime(tramitacao[0].get('Data'), "%Y-%m-%d")
                days_since_last_event = (datetime.now() - last_event_date).days
                
                if days_since_last_event > 90:
                    time_factors.append({
                        "fator": "Última movimentação",
                        "descricao": f"{days_since_last_event} dias desde o último evento",
                        "impacto": "Possível extensão no prazo",
                        "explicacao": "PL sem movimentação recente pode indicar estagnação"
                    })
                    
                    # Se estiver parado há muito tempo, a estimativa pode ficar mais longa
                    if days_since_last_event > 180:
                        if not "+" in estimate:
                            parts = estimate.split("-")
                            if len(parts) == 2:
                                try:
                                    min_months = int(parts[0])
                                    max_months = int(parts[1].replace(" meses", ""))
                                    estimate = f"{min_months+6}-{max_months+12} meses"
                                except ValueError:
                                    pass
            except Exception:
                pass
        
        return estimate, time_factors
    
    def _predict_next_steps(self, pl_details: Dict, 
                          situacao: Dict, 
                          tramitacao: List[Dict]) -> List[Dict]:
        """
        Prediz os próximos passos prováveis na tramitação de um PL.
        
        Args:
            pl_details: Detalhes do PL
            situacao: Situação atual do PL
            tramitacao: Histórico de tramitação
            
        Returns:
            Lista de próximos passos prováveis com probabilidades
        """
        next_steps = []
        
        # Verificar se está arquivado ou prejudicado
        current_status = situacao.get('Situacao', '').upper()
        for status in self.STALLED_STATUS:
            if status.upper() in current_status:
                return [{
                    "passo": "PL não está em tramitação ativa",
                    "probabilidade": "Alta",
                    "observacao": "PL foi arquivado, prejudicado ou retirado"
                }]
        
        # Localização atual
        current_location = situacao.get('Local', '')
        
        # Predizer próximos passos com base na localização atual
        if "Plenário" in current_location:
            next_steps.append({
                "passo": "Votação em Plenário",
                "probabilidade": "Alta",
                "observacao": "PL já está no Plenário, próximo passo natural é a votação"
            })
            
            next_steps.append({
                "passo": "Encaminhamento para sanção/promulgação",
                "probabilidade": "Média",
                "observacao": "Se aprovado em Plenário, será encaminhado para próxima fase"
            })
            
            next_steps.append({
                "passo": "Encaminhamento à Câmara dos Deputados",
                "probabilidade": "Média",
                "observacao": "Se aprovado no Senado, segue para a Câmara dos Deputados"
            })
        
        elif "CCJ" in current_location or "Constituição e Justiça" in current_location:
            next_steps.append({
                "passo": "Parecer do Relator",
                "probabilidade": "Alta",
                "observacao": "Próximo passo natural na CCJ é a emissão de parecer pelo relator"
            })
            
            next_steps.append({
                "passo": "Votação na Comissão",
                "probabilidade": "Média",
                "observacao": "Após parecer, o projeto será votado na comissão"
            })
            
            next_steps.append({
                "passo": "Encaminhamento para outras comissões",
                "probabilidade": "Média",
                "observacao": "Após a CCJ, normalmente o projeto passa por outras comissões pertinentes"
            })
        
        elif "Comissão" in current_location:
            next_steps.append({
                "passo": "Designação de Relator",
                "probabilidade": "Alta" if "DESIGNADO RELATOR" not in current_status else "Baixa",
                "observacao": "Primeiro passo em uma comissão é a designação de relator"
            })
            
            next_steps.append({
                "passo": "Emissão de Parecer",
                "probabilidade": "Alta" if "DESIGNADO RELATOR" in current_status else "Média",
                "observacao": "Após designação, o relator emite parecer sobre o projeto"
            })
            
            next_steps.append({
                "passo": "Votação na Comissão",
                "probabilidade": "Média",
                "observacao": "Após parecer, o projeto é votado na comissão"
            })
            
            next_steps.append({
                "passo": "Encaminhamento para outra comissão ou Plenário",
                "probabilidade": "Média",
                "observacao": "Após aprovação na comissão atual, segue o fluxo legislativo"
            })
        
        else:
            # Caso genérico
            next_steps = [
                {
                    "passo": "Distribuição para Comissões",
                    "probabilidade": "Média",
                    "observacao": "PL pode ser distribuído para análise em comissões pertinentes"
                },
                {
                    "passo": "Designação de Relator",
                    "probabilidade": "Média",
                    "observacao": "Designação de relator para analisar o PL"
                },
                {
                    "passo": "Inclusão na pauta de comissão",
                    "probabilidade": "Baixa",
                    "observacao": "PL pode ser incluído na pauta de votação de alguma comissão"
                }
            ]
        
        # Se tiver tramitação, tentar identificar padrões recorrentes
        if len(tramitacao) > 3:
            # Identificar locais mais recorrentes
            locations = []
            for event in tramitacao:
                if event.get('Local'):
                    locations.append(event.get('Local'))
            
            if locations:
                try:
                    # Contar ocorrências
                    from collections import Counter
                    location_counts = Counter(locations)
                    
                    # Pegar o local mais frequente (exceto o atual)
                    most_common = [loc for loc, _ in location_counts.most_common() if loc != current_location]
                    
                    if most_common:
                        next_steps.append({
                            "passo": f"Retorno para {most_common[0]}",
                            "probabilidade": "Baixa",
                            "observacao": "Baseado no histórico de tramitação, pode retornar a este local"
                        })
                except Exception:
                    pass
        
        return next_steps
    
    def _risk_level_name(self, risk_score: float) -> str:
        """
        Converte um score de risco em um nome de nível.
        
        Args:
            risk_score: Score de risco (0-100)
            
        Returns:
            Nome do nível de risco
        """
        if risk_score < 20:
            return "Muito Baixo"
        elif risk_score < 40:
            return "Baixo"
        elif risk_score < 60:
            return "Médio"
        elif risk_score < 80:
            return "Alto"
        else:
            return "Muito Alto"
    
    def get_sector_risk_overview(self, sector_pls: List[Dict]) -> Dict[str, Any]:
        """
        Gera uma visão geral dos riscos para um setor com base em vários PLs.
        
        Args:
            sector_pls: Lista de PLs do setor com identificadores
            
        Returns:
            Visão geral dos riscos para o setor
        """
        # Verificar se há PLs
        if not sector_pls:
            return {
                "timestamp": datetime.now().timestamp(),
                "error": "Nenhum PL fornecido para análise"
            }
        
        # Analisar cada PL
        pl_analyses = []
        for pl in sector_pls:
            try:
                sigla = pl.get('Sigla') or pl.get('sigla')
                numero = pl.get('Numero') or pl.get('numero')
                ano = pl.get('Ano') or pl.get('ano')
                
                if sigla and numero and ano:
                    analysis = self.analyze_pl_risk(sigla, numero, ano)
                    if analysis and 'error' not in analysis:
                        pl_analyses.append(analysis)
            except Exception as e:
                logger.error(f"Erro ao analisar PL {pl}: {str(e)}")
        
        if not pl_analyses:
            return {
                "timestamp": datetime.now().timestamp(),
                "error": "Não foi possível analisar nenhum dos PLs fornecidos"
            }
        
        # Calcular estatísticas
        risk_scores = [analysis['risco_aprovacao']['score'] for analysis in pl_analyses]
        avg_risk = sum(risk_scores) / len(risk_scores)
        
        # Classificar PLs por risco
        high_risk_pls = [a for a in pl_analyses if a['risco_aprovacao']['score'] >= 60]
        medium_risk_pls = [a for a in pl_analyses if 40 <= a['risco_aprovacao']['score'] < 60]
        low_risk_pls = [a for a in pl_analyses if a['risco_aprovacao']['score'] < 40]
        
        # Preparar visão geral
        overview = {
            "timestamp": datetime.now().timestamp(),
            "data_atualizacao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "numero_pls_analisados": len(pl_analyses),
            "risco_medio": avg_risk,
            "nivel_risco_medio": self._risk_level_name(avg_risk),
            "distribuicao_risco": {
                "alto_risco": len(high_risk_pls),
                "medio_risco": len(medium_risk_pls),
                "baixo_risco": len(low_risk_pls)
            },
            "pls_alto_risco": [
                {
                    "pl_id": pl['pl_id'],
                    "titulo": pl['titulo'],
                    "score": pl['risco_aprovacao']['score'],
                    "status": pl['status_atual']['situacao']
                } for pl in sorted(high_risk_pls, key=lambda x: x['risco_aprovacao']['score'], reverse=True)
            ],
            "proximos_eventos_criticos": self._identify_critical_events(pl_analyses)
        }
        
        return overview
    
    def _identify_critical_events(self, pl_analyses: List[Dict]) -> List[Dict]:
        """
        Identifica eventos críticos nos próximos passos dos PLs.
        
        Args:
            pl_analyses: Lista de análises de PLs
            
        Returns:
            Lista de eventos críticos ordenados por prioridade
        """
        critical_events = []
        
        for analysis in pl_analyses:
            # Considerar apenas PLs de alto risco
            if analysis['risco_aprovacao']['score'] >= 60:
                # Analisar próximos passos
                for step in analysis['proximos_passos']:
                    if step['probabilidade'] in ['Alta', 'Média']:
                        # Eventos de votação são especialmente críticos
                        if 'Votação' in step['passo'] or 'Parecer' in step['passo']:
                            critical_events.append({
                                "pl_id": analysis['pl_id'],
                                "titulo": analysis['titulo'],
                                "evento": step['passo'],
                                "probabilidade": step['probabilidade'],
                                "observacao": step['observacao'],
                                "risco": analysis['risco_aprovacao']['score']
                            })
        
        # Ordenar por risco (maior primeiro) e depois por probabilidade
        critical_events.sort(key=lambda x: (x['risco'], 1 if x['probabilidade'] == 'Alta' else 0), reverse=True)
        
        return critical_events[:5]  # Retornar os 5 mais críticos


# Exemplo de uso
if __name__ == "__main__":
    analyzer = PLRiskAnalyzer()
    
    # Analisar um PL específico
    print("Analisando PL 2234/2022...")
    analysis = analyzer.analyze_pl_risk("PL", "2234", "2022")
    
    print(f"\nRisco de aprovação: {analysis['risco_aprovacao']['score']:.1f} ({analysis['risco_aprovacao']['nivel']})")
    print(f"Tempo estimado: {analysis['tempo_estimado']['estimativa']}")
    
    print("\nFatores de risco:")
    for factor in analysis['risco_aprovacao']['fatores']:
        print(f"- {factor['fator']}: {factor['descricao']} ({factor['impacto']})")
    
    print("\nPróximos passos prováveis:")
    for step in analysis['proximos_passos']:
        print(f"- {step['passo']} ({step['probabilidade']})")
        print(f"  {step['observacao']}")
    
    # Análise de setor (PLs de apostas)
    pls_apostas = [
        {"Sigla": "PL", "Numero": "2234", "Ano": "2022"},
        {"Sigla": "PL", "Numero": "3405", "Ano": "2023"},
        {"Sigla": "PL", "Numero": "3563", "Ano": "2024"}
    ]
    
    print("\nAnalisando setor de apostas...")
    sector_analysis = analyzer.get_sector_risk_overview(pls_apostas)
    
    print(f"\nRisco médio do setor: {sector_analysis['risco_medio']:.1f} ({sector_analysis['nivel_risco_medio']})")
    print(f"Distribuição: {sector_analysis['distribuicao_risco']}")
    
    print("\nPLs de alto risco:")
    for pl in sector_analysis['pls_alto_risco']:
        print(f"- {pl['pl_id']}: {pl['titulo'][:50]}... (Score: {pl['score']:.1f})")
    
    print("\nPróximos eventos críticos:")
    for event in sector_analysis['proximos_eventos_criticos']:
        print(f"- {event['pl_id']}: {event['evento']} ({event['probabilidade']})")
        print(f"  {event['observacao']}")