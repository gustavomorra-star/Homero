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

st.set_page_config(layout="wide")
st.title("💼 Homero - Sistema de Registro Presupuestario")
st.write("📍 Municipalidad de Sunchales | Base de Datos Limpia de Cero")

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
with tab_formulario:
    st.subheader("📥 Cargar Nuevo Renglón Presupuestario")
    
    col1, col2 = st.columns(2)
    with col1:
        f_sec = st.selectbox("1. SECRETARÍA:", opciones_secretarias, key="reg_sec")
        
        opciones_sub_filtradas = MAPEO_ESTRUCTURA[f_sec]
        f_sub = st.selectbox("2. SUBSECRETARÍA:", opciones_sub_filtradas, key="reg_sub")
        
        # Consulta dinámica a la base de datos
        conn = sqlite3.connect(DB_NAME)
        query_destinos = "SELECT nombre_destino FROM destinos_sistema WHERE secretaria = ? AND subsecretaria = ?"
        df_destinos_db = pd.read_sql_query(query_destinos, conn, params=(f_sec, f_sub))
        conn.close()
        
        lista_destinos_disponibles = df_destinos_db["nombre_destino"].tolist()
        
        if not lista_destinos_disponibles:
            st.warning("⚠️ No hay destinos creados para esta Subsecretaría. Registralo primero en la pestaña '➕ GESTIÓN DE DESTINOS'.")
            f_dest = None
        else:
            f_dest = st.selectbox("3. DESTINO SELECCIONADO:", lista_destinos_disponibles, key="reg_dest")
        
    with col2:
        f_obj = st.selectbox("OBJETO DE GASTO:", opciones_objetos, key="reg_obj")
        f_padre = st.selectbox("CUENTA PADRE:", list(MAPEO_GASTOS[f_obj].keys()), key="reg_padre")
        f_presup = st.selectbox("CUENTA DE IMPUTACIÓN / PARTIDA:", MAPEO_GASTOS[f_obj][f_padre], key="reg_presup")


    st.markdown("---")
    col3, col4, col5 = st.columns(3)
    with col3:
        f_total = st.number_input("PRESUPUESTO / VALOR ($):", min_value=0.0, step=100.0)
        f_fuente = st.selectbox("F.FIN:", opciones_fuente_fin)
    with col4:
        f_clase = st.selectbox("CLASE:", opciones_clase)
        f_tipo = st.selectbox("TIPO:", opciones_tipo)
    with col5:
        f_finan = st.selectbox("FINALIDAD:", opciones_finalidad)

    st.markdown("<br>", unsafe_allow_html=True)
    
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
    st.subheader("📋 Panel de Control y Modificación de Cargas")
    
    conn = sqlite3.connect(DB_NAME)
    df_auditoria = pd.read_sql_query("SELECT * FROM egresos_sistema", conn)
    conn.close()
    
    if df_auditoria.empty:
        st.info("No hay registros en la base de datos para modificar.")
    else:
        st.markdown("**1. Elegí el registro que querés Corregir o Eliminar:**")
        # Generar una línea descriptiva por fila para identificarla fácil en la lista
        df_auditoria["Visualizar"] = df_auditoria.apply(
            lambda r: f"ID: {r['id']} | Destino: {r['destino']} | Partida: {str(r['cuenta_presupuestaria'])[:30]}... | Monto: ${r['total']:,.2f}", axis=1
        )
        
        opciones_lineas = df_auditoria["Visualizar"].tolist()
        linea_seleccionada = st.selectbox("Seleccioná un movimiento de la lista:", opciones_lineas)
        
        # Extraer los datos reales de la fila elegida para precargarlos
        fila_real = df_auditoria[df_auditoria["Visualizar"] == linea_seleccionada].iloc[0]
        id_registro = int(fila_real["id"])
        
        st.markdown("---")
        st.markdown(f"🛠️ **Formulario de Corrección para el ID: {id_registro}**")
        
        # Cuadrícula para editar los valores en caliente
        col_ed1, col_ed2, col_ed3 = st.columns(3)
        with col_ed1:
            nuevo_total = st.number_input("Corregir Monto ($):", min_value=0.0, value=float(fila_real["total"]), key=f"tot_{id_registro}")
            nueva_fuente = st.selectbox("Cambiar F.Fin:", opciones_fuente_fin, index=opciones_fuente_fin.index(fila_real["fuente_fin"]) if fila_real["fuente_fin"] in opciones_fuente_fin else 0)
        with col_ed2:
            nueva_clase = st.selectbox("Cambiar Clase:", opciones_clase, index=opciones_clase.index(fila_real["clase"]) if fila_real["clase"] in opciones_clase else 0)
            nuevo_tipo = st.selectbox("Cambiar Tipo:", opciones_tipo, index=opciones_tipo.index(fila_real["tipo"]) if fila_real["tipo"] in opciones_tipo else 0)
        with col_ed3:
            nuevo_finan = st.selectbox("Cambiar Finalidad:", opciones_finalidad, index=opciones_finalidad.index(fila_real["finalidad"]) if fila_real["finalidad"] in opciones_finalidad else 0)
            
        st.markdown("<br>", unsafe_allow_html=True)
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            if st.button("🔄 ACTUALIZAR REGISTRO", type="primary", use_container_width=True):
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE egresos_sistema 
                    SET total = ?, fuente_fin = ?, clase = ?, tipo = ?, financiamiento = ?
                    WHERE id = ?
                """, (nuevo_total, nueva_fuente, nueva_clase, nuevo_tipo, nuevo_finan, id_registro))
                conn.commit()
                conn.close()
                st.success(f"✅ ¡ID {id_registro} actualizado correctamente!")
                st.rerun()
                
        with col_btn2:
            if st.button("🗑️ ELIMINAR REGISTRO TOTALMENTE", type="secondary", use_container_width=True):
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM egresos_sistema WHERE id = ?", (id_registro,))
                conn.commit()
                conn.close()
                st.warning(f"💥 El registro ID {id_registro} fue eliminado del sistema.")
                st.rerun()
