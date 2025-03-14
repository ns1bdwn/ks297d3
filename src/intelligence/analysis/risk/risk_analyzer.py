"""
Classe principal de análise de risco regulatório.
"""
import os
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from .risk_calculators import RiskCalculator
from .timeline_predictor import TimelinePredictor
from .context_analyzer import ContextAnalyzer
from ..providers.senado_provider import SenadoProvider

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("pl_risk_analyzer")

class PLRiskAnalyzer:
    """
    Analisador de risco regulatório para Projetos de Lei.
    Utiliza dados reais de APIs legislativas para avaliar riscos.
    """
    
    def __init__(self, data_dir: str = None):
        """
        Inicializa o analisador de risco.
        
        Args:
            data_dir: Diretório para armazenar dados de análise.
        """
        # Diretório base para dados com caminho absoluto
        if data_dir is None:
            # Usar caminho absoluto relativo ao script
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.abspath(os.path.join(script_dir, "../../../.."))
            self.data_dir = os.path.join(project_root, "data", "risk_analysis")
            logger.info(f"Diretório de análise configurado: {self.data_dir}")
        else:
            self.data_dir = data_dir
        
        # Garantir que o diretório existe
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Provedor de dados padrão (Senado)
        self.provider = SenadoProvider()
        
        # Cache de análises realizadas
        self.analysis_cache = {}
    
    def analyze_pl_risk(self, sigla: str, numero: str, ano: str, 
                       force_refresh: bool = False) -> Dict[str, Any]:
        """
        Analisa o risco regulatório de um PL com base nos dados reais.
        
        Args:
            sigla: Sigla do PL (ex: PL, PEC)
            numero: Número do PL
            ano: Ano do PL
            force_refresh: Se True, força nova análise mesmo se houver cache
            
        Returns:
            Dicionário com análise de risco aprimorada
        """
        pl_id = f"{sigla} {numero}/{ano}"
        logger.info(f"Analisando risco regulatório do {pl_id}")
        
        # Verificar cache em memória
        if not force_refresh and pl_id in self.analysis_cache:
            logger.info(f"Usando análise em cache na memória para {pl_id}")
            return self.analysis_cache[pl_id]
        
        # Verificar cache em disco
        if not force_refresh:
            cache_file = os.path.join(self.data_dir, f"{sigla}_{numero}_{ano}_risk.json")
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        analysis = json.load(f)
                    
                    # Verificar se a análise é recente (menos de 24 horas)
                    if isinstance(analysis, dict) and 'timestamp' in analysis:
                        analysis_time = analysis.get('timestamp', 0)
                        now = datetime.now().timestamp()
                        
                        if now - analysis_time < 24 * 60 * 60:
                            logger.info(f"Usando análise recente em disco para {pl_id}")
                            # Atualizar cache em memória
                            self.analysis_cache[pl_id] = analysis
                            return analysis
                except Exception as e:
                    logger.error(f"Erro ao carregar análise do disco para {pl_id}: {str(e)}")
        
        # Buscar dados detalhados do PL
        pl_id_info = {
            'sigla': sigla,
            'numero': numero,
            'ano': ano
        }
        
        pl_details = self.provider.get_pl_details(pl_id_info)
        
        if not pl_details:
            logger.warning(f"PL {pl_id} não encontrado")
            error_result = {
                "pl_id": pl_id,
                "timestamp": datetime.now().timestamp(),
                "data_atualizacao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "error": "PL não encontrado"
            }
            return error_result
        
        # Extrair informações relevantes
        situacao = pl_details.get('Situacao', {})
        tramitacao = pl_details.get('Tramitacao_Detalhada', [])
        
        # Realizar análise contextual
        contexto_ai = ContextAnalyzer.analyze_context(pl_details, situacao, tramitacao)
        
        # Calcular o risco de aprovação
        risk_score, risk_factors = RiskCalculator.calculate_approval_risk(pl_details, situacao, tramitacao)
        
        # Adicionar fatores de risco baseados na análise contextual
        if contexto_ai["urgencia"] == "Alta":
            risk_score += 10
            risk_factors.append({
                "fator": "Urgência Legislativa",
                "descricao": "PL com indicadores de tramitação urgente",
                "impacto": "+10 pontos",
                "explicacao": "A urgência aumenta significativamente as chances de aprovação rápida"
            })
        
        if contexto_ai["controversia"] == "Alta":
            risk_score -= 5
            risk_factors.append({
                "fator": "Controvérsia",
                "descricao": "PL apresenta elementos controversos",
                "impacto": "-5 pontos",
                "explicacao": "Temas controversos tendem a enfrentar maior resistência e debate"
            })
        
        # Calcular tempo estimado para aprovação
        time_estimate, time_factors = TimelinePredictor.estimate_approval_time(pl_details, situacao, tramitacao)
        
        # Ajustar estimativa baseada na análise contextual
        if contexto_ai["urgencia"] == "Alta":
            # Reduzir tempo estimado
            if "meses" in time_estimate:
                parts = time_estimate.split("-")
                if len(parts) == 2:
                    try:
                        min_months = int(parts[0])
                        max_months = int(parts[1].replace(" meses", ""))
                        time_estimate = f"{max(1, min_months-2)}-{max(3, max_months-3)} meses"
                    except ValueError:
                        pass
            
            # Adicionar fator explicativo
            time_factors.append({
                "fator": "Urgência Legislativa",
                "descricao": "PL com sinais de tramitação prioritária",
                "impacto": "Redução significativa no tempo esperado",
                "explicacao": "Projetos com urgência têm prazos reduzidos em todas as etapas"
            })
        
        # Calcular próximos passos prováveis
        next_steps = TimelinePredictor.predict_next_steps(pl_details, situacao, tramitacao)
        
        # Adicionar análise de tendência política
        political_trend = {
            "tendencia": "Favorável" if risk_score > 60 else "Neutra" if risk_score > 40 else "Desfavorável",
            "contexto_politico": contexto_ai["contexto_politico"],
            "impacto_setorial": contexto_ai["impacto_setorial"]
        }
        
        # Extrair detalhes de autoria
        detalhes_autoria = self._extract_autoria_detalhada(pl_details)
        
        # Limitar o risco a 0-100
        risk_score = max(0, min(100, risk_score))
        
        # Montar análise completa aprimorada
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
                "nivel": RiskCalculator.risk_level_name(risk_score),
                "fatores": risk_factors
            },
            "tempo_estimado": {
                "estimativa": time_estimate,
                "fatores": time_factors
            },
            "proximos_passos": next_steps,
            "analise_politica": political_trend,
            "ultimos_eventos": tramitacao[:5] if tramitacao else [],
            "detalhes_autoria": detalhes_autoria,
            "projetos_relacionados": pl_details.get('projetos_relacionados', []) if 'projetos_relacionados' in pl_details else []
        }
        
        # Salvar em cache (memória)
        self.analysis_cache[pl_id] = analysis
        
        # Salvar em disco
        try:
            cache_file = os.path.join(self.data_dir, f"{sigla}_{numero}_{ano}_risk.json")
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, ensure_ascii=False, indent=4)
                logger.info(f"Análise de risco salva em disco: {cache_file}")
        except Exception as e:
            logger.error(f"Erro ao salvar análise em disco para {pl_id}: {str(e)}")
        
        return analysis
    
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
        
        # Coletar contextos políticos e setoriais
        contextos_politicos = []
        contextos_setoriais = []
        for analysis in pl_analyses:
            if 'analise_politica' in analysis:
                if 'contexto_politico' in analysis['analise_politica']:
                    contexto = analysis['analise_politica']['contexto_politico']
                    if contexto and contexto not in contextos_politicos and contexto != "Não disponível":
                        contextos_politicos.append(contexto)
                
                if 'impacto_setorial' in analysis['analise_politica']:
                    contexto = analysis['analise_politica']['impacto_setorial']
                    if contexto and contexto not in contextos_setoriais and contexto != "Não disponível":
                        contextos_setoriais.append(contexto)
        
        # Identificar eventos críticos
        eventos_criticos = self._identify_critical_events(pl_analyses)
        
        # Preparar visão geral
        overview = {
            "timestamp": datetime.now().timestamp(),
            "data_atualizacao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "numero_pls_analisados": len(pl_analyses),
            "risco_medio": avg_risk,
            "nivel_risco_medio": RiskCalculator.risk_level_name(avg_risk),
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
            "contextos_politicos": contextos_politicos[:3],  # Limitar a 3 contextos
            "contextos_setoriais": contextos_setoriais[:3],  # Limitar a 3 contextos
            "proximos_eventos_criticos": eventos_criticos
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
                                "contexto": step.get('contexto', ''),
                                "risco": analysis['risco_aprovacao']['score']
                            })
        
        # Ordenar por risco (maior primeiro) e depois por probabilidade
        critical_events.sort(key=lambda x: (x['risco'], 1 if x['probabilidade'] == 'Alta' else 0), reverse=True)
        
        return critical_events[:5]  # Retornar os 5 mais críticos
    
    def _extract_autoria_detalhada(self, pl_details: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Extrai detalhes de autoria do PL.
        
        Args:
            pl_details: Detalhes do PL
            
        Returns:
            Lista com informações dos autores
        """
        autores = []
        
        # Extrair da estrutura detalhes_adicionais, se disponível
        if 'detalhes_adicionais' in pl_details and 'autoria_detalhada' in pl_details['detalhes_adicionais']:
            autoria_detalhada = pl_details['detalhes_adicionais']['autoria_detalhada']
            if isinstance(autoria_detalhada, list):
                return autoria_detalhada
        
        # Extrair do campo Autor principal como fallback
        autor_principal = pl_details.get('Autor', '')
        if autor_principal:
            # Tentar extrair partido/UF do nome do autor
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
            if "Senador" in nome or "Senadora" in nome:
                tipo = "Parlamentar"
            elif "Executivo" in nome or "Presidente" in nome:
                tipo = "Poder Executivo"
            elif "Comissão" in nome:
                tipo = "Comissão"
            else:
                tipo = "Outro"
            
            autores.append({
                "nome": nome,
                "tipo": tipo,
                "partido": partido,
                "uf": uf
            })
        
        # Extrair de Relatores se disponível
        if 'Relatores' in pl_details:
            relatores = pl_details.get('Relatores', [])
            if isinstance(relatores, list):
                for relator in relatores:
                    # Verificar se o relator já está na lista
                    if isinstance(relator, dict):
                        nome_relator = relator.get('Nome', '')
                        if nome_relator and not any(a.get('nome') == nome_relator for a in autores):
                            autores.append({
                                "nome": nome_relator,
                                "tipo": "Relator",                             
                                "partido": relator.get('SiglaPartido', ''),
                                "uf": relator.get('UF', ''),
                                "comissao": relator.get('Comissao', '')
                            })
        
        return autores