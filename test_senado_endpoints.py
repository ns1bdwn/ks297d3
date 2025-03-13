# test_senado_endpoints.py
"""
Script para testar os endpoints corretos da API do Senado e extrair informações sobre relatores.
"""
import requests
import logging
import json
import xmltodict
import os
import re
from datetime import datetime
from typing import Dict, List, Any

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("senado_endpoints_test.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("test_senado_endpoints")

# Diretório para salvar resultados
RESULTS_DIR = "senado_test_results"
os.makedirs(RESULTS_DIR, exist_ok=True)

class SenadoEndpointTester:
    """
    Classe para testar vários endpoints da API do Senado.
    """
    BASE_URL = "https://legis.senado.leg.br/dadosabertos"
    
    def make_request(self, endpoint: str, params: Dict = None) -> Dict:
        """
        Faz uma requisição à API do Senado.
        
        Args:
            endpoint: Endpoint da API
            params: Parâmetros da requisição
            
        Returns:
            Dados da resposta e status de sucesso
        """
        if params is None:
            params = {}
        
        # Construir URL
        url = f"{self.BASE_URL}/{endpoint}"
        
        try:
            # Fazer requisição
            logger.info(f"Requisitando: {url}")
            response = requests.get(url, params=params)
            
            # Salvar status e cabeçalhos para análise
            logger.info(f"Status Code: {response.status_code}")
            logger.info(f"Content-Type: {response.headers.get('Content-Type')}")
            
            # Verificar resposta
            if response.status_code == 200:
                # Salvar resposta raw para análise
                safe_endpoint = endpoint.replace('/', '_')
                filename = f"{RESULTS_DIR}/raw_{safe_endpoint}_{datetime.now().strftime('%H%M%S')}.txt"
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                
                try:
                    # Verificar se é XML (o formato padrão da API do Senado)
                    if 'xml' in response.headers.get('Content-Type', '').lower():
                        # Converter XML para dicionário
                        data = xmltodict.parse(response.content)
                        
                        # Salvar versão JSON para análise facilitada
                        json_filename = f"{RESULTS_DIR}/json_{safe_endpoint}_{datetime.now().strftime('%H%M%S')}.json"
                        with open(json_filename, 'w', encoding='utf-8') as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
                            
                        return {"data": data, "success": True}
                    else:
                        # Tentar como JSON
                        data = response.json()
                        return {"data": data, "success": True}
                except Exception as e:
                    logger.error(f"Erro ao processar resposta para {endpoint}: {str(e)}")
                    return {"data": {}, "success": False, "error": str(e)}
            else:
                logger.error(f"Erro {response.status_code} ao acessar {endpoint}")
                logger.info(f"Resposta: {response.text[:500]}")
                return {"data": {}, "success": False, "error": f"Status code: {response.status_code}"}
        except Exception as e:
            logger.error(f"Erro ao fazer requisição para {endpoint}: {str(e)}")
            return {"data": {}, "success": False, "error": str(e)}
    
    def test_pl_endpoints(self, sigla: str, numero: str, ano: str):
        """
        Testa vários endpoints para um PL específico.
        
        Args:
            sigla: Sigla do PL
            numero: Número do PL
            ano: Ano do PL
        """
        pl_id = f"{sigla} {numero}/{ano}"
        logger.info(f"===== TESTANDO ENDPOINTS PARA {pl_id} =====")
        
        # Lista de endpoints potenciais a testar
        identificacao_endpoints = [
            f"materia/{sigla}/{numero}/{ano}",
            f"materia/pesquisa/lista?sigla={sigla}&numero={numero}&ano={ano}"
        ]
        
        # Testar endpoints de identificação para obter o código da matéria
        codigo_materia = None
        
        for endpoint in identificacao_endpoints:
            logger.info(f"Testando endpoint de identificação: {endpoint}")
            result = self.make_request(endpoint)
            
            if result["success"]:
                # Tentar extrair código da matéria
                try:
                    if "DetalheMateria" in result["data"]:
                        codigo_materia = result["data"]["DetalheMateria"]["Materia"]["IdentificacaoMateria"]["CodigoMateria"]
                        logger.info(f"Código da matéria encontrado: {codigo_materia}")
                        break
                    elif "PesquisaBasicaMateria" in result["data"]:
                        materias = result["data"]["PesquisaBasicaMateria"]["Materias"]["Materia"]
                        if isinstance(materias, list) and len(materias) > 0:
                            codigo_materia = materias[0]["IdentificacaoMateria"]["CodigoMateria"]
                        elif isinstance(materias, dict):
                            codigo_materia = materias["IdentificacaoMateria"]["CodigoMateria"]
                        
                        if codigo_materia:
                            logger.info(f"Código da matéria encontrado: {codigo_materia}")
                            break
                except Exception as e:
                    logger.error(f"Erro ao extrair código da matéria: {str(e)}")
        
        if not codigo_materia:
            logger.error(f"Não foi possível obter o código da matéria para {pl_id}")
            return
        
        # Lista de endpoints para testar com o código da matéria
        code_based_endpoints = [
            # Endpoints oficiais
            f"materia/{codigo_materia}",               # Detalhes da matéria
            f"materia/textos/{codigo_materia}",        # Textos da matéria
            f"materia/autoria/{codigo_materia}",       # Autoria
            f"materia/situacaoatual/{codigo_materia}", # Situação atual
            
            # Testes de possíveis endpoints para relatores/tramitação
            f"materia/relator/{codigo_materia}",       # Possível endpoint para relator
            f"materia/relatores/{codigo_materia}",     # Possível variação 
            f"materia/relatoria/{codigo_materia}",     # Endpoint que estávamos usando
            f"materia/comissoes/{codigo_materia}",     # Comissões
            f"materia/movimentacoes/{codigo_materia}", # Movimentações/tramitação
            f"materia/tramitacoes/{codigo_materia}",   # Possível variação
            f"materia/tramitacao/{codigo_materia}"     # Endpoint que tivemos problema
        ]
        
        # Resultados dos endpoints funcionais
        working_endpoints = {}
        
        for endpoint in code_based_endpoints:
            logger.info(f"Testando endpoint: {endpoint}")
            result = self.make_request(endpoint)
            
            if result["success"]:
                logger.info(f"✅ Endpoint {endpoint} funcionou")
                working_endpoints[endpoint] = result["data"]
                
                # Procurar referências a relatores no conteúdo
                content_str = json.dumps(result["data"], ensure_ascii=False).lower()
                if "relator" in content_str:
                    logger.info(f"🔍 Encontradas referências a 'relator' no endpoint {endpoint}")
                    
                    # Salvar para análise detalhada
                    relator_filename = f"{RESULTS_DIR}/relator_refs_{endpoint.replace('/', '_')}.json"
                    with open(relator_filename, 'w', encoding='utf-8') as f:
                        json.dump(result["data"], f, ensure_ascii=False, indent=2)
            else:
                logger.warning(f"❌ Endpoint {endpoint} falhou: {result.get('error', 'Unknown error')}")
        
        # Analisar especificamente os dados de movimentações para relator
        if f"materia/movimentacoes/{codigo_materia}" in working_endpoints:
            logger.info("\nAnalisando dados de movimentações para referências a relatores:")
            movimentacoes_data = working_endpoints[f"materia/movimentacoes/{codigo_materia}"]
            
            try:
                movimentacoes = movimentacoes_data.get("MovimentacaoMateria", {}).get("Movimentacoes", {}).get("Movimentacao", [])
                
                # Garantir que seja uma lista
                if not isinstance(movimentacoes, list):
                    movimentacoes = [movimentacoes]
                
                # Procurar por movimentações relacionadas a relatores
                relator_refs = []
                for idx, mov in enumerate(movimentacoes):
                    texto = mov.get("TextoMovimentacao", "").lower()
                    if "relator" in texto:
                        relator_refs.append({
                            "index": idx,
                            "data": mov.get("DataMovimentacao", ""),
                            "local": mov.get("Local", {}).get("NomeLocal", ""),
                            "situacao": mov.get("Situacao", {}).get("DescricaoSituacao", ""),
                            "texto": mov.get("TextoMovimentacao", "")
                        })
                
                if relator_refs:
                    logger.info(f"🔍 Encontradas {len(relator_refs)} movimentações relacionadas a relatores")
                    
                    # Salvar para análise
                    with open(f"{RESULTS_DIR}/relator_movimentacoes_{codigo_materia}.json", 'w', encoding='utf-8') as f:
                        json.dump(relator_refs, f, ensure_ascii=False, indent=2)
                        
                    # Exibir as referências encontradas
                    for ref in relator_refs:
                        logger.info(f"  📌 [{ref['data']}] {ref['local']} - {ref['situacao']}")
                        logger.info(f"      {ref['texto']}")
                else:
                    logger.warning(f"Nenhuma referência a relatores encontrada nas movimentações")
            except Exception as e:
                logger.error(f"Erro ao analisar movimentações: {str(e)}")
        
        # Resumo dos endpoints funcionais
        logger.info("\n===== RESUMO DOS ENDPOINTS =====")
        logger.info(f"Total de endpoints testados: {len(code_based_endpoints)}")
        logger.info(f"Endpoints funcionais: {len(working_endpoints)}")
        
        for endpoint in working_endpoints.keys():
            logger.info(f"  ✅ {endpoint}")
        
        # Conclusão
        logger.info("\n===== CONCLUSÃO =====")
        if f"materia/movimentacoes/{codigo_materia}" in working_endpoints:
            logger.info("✅ O endpoint materia/movimentacoes/{codigo} está funcionando e contém referências a relatores")
            logger.info("   Este deve ser o endpoint correto para extrair informações sobre relatores")
        else:
            logger.warning("❌ Não foi possível encontrar um endpoint confiável para obter informações de relatores")
        
        logger.info(f"===== FIM DO TESTE PARA {pl_id} =====\n")

if __name__ == "__main__":
    tester = SenadoEndpointTester()
    
    # Testar o PL 2234/2022 (sabemos que tem o Sen. Irajá como relator)
    tester.test_pl_endpoints("PL", "2234", "2022")
    
    # Testar o PL 3405/2023 (que estava com problemas)
    tester.test_pl_endpoints("PL", "3405", "2023")