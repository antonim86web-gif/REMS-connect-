import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date

# --- 1. CONFIGURAZIONE & STILE ---
st.set_page_config(page_title="REMS Connect PRO", layout="wide")

st.markdown("""
<style>
    .card {padding: 12px; margin: 8px 0; border-radius: 10px; background: white; border-left: 5px solid #64748b; box-shadow: 0 2px 4px rgba(0,0,0,0.05);}
    .nota-header {font-size: 0.75rem; color: #64748b; border-bottom: 1px solid #f1f5f9; margin-bottom: 5px;}
    .agitato {border-left-color: #ef4444 !important; background-color: #fef2f2 !important;}
    .log-cambio {border-left: 5px solid #f59e0b !important; background-color: #fffbeb !important; font-style: italic;}
    .terapia-card {border-left-color: #10b981 !important; background-color: #f0fdf4 !important;}
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

# --- 3. LOGIN (RIGA 41 CORRETTA) ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    pwd = st.text_input("Inserire Codice Accesso", type="password")
    if st.button("ACCEDI"):
        if pwd in ["rems2026", "admin2026"]:
            st.session_state.auth = True
            st.session_state.role = "admin" if "admin" in pwd else "user"
            st.rerun()
    st.stop()

# --- 4. SIDEBAR ---
menu = st.sidebar.radio("NAVIGAZIONE", ["Monitoraggio", "Agenda", "Terapie", "Documenti", "Gestione"])

# --- 5. MODULI ---

# --- MONITORAGGIO ---
if menu == "Monitoraggio":
    pazienti = db_run("SELECT * FROM pazienti ORDER BY nome")
    for p_id, nome in pazienti:
        with st.expander(f"👤 {nome.upper()} - Diario Clinico"):
            c1, c2 = st.columns(2)
            r = c1.selectbox("Ruolo", ["Psichiatra", "Infermiere", "OSS", "Psicologo", "Educatore"], key=f"r{p_id}")
            f = c2.text_input("Firma Operatore", key=f"f{p_id}")
            u = st.radio("Stato Paziente", ["Stabile", "Cupo", "Deflesso", "Agitato"], key=f"u{p_id}", horizontal=True)
            n = st.text_area("Nota Clinica", key=f"n{p_id}")
            if st.button("Salva Nota", key=f"b{p_id}"):
                if n and f:
                    db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%Y-%m-%d %H:%M"), u, n, r, f), True)
                    st.rerun()
            
            st.divider()
            sq = st.text_input("🔍 Cerca parola chiave...", key=f"sq{p_id}")
            sql = "SELECT data, umore, nota, ruolo, op FROM eventi WHERE id=?"
            pars = [p_id]
            if sq: 
                sql += " AND nota LIKE ?"
                pars.append(f"%{sq}%")
            
            for d, um, tx, ru, fi in db_run(sql + " ORDER BY data DESC", tuple(pars)):
                cl = f"card {'log-cambio' if '[CAMBIO' in tx else ''} {'agitato' if um=='Agitato' else ''}"
                st.markdown(f'<div class="{cl}"><div class="nota-header">{d} | {ru} | {fi}</div><b>{um}</b><br>{tx}</div>', unsafe_allow_html=True)

# --- AGENDA ---
elif menu == "Agenda":
    st.subheader("📅 Registro Appuntamenti e Uscite")
    paz = db_run("SELECT * FROM pazienti ORDER BY nome")
    
    if paz:
        with st.expander("➕ REGISTRA NUOVO EVENTO"):
            p_map = {p[1]: p[0] for p in paz}
            ps = st.selectbox("Paziente", list(p_map.keys()))
            ts = st.selectbox("Tipo", ["Uscita", "Udienza", "Visita Medica", "Permesso", "Rientro"])
            ds = st.date_input("Data", value=date.today())
            rs = st.text_input("Dettagli / Destinazione")
            if st.button("SALVA IN AGENDA"):
                db_run("INSERT INTO agenda (p_id,tipo,d_ora,note,rif) VALUES (?,?,?,?,?)", (p_map[ps], ts, str(ds), "", rs), True)
                st.rerun()
    
    st.divider()
    eventi = db_run("SELECT a.tipo, a.d_ora, a.rif, p.nome, a.row_id FROM agenda a JOIN pazienti p ON a.p_id = p.id ORDER BY d_ora DESC")
    if eventi:
        for t, d, r, pn, rid in eventi:
            st.markdown(f'''
            <div class="card">
                <div class="nota-header">📅 Data: {d}</div>
                <b>{pn}</b> — <span style="color:#1e3a8a;">{t.upper()}</span><br>
                <i>Nota: {r}</i>
            </div>''', unsafe_allow_html=True)
            if st.session_state.role == "admin" and st.button(f"Elimina #{rid}", key=f"del_ev_{rid}"):
                db_run("DELETE FROM agenda WHERE row_id=?", (rid,), True)
                st.rerun()

# --- TERAPIE ---
elif menu == "Terapie":
    pazienti = db_run("SELECT * FROM pazienti ORDER BY nome")
    for p_id, nome in pazienti:
        with st.expander(f"💊 TERAPIA: {nome.upper()}"):
            if st.session_state.role == "admin":
                f = st.text_input("Farmaco", key=f"f{p_id}")
                d = st.text_input("Dosaggio", key=f"d{p_id}")
                m = st.text_input("Medico", key=f"m{p_id}")
                if st.button("Conferma Variazione", key=f"btn{p_id}"):
                    db_run("INSERT INTO terapie (p_id, farmaco, dosaggio, data, medico) VALUES (?,?,?,?,?)", (p_id, f, d, date.today().strftime("%d/%m/%Y"), m), True)
                    # Log automatico in Monitoraggio
                    msg = f"[CAMBIO TERAPIA] {f} ({d}) - Medico: {m}"
                    db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%Y-%m-%d %H:%M"), "Stabile", msg, "SISTEMA", "ADMIN"), True)
                    st.rerun()
            st.divider()
            for fa, do, da, me, rid in db_run("SELECT farmaco, dosaggio, data, medico, row_id FROM terapie WHERE p_id=?", (p_id,)):
                st.markdown(f'<div class="card terapia-card"><b>{fa}</b>: {do} <br><small>Data: {da} — Dr. {me}</small></div>', unsafe_allow_html=True)

# --- DOCUMENTI ---
elif menu == "Documenti":
    paz = db_run("SELECT * FROM pazienti ORDER BY nome")
    if paz:
        sel_p = st.selectbox("Seleziona Paziente", [p[1] for p in paz])
        pid = [p[0] for p in paz if p[1] == sel_p][0]
        up = st.file_uploader("Carica File (PDF/JPG)")
        if up and st.button("SALVA FILE"):
            db_run("INSERT INTO documenti (p_id, nome_doc, file_blob, data) VALUES (?,?,?,?)", (pid, up.name, up.read(), date.today().strftime("%d/%m/%Y")), True)
            st.rerun()
        for n, b, d, rid in db_run("SELECT nome_doc, file_blob, data, row_id FROM documenti WHERE p_id=?", (pid,)):
            st.download_button(f"📥 Scarica: {n} ({d})", b, file_name=n, key=f"dl_{rid}")

# --- GESTIONE ---
elif menu == "Gestione":
    n = st.text_input("Nuovo Paziente")
    if st.button("AGGIUNGI"):
        if n: db_run("INSERT INTO pazienti (nome) VALUES (?)", (n,), True); st.rerun()
    st.divider()
    for pid, pnome in db_run("SELECT id, nome FROM pazienti ORDER BY nome"):
        c1, c2 = st.columns([5,1])
        c1.write(f"👤 **{pnome}**")
        if c2.button("Elimina", key=f"del{pid}"):
            db_run("DELETE FROM pazienti WHERE id=?", (pid,), True); st.rerun()
