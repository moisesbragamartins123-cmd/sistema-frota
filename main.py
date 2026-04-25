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

# CSS para melhorar o visual e incluir as cores do Saldo do Tanque
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    [data-testid="stMetricValue"] { font-size: 1.8rem !important; color: #003366; font-weight: 700; }
    .stButton>button { border-radius: 8px; font-weight: bold; }
    .saldo-ok { color: #3B6D11; font-weight: bold; background-color: #EAF3DE; padding: 12px; border-radius: 8px; border: 1px solid #C0DD97; font-size: 1.1rem; }
    .saldo-low { color: #854F0B; font-weight: bold; background-color: #FAEEDA; padding: 12px; border-radius: 8px; border: 1px solid #FAC775; font-size: 1.1rem; }
    </style>
""", unsafe_allow_html=True)

# Conexão Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- SISTEMA DE LOGIN (COM LOGO RESTAURADA) ---
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

# --- NAVEGAÇÃO E MENU (COM LOGO NA BARRA RESTAURADA) ---
def logout():
    st.session_state.logged_in = False
    st.rerun()

if os.path.exists("logo.png"):
    col_s1, col_s2, col_s3 = st.sidebar.columns([1, 2, 1])
    with col_s2:
        st.image("logo.png", use_container_width=True)
        
st.sidebar.markdown("<h3 style='text-align: center; margin-top:0;'>Copa Engenharia</h3>", unsafe_allow_html=True)
st.sidebar.divider()

menu = st.sidebar.radio("Menu Principal", ["🏠 Início", "📝 Lançar Abastec.", "🛢️ Tanque Interno", "🚜 Frota", "🏪 Fornecedores", "📋 Relatórios"])

st.sidebar.divider()
col_side1, col_side2, col_side3 = st.sidebar.columns([1,2,1])
with col_side2:
    if st.button("🚪 Sair", key="side_logout", use_container_width=True):
        logout()

# FUNÇÕES DO BANCO DE DADOS
def get_data(table):
    try:
        res = supabase.table(table).select("*").execute()
        return pd.DataFrame(res.data)
    except Exception as e:
        st.error(f"⚠️ Erro ao ler a tabela '{table}': {e}")
        return pd.DataFrame()

def calcular_saldo_tanque():
    df_ent = get_data("entradas_tanque")
    df_sai = get_data("abastecimentos")
    
    t_ent = pd.to_numeric(df_ent['quantidade']).sum() if not df_ent.empty and 'quantidade' in df_ent.columns else 0
    t_sai = 0
    if not df_sai.empty and 'origem' in df_sai.columns and 'quantidade' in df_sai.columns:
        df_sai_tanque = df_sai[df_sai['origem'] == 'Tanque da Obra']
        t_sai = pd.to_numeric(df_sai_tanque['quantidade']).sum()
        
    return t_ent - t_sai, t_ent, t_sai

# --- PÁGINA: INÍCIO ---
if menu == "🏠 Início":
    st.title("Resumo da Operação")
    df = get_data("abastecimentos")
    
    saldo_atual, t_ent, t_sai = calcular_saldo_tanque()
    
    if saldo_atual < 500:
        st.markdown(f"<div class='saldo-low'>⚠️ Atenção: Saldo atual do tanque da obra é de apenas {saldo_atual:,.1f} Litros!</div><br>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='saldo-ok'>✅ Saldo atual do tanque da obra: {saldo_atual:,.1f} Litros.</div><br>", unsafe_allow_html=True)

    if not df.empty:
        df['total'] = pd.to_numeric(df['total'])
        df['quantidade'] = pd.to_numeric(df['quantidade'])
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Investimento Total", f"R$ {df['total'].sum():,.2f}")
        m2.metric("Volume Consumido (L)", f"{df['quantidade'].sum():,.1f} L")
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
        st.info("Nenhum dado encontrado. Comece a lançar abastecimentos!")

# --- PÁGINA: LANÇAR ---
elif menu == "📝 Lançar Abastec.":
    st.header("Lançamento de Abastecimento (Saída)")
    df_v = get_data("veiculos")
    df_f = get_data("fornecedores")
    df_abast = get_data("abastecimentos") 
    
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
        
        st.info(f"⛽ **Combustível:** {comb_v} | 🏷️ **Placa:** {placa_v} | ⏱️ **Maior Horímetro Registrado:** {maior_horimetro}")
        
        origem_comb = st.radio("Origem do Combustível:", ["Posto Externo", "Tanque da Obra"], horizontal=True)

        with st.form("form_abast", clear_on_submit=False):
            c0, c1, c2 = st.columns([1, 2, 2])
            numero_ficha = c0.text_input("Nº Ficha / Cupom")
            
            if origem_comb == "Posto Externo":
                posto = c1.selectbox("Posto Fornecedor", df_f['nome'].tolist() if not df_f.empty else ["Cadastre um fornecedor"])
            else:
                posto = c1.text_input("Fornecedor", value="Estoque Interno do Tanque", disabled=True)

            data = c2.date_input("Data do Abastecimento")
            
            c3, c4, c5 = st.columns(3)
            horimetro = c3.number_input("Horímetro / KM", min_value=0.0, value=maior_horimetro, step=0.1)
            litros = c4.number_input("Litros", min_value=0.0)
            preco = c5.number_input("Preço Unitário (R$)", min_value=0.0)

            c6, c7 = st.columns(2)
            obra = c6.text_input("Obra / Trecho (Opcional)")
            observacao = c7.text_input("Observações (Opcional)")
            
            if st.form_submit_button("Confirmar Lançamento"):
                saldo, _, _ = calcular_saldo_tanque()

                if comb_v == 'Não definido' or pd.isna(comb_v):
                    st.error("Erro: Veículo sem combustível padrão definido na Frota.")
                elif litros <= 0:
                    st.error("Erro: Litros devem ser maiores que zero.")
                elif origem_comb == "Tanque da Obra" and litros > saldo:
                    st.error(f"⚠️ ERRO: Saldo insuficiente no tanque da obra! Você tentou retirar {litros}L, mas só há {saldo}L disponíveis.")
                else:
                    try:
                        supabase.table("abastecimentos").insert({
                            "data": str(data), "numero_ficha": numero_ficha, "origem": origem_comb, "prefixo": veic_sel, 
                            "quantidade": litros, "valor_unitario": preco, "total": litros*preco, 
                            "fornecedor": posto, "tipo_combustivel": comb_v, "horimetro": horimetro,
                            "obra": obra, "observacao": observacao
                        }).execute()
                        st.success("Abastecimento registrado com sucesso!")
                        time.sleep(1.5)
                        st.rerun() 
                    except Exception as e:
                        st.error(f"Erro ao salvar abastecimento: {e}")
    else:
        st.warning("⚠️ Cadastre primeiro sua Frota antes de lançar!")

# --- PÁGINA: TANQUE INTERNO ---
elif menu == "🛢️ Tanque Interno":
    st.header("Gestão do Tanque da Obra")
    saldo_atual, t_ent, t_sai = calcular_saldo_tanque()
    
    col_t1, col_t2, col_t3 = st.columns(3)
    col_t1.metric("Total Comprado (Entradas)", f"{t_ent:,.1f} L")
    col_t2.metric("Total Abastecido (Saídas)", f"{t_sai:,.1f} L")
    col_t3.metric("SALDO DISPONÍVEL", f"{saldo_atual:,.1f} L")
    
    st.divider()
    st.subheader("Registrar Chegada de Combustível (Encher o Tanque)")
    df_f = get_data("fornecedores")
    
    with st.form("form_entrada", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        data_ent = c1.date_input("Data do Recebimento")
        ficha_ent = c2.text_input("Nº da Nota Fiscal / Ficha")
        forn_ent = c3.selectbox("Distribuidora / Fornecedor", df_f['nome'].tolist() if not df_f.empty else ["Cadastre um fornecedor"])
        
        c4, c5, c6 = st.columns(3)
        comb_ent = c4.selectbox("Combustível Recebido", ["Diesel S10", "Diesel S500", "Gasolina", "Arla 32"])
        qtd_ent = c5.number_input("Quantidade Recebida (Litros)", min_value=0.0)
        preco_ent = c6.number_input("Preço Unitário na Nota (R$/L)", min_value=0.0)
        
        obs_ent = st.text_input("Observações Gerais")
        
        if st.form_submit_button("Confirmar Entrada no Tanque"):
            if qtd_ent > 0:
                supabase.table("entradas_tanque").insert({
                    "data": str(data_ent), "numero_ficha": ficha_ent, "fornecedor": forn_ent,
                    "combustivel": comb_ent, "quantidade": qtd_ent, "valor_unitario": preco_ent,
                    "total": qtd_ent * preco_ent, "observacao": obs_ent
                }).execute()
                st.success("Entrada registrada! O saldo do tanque foi atualizado.")
                time.sleep(1.5)
                st.rerun()

# --- PÁGINA: FROTA ---
elif menu == "🚜 Frota":
    st.header("Gestão de Frota e Categorias")
    tab_frota, tab_classes = st.tabs(["🚜 Veículos", "📂 Gerenciar Classes"])

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

# --- PÁGINA: FORNECEDORES (FICHA COMPLETA RESTAURADA) ---
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
            
            cb1, cb2 = st.columns(2)
            banco = cb1.text_input("Nome do Banco")
            tipo_conta = cb2.selectbox("Tipo de Conta", ["Corrente", "Poupança", "Outra"])
            
            if st.form_submit_button("Cadastrar Fornecedor"):
                try:
                    supabase.table("fornecedores").insert({
                        "nome": nome_fantasia, "razao_social": razao_social, "cnpj": cnpj, 
                        "agencia": agencia, "conta": conta, "pix": pix,
                        "banco": banco, "tipo_conta": tipo_conta
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
                    st.write(f"**Banco:** {r.get('banco', '---')} | **Tipo:** {r.get('tipo_conta', '---')}")
                    st.write(f"**Agência:** {r.get('agencia', '---')} | **Conta:** {r.get('conta', '---')} | **PIX:** {r.get('pix', '---')}")
                    if st.button("Remover Fornecedor", key=f"f_{r['id']}"):
                        try:
                            supabase.table("fornecedores").delete().eq("id", r['id']).execute()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao excluir: {e}")

# --- PÁGINA: RELATÓRIOS (COM CÁLCULO INTELIGENTE E COLUNAS NOVAS) ---
elif menu == "📋 Relatórios":
    st.header("Relatórios de Abastecimento e Produtividade")
    df = get_data("abastecimentos")

    if not df.empty:
        df_v = get_data("veiculos")
        if not df_v.empty:
            df = df.merge(df_v[['prefixo', 'classe', 'placa']], on='prefixo', how='left')
        else:
            df['classe'] = "N/A"
            df['placa'] = "N/A"

        # Garante as colunas para não dar erro se o banco estiver se atualizando
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

        df['horas_trabalhadas'] = df['horas_trabalhadas'].apply(lambda x: round(x, 1) if pd.notna(x) else None)

        col_f1, col_f2 = st.columns(2)
        lista_fornecedores = ["Todos"] + sorted(df['fornecedor'].dropna().unique().tolist())
        filtro_fornecedor = col_f1.selectbox("Filtrar por Fornecedor", lista_fornecedores)
        
        lista_origem = ["Todas"] + df['origem'].dropna().unique().tolist()
        filtro_origem = col_f2.selectbox("Filtrar por Origem", lista_origem)
        
        if filtro_fornecedor != "Todos":
            df = df[df['fornecedor'] == filtro_fornecedor]
        if filtro_origem != "Todas":
            df = df[df['origem'] == filtro_origem]

        colunas_ordenadas = ['data', 'origem', 'numero_ficha', 'fornecedor', 'prefixo', 'classe', 'placa', 'tipo_combustivel', 'quantidade', 'valor_unitario', 'total', 'horimetro', 'horas_trabalhadas', 'consumo_l_h', 'obra', 'observacao']
        colunas_finais = [col for col in colunas_ordenadas if col in df.columns]
        df_export = df[colunas_finais]
        
        nomes_bonitos = {
            'data': 'Data', 'origem': 'Origem', 'numero_ficha': 'Nº Ficha', 'fornecedor': 'Posto/Fornecedor', 
            'prefixo': 'Prefixo', 'classe': 'Classe', 'placa': 'Placa',
            'tipo_combustivel': 'Combustível', 'quantidade': 'Litros', 
            'valor_unitario': 'R$/L', 'total': 'Total (R$)', 
            'horimetro': 'Horímetro Atual', 'horas_trabalhadas': 'Horas Trab.', 'consumo_l_h': 'Consumo (L/h)',
            'obra': 'Obra/Trecho', 'observacao': 'Observação'
        }
        df_export = df_export.rename(columns=nomes_bonitos)

        st.dataframe(df_export, use_container_width=True)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_export.to_excel(writer, index=False, sheet_name='Produtividade')
            workbook = writer.book
            worksheet = writer.sheets['Produtividade']
            
            for i, col in enumerate(df_export.columns):
                try:
                    tamanho_titulo = len(str(col))
                    tamanho_dados = df_export[col].astype(str).str.len().max()
                    tamanho_final = tamanho_titulo if pd.isna(tamanho_dados) else max(tamanho_titulo, int(tamanho_dados))
                    worksheet.set_column(i, i, tamanho_final + 2)
                except:
                    worksheet.set_column(i, i, 15)
        
        nome_arquivo = f"Relatorio_Frota_Copa_{datetime.now().strftime('%d_%m_%Y')}.xlsx"
        st.download_button(
            label=f"📥 Baixar Relatório Completo em Excel",
            data=output.getvalue(),
            file_name=nome_arquivo,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("Nenhum dado de abastecimento encontrado.")
