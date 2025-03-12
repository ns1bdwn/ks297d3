# debug_api.py - Script de diagnóstico da API do Senado
import sys
import logging
import json
from datetime import datetime

# Configurar logging detalhado
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('api_debug.log')
    ]
)

# Importar as classes necessárias
from src.intelligence.collectors.senado_api import SenadoAPI
from src.intelligence.collectors.senado_collector import SenadoCollector

def test_api_endpoints(sigla, numero, ano):
    """Testa diferentes endpoints da API para um PL específico"""
    logger = logging.getLogger("api_debug")
    results = {}

    # 1. Teste com a classe SenadoAPI
    try:
        logger.info(f"Testando SenadoAPI.get_pl_by_id({sigla}, {numero}, {ano})")
        api = SenadoAPI()
        api_result = api.get_pl_by_id(sigla, numero, ano)
        results["senado_api"] = {
            "success": bool(api_result),
            "keys_found": list(api_result.keys()) if api_result else [],
            "data": api_result
        }
        logger.info(f"Resultado da API: {json.dumps(results['senado_api']['keys_found'], indent=2)}")
    except Exception as e:
        logger.error(f"Erro ao testar SenadoAPI: {str(e)}", exc_info=True)
        results["senado_api"] = {"success": False, "error": str(e)}

    # 2. Teste com a classe SenadoCollector
    try:
        logger.info(f"Testando SenadoCollector.get_pl_by_id({sigla}, {numero}, {ano})")
        collector = SenadoCollector()
        collector_result = collector.get_pl_by_id(sigla, numero, ano)
        results["senado_collector"] = {
            "success": bool(collector_result),
            "keys_found": list(collector_result.keys()) if collector_result else [],
            "data": collector_result
        }
        logger.info(f"Resultado do Collector: {json.dumps(results['senado_collector']['keys_found'], indent=2)}")
    except Exception as e:
        logger.error(f"Erro ao testar SenadoCollector: {str(e)}", exc_info=True)
        results["senado_collector"] = {"success": False, "error": str(e)}

    # 3. Verificar endpoints diretos da API do Senado (Bypass das classes)
    try:
        import requests
        logger.info("Testando endpoint direto da API do Senado")
        
        # Endpoint para matéria legislativa
        endpoint = f"https://legis.senado.leg.br/dadosabertos/materia/{sigla}/{numero}/{ano}"
        logger.info(f"URL: {endpoint}")
        
        response = requests.get(endpoint)
        logger.info(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '')
            logger.info(f"Content-Type: {content_type}")
            
            if 'xml' in content_type.lower():
                logger.info("API retornou XML (esperado)")
                import xmltodict
                data = xmltodict.parse(response.content)
                results["api_direct"] = {
                    "success": True,
                    "format": "XML",
                    "keys_found": list(data.keys()) if data else []
                }
            elif 'json' in content_type.lower():
                logger.info("API retornou JSON")
                data = response.json()
                results["api_direct"] = {
                    "success": True,
                    "format": "JSON",
                    "keys_found": list(data.keys()) if data else []
                }
            else:
                logger.warning(f"API retornou formato inesperado: {content_type}")
                results["api_direct"] = {
                    "success": False,
                    "error": f"Formato inesperado: {content_type}"
                }
        else:
            logger.error(f"API retornou código de erro: {response.status_code}")
            results["api_direct"] = {
                "success": False,
                "error": f"Status code: {response.status_code}"
            }
    except Exception as e:
        logger.error(f"Erro ao acessar a API diretamente: {str(e)}", exc_info=True)
        results["api_direct"] = {"success": False, "error": str(e)}

    # Salvar resultados
    with open(f"api_debug_{sigla}_{numero}_{ano}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    return results

if __name__ == "__main__":
    if len(sys.argv) > 3:
        sigla = sys.argv[1]
        numero = sys.argv[2]
        ano = sys.argv[3]
    else:
        sigla = "PL"
        numero = "2234"
        ano = "2022"

    print(f"Testando API para {sigla} {numero}/{ano}...")
    results = test_api_endpoints(sigla, numero, ano)
    
    # Mostrar um resumo dos resultados
    print("\n=== RESUMO DOS RESULTADOS ===")
    for source, result in results.items():
        success = result.get("success", False)
        status = "✅ SUCESSO" if success else "❌ FALHA"
        print(f"{source}: {status}")
        if success:
            if source in ['senado_api', 'senado_collector']:
                if 'keys_found' in result:
                    print(f"  Campos encontrados: {', '.join(result['keys_found'])}")
            else:
                format_type = result.get('format', 'Desconhecido')
                print(f"  Formato: {format_type}")
        else:
            print(f"  Erro: {result.get('error', 'Desconhecido')}")
    
    print("\nVerifique o arquivo api_debug.log e o arquivo JSON gerado para detalhes completos.")