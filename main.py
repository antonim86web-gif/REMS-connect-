import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

# --- CONFIGURAZIONE PROFESSIONALE ---
st.set_page_config(page_title="SISTEMA GESTIONALE REMS v29.0", layout="wide", page_icon="🏥")

# --- MOTORE DATABASE (STRUTTURA BLINDATA) ---
def init_db():
    conn = sqlite3.connect('rems_final_v12.db', check_same_thread=False)
    c = conn.cursor()
    # Tabella Diario: Estesa con colonna Categoria per filtri professionali
    c.execute('''CREATE TABLE IF NOT EXISTS diario 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  data TEXT, 
                  paziente TEXT, 
                  nota TEXT, 
                  autore TEXT, 
                  ruolo_autore TEXT,
                  categoria TEXT)''')
    # Tabella Stanze: Per la Mappa Visiva
    c.execute('''CREATE TABLE IF NOT EXISTS stanze 
                 (paziente TEXT PRIMARY KEY, stanza TEXT, letto TEXT, data_aggiornamento TEXT)''')
    # Tabella Appuntamenti
    c.execute('''CREATE TABLE IF NOT EXISTS appuntamenti 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, ora TEXT, paziente TEXT, impegno TEXT, stato TEXT)''')
    # Tabella Cassa (Esempio per integrazione)
    c.execute('''CREATE TABLE IF NOT EXISTS cassa 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, paziente TEXT, operazione TEXT, importo REAL, data TEXT)''')
    conn.commit()
    return conn

conn = init_db()

# --- GESTIONE SESSIONE ---
if 'ruolo' not in st.session_state:
    st.session_state.ruolo = None

# --- FUNZIONI DI SERVIZIO (OPERAZIONI DB) ---
def salva_nota(paziente, nota, categoria):
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    c = conn.cursor()
    c.execute("INSERT INTO diario (data, paziente, nota, autore, ruolo_autore, categoria) VALUES (?,?,?,?,?,?)",
              (now, paziente, nota, "Operatore", st.session_state.ruolo, categoria))
    conn.commit()

# --- LOGIN MULTI-PROFILO ---
if st.session_state.ruolo is None:
    st.title("🛡️ Accesso Protetto REMS v29.0")
    with st.container():
        col_l, col_r = st.columns(2)
        with col_l:
            ruolo_scelto = st.selectbox("Seleziona Profilo Professionale", 
                                       ["Medico", "Infermiere", "OSS", "Educatore", 
                                        "Psicologo", "Assistente Sociale", "OPSI", "Admin"])
        with col_r:
            password = st.text_input("Inserisci Password", type="password")
        
        if st.button("ENTRA NEL SISTEMA"):
            if password == "rems2024": # Mantengo la tua logica di accesso
                st.session_state.ruolo = ruolo_scelto
                st.rerun()
            else:
                st.error("Credenziali non valide.")
    st.stop()

# --- INTERFACCIA PRINCIPALE ---
st.sidebar.header(f"✨ Benvenuto, {st.session_state.ruolo}")
scelta = st.sidebar.radio("NAVIGAZIONE", 
                         ["MAPPA VISIVA LETTI", "DIARIO CLINICO INTEGRATO", "AGENDA APPUNTAMENTI", "CASSA & FONDI", "PANNELLO ADMIN"])

lista_pazienti = ["Rossi Mario", "Bianchi Luigi", "Verdi Giuseppe", "Esposito Ciro", "Russo Antonio", "Fumagalli Luca"]

# --- 1. MODULO MAPPA VISIVA (Potere di modifica a tutti) ---
if scelta == "MAPPA VISIVA LETTI":
    st.header("📍 Gestione Posti Letto e Stanze")
    
    col_map1, col_map2 = st.columns([1, 2])
    
    with col_map1:
        st.subheader("🔄 Aggiorna Posizione")
        pax = st.selectbox("Paziente", lista_pazienti)
        stz = st.selectbox("Assegna Stanza", [f"Stanza {i}" for i in range(101, 115)])
        letto = st.radio("Letto", ["A (Finestra)", "B (Porta)"], horizontal=True)
        
        if st.button("CONFERMA SPOSTAMENTO"):
            now_t = datetime.now().strftime("%d/%m/%Y %H:%M")
            conn.execute("INSERT OR REPLACE INTO stanze (paziente, stanza, letto, data_aggiornamento) VALUES (?,?,?,?)",
                         (pax, stz, letto, now_t))
            conn.commit()
            st.success(f"Spostamento di {pax} registrato.")

    with col_map2:
        df_s = pd.read_sql("SELECT * FROM stanze", conn)
        if not df_s.empty:
            fig = px.bar(df_s, x="stanza", y="letto", color="paziente", title="Distribuzione Occupazione",
                         hover_data=["data_aggiornamento"], barmode="group")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Mappa vuota. Inizia ad assegnare i posti letto.")

# --- 2. DIARIO CLINICO (AREE DEDICATE + ADMIN) ---
elif scelta == "DIARIO CLINICO INTEGRATO":
    st.header("📖 Diario Clinico Professionale")

    # --- ESPANSIONE PER LE NUOVE FIGURE ---
    
    # SEZIONE PSICOLOGO
    if st.session_state.ruolo in ["Psicologo", "Admin"]:
        with st.expander("🧠 AREA PSICOLOGIA - Colloqui e Test", expanded=(st.session_state.ruolo=="Psicologo")):
            c_psi1, c_psi2 = st.columns(2)
            p_pax = c_psi1.selectbox("Seleziona Paziente", lista_pazienti, key="psi_p")
            p_att = c_psi2.selectbox("Attività", ["Colloquio Supporto", "Somministrazione MMPI-2", "Test di Rorschach", "Relazione Clinica"])
            p_nota = st.text_area("Annotazioni Psicologiche Dettagliate", height=150)
            if st.button("ARCHIVIA NOTA PSICOLOGICA"):
                salva_nota(p_pax, f"[{p_att}] {p_nota}", "PSICOLOGIA")
                st.success("Nota salvata nel registro clinico.")

    # SEZIONE ASSISTENTE SOCIALE
    if st.session_state.ruolo in ["Assistente Sociale", "Admin"]:
        with st.expander("🤝 AREA SOCIALE - Progetti e Territorio", expanded=(st.session_state.ruolo=="Assistente Sociale")):
            c_soc1, c_soc2 = st.columns(2)
            s_pax = c_soc1.selectbox("Seleziona Paziente", lista_pazienti, key="soc_p")
            s_ambito = c_soc2.selectbox("Ambito", ["Rapporto UEPE", "Contatto Famiglia", "Ricerca Struttura", "Licenza Esperimento"])
            s_ente = st.text_input("Ente Coinvolto (Comune, Tribunale, Sert)")
            s_nota = st.text_area("Dettagli Intervento Sociale")
            if st.button("REGISTRA INTERVENTO SOCIALE"):
                salva_nota(s_pax, f"Ambito: {s_ambito} | Ente: {s_ente} | Nota: {s_nota}", "SOCIALE")
                st.success("Dati sociali aggiornati.")

    # SEZIONE OPSI (SICUREZZA INTERNA)
    if st.session_state.ruolo in ["OPSI", "Admin"]:
        with st.expander("🛡️ AREA OPSI - Sicurezza e Vigilanza", expanded=(st.session_state.ruolo=="OPSI")):
            c_opsi1, c_opsi2 = st.columns(2)
            o_pax = c_opsi1.selectbox("Paziente (se coinvolto)", ["Controllo Generale"] + lista_pazienti, key="opsi_p")
            o_tipo = c_opsi2.selectbox("Tipo Intervento", ["Ispezione Camere", "Ronda Perimetrale", "Rapporto Disciplinare", "Controllo Barriere"])
            o_allerta = st.select_slider("Livello di Criticità", options=["BASSO", "MEDIO", "ELEVATO", "CRITICO"])
            o_nota = st.text_area("Relazione di Sicurezza OPSI")
            if st.button("INVIA REPORT SICUREZZA"):
                salva_nota(o_pax, f"TIPO: {o_tipo} | ALLERTA: {o_allerta} | {o_nota}", "SICUREZZA")
                st.warning("Report di sicurezza archiviato.")

    # --- VISUALIZZAZIONE STORICO (FILTRAGGIO AVANZATO) ---
    st.markdown("---")
    st.subheader("🕒 Cronologia Interventi del Reparto")
    filtro_cat = st.multiselect("Mostra solo:", 
                               ["MEDICA", "INFERMIERISTICA", "PSICOLOGIA", "SOCIALE", "SICUREZZA"],
                               default=["MEDICA", "INFERMIERISTICA", "PSICOLOGIA", "SOCIALE", "SICUREZZA"])
    
    query = f"SELECT data, paziente, categoria, nota, ruolo_autore FROM diario WHERE categoria IN ({','.join(['?']*len(filtro_cat))}) ORDER BY id DESC"
    df_d = pd.read_sql(query, conn, params=filtro_cat)
    
    for index, row in df_d.iterrows():
        with st.chat_message("user" if row['categoria'] == 'SICUREZZA' else "assistant"):
            st.write(f"**{row['data']}** - **{row['paziente']}** ({row['categoria']})")
            st.info(row['nota'])
            st.caption(f"Inserito da: {row['ruolo_autore']}")

# --- 3. AGENDA APPUNTAMENTI ---
elif scelta == "AGENDA APPUNTAMENTI":
    st.header("📅 Agenda di Reparto")
    with st.form("form_app"):
        col_a1, col_a2, col_a3 = st.columns(3)
        data_a = col_a1.date_input("Data Evento")
        ora_a = col_a2.time_input("Ora")
        pax_a = col_a3.selectbox("Paziente", lista_pazienti)
        motivo = st.text_input("Oggetto (Udienza, Visita specialistica, Colloquio)")
        if st.form_submit_button("PROGRAMMA EVENTO"):
            conn.execute("INSERT INTO appuntamenti (data, ora, paziente, impegno, stato) VALUES (?,?,?,?,?)",
                         (str(data_a), str(ora_a), pax_a, motivo, "Programmato"))
            conn.commit()
            st.success("Evento aggiunto in agenda.")

    df_app = pd.read_sql("SELECT data, ora, paziente, impegno FROM appuntamenti ORDER BY data, ora", conn)
    st.dataframe(df_app, use_container_width=True)

# --- 4. PANNELLO ADMIN (CABINA DI REGIA) ---
elif scelta == "PANNELLO ADMIN":
    if st.session_state.ruolo == "Admin":
        st.header("👑 Controllo Totale Amministratore")
        
        tab1, tab2 = st.tabs(["Statistiche Interventi", "Gestione Database"])
        
        with tab1:
            st.subheader("Analisi Attività per Ruolo")
            df_stats = pd.read_sql("SELECT ruolo_autore, COUNT(*) as n_interventi FROM diario GROUP BY ruolo_autore", conn)
            fig_stats = px.pie(df_stats, values='n_interventi', names='ruolo_autore', hole=.3)
            st.plotly_chart(fig_stats)
            
        with tab2:
            st.subheader("Manutenzione Dati")
            if st.button("SCARICA BACKUP EXCEL"):
                df_all = pd.read_sql("SELECT * FROM diario", conn)
                df_all.to_excel("backup_rems.xlsx")
                st.success("Backup generato con successo.")
    else:
        st.error("Accesso negato. Questa sezione è riservata esclusivamente all'Admin.")

# --- FOOTER ---
st.sidebar.markdown("---")
if st.sidebar.button("LOGOUT"):
    st.session_state.ruolo = None
    st.rerun()
