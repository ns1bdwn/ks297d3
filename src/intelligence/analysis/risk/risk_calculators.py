"""
Calculadoras para diferentes tipos de risco regulatório.
"""
import logging
from typing import Dict, List, Any, Tuple
from datetime import datetime

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("risk_calculator")

class RiskCalculator:
    """
    Classe para cálculo de diferentes métricas de risco regulatório.
    """
    
    # Comissões com maior poder de aprovação
    HIGH_POWER_COMMITTEES = [
        "CCJ", "CAE", "PLENÁRIO", "MESA", "COMISSÃO DIRETORA", 
        "COMISSÃO DE CONSTITUIÇÃO E JUSTIÇA", "COMISSÃO DE ASSUNTOS ECONÔMICOS"
    ]
    
    # Status que indicam avanço no processo legislativo
    ADVANCING_STATUS = [
        "APROVAD", "APROVAÇÃO", "VOTAÇÃO", "DESIGNADO RELATOR", 
        "INCLUÍDA EM ORDEM DO DIA", "PRONTA PARA A PAUTA", "AUDIÊNCIA PÚBLICA",
        "PARECER FAVORÁVEL", "URGÊNCIA"
    ]
    
    # Status que indicam estagnação ou arquivamento
    STALLED_STATUS = [
        "ARQUIVAD", "PREJUDICAD", "RETIRAD", "REJEITAD", 
        "DEVOLVID", "RETIRADO PELO AUTOR", "PARECER CONTRÁRIO"
    ]
    
    @staticmethod
    def risk_level_name(risk_score: float) -> str:
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
    
    @classmethod
    def calculate_approval_risk(cls, 
                              pl_details: Dict[str, Any], 
                              situacao: Dict[str, Any], 
                              tramitacao: List[Dict[str, Any]]) -> Tuple[float, List[Dict]]:
        """
        Calcula o risco de aprovação de um PL com base no status atual e histórico.
        
        Args:
            pl_details: Detalhes do PL
            situacao: Situação atual do PL
            tramitacao: Histórico de tramitação
            
        Returns:
            Tupla com score de risco (0-100) e lista de fatores que contribuíram
        """
        # Validar entradas
        if not isinstance(pl_details, dict):
            logger.error(f"pl_details não é um dicionário: {type(pl_details)}")
            return 50.0, [{"fator": "Erro de dados", "descricao": "Dados do PL inválidos", 
                          "impacto": "Neutro", "explicacao": "Usando pontuação padrão de 50%"}]
            
        if not isinstance(situacao, dict):
            logger.error(f"situacao não é um dicionário: {type(situacao)}")
            situacao = {}
            
        if not isinstance(tramitacao, list):
            logger.error(f"tramitacao não é uma lista: {type(tramitacao)}")
            tramitacao = []
        
        # Inicializar score e fatores
        risk_score = 50.0  # Começa com 50% de chance (neutro)
        risk_factors = []
        
        # Fator 1: Status atual
        current_status = situacao.get('Situacao', '').upper()
        current_location = situacao.get('Local', '').upper()
        
        # Verificar se está em comissão de alto poder
        in_powerful_committee = False
        for committee in cls.HIGH_POWER_COMMITTEES:
            if committee in current_location:
                in_powerful_committee = True
                risk_score += 10
                risk_factors.append({
                    "fator": "Localização atual",
                    "descricao": f"PL está em {situacao.get('Local', '')}",
                    "impacto": "+10 pontos",
                    "explicacao": "Comissões com maior poder de decisão aceleram a aprovação"
                })
                break
        
        if not in_powerful_committee and current_location:
            risk_score -= 5
            risk_factors.append({
                "fator": "Localização atual",
                "descricao": f"PL está em {situacao.get('Local', '')}",
                "impacto": "-5 pontos",
                "explicacao": "Comissões de menor influência tendem a atrasar o processo"
            })
        
        # Verificar status de avanço
        advancing = False
        for status in cls.ADVANCING_STATUS:
            if status in current_status:
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
        for status in cls.STALLED_STATUS:
            if status in current_status:
                stalled = True
                risk_score -= 40
                risk_factors.append({
                    "fator": "Status atual",
                    "descricao": f"Status: {situacao.get('Situacao', '')}",
                    "impacto": "-40 pontos",
                    "explicacao": "Status indica estagnação ou arquivamento"
                })
                break
        
        if not advancing and not stalled and current_status:
            risk_factors.append({
                "fator": "Status atual",
                "descricao": f"Status: {situacao.get('Situacao', '')}",
                "impacto": "Neutro",
                "explicacao": "Status atual não indica claramente avanço ou estagnação"
            })
        
        # Fator 2: Tempo desde a apresentação
        try:
            presentation_date = pl_details.get('Data', '')
            if presentation_date:
                presentation_date = datetime.strptime(presentation_date, "%Y-%m-%d")
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
        except Exception as e:
            logger.warning(f"Erro ao calcular tempo desde apresentação: {str(e)}")
        
        # Fator 3: Velocidade de tramitação
        if len(tramitacao) >= 2:
            try:
                # Calcular o tempo médio entre eventos
                dates = []
                for event in tramitacao:
                    if isinstance(event, dict) and event.get('Data'):
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
        if tramitacao and isinstance(tramitacao[0], dict) and tramitacao[0].get('Data'):
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
            except Exception as e:
                logger.warning(f"Erro ao calcular dias desde última movimentação: {str(e)}")
        
        # Fator 5: Verificar se tem relatores designados
        if 'Relatores' in pl_details:
            relatores = pl_details.get('Relatores', [])
            if isinstance(relatores, list) and len(relatores) > 0:
                risk_score += 10
                risk_factors.append({
                    "fator": "Designação de relatores",
                    "descricao": f"{len(relatores)} relator(es) designado(s)",
                    "impacto": "+10 pontos",
                    "explicacao": "PLs com relatores designados têm maior chance de avançar no processo legislativo"
                })
            else:
                risk_score -= 5
                risk_factors.append({
                    "fator": "Ausência de relatores",
                    "descricao": "Nenhum relator designado",
                    "impacto": "-5 pontos",
                    "explicacao": "A ausência de relatores pode indicar menor prioridade ou estágio inicial de tramitação"
                })
        
        # Fator 6: Relevância do autor
        autor = pl_details.get('Autor', '')
        
        # Verificar tipo de autor
        autor_influente = False
        if "Poder Executivo" in autor or "Presidente" in autor or "Ministério" in autor:
            autor_influente = True
            risk_score += 15
            risk_factors.append({
                "fator": "Relevância do autor",
                "descricao": f"Autor: {autor}",
                "impacto": "+15 pontos",
                "explicacao": "PLs do Poder Executivo têm maior prioridade e chance de aprovação"
            })
        elif "Mesa Diretora" in autor or "Comissão" in autor:
            autor_influente = True
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