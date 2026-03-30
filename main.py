import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date

# --- 1. CONFIGURAZIONE & STILE ---
st.set_page_config(page_title="REMS Connect PRO", layout="wide")

st.markdown("""
<style>
    .main-title {text-align: center; color: #1e3a8a; margin-bottom: 20px; font-weight: bold; font-family: sans-serif;}
    /* Stile Tabella Clinica */
    .clinica-table {width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 0.9rem; margin-top: 10px;}
    .clinica-table th {background-color: #1e3a8a; color: white; padding: 12px; text-align: left; border: 1px solid #e2e8f0;}
    .clinica-table td {padding: 10px; border: 1px solid #e2e8f0; vertical-align: top;}
    .row-agitato {background-color: #fef2f2; font-weight: bold;}
    .row-stabile {background-color: #ffffff;}
    .row-log {background-color: #fffbeb; font-style: italic; color: #92400e;}
    .badge-agitato {background-color: #ef4444; color: white; padding: 3px 8px; border-radius: 4px; font-size: 0.7rem;}
    .badge-stabile {background-color: #10b981; color: white; padding: 3px 8px; border-radius: 4px; font-size: 0.7rem;}
    /* Card per Agenda e Terapie */
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
    with st.container():
        pwd = st.text_input("Codice Accesso Operatore", type="password")
        if st.button("ACCEDI AL SISTEMA"):
            if pwd in ["rems2026", "admin2026"]:
                st.session_state.auth = True
                st.session_state.role = "admin" if pwd == "admin2026" else "user"
                st.rerun()
    st.stop()

st.markdown("<h1 class='main-title'>REMS CONNECT PRO</h1>", unsafe_allow_html=True)

# --- 4. SIDEBAR ---
menu = st.sidebar.radio("MENU PRINCIPALE", ["Monitoraggio", "Agenda", "Terapie", "Documenti", "Gestione"])
ruoli_lista = ["Tutti", "Psichiatra", "Infermiere", "OSS", "Psicologo", "Educatore", "SISTEMA"]

# --- 5. MONITORAGGIO (VISUALIZZAZIONE TABELLARE) ---
if menu == "Monitoraggio":
    pazienti = db_run("SELECT * FROM pazienti ORDER BY nome")
    for p_id, nome in pazienti:
        with st.expander(f"👤 PAZIENTE: {nome.upper()} - Diario Clinico"):
            # Inserimento Nota
            st.markdown("### + NUOVA ANNOTAZIONE")
            c1, c2, c3 = st.columns([1, 1, 1])
            r_ins = c1.selectbox("Tuo Ruolo", ruoli_lista[1:-1], key=f"r_i{p_id}")
            f_ins = c2.text_input("Firma Operatore", key=f"f_i{p_id}")
            u_ins = c3.selectbox("Stato Paziente", ["Stabile", "Cupo", "Deflesso", "Agitato"], key=f"u_i{p_id}")
            n_ins = st.text_area("Nota Clinica Dettagliata", key=f"n_i{p_id}", height=100)
            
            if st.button("REGISTRA NOTA", key=f"btn_s{p_id}"):
                if n_ins and f_ins:
                    data_ora = datetime.now().strftime("%d/%m/%y %H:%M")
                    db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, data_ora, u_ins, n_ins, r_ins, f_ins), True)
                    st.rerun()
            
            st.divider()
            
            # Filtri Ricerca
            st.markdown("### 🔍 FILTRI STORICO")
            f1, f2 = st.columns(2)
            d_filter = f1.date_input("Filtra per Data", value=None, key=f"d_f{p_id}")
            r_filter = f2.selectbox("Filtra per Ruolo", ruoli_lista, key=f"r_f{p_id}")
            
            sql = "SELECT data, umore, nota, ruolo, op FROM eventi WHERE id=?"
            pars = [p_id]
            if d_filter:
                sql += " AND data LIKE ?"
                pars.append(f"{d_filter.strftime('%d/%m/%y')}%")
            if r_filter != "Tutti":
                sql += " AND ruolo = ?"
                pars.append(r_filter)
            
            note_data = db_run(sql + " ORDER BY row_id DESC", tuple(pars))
            
            if note_data:
                # Tabella HTML
                table_html = """
                <table class="clinica-table">
                    <thead>
                        <tr>
                            <th>DATA & ORA</th>
                            <th>STATO</th>
                            <th>OPERATORE</th>
                            <th>ANNOTAZIONE CLINICA</th>
                        </tr>
                    </thead>
                    <tbody>
                """
                for d, um, tx, ru, fi in note_data:
                    r_style = "row-agitato" if um == "Agitato" else ("row-log" if "[CAMBIO" in tx else "row-stabile")
                    b_style = "badge-agitato" if um == "Agitato" else "badge-stabile"
                    
                    table_html += f"""
                    <tr class="{r_style}">
                        <td style="white-space:nowrap;">{d}</td>
                        <td><span class="{b_style}">{um.upper()}</span></td>
                        <td><b>{ru}</b><br>{fi}</td>
                        <td>{tx}</td>
                    </tr>
                    """
                table_html += "</tbody></table>"
                st.markdown(table_html, unsafe_allow_html=True)
            else:
                st.info("Nessuna annotazione trovata con i filtri selezionati.")

# --- 6. AGENDA ---
elif menu == "Agenda":
    st.subheader("📅 Registro Appuntamenti e Uscite")
    paz = db_run("SELECT * FROM pazienti ORDER BY nome")
    if paz:
        with st.expander("➕ REGISTRA NUOVO EVENTO"):
            p_map = {p[1]: p[0] for p in paz}
            ps = st.selectbox("Paziente", list(p_map.keys()))
            ts = st.selectbox("Tipo", ["Uscita", "Udienza", "Visita Medica", "Permesso", "Rientro"])
            ds = st.date_input("Data Evento", value=date.today())
            rs = st.text_input("Dettagli / Destinazione")
            if st.button("SALVA IN AGENDA"):
                db_run("INSERT INTO agenda (p_id,tipo,d_ora,note,rif) VALUES (?,?,?,?,?)", (p_map[ps], ts, str(ds), "", rs), True)
                st.rerun()
    
    st.divider()
    ev_list = db_run("SELECT a.tipo, a.d_ora, a.rif, p.nome, a.row_id FROM agenda a JOIN pazienti p ON a.p_id = p.id ORDER BY d_ora DESC")
    for t, d, r, pn, rid in ev_list:
        st.markdown(f'<div class="card"><b>{d}</b> | {pn} | <span style="color:#1e3a8a;">{t.upper()}</span><br><small>{r}</small></div>', unsafe_allow_html=True)
        if st.session_state.role == "admin" and st.button(f"Rimuovi #{rid}", key=f"del_ev_{rid}"):
            db_run("DELETE FROM agenda WHERE row_id=?", (rid,), True); st.rerun()

# --- 7. TERAPIE ---
elif menu == "Terapie":
    pazienti = db_run("SELECT * FROM pazienti ORDER BY nome")
    for p_id, nome in pazienti:
        with st.expander(f"💊 TERAPIA: {nome.upper()}"):
            if st.session_state.role == "admin":
                f_t = st.text_input("Farmaco", key=f"ft{p_id}")
                d_t = st.text_input("Dose", key=f"dt{p_id}")
                m_t = st.text_input("Medico", key=f"mt{p_id}")
                if st.button("Conferma Variazione", key=f"bt{p_id}"):
                    db_run("INSERT INTO terapie (p_id, farmaco, dosaggio, data, medico) VALUES (?,?,?,?,?)", (p_id, f_t, d_t, date.today().strftime("%d/%m/%Y"), m_t), True)
                    # Log automatico nel monitoraggio
                    msg = f"[CAMBIO TERAPIA] Inserito: {f_t} ({d_t}), Medico: {m_t}"
                    db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%y %H:%M"), "Stabile", msg, "SISTEMA", "ADMIN"), True)
                    st.rerun()
            
            st.divider()
            for fa, do, da, me, rid in db_run("SELECT farmaco, dosaggio, data, medico, row_id FROM terapie WHERE p_id=?", (p_id,)):
                st.success(f"**{fa}** - {do} | Prescritta: {da} da Dr. {me}")

# --- 8. DOCUMENTI ---
elif menu == "Documenti":
    paz = db_run("SELECT * FROM pazienti ORDER BY nome")
    if paz:
        sel_p = st.selectbox("Seleziona Paziente", [p[1] for p in paz])
        pid = [p[0] for p in paz if p[1] == sel_p][0]
        up = st.file_uploader("Carica Documento (PDF/JPG)")
        if up and st.button("SALVA FILE"):
            db_run("INSERT INTO documenti (p_id, nome_doc, file_blob, data) VALUES (?,?,?,?)", (pid, up.name, up.read(), date.today().strftime("%d/%m/%Y")), True); st.rerun()
        
        for n, b, d, rid in db_run("SELECT nome_doc, file_blob, data, row_id FROM documenti WHERE p_id=?", (pid,)):
            st.download_button(f"📥 Scarica: {n} ({d})", b, file_name=n, key=f"dl_{rid}")

# --- 9. GESTIONE ---
elif menu == "Gestione":
    st.subheader("Anagrafica Pazienti")
    if st.session_state.role == "admin":
        n_p = st.text_input("Nome Nuovo Paziente")
        if st.button("AGGIUNGI PAZIENTE"):
            if n_p: db_run("INSERT INTO pazienti (nome) VALUES (?)", (n_p,), True); st.rerun()
        st.divider()
        for pid, pnome in db_run("SELECT id, nome FROM pazienti ORDER BY nome"):
            c1, c2, c3 = st.columns([4, 1, 1])
            new_n = c1.text_input("Modifica", value=pnome, label_visibility="collapsed", key=f"ed_{pid}")
            if c2.button("💾", key=f"sv_{pid}"):
                db_run("UPDATE pazienti SET nome=? WHERE id=?", (new_n, pid), True); st.rerun()
            if c3.button("🗑️", key=f"dl_{pid}"):
                db_run("DELETE FROM pazienti WHERE id=?", (pid,), True); st.rerun()
    else:
        st.warning("Accesso in sola lettura. Solo l'Amministratore può modificare i dati anagrafici.")
        for pid, pnome in db_run("SELECT id, nome FROM pazienti ORDER BY nome"):
            st.markdown(f"👤 {pnome}")
