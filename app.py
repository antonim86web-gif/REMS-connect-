import streamlit as st
import pandas as pd
import hashlib
import calendar
import io
from datetime import datetime, timedelta, timezone
from groq import Groq
from supabase import create_client
from fpdf import FPDF

# --- CONNESSIONE SUPABASE ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- UTILITY: ORARIO ITALIA ---
def get_now_it():
    return datetime.now(timezone.utc) + timedelta(hours=2)

# --- MOTORE DATABASE UNIFICATO (SELECT, INSERT, DELETE) ---
def db_run(query, params=None, commit=False):
    try:
        q = query.upper()
        # 1. UTENTI
        if "FROM UTENTI" in q:
            res = supabase.table("utenti").select("*").execute()
            return res.data
        # 2. PAZIENTI
        if "FROM PAZIENTI" in q:
            res = supabase.table("pazienti").select("*").eq("stato", "ATTIVO").execute()
            return res.data
        # 3. EVENTI / DIARIO
        if "FROM EVENTI" in q or "FROM DIARIO" in q:
            if "INSERT INTO" in q:
                d_ins = {"id": params[0], "data": params[1], "nota": params[2], "ruolo": params[3], "op": params[4]}
                if len(params) > 5: d_ins["esito"] = params[5]
                supabase.table("eventi").insert(d_ins).execute()
                return True
            res = supabase.table("eventi").select("*").eq("id", params[0]).order("id_u", ascending=False).execute()
            return res.data
        # 4. TERAPIE
        if "FROM TERAPIE" in q:
            if "INSERT INTO" in q:
                supabase.table("terapie").insert({"p_id": params[0], "farmaco": params[1], "dose": params[2], "mat_nuovo": params[3], "pom_nuovo": params[4], "al_bisogno": params[5]}).execute()
                return True
            if "DELETE" in q:
                supabase.table("terapie").delete().eq("id_u", params[0]).execute()
                return True
            res = supabase.table("terapie").select("*").eq("p_id", params[0]).execute()
            return res.data
        # 5. STANZE / ASSEGNAZIONI
        if "FROM STANZE" in q:
            res = supabase.table("stanze").select("*").order("id").execute()
            return res.data
        if "FROM ASSEGNAZIONI" in q:
            if "DELETE" in q:
                supabase.table("assegnazioni").delete().eq("p_id", params[0]).execute()
                return True
            if "INSERT" in q:
                supabase.table("assegnazioni").insert({"p_id": params[0], "stanza_id": params[1], "letto": params[2], "data_ass": params[3]}).execute()
                return True
            res = supabase.table("assegnazioni").select("p_id, stanza_id, letto").execute()
            return res.data
        return []
    except Exception as e:
        st.error(f"Errore DB: {e}")
        return []

# --- GENERATORE PDF ---
def genera_pdf_clinico(p_nome, dati):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "REMS-CONNECT - REPORT CLINICO", ln=True, align='C')
    pdf.ln(10)
    for ev in dati:
        pdf.set_font("Arial", 'B', 10)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(0, 7, f"Data: {ev['data']} | Op: {ev['op']}", ln=True, fill=True)
        pdf.set_font("Arial", size=10)
        pdf.multi_cell(0, 7, str(ev['nota']).encode('latin-1', 'replace').decode('latin-1'))
        pdf.ln(2)
    return bytes(pdf.output())

# --- IA ---
def genera_relazione_ia(testo):
    try:
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
        chat = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": "Sei uno psichiatra esperto REMS."}, {"role": "user", "content": testo}]
        )
        return chat.choices[0].message.content
    except: return "Servizio IA non disponibile al momento."

# --- STILE CSS ELITE PRO ---
st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #1e3a8a !important; }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    .section-banner { background-color: #1e3a8a; color: white !important; padding: 25px; border-radius: 12px; margin-bottom: 30px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.3); }
    .ai-box { background: #f8fafc; border: 2px solid #a855f7; border-radius: 15px; padding: 25px; margin-top: 10px; }
    .map-reparto { background: #f1f5f9; padding: 15px; border-radius: 12px; margin-bottom: 20px; }
    .stanza-tile { background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px; border-left: 6px solid #94a3b8; margin-bottom: 5px; }
    .stanza-piena { border-left-color: #2563eb; background-color: #eff6ff; }
    .postit { padding: 15px; border-radius: 8px; margin-bottom: 12px; border-left: 10px solid #2563eb; background: #ffffff; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); }
</style>
""", unsafe_allow_html=True)

# --- LOGIN ---
if 'user_session' not in st.session_state: st.session_state.user_session = None
if not st.session_state.user_session:
    st.markdown("<div class='section-banner'><h2>🏥 REMS CONNECT ELITE ACCESSO</h2></div>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        with st.form("L"):
            u_i = st.text_input("User").lower().strip()
            p_i = st.text_input("Pass", type="password")
            if st.form_submit_button("ACCEDI"):
                res = supabase.table("utenti").select("*").eq("user", u_i).execute()
                if res.data and res.data[0]['pwd'] == p_i:
                    st.session_state.user_session = res.data[0]
                    st.rerun()
    with col2:
        with st.form("R"):
            ru, rp, rn, rc = st.text_input("New User"), st.text_input("New Pass"), st.text_input("Nome"), st.text_input("Cognome")
            rq = st.selectbox("Ruolo", ["Psichiatra", "Infermiere", "OSS", "Educatore", "Psicologo", "Assistente Sociale", "Opsi", "Coordinatore"])
            if st.form_submit_button("REGISTRA"):
                supabase.table("utenti").insert({"user": ru.lower(), "pwd": rp, "nome": rn, "cognome": rc, "qualifica": rq}).execute()
                st.success("Ok!")
    st.stop()

u = st.session_state.user_session
ruolo_corr = u.get('qualifica', 'Operatore')
firma_op = f"{u['nome']} {u['cognome']}"

# --- SIDEBAR ---
with st.sidebar:
    st.markdown(f"### 👤 {firma_op.upper()}")
    nav = st.radio("NAVIGAZIONE", ["📊 Monitoraggio", "👥 Modulo Equipe", "📅 Agenda", "🗺️ Mappa Posti"])
    if st.button("LOGOUT"):
        st.session_state.user_session = None
        st.rerun()

# --- LOGICA NAVIGAZIONE ---

if nav == "🗺️ Mappa Posti":
    st.markdown("<div class='section-banner'><h2>TABELLONE POSTI LETTO</h2></div>", unsafe_allow_html=True)
    stanze = db_run("SELECT * FROM stanze")
    assegnazioni = db_run("SELECT * FROM assegnazioni")
    paz_attivi = db_run("SELECT * FROM pazienti")
    
    mappa = {s['id']: {'rep': s['reparto'], 'tipo': s['tipo'], 'letti': {1: None, 2: None}} for s in stanze}
    for ass in assegnazioni:
        if ass['stanza_id'] in mappa:
            p_n = next((p['nome'] for p in paz_attivi if p['id'] == ass['p_id']), "Sconosciuto")
            mappa[ass['stanza_id']]['letti'][ass['letto']] = p_n

    ca, cb = st.columns(2)
    for r, col in [("A", ca), ("B", cb)]:
        with col:
            st.markdown(f"### Reparto {r}")
            for sid, info in mappa.items():
                if info['rep'] == r:
                    occ = len([v for v in info['letti'].values() if v])
                    cls = "stanza-piena" if occ == 2 else ""
                    st.markdown(f"<div class='stanza-tile {cls}'><b>Stanza {sid}</b><br>L1: {info['letti'][1] or 'Libero'}<br>L2: {info['letti'][2] or 'Libero'}</div>", unsafe_allow_html=True)

elif nav == "📊 Monitoraggio":
    st.markdown("<div class='section-banner'><h2>DIARIO CLINICO GENERALE</h2></div>", unsafe_allow_html=True)
    p_lista = db_run("SELECT * FROM pazienti")
    for p in p_lista:
        with st.expander(f"📁 SCHEDA: {p['nome']}"):
            evs = db_run("SELECT * FROM eventi", (p['id'],))
            if evs:
                st.download_button("📄 Export PDF", genera_pdf_clinico(p['nome'], evs), f"{p['nome']}.pdf", key=f"pdf_{p['id']}")
                for e in evs:
                    st.markdown(f"<div class='postit'><b>{e['data']}</b> - {e['ruolo']}<br>{e['nota']}</div>", unsafe_allow_html=True)

elif nav == "👥 Modulo Equipe":
    st.markdown("<div class='section-banner'><h2>MODULO OPERATIVO</h2></div>", unsafe_allow_html=True)
    p_lista = db_run("SELECT * FROM pazienti")
    p_sel = st.selectbox("Paziente", [p['nome'] for p in p_lista])
    p_id = [p['id'] for p in p_lista if p['nome'] == p_sel][0]

    if ruolo_corr == "Psichiatra":
        t1, t2, t3 = st.tabs(["📋 Diario", "💊 Terapie", "🤖 IA"])
        with t1:
            n = st.text_area("Nota Clinica")
            if st.button("Salva"):
                db_run("INSERT INTO eventi", (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"🩺 {n}", ruolo_corr, firma_op))
                st.rerun()
        with t2:
            st.subheader("Prescrizione")
            with st.form("f"):
                farm, dose = st.text_input("Farmaco"), st.text_input("Dose")
                m, p, b = st.checkbox("M"), st.checkbox("P"), st.checkbox("B")
                if st.form_submit_button("Aggiungi"):
                    db_run("INSERT INTO terapie", (p_id, farm, dose, int(m), int(p), int(b)))
                    st.rerun()
            curr_t = db_run("SELECT * FROM terapie", (p_id,))
            for ct in curr_t:
                st.info(f"{ct['farmaco']} - {ct['dose']}")
                if st.button("Elimina", key=ct['id_u']): db_run("DELETE FROM terapie", (ct['id_u'],)); st.rerun()
        with t3:
            if st.button("Genera Briefing IA"):
                evs = db_run("SELECT * FROM eventi", (p_id,))
                prompt = "\n".join([e['nota'] for e in evs[:15]])
                st.write(genera_relazione_ia(prompt))

    elif ruolo_corr == "Infermiere":
        t1, t2 = st.tabs(["💊 Smarcatura", "💓 Parametri"])
        with t1:
            turno = st.selectbox("Turno", ["Mattina", "Pomeriggio", "Bisogno"])
            terapie = db_run("SELECT * FROM terapie", (p_id,))
            for t in terapie:
                mostra = (turno=="Mattina" and t['mat_nuovo']) or (turno=="Pomeriggio" and t['pom_nuovo']) or (turno=="Bisogno" and t['al_bisogno'])
                if mostra:
                    st.write(f"**{t['farmaco']}** ({t['dose']})")
                    c1, c2 = st.columns(2)
                    if c1.button("✅ Assunto", key=f"a_{t['id_u']}"):
                        db_run("INSERT INTO eventi", (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"✔️ {t['farmaco']}", ruolo_corr, firma_op, "A"))
                        st.rerun()
                    if c2.button("❌ Rifiuto", key=f"r_{t['id_u']}"):
                        db_run("INSERT INTO eventi", (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"❌ {t['farmaco']}", ruolo_corr, firma_op, "R"))
                        st.rerun()
        with t2:
            with st.form("p"):
                val = st.text_input("PA / FC / SpO2")
                if st.form_submit_button("Salva"):
                    db_run("INSERT INTO eventi", (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"💓 {val}", ruolo_corr, firma_op))
                    st.rerun()
    else:
        st.subheader("Consegna Operatore")
        nota = st.text_area("Nota")
        if st.button("Registra"):
            db_run("INSERT INTO eventi", (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), nota, ruolo_corr, firma_op))
            st.success("Fatto!"); st.rerun()

elif nav == "📅 Agenda":
    st.markdown("<div class='section-banner'><h2>AGENDA DINAMICA</h2></div>", unsafe_allow_html=True)
    st.info("Visualizzazione cronologica eventi ultimi 30 giorni.")
    p_lista = db_run("SELECT * FROM pazienti")
    p_sel = st.selectbox("Filtra Paziente", [p['nome'] for p in p_lista])
    p_id = [p['id'] for p in p_lista if p['nome'] == p_sel][0]
    evs = db_run("SELECT * FROM eventi", (p_id,))
    if evs:
        df = pd.DataFrame(evs)
        st.table(df[['data', 'ruolo', 'op', 'nota']].head(20))
