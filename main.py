import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime, date, timedelta
import plotly.express as px
import plotly.graph_objects as go
import os
import io
import hashlib
import xlsxwriter
from fpdf import FPDF

# ═══════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO DA PÁGINA
# ═══════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="PavControl — COPA Engenharia",
    page_icon="🛣️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═══════════════════════════════════════════════════════════════════
# CSS GLOBAL
# ═══════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');
html,body,[class*="css"]{font-family:'DM Sans',sans-serif;}

/* ── Sidebar ── */
[data-testid="stSidebar"]{background:#0D1B2A;}
[data-testid="stSidebar"] *{color:#A8C0D6 !important;}
[data-testid="stSidebar"] h3{color:#3DD6A3 !important;}
[data-testid="stSidebarNav"]{display:none;}

/* ── Main background ── */
.main{background:#F0F4F8;}

/* ── Labels dos campos ── */
.stTextInput>label,.stSelectbox>label,.stNumberInput>label,
.stDateInput>label,.stTextArea>label,.stTimeInput>label{
    font-size:11px !important;color:#475569 !important;
    font-weight:700 !important;text-transform:uppercase;
    letter-spacing:.06em;margin-bottom:4px !important;}

/* ── Inputs e selects ── */
div[data-baseweb="input"],div[data-baseweb="select"]{
    border-radius:6px !important;border:1.5px solid #CBD5E1 !important;
    background:#FFFFFF !important;}
div[data-baseweb="input"]:focus-within,div[data-baseweb="select"]:focus-within{
    border-color:#2563EB !important;
    box-shadow:0 0 0 3px rgba(37,99,235,.12) !important;}

/* ── Botão primário ── */
div.stButton>button:first-child{
    background:#1D4ED8 !important;color:#fff !important;
    border:none !important;border-radius:7px !important;
    font-weight:700 !important;font-size:13px !important;
    padding:.6rem 1.4rem !important;
    box-shadow:0 2px 8px rgba(29,78,216,.30) !important;
    transition:all .18s ease !important;text-transform:uppercase !important;letter-spacing:.04em;}
div.stButton>button:first-child:hover{
    background:#1e40af !important;transform:translateY(-1px) !important;
    box-shadow:0 6px 16px rgba(29,78,216,.35) !important;}

/* ── Forms ── */
div[data-testid="stForm"]{
    border:none;border-radius:14px;padding:1.8rem;background:#fff;
    box-shadow:0 4px 24px rgba(0,0,0,.06);}

/* ── Banners ── */
.bk-ok {background:#DCFCE7;color:#166534;border:1px solid #86EFAC;border-radius:8px;padding:10px 14px;font-weight:600;font-size:12px;margin-bottom:.8rem;}
.bk-lo {background:#FEF9C3;color:#854D0E;border:1px solid #FDE047;border-radius:8px;padding:10px 14px;font-weight:600;font-size:12px;margin-bottom:.8rem;}
.bk-er {background:#FEE2E2;color:#991B1B;border:1px solid #FCA5A5;border-radius:8px;padding:10px 14px;font-weight:600;font-size:12px;margin-bottom:.8rem;}
.bk-in {background:#DBEAFE;color:#1E40AF;border:1px solid #93C5FD;border-radius:8px;padding:10px 14px;font-weight:600;font-size:12px;margin-bottom:.8rem;}

/* ── KPI cards ── */
.kpi{background:#fff;border-radius:12px;padding:1.2rem 1.4rem;
     box-shadow:0 2px 12px rgba(0,0,0,.05);border-left:4px solid #2563EB;}
.kpi .val{font-size:22px;font-weight:700;color:#0F172A;margin:4px 0 0;}
.kpi .lbl{font-size:10px;font-weight:700;text-transform:uppercase;
          letter-spacing:.06em;color:#64748B;}
.kpi .ico{font-size:18px;}

/* ── Tank gauge ── */
.tank-card{background:#fff;border-radius:12px;padding:1rem 1.2rem;
           box-shadow:0 2px 12px rgba(0,0,0,.05);margin-bottom:.5rem;}
.tank-name{font-size:13px;font-weight:700;color:#0F172A;}
.tank-val {font-size:20px;font-weight:700;font-family:'DM Mono',monospace;}
.tank-ok  {color:#16A34A;}
.tank-low {color:#D97706;}
.tank-crit{color:#DC2626;}

/* ── Tabelas ── */
.dataframe thead tr th{background:#1D4ED8 !important;color:#fff !important;font-size:11px !important;}
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# SUPABASE
# ═══════════════════════════════════════════════════════════════════
@st.cache_resource
def get_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = get_supabase()


# ═══════════════════════════════════════════════════════════════════
# CRUD — com cache de 20 segundos por tabela
# ═══════════════════════════════════════════════════════════════════
@st.cache_data(ttl=20)
def get_data(table: str) -> pd.DataFrame:
    try:
        res = supabase.table(table).select("*").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception as e:
        st.warning(f"⚠️ Erro ao buscar {table}: {e}")
        return pd.DataFrame()


def _invalidate(table: str | None = None):
    """Limpa o cache após qualquer escrita."""
    get_data.clear()


def insert_data(table: str, data: dict) -> bool:
    try:
        supabase.table(table).insert(data).execute()
        _invalidate()
        return True
    except Exception as e:
        st.error(f"❌ Erro ao salvar em {table}: {e}")
        return False


def update_data(table: str, row_id, data: dict) -> bool:
    try:
        supabase.table(table).update(data).eq("id", row_id).execute()
        _invalidate()
        return True
    except Exception as e:
        st.error(f"❌ Erro ao atualizar {table}: {e}")
        return False


def delete_data(table: str, row_id) -> bool:
    try:
        supabase.table(table).delete().eq("id", row_id).execute()
        _invalidate()
        return True
    except Exception as e:
        st.error(f"❌ Erro ao excluir de {table}: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════
# FUNÇÕES AUXILIARES
# ═══════════════════════════════════════════════════════════════════
def hash_senha(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def dia_semana_pt(d) -> str:
    dias = ["SEG","TER","QUA","QUI","SEX","SÁB","DOM"]
    try:
        if isinstance(d, str):
            d = datetime.strptime(d[:10], "%Y-%m-%d")
        return dias[d.weekday()]
    except Exception:
        return ""


def lista_obras(incluir_todas: bool = False) -> list:
    df_o = get_data("obras")
    if df_o.empty:
        return ["GERAL"] if incluir_todas else []
    if "status" in df_o.columns:
        ativas = df_o[df_o["status"] != "Encerrada"]
    else:
        ativas = df_o
    nomes = ativas["nome"].dropna().tolist()
    if incluir_todas:
        return ["TODAS"] + nomes
    return nomes


def to_float(v, default=0.0) -> float:
    try:
        return float(v or default)
    except (ValueError, TypeError):
        return default


# ═══════════════════════════════════════════════════════════════════
# SALDO DE TANQUES — calculado UMA vez por ciclo de render
# ═══════════════════════════════════════════════════════════════════
def calcular_todos_saldos() -> dict[str, float]:
    """
    Retorna {nome_tanque: saldo_litros} para todos os tanques.
    Busca cada tabela uma única vez e filtra em memória.
    """
    df_tanq  = get_data("tanques")
    df_ent   = get_data("entradas_tanque")
    df_sai   = get_data("abastecimentos")
    df_transf= get_data("transferencias_tanque")

    # Filtra apenas registros ATIVOS
    if not df_sai.empty and "status" in df_sai.columns:
        df_sai = df_sai[df_sai["status"] == "ATIVO"]
    if not df_transf.empty and "status" in df_transf.columns:
        df_transf = df_transf[df_transf["status"] == "ATIVO"]

    saldos: dict[str, float] = {}
    if df_tanq.empty:
        return saldos

    for _, row in df_tanq.iterrows():
        nome = row.get("nome", "")
        if not nome:
            continue

        # Entradas
        ent = 0.0
        if not df_ent.empty and "nome_tanque" in df_ent.columns:
            ent = pd.to_numeric(
                df_ent[df_ent["nome_tanque"] == nome]["quantidade"], errors="coerce"
            ).sum()

        # Saídas diretas (abastecimento de veículo a partir do tanque)
        sai_dir = 0.0
        if (not df_sai.empty
                and "origem" in df_sai.columns
                and "nome_tanque" in df_sai.columns):
            mask = (df_sai["origem"] == "Tanque Interno") & (df_sai["nome_tanque"] == nome)
            sai_dir = pd.to_numeric(df_sai.loc[mask, "quantidade"], errors="coerce").sum()

        # Saídas via transferência para caminhão-tanque
        sai_transf = 0.0
        if not df_transf.empty and "tanque_origem" in df_transf.columns:
            mask_t = df_transf["tanque_origem"] == nome
            sai_transf = pd.to_numeric(df_transf.loc[mask_t, "quantidade"], errors="coerce").sum()

        saldos[nome] = float(ent) - float(sai_dir) - float(sai_transf)

    return saldos


def saldo_tanque(nome: str, saldos: dict) -> float:
    return saldos.get(nome, 0.0)


# ═══════════════════════════════════════════════════════════════════
# EXPORTAÇÃO — EXCEL PADRÃO
# ═══════════════════════════════════════════════════════════════════
def gerar_excel_limpo(df: pd.DataFrame, nome_aba: str = "Relatório") -> bytes:
    df = df.fillna("").copy()
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as w:
        df.to_excel(w, index=False, sheet_name=nome_aba[:31])
        ws = w.sheets[nome_aba[:31]]
        for i, col in enumerate(df.columns):
            try:
                sz = max(len(str(col)), df[col].astype(str).str.len().max())
                ws.set_column(i, i, min(int(sz) + 2, 55))
            except Exception:
                ws.set_column(i, i, 16)
    return buf.getvalue()


def gerar_excel_abastecimentos(df: pd.DataFrame, titulo: str, periodo: str) -> bytes:
    """Excel formatado para relatório de abastecimentos por fornecedor."""
    df = df.fillna("").copy()
    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf)
    ws = wb.add_worksheet("Abastecimentos")

    # Formatos
    fmt_title = wb.add_format({"bold": True, "font_size": 12, "align": "center",
                                "bg_color": "#1D4ED8", "font_color": "#FFFFFF",
                                "border": 1, "text_wrap": True})
    fmt_header = wb.add_format({"bold": True, "font_size": 9, "align": "center",
                                 "bg_color": "#DBEAFE", "border": 1, "text_wrap": True})
    fmt_data   = wb.add_format({"font_size": 9, "border": 1, "align": "center"})
    fmt_num    = wb.add_format({"font_size": 9, "border": 1, "align": "right",
                                 "num_format": "#,##0.00"})
    fmt_money  = wb.add_format({"font_size": 9, "border": 1, "align": "right",
                                 "num_format": 'R$ #,##0.00'})
    fmt_total  = wb.add_format({"bold": True, "font_size": 9, "border": 1,
                                 "align": "right", "bg_color": "#F1F5F9",
                                 "num_format": 'R$ #,##0.00'})

    # Título
    ws.merge_range(0, 0, 0, 11, titulo.upper(), fmt_title)
    ws.write(1, 0, f"Período: {periodo}", wb.add_format({"italic": True, "font_size": 9}))

    # Cabeçalho
    headers = ["DATA", "DIA", "FICHA", "PREFIXO", "PLACA", "MOTORISTA",
               "FORNECEDOR", "COMBUSTÍVEL", "QTDE (L)", "VL UNIT (R$)", "TOTAL (R$)", "OBRA"]
    widths  = [12, 6, 10, 10, 10, 22, 22, 14, 10, 12, 12, 20]
    ws.set_row(2, 28)
    for i, (h, w) in enumerate(zip(headers, widths)):
        ws.write(2, i, h, fmt_header)
        ws.set_column(i, i, w)

    t_litros = 0.0
    t_total  = 0.0
    row = 3
    for _, r in df.iterrows():
        qtd  = to_float(r.get("quantidade"))
        vunt = to_float(r.get("valor_unitario"))
        tot  = to_float(r.get("total"))
        t_litros += qtd
        t_total  += tot
        ws.write(row, 0,  str(r.get("data",""))[:10], fmt_data)
        ws.write(row, 1,  dia_semana_pt(str(r.get("data",""))[:10]), fmt_data)
        ws.write(row, 2,  str(r.get("numero_ficha","")), fmt_data)
        ws.write(row, 3,  str(r.get("prefixo","")), fmt_data)
        ws.write(row, 4,  str(r.get("placa","")), fmt_data)
        ws.write(row, 5,  str(r.get("motorista","")), fmt_data)
        ws.write(row, 6,  str(r.get("fornecedor","")), fmt_data)
        ws.write(row, 7,  str(r.get("tipo_combustivel","")), fmt_data)
        ws.write(row, 8,  qtd,  fmt_num)
        ws.write(row, 9,  vunt, fmt_money)
        ws.write(row, 10, tot,  fmt_money)
        ws.write(row, 11, str(r.get("obra","")), fmt_data)
        row += 1

    # Linha de totais
    ws.merge_range(row, 0, row, 7, "TOTAIS GERAIS", fmt_total)
    ws.write(row, 8,  t_litros, wb.add_format({"bold": True, "font_size": 9, "border": 1,
                                                "align": "right", "bg_color": "#F1F5F9",
                                                "num_format": "#,##0.00"}))
    ws.write(row, 9,  "", fmt_total)
    ws.write(row, 10, t_total, fmt_total)
    ws.write(row, 11, "", fmt_total)

    wb.close()
    buf.seek(0)
    return buf.getvalue()


def gerar_excel_tanque_movimentos(df_ent, df_sai, df_transf, nome_tanque, periodo) -> bytes:
    """Excel com movimentação completa de um tanque."""
    buf = io.BytesIO()
    wb  = xlsxwriter.Workbook(buf)
    ws  = wb.add_worksheet("Movimentação")

    fmt_title  = wb.add_format({"bold": True, "font_size": 11, "align": "center",
                                  "bg_color": "#0D1B2A", "font_color": "#3DD6A3", "border": 1})
    fmt_header = wb.add_format({"bold": True, "font_size": 8, "align": "center",
                                  "bg_color": "#DBEAFE", "border": 1, "text_wrap": True})
    fmt_data   = wb.add_format({"font_size": 8, "border": 1, "align": "center"})
    fmt_ent    = wb.add_format({"font_size": 8, "border": 1, "align": "right",
                                  "num_format": "#,##0.0", "font_color": "#166534"})
    fmt_sai    = wb.add_format({"font_size": 8, "border": 1, "align": "right",
                                  "num_format": "#,##0.0", "font_color": "#991B1B"})
    fmt_saldo  = wb.add_format({"bold": True, "font_size": 8, "border": 1,
                                  "align": "right", "num_format": "#,##0.0"})
    fmt_money  = wb.add_format({"font_size": 8, "border": 1, "align": "right",
                                  "num_format": 'R$ #,##0.00'})
    fmt_total  = wb.add_format({"bold": True, "font_size": 9, "border": 1,
                                  "align": "right", "bg_color": "#F1F5F9"})

    ws.merge_range(0, 0, 0, 13, f"MOVIMENTAÇÃO DE TANQUE — {nome_tanque.upper()} — {periodo}", fmt_title)

    heads  = ["DATA","DIA","TIPO","FICHA","PLACA","PREFIXO","MOTORISTA/FORN.",
              "PRODUTO","KM/HOR","ENTRADA(L)","SAÍDA(L)","VL.UNIT(R$)","TOTAL(R$)","SALDO(L)"]
    widths = [11,6,14,10,10,8,24,14,8,11,10,12,12,11]
    ws.set_row(1, 26)
    for i, (h, w) in enumerate(zip(heads, widths)):
        ws.write(1, i, h, fmt_header)
        ws.set_column(i, i, w)

    # Consolida movimentos
    movs = []
    if not df_ent.empty:
        for _, r in df_ent.iterrows():
            movs.append({**r.to_dict(), "_tipo": "ENTRADA"})
    if not df_sai.empty:
        for _, r in df_sai.iterrows():
            movs.append({**r.to_dict(), "_tipo": "SAÍDA DIRETA"})
    if not df_transf.empty:
        for _, r in df_transf.iterrows():
            movs.append({**r.to_dict(), "_tipo": "TRANSF. CAMINHÃO"})
    movs.sort(key=lambda x: str(x.get("data", "")))

    saldo = 0.0
    t_ent = 0.0; t_sai = 0.0
    for ri, r in enumerate(movs, start=2):
        tipo = r["_tipo"]
        qtd  = to_float(r.get("quantidade"))
        vunt = to_float(r.get("valor_unitario"))
        tot  = to_float(r.get("total"))
        if tipo == "ENTRADA":
            saldo += qtd; t_ent += qtd
            q_ent, q_sai = qtd, 0.0
        else:
            saldo -= qtd; t_sai += qtd
            q_ent, q_sai = 0.0, qtd

        forn = (r.get("fornecedor","") if tipo == "ENTRADA"
                else r.get("motorista", r.get("caminhao_tanque","")))
        prod = (r.get("combustivel","") if tipo == "ENTRADA"
                else r.get("tipo_combustivel", r.get("produto","")))

        ws.write(ri, 0,  str(r.get("data",""))[:10], fmt_data)
        ws.write(ri, 1,  dia_semana_pt(str(r.get("data",""))[:10]), fmt_data)
        ws.write(ri, 2,  tipo, fmt_data)
        ws.write(ri, 3,  str(r.get("numero_ficha","")), fmt_data)
        ws.write(ri, 4,  str(r.get("placa","")), fmt_data)
        ws.write(ri, 5,  str(r.get("prefixo","")), fmt_data)
        ws.write(ri, 6,  str(forn), fmt_data)
        ws.write(ri, 7,  str(prod), fmt_data)
        ws.write(ri, 8,  str(r.get("horimetro","")), fmt_data)
        ws.write(ri, 9,  q_ent if q_ent else "", fmt_ent if q_ent else fmt_data)
        ws.write(ri, 10, q_sai if q_sai else "", fmt_sai if q_sai else fmt_data)
        ws.write(ri, 11, vunt, fmt_money)
        ws.write(ri, 12, tot,  fmt_money)
        ws.write(ri, 13, saldo, fmt_saldo)

    row_t = 2 + len(movs)
    ws.merge_range(row_t, 0, row_t, 8, "TOTAIS GERAIS", fmt_total)
    fmt_ent_tot = wb.add_format({"bold": True, "font_size": 9, "border": 1,
                                  "align": "right", "bg_color": "#DCFCE7",
                                  "num_format": "#,##0.0"})
    fmt_sai_tot = wb.add_format({"bold": True, "font_size": 9, "border": 1,
                                  "align": "right", "bg_color": "#FEE2E2",
                                  "num_format": "#,##0.0"})
    ws.write(row_t, 9,  t_ent, fmt_ent_tot)
    ws.write(row_t, 10, t_sai, fmt_sai_tot)
    ws.write(row_t, 11, "", fmt_total)
    ws.write(row_t, 12, "", fmt_total)
    ws.write(row_t, 13, t_ent - t_sai, fmt_saldo)

    wb.close()
    buf.seek(0)
    return buf.getvalue()


def gerar_excel_fluxo(df_resumo: pd.DataFrame, titulo: str) -> bytes:
    buf = io.BytesIO()
    wb  = xlsxwriter.Workbook(buf)
    ws  = wb.add_worksheet("Fluxo de Caixa")
    fmt_h  = wb.add_format({"bold":True,"font_size":10,"align":"center",
                              "bg_color":"#0D1B2A","font_color":"#3DD6A3","border":1})
    fmt_d  = wb.add_format({"font_size":9,"border":1,"align":"left"})
    fmt_m  = wb.add_format({"font_size":9,"border":1,"align":"right","num_format":"R$ #,##0.00"})
    fmt_n  = wb.add_format({"font_size":9,"border":1,"align":"right","num_format":"#,##0.00"})
    fmt_t  = wb.add_format({"bold":True,"font_size":9,"border":1,"align":"right",
                              "bg_color":"#F1F5F9","num_format":"R$ #,##0.00"})
    ws.merge_range(0, 0, 0, len(df_resumo.columns)-1, titulo, fmt_h)
    for ci, col in enumerate(df_resumo.columns):
        ws.write(1, ci, col, fmt_h)
        ws.set_column(ci, ci, 20)
    for ri, (_, row) in enumerate(df_resumo.iterrows(), start=2):
        for ci, val in enumerate(row):
            if isinstance(val, float):
                ws.write(ri, ci, val, fmt_m)
            else:
                ws.write(ri, ci, str(val), fmt_d)
    wb.close()
    buf.seek(0)
    return buf.getvalue()


# ═══════════════════════════════════════════════════════════════════
# COMPONENTES VISUAIS
# ═══════════════════════════════════════════════════════════════════
def kpi_card(col, icon: str, label: str, value: str, color: str = "#2563EB"):
    col.markdown(f"""
    <div class='kpi' style='border-left-color:{color}'>
        <div class='ico'>{icon}</div>
        <div class='val'>{value}</div>
        <div class='lbl'>{label}</div>
    </div>
    """, unsafe_allow_html=True)


def tank_gauge(col, nome: str, saldo: float, capacidade: float):
    pct = min(saldo / capacidade, 1.0) if capacidade > 0 else 0
    pct_txt = f"{pct*100:.0f}%" if capacidade > 0 else ""

    if pct > 0.30:
        cls = "tank-ok"; ic = "🟢"
    elif pct > 0.15:
        cls = "tank-low"; ic = "🟡"
    else:
        cls = "tank-crit"; ic = "🔴"

    col.markdown(f"""
    <div class='tank-card'>
        <div class='tank-name'>{ic} {nome}</div>
        <div class='tank-val {cls}'>{saldo:,.0f} L {pct_txt}</div>
    </div>
    """, unsafe_allow_html=True)
    if capacidade > 0:
        col.progress(max(0.0, pct))


def banner(msg: str, tipo: str = "in"):
    cls = {"ok":"bk-ok","lo":"bk-lo","er":"bk-er","in":"bk-in"}.get(tipo,"bk-in")
    st.markdown(f"<div class='{cls}'>{msg}</div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# LOGIN
# ═══════════════════════════════════════════════════════════════════
for k, v in [("logged_in", False), ("usuario_logado", ""), ("perfil_logado", "")]:
    if k not in st.session_state:
        st.session_state[k] = v

if not st.session_state.logged_in:
    st.markdown("""
    <style>
    [data-testid="stAppViewContainer"]{
        background:linear-gradient(135deg,#0D1B2A 0%,#1e3a5f 100%) !important;}
    [data-testid="stHeader"]{background:transparent !important;}
    [data-testid="stSidebar"]{display:none;}
    div[data-testid="stForm"]{background:rgba(255,255,255,.97) !important;
        border-radius:16px !important;padding:2.5rem !important;
        box-shadow:0 20px 60px rgba(0,0,0,.4) !important;}
    </style>
    """, unsafe_allow_html=True)

    st.write("<br><br>", unsafe_allow_html=True)
    _, c2, _ = st.columns([1, 2.2, 1])
    with c2:
        with st.form("login"):
            if os.path.exists("logo.png"):
                _, lc, _ = st.columns([1,2,1])
                with lc:
                    st.image("logo.png", width=240)

            st.markdown("""
            <h2 style='text-align:center;color:#0D1B2A;font-weight:700;
                        margin:.5rem 0 1.5rem;font-size:22px;'>
            🛣️ PavControl — COPA Engenharia
            </h2>""", unsafe_allow_html=True)

            u = st.text_input("Usuário", placeholder="Digite seu login")
            p = st.text_input("Senha", type="password", placeholder="••••••••")
            st.write("")

            if st.form_submit_button("ENTRAR NO SISTEMA", use_container_width=True):
                autenticado = False
                try:
                    # Tenta com senha em hash primeiro, depois texto puro (legado)
                    senha_hash = hash_senha(p)
                    res = supabase.table("usuarios").select("*").eq("login", u).execute()
                    if res.data:
                        usr = res.data[0]
                        if usr.get("senha") in (p, senha_hash):
                            st.session_state.logged_in      = True
                            st.session_state.usuario_logado = usr["nome"]
                            st.session_state.perfil_logado  = usr.get("perfil","Operador")
                            autenticado = True
                except Exception:
                    pass

                if not autenticado:
                    # Fallback admin via secrets
                    if (u == st.secrets.get("ADMIN_USER","admin")
                            and p == st.secrets.get("ADMIN_PASS","copa@2025")):
                        st.session_state.logged_in      = True
                        st.session_state.usuario_logado = "Admin"
                        st.session_state.perfil_logado  = "Admin"
                    else:
                        st.error("❌ Usuário ou senha incorretos.")

                if st.session_state.logged_in:
                    st.rerun()
    st.stop()


# ═══════════════════════════════════════════════════════════════════
# SIDEBAR / MENU
# ═══════════════════════════════════════════════════════════════════
with st.sidebar:
    if os.path.exists("logo.png"):
        _, lc, _ = st.columns([1,2,1])
        with lc:
            st.image("logo.png", width=220)

    st.markdown(f"""
    <div style='text-align:center;color:#3DD6A3;font-size:12px;
                font-weight:700;margin:.3rem 0 .8rem;'>
        👤 {st.session_state.usuario_logado}
    </div>""", unsafe_allow_html=True)
    st.divider()

    opcoes = [
        "🏠 Painel Geral",
        "💰 Fluxo de Caixa",
        "⛽ Lançar Abastecimento",
        "🔄 Transferência Caminhão-Tanque",
        "🛢️ Tanques / Estoque",
        "🚚 Boletim de Transporte",
        "🚜 Frota e Equipamentos",
        "🏗️ Obras",
        "🏪 Fornecedores",
        "📋 Relatórios e Fechamentos",
    ]
    if st.session_state.perfil_logado == "Admin":
        opcoes.append("👥 Usuários e Acessos")

    menu = st.radio("Navegação", opcoes, label_visibility="collapsed")
    st.divider()
    st.markdown("<br><br>", unsafe_allow_html=True)
    if st.button("↩️ Sair do Sistema", use_container_width=True):
        st.session_state.logged_in      = False
        st.session_state.usuario_logado = ""
        st.session_state.perfil_logado  = ""
        st.rerun()
    st.caption("☁️ Supabase · Dados em tempo real")


# ═══════════════════════════════════════════════════════════════════
# 1 · PAINEL GERAL
# ═══════════════════════════════════════════════════════════════════
if menu == "🏠 Painel Geral":
    st.markdown("## 🏠 Painel Geral — Centro de Comando")

    # ── Filtros de período e obra ─────────────────────────────────
    fc1, fc2, fc3 = st.columns(3)
    d_ini = fc1.date_input("De",  value=date.today().replace(day=1))
    d_fim = fc2.date_input("Até", value=date.today())
    obras_painel = lista_obras(incluir_todas=True)
    obra_filtro  = fc3.selectbox("Obra", obras_painel) if obras_painel else "TODAS"

    # ── Busca de dados ────────────────────────────────────────────
    df_tanq  = get_data("tanques")
    df_ab    = get_data("abastecimentos")
    df_prod  = get_data("producao")
    df_ent_t = get_data("entradas_tanque")
    saldos   = calcular_todos_saldos()

    if not df_ab.empty and "status" in df_ab.columns:
        df_ab = df_ab[df_ab["status"] == "ATIVO"]

    # ── Filtro por período e obra ─────────────────────────────────
    def filtrar_por_periodo(df, d_ini, d_fim, obra_col="obra"):
        if df.empty:
            return df
        df = df.copy()
        df["_dt"] = pd.to_datetime(df.get("data",""), errors="coerce").dt.date
        df = df[df["_dt"].notna() & (df["_dt"] >= d_ini) & (df["_dt"] <= d_fim)]
        if obra_filtro and obra_filtro != "TODAS" and obra_col in df.columns:
            df = df[df[obra_col] == obra_filtro]
        return df

    daf  = filtrar_por_periodo(df_ab, d_ini, d_fim)
    dpf  = filtrar_por_periodo(df_prod, d_ini, d_fim)

    t_gasto   = pd.to_numeric(daf.get("total",      pd.Series(dtype=float)), errors="coerce").sum()
    t_litros  = pd.to_numeric(daf.get("quantidade", pd.Series(dtype=float)), errors="coerce").sum()
    t_ton     = pd.to_numeric(dpf.get("toneladas",  pd.Series(dtype=float)), errors="coerce").sum()
    t_viagens = int(pd.to_numeric(dpf.get("carradas", pd.Series(dtype=float)), errors="coerce").sum())

    custo_ton   = t_gasto  / t_ton    if t_ton    > 0 else 0
    litros_ton  = t_litros / t_ton    if t_ton    > 0 else 0
    litros_viag = t_litros / t_viagens if t_viagens > 0 else 0

    # ── KPIs principais ───────────────────────────────────────────
    st.markdown("#### 📊 Indicadores do Período")
    c1, c2, c3, c4 = st.columns(4)
    kpi_card(c1, "💰", "Gasto com Combustível", f"R$ {t_gasto:,.2f}", "#DC2626")
    kpi_card(c2, "⛽", "Litros Abastecidos",    f"{t_litros:,.0f} L",  "#2563EB")
    kpi_card(c3, "🏗️", "Toneladas Transportadas", f"{t_ton:,.1f} t",  "#059669")
    kpi_card(c4, "🚚", "Viagens Realizadas",    str(t_viagens),         "#7C3AED")

    st.markdown("<br>", unsafe_allow_html=True)
    c5, c6, c7, _ = st.columns(4)
    kpi_card(c5, "📉", "Custo / Tonelada",    f"R$ {custo_ton:,.2f}",   "#D97706")
    kpi_card(c6, "🔢", "Litros / Tonelada",   f"{litros_ton:,.2f} L",   "#0891B2")
    kpi_card(c7, "🛣️", "Litros / Viagem",     f"{litros_viag:,.1f} L",  "#7C3AED")

    st.divider()

    # ── Saldo dos Tanques em tempo real ───────────────────────────
    if not df_tanq.empty:
        st.markdown("#### 🛢️ Situação dos Tanques em Tempo Real")
        cols_tanq = st.columns(min(len(df_tanq), 5))
        for i, (_, row) in enumerate(df_tanq.iterrows()):
            nm  = row.get("nome","")
            cap = to_float(row.get("capacidade"))
            sd  = saldos.get(nm, 0.0)
            with cols_tanq[i % len(cols_tanq)]:
                tank_gauge(st.container(), nm, sd, cap)

    st.divider()

    # ── Gráficos ──────────────────────────────────────────────────
    if not daf.empty and "data" in daf.columns:
        daf["Mês"] = pd.to_datetime(daf["data"], errors="coerce").dt.strftime("%m/%Y")
        daf["total_n"] = pd.to_numeric(daf.get("total",0), errors="coerce").fillna(0)

        col_g1, col_g2 = st.columns(2)

        with col_g1:
            g_mes = daf.groupby("Mês")["total_n"].sum().reset_index()
            if not g_mes.empty:
                fig = px.bar(g_mes, x="Mês", y="total_n",
                             title="💰 Gasto Mensal com Combustível",
                             labels={"total_n":"Total (R$)","Mês":"Mês/Ano"},
                             color_discrete_sequence=["#2563EB"])
                fig.update_traces(texttemplate="R$%{y:,.0f}", textposition="outside")
                fig.update_layout(plot_bgcolor="rgba(0,0,0,0)",
                                  paper_bgcolor="rgba(0,0,0,0)", margin=dict(t=40,b=20,l=0,r=0))
                st.plotly_chart(fig, use_container_width=True)

        with col_g2:
            if "obra" in daf.columns:
                g_obra = (daf.groupby("obra")["total_n"].sum()
                            .reset_index()
                            .sort_values("total_n", ascending=False)
                            .head(8))
                if not g_obra.empty:
                    fig2 = px.bar(g_obra, x="total_n", y="obra", orientation="h",
                                  title="🏗️ Gasto por Obra",
                                  labels={"total_n":"Total (R$)","obra":"Obra"},
                                  color_discrete_sequence=["#059669"])
                    fig2.update_layout(plot_bgcolor="rgba(0,0,0,0)",
                                       paper_bgcolor="rgba(0,0,0,0)",
                                       margin=dict(t=40,b=20,l=0,r=0),
                                       yaxis={"categoryorder":"total ascending"})
                    st.plotly_chart(fig2, use_container_width=True)

    # ── Top veículos consumidores ─────────────────────────────────
    if not daf.empty and "prefixo" in daf.columns:
        st.markdown("#### 🚜 Top 10 — Maiores Consumidores")
        top_v = (pd.to_numeric(daf.groupby("prefixo")["quantidade"].sum(), errors="coerce")
                   .reset_index()
                   .sort_values("quantidade", ascending=False)
                   .head(10))
        if not top_v.empty:
            fig3 = px.bar(top_v, x="prefixo", y="quantidade",
                          labels={"quantidade":"Litros","prefixo":"Veículo/Equip."},
                          color_discrete_sequence=["#7C3AED"])
            fig3.update_layout(plot_bgcolor="rgba(0,0,0,0)",
                               paper_bgcolor="rgba(0,0,0,0)", margin=dict(t=20,b=20,l=0,r=0))
            st.plotly_chart(fig3, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════
# 2 · FLUXO DE CAIXA INTELIGENTE
# ═══════════════════════════════════════════════════════════════════
elif menu == "💰 Fluxo de Caixa":
    st.markdown("## 💰 Fluxo de Caixa — Combustível")
    banner("Acompanhe entradas (compras), saídas (abastecimentos) e saldo financeiro por período, obra e fornecedor.", "in")

    # ── Filtros ───────────────────────────────────────────────────
    fc1, fc2, fc3 = st.columns(3)
    d_ini = fc1.date_input("Período De",  value=date.today().replace(day=1), key="fc_ini")
    d_fim = fc2.date_input("Período Até", value=date.today(),                key="fc_fim")
    obras_fc = lista_obras(incluir_todas=True)
    obra_fc  = fc3.selectbox("Obra", obras_fc, key="fc_obra") if obras_fc else "TODAS"

    # ── Dados ─────────────────────────────────────────────────────
    df_ent_t  = get_data("entradas_tanque")    # compras para o tanque
    df_ab     = get_data("abastecimentos")      # abastecimentos externos + tanque
    df_transf = get_data("transferencias_tanque")

    if not df_ab.empty and "status" in df_ab.columns:
        df_ab = df_ab[df_ab["status"] == "ATIVO"]
    if not df_transf.empty and "status" in df_transf.columns:
        df_transf = df_transf[df_transf["status"] == "ATIVO"]

    def aplicar_filtro_fc(df, obra_col="obra"):
        if df.empty:
            return df
        df = df.copy()
        df["_dt"] = pd.to_datetime(df.get("data",""), errors="coerce").dt.date
        df = df[df["_dt"].notna() & (df["_dt"] >= d_ini) & (df["_dt"] <= d_fim)]
        if obra_fc != "TODAS" and obra_col in df.columns:
            df = df[df[obra_col] == obra_fc]
        return df

    ent_f  = aplicar_filtro_fc(df_ent_t)
    ab_f   = aplicar_filtro_fc(df_ab)
    tr_f   = aplicar_filtro_fc(df_transf)

    # ── Totais financeiros ────────────────────────────────────────
    # Entradas de caixa = compras de combustível (o que foi pago ao fornecedor p/ tanque)
    total_compras   = pd.to_numeric(ent_f.get("total",      pd.Series(dtype=float)), errors="coerce").sum()
    litros_compras  = pd.to_numeric(ent_f.get("quantidade", pd.Series(dtype=float)), errors="coerce").sum()

    # Saídas = abastecimentos em postos externos
    ab_posto = ab_f[ab_f.get("origem", pd.Series(dtype=str)) == "Posto Externo"] if not ab_f.empty and "origem" in ab_f.columns else pd.DataFrame()
    total_posto   = pd.to_numeric(ab_posto.get("total",      pd.Series(dtype=float)), errors="coerce").sum()
    litros_posto  = pd.to_numeric(ab_posto.get("quantidade", pd.Series(dtype=float)), errors="coerce").sum()

    # Abastecimentos do tanque (consumo interno)
    ab_tanq = ab_f[ab_f.get("origem", pd.Series(dtype=str)) == "Tanque Interno"] if not ab_f.empty and "origem" in ab_f.columns else pd.DataFrame()
    litros_tanq = pd.to_numeric(ab_tanq.get("quantidade", pd.Series(dtype=float)), errors="coerce").sum()
    # Custo do tanque = proporcional ao custo médio das compras
    preco_medio = (total_compras / litros_compras) if litros_compras > 0 else 0
    total_tanq  = litros_tanq * preco_medio

    total_geral = total_posto + total_compras

    # ── KPIs financeiros ──────────────────────────────────────────
    st.markdown("#### 📊 Resumo Financeiro do Período")
    k1, k2, k3, k4 = st.columns(4)
    kpi_card(k1, "🏪", "Compras p/ Tanque (Distribuidoras)", f"R$ {total_compras:,.2f}", "#059669")
    kpi_card(k2, "⛽", "Abastec. em Postos Externos",        f"R$ {total_posto:,.2f}",   "#DC2626")
    kpi_card(k3, "💡", "Custo Estimado (Tanque Próprio)",    f"R$ {total_tanq:,.2f}",    "#D97706")
    kpi_card(k4, "🔢", "Preço Médio Compra",                f"R$ {preco_medio:,.3f}/L", "#2563EB")

    st.markdown("<br>", unsafe_allow_html=True)
    k5, k6, k7, k8 = st.columns(4)
    kpi_card(k5, "📦", "Litros Comprados (Tanque)",   f"{litros_compras:,.0f} L",  "#059669")
    kpi_card(k6, "🚗", "Litros Abast. (Postos)",      f"{litros_posto:,.0f} L",    "#DC2626")
    kpi_card(k7, "🛢️", "Litros Abast. (Tanque Prop.)", f"{litros_tanq:,.0f} L",    "#D97706")
    kpi_card(k8, "💰", "Gasto Total no Período",      f"R$ {total_geral:,.2f}",    "#7C3AED")

    st.divider()

    # ── Abas de análise ───────────────────────────────────────────
    aba_forn, aba_obra, aba_veic, aba_evolucao = st.tabs([
        "🏪 Por Fornecedor", "🏗️ Por Obra", "🚜 Por Veículo", "📈 Evolução Mensal"
    ])

    # Análise por Fornecedor
    with aba_forn:
        st.markdown("##### 💳 Consolidado por Fornecedor — Base para Pagamentos")

        linhas = []
        # Compras para tanque
        if not ent_f.empty and "fornecedor" in ent_f.columns:
            g = ent_f.groupby("fornecedor").agg(
                litros=("quantidade","sum"), total=("total","sum")
            ).reset_index()
            g["tipo"] = "Compra p/ Tanque"
            g.columns = ["Fornecedor","Litros","Total R$","Tipo"]
            linhas.append(g)

        # Abastecimentos externos
        if not ab_posto.empty and "fornecedor" in ab_posto.columns:
            g2 = ab_posto.groupby("fornecedor").agg(
                litros=("quantidade","sum"), total=("total","sum")
            ).reset_index()
            g2["tipo"] = "Abastecimento Externo"
            g2.columns = ["Fornecedor","Litros","Total R$","Tipo"]
            linhas.append(g2)

        if linhas:
            df_forn = pd.concat(linhas, ignore_index=True)
            df_forn["Litros"]    = pd.to_numeric(df_forn["Litros"],   errors="coerce").fillna(0)
            df_forn["Total R$"]  = pd.to_numeric(df_forn["Total R$"], errors="coerce").fillna(0)
            df_forn["Preço Médio"] = (df_forn["Total R$"] / df_forn["Litros"]).replace([float("inf")], 0).round(3)

            # Gráfico
            fig_f = px.bar(
                df_forn.sort_values("Total R$", ascending=False),
                x="Fornecedor", y="Total R$", color="Tipo",
                barmode="group",
                color_discrete_sequence=["#2563EB","#059669"],
                title="Gasto por Fornecedor"
            )
            fig_f.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_f, use_container_width=True)

            st.dataframe(
                df_forn.sort_values("Total R$", ascending=False)
                       .style.format({"Litros":"{:,.1f}","Total R$":"R$ {:,.2f}","Preço Médio":"R$ {:,.3f}"}),
                use_container_width=True, hide_index=True
            )

            # Botão pagamento por fornecedor
            st.markdown("##### 📥 Exportar Relatório de Pagamento por Fornecedor")
            fornecedores_unicos = df_forn["Fornecedor"].dropna().unique().tolist()
            col_fsel, col_fbtn = st.columns([2,1])
            forn_pag = col_fsel.selectbox("Selecionar fornecedor para exportar", fornecedores_unicos, key="forn_pag")
            if col_fbtn.button("📄 Gerar Relatório de Pagamento"):
                df_pag = ab_posto[ab_posto.get("fornecedor","") == forn_pag] if not ab_posto.empty else pd.DataFrame()
                if not ent_f.empty and "fornecedor" in ent_f.columns:
                    df_compras_pag = ent_f[ent_f["fornecedor"] == forn_pag]
                    if not df_pag.empty and not df_compras_pag.empty:
                        pass  # ambos têm dados
                    elif not df_compras_pag.empty:
                        df_pag = df_compras_pag
                per_str = f"{d_ini.strftime('%d/%m/%Y')} a {d_fim.strftime('%d/%m/%Y')}"
                xl_pag = gerar_excel_abastecimentos(
                    df_pag,
                    f"RELATÓRIO DE PAGAMENTO — {forn_pag.upper()}",
                    per_str
                )
                st.download_button(
                    f"⬇️ Baixar Excel — {forn_pag}",
                    data=xl_pag,
                    file_name=f"Pagamento_{forn_pag}_{d_ini}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.info("Nenhum dado no período selecionado.")

    # Análise por Obra
    with aba_obra:
        st.markdown("##### 🏗️ Custo de Combustível por Obra")
        if not ab_f.empty and "obra" in ab_f.columns:
            g_obra = ab_f.groupby("obra").agg(
                litros=("quantidade","sum"),
                gasto=("total","sum"),
                abast=("id","count") if "id" in ab_f.columns else ("quantidade","count")
            ).reset_index()
            g_obra.columns = ["Obra","Litros","Gasto R$","Qtde Abast."]
            g_obra["Litros"]   = pd.to_numeric(g_obra["Litros"],  errors="coerce").fillna(0)
            g_obra["Gasto R$"] = pd.to_numeric(g_obra["Gasto R$"],errors="coerce").fillna(0)
            g_obra = g_obra.sort_values("Gasto R$", ascending=False)

            fig_o = px.pie(g_obra, names="Obra", values="Gasto R$",
                           title="Distribuição de Custo por Obra",
                           color_discrete_sequence=px.colors.qualitative.Bold)
            fig_o.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_o, use_container_width=True)

            st.dataframe(
                g_obra.style.format({"Litros":"{:,.1f}","Gasto R$":"R$ {:,.2f}"}),
                use_container_width=True, hide_index=True
            )

            xl_obra = gerar_excel_limpo(g_obra, "Custo por Obra")
            st.download_button("📥 Exportar Excel", xl_obra,
                               f"Custo_Obra_{d_ini}_{d_fim}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.info("Nenhum abastecimento com obra vinculada no período.")

    # Análise por Veículo
    with aba_veic:
        st.markdown("##### 🚜 Consumo e Custo por Veículo / Equipamento")
        if not ab_f.empty and "prefixo" in ab_f.columns:
            g_veic = ab_f.groupby("prefixo").agg(
                litros=("quantidade","sum"),
                gasto=("total","sum")
            ).reset_index()
            g_veic.columns = ["Veículo","Litros","Gasto R$"]
            g_veic["Litros"]       = pd.to_numeric(g_veic["Litros"],  errors="coerce").fillna(0)
            g_veic["Gasto R$"]     = pd.to_numeric(g_veic["Gasto R$"],errors="coerce").fillna(0)
            g_veic["Preço Médio"]  = (g_veic["Gasto R$"] / g_veic["Litros"]).replace([float("inf")], 0).round(3)
            g_veic = g_veic.sort_values("Litros", ascending=False)

            fig_v = px.bar(g_veic.head(15), x="Veículo", y="Litros",
                           title="Top 15 — Maiores Consumidores (Litros)",
                           color="Gasto R$",
                           color_continuous_scale="Blues")
            fig_v.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_v, use_container_width=True)

            st.dataframe(
                g_veic.style.format({"Litros":"{:,.1f}","Gasto R$":"R$ {:,.2f}","Preço Médio":"R$ {:,.3f}"}),
                use_container_width=True, hide_index=True
            )
        else:
            st.info("Nenhum dado de veículo no período.")

    # Evolução Mensal
    with aba_evolucao:
        st.markdown("##### 📈 Evolução Mensal do Gasto com Combustível")
        # Combina compras de tanque + abastecimentos externos
        frames = []
        if not ab_f.empty and "data" in ab_f.columns:
            tmp = ab_f[["data","total","origem"]].copy()
            tmp["total"] = pd.to_numeric(tmp["total"], errors="coerce").fillna(0)
            tmp["Mês"] = pd.to_datetime(tmp["data"], errors="coerce").dt.strftime("%m/%Y")
            frames.append(tmp.groupby(["Mês","origem"])["total"].sum().reset_index()
                            .rename(columns={"origem":"Categoria","total":"Valor R$"}))
        if not ent_f.empty and "data" in ent_f.columns:
            tmp2 = ent_f[["data","total"]].copy()
            tmp2["total"] = pd.to_numeric(tmp2["total"], errors="coerce").fillna(0)
            tmp2["Mês"] = pd.to_datetime(tmp2["data"], errors="coerce").dt.strftime("%m/%Y")
            tmp2["Categoria"] = "Compra p/ Tanque"
            frames.append(tmp2.groupby(["Mês","Categoria"])["total"].sum().reset_index()
                            .rename(columns={"total":"Valor R$"}))

        if frames:
            df_evo = pd.concat(frames, ignore_index=True)
            fig_e  = px.line(df_evo, x="Mês", y="Valor R$", color="Categoria",
                             markers=True, title="Evolução Mensal por Categoria",
                             color_discrete_sequence=["#2563EB","#059669","#D97706"])
            fig_e.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_e, use_container_width=True)
        else:
            st.info("Nenhum dado no período.")


# ═══════════════════════════════════════════════════════════════════
# 3 · LANÇAR ABASTECIMENTO
# ═══════════════════════════════════════════════════════════════════
elif menu == "⛽ Lançar Abastecimento":
    st.markdown("## ⛽ Lançar Abastecimento")

    df_v  = get_data("veiculos")
    df_f  = get_data("fornecedores")
    df_t  = get_data("tanques")
    df_a  = get_data("abastecimentos")
    saldos = calcular_todos_saldos()

    if df_v.empty:
        banner("⚠️ Nenhum veículo cadastrado. Cadastre em 🚜 Frota e Equipamentos.", "lo")
        st.stop()

    # ── Seleção de veículo ────────────────────────────────────────
    v_sel = st.selectbox("🚜 Veículo / Equipamento", df_v["prefixo"].tolist())
    v_info = df_v[df_v["prefixo"] == v_sel].iloc[0]
    comb_padrao    = v_info.get("tipo_combustivel_padrao","Diesel S10")
    placa_padrao   = v_info.get("placa","")
    motorista_padrao = v_info.get("motorista","")

    # Último horímetro
    m_hor = 0.0
    if not df_a.empty and "prefixo" in df_a.columns:
        df_hist = df_a[df_a["prefixo"] == v_sel].copy()
        df_hist["hor_n"] = pd.to_numeric(df_hist.get("horimetro"), errors="coerce")
        m_hor = df_hist["hor_n"].max() or 0.0

    origem = st.radio("Origem do Combustível", ["Posto Externo","Tanque Interno"], horizontal=True)

    # Pré-visualização de saldo do tanque
    saldo_preview = None
    tanq_preview  = None
    if origem == "Tanque Interno" and not df_t.empty:
        tanq_preview = st.selectbox("Tanque (pré-visualização)", df_t["nome"].tolist(), key="prv_tanq")
        saldo_preview = saldos.get(tanq_preview, 0.0)
        cls = "bk-ok" if saldo_preview >= 500 else "bk-lo"
        st.markdown(f"<div class='{cls}'>🛢️ Saldo atual de <strong>{tanq_preview}</strong>: "
                    f"<strong>{saldo_preview:,.1f} L</strong></div>", unsafe_allow_html=True)

    obras_lista = lista_obras()

    with st.form("form_ab", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        data_ab   = c1.date_input("Data")
        ficha     = c2.text_input("Ficha / Nota Fiscal")
        motorista = c3.text_input("Motorista", value=motorista_padrao)

        c4, c5, c6 = st.columns(3)
        if origem == "Posto Externo":
            fornecedores_lista = df_f["nome"].tolist() if not df_f.empty else ["Sem cadastro"]
            posto  = c4.selectbox("Fornecedor", fornecedores_lista)
            n_tanq = None
        else:
            n_tanq = c4.selectbox("Tanque", df_t["nome"].tolist() if not df_t.empty else [], key="tanq_form")
            posto  = "Estoque Próprio"

        hor = c5.number_input("KM / Horímetro", value=float(m_hor), min_value=0.0)
        obs = c6.text_input("Observação")

        c7, c8, c9 = st.columns(3)
        litros = c7.number_input("Litros", min_value=0.0, step=0.5)
        preco  = c8.number_input("Preço (R$/L)", min_value=0.0, step=0.01)

        if obras_lista:
            obra_ab = c9.selectbox("Obra / Projeto", obras_lista)
        else:
            obra_ab = c9.text_input("Obra / Projeto")

        total = litros * preco
        st.markdown(f"<div class='bk-in'>💰 <strong>Total calculado: R$ {total:,.2f}</strong> "
                    f"| {litros:,.1f} L × R$ {preco:,.3f}/L</div>", unsafe_allow_html=True)

        if origem == "Tanque Interno" and saldo_preview is not None and litros > saldo_preview:
            st.markdown(f"<div class='bk-er'>⚠️ Quantidade ({litros:,.1f} L) "
                        f"excede o saldo disponível ({saldo_preview:,.1f} L)!</div>",
                        unsafe_allow_html=True)

        if st.form_submit_button("💾 REGISTRAR ABASTECIMENTO", use_container_width=True):
            if litros <= 0:
                st.error("⚠️ Informe a quantidade de litros.")
            else:
                ok = insert_data("abastecimentos", {
                    "data":             str(data_ab),
                    "numero_ficha":     ficha,
                    "origem":           origem,
                    "nome_tanque":      n_tanq if origem == "Tanque Interno" else None,
                    "prefixo":          v_sel,
                    "placa":            placa_padrao,
                    "motorista":        motorista.upper(),
                    "tipo_combustivel": comb_padrao,
                    "quantidade":       litros,
                    "valor_unitario":   preco,
                    "total":            round(total, 2),
                    "fornecedor":       posto,
                    "horimetro":        hor,
                    "obra":             obra_ab,
                    "observacao":       obs,
                    "status":           "ATIVO",
                    "criado_por":       st.session_state.usuario_logado,
                })
                if ok:
                    st.success("✅ Abastecimento registrado com sucesso!")
                    st.rerun()

    # ── Listagem ──────────────────────────────────────────────────
    st.divider()
    st.subheader("📋 Abastecimentos Registrados")

    if df_a.empty:
        st.info("Nenhum registro encontrado.")
    else:
        df_a = df_a.sort_values("data", ascending=False).fillna("")
        fl1, fl2, fl3, fl4 = st.columns(4)
        f_di   = fl1.date_input("De",    value=date.today().replace(day=1), key="f_di_ab")
        f_df   = fl2.date_input("Até",   value=date.today(),                key="f_df_ab")
        f_veic = fl3.selectbox("Veículo", ["TODOS"] + df_v["prefixo"].tolist(), key="f_veic_ab")
        obras_f = lista_obras(incluir_todas=True)
        f_obra  = fl4.selectbox("Obra", obras_f if obras_f else ["TODAS"], key="f_obra_ab")

        df_a["data_dt"] = pd.to_datetime(df_a["data"], errors="coerce").dt.date
        df_a_fil = df_a[(df_a["data_dt"] >= f_di) & (df_a["data_dt"] <= f_df)]
        if f_veic != "TODOS":
            df_a_fil = df_a_fil[df_a_fil["prefixo"] == f_veic]
        if f_obra not in ("TODAS","") and "obra" in df_a_fil.columns:
            df_a_fil = df_a_fil[df_a_fil["obra"] == f_obra]

        ativos    = df_a_fil[df_a_fil.get("status", pd.Series(["ATIVO"]*len(df_a_fil))) == "ATIVO"]
        cancelados= df_a_fil[df_a_fil.get("status", pd.Series(["ATIVO"]*len(df_a_fil))) != "ATIVO"]

        # KPI do filtro
        tot_l = pd.to_numeric(ativos.get("quantidade",0), errors="coerce").sum()
        tot_r = pd.to_numeric(ativos.get("total",0),      errors="coerce").sum()
        mk1, mk2, mk3 = st.columns(3)
        kpi_card(mk1,"⛽","Litros no Filtro", f"{tot_l:,.1f} L", "#2563EB")
        kpi_card(mk2,"💰","Gasto no Filtro",  f"R$ {tot_r:,.2f}", "#DC2626")
        kpi_card(mk3,"📋","Registros Ativos", str(len(ativos)), "#059669")
        st.markdown("<br>", unsafe_allow_html=True)

        tab1, tab2 = st.tabs([f"✅ Ativos ({len(ativos)})", f"❌ Cancelados ({len(cancelados)})"])

        with tab1:
            if ativos.empty:
                st.info("Nenhum registro ativo no período/filtro.")
            else:
                for r in ativos.head(60).to_dict("records"):
                    obra_tag = f" | 🏗️ {r.get('obra','')}" if r.get("obra") else ""
                    with st.expander(
                        f"📅 {r.get('data','')[:10]} | 🚜 {r.get('prefixo','')} | "
                        f"⛽ {to_float(r.get('quantidade')):,.1f} L | "
                        f"💰 R$ {to_float(r.get('total')):,.2f}{obra_tag}"
                    ):
                        ec1, ec2, ec3, ec4 = st.columns(4)
                        ec1.write(f"**Motorista:** {r.get('motorista','')}")
                        ec2.write(f"**Placa:** {r.get('placa','')}")
                        ec3.write(f"**Fornecedor:** {r.get('fornecedor','')}")
                        ec4.write(f"**Origem:** {r.get('origem','')}")
                        ec5, ec6, ec7, ec8 = st.columns(4)
                        ec5.write(f"**Ficha:** {r.get('numero_ficha','')}")
                        ec6.write(f"**KM/Hor:** {r.get('horimetro','')}")
                        ec7.write(f"**Obra:** {r.get('obra','-')}")
                        ec8.write(f"**Obs:** {r.get('observacao','')}")

                        with st.form(f"edit_ab_{r.get('id')}"):
                            st.markdown("**✏️ Editar Registro**")
                            ne1, ne2, ne3 = st.columns(3)
                            new_litros = ne1.number_input("Litros",     value=to_float(r.get("quantidade")), min_value=0.0, key=f"nl_{r.get('id')}")
                            new_preco  = ne2.number_input("Preço R$/L", value=to_float(r.get("valor_unitario")), min_value=0.0, key=f"np_{r.get('id')}")
                            obras_edit = lista_obras()
                            obra_atual = r.get("obra","")
                            idx_o = obras_edit.index(obra_atual) if obra_atual in obras_edit else 0
                            new_obra = ne3.selectbox("Obra", obras_edit, index=idx_o, key=f"no_{r.get('id')}") if obras_edit else ne3.text_input("Obra", value=obra_atual, key=f"no_{r.get('id')}")
                            ne4, ne5 = st.columns(2)
                            new_hor  = ne4.number_input("KM/Hor", value=to_float(r.get("horimetro")), min_value=0.0, key=f"nh_{r.get('id')}")
                            new_obs  = ne5.text_input("Observação", value=r.get("observacao",""), key=f"nobs_{r.get('id')}")
                            cs, cc = st.columns(2)
                            if cs.form_submit_button("💾 Salvar Edição", use_container_width=True):
                                if update_data("abastecimentos", r.get("id"), {
                                    "quantidade": new_litros, "valor_unitario": new_preco,
                                    "total": round(new_litros * new_preco, 2),
                                    "horimetro": new_hor, "obra": new_obra, "observacao": new_obs
                                }):
                                    st.success("✅ Atualizado!")
                                    st.rerun()
                            if cc.form_submit_button("❌ Cancelar Registro", use_container_width=True):
                                supabase.table("abastecimentos").update({"status":"CANCELADO"}).eq("id", r.get("id")).execute()
                                _invalidate()
                                st.warning("Registro cancelado.")
                                st.rerun()

        with tab2:
            if cancelados.empty:
                st.info("Nenhum registro cancelado.")
            else:
                for r in cancelados.head(30).to_dict("records"):
                    c1, c2 = st.columns([5,1])
                    c1.write(f"❌ {r.get('data','')[:10]} | {r.get('prefixo','')} | "
                             f"{to_float(r.get('quantidade')):,.1f} L | Obra: {r.get('obra','-')}")
                    if c2.button("↩️ Restaurar", key=f"rest_{r.get('id')}"):
                        supabase.table("abastecimentos").update({"status":"ATIVO"}).eq("id", r.get("id")).execute()
                        _invalidate()
                        st.rerun()


# ═══════════════════════════════════════════════════════════════════
# 4 · TRANSFERÊNCIA CAMINHÃO-TANQUE
# ═══════════════════════════════════════════════════════════════════
elif menu == "🔄 Transferência Caminhão-Tanque":
    st.markdown("## 🔄 Transferência — Caminhão-Tanque para Campo")
    banner("Registre aqui quando o caminhão-tanque retira combustível do tanque fixo e abastece veículos em campo. "
           "O saldo do tanque é atualizado automaticamente.", "in")

    df_v     = get_data("veiculos")
    df_t     = get_data("tanques")
    df_tr    = get_data("transferencias_tanque")
    saldos   = calcular_todos_saldos()

    df_ct = pd.DataFrame()
    if not df_v.empty and "tipo_veiculo" in df_v.columns:
        df_ct = df_v[df_v["tipo_veiculo"] == "Caminhão-Tanque"]

    obras_lista = lista_obras()

    tab_reg, tab_hist = st.tabs(["➕ Registrar Transferência","📋 Histórico"])

    with tab_reg:
        if df_t.empty:
            banner("⚠️ Cadastre ao menos um tanque fixo antes.", "lo")
        else:
            st.markdown("#### 🛢️ Saldo Atual dos Tanques")
            df_tanq = get_data("tanques")
            cols_sd = st.columns(min(len(df_tanq), 5))
            for idx_t, row_t in df_tanq.iterrows():
                nm = row_t.get("nome","")
                cap = to_float(row_t.get("capacidade"))
                sd  = saldos.get(nm, 0.0)
                with cols_sd[idx_t % min(len(df_tanq), 5)]:
                    tank_gauge(st.container(), nm, sd, cap)

            st.divider()

            with st.form("form_transf", clear_on_submit=True):
                ct1, ct2, ct3 = st.columns(3)
                data_tr   = ct1.date_input("Data da Transferência")
                ficha_tr  = ct2.text_input("Ficha / Documento")
                tanq_orig = ct3.selectbox("Tanque de Origem", df_t["nome"].tolist())

                ct4, ct5, ct6 = st.columns(3)
                if not df_ct.empty:
                    caminhao_sel = ct4.selectbox("Caminhão-Tanque", df_ct["prefixo"].tolist())
                    info_ct = df_ct[df_ct["prefixo"] == caminhao_sel].iloc[0]
                    motorista_ct = info_ct.get("motorista","")
                    placa_ct     = info_ct.get("placa","")
                else:
                    caminhao_sel = ct4.text_input("Caminhão-Tanque (prefixo)")
                    motorista_ct = ""; placa_ct = ""

                motorista_tr = ct5.text_input("Motorista", value=motorista_ct)
                placa_tr     = ct6.text_input("Placa",     value=placa_ct)

                ct7, ct8, ct9 = st.columns(3)
                qtd_tr    = ct7.number_input("Quantidade (L)", min_value=0.0, step=10.0)
                vunt_tr   = ct8.number_input("Valor Unitário (R$/L)", min_value=0.0, step=0.01)
                produto_tr= ct9.selectbox("Produto", ["Diesel S10","Diesel S500","Gasolina Comum"])

                ct10, ct11 = st.columns(2)
                if obras_lista:
                    obra_tr = ct10.selectbox("Obra Atendida", obras_lista)
                else:
                    obra_tr = ct10.text_input("Obra Atendida")
                obs_tr = ct11.text_input("Observação")

                total_tr = qtd_tr * vunt_tr
                saldo_orig = saldos.get(tanq_orig, 0.0)

                st.markdown(f"<div class='bk-in'>💰 Total: <strong>R$ {total_tr:,.2f}</strong> "
                            f"| Saldo disponível em <strong>{tanq_orig}</strong>: "
                            f"<strong>{saldo_orig:,.1f} L</strong></div>", unsafe_allow_html=True)

                if qtd_tr > saldo_orig > 0:
                    st.markdown(f"<div class='bk-er'>⚠️ Quantidade ({qtd_tr:,.1f} L) "
                                f"excede o saldo ({saldo_orig:,.1f} L)!</div>", unsafe_allow_html=True)

                if st.form_submit_button("💾 REGISTRAR TRANSFERÊNCIA", use_container_width=True):
                    if qtd_tr <= 0:
                        st.error("⚠️ Informe a quantidade.")
                    else:
                        ok = insert_data("transferencias_tanque", {
                            "data":             str(data_tr),
                            "numero_ficha":     ficha_tr,
                            "tanque_origem":    tanq_orig,
                            "caminhao_tanque":  caminhao_sel,
                            "placa":            placa_tr,
                            "motorista":        motorista_tr.upper(),
                            "produto":          produto_tr,
                            "quantidade":       qtd_tr,
                            "valor_unitario":   vunt_tr,
                            "total":            round(total_tr, 2),
                            "obra":             obra_tr,
                            "observacao":       obs_tr,
                            "status":           "ATIVO",
                            "criado_por":       st.session_state.usuario_logado,
                        })
                        if ok:
                            st.success(f"✅ Transferência registrada! Novo saldo estimado de {tanq_orig}: "
                                       f"{saldo_orig - qtd_tr:,.1f} L")
                            st.rerun()

    with tab_hist:
        if df_tr.empty:
            st.info("Nenhuma transferência registrada.")
        else:
            df_tr = df_tr.sort_values("data", ascending=False).fillna("")
            fh1, fh2 = st.columns(2)
            fh_di = fh1.date_input("De",  value=date.today().replace(day=1), key="fh_tr_di")
            fh_df = fh2.date_input("Até", value=date.today(),                key="fh_tr_df")
            df_tr["data_dt"] = pd.to_datetime(df_tr["data"], errors="coerce").dt.date
            df_tr_fil = df_tr[(df_tr["data_dt"] >= fh_di) & (df_tr["data_dt"] <= fh_df)]

            tot_l = pd.to_numeric(df_tr_fil.get("quantidade",0), errors="coerce").sum()
            tot_r = pd.to_numeric(df_tr_fil.get("total",0),      errors="coerce").sum()
            km1, km2 = st.columns(2)
            kpi_card(km1, "⛽", "Total Transferido", f"{tot_l:,.1f} L", "#2563EB")
            kpi_card(km2, "💰", "Valor Total",        f"R$ {tot_r:,.2f}", "#DC2626")
            st.markdown("<br>", unsafe_allow_html=True)

            cols_show = [c for c in ["data","tanque_origem","caminhao_tanque","motorista",
                                     "produto","quantidade","valor_unitario","total","obra","status"]
                         if c in df_tr_fil.columns]
            st.dataframe(df_tr_fil[cols_show], use_container_width=True, hide_index=True)

            xl_tr = gerar_excel_limpo(df_tr_fil[cols_show], "Transferências")
            st.download_button("📥 Exportar Excel", xl_tr,
                               f"Transferencias_{fh_di}_{fh_df}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# ═══════════════════════════════════════════════════════════════════
# 5 · TANQUES / ESTOQUE
# ═══════════════════════════════════════════════════════════════════
elif menu == "🛢️ Tanques / Estoque":
    st.markdown("## 🛢️ Gestão de Tanques e Comboios")

    df_t     = get_data("tanques")
    df_f     = get_data("fornecedores")
    df_ent   = get_data("entradas_tanque")
    df_sai   = get_data("abastecimentos")
    df_transf= get_data("transferencias_tanque")
    saldos   = calcular_todos_saldos()

    if not df_sai.empty and "status" in df_sai.columns:
        df_sai = df_sai[df_sai["status"] == "ATIVO"]
    if not df_transf.empty and "status" in df_transf.columns:
        df_transf = df_transf[df_transf["status"] == "ATIVO"]

    # ── Painel de saldo em tempo real ────────────────────────────
    if not df_t.empty:
        st.markdown("### 📊 Situação Atual dos Tanques")
        cols_t = st.columns(min(len(df_t), 5))
        for i, (_, row) in enumerate(df_t.iterrows()):
            nm  = row.get("nome","")
            cap = to_float(row.get("capacidade"))
            sd  = saldos.get(nm, 0.0)
            with cols_t[i % len(cols_t)]:
                tank_gauge(st.container(), nm, sd, cap)
                if cap > 0:
                    limite_low = cap * 0.15
                    if sd <= limite_low:
                        st.markdown(f"<div class='bk-lo'>⚠️ Nível crítico! Abastecer o tanque.</div>",
                                    unsafe_allow_html=True)

    st.divider()

    # ── Abas de operações ─────────────────────────────────────────
    aba_ent, aba_hist, aba_cad = st.tabs([
        "📥 Registrar Entrada (Compra)",
        "📋 Histórico de Movimentação",
        "⚙️ Cadastrar / Gerenciar Tanques"
    ])

    with aba_ent:
        st.markdown("#### Registrar Entrada de Combustível no Tanque")
        if df_t.empty:
            banner("⚠️ Cadastre um tanque primeiro na aba ⚙️.", "lo")
        else:
            with st.form("f_ent_tanq", clear_on_submit=True):
                e1, e2, e3 = st.columns(3)
                data_e  = e1.date_input("Data da Entrega")
                ficha_e = e2.text_input("NF / Documento Fiscal")
                tanq_e  = e3.selectbox("Tanque de Destino", df_t["nome"].tolist())

                e4, e5, e6 = st.columns(3)
                forn_e = e4.selectbox("Distribuidora / Fornecedor",
                                      df_f["nome"].tolist() if not df_f.empty else ["Sem cadastro"])
                comb_e = e5.selectbox("Produto", ["Diesel S10","Diesel S500","Gasolina Comum"])
                obs_e  = e6.text_input("Observação")

                e7, e8 = st.columns(2)
                qtd_e  = e7.number_input("Quantidade (L)", min_value=0.0, step=100.0)
                vunt_e = e8.number_input("Valor Unitário (R$/L)", min_value=0.0, step=0.001, format="%.3f")
                total_e = qtd_e * vunt_e

                obras_e = lista_obras()
                obra_e  = st.selectbox("Obra / Centro de Custo", obras_e) if obras_e else st.text_input("Obra")

                sd_atual = saldos.get(tanq_e, 0.0)
                st.markdown(f"<div class='bk-in'>💰 Valor total: <strong>R$ {total_e:,.2f}</strong> "
                            f"| Saldo atual de <strong>{tanq_e}</strong>: <strong>{sd_atual:,.1f} L</strong> → "
                            f"Após entrada: <strong>{sd_atual + qtd_e:,.1f} L</strong></div>",
                            unsafe_allow_html=True)

                if st.form_submit_button("💾 REGISTRAR ENTRADA NO TANQUE", use_container_width=True):
                    if qtd_e <= 0:
                        st.error("⚠️ Informe a quantidade.")
                    else:
                        ok = insert_data("entradas_tanque", {
                            "data":           str(data_e),
                            "numero_ficha":   ficha_e,
                            "nome_tanque":    tanq_e,
                            "fornecedor":     forn_e,
                            "combustivel":    comb_e,
                            "quantidade":     qtd_e,
                            "valor_unitario": vunt_e,
                            "total":          round(total_e, 2),
                            "obra":           obra_e,
                            "observacao":     obs_e,
                            "criado_por":     st.session_state.usuario_logado,
                        })
                        if ok:
                            st.success(f"✅ Entrada registrada! Novo saldo de {tanq_e}: "
                                       f"{sd_atual + qtd_e:,.1f} L")
                            st.rerun()

    with aba_hist:
        st.markdown("#### Histórico de Movimentação do Tanque")
        if df_t.empty:
            st.info("Nenhum tanque cadastrado.")
        else:
            hc1, hc2, hc3 = st.columns(3)
            tanq_sel = hc1.selectbox("Tanque", df_t["nome"].tolist(), key="hist_tanq")
            h_di = hc2.date_input("De",  value=date.today().replace(day=1), key="h_di_t")
            h_df = hc3.date_input("Até", value=date.today(),                key="h_df_t")

            def fil_dt(df, col="data"):
                if df.empty: return df
                df = df.copy()
                df["_dt"] = pd.to_datetime(df.get(col,""), errors="coerce").dt.date
                return df[df["_dt"].notna() & (df["_dt"] >= h_di) & (df["_dt"] <= h_df)]

            ent_h   = fil_dt(df_ent[df_ent.get("nome_tanque","") == tanq_sel]) if not df_ent.empty and "nome_tanque" in df_ent.columns else pd.DataFrame()
            sai_h   = fil_dt(df_sai[(df_sai.get("origem","") == "Tanque Interno") & (df_sai.get("nome_tanque","") == tanq_sel)]) if not df_sai.empty and "nome_tanque" in df_sai.columns else pd.DataFrame()
            transf_h= fil_dt(df_transf[df_transf.get("tanque_origem","") == tanq_sel]) if not df_transf.empty and "tanque_origem" in df_transf.columns else pd.DataFrame()

            t_ent  = pd.to_numeric(ent_h.get("quantidade",   pd.Series(dtype=float)), errors="coerce").sum()
            t_sai  = pd.to_numeric(sai_h.get("quantidade",   pd.Series(dtype=float)), errors="coerce").sum()
            t_tr   = pd.to_numeric(transf_h.get("quantidade",pd.Series(dtype=float)), errors="coerce").sum()
            t_val_ent = pd.to_numeric(ent_h.get("total",     pd.Series(dtype=float)), errors="coerce").sum()

            km1, km2, km3, km4 = st.columns(4)
            kpi_card(km1, "📥", "Entradas no Período",    f"{t_ent:,.1f} L",    "#059669")
            kpi_card(km2, "📤", "Saídas Diretas",         f"{t_sai:,.1f} L",    "#DC2626")
            kpi_card(km3, "🚛", "Transf. Caminhão",       f"{t_tr:,.1f} L",     "#D97706")
            kpi_card(km4, "⛽", "Saldo no Período",       f"{t_ent-t_sai-t_tr:,.1f} L", "#2563EB")

            st.markdown("<br>", unsafe_allow_html=True)
            if t_ent > 0 or t_sai > 0 or t_tr > 0:
                xl_t = gerar_excel_tanque_movimentos(ent_h, sai_h, transf_h, tanq_sel,
                                                     f"{h_di.strftime('%d/%m/%Y')} a {h_df.strftime('%d/%m/%Y')}")
                st.download_button("📥 Baixar Movimentação Excel", xl_t,
                                   f"Tanque_{tanq_sel}_{h_di}.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                st.info("Nenhum movimento no período selecionado.")

    with aba_cad:
        st.markdown("#### Cadastrar Novo Tanque")
        with st.form("f_cad_tanq", clear_on_submit=True):
            c1, c2 = st.columns(2)
            nm_t = c1.text_input("Nome / Identificação do Tanque")
            cap  = c2.number_input("Capacidade Máxima (L)", min_value=0.0, step=500.0)
            if st.form_submit_button("💾 Salvar Tanque", use_container_width=True):
                if nm_t:
                    if insert_data("tanques", {"nome": nm_t.upper(), "capacidade": cap,
                                               "criado_por": st.session_state.usuario_logado}):
                        st.success("✅ Tanque salvo!")
                        st.rerun()
                else:
                    st.error("⚠️ Nome obrigatório.")

        if not df_t.empty:
            st.divider()
            st.subheader("Tanques Cadastrados")
            for _, r in df_t.iterrows():
                cc1, cc2 = st.columns([5,1])
                sd = saldos.get(r.get("nome",""), 0.0)
                cap = to_float(r.get("capacidade"))
                pct = f"({sd/cap*100:.0f}%)" if cap > 0 else ""
                cc1.write(f"**{r['nome']}** — Cap: {cap:,.0f} L | Saldo: {sd:,.1f} L {pct}")
                if cc2.button("❌", key=f"d_t_{r['id']}"):
                    if delete_data("tanques", r["id"]):
                        st.rerun()


# ═══════════════════════════════════════════════════════════════════
# 6 · BOLETIM DE TRANSPORTE
# ═══════════════════════════════════════════════════════════════════
elif menu == "🚚 Boletim de Transporte":
    st.markdown("## 🚚 Boletim Diário de Produção")
    df_v = get_data("veiculos")
    if df_v.empty:
        banner("⚠️ Cadastre veículos em 🚜 Frota e Equipamentos primeiro.", "lo")
        st.stop()

    obras_lista = lista_obras()

    with st.form("f_prod", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        dt_p = c1.date_input("Data do Boletim", value=date.today())
        pref = c2.selectbox("Veículo / Equipamento", df_v["prefixo"].tolist())
        v_info = df_v[df_v["prefixo"] == pref].iloc[0]
        mot  = c3.text_input("Motorista / Operador", value=v_info.get("motorista",""))

        c4, c5, c6 = st.columns(3)
        if obras_lista:
            obra_bol = c4.selectbox("Obra / Projeto", obras_lista)
        else:
            obra_bol = c4.text_input("Obra / Projeto")
        orig_rota = c5.text_input("Origem / Jazida")
        dest_rota = c6.text_input("Destino / Trecho")

        c7, c8, c9, c10 = st.columns(4)
        op_tipo  = c7.selectbox("Tipo de Operação", [
            "Transporte de Massa/CBUQ","Transporte de Fresado",
            "Terraplanagem","Venda de Massa","Ocioso/Manutenção"
        ])
        km_s     = c8.number_input("KM Inicial", min_value=0.0)
        km_c     = c9.number_input("KM Final",   min_value=0.0)
        carradas = c10.number_input("Nº Viagens", min_value=0, step=1)

        c11, c12 = st.columns(2)
        ton   = c11.number_input("Total Toneladas", min_value=0.0)
        obs_p = c12.text_input("Observações")

        if st.form_submit_button("💾 SALVAR BOLETIM", use_container_width=True):
            if op_tipo != "Ocioso/Manutenção" and carradas <= 0:
                st.error("⚠️ Informe o número de viagens.")
            else:
                if insert_data("producao", {
                    "data": str(dt_p), "prefixo": pref,
                    "motorista": mot.upper(), "obra": obra_bol,
                    "tipo_operacao": op_tipo, "origem": orig_rota.upper(),
                    "destino": dest_rota.upper(), "km_saida": km_s,
                    "km_chegada": km_c, "carradas": carradas, "toneladas": ton,
                    "observacao": obs_p, "criado_por": st.session_state.usuario_logado,
                }):
                    st.success("✅ Boletim salvo!")
                    st.rerun()

    df_bol = get_data("producao")
    if not df_bol.empty:
        st.divider()
        st.subheader("📋 Boletins Recentes")
        df_br = df_bol.sort_values("data", ascending=False).head(30).fillna("")
        cols_b = [c for c in ["data","prefixo","motorista","obra","tipo_operacao",
                               "origem","destino","carradas","toneladas","km_saida","km_chegada"]
                  if c in df_br.columns]
        st.dataframe(df_br[cols_b], use_container_width=True, hide_index=True)

        xl_b = gerar_excel_limpo(df_br[cols_b], "Boletins")
        st.download_button("📥 Exportar Excel", xl_b, f"Boletins_{date.today()}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# ═══════════════════════════════════════════════════════════════════
# 7 · FROTA E EQUIPAMENTOS
# ═══════════════════════════════════════════════════════════════════
elif menu == "🚜 Frota e Equipamentos":
    st.markdown("## 🚜 Gestão de Frota")
    df_v  = get_data("veiculos")
    df_ab = get_data("abastecimentos")
    if not df_ab.empty and "status" in df_ab.columns:
        df_ab = df_ab[df_ab["status"] == "ATIVO"]

    with st.expander("➕ CADASTRAR NOVO VEÍCULO / EQUIPAMENTO", expanded=True):
        with st.form("f_v", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            pref      = c1.text_input("Código / Prefixo (Ex: CA-01)")
            plc       = c2.text_input("Placa")
            categoria = c3.selectbox("Categoria", ["Veículo","Equipamento"])
            c4, c5, c6 = st.columns(3)
            mot       = c4.text_input("Motorista / Operador Fixo")
            comb      = c5.selectbox("Combustível Padrão", ["Diesel S10","Diesel S500","Gasolina Comum"])
            tipo_v    = c6.selectbox("Tipo", ["Veículo","Equipamento","Caminhão-Tanque"])

            if st.form_submit_button("💾 Salvar", use_container_width=True):
                if pref:
                    if insert_data("veiculos", {
                        "prefixo": pref.upper(), "placa": plc.upper(),
                        "categoria": categoria, "motorista": mot.upper(),
                        "tipo_combustivel_padrao": comb, "tipo_veiculo": tipo_v,
                    }):
                        st.success("✅ Salvo!")
                        st.rerun()
                else:
                    st.error("⚠️ Prefixo obrigatório.")

    if not df_v.empty:
        st.divider()
        tab_veic, tab_ct = st.tabs(["🚜 Veículos e Equipamentos","🚛 Caminhões-Tanque"])

        for tab, filtro in [(tab_veic, lambda df: df[df.get("tipo_veiculo", pd.Series(dtype=str)) != "Caminhão-Tanque"] if "tipo_veiculo" in df.columns else df),
                            (tab_ct,   lambda df: df[df.get("tipo_veiculo", pd.Series(dtype=str)) == "Caminhão-Tanque"] if "tipo_veiculo" in df.columns else pd.DataFrame())]:
            with tab:
                df_fil = filtro(df_v)
                if df_fil.empty:
                    st.info("Nenhum registro.")
                else:
                    for _, r in df_fil.iterrows():
                        # Consumo do veículo
                        cons_v = 0.0
                        if not df_ab.empty and "prefixo" in df_ab.columns:
                            cons_v = pd.to_numeric(
                                df_ab[df_ab["prefixo"] == r.get("prefixo","")].get("quantidade",0),
                                errors="coerce"
                            ).sum()

                        cc1, cc2, cc3 = st.columns([4, 1, 1])
                        cc1.markdown(
                            f"**{r.get('prefixo','')}** | {r.get('tipo_veiculo', r.get('categoria','-'))} "
                            f"| Placa: {r.get('placa','')} | Op: {r.get('motorista','')} "
                            f"| 🔥 {cons_v:,.0f} L consumidos"
                        )
                        if cc2.button("✏️", key=f"edit_v_{r.get('id','x')}"):
                            st.session_state[f"edit_v_{r.get('id')}"] = True
                        if cc3.button("❌", key=f"d_v_{r.get('id','x')}"):
                            if delete_data("veiculos", r.get("id")):
                                st.rerun()


# ═══════════════════════════════════════════════════════════════════
# 8 · OBRAS
# ═══════════════════════════════════════════════════════════════════
elif menu == "🏗️ Obras":
    st.markdown("## 🏗️ Gestão de Obras e Projetos")
    banner("Obras cadastradas aqui ficam disponíveis em todos os módulos (abastecimentos, transferências e boletins).", "in")

    df_o  = get_data("obras")
    df_ab = get_data("abastecimentos")
    if not df_ab.empty and "status" in df_ab.columns:
        df_ab = df_ab[df_ab["status"] == "ATIVO"]

    with st.expander("➕ CADASTRAR NOVA OBRA", expanded=True):
        with st.form("f_obra", clear_on_submit=True):
            co1, co2, co3 = st.columns(3)
            nome_obra   = co1.text_input("Nome da Obra / Projeto")
            codigo_obra = co2.text_input("Código / ART")
            status_obra = co3.selectbox("Status", ["Ativa","Pausada","Encerrada"])
            co4, co5 = st.columns(2)
            local_obra = co4.text_input("Município / Localização")
            resp_obra  = co5.text_input("Responsável Técnico")
            obs_obra   = st.text_input("Observações")
            if st.form_submit_button("💾 Salvar Obra", use_container_width=True):
                if nome_obra:
                    if insert_data("obras", {
                        "nome": nome_obra.upper(), "codigo": codigo_obra.upper(),
                        "status": status_obra, "local": local_obra.upper(),
                        "responsavel": resp_obra.upper(), "observacao": obs_obra,
                        "criado_por": st.session_state.usuario_logado,
                    }):
                        st.success("✅ Obra salva!")
                        st.rerun()
                else:
                    st.error("⚠️ Nome obrigatório.")

    if not df_o.empty:
        st.divider()
        st.subheader("📋 Obras Cadastradas")
        for _, r in df_o.iterrows():
            nome_o   = r.get("nome","")
            status_o = r.get("status","Ativa")
            ic = {"Ativa":"🟢","Pausada":"🟡","Encerrada":"🔴"}.get(status_o,"⚪")

            with st.expander(f"{ic} {nome_o} | {r.get('codigo','')} | {status_o}"):
                oc1, oc2, oc3 = st.columns(3)
                oc1.write(f"**Local:** {r.get('local','-')}")
                oc2.write(f"**Responsável:** {r.get('responsavel','-')}")
                oc3.write(f"**Obs:** {r.get('observacao','-')}")

                # KPIs da obra
                if not df_ab.empty and "obra" in df_ab.columns:
                    df_obra_ab = df_ab[df_ab["obra"] == nome_o]
                    total_l = pd.to_numeric(df_obra_ab.get("quantidade",0), errors="coerce").sum()
                    total_r = pd.to_numeric(df_obra_ab.get("total",0),      errors="coerce").sum()
                    ok1, ok2, ok3 = st.columns(3)
                    kpi_card(ok1,"⛽","Litros consumidos",f"{total_l:,.1f} L","#2563EB")
                    kpi_card(ok2,"💰","Gasto total",      f"R$ {total_r:,.2f}","#DC2626")
                    kpi_card(ok3,"📋","Nº abastecimentos",str(len(df_obra_ab)),"#059669")
                    st.markdown("<br>", unsafe_allow_html=True)

                col_s, col_d = st.columns(2)
                novo_st = col_s.selectbox("Status", ["Ativa","Pausada","Encerrada"],
                                           index=["Ativa","Pausada","Encerrada"].index(status_o)
                                           if status_o in ["Ativa","Pausada","Encerrada"] else 0,
                                           key=f"st_o_{r['id']}")
                if col_s.button("💾 Atualizar", key=f"upd_o_{r['id']}"):
                    if update_data("obras", r["id"], {"status": novo_st}):
                        st.success("Atualizado!")
                        st.rerun()
                if col_d.button("❌ Excluir", key=f"del_o_{r['id']}"):
                    if delete_data("obras", r["id"]):
                        st.rerun()


# ═══════════════════════════════════════════════════════════════════
# 9 · FORNECEDORES
# ═══════════════════════════════════════════════════════════════════
elif menu == "🏪 Fornecedores":
    st.markdown("## 🏪 Postos e Distribuidoras")
    df_f  = get_data("fornecedores")
    df_ab = get_data("abastecimentos")
    df_et = get_data("entradas_tanque")
    if not df_ab.empty and "status" in df_ab.columns:
        df_ab = df_ab[df_ab["status"] == "ATIVO"]

    with st.expander("➕ CADASTRAR NOVO FORNECEDOR", expanded=True):
        with st.form("f_f", clear_on_submit=True):
            c1, c2 = st.columns(2)
            nm = c1.text_input("Nome Fantasia (aparece no app)")
            rz = c2.text_input("Razão Social")
            c3, c4 = st.columns(2)
            cnpj = c3.text_input("CNPJ")
            tel  = c4.text_input("Telefone / Contato")
            st.markdown("**Dados Bancários**")
            c5, c6, c7 = st.columns(3)
            banco = c5.text_input("Banco")
            ag    = c6.text_input("Agência")
            cta   = c7.text_input("Conta")
            c8, c9 = st.columns(2)
            pix   = c8.text_input("Chave PIX")
            tipo_c = c9.selectbox("Tipo de Conta", ["Corrente","Poupança","Outros"])

            if st.form_submit_button("💾 Salvar Fornecedor", use_container_width=True):
                if nm:
                    if insert_data("fornecedores", {
                        "nome": nm, "razao_social": rz, "cnpj": cnpj, "telefone": tel,
                        "banco": banco, "agencia": ag, "conta": cta, "pix": pix,
                        "tipo_conta": tipo_c, "criado_por": st.session_state.usuario_logado,
                    }):
                        st.success("✅ Fornecedor salvo!")
                        st.rerun()
                else:
                    st.error("⚠️ Nome fantasia obrigatório.")

    if not df_f.empty:
        st.divider()
        for _, r in df_f.iterrows():
            nome_f = r.get("nome","")
            # Volume total fornecido
            vol_posto = vol_tanque = 0.0
            if not df_ab.empty and "fornecedor" in df_ab.columns:
                vol_posto = pd.to_numeric(
                    df_ab[df_ab["fornecedor"] == nome_f].get("total",0), errors="coerce"
                ).sum()
            if not df_et.empty and "fornecedor" in df_et.columns:
                vol_tanque = pd.to_numeric(
                    df_et[df_et["fornecedor"] == nome_f].get("total",0), errors="coerce"
                ).sum()
            total_pago = vol_posto + vol_tanque

            with st.expander(f"🏪 {nome_f} | CNPJ: {r.get('cnpj','-')} | 💰 R$ {total_pago:,.2f} acumulado"):
                fc1, fc2, fc3 = st.columns(3)
                fc1.write(f"**Razão Social:** {r.get('razao_social','-')}")
                fc2.write(f"**Banco:** {r.get('banco','-')} — Ag: {r.get('agencia','-')} — Cta: {r.get('conta','-')}")
                fc3.write(f"**PIX:** {r.get('pix','-')} | **Tipo:** {r.get('tipo_conta','-')}")
                if st.button("❌ Excluir", key=f"del_f_{r['id']}"):
                    if delete_data("fornecedores", r["id"]):
                        st.rerun()


# ═══════════════════════════════════════════════════════════════════
# 10 · RELATÓRIOS E FECHAMENTOS
# ═══════════════════════════════════════════════════════════════════
elif menu == "📋 Relatórios e Fechamentos":
    st.markdown("## 📋 Relatórios e Fechamentos")

    aba1, aba2, aba3, aba4 = st.tabs([
        "📄 Abastecimentos por Fornecedor",
        "🛢️ Fechamento de Tanques",
        "🚚 Produção",
        "🔗 Rastreabilidade por Obra"
    ])

    # ── ABA 1: por Fornecedor ─────────────────────────────────────
    with aba1:
        st.markdown("#### Relatório de Abastecimentos — por Fornecedor")
        df_ab_r = get_data("abastecimentos")
        df_f_r  = get_data("fornecedores")
        if not df_ab_r.empty and "status" in df_ab_r.columns:
            df_ab_r = df_ab_r[df_ab_r["status"] == "ATIVO"]

        r1, r2, r3, r4 = st.columns(4)
        dt_i = r1.date_input("De",   value=date.today().replace(day=1), key="r1_di")
        dt_f = r2.date_input("Até",  value=date.today(),                key="r1_df")
        forn_list = ["TODOS"] + (df_f_r["nome"].tolist() if not df_f_r.empty else [])
        forn_sel  = r3.selectbox("Fornecedor", forn_list, key="r1_forn")
        obra_sel_r = r4.selectbox("Obra", lista_obras(incluir_todas=True), key="r1_obra")

        if st.button("🔍 Gerar Relatório", key="btn_r1"):
            df_fil = df_ab_r.copy() if not df_ab_r.empty else pd.DataFrame()
            if not df_fil.empty and "data" in df_fil.columns:
                df_fil["data_dt"] = pd.to_datetime(df_fil["data"], errors="coerce").dt.date
                df_fil = df_fil[(df_fil["data_dt"] >= dt_i) & (df_fil["data_dt"] <= dt_f)]
                if forn_sel != "TODOS" and "fornecedor" in df_fil.columns:
                    df_fil = df_fil[df_fil["fornecedor"] == forn_sel]
                if obra_sel_r != "TODAS" and "obra" in df_fil.columns:
                    df_fil = df_fil[df_fil["obra"] == obra_sel_r]

            if df_fil.empty:
                st.warning("Nenhum registro no período/filtro.")
            else:
                tot_l = pd.to_numeric(df_fil.get("quantidade",0), errors="coerce").sum()
                tot_r = pd.to_numeric(df_fil.get("total",0),      errors="coerce").sum()
                m1, m2, m3 = st.columns(3)
                kpi_card(m1,"⛽","Total Litros",f"{tot_l:,.1f} L","#2563EB")
                kpi_card(m2,"💰","Total R$",    f"R$ {tot_r:,.2f}","#DC2626")
                kpi_card(m3,"📋","Registros",   str(len(df_fil)),"#059669")
                st.markdown("<br>", unsafe_allow_html=True)

                per_str = f"{dt_i.strftime('%d/%m/%Y')} a {dt_f.strftime('%d/%m/%Y')}"
                xl = gerar_excel_abastecimentos(
                    df_fil,
                    f"RELATÓRIO — {forn_sel.upper() if forn_sel != 'TODOS' else 'GERAL'}",
                    per_str
                )
                st.download_button("📥 Baixar Excel", xl,
                                   f"Relatorio_{forn_sel}_{dt_i}.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                   use_container_width=True)

                cols_show = [c for c in ["data","prefixo","placa","motorista","fornecedor",
                                         "tipo_combustivel","quantidade","valor_unitario","total","obra","observacao"]
                             if c in df_fil.columns]
                st.dataframe(df_fil[cols_show], use_container_width=True, hide_index=True)

    # ── ABA 2: Fechamento de Tanques ─────────────────────────────
    with aba2:
        st.markdown("#### Fechamento Físico de Tanques")
        df_ent_r  = get_data("entradas_tanque")
        df_t_r    = get_data("tanques")
        df_ab2    = get_data("abastecimentos")
        df_tr2    = get_data("transferencias_tanque")
        if not df_ab2.empty and "status" in df_ab2.columns:
            df_ab2 = df_ab2[df_ab2["status"] == "ATIVO"]
        if not df_tr2.empty and "status" in df_tr2.columns:
            df_tr2 = df_tr2[df_tr2["status"] == "ATIVO"]

        c1, c2, c3 = st.columns(3)
        di_t  = c1.date_input("De",  value=date.today().replace(day=1), key="t2_di")
        df_tq = c2.date_input("Até", value=date.today(),                key="t2_df")
        tanq_sel2 = c3.selectbox("Tanque", df_t_r["nome"].tolist() if not df_t_r.empty else ["—"])

        if st.button("🔍 Gerar Fechamento"):
            def fil_t2(df, col_tanq, val):
                if df.empty or col_tanq not in df.columns: return pd.DataFrame()
                df = df[df[col_tanq] == val].copy()
                df["_dt"] = pd.to_datetime(df.get("data",""), errors="coerce").dt.date
                return df[df["_dt"].notna() & (df["_dt"] >= di_t) & (df["_dt"] <= df_tq)]

            ent_f2   = fil_t2(df_ent_r, "nome_tanque", tanq_sel2)
            sai_f2   = fil_t2(df_ab2[(df_ab2.get("origem","") == "Tanque Interno")] if not df_ab2.empty and "origem" in df_ab2.columns else pd.DataFrame(), "nome_tanque", tanq_sel2)
            transf_f2= fil_t2(df_tr2, "tanque_origem", tanq_sel2)

            te = pd.to_numeric(ent_f2.get("quantidade",   pd.Series(dtype=float)), errors="coerce").sum()
            ts = pd.to_numeric(sai_f2.get("quantidade",   pd.Series(dtype=float)), errors="coerce").sum()
            tt = pd.to_numeric(transf_f2.get("quantidade",pd.Series(dtype=float)), errors="coerce").sum()
            tv = pd.to_numeric(ent_f2.get("total",        pd.Series(dtype=float)), errors="coerce").sum()

            m1, m2, m3, m4 = st.columns(4)
            kpi_card(m1,"📥","Entradas",       f"{te:,.1f} L", "#059669")
            kpi_card(m2,"📤","Saídas Diretas", f"{ts:,.1f} L", "#DC2626")
            kpi_card(m3,"🚛","Transf. Caminhão",f"{tt:,.1f} L","#D97706")
            kpi_card(m4,"⛽","Saldo do Período",f"{te-ts-tt:,.1f} L","#2563EB")
            st.markdown("<br>", unsafe_allow_html=True)

            if te > 0 or ts > 0 or tt > 0:
                xl_t2 = gerar_excel_tanque_movimentos(ent_f2, sai_f2, transf_f2, tanq_sel2,
                                                      f"{di_t.strftime('%d/%m/%Y')} a {df_tq.strftime('%d/%m/%Y')}")
                st.download_button("📥 Baixar Excel", xl_t2,
                                   f"Fechamento_{tanq_sel2}_{di_t}.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                st.info("Nenhum movimento no período.")

    # ── ABA 3: Produção ──────────────────────────────────────────
    with aba3:
        st.markdown("#### Boletins de Produção")
        df_prod = get_data("producao")
        p1, p2 = st.columns(2)
        d1 = p1.date_input("De",  value=date.today().replace(day=1), key="p3_di")
        d2 = p2.date_input("Até", value=date.today(),                key="p3_df")
        if st.button("📊 Extrair"):
            if not df_prod.empty and "data" in df_prod.columns:
                df_prod["_dt"] = pd.to_datetime(df_prod["data"], errors="coerce").dt.date
                df_pf = df_prod[(df_prod["_dt"] >= d1) & (df_prod["_dt"] <= d2)]
                if not df_pf.empty:
                    tot_ton  = pd.to_numeric(df_pf.get("toneladas",0), errors="coerce").sum()
                    tot_viag = int(pd.to_numeric(df_pf.get("carradas",0), errors="coerce").sum())
                    m1, m2 = st.columns(2)
                    kpi_card(m1,"🏗️","Toneladas",str(f"{tot_ton:,.1f} t"),"#059669")
                    kpi_card(m2,"🚚","Viagens",   str(tot_viag),"#2563EB")
                    st.markdown("<br>", unsafe_allow_html=True)
                    xl_p = gerar_excel_limpo(df_pf.drop(columns=["_dt"], errors="ignore"), "Producao")
                    st.download_button("📥 Baixar Excel", xl_p, f"Producao_{d1}_{d2}.xlsx",
                                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                    st.dataframe(df_pf.drop(columns=["_dt"], errors="ignore"),
                                 use_container_width=True, hide_index=True)
                else:
                    st.info("Nenhum boletim no período.")

    # ── ABA 4: Rastreabilidade por Obra ──────────────────────────
    with aba4:
        st.markdown("#### 🔗 Rastreabilidade Completa por Obra")
        banner("Veja o fluxo completo: <strong>Compra → Tanque → Caminhão → Veículo → Obra</strong>", "in")

        obras_r = lista_obras()
        if not obras_r:
            st.warning("⚠️ Nenhuma obra cadastrada.")
        else:
            cr1, cr2, cr3 = st.columns(3)
            obra_rastr = cr1.selectbox("Obra", obras_r, key="rastr_obra")
            dr_i = cr2.date_input("De",  value=date.today().replace(day=1), key="rastr_di")
            dr_f = cr3.date_input("Até", value=date.today(),                key="rastr_df")

            if st.button("🔍 Gerar Rastreabilidade"):
                def get_rastr(table, col_obra, di, df):
                    data = get_data(table)
                    if data.empty or col_obra not in data.columns: return pd.DataFrame()
                    if "status" in data.columns: data = data[data["status"] == "ATIVO"]
                    data["_dt"] = pd.to_datetime(data.get("data",""), errors="coerce").dt.date
                    return data[(data[col_obra] == obra_rastr) &
                                (data["_dt"].notna()) &
                                (data["_dt"] >= di) & (data["_dt"] <= df)]

                df_ab_ra   = get_rastr("abastecimentos",        "obra", dr_i, dr_f)
                df_tr_ra   = get_rastr("transferencias_tanque", "obra", dr_i, dr_f)
                df_prod_ra = get_rastr("producao",              "obra", dr_i, dr_f)

                tot_l_ab = pd.to_numeric(df_ab_ra.get("quantidade",0), errors="coerce").sum()
                tot_r_ab = pd.to_numeric(df_ab_ra.get("total",0),      errors="coerce").sum()
                tot_l_tr = pd.to_numeric(df_tr_ra.get("quantidade",0), errors="coerce").sum()
                tot_r_tr = pd.to_numeric(df_tr_ra.get("total",0),      errors="coerce").sum()
                tot_ton  = pd.to_numeric(df_prod_ra.get("toneladas",0),errors="coerce").sum()
                tot_viag = int(pd.to_numeric(df_prod_ra.get("carradas",0),errors="coerce").sum())

                st.markdown(f"### 📊 Resumo — {obra_rastr}")
                k1, k2, k3, k4 = st.columns(4)
                kpi_card(k1,"⛽","Total Litros",f"{tot_l_ab+tot_l_tr:,.1f} L","#2563EB")
                kpi_card(k2,"💰","Gasto Total",  f"R$ {tot_r_ab+tot_r_tr:,.2f}","#DC2626")
                kpi_card(k3,"🏗️","Toneladas",   f"{tot_ton:,.1f} t","#059669")
                kpi_card(k4,"🚚","Viagens",      str(tot_viag),"#7C3AED")
                st.markdown("<br>", unsafe_allow_html=True)

                if not df_ab_ra.empty:
                    st.markdown("##### ⛽ Abastecimentos")
                    cols_ab = [c for c in ["data","prefixo","placa","motorista","fornecedor",
                                           "tipo_combustivel","quantidade","valor_unitario","total","origem"]
                               if c in df_ab_ra.columns]
                    st.dataframe(df_ab_ra[cols_ab], use_container_width=True, hide_index=True)

                if not df_tr_ra.empty:
                    st.markdown("##### 🚛 Transferências via Caminhão-Tanque")
                    cols_tr = [c for c in ["data","tanque_origem","caminhao_tanque","motorista",
                                           "produto","quantidade","valor_unitario","total"]
                               if c in df_tr_ra.columns]
                    st.dataframe(df_tr_ra[cols_tr], use_container_width=True, hide_index=True)

                if not df_prod_ra.empty:
                    st.markdown("##### 🚚 Boletins de Produção")
                    cols_pr = [c for c in ["data","prefixo","motorista","tipo_operacao",
                                           "origem","destino","carradas","toneladas"]
                               if c in df_prod_ra.columns]
                    st.dataframe(df_prod_ra[cols_pr], use_container_width=True, hide_index=True)

                # Exportar
                buf_r = io.BytesIO()
                with pd.ExcelWriter(buf_r, engine="xlsxwriter") as wr:
                    if not df_ab_ra.empty:
                        df_ab_ra.drop(columns=["_dt"], errors="ignore").to_excel(wr, index=False, sheet_name="Abastecimentos")
                    if not df_tr_ra.empty:
                        df_tr_ra.drop(columns=["_dt"], errors="ignore").to_excel(wr, index=False, sheet_name="Transferencias")
                    if not df_prod_ra.empty:
                        df_prod_ra.drop(columns=["_dt"], errors="ignore").to_excel(wr, index=False, sheet_name="Producao")
                st.download_button("📥 Exportar Rastreabilidade Completa",
                                   buf_r.getvalue(),
                                   f"Rastreabilidade_{obra_rastr}_{dr_i}_{dr_f}.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                   use_container_width=True)


# ═══════════════════════════════════════════════════════════════════
# 11 · USUÁRIOS E ACESSOS
# ═══════════════════════════════════════════════════════════════════
elif menu == "👥 Usuários e Acessos":
    if st.session_state.perfil_logado != "Admin":
        st.error("⛔ Acesso restrito a administradores.")
        st.stop()

    st.markdown("## 👥 Gestão de Usuários e Acessos")
    banner("Senhas são armazenadas com hash SHA-256. Novos usuários já recebem senha protegida.", "in")

    with st.form("f_usr", clear_on_submit=True):
        c1, c2 = st.columns(2)
        nm_u = c1.text_input("Nome Completo")
        lg_u = c2.text_input("Login")
        c3, c4 = st.columns(2)
        sn_u = c3.text_input("Senha", type="password")
        pf_u = c4.selectbox("Perfil", ["Operador","Admin"])
        if st.form_submit_button("💾 Criar Usuário", use_container_width=True):
            if nm_u and lg_u and sn_u:
                if insert_data("usuarios", {
                    "nome": nm_u, "login": lg_u,
                    "senha": hash_senha(sn_u),
                    "perfil": pf_u
                }):
                    st.success("✅ Usuário criado!")
                    st.rerun()
            else:
                st.error("⚠️ Preencha todos os campos.")

    df_u = get_data("usuarios")
    if not df_u.empty:
        st.divider()
        st.subheader("Usuários Cadastrados")
        for _, r in df_u.iterrows():
            cc1, cc2, cc3 = st.columns([4, 1, 1])
            cc1.write(f"**{r.get('nome','')}** ({r.get('login','')}) — Nível: {r.get('perfil','')}")
            if cc2.button("🔑 Reset", key=f"rst_u_{r['id']}", help="Redefinir senha"):
                st.session_state[f"reset_u_{r['id']}"] = True
            if cc3.button("❌", key=f"del_u_{r['id']}"):
                if delete_data("usuarios", r["id"]):
                    st.rerun()

            if st.session_state.get(f"reset_u_{r['id']}"):
                with st.form(f"reset_form_{r['id']}"):
                    nova_senha = st.text_input("Nova Senha", type="password", key=f"ns_{r['id']}")
                    if st.form_submit_button("💾 Confirmar Reset"):
                        if nova_senha:
                            if update_data("usuarios", r["id"], {"senha": hash_senha(nova_senha)}):
                                st.success("Senha atualizada!")
                                st.session_state.pop(f"reset_u_{r['id']}", None)
                                st.rerun()
