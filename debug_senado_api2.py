# debug_senado_api.py - Salve este arquivo na raiz do projeto

import sys
import os
import json
from datetime import datetime

# Adiciona o diretório raiz ao path para importações
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Importa a implementação atualizada da API do Senado
from src.intelligence.collectors.senado_api import SenadoAPI

def debug_pl(sigla, numero, ano):
    """Testa a extração de dados completos de um PL específico"""
    print(f"====== DEBUGGING PL {sigla} {numero}/{ano} ======")
    
    # Inicializa a API
    api = SenadoAPI()
    
    # Busca detalhes básicos
    print("\n1. Buscando detalhes básicos")
    pl_details = api.get_pl_by_id(sigla, numero, ano)
    if not pl_details:
        print("  ❌ Falha: PL não encontrado")
        return
        
    print(f"  ✅ PL encontrado: {pl_details.get('Título', '')[:100]}...")
    
    # Verifica o código da matéria
    codigo_materia = pl_details.get('CodigoMateria')
    if not codigo_materia:
        print("  ❌ Falha: Código da matéria não encontrado")
        return
        
    print(f"  ✅ Código da matéria: {codigo_materia}")
    
    # Busca relatores diretamente
    print("\n2. Buscando relatores")
    relatores = api.get_pl_relatores(codigo_materia)
    print(f"  Encontrados {len(relatores)} relatores")
    
    if relatores:
        for i, relator in enumerate(relatores):
            print(f"  Relator {i+1}: {relator.get('Nome', '')} ({relator.get('Partido', '')}/{relator.get('UF', '')})")
            print(f"    Comissão: {relator.get('Comissao', '')}")
            print(f"    Data designação: {relator.get('DataDesignacao', '')}")
    else:
        print("  ⚠️ Nenhum relator encontrado")
    
    # Verifica como o PLRiskAnalyzer processaria esse PL
    print("\n3. Simulando análise do PLRiskAnalyzer")
    try:
        from src.intelligence.analysis.pl_risk_analysis import PLRiskAnalyzer
        analyzer = PLRiskAnalyzer()
        
        # Salvar dados brutos para análise
        print("  Salvando dados brutos para análise")
        with open(f"debug_pl_{sigla}_{numero}_{ano}_raw.json", "w", encoding="utf-8") as f:
            json.dump(pl_details, f, indent=2, ensure_ascii=False)
            
        # Testar chamada do analisador
        print("  Executando analyze_pl_risk (pode demorar)...")
        analysis = analyzer.analyze_pl_risk(sigla, numero, ano, force_refresh=True)
        
        # Salvar resultado da análise
        with open(f"debug_pl_{sigla}_{numero}_{ano}_analysis.json", "w", encoding="utf-8") as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
            
        print(f"  ✅ Análise concluída e salva em debug_pl_{sigla}_{numero}_{ano}_analysis.json")
        
        # Verificar se os próximos passos incluem informações de relatores
        proximos_passos = analysis.get('proximos_passos', [])
        print(f"  Próximos passos gerados: {len(proximos_passos)}")
        
    except Exception as e:
        print(f"  ❌ Erro ao simular análise: {str(e)}")

# Execute o debug para o PL 3405/2023
if __name__ == "__main__":
    debug_pl("PL", "3405", "2023")