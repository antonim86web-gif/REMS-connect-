import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- DATABASE ENGINE ---
def init_db():
    conn = sqlite3.connect('rems_connect_v1.db')
    c = conn.cursor()
    # Tabella Pazienti
    c.execute('''CREATE TABLE IF NOT EXISTS pazienti 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT)''')
    # Tabella Eventi (Umore + Note)
    c.execute('''CREATE TABLE IF NOT EXISTS eventi 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  p_id INTEGER, 
                  umore TEXT, 
                  nota TEXT, 
                  data TEXT,
                  FOREIGN KEY(p_id) REFERENCES pazienti(id))''')
    conn.commit()
    conn.close()

def db_query(query, params=(), commit=False):
    conn = sqlite3.connect('rems_connect_v1.db')
    c = conn.cursor()
    c.execute(query, params)
    if commit:
        conn.commit()
        res = None
    else:
        res = c.fetchall()
    conn.close()
    return res

# --- LOGICA APP ---
init_db()
st.set_page_config(page_title="REMS Connect Pro", layout="wide")

# Configurazione Stati
stati_config = {
    "Stabile": {"color": "green", "icon": "🙂", "punti": 3},
    "Deflesso": {"color": "orange", "icon": "😐", "punti": 2},
    "Cupo": {"color": "red", "icon": "☹️", "punti": 1}
}

if "auth" not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 Accesso Perito")
    if st.text_input("Codice", type="password") == "rems2026":
        if st.button("Sblocca"):
            st.session_state.auth = True
            st.rerun()
else:
    menu = st.sidebar.selectbox("Menu", ["Dashboard Umore", "Anagrafica & Note", "Analisi Storica"])

    # --- 1. DASHBOARD UMORE ---
    if menu == "Dashboard Umore":
        st.title("📊 Stato Attuale")
        pazienti = db_query("SELECT * FROM pazienti ORDER BY nome")
        
        for p in pazienti:
            p_id, p_nome = p
            # Prendi l'ultimo evento registrato
            ultimo = db_query("SELECT umore, data FROM eventi WHERE p_id=? ORDER BY id DESC LIMIT 1", (p_id,))
            u_attuale = ultimo[0][0] if ultimo else "Stabile"
            u_data = ultimo[0][1] if ultimo else "Nessun dato"
            
            cfg = stati_config[u_attuale]
            
            with st.expander(f" {cfg['icon']} {p_nome} (Ultimo: {u_data})"):
                col1, col2 = st.columns([1, 2])
                with col1:
                    nuovo_u = st.select_slider(f"Aggiorna Umore", options=list(stati_config.keys()), value=u_attuale, key=f"sl_{p_id}")
                with col2:
                    nuova_nota = st.text_area("Inserisci Nota Clinica", key=f"nt_{p_id}", placeholder="Scrivi qui osservazioni...")
                
                if st.button("Registra Aggiornamento", key=f"btn_{p_id}"):
                    ora = datetime.now().strftime("%d/%m/%Y %H:%M")
                    db_query("INSERT INTO eventi (p_id, umore, nota, data) VALUES (?,?,?,?)", 
                             (p_id, nuovo_u, nuova_nota, ora), commit=True)
                    st.success("Registrato!")
                    st.rerun()

        # --- 2. ANAGRAFICA & NOTE ---
    elif menu == "Anagrafica & Note":
        st.title("📝 Gestione Documentale")
        with st.form("nuovo_p"):
            nome = st.text_input("Nuovo Paziente")
            if st.form_submit_button("Aggiungi"):
                db_query("INSERT INTO pazienti (nome) VALUES (?)", (nome,), commit=True)
                st.success("Paziente aggiunto!")
                st.rerun()
        
        st.divider()
        
        # Recuperiamo la lista nomi
        lista_nomi = [p[1] for p in db_query("SELECT nome FROM pazienti")]
        
        if not lista_nomi:
            st.warning("Nessun paziente in archivio. Aggiungine uno sopra.")
        else:
            p_scelto = st.selectbox("Seleziona Paziente per vedere le Note", lista_nomi)
            if p_scelto:
                pid_res = db_query("SELECT id FROM pazienti WHERE nome=?", (p_scelto,))
                if pid_res:
                    pid = pid_res[0][0]
                    eventi = db_query("SELECT data, umore, nota FROM eventi WHERE p_id=? ORDER BY id DESC", (pid,))
                    if not eventi:
                        st.write("Nessuna nota presente per questo paziente.")
                    for e in eventi:
                        st.info(f"**Data:** {e[0]} | **Stato:** {e[1]}")
                        st.write(f"✍️ {e[2] if e[2] else 'Nessuna nota inserita.'}")
                        st.divider()


    # --- 3. ANALISI STORICA ---
    elif menu == "Analisi Storica":
        st.title("📈 Andamento Temporale")
        # Qui potremmo inserire grafici usando st.line_chart
        st.write("In questa sezione potremo visualizzare i grafici di andamento per ogni paziente.")
        # Esempio rapido dati
        raw_data = db_query("SELECT p.nome, e.umore, e.data FROM eventi e JOIN pazienti p ON e.p_id = p.id")
        if raw_data:
            df = pd.DataFrame(raw_data, columns=['Paziente', 'Umore', 'Data'])
            st.table(df)
