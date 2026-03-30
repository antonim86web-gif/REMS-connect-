import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="REMS Connect PRO", layout="wide")

st.markdown("""
<style>
    .main-title {text-align: center; color: #1e3a8a; font-weight: bold; margin-bottom:20px;}
    .status-ok {color: #10b981; font-weight: bold; background: #ecfdf5; padding: 5px; border-radius: 5px;}
    .clinica-table {width: 100%; border-collapse: collapse; font-size: 0.85rem;}
    .clinica-table tr {border-bottom: 1px solid #eee;}
    .clinica-table td {padding: 10px; vertical-align: top;}
    .saldo-box {padding: 15px; border-radius: 10px; background-color: #f8fafc; text-align: center; border: 2px solid #1e3a8a;}
</style>
""", unsafe_allow_html=True)

# --- 2. DATABASE CON MIGRAZIONE AUTOMATICA ---
DB_NAME = "rems_connect_data.db"

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        # Creazione tabelle base
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, umore TEXT, nota TEXT, ruolo TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dosaggio TEXT, medico TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS soldi (p_id INTEGER, data TEXT, desc TEXT, importo REAL, tipo TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        
        # MIGRAZIONE: Aggiunge la colonna 'turni' se manca
        try:
            cur.execute("ALTER TABLE terapie ADD COLUMN turni TEXT")
        except sqlite3.OperationalError:
            pass # La colonna esiste già

        if query:
            cur.execute(query, params)
        if commit: conn.commit()
        return cur.fetchall()

# Inizializzazione DB
db_run("")

# --- 3. LOGIN ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.markdown("<h1 class='main-title'>REMS CONNECT PRO</h1>", unsafe_allow_html=True)
    with st.form("login"):
        pwd = st.text_input("Codice Accesso", type="password")
        if st.form_submit_button("ENTRA"):
            if pwd in ["rems2026", "admin2026"]:
                st.session_state.auth = True
                st.rerun()
    st.stop()

# --- 4. NAVIGAZIONE ---
menu = st.sidebar.radio("MENU", ["Monitoraggio", "Equipe", "Gestione"])

if menu == "Equipe":
    figura = st.sidebar.selectbox("Ruolo", ["Psichiatra", "Infermiere", "Educatore", "Psicologo"])
    paz = db_run("SELECT * FROM pazienti ORDER BY nome")
    
    if paz:
        sel_p = st.selectbox("Seleziona Paziente", [p[1] for p in paz])
        p_id = [p[0] for p in paz if p[1] == sel_p][0]
        st.divider()

        # --- PSICHIATRA ---
        if figura == "Psichiatra":
            st.subheader("📋 Prescrizione Terapia")
            with st.form("presc_form"):
                f = st.text_input("Farmaco")
                d = st.text_input("Dosaggio/Orario")
                st.write("Turni di somministrazione:")
                c1, c2, c3 = st.columns(3)
                tm = c1.checkbox("Mattina")
                tp = c2.checkbox("Pomeriggio")
                tn = c3.checkbox("Notte")
                m = st.text_input("Medico")
                if st.form_submit_button("SALVA"):
                    t_list = []
                    if tm: t_list.append("M")
                    if tp: t_list.append("P")
                    if tn: t_list.append("N")
                    db_run("INSERT INTO terapie (p_id, farmaco, dosaggio, turni, medico) VALUES (?,?,?,?,?)", 
                           (p_id, f, d, ",".join(t_list), m), True)
                    db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", 
                           (p_id, datetime.now().strftime("%d/%m/%y %H:%M"), "Stabile", f"⚠️ [CAMBIO] {f} ({d})", "Psichiatra", m), True)
                    st.rerun()

        # --- INFERMIERE ---
        elif figura == "Infermiere":
            st.subheader("💉 Gestione Turni")
            c_d, c_t = st.columns(2)
            d_sel = c_d.date_input("Data", date.today())
            t_sel = c_t.selectbox("Turno", ["Mattina", "Pomeriggio", "Notte"])
            sigla = t_sel[0]
            inf_f = st.text_input("Firma Infermiere")
            
            st.write(f"**Farmaci turno {t_sel}:**")
            data_s = d_sel.strftime("%d/%m/%Y")
            
            terapie = db_run("SELECT farmaco, dosaggio, turni, row_id FROM terapie WHERE p_id=?", (p_id,))
            for f, d, turni_f, rid in terapie:
                if turni_f and sigla in turni_f:
                    tag = f"[REP_{sigla}] {f}"
                    fatto = db_run("SELECT op FROM eventi WHERE id=? AND nota LIKE ? AND data LIKE ?", (p_id, f"%{tag}%", f"{data_s}%"))
                    
                    with st.container():
                        col1, col2, col3 = st.columns([3, 3, 2])
                        col1.markdown(f"**{f}**<br><small>{d}</small>", unsafe_allow_html=True)
                        if fatto:
                            col2.markdown(f"<div class='status-ok'>✅ Firmato: {fatto[0][0]}</div>", unsafe_allow_html=True)
                        else:
                            est = col2.selectbox("Stato", ["Assunta", "Parziale", "Rifiutata"], key=f"e{rid}{sigla}")
                            if col3.button("CONVALIDA", key=f"b{rid}{sigla}"):
                                if inf_f:
                                    db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", 
                                           (p_id, f"{data_s} {datetime.now().strftime('%H:%M')}", "Stabile", f"{tag} -> {est}", "Infermiere", inf_f), True)
                                    st.rerun()
                                else: st.error("Firma necessaria")

        # --- EDUCATORI ---
        elif figura == "Educatore":
            st.subheader("💰 Contabilità")
            movs = db_run("SELECT importo, tipo FROM soldi WHERE p_id=?", (p_id,))
            saldo = sum([m[0] if m[1] == "Entrata" else -m[0] for m in movs])
            st.markdown(f'<div class="saldo-box"><h5>SALDO DISPONIBILE</h5><h2>€ {saldo:.2f}</h2></div>', unsafe_allow_html=True)
            
            with st.expander("Registra Movimento"):
                tipo = st.radio("Tipo", ["Entrata", "Uscita"], horizontal=True)
                imp = st.number_input("Importo €", min_value=0.0)
                cau = st.text_input("Causale")
                fir = st.text_input("Firma Educatore")
                if st.button("SALVA MOVIMENTO"):
                    db_run("INSERT INTO soldi (p_id, data, desc, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, date.today().strftime("%d/%m/%Y"), cau, imp, tipo, fir), True); st.rerun()

            st.write("---")
            storico = db_run("SELECT data, desc, importo, tipo, op FROM soldi WHERE p_id=? ORDER BY row_id DESC", (p_id,))
            if storico:
                df_s = pd.DataFrame(storico, columns=["Data", "Causale", "Importo", "Tipo", "Operatore"])
                st.table(df_s)

elif menu == "Monitoraggio":
    pazienti = db_run("SELECT * FROM pazienti ORDER BY nome")
    for p_id, nome in pazienti:
        with st.expander(f"👤 DIARIO: {nome.upper()}"):
            note = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY row_id DESC", (p_id,))
            if note:
                h = '<table class="clinica-table">'
                for d, ru, op, nt in note:
                    bg = "#f0fdf4" if "REP_" in nt else ("#fffbeb" if "CAMBIO" in nt else "white")
                    h += f'<tr style="background:{bg}"><td>{d}</td><td><b>{ru}</b><br>{op}</td><td>{nt}</td></tr>'
                st.markdown(h + '</table>', unsafe_allow_html=True)

elif menu == "Gestione":
    st.subheader("⚙️ Amministrazione")
    nuovo = st.text_input("Aggiungi Paziente")
    if st.button("SALVA"):
        if nuovo: db_run("INSERT INTO pazienti (nome) VALUES (?)", (nuovo,), True); st.rerun()
