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
</style>
""", unsafe_allow_html=True)

# --- 2. FUNZIONI DATABASE ---
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
menu = st.sidebar.radio("NAVIGAZIONE", ["Monitoraggio", "Equipe", "Gestione"])

# --- 5. GESTIONE PAZIENTI (Aggiungi, Modifica, Elimina) ---
if menu == "Gestione":
    st.header("⚙️ Amministrazione Anagrafica")
    
    t1, t2, t3 = st.tabs(["➕ Aggiungi", "📝 Modifica", "🗑️ Elimina"])
    
    with t1:
        st.subheader("Registra Nuovo Paziente")
        with st.form("add_p"):
            nuovo_nome = st.text_input("Nome e Cognome")
            if st.form_submit_button("SALVA NUOVO INGRESSO"):
                if nuovo_nome:
                    db_run("INSERT INTO pazienti (nome) VALUES (?)", (nuovo_nome,), True)
                    st.success(f"{nuovo_nome} registrato correttamente!"); st.rerun()
                else: st.error("Inserisci un nome")

    with t2:
        st.subheader("Modifica Nome Paziente")
        paz_list = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
        if paz_list:
            p_da_mod = st.selectbox("Seleziona chi modificare", [p[1] for p in paz_list], key="sel_mod")
            id_mod = [p[0] for p in paz_list if p[1] == p_da_mod][0]
            nuovo_nome_input = st.text_input("Nuovo Nome", value=p_da_mod)
            if st.button("AGGIORNA ANAGRAFICA"):
                db_run("UPDATE pazienti SET nome=? WHERE id=?", (nuovo_nome_input, id_mod), True)
                st.success("Nome aggiornato!"); st.rerun()
        else: st.info("Nessun paziente in archivio")

    with t3:
        st.subheader("Eliminazione Definitiva")
        paz_list_del = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
        if paz_list_del:
            p_da_del = st.selectbox("Seleziona chi eliminare", [p[1] for p in paz_list_del], key="sel_del")
            id_del = [p[0] for p in paz_list_del if p[1] == p_da_del][0]
            st.warning(f"Attenzione: l'eliminazione di {p_da_del} cancellerà anche diari, terapie e contabilità.")
            conferma = st.checkbox("Confermo di voler eliminare tutti i dati")
            if st.button("ELIMINA DEFINITIVAMENTE"):
                if conferma:
                    db_run("DELETE FROM pazienti WHERE id=?", (id_del,), True)
                    db_run("DELETE FROM eventi WHERE id=?", (id_del,), True)
                    db_run("DELETE FROM terapie WHERE p_id=?", (id_del,), True)
                    db_run("DELETE FROM soldi WHERE p_id=?", (id_del,), True)
                    st.success("Dati rimossi."); st.rerun()
                else: st.error("Spunta la casella di conferma prima di procedere")

# --- 6. EQUIPE (Psichiatra, Infermiere, Educatore, OSS) ---
elif menu == "Equipe":
    figura = st.sidebar.selectbox("Ruolo", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
    paz_data = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    
    if paz_data:
        sel_p_nome = st.selectbox("Seleziona Paziente", [p[1] for p in paz_data])
        p_id = [p[0] for p in paz_data if p[1] == sel_p_nome][0]
        st.divider()

        if figura == "Psichiatra":
            st.subheader("📋 Prescrizione Terapia")
            with st.form("presc"):
                f, d = st.text_input("Farmaco"), st.text_input("Dosaggio")
                c1,c2,c3 = st.columns(3)
                tm, tp, tn = c1.checkbox("M"), c2.checkbox("P"), c3.checkbox("N")
                med = st.text_input("Firma Medico")
                if st.form_submit_button("SALVA"):
                    t_list = [s for s, b in zip(["M", "P", "N"], [tm, tp, tn]) if b]
                    db_run("INSERT INTO terapie (p_id, farmaco, dosaggio, turni, medico, data_prescr) VALUES (?,?,?,?,?,?)", 
                           (p_id, f, d, ",".join(t_list), med, date.today().strftime("%d/%m/%Y")), True); st.rerun()

        elif figura == "Infermiere":
            st.subheader("💉 Somministrazione")
            d_somm = st.date_input("Data", date.today())
            t_somm = st.selectbox("Turno", ["Mattina", "Pomeriggio", "Notte"])
            firma_inf = st.text_input("Firma Infermiere")
            terapie = db_run("SELECT farmaco, dosaggio, turni, row_id FROM terapie WHERE p_id=?", (p_id,))
            for f, d, tu_f, rid in terapie:
                if tu_f and t_somm[0] in tu_f:
                    tag = f"[REP_{t_somm[0]}] {f}"
                    data_str = d_somm.strftime("%d/%m/%Y")
                    check = db_run("SELECT op, nota FROM eventi WHERE id=? AND nota LIKE ? AND data LIKE ?", (p_id, f"%{tag}%", f"{data_str}%"))
                    st.markdown("<div class='card-box'>", unsafe_allow_html=True)
                    c_a, c_b, c_c = st.columns([2, 2, 1])
                    c_a.write(f"**{f}** ({d})")
                    if check: c_b.write(f"✅ {check[0][1].split('->')[-1]} ({check[0][0]})")
                    else:
                        scelta = c_b.radio("Esito", ["Assunta", "Rifiutata"], key=f"s_{rid}", horizontal=True)
                        if c_c.button("OK", key=f"b_{rid}"):
                            db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", 
                                   (p_id, f"{data_str} {datetime.now().strftime('%H:%M')}", "Stabile", f"{tag} -> {scelta}", "Infermiere", firma_inf), True); st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)

        elif figura == "Educatore":
            st.subheader("💰 Contabilità")
            movs = db_run("SELECT data, desc, importo, tipo, op FROM soldi WHERE p_id=? ORDER BY row_id DESC", (p_id,))
            saldo = sum([m[2] if m[3] == "Entrata" else -m[2] for m in movs])
            st.markdown(f'<div class="saldo-box">Saldo: € {saldo:.2f}</div>', unsafe_allow_html=True)
            with st.expander("Nuovo Movimento"):
                tp = st.radio("Tipo", ["Entrata", "Uscita"], horizontal=True)
                im = st.number_input("Euro €", min_value=0.0)
                ds = st.text_input("Causale")
                fi = st.text_input("Firma")
                if st.button("REGISTRA"):
                    db_run("INSERT INTO soldi (p_id, data, desc, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, date.today().strftime("%d/%m/%Y"), ds, im, tp, fi), True); st.rerun()
            if movs:
                h = "<table class='custom-table'><tr><th>DATA</th><th>CAUSALE</th><th>ENTRATA</th><th>USCITA</th><th>FIRMA</th></tr>"
                for d, ds, im, tp, op in movs:
                    h += f"<tr><td>{d}</td><td>{ds}</td><td>{'€'+str(im) if tp=='Entrata' else ''}</td><td style='color:red'>{'€'+str(im) if tp=='Uscita' else ''}</td><td>{op}</td></tr>"
                st.markdown(h + "</table>", unsafe_allow_html=True)

# --- 7. MONITORAGGIO ---
elif menu == "Monitoraggio":
    paz_list = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    for pid, nome in paz_list:
        with st.expander(f"👤 {nome.upper()}"):
            note = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY row_id DESC", (pid,))
            if note:
                h = "<table class='custom-table'><tr><th>DATA</th><th>RUOLO</th><th>OP</th><th>NOTA</th></tr>"
                for d, ru, op, nt in note: h += f"<tr><td>{d}</td><td>{ru}</td><td>{op}</td><td>{nt}</td></tr>"
                st.markdown(h + "</table>", unsafe_allow_html=True)
