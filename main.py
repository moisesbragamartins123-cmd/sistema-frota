import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime
import plotly.express as px

# Configuração da Página
st.set_page_config(page_title="Copa Engenharia", layout="wide")

# Conexão Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- LOGIN DISCRETO ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1,1,1])
    with col2:
        st.write("")
        with st.container(border=True):
            st.subheader("Copa Engenharia - Login")
            u = st.text_input("Usuário")
            p = st.text_input("Senha", type="password")
            if st.button("Acessar Sistema"):
                if u == "admin" and p == "obra2026":
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Dados incorretos")
    st.stop()

# --- BARRA LATERAL (Título Discreto) ---
st.sidebar.markdown("### 🏗️ Copa Engenharia Ltda")
st.sidebar.caption("Controle de Abastecimento")
st.sidebar.divider()
menu = st.sidebar.radio("Navegação", ["📊 Dashboard", "📝 Lançar", "🚜 Frota", "🏪 Fornecedores", "📋 Relatórios"])

# Função para buscar dados
def get_data(table):
    try:
        res = supabase.table(table).select("*").execute()
        return pd.DataFrame(res.data)
    except:
        return pd.DataFrame()

# --- 1. DASHBOARD COM GRÁFICOS ---
if menu == "📊 Dashboard":
    st.header("Resumo Operacional")
    df = get_data("abastecimentos")
    
    if not df.empty:
        df['data'] = pd.to_datetime(df['data'])
        df['Mês/Ano'] = df['data'].dt.strftime('%m/%Y')
        
        c1, c2 = st.columns(2)
        filtro_p = c1.multiselect("Filtrar por Posto", df['fornecedor'].unique())
        
        dff = df.copy()
        if filtro_p:
            dff = dff[dff['fornecedor'].isin(filtro_p)]

        # Gráfico de Colunas Mensal
        resumo = dff.groupby(['Mês/Ano', 'fornecedor'])['total'].sum().reset_index()
        fig = px.bar(resumo, x='Mês/Ano', y='total', color='fornecedor', 
                     title="Gasto Mensal por Posto (R$)", barmode='group')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Ainda não há dados para gerar o Dashboard.")

# --- 2. LANÇAR ABASTECIMENTO ---
elif menu == "📝 Lançar":
    st.header("Novo Lançamento")
    df_v = get_data("veiculos")
    df_f = get_data("fornecedores")
    
    with st.form("f_abast", clear_on_submit=True):
        c1, c2 = st.columns(2)
        v = c1.selectbox("Equipamento", df_v['prefixo'].tolist() if not df_v.empty else [])
        f = c2.selectbox("Fornecedor/Posto", df_f['nome'].tolist() if not df_f.empty else [])
        tipo = c1.selectbox("Combustível", ["Diesel S10", "Diesel S500", "Gasolina", "Arla 32"])
        
        qtd = c2.number_input("Litros", min_value=0.0)
        preco = c1.number_input("Preço Unitário", min_value=0.0)
        data_ab = c2.date_input("Data", datetime.now())
        
        if st.form_submit_button("Salvar Abastecimento"):
            supabase.table("abastecimentos").insert({
                "data": str(data_ab), "prefixo": v, "fornecedor": f,
                "quantidade": qtd, "valor_unitario": preco, "total": qtd*preco,
                "tipo_combustivel": tipo
            }).execute()
            st.success("Salvo com sucesso!")

# --- 3. FROTA (COM EDITAR E APAGAR) ---
elif menu == "🚜 Frota":
    st.header("Gestão de Frota")
    t1, t2 = st.tabs(["Listagem e Ações", "Cadastrar Novo"])
    
    with t2:
        with st.form("novo_v"):
            p = st.text_input("Prefixo")
            pl = st.text_input("Placa")
            mot = st.text_input("Motorista Atual")
            if st.form_submit_button("Cadastrar"):
                supabase.table("veiculos").insert({"prefixo": p, "placa": pl, "motorista": mot}).execute()
                st.rerun()

    with t1:
        df_v = get_data("veiculos")
        for i, row in df_v.iterrows():
            with st.expander(f"🚗 {row['prefixo']} - {row['motorista']}"):
                with st.form(f"edit_{row['id']}"):
                    u_mot = st.text_input("Editar Motorista", row['motorista'])
                    u_placa = st.text_input("Editar Placa", row['placa'])
                    col_btn1, col_btn2 = st.columns(2)
                    if col_btn1.form_submit_button("✅ Salvar Alterações"):
                        supabase.table("veiculos").update({"motorista": u_mot, "placa": u_placa}).eq("id", row['id']).execute()
                        st.rerun()
                    if col_btn2.form_submit_button("🗑️ EXCLUIR VEÍCULO"):
                        supabase.table("veiculos").delete().eq("id", row['id']).execute()
                        st.rerun()

# --- 4. FORNECEDORES (COM DADOS BANCÁRIOS) ---
elif menu == "🏪 Fornecedores":
    st.header("Gestão de Fornecedores")
    t1, t2 = st.tabs(["Lista de Fornecedores", "Novo Fornecedor"])
    
    with t2:
        with st.form("novo_f"):
            n = st.text_input("Nome/Posto")
            cnpj = st.text_input("CNPJ")
            c1, c2, c3 = st.columns(3)
            age = c1.text_input("Agência")
            cta = c2.text_input("Conta")
            px = c3.text_input("Chave PIX")
            if st.form_submit_button("Cadastrar Fornecedor"):
                supabase.table("fornecedores").insert({"nome": n, "cnpj": cnpj, "agencia": age, "conta": cta, "pix": px}).execute()
                st.rerun()

    with t1:
        df_f = get_data("fornecedores")
        for i, row in df_f.iterrows():
            with st.expander(f"🏪 {row['nome']}"):
                st.write(f"CNPJ: {row['cnpj']}")
                st.write(f"Banco: Ag {row['agencia']} | Conta {row['conta']} | PIX: {row['pix']}")
                if st.button("🗑️ Excluir", key=f"del_f_{row['id']}"):
                    supabase.table("fornecedores").delete().eq("id", row['id']).execute()
                    st.rerun()

# --- 5. RELATÓRIOS ---
elif menu == "📋 Relatórios":
    st.header("Relatórios Detalhados")
    df = get_data("abastecimentos")
    st.dataframe(df, use_container_width=True)
    st.download_button("Baixar CSV", df.to_csv(index=False), "relatorio_copa.csv")
