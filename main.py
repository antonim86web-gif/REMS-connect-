import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date

# --- 1. CONFIGURAZIONE & STILE ---
st.set_page_config(page_title="REMS Connect PRO", layout="wide")

st.markdown("""
<style>
    .main-title {text-align: center; color: #1e3a8a; margin-bottom: 20px; font-weight: bold;}
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

# --- 3. LOGIN ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.markdown("<h1 class='main-title'>REMS CONNECT</h1>", unsafe_allow_html=True)
    pwd = st.text_input("Inserire Codice Accesso", type="password")
    if st.button("ACCEDI"):
        if pwd in ["rems2026", "admin2026"]:
            st.session_state.auth = True
            st.session_state.role = "admin" if pwd == "admin2026" else "user"
            st.rerun()
    st.stop()

st.markdown("<h1 class='main-title'>REMS CONNECT</h1>", unsafe_allow_html=True)

# --- 4. SIDEBAR ---
menu = st.sidebar.radio("NAVIGAZIONE", ["Monitoraggio", "Agenda", "Terapie", "Documenti", "Gestione"])
ruoli_lista = ["Tutti", "Psichiatra", "Infermiere", "OSS", "Psicologo", "Educatore", "SISTEMA"]

# --- 5. MONITORAGGIO ---
if menu == "Monitoraggio":
    pazienti = db_run("SELECT * FROM pazienti ORDER BY nome")
    for p_id, nome in pazienti:
        with st.expander(f"👤 {nome.upper()} - Diario Clinico"):
            c1, c2 = st.columns(2)
            r_ins = c1.selectbox("Tuo Ruolo", ruoli_lista[1:-1], key=f"r_ins{p_id}")
            f_ins = c2.text_input("Firma Operatore", key=f"f_ins{p_id}")
            u_ins = st.radio("Stato Paziente", ["Stabile", "Cupo", "Deflesso", "Agitato"], key=f"u_ins{p_id}", horizontal=True)
            n_ins = st.text_area("Nota Clinica", key=f"n_ins{p_id}")
            if st.button("Salva Nota", key=f"btn_save{p_id}"):
                if n_ins and f_ins:
                    db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%Y-%m-%d %H:%M"), u_ins, n_ins, r_ins, f_ins), True)
                    st.rerun()
            st.divider()
            st.markdown("🔍 **Filtra Storico**")
            f1, f2 = st.columns(2)
            data_filtro = f1.date_input("Per Data", value=None, key=f"date{p_id}")
            ruolo_filtro = f2.selectbox("Per Figura Professionale", ruoli_lista, key=f"role{p_id}")
            
            sql = "SELECT data, umore, nota, ruolo, op FROM eventi WHERE id=?"
            pars = [p_id]
            if data_filtro:
                sql += " AND data LIKE ?"
                pars.append(f"{data_filtro}%")
            if ruolo_filtro != "Tutti":
                sql += " AND ruolo = ?"
                pars.append(ruolo_filtro)
                
            for d, um, tx, ru, fi in db_run(sql + " ORDER BY data DESC", tuple(pars)):
                cl = f"card {'log-cambio' if '[CAMBIO' in tx else ''} {'agitato' if um=='Agitato' else ''}"
                st.markdown(f'<div class="{cl}"><div class="nota-header">{d} | {ru} | {fi}</div><b>{um}</b><br>{tx}</div>', unsafe_allow_html=True)

# --- 6. AGENDA ---
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
    for t, d, r, pn, rid in eventi:
        st.markdown(f'<div class="card"><div class="nota-header">Data: {d}</div><b>{pn}</b> — {t.upper()}<br><i>{r}</i></div>', unsafe_allow_html=True)
        if st.session_state.role == "admin" and st.button(f"Rimuovi #{rid}", key=f"del_ev_{rid}"):
            db_run("DELETE FROM agenda WHERE row_id=?", (rid,), True); st.rerun()

# --- 7. TERAPIE ---
elif menu == "Terapie":
    pazienti = db_run("SELECT * FROM pazienti ORDER BY nome")
    for p_id, nome in pazienti:
        with st.expander(f"💊 TERAPIA: {nome.upper()}"):
            if st.session_state.role == "admin":
                f_t = st.text_input("Farmaco", key=f"f{p_id}")
                d_t = st.text_input("Dose", key=f"d{p_id}")
                m_t = st.text_input("Medico", key=f"m{p_id}")
                if st.button("Conferma", key=f"btn{p_id}"):
                    db_run("INSERT INTO terapie (p_id, farmaco, dosaggio, data, medico) VALUES (?,?,?,?,?)", (p_id, f_t, d_t, date.today().strftime("%d/%m/%Y"), m_t), True)
                    db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%Y-%m-%d %H:%M"), "Stabile", f"[CAMBIO TERAPIA] {f_t} ({d_t})", "SISTEMA", "ADMIN"), True)
                    st.rerun()
            for fa, do, da, me, rid in db_run("SELECT farmaco, dosaggio, data, medico, row_id FROM terapie WHERE p_id=?", (p_id,)):
                st.markdown(f'<div class="card terapia-card"><b>{fa}</b>: {do} <br><small>{da} — Dr. {me}</small></div>', unsafe_allow_html=True)

# --- 8. DOCUMENTI ---
elif menu == "Documenti":
    paz = db_run("SELECT * FROM pazienti ORDER BY nome")
    if paz:
        sel_p = st.selectbox("Paziente", [p[1] for p in paz])
        pid = [p[0] for p in paz if p[1] == sel_p][0]
        up = st.file_uploader("Carica File")
        if up and st.button("SALVA"):
            db_run("INSERT INTO documenti (p_id, nome_doc, file_blob, data) VALUES (?,?,?,?)", (pid, up.name, up.read(), date.today().strftime("%d/%m/%Y")), True); st.rerun()
        for n, b, d, rid in db_run("SELECT nome_doc, file_blob, data, row_id FROM documenti WHERE p_id=?", (pid,)):
            st.download_button(f"📥 Scarica: {n}", b, file_name=n, key=f"dl_{rid}")

# --- 9. GESTIONE ---
elif menu == "Gestione":
    st.subheader("Anagrafica Pazienti")
    if st.session_state.role == "admin":
        n_p = st.text_input("Nuovo Paziente")
        if st.button("AGGIUNGI"):
            if n_p: db_run("INSERT INTO pazienti (nome) VALUES (?)", (n_p,), True); st.rerun()
        st.divider()
        for pid, pnome in db_run("SELECT id, nome FROM pazienti ORDER BY nome"):
            with st.container():
                c1, c2, c3 = st.columns([4, 1, 1])
                new_n = c1.text_input(f"Modifica", value=pnome, label_visibility="collapsed", key=f"ed_{pid}")
                if c2.button("💾", key=f"sv_{pid}"):
                    db_run("UPDATE pazienti SET nome=? WHERE id=?", (new_n, pid), True); st.rerun()
                if c3.button("🗑️", key=f"dl_{pid}"):
                    db_run("DELETE FROM pazienti WHERE id=?", (pid,), True); st.rerun()
    else:
        st.warning("Sola lettura per utenti. Modifiche riservate all'Admin.")
        for pid, pnome in db_run("SELECT id, nome FROM pazienti ORDER BY nome"):
            st.markdown(f'<div class="card">👤 {pnome}</div>', unsafe_allow_html=True)
