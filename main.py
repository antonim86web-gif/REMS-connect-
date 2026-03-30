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
        text-align: center; color: #1e3a8a; font-family: 'Orbitron', sans-serif;
        font-size: 3rem !important; font-weight: 700; margin-bottom: 20px;
        text-transform: uppercase; letter-spacing: 4px; text-shadow: 0 0 10px rgba(37, 99, 235, 0.2);
    }
    .stButton>button { 
        height: 3.5rem !important; font-size: 1.1rem !important; border-radius: 12px !important; 
        background-color: #2563eb !important; color: white !important; font-weight: bold !important; 
        width: 100%; font-family: 'Orbitron', sans-serif;
    }
    .nota-card { padding: 12px; margin-bottom: 8px; border-radius: 8px; color: #1e293b; border-left: 6px solid #cbd5e1; background-color: #f8fafc; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
    .agenda-card { background-color: white; padding: 15px; border-radius: 10px; border: 1px solid #e2e8f0; margin-bottom: 10px; border-top: 4px solid #2563eb; }
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
    # Nuova tabella per Agenda e Uscite
    cur.execute("""CREATE TABLE IF NOT EXISTS agenda 
                   (id INTEGER PRIMARY KEY, p_id INTEGER, tipo TEXT, data_ora TEXT, note TEXT, operatore_rif TEXT)""")
    cur.execute(query, params)
    res = cur.fetchall()
    if commit: conn.commit()
    conn.close()
    return res

# --- 3. SESSION STATE ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'role' not in st.session_state: st.session_state.role = "user"
if 'menu_val' not in st.session_state: st.session_state.menu_val = "📊 Monitoraggio"

# --- 4. LOGIN ---
if not st.session_state.auth:
    st.markdown('<h1 class="rems-header">REMS CONNECT</h1>', unsafe_allow_html=True)
    pwd = st.text_input("Codice Identificativo", type="password")
    if st.button("ENTRA"):
        if pwd == "rems2026": st.session_state.auth = True; st.session_state.role = "user"; st.rerun()
        elif pwd == "admin2026": st.session_state.auth = True; st.session_state.role = "admin"; st.rerun()
        else: st.error("Codice errato")
    st.stop()

# --- 5. INTERFACCIA ---
st.markdown('<h1 class="rems-header">REMS CONNECT</h1>', unsafe_allow_html=True)

c_nav1, c_nav2, c_nav3 = st.columns(3)
with c_nav1:
    if st.button("📊 Monitoraggio"): st.session_state.menu_val = "📊 Monitoraggio"; st.rerun()
with c_nav2:
    if st.button("📅 Agenda & Uscite"): st.session_state.menu_val = "📅 Agenda"; st.rerun()
with c_nav3:
    if st.session_state.role == "admin":
        if st.button("⚙️ Gestione"): st.session_state.menu_val = "⚙️ Gestione"; st.rerun()
    else: st.button("⚙️ Gestione (Admin)", disabled=True)

# --- 6. LOGICA MENU ---

# --- MONITORAGGIO ---
if st.session_state.menu_val == "📊 Monitoraggio":
    pazienti = db_query("SELECT id, nome FROM pazienti ORDER BY nome")
    for p_id, nome in pazienti:
        with st.expander(f"👤 {nome.upper()}"):
            # (Codice salvataggio note identico a prima...)
            c1, c2 = st.columns(2)
            with c1: ruolo = st.selectbox("Ruolo:", ["Psichiatra", "Infermiere", "OSS", "Psicologo", "Educatore"], key=f"r_{p_id}")
            with c2: operatore = st.text_input("Firma:", key=f"f_{p_id}")
            umore = st.radio("Stato", ["Stabile", "Cupo", "Deflesso", "Agitato"], key=f"u_{p_id}", horizontal=True)
            nota = st.text_area("Nota:", key=f"n_{p_id}")
            if st.button("SALVA NOTA", key=f"b_{p_id}"):
                if nota and operatore:
                    dt = datetime.now().strftime("%Y-%m-%d %H:%M")
                    db_query("INSERT INTO eventi (p_id, data, umore, nota, ruolo, operatore) VALUES (?,?,?,?,?,?)", (p_id, dt, umore, nota, ruolo, operatore), True)
                    st.rerun()
            st.divider()
            # Visualizzazione note...
            eventi = db_query("SELECT data, umore, ruolo, operatore, nota FROM eventi WHERE p_id=? ORDER BY data DESC", (p_id,))
            for e in eventi:
                cls = "allerta-agitato" if e[1] == "Agitato" else ""
                st.markdown(f'<div class="nota-card nota-{e[2]} {cls}"><small>{e[0]} | {e[2]} | {e[3]}</small><br><b>{e[1]}</b><br>{e[4]}</div>', unsafe_allow_html=True)

# --- AGENDA & USCITE (LA NOVITÀ) ---
elif st.session_state.menu_val == "📅 Agenda":
    st.title("Agenda Visite ed Uscite")
    pazienti = db_query("SELECT id, nome FROM pazienti ORDER BY nome")
    p_dict = {p[1]: p[0] for p in pazienti}

    with st.expander("➕ REGISTRA NUOVO EVENTO (Visita/Uscita/Udienza)"):
        p_sel = st.selectbox("Paziente:", list(p_dict.keys()))
        tipo = st.selectbox("Tipo Evento:", ["Visita con Parenti", "Uscita con Operatore", "Udienza / Perizia", "Visita Medica Esterna"])
        data_ev = st.date_input("Data:")
        ora_ev = st.time_input("Ora:")
        accompagnatore = st.text_input("Operatore di riferimento / Accompagnatore:")
        dettagli = st.text_area("Note (es: Nomi parenti, destinazione uscita, autorizzazione magistrato)")
        
        if st.button("PROGRAMMA EVENTO"):
            dt_str = f"{data_ev} {ora_ev.strftime('%H:%M')}"
            db_query("INSERT INTO agenda (p_id, tipo, data_ora, note, operatore_rif) VALUES (?,?,?,?,?)", 
                     (p_dict[p_sel], tipo, dt_str, dettagli, accompagnatore), True)
            st.success("Evento registrato correttamente!")
            st.rerun()

    st.divider()
    
    # Filtro rapido
    filtro_tipo = st.multiselect("Filtra per tipo:", ["Visita con Parenti", "Uscita con Operatore", "Udienza / Perizia", "Visita Medica Esterna"])
    
    eventi_agenda = db_query("""SELECT agenda.tipo, agenda.data_ora, agenda.note, agenda.operatore_rif, pazienti.nome 
                                FROM agenda JOIN pazienti ON agenda.p_id = pazienti.id 
                                ORDER BY agenda.data_ora ASC""")
    
    for ev in eventi_agenda:
        if filtro_tipo and ev[0] not in filtro_tipo: continue
        
        col_icon = "👥" if "Parenti" in ev[0] else "🚶‍♂️" if "Uscita" in ev[0] else "⚖️" if "Udienza" in ev[0] else "🏥"
        st.markdown(f"""
        <div class="agenda-card">
            <div style="display: flex; justify-content: space-between;">
                <b>{col_icon} {ev[0].upper()}</b>
                <span style="color: #2563eb;">📅 {ev[1]}</span>
            </div>
            <div style="font-size: 1.2rem; margin: 10px 0;">Paziente: <b>{ev[4].upper()}</b></div>
            <div style="font-size: 0.9rem; color: #475569;">
                Rif/Accompagnatore: <b>{ev[3]}</b><br>
                Note: <i>{ev[2]}</i>
            </div>
        </div>
        """, unsafe_allow_html=True)

# --- GESTIONE ---
elif st.session_state.menu_val == "⚙️ Gestione" and st.session_state.role == "admin":
    st.title("Gestione Anagrafica")
    # (Codice gestione anagrafica identico a prima...)
    with st.expander("➕ Aggiungi"):
        nome_n = st.text_input("Nome")
        if st.button("Salva"): db_query("INSERT INTO pazienti (nome) VALUES (?)", (nome_n,), True); st.rerun()
