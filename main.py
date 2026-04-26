import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime
import plotly.express as px
import os
import time
import io
from fpdf import FPDF

# --- CONFIGURAÇÃO E ESTÉTICA ---
st.set_page_config(page_title="Gestão de Frota", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f4f6f8; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    .stTextInput>label, .stSelectbox>label, .stNumberInput>label, .stDateInput>label {
        font-size: 11px !important; text-transform: uppercase; color: #666; letter-spacing: 0.05em; font-weight: 600;
    }
    div.stButton > button:first-child {
        background-color: #1D9E75; color: white; border: none; border-radius: 6px; font-weight: 600; padding: 0.5rem 1rem;
    }
    div.stButton > button:first-child:hover { background-color: #0F6E56; border-color: #0F6E56; color: white;}
    div[data-testid="stForm"] {
        border: 1px solid #e0e6ed; border-radius: 12px; padding: 1.5rem; background-color: #ffffff; box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    .saldo-ok { color: #3B6D11; font-weight: bold; background-color: #EAF3DE; padding: 12px; border-radius: 8px; border: 1px solid #C0DD97; font-size: 1.1rem; margin-bottom: 1rem;}
    .saldo-low { color: #854F0B; font-weight: bold; background-color: #FAEEDA; padding: 12px; border-radius: 8px; border: 1px solid #FAC775; font-size: 1.1rem; margin-bottom: 1rem;}
    </style>
""", unsafe_allow_html=True)

# --- CONEXÃO BANCO DE DADOS ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- FUNÇÕES GERADORAS (PDF E EXCEL) ---
def gerar_pdf_relatorio(df, tipo, titulo_esq, sub_esq, data_esq, dados_dir, titulo_tabela):
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.add_page()
    
    pdf.rect(10, 10, 110, 22)
    x_texto_esq = 12
    if os.path.exists("logo.png"):
        try:
            pdf.image("logo.png", x=12, y=12, h=18)
            x_texto_esq = 48 
        except:
            pass
            
    pdf.set_xy(x_texto_esq, 12)
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(0, 6, titulo_esq.upper(), ln=1)
    pdf.set_x(x_texto_esq); pdf.cell(0, 6, sub_esq.upper(), ln=1)
    pdf.set_x(x_texto_esq); pdf.cell(0, 6, data_esq.upper(), ln=1)
    
    pdf.rect(125, 10, 162, 22)
    pdf.set_xy(127, 12)
    pdf.set_font("Arial", 'B', 9)
    
    linha_atual = 0
    for chave, valor in dados_dir.items():
        if linha_atual % 2 == 0:
            pdf.set_x(127)
            pdf.cell(80, 5, f"{chave}: {valor}")
        else:
            pdf.cell(80, 5, f"{chave}: {valor}", ln=1)
        linha_atual += 1
            
    pdf.set_y(35)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(277, 8, titulo_tabela.upper(), border=1, align="C", ln=1)
    
    pdf.set_font("Arial", 'B', 7)
    pdf.set_fill_color(240, 240, 240)
    
    if tipo == "SAIDAS":
        cols = [("DATA", 16), ("FICHA", 17), ("PLACA", 16), ("PREFIXO", 16), 
                ("MÁQUINA/OPERADOR", 55), ("PRODUTO", 20), ("QTD (L)", 16), 
                ("V. UNIT.", 16), ("TOTAL (R$)", 22), ("KM/HOR", 16), ("OBSERVAÇÃO", 67)]
    else:
        cols = [("DATA", 18), ("FICHA/NF", 25), ("FORNECEDOR/DISTRIBUIDORA", 65), ("TANQUE DESTINO", 45), 
                ("PRODUTO", 25), ("QTD (L)", 22), ("V. UNIT.", 22), 
                ("TOTAL (R$)", 25), ("OBSERVAÇÕES GERAIS", 30)]
        
    for nome, largura in cols: 
        pdf.cell(largura, 7, nome, border=1, align="C", fill=True)
    pdf.ln()

    pdf.set_font("Arial", '', 7)
    total_litros = 0
    total_dinheiro = 0
    
    for _, r in df.iterrows():
        if tipo == "SAIDAS":
            eq = str(r.get('motorista',''))[:35]
            obs = str(r.get('observacao',''))[:40]
            pdf.cell(16, 6, str(r.get('data',''))[:10], border=1, align="C")
            pdf.cell(17, 6, str(r.get('numero_ficha',''))[:15], border=1, align="C")
            pdf.cell(16, 6, str(r.get('placa',''))[:8], border=1, align="C")
            pdf.cell(16, 6, str(r.get('prefixo',''))[:8], border=1, align="C")
            pdf.cell(55, 6, eq, border=1, align="L")
            pdf.cell(20, 6, str(r.get('tipo_combustivel',''))[:12], border=1, align="C")
            pdf.cell(16, 6, f"{float(r.get('quantidade',0)):.2f}", border=1, align="R")
            pdf.cell(16, 6, f"{float(r.get('valor_unitario',0)):.2f}", border=1, align="R")
            pdf.cell(22, 6, f"{float(r.get('total',0)):.2f}", border=1, align="R")
            pdf.cell(16, 6, str(r.get('horimetro',''))[:8], border=1, align="C")
            pdf.cell(67, 6, obs, border=1, align="L")
        else:
            forn = str(r.get('fornecedor',''))[:40]
            dest = str(r.get('nome_tanque',''))[:25]
            obs = str(r.get('observacao',''))[:18]
            pdf.cell(18, 6, str(r.get('data',''))[:10], border=1, align="C")
            pdf.cell(25, 6, str(r.get('numero_ficha',''))[:15], border=1, align="C")
            pdf.cell(65, 6, forn, border=1, align="L")
            pdf.cell(45, 6, dest, border=1, align="C")
            pdf.cell(25, 6, str(r.get('combustivel',''))[:12], border=1, align="C")
            pdf.cell(22, 6, f"{float(r.get('quantidade',0)):.2f}", border=1, align="R")
            pdf.cell(22, 6, f"{float(r.get('valor_unitario',0)):.2f}", border=1, align="R")
            pdf.cell(25, 6, f"{float(r.get('total',0)):.2f}", border=1, align="R")
            pdf.cell(30, 6, obs, border=1, align="L")
            
        pdf.ln()
        total_litros += float(r.get('quantidade',0))
        total_dinheiro += float(r.get('total',0))

    pdf.set_font("Arial", 'B', 8)
    if tipo == "SAIDAS":
        pdf.cell(136, 8, "TOTAIS GERAIS", border=1, align="R")
        pdf.cell(16, 8, f"{total_litros:,.2f}", border=1, align="R")
        pdf.cell(16, 8, "-", border=1, align="C")
        pdf.cell(22, 8, f"R$ {total_dinheiro:,.2f}", border=1, align="R")
        pdf.cell(87, 8, "", border=1)
    else:
        pdf.cell(178, 8, "TOTAIS GERAIS", border=1, align="R")
        pdf.cell(22, 8, f"{total_litros:,.2f}", border=1, align="R")
        pdf.cell(22, 8, "-", border=1, align="C")
        pdf.cell(25, 8, f"R$ {total_dinheiro:,.2f}", border=1, align="R")
        pdf.cell(30, 8, "", border=1)
        
    return pdf.output(dest='S').encode('latin-1')

def renomear_para_excel(df, tipo):
    if df.empty: return df
    if tipo == "SAIDAS":
        n = {'data': 'Data', 'origem': 'Origem', 'nome_tanque': 'Tanque Próprio', 'numero_ficha': 'Nº Ficha', 'fornecedor': 'Posto / Distribuidora', 'prefixo': 'Prefixo', 'classe': 'Classe', 'placa': 'Placa', 'motorista': 'Operador / Motorista', 'tipo_combustivel': 'Produto', 'quantidade': 'Litros', 'valor_unitario': 'R$/L', 'total': 'Total (R$)', 'horimetro': 'Horímetro/KM', 'horas_trabalhadas': 'Horas Trab.', 'consumo_l_h': 'Consumo (L/h)', 'obra': 'Obra/Local', 'observacao': 'Obs'}
    else:
        n = {'data': 'Data', 'numero_ficha': 'Nº Ficha / NF', 'fornecedor': 'Distribuidora', 'nome_tanque': 'Tanque Destino', 'combustivel': 'Produto', 'quantidade': 'Litros', 'valor_unitario': 'R$/L', 'total': 'Total (R$)', 'observacao': 'Obs'}
    return df.rename(columns={k: v for k, v in n.items() if k in df.columns})

def exportar_excel(df_formatado, nome_aba="Relatorio"):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df_formatado.to_excel(writer, index=False, sheet_name=nome_aba)
        planilha = writer.sheets[nome_aba]
        for i, col in enumerate(df_formatado.columns):
            try:
                tamanho = max(len(str(col)), df_formatado[col].astype(str).str.len().max() if not df_formatado.empty else 10)
                planilha.set_column(i, i, min(int(tamanho) + 2, 50))
            except:
                planilha.set_column(i, i, 15)
    return buffer.getvalue()

def get_data(table):
    try:
        res = supabase.table(table).select("*").execute()
        return pd.DataFrame(res.data)
    except Exception as e:
        return pd.DataFrame()

def calcular_saldo_especifico(nome_tanque):
    df_ent = get_data("entradas_tanque")
    df_sai = get_data("abastecimentos")
    
    t_ent = 0
    if not df_ent.empty and 'quantidade' in df_ent.columns and 'nome_tanque' in df_ent.columns:
        df_ent_filtrado = df_ent[df_ent['nome_tanque'] == nome_tanque]
        t_ent = pd.to_numeric(df_ent_filtrado['quantidade']).sum()
        
    t_sai = 0
    if not df_sai.empty and 'origem' in df_sai.columns and 'quantidade' in df_sai.columns and 'nome_tanque' in df_sai.columns:
        df_sai_filtrado = df_sai[(df_sai['origem'] == 'Tanque Interno') & (df_sai['nome_tanque'] == nome_tanque)]
        t_sai = pd.to_numeric(df_sai_filtrado['quantidade']).sum()
        
    return t_ent - t_sai

# --- SISTEMA DE LOGIN ---
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
            submit = st.form_submit_button("ENTRAR NO SISTEMA", use_container_width=True)
            if submit:
                if u == "admin" and p == "obra2026":
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Dados incorretos.")
    st.stop()

def logout():
    st.session_state.logged_in = False
    st.rerun()

# --- SIDEBAR ---
if os.path.exists("logo.png"):
    col_s1, col_s2, col_s3 = st.sidebar.columns([1, 2, 1])
    with col_s2: st.image("logo.png", use_container_width=True)
        
st.sidebar.markdown("<h3 style='text-align: center; margin-top:0; color:#1D9E75;'>Gestão de Obras</h3>", unsafe_allow_html=True)
st.sidebar.divider()
menu = st.sidebar.radio("Navegação Principal", ["🏠 Painel Início", "📝 Lançar Abastecimento", "🛢️ Tanques / Estoque", "🚜 Frota", "🏪 Fornecedores", "📋 Relatórios / PDF"])
st.sidebar.divider()
if st.sidebar.button("🚪 Sair do Sistema", use_container_width=True): logout()
st.sidebar.markdown("<div style='text-align: center; color: #888; font-size: 11px; margin-top: 15px;'>☁️ Armazenamento: Saudável<br><i>Capacidade: 500MB (Plano Free)</i></div>", unsafe_allow_html=True)

# --- PÁGINA: INÍCIO ---
if menu == "🏠 Painel Início":
    st.title("Painel de Controle da Frota")
    df_tanques = get_data("tanques")
    df_abast = get_data("abastecimentos")
    
    if not df_tanques.empty:
        st.subheader("Situação Real dos Tanques/Comboios (Estoque Físico)")
        cols_t = st.columns(len(df_tanques))
        for idx, row in df_tanques.iterrows():
            nome_t = row['nome']
            cap_t = float(row.get('capacidade', 0))
            saldo_t = calcular_saldo_especifico(nome_t)
            with cols_t[idx]:
                limite = (cap_t * 0.15) if cap_t > 0 else 500
                if saldo_t <= limite:
                    st.markdown(f"<div class='saldo-low'>⚠️ {nome_t}<br>Saldo Baixo: {saldo_t:,.1f} L</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='saldo-ok'>✅ {nome_t}<br>Saldo Normal: {saldo_t:,.1f} L</div>", unsafe_allow_html=True)

    st.divider()
    st.subheader("Resumo de Gastos e Consumo")
    
    if not df_abast.empty:
        # Extrai a data corretamente para gerar o Mês
        df_abast['data_valida'] = pd.to_datetime(df_abast['data'], errors='coerce')
        df_abast['Mes'] = df_abast['data_valida'].dt.strftime('%m/%Y')
        
        # Filtro Inteligente de Mês
        lista_meses = ["Todos"] + sorted(df_abast['Mes'].dropna().unique().tolist(), reverse=True)
        col_m1, col_m2 = st.columns([1, 2])
        mes_selecionado = col_m1.selectbox("📅 Filtrar dados por Mês/Ano:", lista_meses)
        
        if mes_selecionado != "Todos":
            df_abast_filtrado = df_abast[df_abast['Mes'] == mes_selecionado]
        else:
            df_abast_filtrado = df_abast
            
        df_abast_filtrado['total'] = pd.to_numeric(df_abast_filtrado['total'])
        df_abast_filtrado['quantidade'] = pd.to_numeric(df_abast_filtrado['quantidade'])
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Investimento no Período", f"R$ {df_abast_filtrado['total'].sum():,.2f}")
        m2.metric("Volume Consumido (L)", f"{df_abast_filtrado['quantidade'].sum():,.1f} L")
        m3.metric("Abastecimentos (Saídas)", len(df_abast_filtrado))
        
        with st.expander("📈 Visualizar Gráficos de Tendência", expanded=True):
            if mes_selecionado == "Todos":
                # Mostra o Gasto Mensal
                df_grafico = df_abast_filtrado.groupby('Mes')['total'].sum().reset_index()
                f_gasto = px.bar(df_grafico, x='Mes', y='total', title="Evolução de Gastos por Mês", color_discrete_sequence=['#1D9E75'])
            else:
                # Mostra o Gasto Diário daquele Mês
                df_abast_filtrado['Dia'] = df_abast_filtrado['data_valida'].dt.strftime('%d/%m/%Y')
                df_grafico = df_abast_filtrado.groupby('Dia')['total'].sum().reset_index()
                f_gasto = px.bar(df_grafico, x='Dia', y='total', title=f"Gastos Diários em {mes_selecionado}", color_discrete_sequence=['#1D9E75'])
                
            st.plotly_chart(f_gasto, use_container_width=True)
    else:
        st.info("Nenhum dado de abastecimento registrado.")

# --- PÁGINA: LANÇAR ABASTECIMENTO ---
elif menu == "📝 Lançar Abastecimento":
    st.header("Lançar Saída de Combustível")
    df_v = get_data("veiculos")
    df_f = get_data("fornecedores")
    df_a = get_data("abastecimentos") 
    df_t = get_data("tanques")
    
    if df_v.empty:
        st.warning("⚠️ Cadastre veículos na aba 'Frota'.")
    else:
        v_sel = st.selectbox("Selecione o Veículo / Máquina", df_v['prefixo'].tolist())
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
            
            n_tanque_sel = None
            if origem == "Posto Externo":
                posto = c2.selectbox("Posto Fornecedor", df_f['nome'].tolist() if not df_f.empty else ["Sem cadastro"])
            else:
                n_tanque_sel = c2.selectbox("Selecione o Tanque", df_t['nome'].tolist() if not df_t.empty else ["Sem cadastro"])
                posto = "Estoque Próprio"

            data_abast = c3.date_input("Data do Abastecimento")
            
            c4, c5, c6 = st.columns(3)
            hor_atual = c4.number_input("Horímetro / KM Atual", min_value=0.0, value=m_horimetro, step=0.1)
            litros = c5.number_input("Litros", min_value=0.0)
            preco = c6.number_input("Preço Unitário (R$)", min_value=0.0)

            c7, c8 = st.columns(2)
            obra = c7.text_input("Obra / Trecho")
            obs = c8.text_input("Observações")
            
            if st.form_submit_button("Confirmar Saída"):
                saldo_t = calcular_saldo_especifico(n_tanque_sel) if n_tanque_sel else 0
                if litros <= 0:
                    st.error("⚠️ Litros devem ser maior que zero.")
                elif origem == "Tanque Interno" and litros > saldo_t:
                    st.error(f"⚠️ BLOQUEADO: Saldo insuficiente no '{n_tanque_sel}'. Tentou retirar: {litros}L | Saldo: {saldo_t}L.")
                else:
                    supabase.table("abastecimentos").insert({
                        "data": str(data_abast), "numero_ficha": ficha, "origem": origem, "nome_tanque": n_tanque_sel, 
                        "prefixo": v_sel, "quantidade": litros, "valor_unitario": preco, "total": litros * preco, 
                        "fornecedor": posto, "tipo_combustivel": comb_padrao, "horimetro": hor_atual, "obra": obra, "observacao": obs
                    }).execute()
                    st.success("Salvo com sucesso!"); time.sleep(1); st.rerun() 

# --- PÁGINA: ESTOQUE E TANQUES ---
elif menu == "🛢️ Tanques / Estoque":
    st.header("Gestão de Estoque Interno")
    t_visao, t_entrada, t_config = st.tabs(["📊 Saldo", "📥 Receber Compra (Entrada)", "⚙️ Configurar Tanques"])
    
    with t_config:
        with st.form("f_tanque", clear_on_submit=True):
            c1, c2 = st.columns([2, 1])
            nome_t = c1.text_input("Nome (Ex: Tanque Matriz)")
            cap_t = c2.number_input("Capacidade (L)", min_value=0.0)
            if st.form_submit_button("Salvar Tanque") and nome_t:
                supabase.table("tanques").insert({"nome": nome_t, "capacidade": cap_t}).execute()
                st.rerun()
        df_t = get_data("tanques")
        if not df_t.empty:
            for _, r in df_t.iterrows():
                cb1, cb2 = st.columns([4, 1])
                cb1.write(f"🛢️ **{r['nome']}** | {r.get('capacidade', 0)} L")
                if cb2.button("Remover", key=f"dt_{r['id']}"):
                    supabase.table("tanques").delete().eq("id", r['id']).execute()
                    st.rerun()

    with t_entrada:
        df_t = get_data("tanques")
        df_f = get_data("fornecedores")
        if df_t.empty:
            st.warning("⚠️ Cadastre um Tanque primeiro.")
        else:
            with st.form("f_ent"):
                c1, c2, c3 = st.columns(3)
                d_ent = c1.date_input("Data Recebimento")
                nf_ent = c2.text_input("Nº Nota Fiscal")
                forn_ent = c3.selectbox("Distribuidora", df_f['nome'].tolist() if not df_f.empty else ["Sem cadastro"])
                
                c4, c5 = st.columns(2)
                t_dest = c4.selectbox("Tanque Destino", df_t['nome'].tolist())
                prod_ent = c5.selectbox("Produto", ["Diesel S10", "Diesel S500", "Gasolina", "Arla 32"])
                
                c7, c8 = st.columns(2)
                q_ent = c7.number_input("Litros Recebidos", min_value=0.0)
                p_ent = c8.number_input("Preço NF (R$/L)", min_value=0.0)
                obs_ent = st.text_input("Observações")
                
                if st.form_submit_button("Confirmar Entrada"):
                    if q_ent > 0:
                        supabase.table("entradas_tanque").insert({
                            "data": str(d_ent), "numero_ficha": nf_ent, "fornecedor": forn_ent, "nome_tanque": t_dest, 
                            "combustivel": prod_ent, "quantidade": q_ent, "valor_unitario": p_ent, "total": q_ent * p_ent, "observacao": obs_ent
                        }).execute()
                        st.success("Estoque atualizado!"); time.sleep(1); st.rerun()

    with t_visao:
        df_t = get_data("tanques")
        for _, r in df_t.iterrows():
            nm = r['nome']
            cp = float(r.get('capacidade', 0))
            sd = calcular_saldo_especifico(nm)
            with st.expander(f"📊 {nm} - Saldo: {sd:,.1f} L", expanded=True):
                if cp > 0:
                    pct = max(min(sd / cp, 1.0), 0)
                    st.progress(pct)
                    st.caption(f"Capacidade: {cp:,.1f} L | ~{pct*100:.0f}% cheio")

# --- PÁGINA: FROTA ---
elif menu == "🚜 Frota":
    st.header("Gestão de Máquinas e Veículos")
    tf1, tf2 = st.tabs(["🚜 Frota Ativa", "📂 Categorias"])
    with tf2:
        with st.form("fc"):
            nc = st.text_input("Nova Categoria")
            if st.form_submit_button("Salvar") and nc:
                supabase.table("classes_frota").insert({"nome": nc}).execute(); st.rerun()
        df_c = get_data("classes_frota")
        for _, r in df_c.iterrows():
            c1, c2 = st.columns([3, 1])
            c1.write(f"• {r['nome']}")
            if c2.button("Excluir", key=f"dc_{r['id']}"): supabase.table("classes_frota").delete().eq("id", r['id']).execute(); st.rerun()
    with tf1:
        df_c = get_data("classes_frota")
        with st.form("fv"):
            c1, c2 = st.columns(2)
            px = c1.text_input("Prefixo (Ex: CAM-01)")
            pl = c2.text_input("Placa")
            c3, c4 = st.columns(2)
            cl = c3.selectbox("Categoria", df_c['nome'].tolist() if not df_c.empty else ["N/A"])
            cb = c4.selectbox("Combustível", ["Diesel S10", "Diesel S500", "Gasolina", "Arla 32"])
            mot = st.text_input("Operador")
            if st.form_submit_button("Cadastrar"):
                supabase.table("veiculos").insert({"prefixo": px, "placa": pl, "classe": cl, "motorista": mot, "tipo_combustivel_padrao": cb}).execute()
                st.rerun()
        df_v = get_data("veiculos")
        for _, r in df_v.iterrows():
            with st.expander(f"🚜 {r['prefixo']} | Placa: {r.get('placa', '')}"):
                st.write(f"Categoria: {r.get('classe', '')} | Operador: {r.get('motorista', '')}")
                if st.button("Remover", key=f"dv_{r['id']}"): supabase.table("veiculos").delete().eq("id", r['id']).execute(); st.rerun()

# --- PÁGINA: FORNECEDORES ---
elif menu == "🏪 Fornecedores":
    st.header("Cadastro de Postos e Distribuidoras")
    with st.form("ff"):
        c1, c2 = st.columns(2)
        n = c1.text_input("Nome Fantasia")
        rz = c2.text_input("Razão Social")
        c3, c4, c5, c6 = st.columns(4)
        cn = c3.text_input("CNPJ")
        ag = c4.text_input("Agência")
        cc = c5.text_input("Conta")
        px = c6.text_input("PIX")
        c7, c8 = st.columns(2)
        bc = c7.text_input("Banco")
        tc = c8.selectbox("Tipo de Conta", ["Corrente", "Poupança", "Outra"])
        if st.form_submit_button("Salvar Fornecedor"):
            supabase.table("fornecedores").insert({"nome": n, "razao_social": rz, "cnpj": cn, "agencia": ag, "conta": cc, "pix": px, "banco": bc, "tipo_conta": tc}).execute()
            st.rerun()
    df_f = get_data("fornecedores")
    for _, r in df_f.iterrows():
        with st.expander(f"🏪 {r['nome'].upper()}"):
            st.write(f"CNPJ: {r.get('cnpj', '')} | Banco: {r.get('banco', '')} | Ag/Cc: {r.get('agencia', '')}/{r.get('conta', '')} | PIX: {r.get('pix', '')}")
            if st.button("Remover", key=f"df_{r['id']}"): supabase.table("fornecedores").delete().eq("id", r['id']).execute(); st.rerun()

# --- PÁGINA: RELATÓRIOS E FECHAMENTOS ---
elif menu == "📋 Relatórios / PDF":
    st.header("Central de Relatórios e Exportações")
    df_s = get_data("abastecimentos")
    df_e = get_data("entradas_tanque")
    df_f = get_data("fornecedores")
    df_t = get_data("tanques")
    df_v = get_data("veiculos")
    
    # Garantia de colunas e dados formatados
    for col in ['origem', 'obra', 'observacao', 'nome_tanque', 'numero_ficha']:
        if col not in df_s.columns: df_s[col] = ""
    for col in ['numero_ficha', 'nome_tanque', 'observacao']:
        if col not in df_e.columns: df_e[col] = ""

    # FILTRO GLOBAL DE MÊS PARA TODOS OS RELATÓRIOS
    col_rm1, col_rm2 = st.columns([1, 2])
    if not df_s.empty:
        df_s['Mes_Ref'] = pd.to_datetime(df_s['data'], errors='coerce').dt.strftime('%m/%Y')
        meses_disp = sorted(df_s['Mes_Ref'].dropna().unique().tolist(), reverse=True)
    else:
        meses_disp = []
        
    mes_rel_sel = col_rm1.selectbox("📅 Escolha o mês do relatório:", ["Todos"] + meses_disp)
    
    if mes_rel_sel != "Todos":
        if not df_s.empty: df_s = df_s[df_s['Mes_Ref'] == mes_rel_sel]
        if not df_e.empty: 
            df_e['Mes_Ref'] = pd.to_datetime(df_e['data'], errors='coerce').dt.strftime('%m/%Y')
            df_e = df_e[df_e['Mes_Ref'] == mes_rel_sel]

    st.divider()

    t_sai, t_ent, t_geral = st.tabs(["📤 Fechamento de Saídas (Postos/Tanques)", "📥 Fechamento de Entradas (Compras)", "📊 Tabela Dinâmica Geral"])

    with t_sai:
        st.write("Gere o relatório timbrado para pagar postos ou conferir o uso do tanque próprio.")
        cs1, cs2, cs3 = st.columns(3)
        filtro_orig_s = cs1.selectbox("Origem:", ["Posto Externo", "Tanque Interno"], key="o_s")
        
        if filtro_orig_s == "Posto Externo":
            local_sel_s = cs2.selectbox("Qual Posto?", ["Selecione..."] + (df_f['nome'].tolist() if not df_f.empty else []))
        else:
            local_sel_s = cs2.selectbox("Qual Tanque?", ["Selecione..."] + (df_t['nome'].tolist() if not df_t.empty else []))
            
        periodo_s = cs3.text_input("Período p/ Cabeçalho:", mes_rel_sel if mes_rel_sel != "Todos" else "Mês Atual", key="p_s")
        obra_s = st.text_input("Obra p/ Cabeçalho:", "OBRA DE PAVIMENTAÇÃO", key="ob_s")
        
        if local_sel_s != "Selecione...":
            filtro_col = 'fornecedor' if filtro_orig_s == "Posto Externo" else 'nome_tanque'
            df_s_filt = df_s[df_s[filtro_col] == local_sel_s]
            
            if not df_v.empty:
                df_s_filt = df_s_filt.merge(df_v[['prefixo', 'placa', 'motorista']], on='prefixo', how='left')
                
            cb1, cb2 = st.columns(2)
            if cb1.button("📄 Gerar PDF Timbrado (Saídas)"):
                if filtro_orig_s == "Posto Externo":
                    dados_posto = df_f[df_f['nome'] == local_sel_s].iloc[0].to_dict()
                    dados_dir = {"FORNECEDOR": dados_posto.get('nome',''), "PIX": dados_posto.get('pix',''), "BANCO/AG": f"{dados_posto.get('banco','')} / {dados_posto.get('agencia','')}", "CONTA": dados_posto.get('conta','')}
                else:
                    dados_dir = {"LOCAL DE ORIGEM": local_sel_s, "TIPO": "Estoque Próprio", "CONTROLE": "Interno Automático"}
                
                pdf_s = gerar_pdf_relatorio(df_s_filt, "SAIDAS", f"OBRA: {obra_s}", "DESCRIÇÃO: FECHAMENTO DE CONSUMO", f"PERÍODO: {periodo_s}", dados_dir, f"CONTROLE DE ABASTECIMENTO - {local_sel_s}")
                st.download_button("⬇️ Baixar PDF", pdf_s, f"Fechamento_{local_sel_s}.pdf", "application/pdf")
                
            if cb2.button("📊 Baixar em Excel (Saídas)"):
                df_s_xls = renomear_para_excel(df_s_filt, "SAIDAS")
                xls_s = exportar_excel(df_s_xls, "Fechamento")
                st.download_button("⬇️ Baixar Excel", xls_s, f"Fechamento_{local_sel_s}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    with t_ent:
        st.write("Gere relatórios de todas as compras de combustível que alimentaram seus tanques.")
        ce1, ce2, ce3 = st.columns(3)
        filtro_forn_e = ce1.selectbox("Filtrar por Fornecedor:", ["Todos"] + (df_f['nome'].tolist() if not df_f.empty else []))
        filtro_tanq_e = ce2.selectbox("Filtrar por Destino (Tanque):", ["Todos"] + (df_t['nome'].tolist() if not df_t.empty else []))
        periodo_e = ce3.text_input("Período p/ Cabeçalho:", mes_rel_sel if mes_rel_sel != "Todos" else "Mês Atual", key="p_e")
        
        df_e_filt = df_e.copy()
        if not df_e_filt.empty:
            if filtro_forn_e != "Todos": df_e_filt = df_e_filt[df_e_filt['fornecedor'] == filtro_forn_e]
            if filtro_tanq_e != "Todos": df_e_filt = df_e_filt[df_e_filt['nome_tanque'] == filtro_tanq_e]
            
        cbe1, cbe2 = st.columns(2)
        if cbe1.button("📄 Gerar PDF Timbrado (Entradas)"):
            dados_dir = {"FORNECEDOR FILTRADO": filtro_forn_e, "TANQUE DESTINO": filtro_tanq_e, "OPERAÇÃO": "Entrada de Estoque", "STATUS": "Conferido"}
            pdf_e = gerar_pdf_relatorio(df_e_filt, "ENTRADAS", "CONTROLE CENTRAL", "DESCRIÇÃO: ENTRADAS DE COMBUSTÍVEL", f"PERÍODO: {periodo_e}", dados_dir, "RELATÓRIO DE COMPRAS E RECEBIMENTOS")
            st.download_button("⬇️ Baixar PDF", pdf_e, "Entradas_Combustivel.pdf", "application/pdf")
            
        if cbe2.button("📊 Baixar em Excel (Entradas)"):
            df_e_xls = renomear_para_excel(df_e_filt, "ENTRADAS")
            xls_e = exportar_excel(df_e_xls, "Entradas")
            st.download_button("⬇️ Baixar Excel", xls_e, "Entradas_Combustivel.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    with t_geral:
        st.write("Visão geral de produtividade da frota (Cálculo de L/h).")
        if not df_s.empty:
            if not df_v.empty:
                df_s_geral = df_s.merge(df_v[['prefixo', 'classe', 'placa', 'motorista']], on='prefixo', how='left')
            else: df_s_geral = df_s.copy()

            df_s_geral['data_hora'] = pd.to_datetime(df_s_geral['data'])
            df_s_geral = df_s_geral.sort_values(by=['prefixo', 'data_hora', 'horimetro'])
            df_s_geral['h_ant'] = df_s_geral.groupby('prefixo')['horimetro'].shift(1)
            df_s_geral['horas_trabalhadas'] = df_s_geral['horimetro'] - df_s_geral['h_ant']
            df_s_geral['consumo_l_h'] = df_s_geral.apply(lambda r: round(r['quantidade']/r['horas_trabalhadas'], 2) if pd.notna(r['horas_trabalhadas']) and r['horas_trabalhadas']>0 else None, axis=1)
            
            c_g1, c_g2 = st.columns(2)
            f_geral_forn = c_g1.selectbox("Fornecedor / Origem:", ["Todos"] + sorted(df_s_geral['fornecedor'].dropna().unique().tolist()))
            f_geral_ori = c_g2.selectbox("Tipo de Local:", ["Todas"] + df_s_geral['origem'].dropna().unique().tolist())
            
            if f_geral_forn != "Todos": df_s_geral = df_s_geral[df_s_geral['fornecedor'] == f_geral_forn]
            if f_geral_ori != "Todas": df_s_geral = df_s_geral[df_s_geral['origem'] == f_geral_ori]

            df_s_xls = renomear_para_excel(df_s_geral, "SAIDAS")
            st.dataframe(df_s_xls, use_container_width=True)
            
            xls_geral = exportar_excel(df_s_xls, "Produtividade")
            st.download_button("⬇️ Exportar Tabela Completa p/ Excel", xls_geral, "Tabela_Dinamica_Completa.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.info("Sem dados de consumo ainda.")
