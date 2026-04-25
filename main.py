import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime
import plotly.express as px
import os
import time
import io

# --- CONFIGURAÇÃO E ESTÉTICA "PAVCONTROL" ---
st.set_page_config(page_title="Gestão de Frota", layout="wide")

st.markdown("""
    <style>
    /* Fundo da tela e fontes */
    .main { background-color: #f4f6f8; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    
    /* Títulos de campos (Labels) menores, maiúsculos e elegantes */
    .stTextInput>label, .stSelectbox>label, .stNumberInput>label, .stDateInput>label {
        font-size: 11px !important; text-transform: uppercase; color: #666; letter-spacing: 0.05em; font-weight: 600;
    }
    
    /* Estilo dos Botões Principais (Verde PavControl) */
    div.stButton > button:first-child {
        background-color: #1D9E75; color: white; border: none; border-radius: 6px; font-weight: 600; padding: 0.5rem 1rem;
    }
    div.stButton > button:first-child:hover { background-color: #0F6E56; border-color: #0F6E56; color: white;}
    
    /* Formulários estilo "Card" branco */
    div[data-testid="stForm"] {
        border: 1px solid #e0e6ed; border-radius: 12px; padding: 1.5rem; background-color: #ffffff; box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    
    /* Indicadores de Saldo */
    .saldo-ok { color: #3B6D11; font-weight: bold; background-color: #EAF3DE; padding: 12px; border-radius: 8px; border: 1px solid #C0DD97; font-size: 1.1rem; margin-bottom: 1rem;}
    .saldo-low { color: #854F0B; font-weight: bold; background-color: #FAEEDA; padding: 12px; border-radius: 8px; border: 1px solid #FAC775; font-size: 1.1rem; margin-bottom: 1rem;}
    </style>
""", unsafe_allow_html=True)

# --- CONEXÃO BANCO DE DADOS ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- SISTEMA DE LOGIN (COM LOGO) ---
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

# --- NAVEGAÇÃO ---
def logout():
    st.session_state.logged_in = False
    st.rerun()

if os.path.exists("logo.png"):
    col_s1, col_s2, col_s3 = st.sidebar.columns([1, 2, 1])
    with col_s2:
        st.image("logo.png", use_container_width=True)
        
st.sidebar.markdown("<h3 style='text-align: center; margin-top:0; color:#1D9E75;'>Gestão de Obras</h3>", unsafe_allow_html=True)
st.sidebar.divider()

menu = st.sidebar.radio("Menu Principal", ["🏠 Painel Início", "📝 Lançar Abastec.", "🛢️ Tanques / Comboios", "🚜 Frota", "🏪 Fornecedores", "📋 Relatórios"])
st.sidebar.divider()
if st.sidebar.button("🚪 Sair", use_container_width=True):
    logout()

# --- FUNÇÕES CORE ---
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

# --- PÁGINA: INÍCIO ---
if menu == "🏠 Painel Início":
    st.title("Painel de Controle")
    df = get_data("abastecimentos")
    df_tanques = get_data("tanques")
    
    # Renderiza o saldo de todos os tanques cadastrados na tela inicial
    if not df_tanques.empty:
        st.subheader("Situação dos Tanques/Comboios")
        cols_t = st.columns(len(df_tanques))
        for idx, row in df_tanques.iterrows():
            nome_t = row['nome']
            cap_t = row.get('capacidade', 0)
            saldo_t = calcular_saldo_especifico(nome_t)
            
            with cols_t[idx]:
                if saldo_t < (cap_t * 0.15) if cap_t else 500: # Alerta se menor que 15% ou 500L
                    st.markdown(f"<div class='saldo-low'>⚠️ {nome_t}<br>Saldo: {saldo_t:,.1f} L</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='saldo-ok'>✅ {nome_t}<br>Saldo: {saldo_t:,.1f} L</div>", unsafe_allow_html=True)

    st.divider()
    if not df.empty:
        df['total'] = pd.to_numeric(df['total'])
        df['quantidade'] = pd.to_numeric(df['quantidade'])
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Investimento Total (Operação)", f"R$ {df['total'].sum():,.2f}")
        m2.metric("Volume Consumido (L)", f"{df['quantidade'].sum():,.1f} L")
        m3.metric("Nº de Abastecimentos", len(df))
        
        st.write("<br>", unsafe_allow_html=True)
        with st.expander("📈 Gráficos de Tendência"):
            df['data'] = pd.to_datetime(df['data'])
            df['Mes'] = df['data'].dt.strftime('%m/%Y')
            f_gasto = px.bar(df.groupby('Mes')['total'].sum().reset_index(), x='Mes', y='total', title="Gastos Mensais", color_discrete_sequence=['#1D9E75'])
            st.plotly_chart(f_gasto, use_container_width=True)
    else:
        st.info("Nenhum dado encontrado.")

# --- PÁGINA: LANÇAR ---
elif menu == "📝 Lançar Abastec.":
    st.header("Lançamento de Abastecimento (Saída)")
    df_v = get_data("veiculos")
    df_f = get_data("fornecedores")
    df_abast = get_data("abastecimentos") 
    df_tanques = get_data("tanques")
    
    if not df_v.empty:
        veic_sel = st.selectbox("Selecione o Veículo/Máquina", df_v['prefixo'].tolist())
        
        info_v = df_v[df_v['prefixo'] == veic_sel].iloc[0]
        comb_v = info_v.get('tipo_combustivel_padrao', 'Não definido')
        placa_v = info_v.get('placa', 'N/A')
        
        maior_horimetro = 0.0
        if not df_abast.empty and 'horimetro' in df_abast.columns:
            hist_veiculo = df_abast[df_abast['prefixo'] == veic_sel]
            if not hist_veiculo.empty:
                maior_horimetro = float(hist_veiculo['horimetro'].max())
        
        st.info(f"⛽ Combustível: **{comb_v}** | 🏷️ Placa: **{placa_v}** | ⏱️ Maior Horímetro Registrado: **{maior_horimetro}**")
        
        origem_comb = st.radio("Origem do Combustível:", ["Posto Externo", "Tanque Interno"], horizontal=True)

        with st.form("form_abast", clear_on_submit=False):
            c0, c1, c2 = st.columns([1, 2, 2])
            numero_ficha = c0.text_input("Nº Ficha / Cupom")
            
            nome_tanque_sel = None
            if origem_comb == "Posto Externo":
                posto = c1.selectbox("Posto Fornecedor", df_f['nome'].tolist() if not df_f.empty else [])
            else:
                if df_tanques.empty:
                    posto = c1.selectbox("Selecione o Tanque", ["Cadastre um tanque primeiro"])
                else:
                    nome_tanque_sel = c1.selectbox("Selecione o Tanque / Comboio", df_tanques['nome'].tolist())
                    posto = "Estoque Próprio"

            data = c2.date_input("Data do Abastecimento")
            
            c3, c4, c5 = st.columns(3)
            horimetro = c3.number_input("Horímetro / KM Atual", min_value=0.0, value=maior_horimetro, step=0.1)
            litros = c4.number_input("Litros", min_value=0.0)
            preco = c5.number_input("Preço Unitário (R$)", min_value=0.0)

            c6, c7 = st.columns(2)
            obra = c6.text_input("Obra / Trecho")
            observacao = c7.text_input("Observações Gerais")
            
            if st.form_submit_button("Confirmar Saída"):
                saldo_tanque = calcular_saldo_especifico(nome_tanque_sel) if nome_tanque_sel else 0

                if litros <= 0:
                    st.error("Erro: Litros devem ser maiores que zero.")
                elif origem_comb == "Tanque Interno" and litros > saldo_tanque:
                    st.error(f"⚠️ ERRO: Saldo insuficiente no {nome_tanque_sel}! Você tentou retirar {litros}L, mas só há {saldo_tanque}L disponíveis.")
                else:
                    try:
                        supabase.table("abastecimentos").insert({
                            "data": str(data), "numero_ficha": numero_ficha, "origem": origem_comb, 
                            "nome_tanque": nome_tanque_sel, "prefixo": veic_sel, 
                            "quantidade": litros, "valor_unitario": preco, "total": litros*preco, 
                            "fornecedor": posto, "tipo_combustivel": comb_v, "horimetro": horimetro,
                            "obra": obra, "observacao": observacao
                        }).execute()
                        st.success("Abastecimento registrado com sucesso!")
                        time.sleep(1.5)
                        st.rerun() 
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")
    else:
        st.warning("Cadastre primeiro a Frota.")

# --- PÁGINA: MÚLTIPLOS TANQUES ---
elif menu == "🛢️ Tanques / Comboios":
    st.header("Gestão de Estoque Próprio")
    
    t_painel, t_entrada, t_gerenciar = st.tabs(["📊 Visão Geral", "📥 Lançar Entrada (Compra)", "⚙️ Cadastrar Tanques"])
    
    with t_gerenciar:
        st.subheader("Cadastrar Novo Tanque ou Comboio")
        with st.form("form_novo_tanque", clear_on_submit=True):
            c1, c2 = st.columns([2, 1])
            nome_t = c1.text_input("Nome de Identificação (Ex: Tanque Matriz, Comboio 01)")
            cap_t = c2.number_input("Capacidade Total (Litros)", min_value=0.0)
            if st.form_submit_button("Criar Tanque"):
                if nome_t:
                    supabase.table("tanques").insert({"nome": nome_t, "capacidade": cap_t}).execute()
                    st.success("Tanque cadastrado!")
                    time.sleep(1)
                    st.rerun()
                    
        df_tanques = get_data("tanques")
        if not df_tanques.empty:
            st.divider()
            st.write("**Tanques Cadastrados:**")
            for _, r in df_tanques.iterrows():
                col1, col2 = st.columns([4, 1])
                col1.write(f"🛢️ **{r['nome']}** (Capacidade: {r.get('capacidade', 0)} L)")
                if col2.button("Remover", key=f"del_t_{r['id']}"):
                    supabase.table("tanques").delete().eq("id", r['id']).execute()
                    st.rerun()

    with t_entrada:
        df_tanques = get_data("tanques")
        df_f = get_data("fornecedores")
        
        if df_tanques.empty:
            st.warning("Cadastre um Tanque na aba '⚙️ Cadastrar Tanques' primeiro!")
        else:
            with st.form("form_entrada", clear_on_submit=True):
                st.write("Registre o combustível entregue pela distribuidora no seu tanque.")
                c1, c2, c3 = st.columns(3)
                data_ent = c1.date_input("Data do Recebimento")
                ficha_ent = c2.text_input("Nº da Ficha / NF")
                forn_ent = c3.selectbox("Distribuidora", df_f['nome'].tolist() if not df_f.empty else ["Sem fornecedor"])
                
                c4, c5 = st.columns(2)
                tanque_dest = c4.selectbox("Para qual Tanque/Comboio foi?", df_tanques['nome'].tolist())
                comb_ent = c5.selectbox("Produto Recebido", ["Diesel S10", "Diesel S500", "Gasolina", "Arla 32"])
                
                c7, c8 = st.columns(2)
                qtd_ent = c7.number_input("Quantidade (Litros)", min_value=0.0)
                preco_ent = c8.number_input("Preço Unitário (R$/L)", min_value=0.0)
                
                obs_ent = st.text_input("Observações")
                
                if st.form_submit_button("Confirmar Recebimento"):
                    if qtd_ent > 0:
                        supabase.table("entradas_tanque").insert({
                            "data": str(data_ent), "numero_ficha": ficha_ent, "fornecedor": forn_ent,
                            "nome_tanque": tanque_dest, "combustivel": comb_ent, "quantidade": qtd_ent, 
                            "valor_unitario": preco_ent, "total": qtd_ent * preco_ent, "observacao": obs_ent
                        }).execute()
                        st.success("Estoque do tanque atualizado!")
                        time.sleep(1.5)
                        st.rerun()

    with t_painel:
        df_tanques = get_data("tanques")
        if df_tanques.empty:
            st.info("Nenhum tanque cadastrado.")
        else:
            for _, row in df_tanques.iterrows():
                nome = row['nome']
                cap = row.get('capacidade', 0)
                saldo = calcular_saldo_especifico(nome)
                
                with st.expander(f"📊 {nome} - Saldo Atual: {saldo:,.1f} L", expanded=True):
                    if cap > 0:
                        perc = min(saldo / cap, 1.0) if cap else 0
                        st.progress(perc)
                        st.caption(f"Capacidade Total: {cap:,.1f} L ({perc*100:.0f}% cheio)")
                    else:
                        st.caption("Capacidade total não definida.")

# --- PÁGINA: FROTA ---
elif menu == "🚜 Frota":
    st.header("Gestão de Frota e Categorias")
    tab_frota, tab_classes = st.tabs(["🚜 Veículos", "📂 Gerenciar Classes"])

    with tab_classes:
        with st.form("form_classe", clear_on_submit=True):
            nova_classe = st.text_input("Nome da Classe (Ex: Caçambas)")
            if st.form_submit_button("Criar Classe") and nova_classe:
                supabase.table("classes_frota").insert({"nome": nova_classe}).execute()
                st.rerun()
        df_classes = get_data("classes_frota")
        if not df_classes.empty:
            for _, c in df_classes.iterrows():
                col_c1, col_c2 = st.columns([3, 1])
                col_c1.write(f"• {c['nome']}")
                if col_c2.button("Excluir", key=f"del_cl_{c['id']}"):
                    supabase.table("classes_frota").delete().eq("id", c['id']).execute()
                    st.rerun()

    with tab_frota:
        df_classes = get_data("classes_frota")
        with st.form("form_veic", clear_on_submit=True):
            c1, c2 = st.columns(2)
            prefixo = c1.text_input("Prefixo (ID)")
            placa = c2.text_input("Placa")
            c3, c4 = st.columns(2)
            classe_sel = c3.selectbox("Classe", df_classes['nome'].tolist() if not df_classes.empty else [])
            combustivel = c4.selectbox("Combustível Padrão", ["Diesel S10", "Diesel S500", "Gasolina", "Arla 32"])
            motorista = st.text_input("Motorista/Operador")
            if st.form_submit_button("Salvar Veículo"):
                supabase.table("veiculos").insert({"prefixo": prefixo, "placa": placa, "classe": classe_sel, "motorista": motorista, "tipo_combustivel_padrao": combustivel}).execute()
                st.rerun()
        df_v = get_data("veiculos")
        if not df_v.empty:
            for i, r in df_v.iterrows():
                with st.expander(f"🚜 {r['prefixo']} - Placa: {r.get('placa', 'S/P')}"):
                    st.write(f"Classe: {r.get('classe', '')} | Motorista: {r['motorista']}")
                    if st.button("Remover", key=f"v_{r['id']}"):
                        supabase.table("veiculos").delete().eq("id", r['id']).execute()
                        st.rerun()

# --- PÁGINA: FORNECEDORES (COMPLETA) ---
elif menu == "🏪 Fornecedores":
    st.header("Fornecedores e Postos")
    t1, t2 = st.tabs(["Lista de Parceiros", "Novo Fornecedor"])
    with t2:
        with st.form("new_f", clear_on_submit=True):
            nome_fantasia = st.text_input("Nome Fantasia")
            razao_social = st.text_input("Razão Social")
            c1, c2, c3, c4 = st.columns(4)
            cnpj = c1.text_input("CNPJ")
            agencia = c2.text_input("Agência")
            conta = c3.text_input("Conta")
            pix = c4.text_input("Chave PIX")
            cb1, cb2 = st.columns(2)
            banco = cb1.text_input("Nome do Banco")
            tipo_conta = cb2.selectbox("Tipo de Conta", ["Corrente", "Poupança", "Outra"])
            if st.form_submit_button("Cadastrar Fornecedor"):
                supabase.table("fornecedores").insert({"nome": nome_fantasia, "razao_social": razao_social, "cnpj": cnpj, "agencia": agencia, "conta": conta, "pix": pix, "banco": banco, "tipo_conta": tipo_conta}).execute()
                st.rerun()
    with t1:
        df_f = get_data("fornecedores")
        if not df_f.empty:
            for i, r in df_f.iterrows():
                with st.expander(f"🏪 {r['nome']}"):
                    st.write(f"CNPJ: {r.get('cnpj', '')} | Banco: {r.get('banco', '')} | Ag/Cc: {r.get('agencia', '')}/{r.get('conta', '')} | PIX: {r.get('pix', '')}")
                    if st.button("Remover", key=f"f_{r['id']}"):
                        supabase.table("fornecedores").delete().eq("id", r['id']).execute()
                        st.rerun()

# --- PÁGINA: RELATÓRIOS ---
elif menu == "📋 Relatórios":
    st.header("Relatórios de Operação e Produtividade")
    df = get_data("abastecimentos")

    if not df.empty:
        df_v = get_data("veiculos")
        if not df_v.empty:
            df = df.merge(df_v[['prefixo', 'classe', 'placa']], on='prefixo', how='left')

        # Garante colunas
        for col in ['origem', 'obra', 'observacao', 'nome_tanque', 'numero_ficha']:
            if col not in df.columns: df[col] = ""

        df['data_hora_ordenacao'] = pd.to_datetime(df['data'])
        df = df.sort_values(by=['prefixo', 'data_hora_ordenacao', 'horimetro'])
        
        df['horimetro_anterior'] = df.groupby('prefixo')['horimetro'].shift(1)
        df['horas_trabalhadas'] = df['horimetro'] - df['horimetro_anterior']
        
        df['consumo_l_h'] = df.apply(
            lambda row: round(row['quantidade'] / row['horas_trabalhadas'], 2) if pd.notna(row['horas_trabalhadas']) and row['horas_trabalhadas'] > 0 else None, axis=1)
        df['horas_trabalhadas'] = df['horas_trabalhadas'].apply(lambda x: round(x, 1) if pd.notna(x) else None)

        col_f1, col_f2 = st.columns(2)
        filtro_fornecedor = col_f1.selectbox("Fornecedor / Posto", ["Todos"] + sorted(df['fornecedor'].dropna().unique().tolist()))
        filtro_origem = col_f2.selectbox("Origem do Combustível", ["Todas"] + df['origem'].dropna().unique().tolist())
        
        if filtro_fornecedor != "Todos": df = df[df['fornecedor'] == filtro_fornecedor]
        if filtro_origem != "Todas": df = df[df['origem'] == filtro_origem]

        colunas_ordenadas = ['data', 'origem', 'nome_tanque', 'numero_ficha', 'fornecedor', 'prefixo', 'classe', 'placa', 'tipo_combustivel', 'quantidade', 'valor_unitario', 'total', 'horimetro', 'horas_trabalhadas', 'consumo_l_h', 'obra', 'observacao']
        df_export = df[[c for c in colunas_ordenadas if c in df.columns]]
        
        nomes = {'data': 'Data', 'origem': 'Origem', 'nome_tanque': 'Nome Tanque', 'numero_ficha': 'Ficha/NF', 'fornecedor': 'Posto/Forn.', 'prefixo': 'Prefixo', 'classe': 'Classe', 'placa': 'Placa', 'tipo_combustivel': 'Combustível', 'quantidade': 'Litros', 'valor_unitario': 'R$/L', 'total': 'Total (R$)', 'horimetro': 'Horímetro/KM', 'horas_trabalhadas': 'Horas Trab.', 'consumo_l_h': 'Consumo (L/h)', 'obra': 'Obra/Trecho', 'observacao': 'Obs'}
        df_export = df_export.rename(columns=nomes)

        st.dataframe(df_export, use_container_width=True)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_export.to_excel(writer, index=False, sheet_name='Produtividade')
            worksheet = writer.sheets['Produtividade']
            for i, col in enumerate(df_export.columns):
                tamanho = max(len(str(col)), df_export[col].astype(str).str.len().max() if not df_export.empty else 10)
                worksheet.set_column(i, i, int(tamanho) + 2)
        
        st.download_button("📥 Baixar Relatório Completo em Excel", data=output.getvalue(), file_name="Relatorio_Gestao.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        st.info("Nenhum abastecimento encontrado.")
