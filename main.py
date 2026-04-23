import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime
import plotly.express as px

# 1. Configuração Básica
st.set_page_config(page_title="Copa Engenharia", layout="wide")

# Conexão Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# 2. Login Discreto
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.write("") # Espaçador
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        st.subheader("Controle de Abastecimento - Login")
        u = st.text_input("Usuário")
        p = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            if u == "admin" and p == "obra2026":
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Dados inválidos")
    st.stop()

# 3. Navegação Lateral
st.sidebar.markdown("### 🏗️ Copa Engenharia Ltda")
st.sidebar.divider()
menu = st.sidebar.radio("Navegação", ["📊 Dashboard", "📝 Lançar", "🚜 Frota", "🏪 Fornecedores", "📋 Relatórios"])

def get_data(table):
    try:
        res = supabase.table(table).select("*").execute()
        return pd.DataFrame(res.data)
    except:
        return pd.DataFrame()

# --- MÓDULOS DO SISTEMA ---

if menu == "📊 Dashboard":
    st.header("Resumo Operacional")
    df = get_data("abastecimentos")
    if not df.empty:
        df['data'] = pd.to_datetime(df['data'])
        df['Mes_Ano'] = df['data'].dt.strftime('%m/%Y')
        
        # Filtros
        c1, c2 = st.columns(2)
        f_posto = c1.multiselect("Filtrar por Posto", df['fornecedor'].unique())
        f_comb = c2.multiselect("Filtrar por Combustível", df['tipo_combustivel'].unique() if 'tipo_combustivel' in df.columns else [])
        
        dff = df.copy()
        if f_posto: dff = dff[dff['fornecedor'].isin(f_posto)]
        if f_comb: dff = dff[dff['tipo_combustivel'].isin(f_comb)]

        # Gráfico Mensal
        resumo = dff.groupby(['Mes_Ano', 'fornecedor'])['total'].sum().reset_index()
        fig = px.bar(resumo, x='Mes_Ano', y='total', color='fornecedor', title="Gasto por Mês e Posto (R$)", barmode='group')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Lance dados para ver os gráficos.")

elif menu == "📝 Lançar":
    st.header("Lançar Abastecimento")
    df_v = get_data("veiculos")
    df_f = get_data("fornecedores")
    
    with st.form("abast_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        veic = col1.selectbox("Equipamento", df_v['prefixo'].tolist() if not df_v.empty else [])
        post = col2.selectbox("Posto", df_f['nome'].tolist() if not df_f.empty else [])
        comb = col1.selectbox("Combustível", ["Diesel S10", "Diesel S500", "Gasolina", "Arla 32"])
        data = col2.date_input("Data", datetime.now())
        qtd = col1.number_input("Litros", min_value=0.0)
        pre = col2.number_input("Preço Unitário", min_value=0.0)
        
        if st.form_submit_button("Confirmar Lançamento"):
            supabase.table("abastecimentos").insert({
                "data": str(data), "prefixo": veic, "quantidade": qtd, "valor_unitario": pre,
                "total": qtd*pre, "fornecedor": post, "tipo_combustivel": comb
            }).execute()
            st.success("Salvo!")

elif menu == "🚜 Frota":
    st.header("Gestão de Frota")
    t1, t2 = st.tabs(["Editar/Excluir", "Novo Veículo"])
    
    with t2:
        with st.form("new_v"):
            pref = st.text_input("Prefixo")
            mot = st.text_input("Motorista")
            if st.form_submit_button("Cadastrar"):
                supabase.table("veiculos").insert({"prefixo": pref, "motorista": mot}).execute()
                st.rerun()
    
    with t1:
        df_v = get_data("veiculos")
        for i, r in df_v.iterrows():
            with st.expander(f"🚗 {r['prefixo']} - {r['motorista']}"):
                with st.form(f"ed_{r['id']}"):
                    n_mot = st.text_input("Motorista", r['motorista'])
                    c1, c2 = st.columns(2)
                    if c1.form_submit_button("Salvar"):
                        supabase.table("veiculos").update({"motorista": n_mot}).eq("id", r['id']).execute()
                        st.rerun()
                    if c2.form_submit_button("🗑️ APAGAR"):
                        supabase.table("veiculos").delete().eq("id", r['id']).execute()
                        st.rerun()

elif menu == "🏪 Fornecedores":
    st.header("Fornecedores")
    t1, t2 = st.tabs(["Lista", "Novo Fornecedor"])
    
    with t2:
        with st.form("new_f"):
            nome = st.text_input("Nome/Posto")
            c1, c2, c3 = st.columns(3)
            age = c1.text_input("Agência")
            cta = c2.text_input("Conta")
            pix = c3.text_input("PIX")
            if st.form_submit_button("Cadastrar"):
                supabase.table("fornecedores").insert({"nome": nome, "agencia": age, "conta": cta, "pix": pix}).execute()
                st.rerun()

    with t1:
        df_f = get_data("fornecedores")
        for i, r in df_f.iterrows():
            with st.expander(f"🏪 {r['nome']}"):
                st.write(f"Banco: Ag {r['agencia']} | Cta {r['conta']} | PIX: {r['pix']}")
                if st.button("🗑️ Excluir", key=f"del_{r['id']}"):
                    supabase.table("fornecedores").delete().eq("id", r['id']).execute()
                    st.rerun()

elif menu == "📋 Relatórios":
    st.header("Relatório Geral")
    df = get_data("abastecimentos")
    st.dataframe(df, use_container_width=True)
    st.download_button("Baixar CSV", df.to_csv(index=False), "copa_engenharia.csv")
