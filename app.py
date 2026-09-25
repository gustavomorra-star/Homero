import sqlite3
import pandas as pd
import streamlit as st

DB_NAME = "homero_sistema.db"

def inicializar_base_datos():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. Tabla principal de Egresos
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
            financiamiento TEXT
        )
    """)
    
    # 2. Nueva tabla para registrar Destinos de forma dinámica
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS destinos_sistema (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            secretaria TEXT,
            subsecretaria TEXT,
            nombre_destino TEXT UNIQUE
        )
    """)
    
    # Insertar destinos base si la tabla está vacía para que no empiece en blanco
    cursor.execute("SELECT COUNT(*) FROM destinos_sistema")
    if cursor.fetchone()[0] == 0:
        destinos_iniciales = [
            ("SECRETARÍA DE DESARROLLO Y PROMOCIÓN DE DDHH", "SUBSECRETARÍA DE PROMOCIÓN DE DDHH", "EQUIPO DE POLITICAS DE ADULTOS MAYORES"),
            ("SECRETARÍA DE DESARROLLO Y PROMOCIÓN DE DDHH", "SUBSECRETARÍA DE PROMOCIÓN DE DDHH", "CENTRO CUIDADO INFANTIL (CAIF)"),
            ("SECRETARÍA DE GESTIÓN AMBIENTAL Y TERRITORIAL", "SUBSECRETARÍA DE AMBIENTE Y ACCIÓN CLIMÁTICA", "FONDO PLANTA DE RESIDUOS URBANOS"),
            ("SECRETARÍA DE GESTIÓN AMBIENTAL Y TERRITORIAL", "SUBSECRETARÍA DE OBRAS", "MANTENIMIENTO DE ESPACIOS PÚBLICOS"),
            ("SECRETARÍA DE GESTIÓN AMBIENTAL Y TERRITORIAL", "SUBSECRETARÍA DE AMBIENTE Y ACCIÓN CLIMÁTICA", "OBJETIVO DENGUE")
        ]
        cursor.executemany("""
            INSERT OR IGNORE INTO destinos_sistema (secretaria, subsecretaria, nombre_destino)
            VALUES (?, ?, ?)
        """, destinos_iniciales)
        
    conn.commit()
    conn.close()

inicializar_base_datos()

st.set_page_config(layout="wide")
st.title("💼 Homero - Sistema de Registro Presupuestario")
st.write("📍 Municipalidad de Sunchales | Base de Datos Dinámica")

# --- Estructura fija de Secretarías y Subsecretarías de la Municipalidad ---
MAPEO_ESTRUCTURA = {
    "SECRETARÍA DE GESTIÓN AMBIENTAL Y TERRITORIAL": ["SUBSECRETARÍA DE OBRAS", "SUBSECRETARÍA DE AMBIENTE Y ACCIÓN CLIMÁTICA"],
    "SECRETARÍA DE GOBIERNO": ["SUBSECRETARÍA DE GESTIÓN Y DESARROLLO", "SUBSECRETARÍA DE CULTURA"],
    "SECRETARÍA DE DESARROLLO Y PROMOCIÓN DE DDHH": ["SUBSECRETARÍA DE PROMOCIÓN DE DDHH", "SUBSECRETARÍA DE ECONOMÍA SOCIAL Y SOLIDARIA"],
    "AGENCIA MUNICIPAL DE SEGURIDAD": ["AGENCIA MUNICIPAL DE SEGURIDAD"],
    "INTENDENCIA": ["SUBSECRETARÍA DE HACIENDA Y FINANZAS"],
    "HCD": ["SECRETARÍA PARLAMENTARIA"]
}

opciones_secretarias = list(MAPEO_ESTRUCTURA.keys())
opciones_objetos = ["1. Gasto en personal", "2. Bienes de consumo", "3. Servicios", "4. Bienes de Uso", "5. Transferencias", "6. Activos Financieros"]
opciones_fuente_fin = ["Libre", "Afectado", "Propio", "Fondo Provincial"]
opciones_clase = ["Corriente", "Capital"]
opciones_tipo = ["Municipal", "Provincial", "Nacional"]
opciones_financiamiento = ["RTAS GLES", "FONDOS AFECTADOS"]

# Creación de Pestañas (Añadimos la de Gestión de Destinos)
tab_formulario, tab_agregar_destino, tab_registros = st.tabs([
    "📝 FORMULARIO DE REGISTRO", 
    "➕ AGREGAR DESTINOS",
    "📊 VER DATOS GUARDADOS"
])

# =====================================================================
# PESTAÑA 1: FORMULARIO PRINCIPAL DE REGISTRO (CON CRUCE DINÁMICO)
# =====================================================================
with tab_formulario:
    st.subheader("📥 Cargar Nuevo Renglón Presupuestario")
    
    col1, col2 = st.columns(2)
    with col1:
        f_sec = st.selectbox("1. SECRETARÍA:", opciones_secretarias, key="reg_sec")
        
        opciones_sub_filtradas = MAPEO_ESTRUCTURA[f_sec]
        f_sub = st.selectbox("2. SUBSECRETARÍA:", opciones_sub_filtradas, key="reg_sub")
        
        # --- CRUCE DE DATOS MÁGICO ---
        # Buscamos en la base de datos los destinos cargados para esta Secretaría y Subsecretaría exacta
        conn = sqlite3.connect(DB_NAME)
        query_destinos = "SELECT nombre_destino FROM destinos_sistema WHERE secretaria = ? AND subsecretaria = ?"
        df_destinos_db = pd.read_sql_query(query_destinos, conn, params=(f_sec, f_sub))
        conn.close()
        
        lista_destinos_disponibles = df_destinos_db["nombre_destino"].tolist()
        
        if not lista_destinos_disponibles:
            st.warning("⚠️ No hay destinos creados para esta Subsecretaría. Creá uno en la pestaña '➕ AGREGAR DESTINOS'.")
            f_dest = None
        else:
            f_dest = st.selectbox("3. DESTINO SELECCIONADO:", lista_destinos_disponibles, key="reg_dest")
        
    with col2:
        f_obj = st.selectbox("OBJETO DE GASTO:", opciones_objetos)
        f_padre = st.text_input("CUENTA PADRE (Ej: 21.1.0.0.00.000):")
        f_presup = st.text_input("DETALLE PARTIDA / IMPUTACIÓN:")

    st.markdown("---")
    col3, col4, col5 = st.columns(3)
    with col3:
        f_total = st.number_input("PRESUPUESTO / VALOR ($):", min_value=0.0, step=100.0)
        f_fuente = st.selectbox("F.FIN:", opciones_fuente_fin)
    with col4:
        f_clase = st.selectbox("CLASE:", opciones_clase)
        f_tipo = st.selectbox("TIPO:", opciones_tipo)
    with col5:
        f_finan = st.selectbox("FINANCIAMIENTO:", opciones_financiamiento)

    st.markdown("<br>", unsafe_allow_html=True)
    
    # Deshabilitar botón si no hay destino válido creado
    deshabilitar_boton = f_dest is None
    boton_guardar = st.button("💾 GUARDAR REGISTRO INMEDIATO", type="primary", use_container_width=True, disabled=deshabilitar_boton)
    
    if boton_guardar:
        if f_total > 0 and f_presup and f_dest:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO egresos_sistema 
                (secretaria, subsecretaria, destino, objeto_gasto, cuenta_padre, cuenta_presupuestaria, total, fuente_fin, clase, tipo, financiamiento)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (f_sec, f_sub, f_dest, f_obj, f_padre, f_presup, f_total, f_fuente, f_clase, f_tipo, f_finan))
            conn.commit()
            conn.close()
            st.success(f"✅ ¡Registro insertado en el destino '{f_dest}' correctamente!")
            st.rerun()
        else:
            st.error("❌ Por favor, ingresá un monto mayor a $0 y detallá la partida de imputación.")

# =====================================================================
# PESTAÑA 2: NUEVO ABM DE DESTINOS (ADMINISTRADOR DE DESTINOS)
# =====================================================================
with tab_agregar_destino:
    st.subheader("⚙️ Panel de Creación de Destinos Municipales")
    st.write("Registrá acá los destinos para que aparezcan automáticamente en las opciones del formulario principal.")
    
    col_a, col_b = st.columns(2)
    with col_a:
        d_sec = st.selectbox("Asociar a SECRETARÍA:", opciones_secretarias, key="dest_sec")
        opciones_sub_dest = MAPEO_ESTRUCTURA[d_sec]
        d_sub = st.selectbox("Asociar a SUBSECRETARÍA:", opciones_sub_dest, key="dest_sub")
        d_nombre = st.text_input("Nombre del NUEVO DESTINO (Ej: CAMINOS ESCOLARES SEGUROS):").strip().upper()
        
        boton_crear_destino = st.button("✨ Guardar Nuevo Destino", type="secondary")
        if boton_crear_destino:
            if d_nombre:
                try:
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO destinos_sistema (secretaria, subsecretaria, nombre_destino)
                        VALUES (?, ?, ?)
                    """, (d_sec, d_sub, d_nombre))
                    conn.commit()
                    conn.close()
                    st.success(f"🎯 ¡Destino '{d_nombre}' creado con éxito para la subsecretaría {d_sub}!")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("❌ Ese destino ya existe en el sistema.")
            else:
                st.error("❌ Por favor, escribí un nombre para el destino.")

    with col_b:
        st.markdown("**Destinos cargados actualmente en el sistema:**")
        conn = sqlite3.connect(DB_NAME)
        df_destinos_totales = pd.read_sql_query("SELECT secretaria, subsecretaria, nombre_destino AS [DESTINOS REGISTRADOS] FROM destinos_sistema", conn)
        conn.close()
        st.dataframe(df_destinos_totales, use_container_width=True, hide_index=True)

# =====================================================================
# PESTAÑA 3: HISTORIAL DE REGISTROS DE EGRESOS
# =====================================================================
with tab_registros:
    st.subheader("📋 Historial de Cargas Realizadas")
    conn = sqlite3.connect(DB_NAME)
    df_actual = pd.read_sql_query("SELECT * FROM egresos_sistema", conn)
    conn.close()
    if df_actual.empty:
        st.info("Todavía no se cargaron registros mediante el formulario.")
    else:
        st.dataframe(df_actual.drop(columns=["id"]), use_container_width=True, hide_index=True)

# Barra lateral
st.sidebar.header("⚙️ Herramientas")
if st.sidebar.button("⚠️ Vaciar Base de Datos Completa"):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM egresos_sistema")
    cursor.execute("DELETE FROM destinos_sistema")  # Resetea también los destinos creados
    conn.commit()
    conn.close()
    st.sidebar.success("Base de datos e historial limpios.")
    st.rerun()
