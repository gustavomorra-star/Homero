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

# Inicialización y configuración básica de la aplicación Streamlit
inicializar_base_datos()
st.set_page_config(layout="wide")
st.title("💼 Homero - Sistema de Registro Presupuestario")
st.write("📍 Municipalidad de Sunchales | Formato Oficial Adaptado")

# (El código continúa con la definición de listas, pestañas de formulario, control de datos, reportes y barra lateral para la gestión de la base de datos).
