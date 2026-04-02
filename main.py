import streamlit as st
import sqlite3
import calendar
from datetime import datetime

# 1. CONFIGURAZIONE
st.set_page_config(page_title="REMS Registro", layout="wide")

# 2. STILE CSS (Ottimizzato per Mobile)
st.markdown("""
    <style>
    .scroll-giorni { display: flex; overflow-x: auto; gap: 8px; padding: 10px; background: #f8f9fa; border-radius: 10px; }
    .quadratino { min-width: 42px; height: 55px; border-radius: 8px; border: 1px solid #ddd; display: flex; flex-direction: column; align-items: center; justify-content: center; background: white; flex-shrink: 0; }
    .oggi { border: 3px solid #1e3a8a !important; background: #fff9c4 !important; font-weight: bold; }
    .info-f { font-size: 7px; color: #777; text-align: center; line-height: 1; margin-top: 2px; }
    .stButton>button { width: 100%; border-radius: 8px; }
    </style>
""", unsafe_allow_html=True)

# 3. FUNZIONE DATABASE 
def db_run(query, params=(), commit=False):
    with sqlite3.connect("rems_v12.db", timeout=10) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            if commit: conn.commit()
            return cursor.fetchall()
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e): return []
            return []

# 4. INIZIALIZZAZIONE SILENZIOSA (Niente scritte rosse)
db_run("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY, nome TEXT, stato TEXT DEFAULT 'ATTIVO')", commit=True)
db_run("CREATE TABLE IF NOT EXISTS eventi (id_u INTEGER PRIMARY KEY, id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT, esito TEXT)", commit=True)
db_run("CREATE TABLE IF NOT EXISTS terapie (id_u INTEGER PRIMARY KEY, p_id INTEGER, farmaco TEXT, dose TEXT, mat INTEGER, pom INTEGER, nott INTEGER, is_prn INTEGER DEFAULT 0)", commit=True)
db_run("ALTER TABLE eventi ADD COLUMN esito TEXT", commit=True)
db_run("ALTER TABLE terapie ADD COLUMN is_prn INTEGER DEFAULT 0", commit=True)

# 5. GESTIONE TEMPO AUTOMATICA
oggi_dt = datetime.now()
giorno_oggi = oggi_dt.day
mese_oggi_idx = oggi_dt.month
anno_oggi = oggi_dt.year
stringa_mese_anno = oggi_dt.strftime("%m/%Y")
gg_nel_mese = calendar.monthrange(anno_oggi, mese_oggi_idx)[1]

# 6. INTERFACCIA
p_list = db_run("SELECT id, nome FROM pazienti")
if not p_list:
    if st.button("➕ Inizializza Primo Paziente"):
        db_run("INSERT INTO pazienti (nome) VALUES ('PAZIENTE ESEMPIO')", commit=True)
        st.rerun()
else:
    sel_p = st.selectbox("👤 Seleziona Paziente", [p[1] for p in p_list])
    p_id = [p[0] for p in p_list if p[1] == sel_p][0]
    
    t1, t2 = st.tabs(["💊 REGISTRO FIRME", "🩺 AREA MEDICA"])
    
    with t1:
        turno = st.selectbox("🕒 Turno Attuale", ["Mattina (08-13)", "Pomeriggio/Notte (16-20)", "TAB (Al Bisogno)"])
        farmaci = db_run("SELECT id_u, farmaco, dose, mat, pom, nott, is_prn FROM terapie WHERE p_id=?", (p_id,))
        
        # Mappa orari turni
        mappa_turni = {"Mattina (08-13)": [3, 4], "Pomeriggio/Notte (16-20)": [4, 5], "TAB (Al Bisogno)": [6]}
        
        for f in farmaci:
            # Mostra il farmaco solo se previsto nel turno scelto
            if any(f[idx] == 1 for idx in mappa_turni[turno]):
                st.subheader(f"💊 {f[1]}")
                st.info(f"Dosaggio: {f[2]}")
                
                # Recupero firme del mese corrente
                firme_db = db_run("SELECT data, esito, op FROM eventi WHERE id=? AND nota LIKE ? AND data LIKE ?", 
                                   (p_id, f"%{f[1]}%", f"%/{stringa_mese_anno}%"))
                f_map = {int(d[0].split("/")[0]): {"e": d[1], "o": d[2], "h": d[0].split(" ")[1]} for d in firme_db if d[0]}

                # Visualizzazione a quadratini
                html_codice = "<div class='scroll-giorni'>"
                for d in range(1, gg_nel_mese + 1):
                    info = f_map.get(d)
                    stile_classe = "quadratino oggi" if d == giorno_oggi else "quadratino"
                    
                    esito_v, col, bg = (info['e'], "green", "#dcfce7") if info else ("-", "#888", "white")
                    if esito_v == "R": col, bg = "red", "#fee2e2"
                    
                    dettaglio = f"{info['o']}<br>{info['h']}" if info else ""
                    
                    html_codice += f"""
                    <div class='{stile_classe}' style='background:{bg}; color:{col};'>
                        <span style='font-size:9px;'>{d}</span>
                        <b style='font-size:16px;'>{esito_v}</b>
                        <div class='info-f'>{dettaglio}</div>
                    </div>"""
                html_codice += "</div>"
                st.markdown(html_codice, unsafe_allow_html=True)

                # FIRMA VELOCE (Pre-impostata su OGGI)
                with st.popover(f"✍️ Firma Rapida: {f[1]}"):
                    st.write(f"Conferma per oggi, giorno **{giorno_oggi}**")
                    # Selettore nascosto in fondo per emergenze (cambio giorno se serve)
                    g_scelto = st.number_input("Giorno (modifica solo per errori)", 1, gg_nel_mese, value=giorno_oggi, key=f"day_{f[0]}")
                    
                    col1, col2 = st.columns(2)
                    if col1.button("✅ ASSUNTO", key=f"ok_{f[0]}"):
                        ora_f = datetime.now().strftime('%H:%M')
                        data_f = f"{g_scelto:02d}/{stringa_mese_anno} {ora_f}"
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op, esito) VALUES (?,?,?,?,?,?)", 
                               (p_id, data_f, f"✔️ {f[1]}", "Infermiere", "Rossi", "A"), commit=True)
                        st.rerun()
                    if col2.button("❌ RIFIUTATO", key=f"no_{f[0]}"):
                        ora_f = datetime.now().strftime('%H:%M')
                        data_f = f"{g_scelto:02d}/{stringa_mese_anno} {ora_f}"
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op, esito) VALUES (?,?,?,?,?,?)", 
                               (p_id, data_f, f"✔️ {f[1]}", "Infermiere", "Rossi", "R"), commit=True)
                        st.rerun()
                st.divider()

    with t2:
        st.write("### 🩺 Nuova Prescrizione Medica")
        with st.form("form_medico", clear_on_submit=True):
            nome_f = st.text_input("Nome Farmaco")
            dose_f = st.text_input("Dose (es. 1 cp)")
            ora_f = st.selectbox("Orario", ["MATTINO", "POMERIGGIO", "NOTTE", "TAB"])
            if st.form_submit_button("Aggiungi in Terapia"):
                m, p, n, t = (1,0,0,0) if ora_f=="MATTINO" else ((0,1,0,0) if ora_f=="POMERIGGIO" else ((0,0,1,0) if ora_f=="NOTTE" else (0,0,0,1)))
                db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, is_prn) VALUES (?,?,?,?,?,?,?)", 
                       (p_id, nome_f, dose_f, m, p, n, t), commit=True)
                st.rerun()
