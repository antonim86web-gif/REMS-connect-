import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="REMS Connect PRO", page_icon="🏥", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&display=swap');
    html, body, [class*="css"] { font-size: 19px !important; background-color: #f1f5f9; }
    .rems-header {
        text-align: center;
        color: #1e3a8a;
        font-family: 'Orbitron', sans-serif;
        font-size: 3rem !important;
        font-weight: 700;
        margin-bottom: 20px;
        text-transform: uppercase;
        letter-spacing: 4px;
        text-shadow: 0 0 10px rgba(37, 99, 235, 0.2);
    }
    .stButton>button { 
        height: 3.5rem !important; 
        font-size: 1.1rem !important; 
        border-radius: 12px !important; 
        background-color: #2563eb !important; 
        color: white !important; 
        font-weight: bold !important; 
        width: 100%; 
        font-family: 'Orbitron', sans-serif;
    }
    .nota-card { padding: 12px; margin-bottom: 8px; border-radius: 8px; color: #1e293b; border-left: 6px solid #cbd5e1; background-color: #f8fafc; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
    .nota-Psichiatra { border-left-color: #ef4444 !important; }
    .nota-Infermiere { border-left-color: #3b82f6 !important; }
    .nota-OSS { border-left-color: #8b5cf6 !important; }
    .nota-Psicologo { border-left-color: #10b981 !important; }
    .nota-Educatore { border-left-color: #f59e0b !important; }
    .allerta-agitato { background-color: #fee2e2 !important; border: 2px solid #dc2626 !important; border-left: 10px solid #dc2626 !important; animation: blinker 2s linear infinite; }
    @keyframes blinker { 50% { opacity: 0.8; } }
    div[data-testid="stRadio"] > div { flex-direction: row !important; gap: 10px; }
    #MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# --- 2. DATABASE ---
def db_query(query, params=(), commit=False):
    conn = sqlite3.connect("rems_connect_v1.db", check_same_thread=False)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY, nome TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER PRIMARY KEY, p_id INTEGER, data TEXT, umore TEXT, nota TEXT, ruolo TEXT, operatore TEXT)")
    cur.execute(query, params)
    res = cur.fetchall()
    if commit: conn.commit()
    conn.close()
    return res

# --- 3. SESSION STATE INITIALIZATION ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'role' not in st.session_state: st.session_state.role = "user"
if 'menu_val' not in st.session_state: st.session_state.menu_val = "📊 Monitoraggio"

# --- 4. LOGIN ---
if not st.session_state.auth:
    st.markdown('<h1 class="rems-header">REMS CONNECT</h1>', unsafe_allow_html=True)
    with st.container():
        pwd = st.text_input("Codice Identificativo", type="password")
        if st.button("ENTRA"):
            if pwd == "rems2026":
                st.session_state.auth = True
                st.session_state.role = "user"
                st.rerun()
            elif pwd == "admin2026":
                st.session_state.auth = True
                st.session_state.role = "admin"
                st.rerun()
            else:
                st.error("Codice errato")
    st.stop()

# --- 5. INTERFACCIA PRINCIPALE ---
st.markdown('<h1 class="rems-header">REMS CONNECT</h1>', unsafe_allow_html=True)

# Navigation Buttons
col_nav1, col_nav2 = st.columns(2)
with col_nav1:
    if st.button("📊 Monitoraggio"):
        st.session_state.menu_val = "📊 Monitoraggio"
        st.rerun()
with col_nav2:
    if st.session_state.role == "admin":
        if st.button("⚙️ Gestione"):
            st.session_state.menu_val = "⚙️ Gestione"
            st.rerun()
    else:
        st.button("⚙️ Gestione (Protetto)", disabled=True)

# --- 6. LOGICA DEI MENU ---
if st.session_state.menu_val == "📊 Monitoraggio":
    st.subheader("Pazienti in carico")
    pazienti = db_query("SELECT id, nome FROM pazienti ORDER BY nome")
    
    if not pazienti:
        st.info("Nessun paziente in lista. Vai in Gestione per aggiungerli.")
    
    for p_id, nome in pazienti:
        with st.expander(f"👤 {nome.upper()}", expanded=False):
            if f"v_{p_id}" not in st.session_state: st.session_state[f"v_{p_id}"] = 0
            
            c1, c2 = st.columns(2)
            with c1: ruolo = st.selectbox("Ruolo:", ["Psichiatra", "Infermiere", "OSS", "Psicologo", "Educatore"], key=f"sel_{p_id}_{st.session_state[f'v_{p_id}']}")
            with c2: operatore = st.text_input("Firma:", key=f"op_{p_id}_{st.session_state[f'v_{p_id}']}")
            
            st.write("**Stato Attuale:**")
            umore = st.radio("Stato", ["🟢 Stabile", "🟡 Cupo", "🟠 Deflesso", "🔴 Agitato"], index=0, key=f"u_{p_id}_{st.session_state[f'v_{p_id}']}", horizontal=True, label_visibility="collapsed")
            
            nota = st.text_area("Nota:", key=f"n_{p_id}_{st.session_state[f'v_{p_id}']}", height=100)
            
            if st.button("SALVA NOTA", key=f"btn_{p_id}"):
                if nota and operatore:
                    dt = datetime.now().strftime("%Y-%m-%d %H:%M")
                    umore_clean = umore.split(" ")[1]
                    db_query("INSERT INTO eventi (p_id, data, umore, nota, ruolo, operatore) VALUES (?,?,?,?,?,?)", (p_id, dt, umore_clean, nota, ruolo, operatore), commit=True)
                    st.session_state[f"v_{p_id}"] += 1
                    st.rerun()

            st.divider()
            
            eventi_raw = db_query("SELECT data, umore, ruolo, operatore, nota FROM eventi WHERE p_id=? ORDER BY data DESC", (p_id,))
            if eventi_raw:
                df = pd.DataFrame(eventi_raw, columns=['Data', 'Umore', 'Ruolo', 'Operatore', 'Nota'])
                st.download_button("📥 Scarica Diario", df.to_csv(index=False).encode('utf-8'), f"diario_{nome}.csv", "text/csv", key=f"dl_{p_id}")

                diario_per_data = {}
                for e in eventi_raw:
                    try:
                        d_key = datetime.strptime(e[0].split(" ")[0], "%Y-%m-%d").strftime("%d/%m/%Y")
                        t_key = e[0].split(" ")[1]
                    except:
                        d_key = e[0]; t_key = ""
                    if d_key not in diario_per_data: diario_per_data[d_key] = []
                    diario_per_data[d_key].append({"ora": t_key, "umore": e[1], "ruolo": e[2], "firma": e[3], "testo": e[4]})

                for d_label, note in diario_per_data.items():
                    with st.expander(f"📅 {d_label}"):
                        for n in note:
                            cls = "allerta-agitato" if n['umore'] == "Agitato" else ""
                            st.markdown(f'<div class="nota-card nota-{n["ruolo"]} {cls}"><small><b>{n["ora"]}</b> | {n["ruolo"]} | {n["firma"]}</small><br><b>{n["umore"]}</b><br>{n["testo"]}</div>', unsafe_allow_html=True)

elif st.session_state.menu_val == "⚙️ Gestione" and st.session_state.role == "admin":
    st.title("Gestione Anagrafica")
    with st.expander("➕ Aggiungi Paziente"):
        n_paz = st.text_input("Nome")
        if st.button("Salva"):
            db_query("INSERT INTO pazienti (nome) VALUES (?)", (n_paz,), True)
            st.rerun()
    
    p_list = db_query("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_list:
        with st.expander("✏️ Modifica"):
            p_mod = st.selectbox("Seleziona", [p[1] for p in p_list])
            n_new = st.text_input("Nuovo nome", value=p_mod)
            if st.button("Aggiorna"):
                db_query("UPDATE pazienti SET nome=? WHERE nome=?", (n_new, p_mod), True)
                st.rerun()
        with st.expander("🗑️ Elimina"):
            p_del = st.selectbox("Seleziona da eliminare", [p[1] for p in p_list])
            if st.button("Conferma"):
                db_query("DELETE FROM pazienti WHERE nome=?", (p_del,), True)
                st.rerun()
