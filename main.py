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
    .consegna-box { background-color: #fff7ed; border-left: 5px solid #f97316; padding: 10px; margin-bottom: 10px; border-radius: 4px; }
</style>
""", unsafe_allow_html=True)

# --- 2. GESTIONE DATABASE ---
DB_NAME = "rems_connect_data.db"

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, umore TEXT, nota TEXT, ruolo TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dosaggio TEXT, turni TEXT, medico TEXT, data_prescr TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS soldi (p_id INTEGER, data TEXT, desc TEXT, importo REAL, tipo TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        if query: cur.execute(query, params)
        if commit: conn.commit()
        return cur.fetchall()

# --- 3. LOGIN ---
if 'auth' not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.markdown("<h1 class='main-title'>REMS CONNECT PRO - LOGIN</h1>", unsafe_allow_html=True)
    with st.container():
        col_l1, col_l2, col_l3 = st.columns([1,1,1])
        with col_l2:
            with st.form("login_form"):
                pwd = st.text_input("Codice Accesso", type="password")
                if st.form_submit_button("ENTRA"):
                    if pwd in ["rems2026", "admin2026"]:
                        st.session_state.auth = True
                        st.rerun()
                    else: st.error("Codice errato")
    st.stop()

# --- 4. NAVIGAZIONE ---
st.sidebar.title("MENU")
menu = st.sidebar.radio("VAI A:", ["Monitoraggio", "Equipe", "Gestione"])

# --- 5. LOGICA SEZIONI ---

# --- GESTIONE PAZIENTI ---
if menu == "Gestione":
    st.header("⚙️ Gestione Pazienti")
    t1, t2, t3 = st.tabs(["➕ Aggiungi", "📝 Modifica", "🗑️ Elimina"])
    with t1:
        with st.form("add"):
            n = st.text_input("Nome e Cognome")
            if st.form_submit_button("REGISTRA"):
                if n: db_run("INSERT INTO pazienti (nome) VALUES (?)", (n,), True); st.rerun()
    with t2:
        p_list = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
        if p_list:
            sel = st.selectbox("Seleziona", [p[1] for p in p_list], key="m")
            id_m = [p[0] for p in p_list if p[1] == sel][0]
            nuovo = st.text_input("Nuovo Nome", value=sel)
            if st.button("AGGIORNA"):
                db_run("UPDATE pazienti SET nome=? WHERE id=?", (nuovo, id_m), True); st.rerun()
    with t3:
        p_list_d = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
        if p_list_d:
            sel_d = st.selectbox("Seleziona", [p[1] for p in p_list_d], key="d")
            id_d = [p[0] for p in p_list_d if p[1] == sel_d][0]
            if st.button("ELIMINA DEFINITIVAMENTE"):
                db_run("DELETE FROM pazienti WHERE id=?", (id_d,), True); st.rerun()

# --- EQUIPE ---
elif menu == "Equipe":
    ruolo = st.sidebar.selectbox("Ruolo", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
    pazienti = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    
    if pazienti:
        p_nome = st.selectbox("Seleziona Paziente", [p[1] for p in pazienti])
        p_id = [p[0] for p in pazienti if p[1] == p_nome][0]
        st.divider()

        # --- PSICHIATRA ---
        if ruolo == "Psichiatra":
            st.subheader("📋 Gestione Terapia")
            med_f = st.text_input("Firma Medico (OBBLIGATORIA)")
            with st.expander("➕ Nuova Prescrizione"):
                with st.form("p_form"):
                    f, d = st.text_input("Farmaco"), st.text_input("Dose")
                    c1,c2,c3 = st.columns(3)
                    m, p, n = c1.checkbox("M"), c2.checkbox("P"), c3.checkbox("N")
                    if st.form_submit_button("SALVA"):
                        if not med_f: st.error("Firma obbligatoria!"); st.stop()
                        ts = ",".join([s for s, b in zip(["M","P","N"], [m,p,n]) if b])
                        db_run("INSERT INTO terapie (p_id, farmaco, dosaggio, turni, medico, data_prescr) VALUES (?,?,?,?,?,?)", (p_id, f, d, ts, med_f, date.today().strftime("%d/%m/%Y")), True); st.rerun()

            st.write("#### 💊 Terapie Attive")
            ta = db_run("SELECT data_prescr, farmaco, dosaggio, turni, medico, row_id FROM terapie WHERE p_id=? ORDER BY row_id DESC", (p_id,))
            if ta:
                st.markdown("<table class='custom-table'><tr><th>DATA</th><th>FARMACO</th><th>DOSE</th><th>TURNI</th><th>MEDICO</th><th>AZIONE</th></tr>", unsafe_allow_html=True)
                for da, fa, ds, tu, me, rid in ta:
                    c1,c2,c3,c4,c5,c6 = st.columns([1.5, 2, 1, 1, 1.5, 1])
                    c1.write(da); c2.write(f"**{fa}**"); c3.write(ds); c4.write(tu); c5.write(me)
                    if c6.button("🗑️ Sospendi", key=rid):
                        if not med_f: st.error("Firma obbligatoria!"); st.stop()
                        db_run("DELETE FROM terapie WHERE row_id=?", (rid,), True)
                        db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), "Stabile", f"❌ SOSPESO: {fa}", "Psichiatra", med_f), True); st.rerun()

        # --- INFERMIERE (CON CONSEGNE DI TURNO) ---
        elif ruolo == "Infermiere":
            st.subheader("💉 Area Infermieristica")
            inf_f = st.text_input("Firma Infermiere (OBBLIGATORIA)")
            
            tab_somm, tab_cons = st.tabs(["💊 Somministrazione", "📝 Consegne di Turno"])
            
            with tab_somm:
                col_d, col_t = st.columns(2)
                d_s = col_d.date_input("Data", date.today())
                t_s = col_t.selectbox("Turno", ["Mattina", "Pomeriggio", "Notte"])
                ter = db_run("SELECT farmaco, dosaggio, turni, row_id FROM terapie WHERE p_id=?", (p_id,))
                for f, d, tu_p, rid in ter:
                    if tu_p and t_s[0] in tu_p:
                        st.markdown("<div class='card-box'>", unsafe_allow_html=True)
                        ca, cb, cc = st.columns([2, 2, 1])
                        ca.write(f"**{f}** ({d})")
                        es = cb.radio("Esito", ["Assunta", "Rifiutata"], key=f"es_{rid}_{t_s[0]}", horizontal=True)
                        if cc.button("CONVALIDA", key=f"bt_{rid}_{t_s[0]}"):
                            if not inf_f: st.error("Firma obbligatoria!"); st.stop()
                            db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, f"{d_s.strftime('%d/%m/%Y')} {datetime.now().strftime('%H:%M')}", "Stabile", f"[{t_s[0]}] {f} -> {es}", "Infermiere", inf_f), True); st.rerun()
                        st.markdown("</div>", unsafe_allow_html=True)

            with tab_cons:
                st.write("#### Registra Consegna Clinica")
                turno_cons = st.selectbox("Turno Consegna", ["Mattina", "Pomeriggio", "Notte"], key="t_cons")
                testo_cons = st.text_area("Dettaglio consegna (andamento turno, rilievi clinici, parametri)", height=150)
                if st.button("SALVA CONSEGNA"):
                    if not inf_f:
                        st.error("ERRORE: Inserire la firma per salvare la consegna.")
                    elif not testo_cons:
                        st.warning("Il testo della consegna è vuoto.")
                    else:
                        nota_finale = f"📝 CONSEGNA [{turno_cons}]: {testo_cons}"
                        db_run("INSERT INTO eventi (id, data, umore, nota, ruolo, op) VALUES (?,?,?,?,?,?)",
                               (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), "Stabile", nota_finale, "Infermiere", inf_f), True)
                        st.success("Consegna registrata correttamente nel diario.")
                        st.rerun()

        # --- EDUCATORE ---
        elif ruolo == "Educatore":
            st.subheader("💰 Contabilità")
            ed_f = st.text_input("Firma Educatore (OBBLIGATORIA)")
            mov = db_run("SELECT data, desc, importo, tipo, op FROM soldi WHERE p_id=? ORDER BY row_id DESC", (p_id,))
            saldo = sum([m[2] if m[3] == "Entrata" else -m[2] for m in mov])
            st.markdown(f'<div class="saldo-box">Saldo: € {saldo:.2f}</div>', unsafe_allow_html=True)
            with st.expander("Nuovo Movimento"):
                tm, im, ds = st.radio("Tipo", ["Entrata", "Uscita"], horizontal=True), st.number_input("€", min_value=0.0), st.text_input("Causale")
                if st.button("REGISTRA"):
                    if not ed_f: st.error("Firma obbligatoria!"); st.stop()
                    db_run("INSERT INTO soldi (p_id, data, desc, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, date.today().strftime("%d/%m/%Y"), ds, im, tm, ed_f), True); st.rerun()
            if mov:
                st.markdown("<table class='custom-table'><tr><th>DATA</th><th>CAUSALE</th><th>ENTRATA</th><th>USCITA</th><th>FIRMA</th></tr>", unsafe_allow_html=True)
                for d, ds, im, tp, op in mov:
                    e = f"<span class='txt-entrata'>€ {im:.2f}</span>" if tp == "Entrata" else ""
                    u = f"<span class='txt-uscita'>€ {im:.2f}</span>" if tp == "Uscita" else ""
                    st.markdown(f"<tr><td>{d}</td><td>{ds}</td><td>{e}</td><td>{u}</td><td>{op}</td></tr>", unsafe_allow_html=True)

        # --- OSS ---
        elif ruolo == "OSS":
            st.subheader("🧹 Mansioni OSS")
            with st.form("oss"):
                c1,c2 = st.columns(2)
                m1, m2, m3 = c1.checkbox("Pulizia Camera"), c1.checkbox("Pulizia Refettorio"), c1.checkbox("Pulizia Sala Fumo")
                m4, m5 = c2.checkbox("Pulizia Cortile"), c2.checkbox("Lavatrice")
                oss_f = st.text_input("Firma OSS (OBBLIGATORIA)")
                if st.form_submit_button("REGISTRA"):
                    if not oss_f: st.error("Firma obbligatoria!"); st.stop()
                    ms = [t for b,t in zip([m1,m2,m3,m4,m5], ["Camera","Refettorio","Sala Fumo","Cortile","Lavatrice"]) if b]
                    if ms: db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), "Stabile", f"🧹 Pulizie: {', '.join(ms)}", "OSS", oss_f), True); st.rerun()

# --- MONITORAGGIO ---
elif menu == "Monitoraggio":
    st.header("📊 Diario Clinico")
    p_mon = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    for pid, nome in p_mon:
        with st.expander(f"👤 {nome.upper()}"):
            log = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY row_id DESC", (pid,))
            if log:
                st.markdown("<table class='custom-table'><tr><th>DATA</th><th>RUOLO</th><th>OPERATORE</th><th>NOTA</th></tr>", unsafe_allow_html=True)
                for d, r, o, n in log:
                    st.markdown(f"<tr><td>{d}</td><td><b>{r}</b></td><td>{o}</td><td>{n}</td></tr>", unsafe_allow_html=True)
                st.markdown("</table>", unsafe_allow_html=True)
