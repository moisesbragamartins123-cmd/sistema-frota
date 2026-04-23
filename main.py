import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime

# Configuração da Página
st.set_page_config(page_title="Copa Engenharia", layout="wide")

# Conexão Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- ESTILO DISCRETO (CSS) ---
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    [data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #e0e0e0; }
    .stButton>button { width: 100%; border-radius: 5px; }
    </style>
""", unsafe_allow_html=True)

# --- LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1,1,1])
    with col2:
        st.write("") 
        st.write("")
        with st.container(border=True):
            st.subheader("Acesso ao Sistema")
            u = st.text_input("Usuário")
            p = st.text_input("Senha", type="password")
            if st.button("Entrar"):
                if u == "admin" and p == "obra2026":
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Incorreto")
    st.stop()

# --- BARRA LATERAL (Título no Canto Esquerdo) ---
st.sidebar.markdown("### 🏗️ Copa Engenharia Ltda")
st.sidebar.caption("Controle de Abastecimento e Produção")
st.sidebar.divider()
menu = st.sidebar.radio("Navegação", [
    "📊 Dashboard", 
    "📝 Lançar Abastecimento", 
    "🚜 Gestão de Frota", 
    "🏪 Fornecedores", 
    "📋 Relatórios"
])

# Funções Auxiliares
def get_data(table):
    try:
        res = supabase.table(table).select("*").execute()
        return pd.DataFrame(res.data)
    except:
        return pd.DataFrame()

# --- 1. DASHBOARD ---
if menu == "📊 Dashboard":
    st.header("Resumo Operacional")
    df = get_data("abastecimentos")
    if not df.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Abastecido (L)", f"{df['quantidade'].sum():,.2f}")
        c2.metric("Investimento Total", f"R$ {df['total'].sum():,.2f}")
        c3.metric("Média Preço/L", f"R$ {df['valor_unitario'].mean():,.2f}")
        st.divider()
        st.subheader("Últimos Lançamentos")
        st.dataframe(df.sort_values('criado_em', ascending=False).head(10), use_container_width=True)

# --- 2. LANÇAR ABASTECIMENTO ---
elif menu == "📝 Lançar Abastecimento":
    st.header("Novo Registro de Abastecimento")
    df_v = get_data("veiculos")
    df_f = get_data("fornecedores")
    
    if df_v.empty or df_f.empty:
        st.warning("Cadastre veículos e fornecedores antes de lançar.")
    else:
        with st.form("form_abast", clear_on_submit=True):
            col1, col2 = st.columns(2)
            veiculo = col1.selectbox("Equipamento/Veículo", df_v['prefixo'].tolist())
            fornecedor = col2.selectbox("Posto/Fornecedor", df_f['nome'].tolist())
            
            data = col1.date_input("Data", datetime.now())
            litros = col2.number_input("Quantidade (Litros)", min_value=0.1)
            valor_un = col1.number_input("Valor Unitário (R$)", min_value=0.1)
            
            total = litros * valor_un
            st.info(f"Valor Total do Lançamento: R$ {total:.2f}")
            
            obs = st.text_area("Observações/Notas")
            
            if st.form_submit_button("Confirmar Lançamento"):
                supabase.table("abastecimentos").insert({
                    "data": str(data), "prefixo": veiculo, "quantidade": litros,
                    "valor_unitario": valor_un, "total": total, "fornecedor": fornecedor,
                    "observacao": obs, "usuario_registro": "admin"
                }).execute()
                st.success("Lançamento realizado com sucesso!")

# --- 3. GESTÃO DE FROTA ---
elif menu == "🚜 Gestão de Frota":
    st.header("Controle de Equipamentos")
    t1, t2 = st.tabs(["Novo Veículo", "Classes"])
    
    with t2:
        with st.form("f_class"):
            nova_classe = st.text_input("Nome da Classe (Ex: Escavadeira)")
            if st.form_submit_button("Salvar Classe"):
                supabase.table("classes").insert({"nome": nova_classe}).execute()
                st.rerun()
        st.write("Classes existentes:", get_data("classes"))

    with t1:
        df_c = get_data("classes")
        with st.form("f_veic"):
            col1, col2 = st.columns(2)
            classe = col1.selectbox("Classe", df_c['nome'].tolist() if not df_c.empty else [])
            pref = col2.text_input("Prefixo (Ex: CAM-01)")
            placa = col1.text_input("Placa")
            mot = col2.text_input("Motorista/Responsável")
            if st.form_submit_button("Cadastrar Veículo"):
                supabase.table("veiculos").insert({"prefixo": pref, "placa": placa, "classe": classe, "motorista": mot}).execute()
                st.success("Veículo cadastrado!")

# --- 4. FORNECEDORES ---
elif menu == "🏪 Fornecedores":
    st.header("Cadastro de Postos e Fornecedores")
    with st.form("f_forn", clear_on_submit=True):
        c1, c2 = st.columns(2)
        n = c1.text_input("Nome/Razão Social*")
        cnpj = c2.text_input("CNPJ")
        cid = c1.text_input("Cidade/UF")
        tel = c2.text_input("Telefone")
        banco = st.text_area("Dados Bancários / Chave PIX")
        if st.form_submit_button("Salvar Fornecedor"):
            supabase.table("fornecedores").insert({"nome": n, "cnpj": cnpj, "cidade": cid, "telefone": tel, "dados_bancarios": banco}).execute()
            st.success("Fornecedor salvo!")
    st.dataframe(get_data("fornecedores"), use_container_width=True)

# --- 5. RELATÓRIOS ---
elif menu == "📋 Relatórios":
    st.header("Relatórios Administrativos")
    df = get_data("abastecimentos")
    if not df.empty:
        col1, col2 = st.columns(2)
        f_v = col1.multiselect("Filtrar por Veículo", df['prefixo'].unique())
        f_p = col2.multiselect("Filtrar por Fornecedor", df['fornecedor'].unique())
        
        filtro = df.copy()
        if f_v: filtro = filtro[filtro['prefixo'].isin(f_v)]
        if f_p: filtro = filtro[filtro['fornecedor'].isin(f_p)]
        
        st.dataframe(filtro, use_container_width=True)
        st.download_button("Baixar Relatório (CSV)", filtro.to_csv(index=False), "relatorio_copa.csv")
