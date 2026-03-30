import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date

# --- 1. CONFIGURAZIONE & STILE ---
st.set_page_config(page_title="REMS Connect PRO", layout="wide")

st.markdown("""
<style>
    .main-title {text-align: center; color: #1e3a8a; margin-bottom: 20px; font-weight: bold;}
    /* Tabella Clinica */
    .clinica-table {width: 100%; border-collapse: collapse; font-size: 0.85rem; background-color: white; margin-top: 10px;}
    .clinica-table th {background-color: #1e3a8a; color: white; padding: 10px; text-align: left; border: 1px solid #ddd;}
    .clinica-table td {padding: 8px; border: 1px solid #e2e8f0; vertical-align: top;}
    
    /* Colori Righe */
    .row-stabile {background-color: #ffffff; border-left: 5px solid #10b981 !important;}
    .row-med {background-color: #f0fdf4 !important; border-left: 5px solid #22c55e !important;}
    .row-alert {background-color: #fffbeb !important; border-left: 5px solid #f59e0b !important;}
    .row-agitato {background-color: #fef2f2 !important; border-left: 5px solid #ef4444 !important;}
    
    .saldo-box {padding: 15px; border-radius: 10px; background-color: #f8fafc; text-align: center; border: 2px solid #1e3a8a; margin-bottom: 15px;}
    .entrata {color: #10b981; font-weight: bold;}
    .uscita {color: #ef4444; font-weight: bold;}
</style>
""", unsafe_allow_html=True)

# --- 2. DATABASE ---
DB_NAME = "rems_connect_data.db"

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, umore TEXT, nota TEXT, ruolo TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dosaggio TEXT, data TEXT, medico TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS soldi (p_id INTEGER, data TEXT, desc TEXT, importo REAL, tipo TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute(query, params)
        if commit: conn.commit()
        return cur.fetchall()

# --- 3. LOGIN ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.markdown("<h1 class='main-title'>REMS CONNECT PRO</h1>", unsafe_allow_html=True)
    with st.form("login"):
        pwd = st.text_input("Codice Accesso", type="password")
        if st.form_submit_button("ENTRA"):
            if pwd in ["rems2026", "admin2026"]:
                st.session_state.auth = True
                st.session_state.role = "admin" if pwd == "admin2026" else "user"
                st.rerun()
    st.stop()

# --- 4. NAVIGAZIONE ---
menu = st.sidebar.radio("NAVIGAZIONE", ["Monitoraggio", "Equipe", "Agenda", "Documenti", "Gestione"])

# --- 5. MONITORAGGIO ---
if menu == "Monitoraggio":
    pazienti = db_run("SELECT * FROM pazienti ORDER BY nome")
    for p_id, nome in pazienti:
        with st.expander(f"👤 DIARIO CLINICO: {nome.upper()}"):
            note = db_run("SELECT data, umore, nota, ruolo, op FROM eventi WHERE id=? ORDER BY row_id DESC", (p_id,))
            if note:
                html = '<table class="clinica-table"><thead><tr><th>DATA</th><th>STATO</th><th>RUOLO</th><th>NOTA</th></tr></thead><tbody>'
                for d, um, tx, ru, fi in note:
                    r_cl = "row-med" if "[REPORT]" in tx or "[SOMM]" in tx else ("row-alert" if "[CAMBIO]" in tx else ("row-agitato" if um == "Agitato" else "row-stabile"))
                    html += f'<tr class="{r_cl}"><td>{d}</td><td>{um}</td><td><b>{ru}</b><br>{fi}</td><td>{tx}</td></tr>'
                st.markdown(html + '</tbody></table>', unsafe_allow_html=True)

# --- 6. AREA EQUIPE ---
elif menu == "Equipe":
    figura = st.sidebar.selectbox("Ruolo Professionale", ["Psichiatra", "Infermiere", "Educatore", "Psicologo", "Assistente Sociale", "OSS", "Opsi"])
    
    paz = db_run("SELECT * FROM pazienti ORDER BY nome")
    if not paz:
        st.warning("Nessun paziente in archivio. Vai in 'Gestione' per aggiungerne uno.")
    else:
        sel_p = st.selectbox("Seleziona Paziente", [p[1] for p in paz])
        p_id = [p[0] for p in paz if p[1] == sel_p][0]

        st.divider()

        # --- PSICHIATRA ---
        if figura == "Psichiatra":
            st.subheader("📋 Gestione Terapie")
            with st.form("new_med"):
                f = st.text_input("Farmaco")
                d = st.text_input("Dosaggio")
                m = st.text_input("Medico")
                if st.form_submit_button("AGGIUNGI TERAPIA"):
                    db_run("INSERT INTO terapie (p_id, farmaco, dosaggio, data, medico) VALUES (?,?,?,?,?)", (p_id, f, d, date.today().strftime("%d/%m/%Y"), m), True)
                    db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%y %H:%M"), "Stabile", f"⚠️ [CAMBIO TERAPIA] {f} {d}", "Psichiatra", m), True)
                    st.rerun()
            
            st.write("---")
            t_attive = db_run("SELECT farmaco, dosaggio, medico, row_id FROM terapie WHERE p_id=?", (p_id,))
            for fa, do, me, rid in t_attive:
                c1, c2 = st.columns([5,1])
                c1.info(f"**{fa}** - {do} (Prescritta da: {me})")
                if c2.button("🗑️", key=rid):
                    db_run("DELETE FROM terapie WHERE row_id=?", (rid,), True); st.rerun()

        # --- INFERMIERE ---
        elif figura == "Infermiere":
            st.subheader("💉 Somministrazione Terapia")
            inf_sig = st.text_input("La tua firma")
            
            t_lista = db_run("SELECT farmaco, dosaggio, row_id FROM terapie WHERE p_id=?", (p_id,))
            for f, d, rid in t_lista:
                with st.container():
                    c1, c2, c3 = st.columns([3, 3, 2])
                    c1.markdown(f"**{f}**\n<small>{d}</small>", unsafe_allow_html=True)
                    esito = c2.selectbox("Esito", ["Assunta", "Parziale", "Rifiutata"], key=f"es_{rid}")
                    if c3.button("CONVALIDA", key=f"inf_{rid}"):
                        if inf_sig:
                            rep = f"[REPORT SOMMINISTRAZIONE] {f} ({d}) -> {esito}"
                            db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%y %H:%M"), "Stabile", rep, "Infermiere", inf_sig), True)
                            st.rerun()
                        else: st.error("Firma obbligatoria!")

            st.write("### 📑 Report Somministrazioni Odierne")
            # Ottimizzazione filtro: carichiamo tutti i report e li mostriamo in tabella
            reps = db_run("SELECT data, nota, op FROM eventi WHERE id=? AND nota LIKE '%[REPORT]%' ORDER BY row_id DESC LIMIT 10", (p_id,))
            if reps:
                df = pd.DataFrame(reps, columns=["Data/Ora", "Dettaglio", "Infermiere"])
                st.table(df)
            else:
                st.info("Nessuna somministrazione registrata oggi.")

        # --- EDUCATORI ---
        elif figura == "Educatore":
            st.subheader("💰 Gestione Soldi")
            # Calcolo Saldo
            movs = db_run("SELECT importo, tipo FROM soldi WHERE p_id=?", (p_id,))
            saldo = sum([m[0] if m[1] == "Entrata" else -m[0] for m in movs])
            st.markdown(f'<div class="saldo-box"><h5>SALDO</h5><h2>€ {saldo:.2f}</h2></div>', unsafe_allow_html=True)
            
            with st.expander("Nuova Operazione"):
                t = st.radio("Tipo", ["Entrata", "Uscita"], horizontal=True)
                i = st.number_input("Importo €", min_value=0.0, step=1.0)
                c = st.text_input("Causale")
                f = st.text_input("Firma")
                if st.button("REGISTRA MOVIMENTO"):
                    db_run("INSERT INTO soldi (p_id, data, desc, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, date.today().strftime("%d/%m/%Y"), c, i, t, f), True); st.rerun()
            
            st.write("#### 📊 Estratto Conto")
            storico = db_run("SELECT data, desc, importo, tipo, op FROM soldi WHERE p_id=? ORDER BY row_id DESC", (p_id,))
            if storico:
                h = '<table class="clinica-table"><tr><th>DATA</th><th>CAUSALE</th><th>ENTRATA</th><th>USCITA</th><th>OP</th></tr>'
                for d, ds, im, tp, op in storico:
                    e = f"€ {im:.2f}" if tp == "Entrata" else ""
                    u = f"€ {im:.2f}" if tp == "Uscita" else ""
                    h += f'<tr><td>{d}</td><td>{ds}</td><td class="entrata">{e}</td><td class="uscita">{u}</td><td>{op}</td></tr>'
                st.markdown(h + '</table>', unsafe_allow_html=True)

# --- GESTIONE ---
elif menu == "Gestione":
    st.subheader("⚙️ Amministrazione")
    nuovo = st.text_input("Nome Nuovo Paziente")
    if st.button("SALVA"):
        if nuovo: db_run("INSERT INTO pazienti (nome) VALUES (?)", (nuovo,), True); st.rerun()
    st.write("---")
    for pid, n in db_run("SELECT id, nome FROM pazienti ORDER BY nome"):
        st.write(f"👤 {n}")
