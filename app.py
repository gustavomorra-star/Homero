import os
import pandas as pd
import streamlit as st
import io
import requests

# --- CONEXIÓN DIRECTA POR API REST A LA NUBE DE SUPABASE (ETERNA Y PERMANENTE) ---
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

headers_supabase = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

def ejecutar_query_supabase(tabla, json_datos=None, query_params=None, metodo="GET"):
    url_endpoint = f"{SUPABASE_URL}/rest/v1/{tabla}"
    try:
        if metodo == "GET":
            response = requests.get(url_endpoint, headers=headers_supabase, params=query_params)
            return response.json() if response.status_code in [200, 206] else []
        elif metodo == "POST":
            response = requests.post(url_endpoint, headers=headers_supabase, json=json_datos)
            return response.json()
        elif metodo == "DELETE":
            response = requests.delete(url_endpoint, headers=headers_supabase, params=query_params)
            return response.text
    except Exception as e:
        st.error(f"Error de enlace con la nube: {e}")
        return []

st.set_page_config(layout="wide", page_title="Homero Presupuesto", page_icon="🍩")
st.title("🍩 Homero - Sistema de Registro Presupuestario")
st.write("📍 Municipalidad de Sunchales | Servidor Permanente en la Nube 2027")

# --- Plan de Cuentas Oficial ---
MAPEO_GASTOS = {
    "2. Bienes de consumo": {
        "22.5.0.0.00.000 - Productos químicos, combustibles y lubricantes": ["22.5.5.0.00.000 - Tintas, Pinturas y Colorantes"],
        "22.6.0.0.00.000 - Productos minerales no metálicos": ["22.6.5.0.00.000 - Productos de Cemento, Cal y Yeso"],
        "22.8.0.0.00.000 - Minerales": ["22.8.4.0.00.000 - Piedra, Arcilla y Arena"],
        "22.9.0.0.00.000 - Otros bienes de consumo": ["22.9.3.0.00.000 - Útiles y materiales eléctricos", "22.9.6.0.00.000 - Repuestos y accesorios"]
    },
    "3. Servicios": {
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

tab_formulario, tab_agregar_destino, tab_egresos, tab_registros, tab_oficial = st.tabs([
    "📝 FORMULARIO DE REGISTRO", 
    "➕ GESTIÓN DE DESTINOS",
    "📉 GENERAL (Base de Datos Sheet)",
    "📊 VER DATOS GUARDADOS",
    "🏛️ REPORTE OFICIAL POR DESTINO"
])

# =====================================================================
# PESTAÑA 1: FORMULARIO PRINCIPAL DE REGISTRO
# =====================================================================
with tab_formulario:
    st.subheader("📥 Cargar Nuevo Renglón Presupuestario")
    st.caption("Los campos se encuentran vacíos por defecto. Seleccioná una opción para activar las cascadas de imputación.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**📍 1. Ubicación Institucional**")
        f_sec = st.selectbox(
            "SECRETARÍA:", 
            options=[""] + opciones_secretarias,
            format_func=lambda x: "--- Seleccioná una Secretaría ---" if x == "" else x,
            key="reg_sec"
        )
        
        if f_sec != "":
            opciones_sub_filtradas = MAPEO_ESTRUCTURA[f_sec]
            f_sub = st.selectbox(
                "SUBSECRETARÍA:", 
                options=[""] + opciones_sub_filtradas,
                format_func=lambda x: "--- Seleccioná una Subsecretaría ---" if x == "" else x,
                key="reg_sub"
            )
            
            if f_sub != "":
                conn = sqlite3.connect(DB_NAME)
                df_d = pd.read_sql_query("SELECT nombre_destino FROM destinos_sistema WHERE secretaria = ? AND subsecretaria = ?", conn, params=(f_sec, f_sub))
                conn.close()
                lista_d = df_d["nombre_destino"].tolist()
                
                if not lista_d:
                    st.warning("⚠️ Sin destinos creados para esta área. Crealo primero en '➕ GESTIÓN DE DESTINOS'.")
                    f_dest = None
                else:
                    f_dest = st.selectbox(
                        "DESTINO SELECCIONADO:", 
                        options=[""] + lista_d,
                        format_func=lambda x: "--- Seleccioná un Destino ---" if x == "" else str(x).upper(),
                        key="reg_dest"
                    )
            else:
                f_dest = None
        else:
            f_sub = ""
            f_dest = None
            st.info("💡 Seleccioná una Secretaría arriba para desplegar las Subsecretarías.")
        
    with col2:
        st.markdown("**📊 2. Imputación de Partida**")
        f_obj = st.selectbox(
            "OBJETO DE GASTO:", 
            options=[""] + opciones_objetos,
            format_func=lambda x: "--- Seleccioná un Objeto de Gasto ---" if x == "" else x,
            key="reg_obj"
        )
        
        if f_obj != "":
            diccionario_cuentas_padre = MAPEO_GASTOS[f_obj]
            f_padre = st.selectbox(
                "CUENTA PADRE:", 
                options=[""] + list(diccionario_cuentas_padre.keys()),
                format_func=lambda x: "--- Seleccioná una Cuenta Padre ---" if x == "" else x,
                key="reg_padre"
            )
            
            if f_padre != "":
                lista_imputaciones_filtradas = diccionario_cuentas_padre[f_padre]
                f_presup = st.selectbox(
                    "CUENTA DE IMPUTACIÓN / PARTIDA:", 
                    options=[""] + lista_imputaciones_filtradas,
                    format_func=lambda x: "--- Seleccioná una Partida Final ---" if x == "" else x,
                    key="reg_presup"
                )
            else:
                f_presup = ""
        else:
            f_padre = ""
            f_presup = ""
            st.info("💡 Seleccioná un Objeto de Gasto arriba para desplegar las Cuentas Padre.")

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
    boton_guardar = st.button("💾 GUARDAR REGISTRO INMEDIATO", type="primary", use_container_width=True, disabled=not campos_completos)
    
    if boton_guardar and f_total > 0:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO egresos_sistema (secretaria, subsecretaria, destino, objeto_gasto, cuenta_padre, cuenta_presupuestaria, total, fuente_fin, clase, tipo, finalidad)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (f_sec, f_sub, f_dest, f_obj, f_padre, f_presup, f_total, f_fuente, f_clase, f_tipo, f_finalidad))
        conn.commit()
        conn.close()
        st.success("✅ ¡Renglón presupuestario guardado con éxito!")
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
            try:
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute("INSERT INTO destinos_sistema (secretaria, subsecretaria, nombre_destino) VALUES (?, ?, ?)", (d_sec, d_sub, d_nombre))
                conn.commit()
                conn.close()
                st.success("🎯 Destino añadido correctamente.")
                st.rerun()
            except sqlite3.IntegrityError:
                st.error("❌ Este destino ya se encuentra registrado.")

    with col_b:
        st.markdown("**📋 Listado de Destinos Activos**")
        conn = sqlite3.connect(DB_NAME)
        df_dt = pd.read_sql_query("SELECT subsecretaria AS [SUBSECRETARÍA], nombre_destino AS [DESTINO] FROM destinos_sistema ORDER BY secretaria", conn)
        conn.close()
        if not df_dt.empty:
            st.dataframe(df_dt, use_container_width=True, hide_index=True)

# =====================================================================
# PESTAÑA 3: REPORTES AUTOMÁTICOS CON DESGLOSE VERTICAL
# =====================================================================
with tab_egresos:
    st.subheader("📊 Base de Datos General de Egresos")
    st.caption("Visualización y exportación unificada de la totalidad de renglones presupuestarios en 11 columnas paralelas.")
    
    conn = sqlite3.connect(DB_NAME)
    df_egr_completo = pd.read_sql_query("SELECT * FROM egresos_sistema", conn)
    conn.close()

    if df_egr_completo.empty:
        st.info("No hay movimientos registrados en la base de datos actualmente.")
    else:
        # Indicador masivo de control contable
        st.metric(label="📋 TOTAL GENERAL ACUMULADO MUNICIPAL (EGRESOS)", value=f"${df_egr_completo['total'].sum():,.2f}")
        
        # Sincronizamos dinámicamente la columna de finalidad/financiamiento
        col_finalidad_completa = df_egr_completo["finalidad"] if "finalidad" in df_egr_completo.columns else df_egr_completo["financiamiento"]
        
        # CONSTRUCCIÓN DE LA PLANILLA ABIERTA TOTAL EN PANTALLA
        df_plano_masivo = pd.DataFrame({
            "SECRETARIA": df_egr_completo["secretaria"],
            "SUBSECRETARIA": df_egr_completo["subsecretaria"],
            "DESTINO": df_egr_completo["destino"],
            "OBJETO DEL GASTO": df_egr_completo["objeto_gasto"],
            "CUENTA PADRE": df_egr_completo["cuenta_padre"],
            "CUENTA IMPUTACIÓN": df_egr_completo["cuenta_presupuestaria"],
            "TOTAL": df_egr_completo["total"].map(lambda x: f"${x:,.2f}" if pd.notnull(x) else "$0.00"),
            "FUENTE FIN.": df_egr_completo["fuente_fin"],
            "CLASE": df_egr_completo["clase"],
            "TIPO": df_egr_completo["tipo"],
            "FINALIDAD/FUNCIÓN": col_finalidad_completa
        })
        
        # Renderizamos la totalidad de los datos en una grilla extendida para control visual directo
        st.dataframe(df_plano_masivo, use_container_width=True, hide_index=True)
        
        # =====================================================================
        # 📥 EXPORTADOR GLOBAL EN 11 COLUMNAS SEPARADAS POR PUNTO Y COMA
        # =====================================================================
        st.markdown("---")
        
        df_excel_global = pd.DataFrame({
            "SECRETARIA": df_egr_completo["secretaria"],
            "SUBSECRETARIA": df_egr_completo["subsecretaria"],
            "DESTINO": df_egr_completo["destino"],
            "OBJETO DEL GASTO": df_egr_completo["objeto_gasto"],
            "CUENTA PADRE": df_egr_completo["cuenta_padre"],
            "CUENTA IMPUTACIÓN": df_egr_completo["cuenta_presupuestaria"],
            "TOTAL": df_egr_completo["total"], # Número crudo matemático
            "FUENTE FIN.": df_egr_completo["fuente_fin"],
            "CLASE": df_egr_completo["clase"],
            "TIPO": df_egr_completo["tipo"],
            "FINALIDAD/FUNCIÓN": col_finalidad_completa
        })
        
        # El comando 'sep=";"' fuerza a Excel a dividir las 11 columnas automáticamente en sistemas argentinos
        csv_global_data = df_excel_global.to_csv(index=False, sep=';').encode('utf-8-sig')
        
        st.download_button(
            label="📗 Descargar Base de Datos Completa en 11 Columnas (.xls)", 
            data=csv_global_data, 
            file_name="Base_De_Datos_Egresos_General.xls", 
            mime="application/vnd.ms-excel", 
            use_container_width=True,
            key="btn_descarga_global_sheet_egresos"
        )
# =====================================================================
# PESTAÑA 4: CONSULTA COMPLETA POR BLOQUES Y PANEL DE EDICIÓN SEGURO
# =====================================================================
with tab_registros:
    st.subheader("📋 Planilla de Consulta de Datos Guardados")
    conn = sqlite3.connect(DB_NAME)
    df_auditoria = pd.read_sql_query("SELECT * FROM egresos_sistema", conn)
    conn.close()
    
    if df_auditoria.empty: 
        st.info("No hay registros en la base de datos actualmente.")
    else:
        # 1. Visualización por bloques limpios institucionales
        for (sec, sub, dest), df_grupo in df_auditoria.groupby(["secretaria", "subsecretaria", "destino"]):
            st.markdown(f'<div style="background-color: #f0f2f6; padding: 10px; border-radius: 4px; margin-top: 15px;"><b>🏛️ JURISDICCIÓN:</b> {sec}<br><b>🏢 SUBSEC:</b> {sub} | <b>🎯 DESTINO:</b> {dest}</div>', unsafe_allow_html=True)
            
            df_grupo_copy = df_grupo.copy()
            df_grupo_copy["partida_vertical"] = df_grupo_copy.apply(lambda r: f"{r['objeto_gasto']}\n↳ {r['cuenta_padre']}\n  ↳ {r['cuenta_presupuestaria']}", axis=1)
            
            col_finalidad_bloque = df_grupo_copy["finalidad"] if "finalidad" in df_grupo_copy.columns else df_grupo_copy["financiamiento"]
            df_bloque_vista = pd.DataFrame({
                "ID": df_grupo_copy["id"], 
                "PARTIDA": df_grupo_copy["partida_vertical"], 
                "PRESUPUESTO ($)": df_grupo_copy["total"].map(lambda x: f"${x:,.2f}" if pd.notnull(x) else "$0.00"), 
                "F.FIN": df_grupo_copy["fuente_fin"], 
                "CLASE": df_grupo_copy["clase"], 
                "TIPO": df_grupo_copy["tipo"], 
                "FINALIDAD": col_finalidad_bloque
            })
            st.dataframe(df_bloque_vista, use_container_width=True, hide_index=True)
            st.markdown(f'<div style="text-align: right; font-weight: bold; border-top: 1px solid #dcdcdc; padding-top: 5px; margin-bottom: 15px;">Total Destino: <span style="color: #2e7d32;">${df_grupo_copy["total"].sum():,.2f}</span></div>', unsafe_allow_html=True)
            
        st.markdown("---")
        st.metric(label="📊 TOTAL GENERAL ACUMULADO MUNICIPAL", value=f"${df_auditoria['total'].sum():,.2f}")
        
        # 2. Panel Supervisor de Modificaciones
        st.markdown("---")
        st.markdown("### 🛠️ Panel Supervisor de Modificaciones")
        st.caption("Elegí la fila que querés corregir o dar de baja (el número de ID figura en la primera columna de las tablas de arriba).")
        
        df_auditoria["Texto_Descriptivo"] = df_auditoria.apply(lambda r: f"ID: {r['id']} | Destino: {r['destino']} | Monto: ${r['total']:,.2f}", axis=1)
        linea_seleccionada = st.selectbox("Seleccioná el registro a modificar por su descripción de ID:", df_auditoria["Texto_Descriptivo"].tolist(), key="select_modificar_auditoria")
        
        # Extracción segura sin comandos .iloc
        fila_real = df_auditoria[df_auditoria["Texto_Descriptivo"] == linea_seleccionada]
        id_registro = int(fila_real["id"].values[0])
        
        col_ed1, col_ed2, col_ed3 = st.columns(3)
        with col_ed1:
            nuevo_total = st.number_input("Corregir Monto ($):", min_value=0.0, value=float(fila_real["total"].values[0]), key=f"tot_{id_registro}")
            val_fuente = str(fila_real["fuente_fin"].values[0])
            nueva_fuente = st.selectbox("Cambiar F.Fin:", opciones_fuente_fin, index=opciones_fuente_fin.index(val_fuente) if val_fuente in opciones_fuente_fin else 0, key=f"fuente_{id_registro}")
        with col_ed2:
            val_clase = str(fila_real["clase"].values[0])
            nueva_clase = st.selectbox("Cambiar Clase:", opciones_clase, index=opciones_clase.index(val_clase) if val_clase in opciones_clase else 0, key=f"clase_{id_registro}")
            val_tipo = str(fila_real["tipo"].values[0])
            nuevo_tipo = st.selectbox("Cambiar Tipo:", opciones_tipo, index=opciones_tipo.index(val_tipo) if val_tipo in opciones_tipo else 0, key=f"tipo_{id_registro}")
        with col_ed3:
            val_actual_finalidad = str(fila_real["finalidad"].values[0] if "finalidad" in fila_real.columns else fila_real["financiamiento"].values[0])
            nuevo_finan = st.selectbox("Cambiar Finalidad:", opciones_finalidad, index=opciones_finalidad.index(val_actual_finalidad) if val_actual_finalidad in opciones_finalidad else 0, key=f"finalidad_{id_registro}")
            
        st.markdown("<br>", unsafe_allow_html=True)
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("🔄 ACTUALIZAR REGISTRO SELECCIONADO", type="primary", use_container_width=True, key=f"btn_upd_{id_registro}"):
                conn = sqlite3.connect(DB_NAME)
                conn.cursor().execute("UPDATE egresos_sistema SET total = ?, fuente_fin = ?, clase = ?, tipo = ?, finalidad = ? WHERE id = ?", (nuevo_total, nueva_fuente, nueva_clase, nuevo_tipo, nuevo_finan, id_registro))
                conn.commit()
                conn.close()
                st.success("✅ ¡Registro modificado correctamente!")
                st.rerun()
        with col_btn2:
            if st.button("🗑️ ELIMINAR REGISTRO INDIVIDUAL", type="secondary", use_container_width=True, key=f"btn_del_{id_registro}"):
                conn = sqlite3.connect(DB_NAME)
                conn.cursor().execute("DELETE FROM egresos_sistema WHERE id = ?", (id_registro,))
                conn.commit()
                conn.close()
                st.warning("🗑️ Registro eliminado del sistema.")
                st.rerun()

# Barra lateral de herramientas globales
st.sidebar.header("⚙️ Herramientas")
if st.sidebar.button("⚠️ Vaciar Base de Datos Completa"):
    conn = sqlite3.connect(DB_NAME)
    conn.cursor().execute("DELETE FROM egresos_sistema")
    conn.cursor().execute("DELETE FROM destinos_sistema")
    conn.commit()
    conn.close()
    st.sidebar.success("Base de datos limpia por completo.")
    st.rerun()
# =====================================================================
# 🏛️ PESTAÑA 5: INFORME OFICIAL - PRESUPUESTO DE GASTO POR DESTINO
# =====================================================================
with tab_oficial:
    st.subheader("📋 Consulta de Presupuesto de Gasto por Destino Oficial")
    st.caption("Filtre mediante los selectores en cascada para estructurar la planilla con el formato normativo y sumas jerárquicas.")
    
    conn = sqlite3.connect(DB_NAME)
    df_oficial_base = pd.read_sql_query("SELECT * FROM egresos_sistema", conn)
    conn.close()

    # Selectores en triple cascada limpia e independiente
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        sec_sel = st.selectbox("1. SELECCIONÁ SECRETARÍA:", options=[""] + opciones_secretarias, key="oficial_sec")
    with col_f2:
        sub_opts = [""] + MAPEO_ESTRUCTURA[sec_sel] if sec_sel != "" else [""]
        sub_sel = st.selectbox("2. SELECCIONÁ SUBSECRETARÍA:", options=sub_opts, key="oficial_sub")
    with col_f3:
        if sec_sel != "" and sub_sel != "":
            conn = sqlite3.connect(DB_NAME)
            df_d_of = pd.read_sql_query("SELECT nombre_destino FROM destinos_sistema WHERE secretaria = ? AND subsecretaria = ?", conn, params=(sec_sel, sub_sel))
            conn.close()
            dest_sel = st.selectbox("3. SELECCIONÁ DESTINO:", options=[""] + df_d_of["nombre_destino"].tolist(), format_func=lambda x: "--- Seleccioná ---" if x == "" else str(x).upper(), key="oficial_dest")
        else:
            dest_sel = st.selectbox("3. SELECCIONÁ DESTINO:", options=[""], key="oficial_dest")

    if sec_sel != "" and sub_sel != "" and dest_sel != "":
        df_filtrado_oficial = df_oficial_base[(df_oficial_base["secretaria"] == sec_sel) & (df_oficial_base["subsecretaria"] == sub_sel) & (df_oficial_base["destino"] == dest_sel)].copy()
        total_acumulado_destino = df_filtrado_oficial["total"].sum() if not df_filtrado_oficial.empty else 0.0

        # 1. ENCABEZADO INSTITUCIONAL EN PANTALLA (IDÉNTICO A TU DISEÑO)
        st.markdown(
            f"""
            <div style="border: 1px solid #000000; padding: 0px; border-radius: 2px; background-color: #ffffff; margin-top: 15px; margin-bottom: 20px; font-family: Arial, sans-serif;">
                <table style="width: 100%; border-collapse: collapse; margin: 0;">
                    <tr>
                        <td style="width: 25%; text-align: left; font-size: 11px; color: #555; padding: 15px; border-right: 1px solid #000000;">
                            <b>Municipalidad de Sunchales</b><br><span style="font-size: 9px; color: #777;">Presupuesto Oficial 2027</span>
                        </td>
                        <td style="width: 50%; text-align: center; padding: 15px; border-right: 1px solid #000000; vertical-align: middle;">
                            <h2 style="margin: 0; padding: 0; color: #000000; font-size: 18px; font-weight: bold;">PRESUPUESTO DE GASTO POR DESTINO</h2>
                            <h4 style="margin: 4px 0 0 0; padding: 0; font-size: 13px; font-weight: normal;">-2027-</h4>
                        </td>
                        <td style="width: 25%; text-align: center; padding: 0; margin: 0; vertical-align: middle; background-color: #f5f5f5;">
                            <div style="font-size: 13px; font-weight: bold; border-bottom: 1px solid #000000; padding: 6px 0;">Total Destino</div>
                            <div style="font-size: 18px; font-weight: bold; color: #000000; padding: 10px 0;">${total_acumulado_destino:,.2f}</div>
                        </td>
                    </tr>
                </table>
                <div style="border-top: 1px solid #000000; background-color: #ffffff; font-size: 11px; padding: 6px 10px;">
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="width: 35%; padding: 2px;"><b>SECRETARÍA:</b> {sec_sel}</td>
                            <td style="width: 35%; padding: 2px;"><b>SUBSECRETARÍA:</b> {sub_sel}</td>
                            <td style="width: 30%; padding: 2px; text-align: right;"><b>DESTINO:</b> {str(dest_sel).upper()}</td>
                        </tr>
                    </table>
                </div>
            </div>
            """, 
            unsafe_allow_html=True
        )

        # 2. PROCESAMIENTO EXCLUSIVO DE LA PLANILLA GRÁFICA PARA LA WEB (FUERA DEL TRY)
        filas_planilla = []
        if not df_filtrado_oficial.empty:
            for objeto, df_objeto in df_filtrado_oficial.groupby("objeto_gasto"):
                tot_obj = df_objeto["total"].sum()
                filas_planilla.append({"OBJETO DEL GASTO": f"<b>{objeto}</b>", "PRESUPUESTO": f"<b>${tot_obj:,.2f}</b>", "F.FIN": "", "CLASE": "", "TIPO": "", "FINANCIAMIENTO": ""})
                
                for padre, df_padre in df_objeto.groupby("cuenta_padre"):
                    tot_pad = df_padre["total"].sum()
                    filas_planilla.append({"OBJETO DEL GASTO": f"&nbsp;&nbsp;&nbsp;&nbsp;<b>{padre}</b>", "PRESUPUESTO": f"<b>${tot_pad:,.2f}</b>", "F.FIN": "", "CLASE": "", "TIPO": "", "FINANCIAMIENTO": ""})
                    
                    for _, fila in df_padre.iterrows():
                        val_fin = fila["finalidad"] if "finalidad" in df_filtrado_oficial.columns else fila["financiamiento"]
                        filas_planilla.append({
                            "OBJETO DEL GASTO": f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{fila['cuenta_presupuestaria']}", 
                            "PRESUPUESTO": f"${fila['total']:,.2f}", 
                            "F.FIN": fila["fuente_fin"], 
                            "CLASE": fila["clase"], 
                            "TIPO": fila["tipo"], 
                            "FINANCIAMIENTO": val_fin
                        })

        # Muestra la grilla con todas sus columnas de forma nativa en la web
        if filas_planilla:
            st.write(pd.DataFrame(filas_planilla).to_html(escape=False, index=False), unsafe_allow_html=True)
        else:
            st.info("No hay transacciones registradas para este destino.")
 # =====================================================================
 # =====================================================================
        # 🖨️ CENTRO DE IMPRESIÓN MUNICIPAL AUTOMATIZADO A PDF (2027)
        # =====================================================================
        st.markdown("---")
        st.markdown("#### 🖨️ Centro de Impresión Municipal")

        # Construimos el código HTML/CSS con una orden de auto-impresión nativa (window.print)
        html_imprimible = f"""
        <html>
        <head>
            <meta charset="utf-8">
            <title>Presupuesto Oficial 2027 - {str(dest_sel).upper()}</title>
            <style>
                @page {{ size: A4 landscape; margin: 15mm; }}
                body {{ font-family: Arial, sans-serif; color: #000000; margin: 0 auto; padding: 0; width: 100%; max-width: 1050px; }}
                .container-membrete {{ border: 1px solid #000000; padding: 12px; margin-bottom: 20px; box-sizing: border-box; }}
                .tabla-header {{ width: 100%; border-collapse: collapse; }}
                .tabla-header td {{ border: none; padding: 5px; vertical-align: middle; }}
                .titulo-principal {{ margin: 0; font-size: 16px; font-weight: bold; text-align: center; }}
                .box-total {{ border: 1px solid #000000; background-color: #f5f5f5; text-align: center; }}
                .total-label {{ font-size: 11px; font-weight: bold; border-bottom: 1px solid #000000; padding: 4px 0; }}
                .total-monto {{ font-size: 14px; font-weight: bold; padding: 6px 0; }}
                .linea-institucional {{ width: 100%; border-collapse: collapse; margin-top: 10px; border-top: 1px solid #000000; font-size: 11px; }}
                .linea-institucional td {{ padding-top: 8px; border: none; }}
                .tabla-datos {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 11px; }}
                .tabla-datos th {{ border-bottom: 2px solid #000000; padding: 8px 5px; text-align: center; font-weight: bold; }}
                .tabla-datos td {{ border-bottom: 1px solid #e0e0e0; padding: 8px 5px; vertical-align: middle; text-align: center; }}
                .tabla-datos th:first-child, .tabla-datos td:first-child {{ text-align: left !important; padding-left: 10px; }}
            </style>
        </head>
        <body onload="window.print();">
            <div class="container-membrete">
                <table class="tabla-header">
                    <tr>
                        <td style="width: 25%; font-size: 10px; line-height: 1.3; text-align: left;">
                            <b>Municipalidad de Sunchales</b><br>
                            <span style="color: #555; font-size: 8px;">Presupuesto Oficial 2027</span>
                        </td>
                        <td style="width: 50%; text-align: center; vertical-align: middle;">
                            <div class="titulo-principal">PRESUPUESTO DE GASTO POR DESTINO</div>
                            <div style="text-align: center; font-size: 12px; margin-top: 3px;">-2027-</div>
                        </td>
                        <td style="width: 25%;" class="box-total">
                            <div class="total-label">Total Destino</div>
                            <div class="total-monto">${total_acumulado_destino:,.2f}</div>
                        </td>
                    </tr>
                </table>
                <table class="linea-institucional">
                    <tr>
                        <td><b>SECRETARÍA:</b> {sec_sel}</td>
                        <td><b>SUBSECRETARÍA:</b> {sub_sel}</td>
                        <td style="text-align: right;"><b>DESTINO:</b> {str(dest_sel).upper()}</td>
                    </tr>
                </table>
            </div>
            <table class="tabla-datos">
                <thead>
                    <tr>
                        <th>OBJETO DEL GASTO</th>
                        <th>PRESUPUESTO</th>
                        <th>F.FIN</th>
                        <th>CLASE</th>
                        <th>TIPO</th>
                        <th>FINANCIAMIENTO</th>
                    </tr>
                </thead>
                <tbody>
        """

        # Volcado dinámico de las filas con las sangrías contables intactas
        if filas_planilla:
            for f in filas_planilla:
                txt_partida = f["OBJETO DEL GASTO"]
                txt_monto = f["PRESUPUESTO"]
                es_negrita = "<b>" in txt_partida
                style_row = "font-weight: bold; background-color: #f9f9f5;" if es_negrita else ""
                
                html_imprimible += f"""
                    <tr style="{style_row}">
                        <td>{txt_partida}</td>
                        <td>{txt_monto}</td>
                        <td>{f["F.FIN"]}</td>
                        <td>{f["CLASE"]}</td>
                        <td>{f["TIPO"]}</td>
                        <td>{f["FINANCIAMIENTO"]}</td>
                    </tr>
                """

        html_imprimible += """
                </tbody>
            </table>
        </body>
        </html>
        """

        # Botón de descarga directa del documento imprimible
        st.download_button(
            label="🖨️ GENERAR Y ABRIR REPORTE IMPRIMIBLE A PDF",
            data=html_imprimible,
            file_name=f"Presupuesto_Oficial_{str(dest_sel).replace(' ', '_')}.html",
            mime="text/html",
            use_container_width=True,
            key="btn_oficial_impresion_final_centrada"
        )
        st.info("💡 Al hacer clic, se descargará el reporte optimizado. Abrilo y se desplegará en el acto la ventana de impresión para guardarlo como PDF o imprimirlo en papel, con los números centrados y las cuentas alineadas.")
