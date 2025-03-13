# debug_senado_api.py
"""
Script de diagnóstico para identificar problemas na obtenção de relatores de PLs via API do Senado.
Este script analisa em detalhes as respostas da API e salva os resultados para diagnóstico.
"""
import requests
import logging
import json
import os
import xmltodict
from datetime import datetime

# Configuração de logging detalhado
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("debug_senado_api.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("debug_senado_api")

# Configuração da API do Senado
BASE_URL = "https://legis.senado.leg.br/dadosabertos"

# Diretório para salvar arquivos de debug
DEBUG_DIR = "debug_output"
os.makedirs(DEBUG_DIR, exist_ok=True)

def save_to_file(filename, content, is_xml=False):
    """Salva conteúdo em um arquivo no diretório de debug."""
    file_path = os.path.join(DEBUG_DIR, filename)
    mode = 'w' if isinstance(content, str) else 'wb'
    encoding = 'utf-8' if isinstance(content, str) else None
    
    with open(file_path, mode, encoding=encoding) as f:
        f.write(content)
    
    logger.info(f"Conteúdo salvo em {file_path}")
    return file_path

def debug_pl_relatores(sigla, numero, ano):
    """
    Depura em detalhes o processo de obtenção de relatores para um PL.
    
    Args:
        sigla: Sigla do PL (ex: PL, PEC)
        numero: Número do PL
        ano: Ano do PL
    """
    pl_id = f"{sigla} {numero}/{ano}"
    logger.info(f"==== INICIANDO DIAGNÓSTICO DETALHADO PARA {pl_id} ====")
    
    # ETAPA 1: Obter detalhes básicos do PL para encontrar o código da matéria
    basic_endpoint = f"materia/{sigla}/{numero}/{ano}"
    basic_url = f"{BASE_URL}/{basic_endpoint}"
    
    logger.info(f"1. Buscando dados básicos do PL na URL: {basic_url}")
    
    try:
        response = requests.get(basic_url)
        
        logger.info(f"Status code: {response.status_code}")
        logger.info(f"Content-Type: {response.headers.get('Content-Type')}")
        
        # Salvar resposta XML bruta
        xml_file = save_to_file(f"basic_{sigla}_{numero}_{ano}.xml", response.text)
        
        if response.status_code == 200:
            # Analisar XML para JSON
            try:
                data = xmltodict.parse(response.content)
                # Salvar estrutura analisada para exame
                json_file = save_to_file(f"basic_{sigla}_{numero}_{ano}.json", 
                                         json.dumps(data, ensure_ascii=False, indent=2))
                
                # Extrair CodigoMateria
                materia = data.get('DetalheMateria', {}).get('Materia', {})
                codigo_materia = materia.get('IdentificacaoMateria', {}).get('CodigoMateria')
                
                if codigo_materia:
                    logger.info(f"CodigoMateria encontrado: {codigo_materia}")
                    
                    # ETAPA 2: Buscar relatores usando o código da matéria
                    relatoria_endpoint = f"materia/relatoria/{codigo_materia}"
                    relatoria_url = f"{BASE_URL}/{relatoria_endpoint}"
                    
                    logger.info(f"2. Buscando relatores na URL: {relatoria_url}")
                    
                    rel_response = requests.get(relatoria_url)
                    logger.info(f"Status code: {rel_response.status_code}")
                    logger.info(f"Content-Type: {rel_response.headers.get('Content-Type')}")
                    
                    # Salvar resposta XML bruta de relatoria
                    rel_xml_file = save_to_file(f"relatoria_{codigo_materia}.xml", rel_response.text)
                    
                    if rel_response.status_code == 200:
                        # Analisar XML de relatoria para JSON
                        try:
                            rel_data = xmltodict.parse(rel_response.content)
                            # Salvar estrutura analisada para exame
                            rel_json_file = save_to_file(f"relatoria_{codigo_materia}.json", 
                                                         json.dumps(rel_data, ensure_ascii=False, indent=2))
                            
                            # Examinar estrutura de relatoria detalhadamente
                            relatoria = rel_data.get('RelatoriaMateria', {})
                            logger.info(f"Chaves em RelatoriaMateria: {relatoria.keys() if relatoria else 'Nenhuma'}")
                            
                            materia_rel = relatoria.get('Materia', {})
                            logger.info(f"Chaves em Materia: {materia_rel.keys() if materia_rel else 'Nenhuma'}")
                            
                            # Verificar vários caminhos possíveis para relatores
                            if 'Relatoria' in materia_rel:
                                relatoria_data = materia_rel.get('Relatoria')
                                if isinstance(relatoria_data, list):
                                    logger.info(f"Encontrados {len(relatoria_data)} relatores na estrutura")
                                    for i, rel in enumerate(relatoria_data):
                                        parlamentar = rel.get('Parlamentar', {})
                                        comissao = rel.get('Comissao', {})
                                        logger.info(f"Relator {i+1}: {parlamentar.get('NomeParlamentar')} ({parlamentar.get('SiglaPartidoParlamentar', '')}/{parlamentar.get('UfParlamentar', '')}) na {comissao.get('SiglaComissao', '')}")
                                elif isinstance(relatoria_data, dict):
                                    logger.info("Encontrado 1 relator na estrutura")
                                    parlamentar = relatoria_data.get('Parlamentar', {})
                                    comissao = relatoria_data.get('Comissao', {})
                                    logger.info(f"Relator: {parlamentar.get('NomeParlamentar')} ({parlamentar.get('SiglaPartidoParlamentar', '')}/{parlamentar.get('UfParlamentar', '')}) na {comissao.get('SiglaComissao', '')}")
                                else:
                                    logger.warning(f"Estrutura inesperada em Relatoria: {type(relatoria_data)}")
                                    logger.debug(f"Conteúdo: {relatoria_data}")
                            else:
                                logger.warning("Nenhum elemento 'Relatoria' encontrado na estrutura")
                                
                                # Buscar diretamente valores que mencionem relatores
                                full_text = json.dumps(rel_data)
                                if "relator" in full_text.lower():
                                    logger.info("Termos relacionados a 'relator' encontrados no texto completo, mesmo sem elemento Relatoria")
                                    # Buscar onde aparece
                                    for line in full_text.lower().split("\n"):
                                        if "relator" in line:
                                            logger.info(f"Menção em: {line}")
                        except Exception as e:
                            logger.error(f"Erro ao analisar XML de relatoria: {e}")
                    else:
                        logger.error(f"Falha ao obter dados de relatoria: {rel_response.status_code}")
                        logger.debug(f"Texto de resposta: {rel_response.text[:500]}")
                    
                    # ETAPA 3: Método alternativo - buscar usando endpoint de movimentações
                    logger.info(f"3. Buscando informações nas movimentações")
                    movimentacoes_endpoint = f"materia/movimentacoes/{codigo_materia}"
                    movimentacoes_url = f"{BASE_URL}/{movimentacoes_endpoint}"
                    
                    mov_response = requests.get(movimentacoes_url)
                    mov_xml_file = save_to_file(f"movimentacoes_{codigo_materia}.xml", mov_response.text)
                    
                    if mov_response.status_code == 200:
                        try:
                            mov_data = xmltodict.parse(mov_response.content)
                            mov_json_file = save_to_file(f"movimentacoes_{codigo_materia}.json", 
                                                      json.dumps(mov_data, ensure_ascii=False, indent=2))
                            
                            # Verificar menções a relatores nas movimentações
                            full_text = json.dumps(mov_data).lower()
                            if "relator" in full_text:
                                logger.info("Termos relacionados a 'relator' encontrados nas movimentações")
                            else:
                                logger.info("Nenhuma menção a 'relator' nas movimentações")
                        except Exception as e:
                            logger.error(f"Erro ao analisar movimentações: {e}")
                else:
                    logger.error("CodigoMateria não encontrado nos dados básicos do PL")
            except Exception as e:
                logger.error(f"Erro ao analisar XML básico: {e}")
        else:
            logger.error(f"Falha ao obter dados básicos do PL: {response.status_code}")
            logger.debug(f"Texto de resposta: {response.text[:500]}")
    except Exception as e:
        logger.error(f"Erro na requisição: {e}")
    
    # ETAPA 4: Investigar estrutura completa para entender o que pode estar acontecendo
    logger.info("4. Análise estrutural da API do Senado")
    
    # Tentar buscar informações dos relatores usando o termo "relator" na busca
    logger.info("Buscando PLs com termo 'relator' para verificar estrutura esperada")
    search_url = f"{BASE_URL}/materia/pesquisa/lista"
    search_params = {
        "palavras": "relator designado",
        "limit": 1
    }
    
    try:
        search_response = requests.get(search_url, params=search_params)
        search_xml_file = save_to_file("relator_example_search.xml", search_response.text)
        
        if search_response.status_code == 200:
            try:
                search_data = xmltodict.parse(search_response.content)
                search_json_file = save_to_file("relator_example_search.json", 
                                           json.dumps(search_data, ensure_ascii=False, indent=2))
                logger.info("Exemplo de busca salvo para comparação estrutural")
            except Exception as e:
                logger.error(f"Erro ao analisar exemplo de busca: {e}")
    except Exception as e:
        logger.error(f"Erro na busca de exemplo: {e}")
    
    logger.info(f"==== DIAGNÓSTICO CONCLUÍDO PARA {pl_id} ====")
    logger.info(f"Todos os arquivos de diagnóstico foram salvos no diretório: {DEBUG_DIR}")
    
    # Resumo dos resultados
    logger.info("\n===== RESUMO DO DIAGNÓSTICO =====")
    logger.info(f"PL analisado: {pl_id}")
    if 'codigo_materia' in locals() and codigo_materia:
        logger.info(f"Código da matéria: {codigo_materia}")
        
        rel_encontrado = False
        if 'relatoria_data' in locals():
            if isinstance(relatoria_data, (list, dict)) and relatoria_data:
                rel_encontrado = True
                logger.info("Status: Relatores encontrados na estrutura")
            else:
                logger.info("Status: Estrutura de relatoria existe, mas sem relatores")
        else:
            logger.info("Status: Estrutura de relatoria não encontrada")
            
        logger.info("Conclusão provável: " + (
            "Este PL tem relatores designados" if rel_encontrado else 
            "Este PL não possui relatores designados no sistema do Senado"
        ))
    else:
        logger.info("Status: Não foi possível obter o código da matéria")
        logger.info("Conclusão: Erro na obtenção dos dados básicos do PL")

if __name__ == "__main__":
    # Executar diagnóstico para o PL 3405/2023
    debug_pl_relatores("PL", "3405", "2023")
    
    # Também vamos testar com um PL que sabemos que tem relatores
    # para fins de comparação da estrutura
    logger.info("\n\n==== TESTE DE COMPARAÇÃO ====")
    debug_pl_relatores("PL", "2234", "2022")