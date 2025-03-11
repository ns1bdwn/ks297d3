# src/intelligence/utils/keyword_manager.py
"""
Gerenciador de palavras-chave para monitoramento de PLs.
Permite adicionar, remover e atualizar palavras-chave por setor.
"""
import os
import pandas as pd
import json
from typing import List, Dict, Any, Optional, Union
import logging

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("keyword_manager")

class KeywordManager:
    """
    Classe para gerenciar palavras-chave por setor.
    Armazena em CSV para simplicidade inicial.
    """
    
    def __init__(self, data_dir: str = None):
        """
        Inicializa o gerenciador de palavras-chave.
        
        Args:
            data_dir: Diretório para armazenar dados. Se None, usa o padrão.
        """
        if data_dir is None:
            # Diretório padrão: /data/keywords/
            self.data_dir = os.path.join(os.getcwd(), "data", "keywords")
        else:
            self.data_dir = data_dir
            
        # Garante que o diretório existe
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Prepara dados padrão se não existirem
        self._initialize_default_keywords()
    
    def _initialize_default_keywords(self):
        """
        Inicializa palavras-chave padrão para setores comuns se não existirem.
        """
        # Verifica se já existem arquivos de palavras-chave
        existing_files = os.listdir(self.data_dir)
        
        # Se não houver nenhum arquivo, cria os padrões
        if not existing_files:
            # Palavras-chave para iGaming
            igaming_keywords = [
                {"keyword": "apostas", "type": "term", "enabled": True, "description": "Termo geral para apostas"},
                {"keyword": "jogo online", "type": "term", "enabled": True, "description": "Jogos de azar online"},
                {"keyword": "cassino", "type": "term", "enabled": True, "description": "Operações de cassino"},
                {"keyword": "bingo", "type": "term", "enabled": True, "description": "Jogos de bingo"},
                {"keyword": "loteria", "type": "term", "enabled": True, "description": "Operações de loteria"},
                {"keyword": "Lei 14.790", "type": "reference", "enabled": True, "description": "Lei de regulamentação de apostas de quota fixa"},
                {"keyword": "jogo responsável", "type": "term", "enabled": True, "description": "Práticas de jogo responsável"},
                {"keyword": "quota fixa", "type": "term", "enabled": True, "description": "Apostas de quota fixa"}
            ]
            
            # Palavras-chave para Meios de Pagamento
            payments_keywords = [
                {"keyword": "pagamento", "type": "term", "enabled": True, "description": "Sistemas de pagamento"},
                {"keyword": "PIX", "type": "term", "enabled": True, "description": "Sistema de pagamentos instantâneos"},
                {"keyword": "cartão de crédito", "type": "term", "enabled": True, "description": "Meios de pagamento com cartão"},
                {"keyword": "banco central", "type": "term", "enabled": True, "description": "Regulações do Banco Central"},
                {"keyword": "Resolução BCB", "type": "reference", "enabled": True, "description": "Resoluções do Banco Central"},
                {"keyword": "pagamento instantâneo", "type": "term", "enabled": True, "description": "Sistemas de transferência instantânea"}
            ]
            
            # Palavras-chave para Ativos Digitais
            crypto_keywords = [
                {"keyword": "criptomoedas", "type": "term", "enabled": True, "description": "Ativos digitais baseados em criptografia"},
                {"keyword": "bitcoin", "type": "term", "enabled": True, "description": "Criptomoeda principal"},
                {"keyword": "blockchain", "type": "term", "enabled": True, "description": "Tecnologia de registro distribuído"},
                {"keyword": "token", "type": "term", "enabled": True, "description": "Token digital"},
                {"keyword": "NFT", "type": "term", "enabled": True, "description": "Token não fungível"},
                {"keyword": "stablecoin", "type": "term", "enabled": True, "description": "Criptomoeda estável"},
                {"keyword": "ativos virtuais", "type": "term", "enabled": True, "description": "Definição legal de ativos digitais"}
            ]
            
            # Salva os arquivos
            self._save_keywords("igaming", igaming_keywords)
            self._save_keywords("pagamentos", payments_keywords)
            self._save_keywords("cripto", crypto_keywords)
            
            logger.info("Palavras-chave padrão inicializadas com sucesso.")
    
    def _get_file_path(self, sector: str) -> str:
        """
        Retorna o caminho do arquivo para um setor.
        
        Args:
            sector: Nome do setor
            
        Returns:
            Caminho do arquivo CSV
        """
        # Normaliza o nome do setor (minúsculas, sem espaços)
        sector = sector.lower().replace(" ", "_")
        return os.path.join(self.data_dir, f"{sector}_keywords.csv")
    
    def get_sectors(self) -> List[str]:
        """
        Retorna a lista de setores disponíveis.
        
        Returns:
            Lista de nomes de setores
        """
        try:
            files = os.listdir(self.data_dir)
            sectors = []
            
            for file in files:
                if file.endswith("_keywords.csv"):
                    sector = file.replace("_keywords.csv", "")
                    sectors.append(sector)
                    
            return sectors
        except Exception as e:
            logger.error(f"Erro ao listar setores: {str(e)}")
            return []
    
    def get_keywords(self, sector: str, enabled_only: bool = False) -> pd.DataFrame:
        """
        Retorna as palavras-chave de um setor.
        
        Args:
            sector: Nome do setor
            enabled_only: Se True, retorna apenas palavras-chave ativas
            
        Returns:
            DataFrame com as palavras-chave
        """
        file_path = self._get_file_path(sector)
        
        try:
            if os.path.exists(file_path):
                df = pd.read_csv(file_path)
                
                # Aplica filtro se necessário
                if enabled_only:
                    df = df[df['enabled'] == True]
                    
                return df
            else:
                logger.warning(f"Arquivo de palavras-chave não encontrado para o setor: {sector}")
                return pd.DataFrame(columns=['sector', 'keyword', 'type', 'enabled', 'description'])
        except Exception as e:
            logger.error(f"Erro ao ler palavras-chave: {str(e)}")
            return pd.DataFrame(columns=['sector', 'keyword', 'type', 'enabled', 'description'])
    
    def _save_keywords(self, sector: str, keywords: List[Dict]) -> bool:
        """
        Salva palavras-chave para um setor.
        
        Args:
            sector: Nome do setor
            keywords: Lista de dicionários com palavras-chave
            
        Returns:
            True se salvou com sucesso, False caso contrário
        """
        file_path = self._get_file_path(sector)
        
        try:
            # Prepara DataFrame
            df = pd.DataFrame(keywords)
            
            # Adiciona coluna de setor
            df['sector'] = sector
            
            # Salva no arquivo
            df.to_csv(file_path, index=False)
            logger.info(f"Palavras-chave salvas com sucesso para o setor: {sector}")
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar palavras-chave: {str(e)}")
            return False
    
    def add_keyword(self, sector: str, keyword: str, keyword_type: str = "term", 
                    enabled: bool = True, description: str = "") -> bool:
        """
        Adiciona uma nova palavra-chave a um setor.
        
        Args:
            sector: Nome do setor
            keyword: Palavra-chave a adicionar
            keyword_type: Tipo da palavra-chave (term, reference)
            enabled: Se a palavra-chave está ativa
            description: Descrição da palavra-chave
            
        Returns:
            True se adicionou com sucesso, False caso contrário
        """
        try:
            # Obtém palavras-chave existentes
            df = self.get_keywords(sector)
            
            # Verifica se a palavra-chave já existe
            if not df.empty and keyword in df['keyword'].values:
                logger.warning(f"Palavra-chave '{keyword}' já existe para o setor: {sector}")
                return False
            
            # Cria novo registro
            new_keyword = {
                'sector': sector,
                'keyword': keyword,
                'type': keyword_type,
                'enabled': enabled,
                'description': description
            }
            
            # Adiciona ao DataFrame
            new_df = pd.concat([df, pd.DataFrame([new_keyword])], ignore_index=True)
            
            # Salva no arquivo
            file_path = self._get_file_path(sector)
            new_df.to_csv(file_path, index=False)
            
            logger.info(f"Palavra-chave '{keyword}' adicionada ao setor: {sector}")
            return True
        except Exception as e:
            logger.error(f"Erro ao adicionar palavra-chave: {str(e)}")
            return False
    
    def remove_keyword(self, sector: str, keyword: str) -> bool:
        """
        Remove uma palavra-chave de um setor.
        
        Args:
            sector: Nome do setor
            keyword: Palavra-chave a remover
            
        Returns:
            True se removeu com sucesso, False caso contrário
        """
        try:
            # Obtém palavras-chave existentes
            df = self.get_keywords(sector)
            
            # Verifica se a palavra-chave existe
            if df.empty or keyword not in df['keyword'].values:
                logger.warning(f"Palavra-chave '{keyword}' não encontrada para o setor: {sector}")
                return False
            
            # Remove a palavra-chave
            new_df = df[df['keyword'] != keyword]
            
            # Salva no arquivo
            file_path = self._get_file_path(sector)
            new_df.to_csv(file_path, index=False)
            
            logger.info(f"Palavra-chave '{keyword}' removida do setor: {sector}")
            return True
        except Exception as e:
            logger.error(f"Erro ao remover palavra-chave: {str(e)}")
            return False
    
    def update_keyword_status(self, sector: str, keyword: str, enabled: bool) -> bool:
        """
        Atualiza o status de uma palavra-chave.
        
        Args:
            sector: Nome do setor
            keyword: Palavra-chave a atualizar
            enabled: Novo status (True/False)
            
        Returns:
            True se atualizou com sucesso, False caso contrário
        """
        try:
            # Obtém palavras-chave existentes
            df = self.get_keywords(sector)
            
            # Verifica se a palavra-chave existe
            if df.empty or keyword not in df['keyword'].values:
                logger.warning(f"Palavra-chave '{keyword}' não encontrada para o setor: {sector}")
                return False
            
            # Atualiza o status
            df.loc[df['keyword'] == keyword, 'enabled'] = enabled
            
            # Salva no arquivo
            file_path = self._get_file_path(sector)
            df.to_csv(file_path, index=False)
            
            status_str = "ativada" if enabled else "desativada"
            logger.info(f"Palavra-chave '{keyword}' {status_str} no setor: {sector}")
            return True
        except Exception as e:
            logger.error(f"Erro ao atualizar status da palavra-chave: {str(e)}")
            return False
    
    def toggle_keyword(self, sector: str, keyword: str) -> bool:
        """
        Alterna o status de uma palavra-chave (habilitada/desabilitada).
        
        Args:
            sector: Nome do setor
            keyword: Palavra-chave a alternar
            
        Returns:
            True se alternou com sucesso, False caso contrário
        """
        try:
            # Obtém palavras-chave existentes
            df = self.get_keywords(sector)
            
            # Verifica se a palavra-chave existe
            if df.empty or keyword not in df['keyword'].values:
                logger.warning(f"Palavra-chave '{keyword}' não encontrada para o setor: {sector}")
                return False
            
            # Obtém status atual
            current_status = df.loc[df['keyword'] == keyword, 'enabled'].iloc[0]
            
            # Inverte o status
            df.loc[df['keyword'] == keyword, 'enabled'] = not current_status
            
            # Salva no arquivo
            file_path = self._get_file_path(sector)
            df.to_csv(file_path, index=False)
            
            new_status = not current_status
            status_str = "ativada" if new_status else "desativada"
            logger.info(f"Palavra-chave '{keyword}' {status_str} no setor: {sector}")
            return True
        except Exception as e:
            logger.error(f"Erro ao alternar status da palavra-chave: {str(e)}")
            return False
    
    def export_to_dict(self, sector: str = None) -> Dict[str, List[str]]:
        """
        Exporta palavras-chave como dicionário para uso pelos coletores.
        
        Args:
            sector: Nome do setor (opcional). Se None, exporta todos.
            
        Returns:
            Dicionário com tipos de palavras-chave e suas listas
        """
        result = {"term": [], "reference": []}
        
        try:
            if sector:
                # Exporta apenas para um setor
                df = self.get_keywords(sector, enabled_only=True)
                
                if not df.empty:
                    for keyword_type in ["term", "reference"]:
                        type_df = df[df['type'] == keyword_type]
                        if not type_df.empty:
                            result[keyword_type] = type_df['keyword'].tolist()
            else:
                # Exporta para todos os setores
                sectors = self.get_sectors()
                for sector in sectors:
                    df = self.get_keywords(sector, enabled_only=True)
                    
                    if not df.empty:
                        for keyword_type in ["term", "reference"]:
                            type_df = df[df['type'] == keyword_type]
                            if not type_df.empty:
                                result[keyword_type].extend(type_df['keyword'].tolist())
                
                # Remove duplicatas
                result["term"] = list(set(result["term"]))
                result["reference"] = list(set(result["reference"]))
            
            return result
        except Exception as e:
            logger.error(f"Erro ao exportar palavras-chave: {str(e)}")
            return result


# Exemplo de uso
if __name__ == "__main__":
    manager = KeywordManager()
    
    # Lista setores disponíveis
    sectors = manager.get_sectors()
    print(f"Setores disponíveis: {sectors}")
    
    # Obtém palavras-chave de um setor
    if "igaming" in sectors:
        keywords = manager.get_keywords("igaming")
        print("\nPalavras-chave para iGaming:")
        print(keywords)
        
        # Exporta para formato de dicionário
        keywords_dict = manager.export_to_dict("igaming")
        print("\nExportação para dicionário:")
        print(json.dumps(keywords_dict, indent=2))