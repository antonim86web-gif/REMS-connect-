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
    .clinica-table th {background-color: #f1f5f9; padding: 10px; text-align: left; border-bottom: 2px solid #cbd5e1;}
    .clinica-table td {padding: 10px; border-bottom: 1px solid #eee; vertical-align: top;}
    .row-sospeso {background-color: #fef2f2; color: #b91c1c; text-decoration: line-through;}
</style>
""", unsafe_allow_html=True)

# --- 2. DATABASE ---
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
menu = st.sidebar.radio("MENU", ["Monitoraggio", "Equipe", "Gestione"])

if menu == "Equipe":
    figura = st.sidebar.selectbox("Ruolo", ["Psichiatra", "Infermiere", "Educatore"])
    paz = db_run("SELECT * FROM pazienti ORDER BY nome")
    
    if paz:
        sel_p = st.selectbox("Seleziona Paziente", [p[1] for p in paz])
        p_id = [p[0] for p in paz if p[1] == sel_p][0]
        st.divider()

        # --- PSICHIATRA: GESTIONE COMPLETA TERAPIA ---
        if figura == "Psichiatra":
            st.subheader("📋 Nuova Prescrizione")
            with st.form("presc_form"):
                f = st.text_input("Nome Farmaco")
                d = st.text_input("Dosaggio (es. 10mg o 1cp)")
                st.write("Turni di somministrazione:")
                c1, c2, c3 = st.columns(3)
                tm = c1.checkbox("Mattina")
                tp = c2.checkbox("Pomeriggio")
                tn = c3.checkbox("Notte")
                m = st.text_input("Medico Prescrittore")
                if st.form_submit_button("CONFERMA VARIAZIONE"):
                    if f and m:
                        t_list = []
                        if tm: t_list.append("M")
                        if tp: t_list.append("P")
                        if tn: t_list.append("N")
                        data_ora = datetime.now().strftime("%d/%m/%y %H:%M")
                        db_run("INSERT INTO terapie (p_id, farmaco, dosaggio, turni, medico, data_prescr) VALUES (?,?,?,?,?,?)", 
                               (p_id, f, d, ",".join(t_list), m, data_ora), True)
                        db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", 
                               (p_id, data_ora, "Stabile", f"➕ [VARIAZIONE] Inserito {f} ({d})", "Psichiatra", m), True)
                        st.success(f"Terapia aggiornata per {f}")
                        st.rerun()

            st.write("### 💊 Terapie Attive e Variazioni")
            storico_t = db_run("SELECT farmaco, dosaggio, turni, medico, data_prescr, row_id FROM terapie WHERE p_id=? ORDER BY row_id DESC", (p_id,))
            
            if storico_t:
                h = '<table class="clinica-table"><tr><th>DATA</th><th>FARMACO</th><th>DOSAGGIO</th><th>TURNI</th><th>MEDICO</th><th>AZIONE</th></tr>'
                st.markdown(h, unsafe_allow_html=True)
                for fa, do, tu, me, da, rid in storico_t:
                    col1, col2, col3, col4, col5, col6 = st.columns([2,2,2,1,2,1])
                    col1.write(da)
                    col2.write(f"**{fa}**")
                    col3.write(do)
                    col4.write(tu)
                    col5.write(me)
                    if col6.button("Sospendi", key=f"del_{rid}"):
                        db_run("DELETE FROM terapie WHERE row_id=?", (rid,), True)
                        db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", 
                               (p_id, datetime.now().strftime("%d/%m/%y %H:%M"), "Stabile", f"❌ [VARIAZIONE] SOSPESO {fa}", "Psichiatra", "Sistema"), True)
                        st.rerun()
                st.markdown("</table>", unsafe_allow_html=True)
            else:
                st.info("Nessun farmaco in terapia.")

        # --- INFERMIERE ---
        elif figura == "Infermiere":
            st.subheader("💉 Somministrazione Turno")
            c_d, c_t = st.columns(2)
            d_sel = c_d.date_input("Data", date.today())
            t_sel = c_t.selectbox("Turno", ["Mattina", "Pomeriggio", "Notte"])
            sigla = t_sel[0]
            inf_f = st.text_input("Firma Infermiere")
            
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

# --- ALTRE SEZIONI (MONITORAGGIO / GESTIONE) ---
elif menu == "Monitoraggio":
    pazienti = db_run("SELECT * FROM pazienti ORDER BY nome")
    for p_id, nome in pazienti:
        with st.expander(f"👤 DIARIO CLINICO: {nome.upper()}"):
            note = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY row_id DESC", (p_id,))
            if note:
                h = '<table class="clinica-table">'
                for d, ru, op, nt in note:
                    bg = "#f0fdf4" if "REP_" in nt else ("#fff1f2" if "SOSPESO" in nt else ("#fffbeb" if "VARIAZIONE" in nt else "white"))
                    h += f'<tr style="background:{bg}"><td>{d}</td><td><b>{ru}</b><br>{op}</td><td>{nt}</td></tr>'
                st.markdown(h + '</table>', unsafe_allow_html=True)

elif menu == "Gestione":
    st.subheader("⚙️ Amministrazione")
    nuovo = st.text_input("Aggiungi Paziente")
    if st.button("SALVA"):
        if nuovo: db_run("INSERT INTO pazienti (nome) VALUES (?)", (nuovo,), True); st.rerun()
