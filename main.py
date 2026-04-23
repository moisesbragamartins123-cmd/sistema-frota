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

# CSS para melhorar o visual
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
                    st.error("Dados de acesso incorretos")
    st.stop()

# --- NAVEGAÇÃO E MENU ---
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

# FUNÇÃO SEGURA PARA LER O BANCO DE DADOS
def get_data(table):
    try:
        res = supabase.table(table).select("*").execute()
        return pd.DataFrame(res.data)
    except Exception as e:
        st.error(f"⚠️ Erro ao ler a tabela '{table}': {e}")
        return pd.DataFrame()

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
        
        st.write("<br>", unsafe_allow_html=True)
        with st.expander("📈 Visualizar Gráficos de Tendência"):
            df['data'] = pd.to_datetime(df['data'])
            df['Mes'] = df['data'].dt.strftime('%m/%Y')
            f_gasto = px.bar(df.groupby('Mes')['total'].sum().reset_index(), x='Mes', y='total', title="Gastos Mensais (R$)")
            st.plotly_chart(f_gasto, use_container_width=True)
    else:
        st.info("Nenhum dado encontrado. Comece a lançar abastecimentos para ver os gráficos!")

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
            
            if st.form_submit_button("Confirmar Lançamento"):
                if comb_v == 'Não definido' or pd.isna(comb_v):
                    st.error("Erro: Veículo sem combustível padrão definido na Frota.")
                else:
                    try:
                        supabase.table("abastecimentos").insert({
                            "data": str(data), "prefixo": veic_sel, "quantidade": litros, "valor_unitario": preco,
                            "total": litros*preco, "fornecedor": posto, "tipo_combustivel": comb_v,
                            "horimetro": horimetro
                        }).execute()
                        st.success("Abastecimento registrado com sucesso!")
                    except Exception as e:
                        st.error(f"Erro ao salvar abastecimento: {e}")
    else:
        st.warning("⚠️ Cadastre primeiro sua Frota e Fornecedores antes de lançar!")

# --- PÁGINA: FROTA ---
elif menu == "🚜 Frota":
    st.header("Gestão de Frota e Categorias")
    tab_frota, tab_classes = st.tabs(["🚜 Veículos", "📂 Gerenciar Classes"])

    # ABA: CLASSES
    with tab_classes:
        st.subheader("Criar Novas Classes (Categorias)")
        with st.form("form_classe", clear_on_submit=True):
            nova_classe = st.text_input("Nome da Classe (Ex: Caçambas, Terceirizados, Leves)")
            if st.form_submit_button("Criar Classe"):
                if nova_classe:
                    try:
                        supabase.table("classes_frota").insert({"nome": nova_classe}).execute()
                        st.success(f"Classe '{nova_classe}' criada com sucesso!")
                        time.sleep(1.5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao criar classe: {e}")

        df_classes = get_data("classes_frota")
        if not df_classes.empty:
            st.write("**Classes Existentes:**")
            for _, c in df_classes.iterrows():
                col_c1, col_c2 = st.columns([3, 1])
                col_c1.write(f"• {c['nome']}")
                if col_c2.button("Excluir", key=f"del_cl_{c['id']}"):
                    try:
                        supabase.table("classes_frota").delete().eq("id", c['id']).execute()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao excluir: {e}")

    # ABA: VEÍCULOS
    with tab_frota:
        st.subheader("Cadastrar Veículo na Classe")
        df_classes = get_data("classes_frota")
        
        if df_classes.empty:
            st.warning("⚠️ Crie uma Classe na aba 'Gerenciar Classes' primeiro!")
        else:
            with st.form("form_veic", clear_on_submit=True):
                c1, c2 = st.columns(2)
                prefixo = c1.text_input("Prefixo (ID) - Ex: CAM-01")
                placa = c2.text_input("Placa")
                
                c3, c4 = st.columns(2)
                classe_sel = c3.selectbox("Selecione a Classe", df_classes['nome'].tolist())
                combustivel = c4.selectbox("Combustível Padrão", ["Diesel S10", "Diesel S500", "Gasolina", "Arla 32"])
                
                motorista = st.text_input("Motorista/Operador Responsável")
                
                if st.form_submit_button("Salvar Veículo"):
                    try:
                        supabase.table("veiculos").insert({
                            "prefixo": prefixo, "placa": placa, "classe": classe_sel, 
                            "motorista": motorista, "tipo_combustivel_padrao": combustivel
                        }).execute()
                        st.success(f"Veículo '{prefixo}' salvo na classe '{classe_sel}' com sucesso!")
                        time.sleep(1.5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar veículo: {e}")

        st.divider()
        st.write("**Frota Cadastrada:**")
        df_v = get_data("veiculos")
        if not df_v.empty:
            for i, r in df_v.iterrows():
                with st.expander(f"🚜 {r['prefixo']} - Categoria: {r.get('classe', 'Sem classe')} - Placa: {r.get('placa', 'S/P')}"):
                    st.write(f"**Combustível:** {r.get('tipo_combustivel_padrao', '---')} | **Motorista:** {r['motorista']}")
                    if st.button("🗑️ Excluir", key=f"v_{r['id']}"):
                        try:
                            supabase.table("veiculos").delete().eq("id", r['id']).execute()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao excluir: {e}")

# --- PÁGINA: FORNECEDORES ---
elif menu == "🏪 Fornecedores":
    st.header("Fornecedores e Postos")
    t1, t2 = st.tabs(["Lista de Parceiros", "Novo Fornecedor"])
    
    with t2:
        with st.form("new_f", clear_on_submit=True):
            nome_fantasia = st.text_input("Nome Fantasia (Como é conhecido)", placeholder="Ex: Posto do Trevo")
            razao_social = st.text_input("Razão Social (Nome na Nota)", placeholder="Ex: Auto Posto Silva Ltda")
            
            c1, c2, c3, c4 = st.columns(4)
            cnpj = c1.text_input("CNPJ")
            agencia = c2.text_input("Agência")
            conta = c3.text_input("Conta")
            pix = c4.text_input("Chave PIX")
            
            if st.form_submit_button("Cadastrar Fornecedor"):
                try:
                    supabase.table("fornecedores").insert({
                        "nome": nome_fantasia, "razao_social": razao_social, "cnpj": cnpj, 
                        "agencia": agencia, "conta": conta, "pix": pix
                    }).execute()
                    st.success(f"Fornecedor '{nome_fantasia}' cadastrado com sucesso!")
                    time.sleep(1.5)
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar fornecedor: {e}")

    with t1:
        df_f = get_data("fornecedores")
        if not df_f.empty:
            for i, r in df_f.iterrows():
                with st.expander(f"🏪 {r['nome'].upper()}"):
                    st.write(f"**Razão Social:** {r.get('razao_social', 'N/A')} | **CNPJ:** {r.get('cnpj', '---')}")
                    st.write(f"**Agência:** {r.get('agencia', '---')} | **Conta:** {r.get('conta', '---')} | **PIX:** {r.get('pix', '---')}")
                    if st.button("Remover", key=f"f_{r['id']}"):
                        try:
                            supabase.table("fornecedores").delete().eq("id", r['id']).execute()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao excluir: {e}")

# --- PÁGINA: RELATÓRIOS (COM EXCEL SEGURO) ---
elif menu == "📋 Relatórios":
    st.header("Relatórios de Abastecimento")
    df = get_data("abastecimentos")

    if not df.empty:
        # Puxa informações extras da tabela de veículos
        df_v = get_data("veiculos")
        if not df_v.empty:
            df = df.merge(df_v[['prefixo', 'classe', 'placa']], on='prefixo', how='left')
        else:
            df['classe'] = "N/A"
            df['placa'] = "N/A"

        # Organizando as colunas para o Excel
        colunas_ordenadas = ['id', 'data', 'fornecedor', 'prefixo', 'classe', 'placa', 'tipo_combustivel', 'quantidade', 'valor_unitario', 'total', 'horimetro']
        colunas_finais = [col for col in colunas_ordenadas if col in df.columns]
        df_export = df[colunas_finais]
        
        # Renomeia para português
        nomes_bonitos = {
            'id': 'ID', 'data': 'Data', 'fornecedor': 'Posto/Fornecedor', 
            'prefixo': 'Prefixo (Máquina)', 'classe': 'Classe', 'placa': 'Placa',
            'tipo_combustivel': 'Combustível', 'quantidade': 'Litros', 
            'valor_unitario': 'Preço Unit. (R$)', 'total': 'Total (R$)', 'horimetro': 'Horímetro'
        }
        df_export = df_export.rename(columns=nomes_bonitos)

        # Mostra na tela
        st.dataframe(df_export, use_container_width=True)

        # Lógica SEGURA para gerar Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_export.to_excel(writer, index=False, sheet_name='Abastecimentos')
            workbook = writer.book
            worksheet = writer.sheets['Abastecimentos']
            
            # Formatação de tamanho de coluna segura
            for i, col in enumerate(df_export.columns):
                try:
                    tamanho_titulo = len(str(col))
                    tamanho_dados = df_export[col].astype(str).str.len().max()
                    tamanho_final = tamanho_titulo if pd.isna(tamanho_dados) else max(tamanho_titulo, int(tamanho_dados))
                    worksheet.set_column(i, i, tamanho_final + 2)
                except:
                    worksheet.set_column(i, i, 15) # Largura padrão em caso de erro
        
        st.download_button(
            label="📥 Baixar Relatório Completo em Excel",
            data=output.getvalue(),
            file_name=f"Relatorio_Frota_Copa_{datetime.now().strftime('%d_%m_%Y')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("Nenhum dado de abastecimento encontrado para exportar.")
