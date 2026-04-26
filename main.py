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

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.main { background-color: #F5F7FA; }
[data-testid="stSidebar"] { background: #0F1923; }
[data-testid="stSidebar"] * { color: #C9D4E0 !important; }
[data-testid="stSidebar"] h3 { color: #1D9E75 !important; }
.stTextInput>label, .stSelectbox>label, .stNumberInput>label,
.stDateInput>label, .stTextArea>label {
    font-size: 11px !important; text-transform: uppercase;
    color: #6B7A8D; font-weight: 600; letter-spacing: 0.05em;
}
div.stButton > button:first-child {
    background: #1D9E75; color: white; border: none;
    border-radius: 8px; font-weight: 600; padding: .5rem 1.25rem;
}
div.stButton > button:first-child:hover { background: #0F6E56; }
div[data-testid="stForm"] {
    border: 1px solid #E2E8F0; border-radius: 12px;
    padding: 1.25rem 1.5rem; background: white;
    box-shadow: 0 1px 4px rgba(0,0,0,.04);
}
.banner-ok  { background:#EAF3DE; color:#3B6D11; border:1px solid #C0DD97;
              border-radius:8px; padding:10px 14px; font-weight:600; font-size:13px; margin-bottom:1rem; }
.banner-low { background:#FAEEDA; color:#854F0B; border:1px solid #FAC775;
              border-radius:8px; padding:10px 14px; font-weight:600; font-size:13px; margin-bottom:1rem; }
.banner-err { background:#FCEBEB; color:#A32D2D; border:1px solid #F0B0AE;
              border-radius:8px; padding:10px 14px; font-weight:600; font-size:13px; margin-bottom:1rem; }
.banner-info{ background:#E6F1FB; color:#185FA5; border:1px solid #A8C9EE;
              border-radius:8px; padding:10px 14px; font-weight:600; font-size:13px; margin-bottom:1rem; }
.kpi-box { background:white; border:1px solid #E2E8F0; border-radius:10px;
           padding:1rem; text-align:center; height:100%; }
.kpi-box h3 { margin:0; font-size:22px; color:#0F1923; }
.kpi-box p  { margin:0; font-size:11px; color:#6B7A8D; text-transform:uppercase; font-weight:bold; }
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
# EXPORTAÇÃO — EXCEL PADRÃO COPA (fallback xlsxwriter)
# ═══════════════════════════════════════════════════════════════════
def gerar_excel_copa(df: pd.DataFrame, dados_forn: dict,
                     periodo: str, obra: str, nome_forn: str = "") -> bytes:
    df = df.fillna("").copy()
    dias_pt = {0:"SEG",1:"TER",2:"QUA",3:"QUI",4:"SEX",5:"SÁB",6:"DOM"}

    # Tenta usar template físico se existir
    template = "template_posto.xlsx"
    if os.path.exists(template):
        from openpyxl import load_workbook
        wb = load_workbook(template); ws = wb.active
        ws["D1"] = obra.upper(); ws["D3"] = periodo.upper()
        ws["J1"] = dados_forn.get("razao_social", dados_forn.get("nome","")).upper()
        ws["J2"] = dados_forn.get("agencia",""); ws["J3"] = dados_forn.get("conta","")
        ws["M1"] = dados_forn.get("pix",""); ws["M2"] = dados_forn.get("tipo_conta",""); ws["M3"] = dados_forn.get("banco","")
        row0 = 8
        for i,(_,r) in enumerate(df.iterrows()):
            dia_str = ""
            try: dia_str = dias_pt[datetime.strptime(str(r.get("data",""))[:10],"%Y-%m-%d").weekday()]
            except: pass
            qtd  = float(r.get("quantidade",    0) or 0)
            vunt = float(r.get("valor_unitario", 0) or 0)
            tot  = float(r.get("total",          0) or 0)
            ws.cell(row0+i,1,str(r.get("data",""))[:10]); ws.cell(row0+i,2,dia_str)
            ws.cell(row0+i,3,str(r.get("numero_ficha",""))); ws.cell(row0+i,4,str(r.get("placa","")))
            ws.cell(row0+i,5,str(r.get("prefixo",""))); ws.cell(row0+i,6,str(r.get("motorista","")))
            ws.cell(row0+i,7,str(r.get("fornecedor",""))); ws.cell(row0+i,8,str(r.get("tipo_combustivel","")))
            ws.cell(row0+i,9,qtd).number_format="#,##0.00"
            ws.cell(row0+i,10,vunt).number_format='"R$" #,##0.00'
            ws.cell(row0+i,11,tot).number_format='"R$" #,##0.00'
            ws.cell(row0+i,12,str(r.get("horimetro",""))); ws.cell(row0+i,13,str(r.get("observacao","")))
        buf = io.BytesIO(); wb.save(buf); return buf.getvalue()

    # ── Fallback xlsxwriter ──────────────────────────────────────────
    import xlsxwriter
    buf = io.BytesIO(); wb = xlsxwriter.Workbook(buf)
    ws  = wb.add_worksheet("Abastecimento")
    fh  = wb.add_format({"bold":True,"font_size":9,"border":1,"align":"center","valign":"vcenter","bg_color":"#BDD7EE","text_wrap":True})
    fd  = wb.add_format({"font_size":9,"border":1,"align":"center"})
    fn  = wb.add_format({"font_size":9,"border":1,"num_format":"#,##0.00","align":"right"})
    fm  = wb.add_format({"font_size":9,"border":1,"num_format":'"R$" #,##0.00',"align":"right"})
    ft  = wb.add_format({"bold":True,"font_size":9,"border":1,"num_format":"#,##0.00","align":"right","bg_color":"#D9D9D9"})
    ftm = wb.add_format({"bold":True,"font_size":9,"border":1,"num_format":'"R$" #,##0.00',"align":"right","bg_color":"#D9D9D9"})
    ftx = wb.add_format({"bold":True,"font_size":9,"border":1,"align":"right","bg_color":"#D9D9D9"})
    flb = wb.add_format({"bold":True,"font_size":9})
    fvl = wb.add_format({"font_size":9})
    fti = wb.add_format({"bold":True,"font_size":11,"align":"center","bg_color":"#D9D9D9","border":1})

    ws.write(0,0,"OBRA:",flb); ws.write(0,2,obra.upper(),fvl)
    ws.write(0,5,"PREÇO GASOLINA (L)",flb); ws.write(0,6,dados_forn.get("preco_gasolina","") or "",fvl)
    ws.write(0,8,"RAZÃO SOCIAL",flb); ws.write(0,10,dados_forn.get("razao_social",""),fvl)
    ws.write(0,12,"TIPO DE CONTA:",flb); ws.write(0,13,dados_forn.get("tipo_conta",""),fvl)
    ws.write(1,0,"DESCRIÇÃO:",flb)
    ws.write(1,5,"PREÇO DIESEL (L)",flb); ws.write(1,6,dados_forn.get("preco_diesel","") or "",fvl)
    ws.write(1,8,"AGÊNCIA:",flb); ws.write(1,10,dados_forn.get("agencia",""),fvl)
    ws.write(1,12,"BANCO:",flb); ws.write(1,13,dados_forn.get("banco",""),fvl)
    ws.write(2,0,"PERÍODO:",flb); ws.write(2,2,periodo.upper(),fvl)
    ws.write(2,8,"CONTA:",flb); ws.write(2,10,dados_forn.get("conta",""),fvl)
    ws.write(2,12,"PIX:",flb); ws.write(2,13,dados_forn.get("pix",""),fvl)

    titulo = f"CONTROLE DE ABASTECIMENTO  —  {nome_forn.upper() or obra.upper()}"
    ws.merge_range(3,0,3,13,titulo,fti)

    heads = ["DATA","DIA DA\nSEMANA","FICHA","PLACA","CÓDIGO /\nPREFIXO",
             "VEÍCULO / MAQUINA -\nMOTORISTA / OPERADOR",
             "FORNECEDOR","TIPO DE\nCOMBUSTÍVEL",
             "QUANTIDADE\n(L)","VALOR\nUNITÁRIO (R$)","TOTAL\n(R$)","KM / HOR","OBSERVAÇÃO"]
    widths = [12,8,8,10,10,30,20,12,10,12,12,10,30]
    ws.set_row(4,36)
    for ci,(h,w) in enumerate(zip(heads,widths)):
        ws.write(4,ci,h,fh); ws.set_column(ci,ci,w)

    t_l=0.0; t_r=0.0
    for ri,(_,r) in enumerate(df.iterrows(),start=5):
        dia_str=""
        try: dia_str=dias_pt[datetime.strptime(str(r.get("data",""))[:10],"%Y-%m-%d").weekday()]
        except: pass
        qtd=float(r.get("quantidade",0) or 0); vunt=float(r.get("valor_unitario",0) or 0); tot=float(r.get("total",0) or 0)
        t_l+=qtd; t_r+=tot
        for ci,v in enumerate([str(r.get("data",""))[:10],dia_str,str(r.get("numero_ficha","")),
                                str(r.get("placa","")),str(r.get("prefixo","")),str(r.get("motorista","")),
                                str(r.get("fornecedor","")),str(r.get("tipo_combustivel",""))]):
            ws.write(ri,ci,v,fd)
        ws.write(ri,8,qtd,fn); ws.write(ri,9,vunt,fm); ws.write(ri,10,tot,fm)
        ws.write(ri,11,str(r.get("horimetro","")),fd); ws.write(ri,12,str(r.get("observacao","")),fd)

    row_t=5+len(df)
    ws.merge_range(row_t,0,row_t,7,"TOTAL",ftx)
    ws.write(row_t,8,t_l,ft); ws.write(row_t,9,"",ftx); ws.write(row_t,10,t_r,ftm)
    ws.write(row_t,11,"TOTAL",ftx); ws.write(row_t,12,"",ftx)
    wb.close(); buf.seek(0); return buf.getvalue()


def gerar_excel_tanque(df_ent: pd.DataFrame, df_sai: pd.DataFrame,
                       nome_tanque: str, periodo: str, obra: str) -> bytes:
    dias_pt = {0:"SEG",1:"TER",2:"QUA",3:"QUI",4:"SEX",5:"SÁB",6:"DOM"}
    import xlsxwriter
    buf=io.BytesIO(); wb=xlsxwriter.Workbook(buf); ws=wb.add_worksheet("Tanque")
    fh  = wb.add_format({"bold":True,"font_size":9,"border":1,"align":"center","bg_color":"#BDD7EE","text_wrap":True})
    fd  = wb.add_format({"font_size":9,"border":1,"align":"center"})
    fn  = wb.add_format({"font_size":9,"border":1,"num_format":"#,##0.00","align":"right"})
    fm  = wb.add_format({"font_size":9,"border":1,"num_format":'"R$" #,##0.00',"align":"right"})
    fok = wb.add_format({"font_size":9,"border":1,"num_format":"#,##0.00","align":"right","font_color":"#3B6D11"})
    flo = wb.add_format({"font_size":9,"border":1,"num_format":"#,##0.00","align":"right","font_color":"#854F0B"})
    ft  = wb.add_format({"bold":True,"font_size":9,"border":1,"num_format":"#,##0.00","align":"right","bg_color":"#D9D9D9"})
    ftx = wb.add_format({"bold":True,"font_size":9,"border":1,"align":"right","bg_color":"#D9D9D9"})
    fti = wb.add_format({"bold":True,"font_size":11,"align":"center","bg_color":"#D9D9D9","border":1})
    flb = wb.add_format({"bold":True,"font_size":9}); fvl=wb.add_format({"font_size":9})

    ws.write(0,0,"OBRA:",flb); ws.write(0,2,obra.upper(),fvl)
    ws.write(1,0,"TANQUE:",flb); ws.write(1,2,nome_tanque.upper(),fvl)
    ws.write(2,0,"PERÍODO:",flb); ws.write(2,2,periodo.upper(),fvl)
    ws.merge_range(3,0,3,14,f"CONTROLE DE TANQUE  —  {nome_tanque.upper()}",fti)

    heads=["DATA","DIA","TIPO","FICHA","PLACA","PREF.","VEÍ./OPERADOR",
           "PRODUTO / FORNEC.","KM/HOR","QTD ENTRADA (L)","QTD SAÍDA (L)",
           "VL UNIT. (R$)","TOTAL (R$)","SALDO (L)","OBRA"]
    widths=[12,7,8,10,10,8,25,22,8,14,12,12,12,12,20]
    ws.set_row(4,30)
    for ci,(h,w) in enumerate(zip(heads,widths)):
        ws.write(4,ci,h,fh); ws.set_column(ci,ci,w)

    movs=[]
    if not df_ent.empty:
        for _,r in df_ent.iterrows(): movs.append({**r.to_dict(),"_tipo":"Entrada"})
    if not df_sai.empty:
        for _,r in df_sai.iterrows(): movs.append({**r.to_dict(),"_tipo":"Saída"})
    movs.sort(key=lambda x: str(x.get("data","")))

    saldo=0.0; t_ent=0.0; t_sai=0.0
    for ri,r in enumerate(movs,start=5):
        dia_str=""
        try: dia_str=dias_pt[datetime.strptime(str(r.get("data",""))[:10],"%Y-%m-%d").weekday()]
        except: pass
        qtd=float(r.get("quantidade",0) or 0); vunt=float(r.get("valor_unitario",0) or 0); tot=float(r.get("total",0) or 0)
        tipo=r["_tipo"]
        if tipo=="Entrada": saldo+=qtd; t_ent+=qtd
        else:               saldo-=qtd; t_sai+=qtd
        q_ent=qtd if tipo=="Entrada" else 0; q_sai=qtd if tipo=="Saída" else 0
        forn_veic=r.get("fornecedor","") if tipo=="Entrada" else r.get("motorista","")
        prod_forn=r.get("combustivel","") if tipo=="Entrada" else r.get("tipo_combustivel","")
        ws.write(ri,0,str(r.get("data",""))[:10],fd); ws.write(ri,1,dia_str,fd)
        ws.write(ri,2,tipo,fd); ws.write(ri,3,str(r.get("numero_ficha","")),fd)
        ws.write(ri,4,str(r.get("placa","")),fd); ws.write(ri,5,str(r.get("prefixo","")),fd)
        ws.write(ri,6,forn_veic,fd); ws.write(ri,7,prod_forn,fd)
        ws.write(ri,8,str(r.get("horimetro","")),fd)
        ws.write(ri,9,q_ent if q_ent else "",fn if q_ent else fd)
        ws.write(ri,10,q_sai if q_sai else "",fn if q_sai else fd)
        ws.write(ri,11,vunt,fm); ws.write(ri,12,tot,fm)
        ws.write(ri,13,saldo,fok if saldo>=500 else flo)
        ws.write(ri,14,str(r.get("obra","")),fd)

    row_t=5+len(movs)
    ws.write(row_t,0,"TOTAL",ftx); ws.merge_range(row_t,1,row_t,8,"",ftx)
    ws.write(row_t,9,t_ent,ft); ws.write(row_t,10,t_sai,ft)
    ws.write(row_t,11,"",ftx); ws.write(row_t,12,"",ftx)
    ws.write(row_t,13,t_ent-t_sai,ft); ws.write(row_t,14,"",ftx)
    wb.close(); buf.seek(0); return buf.getvalue()


def gerar_excel_limpo(df: pd.DataFrame, nome_aba: str="Relatório") -> bytes:
    df=df.fillna("").copy()
    buf=io.BytesIO()
    with pd.ExcelWriter(buf,engine="xlsxwriter") as w:
        df.to_excel(w,index=False,sheet_name=nome_aba)
        ws=w.sheets[nome_aba]
        for i,col in enumerate(df.columns):
            try:
                sz=max(len(str(col)),df[col].astype(str).str.len().max())
                ws.set_column(i,i,min(int(sz)+2,50))
            except: ws.set_column(i,i,15)
    return buf.getvalue()


# ═══════════════════════════════════════════════════════════════════
# PDF TIMBRADO
# ═══════════════════════════════════════════════════════════════════
def gerar_pdf(df: pd.DataFrame, tipo: str,
              titulo_esq: str, sub_esq: str, per_esq: str,
              dados_dir: dict, titulo_tab: str) -> bytes:
    df=df.fillna("").copy()
    pdf=FPDF(orientation="L",unit="mm",format="A4"); pdf.add_page()
    pdf.rect(10,10,110,22)
    x=12
    if os.path.exists("logo.png"):
        try: pdf.image("logo.png",x=12,y=12,h=18); x=48
        except: pass
    pdf.set_xy(x,12); pdf.set_font("Arial","B",9)
    pdf.cell(0,6,titulo_esq.upper(),ln=1)
    pdf.set_x(x); pdf.cell(0,6,sub_esq.upper(),ln=1)
    pdf.set_x(x); pdf.cell(0,6,per_esq.upper(),ln=1)
    pdf.rect(125,10,162,22); pdf.set_xy(127,12); pdf.set_font("Arial","B",9)
    for i,(k,v) in enumerate(dados_dir.items()):
        if i%2==0: pdf.set_x(127); pdf.cell(80,5,f"{k}: {v}")
        else:       pdf.cell(80,5,f"{k}: {v}",ln=1)
    pdf.set_y(35); pdf.set_font("Arial","B",10)
    pdf.cell(277,8,titulo_tab.upper(),border=1,align="C",ln=1)
    pdf.set_font("Arial","B",7); pdf.set_fill_color(220,220,220)

    if tipo=="SAIDAS":
        cols=[("DATA",16),("FICHA",15),("PLACA",14),("PREF.",12),
              ("MÁQUINA / MOTORISTA",52),("PRODUTO",18),
              ("QTD (L)",14),("V.UNIT.",14),("TOTAL (R$)",20),("KM/HOR",13),("OBS",69)]
    elif tipo=="TANQUE":
        cols=[("DATA",14),("TIPO",10),("FICHA",14),("PLACA",13),("PREF.",10),
              ("OPERADOR / FORNEC.",40),("PRODUTO",16),("KM/H",10),
              ("ENTRADA(L)",17),("SAÍDA(L)",14),("V.UNIT.",13),("TOTAL",15),("SALDO(L)",14),("OBS",37)]
    else:
        cols=[("DATA",18),("NF/FICHA",22),("DISTRIBUIDORA",60),("TANQUE",42),
              ("PRODUTO",22),("QTD (L)",20),("V.UNIT.",20),("TOTAL (R$)",23),("OBS",30)]

    for n,w in cols: pdf.cell(w,7,n,border=1,align="C",fill=True)
    pdf.ln(); pdf.set_font("Arial","",7)
    t_l=0.0; t_r=0.0; saldo=0.0

    for _,r in df.iterrows():
        q=float(r.get("quantidade",0) or 0); v=float(r.get("valor_unitario",0) or 0); t=float(r.get("total",0) or 0)
        qe=float(r.get("qtd_entrada",0) or 0); qs=float(r.get("qtd_saida",0) or 0)
        saldo+=qe-qs
        if tipo=="SAIDAS":
            for val,w in [(str(r.get("data",""))[:10],16),(str(r.get("numero_ficha",""))[:14],15),
                          (str(r.get("placa",""))[:8],14),(str(r.get("prefixo",""))[:8],12),
                          (str(r.get("motorista",""))[:33],52),(str(r.get("tipo_combustivel",""))[:12],18)]:
                pdf.cell(w,6,val,border=1,align="C")
            pdf.cell(14,6,f"{q:,.2f}",border=1,align="R"); pdf.cell(14,6,f"{v:,.2f}",border=1,align="R")
            pdf.cell(20,6,f"R${t:,.2f}",border=1,align="R"); pdf.cell(13,6,str(r.get("horimetro",""))[:7],border=1,align="C")
            pdf.cell(69,6,str(r.get("observacao",""))[:40],border=1,align="L"); t_l+=q; t_r+=t
        elif tipo=="TANQUE":
            pdf.cell(14,6,str(r.get("data",""))[:10],border=1,align="C")
            pdf.cell(10,6,str(r.get("tipo",""))[:6],border=1,align="C")
            pdf.cell(14,6,str(r.get("numero_ficha",""))[:12],border=1,align="C")
            pdf.cell(13,6,str(r.get("placa",""))[:7],border=1,align="C")
            pdf.cell(10,6,str(r.get("prefixo",""))[:7],border=1,align="C")
            pdf.cell(40,6,str(r.get("motorista_forn",""))[:25],border=1,align="L")
            pdf.cell(16,6,str(r.get("produto",""))[:10],border=1,align="C")
            pdf.cell(10,6,str(r.get("horimetro",""))[:7],border=1,align="C")
            pdf.cell(17,6,f"{qe:,.1f}" if qe else "-",border=1,align="R")
            pdf.cell(14,6,f"{qs:,.1f}" if qs else "-",border=1,align="R")
            pdf.cell(13,6,f"{v:,.2f}",border=1,align="R"); pdf.cell(15,6,f"R${t:,.2f}",border=1,align="R")
            pdf.cell(14,6,f"{saldo:,.1f}",border=1,align="R")
            pdf.cell(37,6,str(r.get("observacao",""))[:22],border=1,align="L"); t_l+=(qe or qs); t_r+=t
        else:
            pdf.cell(18,6,str(r.get("data",""))[:10],border=1,align="C")
            pdf.cell(22,6,str(r.get("numero_ficha",""))[:14],border=1,align="C")
            pdf.cell(60,6,str(r.get("fornecedor",""))[:38],border=1,align="L")
            pdf.cell(42,6,str(r.get("nome_tanque",""))[:25],border=1,align="C")
            pdf.cell(22,6,str(r.get("combustivel",""))[:12],border=1,align="C")
            pdf.cell(20,6,f"{q:,.2f}",border=1,align="R"); pdf.cell(20,6,f"{v:,.2f}",border=1,align="R")
            pdf.cell(23,6,f"R${t:,.2f}",border=1,align="R"); pdf.cell(30,6,str(r.get("observacao",""))[:18],border=1,align="L")
            t_l+=q; t_r+=t
        pdf.ln()

    pdf.set_font("Arial","B",8)
    if tipo=="SAIDAS":
        pdf.cell(136,8,"TOTAIS GERAIS",border=1,align="R"); pdf.cell(14,8,f"{t_l:,.2f}",border=1,align="R")
        pdf.cell(14,8,"-",border=1,align="C"); pdf.cell(20,8,f"R$ {t_r:,.2f}",border=1,align="R"); pdf.cell(82,8,"",border=1)
    elif tipo=="TANQUE":
        pdf.cell(138,8,"TOTAIS",border=1,align="R"); pdf.cell(17,8,f"{t_l:,.2f}",border=1,align="R")
        pdf.cell(14,8,"-",border=1,align="C"); pdf.cell(13,8,"-",border=1,align="C")
        pdf.cell(15,8,f"R$ {t_r:,.2f}",border=1,align="R"); pdf.cell(14,8,f"{saldo:,.1f}",border=1,align="R"); pdf.cell(37,8,"",border=1)
    else:
        pdf.cell(167,8,"TOTAIS GERAIS",border=1,align="R"); pdf.cell(20,8,f"{t_l:,.2f}",border=1,align="R")
        pdf.cell(20,8,"-",border=1,align="C"); pdf.cell(23,8,f"R$ {t_r:,.2f}",border=1,align="R"); pdf.cell(30,8,"",border=1)

    return pdf.output(dest="S").encode("latin-1")


# ═══════════════════════════════════════════════════════════════════
# LOGIN — tabela "usuarios" no Supabase
# ═══════════════════════════════════════════════════════════════════
for k,v in [("logged_in",False),("usuario_logado",""),("perfil_logado","")]:
    if k not in st.session_state: st.session_state[k]=v

if not st.session_state.logged_in:
    st.write("<br><br><br>",unsafe_allow_html=True)
    c1,c2,c3=st.columns([1,1.2,1])
    with c2:
        with st.form("login"):
            if os.path.exists("logo.png"): st.image("logo.png",use_container_width=True)
            st.markdown("<h2 style='text-align:center;color:#333;'>Acesso Restrito</h2>",unsafe_allow_html=True)
            u=st.text_input("Usuário"); p=st.text_input("Senha",type="password")
            if st.form_submit_button("ENTRAR NO SISTEMA",use_container_width=True):
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
# SIDEBAR
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


# ════════════════════════════════════════════════════════════════════
# 1 · PAINEL INÍCIO
# ════════════════════════════════════════════════════════════════════
if menu=="🏠 Painel Início":
    st.markdown("## 🏠 Centro de Comando")
    df_tanq=get_data("tanques"); df_ab=get_data("abastecimentos"); df_prod=get_data("producao")

    if not df_tanq.empty:
        st.subheader("🛢️ Situação dos Tanques / Comboios")
        cols_t=st.columns(min(len(df_tanq),5))
        for idx,row in df_tanq.iterrows():
            nm=row["nome"]; cap=float(row.get("capacidade",0) or 0)
            sd=calcular_saldo(nm); lim=(cap*0.15) if cap>0 else 500
            with cols_t[idx%len(cols_t)]:
                low=sd<=lim; cls="banner-low" if low else "banner-ok"; ic="⚠️" if low else "✅"
                pct_txt=f" / {sd/cap*100:.0f}%" if cap>0 else ""
                st.markdown(f"<div class='{cls}'>{ic} <strong>{nm}</strong><br>{sd:,.1f} L{pct_txt}</div>",unsafe_allow_html=True)
                if cap>0: st.progress(min(sd/cap,1.0))
        st.divider()

    st.markdown("#### 📅 Indicadores do Período")
    cd1,cd2=st.columns(2)
    d_ini=cd1.date_input("De",value=date.today().replace(day=1))
    d_fim=cd2.date_input("Até",value=date.today())

    t_gasto=0;t_litros=0;t_carradas=0;t_ton=0;t_ton_cbuq=0
    if not df_ab.empty:
        df_ab["data_dt"]=pd.to_datetime(df_ab["data"],errors="coerce").dt.date
        daf=df_ab[(df_ab["data_dt"]>=d_ini)&(df_ab["data_dt"]<=d_fim)]
        t_gasto=pd.to_numeric(daf.get("total",pd.Series()),errors="coerce").sum()
        t_litros=pd.to_numeric(daf.get("quantidade",pd.Series()),errors="coerce").sum()
    if not df_prod.empty:
        df_prod["data_dt"]=pd.to_datetime(df_prod["data"],errors="coerce").dt.date
        dpf=df_prod[(df_prod["data_dt"]>=d_ini)&(df_prod["data_dt"]<=d_fim)]
        t_carradas=pd.to_numeric(dpf.get("carradas",pd.Series()),errors="coerce").sum()
        t_ton=pd.to_numeric(dpf.get("toneladas",pd.Series()),errors="coerce").sum()
        if "tipo_operacao" in dpf.columns:
            dc=dpf[dpf["tipo_operacao"].isin(["Transporte de Massa/CBUQ","Venda de Massa"])]
            t_ton_cbuq=pd.to_numeric(dc.get("toneladas",pd.Series()),errors="coerce").sum()

    c1,c2,c3,c4=st.columns(4)
    c1.markdown(f"<div class='kpi-box'><p>💰 Gasto Combustível</p><h3 class='kpi-rojo'>R$ {t_gasto:,.2f}</h3></div>",unsafe_allow_html=True)
    c2.markdown(f"<div class='kpi-box'><p>⛽ Litros Consumidos</p><h3>{t_litros:,.1f} L</h3></div>",unsafe_allow_html=True)
    c3.markdown(f"<div class='kpi-box'><p>🏗️ Ton CBUQ</p><h3>{t_ton_cbuq:,.1f} t</h3></div>",unsafe_allow_html=True)
    c4.markdown(f"<div class='kpi-box'><p>🚚 Viagens</p><h3>{int(t_carradas)}</h3></div>",unsafe_allow_html=True)

    st.write("<br>",unsafe_allow_html=True)
    st.markdown("#### ⚙️ KPIs de Eficiência Logística")
    c5,c6,c7=st.columns(3)
    custo_ton=t_gasto/t_ton_cbuq if t_ton_cbuq>0 else 0
    litros_ton=t_litros/t_ton_cbuq if t_ton_cbuq>0 else 0
    litros_vg=t_litros/t_carradas if t_carradas>0 else 0
    c5.markdown(f"<div class='kpi-box'><p>Custo Diesel / Ton CBUQ</p><h3 class='kpi-verde'>R$ {custo_ton:,.2f}</h3></div>",unsafe_allow_html=True)
    c6.markdown(f"<div class='kpi-box'><p>Litros / Ton CBUQ</p><h3 class='kpi-verde'>{litros_ton:,.2f} L</h3></div>",unsafe_allow_html=True)
    c7.markdown(f"<div class='kpi-box'><p>Litros Médio / Viagem</p><h3 class='kpi-azul'>{litros_vg:,.1f} L</h3></div>",unsafe_allow_html=True)

    if not df_ab.empty:
        st.divider(); st.subheader("📊 Gastos por Mês")
        df_ab["Mês"]=pd.to_datetime(df_ab["data"],errors="coerce").dt.strftime("%m/%Y")
        df_ab["total_n"]=pd.to_numeric(df_ab["total"],errors="coerce").fillna(0)
        g=df_ab.groupby("Mês")["total_n"].sum().reset_index()
        fig=px.bar(g,x="Mês",y="total_n",color_discrete_sequence=["#1D9E75"],labels={"total_n":"R$ Total"})
        fig.update_layout(showlegend=False,plot_bgcolor="white",paper_bgcolor="white",margin=dict(l=0,r=0,t=30,b=0))
        st.plotly_chart(fig,use_container_width=True)


# ════════════════════════════════════════════════════════════════════
# 2 · LANÇAR ABASTECIMENTO
# ════════════════════════════════════════════════════════════════════
elif menu=="⛽ Lançar Abastecimento":
    st.markdown("## ⛽ Lançar Saída de Combustível")
    df_v=get_data("veiculos"); df_f=get_data("fornecedores"); df_a=get_data("abastecimentos"); df_t=get_data("tanques")

    if df_v.empty: st.warning("⚠️ Cadastre veículos em 'Frota e Equipamentos' primeiro."); st.stop()

    v_sel=st.selectbox("🚜 Máquina / Caçamba",df_v["prefixo"].tolist())
    info_v=df_v[df_v["prefixo"]==v_sel].iloc[0]
    comb_padrao=info_v.get("tipo_combustivel_padrao","Diesel S10")
    motorista_padrao=info_v.get("motorista","")
    placa_padrao=info_v.get("placa","")

    m_hor=0.0
    if not df_a.empty and "horimetro" in df_a.columns:
        hist=df_a[df_a["prefixo"]==v_sel]
        if not hist.empty: m_hor=float(pd.to_numeric(hist["horimetro"],errors="coerce").max() or 0)

    st.markdown(f"<div class='banner-info'>⛽ Combustível: <strong>{comb_padrao}</strong>  |  🪪 Placa: <strong>{placa_padrao}</strong>  |  ⏱️ Último KM/Hor: <strong>{m_hor:,.1f}</strong></div>",unsafe_allow_html=True)

    origem=st.radio("Origem do Combustível:",["Posto Externo","Tanque Interno"],horizontal=True)

    with st.form("f_ab",clear_on_submit=True):
        c1,c2,c3=st.columns(3)
        data_ab=c1.date_input("Data",value=date.today()); ficha=c2.text_input("Nº Ficha / Cupom")
        if origem=="Posto Externo":
            postos=df_f["nome"].tolist() if not df_f.empty else ["Sem cadastro"]
            posto=c3.selectbox("Posto Fornecedor",postos); n_tanq=None
        else:
            tanqs=df_t["nome"].tolist() if not df_t.empty else ["Sem cadastro"]
            n_tanq=c3.selectbox("Tanque de Origem",tanqs); posto="Estoque Próprio"
        c4,c5=st.columns(2)
        motorista=c4.text_input("Motorista / Operador",value=motorista_padrao)
        hor=c5.number_input("KM / Horímetro Atual",min_value=0.0,value=m_hor)
        c6,c7,c8=st.columns(3)
        litros=c6.number_input("Litros",min_value=0.0); preco=c7.number_input("Preço Unitário (R$/L)",min_value=0.0)
        obs=c8.text_input("Observações / Obra")
        st.markdown(f"<div class='banner-info'>Total calculado: <strong>R$ {litros*preco:,.2f}</strong></div>",unsafe_allow_html=True)

        if st.form_submit_button("💾 Salvar Abastecimento",use_container_width=True):
            if litros<=0: st.error("⚠️ Litros devem ser maior que zero.")
            elif origem=="Tanque Interno":
                sd=calcular_saldo(n_tanq)
                if litros>sd: st.error(f"⚠️ Saldo insuficiente! Disponível: {sd:,.1f} L | Solicitado: {litros:,.1f} L")
                else:
                    ok=insert_data("abastecimentos",{"data":str(data_ab),"dia_semana":dia_semana_pt(data_ab),"numero_ficha":ficha,"origem":origem,"nome_tanque":n_tanq,"prefixo":v_sel,"placa":placa_padrao,"motorista":motorista.upper(),"tipo_combustivel":comb_padrao,"quantidade":litros,"valor_unitario":preco,"total":litros*preco,"fornecedor":posto,"horimetro":hor,"observacao":obs,"criado_por":st.session_state.usuario_logado})
                    if ok: st.success("✅ Salvo!"); time.sleep(1); st.rerun()
            else:
                ok=insert_data("abastecimentos",{"data":str(data_ab),"dia_semana":dia_semana_pt(data_ab),"numero_ficha":ficha,"origem":origem,"nome_tanque":None,"prefixo":v_sel,"placa":placa_padrao,"motorista":motorista.upper(),"tipo_combustivel":comb_padrao,"quantidade":litros,"valor_unitario":preco,"total":litros*preco,"fornecedor":posto,"horimetro":hor,"observacao":obs,"criado_por":st.session_state.usuario_logado})
                if ok: st.success("✅ Salvo!"); time.sleep(1); st.rerun()

    if not df_a.empty:
        st.divider(); st.subheader("📋 Últimos 20 Abastecimentos")
        df_rec=df_a.sort_values("data",ascending=False).head(20).fillna("")
        cs=[c for c in ["data","dia_semana","numero_ficha","placa","prefixo","motorista","fornecedor","tipo_combustivel","quantidade","valor_unitario","total","horimetro","observacao","criado_por"] if c in df_rec.columns]
        st.dataframe(df_rec[cs],use_container_width=True)


# ════════════════════════════════════════════════════════════════════
# 3 · TANQUES / ESTOQUE
# ════════════════════════════════════════════════════════════════════
elif menu=="🛢️ Tanques / Estoque":
    st.markdown("## 🛢️ Gestão de Estoque Interno")
    tab_saldo,tab_ent,tab_hist,tab_cfg=st.tabs(["📊 Saldo Real","📥 Receber Compra","📋 Histórico","⚙️ Configurar"])

    with tab_cfg:
        with st.form("f_tk_cfg",clear_on_submit=True):
            c1,c2,c3=st.columns(3)
            nm_tk=c1.text_input("Nome do Tanque / Comboio")
            cap_tk=c2.number_input("Capacidade Total (L)",min_value=0.0)
            min_tk=c3.number_input("Nível Mínimo de Alerta (L)",min_value=0.0,value=500.0)
            if st.form_submit_button("Salvar") and nm_tk:
                insert_data("tanques",{"nome":nm_tk,"capacidade":cap_tk,"minimo":min_tk}); st.rerun()
        df_t=get_data("tanques")
        for _,r in df_t.iterrows():
            c1,c2=st.columns([5,1])
            c1.write(f"🛢️ **{r['nome']}** | Cap: {r.get('capacidade',0):,.0f} L | Mín: {r.get('minimo',500):,.0f} L")
            if c2.button("🗑️",key=f"dtk_{r['id']}"): delete_data("tanques",r["id"]); st.rerun()

    with tab_ent:
        df_t=get_data("tanques"); df_f=get_data("fornecedores")
        if df_t.empty: st.warning("⚠️ Cadastre um tanque primeiro.")
        else:
            with st.form("f_ent2",clear_on_submit=True):
                c1,c2,c3=st.columns(3)
                d_ent=c1.date_input("Data"); t_dest=c2.selectbox("Tanque Destino",df_t["nome"].tolist()); nf_ent=c3.text_input("Nº Nota Fiscal")
                c4,c5,c6=st.columns(3)
                forn=c4.selectbox("Distribuidora",df_f["nome"].tolist() if not df_f.empty else ["N/A"])
                prod=c5.selectbox("Produto",["Diesel S10","Diesel S500","Gasolina","Arla 32"]); obs_e=c6.text_input("Obs")
                c7,c8=st.columns(2)
                q_e=c7.number_input("Litros Recebidos",min_value=0.0); p_e=c8.number_input("Preço NF (R$/L)",min_value=0.0)
                st.markdown(f"<div class='banner-info'>Total NF: <strong>R$ {q_e*p_e:,.2f}</strong></div>",unsafe_allow_html=True)
                if st.form_submit_button("📥 Confirmar Entrada",use_container_width=True):
                    if q_e<=0: st.error("⚠️ Litros > 0.")
                    else:
                        ok=insert_data("entradas_tanque",{"data":str(d_ent),"dia_semana":dia_semana_pt(d_ent),"nome_tanque":t_dest,"fornecedor":forn,"numero_ficha":nf_ent,"combustivel":prod,"quantidade":q_e,"valor_unitario":p_e,"total":q_e*p_e,"observacao":obs_e,"criado_por":st.session_state.usuario_logado})
                        if ok: st.success("✅ Estoque atualizado!"); time.sleep(1); st.rerun()

    with tab_saldo:
        df_t=get_data("tanques")
        for _,r in df_t.iterrows():
            nm=r["nome"]; cap=float(r.get("capacidade",0) or 0); mim=float(r.get("minimo",500) or 500); sd=calcular_saldo(nm); low=sd<=mim
            cls="banner-low" if low else "banner-ok"
            with st.expander(f"{'⚠️' if low else '✅'} {nm}  —  {sd:,.1f} L",expanded=True):
                st.markdown(f"<div class='{cls}'>Saldo: <strong>{sd:,.1f} L</strong>{f'  /  Cap: {cap:,.0f} L  (~{sd/cap*100:.0f}% cheio)' if cap>0 else ''}{'  ⚠️ NÍVEL BAIXO!' if low else ''}</div>",unsafe_allow_html=True)
                if cap>0: st.progress(min(sd/cap,1.0))

    with tab_hist:
        df_t=get_data("tanques")
        if df_t.empty: st.info("Nenhum tanque.")
        else:
            tk_sel=st.selectbox("Selecionar tanque",df_t["nome"].tolist(),key="hth")
            df_ent_h=get_data("entradas_tanque"); df_sai_h=get_data("abastecimentos")
            if not df_ent_h.empty and "nome_tanque" in df_ent_h.columns: df_ent_h=df_ent_h[df_ent_h["nome_tanque"]==tk_sel].copy()
            else: df_ent_h=pd.DataFrame()
            if not df_sai_h.empty and "origem" in df_sai_h.columns:
                df_sai_h=df_sai_h[(df_sai_h["origem"]=="Tanque Interno")&(df_sai_h["nome_tanque"]==tk_sel)].copy()
            else: df_sai_h=pd.DataFrame()

            movs=[]
            if not df_ent_h.empty:
                for _,r in df_ent_h.iterrows(): movs.append({"data":r.get("data",""),"dia":r.get("dia_semana",""),"tipo":"Entrada","ficha":r.get("numero_ficha",""),"placa":"","prefixo":"","motorista_forn":r.get("fornecedor",""),"produto":r.get("combustivel",""),"horimetro":"","qtd_entrada":float(r.get("quantidade",0) or 0),"qtd_saida":0,"valor_unitario":float(r.get("valor_unitario",0) or 0),"total":float(r.get("total",0) or 0),"obra":"","observacao":r.get("observacao",""),"criado_por":r.get("criado_por","")})
            if not df_sai_h.empty:
                for _,r in df_sai_h.iterrows(): movs.append({"data":r.get("data",""),"dia":r.get("dia_semana",""),"tipo":"Saída","ficha":r.get("numero_ficha",""),"placa":r.get("placa",""),"prefixo":r.get("prefixo",""),"motorista_forn":r.get("motorista",""),"produto":r.get("tipo_combustivel",""),"horimetro":r.get("horimetro",""),"qtd_entrada":0,"qtd_saida":float(r.get("quantidade",0) or 0),"valor_unitario":float(r.get("valor_unitario",0) or 0),"total":float(r.get("total",0) or 0),"obra":r.get("observacao",""),"observacao":r.get("observacao",""),"criado_por":r.get("criado_por","")})

            if movs:
                df_mov=pd.DataFrame(movs).sort_values("data"); saldo_c=0.0; saldos=[]
                for _,r in df_mov.iterrows(): saldo_c+=r["qtd_entrada"]-r["qtd_saida"]; saldos.append(round(saldo_c,2))
                df_mov["saldo_L"]=saldos
                st.dataframe(df_mov[["data","dia","tipo","ficha","placa","prefixo","motorista_forn","produto","horimetro","qtd_entrada","qtd_saida","valor_unitario","total","saldo_L","criado_por"]].sort_values("data",ascending=False),use_container_width=True)
                t_e=df_mov["qtd_entrada"].sum(); t_s=df_mov["qtd_saida"].sum()
                st.markdown(f"**Entradas:** {t_e:,.2f} L  |  **Saídas:** {t_s:,.2f} L  |  **Saldo:** {t_e-t_s:,.2f} L")
                xls=gerar_excel_tanque(df_ent_h,df_sai_h,tk_sel,"","")
                st.download_button("⬇️ Exportar Excel do Tanque",xls,f"Tanque_{tk_sel.replace(' ','_')}.xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else: st.info("Nenhuma movimentação.")


# ════════════════════════════════════════════════════════════════════
# 4 · BOLETIM DE TRANSPORTE
# ════════════════════════════════════════════════════════════════════
elif menu=="🚚 Boletim de Transporte":
    st.markdown("## 🚚 Boletim de Transporte e Logística")
    df_v=get_data("veiculos")
    if df_v.empty: st.warning("⚠️ Cadastre veículos primeiro."); st.stop()
    cacamba=st.selectbox("Veículo / Caçamba",df_v["prefixo"].tolist())
    mot_pad=df_v[df_v["prefixo"]==cacamba].iloc[0].get("motorista","") if not df_v.empty else ""

    with st.form("f_blt",clear_on_submit=True):
        c1,c2,c3=st.columns(3)
        data_bt=c1.date_input("Data",value=date.today()); motorista=c2.text_input("Motorista",value=mot_pad)
        tipo_op=c3.selectbox("Tipo de Operação",["Transporte de Massa/CBUQ","Transporte de Agregado (Jazida)","Venda de Massa","Remoção de Entulho/Fresado","Outros"])
        c4,c5=st.columns(2)
        origem_bt=c4.text_input("Local de Origem"); destino_bt=c5.text_input("Local de Destino")
        c6,c7,c8=st.columns(3)
        material=c6.text_input("Material (ex: CBUQ, Brita 1)"); carradas=c7.number_input("Carradas / Viagens",min_value=0,step=1); toneladas=c8.number_input("Toneladas Totais",min_value=0.0)
        c9,c10=st.columns(2)
        v_frete=c9.number_input("Valor Frete/Ton ou Diária (R$)",min_value=0.0); obs_bt=c10.text_input("Observações / Comprador")
        v_total=toneladas*v_frete if v_frete>0 and toneladas>0 else 0
        if v_total>0: st.markdown(f"<div class='banner-info'>Total Frete: <strong>R$ {v_total:,.2f}</strong></div>",unsafe_allow_html=True)
        if st.form_submit_button("💾 Salvar Boletim",use_container_width=True):
            if not motorista: st.error("⚠️ Informe o motorista!")
            else:
                ok=insert_data("producao",{"data":str(data_bt),"motorista":motorista.strip().upper(),"veiculo":cacamba,"tipo_operacao":tipo_op,"origem":origem_bt,"destino":destino_bt,"material":material,"carradas":carradas,"toneladas":toneladas,"valor_frete":v_total,"observacao":obs_bt,"criado_por":st.session_state.usuario_logado})
                if ok: st.success("✅ Salvo!"); time.sleep(1); st.rerun()

    st.divider(); df_prod=get_data("producao")
    if not df_prod.empty:
        st.subheader("📋 Últimos Boletins")
        cs=[c for c in ["data","motorista","veiculo","tipo_operacao","origem","destino","material","carradas","toneladas","valor_frete","observacao","criado_por"] if c in df_prod.columns]
        st.dataframe(df_prod.sort_values("data",ascending=False).head(20).fillna("")[cs],use_container_width=True)


# ════════════════════════════════════════════════════════════════════
# 5 · FROTA E EQUIPAMENTOS
# ════════════════════════════════════════════════════════════════════
elif menu=="🚜 Frota e Equipamentos":
    st.markdown("## 🚜 Gestão de Máquinas, Veículos e Caçambas")
    tab_frota,tab_cat=st.tabs(["🚜 Frota Ativa","📂 Categorias"])

    with tab_cat:
        with st.form("f_cat",clear_on_submit=True):
            nc=st.text_input("Nova Categoria")
            if st.form_submit_button("Salvar") and nc: insert_data("classes_frota",{"nome":nc}); st.rerun()
        df_c=get_data("classes_frota")
        for _,r in df_c.iterrows():
            c1,c2=st.columns([5,1]); c1.write(f"• {r['nome']}")
            if c2.button("🗑️",key=f"dcat_{r['id']}"): delete_data("classes_frota",r["id"]); st.rerun()

    with tab_frota:
        df_c=get_data("classes_frota"); cats=df_c["nome"].tolist() if not df_c.empty else ["N/A"]
        with st.form("f_veic",clear_on_submit=True):
            c1,c2,c3=st.columns(3)
            pref_v=c1.text_input("Prefixo / Código (ex: CB-01)"); placa_v=c2.text_input("Placa"); cat_v=c3.selectbox("Categoria",cats)
            c4,c5,c6=st.columns(3)
            comb_v=c4.selectbox("Combustível Padrão",["Diesel S10","Diesel S500","Gasolina","Arla 32"]); mot_v=c5.text_input("Motorista / Operador Fixo"); prop_v=c6.text_input("Proprietário")
            c7,c8,c9=st.columns(3)
            banco_v=c7.text_input("Banco"); ag_v=c8.text_input("Agência"); conta_v=c9.text_input("Conta")
            c10,c11=st.columns(2)
            tconta_v=c10.selectbox("Tipo de Conta",["Corrente","Poupança"]); cnpj_v=c11.text_input("CPF / CNPJ")
            if st.form_submit_button("💾 Salvar"):
                if not pref_v: st.error("⚠️ Informe o prefixo.")
                else:
                    ok=insert_data("veiculos",{"prefixo":pref_v,"placa":placa_v,"classe":cat_v,"tipo_combustivel_padrao":comb_v,"motorista":mot_v.upper(),"proprietario":prop_v,"banco":banco_v,"agencia":ag_v,"conta":conta_v,"tipo_conta":tconta_v,"cnpj":cnpj_v})
                    if ok: st.success("✅ Salvo!"); st.rerun()

        busca=st.text_input("🔍 Buscar...")
        df_v=get_data("veiculos")
        if not df_v.empty:
            if busca:
                mask=df_v.apply(lambda r: busca.lower() in " ".join(r.astype(str).values).lower(),axis=1); df_v=df_v[mask]
            for _,r in df_v.iterrows():
                with st.expander(f"🚜 {r.get('prefixo','')} | {r.get('placa','')} | {r.get('classe','')}"):
                    c1,c2,c3=st.columns(3)
                    c1.write(f"**Motorista:** {r.get('motorista','')}"); c2.write(f"**Proprietário:** {r.get('proprietario','')}"); c3.write(f"**Combustível:** {r.get('tipo_combustivel_padrao','')}")
                    c4,c5=st.columns(2)
                    c4.write(f"**Banco:** {r.get('banco','')} | Ag: {r.get('agencia','')} | Cc: {r.get('conta','')}"); c5.write(f"**CNPJ:** {r.get('cnpj','')}")
                    if st.button("🗑️ Remover",key=f"dv_{r['id']}"): delete_data("veiculos",r["id"]); st.rerun()


# ════════════════════════════════════════════════════════════════════
# 6 · FORNECEDORES
# ════════════════════════════════════════════════════════════════════
elif menu=="🏪 Fornecedores":
    st.markdown("## 🏪 Postos, Distribuidoras e Fornecedores")
    with st.form("f_forn2",clear_on_submit=True):
        c1,c2,c3=st.columns(3); nm_f=c1.text_input("Nome Fantasia"); rz_f=c2.text_input("Razão Social"); cnpj_f=c3.text_input("CNPJ")
        c4,c5,c6=st.columns(3); banco_f=c4.text_input("Banco"); ag_f=c5.text_input("Agência"); cc_f=c6.text_input("Conta")
        c7,c8,c9=st.columns(3); tc_f=c7.selectbox("Tipo de Conta",["Corrente","Poupança"]); pix_f=c8.text_input("Chave PIX"); tel_f=c9.text_input("Telefone")
        c10,c11=st.columns(2); pd_f=c10.number_input("Preço Diesel (R$/L)",min_value=0.0,step=0.01); pg_f=c11.number_input("Preço Gasolina (R$/L)",min_value=0.0,step=0.01)
        if st.form_submit_button("💾 Salvar Fornecedor"):
            if not nm_f: st.error("⚠️ Informe o nome.")
            else:
                ok=insert_data("fornecedores",{"nome":nm_f,"razao_social":rz_f,"cnpj":cnpj_f,"banco":banco_f,"agencia":ag_f,"conta":cc_f,"tipo_conta":tc_f,"pix":pix_f,"telefone":tel_f,"preco_diesel":pd_f or None,"preco_gasolina":pg_f or None})
                if ok: st.success("✅ Salvo!"); st.rerun()

    df_f=get_data("fornecedores")
    if not df_f.empty:
        for _,r in df_f.iterrows():
            with st.expander(f"🏪 {r['nome'].upper()}"):
                c1,c2,c3=st.columns(3)
                c1.write(f"**CNPJ:** {r.get('cnpj','')}"); c2.write(f"**Razão:** {r.get('razao_social','')}"); c3.write(f"**Tel:** {r.get('telefone','')}")
                c4,c5=st.columns(2)
                c4.write(f"**Banco:** {r.get('banco','')} | Ag: {r.get('agencia','')} | Cc: {r.get('conta','')}"); c5.write(f"**PIX:** {r.get('pix','')}  |  Diesel: R$ {r.get('preco_diesel','—')}  |  Gas: R$ {r.get('preco_gasolina','—')}")
                if st.button("🗑️ Remover",key=f"df2_{r['id']}"): delete_data("fornecedores",r["id"]); st.rerun()


# ════════════════════════════════════════════════════════════════════
# 7 · OBRAS CADASTRADAS
# ════════════════════════════════════════════════════════════════════
elif menu=="🏗️ Obras Cadastradas":
    st.markdown("## 🏗️ Cadastro de Obras")
    with st.form("f_obra2",clear_on_submit=True):
        c1,c2,c3=st.columns(3); nm_o=c1.text_input("Nome / Código (ex: TIANGUÁ)"); rod_o=c2.text_input("Rodovia / Local"); mun_o=c3.text_input("Município / UF")
        c4,c5,c6=st.columns(3); ct_o=c4.text_input("Contrato"); cont_o=c5.text_input("Contratante"); ext_o=c6.number_input("Extensão (km)",min_value=0.0,step=0.1)
        c7,c8,c9=st.columns(3); ini_o=c7.date_input("Início"); fim_o=c8.date_input("Prazo"); st_o=c9.selectbox("Status",["Em andamento","Paralisada","Concluída"])
        c10,c11=st.columns(2); per_o=c10.text_input("Período p/ relatórios"); rt_o=c11.text_input("Responsável Técnico")
        if st.form_submit_button("💾 Salvar Obra"):
            if not nm_o: st.error("⚠️ Informe o nome.")
            else:
                ok=insert_data("obras",{"nome":nm_o,"rodovia":rod_o,"municipio":mun_o,"contrato":ct_o,"contratante":cont_o,"extensao_km":ext_o or None,"data_inicio":str(ini_o),"prazo":str(fim_o),"status":st_o,"periodo":per_o,"resp_tecnico":rt_o})
                if ok: st.success("✅ Salvo!"); st.rerun()
    df_ob=get_data("obras")
    if not df_ob.empty:
        cs=[c for c in ["nome","rodovia","municipio","contrato","contratante","extensao_km","data_inicio","prazo","status","periodo"] if c in df_ob.columns]
        st.dataframe(df_ob[cs],use_container_width=True)


# ════════════════════════════════════════════════════════════════════
# 8 · RELATÓRIOS E FECHAMENTOS
# ════════════════════════════════════════════════════════════════════
elif menu=="📋 Relatórios e Fechamentos":
    st.markdown("## 📋 Central de Relatórios, Fechamentos e Acertos")
    cd1,cd2=st.columns(2)
    d_ini=cd1.date_input("Data Inicial",value=date.today().replace(day=1))
    d_fim=cd2.date_input("Data Final",value=date.today())
    st.divider()

    df_ab=get_data("abastecimentos"); df_ent=get_data("entradas_tanque")
    df_prod=get_data("producao"); df_f=get_data("fornecedores")
    df_t=get_data("tanques"); df_v=get_data("veiculos")

    def filtrar(df,col="data"):
        if df.empty or col not in df.columns: return df.copy()
        df=df.copy(); df["_dt"]=pd.to_datetime(df[col],errors="coerce").dt.date
        return df[(df["_dt"]>=d_ini)&(df["_dt"]<=d_fim)].drop(columns=["_dt"])

    df_ab_f=filtrar(df_ab).fillna("") if not df_ab.empty else pd.DataFrame()
    df_ent_f=filtrar(df_ent).fillna("") if not df_ent.empty else pd.DataFrame()
    df_pf=filtrar(df_prod).fillna("") if not df_prod.empty else pd.DataFrame()

    tab_posto,tab_tanq,tab_mot,tab_audit=st.tabs(["📤 Fechamento Postos","🛢️ Fechamento Tanque","👷 Acerto Motoristas","📊 Auditoria Completa"])

    # ── Fechamento Postos ────────────────────────────────────────────
    with tab_posto:
        postos=df_f["nome"].tolist() if not df_f.empty else []
        if not postos: st.info("Nenhum fornecedor cadastrado.")
        else:
            cp1,cp2=st.columns(2)
            posto_sel=cp1.selectbox("Posto:",postos)
            per_sel=cp2.text_input("Período",f"{d_ini.strftime('%d/%m/%Y')} a {d_fim.strftime('%d/%m/%Y')}")
            df_posto=pd.DataFrame()
            if not df_ab_f.empty and "fornecedor" in df_ab_f.columns:
                df_posto=df_ab_f[df_ab_f["fornecedor"]==posto_sel].copy()
                if not df_v.empty and "prefixo" in df_posto.columns:
                    df_posto=df_posto.merge(df_v[["prefixo","placa","motorista"]].drop_duplicates("prefixo"),on="prefixo",how="left",suffixes=("","_vf"))
                    for col_ in ["placa","motorista"]:
                        alt=col_+"_vf"
                        if alt in df_posto.columns: df_posto[col_]=df_posto[col_].fillna(df_posto[alt]); df_posto.drop(columns=[alt],inplace=True)
            if not df_posto.empty:
                tl=pd.to_numeric(df_posto.get("quantidade",pd.Series()),errors="coerce").sum()
                tr=pd.to_numeric(df_posto.get("total",pd.Series()),errors="coerce").sum()
                m1,m2,m3=st.columns(3); m1.metric("Registros",len(df_posto)); m2.metric("Total (L)",f"{tl:,.2f} L"); m3.metric("Total (R$)",f"R$ {tr:,.2f}")
                cs_=[c for c in ["data","dia_semana","numero_ficha","placa","prefixo","motorista","fornecedor","tipo_combustivel","quantidade","valor_unitario","total","horimetro","observacao"] if c in df_posto.columns]
                st.dataframe(df_posto[cs_],use_container_width=True)
                fn_row=df_f[df_f["nome"]==posto_sel].iloc[0].to_dict() if not df_f.empty and len(df_f[df_f["nome"]==posto_sel])>0 else {"nome":posto_sel}
                col_pdf,col_xls=st.columns(2)
                with col_pdf:
                    if st.button("📄 Gerar PDF",use_container_width=True):
                        pdf_b=gerar_pdf(df_posto,"SAIDAS",f"OBRA DE PAVIMENTAÇÃO","FECHAMENTO DE CONSUMO",f"PERÍODO: {per_sel}",{"FORNECEDOR":posto_sel,"PIX":fn_row.get("pix",""),"BANCO/AG":f"{fn_row.get('banco','')} / {fn_row.get('agencia','')}","CONTA":fn_row.get("conta","")},f"CONTROLE DE ABASTECIMENTO — {posto_sel}")
                        st.download_button("⬇️ Baixar PDF",pdf_b,f"Fechamento_{posto_sel}.pdf","application/pdf")
                with col_xls:
                    if st.button("📊 Gerar Excel COPA",use_container_width=True):
                        xls_b=gerar_excel_copa(df_posto,fn_row,per_sel,"OBRA DE PAVIMENTAÇÃO",posto_sel)
                        st.download_button("⬇️ Baixar Excel",xls_b,f"Fechamento_{posto_sel}.xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else: st.info(f"Nenhum abastecimento em '{posto_sel}' no período.")

    # ── Fechamento Tanque ────────────────────────────────────────────
    with tab_tanq:
        tanqs=df_t["nome"].tolist() if not df_t.empty else []
        if not tanqs: st.info("Nenhum tanque.")
        else:
            ct1,ct2=st.columns(2)
            tk_sel2=ct1.selectbox("Tanque:",tanqs); per_tk=ct2.text_input("Período",f"{d_ini.strftime('%d/%m/%Y')} a {d_fim.strftime('%d/%m/%Y')}",key="per_tk")
            df_ent_tk=df_ent_f[df_ent_f["nome_tanque"]==tk_sel2].copy() if not df_ent_f.empty and "nome_tanque" in df_ent_f.columns else pd.DataFrame()
            df_sai_tk=pd.DataFrame()
            if not df_ab_f.empty and "origem" in df_ab_f.columns:
                df_sai_tk=df_ab_f[(df_ab_f["origem"]=="Tanque Interno")&(df_ab_f["nome_tanque"]==tk_sel2)].copy()
            te=pd.to_numeric(df_ent_tk.get("quantidade",pd.Series()),errors="coerce").sum() if not df_ent_tk.empty else 0
            ts=pd.to_numeric(df_sai_tk.get("quantidade",pd.Series()),errors="coerce").sum() if not df_sai_tk.empty else 0
            m1,m2,m3,m4=st.columns(4)
            m1.metric("Entradas (L)",f"{te:,.2f}"); m2.metric("Saídas (L)",f"{ts:,.2f}"); m3.metric("Saldo Período",f"{te-ts:,.2f}"); m4.metric("Saldo Acumulado",f"{calcular_saldo(tk_sel2):,.2f}")
            col_p2,col_x2=st.columns(2)
            with col_p2:
                if st.button("📄 PDF Tanque",use_container_width=True):
                    movs2=[]
                    if not df_ent_tk.empty:
                        for _,r in df_ent_tk.iterrows(): movs2.append({**r.to_dict(),"tipo":"Entrada","motorista_forn":r.get("fornecedor",""),"produto":r.get("combustivel",""),"qtd_entrada":float(r.get("quantidade",0) or 0),"qtd_saida":0})
                    if not df_sai_tk.empty:
                        for _,r in df_sai_tk.iterrows(): movs2.append({**r.to_dict(),"tipo":"Saída","motorista_forn":r.get("motorista",""),"produto":r.get("tipo_combustivel",""),"qtd_entrada":0,"qtd_saida":float(r.get("quantidade",0) or 0)})
                    if movs2:
                        df_pdf=pd.DataFrame(movs2).sort_values("data").fillna("")
                        pdf_b2=gerar_pdf(df_pdf,"TANQUE",f"TANQUE: {tk_sel2}","MOVIMENTAÇÕES","f{per_tk}",{"TANQUE":tk_sel2,"ENTRADAS":f"{te:,.1f} L","SAÍDAS":f"{ts:,.1f} L","SALDO":f"{te-ts:,.1f} L"},f"CONTROLE DE TANQUE — {tk_sel2}")
                        st.download_button("⬇️ Baixar PDF",pdf_b2,f"Tanque_{tk_sel2}.pdf","application/pdf")
            with col_x2:
                if st.button("📊 Excel Tanque",use_container_width=True):
                    xls2=gerar_excel_tanque(df_ent_tk,df_sai_tk,tk_sel2,per_tk,"")
                    st.download_button("⬇️ Baixar Excel",xls2,f"Tanque_{tk_sel2}.xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # ── Acerto Motoristas ────────────────────────────────────────────
    with tab_mot:
        if df_pf.empty: st.info("Nenhum boletim no período.")
        else:
            mots=sorted(df_pf["motorista"].dropna().unique().tolist()) if "motorista" in df_pf.columns else []
            if not mots: st.info("Nenhum motorista.")
            else:
                mot_sel2=st.selectbox("Motorista:",mots)
                if st.button("Calcular Acerto",use_container_width=True):
                    df_mot=df_pf[df_pf["motorista"]==mot_sel2].copy()
                    ganho=pd.to_numeric(df_mot.get("valor_frete",pd.Series()),errors="coerce").sum()
                    veics_mot=df_mot["veiculo"].dropna().unique().tolist() if "veiculo" in df_mot.columns else []
                    custo_d=0.0
                    if not df_ab_f.empty:
                        mask_d=(df_ab_f.get("prefixo",pd.Series("")).isin(veics_mot))|(df_ab_f.get("motorista",pd.Series(""))==mot_sel2)
                        if mask_d.any(): custo_d=pd.to_numeric(df_ab_f.loc[mask_d,"total"],errors="coerce").sum()
                    liquido=ganho-custo_d
                    m1,m2,m3=st.columns(3)
                    m1.markdown(f"<div class='kpi-box'><p>Fretes Realizados</p><h3 class='kpi-verde'>R$ {ganho:,.2f}</h3></div>",unsafe_allow_html=True)
                    m2.markdown(f"<div class='kpi-box'><p>Desconto Diesel</p><h3 class='kpi-rojo'>- R$ {custo_d:,.2f}</h3></div>",unsafe_allow_html=True)
                    m3.markdown(f"<div class='kpi-box'><p>Líquido a Receber</p><h3 class='kpi-azul'>R$ {liquido:,.2f}</h3></div>",unsafe_allow_html=True)
                    cs_m=[c for c in ["data","veiculo","tipo_operacao","origem","destino","material","toneladas","carradas","valor_frete","observacao","criado_por"] if c in df_mot.columns]
                    st.dataframe(df_mot[cs_m],use_container_width=True)
                    xls_ac=gerar_excel_limpo(df_mot[cs_m],f"Acerto_{mot_sel2}")
                    st.download_button("⬇️ Exportar Acerto Excel",xls_ac,f"Acerto_{mot_sel2.replace(' ','_')}.xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # ── Auditoria ────────────────────────────────────────────────────
    with tab_audit:
        st.markdown("#### Auditoria Completa — Coluna 'Digitado Por' rastreia cada lançamento")
        if not df_ab_f.empty:
            df_aud=df_ab_f.copy()
            df_aud["horimetro_n"]=pd.to_numeric(df_aud.get("horimetro",0),errors="coerce").fillna(0)
            df_aud=df_aud.sort_values(["prefixo","data","horimetro_n"])
            df_aud["h_ant"]=df_aud.groupby("prefixo")["horimetro_n"].shift(1)
            df_aud["horas_trab"]=df_aud["horimetro_n"]-df_aud["h_ant"]
            df_aud["consumo_L_H"]=df_aud.apply(lambda r: round(r["quantidade"]/r["horas_trab"],2) if pd.notna(r["horas_trab"]) and r["horas_trab"]>0 else None,axis=1)
            cf1,cf2=st.columns(2)
            f_orig=cf1.selectbox("Origem",["Todas","Posto Externo","Tanque Interno"])
            f_pref=cf2.selectbox("Prefixo",["Todos"]+(df_aud["prefixo"].dropna().unique().tolist() if "prefixo" in df_aud.columns else []))
            if f_orig!="Todas" and "origem" in df_aud.columns: df_aud=df_aud[df_aud["origem"]==f_orig]
            if f_pref!="Todos" and "prefixo" in df_aud.columns: df_aud=df_aud[df_aud["prefixo"]==f_pref]
            nmap={"data":"Data","origem":"Origem","nome_tanque":"Tanque","numero_ficha":"Ficha","fornecedor":"Posto","prefixo":"Prefixo","placa":"Placa","motorista":"Operador","tipo_combustivel":"Produto","quantidade":"Litros","valor_unitario":"R$/L","total":"Total R$","horimetro":"Horímetro","consumo_L_H":"Consumo L/H","observacao":"Obs","criado_por":"Digitado Por"}
            df_show=df_aud.rename(columns={k:v for k,v in nmap.items() if k in df_aud.columns})
            cols_sh=[v for k,v in nmap.items() if v in df_show.columns]
            st.dataframe(df_show[cols_sh].sort_values("Data",ascending=False),use_container_width=True)
            xls_au=gerar_excel_limpo(df_show[cols_sh].fillna(""),"Auditoria")
            st.download_button("⬇️ Baixar Auditoria Excel",xls_au,"Auditoria_Completa.xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else: st.info("Nenhum lançamento no período.")


# ════════════════════════════════════════════════════════════════════
# 9 · USUÁRIOS E ACESSOS
# ════════════════════════════════════════════════════════════════════
elif menu=="👥 Usuários e Acessos":
    if st.session_state.perfil_logado!="Admin": st.error("⛔ Acesso restrito."); st.stop()
    st.markdown("## 👥 Gestão de Usuários e Acessos")
    st.info("O campo **'Digitado Por'** registra automaticamente quem fez cada lançamento.")
    with st.form("f_usr",clear_on_submit=True):
        c1,c2=st.columns(2); nm_u=c1.text_input("Nome Completo"); lg_u=c2.text_input("Login")
        c3,c4=st.columns(2); sn_u=c3.text_input("Senha",type="password"); pf_u=c4.selectbox("Perfil",["Operador","Admin"])
        if st.form_submit_button("💾 Criar Usuário"):
            if nm_u and lg_u and sn_u:
                ok=insert_data("usuarios",{"nome":nm_u,"login":lg_u,"senha":sn_u,"perfil":pf_u})
                if ok: st.success("✅ Usuário criado!"); st.rerun()
            else: st.error("⚠️ Preencha todos os campos.")
    st.divider()
    df_u=get_data("usuarios")
    if not df_u.empty:
        for _,r in df_u.iterrows():
            c1,c2=st.columns([5,1]); c1.write(f"👤 **{r['nome']}**  |  Login: `{r['login']}`  |  Perfil: {r['perfil']}")
            if r.get("login")!="admin":
                if c2.button("🗑️",key=f"du_{r['id']}"): delete_data("usuarios",r["id"]); st.rerun()
