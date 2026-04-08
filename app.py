import streamlit as st
import pandas as pd
import hashlib
import calendar
from datetime import datetime, timedelta, timezone
from groq import Groq
from supabase import create_client
from fpdf import FPDF
import io

# --- CONNESSIONE CLOUD ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- MOTORE GROQ IA ---
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# --- FUNZIONE GENERAZIONE PDF CLINICO ---
def genera_pdf_clinico(p_nome, dati_clinici):
    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_page()
    
    # Intestazione
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f"Report Clinico: {p_nome}", ln=True, align='C')
    pdf.ln(5)
    
    for riga in dati_clinici:
        # Estrazione dati
        data = str(riga[0]) if len(riga) > 0 else ""
        op = str(riga[2]) if len(riga) > 2 else ""
        nota = str(riga[3]) if len(riga) > 3 else ""
        esito = str(riga[4]) if len(riga) > 4 and riga[4] else ""
        
        # --- PULIZIA TESTO PER PDF (Anti-Crash) ---
        # Sostituiamo i simboli come 💊 o caratteri speciali che Arial non legge
        def pulisci(testo):
            return testo.encode('latin-1', 'replace').decode('latin-1')

        data = pulisci(data)
        op = pulisci(op)
        nota = pulisci(nota)
        esito = pulisci(esito)
        # ------------------------------------------

        # Riga Grigia Intestazione Nota
        pdf.set_font("Arial", 'B', 10)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(0, 7, f"Data: {data} | Op: {op}", ln=True, fill=True)
        
        # Testo della nota
        pdf.set_font("Arial", '', 11)
        testo_finale = nota
        if esito:
            testo_finale += f" [ESITO: {esito}]"
            
        pdf.multi_cell(0, 7, testo_finale)
        pdf.ln(2)
        
    # Restituisce i byte del PDF pronti per il download
    pdf_output = pdf.output(dest='S')
    
    if isinstance(pdf_output, str):
        return pdf_output.encode('latin-1')
    return bytes(pdf_output)

# --- AGGIORNAMENTO MOTORE DATABASE (Sostituisci questa parte nel Blocco 1) ---
def db_run(query, params=None, commit=False):
    try:
        if params is None: params = []
        q = query.upper()

        # 1. GESTIONE UTENTI
        if "FROM UTENTI" in q:
            res = supabase.table("utenti").select("*").eq("user", params[0]).execute()
            return res.data if res.data else []

        # 2. GESTIONE PAZIENTI
        elif "FROM PAZIENTI" in q:
            stato = "ATTIVO" if "ATTIVO" in q else "DIMESSO"
            res = supabase.table("pazienti").select("*").eq("stato", stato).order("nome").execute()
            return [[r["id"], r["nome"]] for r in res.data] if res.data else []

        # 3. GESTIONE EVENTI (MONITORAGGIO E DIARIO)
        elif "FROM EVENTI" in q:
            p_id = params[0]
            query_base = supabase.table("eventi").select("*").eq("paziente_id", p_id)
            
            if len(params) > 1 and params[1]:
                term = params[1]
                if term == "SOLO_TERAPIA":
                    query_base = query_base.or_("nota.ilike.%💊%,nota.ilike.%✔️%,nota.ilike.%❌%,esito.neq.None")
                else:
                    query_base = query_base.or_(f"nota.ilike.%{term}%,esito.ilike.%{term}%")
            
            res = query_base.order("id_u", desc=True).limit(100).execute()
            return [[r['data'], r['ruolo'], r['op'], r['nota'], r.get('esito','-')] for r in res.data] if res.data else []

        # 4. GESTIONE TERAPIE
        elif "FROM TERAPIE" in q:
            p_id = params[0]
            res = supabase.table("terapie").select("*").eq("p_id", p_id).execute()
            return [[r['id_t'], r['farmaco'], r['dose'], r['not_somm'], r['pax_nuovo'], r['al_bisogno']] for r in res.data] if res.data else []

        # 5. AZIONI DI SCRITTURA
        if commit:
            if "INSERT INTO EVENTI" in q:
                payload = {"paziente_id": params[0], "data": params[1], "nota": params[2], "ruolo": params[3], "op": params[4]}
                if len(params) > 5: payload["esito"] = params[5]
                supabase.table("eventi").insert(payload).execute()
            
            elif "INSERT INTO TERAPIE" in q:
                payload = {"p_id": params[0], "farmaco": params[1], "dose": params[2], "not_somm": int(params[3]), "pax_nuovo": int(params[4]), "al_bisogno": int(params[5])}
                supabase.table("terapie").insert(payload).execute()
            
            elif "DELETE FROM TERAPIE" in q:
                supabase.table("terapie").delete().eq("id_t", params[0]).execute()

        return []

    except Exception as e:
        st.error(f"Errore DB: {e}")
        return [
            # Esegue una ricerca filtrata sulla tabella eventi
    query = supabase.table("eventi").select("*").eq("id", p_id)
            
            # Se ci sono altri parametri (filtro terapia o testo)
            if len(params) > 1:
                filtro = params[1]
                if filtro == "SOLO_TERAPIA":
                    query = query.or_("nota.ilike.%💊%,nota.ilike.%✔️%,nota.ilike.%❌%,esito.neq.None")
                else:
                    query = query.ilike("nota", f"%{filtro}%")
            
            res = query.order("id_u", ascending=False).execute()
            return [[r['data'], r['ruolo'], r['op'], r['nota'], r.get('esito', '-')] for r in res.data] if res.data else []    
        return []
    except Exception as e:
        st.error(f"Errore DB: {e}")
        return []

# --- FUNZIONI ORARIO ---
def get_now_it():
    return datetime.now(timezone.utc) + timedelta(hours=1)

def get_italy_time():
    return get_now_it()

# --- GENERATORE RELAZIONE IA ---
def genera_relazione_ia(p_id, prompt_text, mock_val=None):
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Sei un esperto clinico REMS. Genera relazioni formali e sintesi precise."},
                {"role": "user", "content": prompt_text}
            ],
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Errore Groq: {str(e)}"

# --- CONFIGURAZIONE UI ELITE ---
st.set_page_config(page_title="REMS Connect ELITE PRO v28.9.2", layout="wide", page_icon="🏥")

# [Righe 180-200 circa: Inizio CSS e Stili]
st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #1e3a8a !important; }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    .sidebar-title { color: #ffffff !important; font-size: 1.8rem !important; font-weight: 800 !important; text-align: center; margin-bottom: 1rem; padding-top: 10px; border-bottom: 2px solid #ffffff33; }
    .user-logged { color: #00ff00 !important; font-weight: 900; font-size: 1.1rem; text-transform: uppercase; margin-bottom: 20px; text-align: center; }
    .section-banner { background-color: #1e3a8a; color: white !important; padding: 25px; border-radius: 12px; margin-bottom: 30px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.3); }
    .ai-box { background: #f8fafc; border: 2px solid #a855f7; border-radius: 15px; padding: 25px; margin-top: 10px; }
</style>
""", unsafe_allow_html=True)

# --- SESSIONE E LOGIN ---
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
            ru = st.text_input("Nuovo Username").lower().strip()
            rp = st.text_input("Nuova Password", type="password")
            rn = st.text_input("Nome")
            rc = st.text_input("Cognome")
            rq = st.selectbox("Qualifica", ["Psichiatra", "Infermiere", "OSS", "Educatore", "Psicologo", "Assistente Sociale", "Opsi", "Coordinatore"])
            if st.form_submit_button("REGISTRA UTENTE"):
                if ru and rp and rn and rc:
                    nuovo = {"user": ru, "pwd": rp, "nome": rn, "cognome": rc, "qualifica": rq}
                    try:
                        supabase.table("utenti").insert(nuovo).execute()
                        st.success("Registrato con successo!")
                    except Exception as e:
                        st.error(f"Errore: {e}")
                else:
                    st.warning("Compila tutti i campi.")
    st.stop()

# --- UTENTE LOGGATO ---
u = st.session_state.user_session
firma_op = f"{u['nome']} {u['cognome']}"

# --- SIDEBAR ---
with st.sidebar:
    st.markdown(f"<div class='sidebar-title'>REMS Connect</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='user-logged'>👤 {firma_op}</div>", unsafe_allow_html=True)
    
    opts = ["📊 Monitoraggio", "👥 Modulo Equipe", "📅 Agenda Dinamica", "🗺️ Mappa Posti Letto"]
    if u.get('qualifica') in ["Coordinatore", "Admin"] or u.get('user') == "admin":
        opts.append("⚙️ Admin")
        
    nav = st.sidebar.radio("NAVIGAZIONE", opts)
    
    if st.sidebar.button("LOGOUT"):
        st.session_state.user_session = None
        st.rerun()
    
    st.sidebar.markdown(f"<br><br><div class='sidebar-footer'><b>Antony</b><br>Webmaster<br>ver. 28.9 Elite</div>", unsafe_allow_html=True)

# --- LOGICA NAVIGAZIONE ---
if nav == "👥 Modulo Equipe":
    st.markdown("<div class='section-banner'><h2>MODULO OPERATIVO EQUIPE</h2></div>", unsafe_allow_html=True)
    ruolo_corr = u.get('qualifica', 'OSS')

    # Simulazione ruolo per Admin
    if u.get('qualifica') in ["Coordinatore", "Admin"] or u.get('user') == "admin":
        ruolo_corr = st.selectbox("Simula Figura:", ["Psichiatra", "Infermiere", "Educatore", "OSS", "Psicologo", "Assistente Sociale", "OPSI"])
 
    p_lista = db_run("SELECT id, nome FROM pazienti")
    if p_lista:
        p_sel = st.selectbox("Seleziona Paziente", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_sel][0]
        
        if ruolo_corr == "Psichiatra":
            t1, t2, t3, t4 = st.tabs(["📋 DIARIO CLINICO", "💊 TERAPIA", "🩺 ESAME OBIETTIVO", "🤖 ANALISI IA"])
            
            with t1:
                st.subheader("Inserimento Nota Clinica")
                with st.form("form_diario_med"):
                    nota_med = st.text_area("Valutazione, colloqui, variazioni...", height=200)
                    if st.form_submit_button("REGISTRA NOTA"):
                        if nota_med:
                            db_run("INSERT INTO eventi", (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"🩺 [DIARIO] {nota_med}", "Psichiatra", firma_op), True)
                            st.success("Nota registrata!")
                            st.rerun()

            with t2:
                st.subheader("💊 Gestione Terapia Farmacologica")
                terapie_attuali = db_run("SELECT * FROM terapie", (p_id,))
                if terapie_attuali:
                    for t in terapie_attuali:
                        c1, c2 = st.columns([4, 1])
                        c1.info(f"💊 {t[1]} - {t[2]} (M:{'✅' if t[3] else '❌'} | P:{'✅' if t[4] else '❌'} | B:{'✅' if t[5] else '❌'})")
                        if c2.button("🗑️", key=f"del_med_{t[0]}"):
                            db_run("DELETE FROM terapie", (t[0],), True)
                            st.rerun()
                
                with st.expander("➕ Prescrivi Nuovo Farmaco"):
                    with st.form("nuova_terapia_med"):
                        f_nome = st.text_input("Nome Farmaco")
                        f_dose = st.text_input("Dosaggio")
                        col1, col2, col3 = st.columns(3)
                        m_n, p_n, a_b = col1.checkbox("Mattina"), col2.checkbox("Pomeriggio"), col3.checkbox("Al bisogno")
                        if st.form_submit_button("CONFERMA PRESCRIZIONE"):
                            if f_nome:
                                db_run("INSERT INTO terapie", (p_id, f_nome, f_dose, 1 if m_n else 0, 1 if p_n else 0, 1 if a_b else 0), True)
                                st.rerun()

            with t3:
                st.subheader("🩺 Esame Obiettivo e Parametri")
                ultimi_p = db_run("SELECT data, nota FROM eventi WHERE id=? AND nota LIKE '💓 Parametri:%' ORDER BY id DESC", (p_id,))
                
                if ultimi_p:
                    # Modifica questa riga aggiungendo gli underscore per i valori extra
                    for d, ruolo, op, n, esito in ultimi_p[:5]: 
                        st.write(f"**{d}**: {n}")
                
                with st.form("esame_ob_med"):
                    e_o = st.text_area("Descrizione esame obiettivo e stato mentale...")
                    if st.form_submit_button("SALVA ESAME OBIETTIVO"):
                        db_run("INSERT INTO eventi", (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"🧠 [E.O.] {e_o}", "Psichiatra", firma_op), True)
                        st.success("Esame salvato!")
                        st.rerun()

            with t4:
                st.subheader("🤖 Analisi Clinica IA (Briefing Medico)")
                b_logs = db_run("SELECT data, op, nota FROM eventi WHERE id=? ORDER BY id_u DESC", (p_id,))
                if b_logs:
                    if st.button("🤖 GENERA RELAZIONE CLINICA AGGIORNATA", type="primary"):
                        testo_note = "\n".join([f"[{d}] {o}: {n}" for d, _, o, n, _ in reversed(b_logs[:20])])
                        with st.spinner("L'IA sta analizzando il caso..."):
                            prompt = f"Agisci come Psichiatra. Analizza queste note e genera una sintesi clinica professionale: {testo_note}"
                            relazione = genera_relazione_ia(p_id, prompt) 
                            st.markdown(f"<div class='ai-box'>{relazione}</div>", unsafe_allow_html=True)
                else:
                    st.warning("Dati insufficienti per l'analisi.")

        elif ruolo_corr == "Infermiere":
            t_inf1, t_inf2, t_inf3, t_inf4 = st.tabs(["💊 KEEP TERAPIA", "💓 PARAMETRI", "📝 CONSEGNE", "📋 BRIEFING IA"])
            
            with t_inf1:
                st.subheader("Registrazione Somministrazione Farmaci")
                st.info(f"👤 Operatore: **{firma_op}**")
                
                turno_attivo = st.selectbox("Seleziona Turno", ["8:13 (Mattina)", "16:20 (Pomeriggio)", "Al bisogno"])
                terapie_keep = db_run("SELECT * FROM terapie", (p_id,))
                
                for f in terapie_keep:
                    t_id_univoco, nome_f, dose_f = f[0], f[1], f[2]
                    # Logica di visualizzazione basata sul turno
                    mostra = (turno_attivo == "8:13 (Mattina)" and f[3] == 1) or \
                             (turno_attivo == "16:20 (Pomeriggio)" and f[4] == 1) or \
                             (turno_attivo == "Al bisogno" and f[5] == 1)
                    
                    if mostra:
                        st.markdown(f"#### 💊 {nome_f} ({dose_f})")
                        mese_corrente = get_now_it().strftime('%m/%Y')
                        
                        # Recupero firme dal DB
                        firme = db_run("FROM EVENTI", (p_id,))
                        # Filtriamo per farmaco e turno specifico nella nota
                        f_map = {}
                        for d_f in firme:
                            if f"[{t_id_univoco}]" in d_f[3] and f"({turno_attivo})" in d_f[3] and mese_corrente in d_f[0]:
                                try:
                                    giorno = int(d_f[0].split("/")[0])
                                    f_map[giorno] = {"e": d_f[4], "o": d_f[2]}
                                except: pass

                        num_giorni = calendar.monthrange(get_now_it().year, get_now_it().month)[1]
                        
                        # --- CALENDARIO ORIZZONTALE ---
                        h = "<div style='display: flex; overflow-x: auto; padding: 10px; gap: 6px;'>"
                        for d in range(1, num_giorni + 1):
                            info = f_map.get(d)
                            is_today = "border: 2px solid #2563eb;" if d == get_now_it().day else "border: 1px solid #ddd;"
                            esito_txt, col_t, bg_c, f_quad = ("-", "#888", "white", "")
                            
                            if info:
                                f_quad = info['o']
                                if info['e'] == "A": esito_txt, col_t, bg_c = ("A", "#15803d", "#dcfce7")
                                elif info['e'] == "R": esito_txt, col_t, bg_c = ("R", "#b91c1c", "#fee2e2")
                            
                            h += f"""
                            <div style='min-width: 80px; height: 80px; background: {bg_c}; color: {col_t}; {is_today} 
                                 border-radius: 6px; display: flex; flex-direction: column; align-items: center; justify-content: center;'>
                                <div style='font-weight: bold; font-size: 0.7rem;'>{d}</div>
                                <div style='font-size: 1.1rem; font-weight: bold;'>{esito_txt}</div>
                                <div style='font-size: 0.5rem; color: #333; font-weight: 600;'>{f_quad}</div>
                            </div>"""
                        st.markdown(h + "</div>", unsafe_allow_html=True)
                        
                        with st.popover(f"Smarca {nome_f}"):
                            c1, c2 = st.columns(2)
                            if c1.button("✅ ASSUNTO", key=f"ok_{t_id_univoco}_{d}"):
                                nota_f = f"✔️ [{t_id_univoco}] {nome_f} ({turno_attivo})"
                                db_run("INSERT INTO eventi", (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), nota_f, "Infermiere", firma_op, "A"), True)
                                st.rerun()
                            if c2.button("❌ RIFIUTO", key=f"ko_{t_id_univoco}_{d}"):
                                nota_f = f"❌ [{t_id_univoco}] RIFIUTO {nome_f} ({turno_attivo})"
                                db_run("INSERT INTO eventi", (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), nota_f, "Infermiere", firma_op, "R"), True)
                                st.rerun()
                        st.divider()

            with t_inf2:
                st.subheader("💓 Parametri Vitali")
                with st.form("form_p_inf"):
                    c1, c2, c3 = st.columns(3)
                    p_v = c1.text_input("PA (Pressione)")
                    f_v = c2.text_input("FC (Frequenza)")
                    s_v = c3.text_input("SatO2")
                    if st.form_submit_button("REGISTRA PARAMETRI"):
                        nota_p = f"💓 Parametri: PA {p_v}, FC {f_v}, Sat {s_v}"
                        db_run("INSERT INTO eventi", (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), nota_p, "Infermiere", firma_op), True)
                        st.success("Parametri salvati!")
                        st.rerun()

            with t_inf3:
                st.subheader("📝 Consegne Infermieristiche")
                with st.form("cons_inf"):
                    txt_c = st.text_area("Note di turno, eventi, osservazioni...")
                    if st.form_submit_button("SALVA CONSEGNA"):
                        db_run("INSERT INTO eventi", (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"📝 {txt_c}", "Infermiere", firma_op), True)
                        st.rerun()
                        with t_inf4:
                            st.subheader("📋 Briefing Infermieristico IA")
                # Recupera gli eventi delle ultime 24 ore per il briefing
                b_logs = db_run("SELECT data, op, nota FROM eventi WHERE id=? ORDER BY id_u DESC", (p_id,))
                if b_logs:
                    if st.button("🤖 GENERA BRIEFING TURNO", type="secondary"):
                        testo_note = "\n".join([f"[{d}] {o}: {n}" for d, o, n in reversed(b_logs[:15])])
                        with st.spinner("Analisi in corso..."):
                            prompt = f"Agisci come Infermiere Coordinatore. Riassumi i punti salienti del turno per il passaggio consegne: {testo_note}"
                            briefing = genera_relazione_ia(p_id, prompt)
                            st.markdown(f"<div class='ai-box'>{briefing}</div>", unsafe_allow_html=True)

        elif ruolo_corr in ["Educatore", "OSS", "Psicologo", "Assistente Sociale"]:
            st.subheader(f"Diario {ruolo_corr}")
            with st.form("form_equipe"):
                nota_eq = st.text_area("Inserisci osservazione o attività...")
                if st.form_submit_button("REGISTRA"):
                    if nota_eq:
                        db_run("INSERT INTO eventi", (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"📝 {nota_eq}", ruolo_corr, firma_op), True)
                        st.success("Nota registrata!")
                        st.rerun()

#Ecco il blocco completo e millimetrico per la sezione Monitoraggio. Ho corretto la gestione dei dati per evitare quell'errore NoneType e ho aggiunto la funzione di stampa che scarica solo i dati filtrati.


elif nav == "📊 Monitoraggio":
    st.markdown("<div class='section-banner'><h2>📊 MONITORAGGIO CLINICO GENERALE</h2></div>", unsafe_allow_html=True)
    
    # 1. Recupero lista pazienti (Usa il tuo sistema standard)
    p_lista = db_run("FROM PAZIENTI", ["ATTIVO"])
    
    # 2. Interfaccia Filtri
    c1, c2 = st.columns([1, 2])
    with c1:
        solo_t = st.toggle("💊 Solo Terapie / Obiettivo", key="togg_mon")
    with c2:
        cerca_p = st.text_input("Cerca nel diario:", placeholder="Es: Clozapina, Parametri...", key="inp_mon")

    st.divider()

    # 3. Ciclo unico pazienti
    if p_lista:
        for p in p_lista:
            # Estrazione sicura ID e Nome dai tuoi dati [id, nome]
            pid = p[0]
            nome = p[1]
            
            with st.expander(f"📁 SCHEDA: {nome}"):
                
                # CHIAMATA AL TUO MOTORE AGGIORNATO (FROM EVENTI_LIBERO)
                if solo_t:
                    # Cerca pillole, esiti e parole chiave obiettivo
                    eventi = db_run("FROM EVENTI_LIBERO", [pid, "SOLO_TERAPIA"])
                elif cerca_p:
                    # Cerca per parola chiave libera
                    eventi = db_run("FROM EVENTI_LIBERO", [pid, cerca_p])
                else:
                    # Carica tutto il diario del paziente
                    eventi = db_run("FROM EVENTI_LIBERO", [pid])

                if eventi:
                    st.caption(f"🔍 Record trovati: {len(eventi)}")
                    
                    # Preparazione testo per Report/Stampa
                    testo_report = f"DIARIO CLINICO: {nome}\n" + "="*30 + "\n\n"
                    
                    for e in eventi:
                        # Mapping dei dati restituiti dalla tua db_run:
                        # e[0]=data, e[1]=ruolo, e[2]=op, e[3]=nota, e[4]=esito
                        d_e, r_e, o_e, n_e, s_e = e[0], e[1], e[2], e[3], e[4]
                        
                        testo_report += f"[{d_e}] {o_e} ({r_e})\nNOTA: {n_e} | ESITO: {s_e}\n" + "-"*20 + "\n"
                        
                        # --- LOGICA VISUALE (BOX COLORATI) ---
                        nota_str = str(n_e).lower()
                        is_obj = any(x in nota_str for x in ['obiettivo', 'esame', 'parametri'])
                        
                        if s_e in ['A', 'R'] or any(sym in str(n_e) for sym in ['💊', '✔️', '❌']):
                            # Verde per Somministrato (A), Rosso per Rifiutato (R)
                            bg = "#dcfce7" if s_e == 'A' else "#fee2e2"
                            st.markdown(f"""
                            <div style='background-color:{bg}; padding:10px; border-radius:8px; border-left:6px solid #1e3a8a; color:black; margin-bottom:8px;'>
                                <b>{d_e}</b> | Esito: <b>{s_e if s_e else '-'}</b><br>
                                <small>{r_e} - {o_e}</small><br>{n_e}
                            </div>
                            """, unsafe_allow_html=True)
                        elif is_obj:
                            # Box Azzurro per Esame Obiettivo
                            st.markdown(f"""
                            <div style='background-color:#e0f2fe; padding:10px; border-radius:8px; border-left:6px solid #0369a1; color:black; margin-bottom:8px;'>
                                <b>{d_e} (ESAME OBIETTIVO)</b><br>{n_e}
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            # Diario Standard
                            st.write(f"📝 **{d_e}** ({o_e}): {n_e}")
                    
                    # Tasto per scaricare solo i dati visualizzati (Filtrati)
                    st.divider()
                    st.download_button(
                        label=f"📥 Scarica Report {nome}",
                        data=testo_report,
                        file_name=f"Diario_{nome}.txt",
                        key=f"dl_{pid}"
                    )
                else:
                    st.info("Nessun dato trovato per i filtri selezionati.")
    else:
        st.warning("Nessun paziente attivo trovato.")
                

elif nav == "📅 Agenda Dinamica":
    st.markdown("<div class='section-banner'><h2>AGENDA REPARTO</h2></div>", unsafe_allow_html=True)
    st.info("Funzionalità in fase di sincronizzazione con il database Cloud.")
    st.calendar = st.date_input("Seleziona Giorno")
    # Logica placeholder per appuntamenti futuri o scadenze legali

elif nav == "🗺️ Mappa Posti Letto":
    st.markdown("<div class='section-banner'><h2>PLANIMETRIA REMS</h2></div>", unsafe_allow_html=True)
    # Esempio di griglia posti letto
    cols = st.columns(4)
    p_lista = db_run("SELECT id, nome FROM pazienti")
    for i, p in enumerate(p_lista[:16]):
        with cols[i % 4]:
            st.markdown(f"""
            <div style='background: white; border: 2px solid #1e3a8a; border-radius: 10px; padding: 15px; text-align: center; margin-bottom: 10px;'>
                <div style='font-size: 2rem;'>🛌</div>
                <div style='font-weight: bold; color: #1e3a8a;'>Posto {i+1}</div>
                <div style='font-size: 0.9rem;'>{p[1]}</div>
            </div>
            """, unsafe_allow_html=True)

elif nav == "⚙️ Admin":
    st.markdown("<div class='section-banner'><h2>PANNELLO DI CONTROLLO</h2></div>", unsafe_allow_html=True)
    t_dim, t_diar = st.tabs(["🚪 RIAMMISSIONE DIMESSI", "📜 LOG DI SISTEMA"])
    
    with t_dim:
        st.subheader("Pazienti Dimessi (Archivio)")
        dimessi = supabase.table("pazienti").select("*").eq("stato", "DIMESSO").execute()
        if dimessi.data:
            for p in dimessi.data:
                c1, c2 = st.columns([0.8, 0.2])
                c1.write(f"📁 {p['nome']}")
                if c2.button("RIAMMETTI", key=f"re_{p['id']}"):
                    db_run("UPDATE pazienti SET stato='ATTIVO' WHERE id=?", (p['id'],), True)
                    st.rerun()
        else:
            st.write("Nessun paziente in archivio.")

    with t_diar:
        st.subheader("Revisione Eventi Totale")
        query_log = "SELECT e.data, e.ruolo, e.op, e.nota, p.nome FROM eventi e JOIN pazienti p ON e.id = p.id ORDER BY e.id_u DESC LIMIT 100"
        # Nota: La db_run va adattata per JOIN complessi su Supabase se necessario
        res_logs = supabase.table("eventi").select("*, pazienti(nome)").order("id_u", descending=True).limit(100).execute()
        if res_logs.data:
            df_logs = pd.DataFrame(res_logs.data)
            st.table(df_logs[['data', 'op', 'nota']])
