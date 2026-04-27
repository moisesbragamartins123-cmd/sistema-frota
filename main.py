import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime, date
import plotly.express as px
import os
import time

# ═══════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO DA PÁGINA
# ═══════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="PavControl — COPA Engenharia",
    page_icon="🛣️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ═══════════════════════════════════════════════════════════════════
# CSS COMPLETO E ESTÁVEL
# ═══════════════════════════════════════════════════════════════════
st.markdown("""
<style>
/* Fonte */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Fundo principal */
.stApp {
    background-color: #F0F2F6;
}

/* ─────────── SIDEBAR ESCURA ─────────── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0F172A 0%, #1E293B 100%);
    border-right: none;
}

[data-testid="stSidebar"] .stMarkdown, 
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] .stRadio label {
    color: #CBD5E1 !important;
}

[data-testid="stSidebar"] h1, 
[data-testid="stSidebar"] h2, 
[data-testid="stSidebar"] h3 {
    color: #10B981 !important;
}

/* Radio menu no sidebar */
[data-testid="stSidebar"] .stRadio > div {
    gap: 8px;
}

[data-testid="stSidebar"] .stRadio label {
    padding: 8px 12px;
    border-radius: 10px;
    font-weight: 500;
    transition: all 0.2s;
}

[data-testid="stSidebar"] .stRadio label:hover {
    background-color: rgba(16, 185, 129, 0.15);
    color: #10B981 !important;
}

/* Botão sair */
[data-testid="stSidebar"] .stButton button {
    background-color: #EF4444 !important;
    color: white !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
}

[data-testid="stSidebar"] .stButton button:hover {
    background-color: #DC2626 !important;
}

/* ─────────── CARDS E KPI ─────────── */
.kpi-card {
    background: white;
    border-radius: 20px;
    padding: 1.2rem;
    text-align: center;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    border: 1px solid #E2E8F0;
    transition: transform 0.2s, box-shadow 0.2s;
}

.kpi-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 20px rgba(0,0,0,0.1);
}

.kpi-value {
    font-size: 32px;
    font-weight: 700;
    color: #10B981;
    margin: 8px 0 0 0;
}

.kpi-label {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    color: #64748B;
    letter-spacing: 0.5px;
}

/* ─────────── CARDS DE TANQUE ─────────── */
.tank-card {
    background: white;
    border-radius: 16px;
    padding: 1rem;
    margin: 0.5rem 0;
    border-left: 4px solid #10B981;
    box-shadow: 0 2px 6px rgba(0,0,0,0.04);
}

.tank-card-warning {
    border-left-color: #F59E0B;
    background: #FFFBEB;
}

/* ─────────── BOTÕES ─────────── */
.stButton button {
    background: #10B981 !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
    padding: 0.5rem 1rem !important;
    transition: all 0.2s !important;
}

.stButton button:hover {
    background: #059669 !important;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
}

/* ─────────── FORMULÁRIOS ─────────── */
[data-testid="stForm"] {
    background: white;
    border-radius: 20px;
    padding: 1.5rem;
    border: 1px solid #E2E8F0;
}

/* ─────────── EXPANDER ─────────── */
.streamlit-expanderHeader {
    background: white;
    border-radius: 12px;
    border: 1px solid #E2E8F0;
}

/* ─────────── TÍTULOS ─────────── */
.main-title {
    font-size: 28px;
    font-weight: 700;
    color: #0F172A;
    margin-bottom: 8px;
}

.sub-title {
    color: #64748B;
    margin-bottom: 24px;
    font-size: 14px;
}

.section-title {
    font-size: 18px;
    font-weight: 600;
    color: #0F172A;
    margin: 24px 0 16px 0;
    padding-left: 12px;
    border-left: 4px solid #10B981;
}

/* ─────────── LOGIN ─────────── */
.login-container {
    background: white;
    border-radius: 32px;
    padding: 2.5rem;
    box-shadow: 0 25px 50px -12px rgba(0,0,0,0.25);
    text-align: center;
}

/* ─────────── METRICS ─────────── */
[data-testid="stMetricValue"] {
    color: #10B981;
    font-weight: 700;
}

/* ─────────── TABELA ─────────── */
.dataframe {
    border-radius: 12px;
    overflow: hidden;
}

/* ─────────── PROGRESS BAR ─────────── */
.stProgress > div > div {
    background-color: #10B981 !important;
}
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════
# SUPABASE (configuração)
# ═══════════════════════════════════════════════════════════════════
@st.cache_resource
def get_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = get_supabase()

def get_data(table: str) -> pd.DataFrame:
    try:
        res = supabase.table(table).select("*").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()

def insert_data(table: str, data: dict) -> bool:
    try:
        supabase.table(table).insert(data).execute()
        return True
    except Exception as e:
        st.error(f"Erro: {e}")
        return False

def calcular_saldo(nome_tanque: str) -> float:
    df_ent = get_data("entradas_tanque")
    df_sai = get_data("abastecimentos")
    t_ent = 0.0
    if not df_ent.empty and "nome_tanque" in df_ent.columns:
        t_ent = pd.to_numeric(df_ent[df_ent["nome_tanque"]==nome_tanque]["quantidade"], errors="coerce").sum()
    t_sai = 0.0
    if not df_sai.empty and "nome_tanque" in df_sai.columns:
        mask = df_sai["nome_tanque"] == nome_tanque
        t_sai = pd.to_numeric(df_sai.loc[mask, "quantidade"], errors="coerce").sum()
    return float(t_ent) - float(t_sai)

# ═══════════════════════════════════════════════════════════════════
# LOGIN
# ═══════════════════════════════════════════════════════════════════
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.usuario = ""
    st.session_state.perfil = ""

if not st.session_state.logged_in:
    # Esconde sidebar no login
    st.markdown("""
    <style>
    [data-testid="stHeader"] { background: transparent !important; }
    [data-testid="stSidebar"] { display: none !important; }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        
        # Logo
        st.markdown("<h1 style='color:#10B981; font-size:48px; margin:0;'>🏗️ COPA</h1>", unsafe_allow_html=True)
        st.markdown("<p style='color:#64748B; font-weight:500; margin-top:-10px;'>ENGENHARIA</p>", unsafe_allow_html=True)
        st.markdown("<p style='font-size:14px; color:#94A3B8;'>Multiplicando Caminhos</p>", unsafe_allow_html=True)
        
        st.markdown("<h2 style='margin: 32px 0 8px 0; font-size:24px;'>Acesso Restrito</h2>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            usuario = st.text_input("USUÁRIO", placeholder="Digite seu usuário", label_visibility="collapsed")
            senha = st.text_input("SENHA", type="password", placeholder="Digite sua senha", label_visibility="collapsed")
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.form_submit_button("ENTRAR NO SISTEMA", use_container_width=True):
                # Login via Supabase ou fallback
                try:
                    res = supabase.table("usuarios").select("*").eq("login", usuario).eq("senha", senha).execute()
                    if res.data:
                        st.session_state.logged_in = True
                        st.session_state.usuario = res.data[0]["nome"]
                        st.session_state.perfil = res.data[0]["perfil"]
                        st.rerun()
                    else:
                        st.error("❌ Usuário ou senha incorretos.")
                except:
                    # Fallback para teste
                    if usuario == "admin" and senha == "admin":
                        st.session_state.logged_in = True
                        st.session_state.usuario = "Administrador"
                        st.session_state.perfil = "Admin"
                        st.rerun()
                    else:
                        st.error("❌ Usuário ou senha incorretos.")
        
        st.markdown("<p style='font-size:11px; color:#94A3B8; margin-top:24px;'>Acesso autorizado apenas para usuários cadastrados.</p>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ═══════════════════════════════════════════════════════════════════
# SIDEBAR (pós-login)
# ═══════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("<h2 style='text-align:center; margin-bottom:0;'>🏗️ COPA</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; font-size:12px; margin-top:-10px;'>ENGENHARIA</p>", unsafe_allow_html=True)
    
    st.divider()
    
    # Info do usuário
    st.markdown(f"""
    <div style='background:rgba(16, 185, 129, 0.1); border-radius:16px; padding:12px; text-align:center; margin-bottom:20px;'>
        <span style='font-size:12px; color:#94A3B8;'>👤 USUÁRIO</span>
        <span style='font-size:14px; font-weight:600; display:block; color:#10B981;'>{st.session_state.usuario}</span>
        <span style='font-size:11px; color:#64748B;'>{st.session_state.perfil}</span>
    </div>
    """, unsafe_allow_html=True)
    
    # Menu principal
    menu = st.radio(
        "MENU",
        ["🏠 PAINEL INÍCIO", "⛽ ABASTECIMENTOS", "🛢️ TANQUES", "🚚 TRANSPORTE", "🚜 FROTA", "🏪 FORNECEDORES", "🏗️ OBRAS", "📋 RELATÓRIOS"],
        label_visibility="collapsed"
    )
    
    if st.session_state.perfil == "Admin":
        if st.button("👥 USUÁRIOS", use_container_width=True):
            menu = "👥 USUÁRIOS"
    
    st.divider()
    
    if st.button("🚪 SAIR", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

# ═══════════════════════════════════════════════════════════════════
# 1. PAINEL INÍCIO (FIEL À IMAGEM)
# ═══════════════════════════════════════════════════════════════════
if menu == "🏠 PAINEL INÍCIO":
    st.markdown("<h1 class='main-title'>Centro de Comando da Obra</h1>", unsafe_allow_html=True)
    st.markdown("<p class='sub-title'>Visão geral da operação em tempo real</p>", unsafe_allow_html=True)
    
    # Dados estáticos baseados na imagem
    eficiencia_data = {
        "Caçamba": ["CB-02", "CB-01", "CB-05", "CB-03", "CB-04"],
        "km/L": [3.12, 2.85, 2.48, 2.31, 1.95]
    }
    df_eficiencia = pd.DataFrame(eficiencia_data)
    media_geral = df_eficiencia["km/L"].mean()
    
    # ===== EFICIÊNCIA DAS CAÇAMBAS =====
    st.markdown("<h3 class='section-title'>📊 Eficiência das Caçambas (km/L)</h3>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 3])
    with col1:
        st.markdown(f"""
        <div class='kpi-card'>
            <div class='kpi-label'>MÉDIA GERAL</div>
            <div class='kpi-value'>{media_geral:.2f} km/L</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        fig = px.bar(df_eficiencia, x="Caçamba", y="km/L", 
                     text="km/L", color="km/L",
                     color_continuous_scale=["#F59E0B", "#10B981"])
        fig.update_traces(textposition="outside", marker_line_width=0)
        fig.update_layout(plot_bgcolor="white", height=320, margin=dict(l=0, r=0, t=10, b=0))
        fig.update_xaxes(showgrid=False)
        fig.update_yaxes(showgrid=True, gridcolor="#E2E8F0")
        st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    # ===== PRODUÇÃO DE MASSA ASFÁLTICA =====
    st.markdown("<h3 class='section-title'>🏭 Produção de Massa Asfáltica (tons)</h3>", unsafe_allow_html=True)
    
    producao_data = {
        "Mês": ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out"],
        "Toneladas": [2650, 3420, 4120, 4500, 4850, 4800, 4950, 5100, 5200, 5400]
    }
    df_producao = pd.DataFrame(producao_data)
    
    fig2 = px.bar(df_producao, x="Mês", y="Toneladas", text="Toneladas",
                  color_discrete_sequence=["#10B981"])
    fig2.update_traces(textposition="outside", marker_line_width=0)
    fig2.update_layout(plot_bgcolor="white", height=350, margin=dict(l=0, r=0, t=10, b=0))
    fig2.update_xaxes(showgrid=False)
    fig2.update_yaxes(showgrid=True, gridcolor="#E2E8F0")
    st.plotly_chart(fig2, use_container_width=True)
    
    st.divider()
    
    # ===== CONSUMO POR TIPO DE EQUIPAMENTO =====
    st.markdown("<h3 class='section-title'>⛽ Consumo por Tipo de Equipamento</h3>", unsafe_allow_html=True)
    
    consumo_data = {
        "Equipamento": ["Caçambas", "Pás Carregadeiras", "Escavadeiras"],
        "Consumo (%)": [48.5, 22.1, 15.3]
    }
    df_consumo = pd.DataFrame(consumo_data)
    
    col1, col2 = st.columns([1, 1.5])
    with col1:
        fig3 = px.pie(df_consumo, values="Consumo (%)", names="Equipamento",
                      color_discrete_sequence=["#10B981", "#F59E0B", "#3B82F6"],
                      hole=0.4)
        fig3.update_layout(height=280, margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig3, use_container_width=True)
    
    with col2:
        st.markdown("<div style='background:white; border-radius:20px; padding:1.5rem; height:100%;'>", unsafe_allow_html=True)
        for _, row in df_consumo.iterrows():
            st.markdown(f"""
            <div style='margin-bottom:20px;'>
                <div style='display:flex; justify-content:space-between; margin-bottom:6px;'>
                    <span style='font-weight:500;'>{row['Equipamento']}</span>
                    <span style='color:#10B981; font-weight:700;'>{row['Consumo (%)']}%</span>
                </div>
                <div style='background:#E2E8F0; border-radius:12px; height:10px; overflow:hidden;'>
                    <div style='background:#10B981; width:{row['Consumo (%)']}%; height:10px; border-radius:12px;'></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    st.divider()
    
    # ===== RANKING DE CAÇAMBAS =====
    st.markdown("<h3 class='section-title'>🏆 Ranking de Caçambas por Eficiência</h3>", unsafe_allow_html=True)
    
    ranking_data = {
        "Posição": ["1º", "2º", "3º", "4º", "5º"],
        "Caçamba": ["CB-02", "CB-01", "CB-05", "CB-03", "CB-04"],
        "Eficiência (km/L)": [3.12, 2.85, 2.48, 2.31, 1.95],
        "Consumo (L)": ["8.542", "9.210", "10.150", "11.230", "12.450"]
    }
    df_ranking = pd.DataFrame(ranking_data)
    
    # Estilizando a tabela
    st.dataframe(df_ranking, use_container_width=True, hide_index=True)
    
    st.divider()
    
    # ===== ARMAZENAMENTO (rodapé da imagem) =====
    st.markdown("""
    <div style='background:#F1F5F9; border-radius:20px; padding:1rem; margin-top:1rem;'>
        <div style='display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap;'>
            <div>
                <span style='font-weight:600;'>💾 Armazenamento: Saudável</span>
                <span style='color:#64748B; margin-left:1rem;'>Plano Free (500MB)</span>
            </div>
            <span style='color:#10B981;'>✓ Sincronizado</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════
# 2. ABASTECIMENTOS (simplificado mas funcional)
# ═══════════════════════════════════════════════════════════════════
elif menu == "⛽ ABASTECIMENTOS":
    st.markdown("<h1 class='main-title'>⛽ Lançar Abastecimento</h1>", unsafe_allow_html=True)
    
    df_veiculos = get_data("veiculos")
    if df_veiculos.empty:
        st.warning("⚠️ Nenhum veículo cadastrado. Acesse o menu FROTA primeiro.")
    else:
        with st.form("form_abastecimento"):
            col1, col2 = st.columns(2)
            with col1:
                data = st.date_input("Data", value=date.today())
                veiculo = st.selectbox("Veículo", df_veiculos["prefixo"].tolist())
            with col2:
                litros = st.number_input("Litros", min_value=0.0, step=10.0)
                preco = st.number_input("Preço (R$/L)", min_value=0.0, step=0.01)
            
            motorista = st.text_input("Motorista")
            observacao = st.text_area("Observação", height=68)
            
            st.markdown(f"<div class='kpi-card'><span class='kpi-label'>Total</span><div class='kpi-value'>R$ {litros * preco:,.2f}</div></div>", unsafe_allow_html=True)
            
            if st.form_submit_button("💾 SALVAR ABASTECIMENTO", use_container_width=True):
                if litros > 0:
                    dados = {
                        "data": str(data),
                        "prefixo": veiculo,
                        "motorista": motorista,
                        "quantidade": litros,
                        "valor_unitario": preco,
                        "total": litros * preco,
                        "observacao": observacao,
                        "criado_por": st.session_state.usuario
                    }
                    if insert_data("abastecimentos", dados):
                        st.success("✅ Abastecimento salvo!")
                        time.sleep(1)
                        st.rerun()
                else:
                    st.error("❌ Informe uma quantidade válida.")

# ═══════════════════════════════════════════════════════════════════
# 3. TANQUES
# ═══════════════════════════════════════════════════════════════════
elif menu == "🛢️ TANQUES":
    st.markdown("<h1 class='main-title'>🛢️ Gestão de Tanques</h1>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📊 SALDO ATUAL", "📥 ENTRADA DE COMBUSTÍVEL"])
    
    with tab1:
        df_tanques = get_data("tanques")
        if df_tanques.empty:
            st.info("Nenhum tanque cadastrado.")
        else:
            for _, tanque in df_tanques.iterrows():
                nome = tanque["nome"]
                saldo = calcular_saldo(nome)
                capacidade = tanque.get("capacidade", 0)
                
                if saldo < 500:
                    css_class = "tank-card-warning"
                else:
                    css_class = "tank-card"
                
                st.markdown(f"""
                <div class='{css_class}'>
                    <div style='display:flex; justify-content:space-between; align-items:center;'>
                        <strong style='font-size:16px;'>🛢️ {nome}</strong>
                        <span style='color:{"#F59E0B" if saldo < 500 else "#10B981"}; font-weight:700;'>{saldo:,.0f} Litros</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    with tab2:
        with st.form("form_entrada"):
            col1, col2 = st.columns(2)
            with col1:
                data_ent = st.date_input("Data", value=date.today())
                tanque = st.selectbox("Tanque", df_tanques["nome"].tolist() if not df_tanques.empty else [])
            with col2:
                litros_ent = st.number_input("Litros", min_value=0.0, step=100.0)
                preco_ent = st.number_input("Preço (R$/L)", min_value=0.0, step=0.01)
            
            fornecedor = st.text_input("Fornecedor")
            num_nf = st.text_input("Nº Nota Fiscal")
            
            if st.form_submit_button("📥 REGISTRAR ENTRADA", use_container_width=True):
                if litros_ent > 0 and tanque:
                    dados = {
                        "data": str(data_ent),
                        "nome_tanque": tanque,
                        "quantidade": litros_ent,
                        "valor_unitario": preco_ent,
                        "total": litros_ent * preco_ent,
                        "fornecedor": fornecedor,
                        "numero_ficha": num_nf,
                        "criado_por": st.session_state.usuario
                    }
                    if insert_data("entradas_tanque", dados):
                        st.success("✅ Entrada registrada!")
                        st.rerun()

# ═══════════════════════════════════════════════════════════════════
# 4. TRANSPORTE
# ═══════════════════════════════════════════════════════════════════
elif menu == "🚚 TRANSPORTE":
    st.markdown("<h1 class='main-title'>🚚 Boletim de Transporte</h1>", unsafe_allow_html=True)
    
    with st.form("form_transporte"):
        col1, col2 = st.columns(2)
        with col1:
            data_transp = st.date_input("Data", value=date.today())
            veiculo = st.text_input("Veículo / Placa")
        with col2:
            motorista = st.text_input("Motorista")
            origem = st.text_input("Origem")
        
        destino = st.text_input("Destino")
        toneladas = st.number_input("Toneladas", min_value=0.0, step=1.0)
        valor_frete = st.number_input("Valor do Frete (R$)", min_value=0.0, step=50.0)
        
        if st.form_submit_button("💾 SALVAR BOLETIM", use_container_width=True):
            if motorista and veiculo:
                dados = {
                    "data": str(data_transp),
                    "veiculo": veiculo,
                    "motorista": motorista,
                    "origem": origem,
                    "destino": destino,
                    "toneladas": toneladas,
                    "valor_frete": valor_frete,
                    "criado_por": st.session_state.usuario
                }
                if insert_data("producao", dados):
                    st.success("✅ Boletim salvo!")
                    st.rerun()

# ═══════════════════════════════════════════════════════════════════
# 5. FROTA
# ═══════════════════════════════════════════════════════════════════
elif menu == "🚜 FROTA":
    st.markdown("<h1 class='main-title'>🚜 Frota e Equipamentos</h1>", unsafe_allow_html=True)
    
    with st.form("form_veiculo"):
        col1, col2, col3 = st.columns(3)
        with col1:
            prefixo = st.text_input("Prefixo (ex: CB-01)")
            placa = st.text_input("Placa")
        with col2:
            tipo = st.selectbox("Tipo", ["Caçamba", "Pá Carregadeira", "Escavadeira", "Caminhão"])
            motorista = st.text_input("Motorista Fixo")
        with col3:
            proprietario = st.text_input("Proprietário")
            combustivel = st.selectbox("Combustível", ["Diesel S10", "Diesel S500", "Gasolina"])
        
        if st.form_submit_button("💾 CADASTRAR VEÍCULO", use_container_width=True):
            if prefixo:
                dados = {
                    "prefixo": prefixo,
                    "placa": placa,
                    "classe": tipo,
                    "motorista": motorista,
                    "proprietario": proprietario,
                    "tipo_combustivel_padrao": combustivel,
                    "criado_por": st.session_state.usuario
                }
                if insert_data("veiculos", dados):
                    st.success("✅ Veículo cadastrado!")
                    st.rerun()
    
    st.divider()
    st.markdown("### 📋 Veículos Cadastrados")
    df_veiculos = get_data("veiculos")
    if not df_veiculos.empty:
        st.dataframe(df_veiculos[["prefixo", "placa", "classe", "motorista", "proprietario"]], use_container_width=True, hide_index=True)

# ═══════════════════════════════════════════════════════════════════
# 6. FORNECEDORES
# ═══════════════════════════════════════════════════════════════════
elif menu == "🏪 FORNECEDORES":
    st.markdown("<h1 class='main-title'>🏪 Fornecedores</h1>", unsafe_allow_html=True)
    
    with st.form("form_fornecedor"):
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("Nome Fantasia")
            cnpj = st.text_input("CNPJ")
        with col2:
            telefone = st.text_input("Telefone")
            contato = st.text_input("Contato")
        
        if st.form_submit_button("💾 CADASTRAR FORNECEDOR", use_container_width=True):
            if nome:
                dados = {
                    "nome": nome,
                    "cnpj": cnpj,
                    "telefone": telefone,
                    "contato": contato,
                    "criado_por": st.session_state.usuario
                }
                if insert_data("fornecedores", dados):
                    st.success("✅ Fornecedor cadastrado!")
                    st.rerun()
    
    st.divider()
    df_fornecedores = get_data("fornecedores")
    if not df_fornecedores.empty:
        st.dataframe(df_fornecedores[["nome", "cnpj", "telefone", "contato"]], use_container_width=True, hide_index=True)

# ═══════════════════════════════════════════════════════════════════
# 7. OBRAS
# ═══════════════════════════════════════════════════════════════════
elif menu == "🏗️ OBRAS":
    st.markdown("<h1 class='main-title'>🏗️ Obras Cadastradas</h1>", unsafe_allow_html=True)
    
    with st.form("form_obra"):
        col1, col2 = st.columns(2)
        with col1:
            nome_obra = st.text_input("Nome da Obra")
            local = st.text_input("Local/Rodovia")
        with col2:
            contratante = st.text_input("Contratante")
            status = st.selectbox("Status", ["Em andamento", "Concluída", "Paralisada"])
        
        if st.form_submit_button("💾 CADASTRAR OBRA", use_container_width=True):
            if nome_obra:
                dados = {
                    "nome": nome_obra,
                    "rodovia": local,
                    "contratante": contratante,
                    "status": status,
                    "criado_por": st.session_state.usuario
                }
                if insert_data("obras", dados):
                    st.success("✅ Obra cadastrada!")
                    st.rerun()
    
    st.divider()
    df_obras = get_data("obras")
    if not df_obras.empty:
        st.dataframe(df_obras[["nome", "rodovia", "contratante", "status"]], use_container_width=True, hide_index=True)

# ═══════════════════════════════════════════════════════════════════
# 8. RELATÓRIOS
# ═══════════════════════════════════════════════════════════════════
elif menu == "📋 RELATÓRIOS":
    st.markdown("<h1 class='main-title'>📋 Relatórios e Fechamentos</h1>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        data_ini = st.date_input("Data Inicial", value=date.today().replace(day=1))
    with col2:
        data_fim = st.date_input("Data Final", value=date.today())
    
    st.divider()
    
    df_ab = get_data("abastecimentos")
    df_prod = get_data("producao")
    
    if not df_ab.empty:
        df_ab["data_dt"] = pd.to_datetime(df_ab["data"]).dt.date
        mask = (df_ab["data_dt"] >= data_ini) & (df_ab["data_dt"] <= data_fim)
        df_filtrado = df_ab[mask]
        
        total_litros = df_filtrado["quantidade"].sum() if "quantidade" in df_filtrado.columns else 0
        total_gasto = df_filtrado["total"].sum() if "total" in df_filtrado.columns else 0
        
        col1, col2, col3 = st.columns(3)
        col1.metric("⛽ Total de Litros", f"{total_litros:,.0f} L")
        col2.metric("💰 Total Gasto", f"R$ {total_gasto:,.2f}")
        col3.metric("📋 Registros", len(df_filtrado))
        
        st.dataframe(df_filtrado[["data", "prefixo", "motorista", "quantidade", "total"]].head(20), use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum dado encontrado.")

# ═══════════════════════════════════════════════════════════════════
# 9. USUÁRIOS (Admin apenas)
# ═══════════════════════════════════════════════════════════════════
elif "USUÁRIOS" in menu:
    if st.session_state.perfil != "Admin":
        st.error("⛔ Acesso restrito a administradores.")
    else:
        st.markdown("<h1 class='main-title'>👥 Usuários e Acessos</h1>", unsafe_allow_html=True)
        
        with st.form("form_usuario"):
            col1, col2 = st.columns(2)
            with col1:
                nome_user = st.text_input("Nome Completo")
                login_user = st.text_input("Login")
            with col2:
                senha_user = st.text_input("Senha", type="password")
                perfil_user = st.selectbox("Perfil", ["Operador", "Admin"])
            
            if st.form_submit_button("👤 CRIAR USUÁRIO", use_container_width=True):
                if nome_user and login_user and senha_user:
                    dados = {"nome": nome_user, "login": login_user, "senha": senha_user, "perfil": perfil_user}
                    if insert_data("usuarios", dados):
                        st.success("✅ Usuário criado!")
                        st.rerun()
        
        st.divider()
        df_usuarios = get_data("usuarios")
        if not df_usuarios.empty:
            st.dataframe(df_usuarios[["nome", "login", "perfil"]], use_container_width=True, hide_index=True)
