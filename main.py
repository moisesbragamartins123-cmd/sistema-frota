import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime, date
import plotly.express as px
import os
import time
import io
from fpdf import FPDF

# ═══════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO DA PÁGINA
# ═══════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="PavControl — COPA Engenharia",
    page_icon="🛣️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS GERAL DA APLICAÇÃO (DASHBOARD MODERNIZADO)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.main { background-color: #F4F7FB; }
[data-testid="stSidebar"] { background: #0F1923; }
[data-testid="stSidebar"] * { color: #C9D4E0 !important; }
[data-testid="stSidebar"] h3 { color: #1D9E75 !important; }
.stTextInput>label, .stSelectbox>label, .stNumberInput>label,
.stDateInput>label, .stTextArea>label {
    font-size: 12px !important; text-transform: uppercase;
    color: #475569; font-weight: 600; letter-spacing: 0.05em;
}
div.stButton > button:first-child {
    background: #1D9E75; color: white; border: none;
    border-radius: 8px; font-weight: 600; padding: .5rem 1.25rem;
    transition: all 0.3s ease;
}
div.stButton > button:first-child:hover { 
    background: #0F6E56; 
    box-shadow: 0 4px 12px rgba(29, 158, 117, 0.4);
}
div[data-testid="stForm"] {
    border: none; border-radius: 16px;
    padding: 2rem; background: white;
    box-shadow: 0 10px 30px rgba(0,0,0,0.08);
}
.banner-ok  { background:#EAF3DE; color:#3B6D11; border:1px solid #C0DD97; border-radius:10px; padding:12px 16px; font-weight:600; font-size:13px; margin-bottom:1rem; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }
.banner-low { background:#FAEEDA; color:#854F0B; border:1px solid #FAC775; border-radius:10px; padding:12px 16px; font-weight:600; font-size:13px; margin-bottom:1rem; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }
.banner-err { background:#FCEBEB; color:#A32D2D; border:1px solid #F0B0AE; border-radius:10px; padding:12px 16px; font-weight:600; font-size:13px; margin-bottom:1rem; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }
.banner-info{ background:#E6F1FB; color:#185FA5; border:1px solid #A8C9EE; border-radius:10px; padding:12px 16px; font-weight:600; font-size:13px; margin-bottom:1rem; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }
.kpi-box { background:white; border:none; border-radius:12px; padding:1.5rem; text-align:center; height:100%; box-shadow: 0 4px 15px rgba(0,0,0,0.04); transition: transform 0.2s ease; }
.kpi-box:hover { transform: translateY(-2px); box-shadow: 0 8px 20px rgba(0,0,0,0.08); }
.kpi-box h3 { margin:0; font-size:24px; color:#0F1923; margin-top: 10px; }
.kpi-box p  { margin:0; font-size:11px; color:#64748B; text-transform:uppercase; font-weight:700; letter-spacing: 0.05em; }
.kpi-verde { color:#1D9E75 !important; }
.kpi-rojo  { color:#A32D2D !important; }
.kpi-azul  { color:#185FA5 !important; }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════
# SUPABASE
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
        st.warning(f"⚠️ Erro ao buscar {table}: {e}")
        return pd.DataFrame()

def insert_data(table: str, data: dict) -> bool:
    try:
        supabase.table(table).insert(data).execute()
        return True
    except Exception as e:
        st.error(f"❌ Erro ao salvar: {e}"); return False

def delete_data(table: str, row_id) -> bool:
    try:
        supabase.table(table).delete().eq("id", row_id).execute()
        return True
    except Exception as e:
        st.error(f"❌ Erro ao excluir: {e}"); return False

def calcular_saldo(nome_tanque: str) -> float:
    df_ent = get_data("entradas_tanque")
    df_sai = get_data("abastecimentos")
    t_ent = 0.0
    if not df_ent.empty and "nome_tanque" in df_ent.columns:
        t_ent = pd.to_numeric(df_ent[df_ent["nome_tanque"]==nome_tanque]["quantidade"], errors="coerce").sum()
    t_sai = 0.0
    if not df_sai.empty and "nome_tanque" in df_sai.columns and "origem" in df_sai.columns:
        mask = (df_sai["origem"]=="Tanque Interno") & (df_sai["nome_tanque"]==nome_tanque)
        t_sai = pd.to_numeric(df_sai.loc[mask,"quantidade"], errors="coerce").sum()
    return float(t_ent) - float(t_sai)

def dia_semana_pt(d) -> str:
    dias = ["Segunda","Terça","Quarta","Quinta","Sexta","Sábado","Domingo"]
    try:
        if isinstance(d, str): d = datetime.strptime(d[:10],"%Y-%m-%d")
        return dias[d.weekday()]
    except: return ""

# ═══════════════════════════════════════════════════════════════════
# EXPORTAÇÃO — EXCEL PADRÃO COPA E PDF (Suas funções originais continuam aqui)
# ═══════════════════════════════════════════════════════════════════

# (Mantenha as suas funções gerar_excel_copa, gerar_excel_tanque, gerar_excel_limpo e gerar_pdf originais aqui)
# Para economizar espaço no chat, pulei o bloco gigantesco delas, 
# mas você DEVE deixá-las exatamente onde estão no seu arquivo!

# ═══════════════════════════════════════════════════════════════════
# LOGIN — ESTRUTURA VISUAL E CSS CONDICIONAL (A MÁGICA DA TELA INICIAL)
# ═══════════════════════════════════════════════════════════════════
for k,v in [("logged_in",False),("usuario_logado",""),("perfil_logado","")]:
    if k not in st.session_state: st.session_state[k]=v

if not st.session_state.logged_in:
    # Injeta a imagem de fundo de rodovia apenas na tela de login
    st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(rgba(15, 25, 35, 0.7), rgba(15, 25, 35, 0.7)), url('https://images.unsplash.com/photo-1463171379579-3fdfb86d6285?q=80&w=2070') no-repeat center center fixed !important;
        background-size: cover !important;
    }
    [data-testid="stHeader"] { background: transparent !important; }
    [data-testid="stSidebar"] { display: none; } /* Esconde sidebar no login */
    </style>
    """, unsafe_allow_html=True)
    
    st.write("<br><br><br>", unsafe_allow_html=True)
    
    # Caixinha centralizada do login
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        with st.form("login"):
            if os.path.exists("logo.png"): 
                col_l1, col_l2, col_l3 = st.columns([1, 1.5, 1])
                with col_l2:
                    st.image("logo.png", use_container_width=True)
            
            st.markdown("<h2 style='text-align:center;color:#1E293B;font-weight:700;margin-bottom:1.5rem;'>Acesso Restrito</h2>", unsafe_allow_html=True)
            
            u = st.text_input("Usuário")
            p = st.text_input("Senha", type="password")
            
            st.write("<br>", unsafe_allow_html=True)
            if st.form_submit_button("ENTRAR NO SISTEMA", use_container_width=True):
                try:
                    res=supabase.table("usuarios").select("*").eq("login",u).eq("senha",p).execute()
                    if res.data:
                        st.session_state.logged_in=True
                        st.session_state.usuario_logado=res.data[0]["nome"]
                        st.session_state.perfil_logado=res.data[0]["perfil"]
                        st.rerun()
                    else: st.error("❌ Usuário ou senha incorretos.")
                except:
                    # Fallback secrets
                    if u==st.secrets.get("ADMIN_USER","admin") and p==st.secrets.get("ADMIN_PASS","obra2026"):
                        st.session_state.logged_in=True; st.session_state.usuario_logado="Admin"; st.session_state.perfil_logado="Admin"; st.rerun()
                    else: st.error("❌ Usuário ou senha incorretos.")
    st.stop()

# ═══════════════════════════════════════════════════════════════════
# SIDEBAR (ESQUERDA)
# ═══════════════════════════════════════════════════════════════════
with st.sidebar:
    if os.path.exists("logo.png"):
        c1,c2,c3=st.columns([1,2,1])
        with c2: st.image("logo.png",use_container_width=True)
    st.markdown(f"<div style='text-align:center;color:#1D9E75;font-size:13px;font-weight:bold;'>👤 {st.session_state.usuario_logado}</div>",unsafe_allow_html=True)
    st.divider()
    opcoes=["🏠 Painel Início","⛽ Lançar Abastecimento","🛢️ Tanques / Estoque",
            "🚚 Boletim de Transporte","🚜 Frota e Equipamentos",
            "🏪 Fornecedores","🏗️ Obras Cadastradas","📋 Relatórios e Fechamentos"]
    if st.session_state.perfil_logado=="Admin": opcoes.append("👥 Usuários e Acessos")
    menu=st.sidebar.radio("",opcoes,label_visibility="collapsed")
    st.divider()
    if st.button("🚪 Sair",use_container_width=True):
        st.session_state.logged_in=False; st.session_state.usuario_logado=""; st.session_state.perfil_logado=""; st.rerun()
    st.caption("☁️ Supabase — Tempo Real")


# ════════════════════════════════════════════════════════════════════════════
# 1. PAINEL INÍCIO (DASHBOARD E KPIs)
# ════════════════════════════════════════════════════════════════════════════
if menu == "🏠 Painel Início":
    st.markdown("## 🏠 Centro de Comando da Obra")
    
    df_tanques = get_data("tanques")
    df_abast = get_data("abastecimentos")
    df_prod = get_data("producao")
    
    # Exibe saldos dos tanques reais
    if not df_tanques.empty:
        st.subheader("Situação Real dos Tanques/Comboios (Estoque Físico)")
        cols_t = st.columns(len(df_tanques))
        for idx, row in df_tanques.iterrows():
            nome_t = row['nome']
            cap_t = float(row.get('capacidade', 0))
            saldo_t = calcular_saldo_especifico(nome_t)
            
            with cols_t[idx]:
                if saldo_t <= ((cap_t * 0.15) if cap_t > 0 else 500):
                    st.markdown(f"<div class='banner-low'>⚠️ <strong>{nome_t}</strong><br>Saldo Baixo: {saldo_t:,.1f} L</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='banner-ok'>✅ <strong>{nome_t}</strong><br>Saldo Normal: {saldo_t:,.1f} L</div>", unsafe_allow_html=True)

    st.divider()
    
    # Filtro por Intervalo de Datas
    st.markdown("#### 📅 Filtrar Indicadores por Período")
    c_dt1, c_dt2 = st.columns(2)
    data_inicio = c_dt1.date_input("Data Inicial", value=date.today().replace(day=1))
    data_fim = c_dt2.date_input("Data Final", value=date.today())
    
    # Processamento dos Dados do Período
    t_gasto = 0
    t_litros = 0
    t_carradas = 0
    t_toneladas_geral = 0
    t_toneladas_cbuq = 0
    t_frete_rs = 0
    
    if not df_abast.empty:
        df_abast['data_dt'] = pd.to_datetime(df_abast['data'], errors='coerce').dt.date
        df_a_filt = df_abast[(df_abast['data_dt'] >= data_inicio) & (df_abast['data_dt'] <= data_fim)]
        t_gasto = pd.to_numeric(df_a_filt['total'], errors='coerce').sum()
        t_litros = pd.to_numeric(df_a_filt['quantidade'], errors='coerce').sum()
    else:
        df_a_filt = pd.DataFrame()
        
    if not df_prod.empty:
        df_prod['data_dt'] = pd.to_datetime(df_prod['data'], errors='coerce').dt.date
        df_p_filt = df_prod[(df_prod['data_dt'] >= data_inicio) & (df_prod['data_dt'] <= data_fim)]
        t_carradas = pd.to_numeric(df_p_filt['carradas'], errors='coerce').sum()
        t_toneladas_geral = pd.to_numeric(df_p_filt['toneladas'], errors='coerce').sum()
        t_frete_rs = pd.to_numeric(df_p_filt['valor_frete'], errors='coerce').sum()
        
        # Filtra apenas o Asfalto (CBUQ) para KPIs específicos
        df_cbuq = df_p_filt[df_p_filt['tipo_operacao'].isin(["Transporte de Massa/CBUQ", "Venda de Massa"])]
        t_toneladas_cbuq = pd.to_numeric(df_cbuq['toneladas'], errors='coerce').sum()
    else:
        df_p_filt = pd.DataFrame()

    st.write("<br>", unsafe_allow_html=True)
    
    # Linha 1 de Indicadores: Resumo Geral
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f"<div class='caixa-resumo'><p>Gasto Combustível</p><h3 style='color:#A32D2D;'>R$ {t_gasto:,.2f}</h3></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='caixa-resumo'><p>Total Produzido (CBUQ)</p><h3>{t_toneladas_cbuq:,.1f} Ton</h3></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='caixa-resumo'><p>Volume Transportado (Geral)</p><h3>{t_toneladas_geral:,.1f} Ton</h3></div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='caixa-resumo'><p>Viagens Realizadas</p><h3>{int(t_carradas)} Carradas</h3></div>", unsafe_allow_html=True)

    st.write("<br>", unsafe_allow_html=True)
    
    # Linha 2 de Indicadores: KPIs de Engenharia
    st.markdown("#### ⚙️ Indicadores de Eficiência Logística (KPIs)")
    c5, c6, c7 = st.columns(3)
    
    custo_por_ton = (t_gasto / t_toneladas_cbuq) if t_toneladas_cbuq > 0 else 0
    litros_por_ton = (t_litros / t_toneladas_cbuq) if t_toneladas_cbuq > 0 else 0
    litros_por_carrada = (t_litros / t_carradas) if t_carradas > 0 else 0
    
    c5.markdown(f"<div class='caixa-resumo'><p>Custo Diesel / Ton CBUQ</p><h3 class='kpi-destaque'>R$ {custo_por_ton:,.2f}</h3></div>", unsafe_allow_html=True)
    c6.markdown(f"<div class='caixa-resumo'><p>Consumo Litros / Ton CBUQ</p><h3 class='kpi-destaque'>{litros_por_ton:,.2f} L</h3></div>", unsafe_allow_html=True)
    c7.markdown(f"<div class='caixa-resumo'><p>Gasto Médio / Carrada</p><h3 class='kpi-destaque'>{litros_por_carrada:,.1f} L</h3></div>", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# 2. ABASTECIMENTO (COM RASTREIO DE USUÁRIO E MOTORISTA PADRÃO)
# ════════════════════════════════════════════════════════════════════════════
elif menu == "⛽ Lançar Abastecimento":
    st.markdown("## ⛽ Lançar Saída de Combustível")
    df_v = get_data("veiculos")
    df_f = get_data("fornecedores")
    df_a = get_data("abastecimentos")
    df_t = get_data("tanques")
    
    if df_v.empty:
        st.warning("⚠️ Cadastre veículos na aba 'Frota e Equipamentos'.")
    else:
        # Puxa informações do veículo selecionado para autopreencher campos
        v_sel = st.selectbox("Máquina / Caçamba", df_v['prefixo'].tolist())
        info_v = df_v[df_v['prefixo'] == v_sel].iloc[0]
        comb_padrao = info_v.get('tipo_combustivel_padrao', 'Não definido')
        motorista_padrao = info_v.get('motorista', '')
        
        # Puxa o último horímetro para ajudar quem digita
        m_horimetro = 0.0
        if not df_a.empty and 'horimetro' in df_a.columns:
            hist = df_a[df_a['prefixo'] == v_sel]
            if not hist.empty:
                m_horimetro = float(hist['horimetro'].max())
            
        st.info(f"⛽ Combustível: **{comb_padrao}** | ⏱️ Último Horímetro/Km: **{m_horimetro}**")
        
        origem = st.radio("Origem do Combustível:", ["Posto Externo", "Tanque Interno"], horizontal=True)

        with st.form("f_lanc"):
            c1, c2, c3 = st.columns([1, 2, 2])
            ficha = c1.text_input("Nº Ficha / Cupom")
            
            if origem == "Posto Externo":
                posto = c2.selectbox("Posto Fornecedor", df_f['nome'].tolist() if not df_f.empty else ["Sem cadastro"])
                n_tanque_sel = None
            else:
                n_tanque_sel = c2.selectbox("Tanque de Origem", df_t['nome'].tolist() if not df_t.empty else ["Sem cadastro"])
                posto = "Estoque Próprio"
            
            data_abast = c3.date_input("Data do Abastecimento")
            
            c_m1, c_m2 = st.columns([2, 2])
            # Autopreenchimento Inteligente do Motorista
            motorista_abast = c_m1.text_input("Motorista", value=motorista_padrao)
            hor_atual = c_m2.number_input("KM / Horímetro Atual", min_value=0.0, value=m_horimetro)
            
            c4, c5, c6 = st.columns(3)
            litros = c4.number_input("Litros", min_value=0.0)
            preco = c5.number_input("Preço Unitário (R$)", min_value=0.0)
            obs = c6.text_input("Observações / Obra")
            
            if st.form_submit_button("💾 Salvar Abastecimento", use_container_width=True):
                saldo_t = calcular_saldo_especifico(n_tanque_sel) if n_tanque_sel else 0
                
                if litros <= 0:
                    st.error("⚠️ Litros devem ser maior que zero.")
                elif origem == "Tanque Interno" and litros > saldo_t:
                    st.error(f"⚠️ Saldo insuficiente! (Tem {saldo_t}L)")
                else:
                    supabase.table("abastecimentos").insert({
                        "data": str(data_abast),
                        "numero_ficha": ficha,
                        "origem": origem,
                        "nome_tanque": n_tanque_sel, 
                        "prefixo": v_sel,
                        "motorista": motorista_abast.upper(),
                        "quantidade": litros,
                        "valor_unitario": preco, 
                        "total": litros * preco,
                        "fornecedor": posto,
                        "horimetro": hor_atual,
                        "observacao": obs,
                        "criado_por": st.session_state.usuario_logado # Registra a auditoria
                    }).execute()
                    
                    st.success("✅ Salvo com sucesso!")
                    time.sleep(1)
                    st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# 3. TANQUES E ESTOQUE
# ════════════════════════════════════════════════════════════════════════════
elif menu == "🛢️ Tanques / Estoque":
    st.markdown("## 🛢️ Gestão de Estoque Interno")
    t_visao, t_entrada, t_config = st.tabs(["📊 Saldo Real", "📥 Receber Compra (Entrada)", "⚙️ Configurar"])
    
    with t_config:
        with st.form("f_t"):
            n_t = st.text_input("Nome do Tanque")
            c_t = st.number_input("Capacidade Total (L)", min_value=0.0)
            
            if st.form_submit_button("Salvar Tanque") and n_t:
                supabase.table("tanques").insert({"nome": n_t, "capacidade": c_t}).execute()
                st.rerun()
                
        df_t = get_data("tanques")
        for _, r in df_t.iterrows():
            c1, c2 = st.columns([4,1])
            c1.write(f"🛢️ **{r['nome']}** | Capacidade: {r.get('capacidade',0)} L")
            if c2.button("Excluir", key=f"d_{r['id']}"):
                supabase.table("tanques").delete().eq("id", r['id']).execute()
                st.rerun()
            
    with t_entrada:
        df_t = get_data("tanques")
        df_f = get_data("fornecedores")
        
        if df_t.empty:
            st.warning("Cadastre um tanque primeiro.")
        else:
            with st.form("f_ent"):
                c1, c2 = st.columns(2)
                d_ent = c1.date_input("Data de Recebimento")
                t_dest = c2.selectbox("Tanque Destino", df_t['nome'].tolist())
                
                c3, c4 = st.columns(2)
                forn_ent = c3.selectbox("Distribuidora", df_f['nome'].tolist() if not df_f.empty else ["N/A"])
                nf_ent = c4.text_input("Nº Nota Fiscal")
                
                c5, c6 = st.columns(2)
                q_ent = c5.number_input("Litros", min_value=0.0)
                p_ent = c6.number_input("Preço R$/L", min_value=0.0)
                
                if st.form_submit_button("📥 Confirmar Entrada", use_container_width=True):
                    supabase.table("entradas_tanque").insert({
                        "data": str(d_ent),
                        "nome_tanque": t_dest,
                        "fornecedor": forn_ent,
                        "numero_ficha": nf_ent,
                        "quantidade": q_ent, 
                        "valor_unitario": p_ent,
                        "total": q_ent * p_ent, 
                        "criado_por": st.session_state.usuario_logado # Registra a auditoria
                    }).execute()
                    
                    st.success("✅ Estoque atualizado com sucesso!")
                    time.sleep(1)
                    st.rerun()
                    
    with t_visao:
        for _, r in get_data("tanques").iterrows():
            nm = r['nome']
            cp = float(r.get('capacidade', 0))
            sd = calcular_saldo_especifico(nm)
            
            with st.expander(f"📊 {nm} - Saldo Atual: {sd:,.1f} L", expanded=True):
                st.progress(max(min(sd/cp,1),0) if cp>0 else 0)


# ════════════════════════════════════════════════════════════════════════════
# 4. LOGÍSTICA DE PRODUÇÃO / FRETE (COM RASTREIO E MOTORISTA PADRÃO)
# ════════════════════════════════════════════════════════════════════════════
elif menu == "🚚 Boletim de Transporte":
    st.markdown("## 🚚 Boletim de Transporte e Logística")
    df_v = get_data("veiculos")
    
    st.markdown("#### Registrar Boletim Diário")
    # A escolha da caçamba fora do Form permite atualizar a página para buscar o motorista correto
    cacamba_sel = st.selectbox("Selecione o Veículo / Caçamba", df_v['prefixo'].tolist() if not df_v.empty else ["Sem cadastro"])
    
    motorista_padrao = ""
    if not df_v.empty and cacamba_sel != "Sem cadastro":
        motorista_padrao = df_v[df_v['prefixo'] == cacamba_sel].iloc[0].get('motorista', '')

    with st.form("f_prod", clear_on_submit=True):
        c1, c2, c_tp = st.columns([1, 1.5, 1.5])
        data_pr = c1.date_input("Data do Transporte")
        
        # O sistema sugere o Motorista Padrão, mas permite alteração
        motorista = c2.text_input("Motorista (Para Acerto Financeiro)", value=motorista_padrao)
        
        tipo_op = c_tp.selectbox("Tipo de Operação", [
            "Transporte de Massa/CBUQ",
            "Transporte de Agregado (Jazida)",
            "Venda de Massa",
            "Remoção de Entulho/Fresado",
            "Outros"
        ])
        
        c4, c5 = st.columns(2)
        origem = c4.text_input("Local de Origem (Ex: Usina, Jazida Santa Maria)")
        destino = c5.text_input("Local de Destino (Ex: Obra BR-101, Balança Cliente)")
        
        c6, c7 = st.columns(2)
        material = c6.text_input("Material Transportado (Ex: CBUQ, Brita 1)")
        carradas = c7.number_input("Número de Carradas / Viagens", min_value=0, step=1)
        
        c8, c9, c10 = st.columns(3)
        toneladas = c8.number_input("Toneladas Totais (Obrigatório para KPI)", min_value=0.0)
        v_frete = c9.number_input("Valor Frete/Ton ou Diária (R$)", min_value=0.0)
        obs = c10.text_input("Observações / Comprador")
        
        if st.form_submit_button("💾 Salvar Lançamento Logístico", use_container_width=True):
            if not motorista:
                st.error("⚠️ Digite o nome do motorista!")
            else:
                v_total = toneladas * v_frete if v_frete > 0 else 0 
                
                supabase.table("producao").insert({
                    "data": str(data_pr),
                    "motorista": motorista.strip().upper(),
                    "veiculo": cacamba_sel,
                    "tipo_operacao": tipo_op,
                    "origem": origem,
                    "destino": destino,
                    "material": material,
                    "carradas": carradas,
                    "toneladas": toneladas, 
                    "valor_frete": v_total,
                    "observacao": obs,
                    "criado_por": st.session_state.usuario_logado # Registra auditoria
                }).execute()
                
                st.success("✅ Logística registrada com sucesso!")
                time.sleep(1)
                st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# 5. FROTA E EQUIPAMENTOS
# ════════════════════════════════════════════════════════════════════════════
elif menu == "🚜 Frota e Equipamentos":
    st.markdown("## 🚜 Gestão de Máquinas e Veículos")
    tf1, tf2 = st.tabs(["🚜 Frota Ativa", "📂 Categorias e Classes"])
    
    with tf2:
        with st.form("fc"):
            nc = st.text_input("Nova Categoria (Ex: Caçamba Traçada, Escavadeira)")
            if st.form_submit_button("Salvar Categoria") and nc:
                supabase.table("classes_frota").insert({"nome": nc}).execute()
                st.rerun()
                
        df_c = get_data("classes_frota")
        for _, r in df_c.iterrows():
            c1, c2 = st.columns([4, 1])
            c1.write(f"• {r['nome']}")
            if c2.button("Excluir", key=f"dc_{r['id']}"):
                supabase.table("classes_frota").delete().eq("id", r['id']).execute()
                st.rerun()
            
    with tf1:
        df_c = get_data("classes_frota")
        with st.form("fv"):
            c1, c2 = st.columns(2)
            px = c1.text_input("Prefixo (Ex: CB-01)")
            pl = c2.text_input("Placa do Veículo")
            
            c3, c4 = st.columns(2)
            cl = c3.selectbox("Categoria", df_c['nome'].tolist() if not df_c.empty else ["N/A"])
            comb = c4.selectbox("Combustível Padrão", ["Diesel S10", "Diesel S500", "Gasolina", "Arla 32"])
            
            mot = st.text_input("Operador ou Motorista Fixo (Padrão)")
            
            if st.form_submit_button("Salvar Novo Veículo"):
                supabase.table("veiculos").insert({
                    "prefixo": px,
                    "placa": pl,
                    "classe": cl,
                    "tipo_combustivel_padrao": comb,
                    "motorista": mot.upper()
                }).execute()
                st.rerun()
                
        df_v = get_data("veiculos")
        for _, r in df_v.iterrows():
            with st.expander(f"🚜 {r['prefixo']} | Placa: {r.get('placa','')} | Classe: {r.get('classe','N/A')}"):
                st.write(f"**Motorista:** {r.get('motorista', 'N/A')} | **Combustível:** {r.get('tipo_combustivel_padrao','')}")
                if st.button("Remover Veículo", key=f"dv_{r['id']}"):
                    supabase.table("veiculos").delete().eq("id", r['id']).execute()
                    st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# 6. FORNECEDORES
# ════════════════════════════════════════════════════════════════════════════
elif menu == "🏪 Fornecedores":
    st.markdown("## 🏪 Postos Fornecedores e Bancos")
    
    with st.form("ff"):
        c1, c2 = st.columns(2)
        n = c1.text_input("Nome Fantasia do Posto")
        rz = c2.text_input("Razão Social")
        
        c3, c4, c5, c6 = st.columns(4)
        bc = c3.text_input("Banco")
        ag = c4.text_input("Agência")
        cc = c5.text_input("Conta")
        px = c6.text_input("Chave PIX")
        
        if st.form_submit_button("Salvar Fornecedor"):
            supabase.table("fornecedores").insert({
                "nome": n,
                "razao_social": rz,
                "banco": bc,
                "agencia": ag,
                "conta": cc,
                "pix": px
            }).execute()
            st.rerun()
            
    df_f = get_data("fornecedores")
    for _, r in df_f.iterrows():
        with st.expander(f"🏪 {r['nome'].upper()}"):
            st.write(f"Banco: {r.get('banco', '')} | Ag: {r.get('agencia', '')} | Conta: {r.get('conta', '')} | PIX: {r.get('pix', '')}")
            if st.button("Remover Fornecedor", key=f"df_{r['id']}"):
                supabase.table("fornecedores").delete().eq("id", r['id']).execute()
                st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# 7. USUÁRIOS E ACESSOS (SÓ PARA ADMIN)
# ════════════════════════════════════════════════════════════════════════════
elif menu == "👥 Usuários e Acessos":
    st.markdown("## 👥 Gestão de Usuários")
    st.info("Crie contas para seus apontadores e engenheiros. O sistema registrará tudo o que eles digitarem (Auditoria).")
    
    with st.form("f_user", clear_on_submit=True):
        c1, c2 = st.columns(2)
        n_user = c1.text_input("Nome Completo do Colaborador")
        l_user = c2.text_input("Login (Ex: joao.silva)")
        
        c3, c4 = st.columns(2)
        s_user = c3.text_input("Senha", type="password")
        p_user = c4.selectbox("Perfil de Acesso", ["Operador", "Admin"])
        
        if st.form_submit_button("Salvar Novo Usuário"):
            if n_user and l_user and s_user:
                supabase.table("usuarios").insert({
                    "nome": n_user,
                    "login": l_user,
                    "senha": s_user,
                    "perfil": p_user
                }).execute()
                st.success("✅ Usuário criado com sucesso!")
                st.rerun()
            else:
                st.error("Preencha todos os campos obrigatórios.")
                
    st.markdown("#### Usuários Cadastrados")
    df_u = get_data("usuarios")
    if not df_u.empty:
        for _, r in df_u.iterrows():
            c1, c2 = st.columns([4, 1])
            c1.write(f"👤 **{r['nome']}** | Login: `{r['login']}` | Perfil: {r['perfil']}")
            if r['login'] != 'admin': # Trava de segurança para não apagar o master
                if c2.button("Excluir", key=f"du_{r['id']}"):
                    supabase.table("usuarios").delete().eq("id", r['id']).execute()
                    st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# 8. RELATÓRIOS E FECHAMENTOS (COM RASTREABILIDADE DE AUDITORIA)
# ════════════════════════════════════════════════════════════════════════════
elif menu == "📋 Relatórios e Fechamentos":
    st.markdown("## 📋 Central de Relatórios e Acertos")
    
    # Filtro de Data Global para os Relatórios
    st.markdown("#### 📅 Período de Apuração")
    c_dt1, c_dt2 = st.columns(2)
    data_inicio = c_dt1.date_input("Data Inicial", value=date.today().replace(day=1))
    data_fim = c_dt2.date_input("Data Final", value=date.today())
    st.divider()

    df_s = get_data("abastecimentos")
    df_prod = get_data("producao")
    df_f = get_data("fornecedores")
    
    # Aplica o Filtro de Datas em todo o cruzamento de relatórios
    if not df_s.empty:
        df_s['data_dt'] = pd.to_datetime(df_s['data'], errors='coerce').dt.date
        df_s_filt = df_s[(df_s['data_dt'] >= data_inicio) & (df_s['data_dt'] <= data_fim)].fillna("")
    else:
        df_s_filt = pd.DataFrame()
        
    if not df_prod.empty:
        df_prod['data_dt'] = pd.to_datetime(df_prod['data'], errors='coerce').dt.date
        df_prod_filt = df_prod[(df_prod['data_dt'] >= data_inicio) & (df_prod['data_dt'] <= data_fim)].fillna("")
    else:
        df_prod_filt = pd.DataFrame()
    
    t_acerto, t_postos, t_dinamica = st.tabs(["👷 Acerto de Motoristas", "📤 Fechar Postos", "📊 Tabelas (Auditoria)"])

    # --- ABA: ACERTO DE MOTORISTAS ---
    with t_acerto:
        if not df_prod_filt.empty and not df_s_filt.empty:
            
            todos_motoristas = sorted(df_prod_filt['motorista'].dropna().unique().tolist())
            mot_sel = st.selectbox("Selecione o Motorista:", ["Selecione..."] + todos_motoristas)
            
            if mot_sel != "Selecione..." and st.button("Calcular Acerto Final do Período", use_container_width=True):
                # O que ele faturou
                prod_mot = df_prod_filt[df_prod_filt['motorista'] == mot_sel]
                ganho_bruto = pd.to_numeric(prod_mot['valor_frete']).sum()
                
                # Caçambas que ele pilotou no período
                cacambas_usadas = prod_mot['veiculo'].unique().tolist()
                
                # O que ele gastou de Diesel
                abast_mot = df_s_filt[(df_s_filt['prefixo'].isin(cacambas_usadas)) | (df_s_filt['motorista'] == mot_sel)]
                custo_diesel = pd.to_numeric(abast_mot['total']).sum()
                
                c1, c2, c3 = st.columns(3)
                c1.markdown(f"<div class='caixa-resumo'><p>Fretes Realizados</p><h3 style='color:#1D9E75;'>R$ {ganho_bruto:,.2f}</h3></div>", unsafe_allow_html=True)
                c2.markdown(f"<div class='caixa-resumo'><p>Desconto Diesel</p><h3 style='color:#A32D2D;'>- R$ {custo_diesel:,.2f}</h3></div>", unsafe_allow_html=True)
                c3.markdown(f"<div class='caixa-resumo'><p>Líquido a Receber</p><h3 style='color:#0F1923;'>R$ {ganho_bruto - custo_diesel:,.2f}</h3></div>", unsafe_allow_html=True)
                
                st.write("**Extrato de Viagens / Produção:**")
                st.dataframe(prod_mot[['data', 'veiculo', 'origem', 'destino', 'material', 'toneladas', 'carradas', 'valor_frete', 'criado_por']])
        else:
            st.info("Nenhum registro encontrado neste período.")

    # --- ABA: FECHAMENTO DE POSTOS ---
    with t_postos:
        c_p1, c_p2 = st.columns(2)
        col_p = c_p1.selectbox("Selecione o Posto:", df_f['nome'].tolist() if not df_f.empty else [])
        mes_p = c_p2.text_input("Período p/ Cabeçalho do PDF", f"{data_inicio.strftime('%d/%m/%Y')} A {data_fim.strftime('%d/%m/%Y')}")
        
        if st.button("Gerar Fechamento do Posto (PDF e Excel)"):
            if not df_s_filt.empty:
                df_p = df_s_filt[df_s_filt['fornecedor'] == col_p]
                dados_posto = df_f[df_f['nome'] == col_p].iloc[0].to_dict() if not df_f.empty else {"nome": col_p}
                
                pdf_bytes = gerar_pdf_relatorio(df_p, "SAIDAS", "OBRA DE PAVIMENTAÇÃO", "FECHAMENTO DE CONSUMO", f"PERÍODO: {mes_p}", {"FORNECEDOR": col_p, "PIX": dados_posto.get('pix','')}, f"CONTROLE DE ABASTECIMENTO - {col_p}")
                st.download_button("⬇️ Baixar PDF Timbrado", pdf_bytes, f"Fechamento_Posto_{col_p}.pdf", "application/pdf")
                
                xls_bytes = gerar_excel_com_template(df_p, dados_posto, mes_p, "OBRA DE PAVIMENTAÇÃO")
                st.download_button("⬇️ Baixar Excel (Template)", xls_bytes, f"Fechamento_Posto_{col_p}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # --- ABA: AUDITORIA E TABELA DINÂMICA ---
    with t_dinamica:
        st.write("Tabela completa com a coluna **'Digitado Por'** para auditoria rigorosa de lançamentos.")
        if not df_s_filt.empty:
            df_s_geral = df_s_filt.copy()
            
            # Reordena para calcular o consumo inteligente por Horímetro
            df_s_geral['data_hora'] = pd.to_datetime(df_s_geral['data'], errors='coerce')
            df_s_geral['horimetro_n'] = pd.to_numeric(df_s_geral['horimetro'], errors='coerce').fillna(0)
            df_s_geral = df_s_geral.sort_values(by=['prefixo', 'data_hora', 'horimetro_n'])
            
            df_s_geral['h_ant'] = df_s_geral.groupby('prefixo')['horimetro_n'].shift(1)
            df_s_geral['horas_trabalhadas'] = df_s_geral['horimetro_n'] - df_s_geral['h_ant']
            df_s_geral['consumo_l_h'] = df_s_geral.apply(lambda r: round(r['quantidade']/r['horas_trabalhadas'], 2) if pd.notna(r['horas_trabalhadas']) and r['horas_trabalhadas']>0 else None, axis=1)
            
            # Formatação de nomes de Coluna
            n_cols = {
                'data':'Data', 'origem':'Origem', 'nome_tanque':'Tanque', 'numero_ficha':'Ficha',
                'fornecedor':'Posto', 'prefixo':'Prefixo', 'motorista':'Operador', 'tipo_combustivel':'Produto',
                'quantidade':'Litros', 'total':'Total R$', 'horimetro':'Horímetro', 'consumo_l_h':'Consumo L/H',
                'criado_por':'Digitado Por'
            }
            df_final = df_s_geral.rename(columns={k:v for k,v in n_cols.items() if k in df_s_geral.columns})
            
            st.dataframe(df_final, use_container_width=True)
            
            xls_geral = exportar_excel_limpo(df_final, "Auditoria_Frota")
            st.download_button("⬇️ Baixar Tabela de Auditoria (Excel)", xls_geral, "Auditoria_Frota_Completa.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
