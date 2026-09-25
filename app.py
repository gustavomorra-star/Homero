import os
try:
    import openpyxl
except ImportError:
    os.system('pip install openpyxl')
import sqlite3
import pandas as pd
import streamlit as st

DB_NAME = "homero_sistema.db"

def inicializar_base_datos():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS egresos_sistema (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            secretaria TEXT, subsecretaria TEXT, destino TEXT,
            objeto_gasto TEXT, cuenta_padre TEXT, cuenta_presupuestaria TEXT,
            total REAL, fuente_fin TEXT, clase TEXT, tipo TEXT, finalidad TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS destinos_sistema (
            id INTEGER PRIMARY KEY AUTOINCREMENT, secretaria TEXT, subsecretaria TEXT, nombre_destino TEXT UNIQUE
        )
    """)
    conn.commit()
    conn.close()

inicializar_base_datos()

st.set_page_config(layout="wide", page_title="Homero Presupuesto", page_icon="🍩")
st.title("🍩 Homero - Sistema de Registro Presupuestario")
st.write("📍 Municipalidad de Sunchales | Planillas y Reportes Unificados")

# --- Plan de Cuentas Compactado Oficial ---
MAPEO_GASTOS = {
    "21.0.0.0.00.000 - Gastos de Personal": {
        "21.1.0.0.00.000 - Personal Permanente": ["21.1.1.0.00.000 - Retribución del Cargo", "21.1.4.0.00.000 - SAC", "21.1.6.0.00.000 - Contribuciones Patronales"],
        "21.2.0.0.00.000 - Personal Temporario": ["21.2.1.0.00.000 - Retribución del cargo", "21.2.3.0.00.000 - SAC Temporarios"],
        "21.3.0.0.00.000 - Servicios extraordinarios": ["21.3.1.0.00.000 - Horas Extra"],
        "21.8.0.0.00.000 - Personal Contratado": ["21.8.1.0.00.000 - Retribuciones por contratos"]
    },
    "22.0.0.0.00.000 - Bienes de consumo": {
        "22.1.0.0.00.000 - Productos alimenticios": ["22.1.1.0.00.000 - Alimentos para personas"],
        "22.3.0.0.00.000 - Productos de papel y cartón": ["22.3.1.0.00.000 - Papel de escritorio"],
        "22.5.0.0.00.000 - Productos químicos y combustibles": ["22.5.6.0.00.000 - Combustibles y lubricantes"],
        "22.9.0.0.00.000 - Otros bienes de consumo": ["22.9.1.0.00.000 - Elementos de limpieza", "22.9.7.3.01.000 - Indumentaria"]
    },
    "23.0.0.0.00.000 - Servicios no personales": {
        "23.1.0.0.00.000 - Services básicos": ["23.1.1.0.00.000 - Energía Eléctrica", "23.1.2.0.00.000 - Agua"],
        "23.3.0.0.00.000 - Mantenimiento y limpieza": ["23.3.1.0.00.000 - Mantenimiento de edificios", "23.3.9.1.01.000 - Corte de pasto"],
        "23.4.0.0.00.000 - Servicios técnicos y profesionales": ["23.4.3.0.00.000 - Jurídicos", "23.4.9.2.00.000 - Servicio de Escribanía"],
        "23.7.0.0.00.000 - Pasajes y viáticos": ["23.7.2.0.00.000 - Viáticos", "23.7.3.0.00.000 - Peajes"]
    },
    "24.0.0.0.00.000 - Bienes de uso": {
        "24.2.0.0.00.000 - Construcciones": ["24.2.1.1.01.000 - Materiales de Construcción", "24.2.1.1.02.000 - Mano de Obra"],
        "24.3.0.0.00.000 - Maquinaria y equipo": ["24.3.2.1.00.000 - Obras Menores 2024", "24.3.6.1.00.000 - Computación"]
    },
    "25.0.0.0.00.000 - Transferencias": {
        "25.1.0.0.00.000 - Gastos Corrientes Privados": ["25.1.4.1.01.000 - Viáticos Salud", "25.1.4.4.00.000 - Boleto Educativo"],
        "25.2.0.0.00.000 - Gastos de Capital Privados": ["25.2.4.5.03.000 - B. Sancor", "25.2.4.8.01.000 - Barrio Centro"],
        "25.7.0.0.00.000 - Provinciales y Municipales": ["25.7.6.1.00.000 - Concejo Municipal", "25.7.9.1.00.000 - SAMCO"]
    },
    "26.0.0.0.00.000 - Activos financieros": {
        "26.2.0.0.00.000 - Prestamos CP": ["26.2.1.4.00.000 - Préstamos a Pymes"],
        "26.5.0.0.00.000 - Incremento disponibilidades": ["26.5.1.0.00.000 - Incremento de Caja y Bancos"]
    },
    "4 - GASTOS - PARTIDAS NO PRESUPUESTARIAS": {
        "41.1.0.0.00.000 - Gastos No presupuestarios": ["41.1.1.1.00.000 - DEVOLUCIONES"]
    }
}

MAPEO_ESTRUCTURA = {
    "SECRETARÍA DE GESTIÓN AMBIENTAL Y TERRITORIAL": ["SUBSECRETARÍA DE OBRAS", "SUBSECRETARÍA DE AMBIENTE Y ACCIÓN CLIMÁTICA"],
    "SECRETARÍA DE GOBIERNO": ["SUBSECRETARÍA DE GESTIÓN Y DESARROLLO"],
    "SECRETARÍA DE DESARROLLO Y PROMOCIÓN DE DDHH": ["SUBSECRETARÍA DE PROMOCIÓN DE DDHH", "SUBSECRETARÍA DE CULTURA"],
    "SECRETARÍA DE PRODUCCIÓN Y EMPLEO": ["SUBSECRETARÍA DE DESARROLLO ECONÓMICO Y PRODUCTIVO", "SUBSECRETARÍA DE ECONOMÍA SOCIAL Y SOLIDARIA"],
    "AGENCIA MUNICIPAL DE SEGURIDAD": ["AGENCIA MUNICIPAL DE SEGURIDAD"],
    "INTENDENCIA": ["INTENDENCIA"],
    "SUBSECRETARÍA DE HACIENDA Y FINANZAS": ["SUBSECRETARÍA DE HACIENDA Y FINANZAS"],
    "HCD": ["HCD"]
}

opciones_secretarias = list(MAPEO_ESTRUCTURA.keys())
opciones_objetos = list(MAPEO_GASTOS.keys())
opciones_fuente_fin = ["Municipal", "Provincial", "Nacional"]
opciones_clase = ["Corriente", "Capital"]
opciones_tipo = ["Libre", "Afectado"]
opciones_finalidad = ["Legislativa", "Salud"]

tab_formulario, tab_agregar_destino, tab_egresos, tab_registros, tab_oficial = st.tabs([
    "📝 FORMULARIO DE REGISTRO", 
    "➕ GESTIÓN DE DESTINOS",
    "📉 EGRESOS (Reporte Tipo Sheet)",
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

        # 1. REPRODUCCIÓN DEL ENCABEZADO SUPERIOR CON RECUADRO DE TOTAL DESTINO (PANTALLA)
        st.markdown(
            f"""
            <div style="border: 1px solid #000000; padding: 0px; border-radius: 2px; background-color: #ffffff; margin-top: 15px; margin-bottom: 20px; font-family: Arial, sans-serif;">
                <table style="width: 100%; border-collapse: collapse; margin: 0;">
                    <tr>
                        <td style="width: 25%; text-align: left; font-size: 11px; color: #555; padding: 15px; border-right: 1px solid #000000;">
                            <b>Municipalidad de Sunchales</b><br>
                            <span style="font-size: 9px; color: #777;">Presupuesto Oficial 2027</span>
                        </td>
                        <td style="width: 55%; text-align: center; padding: 15px; border-right: 1px solid #000000; vertical-align: middle;">
                            <h2 style="margin: 0; padding: 0; color: #000000; font-size: 18px; font-weight: bold;">PRESUPUESTO DE GASTO POR DESTINO</h2>
                            <h4 style="margin: 4px 0 0 0; padding: 0; font-size: 13px; font-weight: normal;">-2027-</h4>
                        </td>
                        <td style="width: 25%; text-align: center; padding: 0; margin: 0; vertical-align: middle; background-color: #f5f5f5;">
                            <div style="font-size: 13px; font-weight: bold; border-bottom: 1px solid #000000; padding: 6px 0;">Total Destino</div>
                            <div style="font-size: 18px; font-weight: bold; padding: 10px 0;">${total_acumulado_destino:,.2f}</div>
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

        # 2. PROCESAMIENTO CONTABLE ARBÓREO MATEMÁTICO (SUBTOTALES AUTOMÁTICOS)
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
                        filas_planilla.append({"OBJETO DEL GASTO": f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{fila['cuenta_presupuestaria']}", "PRESUPUESTO": f"${fila['total']:,.2f}", "F.FIN": fila["fuente_fin"], "CLASE": fila["clase"], "TIPO": fila["tipo"], "FINANCIAMIENTO": v
# 3. RENDERIZACIÓN DE LA PLANILLA EN PANTALLA
        if filas_planilla:
            st.write(pd.DataFrame(filas_planilla).to_html(escape=False, index=False), unsafe_allow_html=True)
        else:
            st.info("No hay transacciones registradas para este destino.")

        # =====================================================================
        # 📥 GENERADOR NATIVO DE PDF DIRECTO (.PDF REAL EN SOLAPA 5)
        # =====================================================================
        st.markdown("<br>", unsafe_allow_html=True)
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib import colors

            buf = io.BytesIO()
            doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=35, leftMargin=45, topMargin=35, bottomMargin=35)
            story = []
            
            sty = getSampleStyleSheet()
            L = ParagraphStyle('L', parent=sty['Normal'], fontName='Helvetica', fontSize=9, leading=11, alignment=0)
            B_L = ParagraphStyle('BL', parent=sty['Normal'], fontName='Helvetica-Bold', fontSize=9, leading=11, alignment=0)
            C = ParagraphStyle('C', parent=sty['Normal'], fontName='Helvetica', fontSize=9, leading=11, alignment=1)
            B_C = ParagraphStyle('BC', parent=sty['Normal'], fontName='Helvetica-Bold', fontSize=9, leading=11, alignment=1)
            
            # 1. Membrete Superior 2027 Calibrado
            h_data = [[
                Paragraph("<b>Municipalidad de Sunchales</b><br><font color='#555' size='7'>Presupuesto Oficial 2027</font>", L),
                Paragraph("<b>PRESUPUESTO DE GASTO POR DESTINO</b><br><font size='10'>-2027-</font>", C),
                Paragraph("<b>Total Destino</b><br><font size='12'><b>$" + f"{total_acumulado_destino:,.2f}" + "</b></font>", B_C)
            ]]
            
            # Anchos fijos en puntos para el membrete
            ancho_col_m1 = 130
            ancho_col_m2 = 255
            ancho_col_m3 = 130
            medidas_membrete = [ancho_col_m1, ancho_col_m2, ancho_col_m3]
            
            h_tab = Table(h_data, colWidths=medidas_membrete)
            h_tab.setStyle(TableStyle([
                ('BOX', (0,0), (-1,-1), 1, colors.black),
                ('INNERGRID', (0,0), (-1,-1), 0.5, colors.black),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('BACKGROUND', (2,0), (2,0), colors.HexColor('#f5f5f5')),
                ('PADDING', (0,0), (-1,-1), 8),
            ]))
            story.append(h_tab)
            story.append(Spacer(1, 8))
            
            # 2. Línea de Jurisdicciones
            m_data = [[Paragraph(f"<b>SECRETARÍA:</b> {sec_sel}", L), Paragraph(f"<b>SUBSECRETARÍA:</b> {sub_sel}", L), Paragraph(f"<b>DESTINO:</b> {str(dest_sel).upper()}", C)]]
            medidas_jurisdiccion = [185, 185, 145]
            
            m_tab = Table(m_data, colWidths=medidas_jurisdiccion)
            m_tab.setStyle(TableStyle([('BOX', (0,0), (-1,-1), 1, colors.black), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('PADDING', (0,0), (-1,-1), 5)]))
            story.append(m_tab)
            story.append(Spacer(1, 15))
            
            # 3. Encabezados de la Planilla de Cuentas
            t_data = [[Paragraph("<b>OBJETO DEL GASTO</b>", B_C), Paragraph("<b>PRESUPUESTO</b>", B_C), Paragraph("<b>F.FIN</b>", B_C), Paragraph("<b>CLASE</b>", B_C), Paragraph("<b>TIPO</b>", B_C), Paragraph("<b>FINANCIAMIENTO</b>", B_C)]]
            
            # 4. Inyección del árbol contable jerárquico al PDF
            if not df_filtrado_oficial.empty:
                for objeto, df_objeto in df_filtrado_oficial.groupby("objeto_gasto"):
                    tot_obj = df_objeto["total"].sum()
                    t_data.append([Paragraph(f"<b>{objeto}</b>", L), Paragraph(f"<b>${tot_obj:,.2f}</b>", C), "", "", "", ""])
                    
                    for padre, df_padre in df_objeto.groupby("cuenta_padre"):
                        tot_pad = df_padre["total"].sum()
                        t_data.append([Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;<b>{padre}</b>", B_L), Paragraph(f"<b>${tot_pad:,.2f}</b>", C), "", "", "", ""])
                        
                        for _, fila in df_padre.iterrows():
                            v_fin = fila["finalidad"] if "finalidad" in df_filtrado_oficial.columns else fila["financiamiento"]
                            t_data.append([
                                Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{fila['cuenta_presupuestaria']}", L),
                                Paragraph(f"${fila['total']:,.2f}", C), Paragraph(str(fila["fuente_fin"]), C),
                                Paragraph(str(fila["clase"]), C), Paragraph(str(fila["tipo"]), C), Paragraph(str(v_fin), C)
                            ])
            
            # Anchos fijos en puntos para cada columna de datos (Total: 515 puntos)
            ancho_c1 = 225
            ancho_c2 = 65
            ancho_c3 = 50
            ancho_c4 = 55
            ancho_c5 = 50
            ancho_c6 = 70
            medidas_grilla = [ancho_c1, ancho_c2, ancho_c3, ancho_c4, ancho_c5, ancho_c6]
            
            d_tab = Table(t_data, colWidths=medidas_grilla)
            d_tab.setStyle(TableStyle([
                ('LINEBELOW', (0,0), (-1,0), 1.5, colors.black),
                ('LINEBELOW', (0,1), (-1,-1), 0.5, colors.lightgrey),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('TOPPADDING', (0,0), (-1,-1), 5),
                ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ]))
            story.append(d_tab)
            
            doc.build(story)
            pdf_bytes = buf.getvalue()
            
            st.download_button(
                label="📄 DESCARGAR INFORME OFICIAL EN PDF DIRECTO",
                data=pdf_bytes,
                file_name=f"Presupuesto_Oficial_2027_{str(dest_sel).replace(' ', '_')}.pdf",
                mime="application/pdf",
                use_container_width=True,
                key="btn_pdf_directo_real_final"
            )
        except Exception as e:
            st.error("Error al compilar el archivo PDF de descarga.")
