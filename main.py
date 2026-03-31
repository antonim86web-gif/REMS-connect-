import sqlite3
import streamlit as st
from datetime import datetime, date

# --- 1. DESIGN E STILE (CSS) ---
st.set_page_config(page_title="REMS Connect PRO 2026", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    .stApp { background-color: #f1f5f9; }
    .header-box {
        background: white; padding: 1.5rem; border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 2rem; border-top: 5px solid #1e40af;
    }
    .main-title { color: #1e40af; font-weight: 800; text-align: center; margin: 0; }
    
    /* POST-IT E SCHEDE */
    .postit-container { display: flex; flex-wrap: wrap; gap: 1rem; margin-bottom: 1rem; }
    .postit {
        width: 280px; min-height: 150px; padding: 1.2rem; border-radius: 4px;
        box-shadow: 3px 3px 10px rgba(0,0,0,0.1); position: relative; transition: 0.3s;
    }
    .postit:hover { transform: translateY(-5px); }
    .postit-inf { background-color: #e0f2fe; border-left: 6px solid #0ea5e9; } /* Azzurro */
    .postit-oss { background-color: #fef9c3; border-left: 6px solid #eab308; } /* Giallo */
    .postit-edu { background-color: #f0fdf4; border-left: 6px solid #22c55e; } /* Verde per soldi */
    .postit-header { font-size: 0.75rem; font-weight: 800; color: #475569; border-bottom: 1px solid rgba(0,0,0,0.1); margin-bottom: 8px; }
    .postit-body { font-size: 0.9rem; color: #1e293b; line-height: 1.4; font-weight: 500; }
    .postit-footer { font-size: 0.7rem; margin-top: 12px; font-weight: bold; color: #64748b; text-align: right; }
    
    /* TABELLE */
    .stTable { background: white; border-radius: 8px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

# --- 2. MOTORE DATABASE ---
DB_NAME = "rems_pro_v7.db"
def db_query(q, p=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (p_id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT, umore TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dose TEXT, medico TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS soldi (p_id INTEGER, data TEXT, causale TEXT, importo REAL, tipo TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS appuntamenti (p_id INTEGER, data TEXT, ora TEXT, tipo TEXT, accompagnatore TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        if q: cur.execute(q, p)
        if commit: conn.commit()
        return cur.fetchall()

db_query("") # Inizializza tabelle

# --- 3. LOGIN ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.markdown("<div class='header-box'><h1 class='main-title'>REMS CONNECT PRO - LOGIN</h1></div>", unsafe_allow_html=True)
    with st.columns([1,1,1])[1]:
        pwd = st.text_input("Inserire Codice Identificativo", type="password")
        if st.button("ACCEDI"):
            if pwd == "rems2026": st.session_state.auth = True; st.rerun()
    st.stop()

# --- 4. NAVIGAZIONE ---
st.sidebar.title("🏥 AREA OPERATIVA")
scelta = st.sidebar.radio("Sezione:", ["📊 Monitoraggio Generale", "👥 Equipe Multidisciplinare", "📅 Agenda Appuntamenti", "⚙️ Gestione Pazienti"])

# --- 5. LOGICA DELLE SEZIONI ---
st.markdown(f"<div class='header-box'><h1 class='main-title'>{scelta}</h1></div>", unsafe_allow_html=True)

if scelta == "📊 Monitoraggio Generale":
    paz_list = db_query("SELECT id, nome FROM pazienti ORDER BY nome")
    for pid, nome in paz_list:
        with st.expander(f"👤 {nome.upper()}", expanded=False):
            # Visualizzazione Post-it
            eventi = db_query("SELECT data, ruolo, op, nota, umore FROM eventi WHERE p_id=? ORDER BY row_id DESC", (pid,))
            if eventi:
                st.write("**Ultime Consegne (Post-it):**")
                h_p = "<div class='postit-container'>"
                for d, r, o, n, u in eventi:
                    if "📝" in n:
                        cls = "postit-inf" if r == "Infermiere" else "postit-oss"
                        h_p += f"<div class='postit {cls}'><div class='postit-header'>{d} | {u}</div><div class='postit-body'>{n}</div><div class='postit-footer'>{r}: {o}</div></div>"
                st.markdown(h_p + "</div>", unsafe_allow_html=True)
                
                st.write("**Registro Storico:**")
                st.table([{"Data": x[0], "Ruolo": x[1], "Operatore": x[2], "Nota": x[3]} for x in eventi if "📝" not in x[3]])

elif scelta == "👥 Equipe Multidisciplinare":
    paz_list = db_query("SELECT id, nome FROM pazienti ORDER BY nome")
    if not paz_list: st.warning("Nessun paziente. Vai in Gestione."); st.stop()
    
    ruolo = st.selectbox("Ruolo Professionale:", ["Scegli...", "Psichiatra", "Infermiere", "OSS", "Educatore"])
    p_nome = st.selectbox("Seleziona Paziente:", [p[1] for p in paz_list])
    p_id = [p[0] for p in paz_list if p[1] == p_nome][0]
    st.divider()

    if ruolo == "Psichiatra":
        firma = st.text_input("Firma Medico")
        t1, t2 = st.tabs(["💊 Gestione Farmaci", "📋 Diario Clinico"])
        with t1:
            with st.form("farm"):
                fa, do = st.text_input("Nuovo Farmaco"), st.text_input("Dosaggio/Orari")
                if st.form_submit_button("Aggiungi Terapia"):
                    if firma and fa: 
                        db_query("INSERT INTO terapie (p_id, farmaco, dose, medico) VALUES (?,?,?,?)", (p_id, fa, do, firma), True); st.rerun()
            # Visualizzazione per Variazione
            terapie = db_query("SELECT farmaco, dose, medico, row_id FROM terapie WHERE p_id=?", (p_id,))
            if terapie:
                st.write("**Terapie in corso (Puoi variarle):**")
                for f, d, m, rid in terapie:
                    c1, c2, c3 = st.columns([3,3,1])
                    c1.write(f"💊 **{f}**")
                    c2.write(f"Dosaggio: {d}")
                    if c3.button("🗑️", key=f"del_{rid}"):
                        db_query("DELETE FROM terapie WHERE row_id=?", (rid,), True); st.rerun()

    elif ruolo == "Infermiere":
        firma = st.text_input("Firma Infermiere")
        t1, t2, t3 = st.tabs(["📊 Parametri Vitali", "💊 Somministrazione", "📝 Consegne"])
        with t1:
            with st.form("pv"):
                c1,c2,c3 = st.columns(3); pa, fc, tc = c1.text_input("PA"), c2.text_input("FC"), c3.text_input("TC")
                if st.form_submit_button("Salva Parametri"):
                    if firma: db_query("INSERT INTO eventi (p_id, data, nota, ruolo, op, umore) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"📊 PA:{pa} FC:{fc} TC:{tc}", "Infermiere", firma, "Stabile"), True); st.rerun()
        with t3:
            txt = st.text_area("Scrivi Post-it Consegna")
            if st.button("Pubblica Consegna"):
                if firma and txt: db_query("INSERT INTO eventi (p_id, data, nota, ruolo, op, umore) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"📝 {txt}", "Infermiere", firma, "Stabile"), True); st.rerun()

    elif ruolo == "OSS":
        firma = st.text_input("Firma Operatore OSS")
        t1, t2 = st.tabs(["🧹 Mansioni", "📝 Note OSS"])
        with t1:
            with st.form("oss_m"):
                st.write("**Mansioni Svolte:**")
                m1, m2, m3, m4, m5 = st.checkbox("Pulizia Stanza"), st.checkbox("Refettorio"), st.checkbox("Sale Fumo"), st.checkbox("Cortile"), st.checkbox("Lavatrice")
                if st.form_submit_button("Registra Mansioni"):
                    sel = [v for b,v in zip([m1,m2,m3,m4,m5], ["Stanza","Refettorio","Sale Fumo","Cortile","Lavatrice"]) if b]
                    db_query("INSERT INTO eventi (p_id, data, nota, ruolo, op, umore) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"🧹 Mansioni: {', '.join(sel)}", "OSS", firma, "Collaborante"), True); st.rerun()
        with t2:
            txt = st.text_area("Nota OSS (Post-it)")
            if st.button("Salva Nota"):
                if firma and txt: db_query("INSERT INTO eventi (p_id, data, nota, ruolo, op, umore) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"📝 {txt}", "OSS", firma, "Collaborante"), True); st.rerun()

    elif ruolo == "Educatore":
        firma = st.text_input("Firma Educatore")
        st.subheader("💰 Gestione Cassa Paziente")
        mov = db_query("SELECT data, causale, importo, tipo, op FROM soldi WHERE p_id=? ORDER BY row_id DESC", (p_id,))
        saldo = sum([m[2] if m[3] == "Entrata" else -m[2] for m in mov])
        st.metric("SALDO ATTUALE", f"€ {saldo:.2f}")
        
        with st.form("soldi_f"):
            c1,c2,c3 = st.columns([1,2,1])
            tp = c1.radio("Tipo", ["Entrata", "Uscita"])
            cs = c2.text_input("Causale")
            im = c3.number_input("€", min_value=0.0)
            if st.form_submit_button("Registra Movimento"):
                if firma: db_query("INSERT INTO soldi (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, date.today().strftime("%d/%m/%Y"), cs, im, tp, firma), True); st.rerun()
        
        if mov:
            st.write("**Lista Movimenti:**")
            h_e = "<div class='postit-container'>"
            for d, c, i, t, o in mov:
                color = "#dcfce7" if t == "Entrata" else "#fee2e2"
                h_e += f"<div class='postit' style='background:{color}; border-left:6px solid {'#22c55e' if t=='Entrata' else '#ef4444'}'><div class='postit-header'>{d} | {t}</div><div class='postit-body'><b>{c}</b><br>Importo: € {i:.2f}</div><div class='postit-footer'>Op: {o}</div></div>"
            st.markdown(h_e + "</div>", unsafe_allow_html=True)

elif scelta == "📅 Agenda Appuntamenti":
    paz_list = db_query("SELECT id, nome FROM pazienti ORDER BY nome")
    if paz_list:
        p_nome = st.selectbox("Paziente", [p[1] for p in paz_list])
        p_id = [p[0] for p in paz_list if p[1] == p_nome][0]
        with st.form("agenda"):
            d, h = st.date_input("Data"), st.time_input("Ora")
            ti = st.selectbox("Tipo", ["Visita Medica", "Visita con Parenti", "Udienza", "Permesso"])
            acc = st.text_input("Accompagnatore")
            if st.form_submit_button("Programma Uscita"):
                db_query("INSERT INTO appuntamenti (p_id, data, ora, tipo, accompagnatore) VALUES (?,?,?,?,?)", (p_id, d.strftime("%d/%m/%Y"), h.strftime("%H:%M"), ti, acc), True)
                st.success("Programmato."); st.rerun()
        
        app = db_query("SELECT data, ora, tipo, accompagnatore FROM appuntamenti WHERE p_id=?", (p_id,))
        if app: st.table([{"Data": x[0], "Ora": x[1], "Tipo": x[2], "Accompagnatore": x[3]} for x in app])

elif scelta == "⚙️ Gestione Pazienti":
    nuovo = st.text_input("Nome e Cognome nuovo ingresso")
    if st.button("REGISTRA"):
        if nuovo: db_query("INSERT INTO pazienti (nome) VALUES (?)", (nuovo.strip().upper(),), True); st.rerun()
    st.divider()
    for pid, nome in db_query("SELECT id, nome FROM pazienti"):
        c1, c2 = st.columns([5,1])
        c1.write(f"👤 {nome}")
        if c2.button("Elimina", key=f"delp_{pid}"): db_query("DELETE FROM pazienti WHERE id=?", (pid,), True); st.rerun()
