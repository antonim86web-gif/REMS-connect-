import streamlit as st
import sqlite3
import calendar
from datetime import datetime

# --- CONFIGURAZIONE E STILE ---
st.set_page_config(page_title="REMS Connect Pro", layout="wide")

st.markdown("""
    <style>
    .scroll-giorni { display: flex; overflow-x: auto; gap: 6px; padding: 10px; background: #f8f9fa; border-radius: 10px; border: 1px solid #eee; }
    .quadratino { 
        min-width: 44px; height: 58px; border-radius: 6px; border: 1px solid #ddd; 
        display: flex; flex-direction: column; align-items: center; justify-content: flex-start; 
        background: white; flex-shrink: 0; padding-top: 2px;
    }
    .oggi { border: 2.5px solid #1e3a8a !important; background: #fffde7 !important; }
    .num-giorno { font-size: 8px; color: #999; margin-bottom: -2px; }
    .lettera-esito { font-size: 11px; font-weight: bold; margin-top: 1px; }
    .info-firma { font-size: 7px; color: #444; text-align: center; line-height: 1.1; margin-top: 3px; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; }
    .card-paziente { background: #f0f2f6; padding: 15px; border-radius: 10px; border-left: 5px solid #1e3a8a; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

# --- DATABASE ENGINE ---
def db_run(query, params=(), commit=False):
    with sqlite3.connect("rems_pro_v35.db", timeout=10) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            if commit: conn.commit()
            return cursor.fetchall()
        except sqlite3.OperationalError: return []

# Inizializzazione Tabelle
db_run("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY, nome TEXT, stanza TEXT, stato TEXT DEFAULT 'ATTIVO')", commit=True)
db_run("CREATE TABLE IF NOT EXISTS eventi (id_u INTEGER PRIMARY KEY, id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT, esito TEXT)", commit=True)
db_run("CREATE TABLE IF NOT EXISTS terapie (id_u INTEGER PRIMARY KEY, p_id INTEGER, farmaco TEXT, dose TEXT, mat INTEGER, pom INTEGER, tab INTEGER)", commit=True)

# --- LOGICA TEMPORALE AUTOMATICA ---
adesso = datetime.now()
giorno_oggi = adesso.day
filtro_mese = adesso.strftime("%m/%Y")
gg_mese = calendar.monthrange(adesso.year, adesso.month)[1]

# --- SIDEBAR: MONITORAGGIO & STANZE ---
with st.sidebar:
    st.title("🏥 REMS Connect")
    p_list = db_run("SELECT id, nome, stanza FROM pazienti WHERE stato='ATTIVO'")
    if not p_list:
        if st.button("➕ Inizializza Primo Paziente"):
            db_run("INSERT INTO pazienti (nome, stanza) VALUES ('Paziente Esempio', 'Stanza 101')", commit=True)
            st.rerun()
        st.stop()
    
    sel_p_nome = st.selectbox("Seleziona Paziente (Mappa Stanze)", [f"{p[2]} - {p[1]}" for p in p_list])
    p_id = [p[0] for p in p_list if f"{p[2]} - {p[1]}" == sel_p_nome][0]
    p_nome = [p[1] for p in p_list if p[0] == p_id][0]

# --- CORPO CENTRALE ---
st.markdown(f"<div class='card-paziente'><h3>👤 {p_nome}</h3><p>Mese: {filtro_mese} | Oggi: {giorno_oggi}</p></div>", unsafe_allow_html=True)

t_inf, t_med, t_equipe = st.tabs(["💊 INFERMIERE", "🩺 MEDICO", "👥 EQUIPE"])

# --- TAB INFERMIERE ---
with t_inf:
    sub_t1, sub_t2, sub_t3 = st.tabs(["Terapia", "Parametri Vitali", "Consegne"])
    
    with sub_t1:
        turno = st.selectbox("Scegli Turno", ["Mattina (08-13)", "Pomeriggio/Notte (16-20)", "TAB (Al bisogno)"])
        farmaci = db_run("SELECT id_u, farmaco, dose, mat, pom, tab FROM terapie WHERE p_id=?", (p_id,))
        mappa = {"Mattina (08-13)": 3, "Pomeriggio/Notte (16-20)": 4, "TAB (Al bisogno)": 5}
        col_idx = mappa[turno]
        
        for f in farmaci:
            if f[col_idx] == 1:
                st.write(f"**{f[1]}** - {f[2]}")
                # Recupero firme
                firme = db_run("SELECT data, esito, op FROM eventi WHERE id=? AND nota LIKE ? AND data LIKE ?", 
                               (p_id, f"%{f[1]}%", f"%/{filtro_mese}%"))
                f_map = {int(d[0].split("/")[0]): {"e": d[1], "o": d[2], "h": d[0].split(" ")[1]} for d in firme if d[0]}

                # Griglia quadratini
                h = "<div class='scroll-giorni'>"
                for d in range(1, gg_mese + 1):
                    info = f_map.get(d)
                    cl = "quadratino oggi" if d == giorno_oggi else "quadratino"
                    es, col, bg = (info['e'], "green", "#dcfce7") if info else ("-", "#888", "white")
                    if es == "R": col, bg = "red", "#fee2e2"
                    h += f"<div class='{cl}' style='background:{bg}; color:{col};'><div class='num-giorno'>{d}</div><div class='lettera-esito'>{es}</div><div class='info-firma'>{info['o'] if info else ''}<br>{info['h'] if info else ''}</div></div>"
                h += "</div>"
                st.markdown(h, unsafe_allow_html=True)

                with st.popover(f"Smarca {f[1]}"):
                    c1, c2 = st.columns(2)
                    if c1.button("✅ ASSUNTO", key=f"A_{f[0]}_{turno}"):
                        dt = f"{giorno_oggi:02d}/{filtro_mese} {datetime.now().strftime('%H:%M')}"
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op, esito) VALUES (?,?,?,?,?,?)", (p_id, dt, f"✔️ {f[1]}", "Inf", "ROSSI", "A"), commit=True)
                        st.rerun()
                    if c2.button("❌ RIFIUTATO", key=f"R_{f[0]}_{turno}"):
                        dt = f"{giorno_oggi:02d}/{filtro_mese} {datetime.now().strftime('%H:%M')}"
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op, esito) VALUES (?,?,?,?,?,?)", (p_id, dt, f"✔️ {f[1]}", "Inf", "ROSSI", "R"), commit=True)
                        st.rerun()
                st.divider()

    with sub_t2:
        with st.form("parametri"):
            pa = st.text_input("Pressione Arteriara")
            so2 = st.text_input("Saturazione O2")
            if st.form_submit_button("Registra Parametri"):
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), f"PA: {pa}, SO2: {so2}", "Inf", "ROSSI"), commit=True)
                st.rerun()

    with sub_t3:
        nota = st.text_area("Nuova Consegna Infermieristica")
        if st.button("Salva Consegna Inf."):
            db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), nota, "Inf", "ROSSI"), commit=True)
            st.rerun()

# --- TAB MEDICO ---
with t_med:
    sub_m1, sub_m2 = st.tabs(["Gestione Terapia", "Consegne Cliniche"])
    with sub_m1:
        st.write("### 🩺 Prescrizione")
        with st.form("med_presc"):
            fn = st.text_input("Nome Farmaco")
            fd = st.text_input("Dosaggio")
            orario = st.selectbox("Fascia Oraria", ["8:13 (Mattina)", "16-20 (Pomeriggio)", "Al bisogno (TAB)"])
            if st.form_submit_button("Aggiungi Terapia"):
                m, p, t = (1,0,0) if "8:13" in orario else ((0,1,0) if "16-20" in orario else (0,0,1))
                db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, tab) VALUES (?,?,?,?,?,?)", (p_id, fn, fd, m, p, t), commit=True)
                st.rerun()
        
        st.write("### 🗑️ Terapie Attive (per Modifica/Elimina)")
        attive = db_run("SELECT id_u, farmaco, dose FROM terapie WHERE p_id=?", (p_id,))
        for a in attive:
            col1, col2 = st.columns([4,1])
            col1.write(f"{a[1]} - {a[2]}")
            if col2.button("Elimina", key=f"del_{a[0]}"):
                db_run("DELETE FROM terapie WHERE id_u=?", (a[0],), commit=True)
                st.rerun()

    with sub_m2:
        nota_m = st.text_area("Diario Clinico Medico")
        if st.button("Salva Diario"):
            db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), nota_m, "Medico", "Dott. Latini"), commit=True)
            st.rerun()

# --- TAB EQUIPE ---
with t_equipe:
    ruolo_eq = st.selectbox("Seleziona Ruolo", ["Psicologo", "Educatore", "OSS", "Assistente Sociale"])
    nota_eq = st.text_area(f"Nota per {ruolo_eq}")
    if st.button(f"Salva Nota {ruolo_eq}"):
        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), nota_eq, ruolo_eq, "Equipe"), commit=True)
        st.rerun()
    
    st.divider()
    st.write("### 📜 Storico Eventi (Agenda Dinamica)")
    storia = db_run("SELECT data, ruolo, nota, op FROM eventi WHERE id=? ORDER BY id_u DESC LIMIT 10", (p_id,))
    for s in storia:
        st.write(f"**{s[0]}** | {s[1]} ({s[3]}): {s[2]}")
