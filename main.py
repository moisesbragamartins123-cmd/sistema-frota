import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime
import plotly.express as px
import os
import time
import io

# 1. Configuração e Estética de Alto Nível
st.set_page_config(page_title="Copa Engenharia", layout="wide")

# CSS customizado
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    [data-testid="stMetricValue"] { font-size: 1.8rem !important; color: #003366; font-weight: 700; }
    .stButton>button { border-radius: 8px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# Conexão Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- LÓGICA DE LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown('<style>body { background-color: #1a1a2e; }</style>', unsafe_allow_html=True)
    st.write("<br><br><br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.2, 1]) 
    with col2:
        with st.form("login_form"):
            c_img1, c_img2, c_img3 = st.columns([1, 1, 1])
            with c_img2:
                if os.path.exists("logo.png"):
                    st.image("logo.png", use_container_width=True) 
            
            st.markdown("<h2 style='text-align: center; color: #333; margin-top:0;'>Acesso Restrito</h2>", unsafe_allow_html=True)
            
            u = st.text_input("Usuário")
            p = st.text_input("Senha", type="password")
            
            st.write("") 
            submit = st.form_submit_button("ENTRAR NO SISTEMA", use_container_width=True)
            
            if submit:
                if u == "admin" and p == "obra2026":
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Dados de acesso incorretos")
    st.stop()

# --- NAVEGAÇÃO INTERNA ---
def logout():
    st.session_state.logged_in = False
    st.rerun()

if os.path.exists("logo.png"):
    col_s1, col_s2, col_s3 = st.sidebar.columns([1, 2, 1])
    with col_s2:
        st.image("logo.png", use_container_width=True)
        
st.sidebar.markdown("<h3 style='text-align: center; margin-top:0;'>Copa Engenharia</h3>", unsafe_allow_html=True)
st.sidebar.divider()

menu = st.sidebar.radio("Menu Principal", ["🏠 Início", "📝 Lançar", "🚜 Frota", "🏪 Fornecedores", "📋 Relatórios"])

st.sidebar.divider()
col_side1, col_side2, col_side3 = st.sidebar.columns([1,2,1])
with col_side2:
    if st.button("🚪 Sair", key="side_logout", use_container_width=True):
        logout()

def get_data(table):
    try:
        res = supabase.table(table).select("*").execute()
        return pd.DataFrame(res.data)
    except: return pd.DataFrame()

# --- PÁGINA: INÍCIO ---
if menu == "🏠 Início":
    st.title("Resumo da Operação")
    df = get_data("abastecimentos")
    
    if not df.empty:
        df['total'] = pd.to_numeric(df['total'])
        df['quantidade'] = pd.to_numeric(df['quantidade'])
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Investimento Total", f"R$ {df['total'].sum():,.2f}")
        m2.metric("Volume Total (Litros)", f"{df['quantidade'].sum():,.1f} L")
        m3.metric("Nº de Abastecimentos", len(df))
        
        st.divider()
        st.subheader("Consumo por Combustível")
        resumo_comb = df.groupby('tipo_combustivel')['quantidade'].sum().reset_index()
        
        if len(resumo_comb) > 0:
            cols = st.columns(len(resumo_comb))
            for i, row in resumo_comb.iterrows():
                nome_comb = row['tipo_combustivel'] if pd.notna(row['tipo_combustivel']) else "Não Informado"
                cols[i].metric(nome_comb, f"{row['quantidade']:,.1f} L")
        else:
            st.info("Nenhum dado de combustível detalhado para exibir.")

        st.write("<br>", unsafe_allow_html=True)
        with st.expander("📈 Visualizar Gráficos de Tendência"):
            df['data'] = pd.to_datetime(df['data'])
            df['Mes'] = df['data'].dt.strftime('%m/%Y')
            f_gasto = px.bar(df.groupby('Mes')['total'].sum().reset_index(), x='Mes', y='total', title="Gastos Mensais (R$)")
            st.plotly_chart(f_gasto, use_container_width=True)
    else:
        st.info("Lance dados para gerar o painel de indicadores.")

# --- PÁGINA: LANÇAR ---
elif menu == "📝 Lançar":
    st.header("Lançamento de Abastecimento")
    df_v = get_data("veiculos")
    df_f = get_data("fornecedores")
    
    if not df_v.empty and not df_f.empty:
        veic_sel = st.selectbox("Selecione o Veículo/Máquina", df_v['prefixo'].tolist())
        
        info_v = df_v[df_v['prefixo'] == veic_sel].iloc[0]
        comb_v = info_v.get('tipo_combustivel_padrao', 'Não definido')
        placa_v = info_v.get('placa', 'N/A')
        
        st.info(f"⛽ **Combustível:** {comb_v} | 🏷️ **Placa:** {placa_v}")
        
        with st.form("form_abast", clear_on_submit=True):
            c1, c2 = st.columns(2)
            posto = c1.selectbox("Posto Fornecedor", df_f['nome'].tolist())
            data = c2.date_input("Data do Abastecimento")
            
            c3, c4, c5 = st.columns(3)
            horimetro = c3.number_input("Horímetro Atual", min_value=0.0, step=0.1)
            litros = c4.number_input("Litros", min_value=0.0)
            preco = c5.number_input("Preço Unitário (R$)", min_value=0.0)
