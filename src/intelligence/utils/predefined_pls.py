# src/intelligence/utils/predefined_pls.py
"""
Gerenciador de PLs pré-definidos para análise de impacto regulatório.
Mantém uma lista fixa de PLs importantes a serem analisados.
"""
import os
import json
import pandas as pd
import logging
from typing import List, Dict, Tuple, Any
from datetime import datetime

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("predefined_pls")

class PredefinedPLManager:
    """
    Classe para gerenciar PLs pré-definidos para análise regulatória.
    """
    
    # Lista inicial de PLs do Senado a serem monitorados
    # Reduzida para incluir apenas os que estão no CSV criado pelo SenadoCollector
    INITIAL_PLS_SENADO = [
        ('2234', '2022'), ('3405', '2023'), ('3563', '2024'), ('3718', '2024'),
        ('4392', '2024'), ('4391', '2024'), ('4390', '2024'),
        ('4031', '2024'), ('3795', '2024'), ('3719', '2024')
    ]
    
    def __init__(self, data_dir: str = None):
        """
        Inicializa o gerenciador de PLs pré-definidos.
        
        Args:
            data_dir: Diretório para armazenar dados. Se None, usa o padrão.
        """
        if data_dir is None:
            # Diretório padrão para armazenar dados dos PLs
            self.data_dir = os.path.join(os.getcwd(), "data", "predefined_pls")
        else:
            self.data_dir = data_dir
        
        # Garantir que o diretório existe
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Cria o arquivo de PLs se não existir
        self.pls_file = os.path.join(self.data_dir, "senado_pls.json")
        if not os.path.exists(self.pls_file):
            self._initialize_pls_list()
    
    def _initialize_pls_list(self):
        """
        Inicializa a lista de PLs com os valores iniciais.
        Verifica quais PLs estão disponíveis no SenadoCollector antes de adicioná-los.
        """
        try:
            # Importar dentro da função para evitar importação circular
            from src.intelligence.collectors.senado_collector import SenadoCollector
            
            # Inicializar o coletor para verificar PLs disponíveis
            collector = SenadoCollector()
            
            # Formata os PLs iniciais
            pls_data = {}
            
            # Para cada PL na lista inicial
            for numero, ano in self.INITIAL_PLS_SENADO:
                pl_id = f"PL {numero}/{ano}"
                # Verifica se o PL existe no CSV do SenadoCollector
                pl_details = collector.get_pl_by_id("PL", numero, ano)
                
                if pl_details:
                    logger.info(f"PL {pl_id} encontrado no SenadoCollector, adicionando...")
                    pls_data[pl_id] = {
                        "sigla": "PL",
                        "numero": numero,
                        "ano": ano,
                        "added_date": datetime.now().isoformat(),
                        "details_cached": True,  # Já está no CSV, então consideramos cacheado
                        "notes": "PL adicionado na inicialização",
                        "priority": "Media",  # Prioridade padrão
                        "categories": ["Sem categoria"]  # Categorias iniciais
                    }
                else:
                    logger.warning(f"PL {pl_id} não encontrado no SenadoCollector, ignorando...")
            
            # Salva no arquivo
            with open(self.pls_file, 'w', encoding='utf-8') as f:
                json.dump(pls_data, f, ensure_ascii=False, indent=4)
            
            logger.info(f"Lista inicial de {len(pls_data)} PLs criada com sucesso.")
        except Exception as e:
            logger.error(f"Erro ao inicializar lista de PLs: {str(e)}")
    
    def get_all_pls(self) -> Dict:
        """
        Retorna todos os PLs pré-definidos.
        
        Returns:
            Dicionário com os PLs
        """
        try:
            with open(self.pls_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Erro ao carregar PLs: {str(e)}")
            return {}
    
    def get_pls_as_dataframe(self) -> pd.DataFrame:
        """
        Retorna os PLs como DataFrame para fácil manipulação e exibição.
        
        Returns:
            DataFrame com os PLs
        """
        pls_dict = self.get_all_pls()
        if not pls_dict:
            return pd.DataFrame()
        
        # Preparar dados para o DataFrame
        rows = []
        for pl_id, pl_data in pls_dict.items():
            row = {
                'ID': pl_id,
                'Sigla': pl_data.get('sigla', 'PL'),
                'Número': pl_data.get('numero', ''),
                'Ano': pl_data.get('ano', ''),
                'Adicionado em': pl_data.get('added_date', ''),
                'Prioridade': pl_data.get('priority', 'Media'),
                'Categorias': ', '.join(pl_data.get('categories', ['Sem categoria'])),
                'Notas': pl_data.get('notes', '')
            }
            rows.append(row)
        
        return pd.DataFrame(rows)
    
    def add_pl(self, sigla: str, numero: str, ano: str, notes: str = "", 
               priority: str = "Media", categories: List[str] = None,
               custom_details: Dict = None, force_add: bool = False) -> bool:
        """
        Adiciona um novo PL à lista.
        Permite adicionar PLs que não existam no SenadoCollector, se fornecidos detalhes personalizados.
        
        Args:
            sigla: Sigla do PL (ex: PL, PEC)
            numero: Número do PL
            ano: Ano do PL
            notes: Notas sobre o PL
            priority: Prioridade (Alta, Media, Baixa)
            categories: Lista de categorias
            custom_details: Detalhes personalizados para PLs que não estão no SenadoCollector
            force_add: Se True, adiciona o PL mesmo que não esteja no SenadoCollector
            
        Returns:
            True se adicionou com sucesso, False caso contrário
        """
        try:
            # Carrega PLs existentes
            pls_dict = self.get_all_pls()
            
            # Formata o ID
            pl_id = f"{sigla} {numero}/{ano}"
            
            # Verifica se já existe
            if pl_id in pls_dict:
                logger.warning(f"PL {pl_id} já existe na lista.")
                return False
            
            # Verifica se o PL existe no SenadoCollector
            from src.intelligence.collectors.senado_collector import SenadoCollector
            collector = SenadoCollector()
            pl_details = collector.get_pl_by_id(sigla, numero, ano)
            
            # Se não encontrou o PL e não foi fornecido force_add nem custom_details
            if not pl_details and not force_add and not custom_details:
                logger.warning(f"PL {pl_id} não encontrado no SenadoCollector. Use force_add=True ou forneça custom_details para adicionar manualmente.")
                return False
            
            # Adiciona o novo PL
            pls_dict[pl_id] = {
                "sigla": sigla,
                "numero": numero,
                "ano": ano,
                "added_date": datetime.now().isoformat(),
                "details_cached": pl_details is not None,  # True se existe no SenadoCollector
                "notes": notes,
                "priority": priority,
                "categories": categories if categories else ["Sem categoria"],
                "is_custom": not pl_details and (force_add or custom_details is not None)  # Marca como personalizado
            }
            
            # Salva no arquivo
            with open(self.pls_file, 'w', encoding='utf-8') as f:
                json.dump(pls_dict, f, ensure_ascii=False, indent=4)
            
            # Se for um PL personalizado e tiver detalhes, salvá-los
            if custom_details and not pl_details:
                # Adicionar ao CSV do SenadoCollector
                from src.intelligence.collectors.senado_collector import SenadoCollector
                csv_collector = SenadoCollector()
                csv_collector.add_pl_to_csv(sigla, numero, ano, custom_details)
                
                # Salvar no cache
                cache_file = os.path.join(self.data_dir, f"{sigla}_{numero}_{ano}_details.json")
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(custom_details, f, ensure_ascii=False, indent=4)
                logger.info(f"Detalhes personalizados para PL {pl_id} salvos com sucesso.")
            
            logger.info(f"PL {pl_id} adicionado com sucesso.")
            return True
        except Exception as e:
            logger.error(f"Erro ao adicionar PL: {str(e)}")
            return False
    
    def remove_pl(self, pl_id: str) -> bool:
        """
        Remove um PL da lista.
        
        Args:
            pl_id: ID do PL a remover (ex: PL 1234/2023)
            
        Returns:
            True se removeu com sucesso, False caso contrário
        """
        try:
            # Carrega PLs existentes
            pls_dict = self.get_all_pls()
            
            # Verifica se existe
            if pl_id not in pls_dict:
                logger.warning(f"PL {pl_id} não encontrado na lista.")
                return False
            
            # Remove o PL
            del pls_dict[pl_id]
            
            # Salva no arquivo
            with open(self.pls_file, 'w', encoding='utf-8') as f:
                json.dump(pls_dict, f, ensure_ascii=False, indent=4)
            
            logger.info(f"PL {pl_id} removido com sucesso.")
            return True
        except Exception as e:
            logger.error(f"Erro ao remover PL: {str(e)}")
            return False
    
    def update_pl(self, pl_id: str, notes: str = None, priority: str = None, 
                  categories: List[str] = None) -> bool:
        """
        Atualiza informações de um PL.
        
        Args:
            pl_id: ID do PL a atualizar
            notes: Novas notas (opcional)
            priority: Nova prioridade (opcional)
            categories: Novas categorias (opcional)
            
        Returns:
            True se atualizou com sucesso, False caso contrário
        """
        try:
            # Carrega PLs existentes
            pls_dict = self.get_all_pls()
            
            # Verifica se existe
            if pl_id not in pls_dict:
                logger.warning(f"PL {pl_id} não encontrado na lista.")
                return False
            
            # Atualiza os campos fornecidos
            if notes is not None:
                pls_dict[pl_id]["notes"] = notes
            
            if priority is not None:
                pls_dict[pl_id]["priority"] = priority
            
            if categories is not None:
                pls_dict[pl_id]["categories"] = categories
            
            # Salva no arquivo
            with open(self.pls_file, 'w', encoding='utf-8') as f:
                json.dump(pls_dict, f, ensure_ascii=False, indent=4)
            
            logger.info(f"PL {pl_id} atualizado com sucesso.")
            return True
        except Exception as e:
            logger.error(f"Erro ao atualizar PL: {str(e)}")
            return False
    
    def fetch_pl_details(self, pl_id: str = None, force_refresh: bool = False) -> Dict:
        """
        Busca detalhes de um PL ou de todos os PLs da lista, seja do CSV ou de caches personalizados.
        
        Args:
            pl_id: ID do PL específico para buscar (se None, busca todos)
            force_refresh: Se True, força atualização mesmo se já tiver cache
            
        Returns:
            Dicionário com detalhes dos PLs
        """
        try:
            # Inicializa o coletor
            from src.intelligence.collectors.senado_collector import SenadoCollector
            collector = SenadoCollector()
            
            # Carrega PLs existentes
            pls_dict = self.get_all_pls()
            details_dict = {}
            
            # Se foi especificado um PL
            if pl_id:
                if pl_id not in pls_dict:
                    logger.warning(f"PL {pl_id} não encontrado na lista.")
                    return {}
                
                # Extrai informações do PL
                pl_data = pls_dict[pl_id]
                sigla = pl_data["sigla"]
                numero = pl_data["numero"]
                ano = pl_data["ano"]
                is_custom = pl_data.get("is_custom", False)
                
                # Arquivo de cache para este PL
                cache_file = os.path.join(self.data_dir, f"{sigla}_{numero}_{ano}_details.json")
                
                # Verifica se já tem cache e se não precisa forçar atualização
                if os.path.exists(cache_file) and not force_refresh:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        pl_details = json.load(f)
                    
                    logger.info(f"Detalhes do PL {pl_id} carregados do cache.")
                    return {pl_id: pl_details}
                
                # Se for um PL personalizado e não tiver cache, cria um objeto vazio
                if is_custom and not os.path.exists(cache_file):
                    pl_details = {
                        "Título": f"[Personalizado] PL {numero}/{ano}",
                        "Data": datetime.now().strftime("%Y-%m-%d"),
                        "Autor": "Usuário",
                        "Status": "Desconhecido",
                        "URL": "",
                        "Palavras-chave": ""
                    }
                    
                    # Salva no cache
                    with open(cache_file, 'w', encoding='utf-8') as f:
                        json.dump(pl_details, f, ensure_ascii=False, indent=4)
                    
                    # Marca como em cache
                    pls_dict[pl_id]["details_cached"] = True
                    with open(self.pls_file, 'w', encoding='utf-8') as f:
                        json.dump(pls_dict, f, ensure_ascii=False, indent=4)
                    
                    logger.info(f"Detalhes padrão do PL personalizado {pl_id} criados e salvos.")
                    return {pl_id: pl_details}
                
                # Busca detalhes na API
                logger.info(f"Buscando detalhes do PL {pl_id} na API do Senado...")
                pl_details = collector.get_pl_by_id(sigla, numero, ano)
                
                if pl_details:
                    # Salva no cache
                    with open(cache_file, 'w', encoding='utf-8') as f:
                        json.dump(pl_details, f, ensure_ascii=False, indent=4)
                    
                    # Marca como em cache
                    pls_dict[pl_id]["details_cached"] = True
                    with open(self.pls_file, 'w', encoding='utf-8') as f:
                        json.dump(pls_dict, f, ensure_ascii=False, indent=4)
                    
                    logger.info(f"Detalhes do PL {pl_id} obtidos e salvos com sucesso.")
                    return {pl_id: pl_details}
                else:
                    logger.warning(f"Não foi possível obter detalhes do PL {pl_id}.")
                    
                    # Se for um PL personalizado, criar detalhes básicos
                    if is_custom:
                        pl_details = {
                            "Título": f"[Personalizado] PL {numero}/{ano}",
                            "Data": datetime.now().strftime("%Y-%m-%d"),
                            "Autor": "Usuário",
                            "Status": "Desconhecido",
                            "URL": "",
                            "Palavras-chave": ""
                        }
                        
                        # Salva no cache
                        with open(cache_file, 'w', encoding='utf-8') as f:
                            json.dump(pl_details, f, ensure_ascii=False, indent=4)
                        
                        logger.info(f"Detalhes básicos do PL personalizado {pl_id} criados.")
                        return {pl_id: pl_details}
                    
                    return {}
            
            # Se não foi especificado um PL, busca todos
            for pl_id, pl_data in pls_dict.items():
                sigla = pl_data["sigla"]
                numero = pl_data["numero"]
                ano = pl_data["ano"]
                is_custom = pl_data.get("is_custom", False)
                
                # Arquivo de cache para este PL
                cache_file = os.path.join(self.data_dir, f"{sigla}_{numero}_{ano}_details.json")
                
                # Verifica se já tem cache e se não precisa forçar atualização
                if os.path.exists(cache_file) and not force_refresh:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        pl_details = json.load(f)
                    
                    details_dict[pl_id] = pl_details
                    logger.info(f"Detalhes do PL {pl_id} carregados do cache.")
                    continue
                
                # Se for um PL personalizado e não tiver cache, cria um objeto básico
                if is_custom and not os.path.exists(cache_file):
                    pl_details = {
                        "Título": f"[Personalizado] PL {numero}/{ano}",
                        "Data": datetime.now().strftime("%Y-%m-%d"),
                        "Autor": "Usuário",
                        "Status": "Desconhecido",
                        "URL": "",
                        "Palavras-chave": ""
                    }
                    
                    # Salva no cache
                    with open(cache_file, 'w', encoding='utf-8') as f:
                        json.dump(pl_details, f, ensure_ascii=False, indent=4)
                    
                    details_dict[pl_id] = pl_details
                    logger.info(f"Detalhes básicos do PL personalizado {pl_id} criados.")
                    continue
                
                # Busca detalhes na API
                logger.info(f"Buscando detalhes do PL {pl_id} na API do Senado...")
                pl_details = collector.get_pl_by_id(sigla, numero, ano)
                
                if pl_details:
                    # Salva no cache
                    with open(cache_file, 'w', encoding='utf-8') as f:
                        json.dump(pl_details, f, ensure_ascii=False, indent=4)
                    
                    # Marca como em cache
                    pls_dict[pl_id]["details_cached"] = True
                    details_dict[pl_id] = pl_details
                    logger.info(f"Detalhes do PL {pl_id} obtidos e salvos com sucesso.")
                else:
                    logger.warning(f"Não foi possível obter detalhes do PL {pl_id}.")
                    
                    # Se for um PL personalizado, criar detalhes básicos
                    if is_custom:
                        pl_details = {
                            "Título": f"[Personalizado] PL {numero}/{ano}",
                            "Data": datetime.now().strftime("%Y-%m-%d"),
                            "Autor": "Usuário",
                            "Status": "Desconhecido",
                            "URL": "",
                            "Palavras-chave": ""
                        }
                        
                        # Salva no cache
                        with open(cache_file, 'w', encoding='utf-8') as f:
                            json.dump(pl_details, f, ensure_ascii=False, indent=4)
                        
                        details_dict[pl_id] = pl_details
                        logger.info(f"Detalhes básicos do PL personalizado {pl_id} criados.")
            
            # Atualiza o arquivo principal
            with open(self.pls_file, 'w', encoding='utf-8') as f:
                json.dump(pls_dict, f, ensure_ascii=False, indent=4)
            
            return details_dict
        except Exception as e:
            logger.error(f"Erro ao buscar detalhes dos PLs: {str(e)}")
            return {}
    
    def get_pl_details_dataframe(self, force_refresh: bool = False) -> pd.DataFrame:
        """
        Obtém detalhes de todos os PLs como DataFrame para exibição.
        
        Args:
            force_refresh: Se True, força atualização dos dados
            
        Returns:
            DataFrame com detalhes dos PLs
        """
        # Busca detalhes de todos os PLs
        details_dict = self.fetch_pl_details(force_refresh=force_refresh)
        
        # Se não encontrou nenhum detalhe, tenta uma abordagem alternativa
        if not details_dict:
            logger.warning("Nenhum detalhe encontrado via fetch_pl_details. Usando abordagem alternativa.")
            # Importar coletor diretamente
            from src.intelligence.collectors.senado_collector import SenadoCollector
            collector = SenadoCollector()
            
            # Obter todos os PLs disponíveis
            pls_dict = self.get_all_pls()
            details_dict = {}
            
            # Para cada PL na lista
            for pl_id, pl_data in pls_dict.items():
                parts = pl_id.split(" ")
                if len(parts) >= 2:
                    sigla = parts[0]
                    numero_ano = parts[1].split("/")
                    if len(numero_ano) >= 2:
                        numero = numero_ano[0]
                        ano = numero_ano[1]
                        
                        # Buscar detalhes diretamente
                        pl_details = collector.get_pl_by_id(sigla, numero, ano)
                        if pl_details:
                            details_dict[pl_id] = pl_details
            
            # Se ainda não encontrou nada, retorna DataFrame vazio
            if not details_dict:
                logger.error("Não foi possível obter detalhes dos PLs. Retornando DataFrame vazio.")
                return pd.DataFrame()
        
        # Preparar dados para o DataFrame
        rows = []
        for pl_id, pl_details in details_dict.items():
            row = {
                'ID': pl_id,
                'Título': pl_details.get('Título', 'Não disponível'),
                'Data': pl_details.get('Data', ''),
                'Autor': pl_details.get('Autor', 'Não disponível'),
                'Status': pl_details.get('Status', 'Não disponível'),
                'URL': pl_details.get('URL', ''),
                'Palavras-chave': pl_details.get('Palavras-chave', '')
            }
            
            # Adicionar campos da lista de PLs pré-definidos
            pls_dict = self.get_all_pls()
            if pl_id in pls_dict:
                row['Prioridade'] = pls_dict[pl_id].get('priority', 'Media')
                row['Categorias'] = ', '.join(pls_dict[pl_id].get('categories', ['Sem categoria']))
                row['Notas'] = pls_dict[pl_id].get('notes', '')
            
            rows.append(row)
        
        return pd.DataFrame(rows)


# Exemplo de uso
if __name__ == "__main__":
    manager = PredefinedPLManager()
    
    # Lista PLs atuais
    pls_df = manager.get_pls_as_dataframe()
    print(f"PLs pré-definidos ({len(pls_df)}):")
    print(pls_df[['ID', 'Número', 'Ano', 'Prioridade']].head())
    
    # Busca detalhes de todos os PLs
    details = manager.fetch_pl_details()
    print(f"\nDetalhes obtidos para {len(details)} PLs.")
    
    # Obter detalhes como DataFrame
    details_df = manager.get_pl_details_dataframe()
    if not details_df.empty:
        print("\nExemplo de detalhes:")
        print(details_df[['ID', 'Título', 'Status']].head())