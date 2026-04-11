import streamlit as st
import pandas as pd
import hashlib
from datetime import datetime
from zoneinfo import ZoneInfo
from supabase import create_client
from fpdf import FPDF
from groq import Groq

# --- CONFIGURAZIONE E CSS ELITE ---
st.set_page_config(page_title="REMS Connect ELITE PRO v28.9.2", layout="wide", page_icon="🏥")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #c9d1d9; }
    .stSidebar { background-color: #161b22 !important; border-right: 1px solid #30363d; min-width: 320px !important; }
    .software-header { color: #ff4b4b; font-size: 28px; font-weight: bold; text-align: center; padding: 10px; border-bottom: 2px solid #ff4b4b; }
    .user-logged { color: #8b949e; font-size: 14px; text-align: center; padding: 15px 0; border-bottom: 1px solid #30363d; margin-bottom: 20px; }
    .stButton>button { width: 100%; border-radius: 4px; background-color: #21262d; border: 1px solid #30363d; color: #c9d1d9; height: 45px; font-weight: bold; }
    .stButton>button:hover { border-color: #ff4b4b; color: #ff4b4b; background-color: #161b22; }
    .fab { position: fixed; bottom: 30px; right: 30px; background: #ff4b4b; color: white; width: 65px; height: 65px; border-radius: 50%; 
           display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 15px rgba(0,0,0,0.5); z-index: 1000; cursor: pointer; font-size: 26px; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { background-color: #1e2228; border-radius: 5px 5px 0 0; padding: 10px 20px; color: #8b949e; }
    .stTabs [aria-selected="true"] { background-color: #ff4b4b !important; color: white !important; }
    </style>
""", unsafe_allow_html=True)

# --- MOTORE DATABASE ---
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
def get_now_it(): return datetime.now(ZoneInfo("Europe/Rome"))

# --- SESSION STATE ---
for k, v in [("autenticato", False), ("menu", "Monitoraggio"), ("u", None), ("r", None)]:
    if k not in st.session_state: st.session_state[k] = v

if not st.session_state.autenticato:
    st.markdown("<h2 style='text-align:center'>🔓 ACCESSO CRITICO REMS</h2>", unsafe_allow_html=True)
    with st.form("login"):
        u, p = st.text_input("User"), st.text_input("Password", type="password")
        if st.form_submit_button("AUTENTICA"):
            hp = hashlib.sha256(p.encode()).hexdigest()
            res = supabase.table("utenti").select("*").eq("username", u).execute()
            if res.data and res.data[0]['password'] == hp:
                st.session_state.update({"autenticato": True, "u": u, "r": res.data[0]['ruolo']})
                st.rerun()
    st.stop()

# --- SIDEBAR GERARCHICA RICHIESTA ---
with st.sidebar:
    st.markdown('<div class="software-header">REMS-CONNECT</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="user-logged">👤 {st.session_state.u} <br> [{st.session_state.r}]</div>', unsafe_allow_html=True)
    
    if st.button("📈 MONITORAGGIO"): st.session_state.menu = "Monitoraggio"
    if st.button("👥 EQUIPE"): st.session_state.menu = "Equipe"
    if st.button("📅 AGENDA DINAMICA"): st.session_state.menu = "Agenda"
    if st.button("🗺️ MAPPA POSTI LETTO"): st.session_state.menu = "Mappa"
    if st.button("⚙️ ADMIN"): st.session_state.menu = "Admin"
    
    st.divider()
    p_data = supabase.table("pazienti").select("*").order("nome").execute().data
    df_p = pd.DataFrame(p_data)
    p_sel = st.selectbox("🎯 PAZIENTE IN CARICO:", df_p['nome'].tolist())
    p_id = df_p[df_p['nome'] == p_sel]['id'].values[0]

    st.markdown("<br>"*5, unsafe_allow_html=True)
    if st.button("🔓 LOGOUT"):
        st.session_state.clear(); st.rerun()

# --- MODULI INTEGRALI ---
menu = st.session_state.menu

if menu == "Monitoraggio":
    st.title(f"📈 Monitoraggio Clinico: {p_sel}")
    c1, c2, c3 = st.columns(3)
    # Post-it Rapidi (Recupero logica originale)
    postits = supabase.table("postits").select("*").eq("p_id", p_id).execute().data
    for p in postits: st.warning(f"📌 {p['nota']}")
    
    # Diario Rapido
    eventi = supabase.table("eventi").select("*").eq("id", p_id).order("id_u", desc=True).limit(50).execute().data
    for ev in eventi:
        with st.expander(f"{ev['data']} - {ev['op']} ({ev['ruolo']})"):
            st.write(ev['nota'])

elif menu == "Equipe":
    st.title(f"👥 Equipe Multidisciplinare: {p_sel}")
    t_med, t_inf, t_psi, t_soc, t_edu, t_oss = st.tabs(["Medico", "Infermiere", "Psicologo", "Sociale", "Educatore", "OSS"])
    
    with t_med: # Funzioni Medico & Psichiatra
        st.subheader("Diario Clinico e Terapie")
        n_clinica = st.text_area("Nota Clinica / Diagnostica:")
        if st.button("Registra Atto Medico"):
    supabase.table("eventi").insert({
        "id": int(p_id),  # <--- AGGIUNGI int() QUI
        "data": get_now_it().strftime("%d/%m/%Y %H:%M"), 
        "nota": f"[MED] {n_clinica}", 
        "op": st.session_state.u, 
        "ruolo": "Medico"
    }).execute()
    st.rerun()

    with t_inf: # Funzioni Infermieristiche
        st.subheader("Smarcatura e Somministrazione")
        terapie = supabase.table("terapie").select("*").eq("p_id", p_id).execute().data
        for t in terapie:
            c1, c2 = st.columns([0.8, 0.2])
            c1.write(f"💊 **{t['farmaco']}** | {t['dose']}")
            if c2.button("✅ SMARCA", key=f"t_{t['id_u']}"):
                supabase.table("eventi").insert({"id":p_id, "data":get_now_it().strftime("%d/%m/%Y %H:%M"), "nota":f"SOMMINISTRATO: {t['farmaco']}", "op":st.session_state.u, "ruolo":"Infermiere", "esito":"S"}).execute()
                st.rerun()

    with t_soc: # Funzioni Assistente Sociale (Peculio/Cassa)
        st.subheader("Gestione Peculio e Progetto Sociale")
        cassa = supabase.table("cassa").select("*").eq("p_id", p_id).execute().data
        st.table(pd.DataFrame(cassa))
        if st.button("Nuovo Movimento Cassa"):
             # Qui andrebbe il form inserimento cassa
             pass

elif menu == "Agenda":
    st.title("📅 Agenda Dinamica e Scadenze")
    # Logica appuntamenti magistrati / visite
    app = supabase.table("appuntamenti").select("*").eq("p_id", p_id).execute().data
    st.dataframe(pd.DataFrame(app))

elif menu == "Mappa":
    st.title("🗺️ Layout Posti Letto")
    # Logica stanze riga 1400+ originale
    mappa = supabase.table("stanze").select("*").execute().data
    st.write(mappa)

elif menu == "Admin":
    if st.session_state.r == "Admin":
        st.title("⚙️ Amministrazione Sistema")
        # Logica cancellazione specifica riga 1700
        logs = supabase.table("eventi").select("*, pazienti(nome)").order("id_u", desc=True).limit(100).execute().data
        for ldt, lru, lop, lnt, lpnome, lidu in [(x['data'], x['ruolo'], x['op'], x['nota'], x['pazienti']['nome'], x['id_u']) for x in logs]:
            c1, c2 = st.columns([0.85, 0.15])
            c1.write(f"**[{ldt}]** {lpnome} | {lop}: {lnt}")
            if c2.button("🗑️", key=f"del_{lidu}"):
                supabase.table("eventi").delete().eq("id_u", lidu).execute()
                st.rerun()
    else: st.error("Accesso negato.")

# TASTO FLOTTANTE
st.markdown('<div class="fab">📝</div>', unsafe_allow_html=True)
