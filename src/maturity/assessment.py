# src/maturity/assessment.py
"""
Classe para gerenciar avaliação de maturidade regulatória.
"""
import os
import json
import pandas as pd
import numpy as np
from datetime import datetime

class MaturityAssessment:
    """
    Gerencia a avaliação de maturidade regulatória, incluindo o questionário,
    cálculo de scores e geração de recomendações.
    """
    
    def __init__(self):
        """
        Inicializa a avaliação de maturidade com frameworks, dimensões,
        níveis de maturidade e questionário.
        """
        # Frameworks utilizados e suas proporções
        self.frameworks = {
            "COSO ERM": {"weight": 0.5, "color": "#366092"},
            "IBGC": {"weight": 0.2, "color": "#70AD47"},
            "ISO 31000": {"weight": 0.2, "color": "#ED7D31"},
            "AIR": {"weight": 0.1, "color": "#4472C4"}
        }
        
        # Dimensões avaliadas
        self.dimensions = [
            "Governança",
            "Cultura",
            "Estratégia",
            "Riscos",
            "Compliance",
            "Advocacy",
            "Tecnologia"
        ]
        
        # Níveis de maturidade
        self.maturity_levels = {
            1: {
                "label": "Inicial",
                "desc": "Processos ad hoc, pouca formalização, abordagem reativa."
            },
            2: {
                "label": "Básico",
                "desc": "Processos documentados, mas pouco integrados, abordagem proativa limitada."
            },
            3: {
                "label": "Estabelecido",
                "desc": "Processos padronizados e integrados, abordagem predominantemente proativa."
            },
            4: {
                "label": "Gerenciado",
                "desc": "Processos monitorados com métricas, melhoria contínua, integração estratégica."
            },
            5: {
                "label": "Otimizado",
                "desc": "Processos altamente otimizados, inovação, liderança no setor."
            }
        }
        
        # Carrega as perguntas do questionário
        self.questions = self._load_questions()
    
    def _load_questions(self):
        """
        Carrega as perguntas do questionário de um arquivo JSON ou define-as internamente.
        
        Returns:
            list: Lista de dicionários com as perguntas e metadados associados.
        """
        # Em uma versão real, isso carregaria de um arquivo
        # Por simplicidade, definimos diretamente no código
        
        questions = [
            {
                "id": "coso_1",
                "framework": "COSO ERM",
                "dimension": "Governança",
                "question": "A organização possui estrutura de governança que integra riscos regulatórios à gestão geral de riscos corporativos?",
                "evidence_examples": "Organograma, políticas formalizadas, mandato do comitê de riscos que inclua riscos regulatórios"
            },
            {
                "id": "coso_2",
                "framework": "COSO ERM",
                "dimension": "Estratégia",
                "question": "A empresa utiliza algum sistema de ERM (Enterprise Risk Management) que inclui ou poderia ser expandido para melhor gestão de riscos regulatórios?",
                "evidence_examples": "Demonstração do sistema ERM atual, avaliação de capacidade de integração, exemplos de como outros tipos de riscos são geridos"
            },
            {
                "id": "coso_3",
                "framework": "COSO ERM",
                "dimension": "Riscos",
                "question": "O processo de identificação e avaliação de riscos corporativos incorpora metodologias específicas para riscos regulatórios?",
                "evidence_examples": "Matriz integrada de riscos, procedimentos de avaliação de riscos, templates de análise que incluam critérios regulatórios"
            },
            {
                "id": "coso_4",
                "framework": "COSO ERM",
                "dimension": "Tecnologia",
                "question": "As ferramentas tecnológicas de gestão de riscos corporativos (ERM) são adaptadas ou complementadas para monitorar mudanças regulatórias?",
                "evidence_examples": "Integrações entre sistemas de ERM e monitoramento regulatório, workflows compartilhados, dashboards unificados"
            },
            {
                "id": "ibgc_1",
                "framework": "IBGC",
                "dimension": "Governança",
                "question": "A alta administração demonstra comprometimento com a gestão de riscos regulatórios?",
                "evidence_examples": "Atas de reunião, políticas assinadas, comunicações internas"
            },
            {
                "id": "ibgc_2",
                "framework": "IBGC",
                "dimension": "Cultura",
                "question": "Existe uma cultura de transparência e accountability relacionada a riscos regulatórios?",
                "evidence_examples": "Pesquisas de clima, documentos de comunicação, programas de treinamento"
            },
            {
                "id": "iso_1",
                "framework": "ISO 31000",
                "dimension": "Riscos",
                "question": "A gestão de riscos regulatórios é integrada aos processos organizacionais?",
                "evidence_examples": "Fluxos de processo, documentação de procedimentos, relatórios integrados"
            },
            {
                "id": "iso_2",
                "framework": "ISO 31000",
                "dimension": "Compliance",
                "question": "A organização monitora sistematicamente a eficácia de seus controles regulatórios?",
                "evidence_examples": "Relatórios de monitoramento, auditorias, indicadores de desempenho"
            },
            {
                "id": "air_1",
                "framework": "AIR",
                "dimension": "Advocacy",
                "question": "A organização participa ativamente de consultas públicas e processos regulatórios?",
                "evidence_examples": "Documentos de participação, contribuições formalizadas, registros de interação"
            },
            {
                "id": "air_2",
                "framework": "AIR",
                "dimension": "Compliance",
                "question": "São realizadas análises de impacto de novas regulações nos processos da organização?",
                "evidence_examples": "Relatórios de análise, documentos de planejamento de implementação"
            }
        ]
        
        return questions
    
    def calculate_scores(self, responses, evidences):
        """
        Calcula os scores de maturidade baseados nas respostas e evidências.
        
        Args:
            responses (dict): Dicionário com respostas (id_questao: valor_resposta)
            evidences (dict): Dicionário com evidências (id_questao: texto_evidencia)
            
        Returns:
            tuple: (framework_scores, dimension_scores, overall_score)
        """
        # Inicializa dicionários para armazenar scores
        framework_scores = {fw: 0 for fw in self.frameworks}
        framework_counts = {fw: 0 for fw in self.frameworks}
        
        dimension_scores = {dim: 0 for dim in self.dimensions}
        dimension_counts = {dim: 0 for dim in self.dimensions}
        
        # Processa cada questão respondida
        for q_id, response in responses.items():
            # Encontra a questão correspondente
            question = next((q for q in self.questions if q["id"] == q_id), None)
            if not question:
                continue
                
            framework = question["framework"]
            dimension = question["dimension"]
            
            # Valor base da resposta
            score = float(response)
            
            # Ajuste baseado em evidências
            evidence = evidences.get(q_id, "")
            
            # Corrigir o cálculo do evidence_bonus para evitar uso de len() em float
            if isinstance(evidence, str):
                evidence_bonus = min(0.3, len(evidence) / 500 * 0.3)
            else:
                evidence_bonus = 0
                
            # Se resposta >= 3 mas sem evidências suficientes, ajustar para 2.5
            if score >= 3 and (not evidence or len(str(evidence)) < 50):
                adjusted_score = 2.5
            else:
                adjusted_score = score + evidence_bonus
            
            # Limitar score máximo a 5
            adjusted_score = min(5, adjusted_score)
            
            # Acumular scores por framework e dimensão
            framework_scores[framework] += adjusted_score
            framework_counts[framework] += 1
            
            dimension_scores[dimension] += adjusted_score
            dimension_counts[dimension] += 1
        
        # Calcular médias por framework
        for fw in framework_scores:
            if framework_counts[fw] > 0:
                framework_scores[fw] /= framework_counts[fw]
            else:
                framework_scores[fw] = 0
        
        # Calcular médias por dimensão
        for dim in dimension_scores:
            if dimension_counts[dim] > 0:
                dimension_scores[dim] /= dimension_counts[dim]
            else:
                dimension_scores[dim] = 0
        
        # Calcular score geral ponderado por framework
        overall_score = sum(framework_scores[fw] * self.frameworks[fw]["weight"] 
                           for fw in framework_scores)
        
        return framework_scores, dimension_scores, overall_score
    
    def _get_maturity_level(self, score):
        """
        Retorna o nível de maturidade correspondente ao score.
        
        Args:
            score (float): Score entre 1 e 5
            
        Returns:
            dict: Label e descrição do nível de maturidade
        """
        # Arredondar para o nível mais próximo
        level = round(score)
        
        # Garantir que está dentro dos limites
        level = max(1, min(5, level))
        
        return self.maturity_levels[level]
    
    def _generate_recommendations(self, framework_scores, dimension_scores):
        """
        Gera recomendações baseadas nos scores calculados.
        
        Args:
            framework_scores (dict): Scores por framework
            dimension_scores (dict): Scores por dimensão
            
        Returns:
            list: Lista de recomendações
        """
        recommendations = []
        
        # Encontrar dimensões com scores mais baixos
        sorted_dimensions = sorted(dimension_scores.items(), key=lambda x: x[1])
        low_dimensions = [dim for dim, score in sorted_dimensions[:3] if score < 4]
        
        # Gerar recomendações para dimensões com baixo score
        for dimension in low_dimensions:
            if dimension == "Governança":
                recommendations.append({
                    "area": "Governança",
                    "recommendation": "Expandir o escopo do comitê de riscos existente para incluir riscos regulatórios de forma estruturada",
                    "priority": "Alta" if dimension_scores[dimension] < 3 else "Média"
                })
            elif dimension == "Cultura":
                recommendations.append({
                    "area": "Cultura",
                    "recommendation": "Integrar conscientização regulatória aos programas existentes de cultura de riscos",
                    "priority": "Alta" if dimension_scores[dimension] < 3 else "Média"
                })
            elif dimension == "Estratégia":
                recommendations.append({
                    "area": "Estratégia",
                    "recommendation": "Adaptar ferramentas de planejamento estratégico para considerar impactos regulatórios nas decisões de negócio",
                    "priority": "Alta" if dimension_scores[dimension] < 3 else "Média"
                })
            elif dimension == "Riscos":
                recommendations.append({
                    "area": "Riscos",
                    "recommendation": "Enriquecer metodologias de ERM existentes com critérios específicos para avaliação de riscos regulatórios",
                    "priority": "Alta" if dimension_scores[dimension] < 3 else "Média"
                })
            elif dimension == "Compliance":
                recommendations.append({
                    "area": "Compliance",
                    "recommendation": "Integrar o monitoramento de compliance regulatório aos sistemas de gestão de riscos corporativos",
                    "priority": "Alta" if dimension_scores[dimension] < 3 else "Média"
                })
            elif dimension == "Advocacy":
                recommendations.append({
                    "area": "Advocacy",
                    "recommendation": "Estabelecer processo de feedback entre participação regulatória e avaliação de riscos corporativos",
                    "priority": "Alta" if dimension_scores[dimension] < 3 else "Média"
                })
            elif dimension == "Tecnologia":
                recommendations.append({
                    "area": "Tecnologia",
                    "recommendation": "Implementar integrações entre sistemas de ERM e ferramentas de monitoramento regulatório",
                    "priority": "Alta" if dimension_scores[dimension] < 3 else "Média"
                })
        
        # Adicionar recomendação baseada no framework com menor score
        lowest_framework = min(framework_scores.items(), key=lambda x: x[1])
        if lowest_framework[0] == "COSO ERM" and lowest_framework[1] < 3.5:
            recommendations.append({
                "area": "Gestão de Riscos",
                "recommendation": "Adaptar framework COSO ERM para melhor incorporar riscos regulatórios específicos do setor",
                "priority": "Alta" if lowest_framework[1] < 3 else "Média"
            })
        elif lowest_framework[0] == "IBGC" and lowest_framework[1] < 3.5:
            recommendations.append({
                "area": "Governança Corporativa",
                "recommendation": "Alinhar práticas de governança às recomendações do IBGC",
                "priority": "Alta" if lowest_framework[1] < 3 else "Média"
            })
        elif lowest_framework[0] == "ISO 31000" and lowest_framework[1] < 3.5:
            recommendations.append({
                "area": "Processo de Gestão de Riscos",
                "recommendation": "Estruturar processo de gestão de riscos conforme ISO 31000",
                "priority": "Alta" if lowest_framework[1] < 3 else "Média"
            })
        elif lowest_framework[0] == "AIR" and lowest_framework[1] < 3.5:
            recommendations.append({
                "area": "Análise de Impacto",
                "recommendation": "Implementar metodologia formal de análise de impacto regulatório",
                "priority": "Alta" if lowest_framework[1] < 3 else "Média"
            })
        
        return recommendations
    
    def generate_assessment_report(self, client_id, responses, evidences):
        """
        Gera um relatório completo da avaliação de maturidade.
        
        Args:
            client_id (str): Identificador do cliente
            responses (dict): Respostas do questionário
            evidences (dict): Evidências fornecidas
            
        Returns:
            dict: Dados do relatório gerado
        """
        # Calcular scores
        framework_scores, dimension_scores, overall_score = self.calculate_scores(responses, evidences)
        
        # Obter nível de maturidade
        maturity_level = self._get_maturity_level(overall_score)
        
        # Gerar recomendações
        recommendations = self._generate_recommendations(framework_scores, dimension_scores)
        
        # Dados do relatório
        report = {
            "client_id": client_id,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "overall_score": overall_score,
            "maturity_level": maturity_level,
            "framework_scores": framework_scores,
            "dimension_scores": dimension_scores,
            "responses": responses,
            "evidences": evidences,
            "recommendations": recommendations
        }
        
        return report