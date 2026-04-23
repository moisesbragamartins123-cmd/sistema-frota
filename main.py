import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime
import plotly.express as px

# Configuração
st.set_page_config(page_title="Copa Engenharia", layout="wide")

# Conexão
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# Login Discreto
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if not st.session_state.logged_in:
    c1, c2, c3 = st.columns([1,1,1])
    with col2 := c2:
        with st.container(border=True):
            st.subheader("Copa Engenharia - Login")
            u = st.text_input("Usuário")
            p = st.text_input("Senha", type="password")
            if st.button("Acessar"):
                if u == "admin" and p == "obra2026":
                    st.session_state.logged_in = True
                    st.rerun()
    st.stop()

# Navegação Lateral
st.sidebar.markdown("### 🏗️ Copa Engenharia Ltda")
menu = st.sidebar.radio("Navegação", ["📊 Dashboard", "📝 Lançar", "🚜 Frota", "🏪 Fornecedores", "📋 Relatórios"])

def get_data(table):
    try:
        return pd.DataFrame(supabase.table(table).select("*").execute().data)
    except: return pd.DataFrame()

# --- 1. DASHBOARD COM GRÁFICOS MENSAIS ---
if menu == "📊 Dashboard":
    st.header("Resumo Operacional")
    df = get_data("abastecimentos")
    
    if not df.empty:
        df['data'] = pd.to_datetime(df['data'])
        df['Mes/Ano'] = df['data'].dt.strftime('%m/%Y')
        
        # Filtros do Gráfico
        col_f1, col_f2 = st.columns(2)
        filtro_posto = col_f1.multiselect("Filtrar Gráfico por Posto", df['fornecedor'].unique())
        filtro_comb = col_f2.multiselect("Filtrar por Combustível", df['tipo_combustivel'].unique())
        
        dff = df.copy()
        if filtro_posto: dff = dff[dff['fornecedor'].isin(filtro_posto)]
        if filtro_comb: dff = dff[dff['tipo_combustivel'].isin(filtro_comb)]

        # Gráfico de Colunas
        resumo_mes = dff.groupby(['Mes/Ano', 'fornecedor', 'tipo_combustivel'])['total'].sum().reset_index()
        fig = px.bar(resumo_mes, x='Mes/Ano', y='total', color='fornecedor', 
                     title="Gasto Mensal por Fornecedor (R$)", barmode='group')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aguardando lançamentos para gerar gráficos.")

# --- 2. LANÇAR ABASTECIMENTO ---
elif menu == "📝 Lançar":
    st.header("Lançar Abastecimento")
    df_v = get_data("veiculos"); df_f = get_data("fornecedores")
    with st.form("f_abast", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        veic = c1.selectbox("Veículo", df_v['prefixo'].tolist() if not df_v.empty else [])
        forn = c2.selectbox("Posto", df_f['nome'].tolist() if not df_f.empty else [])
        comb = c3.selectbox("Combustível", ["Diesel S10", "Diesel S500", "Gasolina", "Arla 32"])
        
        data = c1.date_input("Data", datetime.now())
        qtd = c2.number_input("Litros", min_value=0.0)
        val = c3.number_input("Valor Unitário", min_value=0.0)
        
        if st.form_submit_button("Salvar Registro"):
            supabase.table("abastecimentos").insert({
                "data": str(data), "prefixo": veic, "quantidade": qtd, 
                "valor_unitario": val, "total": qtd*val, "fornecedor": forn, "tipo_combustivel": comb
            }).execute()
            st.success("Lançado!")

# --- 3. FROTA (COM EDIÇÃO/EXCLUSÃO) ---
elif menu == "🚜 Frota":
    st.header("Gestão de Frota")
    tab1, tab2 = st.tabs(["Listar/Editar", "Novo Veículo"])
    df_v = get_data("veiculos")
    
    with tab1:
        if not df_v.empty:
            for index, row in df_v.iterrows():
                with st.expander(f"🚗 {row['prefixo']} - {row['classe']}"):
                    with st.form(f"edit_v_{row['id']}"):
                        new_mot = st.text_input("Motorista", row['motorista'])
                        new_placa = st.text_input("Placa", row['placa'])
                        col_e1, col_e2 = st.columns(2)
                        if col_e1.form_submit_button("Atualizar"):
                            supabase.table("veiculos").update({"motorista": new_mot, "placa": new_placa}).eq("id", row['id']).execute()
                            st.rerun()
                        if col_e2.form_submit_button("❌ APAGAR"):
                            supabase.table("veiculos").delete().eq("id", row['id']).execute()
                            st.rerun()

# --- 4. FORNECEDORES (COM BANCO E EDIÇÃO) ---
elif menu == "🏪 Fornecedores":
    st.header("Fornecedores")
    t1, t2 = st.tabs(["Lista/Ações", "Novo Cadastro"])
    
    with t2:
        with st.form("f_new_f"):
            nome = st.text_input("Razão Social")
            cnpj = st.text_input("CNPJ")
            c1, c2, c3 = st.columns(3)
            age = c1.text_input("Agência")
            cta = c2.text_input("Conta")
            pix = c3.text_input("Chave PIX")
            if st.form_submit_button("Cadastrar"):
                supabase.table("fornecedores").insert({"nome": nome, "cnpj": cnpj, "agencia": age, "conta": cta, "pix": pix}).execute()
                st.rerun()

    with t1:
        df_f = get_data("fornecedores")
        for i, r in df_f.iterrows():
            with st.expander(f"🏪 {r['nome']}"):
                st.write(f"CNPJ: {r['cnpj']} | PIX: {r['pix']}")
                if st.button("Excluir Fornecedor", key=f"del_f_{r['id']}"):
                    supabase.table("fornecedores").delete().eq("id", r['id']).execute()
                    st.rerun()

# --- 5. RELATÓRIOS ---
elif menu == "📋 Relatórios":
    st.header("Relatórios para Financeiro")
    df = get_data("abastecimentos")
    st.dataframe(df, use_container_width=True)
