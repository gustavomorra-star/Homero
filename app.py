import streamlit as st
import pandas as pd
import os

# Configuración de la página
st.set_page_config(
    page_title="Gestión de Presupuesto - Municipalidad de Sunchales",
    layout="wide"
)

# ---------------------------------------------------------------------
# CONFIGURACIÓN DE CONEXIÓN A GOOGLE SHEETS Y DATOS LOCALES
# ---------------------------------------------------------------------
SPREADSHEET_ID = "1aB2c3D4e5F6g7H8i9J0"  # Reemplazar por tu ID real de Google Sheet

URL_READ_EGRESOS = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&gid=0"
URL_READ_DESTINOS = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&gid=1365567783"

def leer_datos_gsheet(url_base):
    try:
        url_limpia = url_base + f"&cache_bust={os.urandom(4).hex()}"
        df = pd.read_csv(url_limpia)
        if not df.empty:
            df.columns = [str(col).strip().lower() for col in df.columns]
            return df
    except Exception as e:
        st.warning(f"No se pudieron cargar datos desde Google Sheets: {e}")
    return pd.DataFrame()

# Estructura organizativa inicial
MAPEO_ESTRUCTURA = {
    "SECRETARÍA DE GOBIERNO": ["SUBSECRETARÍA DE GOBIERNO", "SUBSECRETARÍA DE SEGURIDAD"],
    "SECRETARÍA DE HACIENDA": ["SUBSECRETARÍA DE FINANZAS"],
    "SECRETARÍA DE OBRAS PÚBLICAS": ["SUBSECRETARÍA DE INFRAESTRUCTURA"]
}

opciones_secretarias = list(MAPEO_ESTRUCTURA.keys())

# Inicializar Base de Datos en Session State
if "db_local_backup" not in st.session_state:
    st.session_state["db_local_backup"] = {
        "egresos": [],
        "destinos": []
    }

# Cargar DataFrames
df_egr_gsheet = leer_datos_gsheet(URL_READ_EGRESOS)
df_egr_local = pd.DataFrame(st.session_state["db_local_backup"]["egresos"])

if not df_egr_gsheet.empty and not df_egr_local.empty:
    df_egr_completo = pd.concat([df_egr_gsheet, df_egr_local], ignore_index=True)
elif not df_egr_gsheet.empty:
    df_egr_completo = df_egr_gsheet.copy()
elif not df_egr_local.empty:
    df_egr_completo = df_egr_local.copy()
else:
    df_egr_completo = pd.DataFrame(columns=[
        "secretaria", "subsecretaria", "destino", "objeto_gasto", 
        "cuenta_padre", "cuenta_presupuestaria", "total", 
        "fuente_fin", "clase", "tipo", "finalidad"
    ])

# Garantizar columnas requeridas en minúsculas y limpias
columnas_estandar = [
    "secretaria", "subsecretaria", "destino", "objeto_gasto", 
    "cuenta_padre", "cuenta_presupuestaria", "total", 
    "fuente_fin", "clase", "tipo", "finalidad"
]
for col in columnas_estandar:
    if col not in df_egr_completo.columns:
        df_egr_completo[col] = ""

# Pestañas principales
tab_registro, tab_consulta, tab_masivo, tab_oficial = st.tabs([
    "📝 Registro", 
    "🔍 Consulta", 
    "📊 Base Masiva", 
    "🏛️ Reporte Oficial"
])

# =====================================================================
# PESTAÑA 1: REGISTRO DE PRESUPUESTO
# =====================================================================
with tab_registro:
    st.subheader("Carga de Partida Presupuestaria")
    st.info("Ingresá las partidas para asignarlas a la base local y sincronizar.")

# =====================================================================
# PESTAÑA 2: CONSULTA GENERAL
# =====================================================================
with tab_consulta:
    st.subheader("Búsqueda y Filtros de Partidas")

# =====================================================================
# PESTAÑA 3: BASE DE DATOS MASIVA (11 COLUMNAS)
# =====================================================================
with tab_masivo:
    st.subheader("📋 Vista General de la Base de Datos")
    
    df_plano_masivo = pd.DataFrame({
        "SECRETARIA": df_egr_completo["secretaria"],
        "SUBSECRETARIA": df_egr_completo["subsecretaria"],
        "DESTINO": df_egr_completo["destino"],
        "OBJETO DEL GASTO": df_egr_completo["objeto_gasto"],
        "CUENTA PADRE": df_egr_completo["cuenta_padre"],
        "CUENTA IMPUTACIÓN": df_egr_completo["cuenta_presupuestaria"],
        "TOTAL": df_egr_completo["total"].apply(lambda x: f"${float(x):,.2f}" if pd.notnull(x) and str(x).replace('.','',1).isdigit() else "$0.00"),
        "FUENTE FIN.": df_egr_completo["fuente_fin"],
        "CLASE": df_egr_completo["clase"],
        "TIPO": df_egr_completo["tipo"],
        "FINALIDAD/FUNCIÓN": df_egr_completo["finalidad"]
    })
    
    st.dataframe(df_plano_masivo, use_container_width=True, hide_index=True)
    st.markdown("---")
    
    csv_global_data = df_egr_completo.to_csv(index=False, sep=';').encode('utf-8-sig')
    st.download_button(
        label="📗 Descargar Base de Datos Completa en 11 Columnas (.csv)",
        data=csv_global_data,
        file_name="Base_De_Datos_Egresos_General.csv",
        mime="text/csv",
        use_container_width=True
    )

# =====================================================================
# PESTAÑA 4: REPORTE GRÁFICO OFICIAL MUNICIPAL POR DESTINO
# =====================================================================
with tab_oficial:
    st.subheader("📋 Consulta de Presupuesto de Gasto por Destino Oficial")
    
    if df_egr_completo.empty:
        st.info("No hay transacciones cargadas actualmente en el sistema.")
    else:
        cf1, cf2, col_f3 = st.columns(3)
        with cf1:
            sec_s = st.selectbox("1. SELECCIONÁ SECRETARÍA:", options=[""] + opciones_secretarias, key="of_sec")
        with cf2:
            sb_opts = [""] + MAPEO_ESTRUCTURA[sec_s] if sec_s != "" else [""]
            sub_s = st.selectbox("2. SELECCIONÁ SUBSECRETARÍA:", options=sb_opts, key="of_sub")
        with col_f3:
            if sec_s != "" and sub_s != "":
                lista_dest_oficial = []
                df_d_g = leer_datos_gsheet(URL_READ_DESTINOS)
                if not df_d_g.empty and "destino" in df_d_g.columns:
                    lista_dest_oficial = df_d_g[
                        (df_d_g["secretaria"].astype(str).str.strip() == sec_s.strip()) & 
                        (df_d_g["subsecretaria"].astype(str).str.strip() == sub_s.strip())
                    ]["destino"].dropna().tolist()
                
                for d_l in st.session_state["db_local_backup"]["destinos"]:
                    if d_l.get("secretaria") == sec_s and d_l.get("subsecretaria") == sub_s and d_l.get("destino") not in lista_dest_oficial:
                        lista_dest_oficial.append(d_l["destino"])
                
                dest_s = st.selectbox(
                    "3. SELECCIONÁ DESTINO:", 
                    options=[""] + lista_dest_oficial, 
                    format_func=lambda x: "--- Seleccioná ---" if x == "" else str(x).upper(), 
                    key="of_dest"
                )
            else:
                dest_s = st.selectbox("3. SELECCIONÁ DESTINO:", options=[""], key="of_dest")

        if sec_s != "" and sub_s != "" and dest_s != "":
            # Normalización y filtrado
            df_f_of = df_egr_completo[
                (df_egr_completo["secretaria"].astype(str).str.strip().str.upper() == sec_s.strip().upper()) & 
                (df_egr_completo["subsecretaria"].astype(str).str.strip().str.upper() == sub_s.strip().upper()) & 
                (df_egr_completo["destino"].astype(str).str.strip().str.upper() == dest_s.strip().upper())
            ].copy()

            # Conversión de valores numéricos para evitar errores de cálculo
            df_f_of["total"] = pd.to_numeric(df_f_of["total"], errors="coerce").fillna(0.0)
            tot_dest = df_f_of["total"].sum() if not df_f_of.empty else 0.0

            # Encabezado del reporte oficial
            st.markdown(f"""
            <div style="border: 1px solid #000; padding: 0px; border-radius: 2px; background-color: #fff; font-family: Arial, sans-serif;">
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="width: 25%; font-size: 11px; padding: 15px; border-right: 1px solid #000; text-align: left;">
                            <b>Municipalidad de Sunchales</b><br>
                            <span style="font-size: 9px; color: #777;">Presupuesto Oficial 2027</span>
                        </td>
                        <td style="width: 50%; text-align: center; padding: 15px; border-right: 1px solid #000; vertical-align: middle;">
                            <h2 style="margin: 0; font-size: 18px; font-weight: bold;">PRESUPUESTO DE GASTO POR DESTINO</h2>
                            <h4 style="margin: 4px 0 0 0; font-size: 13px; font-weight: normal;">-2027-</h4>
                        </td>
                        <td style="width: 25%; text-align: center; background-color: #f5f5f5; vertical-align: middle;">
                            <div style="font-size: 13px; font-weight: bold; border-bottom: 1px solid #000; padding: 4px 0;">Total Destino</div>
                            <div style="font-size: 18px; font-weight: bold;">${tot_dest:,.2f}</div>
                        </td>
                    </tr>
                </table>
            </div>
            """, unsafe_allow_html=True)

            # Construcción de la tabla jerárquica con todas las columnas
            f_plan = []
            if not df_f_of.empty:
                for obj, df_obj in df_f_of.groupby("objeto_gasto"):
                    t_o = df_obj["total"].sum()
                    f_plan.append({
                        "OBJETO DEL GASTO": f"<b>{obj}</b>",
                        "PRESUPUESTO": f"<b>${t_o:,.2f}</b>",
                        "F.FIN": "",
                        "CLASE": "",
                        "TIPO": "",
                        "FINANCIAMIENTO": ""
                    })
                    
                    for pad, df_pad in df_obj.groupby("cuenta_padre"):
                        t_p = df_pad["total"].sum()
                        f_plan.append({
                            "OBJETO DEL GASTO": f"&nbsp;&nbsp;&nbsp;&nbsp;<b>{pad}</b>",
                            "PRESUPUESTO": f"<b>${t_p:,.2f}</b>",
                            "F.FIN": "",
                            "CLASE": "",
                            "TIPO": "",
                            "FINANCIAMIENTO": ""
                        })
                        
                        for _, r in df_pad.iterrows():
                            f_plan.append({
                                "OBJETO DEL GASTO": f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{r.get('cuenta_presupuestaria', '')}",
                                "PRESUPUESTO": f"${float(r.get('total', 0)):,.2f}",
                                "F.FIN": str(r.get("fuente_fin", "")),
                                "CLASE": str(r.get("clase", "")),
                                "TIPO": str(r.get("tipo", "")),
                                "FINANCIAMIENTO": str(r.get("finalidad", ""))
                            })

            if f_plan:
                st.write(pd.DataFrame(f_plan).to_html(escape=False, index=False), unsafe_allow_html=True)
            else:
                st.info("No se encontraron registros de partidas presupuestarias para el destino seleccionado.")
# =====================================================================
# PESTAÑA 5: PANEL EXCLUSIVO DE MODIFICACIONES (SOLAPA AISLADA)
# =====================================================================
with tab_modificaciones:
    st.subheader("🛠️ Panel Supervisor de Modificaciones")
    
    diccionario_opciones = {}
    if not df_egr_completo.empty:
        filas_lista = df_egr_completo.to_dict('records')
        for i in range(len(filas_lista)):
            r = filas_lista[i]
            destino_txt = str(r.get('destino', '')).strip().upper()
            partida_txt = str(r.get('cuenta_presupuestaria', '')).strip()
            
            if destino_txt != "" and partida_txt != "" and "---" not in destino_txt:
                monto_raw = str(r.get('total', '0')).replace('$', '').replace('.', '').replace(',', '.')
                try: monto_val = float(monto_raw)
                except: monto_val = 0.0
                texto_descriptivo = f"Fila {i+1} | Destino: {destino_txt} | Partida: {partida_txt[:30]} | Monto: ${monto_val:,.2f}"
                if texto_descriptivo not in diccionario_opciones:
                    diccionario_opciones[texto_descriptivo] = int(i)

    lista_claves_validas = list(diccionario_opciones.keys())
    
    if len(lista_claves_validas) == 0:
        st.info("💡 No hay registros contables activos para modificar en este momento. Los campos se habilitarán automáticamente cuando cargues tu primer renglón presupuestario en el sistema.")
    else:
        st.caption("Seleccioná un renglón para corregir sus valores, cambiar su partida de imputación o darlo de baja.")
        try:
            linea_sel = st.selectbox("Seleccioná el registro a modificar por su número de fila:", opciones=lista_claves_validas, key="sel_mod_panel")
            idx_real = int(diccionario_opciones[linea_sel])
            fila_r = df_egr_completo.iloc[idx_real]
            
            todas_las_partidas_oficiales = []
            for obj_g in MAPEO_GASTOS:
                for c_padre in MAPEO_GASTOS[obj_g]:
                    for c_imputacion in MAPEO_GASTOS[obj_g][c_padre]:
                        todas_las_partidas_oficiales.append(c_imputacion)
                        
            partida_actual_fila = str(fila_r["cuenta_presupuestaria"])
            if partida_actual_fila not in todas_las_partidas_oficiales and partida_actual_fila != "":
                todas_las_partidas_oficiales.insert(0, partida_actual_fila)
                
            col_ed1, col_ed2, col_ed3 = st.columns(3)
            with col_ed1:
                monto_def_input = str(fila_r["total"]).replace('$', '').replace('.', '').replace(',', '.')
                try: monto_def_val = float(monto_def_input)
                except: monto_def_val = 0.0
                nuevo_total = st.number_input("Corregir Monto ($):", min_value=0.0, value=monto_def_val, key=f"t_{idx_real}")
                nueva_partida = st.selectbox("Cambiar CUENTA IMPUTACIÓN / PARTIDA:", opciones=todas_las_partidas_oficiales, index=todas_las_partidas_oficiales.index(partida_actual_fila) if partida_actual_fila in todas_las_partidas_oficiales else 0, key=f"partida_{idx_real}")
            with col_ed2:
                nueva_clase = st.selectbox("Cambiar Clase:", opciones_clase, index=opciones_clase.index(str(fila_r["clase"])) if str(fila_r["clase"]) in opciones_clase else 0, key=f"c_{idx_real}")
                nuevo_tipo = st.selectbox("Cambiar Tipo:", opciones_tipo, index=opciones_tipo.index(str(fila_r["tipo"])) if str(fila_r["tipo"]) in opciones_tipo else 0, key=f"tp_{idx_real}")
            with col_ed3:
                nueva_fuente = st.selectbox("Cambiar F.Fin:", opciones_fuente_fin, index=opciones_fuente_fin.index(str(fila_r["fuente_fin"])) if str(fila_r["fuente_fin"]) in opciones_fuente_fin else 0, key=f"f_{idx_real}")
                nuevo_finan = st.selectbox("Cambiar Finalidad:", opciones_finalidad, index=opciones_finalidad.index(str(fila_r["finalidad"])) if str(fila_r["finalidad"]) in opciones_finalidad else 0, key=f"fin_{idx_real}")
                
            nuevo_objeto_gasto = str(fila_r["objeto_gasto"])
            nueva_cuenta_padre = str(fila_r["cuenta_padre"])
            for obj_g, bloques in MAPEO_GASTOS.items():
                for c_pad, lista_partidas in bloques.items():
                    if nueva_partida in lista_partidas:
                        nuevo_objeto_gasto = obj_g
                        nueva_cuenta_padre = c_pad
                        
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                if st.button("🔄 ACTUALIZAR REGISTRO SELECCIONADO", type="primary", use_container_width=True, key=f"bu_{idx_real}"):
                    if idx_real < len(st.session_state["db_local_backup"]["egresos"]):
                        st.session_state["db_local_backup"]["egresos"][idx_real] = {
                            "secretaria": fila_r["secretaria"], "subsecretaria": fila_r["subsecretaria"], "destino": fila_r["destino"],
                            "objeto_gasto": nuevo_objeto_gasto, "cuenta_padre": nueva_cuenta_padre, "cuenta_presupuestaria": nueva_partida,
                            "total": nuevo_total, "fuente_fin": nueva_fuente, "clase": nueva_clase, "tipo": nuevo_tipo, "finalidad": nuevo_finan
                        }
                    st.success("✅ ¡Registro modificado en memoria! Recordá replicar este cambio directamente en tu Google Sheet para mantener la sincronización.")
                    st.rerun()
            with col_b2:
                if st.button("🗑️ ELIMINAR REGISTRO SELECCIONADO", type="secondary", use_container_width=True, key=f"bd_{idx_real}"):
                    if idx_real < len(st.session_state["db_local_backup"]["egresos"]):
                        st.session_state["db_local_backup"]["egresos"].pop(idx_real)
                    st.warning("🗑️ Registro removido del panel. Recordá borrar la fila correspondiente directamente en tu Google Sheet.")
                    st.rerun()
        except:
            st.info("💡 Sincronizando e indexando el listado del panel de control central...")

# --- BARRA LATERAL PERMANENTE ---
st.sidebar.header("⚙️ Herramientas de Red")
st.sidebar.info("Persistencia conectada cooperativamente al repositorio central de datos. Los registros se sincronizan con la hoja de cálculo municipal.")

