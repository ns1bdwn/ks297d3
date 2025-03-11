# src/ui/predefined_pls_view.py
"""
Interface simplificada para exibir e trabalhar com PLs pré-definidos.
Foco na análise de impacto regulatório.
"""
import streamlit as st
import pandas as pd
import os
import sys
from datetime import datetime
import logging
import json

# Adicionar o diretório raiz ao path para importações relativas
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.intelligence.utils.predefined_pls import PredefinedPLManager

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("predefined_pls_view")

def render_predefined_pls_view():
    """
    Renderiza a interface para trabalhar com PLs pré-definidos.
    """
    st.write("### Projetos de Lei Monitorados")
    st.write("Lista de PLs importantes para análise de impacto regulatório.")
    
    # Inicializar gerenciador de PLs
    pl_manager = PredefinedPLManager()
    
    # Inicializar variáveis de sessão
    if "selected_pls" not in st.session_state:
        st.session_state.selected_pls = []
    
    if "current_pl_details" not in st.session_state:
        st.session_state.current_pl_details = None
    
    # Botões de ação
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Atualizar Dados", use_container_width=True):
            with st.spinner("Atualizando dados dos PLs..."):
                # Forçar atualização dos detalhes de todos os PLs
                pl_manager.fetch_pl_details(force_refresh=True)
                st.success("Dados atualizados com sucesso!")
    
    with col2:
        if st.button("Adicionar Novo PL", use_container_width=True):
            st.session_state.show_add_pl_form = True
    
    with col3:
        if st.button("Ver Selecionados para Análise", use_container_width=True):
            if not st.session_state.selected_pls:
                st.warning("Nenhum PL selecionado. Por favor, selecione PLs na lista abaixo.")
            else:
                st.session_state.analysis_pls = st.session_state.selected_pls
                # Redirecionar para a aba de análise de impacto
                st.session_state.menu_option = "Análise de Impacto"
                st.rerun()
    
    # Formulário para adicionar novo PL
    if st.session_state.get("show_add_pl_form", False):
        with st.form("add_pl_form", clear_on_submit=True):
            st.write("#### Adicionar Novo PL")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                sigla = st.selectbox(
                    "Tipo",
                    options=["PL", "PEC", "PLP", "PDL", "PDS", "MPV"],
                    index=0
                )
            
            with col2:
                numero = st.text_input("Número", placeholder="Ex: 1234")
            
            with col3:
                ano = st.text_input("Ano", placeholder="Ex: 2023")
            
            notes = st.text_area("Notas", placeholder="Informações importantes sobre este PL")
            
            col1, col2 = st.columns(2)
            
            with col1:
                priority = st.selectbox(
                    "Prioridade",
                    options=["Alta", "Media", "Baixa"],
                    index=1
                )
            
            with col2:
                categories = st.multiselect(
                    "Categorias",
                    options=["Tributário", "Regulatório", "Operacional", "Compliance", "Tecnologia"],
                    default=["Regulatório"]
                )
            
            submit = st.form_submit_button("Adicionar PL", use_container_width=True)
            
            if submit:
                if not numero or not ano:
                    st.error("Número e Ano são obrigatórios.")
                else:
                    # Primeiro tentamos adicionar normalmente
                    success = pl_manager.add_pl(
                        sigla=sigla,
                        numero=numero,
                        ano=ano,
                        notes=notes,
                        priority=priority,
                        categories=categories
                    )
                    
                    # Se falhou, pode ser porque o PL não existe no SenadoCollector
                    if not success:
                        # Perguntamos se o usuário quer adicionar manualmente
                        st.warning(f"PL {sigla} {numero}/{ano} não encontrado na base de dados.")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("Adicionar Manualmente", key="add_manual"):
                                # Adicionar detalhes personalizados e forçar adição
                                custom_details = {
                                    "Título": f"PL {numero}/{ano} - Personalizado",
                                    "Data": datetime.now().strftime("%Y-%m-%d"),
                                    "Autor": "Usuário",
                                    "Status": "Personalizado",
                                    "URL": "",
                                    "Palavras-chave": ",".join(categories) if categories else ""
                                }
                                
                                success = pl_manager.add_pl(
                                    sigla=sigla,
                                    numero=numero,
                                    ano=ano,
                                    notes=notes,
                                    priority=priority,
                                    categories=categories,
                                    custom_details=custom_details,
                                    force_add=True
                                )
                                
                                if success:
                                    st.success(f"PL {sigla} {numero}/{ano} adicionado manualmente com sucesso!")
                                    st.session_state.show_add_pl_form = False
                                    # Buscar detalhes do novo PL
                                    pl_id = f"{sigla} {numero}/{ano}"
                                    pl_manager.fetch_pl_details(pl_id=pl_id)
                                    st.rerun()
                                else:
                                    st.error("Erro ao adicionar PL manualmente.")
                        with col2:
                            if st.button("Cancelar", key="cancel_add"):
                                st.session_state.show_add_pl_form = False
                                st.rerun()
                    else:
                        st.success(f"PL {sigla} {numero}/{ano} adicionado com sucesso!")
                        st.session_state.show_add_pl_form = False
                        # Buscar detalhes do novo PL
                        pl_id = f"{sigla} {numero}/{ano}"
                        pl_manager.fetch_pl_details(pl_id=pl_id)
                        st.rerun()
    
    # Obter dados dos PLs e exibir em uma tabela
    with st.spinner("Carregando dados dos PLs..."):
        pl_details_df = pl_manager.get_pl_details_dataframe()
    
    if pl_details_df.empty:
        st.info("Nenhum dado disponível. Clique em 'Atualizar Dados' para buscar informações dos PLs.")
    else:
        # Filtros
        st.write("#### Filtros")
        col1, col2 = st.columns(2)
        
        with col1:
            # Filtro por prioridade
            priority_filter = st.multiselect(
                "Filtrar por prioridade",
                options=["Alta", "Media", "Baixa"],
                default=[]
            )
        
        with col2:
            # Filtro por texto
            search_text = st.text_input("Pesquisar", placeholder="Digite para filtrar")
        
        # Aplicar filtros
        filtered_df = pl_details_df
        
        if priority_filter:
            filtered_df = filtered_df[filtered_df['Prioridade'].isin(priority_filter)]
        
        if search_text:
            # Filtrar por texto em qualquer coluna
            mask = filtered_df.astype(str).apply(
                lambda row: row.str.contains(search_text, case=False).any(),
                axis=1
            )
            filtered_df = filtered_df[mask]
        
        # Exibir tabela de PLs
        st.write(f"#### PLs Monitorados ({len(filtered_df)})")
        
        # Exibir lista de PLs com checkbox para seleção
        for i, row in filtered_df.iterrows():
            pl_id = row['ID']
            
            # Container para cada PL
            with st.container():
                col1, col2 = st.columns([1, 10])
                
                with col1:
                    # Checkbox para seleção
                    is_selected = pl_id in st.session_state.selected_pls
                    selected = st.checkbox(
                        "Selecionar",
                        value=is_selected,
                        key=f"select_{pl_id}",
                        label_visibility="collapsed"
                    )
                    
                    # Atualizar lista de PLs selecionados
                    if selected and pl_id not in st.session_state.selected_pls:
                        st.session_state.selected_pls.append(pl_id)
                    elif not selected and pl_id in st.session_state.selected_pls:
                        st.session_state.selected_pls.remove(pl_id)
                
                with col2:
                    # Expander com detalhes do PL
                    with st.expander(f"{pl_id} - {row['Título'][:100]}...", expanded=False):
                        # Detalhes em colunas
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**Data:** {row.get('Data', 'N/A')}")
                            st.write(f"**Autor:** {row.get('Autor', 'N/A')}")
                            st.write(f"**Status:** {row.get('Status', 'N/A')}")
                            st.write(f"**Prioridade:** {row.get('Prioridade', 'Media')}")
                        
                        with col2:
                            st.write(f"**Categorias:** {row.get('Categorias', 'N/A')}")
                            if 'Notas' in row and row['Notas']:
                                st.write(f"**Notas:** {row['Notas']}")
                            if 'URL' in row and row['URL']:
                                st.write(f"**Texto Completo:** [Acessar]({row['URL']})")
                        
                        # Ementa/Título completo
                        st.write("**Ementa:**")
                        st.info(row['Título'])
                        
                        # Ações para este PL
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            if st.button("Editar Notas", key=f"edit_{pl_id}", use_container_width=True):
                                st.session_state.editing_pl = pl_id
                                st.session_state.editing_notes = row.get('Notas', '')
                                st.session_state.editing_priority = row.get('Prioridade', 'Media')
                                st.session_state.editing_categories = row.get('Categorias', '').split(', ') if isinstance(row.get('Categorias', ''), str) else []
                        
                        with col2:
                            if st.button("Analisar Impacto", key=f"analyze_{pl_id}", use_container_width=True):
                                if pl_id not in st.session_state.selected_pls:
                                    st.session_state.selected_pls.append(pl_id)
                                st.session_state.analysis_pls = [pl_id]
                                # Redirecionar para a aba de análise de impacto
                                st.session_state.menu_option = "Análise de Impacto"
                                st.rerun()
                        
                        with col3:
                            if st.button("Remover", key=f"remove_{pl_id}", use_container_width=True):
                                if pl_manager.remove_pl(pl_id):
                                    if pl_id in st.session_state.selected_pls:
                                        st.session_state.selected_pls.remove(pl_id)
                                    st.success(f"PL {pl_id} removido com sucesso!")
                                    st.rerun()
                                else:
                                    st.error(f"Erro ao remover PL {pl_id}.")
                
                # Linha divisória entre PLs
                st.markdown("---")
    
    # Formulário para editar PL
    if hasattr(st.session_state, 'editing_pl'):
        pl_id = st.session_state.editing_pl
        with st.form(f"edit_pl_form_{pl_id}"):
            st.write(f"#### Editar PL {pl_id}")
            
            # Buscar detalhes do PL para permitir edição mais completa
            pl_parts = pl_id.split(" ")
            sigla = pl_parts[0]
            numero_ano = pl_parts[1].split("/")
            numero = numero_ano[0]
            ano = numero_ano[1]
            
            # Verificar se é um PL personalizado
            pls_dict = pl_manager.get_all_pls()
            is_custom = False
            if pl_id in pls_dict:
                is_custom = pls_dict[pl_id].get("is_custom", False)
            
            # Se for um PL personalizado, mostrar mais campos para edição
            if is_custom:
                # Obter detalhes atuais
                pl_details = {}
                try:
                    # Buscar detalhes do cache
                    cache_file = os.path.join(os.getcwd(), "data", "predefined_pls", f"{sigla}_{numero}_{ano}_details.json")
                    if os.path.exists(cache_file):
                        with open(cache_file, 'r', encoding='utf-8') as f:
                            pl_details = json.load(f)
                except Exception as e:
                    logger.error(f"Erro ao carregar detalhes do PL {pl_id}: {str(e)}")
                
                st.write("**Detalhes Personalizados**")
                
                titulo = st.text_area(
                    "Título/Ementa",
                    value=pl_details.get("Título", f"[Personalizado] {pl_id}"),
                    height=100
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    autor = st.text_input(
                        "Autor",
                        value=pl_details.get("Autor", "Usuário")
                    )
                with col2:
                    status = st.text_input(
                        "Status",
                        value=pl_details.get("Status", "Personalizado")
                    )
                
                url = st.text_input(
                    "URL (opcional)",
                    value=pl_details.get("URL", "")
                )
                
                keywords = st.text_input(
                    "Palavras-chave (separadas por vírgula)",
                    value=pl_details.get("Palavras-chave", "")
                )
            
            # Notas
            notes = st.text_area(
                "Notas",
                value=st.session_state.editing_notes,
                placeholder="Informações importantes sobre este PL"
            )
            
            # Prioridade e categorias
            col1, col2 = st.columns(2)
            
            with col1:
                priority = st.selectbox(
                    "Prioridade",
                    options=["Alta", "Media", "Baixa"],
                    index=["Alta", "Media", "Baixa"].index(st.session_state.editing_priority) if st.session_state.editing_priority in ["Alta", "Media", "Baixa"] else 1
                )
            
            with col2:
                categories = st.multiselect(
                    "Categorias",
                    options=["Tributário", "Regulatório", "Operacional", "Compliance", "Tecnologia"],
                    default=st.session_state.editing_categories
                )
            
            # Botões
            col1, col2 = st.columns(2)
            
            with col1:
                cancel = st.form_submit_button("Cancelar", use_container_width=True)
            
            with col2:
                save = st.form_submit_button("Salvar", use_container_width=True)
            
            if save:
                # Atualizar notas, prioridade e categorias
                success = pl_manager.update_pl(pl_id, notes=notes, priority=priority, categories=categories)
                
                # Se for um PL personalizado, atualizar detalhes estendidos
                if is_custom and success:
                    try:
                        # Atualizar detalhes no cache
                        custom_details = {
                            "Título": titulo,
                            "Autor": autor,
                            "Status": status,
                            "URL": url,
                            "Palavras-chave": keywords,
                            "Data": pl_details.get("Data", datetime.now().strftime("%Y-%m-%d"))
                        }
                        
                        # Salvar no cache
                        cache_file = os.path.join(os.getcwd(), "data", "predefined_pls", f"{sigla}_{numero}_{ano}_details.json")
                        with open(cache_file, 'w', encoding='utf-8') as f:
                            json.dump(custom_details, f, ensure_ascii=False, indent=4)
                        
                        # Atualizar no CSV
                        from src.intelligence.collectors.senado_collector import SenadoCollector
                        collector = SenadoCollector()
                        
                        # Remover o PL atual do CSV (abordagem simplificada)
                        df = pd.read_csv(collector.csv_path, encoding='utf-8')
                        df = df[~((df['Sigla'] == sigla) & (df['Numero'] == numero) & (df['Ano'] == ano))]
                        df.to_csv(collector.csv_path, index=False, encoding='utf-8')
                        
                        # Adicionar o PL atualizado
                        collector.add_pl_to_csv(sigla, numero, ano, custom_details)
                        
                        st.success(f"Detalhes personalizados do PL {pl_id} atualizados com sucesso!")
                    except Exception as e:
                        st.error(f"Erro ao atualizar detalhes personalizados: {str(e)}")
                        logger.error(f"Erro ao atualizar detalhes personalizados do PL {pl_id}: {str(e)}")
                
                if success:
                    st.success(f"PL {pl_id} atualizado com sucesso!")
                    # Remover variáveis de edição
                    del st.session_state.editing_pl
                    del st.session_state.editing_notes
                    del st.session_state.editing_priority
                    del st.session_state.editing_categories
                    st.rerun()
                else:
                    st.error(f"Erro ao atualizar PL {pl_id}.")
            
            if cancel:
                # Remover variáveis de edição
                del st.session_state.editing_pl
                del st.session_state.editing_notes
                del st.session_state.editing_priority
                del st.session_state.editing_categories
                st.rerun()