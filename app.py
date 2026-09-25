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
            financiamiento TEXT
        )
    """)
    conn.commit()
    conn.close()

inicializar_base_datos()

st.set_page_config(layout="wide")
st.title("💼 Homero - Sistema de Registro Presupuestario")
st.write("📍 Municipalidad de Sunchales | Filtros en Cascada")

# =====================================================================
# 🗂️ MAPEO COMPLETO EN CASCADA (Secretaría -> Subsecretaría -> Destinos)
# =====================================================================
# Modificá los nombres entre comillas acá abajo para armar tu estructura real:
ESTRUCTURA_CASCADA = {
    "SECRETARÍA DE GESTIÓN AMBIENTAL Y TERRITORIAL": {
        "SUBSECRETARÍA DE OBRAS": [
            "N/N",
        
        ],
        "SUBSECRETARÍA DE AMBIENTE Y ACCIÓN CLIMÁTICA": [
            "FONDO PLANTA DE RESIDUOS URBANOS",
            "PIGA - CONTROL DE PLAGAS",
            "OBJETIVO DENGUE"
        ]
    },
    "SECRETARÍA DE GOBIERNO": {
        "SUBSECRETARÍA DE GESTIÓN Y DESARROLLO": [
            " ",
            " "
        ],
      
    },
    "SECRETARÍA DE DESARROLLO Y PROMOCIÓN DE DDHH": {
        "SUBSECRETARÍA DE PROMOCIÓN DE DDHH": [
            "EQUIPO DE POLITICAS DE ADULTOS MAYORES",
            "CENTRO CUIDADO INFANTIL (CAIF)"
        ],
          "SUBSECRETARÍA DE CULTURA": [
            "EVENTOS CULTURALES MUNICIPALES",
            "TALLERES LICEO"
        ]
    },
    "SECRETARÍA DE PRODUCCIÓN Y EMPLEO":{
        "SUBSECRETARÍA DE ECONOMÍA SOCIAL Y SOLIDARIA": [
            "APOYO A EMPRENDEDORES",
            "HUERTAS COMUNITARIAS"
        ],
        "SUBSECRETARÍA DE DESARROLLO ECONÓMICO Y PRODUCTIVO":[
            "CASA DEL EMPRENDEDOR",
            "TURISMO",
        ]
    },
    "AGENCIA MUNICIPAL DE SEGURIDAD": {
        "AGENCIA MUNICIPAL DE SEGURIDAD": [
            "CAMINOS ESCOLARES SEGUROS",
            "MONITOREO URBANO"
        ]
    },
    "INTENDENCIA": {
        "INTENDENCIA":[
            "INTENDENCIA"
        ]
    },
    "SUBSECRETARÍA DE HACIENDA Y FINANZAS":{
        "SUBSECRETARÍA DE HACIENDA Y FINANZAS": [
            "SUBSECRETARÍA DE HACIENDA Y FINANZAS",
            "COMPRAS Y CONTRATACIONES",
        ]
    }
}

# Opciones fijas del resto del formulario
opciones_objetos = ["1. Gasto en personal", "2. Bienes de consumo", "3. Servicios", "4. Bienes de Uso", "5. Transferencias", "6. Activos Financieros"]
opciones_fuente_fin = ["Libre", "Afectado", "Propio", "Fondo Provincial"]
opciones_clase = ["Corriente", "Capital"]
opciones_tipo = ["Municipal", "Provincial", "Nacional"]
opciones_financiamiento = ["RTAS GLES", "FONDOS AFECTADOS"]

tab_formulario, tab_registros = st.tabs(["📝 FORMULARIO DE REGISTRO", "📊 VER DATOS GUARDADOS"])

with tab_formulario:
    st.subheader("📥 Cargar Nuevo Renglón Presupuestario")
    
    col1, col2 = st.columns(2)
    with col1:
        # 1. Elegir Secretaría
        f_sec = st.selectbox("1. SECRETARÍA:", list(ESTRUCTURA_CASCADA.keys()))
        
        # 2. Filtrar Subsecretarías según la Secretaría elegida
        diccionario_subsecretarias = ESTRUCTURA_CASCADA[f_sec]
        f_sub = st.selectbox("2. SUBSECRETARÍA:", list(diccionario_subsecretarias.keys()))
        
        # 3. Filtrar Destinos según la Subsecretaría elegida
        lista_destinos_filtrados = diccionario_subsecretarias[f_sub]
        f_dest = st.selectbox("3. DESTINO:", lista_destinos_filtrados)
        
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
    boton_guardar = st.button("💾 GUARDAR REGISTRO INMEDIATO", type="primary", use_container_width=True)
    
    if boton_guardar:
        if f_total > 0 and f_presup:
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

with tab_registros:
    st.subheader("📋 Historial de Cargas Realizadas")
    conn = sqlite3.connect(DB_NAME)
    df_actual = pd.read_sql_query("SELECT * FROM egresos_sistema", conn)
    conn.close()
    if df_actual.empty:
        st.info("Todavía no se cargaron registros mediante el formulario.")
    else:
        st.dataframe(df_actual.drop(columns=["id"]), use_container_width=True, hide_index=True)

st.sidebar.header("⚙️ Herramientas")
if st.sidebar.button("⚠️ Vaciar Base de Datos Completa"):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM egresos_sistema")
    conn.commit()
    conn.close()
    st.sidebar.success("Base de datos reseteada con éxito.")
    st.rerun()
