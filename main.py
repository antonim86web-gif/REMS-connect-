import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import plotly.express as px

# --- 1. CONFIGURAZIONE & STILE ---
st.set_page_config(page_title="REMS Connect PRO", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .block-container {padding-top: 1.5rem;}
    .card {padding: 12px; margin: 8px 0; border-radius: 10px; background: white; border-left: 5px solid #64748b; box-shadow: 0 2px 4px rgba(0,0,0,0.05);}
    .nota-header {font-size: 0.75rem; color: #64748b; border-bottom: 1px solid #f1f5f9; margin-bottom: 5px;}
    .agitato {border-left-color: #ef4444 !important; background-color: #fef2f2 !important;}
    .terapia-card {border-left-color: #10b981 !important; background-color: #f0fdf4 !important;}
    section[data-testid="stSidebar"] { background-color: #f8fafc; border-right: 1px solid #e2e8f0; }
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
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dosaggio TEXT, data TEXT, medico TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS documenti (p_id INTEGER, nome_doc TEXT, file_blob BLOB, data TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        try:
            cur.execute("SELECT medico FROM terapie LIMIT 1")
        except sqlite3.OperationalError:
            cur.execute("ALTER TABLE terapie ADD COLUMN medico TEXT DEFAULT 'N.D.'")
            conn.commit()
        cur.execute(query, params)
        if commit: conn.commit()
        return cur.fetchall()

# --- 3. SESSIONE ---
if 'auth' not in st.session_state: st.session_state.auth = False
for k in ['v_g', 'v_a', 'v_t']: 
    if k not in st.session_state: st.session_state[k] = 0

# --- 4. LOGIN ---
if not st.session_state.auth:
    st.markdown("<h3 style='text-align:center;'>REMS CONNECT SYSTEM</h3>", unsafe_allow_html=True)
    pwd = st.text_input("Codice Accesso", type="password")
    if st.button("ACCEDI"):
        if pwd in ["rems2026", "admin2026"]:
            st.session_state.auth = True
            st.session_state.role = "admin" if "admin" in pwd else "user"
            st.rerun()
    st.stop()

# --- 5. SIDEBAR ---
with st.sidebar:
    st.markdown("<h2 style='color:#1e3a8a;'>REMS Connect</h2>", unsafe_allow_html=True)
    st.write(f"Utente: **{st.session_state.role.upper()}**")
    st.divider()
    menu_options = ["Monitoraggio", "Agenda", "Terapie", "Statistiche", "Documenti"]
    if st.session_state.role == "admin": menu_options.append("Gestione")
    st.session_state.menu = st.radio("VAI A:", menu_options)
    st.divider()
    if st.button("Logout"):
        st.session_state.auth = False
        st.rerun()

# --- 6. MODULI ---
st.title(f"{st.session_state.menu}")

if st.session_state.menu == "Monitoraggio":
    ruoli_list = ["Tutti", "Psichiatra", "Infermiere", "OSS", "Psicologo", "Educatore"]
    pazienti = db_run("SELECT * FROM pazienti ORDER BY nome")
    if not pazienti: st.info("Nessun paziente in anagrafica.")
    for p_id, nome in pazienti:
        with st.expander(f"👤 {nome.upper()}"):
            vi = st.session_state.get(f"v_{p_id}", 0)
            c1, c2 = st.columns(2)
            r = c1.selectbox("Ruolo", ruoli_list[1:], key=f"r{p_id}{vi}")
            o = c2.text_input("Firma", key=f"f{p_id}{vi}")
            u = st.radio("Stato", ["Stabile", "Cupo", "Deflesso", "Agitato"], key=f"u{p_id}{vi}", horizontal=True)
            n = st.text_area("Nota Clinica", key=f"n{p_id}{vi}")
            if st.button("SALVA NOTA", key=f"btn{p_id}"):
                if n and o:
                    db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%Y-%m-%d %H:%M"), u, n, r, o), True)
                    st.session_state[f"v_{p_id}"] = vi + 1; st.rerun()
            st.divider()
            sf1, sf2 = st.columns([2, 1])
            sq = sf1.text_input("🔍 Cerca parole chiave...", key=f"sq{p_id}")
            fr = sf2.selectbox("Filtra Ruolo", ruoli_list, key=f"fr{p_id}")
            query = "SELECT data, umore, nota, ruolo, op, row_id FROM eventi WHERE id=?"
            pars = [p_id]
            if sq: query += " AND nota LIKE ?"; pars.append(f"%{sq}%")
            if fr != "Tutti": query += " AND ruolo = ?"; pars.append(fr)
            query += " ORDER BY data DESC"
            for d, um, tx, ru, fi, rid in db_run(query, tuple(pars)):
                cl = "card agitato" if um=="Agitato" else "card"
                st.markdown(f'<div class="{cl}"><div class="nota-header">{d} | {ru} | {fi}</div><b>{um}</b><br>{tx}</div>', unsafe_allow_html=True)
                if st.session_state.role == "admin" and st.button(f"Elimina #{rid}", key=f"del_ev_{rid}"):
                    db_run("DELETE FROM eventi WHERE row_id=?", (rid,), True); st.rerun()

elif st.session_state.menu == "Agenda":
    paz = db_run("SELECT * FROM pazienti ORDER BY nome")
    if paz:
        with st.expander("➕ NUOVO APPUNTAMENTO"):
            p_map = {p[1]: p[0] for p in paz}
            ps = st.selectbox("Paziente", list(p_map.keys()))
            ts = st.selectbox("Tipo", ["Udienza", "Visita", "Uscita"])
            ds = st.date_input("Data")
            rs = st.text_input("Dettagli/Note")
            if st.button("REGISTRA"):
                db_run("INSERT INTO agenda (p_id,tipo,d_ora,note,rif) VALUES (?,?,?,?,?)", (p_map[ps], ts, str(ds), "", rs), True)
                st.rerun()
    for t, d, r, pn, rid in db_run("SELECT a.tipo, a.d_ora, a.rif, p.nome, a.row_id FROM agenda a JOIN pazienti p ON a.p_id = p.id ORDER BY d_ora ASC"):
        st.markdown(f'<div class="card"><b>{t}</b> | {d}<br>Paziente: {pn} | {r}</div>', unsafe_allow_html=True)
        if st.session_state.role == "admin" and st.button(f"Elimina App. #{rid}", key=f"del_ag_{rid}"):
            db_run("DELETE FROM agenda WHERE row_id=?", (rid,), True); st.rerun()

elif st.session_state.menu == "Terapie":
    paz = db_run("SELECT * FROM pazienti ORDER BY nome")
    if paz:
        p_map = {p[1]: p[0] for p in paz}
        sel_p = st.selectbox("Seleziona Paziente", list(p_map.keys()))
        pid = p_map[sel_p]
        if st.session_state.role == "admin":
            with st.expander("➕ AGGIUNGI/VARIA TERAPIA"):
                f = st.text_input("Farmaco")
                d = st.text_input("Dosaggio")
                m = st.text_input("Medico Prescrittore")
                if st.button("REGISTRA"):
                    db_run("INSERT INTO terapie (p_id, farmaco, dosaggio, data, medico) VALUES (?,?,?,?,?)", (pid, f, d, datetime.now().strftime("%Y-%m-%d"), m), True)
                    st.rerun()
        for f, ds, dt, med, rid in db_run("SELECT farmaco, dosaggio, data, medico, row_id FROM terapie WHERE p_id=? ORDER BY data DESC", (pid,)):
            st.markdown(f'<div class="card terapia-card"><div class="nota-header">{dt} | Medico: {med}</div>💊 <b>{f}</b><br>{ds}</div>', unsafe_allow_html=True)
            if st.session_state.role == "admin" and st.button(f"Elimina farmaco #{rid}", key=f"del_t_{rid}"):
                db_run("DELETE FROM terapie WHERE row_id=?", (rid,), True); st.rerun()

elif st.session_state.menu == "Statistiche":
    paz_list = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if paz_list:
        p_map = {p[1]: p[0] for p in paz_list}
        sel_p = st.selectbox("Analisi Paziente:", list(p_map.keys()))
        res = db_run("SELECT data, umore FROM eventi WHERE id=? ORDER BY data ASC", (p_map[sel_p],))
        if res:
            df = pd.DataFrame(res, columns=["Data", "Umore"])
            c1, c2 = st.columns(2)
            with c1: 
                fig_pie = px.pie(df, names="Umore", color="Umore", color_discrete_map={"Agitato":"#ef4444", "Stabile":"#10b981", "Cupo":"#1e3a8a", "Deflesso":"#f59e0b"})
                st.plotly_chart(fig_pie, use_container_width=True)
            with c2: 
                df['Data'] = pd.to_datetime(df['Data'])
                df['Livello'] = df['Umore'].map({"Agitato": 0, "Cupo": 1, "Deflesso": 2, "Stabile": 3})
                fig_line = px.line(df, x="Data", y="Livello", markers=True)
                fig_line.update_yaxes(tickvals=[0, 1, 2, 3], ticktext=["Agitato", "Cupo", "Deflesso", "Stabile"])
                st.plotly_chart(fig_line, use_container_width=True)
        else: st.warning("Dati insufficienti per questo paziente.")
    else: st.info("Nessun paziente in anagrafica.")

elif st.session_state.menu == "Documenti":
    paz = db_run("SELECT * FROM pazienti ORDER BY nome")
    if paz:
        p_map = {p[1]: p[0] for p in paz}
        sel_p = st.selectbox("Paziente", list(p_map.keys()))
        up = st.file_uploader("Carica File", type=['pdf', 'jpg', 'png'])
        if up and st.button("SALVA"):
            db_run("INSERT INTO documenti (p_id, nome_doc, file_blob, data) VALUES (?,?,?,?)", (p_map[sel_p], up.name, up.read(), datetime.now().strftime("%Y-%m-%d")), True)
            st.rerun()
        for n, b, d, rid in db_run("SELECT nome_doc, file_blob, data, row_id FROM documenti WHERE p_id=?", (p_map[sel_p],)):
            st.download_button(f"📥 {n} ({d})", b, file_name=n, key=f"dl_{rid}")
            if st.session_state.role == "admin" and st.button(f"Elimina Doc #{rid}", key=f"del_doc_{rid}"):
                db_run("DELETE FROM documenti WHERE row_id=?", (rid,), True); st.rerun()

elif st.session_state.menu == "Gestione":
    st.subheader("Anagrafica Pazienti")
    nn = st.text_input("Aggiungi Paziente")
    if st.button("➕ AGGIUNGI"):
        if nn: db_run("INSERT INTO pazienti (nome) VALUES (?)", (nn,), True); st.rerun()
    st.divider()
    for pid, pnome in db_run("SELECT id, nome FROM pazienti ORDER BY nome"):
        c1, c2, c3 = st.columns([3, 1, 1])
        nuovo = c1.text_input(f"Edita", value=pnome, key=f"ed_{pid}", label_visibility="collapsed")
        if c2.button("💾", key=f"s_{pid}"):
            db_run("UPDATE pazienti SET nome=? WHERE id=?", (nuovo, pid), True); st.rerun()
        if c3.button("🗑️", key=f"d_{pid}"):
            db_run("DELETE FROM pazienti WHERE id=?", (pid,), True); st.rerun()
    st.divider()
    with open(DB_NAME, "rb") as f: st.download_button("📥 BACKUP DB", f, file_name="rems_backup.db")
