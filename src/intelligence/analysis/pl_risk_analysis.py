# src/intelligence/analysis/pl_risk_analysis.py
"""
Módulo para análise de risco regulatório baseado em dados reais dos PLs.
Utiliza dados da API do Senado e algoritmos de análise para avaliar o risco.
"""
import logging
import json
import os
import re
from datetime import datetime, timedelta
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
    Utiliza dados reais da API do Senado para avaliar riscos.
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
        Analisa o risco regulatório de um PL com base nos dados reais da API do Senado.
        
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
        
        # CORREÇÃO: Usar o método correto get_pl_by_id em vez de get_additional_pl_details
        pl_details = self.senado_api.get_pl_by_id(sigla, numero, ano)
        
        if not pl_details:
            logger.warning(f"PL {sigla} {numero}/{ano} não encontrado na API do Senado")
            return {
                "pl_id": pl_id,
                "timestamp": datetime.now().timestamp(),
                "error": "PL não encontrado na API do Senado"
            }
        
        # CORREÇÃO: Enriquecer dados com informações adicionais
        if pl_details:
            try:
                # Obter código da matéria se disponível
                codigo_materia = pl_details.get('CodigoMateria')
                
                # Buscar tramitação detalhada se não tiver
                if 'Tramitacao' not in pl_details or not pl_details['Tramitacao']:
                    tramitacao = self.senado_api.get_pl_tramitacao(sigla, numero, ano, codigo_materia)
                    pl_details['Tramitacao'] = tramitacao
                    
                # Buscar relatores se tiver código da matéria
                if codigo_materia and ('Relatores' not in pl_details or not pl_details.get('Relatores')):
                    relatores = self.senado_api.get_pl_relatores(codigo_materia)
                    pl_details['Relatores'] = relatores
            except Exception as e:
                logger.warning(f"Erro ao enriquecer dados do PL: {str(e)}")
        
        # Extrair informações relevantes
        situacao = pl_details.get('Situacao', {})
        tramitacao = pl_details.get('Tramitacao', [])
        
        # Realizar análise contextual
        contexto_ai = self._analyze_context_with_ai(pl_details, situacao, tramitacao)
        
        # Calcular o risco de aprovação
        risk_score, risk_factors = self._calculate_approval_risk(pl_details, situacao, tramitacao)
        
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
        time_estimate, time_factors = self._estimate_approval_time(pl_details, situacao, tramitacao)
        
        # Calcular próximos passos prováveis com análise aprimorada
        next_steps = self._predict_next_steps(pl_details, situacao, tramitacao)
        
        # Adicionar análise de tendência política
        political_trend = {
            "tendencia": "Favorável" if risk_score > 60 else "Neutra" if risk_score > 40 else "Desfavorável",
            "contexto_politico": contexto_ai["contexto_politico"],
            "impacto_setorial": contexto_ai["impacto_setorial"]
        }
        
        # Extrair detalhes de autoria
        detalhes_autoria = self._extract_autoria_detalhada(pl_details)
        
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
                "nivel": self._risk_level_name(risk_score),
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
            "projetos_relacionados": pl_details.get('detalhes_adicionais', {}).get('projetos_relacionados', [])
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

    def _extract_autoria_detalhada(self, pl_details: Dict) -> List[Dict]:
        """
        Extrai detalhes de autoria do PL.
        
        Args:
            pl_details: Detalhes do PL
            
        Returns:
            Lista com informações dos autores
        """
        autores = []
        
        # Extrair da estrutura detalhes_adicionais, se disponível
        autoria_detalhada = pl_details.get('detalhes_adicionais', {}).get('autoria_detalhada', [])
        if autoria_detalhada:
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
        relatores = pl_details.get('Relatores', [])
        for relator in relatores:
            # Verificar se o relator já está na lista
            nome_relator = relator.get('Nome', '')
            if nome_relator and not any(a['nome'] == nome_relator for a in autores):
                autores.append({
                    "nome": nome_relator,
                    "tipo": "Relator",
                    "partido": relator.get('Partido', ''),
                    "uf": relator.get('UF', ''),
                    "comissao": relator.get('Comissao', '')
                })
        
        return autores

    def _analyze_context_with_ai(self, pl_details, situacao, tramitacao):
        """
        Utiliza análise baseada em regras para análise contextual do PL.
        
        Args:
            pl_details: Detalhes do PL
            situacao: Situação atual
            tramitacao: Histórico de tramitação
            
        Returns:
            Dicionário com análise contextual
        """
        try:
            # CORREÇÃO: Análise mais específica e robusta
            titulo = pl_details.get('Título', '')
            keywords = pl_details.get('Palavras-chave', '')
            autor = pl_details.get('Autor', '')
            status_atual = situacao.get('Situacao', '') + " " + situacao.get('Local', '')
            
            # Verificar setores específicos afetados
            setores = {
                "igaming": ["apostas", "jogo", "bet", "cassino", "loteria", "quota fixa", "gaming"],
                "meios_pagamento": ["pagamento", "pix", "cartão", "banco", "financeiro", "transferência", "payment"],
                "digital_assets": ["cripto", "bitcoin", "blockchain", "token", "digital", "ativo", "nft", "stablecoin"]
            }
            
            texto_completo = (titulo + " " + keywords + " " + autor + " " + status_atual).lower()
            
            # Detectar setores específicos afetados
            setor_detectado = None
            for setor, termos in setores.items():
                if any(termo in texto_completo for termo in termos):
                    setor_detectado = setor
                    break
            
            # Concatenar eventos de tramitação recentes
            eventos_texto = ""
            for evento in tramitacao[:5]:  # Apenas os 5 eventos mais recentes
                data = evento.get('Data', '')
                local = evento.get('Local', '')
                situacao_evt = evento.get('Situacao', '')
                texto = evento.get('Texto', '')
                
                eventos_texto += f"{data} - {local} - {situacao_evt}: {texto}\n"
            
            # Texto completo para análise
            texto_completo += " " + eventos_texto.lower()
            
            # Análise de urgência e prioridade
            urgencia_keywords = ["urgência", "prioridade", "relevante", "imediato", "emergencial"]
            controversia_keywords = ["polêmico", "controverso", "divergência", "debate", "discordância", "crítica"]
            
            urgencia_score = sum(1 for kw in urgencia_keywords if kw in texto_completo)
            controversia_score = sum(1 for kw in controversia_keywords if kw in texto_completo)
            
            # Identificar se há relatores (aumenta urgência)
            if 'Relatores' in pl_details and pl_details['Relatores']:
                urgencia_score += 1
            
            # Verificar se está em comissão de alto poder (aumenta urgência)
            local_atual = situacao.get('Local', '').upper()
            for committee in self.HIGH_POWER_COMMITTEES:
                if committee in local_atual:
                    urgencia_score += 1
                    break
            
            # Resultado da análise contextual
            return {
                "urgencia": "Alta" if urgencia_score >= 2 else "Média" if urgencia_score == 1 else "Baixa",
                "controversia": "Alta" if controversia_score >= 2 else "Média" if controversia_score == 1 else "Baixa",
                "contexto_politico": self._analise_contexto_politico(pl_details),
                "impacto_setorial": self._analise_impacto_setorial(pl_details) if setor_detectado else 
                                   "Impacto setorial não identificado automaticamente."
            }
        except Exception as e:
            logger.error(f"Erro na análise contextual: {str(e)}")
            return {
                "urgencia": "Média",
                "controversia": "Média",
                "contexto_politico": "Não disponível devido a erro na análise",
                "impacto_setorial": "Não disponível devido a erro na análise"
            }

    def _analise_contexto_politico(self, pl_details):
        """Analisa o contexto político do PL com base nos autores e timing"""
        try:
            autor = pl_details.get('Autor', '')
            
            # Verificar se há relatores
            tem_relator = 'Relatores' in pl_details and len(pl_details['Relatores']) > 0
            
            # Extrair informações básicas de contexto
            contexto = ""
            
            # Verificar tipo de autor
            if "Executivo" in autor or "Presidente" in autor or "Ministério" in autor:
                contexto += "PL de iniciativa do Poder Executivo, geralmente com alta prioridade e maior probabilidade de aprovação. "
            elif "Comissão" in autor or "Mesa Diretora" in autor:
                contexto += "PL institucional, com tramitação potencialmente mais rápida devido ao apoio dos órgãos diretivos. "
            elif "Senador" in autor or "Senadora" in autor:
                # Tentar extrair o partido
                partido_match = re.search(r'\((.*?)/.*?\)', autor)
                if partido_match:
                    partido = partido_match.group(1)
                    contexto += f"PL de autoria parlamentar do partido {partido}. "
                else:
                    contexto += "PL de autoria parlamentar. "
            
            # Analisar relatores
            if tem_relator:
                relatores = pl_details['Relatores']
                if len(relatores) == 1:
                    relator = relatores[0]
                    contexto += f"Possui relator designado: {relator.get('Nome', '')} ({relator.get('Partido', '')}/{relator.get('UF', '')}) na comissão {relator.get('Comissao', '')}. "
                else:
                    contexto += f"Possui {len(relatores)} relatores designados em diferentes comissões, o que indica tramitação ativa. "
            else:
                contexto += "Não possui relator designado, o que pode indicar estágio inicial de tramitação. "
            
            # Analisar situação atual
            situacao = pl_details.get('Situacao', {})
            local_atual = situacao.get('Local', '')
            status_atual = situacao.get('Situacao', '')
            
            if local_atual:
                if any(committee.upper() in local_atual.upper() for committee in self.HIGH_POWER_COMMITTEES):
                    contexto += f"Encontra-se em {local_atual}, que é uma instância decisória de alta influência no processo legislativo. "
                else:
                    contexto += f"Encontra-se em {local_atual}. "
            
            if status_atual:
                contexto += f"Status atual: {status_atual}. "
            
            # Analisar tempo de tramitação
            data_apresentacao = pl_details.get('Data', '')
            if data_apresentacao:
                try:
                    data_inicial = datetime.strptime(data_apresentacao, "%Y-%m-%d")
                    tempo_tramitacao = (datetime.now() - data_inicial).days
                    
                    if tempo_tramitacao < 30:
                        contexto += "Projeto recente com menos de 30 dias de tramitação. "
                    elif tempo_tramitacao < 180:
                        contexto += "Projeto em tramitação há menos de 6 meses. "
                    elif tempo_tramitacao < 365:
                        contexto += "Projeto em tramitação há menos de 1 ano. "
                    else:
                        contexto += f"Projeto em tramitação há mais de {tempo_tramitacao // 365} anos, indicando possíveis obstáculos políticos ou baixa prioridade. "
                except Exception:
                    pass
            
            if not contexto:
                contexto = "Contexto político não disponível devido à limitação de informações."
                
            return contexto
        except Exception as e:
            logger.error(f"Erro na análise de contexto político: {str(e)}")
            return "Não foi possível determinar o contexto político devido a erro na análise."

    def _analise_impacto_setorial(self, pl_details):
        """Análise do impacto setorial com base em palavras-chave e tema"""
        try:
            titulo = pl_details.get('Título', '')
            keywords = pl_details.get('Palavras-chave', '').split(',')
            keywords = [k.strip().lower() for k in keywords if k.strip()]
            
            texto_completo = titulo.lower() + " " + " ".join(keywords)
            
            # Setores de interesse
            setores = {
                "igaming": ["apostas", "jogo", "bet", "cassino", "loteria", "quota fixa", "gaming"],
                "meios_pagamento": ["pagamento", "pix", "cartão", "banco", "financeiro", "transferência", "payment"],
                "digital_assets": ["cripto", "bitcoin", "blockchain", "token", "digital", "ativo", "nft", "stablecoin", "moeda virtual"]
            }
            
            # Identificar setores afetados
            setores_afetados = []
            for setor, termos in setores.items():
                if any(termo in texto_completo for termo in termos):
                    setores_afetados.append(setor)
            
            if not setores_afetados:
                # Tentar identificar por setor mais amplo
                setores_amplos = {
                    "tributário": ["tributo", "imposto", "taxa", "contribuição", "fiscal"],
                    "regulatório": ["regulação", "marco regulatório", "lei", "norma", "regra"],
                    "tecnológico": ["tecnologia", "internet", "digital", "online", "eletrônico"],
                    "financeiro": ["financeiro", "bancário", "crédito", "investimento", "finança"]
                }
                
                for setor, termos in setores_amplos.items():
                    if any(termo in texto_completo for termo in termos):
                        setores_afetados.append(setor)
            
            if not setores_afetados:
                return "Impacto setorial não identificado automaticamente. Recomenda-se análise manual."
                
            # Personalizar mensagem por setor
            if "igaming" in setores_afetados:
                return """
                PL com potencial impacto direto no setor de iGaming. Recomenda-se atenção especial às disposições sobre:
                
                • Licenciamento e requisitos operacionais
                • Tributação específica do setor
                • Mecanismos de jogo responsável e prevenção à ludopatia
                • Requisitos de KYC e prevenção à lavagem de dinheiro
                • Restrições de publicidade e marketing
                
                Este projeto pode alterar significativamente o ambiente regulatório do setor, requerendo possíveis adaptações em processos, sistemas e políticas internas.
                """
            elif "meios_pagamento" in setores_afetados:
                return """
                PL com impacto no setor de meios de pagamento. Áreas críticas a monitorar:
                
                • Regulação de taxas e tarifas
                • Requisitos de interoperabilidade
                • Novas exigências de transparência
                • Proteção de dados de transações
                • Alterações em prazos de liquidação
                
                Empresas do setor podem precisar adaptar infraestrutura tecnológica e processos operacionais para atender a novos requisitos regulatórios.
                """
            elif "digital_assets" in setores_afetados:
                return """
                PL relacionado a ativos digitais. Pontos de atenção:
                
                • Definição legal de criptoativos
                • Requisitos de registro e licenciamento
                • Tratamento tributário de operações
                • Regras de KYC/AML para exchanges
                • Regulação sobre custódia e administração de ativos
                
                O projeto pode estabelecer novas obrigações para operadores do mercado e impactar a oferta de serviços relacionados a criptoativos no Brasil.
                """
            elif "tributário" in setores_afetados:
                return """
                PL com impacto tributário. Principais aspectos a considerar:
                
                • Possíveis alterações em alíquotas ou base de cálculo
                • Novas obrigações acessórias
                • Mudanças em regimes especiais
                • Impactos em planejamento fiscal
                
                Recomenda-se análise detalhada para quantificar impactos financeiros e adequar processos fiscais.
                """
            else:
                return f"""
                PL com possível impacto nos setores: {', '.join(setores_afetados)}. 
                
                Recomenda-se análise detalhada do texto para identificar:
                • Novos requisitos regulatórios
                • Mudanças em processos operacionais
                • Impactos em compliance
                • Necessidades de adaptação tecnológica
                
                Uma avaliação específica permitirá quantificar custos e esforços de adaptação necessários.
                """
        except Exception as e:
            logger.error(f"Erro na análise de impacto setorial: {str(e)}")
            return "Não foi possível determinar o impacto setorial devido a erro na análise."
    
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
        for status in self.STALLED_STATUS:
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
        
        # Fator 5: Verificar se tem relatores designados
        tem_relator = 'Relatores' in pl_details and len(pl_details['Relatores']) > 0
        if tem_relator:
            risk_score += 10
            risk_factors.append({
                "fator": "Designação de relatores",
                "descricao": f"{len(pl_details['Relatores'])} relator(es) designado(s)",
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
            if status in current_status:
                time_factors.append({
                    "fator": "Status atual",
                    "descricao": f"Status: {situacao.get('Situacao', '')}",
                    "impacto": "Não aplicável",
                    "explicacao": "PL arquivado, prejudicado ou retirado"
                })
                return "Não aplicável (PL não está em tramitação ativa)", time_factors
        
        # Estimativa baseada na localização atual
        current_location = situacao.get('Local', '').upper()
        
        # Verificar se está em plenário
        if "PLENÁRIO" in current_location:
            estimate = "3-6 meses"
            time_factors.append({
                "fator": "Localização atual",
                "descricao": f"PL está em {situacao.get('Local', '')}",
                "impacto": "3-6 meses",
                "explicacao": "PLs em Plenário geralmente têm tramitação mais rápida se houver prioridade"
            })
        # Verificar se está na CCJ
        elif "CCJ" in current_location or "CONSTITUIÇÃO E JUSTIÇA" in current_location:
            estimate = "6-12 meses"
            time_factors.append({
                "fator": "Localização atual",
                "descricao": f"PL está em {situacao.get('Local', '')}",
                "impacto": "6-12 meses",
                "explicacao": "A CCJ é uma comissão crucial e pode demandar análise detalhada"
            })
        # Verificar se está em comissão de alto poder
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
        
        # Verificar se tem relatores (acelera o processo)
        tem_relator = 'Relatores' in pl_details and len(pl_details['Relatores']) > 0
        if tem_relator:
            time_factors.append({
                "fator": "Presença de relatores",
                "descricao": f"{len(pl_details['Relatores'])} relator(es) designado(s)",
                "impacto": "Redução no tempo estimado",
                "explicacao": "A designação de relatores acelera o processo legislativo"
            })
            
            # Reduzir o tempo estimado
            if "-" in estimate:
                parts = estimate.split("-")
                if len(parts) == 2:
                    try:
                        min_months = max(1, int(parts[0]) - 2)
                        max_months = max(min_months + 2, int(parts[1].replace(" meses", "")) - 2)
                        estimate = f"{min_months}-{max_months} meses"
                    except ValueError:
                        pass
        
        return estimate, time_factors
    
    def _predict_next_steps(self, pl_details: Dict, situacao: Dict, tramitacao: List[Dict]) -> List[Dict]:
        """
        Prediz os próximos passos prováveis na tramitação de um PL.
        
        Args:
            pl_details: Detalhes do PL
            situacao: Situação atual do PL
            tramitacao: Histórico de tramitação
            
        Returns:
            Lista de próximos passos prováveis com probabilidades e contextualização
        """
        next_steps = []
        
        # Verificar se está arquivado ou prejudicado
        current_status = situacao.get('Situacao', '').upper()
        for status in self.STALLED_STATUS:
            if status in current_status:
                return [{
                    "passo": "PL não está em tramitação ativa",
                    "probabilidade": "Alta",
                    "observacao": "PL foi arquivado, prejudicado ou retirado",
                    "contexto": "O projeto não terá continuidade no processo legislativo a menos que haja recurso ou reapresentação."
                }]
        
        # Localização atual
        current_location = situacao.get('Local', '')
        
        # Verificar se tem relatores designados
        tem_relator = 'Relatores' in pl_details and len(pl_details['Relatores']) > 0
        relator_nome = ""
        if tem_relator and pl_details['Relatores']:
            relator = pl_details['Relatores'][0]
            relator_nome = relator.get('Nome', '')
        
        # Predizer próximos passos com base na localização atual e contexto
        if "Plenário" in current_location:
            # Análise para PLs em Plenário
            next_steps.append({
                "passo": "Votação em Plenário",
                "probabilidade": "Alta",
                "observacao": "PL já está no Plenário, próximo passo natural é a votação",
                "contexto": "Tempo estimado: 7-14 dias."
            })
            
            next_steps.append({
                "passo": "Aprovação no Plenário",
                "probabilidade": "Média",
                "observacao": "Votação para aprovação do PL no plenário",
                "contexto": "Após ser pautado, o PL será submetido à votação."
            })
            
            next_steps.append({
                "passo": "Encaminhamento para próxima etapa",
                "probabilidade": "Média",
                "observacao": "Se aprovado, seguirá para próxima fase do processo legislativo",
                "contexto": "Após aprovação, o PL seguirá para a Câmara (se originário do Senado) ou para sanção/promulgação (se já aprovado na Câmara)."
            })
        
        elif "CCJ" in current_location or "Constituição e Justiça" in current_location:
            # Análise para PLs na CCJ
            next_steps.append({
                "passo": "Designação de Relator" if not tem_relator else "Emissão de Parecer pelo Relator",
                "probabilidade": "Alta",
                "observacao": f"Relator: {'Já designado - ' + relator_nome if tem_relator else 'Pendente'}",
                "contexto": f"{'Relator já designado: ' + relator_nome + '. ' if tem_relator else 'Aguardando designação de relator. '}"
                          f"Na CCJ, o tempo médio para emissão de parecer é de aproximadamente 30 dias."
            })
            
            next_steps.append({
                "passo": "Votação na CCJ",
                "probabilidade": "Alta" if tem_relator else "Média",
                "observacao": "Após parecer, o projeto será votado na comissão",
                "contexto": f"{'Com relator já designado, o processo tende a ser mais rápido. ' if tem_relator else ''}"
            })
            
            next_steps.append({
                "passo": "Encaminhamento para outras comissões",
                "probabilidade": "Média",
                "observacao": "Após a CCJ, o projeto segue para outras comissões pertinentes",
                "contexto": f"A CCJ é uma etapa determinante. PLs aprovados na CCJ têm maior chance de aprovação nas comissões subsequentes."
            })
        
        elif "Comissão" in current_location:
            # Análise para PLs em outras comissões
            next_steps.append({
                "passo": "Designação de Relator" if not tem_relator else "Emissão de Parecer pelo Relator",
                "probabilidade": "Alta",
                "observacao": f"Relator: {'Já designado - ' + relator_nome if tem_relator else 'Pendente'}",
                "contexto": f"{'Relator já designado: ' + relator_nome + '. ' if tem_relator else 'Aguardando designação de relator. '}"
                          f"O tempo médio para emissão de parecer é de aproximadamente 30 dias."
            })
            
            next_steps.append({
                "passo": "Votação na Comissão",
                "probabilidade": "Alta" if tem_relator else "Média",
                "observacao": "Após parecer, o projeto é votado na comissão",
                "contexto": f"{'Com relator já designado, o processo tende a ser mais rápido. ' if tem_relator else ''}"
            })
            
            next_steps.append({
                "passo": "Realização de Audiência Pública",
                "probabilidade": "Média",
                "observacao": "Possível audiência pública para debater o projeto",
                "contexto": "Audiências públicas podem estender o tempo de tramitação em 15-30 dias."
            })
        
        else:
            # Caso genérico ou início de tramitação
            next_steps = [
                {
                    "passo": "Distribuição para Comissões",
                    "probabilidade": "Alta",
                    "observacao": "PL será distribuído para análise em comissões pertinentes",
                    "contexto": "A distribuição inicial geralmente ocorre em até 15 dias após a apresentação."
                },
                {
                    "passo": "Designação de Relator",
                    "probabilidade": "Média",
                    "observacao": "Designação de relator para analisar o PL",
                    "contexto": "A designação de relator é fundamental para o andamento do PL e geralmente ocorre após a distribuição para comissões."
                },
                {
                    "passo": "Inclusão na pauta de comissão",
                    "probabilidade": "Baixa",
                    "observacao": "PL pode ser incluído na pauta de votação de alguma comissão",
                    "contexto": "O tempo médio para inclusão na pauta após designação de relator é de aproximadamente 45 dias."
                }
            ]
        
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