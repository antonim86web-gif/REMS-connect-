import streamlit as st
import sqlite3
import calendar
from datetime import datetime

# --- CONFIGURAZIONE E STILE ---
st.set_page_config(page_title="REMS Connect PRO", layout="wide")

st.markdown("""
    <style>
    .scroll-giorni { 
        display: flex; overflow-x: auto; gap: 8px; padding: 15px 5px;
        background: #f1f3f5; border-radius: 10px; margin-bottom: 10px;
    }
    .quadratino {
        min-width: 42px; height: 55px; border-radius: 8px; 
        display: flex; flex-direction: column; align-items: center; 
        justify-content: center; border: 1px solid #dee2e6; background: white;
    }
    .oggi-attivo { border: 3px solid #1e3a8a !important; background-color: #fff9c4 !important; }
    .info-firma { font-size: 7px; color: #666; margin-top: 2px; text-align: center; line-height: 1.1; }
    .farmaco-label { font-size: 1.2rem; font-weight: 800; color: #1e3a8a; margin-top: 10px; }
    .sez-titolo { background: #1e3a8a; color: white; padding: 10px; border-radius: 8px; text-align: center; margin-bottom: 15px; }
    </style>
""", unsafe_allow_html=True)

# --- DATABASE ENGINE ---
DB_NAME = "rems_final_v12.db"
def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            if commit: conn.commit()
            return cursor.fetchall()
        except Exception as e:
            st.error(f"Errore DB: {e}")
            return []

def init_db():
    db_run("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY, nome TEXT, stato TEXT DEFAULT 'ATTIVO')", commit=True)
    db_run("CREATE TABLE IF NOT EXISTS eventi (id_u INTEGER PRIMARY KEY, id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT, esito TEXT)", commit=True)
    db_run("CREATE TABLE IF NOT EXISTS terapie (id_u INTEGER PRIMARY KEY, p_id INTEGER, farmaco TEXT, dose TEXT, mat INTEGER, pom INTEGER, nott INTEGER, is_prn INTEGER DEFAULT 0)", commit=True)
    try: db_run("ALTER TABLE eventi ADD COLUMN esito TEXT", commit=True)
    except: pass
    try: db_run("ALTER TABLE terapie ADD COLUMN is_prn INTEGER DEFAULT 0", commit=True)
    except: pass

init_db()

# --- LOGICA TEMPORALE (Risolve il dubbio del 30 Aprile) ---
oggi_real = datetime.now()
mesi_nomi = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]

with st.sidebar:
    st.header("📅 Archivio")
    mese_sel = st.selectbox("Mese da visualizzare", mesi_nomi, index=oggi_real.month - 1)
    anno_sel = st.number_input("Anno", min_value=2024, max_value=2030, value=oggi_real.year)
    
    # Costruiamo il filtro per il DB: "04/2026"
    mese_idx = mesi_nomi.index(mese_sel) + 1
    stringa_filtro_mese = f"{mese_idx:02d}/{anno_sel}"
    giorni_nel_mese = calendar.monthrange(anno_sel, mese_idx)[1]

# --- LOGICA SMARCAMENTO ---
def registra_firma(p_id, farmaco, turno, esito, giorno_scelto):
    # Se firmo per oggi, uso l'ora reale. Se firmo per un giorno passato, metto ore 23:59 di quel giorno.
    ora_corrente = datetime.now().strftime("%H:%M")
    data_firma = f"{giorno_scelto:02d}/{stringa_filtro_mese} {ora_corrente}"
    op_nome = "Inf. Rossi" # Qui andrebbe lo st.session_state.user se avessi login
    
    db_run("INSERT INTO eventi (id, data, nota, ruolo, op, esito) VALUES (?,?,?,?,?,?)", 
           (p_id, data_firma, f"✔️ SOMM ({turno}): {farmaco}", "Infermiere", op_nome, esito), commit=True)
    st.rerun()

def mostra_registro(p_id, farmaci, turno_label):
    mappa = {"Mattina (08:00 - 13:00)": ["MAT", "POM"], "Pomeriggio/Notte (16:00 - 20:00)": ["POM", "NOT"], "TAB (Al Bisogno)": ["TAB"]}
    indici = {"MAT": 3, "POM": 4, "NOT": 5, "TAB": 6}
    
    chiavi = mappa[turno_label]
    f_filtrati = []
    for f in farmaci:
        for k in chiavi:
            if f[indici[k]] == 1: f_filtrati.append((f, k))

    if not f_filtrati:
        st.info("Nessuna terapia per questo orario.")
        return

    st.markdown(f"<div class='sez-titolo'>{mese_sel.upper()} {anno_sel} - {turno_label}</div>", unsafe_allow_html=True)

    for f_data, t_key in f_filtrati:
        f_id, f_nome, f_dose = f_data[0], f_data[1], f_data[2]
        
        st.markdown(f"<div class='farmaco-label'>{f_nome} <small>({t_key})</small></div>", unsafe_allow_html=True)
        st.caption(f"Dosaggio: {f_dose}")
        
        # Recupero storico del mese selezionato
        firme_db = db_run("SELECT data, esito, op FROM eventi WHERE id=? AND nota LIKE ? AND data LIKE ?", 
                           (p_id, f"%({t_key}): {f_nome}%", f"%/{stringa_filtro_mese}%"))
        f_map = {int(d[0].split("/")[0]): {"esito": d[1], "op": d[2], "ora": d[0].split(" ")[1]} for d in firme_db}

        # Striscia dei giorni
        html_g = "<div class='scroll-giorni'>"
        for d in range(1, giorni_nel_mese + 1):
            info = f_map.get(d, None)
            # Evidenzia oggi solo se siamo nel mese reale corrente
            is_oggi = "oggi-attivo" if (d == oggi_real.day and mese_idx == oggi_real.month and anno_sel == oggi_real.year) else ""
            
            es, color, bg = (info['esito'], "green", "#dcfce7") if info else ("-", "#888", "white")
            if es == "R": color, bg = "red", "#fee2e2"
            
            op_testo = f"{info['op']}<br>{info['ora']}" if info else ""
            
            html_g += f"""<div class='quadratino {is_oggi}' style='background:{bg}; color:{color};'>
                          <span style='font-size:9px;'>{d}</span><b style='font-size:16px;'>{es}</b>
                          <div class='info-firma'>{op_testo}</div></div>"""
        html_g += "</div>"
        st.markdown(html_g, unsafe_allow_html=True)

        # Popover per firma (permette di firmare oggi o correggere il passato)
        with st.popover(f"✍️ Smarca {f_nome}"):
            g_firma = st.number_input("Giorno da firmare", 1, giorni_nel_mese, value=min(oggi_real.day, giorni_nel_mese))
            st.write(f"Stai firmando per il giorno: **{g_firma} {mese_sel}**")
            c1, c2 = st.columns(2)
            if c1.button("✅ ASSUNTO", key=f"A_{f_id}_{t_key}_{d}"): registra_firma(p_id, f_nome, t_key, "A", g_firma)
            if c2.button("❌ RIFIUTATO", key=f"R_{f_id}_{t_key}_{d}"): registra_firma(p_id, f_nome, t_key, "R", g_firma)
        st.divider()

# --- INTERFACCIA ---
p_list = db_run("SELECT id, nome FROM pazienti WHERE stato='ATTIVO'")
if p_list:
    sel_p = st.sidebar.selectbox("👤 Paziente", [p[1] for p in p_list])
    p_id = [p[0] for p in p_list if p[1] == sel_p][0]

    t_inf, t_med = st.tabs(["💊 REGISTRO", "🩺 MEDICO"])

    with t_inf:
        turno = st.selectbox("Turno", ["Mattina (08:00 - 13:00)", "Pomeriggio/Notte (16:00 - 20:00)", "TAB (Al Bisogno)"])
        farmaci = db_run("SELECT id_u, farmaco, dose, mat, pom, nott, is_prn FROM terapie WHERE p_id=?", (p_id,))
        if farmaci: mostra_registro(p_id, farmaci, turno)
        else: st.info("Nessuna terapia.")

    with t_med:
        with st.form("med"):
            f = st.text_input("Farmaco")
            d = st.text_input("Dose")
            o = st.selectbox("Orario", ["MATTINO (08:00)", "POMERIGGIO (16:00)", "NOTTE (20:00)", "TAB (Al Bisogno)"])
            if st.form_submit_button("Prescrivi"):
                m, p, n, tsu = (1,0,0,0) if "MAT" in o else ((0,1,0,0) if "POM" in o else ((0,0,1,0) if "NOT" in o else (0,0,0,1)))
                db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, is_prn) VALUES (?,?,?,?,?,?,?)", (p_id, f, d, m, p, n, tsu), commit=True)
                st.rerun()
