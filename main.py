import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date

# --- 1. CONFIGURAZIONE & STILE ---
st.set_page_config(page_title="REMS Connect PRO", layout="wide")

st.markdown("""
<style>
    .main-title {text-align: center; color: #1e3a8a; font-weight: bold; margin-bottom:20px;}
    .custom-table {width: 100%; border-collapse: collapse; font-size: 0.85rem; background: white;}
    .custom-table th {background-color: #1e3a8a; color: white; padding: 10px; text-align: left; border: 1px solid #dee2e6;}
    .custom-table td {padding: 10px; border: 1px solid #dee2e6; vertical-align: middle;}
    .badge-m { background: #dcfce7; color: #166534; padding: 2px 6px; border-radius: 4px; font-weight: bold; border: 1px solid #166534; margin-right:2px;}
    .status-ok { color: #10b981; font-weight: bold; border: 1px solid #10b981; padding: 2px 5px; border-radius: 4px; background: #f0fdf4; }
    .card-box { border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; margin-bottom: 10px; background: #ffffff; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .saldo-box { padding: 15px; border-radius: 10px; background-color: #f8fafc; text-align: center; border: 2px solid #1e3a8a; }
</style>
""", unsafe_allow_html=True)

# --- 2. FUNZIONI DATABASE ---
DB_NAME = "rems_connect_data.db"

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY, nome TEXT, giorno_lavatrice TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, umore TEXT, nota TEXT, ruolo TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dosaggio TEXT, turni TEXT, medico TEXT, data_prescr TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS soldi (p_id INTEGER, data TEXT, desc TEXT, importo REAL, tipo TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        if query: cur.execute(query, params)
        if commit: conn.commit()
        return cur.fetchall()

GIORNI = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]

# --- 3. LOGIN ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.markdown("<h1 class='main-title'>REMS CONNECT PRO</h1>", unsafe_allow_html=True)
    with st.form("login"):
        pwd = st.text_input("Codice Accesso", type="password")
        if st.form_submit_button("ENTRA"):
            if pwd in ["rems2026", "admin2026"]:
                st.session_state.auth = True
                st.rerun()
    st.stop()

# --- 4. NAVIGAZIONE ---
menu = st.sidebar.radio("NAVIGAZIONE", ["Monitoraggio", "Equipe", "Gestione"])

if menu == "Equipe":
    figura = st.sidebar.selectbox("Ruolo", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
    paz_data = db_run("SELECT id, nome, giorno_lavatrice FROM pazienti ORDER BY nome")
    
    if paz_data:
        sel_p_nome = st.selectbox("Seleziona Paziente", [p[1] for p in paz_data])
        p_id = [p[0] for p in paz_data if p[1] == sel_p_nome][0]
        g_lav = [p[2] for p in paz_data if p[1] == sel_p_nome][0]
        st.divider()

        # --- SEZIONE PSICHIATRA (RIPRISTINATA) ---
        if figura == "Psichiatra":
            st.subheader("📋 Gestione Terapie (Prescrizione)")
            with st.form("presc_form"):
                c1, c2 = st.columns(2)
                f = c1.text_input("Farmaco")
                d = c2.text_input("Dosaggio")
                st.write("Orari Somministrazione (Turni):")
                ct1, ct2, ct3 = st.columns(3)
                tm = ct1.checkbox("Mattina (M)")
                tp = ct2.checkbox("Pomeriggio (P)")
                tn = ct3.checkbox("Notte (N)")
                medico = st.text_input("Medico Prescrittore")
                if st.form_submit_button("REGISTRA VARIAZIONE TERAPIA"):
                    t_list = [s for s, b in zip(["M", "P", "N"], [tm, tp, tn]) if b]
                    db_run("INSERT INTO terapie (p_id, farmaco, dosaggio, turni, medico, data_prescr) VALUES (?,?,?,?,?,?)", 
                           (p_id, f, d, ",".join(t_list), medico, datetime.now().strftime("%d/%m/%y %H:%M")), True)
                    st.success("Terapia aggiornata!"); st.rerun()

            st.write("#### 💊 Terapie Attualmente in Vigore")
            terapie = db_run("SELECT data_prescr, farmaco, dosaggio, turni, medico, row_id FROM terapie WHERE p_id=? ORDER BY row_id DESC", (p_id,))
            if terapie:
                h = "<table class='custom-table'><tr><th>DATA</th><th>FARMACO</th><th>DOSAGGIO</th><th>TURNI</th><th>MEDICO</th><th>AZIONE</th></tr>"
                for da, fa, do, tu, me, rid in terapie:
                    h += f"<tr><td>{da}</td><td><b>{fa}</b></td><td>{do}</td><td><span class='badge-m'>{tu}</span></td><td>{me}</td><td>---</td></tr>"
                st.markdown(h + "</table>", unsafe_allow_html=True)
                with st.expander("Sospendi Farmaci"):
                    for da, fa, do, tu, me, rid in terapie:
                        if st.button(f"Sospendi {fa}", key=f"sosp_{rid}"):
                            db_run("DELETE FROM terapie WHERE row_id=?", (rid,), True)
                            db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", 
                                   (p_id, datetime.now().strftime("%d/%m/%y %H:%M"), "Stabile", f"❌ SOSPESO: {fa}", "Psichiatra", medico), True)
                            st.rerun()

        # --- SEZIONE INFERMIERE (RIPRISTINATA) ---
        elif figura == "Infermiere":
            st.subheader("💉 Somministrazione Terapia")
            col1, col2 = st.columns(2)
            d_op = col1.date_input("Data", date.today())
            t_op = col2.selectbox("Turno", ["Mattina", "Pomeriggio", "Notte"])
            sigla = t_op[0]
            firma = st.text_input("Firma Infermiere")
            
            st.write(f"**Elenco farmaci previsti per il turno {t_op}:**")
            terapie = db_run("SELECT farmaco, dosaggio, turni, row_id FROM terapie WHERE p_id=?", (p_id,))
            
            for f, d, tu_f, rid in terapie:
                if tu_f and sigla in tu_f:
                    tag = f"[REP_{sigla}] {f}"
                    data_s = d_op.strftime("%d/%m/%Y")
                    check = db_run("SELECT op, nota FROM eventi WHERE id=? AND nota LIKE ? AND data LIKE ?", (p_id, f"%{tag}%", f"{data_s}%"))
                    
                    st.markdown("<div class='card-box'>", unsafe_allow_html=True)
                    c1, c2, c3 = st.columns([2, 2, 1])
                    c1.markdown(f"**{f}**<br><small>{d}</small>", unsafe_allow_html=True)
                    
                    if check:
                        esito = check[0][1].split("->")[-1]
                        c2.markdown(f"<span class='status-ok'>✅ {esito} (Firmato: {check[0][0]})</span>", unsafe_allow_html=True)
                    else:
                        scelta = c2.radio("Stato:", ["Assunta", "Rifiutata", "Parziale"], key=f"inf_{rid}_{sigla}", horizontal=True)
                        if c3.button("CONVALIDA", key=f"btn_{rid}_{sigla}"):
                            if firma:
                                db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", 
                                       (p_id, f"{data_s} {datetime.now().strftime('%H:%M')}", "Stabile", f"{tag} -> {scelta}", "Infermiere", firma), True)
                                st.rerun()
                            else: st.error("Inserire la firma")
                    st.markdown("</div>", unsafe_allow_html=True)

        # --- SEZIONE OSS ---
        elif figura == "OSS":
            st.subheader("🧹 Mansioni OSS")
            oggi_sett = GIORNI[date.today().weekday()]
            if g_lav == oggi_sett:
                st.info(f"🧺 OGGI È IL TURNO LAVATRICE DI {sel_p_nome.upper()}")
            
            with st.form("oss_f"):
                c1, c2 = st.columns(2)
                t1 = c1.checkbox("Pulizia Stanza")
                t2 = c1.checkbox("Pulizia Sale Fumo")
                t3 = c2.checkbox("Pulizia Refettorio")
                t4 = c2.checkbox("Lavatrice")
                f_oss = st.text_input("Firma OSS")
                if st.form_submit_button("REGISTRA"):
                    comp = [t for b, t in zip([t1,t2,t3,t4], ["Stanza", "Fumo", "Refettorio", "Lavatrice"]) if b]
                    db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", 
                           (p_id, datetime.now().strftime("%d/%m/%y %H:%M"), "Stabile", f"🧹 [OSS] {', '.join(comp)}", "OSS", f_oss), True)
                    st.success("Fatto!")

        # --- SEZIONE EDUCATORI ---
        elif figura == "Educatore":
            st.subheader("💰 Gestione Soldi")
            # ... (Logica saldo e movimenti come prima)
            movs = db_run("SELECT importo, tipo FROM soldi WHERE p_id=?", (p_id,))
            saldo = sum([m[0] if m[1] == "Entrata" else -m[0] for m in movs])
            st.markdown(f'<div class="saldo-box">Saldo: € {saldo:.2f}</div>', unsafe_allow_html=True)
            with st.expander("Nuovo Movimento"):
                tm = st.radio("Tipo", ["Entrata", "Uscita"], horizontal=True)
                im = st.number_input("Importo", min_value=0.0)
                ca = st.text_input("Causale")
                fi = st.text_input("Firma")
                if st.button("SALVA MOVIMENTO"):
                    db_run("INSERT INTO soldi (p_id, data, desc, importo, tipo, op) VALUES (?,?,?,?,?,?)", 
                           (p_id, date.today().strftime("%d/%m/%Y"), ca, im, tm, fi), True); st.rerun()

# --- MONITORAGGIO ---
elif menu == "Monitoraggio":
    for p_id, nome, g in db_run("SELECT id, nome, giorno_lavatrice FROM pazienti ORDER BY nome"):
        with st.expander(f"👤 {nome.upper()} (Lavatrice: {g})"):
            note = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY row_id DESC", (p_id,))
            if note:
                h = "<table class='custom-table'><tr><th>DATA</th><th>RUOLO</th><th>OPERATORE</th><th>NOTA</th></tr>"
                for d, ru, op, nt in note:
                    bg = "#f0fdf4" if "REP_" in nt else ("#fff1f2" if "❌" in nt else "white")
                    h += f"<tr style='background:{bg}'><td>{d}</td><td>{ru}</td><td>{op}</td><td>{nt}</td></tr>"
                st.markdown(h + "</table>", unsafe_allow_html=True)

# --- GESTIONE ---
elif menu == "Gestione":
    st.subheader("⚙️ Configurazione Sistema")
    n_p = st.text_input("Nome Nuovo Paziente")
    g_l = st.selectbox("Giorno Lavatrice", GIORNI[:6])
    if st.button("AGGIUNGI PAZIENTE"):
        db_run("INSERT INTO pazienti (nome, giorno_lavatrice) VALUES (?,?)", (n_p, g_l), True); st.rerun()
