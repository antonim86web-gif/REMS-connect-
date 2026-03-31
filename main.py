import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date

# --- 1. CONFIGURAZIONE PAGINA E CSS ---
st.set_page_config(page_title="REMS Connect PRO", layout="wide")

st.markdown("""
<style>
    .main-title {text-align: center; color: #1e3a8a; font-weight: bold; margin-bottom:20px;}
    .custom-table {width: 100%; border-collapse: collapse; font-size: 0.85rem; background: white; margin-top: 10px;}
    .custom-table th {background-color: #1e3a8a; color: white; padding: 10px; text-align: left; border: 1px solid #dee2e6;}
    .custom-table td {padding: 10px; border: 1px solid #dee2e6; vertical-align: middle;}
    .card-box { border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; margin-bottom: 10px; background: #ffffff; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .saldo-box { padding: 15px; border-radius: 10px; background-color: #f8fafc; text-align: center; border: 2px solid #1e3a8a; font-weight: bold; font-size: 1.2rem; margin-bottom: 15px; }
    .txt-uscita { color: #ef4444; font-weight: bold; }
    .txt-entrata { color: #10b981; font-weight: bold; }
    .badge-turno { background: #e0f2fe; color: #0369a1; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 0.75rem; }
</style>
""", unsafe_allow_html=True)

# --- 2. GESTIONE DATABASE (SQLITE) ---
DB_NAME = "rems_connect_data.db"

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        # Inizializzazione tabelle se non esistenti
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, umore TEXT, nota TEXT, ruolo TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dosaggio TEXT, turni TEXT, medico TEXT, data_prescr TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS soldi (p_id INTEGER, data TEXT, desc TEXT, importo REAL, tipo TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        
        if query:
            cur.execute(query, params)
        if commit:
            conn.commit()
        return cur.fetchall()

# --- 3. SISTEMA DI AUTENTICAZIONE ---
if 'auth' not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.markdown("<h1 class='main-title'>REMS CONNECT PRO - LOGIN</h1>", unsafe_allow_html=True)
    with st.container():
        col_l1, col_l2, col_l3 = st.columns([1,1,1])
        with col_l2:
            with st.form("login_form"):
                pwd = st.text_input("Inserire Codice Operatore", type="password")
                if st.form_submit_button("ACCEDI"):
                    if pwd in ["rems2026", "admin2026"]:
                        st.session_state.auth = True
                        st.rerun()
                    else:
                        st.error("Codice errato")
    st.stop()

# --- 4. BARRA LATERALE E NAVIGAZIONE ---
st.sidebar.title("MENU PRINCIPALE")
menu = st.sidebar.radio("VAI A:", ["Monitoraggio", "Equipe", "Gestione"])

# --- 5. LOGICA DELLE SEZIONI ---

# --- SEZIONE GESTIONE (ANAGRAFICA) ---
if menu == "Gestione":
    st.header("⚙️ Gestione Pazienti")
    tab_agg, tab_mod, tab_elim = st.tabs(["➕ Nuovo Paziente", "📝 Modifica Nome", "🗑️ Dimissione/Elimina"])
    
    with tab_agg:
        with st.form("form_aggiunta"):
            nome_nuovo = st.text_input("Nome e Cognome Paziente")
            if st.form_submit_button("REGISTRA INGRESSO"):
                if nome_nuovo:
                    db_run("INSERT INTO pazienti (nome) VALUES (?)", (nome_nuovo,), True)
                    st.success(f"{nome_nuovo} aggiunto al sistema.")
                    st.rerun()
    
    with tab_mod:
        paz_mod = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
        if paz_mod:
            sel_m = st.selectbox("Seleziona paziente da modificare", [p[1] for p in paz_mod], key="sel_mod")
            id_m = [p[0] for p in paz_mod if p[1] == sel_m][0]
            nuovo_n = st.text_input("Nuovo Nome", value=sel_m)
            if st.button("SALVA MODIFICA"):
                db_run("UPDATE pazienti SET nome=? WHERE id=?", (nuovo_n, id_m), True)
                st.rerun()

    with tab_elim:
        paz_del = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
        if paz_del:
            sel_d = st.selectbox("Seleziona paziente da eliminare", [p[1] for p in paz_del], key="sel_del")
            id_d = [p[0] for p in paz_del if p[1] == sel_d][0]
            st.warning("L'operazione cancellerà definitivamente ogni dato (terapia, soldi, diari).")
            if st.button("ELIMINA DEFINITIVAMENTE"):
                db_run("DELETE FROM pazienti WHERE id=?", (id_d,), True)
                db_run("DELETE FROM eventi WHERE id=?", (id_d,), True)
                db_run("DELETE FROM terapie WHERE p_id=?", (id_d,), True)
                db_run("DELETE FROM soldi WHERE p_id=?", (id_d,), True)
                st.rerun()

# --- SEZIONE EQUIPE (OPERATIVITÀ) ---
elif menu == "Equipe":
    ruolo = st.sidebar.selectbox("Seleziona Ruolo Operativo", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
    pazienti = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    
    if pazienti:
        p_nome = st.selectbox("Seleziona Paziente", [p[1] for p in pazienti])
        p_id = [p[0] for p in pazienti if p[1] == p_nome][0]
        st.divider()

        # 1. PSICHIATRA
        if ruolo == "Psichiatra":
            st.subheader("📋 Gestione Terapia Farmacologica")
            firma_medico = st.text_input("Firma Medico (OBBLIGATORIA)")
            
            with st.expander("➕ Nuova Prescrizione"):
                with st.form("presc_form"):
                    farmaco = st.text_input("Nome Farmaco")
                    dose = st.text_input("Dosaggio")
                    st.write("Orari Somministrazione:")
                    c1, c2, c3 = st.columns(3)
                    m = c1.checkbox("Mattina (M)")
                    p = c2.checkbox("Pomeriggio (P)")
                    n = c3.checkbox("Notte (N)")
                    if st.form_submit_button("REGISTRA IN DATABASE"):
                        if not firma_medico: 
                            st.error("ERRORE: Inserire la firma prima di prescrivere.")
                        else:
                            turni = [s for s, b in zip(["M", "P", "N"], [m, p, n]) if b]
                            db_run("INSERT INTO terapie (p_id, farmaco, dosaggio, turni, medico, data_prescr) VALUES (?,?,?,?,?,?)", 
                                   (p_id, farmaco, dose, ",".join(turni), firma_medico, date.today().strftime("%d/%m/%Y")), True)
                            st.rerun()

            st.write("#### 💊 Terapie Attualmente in Vigore")
            t_attive = db_run("SELECT data_prescr, farmaco, dosaggio, turni, medico, row_id FROM terapie WHERE p_id=? ORDER BY row_id DESC", (p_id,))
            if t_attive:
                tab_h = "<table class='custom-table'><tr><th>DATA</th><th>FARMACO</th><th>DOSE</th><th>TURNI</th><th>MEDICO</th><th>AZIONE</th></tr>"
                st.markdown(tab_h, unsafe_allow_html=True)
                for d_p, f_p, d_s, t_u, m_e, r_id in t_attive:
                    c1, c2, c3, c4, c5, c6 = st.columns([1.5, 2, 1.5, 1, 1.5, 1.2])
                    c1.write(d_p); c2.markdown(f"**{f_p}**"); c3.write(d_s); c4.write(t_u); c5.write(m_e)
                    if c6.button("🛑 Sospendi", key=f"sosp_{r_id}"):
                        if not firma_medico:
                            st.error("Firma obbligatoria per sospendere.")
                        else:
                            db_run("DELETE FROM terapie WHERE row_id=?", (r_id,), True)
                            db_run("INSERT INTO eventi (id, data, umore, nota, ruolo, op) VALUES (?,?,?,?,?,?)",
                                   (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), "Stabile", f"❌ SOSPESO: {f_p}", "Psichiatra", firma_medico), True)
                            st.rerun()
                st.markdown("</table>", unsafe_allow_html=True)

        # 2. INFERMIERE
        elif ruolo == "Infermiere":
            st.subheader("💉 Somministrazione Terapie")
            inf_firma = st.text_input("Firma Infermiere Somministratore (OBBLIGATORIA)")
            col_d, col_t = st.columns(2)
            data_s = col_d.date_input("Data Somministrazione", date.today())
            turno_s = col_t.selectbox("Turno Somministrazione", ["Mattina", "Pomeriggio", "Notte"])
            sigla_t = turno_s[0] # M, P o N
            
            t_da_somm = db_run("SELECT farmaco, dosaggio, turni, row_id FROM terapie WHERE p_id=?", (p_id,))
            for f, d, turni_p, rid in t_da_somm:
                if turni_p and sigla_t in turni_p:
                    tag_controllo = f"[{sigla_t}] {f}"
                    data_str = data_s.strftime("%d/%m/%Y")
                    # Verifica se già registrato per oggi/turno
                    gia_fatto = db_run("SELECT op, nota FROM eventi WHERE id=? AND nota LIKE ? AND data LIKE ?", (p_id, f"%{tag_controllo}%", f"{data_str}%"))
                    
                    st.markdown("<div class='card-box'>", unsafe_allow_html=True)
                    ca, cb, cc = st.columns([2, 2, 1])
                    ca.write(f"**{f}**<br><small>{d}</small>", unsafe_allow_html=True)
                    if gia_fatto:
                        cb.write(f"✅ {gia_fatto[0][1].split('->')[-1]} ({gia_fatto[0][0]})")
                    else:
                        esito = cb.radio("Esito", ["Assunta", "Rifiutata"], key=f"es_{rid}_{sigla_t}", horizontal=True)
                        if cc.button("CONVALIDA", key=f"btn_{rid}_{sigla_t}"):
                            if not inf_firma:
                                st.error("Firma obbligatoria!")
                            else:
                                db_run("INSERT INTO eventi (id, data, umore, nota, ruolo, op) VALUES (?,?,?,?,?,?)",
                                       (p_id, f"{data_str} {datetime.now().strftime('%H:%M')}", "Stabile", f"{tag_controllo} -> {esito}", "Infermiere", inf_firma), True)
                                st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)

        # 3. EDUCATORE
        elif ruolo == "Educatore":
            st.subheader("💰 Registro Contabilità Paziente")
            ed_firma = st.text_input("Firma Educatore (OBBLIGATORIA)")
            
            movimenti = db_run("SELECT data, desc, importo, tipo, op FROM soldi WHERE p_id=? ORDER BY row_id DESC", (p_id,))
            saldo = sum([m[2] if m[3] == "Entrata" else -m[2] for m in movimenti])
            st.markdown(f'<div class="saldo-box">SALDO DISPONIBILE: € {saldo:.2f}</div>', unsafe_allow_html=True)
            
            with st.expander("📝 Registra Entrata/Uscita"):
                tipo_m = st.radio("Tipo Operazione", ["Entrata", "Uscita"], horizontal=True)
                importo_m = st.number_input("Cifra in €", min_value=0.0, step=0.5)
                causale_m = st.text_input("Causale/Nota")
                if st.button("ESEGUI TRANSAZIONE"):
                    if not ed_firma:
                        st.error("Firma obbligatoria per la gestione soldi.")
                    else:
                        db_run("INSERT INTO soldi (p_id, data, desc, importo, tipo, op) VALUES (?,?,?,?,?,?)", 
                               (p_id, date.today().strftime("%d/%m/%Y"), causale_m, importo_m, tipo_m, ed_firma), True)
                        st.rerun()
            
            if movimenti:
                tab_s = "<table class='custom-table'><tr><th>DATA</th><th>DESCRIZIONE</th><th>ENTRATA</th><th>USCITA</th><th>OPERATORE</th></tr>"
                for d, ds, im, tp, op in movimenti:
                    ent = f"<span class='txt-entrata'>€ {im:.2f}</span>" if tp == "Entrata" else ""
                    usc = f"<span class='txt-uscita'>€ {im:.2f}</span>" if tp == "Uscita" else ""
                    tab_s += f"<tr><td>{d}</td><td>{ds}</td><td>{ent}</td><td>{usc}</td><td>{op}</td></tr>"
                st.markdown(tab_s + "</table>", unsafe_allow_html=True)

        # 4. OSS
        elif ruolo == "OSS":
            st.subheader("🧹 Mansioni e Igiene")
            with st.form("oss_form"):
                st.write("Mansioni del turno:")
                o1 = st.checkbox("Pulizia Camera")
                o2 = st.checkbox("Pulizia Refettorio")
                o3 = st.checkbox("Pulizia Sala Fumo")
                o4 = st.checkbox("Pulizia Cortile")
                o5 = st.checkbox("Lavatrice")
                firma_oss = st.text_input("Firma OSS (OBBLIGATORIA)")
                if st.form_submit_button("REGISTRA ATTIVITÀ"):
                    if not firma_oss:
                        st.error("Inserire la firma.")
                    else:
                        fatte = [t for b, t in zip([o1,o2,o3,o4,o5], ["Camera", "Refettorio", "Sala Fumo", "Cortile", "Lavatrice"]) if b]
                        if fatte:
                            db_run("INSERT INTO eventi (id, data, umore, nota, ruolo, op) VALUES (?,?,?,?,?,?)",
                                   (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), "Stabile", f"🧹 Pulizie: {', '.join(fatte)}", "OSS", firma_oss), True)
                            st.success("Registrato.")
                            st.rerun()
                        else:
                            st.warning("Seleziona almeno una mansione.")

# --- SEZIONE MONITORAGGIO (DIARIO CLINICO) ---
elif menu == "Monitoraggio":
    st.header("📊 Diario Clinico Integrato")
    paz_mon = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    for pid, nome in paz_mon:
        with st.expander(f"📖 SCHEDA DIARIO: {nome.upper()}"):
            log = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY row_id DESC", (pid,))
            if log:
                tab_m = "<table class='custom-table'><tr><th>DATA E ORA</th><th>RUOLO</th><th>OPERATORE</th><th>DETTAGLIO ATTIVITÀ</th></tr>"
                for d, r, o, n in log:
                    tab_m += f"<tr><td>{d}</td><td><b>{r}</b></td><td>{o}</td><td>{n}</td></tr>"
                st.markdown(tab_m + "</table>", unsafe_allow_html=True)
            else:
                st.info("Nessuna attività registrata per questo paziente.")
