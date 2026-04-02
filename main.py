import streamlit as st
import sqlite3
import calendar
from datetime import datetime

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="REMS Connect PRO - Tracciabilità", layout="wide")

st.markdown("""
    <style>
    .scroll-giorni { 
        display: flex; overflow-x: auto; gap: 8px; padding: 15px 5px;
        background: #f8f9fa; border-radius: 10px; margin-bottom: 10px;
    }
    .quadratino {
        min-width: 42px; height: 55px; border-radius: 8px; 
        display: flex; flex-direction: column; align-items: center; 
        justify-content: center; border: 1px solid #dee2e6; background: white;
        position: relative;
    }
    .oggi-attivo { border: 3px solid #1e3a8a !important; background-color: #fff9c4 !important; }
    .info-firma { font-size: 7px; color: #666; margin-top: 2px; text-align: center; line-height: 1; }
    .farmaco-label { font-size: 1.2rem; font-weight: 800; color: #1e3a8a; }
    </style>
""", unsafe_allow_html=True)

# --- DATABASE ---
DB_NAME = "rems_final_v12.db"
def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            if commit: conn.commit()
            return cursor.fetchall()
        except Exception as e:
            st.error(f"Errore: {e}")
            return []

# --- LOGICA FIRMA (ORA CON OPERATORE) ---
def registra_firma(p_id, farmaco, turno, esito):
    ora = datetime.now().strftime("%d/%m/%Y %H:%M")
    # Qui usiamo un nome fisso "Inf. Turno" o st.session_state.user se hai un login
    operatore = "Inf. Rossi" 
    db_run("INSERT INTO eventi (id, data, nota, ruolo, op, esito) VALUES (?,?,?,?,?,?)", 
           (p_id, ora, f"✔️ SOMM ({turno}): {farmaco}", "Infermiere", operatore, esito), commit=True)
    st.rerun()

# --- RENDERING CON DETTAGLIO FIRMA ---
def mostra_registro_tracciabile(p_id, farmaci, turno_sel):
    mappa_chiavi = {"Mattina (08:00 - 13:00)": ["MAT", "POM"], "Pomeriggio/Notte (16:00 - 20:00)": ["POM", "NOT"], "TAB (Al Bisogno)": ["TAB"]}
    indici = {"MAT": 3, "POM": 4, "NOT": 5, "TAB": 6}
    
    chiavi = mappa_chiavi[turno_sel]
    f_filtrati = []
    for f in farmaci:
        for k in chiavi:
            if f[indici[k]] == 1: f_filtrati.append((f, k))

    oggi = datetime.now()
    giorni_mese = calendar.monthrange(oggi.year, oggi.month)[1]
    mese_corrente = oggi.strftime("%m/%Y")

    for f_data, t_key in f_filtrati:
        f_id, f_nome, f_dose = f_data[0], f_data[1], f_data[2]
        
        st.markdown(f"<div class='farmaco-label'>{f_nome} <small>({t_key})</small></div>", unsafe_allow_html=True)
        st.caption(f"Dosaggio: {f_dose}")
        
        # Recupero TUTTI i dati della firma (inclusi operatore e ora)
        firme_dati = db_run("SELECT data, esito, op FROM eventi WHERE id=? AND nota LIKE ? AND data LIKE ?", 
                            (p_id, f"%({t_key}): {f_nome}%", f"%/{mese_corrente}%"))
        
        # Mappa complessa: giorno -> {esito, operatore, orario}
        firme_map = {int(d[0].split("/")[0]): {"esito": d[1], "op": d[2], "ora": d[0].split(" ")[1]} for d in firme_dati}

        # Striscia dei giorni con Info Operatore
        html_giorni = "<div class='scroll-giorni'>"
        for d in range(1, giorni_mese + 1):
            info = firme_map.get(d, None)
            is_today = "oggi-attivo" if d == oggi.day else ""
            
            esito_vis = info['esito'] if info else '-'
            op_vis = info['op'] if info else ''
            ora_vis = info['ora'] if info else ''
            
            color = "green" if esito_vis == "A" else ("red" if esito_vis == "R" else "#888")
            bg = "#dcfce7" if esito_vis == "A" else ("#fee2e2" if esito_vis == "R" else "white")
            
            html_giorni += f"""
            <div class='quadratino {is_today}' style='background:{bg}; color:{color};'>
                <span style='font-size:9px;'>{d}</span>
                <b style='font-size:15px;'>{esito_vis}</b>
                <div class='info-firma'>{op_vis}<br>{ora_vis}</div>
            </div>"""
        html_giorni += "</div>"
        st.markdown(html_giorni, unsafe_allow_html=True)

        # Bottone Popover per Firmare
        if oggi.day not in firme_map:
            with st.popover(f"✍️ Firma per {f_nome}"):
                c1, c2 = st.columns(2)
                if c1.button("✅ A", key=f"A_{f_id}_{t_key}"): registra_firma(p_id, f_nome, t_key, "A")
                if c2.button("❌ R", key=f"R_{f_id}_{t_key}"): registra_firma(p_id, f_nome, t_key, "R")
        else:
            # Tasto per vedere il dettaglio in un messaggio espandibile
            with st.expander("🔍 Vedi Log Somministrazione"):
                st.write(f"**Operatore:** {firme_map[oggi.day]['op']}")
                st.write(f"**Orario:** {firme_map[oggi.day]['ora']}")
                st.write(f"**Esito:** {firme_map[oggi.day]['esito']}")
        st.divider()

# --- APP INTERFACE ---
p_data = db_run("SELECT id, nome FROM pazienti WHERE stato='ATTIVO'")
if p_data:
    sel_p = st.sidebar.selectbox("Paziente", [p[1] for p in p_data])
    p_id = [p[0] for p in p_data if p[1] == sel_p][0]

    scelta_turno = st.selectbox("Turno", ["Mattina (08:00 - 13:00)", "Pomeriggio/Notte (16:00 - 20:00)", "TAB (Al Bisogno)"])
    
    farmaci = db_run("SELECT id_u, farmaco, dose, mat, pom, nott, is_prn FROM terapie WHERE p_id=?", (p_id,))
    if farmaci:
        mostra_registro_tracciabile(p_id, farmaci, scelta_turno)
