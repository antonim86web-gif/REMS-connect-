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
    .badge-m { background: #dcfce7; color: #166534; padding: 2px 6px; border-radius: 4px; font-weight: bold; border: 1px solid #166534; }
    .card-box { border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; margin-bottom: 10px; background: #ffffff; }
    .saldo-box { padding: 15px; border-radius: 10px; background-color: #f8fafc; text-align: center; border: 2px solid #1e3a8a; margin-bottom:15px; }
    .entrata { color: #10b981; font-weight: bold; }
    .uscita { color: #ef4444; font-weight: bold; }
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
        g_lav = [p[2] for p in paz_data if p[1] == sel_p_nome][0]
        st.divider()

        # --- SEZIONE PSICHIATRA ---
        if figura == "Psichiatra":
            st.subheader("📋 Gestione Terapie")
            with st.form("p_f"):
                f, d = st.text_input("Farmaco"), st.text_input("Dose")
                c1, c2, c3 = st.columns(3)
                tm, tp, tn = c1.checkbox("M"), c2.checkbox("P"), c3.checkbox("N")
                med = st.text_input("Medico")
                if st.form_submit_button("REGISTRA"):
                    t_l = [s for s, b in zip(["M", "P", "N"], [tm, tp, tn]) if b]
                    db_run("INSERT INTO terapie (p_id, farmaco, dosaggio, turni, medico, data_prescr) VALUES (?,?,?,?,?,?)", 
                           (p_id, f, d, ",".join(t_l), med, datetime.now().strftime("%d/%m/%y %H:%M")), True)
                    st.rerun()
            
            st.write("#### Terapie Attive")
            ter = db_run("SELECT data_prescr, farmaco, dosaggio, turni, medico, row_id FROM terapie WHERE p_id=? ORDER BY row_id DESC", (p_id,))
            if ter:
                h = "<table class='custom-table'><tr><th>DATA</th><th>FARMACO</th><th>DOSAGGIO</th><th>T</th><th>MEDICO</th></tr>"
                for da, fa, do, tu, me, rid in ter:
                    h += f"<tr><td>{da}</td><td><b>{fa}</b></td><td>{do}</td><td>{tu}</td><td>{me}</td></tr>"
                st.markdown(h + "</table>", unsafe_allow_html=True)
                with st.expander("Sospendi"):
                    for da, fa, do, tu, me, rid in ter:
                        if st.button(f"Elimina {fa}", key=f"s_{rid}"):
                            db_run("DELETE FROM terapie WHERE row_id=?", (rid,), True)
                            db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%y %H:%M"), "Stabile", f"❌ SOSPESO: {fa}", "Psichiatra", med), True)
                            st.rerun()

        # --- SEZIONE INFERMIERE ---
        elif figura == "Infermiere":
            st.subheader("💉 Somministrazione")
            t_op = st.selectbox("Turno", ["Mattina", "Pomeriggio", "Notte"])
            firma = st.text_input("Firma")
            terapie = db_run("SELECT farmaco, dosaggio, turni, row_id FROM terapie WHERE p_id=?", (p_id,))
            for f, d, tu_f, rid in terapie:
                if tu_f and t_op[0] in tu_f:
                    st.markdown("<div class='card-box'>", unsafe_allow_html=True)
                    c1, c2, c3 = st.columns([2,2,1])
                    c1.write(f"**{f}** ({d})")
                    tag = f"[REP_{t_op[0]}] {f}"
                    check = db_run("SELECT op, nota FROM eventi WHERE id=? AND nota LIKE ? AND data LIKE ?", (p_id, f"%{tag}%", f"{date.today().strftime('%d/%m/%Y')}%"))
                    if check:
                        c2.write(f"✅ {check[0][1].split('->')[-1]}")
                    else:
                        esc = c2.radio("Esito", ["Assunta", "Rifiutata"], key=f"r_{rid}", horizontal=True)
                        if c3.button("OK", key=f"b_{rid}"):
                            db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), "Stabile", f"{tag} -> {esc}", "Infermiere", firma), True)
                            st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)

        # --- SEZIONE EDUCATORI (CORRETTA) ---
        elif figura == "Educatore":
            st.subheader("💰 Gestione Contabilità")
            
            # Recupero TUTTE le transazioni
            storico = db_run("SELECT data, desc, importo, tipo, op FROM soldi WHERE p_id=? ORDER BY row_id DESC", (p_id,))
            saldo = sum([s[2] if s[3] == "Entrata" else -s[2] for s in storico])
            
            st.markdown(f'<div class="saldo-box"><h5>SALDO DISPONIBILE</h5><h2>€ {saldo:.2f}</h2></div>', unsafe_allow_html=True)
            
            with st.expander("📝 Registra Movimento"):
                tipo = st.radio("Tipo", ["Entrata", "Uscita"], horizontal=True)
                importo = st.number_input("Cifra €", min_value=0.0, step=0.50)
                causale = st.text_input("Causale")
                firma_ed = st.text_input("Firma")
                if st.button("CONFERMA OPERAZIONE"):
                    if causale and firma_ed:
                        db_run("INSERT INTO soldi (p_id, data, desc, importo, tipo, op) VALUES (?,?,?,?,?,?)", 
                               (p_id, date.today().strftime("%d/%m/%Y"), causale, importo, tipo, firma_ed), True)
                        st.rerun()

            st.write("#### 📊 Elenco Transazioni Effettuate")
            if storico:
                h = "<table class='custom-table'><tr><th>DATA</th><th>CAUSALE</th><th>ENTRATA</th><th>USCITA</th><th>OPERATORE</th></tr>"
                for d, ds, im, tp, op in storico:
                    en = f"€ {im:.2f}" if tp == "Entrata" else ""
                    us = f"€ {im:.2f}" if tp == "Uscita" else ""
                    h += f"<tr><td>{d}</td><td>{ds}</td><td class='entrata'>{en}</td><td class='uscita'>{us}</td><td>{op}</td></tr>"
                st.markdown(h + "</table>", unsafe_allow_html=True)
            else:
                st.info("Nessuna transazione registrata per questo paziente.")

        # --- SEZIONE OSS ---
        elif figura == "OSS":
            st.subheader("🧹 Mansioni OSS")
            if g_lav == GIORNI[date.today().weekday()]:
                st.warning(f"🧺 TURNO LAVATRICE: {sel_p_nome}")
            # ... logica OSS come prima ...
            with st.form("oss"):
                t1 = st.checkbox("Pulizia Stanza")
                t2 = st.checkbox("Lavatrice")
                f_oss = st.text_input("Firma")
                if st.form_submit_button("REGISTRA"):
                    db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%y %H:%M"), "Stabile", f"🧹 [OSS] Pulizia/Lavanderia", "OSS", f_oss), True)
                    st.rerun()

# --- MONITORAGGIO ---
elif menu == "Monitoraggio":
    for p_id, nome, g in db_run("SELECT id, nome, giorno_lavatrice FROM pazienti ORDER BY nome"):
        with st.expander(f"👤 {nome.upper()}"):
            note = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY row_id DESC", (p_id,))
            if note:
                h = "<table class='custom-table'><tr><th>DATA</th><th>RUOLO</th><th>NOTA</th></tr>"
                for d, ru, op, nt in note:
                    h += f"<tr><td>{d}</td><td>{ru} ({op})</td><td>{nt}</td></tr>"
                st.markdown(h + "</table>", unsafe_allow_html=True)

# --- GESTIONE ---
elif menu == "Gestione":
    st.subheader("⚙️ Amministrazione")
    n_p = st.text_input("Nuovo Paziente")
    g_l = st.selectbox("Giorno Lavatrice", GIORNI[:6])
    if st.button("SALVA"):
        db_run("INSERT INTO pazienti (nome, giorno_lavatrice) VALUES (?,?)", (n_p, g_l), True); st.rerun()
