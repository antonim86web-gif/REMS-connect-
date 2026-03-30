import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="REMS Connect PRO", layout="wide")

st.markdown("""
<style>
    .main-title {text-align: center; color: #1e3a8a; font-weight: bold;}
    .turno-box {padding: 10px; border-radius: 5px; margin-bottom: 10px; border-left: 5px solid #1e3a8a; background: #f1f5f9;}
    .card-farmaco {background: white; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 10px; border: 1px solid #e2e8f0;}
    .status-ok {color: #10b981; font-weight: bold;}
    .status-wait {color: #f59e0b; font-weight: bold;}
</style>
""", unsafe_allow_html=True)

# --- 2. DATABASE (Aggiunta colonna Turni) ---
DB_NAME = "rems_connect_data.db"

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, umore TEXT, nota TEXT, ruolo TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        # Aggiunta colonna turni (M, P, N)
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dosaggio TEXT, turni TEXT, medico TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS soldi (p_id INTEGER, data TEXT, desc TEXT, importo REAL, tipo TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute(query, params)
        if commit: conn.commit()
        return cur.fetchall()

# --- 3. LOGIN & NAVIGAZIONE ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.markdown("<h1 class='main-title'>REMS CONNECT PRO</h1>", unsafe_allow_html=True)
    with st.form("login"):
        pwd = st.text_input("Accesso", type="password")
        if st.form_submit_button("ENTRA"):
            if pwd in ["rems2026", "admin2026"]:
                st.session_state.auth = True
                st.rerun()
    st.stop()

menu = st.sidebar.radio("MENU", ["Monitoraggio", "Equipe", "Gestione"])

# --- 4. LOGICA EQUIPE (PSICHIATRA E INFERMIERE) ---
if menu == "Equipe":
    figura = st.sidebar.selectbox("Ruolo", ["Psichiatra", "Infermiere", "Educatore"])
    paz = db_run("SELECT * FROM pazienti ORDER BY nome")
    
    if paz:
        sel_p = st.selectbox("Paziente", [p[1] for p in paz])
        p_id = [p[0] for p in paz if p[1] == sel_p][0]

        # --- SEZIONE PSICHIATRA: PRESCRIZIONE PER TURNI ---
        if figura == "Psichiatra":
            st.subheader("📋 Prescrizione Terapia per Turni")
            with st.form("prescrizione"):
                f = st.text_input("Farmaco")
                d = st.text_input("Dosaggio (es. 10mg)")
                st.write("Seleziona Turni di somministrazione:")
                c1, c2, c3 = st.columns(3)
                tm = c1.checkbox("Mattina (08:00)")
                tp = c2.checkbox("Pomeriggio (14:00)")
                tn = c3.checkbox("Notte (22:00)")
                med = st.text_input("Medico")
                if st.form_submit_button("SALVA PRESCRIZIONE"):
                    turni_scelti = []
                    if tm: turni_scelti.append("M")
                    if tp: turni_scelti.append("P")
                    if tn: turni_scelti.append("N")
                    db_run("INSERT INTO terapie (p_id, farmaco, dosaggio, turni, medico) VALUES (?,?,?,?,?)", 
                           (p_id, f, d, ",".join(turni_scelti), med), True)
                    st.success("Terapia salvata"); st.rerun()

        # --- SEZIONE INFERMIERE: GESTIONE TURNI E DATA ---
        elif figura == "Infermiere":
            st.subheader("💉 Gestione Somministrazione")
            col_d, col_t = st.columns(2)
            data_sel = col_d.date_input("Data Somministrazione", date.today())
            turno_sel = col_t.selectbox("Seleziona il tuo Turno", ["Mattina", "Pomeriggio", "Notte"])
            sigla_turno = turno_sel[0] # Prende M, P o N
            
            inf_firma = st.text_input("Firma Infermiere")
            
            st.write(f"#### 💊 Farmaci previsti per il turno: {turno_sel}")
            
            # Recupera farmaci che hanno quel turno nella stringa "turni"
            terapie = db_run("SELECT farmaco, dosaggio, turni, row_id FROM terapie WHERE p_id=?", (p_id,))
            
            data_str = data_sel.strftime("%d/%m/%Y")
            
            for f, d, t_string, rid in terapie:
                if sigla_turno in t_string:
                    # Controlla se è già stato somministrato per questa data e questo turno
                    chiave_report = f"[REP_{sigla_turno}] {f}"
                    gia_fatto = db_run("SELECT op FROM eventi WHERE id=? AND nota LIKE ? AND data LIKE ?", 
                                      (p_id, f"%{chiave_report}%", f"{data_str}%"))
                    
                    with st.container():
                        c1, c2, c3 = st.columns([3, 3, 2])
                        c1.markdown(f"**{f}**<br><small>{d}</small>", unsafe_allow_html=True)
                        
                        if gia_fatto:
                            c2.markdown(f"<span class='status-ok'>✅ Somministrato da {gia_fatto[0][0]}</span>", unsafe_allow_html=True)
                        else:
                            esito = c2.selectbox("Esito", ["Assunta", "Parziale", "Rifiutata"], key=f"es_{rid}_{sigla_turno}")
                            if c3.button("CONVALIDA", key=f"btn_{rid}_{sigla_turno}"):
                                if inf_firma:
                                    nota_rep = f"[REPORT_{sigla_turno}] {f} ({d}) -> {esito}"
                                    db_run("INSERT INTO eventi (id, data, umore, nota, ruolo, op) VALUES (?,?,?,?,?,?)",
                                           (p_id, f"{data_str} {datetime.now().strftime('%H:%M')}", "Stabile", nota_rep, "Infermiere", inf_firma), True)
                                    st.rerun()
                                else: st.error("Manca la firma!")

            st.divider()
            st.write("#### 📑 Registro Storico (Tutti i turni)")
            reps = db_run("SELECT data, nota, op FROM eventi WHERE id=? AND nota LIKE '%[REPORT_%' ORDER BY row_id DESC LIMIT 15", (p_id,))
            if reps:
                st.table(pd.DataFrame(reps, columns=["Data/Ora", "Dettaglio Somministrazione", "Infermiere"]))

# --- 5. MONITORAGGIO ---
elif menu == "Monitoraggio":
    # (Visualizzazione del diario clinico con i colori corretti come prima)
    pazienti = db_run("SELECT * FROM pazienti ORDER BY nome")
    for p_id, nome in pazienti:
        with st.expander(f"👤 DIARIO CLINICO: {nome.upper()}"):
            note = db_run("SELECT data, umore, nota, ruolo, op FROM eventi WHERE id=? ORDER BY row_id DESC", (p_id,))
            if note:
                html = '<table style="width:100%; border-collapse: collapse;">'
                for d, um, tx, ru, fi in note:
                    bg = "#f0fdf4" if "REPORT" in tx else "white"
                    html += f'<tr style="background:{bg}; border-bottom:1px solid #eee;">'
                    html += f'<td style="padding:10px;">{d}</td><td style="padding:10px;"><b>{ru}</b></td><td style="padding:10px;">{tx}</td></tr>'
                st.markdown(html + '</table>', unsafe_allow_html=True)
