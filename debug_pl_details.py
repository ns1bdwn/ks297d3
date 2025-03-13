#!/usr/bin/env python3
"""
Script de debug avançado para análise de PLs
"""
import os
import sys
import logging
import json
from datetime import datetime

# Configurar logging detalhado
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("advanced_debug.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("advanced_debug")

# Garantir que o caminho do projeto está no Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def debug_pl_details_extraction():
    """
    Debug detalhado para extração de informações de PLs
    """
    logger.info("=== INÍCIO DO DEBUG AVANÇADO DE EXTRAÇÃO DE PLs ===")
    
    try:
        from src.intelligence.collectors.senado_api import SenadoAPI
        from src.intelligence.analysis.pl_risk_analysis import PLRiskAnalyzer
        
        # Instanciar SenadoAPI e PLRiskAnalyzer
        senado_api = SenadoAPI()
        risk_analyzer = PLRiskAnalyzer()
        
        # PLs de teste - expandir para mais casos
        pls_para_testar = [
            {"sigla": "PL", "numero": "2234", "ano": "2022"},  # PL original
            {"sigla": "PL", "numero": "3405", "ano": "2023"},
            {"sigla": "PL", "numero": "3563", "ano": "2024"}
        ]
        
        for pl in pls_para_testar:
            logger.info(f"\n--- Testando PL {pl['sigla']} {pl['numero']}/{pl['ano']} ---")
            
            # 1. Buscar detalhes pelo SenadoAPI
            logger.info("1. Buscando detalhes pelo SenadoAPI...")
            pl_details = senado_api.get_pl_by_id(pl['sigla'], pl['numero'], pl['ano'])
            
            if pl_details:
                logger.info("✓ Detalhes do PL obtidos com sucesso")
                logger.debug(f"Campos disponíveis: {list(pl_details.keys())}")
                
                # Verificar campos específicos importantes
                campos_importantes = [
                    'Título', 'Data', 'Autor', 'Status', 'Situacao', 
                    'Tramitacao', 'Palavras-chave'
                ]
                
                for campo in campos_importantes:
                    if campo in pl_details:
                        logger.info(f"✓ Campo '{campo}' presente")
                        if isinstance(pl_details[campo], (list, dict)):
                            logger.info(f"  - Tamanho/itens: {len(pl_details[campo])}")
                        else:
                            logger.info(f"  - Valor: {pl_details[campo]}")
            else:
                logger.error(f"✗ Não foi possível obter detalhes do PL {pl['sigla']} {pl['numero']}/{pl['ano']}")
            
            # 2. Análise de Risco
            logger.info("2. Realizando análise de risco...")
            try:
                analysis = risk_analyzer.analyze_pl_risk(
                    pl['sigla'], pl['numero'], pl['ano']
                )
                
                # Verificar campos da análise de risco
                campos_analise = [
                    'risco_aprovacao', 'tempo_estimado', 
                    'proximos_passos', 'analise_politica'
                ]
                
                for campo in campos_analise:
                    if campo in analysis:
                        logger.info(f"✓ Campo de análise '{campo}' presente")
                        if isinstance(analysis[campo], dict) and analysis[campo]:
                            logger.debug(f"  - Subcampos de {campo}: {list(analysis[campo].keys())}")
                        elif isinstance(analysis[campo], list):
                            logger.info(f"  - {campo} tem {len(analysis[campo])} itens")
            except Exception as e:
                logger.error(f"Erro na análise de risco: {str(e)}")
            
            # 3. Análise de próximos passos
            logger.info("3. Verificando método _predict_next_steps...")
            try:
                situacao = pl_details.get('Situacao', {})
                tramitacao = pl_details.get('Tramitacao', [])
                
                next_steps_method = risk_analyzer._predict_next_steps
                next_steps = next_steps_method(pl_details, situacao, tramitacao)
                
                logger.info(f"Próximos passos encontrados: {len(next_steps)}")
                for i, step in enumerate(next_steps, 1):
                    logger.info(f"Passo {i}:")
                    logger.info(f"  - Nome: {step.get('passo', 'N/A')}")
                    logger.info(f"  - Probabilidade: {step.get('probabilidade', 'N/A')}")
                    logger.info(f"  - Contexto: {step.get('contexto', 'N/A')}")
            except Exception as e:
                logger.error(f"Erro ao verificar próximos passos: {str(e)}")
        
    except Exception as e:
        logger.error(f"Erro geral no debug: {str(e)}", exc_info=True)
    
    logger.info("=== FIM DO DEBUG AVANÇADO DE EXTRAÇÃO DE PLs ===")

if __name__ == "__main__":
    debug_pl_details_extraction()