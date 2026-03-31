import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date

# --- 1. CONFIGURAZIONE & STILE ---
st.set_page_config(page_title="REMS Connect PRO", layout="wide")

st.markdown("""
<style>
    .main-title {text-align: center; color: #1e3a8a; font-weight: bold; margin-bottom:20px;}
    .custom-table {width: 100%; border-collapse: collapse; font-size: 0.85rem; background: white;}
    .custom-table th {background-color: #1e3a8a; color: white; padding: 10px; text-align: left; border: 1px solid #dee2e6;}
    .custom-table td {padding: 10px; border: 1px solid #dee2e6; vertical-align: middle;}
    .badge-m { background: #dcfce7; color: #166534; padding: 2px 6px; border-radius: 4px; font-weight: bold; border: 1px solid #166534; margin-right:2px;}
    .status-ok { color: #10b981; font-weight: bold; border: 1px solid #10b981; padding: 2px 5px; border-radius: 4px; background: #f0fdf4; }
    .card-box { border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; margin-bottom: 10px; background: #ffffff; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .saldo-box { padding: 15px; border-radius: 10px; background-color: #f8fafc; text-align: center; border: 2px solid #1e3a8a; font-weight: bold; font-size: 1.2rem; margin-bottom: 15px; }
    .txt-entrata { color: #10b981; font-weight: bold; }
    .txt-uscita { color: #ef4444; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 2. FUNZIONI DATABASE ---
DB_NAME = "rems_connect_data.db"

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY, nome TEXT, giorno_lavatrice TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, umore TEXT, nota TEXT, ruolo TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dosaggio TEXT, turni TEXT, medico TEXT, data_prescr TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS soldi (p_id INTEGER, data TEXT, desc TEXT, importo REAL, tipo TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        
        cur.execute("PRAGMA table_info(pazienti)")
        esistenti = [col[1] for col in cur.fetchall()]
        if "giorno_lavatrice" not in esistenti:
            cur.execute("ALTER TABLE pazienti ADD COLUMN giorno_lavatrice TEXT")

        if query: cur.execute(query, params)
        if commit: conn.commit()
        return cur.fetchall()

GIORNI = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]

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
menu = st.sidebar.radio("NAVIGAZIONE", ["Monitoraggio", "Equipe", "Gestione"])

if menu == "Equipe":
    figura = st.sidebar.selectbox("Ruolo", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
    paz_data = db_run("SELECT id, nome, giorno_lavatrice FROM pazienti ORDER BY nome")
    
    if paz_data:
        sel_p_nome = st.selectbox("Seleziona Paziente", [p[1] for p in paz_data])
        p_id = [p[0] for p in paz_data if p[1] == sel_p_nome][0]
        st.divider()

        # --- SEZIONE PSICHIATRA ---
        if figura == "Psichiatra":
            st.subheader("📋 Prescrizione Terapia")
            with st.form("presc"):
                f = st.text_input("Farmaco")
                d = st.text_input("Dosaggio")
                c1,c2,c3 = st.columns(3)
                tm = c1.checkbox("Mattina (M)")
                tp = c2.checkbox("Pomeriggio (P)")
                tn = c3.checkbox("Notte (N)")
                med = st.text_input("Firma Medico")
                if st.form_submit_button("SALVA PRESCRIZIONE"):
                    t_list = [s for s, b in zip(["M", "P", "N"], [tm, tp, tn]) if b]
                    db_run("INSERT INTO terapie (p_id, farmaco, dosaggio, turni, medico, data_prescr) VALUES (?,?,?,?,?,?)", 
                           (p_id, f, d, ",".join(t_list), med, date.today().strftime("%d/%m/%Y")), True)
                    st.rerun()

        # --- SEZIONE INFERMIERE (SISTEMATA) ---
        elif figura == "Infermiere":
            st.subheader("💉 Somministrazione Terapia")
            c1, c2 = st.columns(2)
            data_somm = c1.date_input("Data Somministrazione", date.today())
            turno_somm = c2.selectbox("Turno", ["Mattina", "Pomeriggio", "Notte"])
            sigla = turno_somm[0] # M, P o N
            firma_inf = st.text_input("Firma Infermiere")

            terapie = db_run("SELECT farmaco, dosaggio, turni, row_id FROM terapie WHERE p_id=?", (p_id,))
            
            for f, d, tu_f, rid in terapie:
                if tu_f and sigla in tu_f:
                    tag = f"[REP_{sigla}] {f}"
                    data_str = data_somm.strftime("%d/%m/%Y")
                    # Controllo se già somministrato
                    check = db_run("SELECT op, nota FROM eventi WHERE id=? AND nota LIKE ? AND data LIKE ?", 
                                   (p_id, f"%{tag}%", f"{data_str}%"))
                    
                    st.markdown("<div class='card-box'>", unsafe_allow_html=True)
                    col_a, col_b, col_c = st.columns([2, 2, 1])
                    col_a.markdown(f"**{f}**<br><small>{d}</small>", unsafe_allow_html=True)
                    
                    if check:
                        esito = check[0][1].split("->")[-1]
                        col_b.markdown(f"<span class='status-ok'>✅ {esito} ({check[0][0]})</span>", unsafe_allow_html=True)
                    else:
                        scelta = col_b.radio("Esito:", ["Assunta", "Rifiutata"], key=f"inf_{rid}_{sigla}", horizontal=True)
                        if col_c.button("CONVALIDA", key=f"btn_{rid}_{sigla}"):
                            if firma_inf:
                                db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", 
                                       (p_id, f"{data_str} {datetime.now().strftime('%H:%M')}", "Stabile", f"{tag} -> {scelta}", "Infermiere", firma_inf), True)
                                st.rerun()
                            else: st.error("Firma necessaria")
                    st.markdown("</div>", unsafe_allow_html=True)

        # --- SEZIONE EDUCATORE (CON TABELLA SOLDI) ---
        elif figura == "Educatore":
            st.subheader("💰 Gestione Contabilità")
            movimenti = db_run("SELECT data, desc, importo, tipo, op FROM soldi WHERE p_id=? ORDER BY row_id DESC", (p_id,))
            saldo = sum([m[2] if m[3] == "Entrata" else -m[2] for m in movimenti])
            st.markdown(f'<div class="saldo-box">Saldo: € {saldo:.2f}</div>', unsafe_allow_html=True)
            
            with st.expander("Nuovo Movimento"):
                tipo = st.radio("Tipo", ["Entrata", "Uscita"], horizontal=True)
                imp = st.number_input("Importo €", min_value=0.0)
                cau = st.text_input("Causale")
                f_ed = st.text_input("Firma")
                if st.button("SALVA"):
                    db_run("INSERT INTO soldi (p_id, data, desc, importo, tipo, op) VALUES (?,?,?,?,?,?)", 
                           (p_id, date.today().strftime("%d/%m/%Y"), cau, imp, tipo, f_ed), True); st.rerun()

            if movimenti:
                h = "<table class='custom-table'><tr><th>DATA</th><th>CAUSALE</th><th>ENTRATA</th><th>USCITA</th><th>FIRMA</th></tr>"
                for d, ds, im, tp, op in movimenti:
                    ent = f"<b>€ {im:.2f}</b>" if tp == "Entrata" else ""
                    usc = f"<span style='color:red'>€ {im:.2f}</span>" if tp == "Uscita" else ""
                    h += f"<tr><td>{d}</td><td>{ds}</td><td>{ent}</td><td>{usc}</td><td>{op}</td></tr>"
                st.markdown(h + "</table>", unsafe_allow_html=True)

# --- MONITORAGGIO ---
elif menu == "Monitoraggio":
    paz_list = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    for pid, nome in paz_list:
        with st.expander(f"👤 {nome.upper()}"):
            note = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY row_id DESC", (pid,))
            if note:
                h = "<table class='custom-table'><tr><th>DATA</th><th>RUOLO</th><th>OP</th><th>NOTA</th></tr>"
                for d, ru, op, nt in note:
                    h += f"<tr><td>{d}</td><td>{ru}</td><td>{op}</td><td>{nt}</td></tr>"
                st.markdown(h + "</table>", unsafe_allow_html=True)

# --- GESTIONE ---
elif menu == "Gestione":
    st.subheader("⚙️ Amministrazione")
    n_p = st.text_input("Nuovo Paziente")
    if st.button("AGGIUNGI"):
        db_run("INSERT INTO pazienti (nome) VALUES (?)", (n_p,), True); st.rerun()
