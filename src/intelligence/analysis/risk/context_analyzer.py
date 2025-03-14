"""
Analisador de contexto político e setorial para PLs.
"""
import logging
import re
from typing import Dict, List, Any

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("context_analyzer")

class ContextAnalyzer:
    """
    Classe para análise de contexto político e setorial de PLs.
    Implementa métodos baseados em regras como fallback para modelos de IA.
    """
    
    # Palavras-chave que indicam urgência
    URGENCY_KEYWORDS = [
        "URGENTE", "URGÊNCIA", "PRIORIDADE", "EMERGENCIAL", "IMEDIATO",
        "REGIME DE URGÊNCIA", "TRAMITAÇÃO URGENTE", "SOLICITAÇÃO DE URGÊNCIA"
    ]
    
    # Palavras-chave que indicam controvérsia
    CONTROVERSY_KEYWORDS = [
        "POLÊMICO", "CONTROVERSO", "DIVERGENTE", "DEBATE", "DISCUSSÃO ACALORADA",
        "OPINIÕES DIVIDIDAS", "RESISTÊNCIA", "OPOSIÇÃO", "MANIFESTAÇÃO CONTRÁRIA",
        "EMBATE", "CONFLITO", "DISCORDÂNCIA"
    ]
    
    # Setores regulados para impacto setorial
    REGULATED_SECTORS = {
        "iGaming": [
            "APOSTAS", "JOGOS DE AZAR", "JOGO ONLINE", "CASSINO", "BINGO", 
            "LOTERIA", "JOGO RESPONSÁVEL", "QUOTA FIXA", "REGULAMENTAÇÃO DE JOGOS"
        ],
        "Meios de Pagamento": [
            "PAGAMENTO", "PIX", "CARTÃO DE CRÉDITO", "BANCO CENTRAL", 
            "MEIOS DE PAGAMENTO", "ARRANJO DE PAGAMENTO", "PAGAMENTO INSTANTÂNEO"
        ],
        "Digital Assets": [
            "CRIPTOMOEDA", "BITCOIN", "BLOCKCHAIN", "TOKEN", "NFT", 
            "STABLECOIN", "ATIVOS VIRTUAIS", "ATIVOS DIGITAIS"
        ]
    }
    
    @classmethod
    def analyze_context(cls, 
                       pl_details: Dict[str, Any], 
                       situacao: Dict[str, Any], 
                       tramitacao: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Realiza análise contextual do PL baseada em regras.
        
        Args:
            pl_details: Detalhes do PL
            situacao: Situação atual do PL
            tramitacao: Histórico de tramitação
            
        Returns:
            Dicionário com análise contextual
        """
        # Validar entradas
        if not isinstance(pl_details, dict):
            logger.error(f"pl_details não é um dicionário: {type(pl_details)}")
            return {
                "urgencia": "Baixa",
                "controversia": "Baixa",
                "contexto_politico": "Contexto político não disponível",
                "impacto_setorial": "Impacto setorial não disponível"
            }
        
        # Analisar urgência
        urgencia = cls._analyze_urgency(pl_details, situacao, tramitacao)
        
        # Analisar controvérsia
        controversia = cls._analyze_controversy(pl_details, tramitacao)
        
        # Determinar contexto político
        contexto_politico = cls._determine_political_context(pl_details, situacao, tramitacao)
        
        # Analisar impacto setorial
        impacto_setorial = cls._analyze_sector_impact(pl_details)
        
        return {
            "urgencia": urgencia,
            "controversia": controversia,
            "contexto_politico": contexto_politico,
            "impacto_setorial": impacto_setorial
        }
    
    @classmethod
    def _analyze_urgency(cls, pl_details: Dict[str, Any], situacao: Dict[str, Any], tramitacao: List[Dict[str, Any]]) -> str:
        """
        Analisa o nível de urgência de um PL com base em seu status e tramitação.
        
        Args:
            pl_details: Detalhes do PL
            situacao: Situação atual do PL
            tramitacao: Histórico de tramitação
            
        Returns:
            Nível de urgência ("Alta", "Média" ou "Baixa")
        """
        urgency_score = 0
        
        # Verificar situação atual
        situacao_desc = situacao.get('Situacao', '').upper()
        for keyword in cls.URGENCY_KEYWORDS:
            if keyword in situacao_desc:
                urgency_score += 3
                break
        
        # Verificar tramitação recente
        if tramitacao and len(tramitacao) > 0:
            # Verificar últimos 5 eventos ou todos se houver menos
            for evento in tramitacao[:min(5, len(tramitacao))]:
                texto = evento.get('Texto', '').upper()
                for keyword in cls.URGENCY_KEYWORDS:
                    if keyword in texto:
                        urgency_score += 2
                        break
        
        # Verificar título/ementa
        titulo = pl_details.get('Título', '').upper()
        for keyword in cls.URGENCY_KEYWORDS:
            if keyword in titulo:
                urgency_score += 1
                break
        
        # Classificar urgência com base no score
        if urgency_score >= 3:
            return "Alta"
        elif urgency_score >= 1:
            return "Média"
        else:
            return "Baixa"
    
    @classmethod
    def _analyze_controversy(cls, pl_details: Dict[str, Any], tramitacao: List[Dict[str, Any]]) -> str:
        """
        Analisa o nível de controvérsia de um PL.
        
        Args:
            pl_details: Detalhes do PL
            tramitacao: Histórico de tramitação
            
        Returns:
            Nível de controvérsia ("Alta", "Média" ou "Baixa")
        """
        controversy_score = 0
        
        # Verificar título/ementa
        titulo = pl_details.get('Título', '').upper()
        for keyword in cls.CONTROVERSY_KEYWORDS:
            if keyword in titulo:
                controversy_score += 2
                break
        
        # Verificar tramitação
        if tramitacao and len(tramitacao) > 0:
            contradiction_count = 0
            rejection_count = 0
            
            for evento in tramitacao:
                texto = evento.get('Texto', '').upper()
                situacao = evento.get('Situacao', '').upper()
                
                # Verificar palavras-chave de controvérsia
                for keyword in cls.CONTROVERSY_KEYWORDS:
                    if keyword in texto:
                        controversy_score += 1
                        break
                
                # Verificar rejeições ou votos contrários
                if "REJEITA" in texto or "CONTRÁRIO" in texto or "VOTO CONTRÁRIO" in texto:
                    rejection_count += 1
                
                # Verificar contradições (aprovações seguidas de rejeições ou vice-versa)
                if ("APROVA" in texto and "REJEITA" in situacao) or ("REJEITA" in texto and "APROVA" in situacao):
                    contradiction_count += 1
            
            # Adicionar pontuação baseada em rejeições e contradições
            controversy_score += min(3, rejection_count)
            controversy_score += min(3, contradiction_count * 2)
        
        # Classificar controvérsia com base no score
        if controversy_score >= 4:
            return "Alta"
        elif controversy_score >= 2:
            return "Média"
        else:
            return "Baixa"
    
    @classmethod
    def _determine_political_context(cls, pl_details: Dict[str, Any], situacao: Dict[str, Any], tramitacao: List[Dict[str, Any]]) -> str:
        """
        Determina o contexto político do PL.
        
        Args:
            pl_details: Detalhes do PL
            situacao: Situação atual do PL
            tramitacao: Histórico de tramitação
            
        Returns:
            Contexto político textual
        """
        # Informações básicas para o contexto
        autor = pl_details.get('Autor', 'Autor não identificado')
        status = pl_details.get('Status', 'Status não disponível')
        
        # Verificar se há alguma informação na tramitação
        tramitacao_info = ""
        if tramitacao and len(tramitacao) > 0:
            ultimo_evento = tramitacao[0]
            data = ultimo_evento.get('Data', '')
            local = ultimo_evento.get('Local', '')
            situacao_desc = ultimo_evento.get('Situacao', '')
            
            if data and (local or situacao_desc):
                tramitacao_info = f" Último evento em {data}: {situacao_desc} - {local}."
        
        # Identificar tipo de autor
        tipo_autor = ""
        if "Senador" in autor or "Senadora" in autor or "Deputado" in autor or "Deputada" in autor:
            tipo_autor = "parlamentar"
        elif "Comissão" in autor:
            tipo_autor = "comissão parlamentar"
        elif "Executivo" in autor or "Presidente" in autor or "Ministério" in autor:
            tipo_autor = "Poder Executivo"
        else:
            tipo_autor = "autor"
        
        # Compor contexto
        contexto = f"PL apresentado por {autor} ({tipo_autor}). Status atual: {status}."
        
        if tramitacao_info:
            contexto += tramitacao_info
        
        return contexto
    
    @classmethod
    def _analyze_sector_impact(cls, pl_details: Dict[str, Any]) -> str:
        """
        Analisa o impacto setorial do PL.
        
        Args:
            pl_details: Detalhes do PL
            
        Returns:
            Descrição do impacto setorial
        """
        # Se não há informações suficientes, retornar mensagem padrão
        titulo = pl_details.get('Título', '')
        if not titulo:
            return "Análise completa indisponível. Recomenda-se avaliar o texto completo do PL."
        
        # Verificar palavras-chave relacionadas a setores regulados
        titulo_upper = titulo.upper()
        palavras_chave = pl_details.get('Palavras-chave', '').upper()
        
        # Setores afetados
        affected_sectors = []
        
        for sector, keywords in cls.REGULATED_SECTORS.items():
            for keyword in keywords:
                if keyword in titulo_upper or keyword in palavras_chave:
                    affected_sectors.append(sector)
                    break
        
        # Remover duplicatas
        affected_sectors = list(set(affected_sectors))
        
        if affected_sectors:
            if len(affected_sectors) == 1:
                return f"Este PL pode afetar o setor de {affected_sectors[0]}. Recomenda-se análise detalhada do texto para avaliação completa de impacto."
            else:
                sectors_str = ", ".join(affected_sectors[:-1]) + " e " + affected_sectors[-1]
                return f"Este PL pode afetar os setores de {sectors_str}. Recomenda-se análise detalhada do texto para avaliação completa de impacto."
        else:
            return "Não foi possível identificar setores específicos impactados. Recomenda-se avaliar o texto completo do PL."