import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime
import plotly.express as px
import os

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
    st.write("") 
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        if os.path.exists("logo.png"):
            st.image("logo.png", width=200)
            
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

# 3. Navegação Lateral (Com Logo)
if os.path.exists("logo.png"):
    st.sidebar.image("logo.png", use_container_width=True)
else:
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
        
        c1, c2 = st.columns(2)
        f_posto = c1.multiselect("Filtrar por Posto", df['fornecedor'].unique())
        f_comb = c2.multiselect("Filtrar por Combustível", df['tipo_combustivel'].unique() if 'tipo_combustivel' in df.columns else [])
        
        dff = df.copy()
        if f_posto: dff = dff[dff['fornecedor'].isin(f_posto)]
        if f_comb: dff = dff[dff['tipo_combustivel'].isin(f_comb)]

        resumo = dff.groupby(['Mes_Ano', 'fornecedor'])['total'].sum().reset_index()
        fig = px.bar(resumo, x='Mes_Ano', y='total', color='fornecedor', title="Gasto por Mês e Posto (R$)", barmode='group')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Lance dados para ver os gráficos.")

elif menu == "📝 Lançar":
    st.header("Lançar Abastecimento")
    df_v = get_data("veiculos")
    df_f = get_data("fornecedores")
    
    if not df_v.empty and not df_f.empty:
        # Coloquei a seleção do veículo fora do form para o sistema identificar o combustível na hora
        veic = st.selectbox("Selecione o Equipamento/Veículo", df_v['prefixo'].tolist())
        
        # Puxa o combustível cadastrado para esse veículo
        dados_veiculo = df_v[df_v['prefixo'] == veic].iloc[0]
        comb_padrao = dados_veiculo.get('tipo_combustivel_padrao', 'Não definido')
        
        st.info(f"⛽ Combustível deste equipamento: **{comb_padrao}**")
        
        with st.form("abast_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            post = col1.selectbox("Posto Fornecedor", df_f['nome'].tolist())
            data = col2.date_input("Data", datetime.now())
            
            qtd = col1.number_input("Litros abastecidos", min_value=0.0)
            pre = col2.number_input("Preço Unitário (R$)", min_value=0.0)
            
            if st.form_submit_button("Confirmar Lançamento"):
                if comb_padrao == 'Não definido':
                    st.error("Este veículo não tem combustível cadastrado. Atualize na aba Frota.")
                else:
                    supabase.table("abastecimentos").insert({
                        "data": str(data), "prefixo": veic, "quantidade": qtd, "valor_unitario": pre,
                        "total": qtd*pre, "fornecedor": post, "tipo_combustivel": comb_padrao
                    }).execute()
                    st.success("Abastecimento salvo com sucesso!")
    else:
        st.warning("Cadastre veículos e fornecedores antes de lançar.")

elif menu == "🚜 Frota":
    st.header("Gestão de Frota")
    t1, t2 = st.tabs(["Editar/Excluir", "Novo Veículo"])
    
    lista_combustiveis = ["Diesel S10", "Diesel S500", "Gasolina", "Arla 32", "Diversos"]

    with t2:
        with st.form("new_v"):
            c1, c2 = st.columns(2)
            pref = c1.text_input("Prefixo (Ex: CAM-01)")
            placa = c2.text_input("Placa")
            mot = c1.text_input("Motorista/Operador")
            comb = c2.selectbox("Combustível Padrão", lista_combustiveis)
            
            if st.form_submit_button("Cadastrar Veículo"):
                supabase.table("veiculos").insert({
                    "prefixo": pref, "placa": placa, "motorista": mot, "tipo_combustivel_padrao": comb
                }).execute()
                st.rerun()
    
    with t1:
        df_v = get_data("veiculos")
        for i, r in df_v.iterrows():
            with st.expander(f"🚗 {r['prefixo']} - Placa: {r.get('placa', 'N/A')} ({r.get('tipo_combustivel_padrao', 'Sem comb.')})"):
                with st.form(f"ed_{r['id']}"):
                    c_e1, c_e2 = st.columns(2)
                    n_mot = c_e1.text_input("Motorista", r['motorista'])
                    n_pla = c_e2.text_input("Placa", r.get('placa', ''))
                    
                    # Puxar o index correto do combustível salvo
                    comb_atual = r.get('tipo_combustivel_padrao', 'Diesel S10')
                    idx_comb = lista_combustiveis.index(comb_atual) if comb_atual in lista_combustiveis else 0
                    n_comb = st.selectbox("Combustível", lista_combustiveis, index=idx_comb)
                    
                    b1, b2 = st.columns(2)
                    if b1.form_submit_button("Salvar Alterações"):
                        supabase.table("veiculos").update({
                            "motorista": n_mot, "placa": n_pla, "tipo_combustivel_padrao": n_comb
                        }).eq("id", r['id']).execute()
                        st.rerun()
                    if b2.form_submit_button("🗑️ APAGAR VEÍCULO"):
                        supabase.table("veiculos").delete().eq("id", r['id']).execute()
                        st.rerun()

elif menu == "🏪 Fornecedores":
    st.header("Fornecedores")
    t1, t2 = st.tabs(["Lista", "Novo Fornecedor"])
    
    with t2:
        with st.form("new_f"):
            c1, c2 = st.columns(2)
            nome = c1.text_input("Razão Social / Nome do Posto")
            cnpj = c2.text_input("CNPJ")
            
            c3, c4, c5 = st.columns(3)
            age = c3.text_input("Agência")
            cta = c4.text_input("Conta")
            pix = c5.text_input("PIX")
            if st.form_submit_button("Cadastrar"):
                supabase.table("fornecedores").insert({
                    "nome": nome, "cnpj": cnpj, "agencia": age, "conta": cta, "pix": pix
                }).execute()
                st.rerun()

    with t1:
        df_f = get_data("fornecedores")
        for i, r in df_f.iterrows():
            with st.expander(f"🏪 {r['nome']}"):
                st.write(f"**CNPJ:** {r.get('cnpj', 'Não cadastrado')}")
                st.write(f"**Banco:** Ag {r['agencia']} | Cta {r['conta']} | **PIX:** {r['pix']}")
                if st.button("🗑️ Excluir", key=f"del_{r['id']}"):
                    supabase.table("fornecedores").delete().eq("id", r['id']).execute()
                    st.rerun()

elif menu == "📋 Relatórios":
    st.header("Relatório Geral")
    df = get_data("abastecimentos")
    st.dataframe(df, use_container_width=True)
    st.download_button("Baixar CSV", df.to_csv(index=False), "copa_engenharia.csv")
