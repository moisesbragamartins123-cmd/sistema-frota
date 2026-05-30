import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime, date
import plotly.express as px
import plotly.graph_objects as go
import os, io, hashlib, xlsxwriter, base64
from fpdf import FPDF

# ═══════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════
st.set_page_config(
    page_title="Sistema de Abastecimentos — Copa Engenharia",
    page_icon="🛣️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
}
.main { background: #F5F7FA; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #0F1C2E;
    border-right: 1px solid #1E3045;
}
[data-testid="stSidebar"] * { color: #8BA7C4 !important; }
[data-testid="stSidebar"] .stRadio label { font-size: 13px !important; font-weight: 500 !important; }

/* ── Labels ── */
.stTextInput > label, .stSelectbox > label,
.stNumberInput > label, .stDateInput > label, .stTextArea > label {
    font-size: 11px !important; color: #64748B !important;
    font-weight: 600 !important; text-transform: uppercase;
    letter-spacing: .07em; margin-bottom: 3px !important;
}

/* ── Inputs ── */
div[data-baseweb="input"], div[data-baseweb="select"] {
    border-radius: 5px !important;
    border: 1px solid #D1D9E0 !important;
    background: #FFFFFF !important;
}
div[data-baseweb="input"]:focus-within,
div[data-baseweb="select"]:focus-within {
    border-color: #1E40AF !important;
    box-shadow: 0 0 0 2px rgba(30,64,175,.12) !important;
}

/* ── Botão primário ── */
div.stButton > button:first-child {
    background: #1E3A5F !important; color: #fff !important;
    border: none !important; border-radius: 5px !important;
    font-weight: 600 !important; font-size: 12px !important;
    padding: .55rem 1.4rem !important; letter-spacing: .04em;
    text-transform: uppercase !important;
    transition: background .15s ease !important;
}
div.stButton > button:first-child:hover {
    background: #152E4D !important;
}

/* ── Formulários ── */
div[data-testid="stForm"] {
    border: none; border-radius: 8px; padding: 1.6rem;
    background: #FFFFFF; box-shadow: 0 1px 8px rgba(0,0,0,.06);
}

/* ── Alertas minimalistas ── */
.av-ok  { background:#F0FDF4; color:#166534; border-left:3px solid #22C55E; border-radius:4px; padding:9px 14px; font-size:12px; font-weight:500; margin:.5rem 0; }
.av-lo  { background:#FFFBEB; color:#92400E; border-left:3px solid #F59E0B; border-radius:4px; padding:9px 14px; font-size:12px; font-weight:500; margin:.5rem 0; }
.av-er  { background:#FEF2F2; color:#991B1B; border-left:3px solid #EF4444; border-radius:4px; padding:9px 14px; font-size:12px; font-weight:500; margin:.5rem 0; }
.av-in  { background:#EFF6FF; color:#1E40AF; border-left:3px solid #3B82F6; border-radius:4px; padding:9px 14px; font-size:12px; font-weight:500; margin:.5rem 0; }

/* ── KPI card ── */
.kp { background:#fff; border-radius:7px; padding:1rem 1.2rem;
      border:1px solid #E2E8F0; }
.kp-val { font-size:21px; font-weight:700; color:#0F172A;
          font-family:'IBM Plex Mono',monospace; margin:4px 0 2px; }
.kp-lbl { font-size:10px; font-weight:600; text-transform:uppercase;
          letter-spacing:.07em; color:#64748B; }
.kp-bar { height:3px; border-radius:2px; margin-top:8px; }

/* ── Tank card ── */
.tk { background:#fff; border-radius:7px; padding:.9rem 1.1rem;
      border:1px solid #E2E8F0; margin-bottom:.4rem; }
.tk-nome { font-size:11px; font-weight:700; text-transform:uppercase;
           letter-spacing:.06em; color:#64748B; }
.tk-val  { font-size:20px; font-weight:700; font-family:'IBM Plex Mono',monospace; }
.tk-g { color:#16A34A; } .tk-y { color:#D97706; } .tk-r { color:#DC2626; }

/* ── Divider limpo ── */
hr { border:none; border-top:1px solid #E2E8F0; margin:1.2rem 0; }

/* ── Page title ── */
h2 { color:#0F172A !important; font-weight:700 !important; font-size:20px !important; }
h3 { color:#1E3A5F !important; font-weight:600 !important; font-size:15px !important; }

/* ── Dataframe ── */
[data-testid="stDataFrame"] { border-radius:6px; overflow:hidden; }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════
# SUPABASE
# ═══════════════════════════════════════════════════════
@st.cache_resource
def get_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = get_supabase()

TABELAS_REQUERIDAS = [
    "usuarios", "veiculos", "fornecedores", "tanques",
    "entradas_tanque", "abastecimentos", "producao",
    "obras", "transferencias_tanque",
]

SQL_CRIAR_TABELAS = """
-- ══════════════════════════════════════════════════════════════
-- Sistema de Abastecimentos — Script de Setup
-- Execute no SQL Editor do Supabase (aba "SQL Editor")
-- É seguro rodar múltiplas vezes (IF NOT EXISTS / IF NOT EXISTS)
-- ══════════════════════════════════════════════════════════════

-- ── 1. NOVAS TABELAS ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.obras (
    id          BIGSERIAL PRIMARY KEY,
    nome        TEXT NOT NULL,
    codigo      TEXT DEFAULT '',
    status      TEXT DEFAULT 'Ativa',
    local       TEXT DEFAULT '',
    responsavel TEXT DEFAULT '',
    observacao  TEXT DEFAULT '',
    criado_por  TEXT DEFAULT '',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.transferencias_tanque (
    id              BIGSERIAL PRIMARY KEY,
    data            DATE,
    numero_ficha    TEXT DEFAULT '',
    tanque_origem   TEXT,
    caminhao_tanque TEXT DEFAULT '',
    placa           TEXT DEFAULT '',
    motorista       TEXT DEFAULT '',
    produto         TEXT DEFAULT 'Diesel S10',
    quantidade      NUMERIC DEFAULT 0,
    valor_unitario  NUMERIC DEFAULT 0,
    total           NUMERIC DEFAULT 0,
    obra            TEXT DEFAULT '',
    observacao      TEXT DEFAULT '',
    status          TEXT DEFAULT 'ATIVO',
    criado_por      TEXT DEFAULT '',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── 2. COLUNAS ADICIONAIS EM TABELAS EXISTENTES ──────────────
-- (ADD COLUMN IF NOT EXISTS não quebra se já existir)

ALTER TABLE public.veiculos
    ADD COLUMN IF NOT EXISTS tipo_veiculo           TEXT DEFAULT 'Veículo',
    ADD COLUMN IF NOT EXISTS tipo_combustivel_padrao TEXT DEFAULT 'Diesel S10',
    ADD COLUMN IF NOT EXISTS motorista              TEXT DEFAULT '',
    ADD COLUMN IF NOT EXISTS placa                  TEXT DEFAULT '',
    ADD COLUMN IF NOT EXISTS categoria              TEXT DEFAULT 'Veículo',
    ADD COLUMN IF NOT EXISTS criado_por             TEXT DEFAULT '';

ALTER TABLE public.abastecimentos
    ADD COLUMN IF NOT EXISTS origem      TEXT DEFAULT 'Posto Externo',
    ADD COLUMN IF NOT EXISTS nome_tanque TEXT DEFAULT '',
    ADD COLUMN IF NOT EXISTS status      TEXT DEFAULT 'ATIVO',
    ADD COLUMN IF NOT EXISTS criado_por  TEXT DEFAULT '',
    ADD COLUMN IF NOT EXISTS obra        TEXT DEFAULT '',
    ADD COLUMN IF NOT EXISTS horimetro   NUMERIC DEFAULT 0;

ALTER TABLE public.tanques
    ADD COLUMN IF NOT EXISTS capacidade NUMERIC DEFAULT 0,
    ADD COLUMN IF NOT EXISTS criado_por TEXT DEFAULT '';

ALTER TABLE public.entradas_tanque
    ADD COLUMN IF NOT EXISTS obra        TEXT DEFAULT '',
    ADD COLUMN IF NOT EXISTS criado_por  TEXT DEFAULT '';

ALTER TABLE public.producao
    ADD COLUMN IF NOT EXISTS tipo_operacao TEXT DEFAULT '',
    ADD COLUMN IF NOT EXISTS origem        TEXT DEFAULT '',
    ADD COLUMN IF NOT EXISTS destino       TEXT DEFAULT '',
    ADD COLUMN IF NOT EXISTS km_saida      NUMERIC DEFAULT 0,
    ADD COLUMN IF NOT EXISTS km_chegada    NUMERIC DEFAULT 0,
    ADD COLUMN IF NOT EXISTS carradas      INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS toneladas     NUMERIC DEFAULT 0,
    ADD COLUMN IF NOT EXISTS obra          TEXT DEFAULT '',
    ADD COLUMN IF NOT EXISTS criado_por    TEXT DEFAULT '';

-- ── 3. SEGURANÇA (Row Level Security) ────────────────────────

ALTER TABLE public.obras ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.transferencias_tanque ENABLE ROW LEVEL SECURITY;

-- Políticas permissivas (ajuste conforme sua autenticação)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='obras' AND policyname='Acesso total') THEN
        CREATE POLICY "Acesso total" ON public.obras FOR ALL USING (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='transferencias_tanque' AND policyname='Acesso total') THEN
        CREATE POLICY "Acesso total" ON public.transferencias_tanque FOR ALL USING (true);
    END IF;
END $$;
"""


# ═══════════════════════════════════════════════════════
# CRUD — silencioso para tabelas ausentes
# ═══════════════════════════════════════════════════════
@st.cache_data(ttl=20)
def get_data(table: str) -> pd.DataFrame:
    try:
        res = supabase.table(table).select("*").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception as e:
        err = str(e)
        # Silencia erros de tabela inexistente — tratados no painel de setup
        if "schema cache" in err or "Could not find" in err:
            return pd.DataFrame()
        st.warning(f"Erro ao buscar {table}: {e}")
        return pd.DataFrame()


def _coluna_existe(tabela: str, coluna: str) -> bool:
    """
    Testa se uma coluna existe tentando fazer SELECT dela.
    Retorna False apenas para erro PGRST204 (coluna não encontrada).
    """
    try:
        supabase.table(tabela).select(coluna).limit(1).execute()
        return True
    except Exception as e:
        err = str(e)
        # PGRST204 = coluna não encontrada no schema cache
        if "PGRST204" in err or (
            "Could not find" in err and "column" in err and tabela in err
        ):
            return False
        # Qualquer outro erro (ex: tabela vazia, RLS, etc.) assume que existe
        return True


@st.cache_data(ttl=15)
def tabelas_ausentes() -> list[str]:
    """Retorna lista de tabelas que não existem no banco."""
    ausentes = []
    for t in TABELAS_REQUERIDAS:
        try:
            supabase.table(t).select("id").limit(1).execute()
        except Exception as e:
            if "schema cache" in str(e) or "Could not find" in str(e):
                ausentes.append(t)
    return ausentes


@st.cache_data(ttl=15)
def colunas_ausentes() -> dict[str, list[str]]:
    """
    Testa cada coluna crítica individualmente via SELECT.
    Funciona mesmo com tabelas vazias.
    Retorna {tabela: [colunas_ausentes]}.
    """
    checks = {
        "veiculos":       ["tipo_veiculo", "tipo_combustivel_padrao", "motorista", "placa", "categoria"],
        "abastecimentos": ["origem", "nome_tanque", "status", "obra", "horimetro"],
        "tanques":        ["capacidade"],
        "producao":       ["tipo_operacao", "carradas", "toneladas", "obra"],
    }
    resultado = {}
    for tabela, colunas in checks.items():
        # Só verifica tabelas que existem
        try:
            supabase.table(tabela).select("id").limit(1).execute()
        except Exception:
            continue  # Tabela ausente — tratada por tabelas_ausentes()

        faltam = [col for col in colunas if not _coluna_existe(tabela, col)]
        if faltam:
            resultado[tabela] = faltam
    return resultado


def _clear():
    get_data.clear()
    tabelas_ausentes.clear()
    colunas_ausentes.clear()


def _col_erro(err_str: str) -> str | None:
    """Extrai o nome da coluna de um erro PGRST204 (coluna não encontrada)."""
    import re
    m = re.search(r"find the '([^']+)' column", err_str)
    return m.group(1) if m else None


def insert_data(table: str, data: dict) -> bool:
    """
    Insere dados removendo automaticamente colunas que não existem na tabela.
    Tenta o insert completo; se falhar por coluna ausente (PGRST204),
    remove a coluna problemática e tenta novamente (até 8 tentativas).
    """
    payload = dict(data)
    for _ in range(8):
        try:
            supabase.table(table).insert(payload).execute()
            _clear()
            return True
        except Exception as e:
            err = str(e)
            col = _col_erro(err)
            if col and col in payload:
                # Remove silenciosamente a coluna ausente e tenta de novo
                payload.pop(col)
                continue
            # Erro diferente — mostra para o usuário
            if "schema cache" in err or "Could not find" in err:
                st.error(
                    f"Coluna ou tabela não encontrada: `{err}`  \n"
                    "👉 Acesse **Setup do Banco de Dados** no menu lateral e execute o script SQL."
                )
            else:
                st.error(f"Erro ao salvar: {e}")
            return False
    st.error("Não foi possível salvar: muitas colunas ausentes na tabela. Execute o script SQL no Setup.")
    return False


def update_data(table: str, row_id, data: dict) -> bool:
    """Atualiza removendo automaticamente colunas que não existem."""
    payload = dict(data)
    for _ in range(8):
        try:
            supabase.table(table).update(payload).eq("id", row_id).execute()
            _clear()
            return True
        except Exception as e:
            err = str(e)
            col = _col_erro(err)
            if col and col in payload:
                payload.pop(col)
                continue
            st.error(f"Erro ao atualizar: {e}")
            return False
    return False


def delete_data(table, row_id):
    try:
        supabase.table(table).delete().eq("id", row_id).execute()
        _clear(); return True
    except Exception as e:
        st.error(f"Erro ao excluir: {e}"); return False


# ═══════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════
def hsh(s): return hashlib.sha256(s.encode()).hexdigest()
def flt(v, d=0.0):
    try: return float(v or d)
    except: return d

def dia_pt(d):
    dias = ["SEG","TER","QUA","QUI","SEX","SÁB","DOM"]
    try:
        if isinstance(d, str): d = datetime.strptime(d[:10], "%Y-%m-%d")
        return dias[d.weekday()]
    except: return ""

def lista_obras(todas=False):
    df = get_data("obras")
    if df.empty: return (["TODAS"] if todas else [])
    nomes = df[df["status"] != "Encerrada"]["nome"].dropna().tolist() if "status" in df.columns else df["nome"].dropna().tolist()
    return (["TODAS"] + nomes) if todas else nomes


# ═══════════════════════════════════════════════════════
# SALDO DE TANQUES — único fetch por ciclo
# ═══════════════════════════════════════════════════════
def todos_saldos() -> dict:
    df_tanq   = get_data("tanques")
    df_ent    = get_data("entradas_tanque")
    df_sai    = get_data("abastecimentos")
    df_transf = get_data("transferencias_tanque")

    if not df_sai.empty and "status" in df_sai.columns:
        df_sai = df_sai[df_sai["status"] == "ATIVO"]
    if not df_transf.empty and "status" in df_transf.columns:
        df_transf = df_transf[df_transf["status"] == "ATIVO"]

    saldos = {}
    if df_tanq.empty: return saldos

    for _, row in df_tanq.iterrows():
        nome = row.get("nome", "")
        if not nome: continue

        ent = 0.0
        if not df_ent.empty and "nome_tanque" in df_ent.columns:
            ent = pd.to_numeric(df_ent[df_ent["nome_tanque"] == nome]["quantidade"], errors="coerce").sum()

        sai_dir = 0.0
        if not df_sai.empty and "origem" in df_sai.columns and "nome_tanque" in df_sai.columns:
            mask = (df_sai["origem"] == "Tanque Interno") & (df_sai["nome_tanque"] == nome)
            sai_dir = pd.to_numeric(df_sai.loc[mask, "quantidade"], errors="coerce").sum()

        sai_tr = 0.0
        if not df_transf.empty and "tanque_origem" in df_transf.columns:
            sai_tr = pd.to_numeric(df_transf.loc[df_transf["tanque_origem"] == nome, "quantidade"], errors="coerce").sum()

        saldos[nome] = float(ent) - float(sai_dir) - float(sai_tr)
    return saldos


# ═══════════════════════════════════════════════════════
# EXPORTAÇÃO
# ═══════════════════════════════════════════════════════
def xl_limpo(df: pd.DataFrame, aba="Dados") -> bytes:
    df = df.fillna("").copy()
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as w:
        df.to_excel(w, index=False, sheet_name=aba[:31])
        ws = w.sheets[aba[:31]]
        for i, col in enumerate(df.columns):
            try: sz = max(len(str(col)), df[col].astype(str).str.len().max())
            except: sz = 14
            ws.set_column(i, i, min(int(sz) + 2, 55))
    return buf.getvalue()


def xl_abastecimentos(df: pd.DataFrame, titulo: str, periodo: str) -> bytes:
    df = df.fillna("").copy()
    buf = io.BytesIO()
    wb  = xlsxwriter.Workbook(buf)
    ws  = wb.add_worksheet("Relatório")
    fT  = wb.add_format({"bold":True,"font_size":11,"align":"center","bg_color":"#1E3A5F","font_color":"#FFFFFF","border":1})
    fH  = wb.add_format({"bold":True,"font_size":9,"align":"center","bg_color":"#DBEAFE","border":1,"text_wrap":True})
    fD  = wb.add_format({"font_size":9,"border":1,"align":"center"})
    fN  = wb.add_format({"font_size":9,"border":1,"align":"right","num_format":"#,##0.00"})
    fM  = wb.add_format({"font_size":9,"border":1,"align":"right","num_format":"R$ #,##0.00"})
    fTot= wb.add_format({"bold":True,"font_size":9,"border":1,"align":"right","bg_color":"#F1F5F9","num_format":"R$ #,##0.00"})

    ws.merge_range(0,0,0,11, titulo.upper(), fT)
    ws.write(1,0, f"Período: {periodo}", wb.add_format({"italic":True,"font_size":9}))
    heads  = ["DATA","DIA","FICHA","PREFIXO","PLACA","MOTORISTA","FORNECEDOR","COMBUSTÍVEL","QTD (L)","VL UNIT","TOTAL","OBRA"]
    widths = [12,6,10,10,10,22,22,14,10,12,12,20]
    ws.set_row(2,26)
    for i,(h,w) in enumerate(zip(heads,widths)):
        ws.write(2,i,h,fH); ws.set_column(i,i,w)

    tL = tR = 0.0
    for ri,(_, r) in enumerate(df.iterrows(), start=3):
        q = flt(r.get("quantidade")); v = flt(r.get("valor_unitario")); t = flt(r.get("total"))
        tL += q; tR += t
        vals = [str(r.get("data",""))[:10], dia_pt(str(r.get("data",""))[:10]),
                str(r.get("numero_ficha","")), str(r.get("prefixo","")),
                str(r.get("placa","")),       str(r.get("motorista","")),
                str(r.get("fornecedor","")),  str(r.get("tipo_combustivel",""))]
        for ci,val in enumerate(vals): ws.write(ri,ci,val,fD)
        ws.write(ri,8,q,fN); ws.write(ri,9,v,fM); ws.write(ri,10,t,fM)
        ws.write(ri,11,str(r.get("obra","")),fD)

    rt = 3 + len(df)
    ws.merge_range(rt,0,rt,7,"TOTAIS GERAIS",fTot)
    ws.write(rt,8, tL, wb.add_format({"bold":True,"font_size":9,"border":1,"align":"right","bg_color":"#F1F5F9","num_format":"#,##0.00"}))
    ws.write(rt,9, "", fTot); ws.write(rt,10, tR, fTot); ws.write(rt,11,"",fTot)
    wb.close(); buf.seek(0)
    return buf.getvalue()


def xl_tanque(df_e, df_s, df_t, nome, periodo) -> bytes:
    buf = io.BytesIO(); wb = xlsxwriter.Workbook(buf)
    ws  = wb.add_worksheet("Movimentação")
    fT  = wb.add_format({"bold":True,"font_size":11,"align":"center","bg_color":"#0F1C2E","font_color":"#FFFFFF","border":1})
    fH  = wb.add_format({"bold":True,"font_size":8,"align":"center","bg_color":"#DBEAFE","border":1,"text_wrap":True})
    fD  = wb.add_format({"font_size":8,"border":1,"align":"center"})
    fE  = wb.add_format({"font_size":8,"border":1,"align":"right","num_format":"#,##0.0","font_color":"#166534"})
    fS  = wb.add_format({"font_size":8,"border":1,"align":"right","num_format":"#,##0.0","font_color":"#991B1B"})
    fSd = wb.add_format({"bold":True,"font_size":8,"border":1,"align":"right","num_format":"#,##0.0"})
    fM  = wb.add_format({"font_size":8,"border":1,"align":"right","num_format":"R$ #,##0.00"})

    ws.merge_range(0,0,0,13, f"MOVIMENTAÇÃO — {nome.upper()} — {periodo}", fT)
    heads  = ["DATA","DIA","TIPO","FICHA","PLACA","PREF.","MOTORISTA/FORN.","PRODUTO","KM/HOR","ENT.(L)","SAÍ.(L)","VL.UNIT","TOTAL","SALDO(L)"]
    widths = [11,6,16,10,10,8,22,14,8,10,10,12,12,11]
    ws.set_row(1,24)
    for i,(h,w) in enumerate(zip(heads,widths)):
        ws.write(1,i,h,fH); ws.set_column(i,i,w)

    movs = []
    for _, r in (df_e.iterrows() if not df_e.empty else []):  movs.append({**r.to_dict(),"_t":"ENTRADA"})
    for _, r in (df_s.iterrows() if not df_s.empty else []):  movs.append({**r.to_dict(),"_t":"SAÍDA DIRETA"})
    for _, r in (df_t.iterrows() if not df_t.empty else []):  movs.append({**r.to_dict(),"_t":"TRANSF."})
    movs.sort(key=lambda x: str(x.get("data","")))

    saldo = te = ts = 0.0
    for ri,r in enumerate(movs, start=2):
        tp = r["_t"]; q = flt(r.get("quantidade")); v = flt(r.get("valor_unitario")); tot = flt(r.get("total"))
        if tp == "ENTRADA": saldo += q; te += q; qe,qs = q,0.0
        else:               saldo -= q; ts += q; qe,qs = 0.0,q
        forn = r.get("fornecedor","") if tp=="ENTRADA" else r.get("motorista", r.get("caminhao_tanque",""))
        prod = r.get("combustivel","") if tp=="ENTRADA" else r.get("tipo_combustivel", r.get("produto",""))
        for ci,val in enumerate([str(r.get("data",""))[:10], dia_pt(str(r.get("data",""))[:10]),
                                  tp, str(r.get("numero_ficha","")), str(r.get("placa","")),
                                  str(r.get("prefixo","")), str(forn), str(prod), str(r.get("horimetro",""))]):
            ws.write(ri,ci,val,fD)
        ws.write(ri,9,  qe if qe else "", fE if qe else fD)
        ws.write(ri,10, qs if qs else "", fS if qs else fD)
        ws.write(ri,11, v, fM); ws.write(ri,12, tot, fM); ws.write(ri,13, saldo, fSd)

    rt = 2+len(movs)
    fTotE = wb.add_format({"bold":True,"font_size":9,"border":1,"align":"right","bg_color":"#F0FDF4","num_format":"#,##0.0"})
    fTotS = wb.add_format({"bold":True,"font_size":9,"border":1,"align":"right","bg_color":"#FEF2F2","num_format":"#,##0.0"})
    fTotN = wb.add_format({"bold":True,"font_size":9,"border":1,"align":"right","bg_color":"#F1F5F9"})
    ws.merge_range(rt,0,rt,8,"TOTAIS",fTotN)
    ws.write(rt,9,te,fTotE); ws.write(rt,10,ts,fTotS)
    ws.write(rt,11,"",fTotN); ws.write(rt,12,"",fTotN); ws.write(rt,13,te-ts,fSd)
    wb.close(); buf.seek(0)
    return buf.getvalue()


# ═══════════════════════════════════════════════════════
# UI COMPONENTS
# ═══════════════════════════════════════════════════════
def kpi(col, label, value, cor="#1E3A5F"):
    col.markdown(f"""
    <div class='kp'>
      <div class='kp-lbl'>{label}</div>
      <div class='kp-val'>{value}</div>
      <div class='kp-bar' style='background:{cor}'></div>
    </div>""", unsafe_allow_html=True)

def tank_card(col, nome, saldo, cap):
    pct = min(saldo/cap, 1.0) if cap>0 else 0
    cls = "tk-g" if pct>0.30 else ("tk-y" if pct>0.10 else "tk-r")
    pct_txt = f" ({pct*100:.0f}%)" if cap>0 else ""
    col.markdown(f"""
    <div class='tk'>
      <div class='tk-nome'>{nome}</div>
      <div class='tk-val {cls}'>{saldo:,.0f} L{pct_txt}</div>
    </div>""", unsafe_allow_html=True)
    if cap>0: col.progress(max(0.0, pct))

def av(msg, tipo="in"):
    cls = {"ok":"av-ok","lo":"av-lo","er":"av-er","in":"av-in"}.get(tipo,"av-in")
    st.markdown(f"<div class='{cls}'>{msg}</div>", unsafe_allow_html=True)

def secao(titulo):
    st.markdown(f"<h3>{titulo}</h3>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════
# LOGIN
# ═══════════════════════════════════════════════════════
for k,v in [("logged_in",False),("usuario_logado",""),("perfil_logado","")]:
    if k not in st.session_state: st.session_state[k] = v

if not st.session_state.logged_in:

    # Encode logo — HTML puro, sem container cinza do Streamlit
    _logo_b64 = ""
    if os.path.exists("logo.png"):
        with open("logo.png", "rb") as _f:
            _logo_b64 = base64.b64encode(_f.read()).decode()

    _logo_img = (
        f'<img src="data:image/png;base64,{_logo_b64}" style="height:48px;object-fit:contain;">'
        if _logo_b64 else
        '<span style="font-size:18px;font-weight:700;color:#1E3A5F;">COPA ENGENHARIA</span>'
    )

    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600;700&display=swap');
    html,body,[class*="css"] {{ font-family:'IBM Plex Sans',sans-serif !important; }}

    [data-testid="stAppViewContainer"] {{
        background: #1C2B3A !important;
    }}
    [data-testid="stHeader"]  {{ background:transparent !important; }}
    [data-testid="stSidebar"] {{ display:none !important; }}

    .main .block-container {{
        padding: 7vh 1rem 2rem !important;
        max-width: 100% !important;
    }}

    /* Card branco limpo — empresarial */
    div[data-testid="stForm"] {{
        background: #FFFFFF !important;
        border-radius: 0 0 4px 4px !important;
        padding: 2.4rem 2.8rem 2.4rem !important;
        box-shadow: 0 8px 32px rgba(0,0,0,.28) !important;
        border: none !important;
    }}

    /* Labels */
    .stTextInput > label {{
        font-size: 11px !important;
        font-weight: 600 !important;
        color: #64748B !important;
        text-transform: uppercase !important;
        letter-spacing: .07em !important;
        margin-bottom: 4px !important;
    }}

    /* Inputs */
    div[data-baseweb="input"] {{
        border-radius: 3px !important;
        border: 1px solid #CBD5E1 !important;
        background: #FAFAFA !important;
    }}
    div[data-baseweb="input"]:focus-within {{
        border-color: #1E3A5F !important;
        background: #fff !important;
        box-shadow: 0 0 0 2px rgba(30,58,95,.12) !important;
    }}
    div[data-baseweb="input"] input {{
        color: #0F172A !important;
        font-family: 'IBM Plex Sans', sans-serif !important;
        font-size: 14px !important;
    }}

    /* Botão */
    div.stButton > button:first-child {{
        background: #1E3A5F !important;
        color: #fff !important;
        border: none !important;
        border-radius: 3px !important;
        font-weight: 600 !important;
        font-size: 12px !important;
        letter-spacing: .08em !important;
        text-transform: uppercase !important;
        padding: .72rem !important;
        margin-top: .6rem !important;
        transition: background .12s ease !important;
    }}
    div.stButton > button:first-child:hover {{
        background: #152E4D !important;
    }}

    /* Erro */
    div[data-testid="stAlert"] {{
        background: #FEF2F2 !important;
        border: 1px solid #FECACA !important;
        border-radius: 3px !important;
    }}
    div[data-testid="stAlert"] p {{ color: #991B1B !important; font-size:13px !important; }}
    </style>
    """, unsafe_allow_html=True)

    _, c2, _ = st.columns([1, 1.38, 1])
    with c2:
        # Faixa branca para o logo (sem conflito com fundo branco do PNG)
        # + faixa navy abaixo com o nome do sistema
        st.markdown(f"""
        <div style="border-radius:4px 4px 0 0;overflow:hidden;
                    box-shadow:0 8px 32px rgba(0,0,0,.28);">
            <div style="background:#fff;padding:1.3rem 2.4rem;
                        border-bottom:3px solid #1E3A5F;">
                {_logo_img}
            </div>
            <div style="background:#1E3A5F;padding:1rem 2.4rem 1.2rem;">
                <div style="font-size:13px;font-weight:600;color:#fff;letter-spacing:.02em;">
                    Sistema de Abastecimentos
                </div>
                <div style="font-size:10px;color:#7FA8C9;margin-top:3px;letter-spacing:.02em;">
                    Gestão de frota e combustível
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login"):
            u = st.text_input("Usuário")
            p = st.text_input("Senha", type="password")
            submitted = st.form_submit_button("Acessar", use_container_width=True)
            st.markdown("""
            <div style="margin-top:1.4rem;padding-top:1rem;
                        border-top:1px solid #F1F5F9;
                        font-size:9px;color:#CBD5E1;letter-spacing:.04em;">
                © Copa Engenharia — Acesso restrito a usuários autorizados
            </div>""", unsafe_allow_html=True)

        if submitted:
            ok = False
            try:
                res = supabase.table("usuarios").select("*").eq("login", u).execute()
                if res.data:
                    usr = res.data[0]
                    if usr.get("senha") in (p, hsh(p)):
                        st.session_state.logged_in      = True
                        st.session_state.usuario_logado = usr["nome"]
                        st.session_state.perfil_logado  = usr.get("perfil", "Operador")
                        ok = True
            except Exception:
                pass
            if not ok:
                if (u == st.secrets.get("ADMIN_USER", "admin")
                        and p == st.secrets.get("ADMIN_PASS", "copa@2025")):
                    st.session_state.logged_in      = True
                    st.session_state.usuario_logado = "Admin"
                    st.session_state.perfil_logado  = "Admin"
                    ok = True
            if not ok:
                st.error("Usuário ou senha incorretos.")
            elif st.session_state.logged_in:
                st.rerun()
    st.stop()


# ═══════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════
with st.sidebar:
    # Logo via base64 para evitar container cinza do st.image
    if os.path.exists("logo.png"):
        with open("logo.png", "rb") as _lf:
            _sb_b64 = base64.b64encode(_lf.read()).decode()
        st.markdown(f"""
        <div style='text-align:center;padding:.6rem 0 .4rem;'>
          <img src="data:image/png;base64,{_sb_b64}"
               style="height:44px;object-fit:contain;filter:brightness(1.15);">
        </div>""", unsafe_allow_html=True)

    ausentes  = tabelas_ausentes()
    cols_aus  = colunas_ausentes()
    tem_problema = bool(ausentes or cols_aus)

    if tem_problema:
        n = len(ausentes) + sum(len(v) for v in cols_aus.values())
        st.markdown(f"""
        <div style='background:#7F1D1D;color:#FCA5A5;border-radius:5px;
                    padding:8px 12px;font-size:11px;font-weight:600;margin:.5rem 0;'>
          ⚠ {n} problema(s) no banco<br>
          <span style='font-weight:400;opacity:.8'>Acesse Setup do Banco</span>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style='background:#14532D;color:#86EFAC;border-radius:5px;
                    padding:6px 12px;font-size:11px;font-weight:600;margin:.5rem 0;'>
          ✓ Banco configurado
        </div>""", unsafe_allow_html=True)

    st.markdown(f"""
    <div style='font-size:11px;color:#4E7A9F;font-weight:600;
                text-align:center;margin:.5rem 0 .8rem;letter-spacing:.04em;'>
        {st.session_state.usuario_logado.upper()}
    </div>""", unsafe_allow_html=True)
    st.divider()

    opcoes = [
        "Painel Geral",
        "Fluxo de Caixa",
        "Lançar Abastecimento",
        "Transferência Caminhão-Tanque",
        "Tanques / Estoque",
        "Boletim de Transporte",
        "Frota e Equipamentos",
        "Obras",
        "Fornecedores",
        "Relatórios e Fechamentos",
    ]
    if ausentes or cols_aus:
        opcoes.append("Setup do Banco de Dados")
    if st.session_state.perfil_logado == "Admin":
        opcoes.append("Usuários e Acessos")

    menu = st.radio("", opcoes, label_visibility="collapsed")
    st.divider()
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Sair", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.usuario_logado = ""
        st.session_state.perfil_logado  = ""
        st.rerun()
    st.caption("Supabase · Dados em tempo real")


# ═══════════════════════════════════════════════════════
# 0 · SETUP DO BANCO
# ═══════════════════════════════════════════════════════
if menu == "Setup do Banco de Dados":
    st.markdown("## Setup do Banco de Dados")

    with st.spinner("Verificando estrutura do banco..."):
        ausentes  = tabelas_ausentes()
        cols_aus  = colunas_ausentes()

    if not ausentes and not cols_aus:
        av("✓ Banco de dados totalmente configurado. Todos os módulos estão disponíveis.", "ok")
        st.markdown("Você pode navegar pelo sistema normalmente. Este item sumirá do menu na próxima verificação automática (a cada 15 segundos).")
        if st.button("Recarregar verificação", use_container_width=False):
            _clear(); st.rerun()
    else:
        # Mostra o que está faltando
        if ausentes:
            av(f"Tabelas ausentes: <strong>{', '.join(ausentes)}</strong>", "er")
        if cols_aus:
            for tab, cols in cols_aus.items():
                av(f"Coluna(s) ausente(s) em <strong>{tab}</strong>: {', '.join(f'<code>{c}</code>' for c in cols)}", "lo")

        st.markdown("#### Como corrigir em 3 passos")
        st.markdown("""
        **1.** Acesse [supabase.com](https://supabase.com) → seu projeto → **SQL Editor**

        **2.** Cole o script abaixo e clique em **RUN** (botão verde no canto superior direito)

        **3.** Volte aqui e clique em **Verificar novamente**
        """)
        st.info("O script usa `IF NOT EXISTS` — é seguro rodar mesmo que algumas tabelas/colunas já existam.")
        st.code(SQL_CRIAR_TABELAS, language="sql")

        col_dl, col_ok = st.columns(2)
        col_dl.download_button(
            "Baixar script SQL",
            SQL_CRIAR_TABELAS,
            file_name="setup_abastecimentos.sql",
            mime="text/plain",
            use_container_width=True,
        )
        if col_ok.button("Verificar novamente", use_container_width=True, type="primary"):
            _clear()
            st.rerun()


# ═══════════════════════════════════════════════════════
# 1 · PAINEL GERAL
# ═══════════════════════════════════════════════════════
elif menu == "Painel Geral":
    st.markdown("## Painel Geral")

    fc1, fc2, fc3 = st.columns(3)
    d_ini = fc1.date_input("Período de",  value=date.today().replace(day=1))
    d_fim = fc2.date_input("Período até", value=date.today())
    obs_f = lista_obras(todas=True)
    obra_f = fc3.selectbox("Obra", obs_f) if obs_f else "TODAS"

    df_tanq = get_data("tanques")
    df_ab   = get_data("abastecimentos")
    df_prod = get_data("producao")
    saldos  = todos_saldos()

    if not df_ab.empty and "status" in df_ab.columns:
        df_ab = df_ab[df_ab["status"] == "ATIVO"]

    def fil(df, obra_col="obra"):
        if df.empty: return df
        df = df.copy()
        df["_dt"] = pd.to_datetime(df.get("data",""), errors="coerce").dt.date
        df = df[df["_dt"].notna() & (df["_dt"] >= d_ini) & (df["_dt"] <= d_fim)]
        if obra_f and obra_f != "TODAS" and obra_col in df.columns:
            df = df[df[obra_col] == obra_f]
        return df

    daf = fil(df_ab); dpf = fil(df_prod)
    t_gasto  = pd.to_numeric(daf.get("total",      pd.Series(dtype=float)), errors="coerce").sum()
    t_litros = pd.to_numeric(daf.get("quantidade", pd.Series(dtype=float)), errors="coerce").sum()
    t_ton    = pd.to_numeric(dpf.get("toneladas",  pd.Series(dtype=float)), errors="coerce").sum()
    t_viag   = int(pd.to_numeric(dpf.get("carradas", pd.Series(dtype=float)), errors="coerce").sum())

    # ── KPIs ──
    c1,c2,c3,c4 = st.columns(4)
    kpi(c1,"Gasto com Combustível",        f"R$ {t_gasto:,.2f}",  "#DC2626")
    kpi(c2,"Litros Abastecidos",           f"{t_litros:,.0f} L",  "#1E40AF")
    kpi(c3,"Toneladas Transportadas",      f"{t_ton:,.1f} t",     "#059669")
    kpi(c4,"Viagens Realizadas",           str(t_viag),            "#7C3AED")
    st.markdown("<br>", unsafe_allow_html=True)

    c5,c6,c7,_ = st.columns(4)
    kpi(c5,"Custo / Tonelada",  f"R$ {(t_gasto/t_ton if t_ton>0 else 0):,.2f}",   "#D97706")
    kpi(c6,"Litros / Tonelada", f"{(t_litros/t_ton if t_ton>0 else 0):,.2f} L",   "#0891B2")
    kpi(c7,"Litros / Viagem",   f"{(t_litros/t_viag if t_viag>0 else 0):,.1f} L", "#6D28D9")

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Tanques ──
    if not df_tanq.empty:
        secao("Situação dos Tanques")
        cols_t = st.columns(min(len(df_tanq), 5))
        for i,(_, row) in enumerate(df_tanq.iterrows()):
            nm = row.get("nome",""); cap = flt(row.get("capacidade")); sd = saldos.get(nm,0.0)
            with cols_t[i % len(cols_t)]:
                tank_card(st.container(), nm, sd, cap)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Gráficos ──
    if not daf.empty and "data" in daf.columns:
        daf["Mês"] = pd.to_datetime(daf["data"], errors="coerce").dt.strftime("%m/%Y")
        daf["total_n"] = pd.to_numeric(daf.get("total",0), errors="coerce").fillna(0)
        g1, g2 = st.columns(2)

        with g1:
            gm = daf.groupby("Mês")["total_n"].sum().reset_index()
            if not gm.empty:
                fig = px.bar(gm, x="Mês", y="total_n", title="Gasto Mensal (R$)",
                             labels={"total_n":"Total (R$)"},
                             color_discrete_sequence=["#1E3A5F"])
                fig.update_traces(texttemplate="R$%{y:,.0f}", textposition="outside", marker_line_width=0)
                fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                                  font_family="IBM Plex Sans", title_font_size=13,
                                  margin=dict(t=36,b=16,l=0,r=0))
                st.plotly_chart(fig, use_container_width=True)

        with g2:
            if "obra" in daf.columns and not daf["obra"].dropna().empty:
                go_ = daf.groupby("obra")["total_n"].sum().reset_index().sort_values("total_n", ascending=False).head(8)
                if not go_.empty:
                    fig2 = px.bar(go_, x="total_n", y="obra", orientation="h", title="Gasto por Obra (R$)",
                                  labels={"total_n":"Total (R$)","obra":""},
                                  color_discrete_sequence=["#1E40AF"])
                    fig2.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                                       font_family="IBM Plex Sans", title_font_size=13,
                                       margin=dict(t=36,b=16,l=0,r=0),
                                       yaxis={"categoryorder":"total ascending"})
                    st.plotly_chart(fig2, use_container_width=True)


# ═══════════════════════════════════════════════════════
# 2 · FLUXO DE CAIXA
# ═══════════════════════════════════════════════════════
elif menu == "Fluxo de Caixa":
    st.markdown("## Fluxo de Caixa")
    av("Entradas = compras para o tanque (distribuidoras). Saídas = abastecimentos em postos externos e consumo do tanque.", "in")

    fc1,fc2,fc3 = st.columns(3)
    d_ini = fc1.date_input("De",  value=date.today().replace(day=1), key="fc_i")
    d_fim = fc2.date_input("Até", value=date.today(),                key="fc_f")
    obf   = lista_obras(todas=True)
    obra_f = fc3.selectbox("Obra", obf, key="fc_ob") if obf else "TODAS"

    df_et = get_data("entradas_tanque")
    df_ab = get_data("abastecimentos")
    if not df_ab.empty and "status" in df_ab.columns:
        df_ab = df_ab[df_ab["status"] == "ATIVO"]

    def afc(df, oc="obra"):
        if df.empty: return df
        df = df.copy()
        df["_dt"] = pd.to_datetime(df.get("data",""), errors="coerce").dt.date
        df = df[df["_dt"].notna() & (df["_dt"] >= d_ini) & (df["_dt"] <= d_fim)]
        if obra_f != "TODAS" and oc in df.columns:
            df = df[df[oc] == obra_f]
        return df

    et_f = afc(df_et); ab_f = afc(df_ab)
    ab_pos = ab_f[ab_f.get("origem",pd.Series(dtype=str)) == "Posto Externo"] if not ab_f.empty and "origem" in ab_f.columns else pd.DataFrame()
    ab_tan = ab_f[ab_f.get("origem",pd.Series(dtype=str)) == "Tanque Interno"] if not ab_f.empty and "origem" in ab_f.columns else pd.DataFrame()

    tot_comp = pd.to_numeric(et_f.get("total",      pd.Series(dtype=float)), errors="coerce").sum()
    lit_comp = pd.to_numeric(et_f.get("quantidade", pd.Series(dtype=float)), errors="coerce").sum()
    tot_pos  = pd.to_numeric(ab_pos.get("total",    pd.Series(dtype=float)), errors="coerce").sum()
    lit_pos  = pd.to_numeric(ab_pos.get("quantidade",pd.Series(dtype=float)), errors="coerce").sum()
    lit_tan  = pd.to_numeric(ab_tan.get("quantidade",pd.Series(dtype=float)), errors="coerce").sum()
    pm       = tot_comp / lit_comp if lit_comp > 0 else 0.0
    tot_tan  = lit_tan * pm

    c1,c2,c3,c4 = st.columns(4)
    kpi(c1,"Compras p/ Tanque (Distrib.)", f"R$ {tot_comp:,.2f}", "#059669")
    kpi(c2,"Abastec. Postos Externos",     f"R$ {tot_pos:,.2f}",  "#DC2626")
    kpi(c3,"Custo Estimado Tanque Próprio",f"R$ {tot_tan:,.2f}",  "#D97706")
    kpi(c4,"Preço Médio Compra",           f"R$ {pm:,.3f}/L",     "#1E40AF")
    st.markdown("<br>", unsafe_allow_html=True)
    c5,c6,c7,c8 = st.columns(4)
    kpi(c5,"Litros Comprados",     f"{lit_comp:,.0f} L", "#059669")
    kpi(c6,"Litros Postos",        f"{lit_pos:,.0f} L",  "#DC2626")
    kpi(c7,"Litros Tanque Próprio",f"{lit_tan:,.0f} L",  "#D97706")
    kpi(c8,"Gasto Total Período",  f"R$ {tot_comp+tot_pos:,.2f}", "#7C3AED")

    st.markdown("<hr>", unsafe_allow_html=True)

    tab_forn, tab_obra, tab_veic, tab_evo = st.tabs([
        "Por Fornecedor","Por Obra","Por Veículo","Evolução Mensal"
    ])

    with tab_forn:
        secao("Consolidado por Fornecedor — Base para Pagamentos")
        frames = []
        if not et_f.empty and "fornecedor" in et_f.columns:
            g = et_f.groupby("fornecedor").agg(litros=("quantidade","sum"),total=("total","sum")).reset_index()
            g["Tipo"] = "Compra p/ Tanque"; g.columns = ["Fornecedor","Litros","Total R$","Tipo"]
            frames.append(g)
        if not ab_pos.empty and "fornecedor" in ab_pos.columns:
            g2 = ab_pos.groupby("fornecedor").agg(litros=("quantidade","sum"),total=("total","sum")).reset_index()
            g2["Tipo"] = "Abastec. Externo"; g2.columns = ["Fornecedor","Litros","Total R$","Tipo"]
            frames.append(g2)

        if frames:
            df_f2 = pd.concat(frames, ignore_index=True)
            df_f2["Litros"]    = pd.to_numeric(df_f2["Litros"],   errors="coerce").fillna(0)
            df_f2["Total R$"]  = pd.to_numeric(df_f2["Total R$"], errors="coerce").fillna(0)
            df_f2["R$/L médio"]= (df_f2["Total R$"]/df_f2["Litros"]).replace([float("inf")],0).round(3)

            fig = px.bar(df_f2.sort_values("Total R$",ascending=False), x="Fornecedor", y="Total R$",
                         color="Tipo", barmode="group",
                         color_discrete_sequence=["#1E3A5F","#1E40AF"])
            fig.update_layout(plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
                              font_family="IBM Plex Sans",title_font_size=13,
                              margin=dict(t=16,b=16,l=0,r=0))
            st.plotly_chart(fig, use_container_width=True)

            st.dataframe(df_f2.sort_values("Total R$",ascending=False)
                            .style.format({"Litros":"{:,.1f}","Total R$":"R$ {:,.2f}","R$/L médio":"R$ {:,.3f}"}),
                         use_container_width=True, hide_index=True)

            st.markdown("<br>", unsafe_allow_html=True)
            secao("Relatório de Pagamento por Fornecedor")
            forn_u = df_f2["Fornecedor"].dropna().unique().tolist()
            cf1,cf2 = st.columns([3,1])
            fp = cf1.selectbox("Fornecedor", forn_u, key="fp_sel")
            if cf2.button("Gerar Excel"):
                df_pag = ab_pos[ab_pos.get("fornecedor","") == fp] if not ab_pos.empty else pd.DataFrame()
                per = f"{d_ini.strftime('%d/%m/%Y')} a {d_fim.strftime('%d/%m/%Y')}"
                xl  = xl_abastecimentos(df_pag, f"PAGAMENTO — {fp.upper()}", per)
                st.download_button(f"Baixar — {fp}", xl,
                                   f"Pagamento_{fp}_{d_ini}.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.info("Nenhum dado no período.")

    with tab_obra:
        secao("Custo por Obra")
        if not ab_f.empty and "obra" in ab_f.columns:
            go_ = ab_f.groupby("obra").agg(litros=("quantidade","sum"),gasto=("total","sum")).reset_index()
            go_.columns = ["Obra","Litros","Gasto R$"]
            go_["Litros"]   = pd.to_numeric(go_["Litros"],  errors="coerce").fillna(0)
            go_["Gasto R$"] = pd.to_numeric(go_["Gasto R$"],errors="coerce").fillna(0)
            go_ = go_.sort_values("Gasto R$", ascending=False)

            fig = px.pie(go_, names="Obra", values="Gasto R$",
                         color_discrete_sequence=px.colors.qualitative.Set2)
            fig.update_layout(font_family="IBM Plex Sans", margin=dict(t=16,b=16,l=0,r=0))
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(go_.style.format({"Litros":"{:,.1f}","Gasto R$":"R$ {:,.2f}"}),
                         use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum dado com obra vinculada.")

    with tab_veic:
        secao("Consumo por Veículo / Equipamento")
        if not ab_f.empty and "prefixo" in ab_f.columns:
            gv = ab_f.groupby("prefixo").agg(litros=("quantidade","sum"),gasto=("total","sum")).reset_index()
            gv.columns = ["Veículo","Litros","Gasto R$"]
            gv["Litros"]   = pd.to_numeric(gv["Litros"],  errors="coerce").fillna(0)
            gv["Gasto R$"] = pd.to_numeric(gv["Gasto R$"],errors="coerce").fillna(0)
            gv = gv.sort_values("Litros", ascending=False)
            fig = px.bar(gv.head(15), x="Veículo", y="Litros",
                         color="Gasto R$", color_continuous_scale="Blues",
                         title="Top 15 Consumidores (Litros)")
            fig.update_layout(plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
                              font_family="IBM Plex Sans",margin=dict(t=36,b=16,l=0,r=0))
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(gv.style.format({"Litros":"{:,.1f}","Gasto R$":"R$ {:,.2f}"}),
                         use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum dado no período.")

    with tab_evo:
        secao("Evolução Mensal")
        fr = []
        if not ab_f.empty and "data" in ab_f.columns:
            tmp = ab_f[["data","total","origem"]].copy()
            tmp["total"] = pd.to_numeric(tmp["total"],errors="coerce").fillna(0)
            tmp["Mês"]   = pd.to_datetime(tmp["data"],errors="coerce").dt.strftime("%m/%Y")
            fr.append(tmp.groupby(["Mês","origem"])["total"].sum().reset_index()
                        .rename(columns={"origem":"Categoria","total":"Valor R$"}))
        if not et_f.empty and "data" in et_f.columns:
            tmp2 = et_f[["data","total"]].copy()
            tmp2["total"] = pd.to_numeric(tmp2["total"],errors="coerce").fillna(0)
            tmp2["Mês"] = pd.to_datetime(tmp2["data"],errors="coerce").dt.strftime("%m/%Y")
            tmp2["Categoria"] = "Compra p/ Tanque"
            fr.append(tmp2.groupby(["Mês","Categoria"])["total"].sum().reset_index()
                        .rename(columns={"total":"Valor R$"}))
        if fr:
            df_evo = pd.concat(fr, ignore_index=True)
            fig = px.line(df_evo, x="Mês", y="Valor R$", color="Categoria", markers=True)
            fig.update_layout(plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
                              font_family="IBM Plex Sans",margin=dict(t=16,b=16,l=0,r=0))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhum dado no período.")


# ═══════════════════════════════════════════════════════
# 3 · LANÇAR ABASTECIMENTO
# ═══════════════════════════════════════════════════════
elif menu == "Lançar Abastecimento":
    st.markdown("## Lançar Abastecimento")

    df_v = get_data("veiculos")
    df_f = get_data("fornecedores")
    df_t = get_data("tanques")
    df_a = get_data("abastecimentos")
    saldos = todos_saldos()

    if df_v.empty:
        av("Nenhum veículo cadastrado. Acesse Frota e Equipamentos para cadastrar.", "lo")
        st.stop()

    c_vs, _ = st.columns([2,1])
    v_sel = c_vs.selectbox("Veículo / Equipamento", df_v["prefixo"].tolist())
    v_info = df_v[df_v["prefixo"] == v_sel].iloc[0]
    comb_pad = v_info.get("tipo_combustivel_padrao","Diesel S10")
    placa_pad = v_info.get("placa","")
    mot_pad   = v_info.get("motorista","")

    m_hor = 0.0
    if not df_a.empty and "prefixo" in df_a.columns:
        df_h = df_a[df_a["prefixo"] == v_sel].copy()
        df_h["hn"] = pd.to_numeric(df_h.get("horimetro"), errors="coerce")
        m_hor = flt(df_h["hn"].max())

    st.markdown("<hr>", unsafe_allow_html=True)
    origem = st.radio("Origem do Combustível", ["Posto Externo","Tanque Interno"], horizontal=True)

    saldo_prev = None; tanq_prev = None
    if origem == "Tanque Interno" and not df_t.empty:
        tanq_prev = st.selectbox("Tanque (visualização de saldo)", df_t["nome"].tolist(), key="prv")
        saldo_prev = saldos.get(tanq_prev, 0.0)
        cls = "ok" if saldo_prev >= 500 else "lo"
        av(f"Saldo atual de <strong>{tanq_prev}</strong>: <strong>{saldo_prev:,.1f} L</strong>", cls)

    obras_l = lista_obras()

    with st.form("f_ab", clear_on_submit=True):
        c1,c2,c3 = st.columns(3)
        data_ab  = c1.date_input("Data")
        ficha    = c2.text_input("Ficha / NF")
        motorista= c3.text_input("Motorista", value=mot_pad)

        c4,c5,c6 = st.columns(3)
        if origem == "Posto Externo":
            fl = df_f["nome"].tolist() if not df_f.empty else []
            posto  = c4.selectbox("Fornecedor", fl) if fl else c4.text_input("Fornecedor")
            n_tanq = None
        else:
            n_tanq = c4.selectbox("Tanque", df_t["nome"].tolist() if not df_t.empty else [])
            posto  = "Estoque Próprio"

        hor = c5.number_input("KM / Horímetro", value=float(m_hor), min_value=0.0)
        obs = c6.text_input("Observação")

        c7,c8,c9 = st.columns(3)
        litros = c7.number_input("Litros",      min_value=0.0, step=0.5)
        preco  = c8.number_input("Preço (R$/L)", min_value=0.0, step=0.001, format="%.3f")
        if obras_l:
            obra_ab = c9.selectbox("Obra / Projeto", obras_l)
        else:
            obra_ab = c9.text_input("Obra / Projeto")

        total = round(litros * preco, 2)
        av(f"Total calculado: <strong>R$ {total:,.2f}</strong> &nbsp;|&nbsp; {litros:,.2f} L × R$ {preco:,.3f}", "in")

        if origem == "Tanque Interno" and saldo_prev is not None and litros > saldo_prev:
            av(f"Quantidade ({litros:,.1f} L) excede o saldo disponível ({saldo_prev:,.1f} L).", "er")

        if st.form_submit_button("REGISTRAR ABASTECIMENTO", use_container_width=True):
            if litros <= 0:
                st.error("Informe a quantidade de litros.")
            else:
                ok = insert_data("abastecimentos", {
                    "data": str(data_ab), "numero_ficha": ficha,
                    "origem": origem,
                    "nome_tanque": n_tanq if origem == "Tanque Interno" else None,
                    "prefixo": v_sel, "placa": placa_pad,
                    "motorista": motorista.upper(), "tipo_combustivel": comb_pad,
                    "quantidade": litros, "valor_unitario": preco, "total": total,
                    "fornecedor": posto, "horimetro": hor, "obra": obra_ab,
                    "observacao": obs, "status": "ATIVO",
                    "criado_por": st.session_state.usuario_logado,
                })
                if ok:
                    st.success("Abastecimento registrado com sucesso.")
                    st.rerun()

    # ── Listagem ──
    st.markdown("<hr>", unsafe_allow_html=True)
    secao("Abastecimentos Registrados")

    if not df_a.empty:
        df_a = df_a.sort_values("data", ascending=False).fillna("")
        fl1,fl2,fl3,fl4 = st.columns(4)
        f_di  = fl1.date_input("De",    value=date.today().replace(day=1), key="fdi_ab")
        f_df  = fl2.date_input("Até",   value=date.today(),                key="fdf_ab")
        f_v   = fl3.selectbox("Veículo",["TODOS"]+df_v["prefixo"].tolist(),  key="fv_ab")
        obfl  = lista_obras(todas=True)
        f_o   = fl4.selectbox("Obra",   obfl if obfl else ["TODAS"],         key="fo_ab")

        df_a["_dt"] = pd.to_datetime(df_a["data"],errors="coerce").dt.date
        fil2 = df_a[(df_a["_dt"]>=f_di)&(df_a["_dt"]<=f_df)]
        if f_v != "TODOS":           fil2 = fil2[fil2["prefixo"] == f_v]
        if f_o not in ("TODAS","") and "obra" in fil2.columns:
            fil2 = fil2[fil2["obra"] == f_o]

        ativos = fil2[fil2.get("status",pd.Series(["ATIVO"]*len(fil2))) == "ATIVO"]
        canel  = fil2[fil2.get("status",pd.Series(["ATIVO"]*len(fil2))) != "ATIVO"]

        tL = pd.to_numeric(ativos.get("quantidade",0),errors="coerce").sum()
        tR = pd.to_numeric(ativos.get("total",0),errors="coerce").sum()
        mk1,mk2,mk3 = st.columns(3)
        kpi(mk1,"Litros no Filtro", f"{tL:,.1f} L", "#1E40AF")
        kpi(mk2,"Gasto no Filtro",  f"R$ {tR:,.2f}","#DC2626")
        kpi(mk3,"Registros Ativos", str(len(ativos)),"#059669")
        st.markdown("<br>", unsafe_allow_html=True)

        tab1,tab2 = st.tabs([f"Ativos ({len(ativos)})", f"Cancelados ({len(canel)})"])
        with tab1:
            if ativos.empty: st.info("Nenhum registro ativo no período.")
            else:
                for r in ativos.head(60).to_dict("records"):
                    with st.expander(f"{r.get('data','')[:10]}  |  {r.get('prefixo','')}  |  {flt(r.get('quantidade')):,.1f} L  |  R$ {flt(r.get('total')):,.2f}  |  {r.get('obra','')}"):
                        ec1,ec2,ec3,ec4 = st.columns(4)
                        ec1.write(f"**Motorista:** {r.get('motorista','')}"); ec2.write(f"**Placa:** {r.get('placa','')}")
                        ec3.write(f"**Fornecedor:** {r.get('fornecedor','')}"); ec4.write(f"**Origem:** {r.get('origem','')}")
                        ec5,ec6 = st.columns(2)
                        ec5.write(f"**KM/Hor:** {r.get('horimetro','')}"); ec6.write(f"**Obs:** {r.get('observacao','')}")
                        with st.form(f"ed_{r.get('id')}"):
                            ne1,ne2,ne3 = st.columns(3)
                            nl = ne1.number_input("Litros",    value=flt(r.get("quantidade")), min_value=0.0, key=f"nl{r.get('id')}")
                            np_ = ne2.number_input("R$/L",     value=flt(r.get("valor_unitario")), min_value=0.0, key=f"np{r.get('id')}")
                            ol  = lista_obras()
                            oa  = r.get("obra","")
                            no_ = ne3.selectbox("Obra", ol, index=ol.index(oa) if oa in ol else 0, key=f"no{r.get('id')}") if ol else ne3.text_input("Obra", value=oa, key=f"no{r.get('id')}")
                            cs,cc = st.columns(2)
                            if cs.form_submit_button("Salvar Edição", use_container_width=True):
                                if update_data("abastecimentos", r.get("id"), {
                                    "quantidade":nl,"valor_unitario":np_,
                                    "total":round(nl*np_,2),"obra":no_
                                }): st.success("Atualizado."); st.rerun()
                            if cc.form_submit_button("Cancelar Registro", use_container_width=True):
                                supabase.table("abastecimentos").update({"status":"CANCELADO"}).eq("id",r.get("id")).execute()
                                _clear(); st.warning("Cancelado."); st.rerun()
        with tab2:
            if canel.empty: st.info("Nenhum cancelado.")
            else:
                for r in canel.head(30).to_dict("records"):
                    c1_,c2_ = st.columns([5,1])
                    c1_.write(f"{r.get('data','')[:10]} | {r.get('prefixo','')} | {flt(r.get('quantidade')):,.1f} L | {r.get('obra','-')}")
                    if c2_.button("Restaurar", key=f"rst{r.get('id')}"):
                        supabase.table("abastecimentos").update({"status":"ATIVO"}).eq("id",r.get("id")).execute()
                        _clear(); st.rerun()
    else:
        st.info("Nenhum abastecimento registrado.")


# ═══════════════════════════════════════════════════════
# 4 · TRANSFERÊNCIA CAMINHÃO-TANQUE
# ═══════════════════════════════════════════════════════
elif menu == "Transferência Caminhão-Tanque":
    st.markdown("## Transferência — Caminhão-Tanque")
    av("Registre a retirada de combustível do tanque fixo para o caminhão-tanque ir abastecer em campo. O saldo do tanque é atualizado automaticamente.", "in")

    df_v   = get_data("veiculos")
    df_t   = get_data("tanques")
    df_tr  = get_data("transferencias_tanque")
    saldos = todos_saldos()

    df_ct = df_v[df_v["tipo_veiculo"] == "Caminhão-Tanque"] if not df_v.empty and "tipo_veiculo" in df_v.columns else pd.DataFrame()
    obras_l = lista_obras()

    tab_r, tab_h = st.tabs(["Registrar Transferência","Histórico"])

    with tab_r:
        if df_t.empty:
            av("Cadastre ao menos um tanque fixo primeiro.", "lo")
        else:
            secao("Saldo Atual dos Tanques")
            ct_ = st.columns(min(len(df_t),5))
            for i,(_, row) in enumerate(df_t.iterrows()):
                nm=row.get("nome",""); cap=flt(row.get("capacidade")); sd=saldos.get(nm,0.0)
                with ct_[i%min(len(df_t),5)]:
                    tank_card(st.container(), nm, sd, cap)

            st.markdown("<hr>", unsafe_allow_html=True)
            with st.form("f_tr", clear_on_submit=True):
                ct1,ct2,ct3 = st.columns(3)
                data_tr  = ct1.date_input("Data")
                ficha_tr = ct2.text_input("Ficha / Documento")
                tanq_o   = ct3.selectbox("Tanque de Origem", df_t["nome"].tolist())

                ct4,ct5,ct6 = st.columns(3)
                if not df_ct.empty:
                    cam = ct4.selectbox("Caminhão-Tanque", df_ct["prefixo"].tolist())
                    ci  = df_ct[df_ct["prefixo"]==cam].iloc[0]
                    mot_ct = ci.get("motorista",""); plc_ct = ci.get("placa","")
                else:
                    cam = ct4.text_input("Caminhão-Tanque (prefixo)")
                    mot_ct = ""; plc_ct = ""

                mot_tr = ct5.text_input("Motorista", value=mot_ct)
                plc_tr = ct6.text_input("Placa",     value=plc_ct)

                ct7,ct8,ct9 = st.columns(3)
                qtd_tr  = ct7.number_input("Quantidade (L)", min_value=0.0, step=10.0)
                vu_tr   = ct8.number_input("Valor Unitário (R$/L)", min_value=0.0, step=0.001, format="%.3f")
                prod_tr = ct9.selectbox("Produto", ["Diesel S10","Diesel S500","Gasolina Comum"])

                ct10,ct11 = st.columns(2)
                if obras_l:
                    obra_tr = ct10.selectbox("Obra Atendida", obras_l)
                else:
                    obra_tr = ct10.text_input("Obra Atendida")
                obs_tr = ct11.text_input("Observação")

                tot_tr = round(qtd_tr * vu_tr, 2)
                sd_o   = saldos.get(tanq_o, 0.0)
                av(f"Total: <strong>R$ {tot_tr:,.2f}</strong> &nbsp;|&nbsp; Saldo de <strong>{tanq_o}</strong>: <strong>{sd_o:,.1f} L</strong> → Após: <strong>{sd_o-qtd_tr:,.1f} L</strong>", "in")
                if qtd_tr > sd_o > 0:
                    av(f"Quantidade ({qtd_tr:,.1f} L) excede o saldo disponível ({sd_o:,.1f} L).", "er")

                if st.form_submit_button("REGISTRAR TRANSFERÊNCIA", use_container_width=True):
                    if qtd_tr <= 0: st.error("Informe a quantidade.")
                    else:
                        if insert_data("transferencias_tanque", {
                            "data":str(data_tr),"numero_ficha":ficha_tr,
                            "tanque_origem":tanq_o,"caminhao_tanque":cam,
                            "placa":plc_tr,"motorista":mot_tr.upper(),
                            "produto":prod_tr,"quantidade":qtd_tr,
                            "valor_unitario":vu_tr,"total":tot_tr,
                            "obra":obra_tr,"observacao":obs_tr,
                            "status":"ATIVO","criado_por":st.session_state.usuario_logado,
                        }):
                            st.success("Transferência registrada.")
                            st.rerun()

    with tab_h:
        if df_tr.empty: st.info("Nenhuma transferência registrada.")
        else:
            df_tr = df_tr.sort_values("data",ascending=False).fillna("")
            h1,h2 = st.columns(2)
            hdi = h1.date_input("De",  value=date.today().replace(day=1), key="hdi_tr")
            hdf = h2.date_input("Até", value=date.today(),                key="hdf_tr")
            df_tr["_dt"] = pd.to_datetime(df_tr["data"],errors="coerce").dt.date
            fil_tr = df_tr[(df_tr["_dt"]>=hdi)&(df_tr["_dt"]<=hdf)]
            tL = pd.to_numeric(fil_tr.get("quantidade",0),errors="coerce").sum()
            tR = pd.to_numeric(fil_tr.get("total",0),errors="coerce").sum()
            m1,m2 = st.columns(2)
            kpi(m1,"Total Transferido",f"{tL:,.1f} L","#1E40AF")
            kpi(m2,"Valor Total",      f"R$ {tR:,.2f}","#DC2626")
            st.markdown("<br>", unsafe_allow_html=True)
            cols_tr = [c for c in ["data","tanque_origem","caminhao_tanque","motorista","produto","quantidade","valor_unitario","total","obra","status"] if c in fil_tr.columns]
            st.dataframe(fil_tr[cols_tr], use_container_width=True, hide_index=True)
            st.download_button("Exportar Excel", xl_limpo(fil_tr[cols_tr],"Transferências"),
                               f"Transferencias_{hdi}_{hdf}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# ═══════════════════════════════════════════════════════
# 5 · TANQUES / ESTOQUE
# ═══════════════════════════════════════════════════════
elif menu == "Tanques / Estoque":
    st.markdown("## Tanques / Estoque")

    df_t   = get_data("tanques")
    df_f   = get_data("fornecedores")
    df_ent = get_data("entradas_tanque")
    df_sai = get_data("abastecimentos")
    df_tr  = get_data("transferencias_tanque")
    saldos = todos_saldos()

    if not df_sai.empty and "status" in df_sai.columns: df_sai = df_sai[df_sai["status"] == "ATIVO"]
    if not df_tr.empty  and "status" in df_tr.columns:  df_tr  = df_tr[df_tr["status"]  == "ATIVO"]

    if not df_t.empty:
        secao("Situação Atual")
        ct_ = st.columns(min(len(df_t),5))
        for i,(_, row) in enumerate(df_t.iterrows()):
            nm=row.get("nome",""); cap=flt(row.get("capacidade")); sd=saldos.get(nm,0.0)
            with ct_[i%min(len(df_t),5)]:
                tank_card(st.container(), nm, sd, cap)
                if cap>0 and sd <= cap*0.15:
                    av("Nível crítico. Providenciar abastecimento.", "er")

    st.markdown("<hr>", unsafe_allow_html=True)
    aba_e, aba_h, aba_c = st.tabs(["Registrar Entrada (Compra)","Histórico de Movimentação","Cadastrar Tanques"])

    with aba_e:
        if df_t.empty: av("Cadastre um tanque primeiro na aba 'Cadastrar Tanques'.", "lo")
        else:
            with st.form("f_et", clear_on_submit=True):
                e1,e2,e3 = st.columns(3)
                data_e  = e1.date_input("Data da Entrega")
                ficha_e = e2.text_input("NF / Documento Fiscal")
                tanq_e  = e3.selectbox("Tanque de Destino", df_t["nome"].tolist())

                e4,e5,e6 = st.columns(3)
                fl_e = df_f["nome"].tolist() if not df_f.empty else []
                forn_e = e4.selectbox("Distribuidora",fl_e) if fl_e else e4.text_input("Distribuidora")
                comb_e = e5.selectbox("Produto",["Diesel S10","Diesel S500","Gasolina Comum"])
                obs_e  = e6.text_input("Observação")

                e7,e8 = st.columns(2)
                qtd_e  = e7.number_input("Quantidade (L)", min_value=0.0, step=100.0)
                vu_e   = e8.number_input("R$/L", min_value=0.0, step=0.001, format="%.3f")
                tot_e  = round(qtd_e * vu_e, 2)
                obr_e  = lista_obras()
                obra_e = st.selectbox("Obra / Centro de Custo", obr_e) if obr_e else st.text_input("Obra")
                sd_at  = saldos.get(tanq_e, 0.0)
                av(f"Valor total: <strong>R$ {tot_e:,.2f}</strong> &nbsp;|&nbsp; Saldo atual: <strong>{sd_at:,.1f} L</strong> → Após entrada: <strong>{sd_at+qtd_e:,.1f} L</strong>", "in")

                if st.form_submit_button("REGISTRAR ENTRADA", use_container_width=True):
                    if qtd_e <= 0: st.error("Informe a quantidade.")
                    else:
                        if insert_data("entradas_tanque",{
                            "data":str(data_e),"numero_ficha":ficha_e,"nome_tanque":tanq_e,
                            "fornecedor":forn_e,"combustivel":comb_e,"quantidade":qtd_e,
                            "valor_unitario":vu_e,"total":tot_e,"obra":obra_e,"observacao":obs_e,
                            "criado_por":st.session_state.usuario_logado,
                        }):
                            st.success(f"Entrada registrada. Novo saldo de {tanq_e}: {sd_at+qtd_e:,.1f} L")
                            st.rerun()

    with aba_h:
        if df_t.empty: st.info("Nenhum tanque cadastrado.")
        else:
            hc1,hc2,hc3 = st.columns(3)
            ts = hc1.selectbox("Tanque", df_t["nome"].tolist(), key="ht_sel")
            hdi_ = hc2.date_input("De",  value=date.today().replace(day=1), key="hdi_tk")
            hdf_ = hc3.date_input("Até", value=date.today(),                key="hdf_tk")

            def ft2(df, col, val):
                if df.empty or col not in df.columns: return pd.DataFrame()
                df = df[df[col]==val].copy()
                df["_dt"]=pd.to_datetime(df.get("data",""),errors="coerce").dt.date
                return df[df["_dt"].notna()&(df["_dt"]>=hdi_)&(df["_dt"]<=hdf_)]

            eh = ft2(df_ent,"nome_tanque",ts)
            sh = ft2(df_sai[df_sai.get("origem",pd.Series(dtype=str))=="Tanque Interno"] if not df_sai.empty and "origem" in df_sai.columns else pd.DataFrame(),"nome_tanque",ts)
            th = ft2(df_tr,"tanque_origem",ts)

            te=pd.to_numeric(eh.get("quantidade",pd.Series(dtype=float)),errors="coerce").sum()
            ts_=pd.to_numeric(sh.get("quantidade",pd.Series(dtype=float)),errors="coerce").sum()
            tt=pd.to_numeric(th.get("quantidade",pd.Series(dtype=float)),errors="coerce").sum()
            m1,m2,m3,m4 = st.columns(4)
            kpi(m1,"Entradas",       f"{te:,.1f} L","#059669")
            kpi(m2,"Saídas Diretas", f"{ts_:,.1f} L","#DC2626")
            kpi(m3,"Transf. Caminhão",f"{tt:,.1f} L","#D97706")
            kpi(m4,"Saldo Período",  f"{te-ts_-tt:,.1f} L","#1E40AF")
            st.markdown("<br>", unsafe_allow_html=True)
            if te>0 or ts_>0 or tt>0:
                per = f"{hdi_.strftime('%d/%m/%Y')} a {hdf_.strftime('%d/%m/%Y')}"
                xl_ = xl_tanque(eh, sh, th, ts, per)
                st.download_button("Exportar Movimentação Excel", xl_,
                                   f"Tanque_{ts}_{hdi_}.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                st.info("Nenhum movimento no período.")

    with aba_c:
        with st.form("f_ct",clear_on_submit=True):
            c1_,c2_ = st.columns(2)
            nm_t = c1_.text_input("Nome / Identificação")
            cap_ = c2_.number_input("Capacidade Máxima (L)", min_value=0.0, step=500.0)
            if st.form_submit_button("Salvar Tanque", use_container_width=True):
                if nm_t:
                    if insert_data("tanques",{"nome":nm_t.upper(),"capacidade":cap_,
                                              "criado_por":st.session_state.usuario_logado}):
                        st.success("Tanque salvo."); st.rerun()
                else: st.error("Nome obrigatório.")
        if not df_t.empty:
            st.markdown("<hr>", unsafe_allow_html=True)
            for _, r in df_t.iterrows():
                c1_,c2_ = st.columns([5,1])
                sd = saldos.get(r.get("nome",""),0.0)
                c1_.write(f"**{r['nome']}** — Cap: {flt(r.get('capacidade')):,.0f} L | Saldo: {sd:,.1f} L")
                if c2_.button("Excluir", key=f"dt_{r['id']}"):
                    if delete_data("tanques",r["id"]): st.rerun()


# ═══════════════════════════════════════════════════════
# 6 · BOLETIM DE TRANSPORTE
# ═══════════════════════════════════════════════════════
elif menu == "Boletim de Transporte":
    st.markdown("## Boletim Diário de Produção")
    df_v = get_data("veiculos")
    if df_v.empty: av("Cadastre veículos em Frota e Equipamentos primeiro.","lo"); st.stop()
    obras_l = lista_obras()

    with st.form("f_bp",clear_on_submit=True):
        c1,c2,c3 = st.columns(3)
        dt_ = c1.date_input("Data", value=date.today())
        pf_ = c2.selectbox("Veículo / Equipamento", df_v["prefixo"].tolist())
        vi  = df_v[df_v["prefixo"]==pf_].iloc[0]
        mt_ = c3.text_input("Motorista / Operador", value=vi.get("motorista",""))

        c4,c5,c6 = st.columns(3)
        if obras_l: ob_ = c4.selectbox("Obra", obras_l)
        else:       ob_ = c4.text_input("Obra")
        or_ = c5.text_input("Origem / Jazida")
        ds_ = c6.text_input("Destino / Trecho")

        c7,c8,c9,c10 = st.columns(4)
        op_ = c7.selectbox("Tipo de Operação",[
            "Transporte de Massa/CBUQ","Transporte de Fresado",
            "Terraplanagem","Venda de Massa","Ocioso/Manutenção"])
        ks_ = c8.number_input("KM Inicial", min_value=0.0)
        kc_ = c9.number_input("KM Final",   min_value=0.0)
        cr_ = c10.number_input("Viagens",    min_value=0, step=1)

        c11,c12 = st.columns(2)
        tn_ = c11.number_input("Toneladas", min_value=0.0)
        ob2_= c12.text_input("Observações")

        if st.form_submit_button("SALVAR BOLETIM", use_container_width=True):
            if op_ != "Ocioso/Manutenção" and cr_ <= 0:
                st.error("Informe o número de viagens.")
            else:
                if insert_data("producao",{
                    "data":str(dt_),"prefixo":pf_,"motorista":mt_.upper(),
                    "obra":ob_,"tipo_operacao":op_,"origem":or_.upper(),
                    "destino":ds_.upper(),"km_saida":ks_,"km_chegada":kc_,
                    "carradas":cr_,"toneladas":tn_,"observacao":ob2_,
                    "criado_por":st.session_state.usuario_logado,
                }):
                    st.success("Boletim salvo."); st.rerun()

    df_b = get_data("producao")
    if not df_b.empty:
        st.markdown("<hr>", unsafe_allow_html=True)
        secao("Últimos Boletins")
        df_br = df_b.sort_values("data",ascending=False).head(30).fillna("")
        cols_ = [c for c in ["data","prefixo","motorista","obra","tipo_operacao","origem","destino","carradas","toneladas"] if c in df_br.columns]
        st.dataframe(df_br[cols_], use_container_width=True, hide_index=True)
        st.download_button("Exportar Excel", xl_limpo(df_br[cols_],"Boletins"),
                           f"Boletins_{date.today()}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# ═══════════════════════════════════════════════════════
# 7 · FROTA E EQUIPAMENTOS
# ═══════════════════════════════════════════════════════
elif menu == "Frota e Equipamentos":
    st.markdown("## Frota e Equipamentos")
    df_v  = get_data("veiculos")
    df_ab = get_data("abastecimentos")
    if not df_ab.empty and "status" in df_ab.columns:
        df_ab = df_ab[df_ab["status"] == "ATIVO"]

    with st.expander("Cadastrar novo veículo / equipamento", expanded=True):
        # Detecta quais colunas existem na tabela veiculos
        cols_v = set(df_v.columns.tolist()) if not df_v.empty else set()
        tem_tipo_veiculo    = "tipo_veiculo"            in cols_v or df_v.empty
        tem_comb_padrao     = "tipo_combustivel_padrao" in cols_v or df_v.empty
        tem_motorista_col   = "motorista"               in cols_v or df_v.empty

        with st.form("f_v", clear_on_submit=True):
            c1,c2,c3 = st.columns(3)
            pf_ = c1.text_input("Código / Prefixo")
            pl_ = c2.text_input("Placa")
            ct_ = c3.selectbox("Categoria", ["Veículo","Equipamento"])

            c4,c5,c6 = st.columns(3)
            mt_ = c4.text_input("Motorista / Operador Fixo")
            cb_ = c5.selectbox("Combustível Padrão", ["Diesel S10","Diesel S500","Gasolina Comum"])
            tv_ = c6.selectbox("Tipo", ["Veículo","Equipamento","Caminhão-Tanque"])

            if st.form_submit_button("Salvar", use_container_width=True):
                if pf_:
                    # Monta o payload com todas as colunas — insert_data remove automaticamente as ausentes
                    payload = {
                        "prefixo":                  pf_.upper(),
                        "placa":                    pl_.upper(),
                        "categoria":                ct_,
                        "motorista":                mt_.upper(),
                        "tipo_combustivel_padrao":  cb_,
                        "tipo_veiculo":             tv_,
                        "criado_por":               st.session_state.usuario_logado,
                    }
                    if insert_data("veiculos", payload):
                        st.success("Salvo com sucesso.")
                        st.rerun()
                else:
                    st.error("Prefixo obrigatório.")

    if not df_v.empty:
        st.markdown("<hr>", unsafe_allow_html=True)
        tab_v, tab_c = st.tabs(["Veículos e Equipamentos","Caminhões-Tanque"])
        for tab, filt in [(tab_v, lambda df: df[df.get("tipo_veiculo",pd.Series(dtype=str))!="Caminhão-Tanque"] if "tipo_veiculo" in df.columns else df),
                          (tab_c, lambda df: df[df.get("tipo_veiculo",pd.Series(dtype=str))=="Caminhão-Tanque"] if "tipo_veiculo" in df.columns else pd.DataFrame())]:
            with tab:
                df_fil = filt(df_v)
                if df_fil.empty: st.info("Nenhum registro.")
                else:
                    for _,r in df_fil.iterrows():
                        cons = pd.to_numeric(df_ab[df_ab["prefixo"]==r.get("prefixo","")].get("quantidade",0),errors="coerce").sum() if not df_ab.empty and "prefixo" in df_ab.columns else 0
                        c1_,c2_ = st.columns([6,1])
                        c1_.write(f"**{r.get('prefixo','')}** | {r.get('tipo_veiculo',r.get('categoria','-'))} | {r.get('placa','')} | Op: {r.get('motorista','')} | Consumo acum.: {cons:,.0f} L")
                        if c2_.button("Excluir", key=f"dv_{r.get('id','x')}"):
                            if delete_data("veiculos",r.get("id")): st.rerun()


# ═══════════════════════════════════════════════════════
# 8 · OBRAS
# ═══════════════════════════════════════════════════════
elif menu == "Obras":
    st.markdown("## Obras e Projetos")
    av("Obras cadastradas aqui ficam disponíveis em todos os módulos do sistema.", "in")
    df_o  = get_data("obras")
    df_ab = get_data("abastecimentos")
    if not df_ab.empty and "status" in df_ab.columns: df_ab = df_ab[df_ab["status"]=="ATIVO"]

    with st.expander("Cadastrar nova obra",expanded=True):
        with st.form("f_ob",clear_on_submit=True):
            o1,o2,o3 = st.columns(3)
            no_ = o1.text_input("Nome da Obra")
            cd_ = o2.text_input("Código / ART")
            st_ = o3.selectbox("Status",["Ativa","Pausada","Encerrada"])
            o4,o5 = st.columns(2)
            lc_ = o4.text_input("Município / Localização")
            rs_ = o5.text_input("Responsável Técnico")
            ob_ = st.text_input("Observações")
            if st.form_submit_button("Salvar Obra",use_container_width=True):
                if no_:
                    if insert_data("obras",{
                        "nome":no_.upper(),"codigo":cd_.upper(),"status":st_,
                        "local":lc_.upper(),"responsavel":rs_.upper(),
                        "observacao":ob_,"criado_por":st.session_state.usuario_logado,
                    }):
                        st.success("Obra salva."); st.rerun()
                else: st.error("Nome obrigatório.")

    if not df_o.empty:
        st.markdown("<hr>", unsafe_allow_html=True)
        for _,r in df_o.iterrows():
            nm_o=r.get("nome",""); st_o=r.get("status","Ativa")
            ic={"Ativa":"●","Pausada":"◐","Encerrada":"○"}.get(st_o,"●")
            with st.expander(f"{ic}  {nm_o}  |  {r.get('codigo','')}  |  {st_o}"):
                oc1,oc2,oc3 = st.columns(3)
                oc1.write(f"**Local:** {r.get('local','-')}"); oc2.write(f"**Responsável:** {r.get('responsavel','-')}"); oc3.write(f"**Obs:** {r.get('observacao','-')}")
                if not df_ab.empty and "obra" in df_ab.columns:
                    df_oa = df_ab[df_ab["obra"]==nm_o]
                    tl=pd.to_numeric(df_oa.get("quantidade",0),errors="coerce").sum()
                    tr=pd.to_numeric(df_oa.get("total",0),errors="coerce").sum()
                    ok1,ok2,ok3 = st.columns(3)
                    kpi(ok1,"Litros consumidos",f"{tl:,.1f} L","#1E40AF")
                    kpi(ok2,"Gasto total",       f"R$ {tr:,.2f}","#DC2626")
                    kpi(ok3,"Abastecimentos",    str(len(df_oa)),"#059669")
                    st.markdown("<br>", unsafe_allow_html=True)
                cs,cd_ = st.columns(2)
                ns=cs.selectbox("Status",["Ativa","Pausada","Encerrada"],
                                index=["Ativa","Pausada","Encerrada"].index(st_o) if st_o in ["Ativa","Pausada","Encerrada"] else 0,
                                key=f"sto_{r['id']}")
                if cs.button("Atualizar Status",key=f"uo_{r['id']}"):
                    if update_data("obras",r["id"],{"status":ns}): st.rerun()
                if cd_.button("Excluir Obra",key=f"do_{r['id']}"):
                    if delete_data("obras",r["id"]): st.rerun()


# ═══════════════════════════════════════════════════════
# 9 · FORNECEDORES
# ═══════════════════════════════════════════════════════
elif menu == "Fornecedores":
    st.markdown("## Fornecedores")
    df_f  = get_data("fornecedores")
    df_et = get_data("entradas_tanque")
    df_ab = get_data("abastecimentos")
    if not df_ab.empty and "status" in df_ab.columns: df_ab=df_ab[df_ab["status"]=="ATIVO"]

    with st.expander("Cadastrar novo fornecedor",expanded=True):
        with st.form("f_fn",clear_on_submit=True):
            c1,c2 = st.columns(2)
            nm_=c1.text_input("Nome Fantasia"); rz_=c2.text_input("Razão Social")
            c3,c4 = st.columns(2)
            cn_=c3.text_input("CNPJ"); tl_=c4.text_input("Telefone")
            st.markdown("**Dados Bancários**")
            c5,c6,c7 = st.columns(3)
            bn_=c5.text_input("Banco"); ag_=c6.text_input("Agência"); ct_=c7.text_input("Conta")
            c8,c9 = st.columns(2)
            px_=c8.text_input("Chave PIX"); tp_=c9.selectbox("Tipo de Conta",["Corrente","Poupança","Outros"])
            if st.form_submit_button("Salvar Fornecedor",use_container_width=True):
                if nm_:
                    if insert_data("fornecedores",{
                        "nome":nm_,"razao_social":rz_,"cnpj":cn_,"telefone":tl_,
                        "banco":bn_,"agencia":ag_,"conta":ct_,"pix":px_,
                        "tipo_conta":tp_,"criado_por":st.session_state.usuario_logado,
                    }):
                        st.success("Fornecedor salvo."); st.rerun()
                else: st.error("Nome obrigatório.")

    if not df_f.empty:
        st.markdown("<hr>", unsafe_allow_html=True)
        for _,r in df_f.iterrows():
            nf_=r.get("nome","")
            vp=pd.to_numeric(df_ab[df_ab.get("fornecedor","") == nf_].get("total",0) if not df_ab.empty and "fornecedor" in df_ab.columns else pd.Series(dtype=float),errors="coerce").sum()
            vt=pd.to_numeric(df_et[df_et.get("fornecedor","") == nf_].get("total",0) if not df_et.empty and "fornecedor" in df_et.columns else pd.Series(dtype=float),errors="coerce").sum()
            with st.expander(f"{nf_}  |  CNPJ: {r.get('cnpj','-')}  |  Acumulado: R$ {vp+vt:,.2f}"):
                fc1,fc2,fc3 = st.columns(3)
                fc1.write(f"**Razão Social:** {r.get('razao_social','-')}")
                fc2.write(f"**Banco:** {r.get('banco','-')} | Ag: {r.get('agencia','-')} | Cta: {r.get('conta','-')}")
                fc3.write(f"**PIX:** {r.get('pix','-')} | **Tipo:** {r.get('tipo_conta','-')}")
                if st.button("Excluir",key=f"df_{r['id']}"):
                    if delete_data("fornecedores",r["id"]): st.rerun()


# ═══════════════════════════════════════════════════════
# 10 · RELATÓRIOS E FECHAMENTOS
# ═══════════════════════════════════════════════════════
elif menu == "Relatórios e Fechamentos":
    st.markdown("## Relatórios e Fechamentos")
    ab1,ab2,ab3,ab4 = st.tabs([
        "Abastecimentos por Fornecedor",
        "Fechamento de Tanques",
        "Produção",
        "Rastreabilidade por Obra"
    ])

    with ab1:
        secao("Relatório de Abastecimentos")
        df_ab_r = get_data("abastecimentos")
        df_f_r  = get_data("fornecedores")
        if not df_ab_r.empty and "status" in df_ab_r.columns:
            df_ab_r = df_ab_r[df_ab_r["status"]=="ATIVO"]

        r1,r2,r3,r4 = st.columns(4)
        dti = r1.date_input("De",  value=date.today().replace(day=1), key="r1di")
        dtf = r2.date_input("Até", value=date.today(),                key="r1df")
        fl  = ["TODOS"]+(df_f_r["nome"].tolist() if not df_f_r.empty else [])
        fs  = r3.selectbox("Fornecedor", fl, key="r1fs")
        obr = lista_obras(todas=True)
        os_ = r4.selectbox("Obra", obr if obr else ["TODAS"], key="r1os")

        if st.button("Gerar Relatório",key="btn_r1"):
            df_fil = df_ab_r.copy() if not df_ab_r.empty else pd.DataFrame()
            if not df_fil.empty and "data" in df_fil.columns:
                df_fil["_dt"]=pd.to_datetime(df_fil["data"],errors="coerce").dt.date
                df_fil=df_fil[(df_fil["_dt"]>=dti)&(df_fil["_dt"]<=dtf)]
                if fs!="TODOS" and "fornecedor" in df_fil.columns: df_fil=df_fil[df_fil["fornecedor"]==fs]
                if os_!="TODAS" and "obra" in df_fil.columns:      df_fil=df_fil[df_fil["obra"]==os_]
            if df_fil.empty:
                st.warning("Nenhum registro no período/filtro.")
            else:
                tl_=pd.to_numeric(df_fil.get("quantidade",0),errors="coerce").sum()
                tr_=pd.to_numeric(df_fil.get("total",0),errors="coerce").sum()
                m1,m2,m3=st.columns(3)
                kpi(m1,"Total Litros",f"{tl_:,.1f} L","#1E40AF")
                kpi(m2,"Total R$",    f"R$ {tr_:,.2f}","#DC2626")
                kpi(m3,"Registros",   str(len(df_fil)),"#059669")
                st.markdown("<br>", unsafe_allow_html=True)
                per=f"{dti.strftime('%d/%m/%Y')} a {dtf.strftime('%d/%m/%Y')}"
                xl_=xl_abastecimentos(df_fil,f"RELATÓRIO — {fs.upper() if fs!='TODOS' else 'GERAL'}",per)
                st.download_button("Baixar Excel", xl_,
                                   f"Relatorio_{fs}_{dti}.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                   use_container_width=True)
                cols_s=[c for c in ["data","prefixo","placa","motorista","fornecedor","tipo_combustivel","quantidade","valor_unitario","total","obra"] if c in df_fil.columns]
                st.dataframe(df_fil[cols_s], use_container_width=True, hide_index=True)

    with ab2:
        secao("Fechamento de Tanques")
        df_et_r = get_data("entradas_tanque")
        df_t_r  = get_data("tanques")
        df_ab2  = get_data("abastecimentos")
        df_tr2  = get_data("transferencias_tanque")
        if not df_ab2.empty and "status" in df_ab2.columns: df_ab2=df_ab2[df_ab2["status"]=="ATIVO"]
        if not df_tr2.empty and "status" in df_tr2.columns: df_tr2=df_tr2[df_tr2["status"]=="ATIVO"]

        tc1,tc2,tc3 = st.columns(3)
        tdi = tc1.date_input("De",  value=date.today().replace(day=1), key="t2di")
        tdf = tc2.date_input("Até", value=date.today(),                key="t2df")
        ts_ = tc3.selectbox("Tanque", df_t_r["nome"].tolist() if not df_t_r.empty else ["—"])

        if st.button("Gerar Fechamento",key="btn_t2"):
            def flt2(df,col,val):
                if df.empty or col not in df.columns: return pd.DataFrame()
                df=df[df[col]==val].copy()
                df["_dt"]=pd.to_datetime(df.get("data",""),errors="coerce").dt.date
                return df[df["_dt"].notna()&(df["_dt"]>=tdi)&(df["_dt"]<=tdf)]

            ef=flt2(df_et_r,"nome_tanque",ts_)
            sf=flt2(df_ab2[df_ab2.get("origem",pd.Series(dtype=str))=="Tanque Interno"] if not df_ab2.empty and "origem" in df_ab2.columns else pd.DataFrame(),"nome_tanque",ts_)
            tf=flt2(df_tr2,"tanque_origem",ts_)

            te=pd.to_numeric(ef.get("quantidade",pd.Series(dtype=float)),errors="coerce").sum()
            ts2=pd.to_numeric(sf.get("quantidade",pd.Series(dtype=float)),errors="coerce").sum()
            tt=pd.to_numeric(tf.get("quantidade",pd.Series(dtype=float)),errors="coerce").sum()
            m1,m2,m3,m4=st.columns(4)
            kpi(m1,"Entradas",        f"{te:,.1f} L","#059669")
            kpi(m2,"Saídas Diretas",  f"{ts2:,.1f} L","#DC2626")
            kpi(m3,"Transf. Caminhão",f"{tt:,.1f} L","#D97706")
            kpi(m4,"Saldo Período",   f"{te-ts2-tt:,.1f} L","#1E40AF")
            st.markdown("<br>", unsafe_allow_html=True)
            if te>0 or ts2>0 or tt>0:
                per=f"{tdi.strftime('%d/%m/%Y')} a {tdf.strftime('%d/%m/%Y')}"
                xl_=xl_tanque(ef,sf,tf,ts_,per)
                st.download_button("Baixar Excel",xl_,
                                   f"Fechamento_{ts_}_{tdi}.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                st.info("Nenhum movimento no período.")

    with ab3:
        secao("Boletins de Produção")
        df_pr=get_data("producao")
        p1,p2=st.columns(2)
        pd1=p1.date_input("De",  value=date.today().replace(day=1), key="p3di")
        pd2=p2.date_input("Até", value=date.today(),                key="p3df")
        if st.button("Extrair",key="btn_p3"):
            if not df_pr.empty and "data" in df_pr.columns:
                df_pr["_dt"]=pd.to_datetime(df_pr["data"],errors="coerce").dt.date
                df_pf=df_pr[(df_pr["_dt"]>=pd1)&(df_pr["_dt"]<=pd2)]
                if not df_pf.empty:
                    tt=pd.to_numeric(df_pf.get("toneladas",0),errors="coerce").sum()
                    tv=int(pd.to_numeric(df_pf.get("carradas",0),errors="coerce").sum())
                    m1,m2=st.columns(2)
                    kpi(m1,"Toneladas",f"{tt:,.1f} t","#059669")
                    kpi(m2,"Viagens",  str(tv),"#1E40AF")
                    st.markdown("<br>", unsafe_allow_html=True)
                    xl_=xl_limpo(df_pf.drop(columns=["_dt"],errors="ignore"),"Producao")
                    st.download_button("Baixar Excel",xl_,
                                       f"Producao_{pd1}_{pd2}.xlsx",
                                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                    st.dataframe(df_pf.drop(columns=["_dt"],errors="ignore"),
                                 use_container_width=True,hide_index=True)
                else: st.info("Nenhum boletim no período.")

    with ab4:
        secao("Rastreabilidade por Obra")
        obr_r = lista_obras()
        if not obr_r: st.warning("Nenhuma obra cadastrada.")
        else:
            cr1,cr2,cr3=st.columns(3)
            ob_r=cr1.selectbox("Obra",obr_r,key="rast_ob")
            dri =cr2.date_input("De",  value=date.today().replace(day=1), key="rast_di")
            drf =cr3.date_input("Até", value=date.today(),                key="rast_df")

            if st.button("Gerar Rastreabilidade",key="btn_rast"):
                def gr(table,col,di,df_):
                    d=get_data(table)
                    if d.empty or col not in d.columns: return pd.DataFrame()
                    if "status" in d.columns: d=d[d["status"]=="ATIVO"]
                    d["_dt"]=pd.to_datetime(d.get("data",""),errors="coerce").dt.date
                    return d[(d[col]==ob_r)&d["_dt"].notna()&(d["_dt"]>=di)&(d["_dt"]<=df_)]

                dab=gr("abastecimentos","obra",dri,drf)
                dtr=gr("transferencias_tanque","obra",dri,drf)
                dpr=gr("producao","obra",dri,drf)

                tla=pd.to_numeric(dab.get("quantidade",0),errors="coerce").sum()
                tra=pd.to_numeric(dab.get("total",0),errors="coerce").sum()
                tlt=pd.to_numeric(dtr.get("quantidade",0),errors="coerce").sum()
                trt=pd.to_numeric(dtr.get("total",0),errors="coerce").sum()
                ttn=pd.to_numeric(dpr.get("toneladas",0),errors="coerce").sum()
                tvg=int(pd.to_numeric(dpr.get("carradas",0),errors="coerce").sum())

                m1,m2,m3,m4=st.columns(4)
                kpi(m1,"Litros Totais",   f"{tla+tlt:,.1f} L","#1E40AF")
                kpi(m2,"Gasto Total",     f"R$ {tra+trt:,.2f}","#DC2626")
                kpi(m3,"Toneladas",       f"{ttn:,.1f} t","#059669")
                kpi(m4,"Viagens",         str(tvg),"#7C3AED")
                st.markdown("<br>", unsafe_allow_html=True)

                if not dab.empty:
                    secao("Abastecimentos")
                    cs=[c for c in ["data","prefixo","motorista","fornecedor","tipo_combustivel","quantidade","total","origem"] if c in dab.columns]
                    st.dataframe(dab[cs],use_container_width=True,hide_index=True)
                if not dtr.empty:
                    secao("Transferências Caminhão-Tanque")
                    cs=[c for c in ["data","tanque_origem","caminhao_tanque","motorista","produto","quantidade","total"] if c in dtr.columns]
                    st.dataframe(dtr[cs],use_container_width=True,hide_index=True)
                if not dpr.empty:
                    secao("Boletins de Produção")
                    cs=[c for c in ["data","prefixo","motorista","tipo_operacao","origem","destino","carradas","toneladas"] if c in dpr.columns]
                    st.dataframe(dpr[cs],use_container_width=True,hide_index=True)

                buf_r=io.BytesIO()
                with pd.ExcelWriter(buf_r,engine="xlsxwriter") as wr:
                    if not dab.empty: dab.drop(columns=["_dt"],errors="ignore").to_excel(wr,index=False,sheet_name="Abastecimentos")
                    if not dtr.empty: dtr.drop(columns=["_dt"],errors="ignore").to_excel(wr,index=False,sheet_name="Transferências")
                    if not dpr.empty: dpr.drop(columns=["_dt"],errors="ignore").to_excel(wr,index=False,sheet_name="Produção")
                st.download_button("Baixar Rastreabilidade Completa",buf_r.getvalue(),
                                   f"Rastreabilidade_{ob_r}_{dri}_{drf}.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                   use_container_width=True)


# ═══════════════════════════════════════════════════════
# 11 · USUÁRIOS E ACESSOS
# ═══════════════════════════════════════════════════════
elif menu == "Usuários e Acessos":
    if st.session_state.perfil_logado != "Admin":
        st.error("Acesso restrito a administradores."); st.stop()
    st.markdown("## Usuários e Acessos")
    av("Senhas armazenadas com hash SHA-256. Novos usuários já recebem senha protegida.", "in")

    with st.form("f_usr",clear_on_submit=True):
        c1,c2=st.columns(2)
        nmu=c1.text_input("Nome Completo"); lgu=c2.text_input("Login")
        c3,c4=st.columns(2)
        snu=c3.text_input("Senha",type="password"); pfu=c4.selectbox("Perfil",["Operador","Admin"])
        if st.form_submit_button("Criar Usuário",use_container_width=True):
            if nmu and lgu and snu:
                if insert_data("usuarios",{"nome":nmu,"login":lgu,"senha":hsh(snu),"perfil":pfu}):
                    st.success("Usuário criado."); st.rerun()
            else: st.error("Preencha todos os campos.")

    df_u=get_data("usuarios")
    if not df_u.empty:
        st.markdown("<hr>", unsafe_allow_html=True)
        secao("Usuários Cadastrados")
        for _,r in df_u.iterrows():
            c1_,c2_,c3_=st.columns([4,1,1])
            c1_.write(f"**{r.get('nome','')}** ({r.get('login','')}) — {r.get('perfil','')}")
            if c2_.button("Reset",key=f"rstu_{r['id']}"):
                st.session_state[f"rst_{r['id']}"]=True
            if c3_.button("Excluir",key=f"delu_{r['id']}"):
                if delete_data("usuarios",r["id"]): st.rerun()
            if st.session_state.get(f"rst_{r['id']}"):
                with st.form(f"rf_{r['id']}"):
                    ns_=st.text_input("Nova Senha",type="password",key=f"ns_{r['id']}")
                    if st.form_submit_button("Confirmar"):
                        if ns_:
                            if update_data("usuarios",r["id"],{"senha":hsh(ns_)}):
                                st.success("Senha atualizada.")
                                st.session_state.pop(f"rst_{r['id']}",None)
                                st.rerun()
