# src/intelligence/collectors/senado_collector.py
"""
Coletor de dados de PLs do Senado.
Versão MVP: Carrega dados de um CSV local em vez de acessar a API do Senado.
"""
import os
import csv
import json
import logging
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("senado_collector")

class SenadoCollector:
    """
    Classe para coletar dados de PLs do Senado.
    Versão MVP: Utiliza dados pré-carregados de um CSV local.
    Versão futura: Integrará com a API de Dados Abertos do Senado.
    """
    
    def __init__(self, csv_path: str = None):
        """
        Inicializa o coletor de dados do Senado.
        
        Args:
            csv_path: Caminho para o CSV de PLs. Se None, usa o padrão.
        """
        # Diretório base do projeto
        self.base_dir = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "..", ".."
        ))
        
        # Definir caminho do CSV
        if csv_path is None:
            self.csv_path = os.path.join(
                self.base_dir, "data", "regulations", "pls_igaming.csv"
            )
        else:
            self.csv_path = csv_path
        
        # Garantir que o diretório existe
        os.makedirs(os.path.dirname(self.csv_path), exist_ok=True)
        
        # Carregar dados se o CSV existir
        self._pls_data = self._load_pls_data()
        
        # Se não houver dados, criar CSV inicial com dados de exemplo
        if not self._pls_data:
            self._create_initial_csv()
            self._pls_data = self._load_pls_data()
    
    def _load_pls_data(self) -> Dict[str, Dict[str, Any]]:
        """
        Carrega dados dos PLs a partir do CSV.
        
        Returns:
            Dicionário com dados dos PLs indexados por ID (sigla_numero_ano)
        """
        if not os.path.exists(self.csv_path):
            logger.warning(f"Arquivo CSV não encontrado: {self.csv_path}")
            return {}
        
        try:
            df = pd.read_csv(self.csv_path, encoding='utf-8')
            
            # Converter DataFrame para dicionário
            pls_dict = {}
            for _, row in df.iterrows():
                pl_id = f"{row['Sigla']}_{row['Numero']}_{row['Ano']}"
                pls_dict[pl_id] = row.to_dict()
            
            logger.info(f"Carregados {len(pls_dict)} PLs do CSV.")
            return pls_dict
        except Exception as e:
            logger.error(f"Erro ao carregar dados do CSV: {str(e)}")
            return {}
    
    def _create_initial_csv(self):
        """
        Cria um CSV inicial com dados de exemplo de PLs relevantes para iGaming.
        """
        logger.info("Criando CSV inicial com PLs de exemplo para iGaming...")
        
        # Dados de exemplo para PLs de iGaming
        data = [
            {
                "Sigla": "PL", 
                "Numero": "2234", 
                "Ano": "2022",
                "Título": "Estabelece o marco regulatório dos jogos e apostas no Brasil, incluindo jogos online, cassinos, bingos, apostas esportivas e outras modalidades, criando regras para licenciamento, operação, tributação e prevenção da lavagem de dinheiro.",
                "Autor": "Sen. Irajá Silvestre",
                "Data": "2022-06-30",
                "Status": "Em tramitação - Comissão de Constituição e Justiça",
                "URL": "https://www25.senado.leg.br/web/atividade/materias/-/materia/151508",
                "Palavras-chave": "jogos de azar, apostas, cassinos, jogos online, tributação, licenças"
            },
            {
                "Sigla": "PL", 
                "Numero": "3405", 
                "Ano": "2023",
                "Título": "Regulamenta as apostas de quota fixa, define regras para as empresas de apostas online (betting), estabelece exigências para operação no Brasil e cria sistema de proteção contra apostas compulsivas.",
                "Autor": "Sen. Davi Alcolumbre",
                "Data": "2023-04-15",
                "Status": "Em tramitação - Comissão de Assuntos Econômicos",
                "URL": "https://www25.senado.leg.br/web/atividade/materias/-/materia/154707",
                "Palavras-chave": "apostas online, betting, quota fixa, esportes, regulação, jogo responsável"
            },
            {
                "Sigla": "PL", 
                "Numero": "3563", 
                "Ano": "2024",
                "Título": "Dispõe sobre mecanismos de Prevenção à Lavagem de Dinheiro e ao Financiamento do Terrorismo (PLDFT) específicos para o setor de apostas online, estabelecendo obrigações para operadores e introduzindo KYC avançado.",
                "Autor": "Sen. Angelo Coronel",
                "Data": "2024-01-22",
                "Status": "Em tramitação - Comissão de Transparência e Fiscalização",
                "URL": "https://www25.senado.leg.br/web/atividade/materias/-/materia/156341",
                "Palavras-chave": "PLDFT, lavagem de dinheiro, apostas, KYC, verificação, compliance"
            },
            {
                "Sigla": "PL", 
                "Numero": "3718", 
                "Ano": "2024",
                "Título": "Cria o Sistema Nacional de Jogo Responsável (SNJR), estabelecendo medidas para prevenção e tratamento da dependência em jogos de azar e apostas, com foco nos mecanismos de autoexclusão e limites obrigatórios.",
                "Autor": "Sen. Soraya Thronicke",
                "Data": "2024-02-14",
                "Status": "Em tramitação - Comissão de Assuntos Sociais",
                "URL": "https://www25.senado.leg.br/web/atividade/materias/-/materia/157023",
                "Palavras-chave": "jogo responsável, dependência, vício, autoexclusão, limites, proteção ao consumidor"
            },
            {
                "Sigla": "PL", 
                "Numero": "4392", 
                "Ano": "2024",
                "Título": "Estabelece regras para publicidade e marketing de casas de apostas, proibindo propaganda voltada a menores de idade e restringindo horários de veiculação, além de exigir avisos sobre jogo responsável.",
                "Autor": "Sen. Eduardo Girão",
                "Data": "2024-03-01",
                "Status": "Em tramitação - Comissão de Comunicação e Direito Digital",
                "URL": "https://www25.senado.leg.br/web/atividade/materias/-/materia/157903",
                "Palavras-chave": "publicidade, propaganda, apostas, proteção de menores, jogo responsável"
            },
            {
                "Sigla": "PL", 
                "Numero": "4391", 
                "Ano": "2024",
                "Título": "Institui normas para segurança cibernética e proteção de dados para empresas de apostas online, exigindo certificações de segurança, testes de penetração regulares e auditorias independentes.",
                "Autor": "Sen. Humberto Costa",
                "Data": "2024-03-01",
                "Status": "Em tramitação - Comissão de Ciência e Tecnologia",
                "URL": "https://www25.senado.leg.br/web/atividade/materias/-/materia/157902",
                "Palavras-chave": "segurança cibernética, dados pessoais, LGPD, proteção, apostas online, certificação"
            },
            {
                "Sigla": "PL", 
                "Numero": "4390", 
                "Ano": "2024",
                "Título": "Regulamenta a integridade das apostas esportivas, criando o Sistema Brasileiro de Prevenção à Manipulação de Resultados, com monitoramento obrigatório de padrões suspeitos e regras para comunicação às autoridades.",
                "Autor": "Sen. Jorge Kajuru",
                "Data": "2024-03-01",
                "Status": "Em tramitação - Comissão de Esporte",
                "URL": "https://www25.senado.leg.br/web/atividade/materias/-/materia/157901",
                "Palavras-chave": "integridade esportiva, manipulação, fraudes, monitoramento, apostas esportivas"
            },
            {
                "Sigla": "PL", 
                "Numero": "4031", 
                "Ano": "2024",
                "Título": "Dispõe sobre a tributação das operações com apostas de quota fixa, alterando alíquotas, base de cálculo e estabelecendo regras para remessas internacionais e distribuição dos recursos arrecadados.",
                "Autor": "Sen. Izalci Lucas",
                "Data": "2024-02-08",
                "Status": "Em tramitação - Comissão de Assuntos Econômicos",
                "URL": "https://www25.senado.leg.br/web/atividade/materias/-/materia/156932",
                "Palavras-chave": "tributação, impostos, apostas, quota fixa, remessas, outorga"
            },
            {
                "Sigla": "PL", 
                "Numero": "3795", 
                "Ano": "2024",
                "Título": "Estabelece critérios técnicos para sistemas de Random Number Generator (RNG) utilizados em jogos de azar virtuais, exigindo certificação, testes periódicos e auditorias independentes.",
                "Autor": "Sen. Rodrigo Cunha",
                "Data": "2024-02-27",
                "Status": "Em tramitação - Comissão de Ciência e Tecnologia",
                "URL": "https://www25.senado.leg.br/web/atividade/materias/-/materia/157423",
                "Palavras-chave": "RNG, geradores, números aleatórios, jogos virtuais, certificação, auditoria"
            },
            {
                "Sigla": "PL", 
                "Numero": "3719", 
                "Ano": "2024",
                "Título": "Regulamenta as operações de pagamento em sites de apostas, estabelecendo limites de transação, regras para meios de pagamento aceitos e procedimentos KYC para prevenção à lavagem de dinheiro.",
                "Autor": "Sen. Alessandro Vieira",
                "Data": "2024-02-14",
                "Status": "Em tramitação - Comissão de Assuntos Econômicos",
                "URL": "https://www25.senado.leg.br/web/atividade/materias/-/materia/157024",
                "Palavras-chave": "pagamentos, transações, limites, meios de pagamento, apostas, KYC"
            }
        ]
        
        # Criar DataFrame e salvar como CSV
        df = pd.DataFrame(data)
        df.to_csv(self.csv_path, index=False, encoding='utf-8')
        
        logger.info(f"CSV inicial criado com {len(data)} PLs em {self.csv_path}")
    
    def get_pl_by_id(self, sigla: str, numero: str, ano: str) -> Dict[str, Any]:
        """
        Busca detalhes de um PL específico.
        Versão MVP: Busca no CSV local.
        Versão futura: Integrará com a API do Senado.
        
        Args:
            sigla: Sigla do PL (ex: PL, PEC)
            numero: Número do PL
            ano: Ano do PL
            
        Returns:
            Dicionário com detalhes do PL ou vazio se não encontrado
        """
        logger.info(f"Buscando PL {sigla} {numero}/{ano}")
        
        # Construir ID do PL
        pl_id = f"{sigla}_{numero}_{ano}"
        
        # Buscar nos dados carregados
        if pl_id in self._pls_data:
            # Converter para o formato esperado
            raw_data = self._pls_data[pl_id]
            return {
                "Título": raw_data.get("Título", ""),
                "Data": raw_data.get("Data", ""),
                "Autor": raw_data.get("Autor", ""),
                "Status": raw_data.get("Status", ""),
                "URL": raw_data.get("URL", ""),
                "Palavras-chave": raw_data.get("Palavras-chave", "")
            }
        
        logger.warning(f"PL {sigla} {numero}/{ano} não encontrado")
        return {}
    
    def add_pl_to_csv(self, sigla: str, numero: str, ano: str, details: Dict[str, Any]) -> bool:
        """
        Adiciona um novo PL ao CSV de dados.
        
        Args:
            sigla: Sigla do PL (ex: PL, PEC)
            numero: Número do PL
            ano: Ano do PL
            details: Dicionário com detalhes do PL
            
        Returns:
            True se adicionou com sucesso, False caso contrário
        """
        try:
            # Verificar se o PL já existe no CSV
            pl_id = f"{sigla}_{numero}_{ano}"
            if pl_id in self._pls_data:
                logger.warning(f"PL {sigla} {numero}/{ano} já existe no CSV.")
                return False
            
            # Carregar DataFrame atual
            if os.path.exists(self.csv_path):
                df = pd.read_csv(self.csv_path, encoding='utf-8')
            else:
                # Se o CSV não existir, criar um novo DataFrame
                df = pd.DataFrame(columns=[
                    "Sigla", "Numero", "Ano", "Título", "Autor", 
                    "Data", "Status", "URL", "Palavras-chave"
                ])
            
            # Preparar nova linha
            new_row = {
                "Sigla": sigla,
                "Numero": numero,
                "Ano": ano,
                "Título": details.get("Título", f"[Personalizado] {sigla} {numero}/{ano}"),
                "Autor": details.get("Autor", "Usuário"),
                "Data": details.get("Data", datetime.now().strftime("%Y-%m-%d")),
                "Status": details.get("Status", "Personalizado"),
                "URL": details.get("URL", ""),
                "Palavras-chave": details.get("Palavras-chave", "")
            }
            
            # Adicionar ao DataFrame e salvar
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            df.to_csv(self.csv_path, index=False, encoding='utf-8')
            
            # Atualizar dados em memória
            self._pls_data = self._load_pls_data()
            
            logger.info(f"PL {sigla} {numero}/{ano} adicionado ao CSV com sucesso.")
            return True
        except Exception as e:
            logger.error(f"Erro ao adicionar PL ao CSV: {str(e)}")
            return False
    
    def search_pls(self, keywords: List[str] = None, date_from: str = None, 
                  date_to: str = None, author: str = None) -> List[Dict[str, Any]]:
        """
        Busca PLs que correspondem aos critérios.
        Versão MVP: Busca no CSV local.
        Versão futura: Integrará com a API do Senado.
        
        Args:
            keywords: Lista de palavras-chave para buscar
            date_from: Data inicial no formato YYYY-MM-DD
            date_to: Data final no formato YYYY-MM-DD
            author: Nome do autor para filtrar
            
        Returns:
            Lista de PLs que correspondem aos critérios
        """
        logger.info("Buscando PLs com filtros")
        
        # Carregar todos os PLs
        results = []
        
        for pl_id, pl_data in self._pls_data.items():
            # Aplicar filtros
            should_include = True
            
            # Filtro por palavras-chave
            if keywords and should_include:
                keywords_match = False
                for keyword in keywords:
                    if (
                        keyword.lower() in pl_data.get("Título", "").lower() or
                        keyword.lower() in pl_data.get("Palavras-chave", "").lower()
                    ):
                        keywords_match = True
                        break
                should_include = keywords_match
            
            # Filtro por autor
            if author and should_include:
                should_include = author.lower() in pl_data.get("Autor", "").lower()
            
            # Filtro por data
            if date_from and should_include and "Data" in pl_data:
                try:
                    pl_date = datetime.strptime(pl_data["Data"], "%Y-%m-%d")
                    from_date = datetime.strptime(date_from, "%Y-%m-%d")
                    should_include = pl_date >= from_date
                except ValueError:
                    # Se o formato da data for inválido, ignora este filtro
                    pass
            
            if date_to and should_include and "Data" in pl_data:
                try:
                    pl_date = datetime.strptime(pl_data["Data"], "%Y-%m-%d")
                    to_date = datetime.strptime(date_to, "%Y-%m-%d")
                    should_include = pl_date <= to_date
                except ValueError:
                    # Se o formato da data for inválido, ignora este filtro
                    pass
            
            # Se passou por todos os filtros, adiciona aos resultados
            if should_include:
                # Construir resultado no formato esperado
                parts = pl_id.split("_")
                sigla, numero, ano = parts[0], parts[1], parts[2]
                
                result = {
                    "ID": f"{sigla} {numero}/{ano}",
                    "Sigla": sigla,
                    "Numero": numero,
                    "Ano": ano,
                    "Título": pl_data.get("Título", ""),
                    "Autor": pl_data.get("Autor", ""),
                    "Data": pl_data.get("Data", ""),
                    "Status": pl_data.get("Status", ""),
                    "URL": pl_data.get("URL", "")
                }
                
                results.append(result)
        
        logger.info(f"Encontrados {len(results)} PLs correspondentes aos filtros")
        return results
    
    def get_recent_pls(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retorna os PLs mais recentes.
        Versão MVP: Retorna do CSV local ordenado por data.
        Versão futura: Integrará com a API do Senado.
        
        Args:
            limit: Número máximo de PLs a retornar
            
        Returns:
            Lista com os PLs mais recentes
        """
        logger.info(f"Buscando {limit} PLs mais recentes")
        
        # Carregar todos os PLs e ordenar por data
        pls_list = []
        for pl_id, pl_data in self._pls_data.items():
            parts = pl_id.split("_")
            sigla, numero, ano = parts[0], parts[1], parts[2]
            
            pl_with_date = {
                "ID": f"{sigla} {numero}/{ano}",
                "Sigla": sigla,
                "Numero": numero,
                "Ano": ano,
                "Título": pl_data.get("Título", ""),
                "Autor": pl_data.get("Autor", ""),
                "Data": pl_data.get("Data", ""),
                "Status": pl_data.get("Status", ""),
                "URL": pl_data.get("URL", "")
            }
            
            # Adicionar data como objeto datetime para ordenação
            try:
                pl_with_date["date_obj"] = datetime.strptime(pl_data.get("Data", "2020-01-01"), "%Y-%m-%d")
            except ValueError:
                # Se o formato da data for inválido, usa uma data antiga
                pl_with_date["date_obj"] = datetime(2020, 1, 1)
            
            pls_list.append(pl_with_date)
        
        # Ordenar por data em ordem decrescente
        pls_list.sort(key=lambda x: x["date_obj"], reverse=True)
        
        # Remover campo auxiliar e limitar resultados
        results = []
        for pl in pls_list[:limit]:
            pl_copy = pl.copy()
            del pl_copy["date_obj"]
            results.append(pl_copy)
        
        logger.info(f"Retornando {len(results)} PLs recentes")
        return results


# Exemplo de uso
if __name__ == "__main__":
    collector = SenadoCollector()
    
    # Buscar um PL específico
    pl_details = collector.get_pl_by_id("PL", "2234", "2022")
    print(f"Detalhes do PL 2234/2022:")
    print(json.dumps(pl_details, indent=2, ensure_ascii=False))
    
    # Buscar PLs recentes
    recent_pls = collector.get_recent_pls(limit=3)
    print(f"\n3 PLs mais recentes:")
    for pl in recent_pls:
        print(f"- {pl['ID']}: {pl['Título'][:50]}...")
    
    # Buscar por palavra-chave
    keyword_pls = collector.search_pls(keywords=["apostas"])
    print(f"\nPLs relacionados a 'apostas' ({len(keyword_pls)}):")
    for pl in keyword_pls:
        print(f"- {pl['ID']}: {pl['Título'][:50]}...")