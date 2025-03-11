# src/shared/storage.py
"""
Classe para gerenciar o armazenamento de dados da aplicação.
"""
import os
import json
import csv
import pandas as pd
from datetime import datetime

class DataStorage:
    """
    Gerencia o armazenamento e recuperação de dados da aplicação.
    Por simplicidade, usa armazenamento baseado em arquivos CSV.
    """
    
    def __init__(self, client_id=None):
        """
        Inicializa o gerenciador de armazenamento.
        
        Args:
            client_id (str, optional): Identificador do cliente.
        """
        self.client_id = client_id
        self.base_dir = os.path.join(os.getcwd(), "data")
        
        # Garantir que diretórios necessários existem
        self._ensure_directories()
    
    def _ensure_directories(self):
        """
        Garante que a estrutura de diretórios necessária existe.
        """
        # Diretório base de dados
        os.makedirs(self.base_dir, exist_ok=True)
        
        # Diretório de clientes
        clients_dir = os.path.join(self.base_dir, "clients")
        os.makedirs(clients_dir, exist_ok=True)
        
        # Diretório específico do cliente
        if self.client_id:
            client_dir = os.path.join(clients_dir, self.client_id)
            os.makedirs(client_dir, exist_ok=True)
            
            # Subdiretórios do cliente
            for subdir in ["assessments", "intelligence", "reports"]:
                os.makedirs(os.path.join(client_dir, subdir), exist_ok=True)
    
    def get_client_dir(self):
        """
        Retorna o caminho para o diretório do cliente atual.
        
        Returns:
            str: Caminho do diretório
        
        Raises:
            ValueError: Se nenhum client_id foi definido
        """
        if not self.client_id:
            raise ValueError("Nenhum cliente selecionado")
        
        return os.path.join(self.base_dir, "clients", self.client_id)
    
    def save_assessment(self, assessment_data):
        """
        Salva dados de avaliação de maturidade para o cliente atual.
        
        Args:
            assessment_data (list): Lista de dicionários com dados de avaliação
            
        Returns:
            str: Caminho do arquivo salvo
            
        Raises:
            ValueError: Se nenhum client_id foi definido
        """
        if not self.client_id:
            raise ValueError("Nenhum cliente selecionado")
        
        # Diretório para assessments
        assessment_dir = os.path.join(self.get_client_dir(), "assessments")
        os.makedirs(assessment_dir, exist_ok=True)
        
        # Nome do arquivo com timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"assessment_{timestamp}.csv"
        file_path = os.path.join(assessment_dir, filename)
        
        # Cria um DataFrame com os dados
        df = pd.DataFrame(assessment_data)
        
        # Salva como CSV
        df.to_csv(file_path, index=False)
        
        # Cria também uma versão "latest" para fácil acesso
        latest_path = os.path.join(assessment_dir, "assessment_latest.csv")
        df.to_csv(latest_path, index=False)
        
        return file_path
    
    def load_assessment(self, version="latest"):
        """
        Carrega dados de avaliação de maturidade para o cliente atual.
        
        Args:
            version (str, optional): Versão a carregar (latest por padrão)
            
        Returns:
            pandas.DataFrame: DataFrame com dados da avaliação ou None se não encontrado
            
        Raises:
            ValueError: Se nenhum client_id foi definido
        """
        if not self.client_id:
            raise ValueError("Nenhum cliente selecionado")
        
        # Diretório para assessments
        assessment_dir = os.path.join(self.get_client_dir(), "assessments")
        
        # Caminho do arquivo
        if version == "latest":
            file_path = os.path.join(assessment_dir, "assessment_latest.csv")
        else:
            file_path = os.path.join(assessment_dir, f"assessment_{version}.csv")
        
        # Verifica se o arquivo existe
        if not os.path.exists(file_path):
            return None
        
        # Carrega como DataFrame
        try:
            df = pd.read_csv(file_path)
            return df
        except Exception as e:
            print(f"Erro ao carregar avaliação: {str(e)}")
            return None
    
    def list_assessments(self):
        """
        Lista todas as avaliações salvas para o cliente atual.
        
        Returns:
            list: Lista de nomes de arquivo (timestamps)
            
        Raises:
            ValueError: Se nenhum client_id foi definido
        """
        if not self.client_id:
            raise ValueError("Nenhum cliente selecionado")
        
        # Diretório para assessments
        assessment_dir = os.path.join(self.get_client_dir(), "assessments")
        
        # Lista arquivos
        files = [f for f in os.listdir(assessment_dir) 
                 if f.startswith("assessment_") and f != "assessment_latest.csv"]
        
        # Extrai timestamps
        timestamps = [f.replace("assessment_", "").replace(".csv", "") for f in files]
        
        return sorted(timestamps, reverse=True)
    
    def save_report(self, report_data, report_type="maturity"):
        """
        Salva um relatório gerado para o cliente atual.
        
        Args:
            report_data (dict): Dados do relatório
            report_type (str, optional): Tipo do relatório
            
        Returns:
            str: Caminho do arquivo salvo
            
        Raises:
            ValueError: Se nenhum client_id foi definido
        """
        if not self.client_id:
            raise ValueError("Nenhum cliente selecionado")
        
        # Diretório para relatórios
        report_dir = os.path.join(self.get_client_dir(), "reports")
        os.makedirs(report_dir, exist_ok=True)
        
        # Nome do arquivo com timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{report_type}_report_{timestamp}.json"
        file_path = os.path.join(report_dir, filename)
        
        # Salva como JSON
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=4)
        
        return file_path
    
    def save_pl_data(self, pl_data):
        """
        Salva dados de projetos de lei para o cliente atual.
        
        Args:
            pl_data (list): Lista de dicionários com dados de PLs
            
        Returns:
            str: Caminho do arquivo salvo
            
        Raises:
            ValueError: Se nenhum client_id foi definido
        """
        if not self.client_id:
            raise ValueError("Nenhum cliente selecionado")
        
        # Diretório para intelligence
        intelligence_dir = os.path.join(self.get_client_dir(), "intelligence")
        os.makedirs(intelligence_dir, exist_ok=True)
        
        # Nome do arquivo com timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"pls_{timestamp}.csv"
        file_path = os.path.join(intelligence_dir, filename)
        
        # Cria um DataFrame com os dados
        df = pd.DataFrame(pl_data)
        
        # Salva como CSV
        df.to_csv(file_path, index=False)
        
        # Cria também uma versão "latest" para fácil acesso
        latest_path = os.path.join(intelligence_dir, "pls_latest.csv")
        df.to_csv(latest_path, index=False)
        
        return file_path
    
    def load_pl_data(self, version="latest"):
        """
        Carrega dados de projetos de lei para o cliente atual.
        
        Args:
            version (str, optional): Versão a carregar (latest por padrão)
            
        Returns:
            pandas.DataFrame: DataFrame com dados de PLs ou None se não encontrado
            
        Raises:
            ValueError: Se nenhum client_id foi definido
        """
        if not self.client_id:
            raise ValueError("Nenhum cliente selecionado")
        
        # Diretório para intelligence
        intelligence_dir = os.path.join(self.get_client_dir(), "intelligence")
        
        # Caminho do arquivo
        if version == "latest":
            file_path = os.path.join(intelligence_dir, "pls_latest.csv")
        else:
            file_path = os.path.join(intelligence_dir, f"pls_{version}.csv")
        
        # Verifica se o arquivo existe
        if not os.path.exists(file_path):
            return None
        
        # Carrega como DataFrame
        try:
            df = pd.read_csv(file_path)
            return df
        except Exception as e:
            print(f"Erro ao carregar dados de PLs: {str(e)}")
            return None