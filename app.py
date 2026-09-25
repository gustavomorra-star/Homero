import sqlite3
import pandas as pd
import streamlit as st

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
    
    # 2. Tabla para registrar Destinos de forma dinámica (Inicia completamente vacía)
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

# Configura la pestaña del navegador con el nombre y la rosquilla de Homero
st.set_page_config(layout="wide", page_title="Homero Presupuesto", page_icon="🍩")
st.title("🍩 Homero - Sistema de Registro Presupuestario")
st.write("📍 Municipalidad de Sunchales | ¡D'oh! Presupuesto Normalizado")

# --- Plan de Cuentas fija de la Municipalidad ---
MAPEO_GASTOS = {
    "21.0.0.0.00.000 - Gastos de Personal": {
        "21.1.0.0.00.000 - Personal Permanente": [
            "21.1.1.0.00.000 - Retribución del Cargo",
            "21.1.2.0.00.000 - Retribución a personal Directivo y de control",
            "21.1.3.0.00.000 - Retribuciones que no hacen al cargo",
            "21.1.4.0.00.000 - Sueldo Anual Complementario",
            "21.1.5.1.00.000 - Aportes Personales",
            "21.1.5.2.00.000 - Aportes Sindicales",
            "21.1.6.0.00.000 - Contribuciones Patronales",
            "21.1.7.0.00.000 - Complementos",
            "21.1.8.0.00.000 - Anticipo Financiero"
        ],
        "21.2.0.0.00.000 - Personal Temporario": [
            "21.2.1.0.00.000 - Retribución del cargo",
            "21.2.2.0.00.000 - Retribuciones que no hacen al cargo",
            "21.2.3.0.00.000 - Sueldo Anual Complementario",
            "21.2.4.1.00.000 - Aportes personales",
            "21.2.4.2.00.000 - Aportes Sindicales",
            "21.2.5.0.00.000 - Contribuciones patronales",
            "21.2.6.0.00.000 - Complementos",
            "21.2.7.0.00.000 - Anticipo Financiero"
        ],
        "21.3.0.0.00.000 - Servicios extraordinarios": [
            "21.3.1.0.00.000 - Retribuciones extraordinarias",
            "21.3.2.0.00.000 - Sueldo anual complementario",
            "21.3.3.0.00.000 - Contribuciones patronales",
            "21.3.4.1.00.000 - Aportes Personales",
            "21.3.4.2.00.000 - Aportes Sindicales"
        ],
        "21.8.0.0.00.000 - Personal Contratado": [
            "21.8.1.0.00.000 - Retribuciones por contratos",
            "21.8.3.0.00.000 - Sueldo Anual Complementario",
            "21.8.5.0.00.000 - Contribuciones patronales"
        ]
    },
    "22.0.0.0.00.000 - Bienes de consumo": {
        "22.1.0.0.00.000 - Productos alimenticios agropecuarios y forestales": [
            "22.1.1.0.00.000 - Alimentos para personas",
            "22.1.2.0.00.000 - Alimentos para animales"
        ],
        "22.3.0.0.00.000 - Productos de papel, cartón e impresos": [
            "22.3.1.0.00.000 - Papel de escritorio y cartón",
            "22.3.5.0.00.000 - Libros, revistas y periódicos"
        ],
        "22.5.0.0.00.000 - Productos químicos, combustibles y lubricantes": [
            "22.5.4.0.00.000 - Insecticidas, fumigantes y otros",
            "22.5.5.0.00.000 - Tintas, Pinturas y Colorantes",
            "22.5.6.0.00.000 - Combustibles y lubricantes"
        ],
        "22.9.0.0.00.000 - Otros bienes de consumo": [
            "22.9.1.0.00.000 - Elementos de limpieza",
            "22.9.2.0.00.000 - Útiles de escritorio, oficina y eseñanza",
            "22.9.7.3.01.000 - Calzado, Guantes e Indumentaria"
        ]
    },
    "23.0.0.0.00.000 - Servicios no personales": {
        "23.1.0.0.00.000 - Servicios básicos": [
            "23.1.1.0.00.000 - Energía Eléctrica",
            "23.1.2.0.00.000 - Agua",
            "23.1.4.0.00.000 - Telefono, telex, telefax"
        ],
        "23.3.0.0.00.000 - Mantenimiento, reparación y limpieza": [
            "23.3.1.0.00.000 - Mantenimiento de edificios",
            "23.3.2.0.00.000 - Mantenimiento de vehículos",
            "23.3.5.0.00.000 - Limpieza, aseo y fumigación",
            "23.3.9.1.01.000 - Corte de pasto y desmalezado",
            "23.3.9.1.02.000 - Poda y mantenimiento de arbolado"
        ],
        "23.4.0.0.00.000 - Servicios técnicos y profesionales": [
            "23.4.2.0.00.000 - Médicos y Sanitarios",
            "23.4.3.0.00.000 - Jurídicos",
            "23.4.9.2.00.000 - Servicio de Escribanía",
            "23.4.9.3.00.000 - Servicio de Agrimensura",
            "23.4.9.4.00.000 - Servicio de Arquitectura",
            "23.4.9.6.01.000 - Servicios de Ingeniería Industrial",
            "23.4.9.6.03.000 - Servicio de Ingeniería Informática"
        ],
        "23.5.0.0.00.000 - Servicios comerciales y financieros": [
            "23.5.4.0.00.000 - Primas y gastos de seguros",
            "23.5.5.0.00.000 - Comisiones y Gastos Bancarios",
            "23.5.6.0.00.000 - Internet"
        ],
        "23.7.0.0.00.000 - Pasajes y viáticos": [
            "23.7.1.0.00.000 - Pasajes",
            "23.7.2.0.00.000 - Viáticos",
            "23.7.3.0.00.000 - Combustibles y Peajes"
        ]
    },
    "24.0.0.0.00.000 - Bienes de uso": {
        "24.2.0.0.00.000 - Construcciones": [
            "24.2.1.1.01.000 - Materiales de Construcción",
            "24.2.1.1.02.000 - Mano de Obra",
            "24.2.3.0.00.000 - Forestación"
        ],
        "24.3.0.0.00.000 - Maquinaria y equipo": [
            "24.3.2.1.00.000 - Obras Menores 2024",
            "24.3.6.1.00.000 - Equipo para computación (Fondo Propio)",
            "24.3.9.2.00.000 - Teléfonos celulares, Tablet y símil"
        ]
    },
    "25.0.0.0.00.000 - Transferencias": {
        "25.1.0.0.00.000 - Transferencias Corrientes Privadas": [
            "25.1.3.0.00.000 - Becas y Pasantías",
            "25.1.4.1.01.000 - Ayudas a Personas (Viáticos Salud)",
            "25.1.4.1.02.000 - Ayudas para Alquiler",
            "25.1.4.4.00.000 - Boleto Educativo",
            "25.1.5.1.01.000 - Fondo Asistencia Educativa Públicas",
            "25.1.7.3.00.000 - Bomberos Voluntarios",
            "25.1.7.5.01.000 - Vecinal B. Centro",
            "25.1.7.5.03.000 - Vecinal B. Sancor",
            "25.1.7.5.06.000 - Vecinal B. Moreno"
        ],
        "25.2.0.0.00.000 - Transferencias de Capital Privadas": [
            "25.2.4.5.03.000 - B. Sancor",
            "25.2.4.5.04.000 - B. Colón",
            "25.2.4.8.01.000 - Barrio Centro",
            "25.2.4.8.10.000 - Particpativo 30%"
        ],
        "25.7.0.0.00.000 - Transferencias Provinciales y Municipales": [
            "25.7.6.1.00.000 - Concejo Municipal",
            "25.7.9.1.00.000 - Transferencia S.A.M.C.O",
            "25.7.9.2.00.000 - Transferencia Policía de Santa Fe"
        ]
    },
    "26.0.0.0.00.000 - Activos financieros": {
        "26.2.0.0.00.000 - Prestamos a corto plazo": [
            "26.2.1.1.00.000 - Préstamo a Microemprendedores",
            "26.2.1.4.00.000 - Préstamos a Pymes",
            "26.2.1.6.01.001 - Préstamos Aporte Reintegrable Salud"
        ],
        "26.5.0.0.00.000 - Incremento de disponibilidades": [
            "26.5.1.0.00.000 - Incremento de Caja y Bancos"
        ]
    },
    "4 - GASTOS - PARTIDAS NO PRESUPUESTARIAS": {
        "41.1.0.0.00.000 - Gastos No presupuestarios": [
            "41.1.1.1.00.000 - DEVOLUCIONES POR INGRESO INDEBIDO"
        ]
    }
}


# --- Estructura institucional fija de la Municipalidad ---
MAPEO_ESTRUCTURA = {
    "SECRETARÍA DE GESTIÓN AMBIENTAL Y TERRITORIAL": ["SUBSECRETARÍA DE OBRAS", "SUBSECRETARÍA DE AMBIENTE Y ACCIÓN CLIMÁTICA"],
    "SECRETARÍA DE GOBIERNO": ["SUBSECRETARÍA DE GESTIÓN Y DESARROLLO"],
    "SECRETARÍA DE DESARROLLO Y PROMOCIÓN DE DDHH": ["SUBSECRETARÍA DE PROMOCIÓN DE DDHH", "SUBSECRETARÍA DE CULTURA"],
    "SECRETARÍA DE PRODUCCIÓN Y EMPLEO":["SUBSECRETARÍA DE DESARROLLO ECONÓMICO Y PRODUCTIVO","SUBSECRETARÍA DE ECONOMÍA SOCIAL Y SOLIDARIA"],
    "AGENCIA MUNICIPAL DE SEGURIDAD": ["AGENCIA MUNICIPAL DE SEGURIDAD"],
    "INTENDENCIA": ["INTENDENCIA"],
    "SUBSECRETARÍA DE HACIENDA Y FINANZAS":["SUBSECRETARÍA DE HACIENDA Y FINANZAS"],
    "HCD": ["HCD"]
}

opciones_secretarias = list(MAPEO_ESTRUCTURA.keys())
opciones_objetos = list(MAPEO_GASTOS.keys())
opciones_fuente_fin = ["Municipal", "Provincial", "Nacional"]
opciones_clase = ["Corriente", "Capital"]
opciones_tipo = ["Libre","Afectado"]
opciones_finalidad = ["Legislativa", "Salud"]

tab_formulario, tab_agregar_destino, tab_registros = st.tabs([
    "📝 FORMULARIO DE REGISTRO", 
    "➕ GESTIÓN DE DESTINOS",
    "📊 VER DATOS GUARDADOS"
])

# =====================================================================
# PESTAÑA 1: FORMULARIO PRINCIPAL DE REGISTRO (CON CRUCE DINÁMICO)
# =====================================================================
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
            INSERT INTO egresos_sistema (secretaria, subsecretaria, destino, objeto_gasto, cuenta_padre, cuenta_presupuestaria, total, fuente_fin, clase, tipo, financiamiento)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (f_sec, f_sub, f_dest, f_obj, f_padre, f_presup, f_total, f_fuente, f_clase, f_tipo, f_finalidad))
    conn.commit()
    conn.close()
    st.success("✅ ¡Renglón presupuestario guardado con éxito!")
    st.rerun()
elif boton_guardar and f_total <= 0:
    st.error("❌ Por favor, ingresá un monto presupuestario mayor a $0.")

# =====================================================================
# PESTAÑA 2: ABM DE DESTINOS DINÁMICOS DESDE CERO
# =====================================================================
with tab_agregar_destino:
    st.subheader("⚙️ Panel de Configuración de Destinos")
    st.caption("Cargá las dependencias específicas de cada área. Se guardarán en la base de datos y quedarán activas en el formulario.")
    
    col_a, col_b = st.columns([1, 1.2])
    with col_a:
        st.markdown("**➕ Registrar Nuevo Destino**")
        d_sec = st.selectbox("Asociar a SECRETARÍA:", opciones_secretarias, key="dest_sec")
        opciones_sub_dest = MAPEO_ESTRUCTURA[d_sec]
        d_sub = st.selectbox("Asociar a SUBSECRETARÍA:", opciones_sub_dest, key="dest_sub")
        d_nombre = st.text_input("Nombre del Destino (Ej: OBJETIVO DENGUE):").strip().upper()
        
        boton_crear_destino = st.button("✨ Registrar Destino", type="secondary", use_container_width=True)
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
                    st.success(f"🎯 Destino '{d_nombre}' añadido correctamente.")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("❌ Este destino ya se encuentra registrado.")
            else:
                st.error("❌ El campo de texto no puede estar vacío.")

    with col_b:
        st.markdown("**📋 Listado de Destinos Activos**")
        conn = sqlite3.connect(DB_NAME)
        df_destinos_totales = pd.read_sql_query("SELECT id, subsecretaria AS [SUBSECRETARÍA], nombre_destino AS [DESTINO] FROM destinos_sistema ORDER BY secretaria, subsecretaria", conn)
        conn.close()
        
        if df_destinos_totales.empty:
            st.info("No hay destinos creados todavía. Toda la configuración está limpia.")
        else:
            # Mostrar la tabla de consulta sin mostrar el ID técnico
            st.dataframe(df_destinos_totales.drop(columns=["id"]), use_container_width=True, hide_index=True)
            
            # Selector rápido para eliminar destinos mal cargados
            st.markdown("---")
            st.markdown("**🗑️ Eliminar un Destino**")
            destino_a_borrar = st.selectbox("Seleccioná el destino que querés remover:", df_destinos_totales["DESTINO"].tolist())
            if st.button("❌ Dar de Baja Destino", type="secondary"):
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM destinos_sistema WHERE nombre_destino = ?", (destino_a_borrar,))
                conn.commit()
                conn.close()
                st.success(f"Destino '{destino_a_borrar}' eliminado.")
                st.rerun()

# =====================================================================
# PESTAÑA 3: HISTORIAL DE REGISTROS DE EGRESOS
# =====================================================================
    st.subheader("📋 Planilla de Consulta de Datos Guardados (Formato R.A.F.A.M.)")
    st.caption("Visualización del presupuesto ejecutado y partidas agrupadas por estructura institucional.")
    
    conn = sqlite3.connect(DB_NAME)
    df_auditoria = pd.read_sql_query("SELECT * FROM egresos_sistema", conn)
    conn.close()
    
    if df_auditoria.empty:
        st.info("No hay registros cargados en el sistema actualmente.")
    else:
        # Agrupamos los datos para armar bloques limpios por Secretaría, Subsecretaría y Destino
        grupos_institucionales = df_auditoria.groupby(["secretaria", "subsecretaria", "destino"])
        
        for (sec, sub, dest), df_grupo in grupos_institucionales:
            # ENCABEZADO GRIS INSTITUCIONAL TIPO R.A.F.A.M.
            st.markdown(
                f"""
                <div style="background-color: #f0f2f6; padding: 10px; border-radius: 4px; margin-top: 20px; margin-bottom: 10px;">
                    <span style="font-weight: bold; color: #1c1d21;">🏛️ JURISDICCIÓN:</span> {sec} <br>
                    <span style="font-weight: bold; color: #1c1d21;">🏢 SUBSECRETARÍA:</span> {sub} | 
                    <span style="font-weight: bold; color: #1c1d21;">🎯 DESTINO:</span> {dest}
                </div>
                """, 
                unsafe_allow_html=True
            )
            
            # Armando la cuadrícula con las columnas contables solicitadas
            df_bloque_vista = pd.DataFrame({
                "CUENTA PADRE": df_grupo["cuenta_padre"],
                "IMPUTACIÓN / PARTIDA": df_grupo["cuenta_presupuestaria"],
                "PRESUPUESTO ($)": df_grupo["total"].map(lambda x: f"${x:,.2f}" if pd.notnull(x) else "$0.00"),
                "F.FIN": df_grupo["fuente_fin"],
                "CLASE": df_grupo["clase"],
                "TIPO": df_grupo["tipo"],
                "FINALIDAD": df_grupo["finalidad"] if "finalidad" in df_grupo.columns else df_grupo["financiamiento"]
            })
            
            # Desplegar la planilla limpia, ancha y sin números de índice
            st.dataframe(df_bloque_vista, use_container_width=True, hide_index=True)
            
            # Cálculo del subtotal del bloque con línea contable inferior
            total_del_bloque = df_grupo["total"].sum()
            st.markdown(
                f"""
                <div style="text-align: right; font-weight: bold; font-size: 16px; margin-top: 5px; margin-bottom: 25px; border-top: 1px solid #dcdcdc; padding-top: 5px;">
                    Total Destino / Jurisdicción: <span style="color: #2e7d32;">${total_del_bloque:,.2f}</span>
                </div>
                """, 
                unsafe_allow_html=True
            )
            
        # Totalizador General Histórico al fondo de la pantalla
        st.markdown("---")
        st.metric(label="📊 TOTAL GENERAL ACUMULADO EN EL SISTEMA", value=f"${df_auditoria['total'].sum():,.2f}")
