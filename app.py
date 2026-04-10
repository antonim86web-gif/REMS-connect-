import re
import hashlib
import calendar
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st
from fpdf import FPDF
from groq import Groq
from supabase import create_client

# --- CONFIGURAZIONE INTERFACCIA ---
st.set_page_config(
    page_title="REMS-Connect Cloud Pro",
    layout="wide",
    page_icon="🏥",
)

# --- INIZIALIZZAZIONE SESSIONE ---
for key, default in (
    ("autenticato", False), ("ruolo", None), ("user", None), 
    ("user_session", None), ("cal_month", None), ("cal_year", None)
):
    if key not in st.session_state:
        st.session_state[key] = default

# --- CONNESSIONE SUPABASE ---
try:
    supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except Exception as e:
    st.error(f"Errore connessione Supabase: {e}")

# --- AI & TIME UTILS ---
try:
    _groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    _groq_client = None

def get_now_it():
    return datetime.now(ZoneInfo("Europe/Rome"))

def db_run(query: str, params: tuple = ()):
    """
    Esegue operazioni su Supabase simulando il comportamento SQL.
    Gestisce la conversione da JSON a Tuple per non rompere l'interfaccia esistente.
    """
    q = query.upper()
    try:
        # 1. LOGICA PAZIENTI
        if "FROM PAZIENTI" in q:
            res = supabase.table("pazienti").select("*").order("nome").execute()
            return [(d['id'], d['nome'], d['reparto']) for d in res.data]

        # 2. LOGICA EVENTI (DIARIO/NOTE) - Fix Critico
        if "FROM EVENTI" in q:
            # Se c'è un JOIN con pazienti (per il Log Amministratore)
            if "JOIN PAZIENTI" in q:
                res = supabase.table("eventi").select("*, pazienti(nome)").order("id_u", desc=True).execute()
                return [(d['data'], d['ruolo'], d['op'], d['nota'], d['pazienti']['nome'], d['id_u']) for d in res.data]
            
            # Query standard per paziente singolo
            st_query = supabase.table("eventi").select("*")
            if params:
                st_query = st_query.eq("id", params[0])
            res = st_query.order("id_u", desc=True).execute()
            return [(d['data'], d['op'], d['nota'], d['ruolo'], d['esito'], d['id_u']) for d in res.data]

        # 3. LOGICA TERAPIE
        if "FROM TERAPIE" in q:
            res = supabase.table("terapie").select("*").eq("p_id", params[0]).execute()
            return [(d['id_t'], d['farmaco'], d['dosaggio'], d['orari']) for d in res.data]

        # 4. LOGICA DELETE (Per Amministratore)
        if "DELETE FROM EVENTI" in q:
            supabase.table("eventi").delete().eq("id_u", params[0]).execute()
            return True

    except Exception as e:
        st.error(f"Errore db_run: {e}")
        return []
    return []



def genera_pdf_clinico(p_nome, dati_clinici, tipo_rep="Report"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, f"REMS-CONNECT - {tipo_rep.upper()}", ln=True, align="C")
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, f"Paziente: {p_nome}", ln=True)
    pdf.ln(10)
    
    for riga in dati_clinici:
        # Supporta sia formati tupla che dizionario per evitare crash
        dt = riga[0] if isinstance(riga, tuple) else riga.get('data')
        op = riga[1] if isinstance(riga, tuple) else riga.get('op')
        nt = riga[2] if isinstance(riga, tuple) else riga.get('nota')
        
        pdf.set_font("Arial", "B", 10)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(0, 7, f"Data: {dt} | Op: {op}", ln=True, fill=True)
        pdf.set_font("Arial", size=10)
        pdf.multi_cell(0, 7, str(nt).encode("latin-1", "replace").decode("latin-1"))
        pdf.ln(4)
    return pdf.output(dest='S').encode('latin-1')

def genera_relazione_ia(p_id, testo_utente):
    if not _groq_client: return "IA non configurata."
    try:
        # Recupero ultime note per dare contesto all'IA
        ultime_note = db_run("SELECT * FROM eventi", (p_id,))[:10]
        context = "\n".join([f"[{n[0]}] {n[2]}" for n in ultime_note])
        
        completion = _groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Sei un esperto clinico in ambito REMS. Genera relazioni formali."},
                {"role": "user", "content": f"Basandoti su questo diario:\n{context}\n\nNota aggiuntiva: {testo_utente}"}
            ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Errore IA: {e}"




if not st.session_state.autenticato:
    st.markdown("<h1 style='text-align: center;'>🏥 REMS-CONNECT PRO</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        with st.form("login_form"):
            user_in = st.text_input("User ID")
            pass_in = st.text_input("Password", type="password")
            if st.form_submit_button("ACCEDI AL SISTEMA"):
                h_pass = hashlib.sha256(pass_in.encode()).hexdigest()
                # Query diretta su Supabase
                res_u = supabase.table("utenti").select("*").eq("username", user_in).execute()
                
                if res_u.data and res_u.data[0]['password'] == h_pass:
                    st.session_state.autenticato = True
                    st.session_state.user = res_u.data[0]['username']
                    st.session_state.ruolo = res_u.data[0]['ruolo']
                    st.rerun()
                else:
                    st.error("Credenziali non valide o accesso negato.")
    st.stop()

# --- LOGOUT E SIDEBAR ---
if st.sidebar.button("🔓 LOGOUT"):
    st.session_state.autenticato = False
    st.rerun()


# Caricamento Pazienti con filtro reparto
pazienti_raw = db_run("SELECT * FROM pazienti")
df_paz = pd.DataFrame(pazienti_raw, columns=['id', 'nome', 'reparto'])

reparti = ["TUTTI"] + sorted(df_paz['reparto'].unique().tolist())
rep_sel = st.sidebar.selectbox("Filtro Reparto", reparti)

if rep_sel != "TUTTI":
    df_paz = df_paz[df_paz['reparto'] == rep_sel]

st.sidebar.divider()
p_nome_sel = st.sidebar.selectbox("👤 SELEZIONA PAZIENTE", df_paz['nome'].tolist())
p_id = df_paz[df_paz['nome'] == p_nome_sel]['id'].values[0]

# --- TABS PRINCIPALI ---
t_diario, t_terapia, t_ia, t_admin = st.tabs([
    "📂 DIARIO CLINICO", "💊 TERAPIA & SMARCATURA", "🤖 ANALISI IA", "⚙️ GESTIONE"
])

with t_diario:
    st.header(f"Diario Clinico: {p_nome_sel}")
    
    with st.expander("➕ AGGIUNGI NUOVA NOTA / EVENTO", expanded=True):
        col_ruolo, col_data = st.columns(2)
        col_ruolo.info(f"Operatore: {st.session_state.user} ({st.session_state.ruolo})")
        nuova_nota = st.text_area("Descrizione evento/osservazione:")
        
        if st.button("REGISTRA NOTA"):
            if nuova_nota:
                data_obj = {
                    "id": p_id,
                    "data": get_now_it().strftime("%d/%m/%Y %H:%M"),
                    "nota": nuova_nota,
                    "op": st.session_state.user,
                    "ruolo": st.session_state.ruolo,
                    "esito": "P" if st.session_state.ruolo == "Medico" else "N"
                }
                supabase.table("eventi").insert(data_obj).execute()
                st.success("Nota registrata correttamente.")
                st.rerun()

    st.divider()
    # Visualizzazione Diario
    eventi = db_run("SELECT * FROM eventi", (p_id,))
    for e in eventi:
        with st.container():
            st.markdown(f"**[{e[0]}] {e[1]} ({e[3]})**")
            st.write(e[2])
            st.divider()


with t_terapia:
    st.header("💊 Piano Terapeutico e Somministrazioni")
    
    terapie_paz = db_run("SELECT * FROM terapie", (p_id,))
    
    if not terapie_paz:
        st.warning("Nessuna terapia attiva per questo paziente.")
    else:
        for t in terapie_paz:
            with st.form(f"smarca_{t[0]}"):
                c1, c2 = st.columns([0.7, 0.3])
                c1.write(f"**FARMACO:** {t[1]} | **DOSAGGIO:** {t[2]}")
                c1.caption(f"Orari previsti: {t[3]}")
                
                smarca = col2.form_submit_button("✅ SMARCA SOMMINISTRAZIONE")
                if smarca:
                    log_terapia = {
                        "id": p_id,
                        "data": get_now_it().strftime("%d/%m/%Y %H:%M"),
                        "nota": f"SOMMINISTRATO: {t[1]} ({t[2]})",
                        "op": st.session_state.user,
                        "ruolo": st.session_state.ruolo,
                        "esito": "S"
                    }
                    supabase.table("eventi").insert(log_terapia).execute()
                    st.success(f"Somministrazione di {t[1]} registrata.")
                    st.rerun()

# --- GESTIONE PDF (In fondo al file) ---
with t_admin:
    if st.button("📥 GENERA REPORT CLINICO PDF"):
        dati_p = db_run("SELECT * FROM eventi", (p_id,))
        pdf_bytes = genera_pdf_clinico(p_nome_sel, dati_p)
        st.download_button(
            label="Scarica PDF",
            data=pdf_bytes,
            file_name=f"Report_{p_nome_sel}_{get_now_it().strftime('%Y%m%d')}.pdf",
            mime="application/pdf"
        )


