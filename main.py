import sqlite3
import streamlit as st
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
