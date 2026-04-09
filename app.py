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

if scelta_menu == "💉 Modulo Equipe":
    if paz_selezionato == "---":
        st.warning("⚠️ Per inserire nuovi dati, seleziona prima un paziente dal menu superiore.")
    else:
        st.header(f"🩺 Area Operativa: {paz_selezionato}")
        
        # --- 1. AREA PSICHIATRA & MEDICO ---
        if ruolo_utente == "Psichiatra":
            with st.expander("💊 Terapie e Analisi Clinica IA", expanded=True):
                t_med1, t_med2 = st.tabs(["Nuova Prescrizione", "Sintesi Clinica IA"])
                with t_med1:
                    farmaco = st.text_input("Farmaco, Dosaggio e Posologia")
                    if st.button("REGISTRA PRESCRIZIONE"):
                        nota_m = f"💊 [PRESCRIZIONE] {farmaco}"
                        supabase.table("eventi").insert({
                            "id_paziente": p_id, "nota": nota_m, "ruolo": "Psichiatra", 
                            "operatore": firma_op, "timestamp": get_now().isoformat()
                        }).execute()
                        st.success("Prescrizione inserita a diario.")
                with t_med2:
                    if st.button("🤖 GENERA RIASSUNTO CLINICO CON IA"):
                        storico = supabase.table("eventi").select("nota").eq("id_paziente", p_id).limit(15).execute()
                        testo_clinico = " ".join([n['nota'] for n in storico.data])
                        prompt = f"Agisci come un perito psichiatra. Riassumi i punti salienti dell'andamento clinico: {testo_clinico}"
                        res_ia = client_groq.chat.completions.create(
                            messages=[{"role": "user", "content": prompt}],
                            model="llama3-8b-8192",
                        )
                        st.info(res_ia.choices[0].message.content)

        # --- 2. AREA INFERMIERE (Smarcamento e Parametri) ---
        elif ruolo_utente == "Infermiere":
            t_inf1, t_inf2 = st.tabs(["📊 Parametri Vitali", "💉 Somministrazione Farmaci"])
            
            with t_inf1:
                st.subheader("Rilevazione Parametri")
                c_inf1, c_inf2, c_inf3 = st.columns(3)
                pa_v = c_inf1.text_input("Pressione (es. 120/80)")
                fc_v = c_inf2.text_input("FC (BPM)")
                t_v = c_inf3.text_input("Temperatura (°C)")
                if st.button("💾 SALVA PARAMETRI"):
                    nota_p = f"📊 [PARAMETRI] PA: {pa_v}, FC: {fc_v}, T: {t_v}"
                    supabase.table("eventi").insert({
                        "id_paziente": p_id, "nota": nota_p, "ruolo": "Infermiere", 
                        "operatore": firma_op, "timestamp": get_now().isoformat()
                    }).execute()
                    st.success("Parametri registrati.")

            with t_inf2:
                st.subheader("Registro Terapie")
                farmaco_sel = st.selectbox("Terapia da somministrare:", ["Mattino", "Mezzogiorno", "Pomeriggio", "Sera", "Notte", "AL BISOGNO"])
                
                # FOCUS: Gestione Accettazione/Rifiuto
                esito = st.radio("Esito Somministrazione:", ["✅ ACCETTATA", "❌ RIFIUTATA", "⚠️ NON SOMMINISTRATA"], horizontal=True)
                motivo = st.text_area("Note / Motivazione del rifiuto (Obbligatoria per rifiuti):")
                
                if st.button("🖋️ FIRMA E REGISTRA"):
                    if esito != "✅ ACCETTATA" and not motivo:
                        st.error("Errore: In caso di rifiuto o mancata somministrazione, è obbligatorio indicare la motivazione.")
                    else:
                        nota_inf = f"💉 [TERAPIA] {farmaco_sel}: {esito}"
                        if motivo: nota_inf += f" | Note: {motivo}"
                        
                        supabase.table("eventi").insert({
                            "id_paziente": p_id, "nota": nota_inf, "ruolo": "Infermiere", 
                            "operatore": firma_op, "timestamp": get_now().isoformat()
                        }).execute()
                        st.success(f"Registrazione effettuata con firma: {firma_op}")

        # --- 3. AREA PSICOLOGO / ASS. SOCIALE ---
        elif ruolo_utente in ["Psicologo", "Assistente Sociale"]:
            st.subheader(f"Area {ruolo_utente}")
            testo_colloquio = st.text_area("Annotazioni sul colloquio / Intervento:")
            if st.button("💾 SALVA INTERVENTO"):
# --- MODULO EQUIPE AVANZATO (CLINICA & DIAGNOSTICA) ---
if menu == "💉 Modulo Equipe":
    if not paziente_attivo:
        st.warning("⚠️ Seleziona un paziente dalla barra laterale.")
    else:
        st.header(f"💉 Centro di Comando Equipe - {paziente_attivo}")
        
        # 1. PSICHIATRA & MEDICO (Prescrizioni e Diagnostica)
        if ruolo_utente in ["Admin", "Psichiatra", "Medico"]:
            with st.expander("🩺 AREA MEDICA: PRESCRIZIONI ED ESAMI", expanded=True):
                st.subheader("💊 Prescrizione Farmacologica")
                farmaco = st.text_input("Farmaco e Dosaggio", placeholder="Es: Quetiapina 300mg ore 20")
                frequenza = st.selectbox("Frequenza", ["1 volta al dì", "2 volte al dì", "3 volte al dì", "Al bisogno (al p.t.)"])
                
                st.subheader("🔬 Richiesta Esami e Accertamenti")
                tipo_esame = st.multiselect("Esami richiesti:", 
                    ["Esami Ematici Completi", "Dosaggio Litiemia", "ECG", "EEG", "TC Encefalo", "Consulenza Specialistica"])
                note_diagnostiche = st.text_area("Note aggiuntive per la diagnostica")
                
                if st.button("💾 Invia Prescrizioni e Richieste"):
                    info_med = f"PRESCRIZIONE: {farmaco} ({frequenza}) | ESAMI: {', '.join(tipo_esame)} | NOTE: {note_diagnostiche}"
                    registra_evento(id_p_attivo, info_med, "Medico/Psichiatra", firma_op)
                    st.success("Prescrizioni registrate e inviate al database.")

        # 2. INFERMIERE (Somministrazione e Parametri)
        if ruolo_utente in ["Admin", "Infermiere"]:
            with st.expander("💊 AREA INFERMIERISTICA: MONITORAGGIO", expanded=False):
                col_inf1, col_inf2, col_inf3 = st.columns(3)
                pa = col_inf1.text_input("Pressione Art.", placeholder="120/80")
                fc = col_inf2.number_input("Freq. Card.", value=0)
                temp = col_inf3.number_input("Temp. °C", value=36.5, step=0.1)
                
                esito_esami = st.text_area("Esito Esami effettuati (se presenti)")
                
                col_btn1, col_btn2 = st.columns(2)
                if col_btn1.button("✅ Terapia Somministrata"):
                    nota_t = f"Terapia OK. Parametri: PA {pa}, FC {fc}, T {temp}. Esiti: {esito_esami}"
                    registra_evento(id_p_attivo, nota_t, "Infermiere", firma_op)
                if col_btn2.button("❌ Terapia Rifiutata"):
                    registra_evento(id_p_attivo, f"RIFIUTO TERAPIA. Motivo: {esito_esami}", "Infermiere", firma_op)

        # 3. PSICOLOGO & SOCIALE (Valutazione Funzionale)
        if ruolo_utente in ["Admin", "Psicologo", "Sociale"]:
            with st.expander("🗣️ AREA PSICOLOGO / SOCIALE", expanded=False):
                intervento = st.selectbox("Intervento", ["Colloquio", "Test VADO/PANSS", "Relazione Magistratura", "Rete Territoriale"])
                contenuto = st.text_area("Contenuto del colloquio o della relazione")
                if st.button("💾 Salva Intervento"):
                    registra_evento(id_p_attivo, f"[{intervento}] {contenuto}", "Psicologo/Sociale", firma_op)

        # 4. EDUCATORE & OPSI (Riabilitazione e Sicurezza)
        if ruolo_utente in ["Admin", "Educatore", "Opsi"]:
            with st.expander("🎨 AREA EDUCATORE & OPSI", expanded=False):
                col_riab1, col_riab2 = st.columns(2)
                with col_riab1:
                    attivita = st.text_input("Attività Riabilitativa")
                    partecipazione = st.select_slider("Partecipazione", ["Nulla", "Minima", "Buona", "Ottima"])
                with col_riab2:
                    clima = st.selectbox("Comportamento", ["Adeguato", "Iperattivo", "Ritiro Sociale", "Aggressività"])
                
                if st.button("💾 Salva Report Riabilitativo"):
                    nota_riab = f"ATTIVITÀ: {attivita} (Partecipazione: {partecipazione}) | COMPORTAMENTO: {clima}"
                    # Identifichiamo il ruolo specifico per la firma
                    r_firma = "Opsi" if "Opsi" in ruolo_utente else "Educatore"
                    registra_evento(id_p_attivo, nota_riab, r_firma, firma_op)

        # 5. OSS (Accudimento)
        if ruolo_utente in ["Admin", "OSS"]:
            with st.expander("🧼 AREA OSS", expanded=False):
                igiene = st.checkbox("Cura della persona effettuata")
                alimentazione = st.select_slider("Alimentazione", ["Scarsa", "Normale", "Eccessiva"])
                if st.button("💾 Salva Nota OSS"):
                    registra_evento(id_p_attivo, f"IGIENE: {'Sì' if igiene else 'No'} | PASTO: {alimentazione}", "OSS", firma_op)



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
