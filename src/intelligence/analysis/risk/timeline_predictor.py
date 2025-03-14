"""
Preditor de timeline e próximos passos para PLs.
"""
import logging
import re
from datetime import datetime
from typing import Dict, List, Any, Tuple

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("timeline_predictor")

class TimelinePredictor:
    """
    Classe para previsão de timeline e próximos passos na tramitação de PLs.
    """
    
    # Mapeamento dos estágios comuns de tramitação e seus tempos médios (em meses)
    STAGE_TIMES = {
        "INICIAL": {"min": 1, "max": 3, "description": "Apresentação e distribuição"},
        "COMISSOES": {"min": 3, "max": 8, "description": "Tramitação nas comissões"},
        "CCJ": {"min": 2, "max": 5, "description": "Análise na CCJ"},
        "RELATOR": {"min": 1, "max": 3, "description": "Análise pelo relator"},
        "PLENARIO": {"min": 1, "max": 4, "description": "Votação em plenário"},
        "REVISAO": {"min": 2, "max": 5, "description": "Revisão na casa revisora"},
        "SANCAO": {"min": 0.5, "max": 1, "description": "Sanção/veto presidencial"}
    }
    
    # Sequências típicas de tramitação para diferentes tipos de projetos
    TYPICAL_PATHS = {
        "NORMAL": ["INICIAL", "COMISSOES", "CCJ", "PLENARIO", "REVISAO", "SANCAO"],
        "URGENTE": ["INICIAL", "RELATOR", "CCJ", "PLENARIO", "SANCAO"],
        "SIMPLIFICADO": ["INICIAL", "COMISSOES", "PLENARIO", "SANCAO"]
    }
    
    # Palavras-chave para identificar o estágio atual
    STAGE_KEYWORDS = {
        "INICIAL": ["APRESENTAÇÃO", "RECEBIDO", "PROTOCOLADO", "AUTUADO", "DISTRIBUÍDO"],
        "COMISSOES": ["COMISSÃO", "CAE", "CAS", "CE", "CI", "DESIGNADO RELATOR"],
        "CCJ": ["CCJ", "COMISSÃO DE CONSTITUIÇÃO E JUSTIÇA", "CONSTITUCIONALIDADE"],
        "RELATOR": ["RELATOR", "DESIGNADO", "DEVOLVIDO PELO RELATOR"],
        "PLENARIO": ["PLENÁRIO", "ORDEM DO DIA", "DISCUSSÃO", "VOTAÇÃO"],
        "REVISAO": ["CÂMARA", "REMESSA", "REVISÃO", "ENVIADO"],
        "SANCAO": ["SANÇÃO", "VETO", "PROMULGAÇÃO", "ENVIADO PARA SANÇÃO"]
    }
    
    @classmethod
    def estimate_approval_time(cls, 
                             pl_details: Dict[str, Any], 
                             situacao: Dict[str, Any], 
                             tramitacao: List[Dict[str, Any]]) -> Tuple[str, List[Dict]]:
        """
        Estima o tempo até a aprovação final do PL.
        
        Args:
            pl_details: Detalhes do PL
            situacao: Situação atual do PL
            tramitacao: Histórico de tramitação
            
        Returns:
            Tupla com (string de estimativa, lista de fatores)
        """
        # Validar entradas
        if not isinstance(pl_details, dict):
            logger.error(f"pl_details não é um dicionário: {type(pl_details)}")
            return "6-12 meses", [{
                "fator": "Estimativa padrão",
                "descricao": "Baseado em tempo médio de tramitação no Congresso",
                "impacto": "Neutro",
                "explicacao": "Analisador completo não disponível, usando estimativa padrão"
            }]
            
        if not isinstance(situacao, dict):
            logger.error(f"situacao não é um dicionário: {type(situacao)}")
            situacao = {}
            
        if not isinstance(tramitacao, list):
            logger.error(f"tramitacao não é uma lista: {type(tramitacao)}")
            tramitacao = []
        
        # Identificar o estágio atual
        current_stage = cls._identify_current_stage(situacao, tramitacao)
        
        # Determinar o caminho de tramitação mais provável
        path_type = cls._determine_path_type(pl_details, tramitacao)
        typical_path = cls.TYPICAL_PATHS[path_type]
        
        # Calcular tempo estimado
        remaining_months = cls._calculate_remaining_time(current_stage, typical_path)
        
        # Ajustar com base na velocidade histórica
        velocity_factor, velocity_explanation = cls._analyze_historical_velocity(tramitacao)
        adjusted_remaining = remaining_months * velocity_factor
        
        # Preparar fatores explicativos
        factors = []
        
        # Fator 1: Estágio atual
        stage_desc = cls.STAGE_TIMES.get(current_stage, {}).get("description", current_stage)
        factors.append({
            "fator": "Estágio atual",
            "descricao": f"PL está no estágio: {stage_desc}",
            "impacto": "Base para estimativa",
            "explicacao": f"Estágio atual identificado com base na situação e tramitação"
        })
        
        # Fator 2: Tipo de caminho de tramitação
        path_desc = "Tramitação normal" if path_type == "NORMAL" else "Tramitação urgente" if path_type == "URGENTE" else "Tramitação simplificada"
        factors.append({
            "fator": "Caminho de tramitação",
            "descricao": path_desc,
            "impacto": f"{'Redução' if path_type != 'NORMAL' else 'Base'} para estimativa",
            "explicacao": f"Tipo de tramitação identificado com base nas características do PL"
        })
        
        # Fator 3: Velocidade histórica
        if velocity_factor != 1.0:
            direction = "Redução" if velocity_factor < 1.0 else "Aumento"
            pct_change = abs(1.0 - velocity_factor) * 100
            factors.append({
                "fator": "Velocidade histórica",
                "descricao": velocity_explanation,
                "impacto": f"{direction} de {pct_change:.0f}% no tempo estimado",
                "explicacao": "Baseado na velocidade de tramitação observada até agora"
            })
        
        # Formatar a estimativa de tempo
        if adjusted_remaining < 1:
            time_estimate = f"{int(adjusted_remaining * 30)} dias"
        else:
            min_months = max(1, int(adjusted_remaining * 0.8))
            max_months = int(adjusted_remaining * 1.2)
            time_estimate = f"{min_months}-{max_months} meses"
        
        return time_estimate, factors
    
    @classmethod
    def _identify_current_stage(cls, situacao: Dict[str, Any], tramitacao: List[Dict[str, Any]]) -> str:
        """
        Identifica o estágio atual de tramitação.
        
        Args:
            situacao: Situação atual do PL
            tramitacao: Histórico de tramitação
            
        Returns:
            Estágio atual identificado
        """
        # Verificar a situação atual
        situacao_text = situacao.get('Situacao', '').upper() + " " + situacao.get('Local', '').upper()
        
        # Procurar por palavras-chave nos textos de situação e local
        for stage, keywords in cls.STAGE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in situacao_text:
                    return stage
        
        # Se não encontrou na situação, verificar a tramitação recente
        if tramitacao and len(tramitacao) > 0:
            tramitacao_text = tramitacao[0].get('Texto', '').upper() + " " + tramitacao[0].get('Local', '').upper()
            
            for stage, keywords in cls.STAGE_KEYWORDS.items():
                for keyword in keywords:
                    if keyword in tramitacao_text:
                        return stage
        
        # Se não conseguiu identificar, assume estágio inicial
        return "INICIAL"
    
    @classmethod
    def _determine_path_type(cls, pl_details: Dict[str, Any], tramitacao: List[Dict[str, Any]]) -> str:
        """
        Determina o tipo de caminho de tramitação mais provável.
        
        Args:
            pl_details: Detalhes do PL
            tramitacao: Histórico de tramitação
            
        Returns:
            Tipo de caminho (NORMAL, URGENTE, SIMPLIFICADO)
        """
        # Verificar características de urgência
        urgency_indicators = 0
        
        # Verificar título/ementa
        titulo = pl_details.get('Título', '').upper()
        
        if "URGÊNCIA" in titulo or "URGENTE" in titulo:
            urgency_indicators += 2
        
        # Verificar tramitação
        if tramitacao:
            # Calcular velocidade média entre eventos (se rápida, pode indicar urgência)
            if len(tramitacao) >= 3:
                try:
                    # Extrair datas dos eventos mais recentes
                    dates = []
                    for evento in tramitacao[:3]:
                        date_str = evento.get('Data', '')
                        if date_str:
                            dates.append(datetime.strptime(date_str, "%Y-%m-%d"))
                    
                    if len(dates) >= 2:
                        # Calcular diferença média em dias
                        diff_days = [(dates[i] - dates[i+1]).days for i in range(len(dates)-1)]
                        avg_days = sum(diff_days) / len(diff_days)
                        
                        # Se a média for menor que 7 dias, indicativo de tramitação rápida
                        if avg_days < 7:
                            urgency_indicators += 1
                        
                        # Se for menor que 3 dias, forte indicativo de urgência
                        if avg_days < 3:
                            urgency_indicators += 2
                except Exception as e:
                    logger.warning(f"Erro ao analisar datas de tramitação: {str(e)}")
            
            # Verificar palavras-chave de urgência nos eventos
            for evento in tramitacao[:5]:  # Verificar apenas os 5 mais recentes
                texto = evento.get('Texto', '').upper()
                situacao = evento.get('Situacao', '').upper()
                
                if "URGÊNCIA" in texto or "URGÊNCIA" in situacao or "URGENTE" in texto:
                    urgency_indicators += 2
                    break
        
        # Verificar autor (projetos do Executivo geralmente tramitam mais rápido)
        autor = pl_details.get('Autor', '').upper()
        if "PRESIDENTE" in autor or "EXECUTIVO" in autor or "MINISTÉRIO" in autor:
            urgency_indicators += 1
        
        # Determinar tipo com base nos indicadores
        if urgency_indicators >= 3:
            return "URGENTE"
        elif urgency_indicators >= 1:
            return "SIMPLIFICADO"
        else:
            return "NORMAL"
    
    @classmethod
    def _calculate_remaining_time(cls, current_stage: str, typical_path: List[str]) -> float:
        """
        Calcula o tempo estimado restante para completar a tramitação.
        
        Args:
            current_stage: Estágio atual de tramitação
            typical_path: Caminho típico de tramitação
            
        Returns:
            Tempo estimado em meses
        """
        # Verificar se o estágio atual está no caminho típico
        if current_stage in typical_path:
            current_index = typical_path.index(current_stage)
        else:
            # Se não está, assumir o primeiro estágio
            current_index = 0
        
        # Calcular tempo restante somando os tempos médios dos estágios restantes
        remaining_time = 0.0
        
        for stage in typical_path[current_index:]:
            stage_time = cls.STAGE_TIMES.get(stage, {"min": 1, "max": 3})
            # Usar valor médio entre mínimo e máximo
            remaining_time += (stage_time["min"] + stage_time["max"]) / 2
        
        return remaining_time
    
    @classmethod
    def _analyze_historical_velocity(cls, tramitacao: List[Dict[str, Any]]) -> Tuple[float, str]:
        """
        Analisa a velocidade histórica de tramitação.
        
        Args:
            tramitacao: Histórico de tramitação
            
        Returns:
            Tupla com (fator de velocidade, explicação)
        """
        if not tramitacao or len(tramitacao) < 2:
            return 1.0, "Histórico insuficiente para análise de velocidade"
        
        try:
            # Extrair datas da tramitação
            dates = []
            for evento in tramitacao:
                date_str = evento.get('Data', '')
                if date_str:
                    try:
                        dates.append(datetime.strptime(date_str, "%Y-%m-%d"))
                    except ValueError:
                        continue
            
            if len(dates) < 2:
                return 1.0, "Datas insuficientes para análise de velocidade"
            
            # Ordenar datas
            dates.sort(reverse=True)
            
            # Calcular tempo total e número de etapas
            total_days = (dates[0] - dates[-1]).days
            
            if total_days == 0:
                return 0.8, "Tramitação muito rápida, sugerindo prioridade"
            
            # Comparar com expectativa
            expected_days = len(dates) * 15  # Assumir média de 15 dias por etapa
            
            velocity_ratio = expected_days / total_days
            
            if velocity_ratio > 1.5:
                return 0.7, "Tramitação significativamente mais rápida que o normal"
            elif velocity_ratio > 1.1:
                return 0.9, "Tramitação ligeiramente mais rápida que o normal"
            elif velocity_ratio < 0.6:
                return 1.3, "Tramitação significativamente mais lenta que o normal"
            elif velocity_ratio < 0.9:
                return 1.1, "Tramitação ligeiramente mais lenta que o normal"
            else:
                return 1.0, "Velocidade de tramitação dentro da média"
        except Exception as e:
            logger.warning(f"Erro ao analisar velocidade histórica: {str(e)}")
            return 1.0, "Não foi possível calcular velocidade histórica"
    
    @classmethod
    def predict_next_steps(cls, 
                          pl_details: Dict[str, Any], 
                          situacao: Dict[str, Any], 
                          tramitacao: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Prediz os próximos passos na tramitação do PL.
        
        Args:
            pl_details: Detalhes do PL
            situacao: Situação atual do PL
            tramitacao: Histórico de tramitação
            
        Returns:
            Lista com próximos passos previstos
        """
        # Validar entradas
        if not isinstance(pl_details, dict):
            logger.error(f"pl_details não é um dicionário: {type(pl_details)}")
            return [{"passo": "Análise não disponível", "probabilidade": "N/A", "observacao": "Erro na análise"}]
            
        if not isinstance(situacao, dict):
            logger.error(f"situacao não é um dicionário: {type(situacao)}")
            situacao = {}
            
        if not isinstance(tramitacao, list):
            logger.error(f"tramitacao não é uma lista: {type(tramitacao)}")
            tramitacao = []
        
        # Verificar se há indicação de arquivamento ou rejeição
        if cls._check_for_termination(situacao, tramitacao):
            return [
                {
                    "passo": "Tramitação encerrada",
                    "probabilidade": "Alta",
                    "observacao": "PL arquivado, rejeitado ou prejudicado",
                    "contexto": "Análise simplificada, sem avaliação detalhada"
                }
            ]
        
        # Identificar o estágio atual
        current_stage = cls._identify_current_stage(situacao, tramitacao)
        
        # Determinar o caminho de tramitação mais provável
        path_type = cls._determine_path_type(pl_details, tramitacao)
        typical_path = cls.TYPICAL_PATHS[path_type].copy()
        
        # Se o estágio atual não está no caminho típico, incluir
        if current_stage not in typical_path:
            typical_path.insert(0, current_stage)
        
        # Encontrar índice do estágio atual
        current_index = typical_path.index(current_stage)
        
        # Próximos passos são os estágios seguintes
        next_steps = []
        
        # Verificar se ainda há passos a seguir
        if current_index >= len(typical_path) - 1:
            next_steps.append({
                "passo": "Conclusão da tramitação",
                "probabilidade": "Alta",
                "observacao": "PL em fase final de tramitação",
                "contexto": cls.STAGE_TIMES.get(current_stage, {}).get("description", current_stage)
            })
        else:
            # Adicionar próximos estágios como passos futuros
            for i, stage in enumerate(typical_path[current_index + 1:][:2]):  # Limitar a 2 próximos passos
                step_prob = "Alta" if i == 0 else "Média" if i == 1 else "Baixa"
                
                next_steps.append({
                    "passo": cls.STAGE_TIMES.get(stage, {}).get("description", stage),
                    "probabilidade": step_prob,
                    "observacao": cls._get_step_observation(stage, situacao, tramitacao),
                    "contexto": cls._get_step_context(i, stage, path_type)
                })
        
        # Se não há próximos passos identificados, usar fallback
        if not next_steps:
            next_steps = [
                {
                    "passo": "Análise em comissões",
                    "probabilidade": "Média",
                    "observacao": "Processo padrão de tramitação",
                    "contexto": "Análise simplificada, sem avaliação detalhada"
                },
                {
                    "passo": "Votação em plenário",
                    "probabilidade": "Baixa",
                    "observacao": "Após análise em comissões",
                    "contexto": "Processo padrão de tramitação legislativa"
                }
            ]
        
        return next_steps
    
    @classmethod
    def _check_for_termination(cls, situacao: Dict[str, Any], tramitacao: List[Dict[str, Any]]) -> bool:
        """
        Verifica se o PL já foi arquivado, rejeitado ou encerrado.
        
        Args:
            situacao: Situação atual do PL
            tramitacao: Histórico de tramitação
            
        Returns:
            True se a tramitação foi encerrada, False caso contrário
        """
        # Verificar situação atual
        situacao_text = situacao.get('Situacao', '').upper()
        
        terminal_keywords = ["ARQUIVAD", "REJEITAD", "PREJUDICAD", "RETIRAD", "VETADO", "ENCERRAD"]
        
        for keyword in terminal_keywords:
            if keyword in situacao_text:
                return True
        
        # Verificar último evento de tramitação
        if tramitacao and len(tramitacao) > 0:
            tramitacao_text = tramitacao[0].get('Texto', '').upper() + " " + tramitacao[0].get('Situacao', '').upper()
            
            for keyword in terminal_keywords:
                if keyword in tramitacao_text:
                    return True
        
        return False
    
    @classmethod
    def _get_step_observation(cls, stage: str, situacao: Dict[str, Any], tramitacao: List[Dict[str, Any]]) -> str:
        """
        Gera uma observação para um próximo passo.
        
        Args:
            stage: Estágio do próximo passo
            situacao: Situação atual do PL
            tramitacao: Histórico de tramitação
            
        Returns:
            Texto da observação
        """
        if stage == "COMISSOES":
            local_atual = situacao.get('Local', '')
            if "COMISSÃO" in local_atual:
                return f"Continuação da análise em {local_atual}"
            return "Análise nas comissões temáticas"
        
        elif stage == "CCJ":
            return "Análise de constitucionalidade e juridicidade"
        
        elif stage == "RELATOR":
            # Verificar se já tem relator designado
            has_relator = False
            if tramitacao:
                for evento in tramitacao[:5]:
                    if "DESIGNADO RELATOR" in evento.get('Texto', '').upper():
                        has_relator = True
                        break
            
            if has_relator:
                return "Análise pelo relator designado"
            else:
                return "Designação de relator e análise"
                
        elif stage == "PLENARIO":
            return "Votação em turno único ou primeiro turno"
            
        elif stage == "REVISAO":
            return "Envio à casa revisora (Câmara ou Senado)"
            
        elif stage == "SANCAO":
            return "Envio para sanção ou veto presidencial"
            
        else:
            return "Processo padrão de tramitação"
    
    @classmethod
    def _get_step_context(cls, step_index: int, stage: str, path_type: str) -> str:
        """
        Gera um contexto para um próximo passo.
        
        Args:
            step_index: Índice do passo na sequência
            stage: Estágio do passo
            path_type: Tipo de caminho de tramitação
            
        Returns:
            Texto de contexto
        """
        if step_index == 0:
            if path_type == "URGENTE":
                return "Tramitação em regime de urgência"
            elif path_type == "SIMPLIFICADO":
                return "Tramitação simplificada"
            else:
                return "Próximo passo no processo legislativo normal"
        else:
            return "Processo padrão de tramitação legislativa"