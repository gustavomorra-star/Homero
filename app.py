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
            secretaria TEXT,
            subsecretaria TEXT,
            destino TEXT,
            objeto_gasto TEXT,
            cuenta_padre TEXT,
            cuenta_presupuestaria TEXT,
            total REAL,
            fuente_fin TEXT,
            clase TEXT,
            tipo TEXT,
            finalidad TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS destinos_sistema (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            secretaria TEXT,
            subsecretaria TEXT,
            nombre_destino TEXT UNIQUE
        )
    """)
    conn.commit()
    conn.close()

inicializar_base_datos()

st.set_page_config(layout="wide", page_title="Homero Presupuesto", page_icon="🍩")
st.title("🍩 Homero - Sistema de Registro Presupuestario")
st.write("📍 Municipalidad de Sunchales | Formato Oficial Adaptado")

MAPEO_GASTOS = {
    "21.0.0.0.00.000 - Gastos de Personal": {
        "21.1.0.0.00.000 - Personal Permanente": ["21.1.1.0.00.000 - Retribución del Cargo", "21.1.2.0.00.000 - Personal Directivo", "21.1.4.0.00.000 - SAC", "21.1.6.0.00.000 - Contribuciones Patronales"],
        "21.2.0.0.00.000 - Personal Temporario": ["21.2.1.0.00.000 - Retribución del cargo", "21.2.3.0.00.000 - SAC Temporarios", "21.2.5.0.00.000 - Contribuciones"],
        "21.3.0.0.00.000 - Servicios extraordinarios": ["21.3.1.0.00.000 - Horas Extra", "21.3.2.0.00.000 - SAC Extra"],
        "21.8.0.0.00.000 - Personal Contratado": ["21.8.1.0.00.000 - Retribuciones por contratos", "21.8.5.0.00.000 - Contribuciones"]
    },
    "22.0.0.0.00.000 - Bienes de consumo": {
        "22.1.0.0.00.000 - Productos alimenticios": ["22.1.1.0.00.000 - Alimentos para personas", "22.1.2.0.00.000 - Alimentos para animales"],
        "22.3.0.0.00.000 - Productos de papel y cartón": ["22.3.1.0.00.000 - Papel de escritorio", "22.3.5.0.00.000 - Libros y revistas"],
        "22.5.0.0.00.000 - Químicos, combustibles y lubricantes": ["22.5.4.0.00.000 - Insecticidas", "22.5.6.0.00.000 - Combustibles y lubricantes"],
        "22.9.0.0.00.000 - Otros bienes de consumo": ["22.9.1.0.00.000 - Elementos de limpieza", "22.9.2.0.00.000 - Útiles de escritorio", "22.9.7.3.01.000 - Indumentaria"]
    },
    "23.0.0.0.00.000 - Servicios no personales": {
        "23.1.0.0.00.000 - Servicios básicos": ["23.1.1.0.00.000 - Energía Eléctrica", "23.1.2.0.00.000 - Agua", "23.1.4.0.00.000 - Teléfono"],
        "23.3.0.0.00.000 - Mantenimiento y limpieza": ["23.3.1.0.00.000 - Mantenimiento edificios", "23.3.2.0.00.000 - Reparación vehículos", "23.3.9.1.01.000 - Corte de pasto"],
        "23.4.0.0.00.000 - Servicios técnicos y profesionales": ["23.4.3.0.00.000 - Jurídicos", "23.4.9.2.00.000 - Escribanía", "23.4.9.4.00.000 - Arquitectura", "23.4.9.6.04.000 - Ingeniería Civil"],
        "23.5.0.0.00.000 - Servicios comerciales": ["23.5.4.0.00.000 - Primas de seguros", "23.5.5.0.00.000 - Gastos Bancarios"],
        "23.7.0.0.00.000 - Pasajes y viáticos": ["23.7.1.0.00.000 - Pasajes", "23.7.2.0.00.000 - Viáticos", "23.7.3.0.00.000 - Peajes"]
    },
    "24.0.0.0.00.000 - Bienes de uso": {
        "24.2.0.0.00.000 - Construcciones": ["24.2.1.1.01.000 - Materiales", "24.2.1.1.02.000 - Mano de Obra", "24.2.3.0.00.000 - Forestación"],
        "24.3.0.0.00.000 - Maquinaria y equipo": ["24.3.2.1.00.000 - Obras Menores 2024", "24.3.6.1.00.000 - Computación", "24.3.9.2.00.000 - Celulares y Tablets"]
    },
    "25.0.0.0.00.000 - Transferencias": {
        "25.1.0.0.00.000 - Transferencias Corrientes": ["25.1.4.1.01.000 - Viáticos Salud", "25.1.4.4.00.000 - Boleto Educativo", "25.1.5.1.01.000 - FAE", "25.1.7.5.01.000 - Vecinal Centro"],
        "25.2.0.0.00.000 - Transferencias de Capital": ["25.2.4.5.03.000 - B. Sancor", "25.2.4.5.04.000 - B. Colón", "25.2.4.8.10.000 - Participativo 30%"],
        "25.7.0.0.00.000 - Provinciales y Municipales": ["25.7.6.1.00.000 - Concejo Municipal", "25.7.9.1.00.000 - SAMCO", "25.7.9.2.00.000 - Policía"]
    },
    "26.0.0.0.00.000 - Activos financieros": {
        "26.2.0.0.00.000 - Prestamos CP": ["26.2.1.1.00.000 - Microemprendedores", "26.2.1.4.00.000 - Pymes"],
        "26.5.0.0.00.000 - Incremento disponibilidades": ["26.5.1.0.00.000 - Caja y Bancos"]
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
    "📊 VER DATOS GUARDADOS (R.A.F.A.M.)"
])
with tab_formulario:
    st.subheader("📥 Cargar Nuevo Renglón Presupuestario")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**📍 1. Ubicación Institucional**")
        f_sec = st.selectbox("SECRETARÍA:", options=[""] + opciones_secretarias, format_func=lambda x: "--- Seleccioná ---" if x == "" else x, key="reg_sec")
        if f_sec != "":
            f_sub = st.selectbox("SUBSECRETARÍA:", options=[""] + MAPEO_ESTRUCTURA[f_sec], format_func=lambda x: "--- Seleccioná ---" if x == "" else x, key="reg_sub")
            if f_sub != "":
                conn = sqlite3.connect(DB_NAME)
                df_d = pd.read_sql_query("SELECT nombre_destino FROM destinos_sistema WHERE secretaria = ? AND subsecretaria = ?", conn, params=(f_sec, f_sub))
                conn.close()
                lista_d = df_d["nombre_destino"].tolist()
                f_dest = st.selectbox("DESTINO SELECCIONADO:", options=[""] + lista_d, format_func=lambda x: "--- Seleccioná ---" if x == "" else str(x).upper(), key="reg_dest") if lista_d else None
                if not lista_d: st.warning("⚠️ Sin destinos creados para esta área.")
            else: f_dest = None
        else: f_sub, f_dest = "", None
    with col2:
        st.markdown("**📊 2. Imputación de Partida**")
        f_obj = st.selectbox("OBJETO DE GASTO:", options=[""] + opciones_objetos, format_func=lambda x: "--- Seleccioná ---" if x == "" else x, key="reg_obj")
        if f_obj != "":
            f_padre = st.selectbox("CUENTA PADRE:", options=[""] + list(MAPEO_GASTOS[f_obj].keys()), format_func=lambda x: "--- Seleccioná ---" if x == "" else x, key="reg_padre")
            f_presup = st.selectbox("PARTIDA:", options=[""] + MAPEO_GASTOS[f_obj][f_padre], format_func=lambda x: "--- Seleccioná ---" if x == "" else x, key="reg_presup") if f_padre != "" else ""
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

    campos_completos = (f_sec != "") and (f_sub != "") and (f_dest != "" and f_dest is not None) and (f_obj != "") and (f_padre != "") and (f_presup != "") and (f_fuente != "") and (f_clase != "") and (f_tipo != "") and (f_finalidad != "")
    if st.button("💾 GUARDAR REGISTRO INMEDIATO", type="primary", use_container_width=True, disabled=not campos_completos) and f_total > 0:
        conn = sqlite3.connect(DB_NAME)
        conn.cursor().execute("INSERT INTO egresos_sistema (secretaria, subsecretaria, destino, objeto_gasto, cuenta_padre, cuenta_presupuestaria, total, fuente_fin, clase, tipo, finalidad) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (f_sec, f_sub, f_dest, f_obj, f_padre, f_presup, f_total, f_fuente, f_clase, f_tipo, f_finalidad))
        conn.commit()
        conn.close()
        st.success("✅ ¡Renglón presupuestario guardado con éxito!")
        st.rerun()

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
                conn.cursor().execute("INSERT INTO destinos_sistema (secretaria, subsecretaria, nombre_destino) VALUES (?, ?, ?)", (d_sec, d_sub, d_nombre))
                conn.commit()
                conn.close()
                st.success("🎯 Destino añadido correctamente.")
                st.rerun()
            except sqlite3.IntegrityError: st.error("❌ Este destino ya existe.")
    with col_b:
        conn = sqlite3.connect(DB_NAME)
        df_dt = pd.read_sql_query("SELECT subsecretaria AS [SUBSECRETARÍA], nombre_destino AS [DESTINO] FROM destinos_sistema ORDER BY secretaria", conn)
        conn.close()
        if not df_dt.empty: st.dataframe(df_dt, use_container_width=True, hide_index=True)

with tab_egresos:
    st.subheader("📊 Consulta de Reportes Presupuestarios por Destino")
    conn = sqlite3.connect(DB_NAME)
    df_egr = pd.read_sql_query("SELECT * FROM egresos_sistema", conn)
    conn.close()
    if df_egr.empty: st.info("No hay movimientos registrados para armar los reportes.")
    else:
        destino_seleccionado = st.selectbox("🔍 BUSCAR Y SELECCIONAR DESTINO:", options=[""] + df_egr["destino"].dropna().unique().tolist(), format_func=lambda x: "--- Elegí un destino ---" if x == "" else str(x).upper())
        if destino_seleccionado != "":
            df_f = df_egr[df_egr["destino"] == destino_seleccionado]
            col_izq, col_der = st.columns(2)
            with col_izq: st.markdown(f"### 🎯 DESTINO: {str(destino_seleccionado).upper()}")
            with col_der: st.metric(label="📋 TOTAL DESTINO", value=f"${df_f['total'].sum():,.2f}")
            df_rep = pd.DataFrame({"CUENTA PADRE": df_f["cuenta_padre"], "PARTIDA": df_f["cuenta_presupuestaria"], "PRESUPUESTO": df_f["total"].map(lambda x: f"${x:,.2f}"), "F.FIN": df_f["fuente_fin"], "CLASE": df_f["clase"], "TIPO": df_f["tipo"], "FINALIDAD": df_f["finalidad"]})
            st.dataframe(df_rep, use_container_width=True, hide_index=True)

with tab_registros:
st.subheader("📋 Planilla de Consulta de Datos Guardados")
conn = sqlite3.connect(DB_NAME)
df_auditoria = pd.read_sql_query("SELECT * FROM egresos_sistema", conn)
conn.close()
if df_auditoria.empty: st.info("No hay registros.")
else:
    for (sec, sub, dest), df_grupo in df_auditoria.groupby(["secretaria", "subsecretaria", "destino"]):
        st.markdown(f'<div style="background-color: #f0f2f6; padding: 10px; border-radius: 4px; margin-top: 15px;"><b>🏛️ JURISDICCIÓN:</b> {sec}<br><b>🏢 SUBSEC:</b> {sub} | <b>🎯 DESTINO:</b> {dest}</div>', unsafe_allow_html=True)
        col_finalidad = df_grupo["finalidad"] if "finalidad" in df_grupo.columns else df_grupo["financiamiento"]
        df_bloque_vista = pd.DataFrame({"CUENTA PADRE": df_grupo["cuenta_padre"], "PARTIDA": df_grupo["cuenta_presupuestaria"], "PRESUPUESTO ($)": df_grupo["total"].map(lambda x: f"${x:,.2f}"), "F.FIN": df_grupo["fuente_fin"], "CLASE": df_grupo["clase"], "TIPO": df_grupo["tipo"], "FINALIDAD": col_finalidad})
        st.dataframe(df_bloque_vista, use_container_width=True, hide_index=True)
        st.markdown(f'<div style="text-align: right; font-weight: bold; border-top: 1px solid #dcdcdc; padding-top: 5px; margin-bottom: 15px;">Total Destino: <span style="color: #2e7d32;">${df_grupo["total"].sum():,.2f}</span></div>', unsafe_allow_html=True)
    st.markdown("---")
    st.metric(label="📊 TOTAL GENERAL ACUMULADO", value=f"${df_auditoria['total'].sum():,.2f}")

