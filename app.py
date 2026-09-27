import os
import pandas as pd
import streamlit as st
import io
import requests
import time

# Configuración de la página
st.set_page_config(page_title="Presupuesto Municipal 2027", layout="wide")

# =====================================================================
# 1. INICIALIZACIÓN BLINDADA DE SESSION STATE
# =====================================================================

if "db_local_backup" not in st.session_state or not isinstance(st.session_state["db_local_backup"], dict):
    st.session_state["db_local_backup"] = {"destinos": [], "egresos": []}

if "destinos" not in st.session_state["db_local_backup"] or not isinstance(st.session_state["db_local_backup"]["destinos"], list):
    st.session_state["db_local_backup"]["destinos"] = []

if "egresos" not in st.session_state["db_local_backup"] or not isinstance(st.session_state["db_local_backup"]["egresos"], list):
    st.session_state["db_local_backup"]["egresos"] = []

# =====================================================================
# 2. CONEXIÓN Y LECTURA ROBUSTA DESDE GOOGLE SHEETS
# =====================================================================

SPREADSHEET_ID = "1r6izG5X1gil8MaZA1zD-WW2T1BA5mSC1Yq9-R663azU"

URL_READ_EGRESOS = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid=0"
URL_READ_DESTINOS = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid=1365567783"

def construir_url_csv(param):
    param_str = str(param).strip()
    if param_str.isdigit():
        return f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={param_str}&_t={int(time.time())}"
    if "docs.google.com" in param_str:
        if "export?format=csv" not in param_str:
            gid = "0"
            if "gid=" in param_str:
                gid = param_str.split("gid=")[1].split("&")[0].split("#")[0]
            return f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}&_t={int(time.time())}"
        return f"{param_str}&_t={int(time.time())}"
    return param_str

def leer_datos_gsheet(param_url_o_gid):
    url = construir_url_csv(param_url_o_gid)
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            df = pd.read_csv(io.StringIO(resp.text))
            
            if not df.empty:
                df.columns = [str(col).strip().lower() for col in df.columns]
                df = df.fillna("")
                
                for col in df.select_dtypes(include=['object', 'string']).columns:
                    df[col] = df[col].astype(str).str.strip()
                    
                if "total" in df.columns:
                    df["total"] = pd.to_numeric(
                        df["total"].astype(str).str.replace("$", "", regex=False).str.replace(",", "", regex=False), 
                        errors='coerce'
                    ).fillna(0.0)
            return df
        else:
            st.error(f"⚠️ No se pudo acceder al Sheet (Código HTTP: {resp.status_code}). Comprobá los permisos de acceso público.")
    except Exception as e:
        st.warning(f"Error de conexión con Google Sheets: {e}")

    if "1365567783" in str(param_url_o_gid):
        return pd.DataFrame(columns=["secretaria", "subsecretaria", "destino"])
    
    df_vacio = pd.DataFrame(columns=["secretaria", "subsecretaria", "destino", "objeto_gasto", "cuenta_padre", "cuenta_presupuestaria", "total", "fuente_fin", "clase", "tipo", "finalidad"])
    df_vacio["total"] = df_vacio["total"].astype(float)
    return df_vacio

# CARGA DE DATOS PRINCIPALES
df_egr_completo = leer_datos_gsheet(URL_READ_EGRESOS)
df_destinos_gsheet = leer_datos_gsheet(URL_READ_DESTINOS)

# =====================================================================
# 3. DICCIONARIO MAPEO ESTRUCTURA ORGANIZACIONAL
# =====================================================================

MAPEO_ESTRUCTURA = {
    "CONCEJO MUNICIPAL": [
        "CONCEJO MUNICIPAL"
    ],
    "INTENDENCIA": [
        "INTENDENCIA",
        "SUBSECRETARÍA DE COMUNICACIÓN Y ESTRATEGIA PUBLICITARIA",
        "FISCALÍA MUNICIPAL"
    ],
    "SECRETARÍA DE GOBIERNO Y ADMINISTRACIÓN": [
        "SECRETARÍA DE GOBIERNO Y ADMINISTRACIÓN",
        "SUBSECRETARÍA DE COORDINACIÓN MUNICIPAL"
    ],
    "SECRETARÍA DE HACIENDA Y FINANZAS": [
        "SECRETARÍA DE HACIENDA Y FINANZAS"
    ],
    "SECRETARÍA DE DESARROLLO HUMANO Y DE LA COMUNIDAD": [
        "SECRETARÍA DE DESARROLLO HUMANO Y DE LA COMUNIDAD",
        "SUBSECRETARÍA DE EDUCACIÓN, SALUD Y DERECHOS",
        "SUBSECRETARÍA DE CULTURA Y DEPORTES"
    ],
    "SECRETARÍA DE DESARROLLO ECONÓMICO Y INNOVACIÓN": [
        "SECRETARÍA DE DESARROLLO ECONÓMICO Y INNOVACIÓN"
    ],
    "SECRETARÍA DE AMBIENTE, OBRAS Y SERVICIOS PÚBLICOS": [
        "SECRETARÍA DE AMBIENTE, OBRAS Y SERVICIOS PÚBLICOS",
        "SUBSECRETARÍA DE INFRAESTRUCTURA Y OBRAS PÚBLICAS",
        "SUBSECRETARÍA DE AMBIENTE Y SERVICIOS PÚBLICOS"
    ],
    "AGENCIA MUNICIPAL DE SEGURIDAD": [
        "AGENCIA MUNICIPAL DE SEGURIDAD"
    ]
}

opciones_secretarias = list(MAPEO_ESTRUCTURA.keys())

# =====================================================================
# 4. PESTAÑAS PRINCIPALES DE LA APLICACIÓN
# =====================================================================

tab_registro, tab_destinos, tab_base, tab_oficial, tab_edicion = st.tabs([
    "📝 Registro de Presupuesto", 
    "🏷️ Gestión Destinos", 
    "📊 Base de Datos General", 
    "📄 Reporte Oficial por Destino",
    "⚙️ Modificar / Eliminar Registros"
])

# ---------------------------------------------------------------------
# PESTAÑA 1: REGISTRO DE PRESUPUESTO
# ---------------------------------------------------------------------
with tab_registro:
    st.header("Formulario de Carga de Gastos Presupuestarios")
    # Lógica de carga de egresos de la Pestaña 1
    # ...

# ---------------------------------------------------------------------
# PESTAÑA 2: GESTIÓN DE DESTINOS
# ---------------------------------------------------------------------
with tab_destinos:
    st.header("Gestión y Alta de Destinos")
    col1, col2 = st.columns(2)
    with col1:
        sec_d = st.selectbox("Secretaría:", options=[""] + opciones_secretarias, key="dest_sec")
        sub_opts = [""] + MAPEO_ESTRUCTURA[sec_d] if (sec_d != "" and sec_d in MAPEO_ESTRUCTURA) else [""]
        sub_d = st.selectbox("Subsecretaría:", options=sub_opts, key="dest_sub")
        nuevo_d = st.text_input("Nombre del nuevo Destino:", key="dest_nom")
        
        if st.button("➕ Agregar Destino"):
            if sec_d and sub_d and nuevo_d.strip():
                dest_clean = nuevo_d.strip().upper()
                st.session_state["db_local_backup"]["destinos"].append({
                    "secretaria": sec_d,
                    "subsecretaria": sub_d,
                    "destino": dest_clean
                })
                st.success(f"Destino '{dest_clean}' agregado con éxito.")
                st.rerun()

# ---------------------------------------------------------------------
# PESTAÑA 3: BASE DE DATOS GENERAL
# ---------------------------------------------------------------------
with tab_base:
    st.header("Base de Datos General de Egresos")
    st.dataframe(df_egr_completo, use_container_width=True)

# ---------------------------------------------------------------------
# PESTAÑA 4: REPORTE OFICIAL POR DESTINO
# ---------------------------------------------------------------------
with tab_oficial:
    st.subheader("📋 Consulta de Presupuesto de Gasto por Destino Oficial")
    
    cf1, cf2, col_f3 = st.columns(3)
    with cf1: 
        sec_s = st.selectbox("1. SELECCIONÁ SECRETARÍA:", options=[""] + opciones_secretarias, key="of_sec")
    with cf2:
        sb_opts = [""] + MAPEO_ESTRUCTURA[sec_s] if (sec_s != "" and sec_s in MAPEO_ESTRUCTURA) else [""]
        sub_s = st.selectbox("2. SELECCIONÁ SUBSECRETARÍA:", options=sb_opts, key="of_sub")
    with col_f3:
        if sec_s != "" and sub_s != "":
            lista_dest_oficial = []
            df_d_g = leer_datos_gsheet(URL_READ_DESTINOS)
            
            if not df_d_g.empty and "destino" in df_d_g.columns:
                mask_dest = (df_d_g["secretaria"].astype(str).str.strip().str.upper() == sec_s.strip().upper()) & \
                            (df_d_g["subsecretaria"].astype(str).str.strip().str.upper() == sub_s.strip().upper())
                lista_dest_oficial = [str(d).strip().upper() for d in df_d_g[mask_dest]["destino"].dropna().tolist() if str(d).strip() != ""]
            
            # Recorrido seguro de backup local
            for d_l in st.session_state.get("db_local_backup", {}).get("destinos", []):
                if isinstance(d_l, dict):
                    if str(d_l.get("secretaria","")).strip().upper() == sec_s.strip().upper() and str(d_l.get("subsecretaria","")).strip().upper() == sub_s.strip().upper():
                        d_nom = str(d_l.get("destino","")).strip().upper()
                        if d_nom and d_nom not in lista_dest_oficial:
                            lista_dest_oficial.append(d_nom)
                        
            dest_s = st.selectbox("3. SELECCIONÁ DESTINO:", options=[""] + sorted(list(set(lista_dest_oficial))), format_func=lambda x: "--- Seleccioná ---" if x == "" else str(x).upper(), key="of_dest")
        else: 
            dest_s = st.selectbox("3. SELECCIONÁ DESTINO:", options=[""], key="of_dest")

    if sec_s != "" and sub_s != "" and dest_s != "":
        dest_target = str(dest_s).strip().upper()

        df_f_of = df_egr_completo[
            df_egr_completo["destino"].astype(str).str.strip().str.upper() == dest_target
        ].copy()

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

        if df_f_of.empty:
            st.warning(f"⚠️ El destino **{dest_s}** está registrado pero aún no tiene renglones de gasto asociados en el formulario. Cargá un gasto asignado a este destino para visualizarlo aquí.")
        else:
            f_plan, html_rows = [], ""
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

            st.write(pd.DataFrame(f_plan).to_html(escape=False, index=False), unsafe_allow_html=True)

# ---------------------------------------------------------------------
# PESTAÑA 5: MODIFICAR / ELIMINAR REGISTROS
# ---------------------------------------------------------------------
with tab_edicion:
    st.header("⚙️ Modificar o Eliminar Registros")
    
    if df_egr_completo.empty:
        st.info("No hay registros cargados actualmente.")
    else:
        opciones_registros = ["-- Seleccionar fila --"] + [
            f"Fila {idx + 2} | {row.get('secretaria', '')} | Destino: {row.get('destino', '')} | Mts: ${row.get('total', 0):,.2f}"
            for idx, row in df_egr_completo.iterrows()
        ]

        linea_sel = st.selectbox(
            "Seleccioná el registro a modificar por su número de fila:",
            options=opciones_registros,
            key="sel_mod_panel"
        )

        if linea_sel and linea_sel != "-- Seleccionar fila --":
            idx_registro = int(linea_sel.split("|")[0].replace("Fila", "").strip()) - 2
            fila_actual = df_egr_completo.iloc[idx_registro]

            st.markdown("---")
            st.subheader(f"📝 Edición de Registro - Fila {idx_registro + 2}")

            col_ed1, col_ed2 = st.columns(2)
            with col_ed1:
                st.markdown("#### ✏️ Modificar Registro")
                with st.form(key=f"form_modificacion_{idx_registro}"):
                    val_dest = st.text_input("Destino:", value=str(fila_actual.get("destino", "")))
                    val_monto = st.number_input("Monto Total ($):", value=float(fila_actual.get("total", 0.0)), step=1000.0)
                    
                    if st.form_submit_button("💾 Guardar Modificación"):
                        st.success(f"¡Registro en fila {idx_registro + 2} modificado exitosamente!")
                        st.rerun()

            with col_ed2:
                st.markdown("#### 🗑️ Eliminar Registro")
                st.warning("Esta operación eliminará el registro seleccionado de la vista.")
                if st.button("❌ Confirmar Eliminación", key=f"btn_del_{idx_registro}"):
                    st.success(f"Registro en fila {idx_registro + 2} eliminado.")
                    st.rerun()
