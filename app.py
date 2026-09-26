import os
import pandas as pd
import streamlit as st
import io
import requests

# --- CONEXIÓN DIRECTA Y PERMANENTE A GOOGLE SHEETS MUNICIPAL ---
# Extraemos el ID único de tu hoja real de cálculo de Sunchales
SPREADSHEET_ID = "1r6izG5X1gil8MaZA1zD-WW2T1BA5mSC1Yq9-R663azU"

# Enlaces de conexión directa para lectura en formato CSV nativo de Google Drive
URL_READ_EGRESOS = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet=egresos"
URL_READ_DESTINOS = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet=destinos"

# Macros de envío web directo para simular la inserción de filas (Formulario)
def leer_datos_gsheet(url_tipo):
    try:
        # Forzamos la descarga del CSV en tiempo real para evitar la caché de Google
        return pd.read_csv(url_tipo + f"&cache_bust={os.urandom(4).hex()}")
    except:
        return pd.DataFrame()

def guardar_fila_gsheet(hoja, diccionario_datos):
    try:
        macro_url = st.secrets["GSHEET_MACRO_URL"]
        paquete_web = {"hoja": hoja, "datos": diccionario_datos}
        # Enviamos los datos por internet en tiempo real hacia tu Apps Script
        requests.post(macro_url, json=paquete_web)
    except Exception as e:
        st.error(f"Error de sincronización con Drive: {e}")

    # Pasarela puente de comunicación Streamlit -> Google Sheet en formato CSV string descriptor
    url_append = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/echo"
    # Por el momento inicializamos el buffer de lectura local integrado
    if "db_local_backup" not in st.session_state:
        st.session_state["db_local_backup"] = {"egresos": [], "destinos": []}
    st.session_state["db_local_backup"][hoja].append(diccionario_datos)

st.set_page_config(layout="wide", page_title="Homero Presupuesto", page_icon="🍩")
st.title("🍩 Homero - Sistema de Registro Presupuestario")
st.write("📍 Municipalidad de Sunchales | Conexión Cooperativa a Google Sheets 2027")

# --- Plan de Cuentas Oficial Municipal ---
MAPEO_GASTOS = {
    "2. Bienes de consumo": {
        "22.5.0.0.00.000 - Productos químicos, combustibles y lubricantes": ["22.5.5.0.00.000 - Tintas, Pinturas y Colorantes"],
        "22.6.0.0.00.000 - Productos minerales no metálicos": ["22.6.5.0.00.000 - Productos de Cemento, Cal y Yeso"],
        "22.8.0.0.00.000 - Minerales": ["22.8.4.0.00.000 - Piedra, Arcilla y Arena"],
        "22.9.0.0.00.000 - Otros bienes de consumo": ["22.9.3.0.00.000 - Útiles y materiales eléctricos", "22.9.6.0.00.000 - Repuestos y accesorios"]
    },
    "3. Services": {
        "23.3.0.0.00.000 - Mantenimiento, reparación y limpieza": ["23.3.1.0.00.000 - Mantenimiento y reparación de edificios y locales"]
    },
    "21.0.0.0.00.000 - Gastos de Personal": {
        "21.1.0.0.00.000 - Personal Permanente": ["21.1.1.0.00.000 - Retribución del Cargo", "21.1.4.0.00.000 - SAC"]
    }
}

MAPEO_ESTRUCTURA = {
    "AGENCIA MUNICIPAL DE SEGURIDAD": ["AGENCIA MUNICIPAL DE SEGURIDAD"],
    "SECRETARÍA DE GESTIÓN AMBIENTAL Y TERRITORIAL": ["SUBSECRETARÍA DE OBRAS", "SUBSECRETARÍA DE AMBIENTE Y ACCIÓN CLIMÁTICA"],
    "SECRETARÍA DE GOBIERNO": ["SUBSECRETARÍA DE GESTIÓN Y DESARROLLO"],
    "SECRETARÍA DE DESARROLLO Y PROMOCIÓN DE DDHH": ["SUBSECRETARÍA DE PROMOCIÓN DE DDHH"],
    "INTENDENCIA": ["INTENDENCIA"],
    "HCD": ["HCD"]
}

opciones_secretarias = list(MAPEO_ESTRUCTURA.keys())
opciones_objetos = list(MAPEO_GASTOS.keys())
opciones_fuente_fin = ["Municipal", "Provincial", "Nacional"]
opciones_clase = ["Corriente", "Capital"]
opciones_tipo = ["Libre", "Afectado"]
opciones_finalidad = ["Legislativa", "Salud", "Seguridad"]

tab_formulario, tab_agregar_destino, tab_egresos, tab_oficial = st.tabs([
    "📝 FORMULARIO DE REGISTRO", 
    "➕ GESTIÓN DE DESTINOS",
    "📉 GENERAL (Base de Datos Sheet)",
    "🏛️ REPORTE OFICIAL POR DESTINO"
])


# Inicialización de la persistencia de respaldo en memoria local coordinada
if "db_local_backup" not in st.session_state:
    st.session_state["db_local_backup"] = {"egresos": [], "destinos": []}

# =====================================================================
# PESTAÑA 1: FORMULARIO PRINCIPAL DE REGISTRO
# =====================================================================
with tab_formulario:
    st.subheader("📥 Cargar Nuevo Renglón Presupuestario")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**📍 1. Ubicación Institucional**")
        f_sec = st.selectbox("SECRETARÍA:", options=[""] + opciones_secretarias, format_func=lambda x: "--- Seleccioná ---" if x == "" else x, key="reg_sec")
        
        if f_sec != "":
            f_sub = st.selectbox("SUBSECRETARÍA:", options=[""] + MAPEO_ESTRUCTURA[f_sec], format_func=lambda x: "--- Seleccioná ---" if x == "" else x, key="reg_sub")
            if f_sub != "":
                # Lectura combinada desde Google Sheets y memoria local
                df_dest_gsheet = leer_datos_gsheet(URL_READ_DESTINOS)
                lista_d = []
                if not df_dest_gsheet.empty and "destino" in df_dest_gsheet.columns:
                    df_fil = df_dest_gsheet[(df_dest_gsheet["secretaria"] == f_sec) & (df_dest_gsheet["subsecretaria"] == f_sub)]
                    lista_d = df_fil["destino"].dropna().astype(str).tolist()
                
                # Sumamos lo acumulado localmente en la sesión actual
                for d_loc in st.session_state["db_local_backup"]["destinos"]:
                    if d_loc["secretaria"] == f_sec and d_loc["subsecretaria"] == f_sub:
                        if d_loc["destino"] not in lista_d:
                            lista_d.append(d_loc["destino"])
                            
                f_dest = st.selectbox("DESTINO SELECCIONADO:", options=[""] + lista_d, format_func=lambda x: "--- Seleccioná ---" if x == "" else str(x).upper(), key="reg_dest") if lista_d else None
                if not lista_d: st.warning("⚠️ Sin destinos creados. Cargalo en la pestaña contigua.")
            else: f_dest = None
        else: f_sub, f_dest = "", None
        
    with col2:
        st.markdown("**📊 2. Imputación de Partida**")
        f_obj = st.selectbox("OBJETO DE GASTO:", options=[""] + opciones_objetos, format_func=lambda x: "--- Seleccioná ---" if x == "" else x, key="reg_obj")
        if f_obj != "":
            f_padre = st.selectbox("CUENTA PADRE:", options=[""] + list(MAPEO_GASTOS[f_obj].keys()), format_func=lambda x: "--- Seleccioná ---" if x == "" else x, key="reg_padre")
            f_presup = st.selectbox("CUENTA DE IMPUTACIÓN / PARTIDA:", options=[""] + MAPEO_GASTOS[f_obj][f_padre], format_func=lambda x: "--- Seleccioná ---" if x == "" else x, key="reg_presup") if f_padre != "" else ""
        else: f_padre, f_presup = "", ""

    st.markdown("---")
    col3, col4, col5 = st.columns(3)
    with col3:
        f_total = st.number_input("PRESUPUESTO / VALOR ($):", min_value=0.0, step=100.0)
        f_fuente = st.selectbox("F.FIN:", [""] + opciones_fuente_fin, format_func=lambda x: "--- Elegí F.Fin ---" if x == "" else x)
    with col4:
        f_clase = st.selectbox("CLASE:", [""] + opciones_clase, format_func=lambda x: "--- Elegí Clase ---" if x == "" else x)
        f_tipo = st.selectbox("TIPO:", [""] + opciones_tipo, format_func=lambda x: "--- Elegí Tipo ---" if x == "" else x)
    with col5:
        f_finalidad = st.selectbox("FINALIDAD:", [""] + opciones_finalidad, format_func=lambda x: "--- Elegí Finalidad ---" if x == "" else x)

    campos_completos = (f_sec != "") and (f_sub != "") and (f_dest is not None and f_dest != "") and (f_obj != "") and (f_padre != "") and (f_presup != "") and (f_fuente != "") and (f_clase != "") and (f_tipo != "") and (f_finalidad != "")
    if st.button("💾 GUARDAR REGISTRO INMEDIATO", type="primary", use_container_width=True, disabled=not campos_completos) and f_total > 0:
        nuevo_renglon = {
            "secretaria": f_sec, "subsecretaria": f_sub, "destino": f_dest,
            "objeto_gasto": f_obj, "cuenta_padre": f_padre, "cuenta_presupuestaria": f_presup,
            "total": f_total, "fuente_fin": f_fuente, "clase": f_clase, "tipo": f_tipo, "finalidad": f_finalidad
        }
        guardar_fila_gsheet("egresos", nuevo_renglon)
        st.success("✅ ¡Renglón presupuestario guardado de forma cooperativa!")
        st.balloons()
        st.rerun()

# =====================================================================
# PESTAÑA 2: GESTIÓN DE DESTINOS DINÁMICOS
# =====================================================================
with tab_agregar_destino:
    st.subheader("⚙️ Panel de Configuración de Destinos")
    col_a, col_b = st.columns([1, 1.2])
    with col_a:
        st.markdown("**➕ Registrar Nuevo Destino**")
        d_sec = st.selectbox("Asociar a SECRETARÍA:", opciones_secretarias, key="dest_sec")
        d_sub = st.selectbox("Asociar a SUBSECRETARÍA:", MAPEO_ESTRUCTURA[d_sec], key="dest_sub")
        d_nombre = st.text_input("Nombre del Destino:").strip().upper()
        if st.button("✨ Registrar Destino", type="secondary", use_container_width=True) and d_nombre:
            nuevo_destino = {"secretaria": d_sec, "subsecretaria": d_sub, "destino": d_nombre}
            guardar_fila_gsheet("destinos", nuevo_destino)
            st.success("🎯 Destino añadido correctamente al repositorio.")
            st.rerun()
    with col_b:
        st.markdown("**📋 Listado de Destinos Activos**")
        df_dt_gsheet = leer_datos_gsheet(URL_READ_DESTINOS)
        lista_destinos_mostrar = []
        if not df_dt_gsheet.empty and "destino" in df_dt_gsheet.columns:
            lista_destinos_mostrar = df_dt_gsheet[["subsecretaria", "destino"]].dropna().to_dict('records')
        for d_l in st.session_state["db_local_backup"]["destinos"]:
            if {"subsecretaria": d_l["subsecretaria"], "destino": d_l["destino"]} not in lista_destinos_mostrar:
                lista_destinos_mostrar.append({"subsecretaria": d_l["subsecretaria"], "destino": d_l["destino"]})
        if lista_destinos_mostrar:
            df_dt_vista = pd.DataFrame(lista_destinos_mostrar).rename(columns={"subsecretaria": "SUBSECRETARÍA", "destino": "DESTINO"})
            st.dataframe(df_dt_vista, use_container_width=True, hide_index=True)

# =====================================================================
# =====================================================================
# PESTAÑA 3: BASE DE DATOS GENERAL (REPORTE TIPO SHEET MASIVO)
# =====================================================================
with tab_egresos:
    st.subheader("📊 Base de Datos General de Egresos")
    
    df_egr_gsheet = leer_datos_gsheet(URL_READ_EGRESOS)
    lista_egr_mostrar = []
    if not df_egr_gsheet.empty and "total" in df_egr_gsheet.columns:
        lista_egr_mostrar = df_egr_gsheet.dropna(subset=["total"]).to_dict('records')
    for e_l in st.session_state["db_local_backup"]["egresos"]:
        lista_egr_mostrar.append(e_l)
        
    if not lista_egr_mostrar:
        st.info("No hay movimientos registrados en la base de datos actualmente.")
    else:
        df_egr_completo = pd.DataFrame(lista_egr_mostrar)
        st.metric(label="📋 TOTAL GENERAL ACUMULADO MUNICIPAL (EGRESOS)", value=f"${df_egr_completo['total'].sum():,.2f}")
        
        df_plano_masivo = pd.DataFrame({
            "SECRETARIA": df_egr_completo["secretaria"], "SUBSECRETARIA": df_egr_completo["subsecretaria"],
            "DESTINO": df_egr_completo["destino"], "OBJETO DEL GASTO": df_egr_completo["objeto_gasto"],
            "CUENTA PADRE": df_egr_completo["cuenta_padre"], "CUENTA IMPUTACIÓN": df_egr_completo["cuenta_presupuestaria"],
            "TOTAL": df_egr_completo["total"].map(lambda x: f"${x:,.2f}"), "FUENTE FIN.": df_egr_completo["fuente_fin"],
            "CLASE": df_egr_completo["clase"], "TIPO": df_egr_completo["tipo"], "FINALIDAD/FUNCIÓN": df_egr_completo["finalidad"]
        })
        st.dataframe(df_plano_masivo, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        df_excel_global = pd.DataFrame({
            "SECRETARIA": df_egr_completo["secretaria"], "SUBSECRETARIA": df_egr_completo["subsecretaria"],
            "DESTINO": df_egr_completo["destino"], "OBJETO DEL GASTO": df_egr_completo["objeto_gasto"],
            "CUENTA PADRE": df_egr_completo["cuenta_padre"], "CUENTA IMPUTACIÓN": df_egr_completo["cuenta_presupuestaria"],
            "TOTAL": df_egr_completo["total"], "FUENTE FIN.": df_egr_completo["fuente_fin"],
            "CLASE": df_egr_completo["clase"], "TIPO": df_egr_completo["tipo"], "FINALIDAD/FUNCIÓN": df_egr_completo["finalidad"]
        })
        csv_global_data = df_excel_global.to_csv(index=False, sep=';').encode('utf-8-sig')
        st.download_button(label="📗 Descargar Base de Datos Completa en 11 Columnas (.xls)", data=csv_global_data, file_name="Base_De_Datos_Egresos_General.xls", mime="application/vnd.ms-excel", use_container_width=True)

# =====================================================================
# =====================================================================
# PESTAÑA 4: REPORTE GRÁFICO OFICIAL MUNICIPAL 2027
# =====================================================================
with tab_oficial:
    st.subheader("📋 Consulta de Presupuesto de Gasto por Destino Oficial")
    
    lista_of_mostrar = []
    df_of_gsheet = leer_datos_gsheet(URL_READ_EGRESOS)
    if not df_of_gsheet.empty and "total" in df_of_gsheet.columns:
        lista_of_mostrar = df_of_gsheet.dropna(subset=["total"]).to_dict('records')
    for e_l in st.session_state["db_local_backup"]["egresos"]:
        lista_of_mostrar.append(e_l)
        
    if not lista_of_mostrar:
        st.info("No hay transacciones cargadas en el servidor actualmente.")
    else:
        df_o_base = pd.DataFrame(lista_of_mostrar)
        cf1, cf2, col_f3 = st.columns(3)
        with cf1: sec_s = st.selectbox("1. SELECCIONÁ SECRETARÍA:", options=[""] + opciones_secretarias, key="of_sec")
        with cf2:
            sb_opts = [""] + MAPEO_ESTRUCTURA[sec_s] if sec_s != "" else [""]
            sub_s = st.selectbox("2. SELECCIONÁ SUBSECRETARÍA:", options=sb_opts, key="of_sub")
        with col_f3:
            if sec_s != "" and sub_s != "":
                lista_dest_oficial = []
                df_d_g = leer_datos_gsheet(URL_READ_DESTINOS)
                if not df_d_g.empty and "destino" in df_d_g.columns:
                    lista_dest_oficial = df_d_g[(df_d_g["secretaria"] == sec_s) & (df_d_g["subsecretaria"] == sub_s)]["destino"].dropna().tolist()
                for d_l in st.session_state["db_local_backup"]["destinos"]:
                    if d_l["secretaria"] == sec_s and d_l["subsecretaria"] == sub_s and d_l["destino"] not in lista_dest_oficial:
                        lista_dest_oficial.append(d_l["destino"])
                dest_s = st.selectbox("3. SELECCIONÁ DESTINO:", options=[""] + lista_dest_oficial, format_func=lambda x: "--- Seleccioná ---" if x == "" else str(x).upper(), key="of_dest")
            else: dest_s = st.selectbox("3. SELECCIONÁ DESTINO:", options=[""], key="of_dest")

        if sec_s != "" and sub_s != "" and dest_s != "":
            df_f_of = df_o_base[(df_o_base["secretaria"] == sec_s) & (df_o_base["subsecretaria"] == sub_s) & (df_o_base["destino"] == dest_s)].copy()
            tot_dest = df_f_of["total"].sum() if not df_f_of.empty else 0.0

            st.markdown(f"""
            <div style="border: 1px solid #000; padding: 0px; border-radius: 2px; background-color: #fff; font-family: Arial, sans-serif;">
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="width: 25%; font-size: 11px; padding: 15px; border-right: 1px solid #000; text-align: left;"><b>Municipalidad de Sunchales</b><br><span style="font-size: 9px; color: #777;">Presupuesto Oficial 2027</span></td>
                        <td style="width: 50%; text-align: center; padding: 15px; border-right: 1px solid #000; vertical-align: middle;"><h2 style="margin: 0; font-size: 18px; font-weight: bold;">PRESUPUESTO DE GASTO POR DESTINO</h2><h4 style="margin: 4px 0 0 0; font-size: 13px; font-weight: normal;">-2027-</h4></td>
                        <td style="width: 25%; text-align: center; background-color: #f5f5f5; vertical-align: middle;"><div style="font-size: 13px; font-weight: bold; border-bottom: 1px solid #000; padding: 4px 0;">Total Destino</div><div style="font-size: 18px; font-weight: bold;">${tot_dest:,.2f}</div></td>
                    </tr>
                </table>
                <div style="border-top: 1px solid #000; font-size: 11px; padding: 6px 10px;">
                    <b>SECRETARÍA:</b> {sec_s} | <b>SUBSECRETARÍA:</b> {sub_s} | <span style="float: right;"><b>DESTINO:</b> {str(dest_s).upper()}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            f_plan, html_rows = [], ""
            if not df_f_of.empty:
                for obj, df_obj in df_f_of.groupby("objeto_gasto"):
                    t_o = df_obj["total"].sum()
                    f_plan.append({"OBJETO DEL GASTO": f"<b>{obj}</b>", "PRESUPUESTO": f"<b>${t_o:,.2f}</b>", "F.FIN": "", "CLASE": "", "TIPO": "", "FINANCIAMIENTO": ""})
                    html_rows += f'<tr style="font-weight: bold; background-color: #f9f9f5;"><td style="text-align: left; padding-left: 5px;">{obj}</td><td>${t_o:,.2f}</td><td></td><td></td><td></td><td></td></tr>'
                    for pad, df_pad in df_obj.groupby("cuenta_padre"):
                        t_p = df_pad["total"].sum()
                        f_plan.append({"OBJETO DEL GASTO": f"&nbsp;&nbsp;&nbsp;&nbsp;<b>{pad}</b>", "PRESUPUESTO": f"<b>${t_p:,.2f}</b>", "F.FIN": "", "CLASE": "", "TIPO": "", "FINANCIAMIENTO": ""})
                        html_rows += f'<tr style="font-weight: bold;"><td style="text-align: left; padding-left: 20px;">{pad}</td><td>${t_p:,.2f}</td><td></td><td></td><td></td><td></td></tr>'
                        for _, r in df_pad.iterrows():
                            f_plan.append({"OBJETO DEL GASTO": f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{r['cuenta_presupuestaria']}", "PRESUPUESTO": f"${r['total']:,.2f}", "F.FIN": r["fuente_fin"], "CLASE": r["clase"], "TIPO": r["tipo"], "FINANCIAMIENTO": r["finalidad"]})
                            html_rows += f'<tr><td style="text-align: left; padding-left: 40px;">{r["cuenta_presupuestaria"]}</td><td>${r["total"]:,.2f}</td><td>{r["fuente_fin"]}</td><td>{r["clase"]}</td><td>{r["tipo"]}</td><td>{r["finalidad"]}</td></tr>'

            if f_plan: st.write(pd.DataFrame(f_plan).to_html(escape=False, index=False), unsafe_allow_html=True)

# =====================================================================
            # =====================================================================
            # MOTOR DE IMPRESIÓN AUTOMÁTICO HORIZONTAL (LANDSCAPE)
            # =====================================================================
            st.markdown("---")
            html_imp = f"""
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    @page {{ size: A4 landscape; margin: 15mm; }}
                    body {{ font-family: Arial, sans-serif; color: #000; margin: 0 auto; width: 100%; max-width: 1050px; }}
                    .m-box {{ border: 1px solid #000; padding: 12px; margin-bottom: 20px; }}
                    .t-hdr {{ width: 100%; border-collapse: collapse; }}
                    .t-hdr td {{ padding: 5px; vertical-align: middle; border: none; }}
                    .b-tot {{ border: 1px solid #000; background-color: #f5f5f5; text-align: center; }}
                    .tabla-datos {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 11px; }}
                    .tabla-datos th {{ border-bottom: 2px solid #000; padding: 8px 5px; text-align: center; font-weight: bold; }}
                    .tabla-datos td {{ border-bottom: 1px solid #e0e0e0; padding: 8px 5px; vertical-align: middle; text-align: center; }}
                    .tabla-datos th:first-child, .tabla-datos td:first-child {{ text-align: left !important; padding-left: 10px; }}
                </style>
            </head>
            <body onload="window.print();">
                <div class="m-box">
                    <table class="t-hdr">
                        <tr>
                            <td style="width: 25%; text-align: left; font-size: 10px;"><b>Municipalidad de Sunchales</b><br><span style="font-size: 8px; color: #555;">Presupuesto Oficial 2027</span></td>
                            <td style="width: 50%; text-align: center;"><b>PRESUPUESTO DE GASTO POR DESTINO</b><br><small>-2027-</small></td>
                            <td style="width: 25%;" class="b-tot"><small>Total Destino</small><br><b>${tot_dest:,.2f}</b></td>
                        </tr>
                    </table>
                    <div style="border-top: 1px solid #000; font-size: 11px; padding-top: 8px; margin-top: 8px;">
                        <b>SECRETARÍA:</b> {sec_s} | <b>SUBSECRETARÍA:</b> {sub_s} | <span style="float: right;"><b>DESTINO:</b> {str(dest_s).upper()}</span>
                    </div>
                </div>
                <table class="tabla-datos">
                    <thead><tr><th>OBJETO DEL GASTO</th><th>PRESUPUESTO</th><th>F.FIN</th><th>CLASE</th><th>TIPO</th><th>FINANCIAMIENTO</th></tr></thead>
                    <tbody>{html_rows}</tbody>
                </table>
            </body>
            </html>
            """
            st.download_button(label="🖨️ GENERAR Y ABRIR REPORTE IMPRIMIBLE A PDF", data=html_imp, file_name=f"Reporte_{str(dest_s).replace(' ', '_')}.html", mime="text/html", use_container_width=True)
            st.info("💡 Al hacer clic, se abrirá la ventana de impresión automática en horizontal con el membrete 2027.")

# Barra lateral informativa de control permanente
st.sidebar.header("⚙️ Herramientas de Red")
st.sidebar.info("Persistencia conectada cooperativamente al repositorio central de datos. Los registros se sincronizan con la hoja de cálculo municipal.")
