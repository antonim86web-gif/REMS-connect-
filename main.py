import sqlite3
import pandas as pd
import streamlit as st
from datetime import datetime, date

# --- 1. CONFIGURAZIONE E DESIGN ---
st.set_page_config(page_title="REMS Connect PRO", layout="wide", page_icon="🏥", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    .stApp { background-color: #ffffff; }
    .main-title {
        text-align: center; 
        background: linear-gradient(90deg, #1e40af, #3b82f6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800; font-size: 2.5rem; margin-bottom: 25px;
    }
    [data-testid="stSidebar"] { background-color: #1e40af !important; border-right: 1px solid #1e3a8a; }
    [data-testid="stSidebar"] * { color: #ffffff !important; font-weight: 600 !important; }
    .custom-table { 
        width: 100%; border-collapse: collapse; background-color: #ffffff;
        border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); 
        margin-bottom: 20px; border: 1px solid #e2e8f0;
    }
    .custom-table th { background-color: #1e293b; color: #ffffff !important; padding: 10px; font-size: 0.75rem; text-transform: uppercase; text-align: left; }
    .custom-table td { padding: 10px; border-bottom: 1px solid #f1f5f9; font-size: 0.85rem; color: #1e293b !important; }
    .badge { padding: 4px 10px; border-radius: 4px; font-size: 0.7rem; font-weight: 700; color: white !important; display: inline-block; }
    .bg-psichiatra { background: #dc2626; } .bg-infermiere { background: #2563eb; }
    .bg-educatore  { background: #059669; } .bg-oss        { background: #d97706; }
    .bg-sistema    { background: #475569; }
</style>
""", unsafe_allow_html=True)

# --- 2. DATABASE ---
DB_NAME = "rems_pro_2026.db"
def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, umore TEXT, nota TEXT, ruolo TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dosaggio TEXT, turni TEXT, medico TEXT, data_prescr TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS soldi (p_id INTEGER, data TEXT, desc TEXT, importo REAL, tipo TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS appuntamenti (p_id INTEGER, data TEXT, ora TEXT, tipo TEXT, accompagnatore TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        if query: cur.execute(query, params)
        if commit: conn.commit()
        return cur.fetchall()

# --- 3. LOGIN ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.markdown("<h1 class='main-title'>SISTEMA REMS CONNECT</h1>", unsafe_allow_html=True)
    with st.columns([1,1,1])[1]:
        with st.form("login"):
            pwd = st.text_input("Codice Identificativo", type="password")
            if st.form_submit_button("ACCEDI"):
                if pwd == "rems2026": st.session_state.auth = True; st.rerun()
    st.stop()

# --- 4. NAVIGAZIONE ---
menu = st.sidebar.radio("NAVIGAZIONE", ["📊 Monitoraggio", "👥 Equipe", "📅 Appuntamenti", "⚙️ Gestione"])

# --- 5. LOGICA ---

if menu == "📊 Monitoraggio":
    st.markdown("<h2 class='main-title'>Diario Clinico Unificato</h2>", unsafe_allow_html=True)
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    for pid, nome in p_lista:
        with st.expander(f"👤 {nome.upper()}", expanded=False):
            log = db_run("SELECT data, ruolo, op, nota, umore FROM eventi WHERE id=? ORDER BY row_id DESC", (pid,))
            if log:
                h = "<table class='custom-table'><tr><th>Data</th><th>Ruolo</th><th>Operatore</th><th>Umore</th><th>Evento</th></tr>"
                for d, r, o, n, u in log:
                    cls = f"bg-{r.lower()}" if r.lower() in ["infermiere", "oss", "psichiatra", "educatore"] else "bg-sistema"
                    h += f"<tr><td>{d}</td><td><span class='badge {cls}'>{r}</span></td><td>{o}</td><td>{u}</td><td>{n}</td></tr>"
                st.markdown(h + "</table>", unsafe_allow_html=True)

elif menu == "👥 Equipe":
    ruolo = st.sidebar.selectbox("PROFILO OPERATIVO", ["Scegli...", "Psichiatra", "Infermiere", "Educatore", "OSS"])
    if ruolo != "Scegli...":
        p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
        if p_lista:
            p_nome = st.selectbox("Seleziona Paziente", [p[1] for p in p_lista])
            p_id = [p[0] for p in p_lista if p[1] == p_nome][0]
            umore_list = ["Stabile", "Agitato", "Collaborante", "Provocatorio", "Depresso"]

            if ruolo == "Psichiatra":
                f_m = st.text_input("Firma Medico")
                with st.form("prescr"):
                    c1,c2 = st.columns(2); fa, do = c1.text_input("Farmaco"), c2.text_input("Dose")
                    m,p,n = st.columns(3); m1, p1, n1 = m.checkbox("M"), p.checkbox("P"), n.checkbox("N")
                    if st.form_submit_button("CONFERMA PRESCRIZIONE"):
                        tu = ",".join([s for s, b in zip(["M","P","N"], [m1,p1,n1]) if b])
                        db_run("INSERT INTO terapie (p_id, farmaco, dosaggio, turni, medico, data_prescr) VALUES (?,?,?,?,?,?)", (p_id, fa, do, tu, f_m, date.today().strftime("%d/%m/%Y")), True); st.rerun()
                
                st.write("**Piano Terapeutico Attivo:**")
                piano = db_run("SELECT farmaco, dosaggio, turni, medico, row_id FROM terapie WHERE p_id=?", (p_id,))
                if piano:
                    df = pd.DataFrame(piano, columns=['Farmaco', 'Dose', 'Turni', 'Medico', 'ID'])
                    df['Cancella'] = False
                    edited_df = st.data_editor(
                        df, 
                        column_config={"Cancella": st.column_config.CheckboxColumn("🗑️")},
                        disabled=['Farmaco', 'Dose', 'Turni', 'Medico', 'ID'],
                        hide_index=True, use_container_width=True
                    )
                    for i in range(len(edited_df)):
                        if edited_df.iloc[i]['Cancella']:
                            db_run("DELETE FROM terapie WHERE row_id=?", (int(edited_df.iloc[i]['ID']),), True); st.rerun()

            elif ruolo == "Infermiere":
                f_i = st.text_input("Firma Infermiere")
                t1, t2, t3 = st.tabs(["💊 Farmaci", "📊 Parametri", "📝 Consegne"])
                with t1:
                    turno = st.selectbox("Turno", ["Mattina", "Pomeriggio", "Notte"])
                    ter = db_run("SELECT farmaco, dosaggio, turni, row_id FROM terapie WHERE p_id=?", (p_id,))
                    acc, rif = [], []
                    for fa, do, tu, rid in ter:
                        if turno[0] in tu:
                            c1,c2,c3 = st.columns([3,1,1]); c1.write(f"**{fa}** ({do})")
                            if c2.checkbox("✔️", key=f"a_{rid}"): acc.append(fa)
                            if c3.checkbox("❌", key=f"r_{rid}"): rif.append(fa)
                    if st.button("REGISTRA SOMMINISTRAZIONE"):
                        nota = f"💊 [{turno}] Assunti: {', '.join(acc)} | Rifiutati: {', '.join(rif)}"
                        db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), "Stabile", nota, "Infermiere", f_i), True); st.rerun()
                    st.write("**Report Farmaci:**")
                    st_f = db_run("SELECT data, nota FROM eventi WHERE id=? AND nota LIKE '💊%' ORDER BY row_id DESC", (p_id,))
                    if st_f:
                        h = "<table class='custom-table'><tr><th>Data</th><th>Dettagli</th></tr>"
                        for d, n in st_f: h += f"<tr><td>{d}</td><td>{n}</td></tr>"
                        st.markdown(h + "</table>", unsafe_allow_html=True)

                with t3:
                    u_i = st.selectbox("Umore", umore_list)
                    txt_i = st.text_area("Consegna Infermieristica")
                    if st.button("SALVA CONSEGNA"):
                        db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), u_i, f"📝 {txt_i}", "Infermiere", f_i), True); st.rerun()
                    st.write("**Report Consegne:**")
                    st_c = db_run("SELECT data, umore, nota, op FROM eventi WHERE id=? AND ruolo='Infermiere' AND nota LIKE '📝%' ORDER BY row_id DESC", (p_id,))
                    if st_c:
                        h = "<table class='custom-table'><tr><th>Data</th><th>Umore</th><th>Nota</th><th>Firma</th></tr>"
                        for d, u, n, o in st_c: h += f"<tr><td>{d}</td><td>{u}</td><td>{n}</td><td>{o}</td></tr>"
                        st.markdown(h + "</table>", unsafe_allow_html=True)

            elif ruolo == "OSS":
                f_o = st.text_input("Firma OSS")
                t_m, t_n = st.tabs(["🧹 Mansioni", "📝 Note OSS"])
                with t_m:
                    with st.form("oss_m"):
                        m1, m2, m3, m4 = st.checkbox("Camera"), st.checkbox("Refettorio"), st.checkbox("Sale Fumo"), st.checkbox("Lavatrice")
                        if st.form_submit_button("REGISTRA MANSIONI"):
                            sel = [t for b,t in zip([m1,m2,m3,m4], ["Camera","Refettorio","Sale Fumo","Lavatrice"]) if b]
                            db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), "Collaborante", f"🧹 Svolto: {', '.join(sel)}", "OSS", f_o), True); st.rerun()
                    st.write("**Report Mansioni:**")
                    st_m_rep = db_run("SELECT data, nota FROM eventi WHERE id=? AND nota LIKE '🧹%' ORDER BY row_id DESC", (p_id,))
                    if st_m_rep:
                        h = "<table class='custom-table'><tr><th>Data</th><th>Attività</th></tr>"
                        for d, n in st_m_rep: h += f"<tr><td>{d}</td><td>{n}</td></tr>"
                        st.markdown(h + "</table>", unsafe_allow_html=True)

                with t_n:
                    txt_o = st.text_area("Nota OSS")
                    if st.button("SALVA NOTA"):
                        db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), "Collaborante", f"📝 {txt_o}", "OSS", f_o), True); st.rerun()
                    st.write("**Report Note OSS:**")
                    st_no = db_run("SELECT data, nota, op FROM eventi WHERE id=? AND ruolo='OSS' AND nota LIKE '📝%' ORDER BY row_id DESC", (p_id,))
                    if st_no:
                        h = "<table class='custom-table'><tr><th>Data</th><th>Nota</th><th>Firma</th></tr>"
                        for d, n, o in st_no: h += f"<tr><td>{d}</td><td>{n}</td><td>{o}</td></tr>"
                        st.markdown(h + "</table>", unsafe_allow_html=True)

elif menu == "📅 Appuntamenti":
    st.markdown("<h2 class='main-title'>Agenda REMS</h2>", unsafe_allow_html=True)
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_lista:
        p_nome = st.selectbox("Seleziona Paziente", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_nome][0]
        
        with st.form("app_form"):
            c1, c2 = st.columns(2)
            d = c1.date_input("Data", value=date.today())
            h = c2.time_input("Ora")
            ti = st.selectbox("Tipo", ["Udienza", "Visita specialistica", "Permesso", "Altro"])
            acc = st.text_input("Accompagnatore / Luogo")
            if st.form_submit_button("REGISTRA IN AGENDA"):
                # Inserimento corretto nel DB appuntamenti
                db_run("INSERT INTO appuntamenti (p_id, data, ora, tipo, accompagnatore) VALUES (?,?,?,?,?)", 
                       (p_id, d.strftime("%d/%m/%Y"), h.strftime("%H:%M"), ti, acc), True)
                # Inserimento automatico nel diario clinico
                db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", 
                       (p_id, datetime.now().strftime("%d/%m %H:%M"), "Stabile", f"📅 APPUNTAMENTO: {ti} - {acc}", "Sistema", "Agenda"), True)
                st.success("Appuntamento registrato!"); st.rerun()

        st.divider()
        st.write(f"**Agenda di {p_nome}:**")
        # Filtro per p_id assicurato
        apps = db_run("SELECT data, ora, tipo, accompagnatore, row_id FROM appuntamenti WHERE p_id=? ORDER BY row_id DESC", (p_id,))
        if apps:
            h_tab = "<table class='custom-table'><tr><th>Data</th><th>Ora</th><th>Tipo</th><th>Dettagli</th><th>Azioni</th></tr>"
            st.markdown(h_tab, unsafe_allow_html=True)
            for da, ora, tip, sco, rid in apps:
                c1, c2 = st.columns([9, 1])
                with c1:
                    st.markdown(f"""<table class='custom-table' style='margin-bottom:0px;'><tr>
                        <td style='width:20%'>{da}</td><td style='width:20%'>{ora}</td><td style='width:20%'>{tip}</td><td style='width:40%'>{sco}</td>
                        </tr></table>""", unsafe_allow_html=True)
                with c2:
                    if st.button("🗑️", key=f"del_app_{rid}"):
                        db_run("DELETE FROM appuntamenti WHERE row_id=?", (rid,), True); st.rerun()

elif menu == "⚙️ Gestione":
    st.header("Anagrafica Pazienti")
    nuovo = st.text_input("Nome e Cognome Paziente")
    if st.button("AGGIUNGI NUOVO"):
        if nuovo: db_run("INSERT INTO pazienti (nome) VALUES (?)", (nuovo.strip().upper(),), True); st.rerun()
    st.divider()
    for pid, nome in db_run("SELECT id, nome FROM pazienti"):
        c1, c2 = st.columns([5,1])
        c1.write(nome)
        if c2.button("Elimina Paziente", key=f"del_p_{pid}"):
            db_run("DELETE FROM pazienti WHERE id=?", (pid,), True); st.rerun()
