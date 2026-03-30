import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date

# --- 1. CONFIGURAZIONE & STILE ---
st.set_page_config(page_title="REMS Connect PRO", layout="wide")

st.markdown("""
<style>
    .main-title {text-align: center; color: #1e3a8a; font-weight: bold; margin-bottom:20px;}
    .status-ok {color: #10b981; font-weight: bold; background: #ecfdf5; padding: 5px; border-radius: 5px; border: 1px solid #10b981;}
    .clinica-table {width: 100%; border-collapse: collapse; font-size: 0.85rem;}
    .clinica-table td {padding: 12px; border-bottom: 1px solid #eee; vertical-align: top;}
    .saldo-box {padding: 20px; border-radius: 10px; background-color: #f8fafc; text-align: center; border: 2px solid #1e3a8a; margin-bottom: 20px;}
</style>
""", unsafe_allow_html=True)

# --- 2. DATABASE CON MIGRAZIONE AUTOMATICA ---
DB_NAME = "rems_connect_data.db"

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, umore TEXT, nota TEXT, ruolo TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dosaggio TEXT, turni TEXT, medico TEXT, data_prescr TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS soldi (p_id INTEGER, data TEXT, desc TEXT, importo REAL, tipo TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        
        # Migrazioni per colonne mancanti
        try: cur.execute("ALTER TABLE terapie ADD COLUMN turni TEXT")
        except: pass
        try: cur.execute("ALTER TABLE terapie ADD COLUMN data_prescr TEXT")
        except: pass

        if query: cur.execute(query, params)
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
                st.session_state.role = "admin" if pwd == "admin2026" else "user"
                st.rerun()
    st.stop()

# --- 4. NAVIGAZIONE ---
menu = st.sidebar.radio("MENU PRINCIPALE", ["Monitoraggio", "Equipe", "Gestione"])

# --- 5. MONITORAGGIO (DIARIO CLINICO) ---
if menu == "Monitoraggio":
    pazienti = db_run("SELECT * FROM pazienti ORDER BY nome")
    for p_id, nome in pazienti:
        with st.expander(f"👤 DIARIO CLINICO: {nome.upper()}"):
            note = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY row_id DESC", (p_id,))
            if note:
                html = '<table class="clinica-table">'
                for d, ru, op, nt in note:
                    # Colori dinamici per tipologia evento
                    bg = "#f0fdf4" if "REPORT" in nt else ("#fff1f2" if "SOSPESO" in nt else ("#fffbeb" if "VARIAZIONE" in nt else "white"))
                    html += f'<tr style="background-color:{bg};"><td><small>{d}</small></td><td><b>{ru}</b><br><small>{op}</small></td><td>{nt}</td></tr>'
                st.markdown(html + '</table>', unsafe_allow_html=True)
            else: st.info("Nessuna nota presente.")

# --- 6. AREA EQUIPE (PSICHIATRA / INFERMIERE / EDUCATORI) ---
elif menu == "Equipe":
    figura = st.sidebar.selectbox("Ruolo Professionale", ["Psichiatra", "Infermiere", "Educatore"])
    paz = db_run("SELECT * FROM pazienti ORDER BY nome")
    
    if paz:
        sel_p = st.selectbox("Seleziona Paziente in carico", [p[1] for p in paz])
        p_id = [p[0] for p in paz if p[1] == sel_p][0]
        st.divider()

        # --- SEZIONE PSICHIATRA ---
        if figura == "Psichiatra":
            st.subheader("📋 Gestione Terapie")
            with st.form("presc_form"):
                c1, c2 = st.columns(2)
                f_nome = c1.text_input("Nome Farmaco")
                f_dose = c2.text_input("Dosaggio/Posologia")
                st.write("Turni di somministrazione:")
                t1, t2, t3 = st.columns(3)
                tm = t1.checkbox("Mattina (08:00)")
                tp = t2.checkbox("Pomeriggio (14:00)")
                tn = t3.checkbox("Notte (22:00)")
                f_med = st.text_input("Medico Prescrittore")
                if st.form_submit_button("CONFERMA VARIAZIONE"):
                    if f_nome and f_med:
                        turni_scelti = []
                        if tm: turni_scelti.append("M")
                        if tp: turni_scelti.append("P")
                        if tn: turni_scelti.append("N")
                        data_ora = datetime.now().strftime("%d/%m/%y %H:%M")
                        db_run("INSERT INTO terapie (p_id, farmaco, dosaggio, turni, medico, data_prescr) VALUES (?,?,?,?,?,?)", 
                               (p_id, f_nome, f_dose, ",".join(turni_scelti), f_med, data_ora), True)
                        db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", 
                               (p_id, data_ora, "Stabile", f"➕ [VARIAZIONE] Inserito {f_nome} ({f_dose})", "Psichiatra", f_med), True)
                        st.rerun()

            st.write("### 💊 Terapie Attive e Variazioni")
            storico_t = db_run("SELECT data_prescr, farmaco, dosaggio, turni, medico, row_id FROM terapie WHERE p_id=? ORDER BY row_id DESC", (p_id,))
            if storico_t:
                # Header Tabella
                h_cols = st.columns([2, 2, 2, 1, 2, 1])
                h_cols[0].write("**DATA**")
                h_cols[1].write("**FARMACO**")
                h_cols[2].write("**DOSAGGIO**")
                h_cols[3].write("**TURNI**")
                h_cols[4].write("**MEDICO**")
                h_cols[5].write("**AZIONE**")
                
                for da, fa, do, tu, me, rid in storico_t:
                    r_cols = st.columns([2, 2, 2, 1, 2, 1])
                    r_cols[0].write(da if da else "-")
                    r_cols[1].write(f"**{fa}**")
                    r_cols[2].write(do)
                    r_cols[3].write(tu)
                    r_cols[4].write(me)
                    if r_cols[5].button("Sospendi", key=f"sosp_{rid}"):
                        db_run("DELETE FROM terapie WHERE row_id=?", (rid,), True)
                        db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", 
                               (p_id, datetime.now().strftime("%d/%m/%y %H:%M"), "Stabile", f"❌ [VARIAZIONE] SOSPESO {fa}", "Psichiatra", "Medico"), True)
                        st.rerun()
            else: st.info("Nessun farmaco registrato.")

        # --- SEZIONE INFERMIERE ---
        elif figura == "Infermiere":
            st.subheader("💉 Somministrazione Terapia")
            c_d, c_t = st.columns(2)
            d_sel = c_d.date_input("Data Somministrazione", date.today())
            t_sel = c_t.selectbox("Turno Operativo", ["Mattina", "Pomeriggio", "Notte"])
            sigla = t_sel[0] # M, P, N
            inf_f = st.text_input("Firma Infermiere in Turno")
            
            data_str = d_sel.strftime("%d/%m/%Y")
            st.write(f"#### 💊 Turno selezionato: {t_sel}")
            
            terapie = db_run("SELECT farmaco, dosaggio, turni, row_id FROM terapie WHERE p_id=?", (p_id,))
            for f, d, turni_f, rid in terapie:
                if turni_f and sigla in turni_f:
                    tag_rep = f"[REPORT_{sigla}] {f}"
                    fatto = db_run("SELECT op FROM eventi WHERE id=? AND nota LIKE ? AND data LIKE ?", (p_id, f"%{tag_rep}%", f"{data_str}%"))
                    
                    with st.container():
                        col1, col2, col3 = st.columns([3, 3, 2])
                        col1.markdown(f"**{f}**<br><small>{d}</small>", unsafe_allow_html=True)
                        if fatto:
                            col2.markdown(f"<div class='status-ok'>✅ Somministrato da {fatto[0][0]}</div>", unsafe_allow_html=True)
                        else:
                            esito = col2.selectbox("Esito", ["Assunta", "Parziale", "Rifiutata"], key=f"es_{rid}_{sigla}")
                            if col3.button("CONVALIDA", key=f"btn_{rid}_{sigla}"):
                                if inf_f:
                                    log_nota = f"{tag_rep} ({d}) -> {esito}"
                                    db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", 
                                           (p_id, f"{data_str} {datetime.now().strftime('%H:%M')}", "Stabile", log_nota, "Infermiere", inf_f), True)
                                    st.rerun()
                                else: st.error("Inserire la firma per convalidare!")

            st.divider()
            st.write("### 📑 Report Somministrazioni")
            reps = db_run("SELECT data, nota, op FROM eventi WHERE id=? AND nota LIKE '%[REPORT_%' ORDER BY row_id DESC LIMIT 20", (p_id,))
            if reps:
                st.table(pd.DataFrame(reps, columns=["Data/Ora", "Dettaglio Somministrazione", "Infermiere"]))

        # --- SEZIONE EDUCATORI ---
        elif figura == "Educatore":
            st.subheader("💰 Gestione Contabilità Paziente")
            movs = db_run("SELECT importo, tipo FROM soldi WHERE p_id=?", (p_id,))
            saldo = sum([m[0] if m[1] == "Entrata" else -m[0] for m in movs])
            st.markdown(f'<div class="saldo-box"><h5>SALDO DISPONIBILE</h5><h2>€ {saldo:.2f}</h2></div>', unsafe_allow_html=True)
            
            with st.expander("📝 Registra Nuova Transazione"):
                tipo_m = st.radio("Tipo Movimento", ["Entrata", "Uscita"], horizontal=True)
                imp_m = st.number_input("Importo (€)", min_value=0.0, step=0.50)
                cau_m = st.text_input("Causale/Descrizione")
                fir_m = st.text_input("Firma Educatore")
                if st.button("REGISTRA"):
                    if cau_m and fir_m:
                        db_run("INSERT INTO soldi (p_id, data, desc, importo, tipo, op) VALUES (?,?,?,?,?,?)", 
                               (p_id, date.today().strftime("%d/%m/%Y"), cau_m, imp_m, tipo_m, fir_m), True)
                        st.success("Movimento salvato!"); st.rerun()

            st.write("#### 📊 Estratto Conto")
            storico_s = db_run("SELECT data, desc, importo, tipo, op FROM soldi WHERE p_id=? ORDER BY row_id DESC", (p_id,))
            if storico_s:
                df_soldi = pd.DataFrame(storico_s, columns=["Data", "Causale", "Importo", "Tipo", "Operatore"])
                st.table(df_soldi)

# --- 7. GESTIONE AMMINISTRATIVA ---
elif menu == "Gestione":
    st.subheader("⚙️ Pannello Gestione")
    nuovo_p = st.text_input("Nome e Cognome nuovo paziente")
    if st.button("AGGIUNGI AL DATABASE"):
        if nuovo_p:
            db_run("INSERT INTO pazienti (nome) VALUES (?)", (nuovo_p,), True)
            st.success("Paziente aggiunto correttamente!"); st.rerun()
    
    st.divider()
    st.write("#### Elenco Pazienti Attivi")
    paz_list = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    for pid, n in paz_list:
        st.write(f"ID: {pid} - **{n}**")
