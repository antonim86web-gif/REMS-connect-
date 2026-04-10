import streamlit as st
import pandas as pd
import hashlib
import calendar
from datetime import datetime, timedelta, timezone
from groq import Groq
from supabase import create_client # <--- NUOVO
from fpdf import FPDF
import io

# --- CONNESSIONE CLOUD (Mettile subito sotto gli import) ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

def genera_pdf_clinico(p_nome, dati_clinici, tipo_rep="Report"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Intestazione
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "REMS-CONNECT - REPORT CLINICO", ln=True, align='C')
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, f"Paziente: {p_nome}", ln=True)
    pdf.ln(10)

    for data, op, nota in dati_clinici:
        # Pulizia totale caratteri
        nota_p = str(nota).encode('latin-1', 'replace').decode('latin-1')
        op_p = str(op).encode('latin-1', 'replace').decode('latin-1')
        
        pdf.set_font("Arial", 'B', 10)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(0, 7, f"Data: {data} | Op: {op_p}", ln=True, fill=True)
        pdf.set_font("Arial", size=10)
        pdf.multi_cell(0, 7, nota_p)
        pdf.ln(4)
        
    # --- IL TRUCCO INFALLIBILE: Esporta come Byte String ---
    pdf_output = pdf.output() # In fpdf2 questo restituisce bytearray o bytes
    return bytes(pdf_output)  # Lo trasformiamo in bytes puri
        
    



# --- FUNZIONE AGGIORNAMENTO DB (INTEGRALE) ---
def db_run(query, params=None, commit=False):
    try:
        if "SELECT" in query.upper():
            # Gestione Tabella Utenti
            if "FROM utenti" in query:
                res = supabase.table("utenti").select("user, nome, cognome, qualifica").execute()
                if res.data:
                    return [(r.get('user','?'), r.get('nome','?'), r.get('cognome','?'), r.get('qualifica','?')) for r in res.data]
                return []
            
            # Gestione Tabella Pazienti (esempio)
            if "FROM pazienti" in query:
                res = supabase.table("pazienti").select("*").execute()
                return res.data if res.data else []

        return []
    except Exception as e:
        # Questo chiude il try e impedisce il crash alla riga 66
        return []

# --- FUNZIONE ORARIO ITALIA ---
def get_italy_time():
    return datetime.now(timezone.utc) + timedelta(hours=2)

    def scrivi_log(azione, dettagli):
    # Log disattivato per compatibilità Cloud
        pass
        user_log = st.session_state.user_session['uid'] if st.session_state.user_session else "SISTEMA"
        data_log = get_italy_time().strftime("%Y-%m-%d %H:%M:%S")
    # Log disattivato per compatibilità Cloud
pass


# --- FUNZIONE GENERATORE RELAZIONE IA ---
def genera_relazione_ia(p_id, p_sel, g_rel):
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Sei un esperto clinico REMS. Genera relazioni formali."},
                {"role": "user", "content": f"ID: {p_id}, Paziente: {p_sel}, Note: {g_rel}"}
            ],
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Errore Groq: {str(e)}"
        

        

# --- CONFIGURAZIONE INTERFACCIA ELITE PRO v28.9.2 ---
st.set_page_config(page_title="REMS Connect ELITE PRO v28.9.2", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #1e3a8a !important; }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    .sidebar-title { color: #ffffff !important; font-size: 1.8rem !important; font-weight: 800 !important; text-align: center; margin-bottom: 1rem; padding-top: 10px; border-bottom: 2px solid #ffffff33; }
    .user-logged { color: #00ff00 !important; font-weight: 900; font-size: 1.1rem; text-transform: uppercase; margin-bottom: 20px; text-align: center; }
    .sidebar-footer { color: #ffffff !important; font-size: 0.8rem; text-align: center; margin-top: 20px; opacity: 0.8; }
    .section-banner { background-color: #1e3a8a; color: white !important; padding: 25px; border-radius: 12px; margin-bottom: 30px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.3); border: solidolid #ffffff22; }
    .stButton>button[kind="secondary"] { background-color: #22c55e !important; color: white !important; border: none !important; width: 100%; font-weight: 700; }
    
    .ai-box { background: #f8fafc; border: 2px solid #a855f7; border-radius: 15px; padding: 25px; margin-top: 10px; box-shadow: 0 4px 12px rgba(168, 85, 247, 0.2); }
    .alert-sidebar { background: #ef4444; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: 800; margin: 10px 5px; border: 2px solid white; animation: pulse 2s infinite; }
    @keyframes pulse { 0% {transform: scale(1);} 50% {transform: scale(1.02);} 100% {transform: scale(1);} }
    .cal-table { width:100%; border-collapse: collapse; table-layout: fixed; background: white; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    .cal-table th { background: #f1f5f9; padding: 10px; color: #1e3a8a; font-weight: 800; border: 1px solid #e2e8f0; font-size: 0.85rem; }
    .cal-table td { border: 1px solid #e2e8f0; vertical-align: top; height: 150px; padding: 5px; position: relative; overflow: visible !important; }
    .day-num-html { font-weight: 900; color: #64748b; font-size: 0.8rem; margin-bottom: 4px; display: block; }
    
    .event-tag-html { font-size: 0.65rem; background: #dbeafe; color: #1e40af; padding: 2px 4px; border-radius: 4px; margin-bottom: 3px; border-left: 3px solid #2563eb; line-height: 1.1; position: relative; cursor: help; }
    .event-tag-html .tooltip-text { visibility: hidden; width: 220px; background-color: #1e3a8a; color: #fff; text-align: left; border-radius: 8px; padding: 12px; position: absolute; z-index: 9999 !important; bottom: 125%; left: 0%; opacity: 0; transition: opacity 0.3s; box-shadow: 0 8px 20px rgba(0,0,0,0.4); font-size: 0.75rem; line-height: 1.4; white-space: normal; border: 1px solid #ffffff44; pointer-events: none; }
    .event-tag-html:hover .tooltip-text { visibility: visible; opacity: 1; }
    
    .today-html { background-color: #f0fdf4 !important; border: 2px solid #22c55e !important; }
    .postit { padding: 15px; border-radius: 8px; margin-bottom: 12px; border-left: 10px solid; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); color: #1e293b; background-color: #ffffff; }
    .postit-header { font-weight: 800; font-size: 0.85rem; text-transform: uppercase; margin-bottom: 5px; display: flex; justify-content: space-between; }
    
    .role-psichiatra { background-color: #fef2f2; border-color: #dc2626; } 
    .role-infermiere { background-color: #eff6ff; border-color: #2563eb; } 
    .role-educatore { background-color: #ecfdf5; border-color: #059669; }  
    .role-oss { background-color: #f8fafc; border-color: #64748b; }
    .role-psicologo { background-color: #faf5ff; border-color: #a855f7; }
    .role-sociale { background-color: #fff7ed; border-color: #f97316; }
    .role-opsi { background-color: #f1f5f9; border-color: #0f172a; border-style: dashed; }
    .scroll-giorni { display: flex; overflow-x: auto; gap: 4px; padding: 8px; background: #fdfdfd; }
    .quadratino { 
        min-width: 38px; height: 50px; border-radius: 4px; border: 1px solid #eee; 
        display: flex; flex-direction: column; align-items: center; justify-content: center; flex-shrink: 0;
    }
    .q-oggi { border: 2px solid #1e3a8a !important; background: #fffde7; }
    .q-num { font-size: 7px; color: #999; }
    .q-esito { font-size: 11px; font-weight: 900; }
    .q-op { font-size: 6px; color: #444; }
    .therapy-container { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 15px; margin-bottom: 15px; border-left: 8px solid #1e3a8a; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }
    .cassa-card { background: #f0fdf4; border: 1px solid #bbf7d0; padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 20px; }
    .saldo-txt { font-size: 2.2rem; font-weight: 900; color: #166534; }
    
    .map-reparto { background: #f1f5f9; padding: 15px; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 20px; }
    .reparto-title { text-align: center; color: #1e3a8a; font-weight: 900; text-transform: uppercase; margin-bottom: 15px; border-bottom: 2px solid #1e3a8a33; }
    .stanza-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 10px; }
    .stanza-tile { background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px; border-left: 6px solid #94a3b8; }
    .stanza-header { font-weight: 800; font-size: 0.8rem; color: #475569; margin-bottom: 5px; border-bottom: 1px solid #eee; }
    .letto-slot { font-size: 0.8rem; color: #1e293b; padding: 2px 0; }
    .stanza-occupata { border-left-color: #22c55e; background-color: #f0fdf4; }
    .stanza-piena { border-left-color: #2563eb; background-color: #eff6ff; }
    .stanza-isolamento { border-left-color: #ef4444; background-color: #fef2f2; border-width: 2px; }
</style>
""", unsafe_allow_html=True)

# --- DATABASE ENGINE ---
DB_NAME = "rems_final_v12.db"
def hash_pw(p): return hashlib.sha256(str.encode(p)).hexdigest()

def db_run(query, params=(), commit=False):
    try:
        # 1. LOGIN UTENTI
        if "FROM utenti" in query:
            user_input = params[0]
            pwd_input = params[1]
            res = supabase.table("utenti").select("*").eq("user", user_input).eq("pwd", pwd_input).execute()
            if res.data:
                # Restituiamo il formato che il tuo codice si aspetta: [[nome, cognome, qualifica]]
                return [[res.data[0]['nome'], res.data[0]['cognome'], res.data[0]['qualifica']]]
            return []

        # 2. SELEZIONE PAZIENTI
        elif "FROM pazienti" in query:
            res = supabase.table("pazienti").select("id, nome").eq("stato", "ATTIVO").execute()
            return [[r['id'], r['nome']] for r in res.data]

        # 3. INSERIMENTO NUOVO PAZIENTE
        elif "INSERT INTO pazienti" in query:
            supabase.table("pazienti").insert({"nome": params[0], "stato": "ATTIVO"}).execute()
            return []

        # 4. LOGICA PER EVENTI/DIARIO
        elif "FROM eventi" in query:
            # Qui filtriamo per l'ID del paziente (params[0])
            res = supabase.table("eventi").select("*").eq("id", params[0]).order("id", descending=True).execute()
            return [[r['data'], r['ruolo'], r['op'], r['nota']] for r in res.data]

    except Exception as e:
        st.error(f"Errore Cloud Supabase: {e}")
        return []
    return []


def render_postits(reparto_filtro):
    # Nota: ci devono essere 4 spazi prima di st.write
    st.write(f"Visualizzazione post-it per: {reparto_filtro}")
    pass


# --- SESSIONE E LOGIN (INIZIO MARGINE SINISTRO) ---
if 'user_session' not in st.session_state:
    st.session_state.user_session = None

if not st.session_state.user_session:
    st.markdown("<div class='section-banner'><h2>🏥 REMS CONNECT - ACCESSO PRO</h2></div>", unsafe_allow_html=True)
    c_l, c_r = st.columns(2)
    
    with c_l:
        st.subheader("Login")
        with st.form("login_main"):
            u_i = st.text_input("Username").lower().strip()
            p_i = st.text_input("Password", type="password")
            if st.form_submit_button("ACCEDI"):
                res = supabase.table("utenti").select("*").eq("user", u_i).execute()
                if res.data and res.data[0]['pwd'] == p_i:
                    st.session_state.user_session = res.data[0]
                    st.rerun()
                else:
                    st.error("Credenziali errate")
    
    with c_r:
        st.subheader("Registrazione")
        with st.form("reg_main"):
            ru = st.text_input("Scegli Username").lower().strip()
            rp = st.text_input("Scegli Password", type="password")
            rn = st.text_input("Nome")
            rc = st.text_input("Cognome")
            rq = st.selectbox("Qualifica", ["Psichiatra", "Infermiere", "OSS", "Educatore", "Psicologo", "Assistente Sociale", "Opsi", "Coordinatore"])
            if st.form_submit_button("REGISTRA NUOVO UTENTE"):
                if ru and rp and rn and rc:
                    nuovo = {"user": ru, "pwd": rp, "nome": rn, "cognome": rc, "qualifica": rq}
                    try:
                        supabase.table("utenti").insert(nuovo).execute()
                        st.success("Registrato! Prova il login a sinistra.")
                    except Exception as e:
                        st.error(f"Errore: {e}")
                else:
                    st.warning("Compila tutti i campi.")
    st.stop()

# --- SE SIAMO QUI, L'UTENTE È LOGGATO ---
u = st.session_state.user_session

    
# --- SIDEBAR ---
with st.sidebar:
    # Calcoliamo prima le scadenze (se hai la funzione db_run pronta)
    try:
        scadenze_query = db_run("SELECT COUNT(*) FROM scadenze WHERE data = CURRENT_DATE")
        conta_oggi = scadenze_query[0][0] if scadenze_query else 0
    except:
        conta_oggi = 0

    st.markdown(f"<div class='sidebar-title'>REMS Connect</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='user-logged'>👤 {u['nome']} {u['cognome']}</div>", unsafe_allow_html=True)
    
    # Il tuo avviso scadenze
    st.sidebar.markdown(f"<div class='alert-sidebar'>⚠️ {conta_oggi} SCADENZE OGGI</div>", unsafe_allow_html=True)
    
    # Il tuo menu completo
    opts = ["📊 Monitoraggio", "👥 Modulo Equipe", "📅 Agenda Dinamica", "🗺️ Mappa Posti Letto"]
    
    # ATTENZIONE: Qui usiamo 'qualifica' perché è quello che salviamo nel database
    if u.get('qualifica') == "Coordinatore" or u.get('user') == "admin":
        opts.append("⚙️ Admin")
        
    nav = st.sidebar.radio("NAVIGAZIONE", opts)
    
    if st.sidebar.button("LOGOUT"):
        try: scrivi_log("LOGOUT", "Uscita dal sistema")
        except: pass
        st.session_state.user_session = None
        st.rerun()
    
    # Il tuo Footer Elite
    st.sidebar.markdown(f"<br><br><br><div class='sidebar-footer'><b>Antony</b><br>Webmaster<br>ver. 28.9 Elite</div>", unsafe_allow_html=True)
# --- LOGICA NAVIGAZIONE ---
if nav == "📍 Mappa Posti":
    st.markdown("<div class='section-banner'><h2>TABELLONE VISIVO POSTI LETTO</h2></div>", unsafe_allow_html=True)

    st.markdown("<div class='section-banner'><h2>TABELLONE VISIVO POSTI LETTO</h2></div>", unsafe_allow_html=True)
    stanze_db = db_run("SELECT id, reparto, tipo FROM stanze ORDER BY id")
    paz_db = db_run("SELECT p.id, p.nome, a.stanza_id, a.letto FROM pazienti p LEFT JOIN assegnazioni a ON p.id = a.p_id WHERE p.stato='ATTIVO'")
    mappa = {s[0]: {'rep': s[1], 'tipo': s[2], 'letti': {1: None, 2: None}} for s in stanze_db}
    for pid, pnome, sid, letto in paz_db:
        if sid in mappa: mappa[sid]['letti'][letto] = {'id': pid, 'nome': pnome}
    
    c_a, c_b = st.columns(2)
    for r_code, col_obj in [("A", c_a), ("B", c_b)]:
        with col_obj:
            st.markdown(f"<div class='map-reparto'><div class='reparto-title'>Reparto {r_code}</div><div class='stanza-grid'>", unsafe_allow_html=True)
            for s_id, s_info in {k:v for k,v in mappa.items() if v['rep']==r_code}.items():
                p_count = len([v for v in s_info['letti'].values() if v])
                cls = "stanza-isolamento" if s_info['tipo']=="ISOLAMENTO" and p_count>0 else ("stanza-piena" if p_count==2 else ("stanza-occupata" if p_count==1 else ""))
                st.markdown(f"<div class='stanza-tile {cls}'><div class='stanza-header'>{s_id} <small>{s_info['tipo']}</small></div>", unsafe_allow_html=True)
                for l in [1, 2]:
                    p = s_info['letti'][l]
                    st.markdown(f"<div class='letto-slot'>L{l}: <b>{p['nome'] if p else 'Libero'}</b></div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("</div></div>", unsafe_allow_html=True)

    with st.expander("Sposta Paziente"):
        p_list = db_run("SELECT id, nome FROM pazienti WHERE stato='ATTIVO' ORDER BY nome")
        sel_p = st.selectbox("Paziente", [p[1] for p in p_list], index=None)
        if sel_p:
            pid_sel = [p[0] for p in p_list if p[1]==sel_p][0]
            posti_liberi = [f"{sid}-L{l}" for sid, si in mappa.items() for l, po in si['letti'].items() if not po]
            dest = st.selectbox("Destinazione", posti_liberi)
            mot = st.text_input("Motivo Trasferimento")
            if st.button("ESEGUI TRASFERIMENTO") and mot:
                dsid, dl = dest.split("-L")
                db_run("DELETE FROM assegnazioni WHERE p_id=?", (pid_sel,), True)
                db_run("INSERT INTO assegnazioni (p_id, stanza_id, letto, data_ass) VALUES (?,?,?,?)", (pid_sel, dsid, int(dl), get_now_it().strftime("%Y-%m-%d")), True)
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (pid_sel, get_now_it().strftime("%d/%m/%Y %H:%M"), f"🔄 TRASFERIMENTO: Spostato in {dsid} Letto {dl}. Motivo: {mot}", u['ruolo'], firma_op), True)
                st.rerun()

elif nav == "📊 Monitoraggio":
    st.markdown("<div class='section-banner'><h2>DIARIO CLINICO GENERALE</h2></div>", unsafe_allow_html=True)
    p_lista = db_run("SELECT id, nome FROM pazienti WHERE stato='ATTIVO' ORDER BY nome")

    # --- INCOLLA QUI IL MOTORE DI RICERCA ---
    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        f_data = st.text_input("📅 Filtra per Data (es: 2026-04)", placeholder="GG/MM/AAAA")
    with c2:
        f_op = st.text_input("👤 Filtra Operatore/Ruolo", placeholder="Es: Rossi o Infermiere")
    st.markdown("---")

    for pid, nome in p_lista:
        with st.expander(f"📁 SCHEDA: {nome}"):
            
            # --- QUERY FILTRATA (Collega i box di ricerca ai dati) ---
            query = "SELECT data, ruolo, op, nota FROM eventi WHERE id=?"
            params = [pid]
            
            if f_data:
                query += " AND data LIKE ?"
                params.append(f"%{f_data}%")
            if f_op:
                query += " AND (op LIKE ? OR ruolo LIKE ?)"
                params.append(f"%{f_op}%")
                params.append(f"%{f_op}%")
            
            # Eseguiamo la ricerca con i filtri applicati
            eventi = db_run(query + " ORDER BY id_u DESC", tuple(params))
            
            # --- VISUALIZZAZIONE ---
            col1, col2 = st.columns([4, 1])
            
            with col2:
                # Usiamo gli stessi eventi filtrati anche per il PDF
                if eventi:
                    # Prepariamo i dati per il PDF (servono 3 colonne: data, op, nota)
                    eventi_pdf = [(e[0], e[2], e[3]) for e in eventi]
                    pdf_data = genera_pdf_clinico(nome, eventi_pdf)
                    st.download_button(label="📄 PDF", data=pdf_data, file_name=f"diario_{nome}.pdf", mime="application/pdf", key=f"pdf_{pid}")

            with col1:
                if eventi:
                    for e in eventi:
                        st.markdown(f"**{e[0]}** - *{e[1]} ({e[2]})*")
                        st.write(e[3])
                        st.divider()
                else:
                    st.info("Nessuna nota trovata con questi filtri.")

elif nav == "👥 Modulo Equipe":
    st.markdown("<div class='section-banner'><h2>MODULO OPERATIVO EQUIPE</h2></div>", unsafe_allow_html=True)
    ruolo_corr = u.get('qualifica', u.get('ruolo', 'OSS'))

       # Usiamo .get per evitare il crash se 'ruolo' non esiste
    if u.get('qualifica') == "Admin" or u.get('user') == "admin":
        ruolo_corr = st.selectbox("Simula Figura:", ["Psichiatra", "Infermiere", "Educatore", "OSS", "Psicologo", "Assistente Sociale", "OPSI"])
 
    p_lista = 
