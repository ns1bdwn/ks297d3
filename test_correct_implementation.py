# test_correct_implementation.py
"""
Script para testar a implementação correta da busca de relatores dos PLs.
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
        logging.FileHandler("correct_implementation_test.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("test_correct_implementation")

# Diretório para salvar resultados
RESULTS_DIR = "correct_implementation_results"
os.makedirs(RESULTS_DIR, exist_ok=True)

class SimplifiedSenadoAPI:
    """
    Versão simplificada da API do Senado para testes diretos.
    """
    BASE_URL = "https://legis.senado.leg.br/dadosabertos"
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Dict:
        """
        Faz uma requisição à API do Senado.
        
        Args:
            endpoint: Endpoint da API
            params: Parâmetros da requisição
            
        Returns:
            Dados da resposta
        """
        if params is None:
            params = {}
        
        # Construir URL
        url = f"{self.BASE_URL}/{endpoint}"
        
        try:
            # Fazer requisição
            logger.info(f"Requisitando: {url}")
            response = requests.get(url, params=params)
            
            # Verificar resposta
            if response.status_code == 200:
                try:
                    # Verificar se é XML (o formato padrão da API do Senado)
                    if 'xml' in response.headers.get('Content-Type', '').lower():
                        # Salvar resposta raw para análise
                        filename = f"{RESULTS_DIR}/raw_{endpoint.replace('/', '_')}_{datetime.now().strftime('%H%M%S')}.xml"
                        with open(filename, 'w', encoding='utf-8') as f:
                            f.write(response.text)
                            
                        # Converter XML para dicionário
                        data = xmltodict.parse(response.content)
                        return data
                    else:
                        # Tentar como JSON
                        data = response.json()
                        return data
                except Exception as e:
                    logger.error(f"Erro ao processar resposta para {endpoint}: {str(e)}")
                    return {}
            else:
                logger.error(f"Erro {response.status_code} ao acessar {endpoint}: {response.text}")
                return {}
        except Exception as e:
            logger.error(f"Erro ao fazer requisição para {endpoint}: {str(e)}")
            return {}
    
    def get_pl_by_id(self, sigla: str, numero: str, ano: str) -> Dict:
        """
        Obtém detalhes básicos de um PL.
        
        Args:
            sigla: Sigla do PL (ex: PL, PEC)
            numero: Número do PL
            ano: Ano do PL
            
        Returns:
            Dicionário com detalhes do PL
        """
        endpoint = f"materia/{sigla}/{numero}/{ano}"
        data = self._make_request(endpoint)
        
        if not data:
            logger.warning(f"PL {sigla} {numero}/{ano} não encontrado")
            return {}
        
        try:
            materia = data.get('DetalheMateria', {}).get('Materia', {})
            id_materia = materia.get('IdentificacaoMateria', {})
            codigo_materia = id_materia.get('CodigoMateria')
            dados_basicos = materia.get('DadosBasicosMateria', {})
            
            return {
                "Titulo": dados_basicos.get('EmentaMateria', ''),
                "CodigoMateria": codigo_materia
            }
        except Exception as e:
            logger.error(f"Erro ao processar dados básicos: {str(e)}")
            return {}
    
    def get_pl_tramitacao(self, codigo_materia: str) -> List[Dict]:
        """
        Obtém a tramitação de um PL.
        
        Args:
            codigo_materia: Código da matéria
            
        Returns:
            Lista de eventos da tramitação
        """
        endpoint = f"materia/tramitacao/{codigo_materia}"
        data = self._make_request(endpoint)
        
        if not data:
            logger.warning(f"Tramitação não encontrada para matéria {codigo_materia}")
            return []
        
        try:
            tramitacao = data.get('TramitacaoMateria', {}).get('Tramitacoes', {}).get('Tramitacao', [])
            
            # Garantir que seja uma lista
            if not isinstance(tramitacao, list):
                tramitacao = [tramitacao]
            
            # Processar tramitação
            tramitacao_processed = []
            for evento in tramitacao:
                tramitacao_processed.append({
                    "Data": evento.get('DataTramitacao', ''),
                    "Local": evento.get('IdentificacaoLocal', ''),
                    "Situacao": evento.get('SituacaoTramitacao', {}).get('DescricaoSituacao', ''),
                    "Texto": evento.get('TextoTramitacao', '')
                })
            
            # Salvar para análise
            with open(f"{RESULTS_DIR}/tramitacao_{codigo_materia}.json", 'w', encoding='utf-8') as f:
                json.dump(tramitacao_processed, f, ensure_ascii=False, indent=2)
            
            return tramitacao_processed
        except Exception as e:
            logger.error(f"Erro ao processar tramitação: {str(e)}")
            return []
    
    def get_pl_comissoes(self, codigo_materia: str) -> List[Dict]:
        """
        Obtém as comissões de um PL.
        
        Args:
            codigo_materia: Código da matéria
            
        Returns:
            Lista de comissões
        """
        endpoint = f"materia/comissoes/{codigo_materia}"
        data = self._make_request(endpoint)
        
        if not data:
            logger.warning(f"Comissões não encontradas para matéria {codigo_materia}")
            return []
        
        try:
            # Salvar dados brutos para análise
            with open(f"{RESULTS_DIR}/comissoes_raw_{codigo_materia}.json", 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            comissoes = data.get('ComissoesSenado', {}).get('Materia', {}).get('Comissoes', {}).get('Comissao', [])
            
            # Garantir que seja uma lista
            if not isinstance(comissoes, list):
                comissoes = [comissoes]
            
            # Processar comissões
            comissoes_processed = []
            for comissao in comissoes:
                comissoes_processed.append({
                    "Sigla": comissao.get('SiglaComissao', ''),
                    "Nome": comissao.get('NomeComissao', ''),
                    "DataDesignacao": comissao.get('DataDesignacao', ''),
                    "Relator": comissao.get('Relator', {})
                })
            
            # Salvar para análise
            with open(f"{RESULTS_DIR}/comissoes_{codigo_materia}.json", 'w', encoding='utf-8') as f:
                json.dump(comissoes_processed, f, ensure_ascii=False, indent=2)
            
            return comissoes_processed
        except Exception as e:
            logger.error(f"Erro ao processar comissões: {str(e)}")
            return []
    
    def extract_relatores_from_tramitacao(self, tramitacao: List[Dict]) -> List[Dict]:
        """
        Extrai informações de relatores a partir da tramitação.
        
        Args:
            tramitacao: Lista de eventos de tramitação
            
        Returns:
            Lista de relatores encontrados
        """
        relatores = []
        seen_names = set()
        
        for evento in tramitacao:
            texto = evento.get('Texto', '').lower()
            
            # Buscar por menções a designação de relatores
            if 'relator' in texto and ('designad' in texto or 'indicad' in texto):
                # Tentar extrair o nome do relator
                import re
                
                # Padrões comuns
                patterns = [
                    r"[Dd]esignad[oa] [Rr]elator[,]?\s+[oa]?\s+[Ss]enador[a]?\s+([A-ZÀ-Ú][a-zà-ú]+(?: [A-ZÀ-Ú][a-zà-ú]+)*)",
                    r"[Dd]esignad[oa] [Rr]elator[,]?\s+[Ss]en[.]?\s+([A-ZÀ-Ú][a-zà-ú]+(?: [A-ZÀ-Ú][a-zà-ú]+)*)",
                    r"[Rr]elator[:]?\s+[Ss]enador[a]?\s+([A-ZÀ-Ú][a-zà-ú]+(?: [A-ZÀ-Ú][a-zà-ú]+)*)",
                    r"[Rr]elator[:]?\s+[Ss]en[.]?\s+([A-ZÀ-Ú][a-zà-ú]+(?: [A-ZÀ-Ú][a-zà-ú]+)*)",
                    r"senador[a]?\s+([A-ZÀ-Ú][a-zà-ú]+(?: [A-ZÀ-Ú][a-zà-ú]+)*)\s+(?:para|como)\s+relator"
                ]
                
                nome_relator = None
                for pattern in patterns:
                    match = re.search(pattern, texto)
                    if match:
                        nome_relator = match.group(1)
                        break
                
                if nome_relator and nome_relator not in seen_names:
                    seen_names.add(nome_relator)
                    
                    # Tentar extrair partido/UF
                    partido = ""
                    uf = ""
                    
                    partido_uf_pattern = r"\(([A-Z]+)[\/\-]([A-Z]{2})\)"
                    partido_uf_match = re.search(partido_uf_pattern, texto)
                    
                    if partido_uf_match:
                        partido = partido_uf_match.group(1)
                        uf = partido_uf_match.group(2)
                    
                    relatores.append({
                        "Nome": nome_relator,
                        "Partido": partido,
                        "UF": uf,
                        "Comissao": evento.get('Local', ''),
                        "DataDesignacao": evento.get('Data', ''),
                        "Texto": texto
                    })
        
        return relatores

def test_pl_relatores(sigla: str, numero: str, ano: str):
    """
    Testa a extração de relatores para um PL.
    
    Args:
        sigla: Sigla do PL (ex: PL, PEC)
        numero: Número do PL
        ano: Ano do PL
    """
    logger.info(f"===== TESTANDO EXTRAÇÃO DE RELATORES PARA {sigla} {numero}/{ano} =====")
    
    api = SimplifiedSenadoAPI()
    
    # Etapa 1: Obter dados básicos do PL
    basic_data = api.get_pl_by_id(sigla, numero, ano)
    
    if not basic_data:
        logger.error(f"Não foi possível obter dados básicos do PL {sigla} {numero}/{ano}")
        return
    
    logger.info(f"Dados básicos obtidos: {json.dumps(basic_data, ensure_ascii=False)}")
    
    codigo_materia = basic_data.get('CodigoMateria')
    if not codigo_materia:
        logger.error(f"Código da matéria não encontrado para PL {sigla} {numero}/{ano}")
        return
    
    # Etapa 2: Obter tramitação
    logger.info(f"Buscando tramitação para código {codigo_materia}")
    tramitacao = api.get_pl_tramitacao(codigo_materia)
    
    if not tramitacao:
        logger.warning(f"Nenhuma tramitação encontrada para o PL {sigla} {numero}/{ano}")
    else:
        logger.info(f"Encontrados {len(tramitacao)} eventos de tramitação")
    
    # Etapa 3: Obter comissões
    logger.info(f"Buscando comissões para código {codigo_materia}")
    comissoes = api.get_pl_comissoes(codigo_materia)
    
    if not comissoes:
        logger.warning(f"Nenhuma comissão encontrada para o PL {sigla} {numero}/{ano}")
    else:
        logger.info(f"Encontradas {len(comissoes)} comissões")
        
        # Verificar se há relatores nas comissões
        relatores_comissoes = []
        for comissao in comissoes:
            relator_info = comissao.get('Relator')
            if relator_info:
                logger.info(f"Encontrado relator na comissão {comissao.get('Sigla')}: {json.dumps(relator_info, ensure_ascii=False)}")
                relatores_comissoes.append(relator_info)
        
        if relatores_comissoes:
            logger.info(f"Encontrados {len(relatores_comissoes)} relatores nas comissões")
        else:
            logger.info("Nenhum relator encontrado nas comissões")
    
    # Etapa 4: Tentar extrair relatores da tramitação
    logger.info("Tentando extrair relatores da tramitação")
    relatores_tramitacao = api.extract_relatores_from_tramitacao(tramitacao)
    
    if relatores_tramitacao:
        logger.info(f"Extraídos {len(relatores_tramitacao)} relatores da tramitação:")
        for i, relator in enumerate(relatores_tramitacao):
            logger.info(f"Relator {i+1}: {relator['Nome']} ({relator['Partido']}/{relator['UF']})")
            logger.info(f"  Comissão: {relator['Comissao']}")
            logger.info(f"  Data: {relator['DataDesignacao']}")
            logger.info(f"  Texto: {relator['Texto'][:100]}...")
            
        # Salvar para análise
        with open(f"{RESULTS_DIR}/relatores_tramitacao_{sigla}_{numero}_{ano}.json", 'w', encoding='utf-8') as f:
            json.dump(relatores_tramitacao, f, ensure_ascii=False, indent=2)
    else:
        logger.warning("Nenhum relator extraído da tramitação")
    
    # Resumo final
    logger.info("\n===== RESUMO =====")
    relatores_totais = len(relatores_comissoes) + len(relatores_tramitacao)
    
    if relatores_totais > 0:
        logger.info(f"✅ Total de relatores encontrados: {relatores_totais}")
        logger.info(f"  - {len(relatores_comissoes)} das comissões")
        logger.info(f"  - {len(relatores_tramitacao)} da tramitação")
    else:
        logger.warning("❌ Nenhum relator encontrado para este PL")

if __name__ == "__main__":
    # Testar PL 2234/2022 (que sabemos que tem o Sen. Irajá como relator)
    test_pl_relatores("PL", "2234", "2022")
    
    # Testar PL 3405/2023 (que estava com problemas)
    test_pl_relatores("PL", "3405", "2023")