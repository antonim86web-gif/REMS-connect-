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
    .row-agitato {background-color: #fef2f2 !important; font-weight: bold; border-left: 5px solid #ef4444 !important;}
    .row-stabile {background-color: #ffffff;}
    .row-log {background-color: #fffbeb !important; font-style: italic; color: #92400e; border-left: 5px solid #f59e0b !important;}
    .badge-agitato {background-color: #ef4444; color: white; padding: 4px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: bold; display: inline-block;}
    .badge-stabile {background-color: #10b981; color: white; padding: 4px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: bold; display: inline-block;}
    .badge-altri {background-color: #64748b; color: white; padding: 4px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: bold; display: inline-block;}
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

# --- 3. GESTIONE LOGIN ---
if 'auth' not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.markdown("<h1 class='main-title'>REMS CONNECT PRO</h1>", unsafe_allow_html=True)
    with st.form("login_form"):
        pwd = st.text_input("Inserire Codice Accesso", type="password")
        submit = st.form_submit_button("ACCEDI")
        if submit:
            if pwd in ["rems2026", "admin2026"]:
                st.session_state.auth = True
                st.session_state.role = "admin" if pwd == "admin2026" else "user"
                st.rerun()
            else:
                st.error("Codice Errato")
    st.stop() # Blocca qui se non autenticato

# --- 4. NAVIGAZIONE (Visibile solo dopo Login) ---
st.markdown("<h1 class='main-title'>REMS CONNECT PRO</h1>", unsafe_allow_html=True)
menu = st.sidebar.radio("NAVIGAZIONE", ["Monitoraggio", "Agenda", "Terapie", "Documenti", "Gestione"])
ruoli_lista = ["Tutti", "Psichiatra", "Infermiere", "OSS", "Psicologo", "Educatore", "SISTEMA"]

# --- 5. MONITORAGGIO ---
if menu == "Monitoraggio":
    pazienti = db_run("SELECT * FROM pazienti ORDER BY nome")
    for p_id, nome in pazienti:
        with st.expander(f"👤 DIARIO CLINICO: {nome.upper()}"):
            st.write("### 📝 Nuova Annotazione")
            c1, c2, c3 = st.columns([1, 1, 1])
            r_ins = c1.selectbox("Ruolo", ruoli_lista[1:-1], key=f"r_in_{p_id}")
            f_ins = c2.text_input("Firma", key=f"f_in_{p_id}")
            u_ins = c3.selectbox("Stato/Umore", ["Stabile", "Cupo", "Deflesso", "Agitato"], key=f"u_in_{p_id}")
            n_ins = st.text_area("Nota Clinica", key=f"n_in_{p_id}")
            
            if st.button("SALVA NOTA", key=f"btn_s_{p_id}"):
                if n_ins and f_ins:
                    data_ora = datetime.now().strftime("%d/%m/%y %H:%M")
                    db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, data_ora, u_ins, n_ins, r_ins, f_ins), True)
                    st.rerun()
            st.divider()
            
            st.write("### 🔍 Filtra Storico")
            f1, f2 = st.columns(2)
            d_filtro = f1.date_input("Per Data", value=None, key=f"d_f_{p_id}")
            r_filtro = f2.selectbox("Per Ruolo", ruoli_lista, key=f"r_f_{p_id}")
            
            sql = "SELECT data, umore, nota, ruolo, op FROM eventi WHERE id=?"
            pars = [p_id]
            if d_filtro:
                sql += " AND data LIKE ?"
                pars.append(f"{d_filtro.strftime('%d/%m/%y')}%")
            if r_filtro != "Tutti":
                sql += " AND ruolo = ?"
                pars.append(r_filtro)
            
            note_storico = db_run(sql + " ORDER BY row_id DESC", tuple(pars))
            
            if note_storico:
                html = '<table class="clinica-table"><thead><tr><th>DATA</th><th>STATO</th><th>OPERATORE</th><th>ANNOTAZIONE</th></tr></thead><tbody>'
                for d, um, tx, ru, fi in note_storico:
                    r_class = "row-agitato" if um == "Agitato" else ("row-log" if "[CAMBIO" in tx else "row-stabile")
                    b_class = "badge-agitato" if um == "Agitato" else "badge-stabile"
                    html += f'<tr class="{r_class}"><td>{d}</td><td><span class="{b_class}">{um.upper()}</span></td><td><b>{ru}</b><br>{fi}</td><td>{tx}</td></tr>'
                html += '</tbody></table>'
                st.markdown(html, unsafe_allow_html=True)
            else:
                st.info("Nessuna nota trovata.")

# --- ALTRE PAGINE (IDENTICHE PER COMPLETEZZA) ---
elif menu == "Agenda":
    st.subheader("📅 Appuntamenti")
    paz = db_run("SELECT * FROM pazienti ORDER BY nome")
    if paz:
        with st.expander("➕ Nuovo Evento"):
            p_map = {p[1]: p[0] for p in paz}
            ps = st.selectbox("Paziente", list(p_map.keys()))
            ts = st.selectbox("Tipo", ["Uscita", "Udienza", "Visita", "Permesso", "Rientro"])
            ds = st.date_input("Data", value=date.today())
            rs = st.text_input("Note")
            if st.button("AGGIUNGI"):
                db_run("INSERT INTO agenda (p_id,tipo,d_ora,note,rif) VALUES (?,?,?,?,?)", (p_map[ps], ts, str(ds), "", rs), True)
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
                    st.rerun()
            for fa, do, da, me, rid in db_run("SELECT farmaco, dosaggio, data, medico, row_id FROM terapie WHERE p_id=?", (p_id,)):
                st.success(f"**{fa}** - {do} (Medico: {me})")

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
            c1, c2 = st.columns([5, 1])
            c1.write(f"👤 {pnome}")
            if c2.button("🗑️", key=f"del_{pid}"):
                db_run("DELETE FROM pazienti WHERE id=?", (pid,), True); st.rerun()
    else:
        st.warning("Accesso Admin richiesto.")
