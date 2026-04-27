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

# CSS GERAL DA APLICAÇÃO (DASHBOARD E FORMULÁRIOS MODERNIZADOS)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.main { background-color: #F4F7FB; }
[data-testid="stSidebar"] { background: #0F1923; }
[data-testid="stSidebar"] * { color: #C9D4E0 !important; }
[data-testid="stSidebar"] h3 { color: #1D9E75 !important; }

/* ═════════ ESTILO DOS CAMPOS DE PREENCHIMENTO E TEXTOS ═════════ */
.stTextInput>label, .stSelectbox>label, .stNumberInput>label,
.stDateInput>label, .stTimeInput>label, .stTextArea>label {
    font-size: 13px !important; 
    color: #1E293B !important; 
    font-weight: 700 !important; 
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 6px !important;
}
div[data-baseweb="input"], div[data-baseweb="select"] {
    border-radius: 8px !important;
    border: 1px solid #CBD5E1 !important;
    background-color: #F8FAFC !important; 
    padding: 2px !important;
}
div[data-baseweb="input"]:focus-within, div[data-baseweb="select"]:focus-within {
    border-color: #0A58CA !important;
    box-shadow: 0 0 0 3px rgba(10, 88, 202, 0.15) !important;
    background-color: #FFFFFF !important;
}

/* ═════════ ESTILO DOS BOTÕES ═════════ */
div.stButton > button:first-child {
    background-color: #0A58CA !important; 
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 800 !important;
    font-size: 15px !important; 
    padding: 0.75rem 1.5rem !important;
    box-shadow: 0 4px 6px rgba(0,0,0,0.15) !important;
    transition: all 0.2s ease-in-out !important;
    text-transform: uppercase !important;
}
div.stButton > button:first-child:hover {
    background-color: #084298 !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 12px rgba(0,0,0,0.2) !important;
}

/* ═════════ ESTILO DOS CARDS E AVISOS ═════════ */
div[data-testid="stForm"] {
    border: none; border-radius: 16px;
    padding: 2rem; background: white;
    box-shadow: 0 10px 30px rgba(0,0,0,0.08);
}
.banner-ok  { background:#EAF3DE; color:#3B6D11; border:1px solid #C0DD97; border-radius:10px; padding:12px 16px; font-weight:600; font-size:13px; margin-bottom:1rem; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }
.banner-low { background:#FAEEDA; color:#854F0B; border:1px solid #FAC775; border-radius:10px; padding:12px 16px; font-weight:600; font-size:13px; margin-bottom:1rem; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }
.banner-err { background:#FCEBEB; color:#A32D2D; border:1px solid #F0B0AE; border-radius:10px; padding:12px 16px; font-weight:600; font-size:13px; margin-bottom:1rem; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }
.banner-info{ background:#E6F1FB; color:#185FA5; border:1px solid #A8C9EE; border-radius:10px; padding:12px 16px; font-weight:600; font-size:13px; margin-bottom:1rem; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }
.kpi-box { background:white; border:none; border-radius:12px; padding:1.5rem; text-align:center; height:100%; box-shadow: 0 4px 15px rgba(0,0,0,0.04); transition: transform 0.2s ease; }
.kpi-box:hover { transform: translateY(-2px); box-shadow: 0 8px 20px rgba(0,0,0,0.08); }
.kpi-box h3 { margin:0; font-size:24px; color:#0F1923; margin-top: 10px; }
.kpi-box p  { margin:0; font-size:11px; color:#64748B; text-transform:uppercase; font-weight:700; letter-spacing: 0.05em; }
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
# EXPORTAÇÃO — EXCEL PADRÃO COPA E PDF TIMBRADO
# ═══════════════════════════════════════════════════════════════════
def gerar_excel_copa(df: pd.DataFrame, dados_forn: dict, periodo: str, obra: str, nome_forn: str = "") -> bytes:
    df = df.fillna("").copy()
    dias_pt = {0:"SEG",1:"TER",2:"QUA",3:"QUI",4:"SEX",5:"SÁB",6:"DOM"}
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

    heads = ["DATA","DIA DA\nSEMANA","FICHA","PLACA","CÓDIGO /\nPREFIXO","VEÍCULO / MAQUINA -\nMOTORISTA / OPERADOR","FORNECEDOR","TIPO DE\nCOMBUSTÍVEL","QUANTIDADE\n(L)","VALOR\nUNITÁRIO (R$)","TOTAL\n(R$)","KM / HOR","OBSERVAÇÃO"]
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
        for ci,v in enumerate([str(r.get("data",""))[:10],dia_str,str(r.get("numero_ficha","")),str(r.get("placa","")),str(r.get("prefixo","")),str(r.get("motorista","")),str(r.get("fornecedor","")),str(r.get("tipo_combustivel",""))]):
            ws.write(ri,ci,v,fd)
        ws.write(ri,8,qtd,fn); ws.write(ri,9,vunt,fm); ws.write(ri,10,tot,fm)
        ws.write(ri,11,str(r.get("horimetro","")),fd); ws.write(ri,12,str(r.get("observacao","")),fd)

    row_t=5+len(df)
    ws.merge_range(row_t,0,row_t,7,"TOTAL",ftx)
    ws.write(row_t,8,t_l,ft); ws.write(row_t,9,"",ftx); ws.write(row_t,10,t_r,ftm)
    ws.write(row_t,11,"TOTAL",ftx); ws.write(row_t,12,"",ftx)
    wb.close(); buf.seek(0); return buf.getvalue()

def gerar_excel_tanque(df_ent: pd.DataFrame, df_sai: pd.DataFrame, nome_tanque: str, periodo: str, obra: str) -> bytes:
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

    heads=["DATA","DIA","TIPO","FICHA","PLACA","PREF.","VEÍ./OPERADOR","PRODUTO / FORNEC.","KM/HOR","QTD ENTRADA (L)","QTD SAÍDA (L)","VL UNIT. (R$)","TOTAL (R$)","SALDO (L)","OBRA"]
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

def gerar_pdf(df: pd.DataFrame, tipo: str, titulo_esq: str, sub_esq: str, per_esq: str, dados_dir: dict, titulo_tab: str) -> bytes:
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
        cols=[("DATA",16),("FICHA",15),("PLACA",14),("PREF.",12),("MÁQUINA / MOTORISTA",52),("PRODUTO",18),("QTD (L)",14),("V.UNIT.",14),("TOTAL (R$)",20),("KM/HOR",13),("OBS",69)]
    elif tipo=="TANQUE":
        cols=[("DATA",14),("TIPO",10),("FICHA",14),("PLACA",13),("PREF.",10),("OPERADOR / FORNEC.",40),("PRODUTO",16),("KM/H",10),("ENTRADA(L)",17),("SAÍDA(L)",14),("V.UNIT.",13),("TOTAL",15),("SALDO(L)",14),("OBS",37)]
    else:
        cols=[("DATA",18),("NF/FICHA",22),("DISTRIBUIDORA",60),("TANQUE",42),("PRODUTO",22),("QTD (L)",20),("V.UNIT.",20),("TOTAL (R$)",23),("OBS",30)]

    for n,w in cols: pdf.cell(w,7,n,border=1,align="C",fill=True)
    pdf.ln(); pdf.set_font("Arial","",7)
    t_l=0.0; t_r=0.0; saldo=0.0

    for _,r in df.iterrows():
        q=float(r.get("quantidade",0) or 0); v=float(r.get("valor_unitario",0) or 0); t=float(r.get("total",0) or 0)
        qe=float(r.get("qtd_entrada",0) or 0); qs=float(r.get("qtd_saida",0) or 0)
        saldo+=qe-qs
        if tipo=="SAIDAS":
            for val,w in [(str(r.get("data",""))[:10],16),(str(r.get("numero_ficha",""))[:14],15),(str(r.get("placa",""))[:8],14),(str(r.get("prefixo",""))[:8],12),(str(r.get("motorista",""))[:33],52),(str(r.get("tipo_combustivel",""))[:12],18)]:
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
# LOGIN — ESTRUTURA VISUAL E CSS CONDICIONAL
# ═══════════════════════════════════════════════════════════════════
for k,v in [("logged_in",False),("usuario_logado",""),("perfil_logado","")]:
    if k not in st.session_state: st.session_state[k]=v

import psutil

if not st.session_state.logged_in:
    st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(rgba(15, 25, 35, 0.7), rgba(15, 25, 35, 0.7)), 
        url('https://images.unsplash.com/photo-1463171379579-3fdfb86d6285?q=80&w=2070') 
        no-repeat center center fixed !important;
        background-size: cover !important;
    }

    [data-testid="stHeader"] { background: transparent !important; }
    [data-testid="stSidebar"] { display: none; }

    /* 🔥 REMOVE ESPAÇOS EXAGERADOS */
    div[data-testid="stForm"] {
        margin-top: -20px;
    }

    img {
        margin-bottom: -15px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 🔥 MENOS ESPAÇO NO TOPO
    st.write("<br>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 2.5, 1])

    with c2:
        with st.form("login"):
            if os.path.exists("logo.png"): 
                col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
                with col_l2:
                    st.image("logo.png", width=280)
                    st.markdown("<div style='margin-top:-25px'></div>", unsafe_allow_html=True)
            
            st.markdown("""
            <h2 style='text-align:center;
                       color:#1E293B;
                       font-weight:700;
                       margin-top:0;
                       margin-bottom:0.3rem;'>
                Acesso Restrito
            </h2>
            """, unsafe_allow_html=True)

            u = st.text_input("Usuário")
            p = st.text_input("Senha", type="password")
            
            st.write("<br>", unsafe_allow_html=True)

            if st.form_submit_button("ENTRAR NO SISTEMA", use_container_width=True):
                try:
                    res = supabase.table("usuarios").select("*").eq("login", u).eq("senha", p).execute()
                    if res.data:
                        st.session_state.logged_in = True
                        st.session_state.usuario_logado = res.data[0]["nome"]
                        st.session_state.perfil_logado = res.data[0]["perfil"]
                        st.rerun()
                    else:
                        st.error("❌ Usuário ou senha incorretos.")
                except:
                    if u == st.secrets.get("ADMIN_USER", "admin") and p == st.secrets.get("ADMIN_PASS", "obra2026"):
                        st.session_state.logged_in = True
                        st.session_state.usuario_logado = "Admin"
                        st.session_state.perfil_logado = "Admin"
                        st.rerun()
                    else:
                        st.error("❌ Usuário ou senha incorretos.")

    st.stop()


# ═══════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════
with st.sidebar:
    if os.path.exists("logo.png"):
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.image("logo.png", width=220)

    st.markdown(
        f"<div style='text-align:center;color:#1D9E75;font-size:13px;font-weight:bold;'>👤 {st.session_state.usuario_logado}</div>",
        unsafe_allow_html=True
    )

    st.divider()

    # 🔐 BOTÃO SAIR
    if st.button("🚪 Sair", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.usuario_logado = ""
        st.session_state.perfil_logado = ""
        st.rerun()

    # 💾 MEMÓRIA
    mem = psutil.virtual_memory()
    st.markdown(
        f"<div style='text-align:center;font-size:12px;'>💾 Memória: <b>{mem.percent}%</b></div>",
        unsafe_allow_html=True
    )

    st.divider()

    opcoes = [
        "🏠 Painel Início",
        "⛽ Lançar Abastecimento",
        "🛢️ Tanques / Estoque",
        "🚚 Boletim de Transporte",
        "🚜 Frota e Equipamentos",
        "🏪 Fornecedores",
        "📋 Relatórios e Fechamentos"
    ]
            
    if st.session_state.perfil_logado == "Admin":
        opcoes.append("👥 Usuários e Acessos")

    menu = st.sidebar.radio("", opcoes, label_visibility="collapsed")

    st.divider()
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

    df_v = get_data("veiculos")
    df_f = get_data("fornecedores")
    df_a = get_data("abastecimentos")
    df_t = get_data("tanques")

    if df_v.empty:
        st.warning("⚠️ Cadastre veículos primeiro.")
        st.stop()

    # Proteções
    if not df_a.empty:
        if "status" not in df_a.columns:
            df_a["status"] = "ATIVO"

    v_sel = st.selectbox("🚜 Máquina / Equipamento", df_v["prefixo"].tolist())
    info_v = df_v[df_v["prefixo"] == v_sel].iloc[0]

    comb_padrao = info_v.get("tipo_combustivel_padrao", "Diesel S10")
    motorista_padrao = info_v.get("motorista", "")
    placa_padrao = info_v.get("placa", "")

    m_hor = 0.0
    if not df_a.empty and "horimetro" in df_a.columns:
        hist = df_a[df_a["prefixo"] == v_sel]
        if not hist.empty:
            m_hor = float(pd.to_numeric(hist["horimetro"], errors="coerce").max() or 0)

    st.markdown(f"""
    <div class='banner-info'>
    ⛽ Combustível: <strong>{comb_padrao}</strong> |
    🪪 Placa: <strong>{placa_padrao}</strong> |
    ⏱️ Último KM/Hor: <strong>{m_hor:,.1f}</strong>
    </div>
    """, unsafe_allow_html=True)

    origem = st.radio("Origem:", ["Posto Externo", "Tanque Interno"], horizontal=True)

    # ================= FORM =================
    with st.form("f_ab", clear_on_submit=True):

        c1, c2, c3 = st.columns(3)
        data_ab = c1.date_input("Data")
        ficha = c2.text_input("Ficha")
        motorista = c3.text_input("Motorista", value=motorista_padrao)

        c4, c5, c6 = st.columns(3)

        if origem == "Posto Externo":
            posto = c4.selectbox("Fornecedor", df_f["nome"].tolist() if not df_f.empty else ["Sem cadastro"])
            n_tanq = None
        else:
            n_tanq = c4.selectbox("Tanque", df_t["nome"].tolist())
            posto = "Estoque Próprio"

        hor = c5.number_input("KM / Horímetro", value=m_hor)
        obs = c6.text_input("Observação")

        c7, c8 = st.columns(2)
        litros = c7.number_input("Litros", min_value=0.0)
        preco = c8.number_input("Preço (R$/L)", min_value=0.0)

        total = litros * preco

        st.markdown(f"""
        <div class='banner-info' style='text-align:center'>
        💰 Total: <strong>R$ {total:,.2f}</strong>
        </div>
        """, unsafe_allow_html=True)

        if st.form_submit_button("💾 Salvar"):

            if litros <= 0:
                st.error("⚠️ Litros inválido.")
            else:

                dados = {
                    "data": str(data_ab),
                    "numero_ficha": ficha,
                    "origem": origem,
                    "nome_tanque": n_tanq,
                    "prefixo": v_sel,
                    "placa": placa_padrao,
                    "motorista": motorista.upper(),
                    "tipo_combustivel": comb_padrao,
                    "quantidade": litros,
                    "valor_unitario": preco,
                    "total": total,
                    "fornecedor": posto,
                    "horimetro": hor,
                    "observacao": obs,
                    "status": "ATIVO"
                }

                ok = insert_data("abastecimentos", dados)

                if ok:
                    st.success("✅ Salvo!")
                    st.rerun()

    # ================= LISTAGEM =================
    st.divider()
    st.subheader("📋 Abastecimentos")

    if df_a.empty:
        st.info("Nenhum registro.")
    else:

        df_a = df_a.sort_values("data", ascending=False).fillna("")

        ativos = df_a[df_a["status"] == "ATIVO"]
        cancelados = df_a[df_a["status"] != "ATIVO"]

        tab1, tab2 = st.tabs(["✅ Ativos", "❌ Cancelados"])

        # ===== ATIVOS =====
        with tab1:
            if ativos.empty:
                st.info("Nenhum ativo.")
            else:
                for _, r in ativos.head(20).iterrows():
                    c1, c2, c3 = st.columns([5,1,1])

                    c1.markdown(
                        f"📅 {r.get('data','')} | "
                        f"🚜 {r.get('prefixo','')} | "
                        f"⛽ {r.get('quantidade',0)} L | "
                        f"💰 R$ {r.get('total',0):,.2f}"
                    )

                    if c2.button("✏️", key=f"edit_{r.get('id')}"):
                        st.warning("Edição em breve")

                    if c3.button("❌", key=f"cancel_{r.get('id')}"):
                        supabase.table("abastecimentos").update({
                            "status": "CANCELADO"
                        }).eq("id", r.get("id")).execute()

                        st.warning("Cancelado!")
                        st.rerun()

        # ===== CANCELADOS =====
        with tab2:
            if cancelados.empty:
                st.info("Nenhum cancelado.")
            else:
                for _, r in cancelados.head(20).iterrows():
                    c1, c2 = st.columns([5,1])

                    c1.markdown(
                        f"❌ {r.get('data','')} | "
                        f"{r.get('prefixo','')} | "
                        f"{r.get('quantidade',0)} L"
                    )

                    if c2.button("↩️", key=f"restore_{r.get('id')}"):
                        supabase.table("abastecimentos").update({
                            "status": "ATIVO"
                        }).eq("id", r.get("id")).execute()

                        st.success("Restaurado!")
                        st.rerun()
# ════════════════════════════════════════════════════════════════════
# 3 · TANQUES / ESTOQUE
# ════════════════════════════════════════════════════════════════════
elif menu=="🛢️ Tanques / Estoque":
    st.markdown("## 🛢️ Gestão de Tanques e Comboios")
    tab1,tab2=st.tabs(["➕ Lançar Entrada de Combustível","📋 Cadastrar Novo Tanque"])
    df_t=get_data("tanques"); df_f=get_data("fornecedores"); df_ent=get_data("entradas_tanque")
    
    with tab1:
        if df_t.empty: st.warning("Cadastre um tanque primeiro.")
        else:
            with st.form("f_ent_t",clear_on_submit=True):
                c1,c2=st.columns(2); d_e=c1.date_input("Data",value=date.today()); nf_e=c2.text_input("NF / Documento")
                c3,c4=st.columns(2)
                forn=c3.selectbox("Fornecedor (Distribuidora)",df_f["nome"].tolist() if not df_f.empty else ["Sem cadastro"])
                tanq=c4.selectbox("Tanque Destino",df_t["nome"].tolist())
                c5,c6,c7=st.columns(3)
                prod=c5.selectbox("Produto",["Diesel S10","Diesel S500","Gasolina Comum"])
                qtd=c6.number_input("Quantidade (Litros)",min_value=0.0)
                vunt=c7.number_input("Valor Unitário (R$)",min_value=0.0)
                obs_e=st.text_input("Observação")
                if st.form_submit_button("📥 Registrar Entrada",use_container_width=True):
                    if qtd<=0: st.error("⚠️ Quantidade inválida.")
                    else:
                        ok=insert_data("entradas_tanque",{"data":str(d_e),"numero_ficha":nf_e,"fornecedor":forn,"nome_tanque":tanq,"combustivel":prod,"quantidade":qtd,"valor_unitario":vunt,"total":qtd*vunt,"observacao":obs_e,"criado_por":st.session_state.usuario_logado})
                        if ok: st.success("✅ Entrada salva!"); time.sleep(1); st.rerun()
            if not df_ent.empty:
                st.subheader("Últimas Entradas")
                df_e_rec=df_ent.sort_values("data",ascending=False).head(10).fillna("")
                
                cols_ent = ["data","numero_ficha","fornecedor","nome_tanque","combustivel","quantidade","valor_unitario","total","criado_por"]
                cols_presentes = [c for c in cols_ent if c in df_e_rec.columns]
                st.dataframe(df_e_rec[cols_presentes],use_container_width=True)
    with tab2:
        with st.form("f_t",clear_on_submit=True):
            nm_t=st.text_input("Nome do Tanque/Comboio")
            cap=st.number_input("Capacidade Máxima (Litros)",min_value=0.0)
            if st.form_submit_button("💾 Salvar Tanque",use_container_width=True):
                if nm_t:
                    ok=insert_data("tanques",{"nome":nm_t.upper(),"capacidade":cap,"criado_por":st.session_state.usuario_logado})
                    if ok: st.success("✅ Tanque salvo!"); time.sleep(1); st.rerun()
                else: st.error("⚠️ Preencha o nome.")
        if not df_t.empty:
            st.subheader("Tanques Cadastrados")
            for _,r in df_t.iterrows():
                cc1,cc2=st.columns([4,1])
                cc1.write(f"**{r['nome']}** — Capacidade: {r.get('capacidade',0):.0f}L")
                if cc2.button("❌",key=f"d_t_{r['id']}"):
                    if delete_data("tanques",r["id"]): st.rerun()

# ════════════════════════════════════════════════════════════════════
# 4 · BOLETIM DE TRANSPORTE E PRODUÇÃO
# ════════════════════════════════════════════════════════════════════
elif menu=="🚚 Boletim de Transporte":
    st.markdown("## 🚚 Boletim Diário de Produção")
    df_v=get_data("veiculos")
    if df_v.empty: st.warning("⚠️ Cadastre veículos primeiro."); st.stop()

    with st.form("f_prod",clear_on_submit=True):
        st.markdown("#### 👤 Dados Operacionais")
        c1,c2,c3=st.columns(3)
        dt_p=c1.date_input("Data do Boletim",value=date.today())
        pref=c2.selectbox("Veículo / Equipamento",df_v["prefixo"].tolist())
        v_info=df_v[df_v["prefixo"]==pref].iloc[0]
        mot=c3.text_input("Motorista / Operador",value=v_info.get("motorista",""))
        
        st.markdown("#### 🛣️ Rota e Viagem")
        c4,c5,c6 = st.columns(3)
        op_tipo=c4.selectbox("Tipo de Operação",["Transporte de Massa/CBUQ","Transporte de Fresado","Terraplanagem","Venda de Massa","Ocioso/Manutenção"])
        origem_rota=c5.text_input("Origem / Jazida (Ex: Usina, Pedreira, Base)")
        destino_rota=c6.text_input("Destino / Trecho de Aplicação")
        
        st.markdown("#### 📊 Produção e Hodômetro")
        c7,c8,c9,c10=st.columns(4)
        km_s=c7.number_input("KM Inicial",min_value=0.0)
        km_c=c8.number_input("KM Final",min_value=0.0)
        carradas=c9.number_input("Nº de Carradas/Viagens",min_value=0,step=1)
        ton=c10.number_input("Total Toneladas",min_value=0.0)
        
        st.markdown("#### ⛽ Abastecimento na Viagem (Opcional)")
        c11, c12, c13 = st.columns(3)
        houve_abast = c11.checkbox("Houve abastecimento externo nesta rota?")
        litros_rota = c12.number_input("Litros abastecidos", min_value=0.0) if houve_abast else 0.0
        valor_abast_rota = c13.number_input("Valor Total (R$)", min_value=0.0) if houve_abast else 0.0

        obs_p=st.text_input("Observações Gerais")

        if st.form_submit_button("💾 Salvar Boletim Diário",use_container_width=True):
            if op_tipo!="Ocioso/Manutenção" and carradas<=0: 
                st.error("⚠️ Insira a quantidade de viagens.")
            else:
                # Dicionário de dados atualizado com as informações completas da viagem
                dados_inserir = {
                    "data": str(dt_p),
                    "prefixo": pref,
                    "motorista": mot.upper(),
                    "tipo_operacao": op_tipo,
                    "origem": origem_rota.upper(),
                    "destino": destino_rota.upper(),
                    "local_aplicacao": destino_rota.upper(), # Mantido para compatibilidade com relatórios
                    "km_saida": km_s,
                    "km_chegada": km_c,
                    "carradas": carradas,
                    "toneladas": ton,
                    "abastecimento_litros": litros_rota,
                    "abastecimento_valor": valor_abast_rota,
                    "observacao": obs_p,
                    "criado_por": st.session_state.usuario_logado
                }
                ok=insert_data("producao", dados_inserir)
                if ok: st.success("✅ Boletim salvo!"); time.sleep(1); st.rerun()

    df_bol=get_data("producao")
    if not df_bol.empty:
        st.divider(); st.subheader("📋 Últimos Boletins Registrados")
        df_br=df_bol.sort_values("data",ascending=False).head(20).fillna("")
        
        # Tabela agora exibe as colunas de origem, destino e abastecimento
        colunas_bol=["data","prefixo","motorista","tipo_operacao", "origem", "destino", "carradas","toneladas", "abastecimento_litros", "km_saida","km_chegada"]
        
        # A vacina contra o Bug: Só puxa as colunas se elas existirem no banco de dados!
        colunas_presentes = [c for c in colunas_bol if c in df_br.columns]
        df_exibir = df_br[colunas_presentes].copy()
        
        st.dataframe(df_exibir,use_container_width=True)

# ════════════════════════════════════════════════════════════════════
# 5 · FROTA E EQUIPAMENTOS
# ════════════════════════════════════════════════════════════════════
elif menu=="🚜 Frota e Equipamentos":
    st.markdown("## 🚜 Gestão de Frota")

    df_v = get_data("veiculos")

    # 🛡️ Proteção contra colunas inexistentes
    if not df_v.empty:
        if "categoria" not in df_v.columns:
            df_v["categoria"] = df_v.get("tipo", "")
        if "tipo_combustivel_padrao" not in df_v.columns:
            df_v["tipo_combustivel_padrao"] = ""
        if "motorista" not in df_v.columns:
            df_v["motorista"] = ""
        if "placa" not in df_v.columns:
            df_v["placa"] = ""

    # ═════════ CADASTRO ═════════
    with st.expander("➕ CADASTRAR NOVO VEÍCULO / EQUIPAMENTO", expanded=True):
        with st.form("f_v", clear_on_submit=True):

            c1, c2, c3 = st.columns(3)
            pref = c1.text_input("Código / Prefixo (Ex: CA-01)")
            plc  = c2.text_input("Placa")
            categoria = c3.selectbox("Categoria", ["Veículo", "Equipamento"])

            c4, c5 = st.columns(2)
            mot  = c4.text_input("Motorista / Operador Fixo")
            comb = c5.selectbox("Combustível Padrão", ["Diesel S10","Diesel S500","Gasolina Comum"])

            if st.form_submit_button("💾 Salvar", use_container_width=True):

                if pref:
                    dados = {
                        "prefixo": pref.upper(),
                        "placa": plc.upper(),
                        "categoria": categoria,
                        "motorista": mot.upper(),
                        "tipo_combustivel_padrao": comb
                    }

                    ok = insert_data("veiculos", dados)

                    if ok:
                        st.success("✅ Salvo com sucesso!")
                        st.rerun()
                else:
                    st.error("⚠️ Prefixo é obrigatório.")

    # ═════════ LISTAGEM ═════════
    if not df_v.empty:
        st.divider()
        st.subheader("📋 Frota Ativa")

        for _, r in df_v.iterrows():
            cc1, cc2 = st.columns([5,1])

            categoria = r.get("categoria") or r.get("tipo") or "-"

            cc1.markdown(
                f"**{r.get('prefixo','')}** | "
                f"{categoria} | "
                f"Placa: {r.get('placa','')} | "
                f"Operador: {r.get('motorista','')}"
            )

            if cc2.button("❌ Excluir", key=f"d_v_{r.get('id','x')}"):
                if delete_data("veiculos", r.get("id")):
                    st.rerun()
# ════════════════════════════════════════════════════════════════════
# 6 · FORNECEDORES
# ════════════════════════════════════════════════════════════════════
elif menu=="🏪 Fornecedores":
    st.markdown("## 🏪 Postos e Distribuidoras")
    df_f=get_data("fornecedores")
    with st.expander("➕ CADASTRAR NOVO FORNECEDOR",expanded=True):
        with st.form("f_f",clear_on_submit=True):
            c1,c2=st.columns(2)
            nm=c1.text_input("Nome Fantasia (Aparece no App)")
            rz=c2.text_input("Razão Social")
            st.markdown("**DADOS BANCÁRIOS / EXPORTAÇÃO**")
            c3,c4,c5=st.columns(3)
            banco=c3.text_input("Banco")
            ag=c4.text_input("Agência")
            cta=c5.text_input("Conta")
            c6,c7=st.columns(2)
            tipo_c=c6.selectbox("Tipo Conta",["Corrente","Poupança"])
            pix=c7.text_input("Chave PIX")
            st.markdown("**PREÇOS CONTRATUAIS (Opcional)**")
            c8,c9=st.columns(2)
            p_d=c8.number_input("Preço Diesel Acordado (R$)",min_value=0.0)
            p_g=c9.number_input("Preço Gasolina Acordado (R$)",min_value=0.0)
            if st.form_submit_button("💾 Salvar Fornecedor",use_container_width=True):
                if nm:
                    ok=insert_data("fornecedores",{"nome":nm.upper(),"razao_social":rz.upper(),"banco":banco,"agencia":ag,"conta":cta,"tipo_conta":tipo_c,"pix":pix,"preco_diesel":p_d,"preco_gasolina":p_g,"criado_por":st.session_state.usuario_logado})
                    if ok: st.success("✅ Salvo!"); time.sleep(1); st.rerun()
                else: st.error("⚠️ Nome Fantasia é obrigatório.")

    if not df_f.empty:
        st.divider(); st.subheader("📋 Fornecedores Cadastrados")
        for _,r in df_f.iterrows():
            cc1,cc2=st.columns([5,1])
            cc1.markdown(f"**{r['nome']}** | Banco: {r.get('banco','')} Ag: {r.get('agencia','')} Cc: {r.get('conta','')} | PIX: {r.get('pix','')}")
            if cc2.button("❌ Excluir",key=f"d_f_{r['id']}"):
                if delete_data("fornecedores",r["id"]): st.rerun()


# ════════════════════════════════════════════════════════════════════
# 8 · RELATÓRIOS E FECHAMENTOS (Mantido intacto para não perder lógica de pdf)
# ════════════════════════════════════════════════════════════════════
elif menu=="📋 Relatórios e Fechamentos":
    st.markdown("## 📋 Central de Relatórios")
    aba1,aba2,aba3=st.tabs(["⛽ Relatório de Saídas","🛢️ Fechamento de Tanques","📉 Resumo Gerencial / Produção"])
    
    with aba1:
        st.markdown("#### Gerar Fechamento de Posto Externo")
        df_a=get_data("abastecimentos"); df_f=get_data("fornecedores")
        c1,c2,c3=st.columns(3)
        dt_i=c1.date_input("Início (Saídas)",value=date.today().replace(day=1))
        dt_f=c2.date_input("Fim (Saídas)",value=date.today())
        forn_sel=c3.selectbox("Filtrar Fornecedor",["TODOS"]+(df_f["nome"].tolist() if not df_f.empty else []))
        if st.button("🔍 Filtrar Saídas"):
            if df_a.empty: st.warning("Sem dados.")
            else:
                df_a["data_dt"]=pd.to_datetime(df_a["data"],errors="coerce").dt.date
                df_filtro=df_a[(df_a["data_dt"]>=dt_i)&(df_a["data_dt"]<=dt_f)]
                if forn_sel!="TODOS": df_filtro=df_filtro[df_filtro["fornecedor"]==forn_sel]
                df_filtro=df_filtro.sort_values("data")
                st.write(f"Encontrados **{len(df_filtro)}** registros.")
                if not df_filtro.empty:
                    c4,c5,c6=st.columns(3)
                    per_str=f"{dt_i.strftime('%d/%m/%Y')} a {dt_f.strftime('%d/%m/%Y')}"
                    obra_padrao="COPA ENGENHARIA"
                    dados_forn={}
                    if forn_sel!="TODOS" and not df_f.empty:
                        fs=df_f[df_f["nome"]==forn_sel]
                        if not fs.empty: dados_forn=fs.iloc[0].to_dict()
                    
                    xl_copa=gerar_excel_copa(df_filtro,dados_forn,per_str,obra_padrao,forn_sel if forn_sel!="TODOS" else "GERAL")
                    c4.download_button("📥 Excel Padrão",data=xl_copa,file_name=f"Abastecimentos_{forn_sel}_{dt_i}.xlsx",mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",use_container_width=True)
                    
                    dados_pdf={"FORNECEDOR":forn_sel if forn_sel!="TODOS" else "GERAL","PERÍODO":per_str}
                    if dados_forn:
                        dados_pdf["CNPJ/CPF"]=dados_forn.get("cnpj","")
                        dados_pdf["BANCO"]=dados_forn.get("banco","")
                        dados_pdf["AGÊNCIA"]=dados_forn.get("agencia","")
                        dados_pdf["CONTA"]=dados_forn.get("conta","")
                        dados_pdf["PIX"]=dados_forn.get("pix","")
                    pdf_bytes=gerar_pdf(df_filtro,"SAIDAS","COPA ENGENHARIA LTDA","DEPARTAMENTO DE EQUIPAMENTOS",f"PERÍODO: {per_str}",dados_pdf,f"RELATÓRIO DE ABASTECIMENTOS - {forn_sel if forn_sel!='TODOS' else 'GERAL'}")
                    c5.download_button("📄 PDF Timbrado",data=pdf_bytes,file_name=f"Relatorio_{forn_sel}_{dt_i}.pdf",mime="application/pdf",use_container_width=True)
                    
                    xl_limpo=gerar_excel_limpo(df_filtro,"Saídas")
                    c6.download_button("📊 Excel Tabela Limpa",data=xl_limpo,file_name="Tabela_Saidas.xlsx",mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",use_container_width=True)

    with aba2:
        st.markdown("#### Fechamento Físico de Tanques (Entradas vs Saídas)")
        df_ent=get_data("entradas_tanque"); df_t=get_data("tanques")
        c1,c2,c3=st.columns(3)
        di_t=c1.date_input("Data Início (Tanque)",value=date.today().replace(day=1))
        df_tq=c2.date_input("Data Fim (Tanque)",value=date.today())
        tanq_sel=c3.selectbox("Selecionar Tanque",df_t["nome"].tolist() if not df_t.empty else ["Sem cadastro"])
        if st.button("🔍 Gerar Fechamento de Tanque"):
            per_t=f"{di_t.strftime('%d/%m/%Y')} a {df_tq.strftime('%d/%m/%Y')}"
            ent_f=pd.DataFrame(); sai_f=pd.DataFrame()
            if not df_ent.empty:
                df_ent["data_dt"]=pd.to_datetime(df_ent["data"],errors="coerce").dt.date
                ent_f=df_ent[(df_ent["data_dt"]>=di_t)&(df_ent["data_dt"]<=df_tq)&(df_ent["nome_tanque"]==tanq_sel)]
            if not df_a.empty:
                sai_f=df_a[(df_a["origem"]=="Tanque Interno")&(df_a["nome_tanque"]==tanq_sel)]
                if not sai_f.empty:
                    sai_f["data_dt"]=pd.to_datetime(sai_f["data"],errors="coerce").dt.date
                    sai_f=sai_f[(sai_f["data_dt"]>=di_t)&(sai_f["data_dt"]<=df_tq)]
            if ent_f.empty and sai_f.empty: st.warning("Nenhum movimento no período.")
            else:
                xl_t=gerar_excel_tanque(ent_f,sai_f,tanq_sel,per_t,"COPA ENGENHARIA")
                c4,c5=st.columns(2)
                c4.download_button("📥 Baixar Excel do Tanque",data=xl_t,file_name=f"Tanque_{tanq_sel}_{di_t}.xlsx",mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",use_container_width=True)
                
                movs=[]
                if not ent_f.empty:
                    for _,r in ent_f.iterrows():
                        movs.append({"data":r.get("data",""),"tipo":"ENTRADA","numero_ficha":r.get("numero_ficha",""),"motorista_forn":r.get("fornecedor",""),"produto":r.get("combustivel",""),"qtd_entrada":r.get("quantidade",0),"qtd_saida":0,"valor_unitario":r.get("valor_unitario",0),"total":r.get("total",0),"observacao":r.get("observacao","")})
                if not sai_f.empty:
                    for _,r in sai_f.iterrows():
                        movs.append({"data":r.get("data",""),"tipo":"SAÍDA","numero_ficha":r.get("numero_ficha",""),"placa":r.get("placa",""),"prefixo":r.get("prefixo",""),"motorista_forn":r.get("motorista",""),"produto":r.get("tipo_combustivel",""),"horimetro":r.get("horimetro",""),"qtd_entrada":0,"qtd_saida":r.get("quantidade",0),"valor_unitario":r.get("valor_unitario",0),"total":r.get("total",0),"observacao":r.get("observacao","")})
                df_movs=pd.DataFrame(movs).sort_values("data")
                pdf_t=gerar_pdf(df_movs,"TANQUE","COPA ENGENHARIA LTDA","CONTROLE DE ESTOQUE",f"PERÍODO: {per_t}",{"TANQUE":tanq_sel},f"FECHAMENTO FÍSICO DE TANQUE - {tanq_sel}")
                c5.download_button("📄 Baixar PDF do Tanque",data=pdf_t,file_name=f"Tanque_{tanq_sel}_{di_t}.pdf",mime="application/pdf",use_container_width=True)

    with aba3:
        st.markdown("#### Exportar Boletins de Produção")
        df_prod=get_data("producao")
        di_p, df_p = st.columns(2)
        d1=di_p.date_input("De (Produção)",value=date.today().replace(day=1))
        d2=df_p.date_input("Até (Produção)",value=date.today())
        if st.button("📊 Extrair Tabela de Produção"):
            if not df_prod.empty:
                df_prod["data_dt"]=pd.to_datetime(df_prod["data"],errors="coerce").dt.date
                df_pf=df_prod[(df_prod["data_dt"]>=d1)&(df_prod["data_dt"]<=d2)]
                if not df_pf.empty:
                    xl_p=gerar_excel_limpo(df_pf.drop(columns=["data_dt"]),"Producao")
                    st.download_button("📥 Baixar Excel Produção",data=xl_p,file_name=f"Producao_{d1}_a_{d2}.xlsx",mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                else: st.info("Nenhum lançamento no período.")
            else: st.info("Nenhum lançamento no banco de dados.")

# ════════════════════════════════════════════════════════════════════
# 9 · USUÁRIOS E ACESSOS
# ════════════════════════════════════════════════════════════════════
elif menu=="👥 Usuários e Acessos":
    if st.session_state.perfil_logado!="Admin": st.error("⛔ Acesso restrito."); st.stop()
    st.markdown("## 👥 Gestão de Usuários e Acessos")
    st.info("O campo **'Criado Por'** registra automaticamente quem fez cada lançamento.")
    with st.form("f_usr",clear_on_submit=True):
        c1,c2=st.columns(2); nm_u=c1.text_input("Nome Completo"); lg_u=c2.text_input("Login")
        c3,c4=st.columns(2); sn_u=c3.text_input("Senha",type="password"); pf_u=c4.selectbox("Perfil",["Operador","Admin"])
        if st.form_submit_button("💾 Criar Usuário",use_container_width=True):
            if nm_u and lg_u and sn_u:
                ok=insert_data("usuarios",{"nome":nm_u,"login":lg_u,"senha":sn_u,"perfil":pf_u})
                if ok: st.success("✅ Usuário criado!"); st.rerun()
            else: st.error("⚠️ Preencha todos os campos.")
            
    df_u = get_data("usuarios")
    if not df_u.empty:
        st.divider(); st.subheader("Usuários Cadastrados")
        for _, r in df_u.iterrows():
            cc1,cc2 = st.columns([5,1])
            cc1.write(f"**{r.get('nome','')}** ({r.get('login','')}) - Nível: {r.get('perfil','')}")
            if cc2.button("❌", key=f"del_u_{r['id']}"):
                if delete_data("usuarios", r["id"]): st.rerun()
