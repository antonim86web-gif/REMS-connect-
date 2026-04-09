import streamlit as st
import pandas as pd
import hashlib
import calendar
from datetime import datetime, timedelta, timezone

def get_now_it():
    # Ora italiana (UTC+2) senza bisogno di librerie esterne
    return datetime.now(timezone(timedelta(hours=2)))
from groq import Groq
from supabase import create_client # <--- NUOVO
# Inizializzazione variabili di sessione mancanti
for key, val in {
    'cal_month': datetime.now().month,
    'cal_year': datetime.now().year,
    'utente': "Ospite",
    'ruolo': "Nessuno"
}.items():
    if key not in st.session_state:
        st.session_state[key] = val
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

    for riga in dati_clinici:
            # Riga 38 e 39: estraiamo i dati (allineate a 12 spazi dal bordo)
            data = riga[0]
            op   = riga[2]
            nota = riga[3]
            
            # Riga 40: Pulizia (allineata a 12 spazi)
            nota_p = str(nota).encode('latin-1', 'replace').decode('latin-1')
            
            # Riga 48: ECCO QUELLA CHE TI DÀ ERRORE (deve essere allineata alle altre!)
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(40, 10, f"Data: {data}", 0, 0)
            pdf.set_font("Arial", '', 10)
            pdf.multi_cell(0, 10, f"Op: {op} - Nota: {nota_p}", 0, 1)
            pdf.ln(2)
        
    # --- IL TRUCCO INFALLIBILE: Esporta come Byte String ---
    pdf_output = pdf.output() # In fpdf2 questo restituisce bytearray o bytes
    return bytes(pdf_output)  # Lo trasformiamo in bytes puri
        
    



# --- MOTORE DATABASE UNIFICATO ---
def db_run(query, params=None, commit=False):
    try:
        if params is None: params = []
        q = query.upper()

        # --- GESTIONE PAZIENTI (Risolve ValueError 302, 350, 788) ---
        if "FROM PAZIENTI" in q:
            res = supabase.table("pazienti").select("*").order("nome").execute()
            if "ATTIVO" in q or "STATO='ATTIVO'" in q:
                return [[r["id"], r["nome"]] for r in res.data if str(r.get("stato", "")).upper() == "ATTIVO"]
            return [[r["id"], r["nome"]] for r in res.data]

        # --- GESTIONE TERAPIE ---
        elif "FROM TERAPIE" in q:
            p_id = params[0] if params else None
            if p_id:
                res = supabase.table("terapie").select("*").eq("p_id", p_id).execute()
                # Restituisce 6 colonne fisse per non rompere i cicli for
                return [[r.get('id', 0), r.get('farmaco', 'Sconosciuto'), r.get('dose', '-'), 
                         r.get('mat_nuovo', 0), r.get('pom_nuovo', 0), r.get('al_bisogno', 0)] for r in res.data]
            return []

        # --- GESTIONE EVENTI/SMARCO (Risolve ValueError 408) ---
        elif "FROM EVENTI" in q:
            p_id = params[0] if params else None
            qb = supabase.table("eventi").select("*")
            if p_id:
                qb = qb.eq("paziente_id", p_id)
            
            # 1. Caso Somministrazioni (3 colonne)
            if "SOMM" in q:
                qb = qb.ilike("nota", "%Somm:%")
                res = qb.order("id", desc=True).execute()
                return [[r.get('data','-'), r.get('nota','-'), r.get('op','-')] for r in res.data] if res.data else []

            # 2. Caso Diario Rapido (2 colonne)
            elif "SELECT DATA, NOTA" in q:
                res = qb.order("id", desc=True).execute()
                return [[r.get('data','-'), r.get('nota','-')] for r in res.data] if res.data else []

            # 3. Caso Default (5 colonne) - L'unico e ultimo ELSE
            else:
                res = qb.order("id", desc=True).limit(100).execute()
                return [[r.get('data','-'), r.get('ruolo','-'), r.get('op','-'), r.get('nota','-'), r.get('esito','-')] for r in res.data] if res.data else []

        # --- SCRITTURA (COMMIT) ---
        if commit:
            if "INSERT INTO EVENTI" in q:
                pay = {"paziente_id": params[0], "data": params[1], "nota": params[2], "ruolo": params[3], "op": params[4]}
                if len(params) > 5: pay["esito"] = params[5]
                supabase.table("eventi").insert(pay).execute()
            
            elif "INSERT INTO TERAPIE" in q:
                pay = {"p_id": params[0], "farmaco": params[1], "dose": params[2], 
                       "mat_nuovo": int(params[3]), "pom_nuovo": int(params[4]), "al_bisogno": int(params[5])}
                supabase.table("terapie").insert(pay).execute()
                
            elif "DELETE" in q:
                supabase.table("terapie").delete().eq("id", params[0]).execute()
        
        return []
    except Exception as e:
        st.error(f"Errore DB: {e}")
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

# --- SESSIONE E LOGIN (INIZIO MARGINE SINISTRO) ---
if 'user_session' not in st.session_state:
    st.session_state.user_session = None
if 'cal_month' not in st.session_state:
    st.session_state.cal_month = datetime.now().month
if 'cal_year' not in st.session_state:
    st.session_state.cal_year = datetime.now().year

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
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (pid_sel, get_now_it().strftime("%d/%m/%Y %H:%M"), f"🔄 TRASFERIMENTO: Spostato in {dsid} Letto {dl}. Motivo: {mot}", u.get('qualifica', 'Operatore') , firma_op), True)
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
 
    p_lista = db_run("SELECT id, nome FROM pazienti WHERE stato='ATTIVO' ORDER BY nome")
    if p_lista:
        p_sel = st.selectbox("Seleziona Paziente", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_sel][0]
        now = get_italy_time(); oggi = now.strftime("%d/%m/%Y")
        
        if ruolo_corr == "Psichiatra":
            # 1. DEFINIZIONE DEI TAB
            t1, t2, t3, t4, t5 = st.tabs(["📋 DIARIO CLINICO", "💊 TERAPIA", "💉 SOMMINISTRAZIONI", "🩺 ESAME OBIETTIVO", "🤖 ANALISI CLINICA IA"])
            
            with t1:
                st.subheader("Inserimento Nota in Diario Clinico")
                with st.form("form_diario_med"):
                    nota_med = st.text_area("Valutazione clinica...", height=200)
                    if st.form_submit_button("REGISTRA NOTA CLINICA"):
                        if nota_med:
                            db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", 
                                   (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"🩺 [DIARIO] {nota_med}", "Psichiatra", firma_op), True)
                            st.success("Nota registrata!")
                            st.rerun()

            with t2:
                st.subheader("💊 Gestione Terapia Farmacologica")
                terapie_attuali = db_run("SELECT id_u, farmaco, dose, mat_nuovo, pom_nuovo, al_bisogno FROM terapie WHERE p_id=?", (p_id,))
                if terapie_attuali:
                    for t in terapie_attuali:
                        c1, c2 = st.columns([4, 1])
                        c1.info(f"💊 {t[1]} - {t[2]}")
                        if c2.button("🗑️", key=f"del_med_{t[0]}_{t[1].replace(' ', '_')}"):
    db_run("DELETE FROM terapie WHERE id_u=?", (t[0],), True)
    st.rerun()
                
                with st.expander("➕ Prescrivi"):
                    with st.form("n_ter"):
                        f_n = st.text_input("Farmaco")
                        if st.form_submit_button("CONFERMA"):
                            db_run("INSERT INTO terapie (p_id, farmaco) VALUES (?,?)", (p_id, f_n), True)
                            st.rerun()

            with t3:
                st.subheader("💉 Registro Somministrazioni")
                res_smarc = db_run("SELECT data_ora, dettaglio, infermiere FROM somministrazioni WHERE id_paziente=?", (p_id,))
                if res_smarc:
                    df_smarc = pd.DataFrame(res_smarc, columns=["Data/Ora", "Dettaglio", "Infermiere"])
                    st.table(df_smarc)
                else:
                    st.info("Nessun dato.")

            with t4:
                st.subheader("🩺 ESAME OBIETTIVO")
                e_o = st.text_area("Descrizione...")
                if st.button("SALVA E.O."):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", 
                           (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"🧠 [E.O.] {e_o}", "Psichiatra", firma_op), True)
                    st.rerun()

            with t5:
                st.subheader("🤖 Analisi IA")
                st.write("Funzione IA attiva.")

            # --- AREA PDF ---
            st.divider()
            with st.expander("📄 ESPORTAZIONE PDF"):
                tipo_rep = st.radio("Report:", ["Diario Completo", "Solo Terapie"], horizontal=True)
                # Creiamo la variabile dati_pdf SEMPRE, così non dà NameError
                dati_pdf = db_run("SELECT data, op, nota FROM eventi WHERE id=?", (p_id,))
                if dati_pdf:
                    try:
                        pdf_b = genera_pdf_clinico(p_id, dati_pdf, tipo_rep)
                        st.download_button("📥 SCARICA PDF", data=pdf_b, file_name="report.pdf")
                    except Exception as e:
                        st.error(f"Errore PDF: {e}")
# Ora l'elif (riga 538) sarà felice perché il blocco sopra è chiuso ben
        elif ruolo_corr == "Infermiere":
            import calendar
            from datetime import timedelta
            t1, t2, t3, t4 = st.tabs(["💊 KEEP TERAPIA", "💓 PARAMETRI", "📝 CONSEGNE", "📋 BRIEFING IA"])
            
            # --- IDENTIFICAZIONE DINAMICA DAL TUO LOGIN ---
    u = st.session_state.user_session
    nome_reale = f"{u['nome']} {u['cognome']}"
    ruolo_reale = u.get('qualifica', 'Operatore')
    with t1:
        st.subheader("Registrazione Somministrazione Farmaci")
        st.info(f"👤 Operatore: **{nome_reale}** | Turno attivo")
        turno_attivo = st.selectbox("Seleziona Turno Operativo", ["8:13 (Mattina)", "16:20 (Pomeriggio)", "Al bisogno"])
        terapie_keep = db_run("SELECT id_u, farmaco, dose, mat_nuovo, pom_nuovo, al_bisogno FROM terapie WHERE p_id=?", (p_id,))
        for f in terapie_keep:
                    t_id_univoco, nome_f, dose_f = f[0], f[1], f[2]
                    mostra = (turno_attivo == "8:13 (Mattina)" and f[3] == 1) or \
                             (turno_attivo == "16:20 (Pomeriggio)" and f[4] == 1) or \
                             (turno_attivo == "Al bisogno" and f[5] == 1)
                    
                    if mostra:
                        st.markdown(f"### 💊 {nome_f} <small>({dose_f})</small>", unsafe_allow_html=True)
                        mese_corrente = get_now_it().strftime('%m/%Y')
                        
                        # Recupero firme dal DB con filtro su Turno e Farmaco
                        firme = db_run("SELECT data, esito, op FROM eventi WHERE id=? AND nota LIKE ? AND nota LIKE ? AND data LIKE ?", 
                                       (p_id, f"%[{t_id_univoco}]%", f"%({turno_attivo})%", f"%/{mese_corrente}%"))
                        
                        f_map = {int(d[0].split("/")[0]): {"e": d[1], "o": d[2]} for d in firme if d[0]}
                        num_giorni = calendar.monthrange(get_now_it().year, get_now_it().month)[1]
                        
                        # --- CALENDARIO CON FIRMA ---
                        h = "<div style='display: flex; overflow-x: auto; padding: 10px; gap: 6px;'>"
                        for d in range(1, num_giorni + 1):
                            info = f_map.get(d)
                            is_today = "border: 2px solid #2563eb;" if d == get_now_it().day else "border: 1px solid #ddd;"
                            esito_txt, col_t, bg_c, firma_quadratino = ("-", "#888", "white", "")
                            
                            if info:
                                firma_quadratino = info['o']
                                if info['e'] == "A": esito_txt, col_t, bg_c = ("A", "#15803d", "#dcfce7")
                                elif info['e'] == "R": esito_txt, col_t, bg_c = ("R", "#b91c1c", "#fee2e2")
                            
                            h += f"""
                            <div style='min-width: 85px; height: 85px; background: {bg_c}; color: {col_t}; 
                                {is_today} border-radius: 6px; display: flex; flex-direction: column; 
                                align-items: center; justify-content: center; font-size: 0.75rem;'>
                                <div style='font-weight: bold;'>{d}</div>
                                <div style='font-size: 1.2rem; font-weight: bold;'>{esito_txt}</div>
                                <div style='font-size: 0.55rem; color: #333; margin-top: 4px; text-align: center; font-weight: 600;'>{firma_quadratino}</div>
                            </div>"""
                        st.markdown(h + "</div>", unsafe_allow_html=True)
                        
                        with st.popover(f"Smarca {nome_f}"):
                            c1, c2 = st.columns(2)
                            if c1.button("✅ ASSUNTO", key=f"ok_{t_id_univoco}_{turno_attivo}"):
                                nota_f = f"✔️ [{t_id_univoco}] {nome_f} ({turno_attivo})"
                                db_run("INSERT INTO eventi (id, data, nota, ruolo, op, esito) VALUES (?,?,?,?,?,?)", 
                                       (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), nota_f, ruolo_reale, nome_reale, "A"), True)
                                st.rerun()
                            if c2.button("❌ RIFIUTO", key=f"ko_{t_id_univoco}_{turno_attivo}"):
                                nota_f = f"❌ [{t_id_univoco}] RIFIUTO {nome_f} ({turno_attivo})"
                                db_run("INSERT INTO eventi (id, data, nota, ruolo, op, esito) VALUES (?,?,?,?,?,?)", 
                                       (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), nota_f, ruolo_reale, nome_reale, "R"), True)
                                st.rerun()
                        st.divider()
                        with t2:
                            st.subheader("💓 Rilevazione Parametri Vitali")
                            with st.form("form_p_inf"):
                                c1, c2, c3 = st.columns(3)
                                p_v = c1.text_input("PA (Pressione)")
                                f_v = c2.text_input("FC (Frequenza)")
                                s_v = c3.text_input("SatO2")
                                if st.form_submit_button("REGISTRA PARAMETRI"):
                                    nota_p = f"💓 Parametri: PA {p_v}, FC {f_v}, Sat {s_v}"
                                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", 
                                    (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), nota_p, ruolo_reale, nome_reale), True)
                                    st.success("Parametri salvati!")
                                    st.rerun()

                                    
                                    with t3:
                                        st.subheader("📝 Consegne Cliniche")
                                        with st.form("form_c_inf"):
                                            txt_c = st.text_area("Inserisci diario clinico...")
                                            if st.form_submit_button("SALVA NOTA"):
                                                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", 
                                                (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"📝 {txt_c}", ruolo_reale, nome_reale), True)
                                                st.success("Nota registrata!")
                                                st.rerun()
                                                
                                                
                                                with t4:
                                                    st.subheader("📋 Briefing Intelligente (IA)")
                                                    # 1. Recupero delle ultime 20 attività
        b_logs = db_run("SELECT data, op, nota FROM eventi WHERE id=? ORDER BY id_u DESC LIMIT 20", (p_id,))
        if b_logs:
            st.success(f"✅ Recuperate le ultime {len(b_logs)} attività dal diario clinico.")
            if st.button("🤖 GENERA RIASSUNTO TURNO (IA)", type="primary", use_container_width=True):
                        # Prepariamo le note in ordine cronologico
                testo_note = "\n".join([f"[{d}] {o}: {n}" for d, o, n in reversed(b_logs)])
                with st.spinner("L'IA sta analizzando i dati..."):
                            # COSTRUIAMO IL MESSAGGIO UNIFICATO (Evita il TypeError)
                    istruzioni_ia = (
                        "RIASSUNTO BRIEFING TURNO: "
                        "Analizza queste ultime 20 note e crea un sunto professionale per il cambio turno, "
                        "dividendo in: 1. Terapie e Rifiuti, 2. Parametri, 3. Note comportamentali.\n\n"
                        f"DATI:\n{testo_note}"
                    )
                            
                            # USIAMO SOLO I 3 PARAMETRI CHE LA TUA FUNZIONE CONOSCE
                    try:
                                # p_id, il nostro testo speciale, 1 giorno
                        sunto = genera_relazione_ia(p_id, istruzioni_ia, 1)
                                
                        st.info("### 📝 Riassunto IA (Ultime 20 attività)")
                        st.write(sunto)
                        st.divider()
                    except Exception as e:
                        st.error(f"Errore nella generazione: {e}")
                    
                    # Visualizzazione note per sicurezza
                        with st.expander("🔍 Controlla i dati originali (Ultime 20)"):
                            for d, o, n in b_logs:
                                st.markdown(f"**{d}** - *{o}*<br>{n}", unsafe_allow_html=True)
                                st.divider()
                    else:
                        st.warning("⚠️ Nessun dato trovato nel diario eventi.")
            elif ruolo_corr == "Psicologo":
                t1, t2 = st.tabs(["🧠 COLLOQUIO", "📝 TEST"])
                with t1:
                    with st.form("f_psi"):
                        txt = st.text_area("Sintesi Colloquio")
                        if st.form_submit_button("SALVA"): 
                            db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"🧠 {txt}", "Psicologo", firma_op), True)
                            st.rerun()
                            with t2:
                                with st.form("f_test"):
                                    test_n = st.text_input("Nome Test"); test_r = st.text_area("Risultato")
                                    if st.form_submit_button("REGISTRA"): 
                                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"📊 TEST {test_n}: {test_r}", "Psicologo", firma_op), True)
                                        st.rerun()
                                    
        elif ruolo_corr == "Assistente Sociale":
            t1, t2 = st.tabs(["🤝 RETE", "🏠 PROGETTO"])
            with t1:
                with st.form("f_soc"):
                    cont = st.text_input("Contatto"); txt = st.text_area("Esito")
                    if st.form_submit_button("SALVA"): 
                       b_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"🤝 CONTATTO {cont}: {txt}", "Assistente Sociale", firma_op), True)
                       st.rerun()
            with t2:
                with st.form("f_prog"):
                    prog = st.text_area("Aggiornamento Progetto")
                    if st.form_submit_button("SALVA"): 
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"🏠 PROGETTO: {prog}", "Assistente Sociale", firma_op), True)
                        st.rerun()

        elif ruolo_corr == "OPSI":
            with st.form("f_opsi"):
                cond = st.multiselect("Stato:", ["Tranquillo", "Agitato", "Ispezione"]); nota = st.text_input("Note")
                if st.form_submit_button("REGISTRA"): 
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"🛡️ VIGILANZA: {', '.join(cond)} | {nota}", "OPSI", firma_op), True)
                    st.rerun()

        elif ruolo_corr == "OSS":
            with st.form("oss_f"):
                mans = st.multiselect("Mansioni:", ["Igiene", "Cambio", "Pulizia", "Letto"]); txt = st.text_area("Note")
                if st.form_submit_button("REGISTRA"): 
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"🧹 {', '.join(mans)} | {txt}", "OSS", firma_op), True)
                    st.rerun()

        elif ruolo_corr == "Educatore":
            t1, t2 = st.tabs(["💰 CASSA", "📝 CONSEGNA"])
            with t1:
                mov = db_run("SELECT importo, tipo FROM cassa WHERE p_id=?", (p_id,)); saldo = sum(m[0] if m[1]=="ENTRATA" else -m[0] for m in mov)
                st.markdown(f"<div class='cassa-card'>Saldo: <span class='saldo-txt'>{saldo:.2f} €</span></div>", unsafe_allow_html=True)
                with st.form("cs"):
                    tp, im, cau = st.selectbox("Tipo", ["ENTRATA", "USCITA"]), st.number_input("€"), st.text_input("Causale")
                    if st.form_submit_button("REGISTRA"):
                        db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, oggi, cau, im, tp, firma_op), True)
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"💰 {tp}: {im}€ - {cau}", "Educatore", firma_op), True)
                        st.rerun()
            with t2:
                with st.form("edu_cons"):
                    txt_edu = st.text_area("Osservazioni")
                    if st.form_submit_button("SALVA"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"📝 {txt_edu}", "Educatore", firma_op), True)
                        st.rerun()
                        def render_postits(p_id):
                            st.markdown("### 📌 Note Rapide")
                            res = db_run("SELECT data, nota FROM eventi WHERE paziente_id = ?", [p_id])
                            if res:
                                for r in res:
                                    d, n = r[:2] # Prende solo Data e Nota
                                    st.info(f"**{d}**: {n}")

elif nav == "📅 Agenda Dinamica":
    st.markdown("<div class='section-banner'><h2>AGENDA DINAMICA REMS</h2></div>", unsafe_allow_html=True)
    c_nav1, c_nav2, c_nav3 = st.columns([1,2,1])
    with c_nav1: 
        if st.button("⬅️ Mese Precedente"): 
            st.session_state.cal_month -= 1
            if st.session_state.cal_month < 1: st.session_state.cal_month=12; st.session_state.cal_year-=1
            st.rerun()
    with c_nav2: 
        mesi_nomi = ["Gennaio","Febbraio","Marzo","Aprile","Maggio","Giugno","Luglio","Agosto","Settembre","Ottobre","Novembre","Dicembre"]
        st.markdown(f"<h3 style='text-align:center;'>{mesi_nomi[st.session_state.cal_month-1]} {st.session_state.cal_year}</h3>", unsafe_allow_html=True)
    with c_nav3:
        if st.button("Mese Successivo ➡️"):
            st.session_state.cal_month += 1
            if st.session_state.cal_month > 12: st.session_state.cal_month=1; st.session_state.cal_year+=1
            st.rerun()
            
    col_cal, col_ins = st.columns([3, 1])
    with col_cal:
        start_d = f"{st.session_state.cal_year}-{st.session_state.cal_month:02d}-01"
        end_d = f"{st.session_state.cal_year}-{st.session_state.cal_month:02d}-31"
        evs_mese = db_run("""SELECT a.data, p.nome, a.ora, a.tipo_evento, a.mezzo, a.nota, a.accompagnatore FROM appuntamenti a JOIN pazienti p ON a.p_id=p.id WHERE a.data BETWEEN ? AND ? AND a.stato='PROGRAMMATO'""", (start_d, end_d))
        mappa_ev = {}
        for d_ev, p_n, h_ev, t_ev, m_ev, nt_ev, acc_ev in evs_mese:
            try:
                g_int = int(d_ev.split("-")[2])
                if g_int not in mappa_ev: mappa_ev[g_int] = []
                prefix = "🚗" if t_ev == "Uscita Esterna" else "🏠"
                tag_final = f'<div class="event-tag-html">{prefix} {p_n}<span class="tooltip-text"><b>{t_ev}</b><br>⏰ {h_ev}<br>🚗 {m_ev}<br>📝 {nt_ev}</span></div>'
                mappa_ev[g_int].append(tag_final)
            except: pass
        
        cal_html = "<table class='cal-table'><thead><tr>" + "".join([f"<th>{d}</th>" for d in ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]]) + "</tr></thead><tbody>"
        cal_obj = calendar.Calendar(firstweekday=0)
        for week in cal_obj.monthdayscalendar(st.session_state.cal_year, st.session_state.cal_month):
            cal_html += "<tr>"
            for day in week:
                if day == 0: cal_html += "<td style='background:#f8fafc;'></td>"
                else:
                    d_iso = f"{st.session_state.cal_year}-{st.session_state.cal_month:02d}-{day:02d}"
                    cls_today = "today-html" if d_iso == oggi_iso else ""
                    cal_html += f"<td class='{cls_today}'><span class='day-num-html'>{day}</span>{''.join(mappa_ev.get(day, []))}</td>"
            cal_html += "</tr>"
        st.markdown(cal_html + "</tbody></table>", unsafe_allow_html=True)

    with col_ins:
        st.subheader("➕ Nuovo Appuntamento")
        with st.form("add_app_cal"):
            p_l = db_run("SELECT id, nome FROM pazienti WHERE stato='ATTIVO' ORDER BY nome")
            ps_sel = st.multiselect("Paziente/i", [p[1] for p in p_l])
            tipo_e = st.selectbox("Tipo", ["Uscita Esterna", "Appuntamento Interno"])
            dat, ora = st.date_input("Giorno"), st.time_input("Ora")
            mezzo_usato = st.selectbox("Macchina", ["Mitsubishi", "Fiat Qubo", "Nessuno"]) if tipo_e == "Uscita Esterna" else "Nessuno"
            accomp, not_a = st.text_input("Accompagnatore"), st.text_area("Note")
            if st.form_submit_button("REGISTRA"):
                for nome_p in ps_sel:
                    pid = [p[0] for p in p_l if p[1]==nome_p][0]
                    db_run("INSERT INTO appuntamenti (p_id, data, ora, nota, stato, autore, tipo_evento, mezzo, accompagnatore) VALUES (?,?,?,?,'PROGRAMMATO',?,?,?,?)", (pid, str(dat), str(ora)[:5], not_a, firma_op, tipo_e, mezzo_usato, accomp), True)
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (pid, get_now_it().strftime("%d/%m/%Y %H:%M"), f"📅 {tipo_e}: {not_a}", u.get('qualifica', 'Operatore') , firma_op), True)
                st.rerun()
        
        st.divider()
        st.subheader("📋 Lista Scadenze")
        agenda_list = db_run("SELECT a.id_u, a.data, a.ora, p.nome, a.tipo_evento FROM appuntamenti a JOIN pazienti p ON a.p_id = p.id WHERE a.data >= ? AND a.stato='PROGRAMMATO' ORDER BY a.data, a.ora", (oggi_iso,))
        for aid, adt, ahr, apn, atev in agenda_list:
            st.markdown(f"**{adt} {ahr}** - {apn}<br>{atev}", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            if c1.button("FATTO", key=f"done_{aid}"): 
                db_run("UPDATE appuntamenti SET stato='COMPLETATO' WHERE id_u=?", (aid,), True)
                st.rerun()
            if c2.button("ELIMINA", key=f"del_{aid}"):
                db_run("DELETE FROM appuntamenti WHERE id_u=?", (aid,), True)
                st.rerun()
            st.markdown("---")

elif nav == "⚙️ Admin":
    st.markdown("<div class='section-banner'><h2>PANNELLO AMMINISTRAZIONE</h2></div>", unsafe_allow_html=True)
    t_ut, t_paz_att, t_paz_dim, t_diar, t_log = st.tabs(["UTENTI", "PAZIENTI ATTIVI", "ARCHIVIO", "DIARIO EVENTI", "📜 LOG"])
    
    with t_ut:
        st.subheader("Gestione Utenti Registrati")
        utenti_raw = db_run("SELECT user, nome, cognome, qualifica FROM utenti")
        
        if utenti_raw:
            for riga in utenti_raw:
                # Controlliamo che la riga abbia effettivamente i dati prima di assegnarli
                if len(riga) >= 4:
                    us, un, uc, uq = riga[0], riga[1], riga[2], riga[3]
                    
                    c1, c2 = st.columns([0.8, 0.2])
                    c1.write(f"**{un} {uc}** ({uq}) - *@{us}*")
                    
                    # Evitiamo che l'admin si cancelli da solo
                    if us != "admin":
                        if c2.button("🗑️", key=f"del_{us}"):
                            supabase.table("utenti").delete().eq("user", us).execute()
                            st.rerun()
                else:
                    st.warning("Trovata riga utente incompleta.")
        else:
            st.info("Nessun utente trovato nel database.")


    with t_paz_att:
        with st.form("np"):
            np_val = st.text_input("Nuovo Paziente")
            if st.form_submit_button("AGGIUNGI"): 
                db_run("INSERT INTO pazienti (nome, stato) VALUES (?, 'ATTIVO')", (np_val.upper(),), True)
                st.rerun()
        for pid, pn in db_run("FROM PAZIENTI ATTIVO"):
            c1, c2, c3 = st.columns([0.6, 0.2, 0.2])
            c1.write(f"**{pn}**")
            if c2.button("DIMETTI", key=f"dim_{pid}"):
                db_run("UPDATE pazienti SET stato='DIMESSO' WHERE id=?", (pid,), True)
                db_run("DELETE FROM assegnazioni WHERE p_id=?", (pid,), True)
                st.rerun()
            if c3.button("ELIMINA", key=f"dp_{pid}"): 
                db_run("DELETE FROM pazienti WHERE id=?", (pid,), True)
                st.rerun()

    with t_paz_dim:
        for pid, pn in db_run("SELECT id, nome FROM pazienti WHERE stato='DIMESSO' ORDER BY nome"):
            c1, c2 = st.columns([0.8, 0.2])
            c1.write(f"📁 {pn}")
            if c2.button("RIAMMETTI", key=f"re_{pid}"):
                db_run("UPDATE pazienti SET stato='ATTIVO' WHERE id=?", (pid,), True)
                st.rerun()

    with t_diar:
        lista_p = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
        filtro_p = st.selectbox("Filtra per Paziente:", ["*TUTTI*"] + [p[1] for p in lista_p])
        
        # Recuperiamo anche e.id_u per poter eliminare la riga specifica
        query_log = "SELECT e.data, e.ruolo, e.op, e.nota, p.nome, e.id_u FROM eventi e JOIN pazienti p ON e.id = p.id"
        params_log = []
        
        if filtro_p != "*TUTTI*":
            query_log += " WHERE p.nome = ?"
            params_log.append(filtro_p)
            
        tutti_log = db_run(query_log + " ORDER BY e.id_u DESC LIMIT 100", tuple(params_log))
        
        for ldt, lru, lop, lnt, lpnome, lidu in tutti_log:
            c1, c2 = st.columns([0.85, 0.15])
            # Mostriamo il testo dell'evento
            c1.write(f"**[{ldt}]** {lpnome} | {lop} ({lru}): {lnt}")
            
            # Tasto Elimina per l'Admin
            if c2.button("🗑️", key=f"del_adm_{lidu}"):
                db_run("DELETE FROM eventi WHERE id_u=?", (lidu,), True)
                st.rerun()
            st.divider()

    with t_log:
        logs_audit = db_run("SELECT data_ora, utente, azione, dettaglio FROM logs_sistema ORDER BY id_log DESC LIMIT 200")
        if logs_audit:
            st.dataframe(pd.DataFrame(logs_audit, columns=["Data/Ora", "Operatore", "Azione", "Descrizione"]), use_container_width=True)
                                    
        
