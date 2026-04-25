import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime
import plotly.express as px
import os
import time
import io
from fpdf import FPDF

# --- CONFIGURAÇÃO E ESTÉTICA "PAVCONTROL" ---
st.set_page_config(page_title="Gestão de Frota", layout="wide")

st.markdown("""
    <style>
    /* Estilo de fundo e fontes */
    .main { background-color: #f4f6f8; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    
    /* Títulos de campos menores e elegantes */
    .stTextInput>label, .stSelectbox>label, .stNumberInput>label, .stDateInput>label {
        font-size: 11px !important; text-transform: uppercase; color: #666; letter-spacing: 0.05em; font-weight: 600;
    }
    
    /* Botões Verdes estilo PavControl */
    div.stButton > button:first-child {
        background-color: #1D9E75; color: white; border: none; border-radius: 6px; font-weight: 600; padding: 0.5rem 1rem;
    }
    div.stButton > button:first-child:hover { background-color: #0F6E56; border-color: #0F6E56; color: white;}
    
    /* Caixas de Formulário */
    div[data-testid="stForm"] {
        border: 1px solid #e0e6ed; border-radius: 12px; padding: 1.5rem; background-color: #ffffff; box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    
    /* Avisos de Saldo */
    .saldo-ok { color: #3B6D11; font-weight: bold; background-color: #EAF3DE; padding: 12px; border-radius: 8px; border: 1px solid #C0DD97; font-size: 1.1rem; margin-bottom: 1rem;}
    .saldo-low { color: #854F0B; font-weight: bold; background-color: #FAEEDA; padding: 12px; border-radius: 8px; border: 1px solid #FAC775; font-size: 1.1rem; margin-bottom: 1rem;}
    </style>
""", unsafe_allow_html=True)

# --- CONEXÃO BANCO DE DADOS ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- FUNÇÃO GERADORA DE PDF (MODELO COPA/POSTO) ---
def gerar_pdf_fechamento_posto(df, dados_fornecedor, periodo_str, obra_str):
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.add_page()
    
    # 1. Cabeçalho Esquerdo (Dados da Obra)
    pdf.rect(10, 10, 100, 20)
    pdf.set_xy(12, 12)
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(0, 5, f"OBRA: {obra_str.upper()}", ln=1)
    
    pdf.set_x(12)
    pdf.cell(0, 5, "DESCRIÇÃO: FECHAMENTO DE ABASTECIMENTO (POSTO)", ln=1)
    
    pdf.set_x(12)
    pdf.cell(0, 5, f"PERÍODO: {periodo_str}", ln=1)

    # 2. Cabeçalho Direito (Dados Financeiros do Fornecedor)
    pdf.rect(115, 10, 172, 20)
    pdf.set_xy(117, 12)
    pdf.cell(85, 5, f"FORNECEDOR: {dados_fornecedor.get('nome', '')[:40]}")
    pdf.cell(85, 5, f"PIX: {dados_fornecedor.get('pix', '')}", ln=1)
    
    pdf.set_x(117)
    pdf.cell(85, 5, f"BANCO: {dados_fornecedor.get('banco', '')} / AG: {dados_fornecedor.get('agencia', '')}")
    pdf.cell(85, 5, f"CONTA: {dados_fornecedor.get('conta', '')}", ln=1)

    # 3. Título Central
    pdf.set_y(35)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(277, 8, f"CONTROLE DE ABASTECIMENTO - {dados_fornecedor.get('nome', 'POSTO').upper()}", border=1, align="C", ln=1)

    # 4. Cabeçalho da Tabela
    pdf.set_font("Arial", 'B', 7)
    pdf.set_fill_color(240, 240, 240)
    
    colunas = [
        ("DATA", 18), ("FICHA", 18), ("PLACA", 18), ("PREFIXO", 18), 
        ("MÁQUINA / MOTORISTA", 55), ("PRODUTO", 22), ("QTD (L)", 18), 
        ("V. UNIT.", 18), ("TOTAL (R$)", 22), ("KM/HOR", 18), ("OBSERVAÇÃO", 52)
    ]
    
    for nome, largura in colunas:
        pdf.cell(largura, 7, nome, border=1, align="C", fill=True)
    pdf.ln()

    # 5. Linhas da Tabela
    pdf.set_font("Arial", '', 7)
    total_litros = 0
    total_dinheiro = 0

    for _, linha in df.iterrows():
        data_str = str(linha.get('data', ''))[:10]
        ficha_str = str(linha.get('numero_ficha', ''))[:15]
        placa_str = str(linha.get('placa', ''))[:8]
        prefixo_str = str(linha.get('prefixo', ''))[:8]
        
        # Junta Veículo e Motorista se houver
        motorista_str = str(linha.get('motorista', ''))
        equipamento = motorista_str[:35]
        
        produto_str = str(linha.get('tipo_combustivel', ''))[:12]
        qtd = float(linha.get('quantidade', 0))
        v_unit = float(linha.get('valor_unitario', 0))
        total_linha = float(linha.get('total', 0))
        horimetro_str = str(linha.get('horimetro', ''))[:8]
        obs_str = str(linha.get('observacao', ''))[:30]

        total_litros += qtd
        total_dinheiro += total_linha

        pdf.cell(18, 6, data_str, border=1, align="C")
        pdf.cell(18, 6, ficha_str, border=1, align="C")
        pdf.cell(18, 6, placa_str, border=1, align="C")
        pdf.cell(18, 6, prefixo_str, border=1, align="C")
        pdf.cell(55, 6, equipamento, border=1, align="L")
        pdf.cell(22, 6, produto_str, border=1, align="C")
        pdf.cell(18, 6, f"{qtd:,.2f}", border=1, align="R")
        pdf.cell(18, 6, f"R$ {v_unit:,.2f}", border=1, align="R")
        pdf.cell(22, 6, f"R$ {total_linha:,.2f}", border=1, align="R")
        pdf.cell(18, 6, horimetro_str, border=1, align="C")
        pdf.cell(52, 6, obs_str, border=1, align="L")
        pdf.ln()

    # 6. Linha de Totais
    pdf.set_font("Arial", 'B', 8)
    pdf.cell(145, 8, "TOTAIS GERAIS", border=1, align="R")
    pdf.cell(18, 8, f"{total_litros:,.2f}", border=1, align="R")
    pdf.cell(18, 8, "-", border=1, align="C")
    pdf.cell(22, 8, f"R$ {total_dinheiro:,.2f}", border=1, align="R")
    pdf.cell(70, 8, "", border=1, align="C")

    return pdf.output(dest='S').encode('latin-1')

# --- FUNÇÕES DE ACESSO AO BANCO ---
def get_data(table):
    try:
        res = supabase.table(table).select("*").execute()
        return pd.DataFrame(res.data)
    except Exception as e:
        st.error(f"⚠️ Erro ao conectar com banco ({table}): {e}")
        return pd.DataFrame()

def calcular_saldo_especifico(nome_tanque):
    df_ent = get_data("entradas_tanque")
    df_sai = get_data("abastecimentos")
    
    total_entrada = 0
    if not df_ent.empty and 'quantidade' in df_ent.columns and 'nome_tanque' in df_ent.columns:
        df_ent_filtrado = df_ent[df_ent['nome_tanque'] == nome_tanque]
        total_entrada = pd.to_numeric(df_ent_filtrado['quantidade']).sum()
        
    total_saida = 0
    if not df_sai.empty and 'origem' in df_sai.columns and 'quantidade' in df_sai.columns and 'nome_tanque' in df_sai.columns:
        df_sai_filtrado = df_sai[(df_sai['origem'] == 'Tanque Interno') & (df_sai['nome_tanque'] == nome_tanque)]
        total_saida = pd.to_numeric(df_sai_filtrado['quantidade']).sum()
        
    return total_entrada - total_saida

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
            st.write("") 
            submit = st.form_submit_button("ENTRAR NO SISTEMA", use_container_width=True)
            
            if submit:
                if u == "admin" and p == "obra2026":
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")
    st.stop()

# --- NAVEGAÇÃO / MENU LATERAL ---
def logout():
    st.session_state.logged_in = False
    st.rerun()

if os.path.exists("logo.png"):
    col_s1, col_s2, col_s3 = st.sidebar.columns([1, 2, 1])
    with col_s2:
        st.image("logo.png", use_container_width=True)
        
st.sidebar.markdown("<h3 style='text-align: center; margin-top:0; color:#1D9E75;'>Gestão de Obras</h3>", unsafe_allow_html=True)
st.sidebar.divider()

menu = st.sidebar.radio("Navegação Principal", ["🏠 Painel Início", "📝 Lançar Abastecimento", "🛢️ Tanques / Estoque", "🚜 Frota", "🏪 Fornecedores", "📋 Relatórios / PDF"])

st.sidebar.divider()
if st.sidebar.button("🚪 Sair do Sistema", use_container_width=True):
    logout()

st.sidebar.markdown("""
    <div style='text-align: center; color: #888; font-size: 11px; margin-top: 15px;'>
        ☁️ Armazenamento: Saudável<br>
        <i>Capacidade: 500MB (Plano Free)</i>
    </div>
""", unsafe_allow_html=True)


# --- PÁGINA: INÍCIO ---
if menu == "🏠 Painel Início":
    st.title("Painel de Controle da Frota")
    df_tanques = get_data("tanques")
    df_abast = get_data("abastecimentos")
    
    if not df_tanques.empty:
        st.subheader("Situação dos Tanques/Comboios")
        cols_t = st.columns(len(df_tanques))
        for idx, row in df_tanques.iterrows():
            nome_t = row['nome']
            cap_t = float(row.get('capacidade', 0))
            saldo_t = calcular_saldo_especifico(nome_t)
            
            with cols_t[idx]:
                limite_alerta = (cap_t * 0.15) if cap_t > 0 else 500
                if saldo_t <= limite_alerta:
                    st.markdown(f"<div class='saldo-low'>⚠️ {nome_t}<br>Saldo Baixo: {saldo_t:,.1f} L</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='saldo-ok'>✅ {nome_t}<br>Saldo Normal: {saldo_t:,.1f} L</div>", unsafe_allow_html=True)

    st.divider()
    if not df_abast.empty:
        df_abast['total'] = pd.to_numeric(df_abast['total'])
        df_abast['quantidade'] = pd.to_numeric(df_abast['quantidade'])
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Investimento Total (Operação)", f"R$ {df_abast['total'].sum():,.2f}")
        m2.metric("Volume Consumido (Litros)", f"{df_abast['quantidade'].sum():,.1f} L")
        m3.metric("Nº de Abastecimentos", len(df_abast))
        
        st.write("<br>", unsafe_allow_html=True)
        with st.expander("📈 Gráficos de Tendência Financeira", expanded=True):
            df_abast['data'] = pd.to_datetime(df_abast['data'])
            df_abast['Mes'] = df_abast['data'].dt.strftime('%m/%Y')
            f_gasto = px.bar(df_abast.groupby('Mes')['total'].sum().reset_index(), x='Mes', y='total', title="Gastos por Mês", color_discrete_sequence=['#1D9E75'])
            st.plotly_chart(f_gasto, use_container_width=True)
    else:
        st.info("Nenhum dado de abastecimento encontrado no banco de dados.")

# --- PÁGINA: LANÇAR ---
elif menu == "📝 Lançar Abastecimento":
    st.header("Lançar Saída de Combustível")
    df_veiculos = get_data("veiculos")
    df_fornecedores = get_data("fornecedores")
    df_abast = get_data("abastecimentos") 
    df_tanques = get_data("tanques")
    
    if df_veiculos.empty:
        st.warning("⚠️ Cadastre primeiro seus veículos na aba 'Frota'.")
    else:
        veiculo_selecionado = st.selectbox("Selecione o Veículo / Máquina", df_veiculos['prefixo'].tolist())
        
        info_veiculo = df_veiculos[df_veiculos['prefixo'] == veiculo_selecionado].iloc[0]
        combustivel_padrao = info_veiculo.get('tipo_combustivel_padrao', 'Não definido')
        placa_veiculo = info_veiculo.get('placa', 'S/P')
        
        maior_horimetro = 0.0
        if not df_abast.empty and 'horimetro' in df_abast.columns:
            historico_veiculo = df_abast[df_abast['prefixo'] == veiculo_selecionado]
            if not historico_veiculo.empty:
                maior_horimetro = float(historico_veiculo['horimetro'].max())
        
        st.info(f"⛽ Combustível Padrão: **{combustivel_padrao}** | 🏷️ Placa: **{placa_veiculo}** | ⏱️ Maior Horímetro/Km: **{maior_horimetro}**")
        
        origem_combustivel = st.radio("De onde saiu o combustível?", ["Posto Externo", "Tanque Interno"], horizontal=True)

        with st.form("form_lancamento", clear_on_submit=False):
            col_1, col_2, col_3 = st.columns([1, 2, 2])
            numero_ficha = col_1.text_input("Nº Ficha / Cupom")
            
            nome_tanque_selecionado = None
            if origem_combustivel == "Posto Externo":
                if df_fornecedores.empty:
                    fornecedor_posto = col_2.selectbox("Posto Fornecedor", ["Cadastre um fornecedor primeiro"])
                else:
                    fornecedor_posto = col_2.selectbox("Posto Fornecedor", df_fornecedores['nome'].tolist())
            else:
                if df_tanques.empty:
                    fornecedor_posto = col_2.selectbox("Selecione o Tanque", ["Cadastre um tanque primeiro"])
                else:
                    nome_tanque_selecionado = col_2.selectbox("Selecione o Tanque / Comboio", df_tanques['nome'].tolist())
                    fornecedor_posto = "Estoque Próprio"

            data_abastecimento = col_3.date_input("Data do Abastecimento")
            
            col_4, col_5, col_6 = st.columns(3)
            horimetro_atual = col_4.number_input("Horímetro / KM Atual", min_value=0.0, value=maior_horimetro, step=0.1)
            litros_abastecidos = col_5.number_input("Quantidade (Litros)", min_value=0.0)
            preco_unitario = col_6.number_input("Preço Unitário (R$)", min_value=0.0)

            col_7, col_8 = st.columns(2)
            nome_obra = col_7.text_input("Obra / Trecho / Local")
            observacao = col_8.text_input("Observações Gerais")
            
            if st.form_submit_button("Confirmar Saída"):
                saldo_disponivel_tanque = calcular_saldo_especifico(nome_tanque_selecionado) if nome_tanque_selecionado else 0

                if litros_abastecidos <= 0:
                    st.error("⚠️ O valor de litros deve ser maior que zero.")
                elif preco_unitario <= 0 and origem_combustivel == "Posto Externo":
                     st.warning("⚠️ O preço unitário está zerado. Tem certeza?")
                elif origem_combustivel == "Tanque Interno" and litros_abastecidos > saldo_disponivel_tanque:
                    st.error(f"⚠️ OPERAÇÃO BLOQUEADA: Saldo insuficiente no '{nome_tanque_selecionado}'. Tentativa de retirada: {litros_abastecidos}L | Saldo Real: {saldo_disponivel_tanque}L.")
                else:
                    try:
                        supabase.table("abastecimentos").insert({
                            "data": str(data_abastecimento), 
                            "numero_ficha": numero_ficha, 
                            "origem": origem_combustivel, 
                            "nome_tanque": nome_tanque_selecionado, 
                            "prefixo": veiculo_selecionado, 
                            "quantidade": litros_abastecidos, 
                            "valor_unitario": preco_unitario, 
                            "total": litros_abastecidos * preco_unitario, 
                            "fornecedor": fornecedor_posto, 
                            "tipo_combustivel": combustivel_padrao, 
                            "horimetro": horimetro_atual,
                            "obra": nome_obra, 
                            "observacao": observacao
                        }).execute()
                        st.success("Abastecimento registrado com sucesso no banco de dados!")
                        time.sleep(1.5)
                        st.rerun() 
                    except Exception as e:
                        st.error(f"⚠️ Erro ao salvar: {e}")

# --- PÁGINA: TANQUES ---
elif menu == "🛢️ Tanques / Estoque":
    st.header("Gestão de Estoque Interno")
    
    tab_visao, tab_entrada, tab_cadastro = st.tabs(["📊 Visão Geral de Saldo", "📥 Receber Combustível (Entrada)", "⚙️ Configurar Tanques"])
    
    with tab_cadastro:
        st.subheader("Cadastrar Novo Tanque ou Comboio")
        with st.form("form_novo_tanque", clear_on_submit=True):
            col_t1, col_t2 = st.columns([2, 1])
            nome_novo_tanque = col_t1.text_input("Identificação (Ex: Tanque Matriz, Comboio 01)")
            capacidade_tanque = col_t2.number_input("Capacidade Total (Litros)", min_value=0.0)
            
            if st.form_submit_button("Salvar Tanque"):
                if nome_novo_tanque:
                    try:
                        supabase.table("tanques").insert({"nome": nome_novo_tanque, "capacidade": capacidade_tanque}).execute()
                        st.success(f"Tanque '{nome_novo_tanque}' cadastrado!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro: {e}")
                    
        df_tanques = get_data("tanques")
        if not df_tanques.empty:
            st.divider()
            st.write("**Lista de Tanques Ativos:**")
            for _, row in df_tanques.iterrows():
                col_btn1, col_btn2 = st.columns([4, 1])
                col_btn1.write(f"🛢️ **{row['nome']}** | Capacidade: {row.get('capacidade', 0)} L")
                if col_btn2.button("Remover Tanque", key=f"del_t_{row['id']}"):
                    supabase.table("tanques").delete().eq("id", row['id']).execute()
                    st.rerun()

    with tab_entrada:
        df_tanques = get_data("tanques")
        df_fornecedores = get_data("fornecedores")
        
        if df_tanques.empty:
            st.warning("⚠️ Você precisa cadastrar um Tanque na aba 'Configurar Tanques' primeiro!")
        else:
            with st.form("form_entrada_combustivel", clear_on_submit=True):
                st.write("Registre aqui quando o caminhão da distribuidora vier encher o seu tanque.")
                col_e1, col_e2, col_e3 = st.columns(3)
                data_entrada = col_e1.date_input("Data do Recebimento")
                ficha_entrada = col_e2.text_input("Nº da Nota Fiscal")
                
                if df_fornecedores.empty:
                    fornecedor_entrada = col_e3.selectbox("Distribuidora", ["Sem cadastro"])
                else:
                    fornecedor_entrada = col_e3.selectbox("Distribuidora", df_fornecedores['nome'].tolist())
                
                col_e4, col_e5 = st.columns(2)
                tanque_destino = col_e4.selectbox("Para qual Tanque/Comboio foi descarregado?", df_tanques['nome'].tolist())
                combustivel_entrada = col_e5.selectbox("Produto Recebido", ["Diesel S10", "Diesel S500", "Gasolina", "Arla 32"])
                
                col_e7, col_e8 = st.columns(2)
                qtd_entrada = col_e7.number_input("Volume Descarregado (Litros)", min_value=0.0)
                preco_entrada = col_e8.number_input("Preço Unitário na NF (R$/L)", min_value=0.0)
                
                obs_entrada = st.text_input("Observações Adicionais")
                
                if st.form_submit_button("Confirmar Entrada no Tanque"):
                    if qtd_entrada <= 0:
                        st.error("A quantidade recebida deve ser maior que zero.")
                    else:
                        try:
                            supabase.table("entradas_tanque").insert({
                                "data": str(data_entrada), 
                                "numero_ficha": ficha_entrada, 
                                "fornecedor": fornecedor_entrada,
                                "nome_tanque": tanque_destino, 
                                "combustivel": combustivel_entrada, 
                                "quantidade": qtd_entrada, 
                                "valor_unitario": preco_entrada, 
                                "total": qtd_entrada * preco_entrada, 
                                "observacao": obs_entrada
                            }).execute()
                            st.success("Estoque do tanque atualizado com sucesso!")
                            time.sleep(1.5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao salvar: {e}")

    with tab_visao:
        df_tanques = get_data("tanques")
        if df_tanques.empty:
            st.info("Nenhum tanque cadastrado no sistema.")
        else:
            for _, row in df_tanques.iterrows():
                nome_do_tanque = row['nome']
                capacidade_maxima = float(row.get('capacidade', 0))
                saldo_atual = calcular_saldo_especifico(nome_do_tanque)
                
                with st.expander(f"📊 {nome_do_tanque} - Saldo: {saldo_atual:,.1f} L", expanded=True):
                    if capacidade_maxima > 0:
                        percentual_cheio = min(saldo_atual / capacidade_maxima, 1.0)
                        if percentual_cheio < 0: percentual_cheio = 0
                        
                        st.progress(percentual_cheio)
                        st.caption(f"Capacidade Máxima: {capacidade_maxima:,.1f} L | O tanque está com aproximadamente {percentual_cheio*100:.0f}% da capacidade.")
                    else:
                        st.caption("Capacidade máxima não configurada para este tanque.")

# --- PÁGINA: FROTA ---
elif menu == "🚜 Frota":
    st.header("Gestão de Veículos e Máquinas")
    tab_frota, tab_classes = st.tabs(["🚜 Frota Ativa", "📂 Classes (Categorias)"])

    with tab_classes:
        with st.form("form_nova_classe", clear_on_submit=True):
            nova_classe_nome = st.text_input("Criar Categoria (Ex: Retroescavadeiras, Caminhões Leves)")
            if st.form_submit_button("Salvar Categoria"):
                if nova_classe_nome:
                    try:
                        supabase.table("classes_frota").insert({"nome": nova_classe_nome}).execute()
                        st.success("Salvo com sucesso!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro: {e}")
                        
        df_classes = get_data("classes_frota")
        if not df_classes.empty:
            st.write("**Categorias Existentes:**")
            for _, row in df_classes.iterrows():
                col_c1, col_c2 = st.columns([3, 1])
                col_c1.write(f"• {row['nome']}")
                if col_c2.button("Remover", key=f"del_class_{row['id']}"):
                    supabase.table("classes_frota").delete().eq("id", row['id']).execute()
                    st.rerun()

    with tab_frota:
        df_classes = get_data("classes_frota")
        with st.form("form_novo_veiculo", clear_on_submit=True):
            col_v1, col_v2 = st.columns(2)
            prefixo_v = col_v1.text_input("Prefixo / Código (Ex: CAM-01)")
            placa_v = col_v2.text_input("Placa (Se houver)")
            
            col_v3, col_v4 = st.columns(2)
            if df_classes.empty:
                classe_v = col_v3.selectbox("Categoria", ["Cadastre uma categoria antes"])
            else:
                classe_v = col_v3.selectbox("Categoria", df_classes['nome'].tolist())
                
            combustivel_v = col_v4.selectbox("Combustível Principal", ["Diesel S10", "Diesel S500", "Gasolina", "Arla 32"])
            motorista_v = st.text_input("Motorista ou Operador Padrão")
            
            if st.form_submit_button("Cadastrar Equipamento na Frota"):
                try:
                    supabase.table("veiculos").insert({
                        "prefixo": prefixo_v, "placa": placa_v, "classe": classe_v, 
                        "motorista": motorista_v, "tipo_combustivel_padrao": combustivel_v
                    }).execute()
                    st.success("Veículo salvo!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro: {e}")
                    
        df_veiculos = get_data("veiculos")
        if not df_veiculos.empty:
            st.divider()
            for _, row in df_veiculos.iterrows():
                with st.expander(f"🚜 {row['prefixo']} | Placa: {row.get('placa', 'S/P')} | Operador: {row.get('motorista', 'Não definido')}"):
                    st.write(f"**Categoria:** {row.get('classe', '')} | **Motor:** {row.get('tipo_combustivel_padrao', '')}")
                    if st.button("Remover Veículo", key=f"del_v_{row['id']}"):
                        supabase.table("veiculos").delete().eq("id", row['id']).execute()
                        st.rerun()

# --- PÁGINA: FORNECEDORES ---
elif menu == "🏪 Fornecedores":
    st.header("Cadastro Completo de Fornecedores e Postos")
    tab_lista_forn, tab_novo_forn = st.tabs(["📋 Lista de Fornecedores", "➕ Adicionar Fornecedor"])
    
    with tab_novo_forn:
        with st.form("form_novo_fornecedor", clear_on_submit=True):
            col_f1, col_f2 = st.columns(2)
            nome_fantasia_forn = col_f1.text_input("Nome Fantasia (Como o posto é chamado)")
            razao_social_forn = col_f2.text_input("Razão Social (Nome oficial para NF)")
            
            col_f3, col_f4, col_f5, col_f6 = st.columns(4)
            cnpj_forn = col_f3.text_input("CNPJ")
            agencia_forn = col_f4.text_input("Agência")
            conta_forn = col_f5.text_input("Conta")
            pix_forn = col_f6.text_input("Chave PIX")
            
            col_f7, col_f8 = st.columns(2)
            banco_forn = col_f7.text_input("Nome do Banco")
            tipo_conta_forn = col_f8.selectbox("Tipo de Conta", ["Corrente", "Poupança", "Outra"])
            
            if st.form_submit_button("Salvar Fornecedor no Banco de Dados"):
                try:
                    supabase.table("fornecedores").insert({
                        "nome": nome_fantasia_forn, "razao_social": razao_social_forn, 
                        "cnpj": cnpj_forn, "agencia": agencia_forn, "conta": conta_forn, 
                        "pix": pix_forn, "banco": banco_forn, "tipo_conta": tipo_conta_forn
                    }).execute()
                    st.success("Fornecedor cadastrado com sucesso!")
                    time.sleep(1.5)
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro: {e}")

    with tab_lista_forn:
        df_fornecedores = get_data("fornecedores")
        if not df_fornecedores.empty:
            for _, row in df_fornecedores.iterrows():
                with st.expander(f"🏪 {row['nome'].upper()}"):
                    st.write(f"**Razão Social:** {row.get('razao_social', 'N/A')} | **CNPJ:** {row.get('cnpj', '---')}")
                    st.write(f"**Banco:** {row.get('banco', '---')} | **Tipo Conta:** {row.get('tipo_conta', '---')}")
                    st.write(f"**Agência:** {row.get('agencia', '---')} | **Conta:** {row.get('conta', '---')} | **PIX:** {row.get('pix', '---')}")
                    if st.button("Remover Cadastro", key=f"del_forn_{row['id']}"):
                        supabase.table("fornecedores").delete().eq("id", row['id']).execute()
                        st.rerun()
        else:
            st.info("Nenhum fornecedor cadastrado ainda.")

# --- PÁGINA: RELATÓRIOS E PDF ---
elif menu == "📋 Relatórios / PDF":
    st.header("Relatórios de Operação, Consumo e Fechamentos")
    df_abast = get_data("abastecimentos")
    df_fornecedores = get_data("fornecedores")

    if not df_abast.empty:
        # INTEGRAÇÃO: Junta os dados dos veículos para o PDF e Excel terem informações ricas
        df_veiculos = get_data("veiculos")
        if not df_veiculos.empty:
            df_abast = df_abast.merge(df_veiculos[['prefixo', 'classe', 'placa', 'motorista']], on='prefixo', how='left')

        # Garantia de colunas para bancos mais antigos
        for col_name in ['origem', 'obra', 'observacao', 'nome_tanque', 'numero_ficha', 'motorista']:
            if col_name not in df_abast.columns: 
                df_abast[col_name] = ""

        # --- SEÇÃO 1: GERADOR DE PDF PARA PAGAMENTO DE POSTOS ---
        st.subheader("🖨️ Gerar Fechamento Timbrado (Postos)")
        with st.container():
            col_pdf1, col_pdf2, col_pdf3 = st.columns([2, 1, 1])
            
            postos_disponiveis = df_fornecedores['nome'].tolist() if not df_fornecedores.empty else []
            posto_selecionado = col_pdf1.selectbox("Selecione o Posto para gerar o fechamento", ["Selecione..."] + postos_disponiveis)
            
            nome_da_obra = col_pdf2.text_input("Nome da Obra", "OBRA DE PAVIMENTAÇÃO")
            periodo_referencia = col_pdf3.text_input("Período (Ex: Abril/2026)", "Mês Atual")
            
            if st.button("Gerar PDF de Pagamento") and posto_selecionado != "Selecione...":
                # Filtra os abastecimentos apenas do posto selecionado
                df_filtrado_posto = df_abast[df_abast['fornecedor'] == posto_selecionado]
                
                # Busca os dados bancários completos daquele posto
                dados_fornecedor = df_fornecedores[df_fornecedores['nome'] == posto_selecionado].iloc[0].to_dict()
                
                if not df_filtrado_posto.empty:
                    pdf_bytes = gerar_pdf_fechamento_posto(df_filtrado_posto, dados_fornecedor, periodo_referencia, nome_da_obra)
                    st.success("✅ PDF Gerado! Clique abaixo para baixar.")
                    st.download_button(
                        label="⬇️ Baixar Fechamento em PDF",
                        data=pdf_bytes,
                        file_name=f"Fechamento_{posto_selecionado.replace(' ', '_')}.pdf",
                        mime="application/pdf"
                    )
                else:
                    st.warning("Não há nenhum abastecimento registrado neste posto para gerar fechamento.")

        st.divider()

        # --- SEÇÃO 2: TABELA DINÂMICA E CÁLCULO DE PRODUTIVIDADE ---
        st.subheader("📊 Visualização Geral e Exportação (Excel)")
        
        # Inteligência de Ordenação para cálculo de consumo
        df_abast['data_hora_ordenacao'] = pd.to_datetime(df_abast['data'])
        df_abast = df_abast.sort_values(by=['prefixo', 'data_hora_ordenacao', 'horimetro'])
        
        df_abast['horimetro_anterior'] = df_abast.groupby('prefixo')['horimetro'].shift(1)
        df_abast['horas_trabalhadas'] = df_abast['horimetro'] - df_abast['horimetro_anterior']
        
        df_abast['consumo_l_h'] = df_abast.apply(
            lambda row: round(row['quantidade'] / row['horas_trabalhadas'], 2) if pd.notna(row['horas_trabalhadas']) and row['horas_trabalhadas'] > 0 else None, 
            axis=1
        )
        df_abast['horas_trabalhadas'] = df_abast['horas_trabalhadas'].apply(lambda x: round(x, 1) if pd.notna(x) else None)

        # Filtros Livres na tela
        col_filtro1, col_filtro2 = st.columns(2)
        filtro_forn = col_filtro1.selectbox("Filtrar por Fornecedor/Posto", ["Todos"] + sorted(df_abast['fornecedor'].dropna().unique().tolist()))
        filtro_ori = col_filtro2.selectbox("Filtrar por Origem do Combustível", ["Todas"] + df_abast['origem'].dropna().unique().tolist())
        
        if filtro_forn != "Todos": 
            df_abast = df_abast[df_abast['fornecedor'] == filtro_forn]
        if filtro_ori != "Todas": 
            df_abast = df_abast[df_abast['origem'] == filtro_ori]

        # Seleção e formatação de colunas para visualização
        colunas_para_mostrar = [
            'data', 'origem', 'nome_tanque', 'numero_ficha', 'fornecedor', 'prefixo', 'classe', 
            'placa', 'motorista', 'tipo_combustivel', 'quantidade', 'valor_unitario', 'total', 
            'horimetro', 'horas_trabalhadas', 'consumo_l_h', 'obra', 'observacao'
        ]
        
        df_final_exportacao = df_abast[[c for c in colunas_para_mostrar if c in df_abast.columns]]
        
        dicionario_nomes = {
            'data': 'Data', 'origem': 'Origem', 'nome_tanque': 'Tanque Próprio', 'numero_ficha': 'Nº Ficha', 
            'fornecedor': 'Posto / Distribuidora', 'prefixo': 'Prefixo', 'classe': 'Classe', 'placa': 'Placa', 
            'motorista': 'Operador / Motorista', 'tipo_combustivel': 'Produto', 'quantidade': 'Litros', 
            'valor_unitario': 'R$/L', 'total': 'Total (R$)', 'horimetro': 'Horímetro/KM', 
            'horas_trabalhadas': 'Horas Trab.', 'consumo_l_h': 'Consumo (L/h)', 'obra': 'Obra/Local', 'observacao': 'Obs'
        }
        df_final_exportacao = df_final_exportacao.rename(columns=dicionario_nomes)

        st.dataframe(df_final_exportacao, use_container_width=True)

        # Lógica Robusta de Excel
        buffer_excel = io.BytesIO()
        with pd.ExcelWriter(buffer_excel, engine='xlsxwriter') as escritor_excel:
            df_final_exportacao.to_excel(escritor_excel, index=False, sheet_name='Produtividade')
            planilha = escritor_excel.sheets['Produtividade']
            
            for index_coluna, nome_coluna in enumerate(df_final_exportacao.columns):
                try:
                    tamanho_titulo = len(str(nome_coluna))
                    tamanho_conteudo = df_final_exportacao[nome_coluna].astype(str).str.len().max()
                    tamanho_ideal = tamanho_titulo if pd.isna(tamanho_conteudo) else max(tamanho_titulo, int(tamanho_conteudo))
                    planilha.set_column(index_coluna, index_coluna, tamanho_ideal + 2)
                except Exception:
                    planilha.set_column(index_coluna, index_coluna, 15)
        
        st.download_button(
            label="📥 Exportar Dados para Excel",
            data=buffer_excel.getvalue(),
            file_name=f"Relatorio_Frota_Copa_{datetime.now().strftime('%d_%m_%Y')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("Nenhum lançamento de abastecimento registrado ainda para gerar relatórios.")
