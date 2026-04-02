import sqlite3
import streamlit as st
from datetime import datetime, timedelta, timezone
import hashlib
import pandas as pd
import calendar

# --- FUNZIONE ORARIO ITALIA (UTC+2) ---
def get_now_it():
    return datetime.now(timezone.utc) + timedelta(hours=2)

# --- CONFIGURAZIONE INTERFACCIA ELITE PRO v28.9.1 ---
st.set_page_config(page_title="REMS Connect ELITE PRO", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #1e3a8a !important; }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    .sidebar-title { color: #ffffff !important; font-size: 1.8rem !important; font-weight: 800 !important; text-align: center; margin-bottom: 1rem; padding-top: 10px; border-bottom: 2px solid #ffffff33; }
    .user-logged { color: #00ff00 !important; font-weight: 900; font-size: 1.1rem; text-transform: uppercase; margin-bottom: 20px; text-align: center; }
    .section-banner { background-color: #1e3a8a; color: white !important; padding: 25px; border-radius: 12px; margin-bottom: 30px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.3); border: 1px solid #ffffff22; }
    
    /* STILI TABELLA AGENDA HTML */
    .cal-table { width:100%; border-collapse: collapse; table-layout: fixed; background: white; border-radius: 12px; overflow: visible; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    .cal-table th { background: #f1f5f9; padding: 10px; color: #1e3a8a; font-weight: 800; border: 1px solid #e2e8f0; font-size: 0.85rem; }
    .cal-table td { border: 1px solid #e2e8f0; vertical-align: top; height: 120px; padding: 5px; position: relative; overflow: visible; }
    .day-num-html { font-weight: 900; color: #64748b; font-size: 0.8rem; margin-bottom: 4px; display: block; }
    
    /* --- SISTEMA TOOLTIP (POP-UP ALL'HOVER) - CORRETTO PER NON TAGLIARE --- */
    .event-tag-html { 
        font-size: 0.7rem; background: #dbeafe; color: #1e40af; padding: 4px 6px; 
        border-radius: 4px; margin-bottom: 4px; border-left: 3px solid #2563eb; 
        line-height: 1.2; position: relative; cursor: help; display: block;
    }
    .event-tag-html .tooltip-text {
        visibility: hidden; width: 220px; background-color: #1e3a8a; color: #fff;
        text-align: left; border-radius: 8px; padding: 12px; position: absolute;
        z-index: 9999; top: 110%; left: 10px; opacity: 0;
        transition: opacity 0.2s; box-shadow: 0 8px 20px rgba(0,0,0,0.4);
        font-size: 0.75rem; line-height: 1.4; white-space: normal; border: 1px solid #ffffff44;
    }
    .event-tag-html:hover { background: #bfdbfe; }
    .event-tag-html:hover .tooltip-text { visibility: visible; opacity: 1; }

    .today-html { background-color: #f0fdf4 !important; border: 2px solid #22c55e !important; }
    .postit { padding: 15px; border-radius: 8px; margin-bottom: 12px; border-left: 10px solid; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); color: #1e293b; background-color: #ffffff; }
    
    /* Ruoli e colori post-it */
    .role-psichiatra { background-color: #fef2f2; border-color: #dc2626; } 
    .role-infermiere { background-color: #eff6ff; border-color: #2563eb; } 
    .role-educatore { background-color: #ecfdf5; border-color: #059669; }  
    .role-oss { background-color: #f8fafc; border-color: #64748b; }
</style>
""", unsafe_allow_html=True)

# --- DATABASE ENGINE ---
DB_NAME = "rems_final_v12.db"
def hash_pw(p): return hashlib.sha256(str.encode(p)).hexdigest()

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute(query, params)
        if commit: conn.commit()
        return cur.fetchall()

# --- SESSIONE E LOGIN ---
if 'user_session' not in st.session_state: st.session_state.user_session = None
if 'cal_month' not in st.session_state: st.session_state.cal_month = get_now_it().month
if 'cal_year' not in st.session_state: st.session_state.cal_year = get_now_it().year

if not st.session_state.user_session:
    # (Logica login semplificata per brevità, usa la tua esistente)
    st.title("🏥 REMS CONNECT - Login")
    u_i = st.text_input("User").lower()
    p_i = st.text_input("Pass", type="password")
    if st.button("Accedi"):
        res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u_i, hash_pw(p_i)))
        if res: st.session_state.user_session = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2], "uid": u_i}; st.rerun()
    st.stop()

u = st.session_state.user_session
firma_op = f"{u['nome']} {u['cognome']} ({u['ruolo']})"
oggi_iso = get_now_it().strftime("%Y-%m-%d")

# --- SIDEBAR E NAVIGAZIONE ---
nav = st.sidebar.radio("NAVIGAZIONE", ["📊 Monitoraggio", "👥 Modulo Equipe", "📅 Agenda Dinamica", "🗺️ Mappa Posti Letto"])

# --- AGENDA DINAMICA (CORRETTA) ---
if nav == "📅 Agenda Dinamica":
    st.markdown("<div class='section-banner'><h2>AGENDA DINAMICA REMS</h2></div>", unsafe_allow_html=True)
    
    # Navigazione Mesi
    c_nav1, c_nav2, c_nav3 = st.columns([1,2,1])
    with c_nav1: 
        if st.button("⬅️ Mese Precedente"): 
            st.session_state.cal_month -= 1
            if st.session_state.cal_month < 1: st.session_state.cal_month=12; st.session_state.cal_year-=1
            st.rerun()
    with c_nav2: 
        mesi_nomi = ["Gennaio","Febbraio","Marzo","Aprile","Maggio","Giugno","Luglio","Agosto","Settembre","Ottobre","Novembre","Dicembre"]
        st.markdown(f"<h3 style='text-align:center;'>{mesi_nomi[st.session_state.cal_month-1]} {st.session_state.cal_year}</h3>", unsafe_allow_html=True)
    with c_nav3:
        if st.button("Mese Successivo ➡️"):
            st.session_state.cal_month += 1
            if st.session_state.cal_month > 12: st.session_state.cal_month=1; st.session_state.cal_year+=1
            st.rerun()

    col_cal, col_ins = st.columns([3, 1.2])
    
    with col_cal:
        start_d = f"{st.session_state.cal_year}-{st.session_state.cal_month:02d}-01"
        end_d = f"{st.session_state.cal_year}-{st.session_state.cal_month:02d}-31"
        
        # Recupero eventi
        evs_mese = db_run("""
            SELECT a.data, p.nome, a.ora, a.tipo_evento, a.mezzo, a.nota, a.accompagnatore 
            FROM appuntamenti a 
            JOIN pazienti p ON a.p_id=p.id 
            WHERE a.data BETWEEN ? AND ? AND a.stato='PROGRAMMATO'
        """, (start_d, end_d))
        
        mappa_ev = {}
        for d_ev, p_n, h_ev, t_ev, m_ev, nt_ev, acc_ev in evs_mese:
            try:
                g_int = int(d_ev.split("-")[2])
                if g_int not in mappa_ev: mappa_ev[g_int] = []
                prefix = "🚗" if t_ev == "Uscita Esterna" else "🏠"
                
                # HTML DEL POP-UP (Usa triple virgolette f''' per evitare errori JS/HTML)
                info_popup = f"<b>{t_ev}</b><br>⏰ Ora: {h_ev}<br>👤 Paz: {p_n}<br>🚗 Mezzo: {m_ev}<br>🤝 Accomp: {acc_ev}<br>📝 Note: {nt_ev}"
                
                tag_final = f'''<div class="event-tag-html">{prefix} {p_n}<span class="tooltip-text">{info_popup}</span></div>'''
                
                mappa_ev[g_int].append(tag_final)
            except: pass

        # Costruzione Tabella Calendario
        cal_html = "<table class='cal-table'><thead><tr>"
        for d_nome in ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]:
            cal_html += f"<th>{d_nome}</th>"
        cal_html += "</tr></thead><tbody>"
        
        cal_obj = calendar.Calendar(firstweekday=0)
        for week in cal_obj.monthdayscalendar(st.session_state.cal_year, st.session_state.cal_month):
            cal_html += "<tr>"
            for day in week:
                if day == 0:
                    cal_html += "<td style='background:#f8fafc;'></td>"
                else:
                    d_iso = f"{st.session_state.cal_year}-{st.session_state.cal_month:02d}-{day:02d}"
                    cls_today = "today-html" if d_iso == oggi_iso else ""
                    g_evs = mappa_ev.get(day, [])
                    html_evs = "".join(g_evs)
                    cal_html += f"<td class='{cls_today}'><span class='day-num-html'>{day}</span>{html_evs}</td>"
            cal_html += "</tr>"
        cal_html += "</tbody></table>"
        st.markdown(cal_html, unsafe_allow_html=True)

    with col_ins:
        st.subheader("➕ Inserimento")
        with st.form("add_app"):
            p_l = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
            ps_sel = st.selectbox("Paziente", [p[1] for p in p_l])
            tipo_e = st.selectbox("Tipo", ["Uscita Esterna", "Appuntamento Interno"])
            dat = st.date_input("Data")
            ora = st.time_input("Ora")
            mez = st.selectbox("Mezzo", ["Nessuno", "Mitsubishi", "Fiat Qubo"])
            acc = st.text_input("Accompagnatore")
            not_a = st.text_area("Note")
            if st.form_submit_button("REGISTRA"):
                pid = [p[0] for p in p_l if p[1]==ps_sel][0]
                db_run("INSERT INTO appuntamenti (p_id, data, ora, nota, stato, autore, tipo_evento, mezzo, accompagnatore) VALUES (?,?,?,?,'PROGRAMMATO',?,?,?,?)", 
                       (pid, str(dat), str(ora)[:5], not_a, firma_op, tipo_e, mez, acc), True)
                st.success("Registrato!"); st.rerun()

# --- (Il resto delle sezioni Equipe, Monitoraggio e Mappa rimane invariato) ---
