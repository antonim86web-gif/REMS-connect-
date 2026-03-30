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
    .status-ok { color: #10b981; font-weight: bold; border: 1px solid #10b981; padding: 2px 5px; border-radius: 4px; background: #f0fdf4; }
    .card-box { border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; margin-bottom: 10px; background: #ffffff; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .saldo-box { padding: 20px; border-radius: 10px; background-color: #f8fafc; text-align: center; border: 2px solid #1e3a8a; margin-bottom: 20px; }
    .entrata { color: #10b981; font-weight: bold; }
    .uscita { color: #ef4444; font-weight: bold; }
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

        # --- SEZIONE PSICHIATRA ---
        if figura == "Psichiatra":
            st.subheader("📋 Gestione Terapie")
            with st.form("presc_form"):
                f = st.text_input("Farmaco")
                d = st.text_input("Dosaggio")
                st.write("Turni:")
                c1, c2, c3 = st.columns(3)
                tm, tp, tn = c1.checkbox("M"), c2.checkbox("P"), c3.checkbox("N")
                med = st.text_input("Medico")
                if st.form_submit_button("CONFERMA VARIAZIONE"):
                    t_list = [s for s, b in zip(["M", "P", "N"], [tm, tp, tn]) if b]
                    dt = datetime.now().strftime("%d/%m/%y %H:%M")
                    db_run("INSERT INTO terapie (p_id, farmaco, dosaggio, turni, medico, data_prescr) VALUES (?,?,?,?,?,?)", 
                           (p_id, f, d, ",".join(t_list), med, dt), True)
                    st.rerun()

            st.write("### 💊 Terapie Attive")
            terapie = db_run("SELECT data_prescr, farmaco, dosaggio, turni, medico, row_id FROM terapie WHERE p_id=? ORDER BY row_id DESC", (p_id,))
            if terapie:
                html = "<table class='custom-table'><tr><th>DATA</th><th>FARMACO</th><th>DOS</th><th>T</th><th>MED</th></tr>"
                for da, fa, do, tu, me, rid in terapie:
                    html += f"<tr><td>{da}</td><td><b>{fa}</b></td><td>{do}</td><td><span class='badge-m'>{tu}</span></td><td>{me}</td></tr>"
                st.markdown(html + "</table>", unsafe_allow_html=True)
                with st.expander("Sospendi Farmaci"):
                    for da, fa, do, tu, me, rid in terapie:
                        if st.button(f"Sospendi {fa}", key=f"del_{rid}"):
                            db_run("DELETE FROM terapie WHERE row_id=?", (rid,), True)
                            db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", 
                                   (p_id, datetime.now().strftime("%d/%m/%y %H:%M"), "Stabile", f"❌ SOSPESO {fa}", "Psichiatra", "Sistema"), True)
                            st.rerun()

        # --- SEZIONE INFERMIERE ---
        elif figura == "Infermiere":
            st.subheader("💉 Gestione Somministrazione")
            col_a, col_b = st.columns(2)
            d_sel = col_a.date_input("Data", date.today())
            t_sel = col_b.selectbox("Turno Operativo", ["Mattina", "Pomeriggio", "Notte"])
            sigla = t_sel[0]
            inf_f = st.text_input("Firma Infermiere")
            
            data_s = d_sel.strftime("%d/%m/%Y")
            terapie = db_run("SELECT farmaco, dosaggio, turni, row_id FROM terapie WHERE p_id=?", (p_id,))
            
            for f, d, turni_f, rid in terapie:
                if turni_f and sigla in turni_f:
                    tag = f"[REP_{sigla}] {f}"
                    fatto = db_run("SELECT op, nota FROM eventi WHERE id=? AND nota LIKE ? AND data LIKE ?", (p_id, f"%{tag}%", f"{data_s}%"))
                    with st.container():
                        st.markdown(f"<div class='card-box'>", unsafe_allow_html=True)
                        c1, c2, c3 = st.columns([2, 2, 1])
                        c1.markdown(f"**{f}**<br><small>{d}</small>", unsafe_allow_html=True)
                        if fatto:
                            c2.markdown(f"<span class='status-ok'>✅ {fatto[0][1].split('->')[-1]}</span>", unsafe_allow_html=True)
                        else:
                            scelta = c2.radio("Esito:", ["Assunta", "Rifiutata", "Parziale"], key=f"opt_{rid}_{sigla}", horizontal=True)
                            if c3.button("OK", key=f"inf_{rid}_{sigla}"):
                                if inf_f:
                                    db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", 
                                           (p_id, f"{data_s} {datetime.now().strftime('%H:%M')}", "Stabile", f"{tag} -> {scelta}", "Infermiere", inf_f), True)
                                    st.rerun()
                        st.markdown("</div>", unsafe_allow_html=True)

        # --- SEZIONE EDUCATORI (RIPRISTINATA) ---
        elif figura == "Educatore":
            st.subheader("💰 Gestione Soldi Paziente")
            
            # Calcolo saldo
            movs = db_run("SELECT importo, tipo FROM soldi WHERE p_id=?", (p_id,))
            saldo = sum([m[0] if m[1] == "Entrata" else -m[0] for m in movs])
            
            st.markdown(f'<div class="saldo-box"><h5>SALDO ATTUALE</h5><h2>€ {saldo:.2f}</h2></div>', unsafe_allow_html=True)
            
            with st.expander("➕ Nuova Operazione"):
                tipo_m = st.radio("Tipo", ["Entrata", "Uscita"], horizontal=True)
                imp_m = st.number_input("Importo (€)", min_value=0.0, step=0.50)
                cau_m = st.text_input("Causale")
                fir_m = st.text_input("Firma Educatore")
                if st.button("REGISTRA MOVIMENTO"):
                    if cau_m and fir_m:
                        db_run("INSERT INTO soldi (p_id, data, desc, importo, tipo, op) VALUES (?,?,?,?,?,?)", 
                               (p_id, date.today().strftime("%d/%m/%Y"), cau_m, imp_m, tipo_m, fir_m), True)
                        st.success("Registrato!"); st.rerun()

            st.write("#### 📊 Estratto Conto")
            storico = db_run("SELECT data, desc, importo, tipo, op FROM soldi WHERE p_id=? ORDER BY row_id DESC", (p_id,))
            if storico:
                h_table = "<table class='custom-table'><tr><th>DATA</th><th>CAUSALE</th><th>ENTRATA</th><th>USCITA</th><th>OPERATORE</th></tr>"
                for d, ds, im, tp, op in storico:
                    en = f"€ {im:.2f}" if tp == "Entrata" else ""
                    us = f"€ {im:.2f}" if tp == "Uscita" else ""
                    h_table += f"<tr><td>{d}</td><td>{ds}</td><td class='entrata'>{en}</td><td class='uscita'>{us}</td><td>{op}</td></tr>"
                st.markdown(h_table + "</table>", unsafe_allow_html=True)

# --- MONITORAGGIO ---
elif menu == "Monitoraggio":
    pazienti = db_run("SELECT * FROM pazienti ORDER BY nome")
    for p_id, nome in pazienti:
        with st.expander(f"👤 DIARIO: {nome.upper()}"):
            note = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY row_id DESC", (p_id,))
            if note:
                h = "<table class='custom-table'><tr><th>DATA</th><th>RUOLO</th><th>NOTA</th></tr>"
                for d, ru, op, nt in note:
                    bg = "#f0fdf4" if "REP_" in nt else ("#fff1f2" if "SOSPESO" in nt else "white")
                    h += f"<tr style='background:{bg}'><td>{d}</td><td><b>{ru}</b><br>{op}</td><td>{nt}</td></tr>"
                st.markdown(h + "</table>", unsafe_allow_html=True)

# --- GESTIONE ---
elif menu == "Gestione":
    st.subheader("⚙️ Gestione Pazienti")
    nuovo = st.text_input("Nuovo Paziente")
    if st.button("SALVA"):
        if nuovo: db_run("INSERT INTO pazienti (nome) VALUES (?)", (nuovo,), True); st.rerun()
