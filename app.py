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
st.write("📍 Municipalidad de Sunchales | Formato Oficial Adaptado de Google Sheets")

opciones_secretarias = [
    "SECRETARÍA DE DESARROLLO Y PROMOCIÓN DE DDHH",
    "AGENCIA MUNICIPAL DE SEGURIDAD",
    "SECRETARÍA DE GESTIÓN AMBIENTAL Y TERRITORIAL",
    "SECRETARÍA DE GOBIERNO",
    "INTENDENCIA",
    "HCD"
]

opciones_subsecretarias = [
    "SUBSECRETARÍA DE PROMOCIÓN DE DDHH",
    "AGENCIA MUNICIPAL DE SEGURIDAD",
    "SUBSECRETARÍA DE AMBIENTE Y ACCIÓN CLIMÁTICA",
    "SUBSECRETARÍA DE GESTIÓN Y DESARROLLO",
    "SUBSECRETARÍA DE HACIENDA Y FINANZAS",
    "SUBSECRETARÍA DE CULTURA"
]

opciones_destinos = [
    "EQUIPO DE POLITICAS DE ADULTOS MAYORES",
    "CENTRO CUIDADO INFANTIL",
    "FONDO PLANTA DE RESIDUOS URBANOS",
    "MANTENIMIENTO DE ESPACIOS PÚBLICOS",
    "OBJETIVO DENGUE"
]

opciones_objetos = [
    "1. Gasto en personal", 
    "2. Bienes de consumo", 
    "3. Servicios", 
    "4. Bienes de Uso", 
    "5. Transferencias",
    "6. Activos Financieros"
]

opciones_fuente_fin = ["Libre", "Afectado", "Propio", "Fondo Provincial"]
opciones_clase = ["Corriente", "Capital"]
opciones_tipo = ["Municipal", "Provincial", "Nacional"]
opciones_financiamiento = ["RTAS GLES", "FONDOS AFECTADOS"]

tab_carga, tab_egresos, tab_caif, tab_recursos = st.tabs([
    "📝 EDICIÓN TIPO SHEET",
    "📉 EGRESOS (Reporte Formateado)",
    "🧸 CAIF",
    "💰 RECURSOS"
])

with tab_carga:
    st.subheader("📊 Hoja de Trabajo en Vivo")
    conn = sqlite3.connect(DB_NAME)
    df_actual = pd.read_sql_query("SELECT * FROM egresos_sistema", conn)
    conn.close()

    config_columnas = {
        "id": None,
        "secretaria": st.column_config.SelectboxColumn("Secretaría", options=opciones_secretarias, width="medium"),
        "subsecretaria": st.column_config.SelectboxColumn("Subsecretaría", options=opciones_subsecretarias, width="medium"),
        "destino": st.column_config.SelectboxColumn("Destino", options=opciones_destinos, width="medium"),
        "objeto_gasto": st.column_config.SelectboxColumn("Objeto del Gasto", options=opciones_objetos, width="small"),
        "cuenta_padre": st.column_config.TextColumn("Cuenta Padre / Imputación", width="large"),
        "cuenta_presupuestaria": st.column_config.TextColumn("Detalle Partida", width="large"),
        "total": st.column_config.NumberColumn("Presupuesto ($)", min_value=0.0, format="$%.2f", width="small"),
        "fuente_fin": st.column_config.SelectboxColumn("F.Fin", options=opciones_fuente_fin, width="small"),
        "clase": st.column_config.SelectboxColumn("Clase", options=opciones_clase, width="small"),
        "tipo": st.column_config.SelectboxColumn("Tipo", options=opciones_tipo, width="small"),
        "financiamiento": st.column_config.SelectboxColumn("Financiamiento", options=opciones_financiamiento, width="small"),
    }

    datos_editados = st.data_editor(
        df_actual,
        column_config=config_columnas,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic"
    )

    if st.button("💾 Guardar y Sincronizar Cambios", type="primary"):
        conn = sqlite3.connect(DB_NAME)
        datos_editados.to_sql("egresos_sistema", conn, if_exists="replace", index=False)
        conn.commit()
        conn.close()
        st.success("¡Datos guardados con éxito!")
        st.rerun()

with tab_egresos:
    conn = sqlite3.connect(DB_NAME)
    df_egr = pd.read_sql_query("SELECT * FROM egresos_sistema", conn)
    conn.close()

    if df_egr.empty:
        st.info("La planilla de carga no tiene registros activos.")
    else:
        destinos_unicos = df_egr["destino"].dropna().unique()
        for dest in destinos_unicos:
            df_destino_filtrado = df_egr[df_egr["destino"] == dest]
            sec_nombre = df_destino_filtrado["secretaria"].iloc[0] if not df_destino_filtrado["secretaria"].empty and pd.notnull(df_destino_filtrado["secretaria"].iloc[0]) else "N/A"
            sub_nombre = df_destino_filtrado["subsecretaria"].iloc[0] if not df_destino_filtrado["subsecretaria"].empty and pd.notnull(df_destino_filtrado["subsecretaria"].iloc[0]) else "N/A"
            total_presupuesto = df_destino_filtrado["total"].sum()

            st.markdown("---")
            col_izq, col_der = st.columns([3, 1])
            with col_izq:
                st.markdown(f"**SECRETARÍA:** {sec_nombre}")
                st.markdown(f"**SUBSECRETARÍA:** {sub_nombre}")
                st.markdown(f"### 🎯 DESTINO: {str(dest).upper()}")
            with col_der:
                st.metric(label="💰 TOTAL DESTINO", value=f"${total_presupuesto:,.2f}")

            df_reporte = pd.DataFrame({
                "OBJETO DEL GASTO": df_destino_filtrado["objeto_gasto"],
                "CUENTA PADRE / IMPUTACIÓN": df_destino_filtrado["cuenta_padre"],
                "DETALLE PARTIDA": df_destino_filtrado["cuenta_presupuestaria"],
                "PRESUPUESTO": df_destino_filtrado["total"].map(lambda x: f"${x:,.2f}" if pd.notnull(x) else "$0.00"),
                "F.FIN": df_destino_filtrado["fuente_fin"],
                "CLASE": df_destino_filtrado["clase"],
                "TIPO": df_destino_filtrado["tipo"],
                "FINANCIAMIENTO": df_destino_filtrado["financiamiento"]
            })
            st.dataframe(df_reporte, use_container_width=True, hide_index=True)

with tab_caif:
    st.subheader("🧸 Módulo Centro de Cuidado Infantil (CAIF)")
    if not df_egr.empty:
        df_caif = df_egr[df_egr["destino"] == "CENTRO CUIDADO INFANTIL"]
        if df_caif.empty:
            st.warning("No se encontraron registros bajo el destino 'CENTRO CUIDADO INFANTIL'.")
        else:
            total_caif = df_caif["total"].sum()
            st.metric(label="Total Ejecutado CAIF", value=f"${total_caif:,.2f}")
            df_caif_vista = pd.DataFrame({
                "OBJETO DEL GASTO": df_caif["objeto_gasto"],
                "CUENTA PADRE": df_caif["cuenta_padre"],
                "PRESUPUESTO": df_caif["total"].map(lambda x: f"${x:,.2f}" if pd.notnull(x) else "$0.00"),
                "F.FIN": df_caif["fuente_fin"],
                "FINANCIAMIENTO": df_caif["financiamiento"]
            })
            st.dataframe(df_caif_vista, use_container_width=True, hide_index=True)

with tab_recursos:
    st.info("Visualización de ingresos corrientes y partidas presupuestarias anuales.")

st.sidebar.header("⚙️ Configuración")
if st.sidebar.button("⚠️ Vaciar Base de Datos Total"):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM egresos_sistema")
    conn.commit()
    conn.close()
    st.sidebar.success("Base de datos limpia.")
    st.rerun()
