import streamlit as st
import sqlite3
from datetime import datetime

# --- 1. CONFIGURAZIONE E STILE ---
st.set_page_config(page_title="REMS Connect", page_icon="🏥", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    /* PULSANTE MENU FISSO */
    button[kind="headerNoSpacing"] {
        display: block !important; position: fixed !important; top: 15px !important; left: 15px !important;
        background-color: #2563eb !important; color: white !important; width: 55px !important; height: 55px !important;
        border-radius: 50% !important; z-index: 999999 !important; border: 2px solid white !important;
    }
    html, body, [class*="css"] { font-size: 19px !important; background-color: #f1f5f9; }
    [data-testid="stSidebar"] { background-color: #1e293b !important; min-width: 280px !important; }
    [data-testid="stSidebar"] * { color: white !important; }
    .stButton>button { height: 4.2rem !important; font-size: 1.3rem !important; border-radius: 15px !important; background-color: #2563eb !important; color: white !important; font-weight: bold !important; }
    .stExpander { border: 2px solid #cbd5e1 !important; border-radius: 15px !important; background-color: white !important; margin-top: 10px !important; }
    
    /* COLORI PER RUOLI */
    .nota-Psichiatra { border-left: 6px solid #ef4444; background-color: #fef2f2; }
    .nota-Infermiere { border-left: 6px solid #3b82f6; background-color: #eff6ff; }
    .nota-Psicologo { border-left: 6px solid #10b981; background-color: #ecfdf5; }
    .nota-Educatore { border-left: 6px solid #f59e0b; background-color: #fffbeb; }
    .nota-OSS { border-left: 6px solid #8b5cf6; background-color: #f5f3ff; }
    
    .nota-card { padding: 15px; margin-bottom: 12px; border-radius: 8px; color: #1e293b; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    #MainMenu, footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# --- 2. DATABASE (Aggiunto campo 'operatore') ---
def db_query(query, params=(), commit=False):
    conn = sqlite3.connect("rems_connect_v1.db")
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY, nome TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER PRIMARY KEY, p_id INTEGER, data TEXT, umore TEXT, nota TEXT, ruolo TEXT, operatore TEXT)")
    
    # Aggiornamento automatico colonne se necessario
    try: cur.execute("ALTER TABLE eventi ADD COLUMN ruolo TEXT")
    except: pass
    try: cur.execute("ALTER TABLE eventi ADD COLUMN operatore TEXT")
    except: pass
    
    cur.execute(query, params)
    res = cur.fetchall()
    if commit: conn.commit()
    conn.close()
    return res

# --- 3. ACCESSO ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.title("🏥 REMS Connect")
    pwd = st.text_input("Codice Struttura", type="password")
    if st.button("ACCEDI"):
        if pwd == "rems2026": st.session_state.auth = True; st.rerun()
    st.stop()

# --- 4. NAVIGAZIONE ---
st.sidebar.title("REMS Connect")
menu = st.sidebar.radio("VAI A:", ["📊 MONITORAGGIO", "⚙️ GESTIONE"])

# --- 5. MONITORAGGIO ---
if menu == "📊 MONITORAGGIO":
    st.title("Equipe REMS")
    pazienti = db_query("SELECT id, nome FROM pazienti ORDER BY nome")
    
    for p_id, nome in pazienti:
        with st.expander(f"👤 {nome.upper()}"):
            st.subheader("Registrazione Turno")
            
            c1, c2 = st.columns(2)
            with c1:
                ruolo = st.selectbox("Ruolo:", ["Psichiatra", "Infermiere", "OSS", "Psicologo", "Educatore"], key=f"r_{p_id}")
            with c2:
                operatore = st.text_input("Nome Operatore:", key=f"op_{p_id}", placeholder="es. Rossi M.")
            
            umore = st.select_slider("Stato del Paziente", options=["Cupo", "Deflesso", "Stabile", "Agitato"], value="Stabile", key=f"u_{p_id}")
            nota = st.text_area("Note e Osservazioni", key=f"n_{p_id}", height=120)
            
            if st.button("SALVA NOTA", key=f"b_{p_id}"):
                if nota and operatore:
                    dt = datetime.now().strftime("%d/%m/%Y %H:%M")
                    db_query("INSERT INTO eventi (p_id, data, umore, nota, ruolo, operatore) VALUES (?,?,?,?,?,?)", 
                             (p_id, dt, umore, nota, ruolo, operatore), commit=True)
                    st.success("Registrato!")
                    st.rerun()
                elif not operatore:
                    st.error("Inserisci il tuo nome (Firma Operatore)")
            
            st.divider()
            st.subheader("Diario Clinico Recente")
            # Carichiamo anche il campo operatore dal database
            eventi = db_query("SELECT data, umore, nota, ruolo, operatore FROM eventi WHERE p_id=? ORDER BY id DESC LIMIT 15", (p_id,))
            for e in eventi:
                r_style = f"nota-{e[3].replace(' ', '')}" if e[3] else ""
                st.markdown(f"""
                <div class="nota-card {r_style}">
                    <div style="display:flex; justify-content: space-between; font-size: 0.8rem; color: #64748b;">
                        <b>{e[0]}</b>
                        <b style="text-transform: uppercase;">{e[3] if e[3] else 'N.D.'}</b>
                    </div>
                    <div style="margin: 5px 0;">Operatore: <b>{e[4] if e[4] else 'Non specificato'}</b></div>
                    <div style="font-weight: bold; font-size: 0.9rem; color: #1e293b;">Stato: {e[1]}</div>
                    <div style="margin-top:8px; border-top: 1px solid #cbd5e1; padding-top: 5px;">{e[2]}</div>
                </div>
                """, unsafe_allow_html=True)

# --- 6. GESTIONE ---
elif menu == "⚙️ GESTIONE":
    st.title("Anagrafica")
    n_paz = st.text_input("Nome e Cognome Paziente")
    if st.button("AGGIUNGI"):
        if n_paz: db_query("INSERT INTO pazienti (nome) VALUES (?)", (n_paz,), commit=True); st.rerun()
    
    st.divider()
    p_list = db_query("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_list:
        p_del = st.selectbox("Elimina", [p[1] for p in p_list])
        if st.button("RIMUOVI DEFINITIVAMENTE"):
            db_query("DELETE FROM pazienti WHERE nome=?", (p_del,), commit=True)
            st.rerun()
