import sqlite3
import streamlit as stimport sqlite3
import streamlit as st
import calendar
from datetime import datetime

# --- 1. FIX DATABASE (Esegui questo blocco per sicurezza) ---
def check_db_integrity():
    with sqlite3.connect("rems_final_v12.db") as conn:
        cursor = conn.cursor()
        # Assicuriamoci che is_prn esista in terapie
        try: cursor.execute("ALTER TABLE terapie ADD COLUMN is_prn INTEGER DEFAULT 0")
        except: pass
        # Assicuriamoci che esito esista in eventi
        try: cursor.execute("ALTER TABLE eventi ADD COLUMN esito TEXT")
        except: pass
        conn.commit()

check_db_integrity()

# --- 2. FUNZIONE DI RENDERING (CORRETTA) ---
def genera_griglia_mensile(p_id, farmaci, turno_target, titolo):
    # Filtro i farmaci per il turno richiesto
    if turno_target == "TAB":
        f_turno = [f for f in farmaci if len(f) > 6 and f[6] == 1]
    else:
        mappa = {"MAT": 3, "POM": 4, "NOT": 5}
        idx = mappa[turno_target]
        f_turno = [f for f in farmaci if len(f) > idx and f[idx] == 1]

    if not f_turno:
        return # Se non ci sono farmaci, non scrive nulla (neanche il titolo)

    st.markdown(f"#### {titolo}")
    
    # CSS per evitare lo schermo bianco e forzare lo scroll
    st.markdown("""
        <style>
            .scroll-wrapper { overflow-x: auto; border: 1px solid #eee; border-radius: 8px; margin-bottom: 20px; }
            .m-table { border-collapse: collapse; width: 100%; font-family: sans-serif; font-size: 11px; }
            .m-table th, .m-table td { border: 1px solid #ddd; padding: 6px; text-align: center; min-width: 32px; }
            .f-col { position: sticky; left: 0; background: #f9f9f9; z-index: 2; min-width: 120px !important; text-align: left !important; }
            .current-day { background-color: #fff9c4 !important; font-weight: bold; }
        </style>
    """, unsafe_allow_html=True)

    # Calcolo giorni del mese corrente
    oggi = datetime.now()
    giorni_nel_mese = calendar.monthrange(oggi.year, oggi.month)[1]
    
    # Costruzione HTML della tabella
    header = "".join([f"<th class='{'current-day' if d == oggi.day else ''}'>{d}</th>" for d in range(1, giorni_nel_mese + 1)])
    html = f"<div class='scroll-wrapper'><table class='m-table'><thead><tr><th class='f-col'>Farmaco</th>{header}</tr></thead><tbody>"
    
    for f in f_turno:
        id_f, nome_f = f[0], f[1]
        righe_giorni = ""
        
        # Recupero TUTTE le firme del mese per questo farmaco in un colpo solo (ottimizzazione)
        mese_str = oggi.strftime("%m/%Y")
        firme = db_run("SELECT data, esito FROM eventi WHERE id=? AND nota LIKE ? AND data LIKE ?", 
                       (p_id, f"%{turno_target}: {nome_f}%", f"%/{mese_str}%"))
        
        # Trasformo in dizionario {giorno: esito}
        firme_dict = {}
        for data_f, esito_f in firme:
            try: 
                gg = int(data_f.split("/")[0])
                firme_dict[gg] = esito_f
            except: continue

        for d in range(1, giorni_nel_mese + 1):
            esito = firme_dict.get(d, "")
            color = "green" if esito == "A" else "red"
            cell_class = "current-day" if d == oggi.day else ""
            righe_giorni += f"<td class='{cell_class}' style='color:{color}; font-weight:bold;'>{esito}</td>"
        
        html += f"<tr><td class='f-col'>{nome_f}</td>{righe_giorni}</tr>"
    
    html += "</tbody></table></div>"
    st.markdown(html, unsafe_allow_html=True)

    # --- BOTTONI DI FIRMA (Solo per oggi) ---
    st.caption(f"Firma per oggi ({oggi.strftime('%d/%m')})")
    cols = st.columns(len(f_turno))
    for i, f in enumerate(f_turno):
        with cols[i]:
            # Controlla se oggi è già firmato
            if oggi.day in firme_dict:
                st.success(f"{f[1]}: {firme_dict[oggi.day]}")
            else:
                c_a, c_r = st.columns(2)
                if c_a.button("A", key=f"btnA_{f[0]}_{turno_target}"):
                    registra_firma(p_id, f[1], turno_target, "A")
                if c_r.button("R", key=f"btnR_{f[0]}_{turno_target}"):
                    registra_firma(p_id, f[1], turno_target, "R")

def registra_firma(p_id, farmaco, turno, esito):
    ora = datetime.now().strftime("%d/%m/%Y %H:%M")
    nota = f"✔️ SOMM ({turno}): {farmaco}"
    # firma_op deve essere definita nella tua sessione
    op = st.session_state.user_session['uid'] if 'user_session' in st.session_state else "Operatore"
    db_run("INSERT INTO eventi (id, data, nota, ruolo, op, esito) VALUES (?,?,?,?,?,?)", 
           (p_id, ora, nota, "Infermiere", op, esito), True)
    st.rerun()

# --- NEL TUO CODICE PRINCIPALE ---
# Assicurati che 'farmaci' contenga (id, nome, dose, mat, pom, nott, is_prn)
farmaci = db_run("SELECT id_u, farmaco, dose, mat, pom, nott, is_prn FROM terapie WHERE p_id=?", (p_id,))

if farmaci:
    genera_griglia_mensile(p_id, farmaci, "MAT", "☀️ MATTINO")
    st.write("---")
    genera_griglia_mensile(p_id, farmaci, "POM", "⛅ POMERIGGIO")
    st.write("---")
    genera_griglia_mensile(p_id, farmaci, "NOT", "🌙 NOTTE")
    st.write("---")
    genera_griglia_mensile(p_id, farmaci, "TAB", "🆘 TAB (Al Bisogno)")
else:
    st.warning("Nessuna terapia trovata per questo paziente.")

from datetime import datetime, timedelta, timezone
import calendar

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="REMS Terapia Mensile", layout="wide")

# CSS per forzare la tabella a non esplodere e permettere lo scroll orizzontale
st.markdown("""
<style>
    .scroll-container {
        overflow-x: auto;
        white-space: nowrap;
        padding-bottom: 20px;
    }
    .terapia-table {
        border-collapse: collapse;
        font-family: sans-serif;
        font-size: 0.8rem;
        width: 100%;
    }
    .terapia-table th, .terapia-table td {
        border: 1px solid #ccc;
        padding: 4px;
        text-align: center;
        min-width: 35px;
    }
    .sticky-col {
        position: sticky;
        left: 0;
        background: white;
        z-index: 10;
        min-width: 150px !important;
        text-align: left !important;
        font-weight: bold;
    }
    .header-turno {
        background-color: #1e3a8a;
        color: white;
        text-align: left;
        padding: 10px;
        font-weight: bold;
        text-transform: uppercase;
    }
    .btn-a { color: green; font-weight: bold; cursor: pointer; }
    .btn-r { color: red; font-weight: bold; cursor: pointer; }
</style>
""", unsafe_allow_html=True)

# --- FUNZIONI DB ---
def db_query(q, p=()):
    with sqlite3.connect("rems_final_v12.db") as conn:
        return conn.execute(q, p).fetchall()

def db_write(q, p=()):
    with sqlite3.connect("rems_final_v12.db") as conn:
        conn.execute(q, p)
        conn.commit()

# --- LOGICA DI FIRMA ---
def firma(p_id, f_id, f_nome, turno, giorno, esito):
    data_f = f"{giorno:02d}/{datetime.now().month:02d}/{datetime.now().year}"
    nota = f"✔️ SOMM ({turno}): {f_nome} | {esito}"
    db_write("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", 
             (p_id, data_f, nota, "Infermiere", "Operatore"))
    st.rerun()

# --- INTERFACCIA ---
p_id = 1 # Esempio per il paziente selezionato
oggi = datetime.now()
num_giorni = calendar.monthrange(oggi.year, oggi.month)[1]

st.title(f"Registro Terapie - {calendar.month_name[oggi.month]} {oggi.year}")

# Carico i farmaci
farmaci = db_query("SELECT id_u, farmaco, dose, mat, pom, nott, is_prn FROM terapie WHERE p_id=?", (p_id,))

# Carico le firme già messe nel mese per questo paziente
firme_mese = db_query("SELECT nota, data FROM eventi WHERE id=? AND nota LIKE '%SOMM%'", (p_id,))
firme_dict = {} # Chiave: (farmaco, giorno, turno) -> Valore: A o R
for f_nota, f_data in firme_mese:
    try:
        g = int(f_data.split("/")[0])
        # Estraggo farmaco e esito dalla stringa nota
        parti = f_nota.split(":")
        f_nome_estratto = parti[1].split("|")[0].strip()
        esito = f_nota.split("|")[-1].strip()
        turno_estratto = parti[0].split("(")[1].split(")")[0]
        firme_dict[(f_nome_estratto, g, turno_estratto)] = esito
    except: continue

def genera_blocco(titolo, lista_farmaci, turno_label):
    if not lista_farmaci: return
    
    st.markdown(f"<div class='header-turno'>{titolo}</div>", unsafe_allow_html=True)
    
    html = f"<div class='scroll-container'><table class='terapia-table'><thead><tr><th class='sticky-col'>Farmaco / Giorno</th>"
    for d in range(1, num_giorni + 1):
        # Evidenzio il giorno corrente
        bg = "#ffffcc" if d == oggi.day else "white"
        html += f"<th style='background:{bg}'>{d}</th>"
    html += "</tr></thead><tbody>"
    
    for f in lista_farmaci:
        html += f"<tr><td class='sticky-col'>{f[1]} <br><small>{f[2]}</small></td>"
        for d in range(1, num_giorni + 1):
            key = (f[1], d, turno_label)
            if key in firme_dict:
                colore = "#dcfce7" if firme_dict[key] == "A" else "#fee2e2"
                testo = f"<b style='color:{'green' if firme_dict[key]=='A' else 'red'}'>{firme_dict[key]}</b>"
                html += f"<td style='background:{colore}'>{testo}</td>"
            else:
                # Per il giorno corrente mostriamo i bottoni (simulati come link per Streamlit)
                if d == oggi.day:
                    # Nota: Streamlit non permette bottoni veri dentro HTML iniettato.
                    # Qui usiamo un trucco: usiamo i bottoni di Streamlit fuori o gestiamo il click
                    html += "<td>...</td>" # In una versione reale useremmo st.columns
                else:
                    html += "<td> </td>"
        html += "</tr>"
    
    html += "</tbody></table></div>"
    st.markdown(html, unsafe_allow_html=True)
    
    # Inserisco i bottoni reali di Streamlit sotto la tabella per il giorno corrente
    cols = st.columns(len(lista_farmaci))
    for idx, f in enumerate(lista_farmaci):
        key_check = (f[1], oggi.day, turno_label)
        if key_check not in firme_dict:
            with cols[idx]:
                st.write(f"**{f[1]}**")
                c_a, c_r = st.columns(2)
                if c_a.button("A", key=f"A_{f[0]}_{turno_label}"): firma(p_id, f[0], f[1], turno_label, oggi.day, "A")
                if c_r.button("R", key=f"R_{f[0]}_{turno_label}"): firma(p_id, f[0], f[1], turno_label, oggi.day, "R")

# --- DIVISIONE FARMACI ---
mat_f = [f for f in farmaci if f[3] == 1]
pom_f = [f for f in farmaci if f[4] == 1]
not_f = [f for f in farmaci if f[5] == 1]
tab_f = [f for f in farmaci if f[6] == 1]

# --- RENDERING ---
genera_blocco("☀️ MATTINO", mat_f, "MAT")
st.write(" ") 
genera_blocco("⛅ POMERIGGIO", pom_f, "POM")
st.write(" ")
genera_blocco("🌙 NOTTE", not_f, "NOT")
st.write(" ")
genera_blocco("🆘 TAB (Al Bisogno)", tab_f, "TAB")
