import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime

# --- 1. CONFIGURAÇÃO E CONEXÃO ---
st.set_page_config(page_title="Sistema Obra Pro v1.0", layout="wide", page_icon="🚧")

# Conectando ao Supabase usando Secrets (Configurações Avançadas no Streamlit Cloud)
try:
    url: str = st.secrets["SUPABASE_URL"]
    key: str = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error("Erro de conexão: Verifique as chaves no Supabase/Secrets.")
    st.stop()

# --- 2. SISTEMA DE LOGIN ---
if 'logado' not in st.session_state:
    st.session_state.logado = False

def tela_login():
    st.markdown("<h1 style='text-align: center;'>🔐 Acesso Restrito</h1>", unsafe_allow_html=True)
    with st.container():
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            usuario = st.text_input("Usuário")
            senha = st.text_input("Senha", type="password")
            if st.button("Entrar", type="primary", use_container_width=True):
                # Usuário padrão para teste (Pode ser melhorado depois)
                if usuario == "admin" and senha == "obra2026":
                    st.session_state.logado = True
                    st.session_state.usuario = usuario
                    st.rerun()
                else:
                    st.error("Usuário ou senha inválidos")

if not st.session_state.logado:
    tela_login()
    st.stop()

# --- 3. MENU LATERAL ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/4342/4342728.png", width=100) # Ícone padrão
    st.title("Gestão de Frota")
    st.write(f"👤 Usuário: **{st.session_state.usuario}**")
    st.divider()
    menu = st.radio("Navegação", ["📊 Dashboard", "📝 Lançar Abastecimento", "🚜 Cadastro de Frota", "🔍 Consulta & Histórico"])
    if st.button("Sair"):
        st.session_state.logado = False
        st.rerun()

# --- 4. MÓDULO: DASHBOARD ---
if menu == "📊 Dashboard":
    st.title("📊 Dashboard Operacional")
    
    # Busca dados no Supabase
    res = supabase.table("abastecimentos").select("*").execute()
    df = pd.DataFrame(res.data)
    
    if not df.empty:
        # Métricas no topo
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📅 Último Lançamento", df['data'].max())
        c2.metric("💰 Preço Médio (L)", f"R$ {df['valor_unitario'].mean():.2f}")
        c3.metric("⛽ Total Litros", f"{df['quantidade'].sum():,.0f} L")
        total_gasto = df['total'].sum()
        c4.metric("💳 Total Gasto", f"R$ {total_gasto:,.2f}")
        
        st.divider()
        st.subheader("📈 Resumo de Lançamentos Recentes")
        st.dataframe(df.sort_values('criado_em', ascending=False).head(10), use_container_width=True)
    else:
        st.info("Nenhum dado encontrado. Comece realizando um abastecimento!")

# --- 5. MÓDULO: LANÇAR ABASTECIMENTO ---
elif menu == "📝 Lançar Abastecimento":
    st.title("📝 Ficha de Abastecimento")
    
    # Busca veículos cadastrados para o Selectbox
    veiculos_res = supabase.table("veiculos").select("prefixo").execute()
    lista_v = [v['prefixo'] for v in veiculos_res.data]
    
    if not lista_v:
        st.warning("⚠️ Cadastre um veículo antes de lançar abastecimentos.")
    else:
        with st.form("form_abastecimento", clear_on_submit=True):
            col1, col2 = st.columns(2)
            data_abs = col1.date_input("Data do Abastecimento", datetime.now())
            prefixo = col2.selectbox("Veículo (Prefixo)", lista_v)
            
            col3, col4, col5 = st.columns(3)
            qtd = col3.number_input("Quantidade (L)", min_value=0.0, step=0.1)
            preco = col4.number_input("Preço Unitário (R$)", min_value=0.0, step=0.01)
            fornecedor = col5.selectbox("Posto / Fonte", ["Tanque Central", "Melosa 01", "Posto Cidade"])
            
            obs = st.text_area("Observações")
            
            if st.form_submit_button("✅ Salvar Lançamento", type="primary"):
                total_abs = qtd * preco
                dados = {
                    "data": str(data_abs),
                    "prefixo": prefixo,
                    "quantidade": qtd,
                    "valor_unitario": preco,
                    "total": total_abs,
                    "fornecedor": fornecedor,
                    "observacao": obs,
                    "usuario_registro": st.session_state.usuario
                }
                supabase.table("abastecimentos").insert(dados).execute()
                st.success(f"Abastecimento de {prefixo} salvo com sucesso!")

# --- 6. MÓDULO: CADASTROS ---
elif menu == "🚜 Cadastro de Frota":
    st.title("🚜 Cadastro de Veículos e Equipamentos")
    
    aba1, aba2 = st.tabs(["Novo Veículo", "Gerenciar Classes"])
    
    with aba1:
        with st.form("form_veiculo"):
            c_cl, c_pr, c_pl = st.columns(3)
            # Busca classes
            classes_res = supabase.table("classes").select("nome").execute()
            lista_c = [c['nome'] for c in classes_res.data]
            
            classe_v = c_cl.selectbox("Classe", lista_c)
            pref_v = c_pr.text_input("Prefixo (Ex: CAM-10)")
            placa_v = c_pl.text_input("Placa")
            mot_v = st.text_input("Motorista/Responsável")
            
            if st.form_submit_button("Cadastrar Veículo"):
                supabase.table("veiculos").insert({
                    "classe": classe_v, "prefixo": pref_v.upper(), "placa": placa_v.upper(), "motorista": mot_v
                }).execute()
                st.success("Veículo cadastrado!")

    with aba2:
        nova_classe = st.text_input("Nome da Nova Classe (Ex: Escavadeiras)")
        if st.button("Adicionar Classe"):
            if nova_classe:
                supabase.table("classes").insert({"nome": nova_classe}).execute()
                st.success("Classe adicionada!")
                st.rerun()

# --- 7. MÓDULO: CONSULTA ---
elif menu == "🔍 Consulta & Histórico":
    st.title("🔍 Pesquisa de Histórico")
    pesquisa = st.text_input("Digite o Prefixo do Veículo para pesquisar:")
    if pesquisa:
        res = supabase.table("abastecimentos").select("*").eq("prefixo", pesquisa.upper()).execute()
        df_p = pd.DataFrame(res.data)
        if not df_p.empty:
            st.write(f"Exibindo resultados para: **{pesquisa.upper()}**")
            st.dataframe(df_p, use_container_width=True)
        else:
            st.warning("Nenhum registro encontrado para este prefixo.")
