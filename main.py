import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date

# --- 1. CONFIGURAZIONE & STILE ---
st.set_page_config(page_title="REMS Connect PRO", layout="wide")

st.markdown("""
<style>
    .main-title {text-align: center; color: #1e3a8a; margin-bottom: 20px; font-weight: bold; font-family: sans-serif;}
    .clinica-table {width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 0.9rem; margin-top: 10px; background-color: white;}
    .clinica-table th {background-color: #1e3a8a; color: white; padding: 12px; text-align: left; border: 1px solid #e2e8f0;}
    .clinica-table td {padding: 10px; border: 1px solid #e2e8f0; vertical-align: top;}
    
    /* Colori delle Righe in base allo Stato */
    .row-agitato {background-color: #fef2f2 !important; border-left: 5px solid #ef4444 !important;}
    .row-deflesso {background-color: #f0f9ff !important; border-left: 5px solid #3b82f6 !important;}
    .row-cupo {background-color: #f8fafc !important; border-left: 5px solid #64748b !important; color: #475569;}
    .row-stabile {background-color: #ffffff; border-left: 5px solid #10b981 !important;}
    .row-log {background-color: #fffbeb !important; font-style: italic; border-left: 5px solid #f59e0b !important;}

    /* Badge Colorati per Umore */
    .badge {padding: 4px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: bold; color: white; display: inline-block;}
    .b-agitato {background-color: #ef4444;}
    .b-deflesso {background-color: #3b82f6;}
    .b-cupo {background-color: #64748b;}
    .b-stabile {background-color: #10b981;}
    .b-sistema {background-color: #f59e0b;}

    .card {padding: 12px; margin: 5px 0; border-radius: 8px; background: #f8fafc; border-left: 5px solid #64748b; box-shadow: 0 1px 3px rgba(0,0,0,0.1);}
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
    st.markdown("<h1 class='main-title'>REMS CONNECT PRO</h1>", unsafe_allow_html=True)
    with st.form("login_panel"):
        pwd = st.text_input("Codice Accesso", type="password")
        if st.form_submit_button("ENTRA"):
            if pwd in ["rems2026", "admin2026"]:
                st.session_state.auth = True
                st.session_state.role = "admin" if pwd == "admin2026" else "user"
                st.rerun()
    st.stop()

# --- 4. NAVIGAZIONE ---
menu = st.sidebar.radio("NAVIGAZIONE", ["Monitoraggio", "Agenda", "Terapie", "Documenti", "Gestione"])
ruoli_lista = ["Tutti", "Psichiatra", "Infermiere", "OSS", "Psicologo", "Educatore", "SISTEMA"]

# --- 5. MONITORAGGIO ---
if menu == "Monitoraggio":
    pazienti = db_run("SELECT * FROM pazienti ORDER BY nome")
    for p_id, nome in pazienti:
        with st.expander(f"👤 DIARIO: {nome.upper()}"):
            # Inserimento
            st.write("### 📝 Nuova Nota")
            c1, c2, c3 = st.columns(3)
            r_ins = c1.selectbox("Ruolo", ruoli_lista[1:-1], key=f"r{p_id}")
            f_ins = c2.text_input("Firma", key=f"f{p_id}")
            u_ins = c3.selectbox("Umore", ["Stabile", "Cupo", "Deflesso", "Agitato"], key=f"u{p_id}")
            n_ins = st.text_area("Annotazione Clinica", key=f"n{p_id}")
            
            if st.button("SALVA", key=f"b{p_id}"):
                if n_ins and f_ins:
                    db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", 
                           (p_id, datetime.now().strftime("%d/%m/%y %H:%M"), u_ins, n_ins, r_ins, f_ins), True)
                    st.rerun()

            st.divider()
            
            # Tabella con colori differenziati
            note = db_run("SELECT data, umore, nota, ruolo, op FROM eventi WHERE id=? ORDER BY row_id DESC", (p_id,))
            if note:
                html = '<table class="clinica-table"><thead><tr><th>DATA</th><th>UMORE</th><th>OPERATORE</th><th>NOTA</th></tr></thead><tbody>'
                for d, um, tx, ru, fi in note:
                    # Selezione Classe Riga e Badge
                    if um == "Agitato": r_cl, b_cl = "row-agitato", "b-agitato"
                    elif um == "Deflesso": r_cl, b_cl = "row-deflesso", "b-deflesso"
                    elif um == "Cupo": r_cl, b_cl = "row-cupo", "b-cupo"
                    elif "[CAMBIO" in tx: r_cl, b_cl = "row-log", "b-sistema"
                    else: r_cl, b_cl = "row-stabile", "b-stabile"
                    
                    html += f'''
                    <tr class="{r_cl}">
                        <td style="white-space:nowrap;">{d}</td>
                        <td><span class="badge {b_cl}">{um.upper()}</span></td>
                        <td><b>{ru}</b><br><small>{fi}</small></td>
                        <td>{tx}</td>
                    </tr>'''
                html += '</tbody></table>'
                st.markdown(html, unsafe_allow_html=True)

# --- (PAGINE RESTANTI IDENTICHE PER FUNZIONALITÀ) ---
elif menu == "Agenda":
    st.subheader("📅 Agenda")
    paz = db_run("SELECT * FROM pazienti ORDER BY nome")
    if paz:
        with st.expander("Nuovo Evento"):
            ps = st.selectbox("Paziente", [p[1] for p in paz])
            ts = st.selectbox("Tipo", ["Uscita", "Udienza", "Visita", "Permesso"])
            ds = st.date_input("Data")
            rs = st.text_input("Note")
            if st.button("AGGIUNGI"):
                pid = [p[0] for p in paz if p[1] == ps][0]
                db_run("INSERT INTO agenda (p_id,tipo,d_ora,note,rif) VALUES (?,?,?,?,?)", (pid, ts, str(ds), "", rs), True)
                st.rerun()
    for t, d, r, pn, rid in db_run("SELECT a.tipo, a.d_ora, a.rif, p.nome, a.row_id FROM agenda a JOIN pazienti p ON a.p_id = p.id ORDER BY d_ora DESC"):
        st.markdown(f'<div class="card"><b>{d}</b> | {pn} | {t.upper()}<br>{r}</div>', unsafe_allow_html=True)

elif menu == "Terapie":
    pazienti = db_run("SELECT * FROM pazienti ORDER BY nome")
    for p_id, nome in pazienti:
        with st.expander(f"💊 TERAPIA: {nome.upper()}"):
            if st.session_state.role == "admin":
                f, d, m = st.text_input("Farmaco", key=f"f{p_id}"), st.text_input("Dose", key=f"d{p_id}"), st.text_input("Medico", key=f"m{p_id}")
                if st.button("Salva", key=f"btn{p_id}"):
                    db_run("INSERT INTO terapie (p_id, farmaco, dosaggio, data, medico) VALUES (?,?,?,?,?)", (p_id, f, d, date.today().strftime("%d/%m/%Y"), m), True)
                    db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%y %H:%M"), "Stabile", f"[CAMBIO TERAPIA] {f} ({d})", "SISTEMA", "ADMIN"), True)
                    st.rerun()
            for fa, do, da, me, rid in db_run("SELECT farmaco, dosaggio, data, medico, row_id FROM terapie WHERE p_id=?", (p_id,)):
                st.success(f"**{fa}** - {do} (Dal: {da})")

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

elif menu == "Gestione":
    if st.session_state.role == "admin":
        nuovo = st.text_input("Nuovo Paziente")
        if st.button("AGGIUNGI"):
            if nuovo: db_run("INSERT INTO pazienti (nome) VALUES (?)", (nuovo,), True); st.rerun()
        for pid, pnome in db_run("SELECT id, nome FROM pazienti ORDER BY nome"):
            st.write(f"👤 {pnome}")
