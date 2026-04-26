import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime, date
import plotly.express as px
import os
import time
import io
from fpdf import FPDF

# ─── PÁGINA E ESTÉTICA PREMIUM ──────────────────────────────────────────────
st.set_page_config(page_title="PavControl — COPA Engenharia", page_icon="🛣️", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.main { background-color: #F5F7FA; }

/* Barra Lateral Escura */
[data-testid="stSidebar"] { background: #0F1923; }
[data-testid="stSidebar"] * { color: #C9D4E0 !important; }
[data-testid="stSidebar"] .stRadio label { font-size: 13px !important; }
[data-testid="stSidebar"] h3 { color: #1D9E75 !important; font-size: 15px !important; }

/* Formulários e Inputs */
.stTextInput>label, .stSelectbox>label, .stNumberInput>label, .stDateInput>label {
    font-size: 11px !important; text-transform: uppercase; color: #6B7A8D; font-weight: 600; letter-spacing: 0.05em;
}

div.stButton > button:first-child {
    background-color: #1D9E75; color: white; border: none; border-radius: 8px; font-weight: 600; padding: 0.5rem 1.25rem; transition: 0.2s;
}
div.stButton > button:first-child:hover { background-color: #0F6E56; color: white;}

div[data-testid="stForm"] {
    border: 1px solid #E2E8F0; border-radius: 12px; padding: 1.25rem 1.5rem; background: white; box-shadow: 0 1px 4px rgba(0,0,0,.04);
}

/* Banners e Resumos */
.banner-ok  { background:#EAF3DE; color:#3B6D11; border:1px solid #C0DD97; border-radius:8px; padding:10px 14px; font-weight:600; font-size:13px; margin-bottom:1rem; }
.banner-low { background:#FAEEDA; color:#854F0B; border:1px solid #FAC775; border-radius:8px; padding:10px 14px; font-weight:600; font-size:13px; margin-bottom:1rem; }
.banner-err { background:#FCEBEB; color:#A32D2D; border:1px solid #F0B0AE; border-radius:8px; padding:10px 14px; font-weight:600; font-size:13px; margin-bottom:1rem; }

.caixa-resumo { background: white; border: 1px solid #E2E8F0; border-radius: 10px; padding: 1rem; text-align: center; height: 100%;}
.caixa-resumo h3 { margin:0; font-size: 22px; color: #0F1923; }
.caixa-resumo p { margin:0; font-size: 11px; color: #6B7A8D; text-transform: uppercase; font-weight: bold;}
.kpi-destaque { color: #1D9E75; font-size: 24px !important; }
</style>
""", unsafe_allow_html=True)

# ─── BANCO DE DADOS SUPABASE ────────────────────────────────────────────────
@st.cache_resource
def get_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = get_supabase()

def get_data(table: str) -> pd.DataFrame:
    try:
        res = supabase.table(table).select("*").execute()
        return pd.DataFrame(res.data)
    except Exception as e:
        return pd.DataFrame()

def calcular_saldo_especifico(nome_tanque):
    df_ent = get_data("entradas_tanque")
    df_sai = get_data("abastecimentos")
    t_ent = pd.to_numeric(df_ent[df_ent['nome_tanque'] == nome_tanque]['quantidade']).sum() if not df_ent.empty and 'nome_tanque' in df_ent.columns else 0
    t_sai = pd.to_numeric(df_sai[(df_sai['origem'] == 'Tanque Interno') & (df_sai['nome_tanque'] == nome_tanque)]['quantidade']).sum() if not df_sai.empty and 'nome_tanque' in df_sai.columns else 0
    return t_ent - t_sai

# ─── MOTORES DE EXPORTAÇÃO (PDF & EXCEL) ────────────────────────────────────
def gerar_excel_com_template(df, dados_fornecedor, periodo_str, obra_str):
    df = df.fillna("")
    template_path = "template_posto.xlsx"
    dias_pt = {0: 'SEG', 1: 'TER', 2: 'QUA', 3: 'QUI', 4: 'SEX', 5: 'SÁB', 6: 'DOM'}
    
    if os.path.exists(template_path):
        from openpyxl import load_workbook
        wb = load_workbook(template_path)
        ws = wb.active
        ws['D1'] = obra_str.upper()
        ws['D3'] = periodo_str.upper()
        ws['J1'] = dados_fornecedor.get('razao_social', dados_fornecedor.get('nome', '')).upper()
        ws['J2'] = dados_fornecedor.get('agencia', '')
        ws['J3'] = dados_fornecedor.get('conta', '')
        ws['M1'] = dados_fornecedor.get('pix', '')
        ws['M2'] = dados_fornecedor.get('tipo_conta', '')
        ws['M3'] = dados_fornecedor.get('banco', '')
        
        linha_inicio = 8
        for index, row in df.iterrows():
            dia_str = ""
            data_val = str(row.get('data',''))[:10]
            try:
                if data_val: dia_str = dias_pt[datetime.strptime(data_val, '%Y-%m-%d').weekday()]
            except: pass

            ws.cell(row=linha_inicio+index, column=1, value=data_val)
            ws.cell(row=linha_inicio+index, column=2, value=dia_str)
            ws.cell(row=linha_inicio+index, column=3, value=str(row.get('numero_ficha','')))
            ws.cell(row=linha_inicio+index, column=4, value=str(row.get('placa','')))
            ws.cell(row=linha_inicio+index, column=5, value=str(row.get('prefixo','')))
            ws.cell(row=linha_inicio+index, column=6, value=str(row.get('motorista','')))
            ws.cell(row=linha_inicio+index, column=7, value=str(row.get('fornecedor','')))
            ws.cell(row=linha_inicio+index, column=8, value=str(row.get('tipo_combustivel','')))
            ws.cell(row=linha_inicio+index, column=9, value=float(row.get('quantidade', 0) or 0)).number_format = '#,##0.00'
            ws.cell(row=linha_inicio+index, column=10, value=float(row.get('valor_unitario', 0) or 0)).number_format = '"R$" #,##0.00'
            ws.cell(row=linha_inicio+index, column=11, value=float(row.get('total', 0) or 0)).number_format = '"R$" #,##0.00'
            ws.cell(row=linha_inicio+index, column=12, value=str(row.get('horimetro','')))
            ws.cell(row=linha_inicio+index, column=13, value=str(row.get('observacao','')))
        buffer = io.BytesIO()
        wb.save(buffer)
        return buffer.getvalue()
    else:
        df_export = df.copy()
        df_export['DIA'] = pd.to_datetime(df_export['data'], errors='coerce').dt.weekday.map(dias_pt)
        colunas_certas = ['data', 'DIA', 'numero_ficha', 'placa', 'prefixo', 'motorista', 'fornecedor', 'tipo_combustivel', 'quantidade', 'valor_unitario', 'total', 'horimetro', 'observacao']
        df_export = df_export[[c for c in colunas_certas if c in df_export.columns]]
        df_export.columns = ["DATA", "DIA", "FICHA", "PLACA", "CÓDIGO", "MÁQUINA/OPERADOR", "FORNECEDOR", "PRODUTO", "QTD (L)", "V. UNIT.", "TOTAL", "KM/HOR", "OBSERVAÇÃO"]
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer: 
            df_export.to_excel(writer, index=False)
        return buffer.getvalue()

def gerar_pdf_relatorio(df, tipo, titulo_esq, sub_esq, data_esq, dados_dir, titulo_tabela):
    df = df.fillna("")
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.add_page()
    pdf.rect(10, 10, 110, 22)
    x_tx = 12
    if os.path.exists("logo.png"):
        try: pdf.image("logo.png", x=12, y=12, h=18); x_tx = 48 
        except: pass
    pdf.set_xy(x_tx, 12); pdf.set_font("Arial", 'B', 9)
    pdf.cell(0, 6, titulo_esq.upper(), ln=1)
    pdf.set_x(x_tx); pdf.cell(0, 6, sub_esq.upper(), ln=1)
    pdf.set_x(x_tx); pdf.cell(0, 6, data_esq.upper(), ln=1)
    
    pdf.rect(125, 10, 162, 22); pdf.set_xy(127, 12); pdf.set_font("Arial", 'B', 9)
    lin = 0
    for k, v in dados_dir.items():
        if lin % 2 == 0: pdf.set_x(127); pdf.cell(80, 5, f"{k}: {v}")
        else: pdf.cell(80, 5, f"{k}: {v}", ln=1)
        lin += 1
            
    pdf.set_y(35); pdf.set_font("Arial", 'B', 10); pdf.cell(277, 8, titulo_tabela.upper(), border=1, align="C", ln=1)
    pdf.set_font("Arial", 'B', 7); pdf.set_fill_color(240, 240, 240)
    
    if tipo == "SAIDAS": cols = [("DATA",16),("FICHA",17),("PLACA",16),("PREFIXO",16),("MÁQUINA/OPERADOR",55),("PRODUTO",20),("QTD (L)",16),("V. UNIT.",16),("TOTAL (R$)",22),("KM/HOR",16),("OBS",67)]
    else: cols = [("DATA",18),("FICHA/NF",25),("FORNECEDOR",65),("TANQUE DESTINO",45),("PRODUTO",25),("QTD (L)",22),("V. UNIT.",22),("TOTAL (R$)",25),("OBS",30)]
        
    for n, w in cols: pdf.cell(w, 7, n, border=1, align="C", fill=True)
    pdf.ln(); pdf.set_font("Arial", '', 7)
    t_l = 0; t_r = 0
    
    for _, r in df.iterrows():
        if tipo == "SAIDAS":
            pdf.cell(16, 6, str(r.get('data',''))[:10], border=1, align="C"); pdf.cell(17, 6, str(r.get('numero_ficha',''))[:15], border=1, align="C"); pdf.cell(16, 6, str(r.get('placa',''))[:8], border=1, align="C"); pdf.cell(16, 6, str(r.get('prefixo',''))[:8], border=1, align="C"); pdf.cell(55, 6, str(r.get('motorista',''))[:35], border=1, align="L"); pdf.cell(20, 6, str(r.get('tipo_combustivel',''))[:12], border=1, align="C")
            q = float(r.get('quantidade',0) or 0); v = float(r.get('valor_unitario',0) or 0); t = float(r.get('total',0) or 0)
            pdf.cell(16, 6, f"{q:.2f}", border=1, align="R"); pdf.cell(16, 6, f"{v:.2f}", border=1, align="R"); pdf.cell(22, 6, f"{t:.2f}", border=1, align="R"); pdf.cell(16, 6, str(r.get('horimetro',''))[:8], border=1, align="C"); pdf.cell(67, 6, str(r.get('observacao',''))[:40], border=1, align="L")
        else:
            q = float(r.get('quantidade',0) or 0); v = float(r.get('valor_unitario',0) or 0); t = float(r.get('total',0) or 0)
            pdf.cell(18, 6, str(r.get('data',''))[:10], border=1, align="C"); pdf.cell(25, 6, str(r.get('numero_ficha',''))[:15], border=1, align="C"); pdf.cell(65, 6, str(r.get('fornecedor',''))[:40], border=1, align="L"); pdf.cell(45, 6, str(r.get('nome_tanque',''))[:25], border=1, align="C"); pdf.cell(25, 6, str(r.get('combustivel',''))[:12], border=1, align="C"); pdf.cell(22, 6, f"{q:.2f}", border=1, align="R"); pdf.cell(22, 6, f"{v:.2f}", border=1, align="R"); pdf.cell(25, 6, f"{t:.2f}", border=1, align="R"); pdf.cell(30, 6, str(r.get('observacao',''))[:18], border=1, align="L")
        pdf.ln(); t_l += q; t_r += t

    pdf.set_font("Arial", 'B', 8)
    if tipo == "SAIDAS":
        pdf.cell(136, 8, "TOTAIS", border=1, align="R"); pdf.cell(16, 8, f"{t_l:,.2f}", border=1, align="R"); pdf.cell(16, 8, "-", border=1, align="C"); pdf.cell(22, 8, f"R$ {t_r:,.2f}", border=1, align="R"); pdf.cell(87, 8, "", border=1)
    else:
        pdf.cell(178, 8, "TOTAIS", border=1, align="R"); pdf.cell(22, 8, f"{t_l:,.2f}", border=1, align="R"); pdf.cell(22, 8, "-", border=1, align="C"); pdf.cell(25, 8, f"R$ {t_r:,.2f}", border=1, align="R"); pdf.cell(30, 8, "", border=1)
    return pdf.output(dest='S').encode('latin-1')

def exportar_excel_limpo(df_formatado, nome_aba="Relatorio"):
    df_formatado = df_formatado.fillna("")
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df_formatado.to_excel(writer, index=False, sheet_name=nome_aba)
        for i, col in enumerate(df_formatado.columns):
            tamanho = max(len(str(col)), df_formatado[col].astype(str).str.len().max() if not df_formatado.empty else 10)
            writer.sheets[nome_aba].set_column(i, i, min(int(tamanho) + 2, 50))
    return buffer.getvalue()


# ─── TELA DE LOGIN ──────────────────────────────────────────────────────────
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if not st.session_state.logged_in:
    st.markdown('<style>body { background-color: #1a1a2e; }</style>', unsafe_allow_html=True)
    st.write("<br><br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.2, 1]) 
    with c2:
        with st.form("login_form"):
            if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True) 
            st.markdown("<h2 style='text-align: center; color: #333; margin-top:0;'>Acesso Restrito</h2>", unsafe_allow_html=True)
            u = st.text_input("Usuário"); p = st.text_input("Senha", type="password")
            if st.form_submit_button("ENTRAR NO SISTEMA", use_container_width=True):
                if u == "admin" and p == "obra2026": st.session_state.logged_in = True; st.rerun()
                else: st.error("Dados incorretos.")
    st.stop()
def logout(): st.session_state.logged_in = False; st.rerun()


# ─── SIDEBAR DE NAVEGAÇÃO ───────────────────────────────────────────────────
if os.path.exists("logo.png"):
    c_img1, c_img2, c_img3 = st.sidebar.columns([1, 2, 1])
    with c_img2: st.image("logo.png", use_container_width=True)
        
st.sidebar.markdown("<h3 style='text-align: center; margin-top:0;'>Gestão de Obras</h3>", unsafe_allow_html=True)
st.sidebar.divider()
menu = st.sidebar.radio("Navegação Principal", [
    "🏠 Painel Início", 
    "⛽ Lançar Abastecimento", 
    "🛢️ Tanques / Estoque", 
    "🚚 Boletim de Transporte", 
    "🚜 Frota e Equipamentos", 
    "🏪 Fornecedores", 
    "📋 Relatórios e Fechamentos"
])
st.sidebar.divider()
if st.sidebar.button("🚪 Sair do Sistema", use_container_width=True): logout()
st.sidebar.markdown("<div style='text-align: center; font-size: 11px; margin-top: 15px;'>☁️ Armazenamento: Saudável<br><i>Plano Free (500MB)</i></div>", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# 1. PAINEL INÍCIO (DASHBOARD E KPIs)
# ════════════════════════════════════════════════════════════════════════════
if menu == "🏠 Painel Início":
    st.markdown("## 🏠 Centro de Comando da Obra")
    df_tanques = get_data("tanques")
    df_abast = get_data("abastecimentos")
    df_prod = get_data("producao")
    
    if not df_tanques.empty:
        st.subheader("Situação Real dos Tanques/Comboios (Estoque Físico)")
        cols_t = st.columns(len(df_tanques))
        for idx, row in df_tanques.iterrows():
            nome_t = row['nome']; cap_t = float(row.get('capacidade', 0)); saldo_t = calcular_saldo_especifico(nome_t)
            with cols_t[idx]:
                if saldo_t <= ((cap_t * 0.15) if cap_t > 0 else 500): st.markdown(f"<div class='banner-low'>⚠️ <strong>{nome_t}</strong><br>Saldo Baixo: {saldo_t:,.1f} L</div>", unsafe_allow_html=True)
                else: st.markdown(f"<div class='banner-ok'>✅ <strong>{nome_t}</strong><br>Saldo Normal: {saldo_t:,.1f} L</div>", unsafe_allow_html=True)

    st.divider()
    
    lista_meses = ["Todos"]
    if not df_abast.empty: lista_meses += pd.to_datetime(df_abast['data'], errors='coerce').dt.strftime('%m/%Y').dropna().unique().tolist()
    if not df_prod.empty: lista_meses += pd.to_datetime(df_prod['data'], errors='coerce').dt.strftime('%m/%Y').dropna().unique().tolist()
    lista_meses = list(dict.fromkeys(lista_meses)) 
    m_sel = st.selectbox("📅 Analisar Período:", sorted(lista_meses, reverse=True))

    # Cálculos
    t_gasto = 0; t_litros = 0; t_carradas = 0; t_toneladas_geral = 0; t_toneladas_cbuq = 0; t_frete_rs = 0
    
    if not df_abast.empty:
        df_a_filt = df_abast if m_sel == "Todos" else df_abast[pd.to_datetime(df_abast['data'], errors='coerce').dt.strftime('%m/%Y') == m_sel]
        t_gasto = pd.to_numeric(df_a_filt['total'], errors='coerce').sum()
        t_litros = pd.to_numeric(df_a_filt['quantidade'], errors='coerce').sum()
        
    if not df_prod.empty:
        df_p_filt = df_prod if m_sel == "Todos" else df_prod[pd.to_datetime(df_prod['data'], errors='coerce').dt.strftime('%m/%Y') == m_sel]
        t_carradas = pd.to_numeric(df_p_filt['carradas'], errors='coerce').sum()
        t_toneladas_geral = pd.to_numeric(df_p_filt['toneladas'], errors='coerce').sum()
        t_frete_rs = pd.to_numeric(df_p_filt['valor_frete'], errors='coerce').sum()
        df_cbuq = df_p_filt[df_p_filt['tipo_operacao'].isin(["Transporte de Massa/CBUQ", "Venda de Massa"])]
        t_toneladas_cbuq = pd.to_numeric(df_cbuq['toneladas'], errors='coerce').sum()

    st.markdown("#### 💰 Resumo Financeiro e Logística")
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f"<div class='caixa-resumo'><p>Gasto Combustível</p><h3 style='color:#A32D2D;'>R$ {t_gasto:,.2f}</h3></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='caixa-resumo'><p>Total Produzido (CBUQ)</p><h3>{t_toneladas_cbuq:,.1f} Ton</h3></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='caixa-resumo'><p>Volume Transportado (Geral)</p><h3>{t_toneladas_geral:,.1f} Ton</h3></div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='caixa-resumo'><p>Viagens Realizadas</p><h3>{int(t_carradas)} Carradas</h3></div>", unsafe_allow_html=True)

    st.write("<br>", unsafe_allow_html=True)
    
    st.markdown("#### ⚙️ Indicadores de Eficiência (KPIs)")
    c5, c6, c7 = st.columns(3)
    custo_por_ton = (t_gasto / t_toneladas_cbuq) if t_toneladas_cbuq > 0 else 0
    litros_por_ton = (t_litros / t_toneladas_cbuq) if t_toneladas_cbuq > 0 else 0
    litros_por_carrada = (t_litros / t_carradas) if t_carradas > 0 else 0
    
    c5.markdown(f"<div class='caixa-resumo'><p>Custo Médio Diesel por Ton de CBUQ</p><h3 class='kpi-destaque'>R$ {custo_por_ton:,.2f} / Ton</h3></div>", unsafe_allow_html=True)
    c6.markdown(f"<div class='caixa-resumo'><p>Consumo Médio por Ton de CBUQ</p><h3 class='kpi-destaque'>{litros_por_ton:,.2f} L / Ton</h3></div>", unsafe_allow_html=True)
    c7.markdown(f"<div class='caixa-resumo'><p>Média de Gasto Logístico</p><h3 class='kpi-destaque'>{litros_por_carrada:,.1f} L / Carrada</h3></div>", unsafe_allow_html=True)

    st.write("<br>", unsafe_allow_html=True)
    st.divider()
    
    st.markdown("#### 🏆 Eficiência da Frota (Ranking de Caçambas)")
    if not df_abast.empty and not df_prod.empty:
        df_abast_v = df_a_filt.groupby('prefixo')['quantidade'].sum().reset_index().rename(columns={'quantidade':'Litros Consumidos'})
        df_prod_v = df_p_filt.groupby('veiculo').agg({'carradas':'sum', 'toneladas':'sum'}).reset_index().rename(columns={'veiculo':'prefixo'})
        
        df_frota = pd.merge(df_prod_v, df_abast_v, on='prefixo', how='outer').fillna(0)
        df_frota['L / Carrada'] = df_frota.apply(lambda x: round(x['Litros Consumidos']/x['carradas'], 1) if x['carradas']>0 else 0, axis=1)
        df_frota['Ton / Litro (Rendimento)'] = df_frota.apply(lambda x: round(x['toneladas']/x['Litros Consumidos'], 2) if x['Litros Consumidos']>0 else 0, axis=1)
        df_frota = df_frota.rename(columns={'prefixo':'Veículo', 'carradas':'Carradas Totais', 'toneladas':'Ton. Transportadas'})
        
        st.dataframe(df_frota.sort_values(by='Ton / Litro (Rendimento)', ascending=False), use_container_width=True)
    else:
        st.info("Registre abastecimentos e produções no mesmo período para gerar o Ranking da Frota.")


# ════════════════════════════════════════════════════════════════════════════
# 2. ABASTECIMENTO (POSTO / TANQUE)
# ════════════════════════════════════════════════════════════════════════════
elif menu == "⛽ Lançar Abastecimento":
    st.markdown("## ⛽ Lançar Saída de Combustível")
    df_v = get_data("veiculos"); df_f = get_data("fornecedores"); df_a = get_data("abastecimentos"); df_t = get_data("tanques")
    
    if df_v.empty: st.warning("⚠️ Cadastre veículos na aba 'Frota e Equipamentos'.")
    else:
        v_sel = st.selectbox("Máquina / Caçamba", df_v['prefixo'].tolist())
        info_v = df_v[df_v['prefixo'] == v_sel].iloc[0]
        comb_padrao = info_v.get('tipo_combustivel_padrao', 'Não definido')
        
        m_horimetro = 0.0
        if not df_a.empty and 'horimetro' in df_a.columns:
            hist = df_a[df_a['prefixo'] == v_sel]
            if not hist.empty: m_horimetro = float(hist['horimetro'].max())
            
        st.info(f"⛽ Combustível: **{comb_padrao}** | ⏱️ Último Horímetro/Km: **{m_horimetro}**")
        origem = st.radio("Origem do Combustível:", ["Posto Externo", "Tanque Interno"], horizontal=True)

        with st.form("f_lanc"):
            c1, c2, c3 = st.columns([1, 2, 2])
            ficha = c1.text_input("Nº Ficha / Cupom")
            if origem == "Posto Externo": posto = c2.selectbox("Posto", df_f['nome'].tolist() if not df_f.empty else ["Sem cadastro"]); n_tanque_sel = None
            else: n_tanque_sel = c2.selectbox("Tanque", df_t['nome'].tolist() if not df_t.empty else ["Sem cadastro"]); posto = "Estoque Próprio"
            
            data_abast = c3.date_input("Data")
            c4, c5, c6 = st.columns(3)
            hor_atual = c4.number_input("KM / Horímetro Atual", min_value=0.0, value=m_horimetro)
            litros = c5.number_input("Litros", min_value=0.0)
            preco = c6.number_input("Preço Unitário (R$)", min_value=0.0)
            obs = st.text_input("Observações / Obra")
            
            if st.form_submit_button("💾 Salvar Abastecimento", use_container_width=True):
                saldo_t = calcular_saldo_especifico(n_tanque_sel) if n_tanque_sel else 0
                if litros <= 0: st.error("⚠️ Litros devem ser maior que zero.")
                elif origem == "Tanque Interno" and litros > saldo_t: st.error(f"⚠️ Saldo insuficiente! (Tem {saldo_t}L)")
                else:
                    supabase.table("abastecimentos").insert({
                        "data": str(data_abast), "numero_ficha": ficha, "origem": origem, "nome_tanque": n_tanque_sel, 
                        "prefixo": v_sel, "quantidade": litros, "valor_unitario": preco, "total": litros * preco, 
                        "fornecedor": posto, "horimetro": hor_atual, "observacao": obs
                    }).execute(); st.success("✅ Salvo!"); time.sleep(1); st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# 3. TANQUES E ESTOQUE
# ════════════════════════════════════════════════════════════════════════════
elif menu == "🛢️ Tanques / Estoque":
    st.markdown("## 🛢️ Gestão de Estoque Interno")
    t_visao, t_entrada, t_config = st.tabs(["📊 Saldo Real", "📥 Receber Compra (Entrada)", "⚙️ Configurar"])
    
    with t_config:
        with st.form("f_t"):
            n_t = st.text_input("Nome Tanque"); c_t = st.number_input("Capacidade Total", min_value=0.0)
            if st.form_submit_button("Salvar") and n_t: supabase.table("tanques").insert({"nome": n_t, "capacidade": c_t}).execute(); st.rerun()
        df_t = get_data("tanques")
        for _, r in df_t.iterrows():
            c1, c2 = st.columns([4,1])
            c1.write(f"🛢️ {r['nome']} | {r.get('capacidade',0)} L")
            if c2.button("Excluir", key=f"d_{r['id']}"): supabase.table("tanques").delete().eq("id", r['id']).execute(); st.rerun()
            
    with t_entrada:
        df_t = get_data("tanques"); df_f = get_data("fornecedores")
        if df_t.empty: st.warning("Cadastre um tanque primeiro.")
        else:
            with st.form("f_ent"):
                c1, c2 = st.columns(2)
                d_ent = c1.date_input("Data"); t_dest = c2.selectbox("Tanque Destino", df_t['nome'].tolist())
                c3, c4 = st.columns(2)
                forn_ent = c3.selectbox("Distribuidora", df_f['nome'].tolist() if not df_f.empty else ["N/A"]); nf_ent = c4.text_input("Nº NF")
                c5, c6 = st.columns(2)
                q_ent = c5.number_input("Litros", min_value=0.0); p_ent = c6.number_input("R$/L", min_value=0.0)
                if st.form_submit_button("📥 Confirmar Entrada", use_container_width=True):
                    supabase.table("entradas_tanque").insert({"data": str(d_ent), "nome_tanque": t_dest, "fornecedor": forn_ent, "numero_ficha": nf_ent, "quantidade": q_ent, "valor_unitario": p_ent, "total": q_ent*p_ent}).execute(); st.success("✅ Estoque atualizado!"); time.sleep(1); st.rerun()
                    
    with t_visao:
        for _, r in get_data("tanques").iterrows():
            nm = r['nome']; cp = float(r.get('capacidade', 0)); sd = calcular_saldo_especifico(nm)
            with st.expander(f"📊 {nm} - {sd:,.1f} L"): st.progress(max(min(sd/cp,1),0) if cp>0 else 0)


# ════════════════════════════════════════════════════════════════════════════
# 4. LOGÍSTICA DE PRODUÇÃO / FRETE
# ════════════════════════════════════════════════════════════════════════════
elif menu == "🚚 Boletim de Transporte":
    st.markdown("## 🚚 Boletim de Transporte e Logística")
    df_v = get_data("veiculos")
    
    with st.form("f_prod", clear_on_submit=True):
        st.markdown("#### Registrar Boletim Diário")
        c1, c2, c3, c_tp = st.columns([1, 1.2, 1.2, 1.2])
        data_pr = c1.date_input("Data")
        motorista = c2.text_input("Motorista (Para Acerto Financeiro)")
        cacamba = c3.selectbox("Veículo / Caçamba", df_v['prefixo'].tolist() if not df_v.empty else ["Sem cadastro"])
        tipo_op = c_tp.selectbox("Operação", ["Transporte de Massa/CBUQ", "Transporte de Agregado (Jazida)", "Venda de Massa", "Remoção de Entulho/Fresado", "Outros"])
        
        c4, c5 = st.columns(2)
        origem = c4.text_input("Origem (Ex: Usina, Jazida Santa Maria, Trecho KM 10)")
        destino = c5.text_input("Destino (Ex: Obra BR, Balança Cliente)")
        
        c6, c7 = st.columns(2)
        material = c6.text_input("Material Transportado (Ex: CBUQ, Brita 1, Bica)")
        carradas = c7.number_input("Número de Carradas / Viagens", min_value=0, step=1)
        
        c8, c9, c10 = st.columns(3)
        toneladas = c8.number_input("Toneladas Totais (Obrigatório para KPI)", min_value=0.0)
        v_frete = c9.number_input("Valor Frete/Ton ou Diária (R$)", min_value=0.0)
        obs = c10.text_input("Obs / Comprador")
        
        if st.form_submit_button("💾 Salvar Lançamento", use_container_width=True):
            if not motorista: st.error("⚠️ Digite o nome do motorista!")
            else:
                v_total = toneladas * v_frete if v_frete > 0 else 0 
                supabase.table("producao").insert({
                    "data": str(data_pr), "motorista": motorista.strip().upper(), "veiculo": cacamba, "tipo_operacao": tipo_op,
                    "origem": origem, "destino": destino, "material": material, "carradas": carradas, "toneladas": toneladas, 
                    "valor_frete": v_total, "observacao": obs 
                }).execute(); st.success("✅ Logística registrada!"); time.sleep(1); st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# 5. FROTA E EQUIPAMENTOS
# ════════════════════════════════════════════════════════════════════════════
elif menu == "🚜 Frota e Equipamentos":
    st.markdown("## 🚜 Gestão de Máquinas e Veículos")
    with st.form("fv"):
        c1, c2, c3 = st.columns(3)
        px = c1.text_input("Prefixo (Ex: CB-01)")
        pl = c2.text_input("Placa")
        comb = c3.selectbox("Combustível Padrão", ["Diesel S10", "Diesel S500", "Gasolina"])
        if st.form_submit_button("Salvar Veículo"): supabase.table("veiculos").insert({"prefixo": px, "placa": pl, "tipo_combustivel_padrao": comb}).execute(); st.rerun()
        
    for _, r in get_data("veiculos").iterrows():
        c1, c2 = st.columns([4,1])
        c1.write(f"🚜 **{r['prefixo']}** | Placa: {r.get('placa','')} | Comb: {r.get('tipo_combustivel_padrao','')}")
        if c2.button("Remover", key=f"dv_{r['id']}"): supabase.table("veiculos").delete().eq("id", r['id']).execute(); st.rerun()


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
        if st.form_submit_button("Salvar Fornecedor"): supabase.table("fornecedores").insert({"nome": n, "razao_social": rz, "banco": bc, "agencia": ag, "conta": cc, "pix": px}).execute(); st.rerun()
        
    for _, r in get_data("fornecedores").iterrows():
        with st.expander(f"🏪 {r['nome'].upper()}"):
            st.write(f"Banco: {r.get('banco', '')} | Ag: {r.get('agencia', '')} | Conta: {r.get('conta', '')} | PIX: {r.get('pix', '')}")
            if st.button("Remover", key=f"df_{r['id']}"): supabase.table("fornecedores").delete().eq("id", r['id']).execute(); st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# 7. RELATÓRIOS E FECHAMENTOS (ACERTO, PDF E EXCEL)
# ════════════════════════════════════════════════════════════════════════════
elif menu == "📋 Relatórios e Fechamentos":
    st.markdown("## 📋 Central de Relatórios e Acertos")
    df_s = get_data("abastecimentos")
    df_prod = get_data("producao")
    df_f = get_data("fornecedores")
    
    if not df_s.empty: df_s = df_s.fillna("")
    if not df_prod.empty: df_prod = df_prod.fillna("")
    
    t_acerto, t_postos, t_dinamica = st.tabs(["👷 Acerto de Motoristas", "📤 Fechar Pagamento de Postos", "📊 Tabelas Limpas"])

    # --- ABA: ACERTO DE MOTORISTAS ---
    with t_acerto:
        st.markdown("#### Cruzamento Automático: Fretes x Diesel Consumido")
        if not df_prod.empty and not df_s.empty:
            df_prod['data'] = pd.to_datetime(df_prod['data'], errors='coerce')
            df_s['data'] = pd.to_datetime(df_s['data'], errors='coerce')
            
            todos_motoristas = sorted(df_prod['motorista'].dropna().unique().tolist())
            mot_sel = st.selectbox("Selecione o Motorista:", ["Selecione..."] + todos_motoristas)
            mes_sel = st.selectbox("Mês de Fechamento:", df_prod['data'].dt.strftime('%m/%Y').dropna().unique().tolist())
            
            if mot_sel != "Selecione..." and st.button("Calcular Acerto Final", use_container_width=True):
                prod_mot = df_prod[(df_prod['motorista'] == mot_sel) & (df_prod['data'].dt.strftime('%m/%Y') == mes_sel)]
                ganho_bruto = pd.to_numeric(prod_mot['valor_frete']).sum()
                
                cacambas_usadas = prod_mot['veiculo'].unique().tolist()
                abast_mot = df_s[(df_s['prefixo'].isin(cacambas_usadas)) & (df_s['data'].dt.strftime('%m/%Y') == mes_sel)]
                custo_diesel = pd.to_numeric(abast_mot['total']).sum()
                
                liquido = ganho_bruto - custo_diesel
                
                c1, c2, c3 = st.columns(3)
                c1.markdown(f"<div class='caixa-resumo'><p>Fretes Realizados</p><h3 style='color:#1D9E75;'>R$ {ganho_bruto:,.2f}</h3></div>", unsafe_allow_html=True)
                c2.markdown(f"<div class='caixa-resumo'><p>Desconto de Diesel</p><h3 style='color:#A32D2D;'>- R$ {custo_diesel:,.2f}</h3></div>", unsafe_allow_html=True)
                c3.markdown(f"<div class='caixa-resumo'><p>Líquido a Receber</p><h3 style='color:#0F1923;'>R$ {liquido:,.2f}</h3></div>", unsafe_allow_html=True)
                
                st.write("**Extrato de Viagens (Produção):**")
                st.dataframe(prod_mot[['data', 'veiculo', 'origem', 'destino', 'material', 'toneladas', 'carradas', 'valor_frete']])
                st.write("**Extrato de Abastecimentos (Descontos):**")
                st.dataframe(abast_mot[['data', 'numero_ficha', 'prefixo', 'fornecedor', 'quantidade', 'total']])
        else:
            st.info("Registre abastecimentos e viagens para calcular acertos.")

    # --- ABA: PAGAMENTO DE POSTOS (O TEMPLATE A) ---
    with t_postos:
        st.write("Geração do PDF Timbrado e do Excel baseados no seu modelo da COPA Engenharia.")
        c_p1, c_p2 = st.columns(2)
        col_p = c_p1.selectbox("Selecione o Posto:", df_f['nome'].tolist() if not df_f.empty else [])
        mes_p = c_p2.text_input("Período p/ Cabeçalho", "Mês Atual")
        
        if st.button("Gerar Fechamento do Posto"):
            if not df_s.empty:
                df_p = df_s[df_s['fornecedor'] == col_p]
                dados_posto = df_f[df_f['nome'] == col_p].iloc[0].to_dict() if not df_f.empty else {"nome": col_p}
                
                # 1. Gerar o PDF
                pdf_bytes = gerar_pdf_relatorio(df_p, "SAIDAS", "OBRA DE PAVIMENTAÇÃO", "FECHAMENTO DE CONSUMO", f"PERÍODO: {mes_p}", {"FORNECEDOR": col_p, "PIX": dados_posto.get('pix','')}, f"CONTROLE DE ABASTECIMENTO - {col_p}")
                st.download_button("⬇️ Baixar PDF Timbrado", pdf_bytes, f"Fechamento_Posto_{col_p}.pdf", "application/pdf")
                
                # 2. Gerar o Excel usando o Caminho A
                xls_bytes = gerar_excel_com_template(df_p, dados_posto, mes_p, "OBRA DE PAVIMENTAÇÃO")
                st.download_button("⬇️ Baixar Excel (Template COPA)", xls_bytes, f"Fechamento_Posto_{col_p}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # --- ABA: TABELA DINÂMICA COMPLETA ---
    with t_dinamica:
        st.write("Tabela completa de Abastecimentos com Consumo (L/H) e organização inteligente de Horímetro.")
        if not df_s.empty:
            df_s_geral = df_s.copy()
            df_s_geral['data_hora'] = pd.to_datetime(df_s_geral['data'], errors='coerce')
            df_s_geral['horimetro_n'] = pd.to_numeric(df_s_geral['horimetro'], errors='coerce').fillna(0)
            df_s_geral = df_s_geral.sort_values(by=['prefixo', 'data_hora', 'horimetro_n'])
            
            df_s_geral['h_ant'] = df_s_geral.groupby('prefixo')['horimetro_n'].shift(1)
            df_s_geral['horas_trabalhadas'] = df_s_geral['horimetro_n'] - df_s_geral['h_ant']
            df_s_geral['consumo_l_h'] = df_s_geral.apply(lambda r: round(r['quantidade']/r['horas_trabalhadas'], 2) if pd.notna(r['horas_trabalhadas']) and r['horas_trabalhadas']>0 else None, axis=1)
            
            n_cols = {'data':'Data', 'origem':'Origem', 'nome_tanque':'Tanque', 'numero_ficha':'Ficha', 'fornecedor':'Posto', 'prefixo':'Prefixo', 'motorista':'Operador', 'tipo_combustivel':'Produto', 'quantidade':'Litros', 'total':'Total R$', 'horimetro':'Horímetro', 'consumo_l_h':'Consumo L/H'}
            df_final = df_s_geral.rename(columns={k:v for k,v in n_cols.items() if k in df_s_geral.columns})
            
            st.dataframe(df_final, use_container_width=True)
            xls_geral = exportar_excel_limpo(df_final, "Produtividade_Frota")
            st.download_button("⬇️ Baixar Tabela Completa (Excel)", xls_geral, "Tabela_Completa_Frota.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
