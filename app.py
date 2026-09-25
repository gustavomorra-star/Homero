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

# Configuración Simpson con la Rosquilla oficial
st.set_page_config(layout="wide", page_title="Homero Presupuesto", page_icon="🍩")
st.title("🍩 Homero - Sistema de Registro Presupuestario")
st.write("📍 Municipalidad de Sunchales | Formato Oficial Adaptado")

# --- Plan de Cuentas Fijo de la Municipalidad de Sunchales ---
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
