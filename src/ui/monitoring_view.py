# src/ui/monitoring_view.py
"""
Interface simplificada para monitoramento de PLs com foco no Senado Federal.
Sem aninhamento excessivo de colunas.
"""
import streamlit as st
import pandas as pd
import os
import sys
from datetime import datetime, timedelta
import logging
import json
from pathlib import Path

# Adicionar o diretório raiz ao path para importações relativas
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.intelligence.collectors.senado_collector import SenadoCollector
from src.intelligence.utils.keyword_manager import KeywordManager

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("monitoring_view")

def render_monitoring_view():
    """
    Renderiza a interface de monitoramento de PLs.
    Versão simplificada para evitar aninhamento excessivo de colunas.
    """
    st.write("### Monitoramento de Projetos de Lei")
    
    # Inicializa variáveis de sessão se não existirem
    _initialize_session_state()
    
    # Duas abas principais: Busca e Resultados
    tab1, tab2 = st.tabs(["Configuração de Busca", "Resultados"])
    
    with tab1:
        _render_search_config()
    
    with tab2:
        _render_search_results()

def _initialize_session_state():
    """Inicializa as variáveis de estado da sessão."""
    if "monitor_sector" not in st.session_state:
        st.session_state.monitor_sector = "igaming"
    
    if "analysis_pls" not in st.session_state:
        st.session_state.analysis_pls = []
    
    if "search_results" not in st.session_state:
        st.session_state.search_results = None
    
    if "show_keyword_manager" not in st.session_state:
        st.session_state.show_keyword_manager = False
    
    if "current_pl_details" not in st.session_state:
        st.session_state.current_pl_details = None
    
    if "selected_pl_ids" not in st.session_state:
        st.session_state.selected_pl_ids = set()

def _render_search_config():
    """
    Renderiza a configuração de busca de PLs.
    """
    st.write("#### Parâmetros de Busca")
    
    # Inicializa o gerenciador de palavras-chave
    keyword_manager = KeywordManager()
    
    # Obtém os setores disponíveis
    sectors = keyword_manager.get_sectors()
    
    # Seletor de setor
    selected_sector = st.selectbox(
        "Setor",
        options=sectors,
        index=sectors.index(st.session_state.monitor_sector) if st.session_state.monitor_sector in sectors else 0,
        key="sector_selector"
    )
    
    # Atualiza o setor na sessão
    st.session_state.monitor_sector = selected_sector
    
    # Obtém palavras-chave do setor selecionado
    keywords_df = keyword_manager.get_keywords(sector=selected_sector)
    
    # Mostra as palavras-chave ativas
    st.write("#### Palavras-chave")
    
    if not keywords_df.empty:
        # Filtra apenas palavras-chave ativas
        active_keywords = keywords_df[keywords_df['enabled'] == True]
        
        if not active_keywords.empty:
            # Mostra checkboxes para palavras-chave ativas
            st.write("**Selecione as palavras-chave para busca:**")
            
            # Agrupa por tipo
            for keyword_type in sorted(active_keywords['type'].unique()):
                st.write(f"**{keyword_type.capitalize()}:**")
                type_keywords = active_keywords[active_keywords['type'] == keyword_type]
                
                for i, row in type_keywords.iterrows():
                    key = f"kw_{row['keyword']}"
                    # Define valor padrão como True
                    if key not in st.session_state:
                        st.session_state[key] = True
                        
                    st.checkbox(
                        row['keyword'], 
                        value=st.session_state[key],
                        key=key,
                        help=row['description'] if row['description'] else None
                    )
        else:
            st.info(f"Nenhuma palavra-chave ativa para o setor {selected_sector}.")
            
        # Botão para gerenciar palavras-chave
        if st.button("Gerenciar Palavras-chave"):
            st.session_state.show_keyword_manager = True
    else:
        st.info(f"Nenhuma palavra-chave configurada para o setor {selected_sector}.")
        
        if st.button("Configurar Palavras-chave"):
            st.session_state.show_keyword_manager = True
    
    # Período de busca
    st.write("#### Período")
    
    # Data inicial: padrão para 3 meses atrás
    default_start = datetime.now() - timedelta(days=90)
    start_date = st.date_input(
        "Data inicial",
        value=default_start,
        max_value=datetime.now(),
        key="start_date"
    )
    
    # Data final: hoje por padrão
    end_date = st.date_input(
        "Data final",
        value=datetime.now(),
        max_value=datetime.now(),
        key="end_date"
    )
    
    # Fonte de dados
    st.write("#### Fonte de Dados")
    st.radio(
        "Fonte",
        options=["Senado Federal"],
        index=0,
        key="data_source"
    )
    
    # Botão para buscar
    if st.button("Buscar PLs", type="primary"):
        with st.spinner("Buscando projetos de lei..."):
            # Obter palavras-chave selecionadas
            active_keywords = [k.replace("kw_", "") for k, v in st.session_state.items() 
                              if k.startswith("kw_") and v]
            
            if not active_keywords:
                st.warning("Selecione pelo menos uma palavra-chave para busca.")
            else:
                # Formatar datas para a API
                start_str = start_date.strftime("%Y%m%d") if start_date else None
                end_str = end_date.strftime("%Y%m%d") if end_date else None
                
                # Instanciar o coletor do Senado
                collector = SenadoCollector()
                
                try:
                    # Realizar a busca
                    st.session_state.search_results = collector.search_multiple_keywords(
                        active_keywords, 
                        start_date=start_str, 
                        end_date=end_str
                    )
                    
                    # Log para diagnóstico
                    logger.info(f"Busca concluída: {len(st.session_state.search_results)} resultados encontrados")
                    
                    # Salvar resultados para o cliente atual
                    if "client_id" in st.session_state and st.session_state.client_id:
                        _save_search_results(st.session_state.search_results)
                except Exception as e:
                    logger.error(f"Erro na busca: {str(e)}")
                    st.error(f"Erro ao realizar busca: {str(e)}")

def _render_search_results():
    """
    Renderiza os resultados da busca de PLs.
    Versão simplificada para evitar aninhamento excessivo de colunas.
    """
    # Contador de PLs selecionados para análise
    if st.session_state.analysis_pls:
        st.info(
            f"**{len(st.session_state.analysis_pls)} PLs selecionados para análise de impacto**. "
            f"Vá para a seção de Análise de Impacto para visualizá-los."
        )
    
    # Resultados da busca
    if st.session_state.search_results is not None:
        if st.session_state.search_results.empty:
            st.info("Nenhum PL encontrado com os critérios especificados.")
        else:
            st.write(f"#### Resultados: {len(st.session_state.search_results)} PLs encontrados")
            
            # Filtros rápidos (numa única linha)
            col1, col2 = st.columns(2)
            
            with col1:
                # Filtrar por status se houver status na coluna
                if 'Status' in st.session_state.search_results.columns:
                    status_options = sorted(st.session_state.search_results['Status'].dropna().unique())
                    if status_options:
                        status_filter = st.multiselect(
                            "Filtrar por status",
                            options=status_options,
                            default=[]
                        )
                    else:
                        status_filter = []
                else:
                    status_filter = []
            
            with col2:
                # Pesquisa por texto
                search_text = st.text_input("Pesquisar nos resultados", placeholder="Digite para filtrar")
            
            # Aplicar filtros
            filtered_results = st.session_state.search_results.copy()
            
            # Aplicar filtro de status
            if status_filter:
                filtered_results = filtered_results[filtered_results['Status'].isin(status_filter)]
            
            # Aplicar filtro de texto
            if search_text:
                text_mask = filtered_results.apply(
                    lambda row: any(search_text.lower() in str(val).lower() for val in row.values),
                    axis=1
                )
                filtered_results = filtered_results[text_mask]
            
            # Botões para selecionar/desmarcar todos (em único nível)
            if st.button("Selecionar Todos"):
                for i, row in filtered_results.iterrows():
                    pl_id = row['ID']
                    st.session_state.selected_pl_ids.add(pl_id)
                    if pl_id not in st.session_state.analysis_pls:
                        st.session_state.analysis_pls.append(pl_id)
            
            if st.button("Desmarcar Todos"):
                for i, row in filtered_results.iterrows():
                    pl_id = row['ID']
                    if pl_id in st.session_state.selected_pl_ids:
                        st.session_state.selected_pl_ids.remove(pl_id)
                    if pl_id in st.session_state.analysis_pls:
                        st.session_state.analysis_pls.remove(pl_id)
            
            # Mostrar resultados em lista sem aninhamento excessivo
            for i, row in filtered_results.iterrows():
                # Verificar se este PL já está selecionado para análise
                pl_id = row['ID']
                is_selected = pl_id in st.session_state.analysis_pls
                
                # Container para cada PL (não dentro de colunas)
                with st.container():
                    # Checkbox para selecionar (em nível base)
                    selected = st.checkbox(
                        f"Selecionar {pl_id}",
                        value=is_selected,
                        key=f"select_{pl_id}",
                        label_visibility="collapsed"
                    )
                    
                    # Atualizar lista de PLs selecionados
                    if selected and pl_id not in st.session_state.analysis_pls:
                        st.session_state.analysis_pls.append(pl_id)
                        st.session_state.selected_pl_ids.add(pl_id)
                    elif not selected and pl_id in st.session_state.analysis_pls:
                        st.session_state.analysis_pls.remove(pl_id)
                        if pl_id in st.session_state.selected_pl_ids:
                            st.session_state.selected_pl_ids.remove(pl_id)
                    
                    # Expander para detalhes (em nível base)
                    with st.expander(f"{pl_id} - {row['Título']}", expanded=False):
                        # Informações básicas (sem colunas aninhadas)
                        st.write("**Informações básicas:**")
                        if 'Data' in row and row['Data']:
                            st.write(f"**Data:** {row['Data']}")
                        if 'Status' in row and row['Status']:
                            st.write(f"**Status:** {row['Status']}")
                        if 'Autor' in row and row['Autor']:
                            st.write(f"**Autor:** {row['Autor']}")
                        if 'Fonte' in row and row['Fonte']:
                            st.write(f"**Fonte:** {row['Fonte']}")
                        
                        st.write("**Conteúdo:**")
                        if 'Palavras-chave' in row and row['Palavras-chave']:
                            st.write("**Palavras-chave no texto:**")
                            st.caption(row['Palavras-chave'])
                        
                        if 'Palavras-chave Correspondidas' in row and row['Palavras-chave Correspondidas']:
                            st.write("**Termos de busca correspondidos:**")
                            st.caption(row['Palavras-chave Correspondidas'])
                        
                        # Link para texto completo
                        if 'URL' in row and row['URL']:
                            st.write(f"**Texto Completo:** [Acessar]({row['URL']})")
                        
                        # Ementa/Resumo com mais destaque
                        st.write("**Ementa:**")
                        st.info(row['Título'])
                        
                        # Botões de ação (em nível base, sem aninhamento)
                        st.write("**Ações:**")
                        
                        # Ver detalhes
                        detail_btn = st.button(
                            "Ver detalhes completos", 
                            key=f"detail_{pl_id}"
                        )
                        
                        if detail_btn:
                            # Obter detalhes do PL
                            try:
                                partes_id = pl_id.split()
                                sigla = partes_id[0]
                                num_ano = partes_id[1].split('/')
                                numero = num_ano[0]
                                ano = num_ano[1]
                                
                                with st.spinner("Carregando detalhes..."):
                                    collector = SenadoCollector()
                                    pl_details = collector.get_pl_by_id(sigla, numero, ano)
                                    if pl_details:
                                        st.session_state.current_pl_details = pl_details
                            except Exception as e:
                                logger.error(f"Erro ao processar ID do PL: {str(e)}")
                                st.error(f"Erro ao processar ID: {pl_id}")
                                
                        # Exportar
                        st.button(
                            "Exportar Resumo", 
                            key=f"export_{pl_id}"
                        )
                
                # Adicionar uma linha divisória entre os itens
                st.markdown("---")
            
            # Mostrar paginação se houver muitos resultados
            result_count = len(filtered_results)
            if result_count > 10:
                st.write(f"Exibindo {result_count} resultados")
                
            # Botão para limpar seleção
            if st.session_state.analysis_pls:
                if st.button("Limpar Seleção", key="clear_selection"):
                    st.session_state.analysis_pls = []
                    st.session_state.selected_pl_ids = set()
                    st.rerun()
    else:
        # Mensagem inicial
        st.info(
            "Configure os termos de busca e clique em 'Buscar PLs' para iniciar o monitoramento. "
            "Os resultados aparecerão aqui."
        )

    # Exibir detalhes do PL quando selecionado
    if "current_pl_details" in st.session_state and st.session_state.current_pl_details:
        _render_pl_details()

    # Gerenciador de palavras-chave
    if "show_keyword_manager" in st.session_state and st.session_state.show_keyword_manager:
        _render_keyword_manager()

def _render_pl_details():
    """
    Renderiza os detalhes de um PL específico.
    Método separado para evitar aninhamento excessivo.
    """
    st.markdown("---")
    st.write("### Detalhes do Projeto de Lei")
    
    pl = st.session_state.current_pl_details
    
    # Título e cabeçalho
    st.write(f"### {pl['ID']}")
    st.write(f"**{pl['Título']}**")
    
    # Utilizar abas para organização (sem aninhamento de colunas)
    tab1, tab2 = st.tabs(["Informações Gerais", "Tramitação"])
    
    with tab1:
        st.write(f"**Data de Apresentação:** {pl['Data']}")
        st.write(f"**Autor:** {pl['Autor']}")
        st.write(f"**Status Atual:** {pl['Status']}")
        
        st.write("**Palavras-chave/Indexação:**")
        st.write(pl.get('Palavras-chave', 'Não disponível'))
        
        if 'URL' in pl and pl['URL']:
            st.write(f"**Texto Integral:** [Acessar]({pl['URL']})")
    
    with tab2:
        # Tramitação se disponível
        if 'Tramitação' in pl and pl['Tramitação']:
            # Exibe tramitação em formato de tabela
            tramitacao_df = pd.DataFrame(pl['Tramitação'])
            tramitacao_df.columns = ["Data", "Situação", "Local", "Texto"]
            st.dataframe(tramitacao_df, use_container_width=True)
        else:
            st.info("Informações de tramitação não disponíveis.")
    
    # Botões de ação (em nível base, sem aninhamento)
    st.write("**Ações:**")
    
    # Botão para adicionar à análise
    pl_id = pl['ID']
    if pl_id not in st.session_state.analysis_pls:
        if st.button("Adicionar à Análise de Impacto"):
            st.session_state.analysis_pls.append(pl_id)
            st.session_state.selected_pl_ids.add(pl_id)
            st.success(f"PL adicionado para análise de impacto.")
    else:
        if st.button("Remover da Análise de Impacto"):
            st.session_state.analysis_pls.remove(pl_id)
            if pl_id in st.session_state.selected_pl_ids:
                st.session_state.selected_pl_ids.remove(pl_id)
            st.info(f"PL removido da análise de impacto.")
    
    # Botão para exportar
    st.button("Exportar Detalhes")
    
    # Botão para fechar
    if st.button("Fechar Detalhes"):
        st.session_state.current_pl_details = None
        st.rerun()

def _render_keyword_manager():
    """
    Renderiza o gerenciador de palavras-chave.
    Método separado para evitar aninhamento excessivo.
    """
    st.markdown("---")
    st.write(f"### Gerenciamento de Palavras-chave")
    
    # Inicializa o gerenciador de palavras-chave
    keyword_manager = KeywordManager()
    
    # Duas abas sem aninhamento excessivo
    tab1, tab2 = st.tabs(["Adicionar Palavra-chave", "Gerenciar Existentes"])
    
    with tab1:
        # Formulário para adicionar nova palavra-chave
        with st.form("add_keyword_form", clear_on_submit=True):
            st.write(f"**Adicionar palavra-chave ao setor: {st.session_state.monitor_sector}**")
            
            new_keyword = st.text_input("Palavra-chave", placeholder="Ex: apostas esportivas")
            keyword_type = st.selectbox(
                "Tipo",
                options=["term", "reference"],
                index=0,
                help="term = termo genérico, reference = referência específica a lei/normativo"
            )
            is_enabled = st.checkbox("Habilitado", value=True)
            description = st.text_area(
                "Descrição (opcional)", 
                placeholder="Explique o significado ou relevância desta palavra-chave"
            )
            
            submit = st.form_submit_button("Adicionar", use_container_width=True)
            
            if submit and new_keyword:
                success = keyword_manager.add_keyword(
                    sector=st.session_state.monitor_sector,
                    keyword=new_keyword,
                    keyword_type=keyword_type,
                    enabled=is_enabled,
                    description=description
                )
                
                if success:
                    st.success(f"Palavra-chave '{new_keyword}' adicionada com sucesso!")
                else:
                    st.error("Erro ao adicionar palavra-chave. Talvez ela já exista.")
    
    with tab2:
        keywords_df = keyword_manager.get_keywords(sector=st.session_state.monitor_sector, enabled_only=False)
        
        if not keywords_df.empty:
            # Agrupa por tipo
            for keyword_type in sorted(keywords_df['type'].unique()):
                st.write(f"#### {keyword_type.capitalize()}")
                
                # Filtra palavra-chave por tipo
                type_keywords = keywords_df[keywords_df['type'] == keyword_type]
                
                for i, row in type_keywords.iterrows():
                    # Container sem aninhamento de colunas
                    with st.container():
                        st.write(f"**{row['keyword']}**")
                        if row['description']:
                            st.caption(row['description'])
                        
                        # Status ativo/inativo
                        enabled = st.checkbox(
                            "Ativo", 
                            value=row['enabled'],
                            key=f"enable_{row['keyword']}"
                        )
                        
                        # Atualizar status se alterado
                        if enabled != row['enabled']:
                            try:
                                # Use toggle_keyword em vez de update_keyword_status
                                keyword_manager.toggle_keyword(
                                    st.session_state.monitor_sector, 
                                    row['keyword']
                                )
                            except Exception as e:
                                st.error(f"Erro ao alterar status: {str(e)}")
                        
                        # Botão para remover
                        if st.button("Remover", key=f"remove_{row['keyword']}"):
                            if keyword_manager.remove_keyword(
                                st.session_state.monitor_sector, 
                                row['keyword']
                            ):
                                st.success(f"Palavra-chave '{row['keyword']}' removida.")
                                st.rerun()
                            else:
                                st.error("Erro ao remover palavra-chave.")
                        
                        # Linha divisória
                        st.markdown("---")
        else:
            st.info(f"Nenhuma palavra-chave configurada para o setor {st.session_state.monitor_sector}.")
    
    # Botão para fechar o gerenciador
    if st.button("Fechar Gerenciador", use_container_width=True):
        st.session_state.show_keyword_manager = False
        st.rerun()

def _save_search_results(results_df):
    """
    Salva os resultados da busca para o cliente atual.
    
    Args:
        results_df: DataFrame com os resultados
    """
    if not st.session_state.client_id:
        return
    
    try:
        # Diretório para dados do cliente
        client_dir = os.path.join(os.getcwd(), "data", "clients", st.session_state.client_id)
        os.makedirs(client_dir, exist_ok=True)
        
        # Diretório de buscas
        searches_dir = os.path.join(client_dir, "searches")
        os.makedirs(searches_dir, exist_ok=True)
        
        # Nome do arquivo com timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = os.path.join(searches_dir, f"search_{timestamp}.csv")
        
        # Salva o DataFrame
        results_df.to_csv(file_path, index=False)
        
        logger.info(f"Resultados de busca salvos em {file_path}")
        
        # Salva também o último resultado para fácil acesso
        last_result_path = os.path.join(client_dir, "last_search_results.csv")
        results_df.to_csv(last_result_path, index=False)
    except Exception as e:
        logger.error(f"Erro ao salvar resultados de busca: {str(e)}")