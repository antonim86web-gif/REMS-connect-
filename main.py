# --- FUNZIONE GENERALE PER I BLOCCHI ---
def genera_blocco_mensile(p_id, farmaci, turno_target, titolo):
    # Filtro i farmaci per il turno
    if turno_target == "TAB":
        f_turno = [f for f in farmaci if len(f) > 6 and f[6] == 1]
    else:
        mappa = {"MAT": 3, "POM": 4, "NOT": 5}
        idx = mappa[turno_target]
        f_turno = [f for f in farmaci if len(f) > idx and f[idx] == 1]

    if not f_turno:
        return # Se non c'è nulla, non mostriamo il blocco

    st.markdown(f"#### {titolo}")
    
    # CSS per la tabella a scorrimento
    st.markdown("""
        <style>
            .scroll-box { overflow-x: auto; border: 1px solid #ddd; border-radius: 5px; margin-bottom: 20px; }
            .m-table { border-collapse: collapse; width: 100%; font-size: 11px; }
            .m-table th, .m-table td { border: 1px solid #eee; padding: 5px; text-align: center; min-width: 30px; }
            .f-name { position: sticky; left: 0; background: #fdfdfd; z-index: 5; min-width: 130px !important; text-align: left !important; font-weight: bold; }
            .today-col { background-color: #fffde7 !important; }
        </style>
    """, unsafe_allow_html=True)

    oggi = datetime.now()
    giorni_mese = calendar.monthrange(oggi.year, oggi.month)[1]
    
    # Intestazione Giorni
    header = "".join([f"<th class='{'today-col' if d == oggi.day else ''}'>{d}</th>" for d in range(1, giorni_mese + 1)])
    html = f"<div class='scroll-box'><table class='m-table'><thead><tr><th class='f-name'>Farmaco</th>{header}</tr></thead><tbody>"
    
    for f in f_turno:
        id_f, nome_f = f[0], f[1]
        righe_giorni = ""
        
        # Recupero firme del mese
        mese_str = oggi.strftime("%m/%Y")
        firme = db_run("SELECT data, esito FROM eventi WHERE id=? AND nota LIKE ? AND data LIKE ?", 
                       (p_id, f"%{turno_target}: {nome_f}%", f"%/{mese_str}%"))
        
        firme_dict = {int(d[0].split("/")[0]): d[1] for d in firme if d[1]}

        for d in range(1, giorni_mese + 1):
            esito = firme_dict.get(d, "")
            col = "green" if esito == "A" else "red"
            is_today = "today-col" if d == oggi.day else ""
            righe_giorni += f"<td class='{is_today}' style='color:{col}; font-weight:bold;'>{esito}</td>"
        
        html += f"<tr><td class='f-name'>{nome_f}</td>{righe_giorni}</tr>"
    
    html += "</tbody></table></div>"
    st.markdown(html, unsafe_allow_html=True)

    # --- BOTTONI FIRMA (Solo per oggi) ---
    st.caption(f"Firma rapida per oggi")
    bt_cols = st.columns(len(f_turno))
    for i, f in enumerate(f_turno):
        with bt_cols[i]:
            if oggi.day in firme_dict:
                st.write(f"✅ {f[1]}")
            else:
                c_a, c_r = st.columns(2)
                if c_a.button("A", key=f"A_{f[0]}_{turno_target}"):
                    registra_firma(p_id, f[1], turno_target, "A")
                if c_r.button("R", key=f"R_{f[0]}_{turno_target}"):
                    registra_firma(p_id, f[1], turno_target, "R")

def registra_firma(p_id, farmaco, turno, esito):
    ora = datetime.now().strftime("%d/%m/%Y %H:%M")
    nota = f"✔️ SOMM ({turno}): {farmaco}"
    op = st.session_state.user_session['uid'] if 'user_session' in st.session_state else "Op"
    db_run("INSERT INTO eventi (id, data, nota, ruolo, op, esito) VALUES (?,?,?,?,?,?)", 
           (p_id, ora, nota, "Infermiere", op, esito), True)
    st.rerun()

# --- NEL MODULO INFERMIERE ---
farmaci = db_run("SELECT id_u, farmaco, dose, mat, pom, nott, is_prn FROM terapie WHERE p_id=?", (p_id,))
if farmaci:
    genera_blocco_mensile(p_id, farmaci, "MAT", "☀️ MATTINO")
    genera_blocco_mensile(p_id, farmaci, "POM", "⛅ POMERIGGIO")
    genera_blocco_mensile(p_id, farmaci, "NOT", "🌙 NOTTE")
    genera_blocco_mensile(p_id, farmaci, "TAB", "🆘 TAB (Al Bisogno)")
