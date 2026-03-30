import streamlit as st
import sqlite3
from datetime import datetime

# --- 1. CONFIGURAZIONE E STILE ---
st.set_page_config(page_title="REMS Connect", page_icon="🏥", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    /* PULSANTE MENU SEMPRE ATTIVO */
    button[kind="headerNoSpacing"] {
        display: block !important; position: fixed !important; top: 15px !important; left: 15px !important;
        background-color: #2563eb !important; color: white !important; width: 55px !important; height: 55px !important;
        border-radius: 50% !important; z-index: 999999 !important; border: 2px solid white !important;
    }
    html, body, [class*="css"] { font-size: 19px !important; background-color: #f1f5f9; }
    [data-testid="stSidebar"] { background-color: #1e293b !important; min-width: 280px !important; }
    [data-testid="stSidebar"] * { color: white !important; }
    .stButton>button { height: 4rem !important; font-size: 1.2rem !important; border-radius: 12px !important; background-color: #2563eb !important; color: white !important; font-weight: bold !important; width: 100%; }
    
    /* CARD DIARIO CON COLORI DI EMERGENZA */
    .nota-card { padding: 12px; margin-bottom: 10px; border-radius: 8px; color: #1e293b; border-left: 6px solid #cbd5e1; background-color: white; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .nota-Psichiatra { border-left-color: #ef4444 !important; background-color: #fef2f2 !important; }
    .nota-Infermiere { border-left-color: #3b82f6 !important; background-color: #eff6ff !important; }
    .nota-OSS { border-left-color: #8b5cf6 !important; background-color: #f5f3ff !important; }
    .nota-Psicologo { border-left-color: #10b981 !important; background-color: #ecfdf5 !important; }
    .nota-Educatore { border-left-color: #f59e0b !important; background-color: #fffbeb !important; }
    
    #MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# --- 2. DATABASE ULTRA-RESISTENTE ---
def db_query(query, params=(), commit=False):
    conn = sqlite3.connect("rems_connect_v1.db", check_same_thread=False)
    cur = conn.cursor()
    # Creazione tabelle base
    cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY, nome TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER PRIMARY KEY, p_id INTEGER, data TEXT, umore TEXT, nota TEXT, ruolo TEXT, operatore TEXT)")
    
    # Check colonne mancanti (per evitare che il diario sparisca)
    columns = [info[1] for info in cur.execute("PRAGMA table_info(eventi)").fetchall()]
    if "ruolo" not in columns:
        cur.execute("ALTER TABLE eventi ADD COLUMN ruolo TEXT DEFAULT 'Nota'")
    if "operatore" not in columns:
        cur.execute("ALTER TABLE eventi ADD COLUMN operatore TEXT DEFAULT 'Anonimo'")
    
    cur.execute(query, params)
    res = cur.fetchall()
    if commit: conn.commit()
    conn.close()
    return res

# --- 3. ACCESSO ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.title("🏥 REMS Connect")
    pwd = st.text_input("Codice Identificativo", type="password")
    if st.button("ENTRA"):
        if pwd == "rems2026": st.session_state.auth = True; st.rerun()
    st.stop()

# --- 4. NAVIGAZIONE ---
st.sidebar.title("REMS Connect")
menu = st.sidebar.radio("MENU", ["Monitoraggio", "Gestione"])

# --- 5. MONITORAGGIO ---
if menu == "Monitoraggio":
    st.title("Diario Clinico")
    pazienti = db_query("SELECT id, nome FROM pazienti ORDER BY nome")
    
    if not pazienti:
        st.info("Nessun paziente. Vai in 'Gestione' per aggiungerne uno.")

    for p_id, nome in pazienti:
        with st.expander(f"👤 {nome.upper()}"):
            # Setup reset campi
            if f"r_{p_id}" not in st.session_state: st.session_state[f"r_{p_id}"] = 0
            
            # Input
            c1, c2 = st.columns(2)
            with c1: ruolo = st.selectbox("Ruolo:", ["Psichiatra", "Infermiere", "OSS", "Psicologo", "Educatore"], key=f"sel_{p_id}_{st.session_state[f'r_{p_id}']}")
            with c2: operatore = st.text_input("Tuo Nome:", key=f"op_{p_id}_{st.session_state[f'r_{p_id}']}", placeholder="Firma")
            
            umore = st.select_slider("Stato:", options=["Cupo", "Deflesso", "Stabile", "Agitato"], value="Stabile", key=f"u_{p_id}_{st.session_state[f'r_{p_id}']}")
            nota = st.text_area("Nota di Turno:", key=f"n_{p_id}_{st.session_state[f'r_{p_id}']}", height=100)
            
            if st.button("SALVA NOTA", key=f"btn_{p_id}"):
                if nota and operatore:
                    dt = datetime.now().strftime("%Y-%m-%d %H:%M")
                    db_query("INSERT INTO eventi (p_id, data, umore, nota, ruolo, operatore) VALUES (?,?,?,?,?,?)", 
                             (p_id, dt, umore, nota, ruolo, operatore), commit=True)
                    st.session_state[f"r_{p_id}"] += 1
                    st.rerun()
                else:
                    st.error("Inserisci Nome e Nota!")

            st.divider()
            
            # LETTURA DIARIO (Corretta per evitare sparizioni)
            eventi = db_query("SELECT data, umore, nota, ruolo, operatore FROM eventi WHERE p_id=? ORDER BY id DESC LIMIT 30", (p_id,))
            
            if not eventi:
                st.write("Ancora nessuna nota per questo paziente.")
            
            for e in eventi:
                # Pulizia dati per il CSS
                raw_ruolo = str(e[3]) if e[3] else "Nota"
                r_class = f"nota-{raw_ruolo.strip()}"
                f_operatore = str(e[4]) if e[4] else "Operatore"
                f_data = str(e[0])
                
                st.markdown(f"""
                <div class="nota-card {r_class}">
                    <div style="font-size:0.8rem; color: #64748b; margin-bottom: 5px;">
                        <b>{f_data}</b> | <b>{raw_ruolo.upper()}</b> | {f_operatore}
                    </div>
                    <b>Stato: {e[1]}</b><br>
                    <div style="margin-top:5px; line-height: 1.4;">{e[2]}</div>
                </div>
                """, unsafe_allow_html=True)

# --- 6. GESTIONE ---
elif menu == "Gestione":
    st.title("Anagrafica")
    nuovo = st.text_input("Nome e Cognome Paziente")
    if st.button("AGGIUNGI"):
        if nuovo: db_query("INSERT INTO pazienti (nome) VALUES (?)", (nuovo,), commit=True); st.rerun()
    st.divider()
    p_list = db_query("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_list:
        p_del = st.selectbox("Seleziona per eliminare", [p[1] for p in p_list])
        if st.button("ELIMINA"):
            db_query("DELETE FROM pazienti WHERE nome=?", (p_del,), commit=True); st.rerun()
