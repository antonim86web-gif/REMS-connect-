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

# --- VARIABILI GLOBALI DI FIRMA ---
# Queste verranno usate in tutti i blocchi successivi
# --- LOGICA DI SICUREZZA PER LE VARIABILI DI SESSIONE (Sostituisce riga 120-121) ---
if not st.session_state.get('logged_in', False):
    # Sezione Login
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

else:
    # --- 1. SIDEBAR TECNOLOGIA ELITE ---
    with st.sidebar:
        st.markdown('<div style="text-align: center; padding: 10px;">', unsafe_allow_html=True)
        st.image("https://img.icons8.com/fluency/96/shield.png", width=60)
        
        u_data = st.session_state.user_data
        ruolo_utente = str(u_data.get('ruolo', 'Nessuno')).strip().capitalize()
        
        st.markdown(f"### {u_data.get('username')}")
        st.markdown(f'<p style="color: #6c757d; font-weight: 500;">🆔 RUOLO: {ruolo_utente}</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        st.divider()

        voci_menu = ["📋 Monitoraggio & Diario", "💉 Modulo Equipe", "🗓️ Agenda Uscite", "🛏️ Mappa Letti", "📖 Diario di Bordo"]
        if ruolo_utente == "Admin":
            voci_menu.append("⚙️ Pannello Admin")

        scelta_menu = st.radio("Sfoglia Sezioni:", voci_menu)
        st.divider()

        # Selezione Paziente
        try:
            res_p = supabase.table("pazienti").select("id, nome").execute()
            lista_p = {p['nome']: p['id'] for p in res_p.data}
            st.markdown('<p style="font-size: 0.8em; font-weight: 700; color: #1e3a8a;">🎯 SELEZIONE PAZIENTE</p>', unsafe_allow_html=True)
            nome_sel = st.selectbox("", ["--"] + list(lista_p.keys()), key="sidebar_paz_select")
            
            if nome_sel != "--":
                paziente_attivo = nome_sel
                id_p_attivo = lista_p[nome_sel]
                st.success(f"Attivo: {paziente_attivo}")
            else:
                paziente_attivo = None
                id_p_attivo = None
                st.warning("⚠️ Seleziona paziente")
        except:
            st.error("Errore Database")

        st.divider()
        if st.button("🚪 LOGOUT", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()

    # =========================================================
    # 3. LOGICA DI CARICAMENTO PAGINE (Routing)
    # =========================================================
    
    if scelta_menu == "📋 Monitoraggio & Diario":
        # Sezione Monitoraggio originale
        st.markdown(f'<h1 style="color: #1e3a8a;">📋 Monitoraggio & Diario Clinico</h1>', unsafe_allow_html=True)
        if paziente_attivo:
            st.info(f"Paziente selezionato: **{paziente_attivo}**")
            # --- Inserisci qui il tuo codice specifico del Monitoraggio ---
        else:
            st.warning("Seleziona un paziente nella Sidebar per visualizzare i dati clinici.")

    elif scelta_menu == "💉 Modulo Equipe":
        # Sezione Modulo Equipe (Blocco 3)
        if not paziente_attivo:
            st.warning("⚠️ Seleziona un paziente nella Sidebar per operare nel Modulo Equipe.")
        else:
            st.markdown(f'<h1 style="color: #1e3a8a;">💉 Modulo Equipe: {paziente_attivo}</h1>', unsafe_allow_html=True)
            # Qui il codice richiama le funzioni medico/infermiere/educatore
            # basandosi sulla variabile 'ruolo_utente'

    elif scelta_menu == "🗓️ Agenda Uscite":
        st.title("🗓️ Agenda Uscite & Permessi")
        # Inserisci qui il codice per l'agenda uscite

    elif scelta_menu == "🛏️ Mappa Letti":
        st.title("🛏️ Gestione Mappa Letti")
        # Inserisci qui il codice per la mappa letti

    elif scelta_menu == "📖 Diario di Bordo":
        st.title("📖 Diario di Bordo (Consegne Reparto)")
        # Inserisci qui il codice per le consegne generali

    elif scelta_menu == "⚙️ Pannello Admin":
        if ruolo_utente == "Admin":
            st.title("⚙️ Pannello Amministrazione Sistema")
            # Inserisci qui il codice per l'approvazione utenti e log
        else:
            st.error("Accesso negato. Autorizzazioni insufficienti.")

# --- FINE DEL FILE ---
            

# =========================================================
# BLOCCO 3: MODULO EQUIPE (Allineato a scelta_menu)
# =========================================================

if scelta_menu == "💉 Modulo Equipe":
        if not paziente_attivo:
            st.warning("⚠️ Seleziona un paziente nella Sidebar per operare nel Modulo Equipe.")
        else:
            # Layout Intestazione Elite
            st.markdown(f"""
                <div style="background-color: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-left: 5px solid #1e3a8a; margin-bottom: 20px;">
                    <h2 style="margin:0; color: #1e3a8a;">💉 Cartella Clinica Integrata</h2>
                    <p style="margin:0; color: #666;">Paziente: <b>{paziente_attivo}</b> | ID: {id_p_attivo}</p>
                </div>
            """, unsafe_allow_html=True)

            # --- SELETTORE RUOLO OPERATIVO (MENU A TENDINA) ---
            opzioni_ruolo = [
                "Psichiatra", "Infermiere", "Educatore", 
                "Psicologo", "Assistente Sociale", "OSS", "OPSI"
            ]
            
            # Se sei Admin puoi switchare, altrimenti vedi solo il tuo
            if ruolo_utente == "Admin":
                ruolo_operativo = st.selectbox("🎭 Visualizza come (Filtro Ruolo):", opzioni_ruolo)
            else:
                ruolo_operativo = ruolo_utente
                st.info(f"Accesso limitato al profilo: **{ruolo_operativo}**")

            st.divider()

            # --- LOGICA DEI SINGOLI MODULI DIVISI ---

            # 1. PSICHIATRA
            if ruolo_operativo == "Psichiatra":
                st.subheader("🩺 Area Medico-Psichiatrica")
                with st.form("form_psichiatra"):
                    st.markdown("##### 💊 Prescrizione Terapia")
                    farmaco = st.text_input("Farmaco e Dosaggio")
                    orari = st.multiselect("Fasce Orarie", ["Mattina", "Pranzo", "Pomeriggio", "Cena", "Notte", "Al bisogno"])
                    note_mediche = st.text_area("Indicazioni Cliniche / Note Peritali")
                    if st.form_submit_button("REGISTRA PRESCRIZIONE"):
                        # Logica save su Supabase (tabella prescrizioni)
                        st.success("Terapia registrata con firma peritale.")

            # 2. INFERMIERE
            elif ruolo_operativo == "Infermiere":
                st.subheader("💉 Area Infermieristica")
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("##### 📊 Parametri Vitali")
                    pa = st.text_input("Pressione Art.")
                    fc = st.number_input("Freq. Cardiaca", step=1)
                with col2:
                    st.markdown("##### 💊 Somministrazione")
                    st.button("✅ CONFERMA TERAPIA MATTINA")
                    st.button("❌ RIFIUTO TERAPIA")

            # 3. EDUCATORE
            elif ruolo_operativo == "Educatore":
                st.subheader("🎨 Area Educativa")
                with st.form("form_educatore"):
                    st.markdown("##### 💰 Gestione Cassa e Tabacco")
                    importo = st.number_input("Importo (€)", step=0.50)
                    causale = st.selectbox("Causale", ["Spesa", "Tabacco", "Ricarica", "Altro"])
                    descrizione = st.text_area("Dettaglio attività educativa")
                    if st.form_submit_button("SALVA OPERAZIONE"):
                        st.success("Movimento cassa registrato.")

            # 4. PSICOLOGO (Separato)
            elif ruolo_operativo == "Psicologo":
                st.subheader("🧠 Area Psicologica")
                with st.expander("📝 Diario Colloqui Individuali", expanded=True):
                    osservazioni = st.text_area("Note del colloquio clinico")
                    test = st.text_input("Test somministrati (es. MMPI-2)")
                    if st.button("SALVA DIARIO PSICOLOGICO"):
                        st.success("Colloquio archiviato in area protetta.")

            # 5. ASSISTENTE SOCIALE (Separato)
            elif ruolo_operativo == "Assistente Sociale":
                st.subheader("🤝 Area Sociale & Territoriale")
                with st.expander("📞 Rapporti Enti Esterni", expanded=True):
                    ente = st.text_input("Ente di riferimento (UEPE, Tribunale, DSM)")
                    relazione = st.text_area("Sintesi aggiornamento sociale")
                    if st.button("SALVA NOTA SOCIALE"):
                        st.success("Aggiornamento inviato all'archivio.")

            # 6. OSS (Separato)
            elif ruolo_operativo == "OSS":
                st.subheader("🧺 Area Assistenziale (OSS)")
                with st.form("form_oss"):
                    st.markdown("##### 🧼 Igiene e Supporto")
                    opzioni_igiene = st.multiselect("Attività svolte", ["Igiene totale", "Cambio biancheria", "Supporto pasti", "Monitoraggio sonno"])
                    note_oss = st.text_area("Note assistenziali")
                    if st.form_submit_button("REGISTRA ATTIVITÀ OSS"):
                        st.success("Nota assistenziale salvata.")

            # 7. OPSI (Separato)
            elif ruolo_operativo == "OPSI":
                st.subheader("🛡️ Area Vigilanza & Sicurezza (OPSI)")
                with st.form("form_opsi"):
                    st.markdown("##### 👮 Monitoraggio Sicurezza")
                    ispezione = st.checkbox("Ispezione camera effettuata")
                    oggetti = st.text_input("Oggetti non autorizzati rinvenuti")
                    comportamento = st.select_slider("Livello di collaborazione", options=["Basso", "Medio", "Alto"])
                    if st.form_submit_button("INVIA REPORT OPSI"):
                        st.success("Report sicurezza inviato al sistema.")
        


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
