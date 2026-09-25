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

tab_formulario, tab_agregar_destino, tab_egresos, tab_registros = st.tabs([
    "📝 FORMULARIO DE REGISTRO", 
    "➕ GESTIÓN DE DESTINOS",
    "📉 EGRESOS (Reporte Tipo Sheet)",
    "📊 VER DATOS GUARDADOS"
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
    st.subheader("📊 Consulta de Reportes Presupuestarios por Destino")
    conn = sqlite3.connect(DB_NAME)
    df_egr = pd.read_sql_query("SELECT * FROM egresos_sistema", conn)
    conn.close()

    if df_egr.empty:
        st.info("No hay movimientos registrados para armar los reportes.")
    else:
        destino_seleccionado = st.selectbox("🔍 BUSCAR Y SELECCIONAR DESTINO MUNICIPAL:", options=[""] + df_egr["destino"].dropna().unique().tolist(), format_func=lambda x: "--- Elegí un destino ---" if x == "" else str(x).upper())
        if destino_seleccionado != "":
            df_f = df_egr[df_egr["destino"] == destino_seleccionado].copy()
            col_izq, col_der = st.columns(2)
            with col_izq: st.markdown(f"### 🎯 DESTINO: {str(destino_seleccionado).upper()}")
            with col_der: st.metric(label="📋 TOTAL DESTINO", value=f"${df_f['total'].sum():,.2f}")
            
            # Formato Vertical en celda escalonado
            df_f["partida_vertical"] = df_f.apply(lambda r: f"{r['objeto_gasto']}\n↳ {r['cuenta_padre']}\n  ↳ {r['cuenta_presupuestaria']}", axis=1)
            col_finalidad_rep = df_f["finalidad"] if "finalidad" in df_f.columns else df_f["financiamiento"]
            
            df_rep = pd.DataFrame({
                "PARTIDA": df_f["partida_vertical"], 
                "PRESUPUESTO": df_f["total"].map(lambda x: f"${x:,.2f}"), 
                "F.FIN": df_f["fuente_fin"], 
                "CLASE": df_f["clase"], 
                "TIPO": df_f["tipo"], 
                "FINALIDAD": col_finalidad_rep
            })
            st.dataframe(df_rep, use_container_width=True, hide_index=True)
            
            # =====================================================================
            # 📥 EXPORTADOR SEGURO CORREGIDO PARA EVITAR CAÍDAS DEL CONVERTIDOR
            # =====================================================================
            st.markdown("---")
            import io
            
            # Forzamos a que el DataFrame se procese estrictamente como texto plano sanitizado
            df_excel_seguro = df_rep.copy()
            df_excel_seguro["PARTIDA"] = df_excel_seguro["PARTIDA"].astype(str)
            
            output_excel = io.BytesIO()
            # Usamos openpyxl con parámetros de buffer crudo para saltear bloqueos de caracteres mutados
            with pd.ExcelWriter(output_excel, engine='openpyxl', mode='w') as writer:
                df_excel_seguro.to_excel(writer, index=False, sheet_name="Reporte_Egresos")
            
            excel_data = output_excel.getvalue()
            
            st.download_button(
                label=" Green 📗 Descargar Planilla Sheet en Excel (.xlsx)", 
                data=excel_data, 
                file_name=f"Planilla_{str(destino_seleccionado).replace(' ', '_')}.xlsx", 
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
                use_container_width=True,
                key=f"btn_descarga_excel_{str(destino_seleccionado).replace(' ', '_')}"
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
