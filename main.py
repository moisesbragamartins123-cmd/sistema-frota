import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime
import plotly.express as px
import os
import time
import io

# Configuração da Página
st.set_page_config(page_title="Copa Engenharia", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    [data-testid="stMetricValue"] { font-size: 1.8rem !important; color: #003366; font-weight: 700; }
    .stButton>button { border-radius: 8px; font-weight: bold; }
    .saldo-ok { color: #3B6D11; font-weight: bold; background-color: #EAF3DE; padding: 10px; border-radius: 8px; border: 1px solid #C0DD97; }
    .saldo-low { color: #854F0B; font-weight: bold; background-color: #FAEEDA; padding: 10px; border-radius: 8px; border: 1px solid #FAC775; }
    </style>
""", unsafe_allow_html=True)

# Conexão Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown('<style>body { background-color: #1a1a2e; }</style>', unsafe_allow_html=True)
    st.write("<br><br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.2, 1]) 
    with col2:
        with st.form("login_form"):
            st.markdown("<h2 style='text-align: center; color: #333; margin-top:0;'>Acesso Restrito</h2>", unsafe_allow_html=True)
            u = st.text_input("Usuário")
            p = st.text_input("Senha", type="password")
            submit = st.form_submit_button("ENTRAR", use_container_width=True)
            if submit:
                if u == "admin" and p == "obra2026":
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Dados de acesso incorretos")
    st.stop()

def logout():
    st.session_state.logged_in = False
    st.rerun()

st.sidebar.markdown("<h3 style='text-align: center; margin-top:0;'>Copa Engenharia</h3>", unsafe_allow_html=True)
st.sidebar.divider()
menu = st.sidebar.radio("Menu Principal", ["🏠 Início", "📝 Lançar Abastec.", "🛢️ Tanque Interno", "🚜 Frota", "🏪 Fornecedores", "📋 Relatórios"])
st.sidebar.divider()
if st.sidebar.button("🚪 Sair", use_container_width=True):
    logout()

def get_data(table):
    try:
        res = supabase.table(table).select("*").execute()
        return pd.DataFrame(res.data)
    except Exception as e:
        return pd.DataFrame()

# FUNÇÃO PARA CALCULAR SALDO DO TANQUE
def calcular_saldo_tanque():
    df_ent = get_data("entradas_tanque")
    df_sai = get_data("abastecimentos")
    
    total_entrada = pd.to_numeric(df_ent['quantidade']).sum() if not df_ent.empty else 0
    # Soma apenas saídas que vieram do Tanque
    total_saida = 0
    if not df_sai.empty and 'origem' in df_sai.columns:
        df_sai_tanque = df_sai[df_sai['origem'] == 'Tanque da Obra']
        total_saida = pd.to_numeric(df_sai_tanque['quantidade']).sum()
        
    return total_entrada - total_saida, total_entrada, total_saida

# --- PÁGINA: INÍCIO ---
if menu == "🏠 Início":
    st.title("Painel de Controle")
    df = get_data("abastecimentos")
    
    saldo_atual, t_ent, t_sai = calcular_saldo_tanque()
    
    # Renderiza o alerta de saldo inspirado no PavControl
    if saldo_atual < 500:
        st.markdown(f"<div class='saldo-low'>⚠️ Atenção: Saldo atual do tanque é de apenas {saldo_atual:,.1f} Litros!</div><br>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='saldo-ok'>✅ Saldo atual do tanque: {saldo_atual:,.1f} Litros.</div><br>", unsafe_allow_html=True)

    if not df.empty:
        df['total'] = pd.to_numeric(df['total'])
        df['quantidade'] = pd.to_numeric(df['quantidade'])
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Investimento Total (Posto + Tanque)", f"R$ {df['total'].sum():,.2f}")
        m2.metric("Volume Consumido pelas Máquinas", f"{df['quantidade'].sum():,.1f} L")
        m3.metric("Nº de Abastecimentos", len(df))
    else:
        st.info("Nenhum dado encontrado.")

# --- PÁGINA: LANÇAR ---
elif menu == "📝 Lançar Abastec.":
    st.header("Registrar Abastecimento (Saída)")
    df_v = get_data("veiculos")
    df_f = get_data("fornecedores")
    df_abast = get_data("abastecimentos") 
    
    if not df_v.empty:
        veic_sel = st.selectbox("Selecione o Veículo/Máquina", df_v['prefixo'].tolist())
        info_v = df_v[df_v['prefixo'] == veic_sel].iloc[0]
        comb_v = info_v.get('tipo_combustivel_padrao', 'Não definido')
        
        maior_horimetro = 0.0
        if not df_abast.empty and 'horimetro' in df_abast.columns:
            hist_veiculo = df_abast[df_abast['prefixo'] == veic_sel]
            if not hist_veiculo.empty:
                maior_horimetro = float(hist_veiculo['horimetro'].max())
        
        st.info(f"⛽ Combustível Padrão: {comb_v} | ⏱️ Maior Horímetro/Km: {maior_horimetro}")
        
        origem_comb = st.radio("De onde saiu o combustível?", ["Posto Externo", "Tanque da Obra"], horizontal=True)
        
        with st.form("form_abast", clear_on_submit=False):
            c0, c1, c2 = st.columns([1, 2, 2])
            numero_ficha = c0.text_input("Nº da Ficha/Nota")
            
            if origem_comb == "Posto Externo":
                fornecedor = c1.selectbox("Posto Fornecedor", df_f['nome'].tolist() if not df_f.empty else ["Cadastre um posto"])
            else:
                fornecedor = c1.text_input("Fornecedor", value="Estoque Interno", disabled=True)
                
            data = c2.date_input("Data do Abastecimento")
            
            c3, c4, c5 = st.columns(3)
            horimetro = c3.number_input("Horímetro / KM", min_value=0.0, value=maior_horimetro, step=0.1)
            litros = c4.number_input("Litros", min_value=0.0)
            preco = c5.number_input("Preço Unitário (R$)", min_value=0.0)
            
            c6, c7 = st.columns([1, 2])
            obra = c6.text_input("Obra / Trecho (Opcional)")
            obs = c7.text_input("Observações (Opcional)")
            
            if st.form_submit_button("Confirmar Lançamento"):
                saldo, _, _ = calcular_saldo_tanque()
                
                if origem_comb == "Tanque da Obra" and litros > saldo:
                    st.error(f"⚠️ ERRO: Saldo insuficiente no tanque. Você tentou retirar {litros}L, mas só há {saldo}L disponíveis.")
                elif litros <= 0:
                    st.error("Erro: Litros devem ser maiores que zero.")
                else:
                    try:
                        supabase.table("abastecimentos").insert({
                            "origem": origem_comb, "data": str(data), "numero_ficha": numero_ficha, 
                            "prefixo": veic_sel, "quantidade": litros, "valor_unitario": preco, 
                            "total": litros*preco, "fornecedor": fornecedor, "tipo_combustivel": comb_v, 
                            "horimetro": horimetro, "obra": obra, "observacao": obs
                        }).execute()
                        st.success("Salvo com sucesso!")
                        time.sleep(1)
                        st.rerun() 
                    except Exception as e:
                        st.error(f"Erro: {e}")

# --- PÁGINA: TANQUE INTERNO ---
elif menu == "🛢️ Tanque Interno":
    st.header("Gestão do Tanque da Obra")
    saldo_atual, t_ent, t_sai = calcular_saldo_tanque()
    
    col_t1, col_t2, col_t3 = st.columns(3)
    col_t1.metric("Total Comprado (Entradas)", f"{t_ent:,.1f} L")
    col_t2.metric("Total Abastecido (Saídas)", f"{t_sai:,.1f} L")
    col_t3.metric("SALDO DISPONÍVEL", f"{saldo_atual:,.1f} L")
    
    st.divider()
    st.subheader("Registrar Chegada de Combustível (Entrada)")
    df_f = get_data("fornecedores")
    
    with st.form("form_entrada", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        data_ent = c1.date_input("Data do Recebimento")
        ficha_ent = c2.text_input("Nº Ficha / Nota Fiscal")
        forn_ent = c3.selectbox("Distribuidora / Fornecedor", df_f['nome'].tolist() if not df_f.empty else [])
        
        c4, c5, c6 = st.columns(3)
        comb_ent = c4.selectbox("Combustível", ["Diesel S10", "Diesel S500", "Gasolina", "Arla 32"])
        qtd_ent = c5.number_input("Quantidade Recebida (Litros)", min_value=0.0)
        preco_ent = c6.number_input("Preço Unitário (R$/L)", min_value=0.0)
        
        obs_ent = st.text_input("Observações")
        
        if st.form_submit_button("Confirmar Entrada no Tanque"):
            if qtd_ent > 0:
                supabase.table("entradas_tanque").insert({
                    "data": str(data_ent), "numero_ficha": ficha_ent, "fornecedor": forn_ent,
                    "combustivel": comb_ent, "quantidade": qtd_ent, "valor_unitario": preco_ent,
                    "total": qtd_ent * preco_ent, "observacao": obs_ent
                }).execute()
                st.success("Entrada registrada! Saldo atualizado.")
                time.sleep(1.5)
                st.rerun()

# --- PÁGINA: FROTA (MANTIDA IGUAL) ---
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
                st.write(f"• {c['nome']}")

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
                supabase.table("veiculos").insert({
                    "prefixo": prefixo, "placa": placa, "classe": classe_sel, 
                    "motorista": motorista, "tipo_combustivel_padrao": combustivel
                }).execute()
                st.rerun()

# --- PÁGINA: FORNECEDORES (MANTIDA IGUAL) ---
elif menu == "🏪 Fornecedores":
    st.header("Fornecedores e Postos")
    with st.form("new_f", clear_on_submit=True):
        c1, c2 = st.columns(2)
        nome_fantasia = c1.text_input("Nome Fantasia")
        razao_social = c2.text_input("Razão Social")
        if st.form_submit_button("Cadastrar Fornecedor"):
            supabase.table("fornecedores").insert({"nome": nome_fantasia, "razao_social": razao_social}).execute()
            st.rerun()

# --- PÁGINA: RELATÓRIOS ---
elif menu == "📋 Relatórios":
    st.header("Relatórios de Abastecimento e Produtividade")
    df = get_data("abastecimentos")

    if not df.empty:
        df_v = get_data("veiculos")
        if not df_v.empty:
            df = df.merge(df_v[['prefixo', 'classe', 'placa']], on='prefixo', how='left')
        
        # Garante que as colunas novas existem no dataframe para evitar erros
        if 'origem' not in df.columns: df['origem'] = "Posto"
        if 'obra' not in df.columns: df['obra'] = ""
        if 'observacao' not in df.columns: df['observacao'] = ""

        df['data_hora_ordenacao'] = pd.to_datetime(df['data'])
        df = df.sort_values(by=['prefixo', 'data_hora_ordenacao', 'horimetro'])
        
        df['horimetro_anterior'] = df.groupby('prefixo')['horimetro'].shift(1)
        df['horas_trabalhadas'] = df['horimetro'] - df['horimetro_anterior']
        
        df['consumo_l_h'] = df.apply(
            lambda row: round(row['quantidade'] / row['horas_trabalhadas'], 2) 
            if pd.notna(row['horas_trabalhadas']) and row['horas_trabalhadas'] > 0 else None, 
            axis=1
        )

        # Filtros
        col_f1, col_f2 = st.columns(2)
        lista_origem = ["Todas"] + df['origem'].dropna().unique().tolist()
        filtro_origem = col_f1.selectbox("Filtrar por Origem", lista_origem)
        
        if filtro_origem != "Todas":
            df = df[df['origem'] == filtro_origem]

        colunas_finais = ['data', 'origem', 'numero_ficha', 'fornecedor', 'prefixo', 'classe', 'quantidade', 'valor_unitario', 'total', 'horimetro', 'horas_trabalhadas', 'consumo_l_h', 'obra', 'observacao']
        colunas_finais = [col for col in colunas_finais if col in df.columns]
        df_export = df[colunas_finais]

        st.dataframe(df_export, use_container_width=True)
        
        # Download
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_export.to_excel(writer, index=False, sheet_name='Abastecimentos')
        
        st.download_button("📥 Baixar Relatório em Excel", data=output.getvalue(), file_name="Relatorio.xlsx", mime="application/vnd.ms-excel")
    else:
        st.info("Nenhum dado encontrado.")
