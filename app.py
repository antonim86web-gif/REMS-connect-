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
        
        u_data = st.session_state.user_data
        ruolo_utente = u_data.get('ruolo', 'Nessuno').strip()
        
        st.write(f"👤 **Op:** {u_data.get('username')}")
        st.write(f"🆔 **Ruolo:** {ruolo_utente}")
        st.divider()

        # Menu principale
        voci_menu = ["📋 Monitoraggio & Diario", "💉 Modulo Equipe", "🗓️ Agenda Uscite", "🛏️ Mappa Letti", "📖 Diario di Bordo"]
        if ruolo_utente == "Admin":
            voci_menu.append("⚙️ Pannello Admin")

        scelta_menu = st.radio("Seleziona Area:", voci_menu)
        st.divider()

        # SELEZIONE PAZIENTE (Carica i nomi da Supabase)
        res_p = supabase.table("pazienti").select("id, nome").execute()
        lista_p = {p['nome']: p['id'] for p in res_p.data}
        
        nome_sel = st.selectbox("🎯 Seleziona Paziente:", ["--"] + list(lista_p.keys()), key="sidebar_paz")
        
        if nome_sel != "--":
            paziente_attivo = nome_sel
            id_p_attivo = lista_p[nome_sel]
        else:
            paziente_attivo = None
            id_p_attivo = None

        st.divider()
        if st.button("🚪 Esci dal Sistema", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()

    # --- RESTO DELLA TUA SIDEBAR (Menu e Selezione Paziente) ---
voci_menu = ["📋 Monitoraggio & Diario", "💉 Modulo Equipe", "🗓️ Agenda Uscite", "🛏️ Mappa Letti", "📖 Diario di Bordo"]
if ruolo_utente == "Admin":
    voci_menu.append("⚙️ Pannello Admin")

    scelta_menu = st.radio("Seleziona Area:", voci_menu)
    st.divider()

    # Selezione Paziente (necessaria per far apparire i moduli nel Blocco 3)
    res_p = supabase.table("pazienti").select("id, nome").execute()
    lista_pazienti = {p['nome']: p['id'] for p in res_p.data}
    nome_sel = st.selectbox("Seleziona Paziente:", ["--"] + list(lista_pazienti.keys()))
    
    if nome_sel != "--":
        paziente_attivo = nome_sel
        id_p_attivo = lista_pazienti[nome_sel]
    else:
        paziente_attivo = None
        id_p_attivo = None

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
            

# =========================================================
# BLOCCO 3: MODULO EQUIPE (Allineato a scelta_menu)
# =========================================================

# Usiamo "scelta_menu" perché è così che l'hai definita nella tua sidebar
if scelta_menu == "💉 Modulo Equipe":
    st.title("💉 Modulo Operativo Equipe Multidisciplinare")
    
    # Verifica selezione paziente (Assicurati che id_p_attivo sia definito nel Blocco 2)
    if not paziente_attivo:
        st.warning("⚠️ Seleziona un paziente nella Sidebar per operare.")
    else:
        st.subheader(f"Paziente in carico: {paziente_attivo}")
        
        # --- 1. AREA PSICHIATRA ---
        if ruolo_utente in ["Admin", "Psichiatra"]:
            with st.expander("🩺 AREA PSICHIATRA - Gestione Clinica", expanded=True):
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.write("### 💊 Prescrizione Terapia")
                    f_nome = st.text_input("Farmaco", key="f_nome")
                    f_fascia = st.selectbox("Fascia Oraria", ["Mattina (08-13)", "Pomeriggio (14-21)", "Al bisogno (H24)"], key="f_fascia")
                    f_dose = st.text_input("Posologia", key="f_dose")
                    if st.button("Conferma Prescrizione"):
                        supabase.table("terapie").insert({
                            "id_paziente": id_p_attivo, "farmaco": f_nome, 
                            "fascia": f_fascia, "dose": f_dose, "medico": st.session_state.user_data['username']
                        }).execute()
                        registra_evento(id_p_attivo, f"Prescritto {f_nome} ({f_fascia})", "Psichiatra", "[PRESC]", st.session_state.user_data['username'])
                        st.success("Terapia registrata correttamente.")
                with col2:
                    st.write("### 📊 Monitoraggio")
                    # Tabella sola lettura per il medico (prende i dati dalle somministrazioni infermieristiche)
                    try:
                        storico_t = supabase.table("somministrazioni").select("*").eq("id_paziente", id_p_attivo).execute()
                        if storico_t.data:
                            df_s = pd.DataFrame(storico_t.data)
                            st.dataframe(df_s[['created_at', 'farmaco', 'stato', 'operatore']], use_container_width=True)
                        else:
                            st.info("Nessuna somministrazione registrata.")
                    except:
                        st.write("Dati monitoraggio non disponibili.")

                st.divider()
                cons_medica = st.text_area("Inserisci Consegna Medica o Richiesta Esami", key="cons_med")
                c_m1, c_m2, c_m3 = st.columns(3)
                if c_m1.button("📌 Invia Consegna"): 
                    registra_evento(id_p_attivo, cons_medica, "Psichiatra", "[CONSEGNA MED]", st.session_state.user_data['username'])
                if c_m2.button("🔬 Richiedi Esami"): 
                    registra_evento(id_p_attivo, f"Richiesti esami: {cons_medica}", "Psichiatra", "[ESAMI]", st.session_state.user_data['username'])
                if c_m3.button("🤖 Relazione IA"): 
                    st.info("Funzione IA Groq in attivazione...")

        # --- 2. AREA INFERMIERE ---
        if ruolo_utente in ["Admin", "Infermiere"]:
            with st.expander("💉 AREA INFERMIERISTICA - Somministrazione", expanded=True):
                st.write("### 🗓️ Calendario Dinamico Terapie")
                # Recupera le terapie prescritte dai medici
                terapie_attive = supabase.table("terapie").select("*").eq("id_paziente", id_p_attivo).execute()
                
                if not terapie_attive.data:
                    st.info("Nessuna terapia prescritta per questo paziente.")
                else:
                    for t in terapie_attive.data:
                        col_t1, col_t2, col_t3 = st.columns([2, 1, 1])
                        col_t1.write(f"**{t['farmaco']}** ({t['fascia']})")
                        # Tasto ASSUNTA
                        if col_t2.button(f"✅ A", key=f"A_{t['id']}"):
                            supabase.table("somministrazioni").insert({
                                "id_paziente": id_p_attivo, "farmaco": t['farmaco'], "stato": "A", "operatore": st.session_state.user_data['username']
                            }).execute()
                            registra_evento(id_p_attivo, f"Assunta: {t['farmaco']}", "Infermiere", "[✅ ASSUNTO]", st.session_state.user_data['username'])
                        # Tasto RIFIUTATA
                        if col_t3.button(f"❌ R", key=f"R_{t['id']}"):
                            motivo = st.text_input(f"Motivo R per {t['farmaco']}", key=f"mot_{t['id']}")
                            if motivo:
                                supabase.table("somministrazioni").insert({
                                    "id_paziente": id_p_attivo, "farmaco": t['farmaco'], "stato": "R", "operatore": st.session_state.user_data['username'], "note": motivo
                                }).execute()
                                registra_evento(id_p_attivo, f"Rifiutata: {t['farmaco']} - Motivo: {motivo}", "Infermiere", "[❌ RIFIUTATO]", st.session_state.user_data['username'])
                                st.warning("Rifiuto registrato.")

                st.divider()
                st.write("### 📊 Parametri & Consegne")
                p1, p2, p3 = st.columns(3)
                pa = p1.text_input("Pressione A.", key="pa_val")
                fc = p2.text_input("Freq. Card.", key="fc_val")
                glic = p3.text_input("Glicemia", key="glic_val")
                cons_inf = st.text_area("Relazione Infermieristica di turno", key="c_inf")
                if st.button("💾 Salva Monitoraggio"):
                    registra_evento(id_p_attivo, f"PA: {pa}, FC: {fc}, Glic: {glic} | {cons_inf}", "Infermiere", "[PARAMETRI]", st.session_state.user_data['username'])

        # --- 3. AREA EDUCATORE ---
        if ruolo_utente in ["Admin", "Educatore"]:
            with st.expander("🎨 AREA EDUCATIVA - Cassa e Tabacco", expanded=False):
                st.write("### 💰 Gestione Cassa")
                c1, c2, c3 = st.columns(3)
                tipo_c = c1.selectbox("Movimento", ["Entrata", "Uscita"], key="c_tipo")
                importo_c = c2.number_input("Euro €", step=0.5, key="c_importo")
                causale_c = c3.text_input("Causale", key="c_causale")
                if st.button("🧧 Registra Cassa"):
                    supabase.table("cassa").insert({
                        "id_paziente": id_p_attivo, "tipo": tipo_c, "importo": importo_c, "causale": causale_c, "operatore": st.session_state.user_data['username']
                    }).execute()
                    registra_evento(id_p_attivo, f"CASSA {tipo_c}: {importo_c}€ - {causale_c}", "Educatore", "[CASSA]", st.session_state.user_data['username'])
                    st.success("Movimento contabile salvato.")
                
                st.divider()
                st.write("### 🚬 Consegna Tabacco")
                qty_tab = st.number_input("Quantità sigarette/tabacco", step=1, key="tab_qty")
                cons_edu = st.text_area("Consegna Educativa / Note Attività", key="c_edu")
                if st.button("💾 Salva Report Educatore"):
                    registra_evento(id_p_attivo, f"Tabacco: {qty_tab} | {cons_edu}", "Educatore", "[TABACCO]", st.session_state.user_data['username'])

        # --- 4. AREA PSICOLOGO / SOCIALE ---
        if ruolo_utente in ["Admin", "Psicologo", "Sociale"]:
            with st.expander("🧠 AREA PSICO-SOCIALE", expanded=False):
                st.write("### 📝 Relazioni e Colloqui")
                nota_ps = st.text_area("Note colloquio / Rapporti UEPE-Tribunale", key="n_ps")
                tag_ps = "[COLLOQUIO]" if ruolo_utente == "Psicologo" else "[ENTI]"
                if st.button("💾 Salva Nota"):
                    registra_evento(id_p_attivo, nota_ps, ruolo_utente, tag_ps, st.session_state.user_data['username'])

# --- 5. CONSEGNE GENERALI (Sempre visibili in fondo al modulo per i ruoli operativi) ---
if scelta_menu == "💉 Modulo Equipe" and ruolo_utente in ["Admin", "OSS", "Opsi"]:
    st.divider()
    st.subheader("📢 Consegne Generali di Reparto")
    nota_gen = st.text_area("Inserisci nota logistica, di sicurezza o igiene ambientale", key="n_gen")
    if st.button("💾 Salva Consegna Generale"):
        tag_gen = "[OPSI-GEN]" if ruolo_utente == "Opsi" else "[GENERALE]"
        registra_evento(0, nota_gen, ruolo_utente, tag_gen, st.session_state.user_data['username'])
        


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
