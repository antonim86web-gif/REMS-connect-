import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date

# --- 1. CONFIGURAZIONE PAGINA E CSS AVANZATO ---
st.set_page_config(page_title="REMS Connect PRO", layout="wide")

st.markdown("""
<style>
    .main-title {text-align: center; color: #1e3a8a; font-weight: bold; margin-bottom:20px;}
    
    /* STILE TABELLA DIARIO CLINICO */
    .diario-table {
        width: 100%;
        border-collapse: collapse;
        margin: 10px 0;
        font-size: 0.9rem;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        background-color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .diario-table th {
        background-color: #1e3a8a;
        color: white;
        padding: 12px;
        text-align: left;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .diario-table td {
        padding: 12px;
        border-bottom: 1px solid #e2e8f0;
        vertical-align: top;
        line-height: 1.4;
    }
    .diario-table tr:nth-child(even) { background-color: #f8fafc; }
    .diario-table tr:hover { background-color: #f1f5f9; }

    /* BADGES RUOLI */
    .badge {
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: bold;
        color: white;
        display: inline-block;
    }
    .bg-psichiatra { background-color: #e11d48; } /* Rosso */
    .bg-infermiere { background-color: #2563eb; } /* Blu */
    .bg-educatore  { background-color: #059669; } /* Verde */
    .bg-oss        { background-color: #d97706; } /* Arancione */

    /* ALTRI STILI */
    .card-box { border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; margin-bottom: 10px; background: white; }
    .saldo-box { padding: 15px; border-radius: 10px; background-color: #f8fafc; text-align: center; border: 2px solid #1e3a8a; font-weight: bold; font-size: 1.2rem; }
    .txt-uscita { color: #ef4444; font-weight: bold; }
    .txt-entrata { color: #10b981; font-weight: bold; }
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

# --- 5. LOGICA SEZIONI ---

if menu == "Gestione":
    st.header("⚙️ Gestione Anagrafica")
    t1, t2, t3 = st.tabs(["➕ Aggiungi", "📝 Modifica", "🗑️ Elimina"])
    with t1:
        with st.form("add_p"):
            n = st.text_input("Nome e Cognome")
            if st.form_submit_button("REGISTRA"):
                if n: db_run("INSERT INTO pazienti (nome) VALUES (?)", (n,), True); st.rerun()
    with t2:
        p_list = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
        if p_list:
            sel = st.selectbox("Seleziona", [p[1] for p in p_list])
            id_m = [p[0] for p in p_list if p[1] == sel][0]
            nuovo = st.text_input("Nuovo Nome", value=sel)
            if st.button("AGGIORNA"):
                db_run("UPDATE pazienti SET nome=? WHERE id=?", (nuovo, id_m), True); st.rerun()
    with t3:
        p_list_d = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
        if p_list_d:
            sel_d = st.selectbox("Seleziona", [p[1] for p in p_list_d])
            id_d = [p[0] for p in p_list_d if p[1] == sel_d][0]
            if st.button("ELIMINA"):
                db_run("DELETE FROM pazienti WHERE id=?", (id_d,), True); st.rerun()

elif menu == "Equipe":
    ruolo = st.sidebar.selectbox("Ruolo", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
    pazienti = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if pazienti:
        p_nome = st.selectbox("Seleziona Paziente", [p[1] for p in pazienti])
        p_id = [p[0] for p in pazienti if p[1] == p_nome][0]
        st.divider()

        if ruolo == "Psichiatra":
            st.subheader("📋 Area Medica")
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
            
            ta = db_run("SELECT data_prescr, farmaco, dosaggio, turni, medico, row_id FROM terapie WHERE p_id=? ORDER BY row_id DESC", (p_id,))
            for da, fa, ds, tu, me, rid in ta:
                st.markdown(f"<div class='card-box'><b>{fa}</b> ({ds}) - {tu} <br> <small>Prescritto il {da} da {me}</small></div>", unsafe_allow_html=True)
                if st.button("🛑 Sospendi", key=f"s_{rid}"):
                    if not med_f: st.error("Firma!"); st.stop()
                    db_run("DELETE FROM terapie WHERE row_id=?", (rid,), True)
                    db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), "Stabile", f"❌ SOSPESO: {fa}", "Psichiatra", med_f), True); st.rerun()

        elif ruolo == "Infermiere":
            st.subheader("💉 Area Infermieristica")
            inf_f = st.text_input("Firma Infermiere (OBBLIGATORIA)")
            tab1, tab2, tab3 = st.tabs(["💊 Somministrazione", "📊 Parametri", "📝 Consegne"])
            with tab1:
                t_s = st.selectbox("Turno", ["Mattina", "Pomeriggio", "Notte"])
                ter = db_run("SELECT farmaco, dosaggio, turni, row_id FROM terapie WHERE p_id=?", (p_id,))
                for f, d, tu_p, rid in ter:
                    if tu_p and t_s[0] in tu_p:
                        st.write(f"**{f}** ({d})")
                        es = st.radio("Esito", ["Assunta", "Rifiutata"], key=f"r_{rid}", horizontal=True)
                        if st.button("CONVALIDA", key=f"b_{rid}"):
                            if not inf_f: st.error("Firma!"); st.stop()
                            db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), "Stabile", f"[{t_s[0]}] {f} -> {es}", "Infermiere", inf_f), True); st.rerun()
            with tab2:
                with st.form("par"):
                    c1,c2,c3,c4 = st.columns(4)
                    sys = c1.number_input("Sistolica", 0, 300)
                    dia = c1.number_input("Diastolica", 0, 200)
                    fc = c2.number_input("FC", 0, 250)
                    sat = c3.number_input("SpO2", 0, 100)
                    tc = c4.number_input("TC", 30.0, 45.0, 36.5, 0.1)
                    if st.form_submit_button("SALVA PARAMETRI"):
                        if not inf_f: st.error("Firma!"); st.stop()
                        db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), "Stabile", f"📊 PARAMETRI: PA {sys}/{dia}, FC {fc}, SpO2 {sat}%, TC {tc}", "Infermiere", inf_f), True); st.rerun()
            with tab3:
                txt = st.text_area("Consegna")
                if st.button("SALVA CONSEGNA"):
                    if not inf_f: st.error("Firma!"); st.stop()
                    db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), "Stabile", f"📝 CONSEGNA: {txt}", "Infermiere", inf_f), True); st.rerun()

        elif ruolo == "Educatore":
            st.subheader("💰 Contabilità")
            ed_f = st.text_input("Firma Educatore (OBBLIGATORIA)")
            mov = db_run("SELECT data, desc, importo, tipo, op FROM soldi WHERE p_id=? ORDER BY row_id DESC", (p_id,))
            saldo = sum([m[2] if m[3] == "Entrata" else -m[2] for m in mov])
            st.markdown(f'<div class="saldo-box">Saldo: € {saldo:.2f}</div>', unsafe_allow_html=True)
            with st.form("cash"):
                tp = st.radio("Tipo", ["Entrata", "Uscita"], horizontal=True)
                im = st.number_input("€", 0.0)
                ds = st.text_input("Causale")
                if st.form_submit_button("REGISTRA"):
                    if not ed_f: st.error("Firma!"); st.stop()
                    db_run("INSERT INTO soldi (p_id, data, desc, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, date.today().strftime("%d/%m/%Y"), ds, im, tp, ed_f), True); st.rerun()

        elif ruolo == "OSS":
            st.subheader("🧹 Mansioni OSS")
            with st.form("oss"):
                o1 = st.checkbox("Pulizia Camera")
                o2 = st.checkbox("Pulizia Refettorio")
                o3 = st.checkbox("Pulizia Sala Fumo")
                o4 = st.checkbox("Pulizia Cortile")
                o5 = st.checkbox("Lavatrice")
                oss_f = st.text_input("Firma OSS (OBBLIGATORIA)")
                if st.form_submit_button("SALVA"):
                    if not oss_f: st.error("Firma!"); st.stop()
                    ms = [t for b,t in zip([o1,o2,o3,o4,o5], ["Camera","Refettorio","Sala Fumo","Cortile","Lavatrice"]) if b]
                    db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), "Stabile", f"🧹 Pulizie: {', '.join(ms)}", "OSS", oss_f), True); st.rerun()

# --- MONITORAGGIO (DIARIO CLINICO RIDISEGNATO) ---
elif menu == "Monitoraggio":
    st.header("📊 Monitoraggio Diario Clinico")
    p_mon = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    
    for pid, nome in p_mon:
        with st.expander(f"📖 SCHEDA CLINICA: {nome.upper()}", expanded=False):
            log = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY row_id DESC", (pid,))
            
            if log:
                # Costruzione tabella HTML personalizzata
                html_table = """
                <table class='diario-table'>
                    <thead>
                        <tr>
                            <th style="width: 15%;">DATA E ORA</th>
                            <th style="width: 12%;">RUOLO</th>
                            <th style="width: 15%;">OPERATORE</th>
                            <th style="width: 58%;">DETTAGLIO NOTA</th>
                        </tr>
                    </thead>
                    <tbody>
                """
                
                for d, r, o, n in log:
                    # Determina il badge in base al ruolo
                    cls = "bg-psichiatra" if r == "Psichiatra" else \
                          "bg-infermiere" if r == "Infermiere" else \
                          "bg-educatore" if r == "Educatore" else "bg-oss"
                    
                    html_table += f"""
                        <tr>
                            <td><b>{d}</b></td>
                            <td><span class="badge {cls}">{r.upper()}</span></td>
                            <td><i>{o}</i></td>
                            <td>{n}</td>
                        </tr>
                    """
                
                html_table += "</tbody></table>"
                st.markdown(html_table, unsafe_allow_html=True)
            else:
                st.info("Nessuna nota presente per questo paziente.")
