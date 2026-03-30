import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date

# --- 1. CONFIGURAZIONE & STILE CSS AVANZATO ---
st.set_page_config(page_title="REMS Connect PRO", layout="wide")

st.markdown("""
<style>
    .main-title {text-align: center; color: #1e3a8a; font-weight: bold; margin-bottom:20px;}
    
    /* Tabella Professionale Lineare */
    .custom-table {
        width: 100%;
        border-collapse: collapse;
        margin: 10px 0;
        font-size: 0.85rem;
        background-white;
    }
    .custom-table th {
        background-color: #1e3a8a;
        color: white;
        padding: 10px;
        text-align: left;
        border: 1px solid #dee2e6;
    }
    .custom-table td {
        padding: 10px;
        border: 1px solid #dee2e6;
        vertical-align: middle;
    }
    .custom-table tr:nth-child(even) { background-color: #f8fafc; }
    
    /* Badge Stati */
    .badge-m { background: #dcfce7; color: #166534; padding: 2px 6px; border-radius: 4px; font-weight: bold; }
    .status-ok { color: #10b981; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 2. FUNZIONI DATABASE ---
DB_NAME = "rems_connect_data.db"

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, umore TEXT, nota TEXT, ruolo TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dosaggio TEXT, turni TEXT, medico TEXT, data_prescr TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS soldi (p_id INTEGER, data TEXT, desc TEXT, importo REAL, tipo TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        
        try: cur.execute("ALTER TABLE terapie ADD COLUMN turni TEXT")
        except: pass
        try: cur.execute("ALTER TABLE terapie ADD COLUMN data_prescr TEXT")
        except: pass

        if query: cur.execute(query, params)
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
                st.rerun()
    st.stop()

# --- 4. NAVIGAZIONE ---
menu = st.sidebar.radio("NAVIGAZIONE", ["Monitoraggio", "Equipe", "Gestione"])

if menu == "Equipe":
    figura = st.sidebar.selectbox("Ruolo", ["Psichiatra", "Infermiere", "Educatore"])
    paz = db_run("SELECT * FROM pazienti ORDER BY nome")
    
    if paz:
        sel_p = st.selectbox("Seleziona Paziente", [p[1] for p in paz])
        p_id = [p[0] for p in paz if p[1] == sel_p][0]
        st.divider()

        # --- PSICHIATRA ---
        if figura == "Psichiatra":
            st.subheader("📋 Nuova Prescrizione")
            with st.form("presc_form"):
                f = st.text_input("Farmaco")
                d = st.text_input("Dosaggio")
                st.write("Turni:")
                c1, c2, c3 = st.columns(3)
                tm = c1.checkbox("M")
                tp = c2.checkbox("P")
                tn = c3.checkbox("N")
                med = st.text_input("Medico")
                if st.form_submit_button("CONFERMA VARIAZIONE"):
                    t_list = []
                    if tm: t_list.append("M")
                    if tp: t_list.append("P")
                    if tn: t_list.append("N")
                    dt = datetime.now().strftime("%d/%m/%y %H:%M")
                    db_run("INSERT INTO terapie (p_id, farmaco, dosaggio, turni, medico, data_prescr) VALUES (?,?,?,?,?,?)", 
                           (p_id, f, d, ",".join(t_list), med, dt), True)
                    st.rerun()

            st.write("### 💊 Terapie Attive")
            terapie = db_run("SELECT data_prescr, farmaco, dosaggio, turni, medico, row_id FROM terapie WHERE p_id=? ORDER BY row_id DESC", (p_id,))
            
            if terapie:
                # Costruiamo la tabella HTML per garantire la linearità su mobile
                html = """<table class='custom-table'>
                <tr><th>DATA</th><th>FARMACO</th><th>DOS</th><th>T</th><th>MED</th><th>AZIONE</th></tr>"""
                for da, fa, do, tu, me, rid in terapie:
                    html += f"""<tr>
                        <td>{da if da else '-'}</td>
                        <td><b>{fa}</b></td>
                        <td>{do}</td>
                        <td><span class='badge-m'>{tu}</span></td>
                        <td>{me}</td>
                        <td></td>
                    </tr>"""
                st.markdown(html + "</table>", unsafe_allow_html=True)
                
                # Per gestire i bottoni Streamlit "dentro" una riga lineare, usiamo un espander di pulizia
                with st.expander("Azioni Rapide (Sospensione)"):
                    for da, fa, do, tu, me, rid in terapie:
                        if st.button(f"Sospendi {fa}", key=f"s_{rid}"):
                            db_run("DELETE FROM terapie WHERE row_id=?", (rid,), True)
                            db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", 
                                   (p_id, datetime.now().strftime("%d/%m/%y %H:%M"), "Stabile", f"❌ SOSPESO {fa}", "Psichiatra", "Sistema"), True)
                            st.rerun()

        # --- INFERMIERE ---
        elif figura == "Infermiere":
            st.subheader("💉 Somministrazione")
            col_a, col_b = st.columns(2)
            d_sel = col_a.date_input("Data", date.today())
            t_sel = col_b.selectbox("Turno", ["Mattina", "Pomeriggio", "Notte"])
            sigla = t_sel[0]
            inf_f = st.text_input("Firma Infermiere")
            
            st.write(f"**Turno {t_sel}**")
            data_s = d_sel.strftime("%d/%m/%Y")
            terapie = db_run("SELECT farmaco, dosaggio, turni, row_id FROM terapie WHERE p_id=?", (p_id,))
            
            for f, d, turni_f, rid in terapie:
                if turni_f and sigla in turni_f:
                    tag = f"[REP_{sigla}] {f}"
                    fatto = db_run("SELECT op FROM eventi WHERE id=? AND nota LIKE ? AND data LIKE ?", (p_id, f"%{tag}%", f"{data_s}%"))
                    
                    with st.container():
                        c1, c2 = st.columns([2, 1])
                        c1.markdown(f"**{f}** ({d})")
                        if fatto:
                            c2.markdown(f"<span class='status-ok'>✅ {fatto[0][0]}</span>", unsafe_allow_html=True)
                        else:
                            if st.button(f"CONVALIDA {f}", key=f"inf_{rid}_{sigla}"):
                                if inf_f:
                                    db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", 
                                           (p_id, f"{data_s} {datetime.now().strftime('%H:%M')}", "Stabile", f"{tag} -> Somministrata", "Infermiere", inf_f), True)
                                    st.rerun()
                                else: st.error("Firma!")

            st.divider()
            st.write("#### 📑 Report Odierni")
            reps = db_run("SELECT data, nota, op FROM eventi WHERE id=? AND nota LIKE '%[REP_%' ORDER BY row_id DESC LIMIT 10", (p_id,))
            if reps:
                st.table(pd.DataFrame(reps, columns=["Data/Ora", "Nota", "Op"]))

# --- MONITORAGGIO ---
elif menu == "Monitoraggio":
    pazienti = db_run("SELECT * FROM pazienti ORDER BY nome")
    for p_id, nome in pazienti:
        with st.expander(f"👤 DIARIO: {nome.upper()}"):
            note = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY row_id DESC", (p_id,))
            if note:
                html = "<table class='custom-table'><tr><th>DATA</th><th>RUOLO</th><th>NOTA</th></tr>"
                for d, ru, op, nt in note:
                    html += f"<tr><td>{d}</td><td><b>{ru}</b><br>{op}</td><td>{nt}</td></tr>"
                st.markdown(html + "</table>", unsafe_allow_html=True)

# --- GESTIONE ---
elif menu == "Gestione":
    st.subheader("⚙️ Gestione")
    nuovo = st.text_input("Aggiungi Paziente")
    if st.button("SALVA"):
        if nuovo: db_run("INSERT INTO pazienti (nome) VALUES (?)", (nuovo,), True); st.rerun()
