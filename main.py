import streamlit as st
import sqlite3
from datetime import datetime

# --- 1. CONFIGURAZIONE E STILE ---
st.set_page_config(page_title="REMS Connect", page_icon="🏥", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    button[kind="headerNoSpacing"] {
        display: block !important; position: fixed !important; top: 15px !important; left: 15px !important;
        background-color: #2563eb !important; color: white !important; width: 55px !important; height: 55px !important;
        border-radius: 50% !important; z-index: 999999 !important; border: 2px solid white !important;
    }
    html, body, [class*="css"] { font-size: 19px !important; background-color: #f1f5f9; }
    [data-testid="stSidebar"] { background-color: #1e293b !important; min-width: 280px !important; }
    [data-testid="stSidebar"] * { color: white !important; }
    .stButton>button { height: 4.2rem !important; font-size: 1.3rem !important; border-radius: 15px !important; background-color: #2563eb !important; color: white !important; font-weight: bold !important; }
    
    /* STILI RUOLI */
    .nota-Psichiatra { border-left: 6px solid #ef4444; background-color: #fef2f2; }
    .nota-Infermiere { border-left: 6px solid #3b82f6; background-color: #eff6ff; }
    .nota-Psicologo { border-left: 6px solid #10b981; background-color: #ecfdf5; }
    .nota-Educatore { border-left: 6px solid #f59e0b; background-color: #fffbeb; }
    .nota-OSS { border-left: 6px solid #8b5cf6; background-color: #f5f3ff; }
    
    .nota-card { padding: 12px; margin-bottom: 8px; border-radius: 8px; color: #1e293b; box-shadow: 0 1px 3px rgba(0,0,0,0.1); font-size: 0.95rem; }
    .date-header { background-color: #e2e8f0; padding: 5px 15px; border-radius: 20px; font-weight: bold; color: #475569; margin: 15px 0 10px 0; display: inline-block; font-size: 0.85rem; }
    #MainMenu, footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# --- 2. DATABASE ---
def db_query(query, params=(), commit=False):
    conn = sqlite3.connect("rems_connect_v1.db")
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY, nome TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER PRIMARY KEY, p_id INTEGER, data TEXT, umore TEXT, nota TEXT, ruolo TEXT, operatore TEXT)")
    try: cur.execute("ALTER TABLE eventi ADD COLUMN ruolo TEXT"); cur.execute("ALTER TABLE eventi ADD COLUMN operatore TEXT")
    except: pass
    cur.execute(query, params)
    res = cur.fetchall()
    if commit: conn.commit()
    conn.close()
    return res

# --- 3. LOGIN ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.title("🏥 REMS Connect")
    pwd = st.text_input("Codice", type="password")
    if st.button("ACCEDI"):
        if pwd == "rems2026": st.session_state.auth = True; st.rerun()
    st.stop()

# --- 4. NAVIGAZIONE ---
st.sidebar.title("REMS Connect")
menu = st.sidebar.radio("VAI A:", ["📊 MONITORAGGIO", "⚙️ GESTIONE"])

# --- 5. MONITORAGGIO ---
if menu == "📊 MONITORAGGIO":
    st.title("Diario di Equipe")
    pazienti = db_query("SELECT id, nome FROM pazienti ORDER BY nome")
    
    for p_id, nome in pazienti:
        with st.expander(f"👤 {nome.upper()}"):
            # --- SEZIONE INSERIMENTO ---
            if f"reset_{p_id}" not in st.session_state: st.session_state[f"reset_{p_id}"] = 0
            
            c1, c2 = st.columns(2)
            with c1: ruolo = st.selectbox("Ruolo:", ["Psichiatra", "Infermiere", "OSS", "Psicologo", "Educatore"], key=f"r_{p_id}_{st.session_state[f'reset_{p_id}']}")
            with c2: operatore = st.text_input("Operatore:", key=f"op_{p_id}_{st.session_state[f'reset_{p_id}']}", placeholder="Nome Cognome")
            
            umore = st.select_slider("Stato", options=["Cupo", "Deflesso", "Stabile", "Agitato"], value="Stabile", key=f"u_{p_id}_{st.session_state[f'reset_{p_id}']}")
            nota = st.text_area("Nota", key=f"n_{p_id}_{st.session_state[f'reset_{p_id}']}", height=100)
            
            if st.button("SALVA NOTA", key=f"b_{p_id}"):
                if nota and operatore:
                    dt = datetime.now().strftime("%Y-%m-%d %H:%M") # Formato ISO per ordinamento facile
                    db_query("INSERT INTO eventi (p_id, data, umore, nota, ruolo, operatore) VALUES (?,?,?,?,?,?)", (p_id, dt, umore, nota, ruolo, operatore), commit=True)
                    st.session_state[f"reset_{p_id}"] += 1
                    st.rerun()
            
            st.divider()
            
            # --- SEZIONE DIARIO CALENDARIZZATO ---
            st.subheader("Consultazione Diario")
            
            # FILTRI RAPIDI
            col_f1, col_f2 = st.columns([1, 1])
            with col_f1:
                filtro_ruolo = st.multiselect("Filtra per Ruolo:", ["Psichiatra", "Infermiere", "OSS", "Psicologo", "Educatore"], key=f"fr_{p_id}")
            with col_f2:
                # Per ora mostriamo le ultime, ma predisposto per ricerca data
                st.write("") # Spazio vuoto per allineamento

            # Caricamento note
            query = "SELECT data, umore, nota, ruolo, operatore FROM eventi WHERE p_id=? ORDER BY data DESC"
            eventi = db_query(query, (p_id,))
            
            current_date = ""
            for e in eventi:
                # Filtro Ruolo Logic
                if filtro_ruolo and e[3] not in filtro_ruolo:
                    continue
                
                # Raggruppamento per Data
                date_str = e[0].split(" ")[0]
                time_str = e[0].split(" ")[1]
                nice_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d/%m/%Y")
                
                if nice_date != current_date:
                    st.markdown(f'<div class="date-header">📅 {nice_date}</div>', unsafe_allow_html=True)
                    current_date = nice_date
                
                r_style = f"nota-{e[3].replace(' ', '')}" if e[3] else ""
                st.markdown(f"""
                <div class="nota-card {r_style}">
                    <small><b>{time_str}</b> - {e[4]} ({e[3]})</small><br>
                    <b>Stato: {e[1]}</b><br>
                    {e[2]}
                </div>
                """, unsafe_allow_html=True)

elif menu == "⚙️ GESTIONE":
    st.title("Anagrafica")
    n_paz = st.text_input("Nuovo Paziente")
    if st.button("AGGIUNGI"):
        if n_paz: db_query("INSERT INTO pazienti (nome) VALUES (?)", (n_paz,), commit=True); st.rerun()
    st.divider()
    p_list = db_query("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_list:
        p_del = st.selectbox("Rimuovi", [p[1] for p in p_list])
        if st.button("ELIMINA"):
            db_query("DELETE FROM pazienti WHERE nome=?", (p_del,), commit=True); st.rerun()
