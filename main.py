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

# --- 5. GESTIONE PAZIENTI ---
if menu == "Gestione":
    st.header("⚙️ Amministrazione")
    t1, t2, t3 = st.tabs(["➕ Aggiungi", "📝 Modifica", "🗑️ Elimina"])
    with t1:
        with st.form("add_p"):
            nuovo_nome = st.text_input("Nome e Cognome")
            if st.form_submit_button("SALVA"):
                if nuovo_nome:
                    db_run("INSERT INTO pazienti (nome) VALUES (?)", (nuovo_nome,), True)
                    st.rerun()
    with t2:
        paz_list = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
        if paz_list:
            p_da_mod = st.selectbox("Seleziona chi modificare", [p[1] for p in paz_list])
            id_mod = [p[0] for p in paz_list if p[1] == p_da_mod][0]
            nuovo_nome_input = st.text_input("Nuovo Nome", value=p_da_mod)
            if st.button("AGGIORNA"):
                db_run("UPDATE pazienti SET nome=? WHERE id=?", (nuovo_nome_input, id_mod), True); st.rerun()
    with t3:
        paz_list_del = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
        if paz_list_del:
            p_da_del = st.selectbox("Seleziona chi eliminare", [p[1] for p in paz_list_del])
            id_del = [p[0] for p in paz_list_del if p[1] == p_da_del][0]
            if st.button("ELIMINA DEFINITIVAMENTE"):
                db_run("DELETE FROM pazienti WHERE id=?", (id_del,), True); st.rerun()

# --- 6. EQUIPE ---
elif menu == "Equipe":
    figura = st.sidebar.selectbox("Ruolo", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
    paz_data = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    
    if paz_data:
        sel_p_nome = st.selectbox("Seleziona Paziente", [p[1] for p in paz_data])
        p_id = [p[0] for p in paz_data if p[1] == sel_p_nome][0]
        st.divider()

        # --- SEZIONE PSICHIATRA ---
        if figura == "Psichiatra":
            st.subheader("📋 Gestione Terapia")
            med_firma = st.text_input("Firma Medico (Obbligatoria per ogni operazione)")

            with st.expander("➕ Prescrivi Nuovo Farmaco"):
                with st.form("presc_new"):
                    f = st.text_input("Farmaco")
                    d = st.text_input("Dosaggio")
                    c1,c2,c3 = st.columns(3)
                    tm, tp, tn = c1.checkbox("M"), c2.checkbox("P"), c3.checkbox("N")
                    if st.form_submit_button("CONFERMA PRESCRIZIONE"):
                        if not med_firma: st.error("❌ Firma necessaria!"); st.stop()
                        t_list = [s for s, b in zip(["M", "P", "N"], [tm, tp, tn]) if b]
                        db_run("INSERT INTO terapie (p_id, farmaco, dosaggio, turni, medico, data_prescr) VALUES (?,?,?,?,?,?)", 
                               (p_id, f, d, ",".join(t_list), med_firma, date.today().strftime("%d/%m/%Y")), True); st.rerun()

            st.write("#### 💊 Riepilogo Terapie Attive")
            terapie = db_run("SELECT data_prescr, farmaco, dosaggio, turni, medico, row_id FROM terapie WHERE p_id=? ORDER BY row_id DESC", (p_id,))
            if terapie:
                h = "<table class='custom-table'><tr><th>DATA</th><th>FARMACO</th><th>DOSAGGIO</th><th>TURNI</th><th>MEDICO</th><th>AZIONE</th></tr>"
                st.markdown(h, unsafe_allow_html=True)
                for da, fa, do, tu, me, rid in terapie:
                    c1, c2, c3, c4, c5, c6 = st.columns([1.5, 2, 1.5, 1, 1.5, 1])
                    c1.write(da); c2.markdown(f"**{fa}**"); c3.write(do); c4.write(tu); c5.write(me)
                    if c6.button("🗑️ Sospendi", key=f"del_{rid}"):
                        if not med_firma: st.error("Firma per sospendere!"); st.stop()
                        db_run("DELETE FROM terapie WHERE row_id=?", (rid,), True)
                        db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", 
                               (p_id, datetime.now().strftime("%d/%m/%y %H:%M"), "Stabile", f"❌ SOSPESO: {fa}", "Psichiatra", med_firma), True); st.rerun()
                st.markdown("</table>", unsafe_allow_html=True)

        # --- SEZIONE INFERMIERE ---
        elif figura == "Infermiere":
            st.subheader("💉 Somministrazione")
            inf_firma = st.text_input("Firma Infermiere (Obbligatoria)")
            t_somm = st.selectbox("Turno", ["Mattina", "Pomeriggio", "Notte"])
            terapie = db_run("SELECT farmaco, dosaggio, turni, row_id FROM terapie WHERE p_id=?", (p_id,))
            for f, d, tu_f, rid in terapie:
                if tu_f and t_somm[0] in tu_f:
                    st.markdown("<div class='card-box'>", unsafe_allow_html=True)
                    c_a, c_b, c_c = st.columns([2, 2, 1])
                    c_a.write(f"**{f}** ({d})")
                    scelta = c_b.radio("Esito", ["Assunta", "Rifiutata"], key=f"s_{rid}", horizontal=True)
                    if c_c.button("CONVALIDA", key=f"b_{rid}"):
                        if not inf_firma: st.error("❌ Firma mancante!"); st.stop()
                        db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", 
                               (p_id, datetime.now().strftime("%d/%m/%y %H:%M"), "Stabile", f"[{t_somm[0]}] {f} -> {scelta}", "Infermiere", inf_firma), True); st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)

        # --- SEZIONE EDUCATORE ---
        elif figura == "Educatore":
            st.subheader("💰 Contabilità")
            ed_firma = st.text_input("Firma Educatore (Obbligatoria)")
            movs = db_run("SELECT data, desc, importo, tipo, op FROM soldi WHERE p_id=? ORDER BY row_id DESC", (p_id,))
            saldo = sum([m[2] if m[3] == "Entrata" else -m[2] for m in movs])
            st.markdown(f'<div class="saldo-box">Saldo: € {saldo:.2f}</div>', unsafe_allow_html=True)
            with st.expander("Registra Movimento"):
                tp = st.radio("Tipo", ["Entrata", "Uscita"], horizontal=True)
                im = st.number_input("Euro €", min_value=0.0)
                ds = st.text_input("Causale")
                if st.button("SALVA"):
                    if not ed_firma: st.error("Firma obbligatoria!"); st.stop()
                    db_run("INSERT INTO soldi (p_id, data, desc, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, date.today().strftime("%d/%m/%Y"), ds, im, tp, ed_firma), True); st.rerun()
            if movs:
                h = "<table class='custom-table'><tr><th>DATA</th><th>CAUSALE</th><th>ENTRATA</th><th>USCITA</th><th>FIRMA</th></tr>"
                for d, ds, im, tp, op in movs:
                    h += f"<tr><td>{d}</td><td>{ds}</td><td>{'€'+str(im) if tp=='Entrata' else ''}</td><td style='color:red'>{'€'+str(im) if tp=='Uscita' else ''}</td><td>{op}</td></tr>"
                st.markdown(h + "</table>", unsafe_allow_html=True)

        # --- SEZIONE OSS ---
        elif figura == "OSS":
            st.subheader("🧹 Mansioni Personale OSS")
            with st.form("oss_tasks"):
                c1, c2 = st.columns(2)
                m1 = c1.checkbox("Pulizia Camera")
                m2 = c1.checkbox("Pulizia Refettorio")
                m3 = c1.checkbox("Pulizia Sala Fumo")
                m4 = c2.checkbox("Pulizia Cortile")
                m5 = c2.checkbox("Lavatrice")
                f_oss = st.text_input("Firma OSS (Obbligatoria)")
                if st.form_submit_button("REGISTRA"):
                    if not f_oss: st.error("Firma obbligatoria!"); st.stop()
                    mans = [t for b, t in zip([m1,m2,m3,m4,m5], ["Camera", "Refettorio", "Sala Fumo", "Cortile", "Lavatrice"]) if b]
                    db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%y %H:%M"), "Stabile", f"🧹 Mansioni: {', '.join(mans)}", "OSS", f_oss), True); st.rerun()

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
