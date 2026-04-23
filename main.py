import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime
import plotly.express as px
import os

# 1. Configuração e Estética de Alto Nível
st.set_page_config(page_title="Copa Engenharia", layout="wide")

# CSS customizado para centralizar login e estilizar métricas
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    [data-testid="stMetricValue"] { font-size: 1.8rem !important; color: #003366; font-weight: 700; }
    .stButton>button { border-radius: 8px; font-weight: bold; }
    .login-box {
        background-color: #ffffff;
        padding: 50px;
        border-radius: 20px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        text-align: center;
    }
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
    # Fundo Escuro na Tela de Login
    st.markdown('<style>body { background-color: #1a1a2e; }</style>', unsafe_allow_html=True)
    st.write("<br><br><br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        if os.path.exists("logo.png"):
            st.image("logo.png", use_container_width=True)
        
        st.markdown("<h2 style='color: #333;'>Acesso Restrito</h2>", unsafe_allow_html=True)
        u = st.text_input("Usuário")
        p = st.text_input("Senha", type="password")
        
        if st.button("ENTRAR NO SISTEMA", use_container_width=True):
            if u == "admin" and p == "obra2026":
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Dados de acesso incorretos")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- NAVEGAÇÃO ---
def logout():
    st.session_state.logged_in = False
    st.rerun()

if os.path.exists("logo.png"):
    st.sidebar.image("logo.png", use_container_width=True)
st.sidebar.markdown("<h3 style='text-align: center;'>Copa Engenharia</h3>", unsafe_allow_html=True)
st.sidebar.divider()

menu = st.sidebar.radio("Menu Principal", ["🏠 Início", "📝 Lançar", "🚜 Frota", "🏪 Fornecedores", "📋 Relatórios"])

st.sidebar.divider()
if st.sidebar.button("🚪 Sair"):
    logout()

# Função para buscar dados
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
        
        # MÉTRICAS FIXAS NO TOPO
        m1, m2, m3 = st.columns(3)
        m1.metric("Investimento Total", f"R$ {df['total'].sum():,.2f}")
        m2.metric("Volume Total (Litros)", f"{df['quantidade'].sum():,.1f} L")
        m3.metric("Nº de Abastecimentos", len(df))
        
        st.divider()
        st.subheader("Consumo por Combustível")
        resumo_comb = df.groupby('tipo_combustivel')['quantidade'].sum().reset_index()
        cols = st.columns(len(resumo_comb))
        for i, row in resumo_comb.iterrows():
            cols[i].metric(row['tipo_combustivel'], f"{row['quantidade']:,.1f} L")

        # GRÁFICOS OCULTOS (EXPANDER)
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
        
        # Puxa informações automáticas do veículo
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
            
            if st.form_submit_button("Confirmar Lançamento"):
                if comb_v == 'Não definido':
                    st.error("Erro: Veículo sem combustível padrão definido na Frota.")
                else:
                    supabase.table("abastecimentos").insert({
                        "data": str(data), "prefixo": veic_sel, "quantidade": litros, "valor_unitario": preco,
                        "total": litros*preco, "fornecedor": posto, "tipo_combustivel": comb_v,
                        "horimetro": horimetro
                    }).execute()
                    st.success("Abastecimento registrado com sucesso!")
    else:
        st.warning("Cadastre primeiro a Frota e os Fornecedores.")

# --- PÁGINA: FROTA ---
elif menu == "🚜 Frota":
    st.header("Gestão de Frota")
    t1, t2 = st.tabs(["Frota Cadastrada", "Adicionar Novo"])
    
    tipos_comb = ["Diesel S10", "Diesel S500", "Gasolina", "Arla 32", "Diversos"]

    with t2:
        with st.form("new_v"):
            c1, c2 = st.columns(2)
            pre = c1.text_input("Prefixo (Ex: CAM-01)")
            pla = c2.text_input("Placa")
            mot = c1.text_input("Motorista/Operador")
            comb = c2.selectbox("Combustível Padrão", tipos_comb)
            if st.form_submit_button("Salvar Veículo"):
                supabase.table("veiculos").insert({
                    "prefixo": pre, "placa": pla, "motorista": mot, "tipo_combustivel_padrao": comb
                }).execute()
                st.rerun()

    with t1:
        df_v = get_data("veiculos")
        for i, r in df_v.iterrows():
            with st.expander(f"🚜 {r['prefixo']} - {r.get('placa', 'S/P')}"):
                st.write(f"**Combustível:** {r.get('tipo_combustivel_padrao', '---')} | **Motorista:** {r['motorista']}")
                if st.button("🗑️ Excluir", key=f"v_{r['id']}"):
                    supabase.table("veiculos").delete().eq("id", r['id']).execute()
                    st.rerun()

# --- PÁGINA: FORNECEDORES ---
elif menu == "🏪 Fornecedores":
    st.header("Fornecedores e Postos")
    t1, t2 = st.tabs(["Lista de Parceiros", "Novo Fornecedor"])
    
    with t2:
        with st.form("new_f"):
            nome_fantasia = st.text_input("Nome Fantasia (Como é conhecido)", placeholder="Ex: Posto do Trevo")
            razao_social = st.text_input("Razão Social (Nome na Nota)", placeholder="Ex: Auto Posto Silva Ltda")
            c1, c2 = st.columns(2)
            cnpj = c1.text_input("CNPJ")
            pix = c2.text_input("Chave PIX")
            if st.form_submit_button("Cadastrar Fornecedor"):
                supabase.table("fornecedores").insert({
                    "nome": nome_fantasia, "razao_social": razao_social, "cnpj": cnpj, "pix": pix
                }).execute()
                st.rerun()

    with t1:
        df_f = get_data("fornecedores")
        for i, r in df_f.iterrows():
            with st.expander(f"🏪 {r['nome'].upper()}"):
                st.write(f"**Razão Social:** {r.get('razao_social', 'N/A')}")
                st.write(f"**CNPJ:** {r['cnpj']} | **PIX:** {r['pix']}")
                if st.button("Remover", key=f"f_{r['id']}"):
                    supabase.table("fornecedores").delete().eq("id", r['id']).execute()
                    st.rerun()

# --- PÁGINA: RELATÓRIOS ---
elif menu == "📋 Relatórios":
    st.header("Histórico de Abastecimentos")
    df = get_data("abastecimentos")
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        st.download_button("Baixar Relatório (CSV)", df.to_csv(index=False), "relatorio_copa.csv")
    else:
        st.info("Nenhum dado encontrado.")
