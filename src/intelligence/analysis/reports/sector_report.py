"""
Gerador de relatórios setoriais para riscos regulatórios.
"""
import os
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("sector_report_generator")

class SectorReportGenerator:
    """
    Gerador de relatórios setoriais para riscos regulatórios.
    """
    
    def __init__(self, reports_dir: str = None):
        """
        Inicializa o gerador de relatórios.
        
        Args:
            reports_dir: Diretório para armazenar relatórios. Se None, usa o padrão.
        """
        if reports_dir is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.abspath(os.path.join(script_dir, "../../../.."))
            self.reports_dir = os.path.join(project_root, "data", "reports")
        else:
            self.reports_dir = reports_dir
        
        # Garantir que o diretório existe
        os.makedirs(self.reports_dir, exist_ok=True)
    
    def generate_sector_report(self, sector_overview: Dict[str, Any], sector_name: str) -> Dict[str, Any]:
        """
        Gera um relatório setorial com base em uma visão geral de riscos.
        
        Args:
            sector_overview: Visão geral dos riscos setoriais
            sector_name: Nome do setor
            
        Returns:
            Relatório setorial enriquecido
        """
        try:
            # Verificar dados mínimos necessários
            if 'risco_medio' not in sector_overview or 'pls_alto_risco' not in sector_overview:
                logger.error("Dados insuficientes para gerar relatório setorial")
                return {"error": "Dados insuficientes para gerar relatório setorial"}
            
            # Criar estrutura básica do relatório
            report = {
                "titulo": f"Relatório de Risco Regulatório - Setor {sector_name}",
                "data_geracao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "setor": sector_name,
                "periodo_analise": datetime.now().strftime("%d/%m/%Y"),
                "visao_geral": self._generate_overview_section(sector_overview),
                "pls_criticos": self._format_critical_pls(sector_overview),
                "eventos_monitorados": self._format_critical_events(sector_overview),
                "conclusoes": self._generate_conclusions(sector_overview, sector_name),
                "recomendacoes": self._generate_recommendations(sector_overview, sector_name)
            }
            
            # Salvar relatório em disco
            self._save_report(report, sector_name)
            
            return report
        except Exception as e:
            logger.error(f"Erro ao gerar relatório setorial: {str(e)}")
            return {"error": f"Erro ao gerar relatório setorial: {str(e)}"}
    
    def _generate_overview_section(self, sector_overview: Dict[str, Any]) -> Dict[str, Any]:
        """
        Gera a seção de visão geral do relatório.
        
        Args:
            sector_overview: Visão geral dos riscos setoriais
            
        Returns:
            Seção de visão geral formatada
        """
        # Extrair dados relevantes
        num_pls = sector_overview.get('numero_pls_analisados', 0)
        risco_medio = sector_overview.get('risco_medio', 0)
        nivel_risco = sector_overview.get('nivel_risco_medio', 'Não disponível')
        
        # Distribuição de risco
        distribuicao = sector_overview.get('distribuicao_risco', {})
        alto_risco = distribuicao.get('alto_risco', 0)
        medio_risco = distribuicao.get('medio_risco', 0)
        baixo_risco = distribuicao.get('baixo_risco', 0)
        
        # Calcular porcentagens
        pct_alto = (alto_risco / num_pls * 100) if num_pls > 0 else 0
        pct_medio = (medio_risco / num_pls * 100) if num_pls > 0 else 0
        pct_baixo = (baixo_risco / num_pls * 100) if num_pls > 0 else 0
        
        # Formatar seção
        return {
            "numero_pls_analisados": num_pls,
            "risco_medio": risco_medio,
            "nivel_risco_medio": nivel_risco,
            "distribuicao": {
                "alto_risco": {
                    "quantidade": alto_risco,
                    "porcentagem": round(pct_alto, 1)
                },
                "medio_risco": {
                    "quantidade": medio_risco,
                    "porcentagem": round(pct_medio, 1)
                },
                "baixo_risco": {
                    "quantidade": baixo_risco,
                    "porcentagem": round(pct_baixo, 1)
                }
            },
            "interpretacao": self._interpret_risk_level(nivel_risco, pct_alto)
        }
    
    def _interpret_risk_level(self, nivel_risco: str, pct_alto_risco: float) -> str:
        """
        Gera uma interpretação textual do nível de risco.
        
        Args:
            nivel_risco: Nível médio de risco
            pct_alto_risco: Porcentagem de PLs de alto risco
            
        Returns:
            Interpretação textual
        """
        if nivel_risco in ["Alto", "Muito Alto"]:
            return (
                f"O setor apresenta um nível {nivel_risco.lower()} de risco regulatório, "
                f"com {pct_alto_risco:.1f}% dos PLs analisados classificados como alto risco. "
                f"Recomenda-se atenção imediata e monitoramento intensivo dos PLs críticos."
            )
        elif nivel_risco == "Médio":
            return (
                f"O setor apresenta um nível médio de risco regulatório, "
                f"com {pct_alto_risco:.1f}% dos PLs analisados classificados como alto risco. "
                f"Recomenda-se monitoramento regular e preparação para possíveis mudanças."
            )
        else:
            return (
                f"O setor apresenta um nível {nivel_risco.lower()} de risco regulatório, "
                f"com apenas {pct_alto_risco:.1f}% dos PLs analisados classificados como alto risco. "
                f"Recomenda-se monitoramento periódico para identificar eventuais mudanças."
            )
    
    def _format_critical_pls(self, sector_overview: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Formata a lista de PLs críticos para o relatório.
        
        Args:
            sector_overview: Visão geral dos riscos setoriais
            
        Returns:
            Lista formatada de PLs críticos
        """
        pls_alto_risco = sector_overview.get('pls_alto_risco', [])
        
        # Limitar aos 5 PLs mais críticos
        return pls_alto_risco[:5]
    
    def _format_critical_events(self, sector_overview: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Formata a lista de eventos críticos para o relatório.
        
        Args:
            sector_overview: Visão geral dos riscos setoriais
            
        Returns:
            Lista formatada de eventos críticos
        """
        eventos = sector_overview.get('proximos_eventos_criticos', [])
        
        # Limitar aos 5 eventos mais críticos
        return eventos[:5]
    
    def _generate_conclusions(self, sector_overview: Dict[str, Any], sector_name: str) -> str:
        """
        Gera conclusões para o relatório setorial.
        
        Args:
            sector_overview: Visão geral dos riscos setoriais
            sector_name: Nome do setor
            
        Returns:
            Conclusões textuais
        """
        # Extrair dados relevantes
        risco_medio = sector_overview.get('risco_medio', 0)
        nivel_risco = sector_overview.get('nivel_risco_medio', 'Médio')
        
        distribuicao = sector_overview.get('distribuicao_risco', {})
        alto_risco = distribuicao.get('alto_risco', 0)
        
        # Gerar conclusão com base no nível de risco
        if nivel_risco in ["Alto", "Muito Alto"]:
            return (
                f"O cenário regulatório para o setor de {sector_name} apresenta um elevado nível de risco, "
                f"com score médio de {risco_medio:.1f}% e {alto_risco} projetos de lei classificados como alto risco. "
                f"Este cenário indica alta probabilidade de mudanças significativas no ambiente regulatório no curto prazo, "
                f"exigindo atenção imediata da alta administração e preparação de planos de contingência para adaptação "
                f"às novas exigências regulatórias."
            )
        elif nivel_risco == "Médio":
            return (
                f"O cenário regulatório para o setor de {sector_name} apresenta um nível moderado de risco, "
                f"com score médio de {risco_medio:.1f}% e {alto_risco} projetos de lei classificados como alto risco. "
                f"Este cenário sugere possibilidade de mudanças no ambiente regulatório no médio prazo, "
                f"recomendando monitoramento contínuo e preparação gradual para adaptação às potenciais "
                f"alterações regulatórias."
            )
        else:
            return (
                f"O cenário regulatório para o setor de {sector_name} apresenta um nível baixo de risco, "
                f"com score médio de {risco_medio:.1f}% e apenas {alto_risco} projetos de lei classificados como alto risco. "
                f"Este cenário sugere estabilidade regulatória no curto e médio prazo, permitindo "
                f"foco em otimização dos processos atuais de compliance e monitoramento periódico "
                f"para identificação precoce de eventuais mudanças."
            )
    
    def _generate_recommendations(self, sector_overview: Dict[str, Any], sector_name: str) -> List[Dict[str, str]]:
        """
        Gera recomendações estratégicas para o relatório setorial.
        
        Args:
            sector_overview: Visão geral dos riscos setoriais
            sector_name: Nome do setor
            
        Returns:
            Lista de recomendações
        """
        # Extrair dados relevantes
        nivel_risco = sector_overview.get('nivel_risco_medio', 'Médio')
        distribuicao = sector_overview.get('distribuicao_risco', {})
        alto_risco = distribuicao.get('alto_risco', 0)
        
        # Recomendações básicas por nível de risco
        if nivel_risco in ["Alto", "Muito Alto"]:
            return [
                {
                    "area": "Monitoramento",
                    "recomendacao": f"Implementar monitoramento diário dos {alto_risco} PLs de alto risco, com alertas automáticos para movimentações críticas.",
                    "prioridade": "Alta"
                },
                {
                    "area": "Advocacy",
                    "recomendacao": "Intensificar esforços de advocacy regulatório através de associações setoriais, priorizando os PLs com maior potencial de impacto negativo.",
                    "prioridade": "Alta"
                },
                {
                    "area": "Compliance",
                    "recomendacao": "Desenvolver planos de adaptação para cenários regulatórios mais prováveis, com foco em prazos reduzidos de implementação.",
                    "prioridade": "Alta"
                },
                {
                    "area": "Governança",
                    "recomendacao": "Elevar o tema para discussão periódica em nível de Conselho de Administração, com envolvimento direto da alta gestão.",
                    "prioridade": "Alta"
                }
            ]
        elif nivel_risco == "Médio":
            return [
                {
                    "area": "Monitoramento",
                    "recomendacao": f"Estabelecer processo de monitoramento semanal dos {alto_risco} PLs de alto risco, com reports para áreas impactadas.",
                    "prioridade": "Média"
                },
                {
                    "area": "Advocacy",
                    "recomendacao": "Participar ativamente em grupos de trabalho setoriais para discussão e influência nas principais propostas legislativas.",
                    "prioridade": "Média"
                },
                {
                    "area": "Compliance",
                    "recomendacao": "Elaborar assessments de impacto regulatório para os PLs críticos, com mapeamento de adaptações necessárias.",
                    "prioridade": "Média"
                },
                {
                    "area": "Governança",
                    "recomendacao": "Incluir riscos regulatórios como item fixo nas reuniões mensais de comitê de riscos.",
                    "prioridade": "Média"
                }
            ]
        else:
            return [
                {
                    "area": "Monitoramento",
                    "recomendacao": "Manter monitoramento mensal das proposições legislativas relevantes para o setor.",
                    "prioridade": "Baixa"
                },
                {
                    "area": "Advocacy",
                    "recomendacao": "Manter participação em fóruns setoriais para acompanhamento do cenário regulatório.",
                    "prioridade": "Baixa"
                },
                {
                    "area": "Compliance",
                    "recomendacao": "Revisar periodicamente os processos de compliance para garantir aderência ao ambiente regulatório atual.",
                    "prioridade": "Média"
                },
                {
                    "area": "Governança",
                    "recomendacao": "Incluir atualização trimestral sobre cenário regulatório nas reuniões de comitê de riscos.",
                    "prioridade": "Baixa"
                }
            ]
    
    def _save_report(self, report: Dict[str, Any], sector_name: str) -> str:
        """
        Salva o relatório setorial em disco.
        
        Args:
            report: Relatório setorial
            sector_name: Nome do setor
            
        Returns:
            Caminho do arquivo salvo
        """
        try:
            # Formatar nome do arquivo
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            sector_slug = sector_name.lower().replace(" ", "_")
            filename = f"setor_{sector_slug}_relatorio_{timestamp}.json"
            
            # Caminho completo
            file_path = os.path.join(self.reports_dir, filename)
            
            # Salvar o relatório
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=4)
            
            logger.info(f"Relatório setorial salvo em: {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Erro ao salvar relatório setorial: {str(e)}")
            return ""