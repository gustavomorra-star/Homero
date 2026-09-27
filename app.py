import os
import pandas as pd
import streamlit as st
import io
import requests

# 1. ORDEN STRICTA DE ANCHO COMPLETO (Debe ser la primera instrucción)
st.set_page_config(layout="wide", page_title="Homero Presupuesto", page_icon="🍩")

# 2. INICIALIZACIÓN INMEDIATA DE MEMORIA (Para evitar caídas de lectura en red)
if "db_local_backup" not in st.session_state:
    st.session_state["db_local_backup"] = {"egresos": [], "destinos": []}

# --- CONEXIÓN DIRECTA Y PERMANENTE A GOOGLE SHEETS MUNICIPAL ---
SPREADSHEET_ID = "1r6izG5X1gil8MaZA1zD-WW2T1BA5mSC1Yq9-R663azU"

# Enlaces de conexión directa originales (Los que sí traían los datos)
URL_READ_EGRESOS = f"https://google.com{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet=egresos"
URL_READ_DESTINOS = f"https://google.com{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet=destinos"

def leer_datos_gsheet(url_tipo):
    try:
        # Descarga nativa pura de Pandas que funcionaba al inicio
        df = pd.read_csv(url_tipo)
        if not df.empty:
            # Normalizamos los encabezados para evitar problemas de mayúsculas accidentales
            df.columns = [str(col).strip().lower() for col in df.columns]
        return df
    except:
        if "sheet=destinos" in str(url_tipo):
            return pd.DataFrame(columns=["secretaria", "subsecretaria", "destino"])
        df_vacio = pd.DataFrame(columns=["secretaria", "subsecretaria", "destino", "objeto_gasto", "cuenta_padre", "cuenta_presupuestaria", "total", "fuente_fin", "clase", "tipo", "finalidad"])
        df_vacio["total"] = df_vacio["total"].astype(float)
        return df_vacio

def guardar_fila_gsheet(hoja, diccionario_datos):
    st.session_state["db_local_backup"][hoja].append(diccionario_datos)
    try:
        macro_url = st.secrets["GSHEET_MACRO_URL"]
        paquete_web = {"hoja": hoja, "datos": diccionario_datos}
        requests.post(macro_url, json=paquete_web)
    except:
        pass

# Dibujamos las etiquetas de títulos superiores del sistema
st.title("🍩 Homero - Sistema de Registro Presupuestario")
st.write("📍 Municipalidad de Sunchales | Conexión Cooperativa a Google Sheets **2027**")

# Definición del ramillete de las 5 solapas independientes en la interfaz superior
tab_formulario, tab_agregar_destino, tab_egresos, tab_oficial, tab_modificaciones = st.tabs([
    "📝 FORMULARIO DE REGISTRO", 
    "➕ GESTIÓN DE DESTINOS",
    "📉 GENERAL (Base de Datos Sheet)",
    "🏛️ REPORTE OFICIAL POR DESTINO",
    "🛠️ PANEL DE MODIFICACIONES"
])

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
        if not df_dt_gsheet.empty:
            df_dt_gsheet = df_dt_gsheet.fillna("")
            lista_destinos_mostrar = df_dt_gsheet.to_dict('records')
        for d_l in st.session_state["db_local_backup"]["destinos"]:
            if d_l not in lista_destinos_mostrar:
                lista_destinos_mostrar.append(d_l)
        if lista_destinos_mostrar:
            df_dt_vista = pd.DataFrame(lista_destinos_mostrar)
            if "subsecretaria" in df_dt_vista.columns and "destino" in df_dt_vista.columns:
                df_dt_vista = df_dt_vista.rename(columns={"subsecretaria": "SUBSECRETARÍA", "destino": "DESTINO"})
                st.dataframe(df_dt_vista[["SUBSECRETARÍA", "DESTINO"]], use_container_width=True, hide_index=True)
            else:
                st.dataframe(df_dt_vista, use_container_width=True, hide_index=True)

# =====================================================================
# PESTAÑA 3: BASE DE DATOS GENERAL Y CONTROL DE MODIFICACIONES
# =====================================================================
with tab_egresos:
    st.subheader("📊 Base de Datos General de Egresos")
    
    df_egr_gsheet = leer_datos_gsheet(URL_READ_EGRESOS)
    lista_egr_mostrar = []
    
    if not df_egr_gsheet.empty:
        df_egr_gsheet = df_egr_gsheet.fillna({"total": 0.0}).fillna("")
        lista_egr_mostrar = df_egr_gsheet.to_dict('records')
        
    for e_l in st.session_state["db_local_backup"]["egresos"]:
        lista_egr_mostrar.append(e_l)
        
    if not lista_egr_mostrar:
        df_egr_completo = pd.DataFrame(columns=["secretaria", "subsecretaria", "destino", "objeto_gasto", "cuenta_padre", "cuenta_presupuestaria", "total", "fuente_fin", "clase", "tipo", "finalidad"])
        df_egr_completo["total"] = df_egr_completo["total"].astype(float)
    else:
        df_egr_completo = pd.DataFrame(lista_egr_mostrar)
        if "total" not in df_egr_completo.columns:
            df_egr_completo["total"] = 0.0
            
    df_egr_completo["total"] = pd.to_numeric(df_egr_completo["total"], errors='coerce').fillna(0.0)
    st.metric(label="📋 TOTAL GENERAL ACUMULADO MUNICIPAL (EGRESOS)", value=f"${df_egr_completo['total'].sum():,.2f}")
    
    for col in ["secretaria", "subsecretaria", "destino", "objeto_gasto", "cuenta_padre", "cuenta_presupuestaria", "fuente_fin", "clase", "tipo", "finalidad"]:
        if col not in df_egr_completo.columns:
            df_egr_completo[col] = ""
            
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

    # --- PANEL SUPERVISOR DE MODIFICACIONES CON BLINDAJE INTEGRAL DE CONTROL ---
    st.markdown("---")
    st.markdown("### 🛠️ Panel Supervisor de Modificaciones")
    
    diccionario_opciones = {}
    if not df_egr_completo.empty:
        filas_lista = df_egr_completo.to_dict('records')
        for i in range(len(filas_lista)):
            r = filas_lista[i]
            destino_txt = str(r.get('destino', '')).strip().upper()
            partida_txt = str(r.get('cuenta_presupuestaria', '')).strip()
            
            if destino_txt != "" and partida_txt != "" and "---" not in destino_txt:
                monto_raw = str(r.get('total', '0')).replace('$', '').replace('.', '').replace(',', '.')
                try:
                    monto_val = float(monto_raw)
                except:
                    monto_val = 0.0
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
                try:
                    monto_def_val = float(monto_def_input)
                except:
                    monto_def_val = 0.0
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

# =====================================================================
# PESTAÑA 4: REPORTE GRÁFICO OFICIAL MUNICIPAL 2027
# =====================================================================
with tab_oficial:
    st.subheader("📋 Consulta de Presupuesto de Gasto por Destino Oficial")
    
    lista_of_mostrar = []
    df_of_gsheet = leer_datos_gsheet(URL_READ_EGRESOS)
    if not df_of_gsheet.empty:
        lista_of_mostrar = df_of_gsheet.to_dict('records')
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
            # Filtramos en minúsculas nativas de forma exacta
            df_f_of = df_o_base[(df_o_base["secretaria"] == sec_s) & (df_o_base["subsecretaria"] == sub_s) & (df_o_base["destino"] == dest_s)].copy()
            
            # Forzamos conversión numérica por si viene como texto desde Google Sheet
            if not df_f_of.empty and "total" in df_f_of.columns:
                df_f_of["total"] = pd.to_numeric(df_f_of["total"], errors='coerce').fillna(0.0)
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
            if not df_f_of.empty and "objeto_gasto" in df_f_of.columns:
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

            # --- MOTOR DE IMPRESIÓN AUTOMÁTICO HORIZONTAL ---
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


