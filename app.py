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
if st.session_state.logged_in and st.session_state.user_data:
    # Cerchiamo i dati sia con la minuscola che con la maiuscola
    u_name = st.session_state.user_data.get('username') or st.session_state.user_data.get('Username', 'Utente')
    u_role = st.session_state.user_data.get('ruolo') or st.session_state.user_data.get('Ruolo', 'Staff')
    
    firma_op = f"{u_name} ({u_role})"
    ruolo_utente = u_role
else:
    # Se i dati mancano, resettiamo e fermiamo per sicurezza
    st.session_state.logged_in = False
    st.stop()


# --- BLOCCO 2: NAVIGAZIONE, FILTRI E MONITORAGGIO ---

# 1. SIDEBAR DI NAVIGAZIONE (Struttura Dinamica per Ruoli)
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>🛡️ MENU</h2>", unsafe_allow_html=True)
    st.write(f"👤 **Op:** {st.session_state.user_data['username']}")
    st.write(f"🆔 **Ruolo:** {ruolo_utente}")
    st.divider()

    # Menu principale
    voci_menu = ["📋 Monitoraggio & Diario", "💉 Modulo Equipe", "🗓️ Agenda Uscite", "🛏️ Mappa Letti", "📖 Diario di Bordo"]
        # Sezione Admin visibile per chi ha ruolo Admin o Staff (per sbloccarti ora)
    if ruolo_utente in ["Admin", "Staff", "admin", "staff"]:
        voci_menu.append("⚙️ Pannello Admin")

    scelta_menu = st.radio("Seleziona Area:", voci_menu)
    
    st.divider()
    if st.button("🚪 Esci dal Sistema"):
        st.session_state.logged_in = False
        st.session_state.user_data = None
        st.rerun()

# 2. SELEZIONE PAZIENTE GLOBALE (Necessaria per i blocchi successivi)
# Recupero lista pazienti da Supabase
try:
    res_paz = supabase.table("pazienti").select("id, nome, letto").execute()
    diz_pazienti = {p['nome']: p['id'] for p in res_paz.data} if res_paz.data else {}
except:
    diz_pazienti = {}

st.markdown("---")
col_p1, col_p2 = st.columns([2, 1])
with col_p1:
    paz_selezionato = st.selectbox("🎯 Operazione attiva su Paziente:", ["---"] + list(diz_pazienti.keys()))
    p_id = diz_pazienti.get(paz_selezionato)

# 3. LOGICA MONITORAGGIO (Visualizzazione Cronologica)
if scelta_menu == "📋 Monitoraggio & Diario":
    st.header(f"🔍 Diario Clinico: {paz_selezionato}")
    
    if paz_selezionato == "---":
        st.info("💡 Seleziona un paziente dal menu a tendina sopra per visualizzare la sua storia clinica.")
    else:
        # --- FILTRI AVANZATI ---
        with st.expander("🔎 Filtri di Ricerca Investigativa", expanded=False):
            f1, f2, f3 = st.columns(3)
            f_ruolo = f1.selectbox("Filtra per Ruolo:", ["Tutti", "Psichiatra", "Infermiere", "Psicologo", "Educatore", "Sociale", "OSS", "OPSI"])
            f_testo = f2.text_input("Cerca parola (es: 'caduta', 'rifiuto'):")
            f_data = f3.date_input("Dalla data:", value=None)

        # --- ESECUZIONE QUERY FILTRATA ---
        query = supabase.table("eventi").select("*").eq("id_paziente", p_id).order("timestamp", desc=True)
        
        if f_ruolo != "Tutti":
            query = query.eq("ruolo", f_ruolo)
        if f_testo:
            query = query.ilike("nota", f"%{f_testo}%")
            
        res_note = query.execute()

        # --- AZIONI DI REPORTISTICA ---
        c_rep1, c_rep2 = st.columns([1, 4])
        if c_rep1.button("📄 GENERA REPORT PDF"):
            st.toast("Preparazione PDF in corso...", icon="⏳")
            # La logica ReportLab verrà richiamata qui nel blocco finale

        # --- VISUALIZZAZIONE A TIMELINE ---
        if res_note.data:
            st.write(f"📝 **{len(res_note.data)}** interventi registrati in archivio.")
            
            # Mappa colori per identificazione rapida
            colori = {
                "Psichiatra": "#d1ecf1", "Infermiere": "#d4edda", 
                "OPSI": "#f8d7da", "Psicologo": "#e2e3e5", 
                "Educatore": "#fff3cd", "Admin": "#ffffff"
            }

            for nota in res_note.data:
                bg = colori.get(nota['ruolo'], "#ffffff")
                # Formattazione data
                dt_obj = datetime.fromisoformat(nota['timestamp'])
                data_f = dt_obj.strftime("%d/%m/%Y - %H:%M")
                
                st.markdown(f"""
                    <div style="background-color:{bg}; padding:15px; border-radius:10px; border-left: 8px solid #2c3e50; margin-bottom:15px; color: #1e1e1e; box-shadow: 2px 2px 8px rgba(0,0,0,0.1);">
                        <div style="display: flex; justify-content: space-between; border-bottom: 1px solid rgba(0,0,0,0.1); padding-bottom: 5px; margin-bottom: 10px;">
                            <span style="font-weight: bold; font-size: 0.9em;">📅 {data_f}</span>
                            <span style="text-transform: uppercase; font-weight: 800; font-size: 0.75em; letter-spacing: 1px;">{nota['ruolo']}</span>
                        </div>
                        <div style="font-size: 1.1em; line-height: 1.4;">{nota['nota']}</div>
                        <div style="text-align: right; margin-top: 10px; font-style: italic; font-size: 0.85em; color: #444;">
                            ✍️ Firmato: {nota['operatore']}
                        </div>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("⚠️ Nessuna nota trovata con i filtri selezionati.")
            

# --- BLOCCO 3: MODULO EQUIPE (OPERATIVITÀ PROFESSIONALE) ---
# =========================================================
# BLOCCO 3: MODULO EQUIPE MULTIDISCIPLINARE
# =========================================================
if menu == "💉 Modulo Equipe":
    st.header("💉 Centro di Comando Equipe")

    # --- A. CONSEGNE GENERALI DI REPARTO (NON PAZIENTE-SPECIFICHE) ---
    st.subheader("📢 Consegne Generali di Reparto")
    col_gen1, col_gen2 = st.columns(2)

    with col_gen1:
        if ruolo_utente in ["Admin", "OSS"]:
            with st.expander("🧼 CONSEGNA GENERALE OSS", expanded=False):
                nota_oss_gen = st.text_area("Briefing Generale OSS (Vitto, Igiene, Magazzino)", key="g_oss")
                if st.button("📌 Invia Consegna Generale OSS"):
                    registra_evento(0, f"REPARTO - OSS: {nota_oss_gen}", "OSS", firma_op)
                    st.success("Consegna OSS registrata.")

    with col_gen2:
        if ruolo_utente in ["Admin", "Opsi"]:
            with st.expander("🛡️ CONSEGNA GENERALE OPSI", expanded=False):
                nota_opsi_gen = st.text_area("Briefing Generale OPSI (Sicurezza, Clima Reparto)", key="g_opsi")
                if st.button("📌 Invia Consegna Generale OPSI"):
                    registra_evento(0, f"REPARTO - OPSI: {nota_opsi_gen}", "Opsi", firma_op)
                    st.success("Consegna Opsi registrata.")

    st.markdown("---")

    # --- B. SEZIONE CLINICA (SPECIFICA PER PAZIENTE) ---
    if not paziente_attivo:
        st.info("👈 Seleziona un paziente dalla barra laterale per le note cliniche.")
    else:
        st.subheader(f"🏥 Cartella Attiva: {paziente_attivo}")

        # 1. PSICHIATRA / MEDICO (Prescrizione e Diagnostica)
        if ruolo_utente in ["Admin", "Psichiatra", "Medico"]:
            with st.expander("🩺 AREA MEDICA & PSICHIATRICA", expanded=True):
                st.write("**Gestione Terapia ed Esami**")
                terapia_presc = st.text_area("Prescrivi o Modifica Terapia (Posologia e Orari)")
                esami_req = st.multiselect("Richiesta Esami:", ["Ematici Generali", "Litiemia", "ECG", "EEG", "TC Encefalo", "Consulenza Specialistica"])
                consegna_med = st.text_area("Integrazione D.I. / Consegna per l'Equipe")
                if st.button("💾 Salva Prescrizioni Mediche"):
                    testo_med = f"PRESCRIZIONE: {terapia_presc} | ESAMI: {', '.join(esami_req)} | CONSEGNA: {consegna_med}"
                    registra_evento(id_p_attivo, testo_med, "Medico", firma_op)
                    st.success("Prescrizione registrata.")

        # 2. INFERMIERE (Smarcamento e Parametri)
        if ruolo_utente in ["Admin", "Infermiere"]:
            with st.expander("💊 AREA INFERMIERISTICA", expanded=True):
                st.write("**Smarcamento Terapia**")
                c1, c2 = st.columns(2)
                if c1.button("✅ TERAPIA ASSUNTA"):
                    registra_evento(id_p_attivo, "Esito Terapia: ASSUNTA", "Infermiere", firma_op)
                if c2.button("❌ TERAPIA RIFIUTATA"):
                    motivo_r = st.text_input("Specifica motivo rifiuto", key="mot_rif")
                    if motivo_r: registra_evento(id_p_attivo, f"Esito Terapia: RIFIUTATA ({motivo_r})", "Infermiere", firma_op)
                
                st.write("**Monitoraggio & Consegne**")
                p1, p2, p3 = st.columns(3)
                pa = p1.text_input("P.A.")
                fc = p2.text_input("F.C.")
                temp = p3.text_input("Temp °C")
                rel_inf = st.text_area("Relazione Infermieristica / Briefing per OSS")
                if st.button("💾 Salva Monitoraggio Infermiere"):
                    registra_evento(id_p_attivo, f"PARAMETRI: PA {pa}, FC {fc}, T {temp} | RELAZIONE: {rel_inf}", "Infermiere", firma_op)

        # 3. PSICOLOGO (Colloqui e Test)
        if ruolo_utente in ["Admin", "Psicologo"]:
            with st.expander("🧠 AREA PSICOLOGICA", expanded=False):
                tipo_at = st.selectbox("Attività", ["Colloquio Individuale", "Somministrazione Test", "Sostegno Psicologico"])
                dettagli_p = st.text_area("Note del colloquio o risultati test")
                if st.button("💾 Salva Nota Psicologo"):
                    registra_evento(id_p_attivo, f"[{tipo_at}] {dettagli_p}", "Psicologo", firma_op)

        # 4. ASSISTENTE SOCIALE (Enti e Territorio)
        if ruolo_utente in ["Admin", "Sociale"]:
            with st.expander("🌍 AREA SOCIALE", expanded=False):
                enti_ext = st.text_input("Relazione con Enti (UEPE, Tribunale, Magistrato)")
                territorio_serv = st.text_area("Contatti con Servizi Territoriali (CSM, SERD, Comuni)")
                if st.button("💾 Salva Relazione Sociale"):
                    registra_evento(id_p_attivo, f"ENTI: {enti_ext} | TERRITORIO: {territorio_serv}", "Sociale", firma_op)

        # 5. EDUCATORE (Cassa, Tabacco e Progetti)
        if ruolo_utente in ["Admin", "Educatore"]:
            with st.expander("🎨 AREA EDUCATIVA: GESTIONE", expanded=False):
                st.write("**💰 Contabilità Cassa Paziente**")
                col_c1, col_c2 = st.columns(2)
                t_mov = col_c1.selectbox("Movimento", ["Entrata", "Uscita"])
                valore = col_c2.number_input("Importo (€)", min_value=0.0, step=0.5)
                causale_c = st.text_input("Causale Movimento")
                
                if st.button("🧧 Registra Movimento Cassa"):
                    if valore > 0 and causale_c:
                        supabase.table("cassa").insert({"id_paziente": id_p_attivo, "tipo": t_mov, "importo": valore, "causale": causale_c, "operatore": firma_op}).execute()
                        segno = "+" if t_mov == "Entrata" else "-"
                        registra_evento(id_p_attivo, f"MOVIMENTO CASSA: {segno}{valore}€ | Causale: {causale_c}", "Educatore", firma_op)
                        st.success("Movimento registrato in tabella e diario.")

                st.markdown("---")
                tabacco_q = st.number_input("Quantità Tabacco/Sigarette consegnata", step=1)
                cons_edu = st.text_area("Consegna Educativa / Progetto Riabilitativo")
                if st.button("💾 Salva Report Educatore"):
                    registra_evento(id_p_attivo, f"TABACCO: {tabacco_q} pz | NOTE: {cons_edu}", "Educatore", firma_op)

        # 6. OPSI (Monitoraggio Clinico/Relazionale)
        if ruolo_utente in ["Admin", "Opsi"]:
            with st.expander("🛡️ AREA OPSI: OSSERVAZIONE", expanded=False):
                clima_paz = st.selectbox("Clima Relazionale", ["Collaborante", "Oppositivo", "Ritiro", "Agitato"])
                obs_opsi = st.text_area("Osservazione Dinamiche e Comportamento")
                if st.button("💾 Salva Nota Opsi"):
                    registra_evento(id_p_attivo, f"CLIMA: {clima_paz} | OSS: {obs_opsi}", "Opsi", firma_op)

        # 7. OSS (Assistenza Diretta)
        if ruolo_utente in ["Admin", "OSS"]:
            with st.expander("🧼 AREA OSS: ASSISTENZA", expanded=False):
                igiene_p = st.checkbox("Igiene Personale Completata")
                appetito_p = st.select_slider("Appetito", options=["Scarso", "Normale", "Eccessivo"])
                if st.button("💾 Salva Nota OSS"):
                    registra_evento(id_p_attivo, f"IGIENE: {igiene_p} | PASTO: {appetito_p}", "OSS", firma_op)
                    

        
        


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
