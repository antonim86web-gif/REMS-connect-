import streamlit as st
import pandas as pd
from supabase import create_client, Client
from groq import Groq
from datetime import datetime
import pytz  # Gestione fuso orario italiano
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas # Pronto per la stampa report

# --- 1. CONFIGURAZIONE PAGINA & STILE "ELITE" ---
st.set_page_config(page_title="REMS-Connect Elite", layout="wide", page_icon="🛡️")

def local_css():
    st.markdown("""
        <style>
        .main { background-color: #f4f7f9; }
        .login-box { 
            max-width: 450px; margin: auto; padding: 40px; 
            background: white; border-radius: 20px; 
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            border: 1px solid #e0e6ed;
        }
        .stButton>button { border-radius: 8px; height: 3.2em; font-weight: 600; transition: 0.3s; }
        .stButton>button:hover { background-color: #007bff; color: white; border-color: #007bff; }
        /* Stile card per le note */
        .note-card {
            padding: 15px; border-radius: 10px; margin-bottom: 10px;
            border-left: 5px solid #333; background: white;
            box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
        }
        </style>
    """, unsafe_allow_html=True)

local_css()

# --- 2. GESTIONE TEMPO E CONNESSIONI ---
def get_now():
    """Ritorna l'orario italiano esatto (gestione automatica legale/solare)"""
    return datetime.now(pytz.timezone('Europe/Rome'))

# Credenziali Supabase e Groq (da inserire nei Secrets di Streamlit)
URL_SB = st.secrets["SUPABASE_URL"]
KEY_SB = st.secrets["SUPABASE_KEY"]
KEY_GROQ = st.secrets["GROQ_API_KEY"]

supabase: Client = create_client(URL_SB, KEY_SB)
client_groq = Groq(api_key=KEY_GROQ)

# --- 3. LOGICA DI SESSIONE E AUTENTICAZIONE ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_data = None
def login_user(username, password):
    # Verifica credenziali
    res = supabase.table("utenti").select("*").eq("username", username).eq("password", password).execute()
    if res.data:
        # Recupero i dati del primo utente trovato
        user = res.data[0]
        
        # CONTROLLO ROBUSTO: Cerchiamo 'ruolo' o 'Ruolo'
        ruolo_effettivo = user.get('ruolo') or user.get('Ruolo') or "Staff"
        
        st.session_state.logged_in = True
        st.session_state.user_data = user
        st.session_state.user_data['ruolo'] = ruolo_effettivo # Lo forziamo per i blocchi success
        
        # REGISTRAZIONE NEI LOG
        try:
            supabase.table("logs").insert({
                "utente": username,
                "azione": "LOGIN_SUCCESS",
                "timestamp": get_now().isoformat(),
                "ruolo": ruolo_effettivo
            }).execute()
        except:
            pass # Evita crash se la tabella logs ha problemi
            
        return True
    return False


# --- 4. INTERFACCIA DI ACCESSO (LOGIN / REGISTRAZIONE) ---
if not st.session_state.logged_in:
    st.markdown("<br><br>", unsafe_allow_html=True)
    with st.container():
        st.markdown("<div class='login-box'>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; color: #1e3a8a;'>🛡️ REMS-Connect Elite</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: gray;'>Sistema Gestionale Clinico Peritale</p>", unsafe_allow_html=True)
        
        tab_log, tab_reg, tab_rec = st.tabs(["🔐 ACCEDI", "✍️ REGISTRATI", "🔄 RECUPERO"])

        with tab_log:
            u = st.text_input("Username", placeholder="Inserisci il tuo username")
            p = st.text_input("Password", type="password", placeholder="••••••••")
            if st.button("ENTRA NEL SISTEMA"):
                if login_user(u, p):
                    st.success("Accesso autorizzato. Caricamento...")
                    st.rerun()
                else:
                    st.error("Credenziali errate o utente non attivo.")

        with tab_reg:
            st.subheader("Richiesta Accreditamento")
            new_u = st.text_input("Username scelto")
            new_r = st.selectbox("Ruolo Professionale", ["Psichiatra", "Infermiere", "Psicologo", "Educatore", "Assistente Sociale", "OSS", "OPSI"])
            new_p = st.text_input("Password (min. 8 caratteri)", type="password")
            conf_p = st.text_input("Conferma Password", type="password")
            
            if st.button("INVIA RICHIESTA AD ADMIN"):
                if new_p == conf_p and len(new_p) >= 8:
                    # Inserimento in tabella 'utenti_richieste' per approvazione
                    supabase.table("utenti_richieste").insert({
                        "username": new_u, "password": new_p, 
                        "ruolo": new_r, "richiesto_il": get_now().isoformat()
                    }).execute()
                    st.info("Richiesta inviata. L'Admin deve approvare il tuo account prima del login.")
                else:
                    st.error("Verifica che le password coincidano e siano lunghe almeno 8 caratteri.")

        with tab_rec:
            st.subheader("Supporto Accesso")
            st.write("Per il reset delle credenziali, contatta l'Amministratore di sistema o inserisci il tuo username qui sotto per inviare una segnalazione.")
            u_rec = st.text_input("Username da resettare")
            if st.button("INVIA SEGNALAZIONE"):
                st.success("Richiesta di reset inoltrata all'Admin.")

        st.markdown("</div>", unsafe_allow_html=True)
    st.stop() # Blocco di sicurezza: se non sei loggato, il codice finisce qui.

# =========================================================
# 1. GESTIONE ACCESSO (LOGIN)
# =========================================================
if not st.session_state.get('logged_in', False):
    st.markdown('<div class="login-box">', unsafe_allow_html=True)
    st.image("https://img.icons8.com/fluency/96/shield.png", width=80)
    st.title("REMS-Connect Elite")
    u = st.text_input("Username", key="login_user")
    p = st.text_input("Password", type="password", key="login_pass")
    
    if st.button("ACCEDI AL SISTEMA", use_container_width=True):
        res = supabase.table("utenti").select("*").eq("username", u).eq("password", p).execute()
        if res.data:
            st.session_state.logged_in = True
            st.session_state.user_data = res.data[0]
            st.rerun()
        else:
            st.error("Credenziali non valide")
    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# 2. AREA RISERVATA (Tutto il software dentro questo ELSE)
# =========================================================
else:
    # --- SIDEBAR ELITE ---
    with st.sidebar:
        st.markdown('<div style="text-align: center;">', unsafe_allow_html=True)
        st.image("https://img.icons8.com/fluency/96/shield.png", width=60)
        u_data = st.session_state.user_data
        u_name = u_data.get('username')
        ruolo_utente = str(u_data.get('ruolo', 'Nessuno')).strip().capitalize()
        st.markdown(f"### {u_name}")
        st.markdown(f"🆔 **{ruolo_utente}**")
        st.markdown('</div>', unsafe_allow_html=True)
        st.divider()

        voci_menu = ["📋 Monitoraggio & Diario", "💉 Modulo Equipe", "🗓️ Agenda Uscite", "🛏️ Mappa Letti", "📖 Diario di Bordo"]
        if ruolo_utente == "Admin":
            voci_menu.append("⚙️ Pannello Admin")
        
        scelta_menu = st.radio("Seleziona Area:", voci_menu)
        st.divider()

        # Selezione Paziente
        res_p = supabase.table("pazienti").select("id, nome").execute()
        lista_p = {p['nome']: p['id'] for p in res_p.data}
        nome_sel = st.selectbox("🎯 Paziente in carico:", ["--"] + list(lista_p.keys()))
        
        paziente_attivo = nome_sel if nome_sel != "--" else None
        id_p_attivo = lista_p.get(nome_sel) if nome_sel != "--" else None

        if st.button("🚪 Esci dal Sistema", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()

    # --- NAVIGAZIONE PAGINE (Indentato correttamente) ---
    
    if scelta_menu == "📋 Monitoraggio & Diario":
        st.title("📋 Monitoraggio & Diario Clinico")
        if paziente_attivo:
            st.info(f"Dati di: {paziente_attivo}")
        else:
            st.warning("Seleziona un paziente nella sidebar.")

    elif scelta_menu == "💉 Modulo Equipe":
        st.markdown(f'<h1 style="color: #1e3a8a;">💉 Modulo Equipe</h1>', unsafe_allow_html=True)
        
        # Admin switch
        ruoli_disponibili = ["Psichiatra", "Infermiere", "Educatore", "Psicologo", "Assistente Sociale", "OSS", "OPSI"]
        if ruolo_utente == "Admin":
            ruolo_op = st.selectbox("🎭 Visualizza come (Filtro Ruolo):", ruoli_disponibili)
        else:
            ruolo_op = ruolo_utente

        st.divider()

        # 🩺 1. PSICHIATRA
        if ruolo_op == "Psichiatra":
            if not paziente_attivo: st.warning("⚠️ Seleziona paziente"); st.stop()
            tab1, tab2 = st.tabs(["📝 Prescrizioni", "📊 Monitoraggio"])
            with tab1:
                with st.form("f_psi"):
                    f_nome = st.text_input("Farmaco")
                    f_orario = st.selectbox("Range Orario", ["Mattina (08:00-13:00)", "Pomeriggio (14:00-21:00)", "Al bisogno (H24)"])
                    f_esami = st.text_area("Prescrizione Esami / Consegna Medica")
                    if st.form_submit_button("REGISTRA & RELAZIONE IA"):
                        st.success("Atto medico registrato.")
            with tab2:
                st.subheader("Andamento Assunzioni (Sola Lettura)")
                st.info("Tabella riassuntiva terapie somministrate in tempo reale.")
                # Esempio tabella statica
                st.table({"Ora": ["08:30"], "Farmaco": ["Depakin"], "Stato": ["A"], "Firma": ["Inf.1"]})

        # 💉 2. INFERMIERE
        elif ruolo_op == "Infermiere":
            if not paziente_attivo: st.warning("⚠️ Seleziona paziente"); st.stop()
            st.subheader("🗓️ Calendario Somministrazioni (A/R)")
            # Logica pulsanti per tabella dinamica
            c1, c2, c3 = st.columns([2,1,1])
            c1.write("**Terapia: Haldol 5mg**")
            if c2.button("✅ A (Assunta)"): st.success(f"Firma: {u_name}")
            if c3.button("❌ R (Rifiutata)"): st.error(f"Firma: {u_name}")
            
            with st.form("f_inf"):
                st.text_input("Parametri Vitali")
                st.text_area("Consegne Infermieristiche")
                if st.form_submit_button("GENERA BREAFING IA"):
                    st.info("Riassunto giornaliero in elaborazione...")

        # 🎨 3. EDUCATORE
        elif ruolo_op == "Educatore":
            if not paziente_attivo: st.warning("⚠️ Seleziona paziente"); st.stop()
            with st.form("f_edu"):
                st.subheader("💰 Registro Cassa & Attività")
                col1, col2 = st.columns(2)
                col1.number_input("Movimento € (Entrate/Uscite)", step=0.50)
                col2.text_input("Gestione Sigarette/Tabacco")
                st.text_area("Attività svolte / Consegne Educative")
                if st.form_submit_button("SALVA & FIRMA"):
                    st.success(f"Registrato da {u_name}")

        # 🧠 4. PSICOLOGO
        elif ruolo_op == "Psicologo":
            if not paziente_attivo: st.warning("⚠️ Seleziona paziente"); st.stop()
            with st.form("f_psico"):
                st.selectbox("Intervento", ["Colloquio Individuale", "Somministrazione Test"])
                st.text_area("Consegna / Relazione Psicologica")
                if st.form_submit_button("ARCHIVIA & RELAZIONE IA"):
                    st.success("Relazione archiviata.")

        # 🤝 5. ASSISTENTE SOCIALE
        elif ruolo_op == "Assistente Sociale":
            if not paziente_attivo: st.warning("⚠️ Seleziona paziente"); st.stop()
            with st.form("f_soc"):
                st.text_input("Rapporti Enti Pubblici (UEPE, DSM, Tribunale)")
                st.text_input("Rapporti Servizi del Territorio")
                st.text_area("Note Varie")
                if st.form_submit_button("SALVA"):
                    st.success("Aggiornamento sociale salvato.")

        # 🧺 6. OSS
        elif ruolo_op == "OSS":
            st.subheader("🧺 Consegne Generiche OSS")
            nota_oss = st.text_area("Consegne reparto (Logistica, Igiene, Varie)")
            if st.button("PUBBLICA CONSEGNA"):
                st.success("Nota OSS inserita.")

        # 🛡️ 7. OPSI
        elif ruolo_op == "OPSI":
            st.subheader("🛡️ Report Sicurezza OPSI")
            nota_opsi = st.text_area("Report vigilanza (Sicurezza Reparto)")
            if st.button("INVIA REPORT"):
                st.success("Report OPSI archiviato.")

    elif scelta_menu == "🗓️ Agenda Uscite":
        st.title("🗓️ Agenda Uscite")

    elif scelta_menu == "🛏️ Mappa Letti":
        st.title("🛏️ Mappa Letti")

    elif scelta_menu == "📖 Diario di Bordo":
        st.title("📖 Diario di Bordo")

    elif scelta_menu == "⚙️ Pannello Admin":
        st.title("⚙️ Pannello Admin")

# --- FINE DEL FILE ---
            

# =========================================================
# BLOCCO 3: MODULO EQUIPE (Allineato a scelta_menu)
# =========================================================

elif scelta_menu == "💉 Modulo Equipe":
        if not paziente_attivo:
            st.warning("⚠️ Seleziona un paziente nella Sidebar per sbloccare la Cartella Clinica.")
        else:
            st.markdown(f'<h2 style="color: #1e3a8a;">💉 Cartella Integrata: {paziente_attivo}</h2>', unsafe_allow_html=True)
            
            # --- SELETTORE RUOLO (LOGICA ELITE) ---
            # Permette all'Admin (Antony) di switchare tra tutti i ruoli 
            opzioni_ruolo = ["Psichiatra", "Infermiere", "Educatore", "Psicologo", "Assistente Sociale", "OSS", "OPSI"]
            if ruolo_utente == "Admin":
                ruolo_op = st.selectbox("🎭 Agisci come (Filtro Ruolo):", opzioni_ruolo)
            else:
                ruolo_op = ruolo_utente

            st.divider()

            # --- 1. AREA PSICHIATRA ---
            if ruolo_op == "Psichiatra":
                st.subheader("🩺 Area Medico-Psichiatrica")
                t_psi1, t_psi2 = st.tabs(["💊 Terapie & Esami", "📊 Monitoraggio Real-Time"])
                
                with t_psi1:
                    with st.form("form_psichiatra"):
                        st.markdown("##### Prescrizione e Modifica Terapia")
                        f_nome = st.text_input("Farmaco")
                        # Orari definiti dai range: Mattina (8-13), Pomeriggio (14-21), Al bisogno (H24) 
                        f_orario = st.selectbox("Fascia Oraria", ["Mattina (08:00-13:00)", "Pomeriggio (14:00-21:00)", "Al bisogno (H24)"])
                        f_dose = st.text_input("Dosaggio")
                        cons_medica = st.text_area("Consegna Medica / Prescrizione Esami")
                        
                        c1, c2 = st.columns(2)
                        if c1.form_submit_button("REGISTRA PRESCRIZIONE"):
                            supabase.table("terapie").insert({
                                "id_paziente": id_p_attivo, "farmaco": f_nome, "fascia": f_orario, 
                                "dose": f_dose, "medico": u_name
                            }).execute()
                            st.success("Terapia e prescrizioni archiviate.")
                        
                        if c2.form_submit_button("✨ GENERA RELAZIONE IA"):
                            st.info("Analisi clinica tramite Groq in corso...") # Integrazione IA 

                with t_psi2:
                    st.markdown("##### Andamento Assunzione (Sola Lettura)") # Tabella non modificabile 
                    res_s = supabase.table("somministrazioni").select("*").eq("id_paziente", id_p_attivo).execute()
                    if res_s.data:
                        st.table(pd.DataFrame(res_s.data)[['timestamp', 'farmaco', 'stato', 'operatore']])
                    else:
                        st.info("Nessun dato di assunzione rilevato.")

            # --- 2. AREA INFERMIERE ---
            elif ruolo_op == "Infermiere":
                st.subheader("💉 Area Infermieristica")
                # Calendario dinamico con Tabella A (Assunta) o R (Rifiutata) e firma 
                with st.expander("🗓️ Calendario Somministrazioni", expanded=True):
                    terapie = supabase.table("terapie").select("*").eq("id_paziente", id_p_attivo).execute()
                    for t in terapie.data:
                        col_t1, col_t2, col_t3 = st.columns([3, 1, 1])
                        col_t1.write(f"**{t['farmaco']}** [{t['fascia']}]")
                        if col_t2.button(f"✅ A", key=f"A_{t['id']}"):
                            supabase.table("somministrazioni").insert({
                                "id_paziente": id_p_attivo, "farmaco": t['farmaco'], "stato": "A", "operatore": u_name
                            }).execute()
                            st.success(f"Assunzione registrata da {u_name}")
                        if col_t3.button(f"❌ R", key=f"R_{t['id']}"):
                            motivo = st.text_input("Motivo Rifiuto", key=f"mot_{t['id']}")
                            if motivo:
                                supabase.table("somministrazioni").insert({
                                    "id_paziente": id_p_attivo, "farmaco": t['farmaco'], "stato": "R", "operatore": u_name, "note": motivo
                                }).execute()
                                st.error("Rifiuto registrato.")

                with st.form("inf_details"):
                    st.markdown("##### Parametri Vitali & Consegne")
                    c1, c2, c3 = st.columns(3)
                    pa = c1.text_input("PA (mmHg)")
                    fc = c2.text_input("FC (bpm)")
                    spo2 = c3.text_input("SpO2 (%)")
                    cons_inf = st.text_area("Consegne Infermieristiche")
                    if st.form_submit_button("SALVA MONITORAGGIO & IA BRIEFING"): # Briefing IA giornaliero 
                        st.success("Dati salvati. Generazione riassunto IA in corso...")

            # --- 3. AREA EDUCATORE ---
            elif ruolo_op == "Educatore":
                st.subheader("🎨 Area Educativa")
                # Registro cassa (Entrate, Uscite, Saldo) 
                with st.form("form_cassa"):
                    st.markdown("##### Registro Cassa, Tabacco e Attività")
                    c1, c2 = st.columns(2)
                    mov = c1.selectbox("Tipo Movimento", ["Entrata", "Uscita"])
                    valore = c2.number_input("Importo (€)", step=0.50)
                    causale = st.text_input("Causale (es. Spesa, Tabacco, Ricarica)")
                    attivita = st.text_area("Descrizione Attività Svolte")
                    cons_edu = st.text_area("Consegne Educative")
                    if st.form_submit_button("REGISTRA E FIRMA"):
                        supabase.table("cassa").insert({
                            "id_paziente": id_p_attivo, "tipo": mov, "importo": valore, 
                            "causale": causale, "operatore": u_name # Firma operatore automatica 
                        }).execute()
                        st.success("Movimento e attività salvati.")

            # --- 4. AREA PSICOLOGO ---
            elif ruolo_op == "Psicologo":
                st.subheader("🧠 Area Psicologica")
                with st.form("form_psicologo"):
                    # Colloqui, Test, Consegne e IA 
                    tipo_c = st.selectbox("Tipo Intervento", ["Colloquio Individuale", "Somministrazione Test", "Gruppo Terapeutico"])
                    dettaglio_test = st.text_input("Test Somministrati (es. MMPI, Rorschach)")
                    nota_psic = st.text_area("Consegna / Relazione Psicologica")
                    if st.form_submit_button("ARCHIVIA & ANALISI IA"):
                        st.success("Nota psicologica salvata con successo.")

            # --- 5. AREA ASSISTENTE SOCIALE ---
            elif ruolo_op == "Assistente Sociale":
                st.subheader("🤝 Area Sociale")
                with st.form("form_sociale"):
                    # Rapporti enti pubblici e territorio 
                    ente = st.text_input("Ente Pubblico / Servizio Territoriale (es. UEPE, DSM)")
                    contatto = st.text_input("Referente / Oggetto")
                    nota_sociale = st.text_area("Dettaglio Rapporti / Varie")
                    if st.form_submit_button("SALVA NOTA SOCIALE"):
                        st.success("Aggiornamento sociale registrato.")

            # --- 6. AREA OSS ---
            elif ruolo_op == "OSS":
                st.subheader("🧺 Area OSS (Consegne Generali)")
                # Consegne non legate al singolo paziente 
                nota_oss = st.text_area("Inserisci Consegna Generica (Igiene ambientale, Logistica reparto)")
                if st.button("PUBBLICA CONSEGNA OSS"):
                    st.success("Consegna generale pubblicata nel diario di bordo.")

            # --- 7. AREA OPSI ---
            elif ruolo_op == "OPSI":
                st.subheader("🛡️ Area OPSI (Vigilanza)")
                # Consegne generiche di sicurezza 
                nota_opsi = st.text_area("Report Vigilanza e Sicurezza (Generico Reparto)")
                if st.button("INVIA REPORT SICUREZZA"):
                    st.success("Report OPSI archiviato.")
        


# --- BLOCCO 4: LOGISTICA, AGENDA, MAPPA LETTI E AMMINISTRAZIONE ---

# 1. DIARIO DI BORDO COMUNE (Reparto/Logistica)
if scelta_menu == "📖 Diario di Bordo":
    st.header("📖 Diario di Bordo Comune")
    st.info("Utilizza questo spazio per comunicazioni di reparto, guasti, ordini o avvisi generali.")
    
    with st.form("form_diario_bordo"):
        livello_urgenza = st.select_slider("Livello Urgenza:", options=["Bassa", "Normale", "Alta", "🚨 CRITICA"])
        messaggio = st.text_area("Messaggio per l'Equipe:")
        if st.form_submit_button("PUBBLICA NOTA DI REPARTO"):
            # Usiamo ID Paziente 0 per indicare note di reparto (non cliniche)
            supabase.table("eventi").insert({
                "id_paziente": 0, "nota": f"[{livello_urgenza}] {messaggio}", 
                "ruolo": ruolo_utente, "operatore": firma_op, "timestamp": get_now().isoformat()
            }).execute()
            st.success("Nota di reparto pubblicata con successo.")
            st.rerun()

# 2. AGENDA DINAMICA (Uscite e Mezzi)
elif scelta_menu == "🗓️ Agenda Uscite":
    st.header("🗓️ Pianificazione Uscite e Trasporti")
    
    with st.expander("🆕 Programma Nuova Uscita/Trasferimento", expanded=True):
        p_coinvolti = st.multiselect("Seleziona Pazienti coinvolti:", list(diz_pazienti.keys()))
        mezzo_u = st.selectbox("Mezzo di trasporto:", ["Auto Reparto 1", "Doblò", "Ambulanza", "Mezzo Civile/Forze Ordine"])
        staff_u = st.text_input("Personale Accompagnatore (es. OPSI Bianchi, Inf. Neri)")
        destinazione = st.text_input("Destinazione (es. Visita Ospedaliera, Tribunale, Permesso)")
        
        if st.button("🚩 VALIDA E SALVA USCITA"):
            nota_u = f"🚗 [AGENDA USCITA] Destinazione: {destinazione} | Mezzo: {mezzo_u} | Staff: {staff_u}"
            # L'uscita viene scritta automaticamente nel diario di ogni paziente coinvolto
            for p_nome in p_coinvolti:
                id_p = diz_pazienti[p_nome]
                supabase.table("eventi").insert({
                    "id_paziente": id_p, "nota": nota_u, "ruolo": "Logistica", 
                    "operatore": firma_op, "timestamp": get_now().isoformat()
                }).execute()
            st.success(f"Uscita registrata per {len(p_coinvolti)} pazienti.")

# 3. MAPPA LETTI (Visualizzazione Spazi)
elif scelta_menu == "🛏️ Mappa Letti":
    st.header("🛏️ Gestione Posti Letto e Blocchi")
    
    col_ala_a, col_ala_b = st.columns(2)
    
    with col_ala_a:
        st.subheader("Blocco A (Stanze 1-6)")
        for i in range(1, 7):
            l_id = f"A{i}"
            # Icona speciale per stanza isolamento A6
            label_l = f"🛏️ Letto {l_id}" + (" 🛡️ (ISOLAMENTO)" if i==6 else "")
            res_l = supabase.table("pazienti").select("nome").eq("letto", l_id).execute()
            occupante = res_l.data[0]['nome'] if res_l.data else "--- LIBERO ---"
            st.button(f"{label_l}: {occupante}", key=f"btn_{l_id}", use_container_width=True)

    with col_ala_b:
        st.subheader("Blocco B (Stanze 1-10)")
        for i in range(1, 11):
            l_id = f"B{i}"
            label_l = f"🛏️ Letto {l_id}" + (" 🛡️ (ISOLAMENTO)" if i==10 else "")
            res_l = supabase.table("pazienti").select("nome").eq("letto", l_id).execute()
            occupante = res_l.data[0]['nome'] if res_l.data else "--- LIBERO ---"
            st.button(f"{label_l}: {occupante}", key=f"btn_{l_id}", use_container_width=True)

# 4. PANNELLO ADMIN (Potere Totale Ladimir)
elif scelta_menu == "⚙️ Pannello Admin":
    st.header("⚙️ Controllo di Gestione (Super-Admin)")
    t_adm1, t_adm2, t_adm3 = st.tabs(["👥 Account & Richieste", "🕵️ Audit Log (Scatola Nera)", "🏥 Gestione Anagrafica"])
    
    with t_adm1:
        st.subheader("Approvazione Nuovi Utenti")
        richieste = supabase.table("utenti_richieste").select("*").execute()
        if richieste.data:
            df_req = pd.DataFrame(richieste.data)
            st.dataframe(df_req, use_container_width=True)
            u_approva = st.selectbox("Seleziona Username da attivare:", [r['username'] for r in richieste.data])
            if st.button("✅ APPROVA E ATTIVA ACCOUNT"):
                # Qui l'admin sposta l'utente nella tabella definitiva 'utenti'
                st.info(f"Procedura di attivazione per {u_approva} avviata.")
        else:
            st.write("Nessuna richiesta di registrazione pendente.")

    with t_adm2:
        st.subheader("🕵️ Cronologia Accessi e Operazioni")
        logs = supabase.table("logs").select("*").order("timestamp", desc=True).limit(100).execute()
        if logs.data:
            st.table(pd.DataFrame(logs.data))
        
        if st.button("📥 SCARICA BACKUP SQL (Sicurezza Peritale)"):
            st.toast("Generazione file di backup...")

    with t_adm3:
        st.subheader("Anagrafica Pazienti")
        with st.form("add_paz_admin"):
            n_paz = st.text_input("Nome e Cognome Paziente")
            l_paz = st.text_input("Assegnazione Letto (es. A3)")
            if st.form_submit_button("REGISTRA NUOVO INGRESSO"):
                supabase.table("pazienti").insert({"nome": n_paz, "letto": l_paz}).execute()
                st.success(f"Paziente {n_paz} inserito correttamente.")

# --- FOOTER DI CHIUSURA ---
st.divider()
st.markdown(f"""
    <div style="text-align: center; color: #7f8c8d; font-size: 0.85em; padding: 20px;">
        <b>REMS-Connect Elite v2.0</b><br>
        Sistema Certificato per la Gestione Clinica e Peritale<br>
        <i>Sessione attiva per: {firma_op} | {get_now().strftime('%d/%m/%Y %H:%M:%S')}</i>
    </div>
""", unsafe_allow_html=True)
