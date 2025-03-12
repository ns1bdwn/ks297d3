#!/usr/bin/env python3
"""
Script para depuração da análise de risco de PLs.
Execute este script diretamente para identificar onde está o problema.
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
        logging.FileHandler("debug_risk_analyzer.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("debug")

# Garantir que o caminho do projeto está no Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def debug_analisador():
    """Função principal de depuração"""
    logger.info("=== INÍCIO DA DEPURAÇÃO DO ANALISADOR DE RISCO ===")
    
    try:
        # 1. Verificar importação do SenadoAPI
        logger.info("1. Verificando importação do SenadoAPI...")
        from src.intelligence.collectors.senado_api import SenadoAPI
        logger.info("✓ Importação do SenadoAPI bem-sucedida")
        
        # 2. Verificar importação do PLRiskAnalyzer
        logger.info("2. Verificando importação do PLRiskAnalyzer...")
        from src.intelligence.analysis.pl_risk_analysis import PLRiskAnalyzer
        logger.info("✓ Importação do PLRiskAnalyzer bem-sucedida")
        
        # 3. Instanciar SenadoAPI
        logger.info("3. Instanciando SenadoAPI...")
        senado_api = SenadoAPI()
        logger.info("✓ SenadoAPI instanciado com sucesso")
        
        # 4. Testar método get_pl_by_id do SenadoAPI
        logger.info("4. Testando método get_pl_by_id do SenadoAPI...")
        pl_details = senado_api.get_pl_by_id("PL", "2234", "2022")
        logger.info(f"Campos presentes no PL: {list(pl_details.keys())}")
        logger.debug(f"Conteúdo do PL: {json.dumps(pl_details, ensure_ascii=False, indent=2)}")
        
        # 5. Testar método get_additional_pl_details do SenadoAPI
        logger.info("5. Testando método get_additional_pl_details do SenadoAPI...")
        try:
            additional_details = senado_api.get_additional_pl_details("PL", "2234", "2022")
            logger.info(f"Método get_additional_pl_details encontrado")
            logger.info(f"Campos adicionais: {list(additional_details.keys())}")
            logger.debug(f"Conteúdo adicional: {json.dumps(additional_details, ensure_ascii=False, indent=2)}")
        except AttributeError:
            logger.error("Método get_additional_pl_details NÃO encontrado - verifique se a implementação foi salva")
        
        # 6. Instanciar PLRiskAnalyzer
        logger.info("6. Instanciando PLRiskAnalyzer...")
        risk_analyzer = PLRiskAnalyzer()
        logger.info("✓ PLRiskAnalyzer instanciado com sucesso")
        
        # 7. Verificar se o método analyze_pl_risk existe
        logger.info("7. Verificando se o método analyze_pl_risk existe...")
        if hasattr(risk_analyzer, 'analyze_pl_risk'):
            logger.info("✓ Método analyze_pl_risk encontrado")
        else:
            logger.error("Método analyze_pl_risk NÃO encontrado")
        
        # 8. Testar análise de PL
        logger.info("8. Testando análise do PL 2234/2022...")
        try:
            analysis = risk_analyzer.analyze_pl_risk("PL", "2234", "2022")
            logger.info(f"Campos presentes na análise: {list(analysis.keys())}")
            
            # Verificar campos específicos importantes
            campos_importantes = [
                'risco_aprovacao', 'tempo_estimado', 'proximos_passos', 
                'analise_politica', 'titulo', 'autor'
            ]
            
            for campo in campos_importantes:
                if campo in analysis:
                    logger.info(f"✓ Campo '{campo}' presente na análise")
                    if isinstance(analysis[campo], dict) and analysis[campo]:
                        logger.info(f"  - Subcampos: {list(analysis[campo].keys())}")
                    elif isinstance(analysis[campo], list) and analysis[campo]:
                        logger.info(f"  - Lista com {len(analysis[campo])} itens")
                    else:
                        logger.info(f"  - Valor: {analysis[campo]}")
                else:
                    logger.error(f"✗ Campo '{campo}' NÃO presente na análise")
            
            # Verificar especificamente o campo de análise política
            if 'analise_politica' in analysis:
                ap = analysis['analise_politica']
                logger.info(f"Análise política: tendência={ap.get('tendencia', 'N/A')}")
                logger.info(f"Contexto político disponível: {'Sim' if ap.get('contexto_politico') else 'Não'}")
                logger.info(f"Impacto setorial disponível: {'Sim' if ap.get('impacto_setorial') else 'Não'}")
            
            # Salvar análise completa para inspeção
            with open("debug_analysis_result.json", "w", encoding="utf-8") as f:
                json.dump(analysis, f, ensure_ascii=False, indent=2)
            logger.info("Análise completa salva em 'debug_analysis_result.json'")
            
        except Exception as e:
            logger.error(f"Erro ao analisar PL: {str(e)}", exc_info=True)
    
    except Exception as e:
        logger.error(f"Erro durante a depuração: {str(e)}", exc_info=True)
    
    logger.info("=== FIM DA DEPURAÇÃO DO ANALISADOR DE RISCO ===")

if __name__ == "__main__":
    debug_analisador()
