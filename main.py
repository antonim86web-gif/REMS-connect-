import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date
import plotly.express as px

# --- 1. CONFIGURAZIONE & STILE ---
st.set_page_config(page_title="REMS Connect PRO", layout="wide")

st.markdown("""
<style>
    .card {padding: 12px; margin: 8px 0; border-radius: 10px; background: white; border-left: 5px solid #64748b; box-shadow: 0 2px 4px rgba(0,0,0,0.05);}
    .nota-header {font-size: 0.75rem; color: #64748b; border-bottom: 1px solid #f1f5f9; margin-bottom: 5px;}
    .agitato {border-left-color: #ef4444 !important; background-color: #fef2f2 !important;}
    .terapia-card {border-left-color: #10b981 !important; background-color: #f0fdf4 !important;}
    .log-cambio {border-left: 5px solid #f59e0b !important; background-color: #fffbeb !important; font-style: italic;}
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
    pwd = st.text_input("Accesso", type="password")
    if st.button("Entra"):
        if pwd in ["rems2026", "admin2026"]:
            st.session_state.auth = True
            st.session_state.role = "admin" if "admin" in pwd else "user"
            st.rerun()
    st.stop()

# --- 4. SIDEBAR ---
menu = st.sidebar.radio("Menu", ["Monitoraggio", "Calendario Attività", "Statistiche Cliniche", "Terapie", "Agenda", "Documenti", "Gestione"])

# --- MONITORAGGIO CON CERCA ---
if menu == "Monitoraggio":
    pazienti = db_run("SELECT * FROM pazienti ORDER BY nome")
    for p_id, nome in pazienti:
        with st.expander(f"👤 {nome.upper()} - Diario"):
            c1, c2 = st.columns(2)
            r = c1.selectbox("Ruolo", ["Psichiatra", "Infermiere", "OSS", "Psicologo"], key=f"r{p_id}")
            f = c2.text_input("Firma", key=f"f{p_id}")
            u = st.radio("Umore", ["Stabile", "Cupo", "Deflesso", "Agitato"], key=f"u{p_id}", horizontal=True)
            n = st.text_area("Nota", key=f"n{p_id}")
            if st.button("Salva", key=f"b{p_id}"):
                db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%Y-%m-%d %H:%M"), u, n, r, f), True); st.rerun()
            
            st.divider()
            st.markdown("🔍 **Filtra Note**")
            sq = st.text_input("Cerca parola...", key=f"sq{p_id}")
            sql = "SELECT data, umore, nota, ruolo, op FROM eventi WHERE id=?"
            pars = [p_id]
            if sq: sql += " AND nota LIKE ?"; pars.append(f"%{sq}%")
            for d, um, tx, ru, fi in db_run(sql + " ORDER BY data DESC", tuple(pars)):
                cl = f"card {'log-cambio' if '[CAMBIO' in tx else ''} {'agitato' if um=='Agitato' else ''}"
                st.markdown(f'<div class="{cl}"><div class="nota-header">{d} | {ru} | {fi}</div><b>{um}</b><br>{tx}</div>', unsafe_allow_html=True)

# --- CALENDARIO ATTIVITÀ ---
elif menu == "Calendario Attività":
    st.subheader("📅 Frequenza Annotazioni")
    paz = db_run("SELECT id, nome FROM pazienti")
    if paz:
        sel_p = st.selectbox("Paziente", [p[1] for p in paz])
        pid = [p[0] for p in paz if p[1] == sel_p][0]
        res = db_run("SELECT data FROM eventi WHERE id=?", (pid,))
        if res:
            df = pd.DataFrame(res, columns=["Data"])
            df['Giorno'] = pd.to_datetime(df['Data']).dt.date
            cal_df = df.groupby('Giorno').size().reset_index(name='Conteggio')
            st.plotly_chart(px.bar(cal_df, x='Giorno', y='Conteggio', title="Note inserite per giorno"), use_container_width=True)
        else: st.info("Nessun dato temporale.")

# --- STATISTICHE CLINICHE ---
elif menu == "Statistiche Cliniche":
    st.subheader("📊 Analisi Umore e Andamento")
    paz = db_run("SELECT id, nome FROM pazienti")
    if paz:
        sel_p = st.selectbox("Paziente", [p[1] for p in paz])
        pid = [p[0] for p in paz if p[1] == sel_p][0]
        res = db_run("SELECT data, umore FROM eventi WHERE id=? AND nota NOT LIKE '[CAMBIO%'", (pid,))
        if res:
            df = pd.DataFrame(res, columns=["Data", "Umore"])
            df['Data'] = pd.to_datetime(df['Data'])
            c1, c2 = st.columns(2)
            with c1: st.plotly_chart(px.pie(df, names="Umore", hole=0.3), use_container_width=True)
            with c2:
                df['Livello'] = df['Umore'].map({"Agitato": 0, "Cupo": 1, "Deflesso": 2, "Stabile": 3})
                st.plotly_chart(px.line(df, x="Data", y="Livello", markers=True), use_container_width=True)

# --- TERAPIE, AGENDA, DOCUMENTI, GESTIONE (Restano come prima) ---
elif menu == "Terapie":
    for p_id, nome in db_run("SELECT * FROM pazienti ORDER BY nome"):
        with st.expander(f"💊 {nome.upper()}"):
            if st.session_state.role == "admin":
                f, d, m = st.text_input("Farmaco", key=f"f{p_id}"), st.text_input("Dose", key=f"d{p_id}"), st.text_input("Medico", key=f"m{p_id}")
                if st.button("Aggiorna", key=f"btn{p_id}"):
                    db_run("INSERT INTO terapie (p_id, farmaco, dosaggio, data, medico) VALUES (?,?,?,?,?)", (p_id, f, d, date.today().strftime("%d/%m/%Y"), m), True)
                    db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%Y-%m-%d %H:%M"), "Stabile", f"[CAMBIO TERAPIA] {f} ({d})", "SISTEMA", "ADMIN"), True)
                    st.rerun()
            for fa, do, da, me, rid in db_run("SELECT farmaco, dosaggio, data, medico, row_id FROM terapie WHERE p_id=?", (p_id,)):
                st.markdown(f'<div class="card terapia-card"><b>{fa}</b>: {do} ({da} - {me})</div>', unsafe_allow_html=True)

elif menu == "Agenda":
    for t, d, r, pn, rid in db_run("SELECT a.tipo, a.d_ora, a.rif, p.nome, a.row_id FROM agenda a JOIN pazienti p ON a.p_id = p.id ORDER BY d_ora ASC"):
        st.markdown(f'<div class="card"><b>{pn}</b>: {t} il {d} <br> {r}</div>', unsafe_allow_html=True)

elif menu == "Documenti":
    paz = db_run("SELECT * FROM pazienti")
    if paz:
        sel_p = st.selectbox("Paziente", [p[1] for p in paz])
        pid = [p[0] for p in paz if p[1] == sel_p][0]
        up = st.file_uploader("File")
        if up and st.button("Carica"):
            db_run("INSERT INTO documenti (p_id, nome_doc, file_blob, data) VALUES (?,?,?,?)", (pid, up.name, up.read(), date.today().strftime("%d/%m/%Y")), True); st.rerun()
        for n, b, d, rid in db_run("SELECT nome_doc, file_blob, data, row_id FROM documenti WHERE p_id=?", (pid,)):
            st.download_button(f"📥 {n}", b, file_name=n, key=f"dl_{rid}")

elif menu == "Gestione":
    n = st.text_input("Nuovo Paziente")
    if st.button("Aggiungi"): db_run("INSERT INTO pazienti (nome) VALUES (?)", (n,), True); st.rerun()
    for pid, pnome in db_run("SELECT id, nome FROM pazienti"):
        st.write(f"👤 {pnome}")
        if st.button("Elimina", key=f"del{pid}"): db_run("DELETE FROM pazienti WHERE id=?", (pid,), True); st.rerun()
