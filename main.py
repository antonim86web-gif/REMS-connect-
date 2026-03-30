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
    .log-cambio {border-left: 5px solid #f59e0b !important; background-color: #fffbeb !important; font-style: italic; font-size: 0.85rem;}
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
        cur.execute(query, params)
        if commit: conn.commit()
        return cur.fetchall()

# --- 3. SESSIONE ---
if 'auth' not in st.session_state: st.session_state.auth = False

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

# --- MONITORAGGIO ---
if st.session_state.menu == "Monitoraggio":
    pazienti = db_run("SELECT * FROM pazienti ORDER BY nome")
    for p_id, nome in pazienti:
        with st.expander(f"👤 {nome.upper()} - Diario Clinico"):
            # Form inserimento nota (codice standard)
            c1, c2 = st.columns(2)
            r = c1.selectbox("Ruolo", ["Psichiatra", "Infermiere", "OSS", "Psicologo", "Educatore"], key=f"r{p_id}")
            o = c2.text_input("Firma", key=f"f{p_id}")
            u = st.radio("Umore", ["Stabile", "Cupo", "Deflesso", "Agitato"], key=f"u{p_id}", horizontal=True)
            n = st.text_area("Nota", key=f"n{p_id}")
            if st.button("SALVA NOTA", key=f"btn{p_id}"):
                if n and o:
                    db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%Y-%m-%d %H:%M"), u, n, r, o), True)
                    st.rerun()
            st.divider()
            # Visualizzazione note
            for d, um, tx, ru, fi, rid in db_run("SELECT data, umore, nota, ruolo, op, row_id FROM eventi WHERE id=? ORDER BY data DESC", (p_id,)):
                is_log = "log-cambio" if "[CAMBIO TERAPIA]" in tx else ""
                cl = f"card {is_log} {'agitato' if um=='Agitato' else ''}"
                st.markdown(f'<div class="{cl}"><div class="nota-header">{d} | {ru} | {fi}</div><b>{um}</b><br>{tx}</div>', unsafe_allow_html=True)

# --- TERAPIE (NUOVA VISUALIZZAZIONE) ---
elif st.session_state.menu == "Terapie":
    pazienti = db_run("SELECT * FROM pazienti ORDER BY nome")
    for p_id, nome in pazienti:
        with st.expander(f"💊 TERAPIA: {nome.upper()}"):
            if st.session_state.role == "admin":
                with st.container():
                    st.markdown("##### ➕ Nuova Prescrizione")
                    f = st.text_input("Farmaco", key=f"f_t{p_id}")
                    d = st.text_input("Dosaggio/Orari", key=f"d_t{p_id}")
                    m = st.text_input("Medico", key=f"m_t{p_id}")
                    if st.button("CONFERMA VARIAZIONE", key=f"btn_t{p_id}"):
                        if f and d:
                            # 1. Inserisce in Tabella Terapie
                            db_run("INSERT INTO terapie (p_id, farmaco, dosaggio, data, medico) VALUES (?,?,?,?,?)", (p_id, f, d, datetime.now().strftime("%d/%m/%Y"), m), True)
                            # 2. SEGNALAZIONE AUTOMATICA: Crea nota nel monitoraggio
                            nota_log = f"[CAMBIO TERAPIA] Inserito farmaco: {f} ({d}) da parte del Medico: {m}"
                            db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%Y-%m-%d %H:%M"), "Stabile", nota_log, "SISTEMA", "ADMIN"), True)
                            st.success("Terapia aggiornata e segnalata nel diario clinico.")
                            st.rerun()
            
            st.markdown("---")
            # Lista farmaci attivi
            for farm, dos, dat, med, rid in db_run("SELECT farmaco, dosaggio, data, medico, row_id FROM terapie WHERE p_id=? ORDER BY row_id DESC", (p_id,)):
                st.markdown(f'''
                <div class="card terapia-card">
                    <div class="nota-header">Prescritta il: {dat} | Medico: {med}</div>
                    <b>{farm}</b><br>{dos}
                </div>''', unsafe_allow_html=True)
                if st.session_state.role == "admin" and st.button(f"Sospendi #{rid}", key=f"del_t_{rid}"):
                    db_run("DELETE FROM terapie WHERE row_id=?", (rid,), True)
                    st.rerun()

# --- STATISTICHE ---
elif st.session_state.menu == "Statistiche":
    paz_list = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if paz_list:
        sel_p = st.selectbox("Seleziona Paziente:", [p[1] for p in paz_list])
        p_id = [p[0] for p in paz_list if p[1] == sel_p][0]
        res = db_run("SELECT data, umore FROM eventi WHERE id=? AND nota NOT LIKE '[CAMBIO TERAPIA]%' ORDER BY data ASC", (p_id,))
        if res:
            df = pd.DataFrame(res, columns=["Data", "Umore"])
            c1, c2 = st.columns(2)
            with c1: st.plotly_chart(px.pie(df, names="Umore", color="Umore", color_discrete_map={"Agitato":"#ef4444", "Stabile":"#10b981", "Cupo":"#1e3a8a", "Deflesso":"#f59e0b"}), use_container_width=True)
            with c2: 
                df['Data'] = pd.to_datetime(df['Data'])
                df['Livello'] = df['Umore'].map({"Agitato": 0, "Cupo": 1, "Deflesso": 2, "Stabile": 3})
                st.plotly_chart(px.line(df, x="Data", y="Livello", markers=True), use_container_width=True)
        else: st.info("Dati clinici insufficienti per le statistiche.")

# --- AGENDA, DOCUMENTI, GESTIONE (Restano attivi come prima) ---
elif st.session_state.menu == "Agenda":
    # ... (Codice Agenda visto in precedenza)
    paz = db_run("SELECT * FROM pazienti ORDER BY nome")
    if paz:
        with st.expander("➕ NUOVO APPUNTAMENTO"):
            p_map = {p[1]: p[0] for p in paz}
            ps = st.selectbox("Paziente", list(p_map.keys()))
            ts = st.selectbox("Tipo", ["Udienza", "Visita", "Uscita"])
            ds = st.date_input("Data")
            rs = st.text_input("Dettagli")
            if st.button("REGISTRA"):
                db_run("INSERT INTO agenda (p_id,tipo,d_ora,note,rif) VALUES (?,?,?,?,?)", (p_map[ps], ts, str(ds), "", rs), True)
                st.rerun()
    for t, d, r, pn, rid in db_run("SELECT a.tipo, a.d_ora, a.rif, p.nome, a.row_id FROM agenda a JOIN pazienti p ON a.p_id = p.id ORDER BY d_ora ASC"):
        st.markdown(f'<div class="card"><b>{t}</b> | {d}<br>Paziente: {pn} | {r}</div>', unsafe_allow_html=True)

elif st.session_state.menu == "Documenti":
    paz = db_run("SELECT * FROM pazienti ORDER BY nome")
    if paz:
        sel_p = st.selectbox("Paziente", [p[1] for p in paz])
        pid = [p[0] for p in paz if p[1] == sel_p][0]
        up = st.file_uploader("Upload", type=['pdf', 'jpg', 'png'])
        if up and st.button("CARICA"):
            db_run("INSERT INTO documenti (p_id, nome_doc, file_blob, data) VALUES (?,?,?,?)", (pid, up.name, up.read(), datetime.now().strftime("%Y-%m-%d")), True)
            st.rerun()
        for n, b, d, rid in db_run("SELECT nome_doc, file_blob, data, row_id FROM documenti WHERE p_id=?", (pid,)):
            st.download_button(f"📥 {n} ({d})", b, file_name=n, key=f"dl_{rid}")

elif st.session_state.menu == "Gestione":
    st.subheader("Anagrafica Pazienti")
    nn = st.text_input("Aggiungi Paziente")
    if st.button("➕ AGGIUNGI"):
        if nn: db_run("INSERT INTO pazienti (nome) VALUES (?)", (nn,), True); st.rerun()
    for pid, pnome in db_run("SELECT id, nome FROM pazienti ORDER BY nome"):
        c1, c2, c3 = st.columns([3, 1, 1])
        nuovo = c1.text_input(f"Edit", value=pnome, key=f"ed_{pid}", label_visibility="collapsed")
        if c2.button("💾", key=f"s_{pid}"): db_run("UPDATE pazienti SET nome=? WHERE id=?", (nuovo, pid), True); st.rerun()
        if c3.button("🗑️", key=f"d_{pid}"): db_run("DELETE FROM pazienti WHERE id=?", (pid,), True); st.rerun()
