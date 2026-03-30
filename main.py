import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import plotly.express as px

# --- 1. CONFIGURAZIONE & STILE ---
st.set_page_config(page_title="REMS Connect PRO", layout="wide")

st.markdown("""
<style>
    .stButton>button {
        width: 100%; border-radius: 8px; height: 40px !important; 
        background-color: white !important; color: #1e3a8a !important; 
        border: 1px solid #e2e8f0; font-size: 0.85rem !important; font-weight: 600;
        margin-bottom: 5px;
    }
    .active-btn button {
        background-color: #1e3a8a !important; color: white !important; 
        border: 1px solid #1e3a8a !important;
    }
    .card {padding: 12px; margin: 8px 0; border-radius: 10px; background: white; border-left: 5px solid #64748b; box-shadow: 0 2px 4px rgba(0,0,0,0.05);}
    .nota-header {font-size: 0.75rem; color: #64748b; border-bottom: 1px solid #f1f5f9; margin-bottom: 5px;}
    .agitato {border-left-color: #ef4444 !important; background-color: #fef2f2 !important;}
    #MainMenu, footer, header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- 2. DATABASE ---
DB_NAME = "rems_connect_data.db"

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, umore TEXT, nota TEXT, ruolo TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS agenda (p_id INTEGER, tipo TEXT, d_ora TEXT, note TEXT, rif TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dosaggio TEXT, data TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS documenti (p_id INTEGER, nome_doc TEXT, file_blob BLOB, data TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS permessi (p_id INTEGER, tipo TEXT, uscita TEXT, rientro TEXT, esito TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute(query, params)
        if commit: conn.commit()
        return cur.fetchall()

# --- 3. SESSIONE ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'menu' not in st.session_state: st.session_state.menu = "Monitoraggio"
for k in ['v_g', 'v_a', 'v_t', 'v_p']: 
    if k not in st.session_state: st.session_state[k] = 0

# --- 4. LOGIN ---
if not st.session_state.auth:
    st.markdown("<h3 style='text-align:center;'>REMS CONNECT LOGIN</h3>", unsafe_allow_html=True)
    pwd = st.text_input("Codice Accesso", type="password")
    if st.button("ACCEDI"):
        if pwd in ["rems2026", "admin2026"]:
            st.session_state.auth = True
            st.session_state.role = "admin" if "admin" in pwd else "user"
            st.rerun()
    st.stop()

# --- 5. NAVIGAZIONE ---
st.markdown("<h4 style='text-align:center; color:#1e3a8a;'>REMS CONNECT SYSTEM</h4>", unsafe_allow_html=True)
cols = st.columns(6)
menu_items = ["Monitoraggio", "Agenda", "Terapie", "Statistiche", "Documenti", "Gestione"]
icons = ["📊", "📅", "💊", "📈", "📂", "⚙️"]

for i, item in enumerate(menu_items):
    if item == "Gestione" and st.session_state.role != "admin": continue
    with cols[i]:
        active = "active-btn" if st.session_state.menu == item else ""
        st.markdown(f'<div class="{active}">', unsafe_allow_html=True)
        if st.button(f"{icons[i]} {item}"):
            st.session_state.menu = item
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# --- 6. MODULI ---

if st.session_state.menu == "Monitoraggio":
    ruoli = ["Psichiatra", "Infermiere", "OSS", "Psicologo", "Educatore"]
    filtro = st.selectbox("Filtra per figura:", ["TUTTI"] + ruoli)
    for p_id, nome in db_run("SELECT * FROM pazienti ORDER BY nome"):
        with st.expander(f"👤 {nome.upper()}"):
            vi = st.session_state.get(f"v_{p_id}", 0)
            c1, c2 = st.columns(2)
            r = c1.selectbox("Ruolo", ruoli, key=f"r{p_id}{vi}")
            o = c2.text_input("Firma", key=f"f{p_id}{vi}")
            u = st.radio("Stato", ["Stabile", "Cupo", "Deflesso", "Agitato"], key=f"u{p_id}{vi}", horizontal=True)
            n = st.text_area("Nota", key=f"n{p_id}{vi}")
            if st.button("SALVA NOTA", key=f"btn{p_id}"):
                if n and o:
                    db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%Y-%m-%d %H:%M"), u, n, r, o), True)
                    st.session_state[f"v_{p_id}"] = vi + 1; st.rerun()
            
            q = "SELECT data, umore, nota, ruolo, op FROM eventi WHERE id=?"
            pa = [p_id]
            if filtro != "TUTTI": q += " AND ruolo=?"; pa.append(filtro)
            for d, um, tx, ru, fi in db_run(q + " ORDER BY data DESC LIMIT 5", tuple(pa)):
                cl = "card agitato" if um=="Agitato" else "card"
                st.markdown(f'<div class="{cl}"><small>{d} | {ru} | {fi}</small><br><b>{um}</b>: {tx}</div>', unsafe_allow_html=True)

elif st.session_state.menu == "Terapie":
    paz = db_run("SELECT * FROM pazienti ORDER BY nome")
    if paz:
        p_map = {p[1]: p[0] for p in paz}
        sel_p = st.selectbox("Seleziona Paziente", list(p_map.keys()))
        pid = p_map[sel_p]
        
        # Solo Admin può modificare
        if st.session_state.role == "admin":
            with st.expander("➕ MODIFICA TERAPIA (Solo Admin)"):
                f = st.text_input("Farmaco")
                d = st.text_input("Dosaggio")
                if st.button("SALVA VARIAZIONE"):
                    db_run("INSERT INTO terapie (p_id, farmaco, dosaggio, data) VALUES (?,?,?,?)", (pid, f, d, datetime.now().strftime("%Y-%m-%d")), True)
                    st.success("Terapia aggiornata"); st.rerun()

        st.subheader(f"Piano Farmacologico Attuale: {sel_p}")
        p_ter = db_run("SELECT farmaco, dosaggio, data, row_id FROM terapie WHERE p_id=? ORDER BY data DESC", (pid,))
        if p_ter:
            for f, d, dt, rid in p_ter:
                st.markdown(f'<div class="card" style="border-left-color: #10b981;">💊 <b>{f}</b> - {d} <br><small>Inserito il: {dt}</small></div>', unsafe_allow_html=True)
                if st.session_state.role == "admin":
                    if st.button(f"Elimina farmaco #{rid}", key=f"del_t_{rid}"):
                        db_run("DELETE FROM terapie WHERE row_id=?", (rid,), True); st.rerun()
        else: st.info("Nessuna terapia registrata.")

elif st.session_state.menu == "Statistiche":
    data = db_run("SELECT p.nome, e.umore, e.data FROM eventi e JOIN pazienti p ON e.id = p.id")
    if data:
        df = pd.DataFrame(data, columns=["Paziente", "Umore", "Data"])
        df['Data'] = pd.to_datetime(df['Data']).dt.date
        fig = px.pie(df, names="Umore", title="Distribuzione Globale Stati d'Animo", color="Umore",
                     color_discrete_map={"Agitato":"#ef4444", "Stabile":"#10b981", "Cupo":"#1e3a8a", "Deflesso":"#f59e0b"})
        st.plotly_chart(fig, use_container_width=True)
    else: st.info("Dati insufficienti per i grafici.")

elif st.session_state.menu == "Gestione":
    vg = st.session_state.v_g
    st.subheader("Anagrafica & Manutenzione")
    nn = st.text_input("Aggiungi Paziente", key=f"nn{vg}")
    if st.button("SALVA NUOVO"):
        if nn: db_run("INSERT INTO pazienti (nome) VALUES (?)", (nn,), True); st.session_state.v_g += 1; st.rerun()
    
    pl = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if pl:
        st.divider()
        psel = st.selectbox("Seleziona Paziente", [p[1] for p in pl], key=f"ps{vg}")
        nuovo_n = st.text_input("Rinomina", value=psel, key=f"modn{vg}")
        c1, c2 = st.columns(2)
        if c1.button("AGGIORNA"):
            pid = [p[0] for p in pl if p[1] == psel][0]
            db_run("UPDATE pazienti SET nome=? WHERE id=?", (nuovo_n, pid), True); st.session_state.v_g += 1; st.rerun()
        if c2.button("ELIMINA"):
            db_run("DELETE FROM pazienti WHERE nome=?", (psel,), True); st.session_state.v_g += 1; st.rerun()
    
    st.divider()
    with open(DB_NAME, "rb") as f:
        st.download_button("📥 BACKUP DATABASE (.db)", f, file_name=f"rems_backup_{datetime.now().strftime('%Y%m%d')}.db")
