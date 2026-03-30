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
    .badge-lavatrice { background: #dbeafe; color: #1e40af; padding: 5px 10px; border-radius: 20px; font-weight: bold; border: 1px solid #1e40af; display: inline-block; margin-bottom: 10px;}
    .status-ok { color: #10b981; font-weight: bold; border: 1px solid #10b981; padding: 2px 5px; border-radius: 4px; background: #f0fdf4; }
    .card-box { border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; margin-bottom: 10px; background: #ffffff; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
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
        
        # Migrazioni
        try: cur.execute("ALTER TABLE pazienti ADD COLUMN giorno_lavatrice TEXT")
        except: pass
        try: cur.execute("ALTER TABLE terapie ADD COLUMN turni TEXT")
        except: pass

        if query: cur.execute(query, params)
        if commit: conn.commit()
        return cur.fetchall()

# Dizionario giorni per traduzione
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
        giorno_assegnato = [p[2] for p in paz_data if p[1] == sel_p_nome][0]
        st.divider()

        # --- SEZIONE OSS ---
        if figura == "OSS":
            st.subheader("🧹 Mansioni Quotidiane OSS")
            
            # Controllo giorno lavatrice
            oggi_settimana = GIORNI[date.today().weekday()]
            if giorno_assegnato:
                if giorno_assegnato == oggi_settimana:
                    st.markdown(f"<div class='badge-lavatrice'>🧺 OGGI È IL GIORNO LAVATRICE ({giorno_assegnato})</div>", unsafe_allow_html=True)
                else:
                    st.info(f"Pianificazione lavatrice: **{giorno_assegnato}** (Oggi è {oggi_settimana})")
            
            with st.form("oss_tasks"):
                c1, c2 = st.columns(2)
                t1 = c1.checkbox("Pulizia Stanza")
                t2 = c1.checkbox("Pulizia Sale Fumo")
                t3 = c2.checkbox("Pulizia Refettorio")
                t4 = c2.checkbox("Lavatrice/Lavanderia")
                oss_firma = st.text_input("Firma Operatore OSS")
                
                if st.form_submit_button("REGISTRA ATTIVITÀ"):
                    if oss_firma:
                        comp = [txt for b, txt in zip([t1,t2,t3,t4], ["Stanza", "Sale Fumo", "Refettorio", "Lavatrice"]) if b]
                        if comp:
                            db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", 
                                   (p_id, datetime.now().strftime("%d/%m/%y %H:%M"), "Stabile", f"🧹 [OSS] Eseguito: {', '.join(comp)}", "OSS", oss_firma), True)
                            st.success("Registrato!")
                        else: st.warning("Seleziona un'attività.")
                    else: st.error("Manca la firma.")

        # --- ALTRE SEZIONI (PSICHIATRA, INFERMIERE, EDUCATORI) ---
        elif figura == "Psichiatra":
            # (Codice psichiatra invariato...)
            st.subheader("📋 Gestione Terapie")
            with st.form("presc"):
                f, d = st.text_input("Farmaco"), st.text_input("Dose")
                med = st.text_input("Medico")
                if st.form_submit_button("SALVA"):
                    db_run("INSERT INTO terapie (p_id, farmaco, dosaggio, medico, data_prescr) VALUES (?,?,?,?,?)", (p_id, f, d, med, datetime.now().strftime("%d/%m/%y %H:%M")), True)
                    st.rerun()

        elif figura == "Infermiere":
            # (Codice infermiere invariato...)
            st.subheader("💉 Somministrazione")
            t_sel = st.selectbox("Turno", ["Mattina", "Pomeriggio", "Notte"])
            inf_f = st.text_input("Firma")
            # Logica somministrazione...

        elif figura == "Educatore":
            # (Codice educatore invariato...)
            st.subheader("💰 Gestione Soldi")
            # Logica soldi...

# --- MONITORAGGIO ---
elif menu == "Monitoraggio":
    pazienti = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    for p_id, nome in pazienti:
        with st.expander(f"👤 DIARIO: {nome.upper()}"):
            note = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY row_id DESC", (p_id,))
            if note:
                h = "<table class='custom-table'><tr><th>DATA</th><th>RUOLO</th><th>NOTA</th></tr>"
                for d, ru, op, nt in note:
                    bg = "#eff6ff" if "[OSS]" in nt else "white"
                    h += f"<tr style='background:{bg}'><td>{d}</td><td><b>{ru}</b><br>{op}</td><td>{nt}</td></tr>"
                st.markdown(h + "</table>", unsafe_allow_html=True)

# --- GESTIONE ---
elif menu == "Gestione":
    st.subheader("⚙️ Gestione Anagrafiche e Turni")
    
    with st.form("nuovo_paz"):
        st.write("### Aggiungi/Aggiorna Paziente")
        n = st.text_input("Nome e Cognome")
        g_lav = st.selectbox("Giorno Lavatrice", ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato"])
        if st.form_submit_button("SALVA PAZIENTE"):
            if n:
                # Se esiste già lo aggiorna, altrimenti lo inserisce
                esistente = db_run("SELECT id FROM pazienti WHERE nome=?", (n,))
                if esistente:
                    db_run("UPDATE pazienti SET giorno_lavatrice=? WHERE nome=?", (g_lav, n), True)
                else:
                    db_run("INSERT INTO pazienti (nome, giorno_lavatrice) VALUES (?,?)", (n, g_lav), True)
                st.success(f"Paziente {n} salvato con turno lavatrice: {g_lav}")
                st.rerun()

    st.divider()
    st.write("#### Elenco Pazienti e Turni Lavatrice")
    lista = db_run("SELECT nome, giorno_lavatrice FROM pazienti ORDER BY nome")
    if lista:
        df_l = pd.DataFrame(lista, columns=["Paziente", "Giorno Lavatrice"])
        st.table(df_l)
