# src/ui/app.py
"""
Aplicação principal do Regulatory Suite usando Streamlit.
Versão com foco em avaliação de maturidade regulatória e análise de impacto de PLs pré-definidos.
"""
import streamlit as st
import pandas as pd
import os
import sys
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime

# Adicionar o diretório raiz ao path para importações relativas
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Importar componentes da aplicação
from src.ui.predefined_pls_view import render_predefined_pls_view
from src.ui.impact_analysis_view import render_impact_analysis_view
from src.maturity.assessment import MaturityAssessment

# Configuração da página
st.set_page_config(
    page_title="Regulatory Suite",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS
st.markdown("""
<style>
    .main {
        padding: 1rem 1rem;
    }
    h1, h2, h3 {
        color: #366092;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f0f2f6;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #366092;
        color: white;
    }
    .dashboard-metrics {
        background-color: #f2f2f2;
        padding: 20px;
        border-radius: 5px;
        margin-bottom: 20px;
    }
    .metric-value {
        font-size: 36px;
        font-weight: bold;
        color: #366092;
    }
</style>
""", unsafe_allow_html=True)

# Estado da sessão para cliente
if "client_id" not in st.session_state:
    st.session_state.client_id = None

# Estado da sessão para menu
if "menu_option" not in st.session_state:
    st.session_state.menu_option = "Dashboard"

# Estado da sessão para avaliação
if "assessment_data" not in st.session_state:
    st.session_state.assessment_data = {}
if "evidence_data" not in st.session_state:
    st.session_state.evidence_data = {}

# Estado para PLs selecionados para análise
if "analysis_pls" not in st.session_state:
    st.session_state.analysis_pls = []

# Sidebar para seleção/criação de cliente
st.sidebar.title("🏢 Cliente")

# Certifique-se de que o diretório clients existe
clients_dir = os.path.join(os.getcwd(), "data", "clients")
os.makedirs(clients_dir, exist_ok=True)

# Listar clientes existentes
client_dirs = [d for d in os.listdir(clients_dir) 
               if os.path.isdir(os.path.join(clients_dir, d))]

client_option = st.sidebar.selectbox(
    "Selecione ou crie um cliente:",
    ["Criar Novo Cliente"] + client_dirs,
    index=0 if not st.session_state.client_id else 
          client_dirs.index(st.session_state.client_id) + 1 if st.session_state.client_id in client_dirs else 0
)

# Lista de clientes existentes ou opção para criar novo
if client_option == "Criar Novo Cliente":
    new_client_name = st.sidebar.text_input("Nome do Novo Cliente:")
    if st.sidebar.button("Criar Cliente") and new_client_name:
        # Criar ID do cliente (slugify do nome)
        client_id = new_client_name.lower().replace(" ", "_")
        # Atualizar estado da sessão
        st.session_state.client_id = client_id
        # Criar diretório do cliente
        client_dir = os.path.join(clients_dir, client_id)
        os.makedirs(client_dir, exist_ok=True)
        # Recarregar a página
        st.rerun()
else:
    st.session_state.client_id = client_option

# Menu principal com todas as opções (foco novo)
st.sidebar.title("📋 Menu")
menu_options = ["Dashboard", "Avaliação de Maturidade", "PLs Monitorados", "Análise de Impacto", "Configurações"]
menu_option = st.sidebar.radio(
    "Selecione uma opção:",
    menu_options,
    index=menu_options.index(st.session_state.menu_option) if st.session_state.menu_option in menu_options else 0
)

# Atualizar opção de menu na sessão
st.session_state.menu_option = menu_option

# Título da página
st.title(f"Regulatory Suite - {menu_option}")

# Conteúdo principal baseado na opção do menu
if menu_option == "Dashboard":
    st.header("📊 Dashboard de Maturidade Regulatória")
    
    if not st.session_state.client_id:
        st.info("Selecione ou crie um cliente para visualizar o dashboard.")
    else:
        try:
            # Tenta carregar a última avaliação
            last_assessment_file = os.path.join(clients_dir, st.session_state.client_id, "assessment.csv")
            if os.path.exists(last_assessment_file):
                assessment_df = pd.read_csv(last_assessment_file)
                
                # Exibir métricas principais
                st.subheader("Visão Geral")
                col1, col2, col3 = st.columns(3)
                
                # Calcular score médio
                if 'response' in assessment_df.columns:
                    avg_score = assessment_df['response'].mean()
                    
                    with col1:
                        st.markdown(f'<div class="dashboard-metrics">'
                                    f'<div class="metric-value">{avg_score:.1f}</div>'
                                    f'<div class="metric-label">Score Geral</div>'
                                    f'</div>', unsafe_allow_html=True)
                    
                    # Determinar nível de maturidade
                    maturity_level = "Inicial"
                    if avg_score > 1.5:
                        maturity_level = "Básico"
                    if avg_score > 2.5:
                        maturity_level = "Estabelecido"
                    if avg_score > 3.5:
                        maturity_level = "Gerenciado"
                    if avg_score > 4.5:
                        maturity_level = "Otimizado"
                    
                    with col2:
                        st.markdown(f'<div class="dashboard-metrics">'
                                    f'<div class="metric-value">{maturity_level}</div>'
                                    f'<div class="metric-label">Nível de Maturidade</div>'
                                    f'</div>', unsafe_allow_html=True)
                
                # Contador de PLs para análise
                num_pls = len(st.session_state.analysis_pls) if hasattr(st.session_state, 'analysis_pls') else 0
                
                with col3:
                    st.markdown(f'<div class="dashboard-metrics">'
                                f'<div class="metric-value">{num_pls}</div>'
                                f'<div class="metric-label">PLs para Análise</div>'
                                f'</div>', unsafe_allow_html=True)
                
                # Gráficos principais
                st.subheader("Análise Detalhada")
                col1, col2 = st.columns(2)
                
                if 'framework' in assessment_df.columns and 'response' in assessment_df.columns:
                    with col1:
                        st.write("#### Maturidade por Framework")
                        # Calcular scores médios por framework
                        framework_scores = assessment_df.groupby('framework')['response'].mean().reset_index()
                        
                        fig, ax = plt.subplots(figsize=(8, 6))
                        bars = ax.bar(framework_scores['framework'], framework_scores['response'],
                                      color=['#366092', '#70AD47', '#ED7D31', '#4472C4'])
                        ax.set_ylim(0, 5)
                        ax.set_xlabel('Framework')
                        ax.set_ylabel('Score (1-5)')
                        ax.spines['top'].set_visible(False)
                        ax.spines['right'].set_visible(False)
                        
                        # Adicionar valores sobre as barras
                        for bar in bars:
                            height = bar.get_height()
                            ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                                    f'{height:.1f}', ha='center', va='bottom')
                        
                        st.pyplot(fig)
                
                if 'dimension' in assessment_df.columns and 'response' in assessment_df.columns:
                    with col2:
                        st.write("#### Maturidade por Dimensão")
                        # Calcular scores médios por dimensão
                        dimension_scores = assessment_df.groupby('dimension')['response'].mean().reset_index()
                        
                        # Gráfico de radar
                        fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
                        
                        # Dados para o gráfico
                        dimensions = dimension_scores['dimension'].tolist()
                        scores = dimension_scores['response'].tolist()
                        
                        # Número de variáveis
                        N = len(dimensions)
                        
                        # Ângulos para cada eixo (igualmente espaçados)
                        angles = [n / float(N) * 2 * np.pi for n in range(N)]
                        angles += angles[:1]  # Fechar o gráfico
                        
                        # Scores
                        scores_plot = scores + [scores[0]]  # Repetir o primeiro valor para fechar o gráfico
                        
                        # Desenhar linhas de grade
                        ax.set_xticks(angles[:-1])
                        ax.set_xticklabels(dimensions)
                        ax.set_yticks([1, 2, 3, 4, 5])
                        ax.set_ylim(0, 5)
                        
                        # Plotar dados
                        ax.plot(angles, scores_plot, linewidth=2, linestyle='solid', color='#366092')
                        ax.fill(angles, scores_plot, alpha=0.25, color='#366092')
                        
                        st.pyplot(fig)
                
                # Recomendações principais
                st.subheader("Principais Ações Recomendadas")
                
                # Identificar áreas de baixa pontuação
                if 'dimension' in assessment_df.columns and 'response' in assessment_df.columns:
                    low_scores = assessment_df[assessment_df['response'] < 3].groupby('dimension')['response'].mean()
                    if not low_scores.empty:
                        low_dim = low_scores.idxmin()
                        st.warning(f"**Área crítica identificada:** {low_dim}")
                        
                        recommendations = {
                            "Governança": "Estabelecer comitê formal para gestão de riscos regulatórios",
                            "Cultura": "Implementar programa de conscientização sobre riscos regulatórios",
                            "Estratégia": "Integrar riscos regulatórios ao planejamento estratégico",
                            "Riscos": "Desenvolver matriz de riscos regulatórios específica",
                            "Compliance": "Implementar sistema de monitoramento contínuo de compliance",
                            "Advocacy": "Estabelecer processos formais para participação em consultas públicas",
                            "Tecnologia": "Implementar ferramentas para monitoramento automático de PLs"
                        }
                        
                        if low_dim in recommendations:
                            st.info(f"**Recomendação prioritária:** {recommendations[low_dim]}")
                    else:
                        st.success("Não foram identificadas áreas críticas. Continue com as boas práticas atuais.")
            else:
                st.warning("Nenhuma avaliação de maturidade encontrada para este cliente. Realize uma avaliação primeiro.")
                if st.button("Iniciar Avaliação de Maturidade"):
                    st.session_state.menu_option = "Avaliação de Maturidade"
                    st.rerun()
        except Exception as e:
            st.error(f"Erro ao carregar dados para o dashboard: {str(e)}")
            st.info("Tente criar uma avaliação primeiro.")

elif menu_option == "Avaliação de Maturidade":
    st.header("📝 Avaliação de Maturidade Regulatória")
    
    if not st.session_state.client_id:
        st.info("Selecione ou crie um cliente para iniciar a avaliação.")
    else:
        try:
            # Inicialização do objeto de avaliação
            assessment = MaturityAssessment()
            
            # Verificar se há avaliação existente para carregar
            assessment_file = os.path.join(clients_dir, st.session_state.client_id, "assessment.csv")
            if os.path.exists(assessment_file) and (not st.session_state.assessment_data or st.button("Carregar Última Avaliação")):
                existing_assessment = pd.read_csv(assessment_file)
                # Converter DataFrame para dicionários para facilitar o uso
                if 'id' in existing_assessment.columns and 'response' in existing_assessment.columns:
                    st.session_state.assessment_data = existing_assessment.set_index('id')['response'].to_dict()
                if 'id' in existing_assessment.columns and 'evidence' in existing_assessment.columns:
                    st.session_state.evidence_data = existing_assessment.set_index('id')['evidence'].to_dict()
                st.success("Avaliação existente carregada com sucesso!")
            
            # Abas para diferentes partes da avaliação
            tab1, tab2, tab3 = st.tabs(["Questionário", "Evidências", "Resultados"])
            
            with tab1:
                st.subheader("Questionário de Maturidade")
                st.write("Responda às perguntas abaixo para avaliar a maturidade regulatória.")
                
                # Agrupar perguntas por framework para melhor organização
                frameworks = sorted(set(q["framework"] for q in assessment.questions))
                
                for framework in frameworks:
                    st.markdown(f"### {framework}")
                    
                    # Filtrar perguntas deste framework
                    framework_questions = [q for q in assessment.questions if q["framework"] == framework]
                    
                    for q in framework_questions:
                        q_id = q["id"]
                        
                        # Exibir dimensão como badge
                        st.markdown(f"**Dimensão:** `{q['dimension']}`")
                        
                        # Exibir a pergunta
                        st.markdown(f"**{q['question']}**")
                        
                        # Controle deslizante para resposta
                        current_value = st.session_state.assessment_data.get(q_id, 1)
                        response = st.slider(
                            f"Nível de Maturidade ({q_id})",
                            min_value=1,
                            max_value=5,
                            value=int(current_value),
                            key=f"slider_{q_id}",
                            help=f"1: Inicial, 2: Básico, 3: Estabelecido, 4: Gerenciado, 5: Otimizado"
                        )
                        
                        # Atualizar estado da sessão
                        st.session_state.assessment_data[q_id] = response
                        
                        # Mostrar descrição do nível selecionado
                        st.info(f"**Nível {response}:** {assessment.maturity_levels[response]['label']} - {assessment.maturity_levels[response]['desc']}")
                        
                        st.write("---")
                
                # Botão para salvar respostas
                if st.button("Salvar Respostas"):
                    # Preparar dados para salvar
                    data = []
                    for q_id, response in st.session_state.assessment_data.items():
                        q_info = next((q for q in assessment.questions if q["id"] == q_id), None)
                        if q_info:
                            data.append({
                                "id": q_id,
                                "framework": q_info["framework"],
                                "dimension": q_info["dimension"],
                                "question": q_info["question"],
                                "response": response,
                                "evidence": st.session_state.evidence_data.get(q_id, "")
                            })
                    
                    # Criar DataFrame e salvar
                    if data:
                        df = pd.DataFrame(data)
                        os.makedirs(os.path.join(clients_dir, st.session_state.client_id), exist_ok=True)
                        df.to_csv(assessment_file, index=False)
                        st.success(f"Respostas salvas com sucesso!")
            
            with tab2:
                st.subheader("Evidências de Maturidade")
                st.write("Forneça evidências para suportar as respostas do questionário.")
                
                # Agrupar perguntas por framework para melhor organização
                frameworks = sorted(set(q["framework"] for q in assessment.questions))
                
                for framework in frameworks:
                    with st.expander(f"{framework}"):
                        # Filtrar perguntas deste framework
                        framework_questions = [q for q in assessment.questions if q["framework"] == framework]
                        
                        for q in framework_questions:
                            q_id = q["id"]
                            
                            # Obter resposta atual
                            response = st.session_state.assessment_data.get(q_id, 1)
                            
                            # Se a resposta for 3 ou maior, solicitar evidências
                            if response >= 3:
                                st.markdown(f"**{q['question']}** (Nível atual: {response})")
                                
                                # Exemplos de evidências esperadas
                                st.markdown(f"*Exemplos de evidências: {q.get('evidence_examples', 'Documentos, políticas, procedimentos relevantes')}*")
                                
                                # Campo para entrada de evidências
                                current_evidence = st.session_state.evidence_data.get(q_id, "")
                                evidence = st.text_area(
                                    f"Evidências para {q_id}",
                                    value=current_evidence,
                                    height=100,
                                    key=f"evidence_{q_id}",
                                    help="Descreva as evidências que suportam o nível de maturidade indicado"
                                )
                                
                                # Atualizar estado da sessão
                                st.session_state.evidence_data[q_id] = evidence
                                
                                # Aviso se não houver evidências
                                if not evidence:
                                    st.warning("Atenção: Sem evidências, o score será ajustado para 2.5 mesmo com resposta de nível mais alto.")
                                
                                st.write("---")
                
                # Botão para salvar evidências
                if st.button("Salvar Evidências"):
                    # Preparar dados para salvar
                    data = []
                    for q_id, response in st.session_state.assessment_data.items():
                        q_info = next((q for q in assessment.questions if q["id"] == q_id), None)
                        if q_info:
                            data.append({
                                "id": q_id,
                                "framework": q_info["framework"],
                                "dimension": q_info["dimension"],
                                "question": q_info["question"],
                                "response": response,
                                "evidence": st.session_state.evidence_data.get(q_id, "")
                            })
                    
                    # Criar DataFrame e salvar
                    if data:
                        df = pd.DataFrame(data)
                        os.makedirs(os.path.join(clients_dir, st.session_state.client_id), exist_ok=True)
                        df.to_csv(assessment_file, index=False)
                        st.success(f"Evidências salvas com sucesso!")
            
            with tab3:
                st.subheader("Resultados da Avaliação")
                
                # Verifica se há dados para calcular resultados
                if st.session_state.assessment_data:
                    # Calcular scores
                    try:
                        framework_scores, dimension_scores, overall_score = assessment.calculate_scores(
                            st.session_state.assessment_data, st.session_state.evidence_data
                        )
                        
                        # Exibir score geral
                        st.markdown(f"### Score Geral: {overall_score:.2f}/5.0")
                        st.markdown(f"**Nível de Maturidade:** {assessment.get_maturity_level(overall_score)['label']} - {assessment.get_maturity_level(overall_score)['desc']}")
                        
                        # Gráficos de scores
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write("Scores por Framework")
                            
                            # Preparar dados para o gráfico
                            frameworks = list(framework_scores.keys())
                            scores = list(framework_scores.values())
                            
                            fig, ax = plt.subplots(figsize=(8, 6))
                            bars = ax.bar(frameworks, scores, color=['#366092', '#70AD47', '#ED7D31', '#4472C4'])
                            ax.set_ylim(0, 5)
                            ax.set_xlabel('Framework')
                            ax.set_ylabel('Score (1-5)')
                            
                            # Adicionar valores sobre as barras
                            for bar in bars:
                                height = bar.get_height()
                                ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                                        f'{height:.1f}', ha='center', va='bottom')
                            
                            st.pyplot(fig)
                        
                        with col2:
                            st.write("Scores por Dimensão")
                            
                            # Preparar dados para o gráfico
                            dimensions = list(dimension_scores.keys())
                            scores = list(dimension_scores.values())
                            
                            # Gráfico de radar
                            fig, ax = plt.subplots(figsize=(10, 8), subplot_kw=dict(polar=True))
                            
                            # Número de variáveis
                            N = len(dimensions)
                            
                            # Ângulos para cada eixo (igualmente espaçados)
                            angles = [n / float(N) * 2 * np.pi for n in range(N)]
                            angles += angles[:1]  # Fechar o gráfico
                            
                            # Scores
                            scores_plot = scores + [scores[0]]  # Repetir o primeiro valor para fechar o gráfico
                            
                            # Desenhar linhas de grade
                            ax.set_xticks(angles[:-1])
                            ax.set_xticklabels(dimensions)
                            ax.set_yticks([1, 2, 3, 4, 5])
                            ax.set_ylim(0, 5)
                            
                            # Plotar dados
                            ax.plot(angles, scores_plot, linewidth=2, linestyle='solid', color='#366092')
                            ax.fill(angles, scores_plot, alpha=0.25, color='#366092')
                            
                            st.pyplot(fig)
                        
                        # Recomendações
                        st.subheader("Recomendações")
                        
                        # Identificar áreas com score baixo
                        low_scores = {dim: score for dim, score in dimension_scores.items() if score < 3}
                        if low_scores:
                            st.write("**Áreas que precisam de atenção:**")
                            for dim, score in sorted(low_scores.items(), key=lambda x: x[1]):
                                st.warning(f"**{dim}:** Score {score:.1f}/5.0")
                                
                                # Recomendações por dimensão
                                recommendations = {
                                    "Governança": "Estabelecer comitê formal para gestão de riscos regulatórios",
                                    "Cultura": "Implementar programa de conscientização sobre riscos regulatórios",
                                    "Estratégia": "Integrar riscos regulatórios ao planejamento estratégico",
                                    "Riscos": "Desenvolver matriz de riscos regulatórios específica",
                                    "Compliance": "Implementar sistema de monitoramento contínuo de compliance",
                                    "Advocacy": "Estabelecer processos formais para participação em consultas públicas",
                                    "Tecnologia": "Implementar ferramentas para monitoramento automático de PLs"
                                }
                                
                                if dim in recommendations:
                                    st.info(f"**Recomendação:** {recommendations[dim]}")
                        else:
                            st.success("Todas as áreas apresentam níveis satisfatórios de maturidade. Continue com as boas práticas atuais.")
                    except Exception as e:
                        st.error(f"Erro ao calcular resultados: {str(e)}")
                        st.info("Verifique se todas as perguntas foram respondidas.")
                else:
                    st.info("Complete o questionário para visualizar os resultados.")
        except Exception as e:
            st.error(f"Erro ao renderizar a avaliação de maturidade: {str(e)}")
            if os.environ.get("STREAMLIT_ENV") == "development":
                st.exception(e)

elif menu_option == "PLs Monitorados":
    if not st.session_state.client_id:
        st.info("Selecione ou crie um cliente para visualizar os PLs monitorados.")
    else:
        try:
            # Renderiza a visão de PLs pré-definidos
            render_predefined_pls_view()
        except Exception as e:
            st.error(f"Erro ao renderizar a lista de PLs: {str(e)}")
            if os.environ.get("STREAMLIT_ENV") == "development":
                st.exception(e)

elif menu_option == "Análise de Impacto":
    if not st.session_state.client_id:
        st.info("Selecione ou crie um cliente para iniciar a análise de impacto.")
    else:
        try:
            # Renderiza a visão de análise de impacto
            render_impact_analysis_view()
        except Exception as e:
            st.error(f"Erro ao renderizar a análise de impacto: {str(e)}")
            if os.environ.get("STREAMLIT_ENV") == "development":
                st.exception(e)

elif menu_option == "Configurações":
    st.header("⚙️ Configurações")
    
    if not st.session_state.client_id:
        st.info("Selecione ou crie um cliente para acessar as configurações.")
    else:
        # Abas para diferentes configurações
        tab1, tab2 = st.tabs(["Geral", "Avançado"])
        
        with tab1:
            st.write("### Configurações Gerais")
            
            # Configurações de notificação
            st.write("#### Notificações")
            
            email_notif = st.checkbox("Ativar notificações por e-mail", value=True)
            if email_notif:
                st.text_input("E-mail para notificações", value="usuario@exemplo.com")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.checkbox("Notificar sobre novos PLs", value=True)
                    st.checkbox("Notificar sobre alterações em PLs monitorados", value=True)
                with col2:
                    st.checkbox("Notificar sobre consultas públicas", value=False)
                    st.checkbox("Resumo semanal", value=True)
            
            # Preferências de exibição
            st.write("#### Preferências de Exibição")
            
            st.selectbox(
                "Tema da interface",
                options=["Claro", "Escuro", "Sistema"],
                index=0
            )
            
            st.slider(
                "Número de resultados por página",
                min_value=10,
                max_value=100,
                value=25,
                step=5
            )
            
            # Botão para salvar configurações
            if st.button("Salvar Configurações"):
                st.success("Configurações salvas com sucesso!")
                
        with tab2:
            st.write("### Configurações Avançadas")
            
            # Configurações de API
            st.write("#### APIs Externas")
            
            st.checkbox("Habilitar cache de requisições", value=True)
            
            st.slider(
                "Tempo limite para requisições (segundos)",
                min_value=5,
                max_value=60,
                value=30,
                step=5
            )
            
            # Opções de PLs monitorados
            st.write("#### Opções de PLs Monitorados")
            
            st.checkbox("Atualizar automaticamente dados dos PLs", value=False)
            
            st.selectbox(
                "Frequência de atualização",
                options=["Diária", "Semanal", "Mensal"],
                index=1
            )
            
            # Botão para salvar configurações
            if st.button("Salvar Configurações Avançadas"):
                st.success("Configurações avançadas salvas com sucesso!")

# Informações de rodapé
st.markdown("---")
st.markdown(
    f"<div style='text-align: center; color: gray; font-size: 12px;'>"
    f"Regulatory Suite v0.1.0 | Data atual: {datetime.now().strftime('%d/%m/%Y')}</div>",
    unsafe_allow_html=True
)

if __name__ == "__main__":
    # Ponto de entrada da aplicação
    pass