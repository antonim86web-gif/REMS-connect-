import streamlit as st
import sqlite3
import calendar
from datetime import datetime

# 1. CONFIGURAZIONE
st.set_page_config(page_title="REMS Registro", layout="wide")

# 2. STILE CSS (Ottimizzato per leggere la firma e rimpicciolire A/R)
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
    .info-firma { 
        font-size: 7px; color: #444; text-align: center; line-height: 1; 
        margin-top: 3px; width: 100%; word-wrap: break-word; font-weight: normal;
    }
    .stButton>button { width: 100%; height: 50px; border-radius: 8px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# 3. FUNZIONE DATABASE (Corazzata)
def db_run(query, params=(), commit=False):
    with sqlite3.connect("rems_v12.db", timeout=10) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            if commit: conn.commit()
            return cursor.fetchall()
        except sqlite3.OperationalError:
            return []

# 4. INIZIALIZZAZIONE TABELLE
db_run("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY, nome TEXT, stato TEXT DEFAULT 'ATTIVO')", commit=True)
db_run("CREATE TABLE IF NOT EXISTS eventi (id_u INTEGER PRIMARY KEY, id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT, esito TEXT)", commit=True)
db_run("CREATE TABLE IF NOT EXISTS terapie (id_u INTEGER PRIMARY KEY, p_id INTEGER, farmaco TEXT, dose TEXT, mat INTEGER, pom INTEGER, nott INTEGER, is_prn INTEGER DEFAULT 0)", commit=True)

# 5. GESTIONE TEMPO (Automatico + Selettore per Archivio/Cambio Mese)
oggi_dt = datetime.now()
mesi_nomi = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]

with st.sidebar:
    st.header("📅 Periodo")
    # Questo risolve il dubbio del 30 aprile: puoi sempre tornare al mese precedente
    mese_sel = st.selectbox("Mese", mesi_nomi, index=oggi_dt.month - 1)
    anno_sel = st.number_input("Anno", 2024, 2030, oggi_dt.year)
    mese_idx = mesi_nomi.index(mese_sel) + 1
    str_filtro_mese = f"{mese_idx:02d}/{anno_sel}"
    gg_del_mese = calendar.monthrange(anno_sel, mese_idx)[1]

# 6. APP PRINCIPALE
p_list = db_run("SELECT id, nome FROM pazienti")
if not p_list:
    if st.button("➕ Crea Primo Paziente"):
        db_run("INSERT INTO pazienti (nome) VALUES ('PAZIENTE 1')", commit=True)
        st.rerun()
else:
    sel_p = st.sidebar.selectbox("👤 Paziente", [p[1] for p in p_list])
    p_id = [p[0] for p in p_list if p[1] == sel_p][0]
    
    tab1, tab2 = st.tabs(["💊 REGISTRO FIRME", "🩺 AREA MEDICA"])
    
    with tab1:
        # Filtro Turno (Solo farmaci del turno scelto)
        turno = st.selectbox("🕒 Turno di Lavoro", ["Mattina (08-13)", "Pomeriggio/Notte (16-20)", "TAB"])
        farmaci = db_run("SELECT id_u, farmaco, dose, mat, pom, nott, is_prn FROM terapie WHERE p_id=?", (p_id,))
        
        # Mappa turni: MAT=3, POM=4, NOT=5, TAB=6
        mappa_orari = {"Mattina (08-13)": [3, 4], "Pomeriggio/Notte (16-20)": [4, 5], "TAB": [6]}
        
        for f in farmaci:
            # Controllo se il farmaco deve essere mostrato in questo turno
            if any(f[idx] == 1 for idx in mappa_orari[turno]):
                st.markdown(f"### {f[1]}")
                st.caption(f"Dosaggio: {f[2]}")
                
                # Carichiamo le firme per il mese e anno selezionati
                firme_db = db_run("SELECT data, esito, op FROM eventi WHERE id=? AND nota LIKE ? AND data LIKE ?", 
                                   (p_id, f"%{f[1]}%", f"%/{str_filtro_mese}%"))
                
                # Mappatura: giorno -> {esito, operatore, ora}
                f_map = {int(d[0].split("/")[0]): {"e": d[1], "o": d[2], "h": d[0].split(" ")[1]} for d in firme_db if d[0]}

                # Striscia Quadratini (A e R piccole come richiesto)
                h = "<div class='scroll-giorni'>"
                for d in range(1, gg_del_mese + 1):
                    info = f_map.get(d)
                    # Evidenzia OGGI solo se mese/anno coincidono con la realtà
                    is_oggi = "oggi" if (d == oggi_dt.day and mese_idx == oggi_dt.month and anno_sel == oggi_dt.year) else ""
                    
                    es, col, bg = (info['e'], "green", "#dcfce7") if info else ("-", "#888", "white")
                    if es == "R": col, bg = "red", "#fee2e2"
                    
                    op_t = f"{info['o']}<br>{info['h']}" if info else ""
                    
                    h += f"""
                    <div class='quadratino {is_oggi}' style='background:{bg}; color:{col};'>
                        <div class='num-giorno'>{d}</div>
                        <div class='lettera-esito'>{es}</div>
                        <div class='info-firma'>{op_t}</div>
                    </div>"""
                h += "</div>"
                st.markdown(h, unsafe_allow_html=True)

                # FIRMA ISTANTANEA (Automatica sul giorno corrente)
                with st.popover(f"✍️ Firma per OGGI"):
                    st.write(f"Conferma per il giorno **{oggi_dt.day} {mese_sel}**")
                    c1, c2 = st.columns(2)
                    
                    if c1.button("✅ ASSUNTO", key=f"ok_{f[0]}_{turno}"):
                        # Registra sul giorno reale di oggi
                        dt_f = f"{oggi_dt.day:02d}/{str_filtro_mese} {datetime.now().strftime('%H:%M')}"
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op, esito) VALUES (?,?,?,?,?,?)", 
                               (p_id, dt_f, f"✔️ {f[1]}", "Inf", "ROSSI", "A"), commit=True)
                        st.rerun()
                        
                    if c2.button("❌ RIFIUTATO", key=f"no_{f[0]}_{turno}"):
                        dt_f = f"{oggi_dt.day:02d}/{str_filtro_mese} {datetime.now().strftime('%H:%M')}"
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op, esito) VALUES (?,?,?,?,?,?)", 
                               (p_id, dt_f, f"✔️ {f[1]}", "Inf", "ROSSI", "R"), commit=True)
                        st.rerun()
                st.divider()

    with tab2:
        st.write("### 🩺 Nuova Prescrizione Medica")
        with st.form("medico"):
            fn = st.text_input("Nome Farmaco")
            fd = st.text_input("Dose (es. 1 bustina)")
            ora = st.selectbox("Orario Somministrazione", ["MATTINO", "POMERIGGIO", "NOTTE", "TAB"])
            if st.form_submit_button("Salva in Terapia"):
                m, p, n, t = (1,0,0,0) if ora=="MATTINO" else ((0,1,0,0) if ora=="POMERIGGIO" else ((0,0,1,0) if ora=="NOTTE" else (0,0,0,1)))
                db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, is_prn) VALUES (?,?,?,?,?,?,?)", 
                       (p_id, fn, fd, m, p, n, t), commit=True)
                st.rerun()
