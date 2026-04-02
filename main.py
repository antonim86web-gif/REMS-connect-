,?,?,?)", (pid, str(dat), str(ora)[:5], not_a, firma_op, tipo_e, mezzo_usato, accomp), True)
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (pid, get_now_it().strftime("%d/%m/%Y %H:%M"), f"📅 {tipo_e}: {not_a}", u['ruolo'], firma_op), True)
                st.rerun()

elif nav == "⚙️ Admin":
    st.markdown("<div class='section-banner'><h2>PANNELLO AMMINISTRAZIONE</h2></div>", unsafe_allow_html=True)
    t_ut, t_paz_att, t_paz_dim, t_diar, t_log = st.tabs(["UTENTI", "PAZIENTI ATTIVI", "ARCHIVIO DIMESSI", "DIARIO EVENTI", "📜 LOG SISTEMA"])
    
    with t_ut:
        for us, un, uc, uq in db_run("SELECT user, nome, cognome, qualifica FROM utenti"):
            c1, c2 = st.columns([0.8, 0.2]); c1.write(f"**{un} {uc}** ({uq})")
            if us != "admin" and c2.button("ELIMINA", key=f"d_{us}"): 
                db_run("DELETE FROM utenti WHERE user=?", (us,), True)
                st.rerun()

    with t_paz_att:
        with st.form("np"):
            np_val = st.text_input("Nuovo Paziente")
            if st.form_submit_button("AGGIUNGI"): 
                db_run("INSERT INTO pazienti (nome, stato) VALUES (?, 'ATTIVO')", (np_val.upper(),), True)
                st.rerun()
        for pid, pn in db_run("SELECT id, nome FROM pazienti WHERE stato='ATTIVO' ORDER BY nome"):
            c1, c2, c3 = st.columns([0.6, 0.2, 0.2]); c1.write(f"**{pn}**")
            if c2.button("DIMETTI", key=f"dim_{pid}"):
                db_run("UPDATE pazienti SET stato='DIMESSO' WHERE id=?", (pid,), True)
                db_run("DELETE FROM assegnazioni WHERE p_id=?", (pid,), True)
                st.rerun()
            if c3.button("ELIMINA", key=f"dp_{pid}"): 
                db_run("DELETE FROM pazienti WHERE id=?", (pid,), True)
                st.rerun()

    with t_paz_dim:
        for pid, pn in db_run("SELECT id, nome FROM pazienti WHERE stato='DIMESSO' ORDER BY nome"):
            c1, c2 = st.columns([0.8, 0.2]); c1.write(f"📁 {pn} (Dimesso)")
            if c2.button("RIAMMETTI", key=f"re_{pid}"):
                db_run("UPDATE pazienti SET stato='ATTIVO' WHERE id=?", (pid,), True)
                st.rerun()

    with t_diar:
        lista_p = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
        filtro_p = st.selectbox("Filtra per Paziente:", ["TUTTI"] + [p[1] for p in lista_p])
        query_log = "SELECT e.id_u, e.data, e.ruolo, e.op, e.nota, p.nome FROM eventi e JOIN pazienti p ON e.id = p.id"
        params_log = []
        if filtro_p != "TUTTI": query_log += " WHERE p.nome = ?"; params_log.append(filtro_p)
        tutti_log = db_run(query_log + " ORDER BY e.id_u DESC LIMIT 100", tuple(params_log))
        for lid, ldt, lru, lop, lnt, lpnome in tutti_log:
            st.text(f"[{ldt}] {lpnome} | {lop} ({lru}): {lnt}")

    with t_log:
        logs_audit = db_run("SELECT data_ora, utente, azione, dettaglio FROM logs_sistema ORDER BY id_log DESC LIMIT 200")
        if logs_audit:
            df_audit = pd.DataFrame(logs_audit, columns=["Data/Ora", "Operatore", "Azione", "Descrizione"])
            st.dataframe(df_audit, use_container_width=Tru
