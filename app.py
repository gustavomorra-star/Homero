import os
import pandas as pd
import streamlit as st
import io
import requests
import time

# Inicialización blindada que se ejecuta SIEMPRE antes que cualquier consulta
if "db_local_backup" not in st.session_state or not isinstance(st.session_state["db_local_backup"], dict):
    st.session_state["db_local_backup"] = {"destinos": [], "egresos": []}

if "destinos" not in st.session_state["db_local_backup"] or not isinstance(st.session_state["db_local_backup"]["destinos"], list):
    st.session_state["db_local_backup"]["destinos"] = []

if "egresos" not in st.session_state["db_local_backup"] or not isinstance(st.session_state["db_local_backup"]["egresos"], list):
    st.session_state["db_local_backup"]["egresos"] = []

# Configuración de la página
st.set_page_config(page_title="Presupuesto Municipal 2027", layout="wide")

# =====================================================================
# 1. CONEXIÓN Y LECTURA ROBUSTA DESDE GOOGLE SHEETS
# =====================================================================

SPREADSHEET_ID = "1r6izG5X1gil8MaZA1zD-WW2T1BA5mSC1Yq9-R663azU"

URL_READ_EGRESOS = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid=0"
URL_READ_DESTINOS = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid=1365567783"

def construir_url_csv(param):
    param_str = str(param).strip()
    if param_str.isdigit():
        return f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={param_str}&_t={int(time.time())}"
    if "docs.google.com" in param_str:
        if "export?format=csv" not in param_str:
            gid = "0"
            if "gid=" in param_str:
                gid = param_str.split("gid=")[1].split("&")[0].split("#")[0]
            return f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}&_t={int(time.time())}"
        return f"{param_str}&_t={int(time.time())}"
    return param_str

def leer_datos_gsheet(param_url_o_gid):
    url = construir_url_csv(param_url_o_gid)
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            df = pd.read_csv(io.StringIO(resp.text))

            if not df.empty:
                df.columns = [str(col).strip().lower() for col in df.columns]
                df = df.fillna("")

                for col in df.select_dtypes(include=['object', 'string']).columns:
                    df[col] = df[col].astype(str).str.strip()

                if "total" in df.columns:
                    df["total"] = pd.to_numeric(
                        df["total"].astype(str).str.replace("$", "", regex=False).str.replace(",", "", regex=False), 
                        errors='coerce'
                    ).fillna(0.0)
            return df
        else:
            st.error(f"⚠️ No se pudo acceder al Sheet (Código HTTP: {resp.status_code}). Comprobá que el enlace esté en 'Cualquier persona con el enlace puede ver'.")
    except Exception as e:
        st.warning(f"Error de conexión con Google Sheets: {e}")

    if "1365567783" in str(param_url_o_gid):
        return pd.DataFrame(columns=["secretaria", "subsecretaria", "destino"])

    df_vacio = pd.DataFrame(columns=["secretaria", "subsecretaria", "destino", "objeto_gasto", "cuenta_padre", "cuenta_presupuestaria", "total", "fuente_fin", "clase", "tipo", "finalidad"])
    df_vacio["total"] = df_vacio["total"].astype(float)
    return df_vacio

def guardar_fila_gsheet(pestana, nuevo_dict):
    if pestana in st.session_state["db_local_backup"]:
        st.session_state["db_local_backup"][pestana].append(nuevo_dict)

# =====================================================================
# 2. CARGA PRINCIPAL DE DATOS Y MENÚ LATERAL
# =====================================================================

df_egr_completo = leer_datos_gsheet(URL_READ_EGRESOS)
df_destinos_gsheet = leer_datos_gsheet(URL_READ_DESTINOS)

# --- Plan de Cuentas Oficial Municipal ---
MAPEO_GASTOS = {
    "1. Gastos en personal": {
        "21.1.0.0.00.000 - Personal Permanente": [
            "21.1.2.0.00.000 - Retribución a personal Directivo y de control",
            "21.1.3.0.00.000 - Retribuciones que no hacen al cargo",
            "21.1.4.0.00.000 - Sueldo Anual Complementario",
            "21.1.5.0.00.000 - Otros gastos en personal",
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
            "21.2.4.0.00.000 - Otros gastos en personal",
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
            "21.3.4.0.00.000 - Otros Gastos en Personal"
        ],
        "21.4.0.0.00.000 - Asignaciones familiares": [
            "21.4.1.0.00.000 - Asignaciones familiares"
        ],
        "21.5.0.0.00.000 - Asistencia social al personal": [
            "21.5.1.0.00.000 - Asistencia social al personal",
            "21.5.2.0.00.000 - Seguros"
        ],
        "21.6.0.0.00.000 - Beneficios y compensaciones": [
            "21.6.1.0.00.000 - Indumentaria",
            "21.6.2.0.00.000 - Servicios de Comedor",
            "21.6.3.0.00.000 - Compensaciones"
        ],
        "21.7.0.0.00.000 - Gabinete Ejecutivo Municipal": [
            "21.7.1.0.00.000 - Personal Gabinete",
            "21.7.1.1.00.000 - Intendente",
            "21.7.1.2.00.000 - Secretarios",
            "21.7.1.3.00.000 - Subsecretarios",
            "21.7.1.4.00.000 - Coordinadores y directores",
            "21.7.1.5.00.000 - Fiscal Municipal",
            "21.7.2.0.00.000 - Sueldo Anual Complementario",
            "21.7.3.0.00.000 - Aportes Personales",
            "21.7.4.0.00.000 - Contribuciones Patronales",
            "21.7.5.0.00.000 - Gastos de Representación",
            "21.7.6.0.00.000 - Anticipo Financiero"
        ],
        "21.8.0.0.00.000 - Concejales": [
            "21.8.1.0.00.000 - Dietas Concejales",
            "21.8.2.0.00.000 - Sueldo Anual Complementario",
            "21.8.3.0.00.000 - Aportes Personales",
            "21.8.4.0.00.000 - Contribuciones Patronales",
            "21.8.5.0.00.000 - Gastos de Representación",
            "21.8.6.0.00.000 - Anticipo Financiero"
        ],
        "21.9.0.0.00.000 - Secretarios Concejales": [
            "21.9.1.0.00.000 - Haberes",
            "21.9.2.0.00.000 - Sueldo Anual Complementario",
            "21.9.3.0.00.000 - Aportes Personales",
            "21.9.4.0.00.000 - Contribuciones Patronales",
            "21.9.5.0.00.000 - Anticipo Financiero"
        ],
        "21.10.0.0.00.000 - Pasantias Educativas": [
            "21.10.1.0.00.000 - Pasantias Educativas"
        ]
    },
    "2. Bienes de consumo": {
        "22.1.0.0.00.000 - Alimentos y productos agroforestales": [
            "22.1.1.0.00.000 - Alimentos para personas",
            "22.1.2.0.00.000 - Alimentos para animales",
            "22.1.3.0.00.000 - Productos agroforestales"
        ],
        "22.2.0.0.00.000 - Textiles y vestuario": [
            "22.2.1.0.00.000 - Textiles y vestuarios",
            "22.2.2.0.00.000 - Acabados textiles",
            "22.2.3.0.00.000 - Confecciones textiles",
            "22.2.4.0.00.000 - Calzados"
        ],
        "22.3.0.0.00.000 - Productos de papel, cartón e impresos": [
            "22.3.1.0.00.000 - Papel de escritorio y cartón",
            "22.3.2.0.00.000 - Papel para computación",
            "22.3.3.0.00.000 - Productos de artes gráficas",
            "22.3.4.0.00.000 - Libros, revistas y periódicos",
            "22.3.5.0.00.000 - Textos de enseñanza",
            "22.3.9.0.00.000 - Otros"
        ],
        "22.4.0.0.00.000 - Productos de cuero y caucho": [
            "22.4.1.0.00.000 - Cuero",
            "22.4.2.0.00.000 - Artículos de cuero",
            "22.4.3.0.00.000 - Cubiertas y cámaras de aire",
            "22.4.9.0.00.000 - Elementos de caucho"
        ],
        "22.5.0.0.00.000 - Productos químicos, combustibles y lubricantes": [
            "22.5.1.0.00.000 - Compuestos químicos",
            "22.5.2.0.00.000 - Productos farmacéuticos y medicinales",
            "22.5.3.0.00.000 - Abonos y plaguicidas",
            "22.5.4.0.00.000 - Insecticidas, fumigantes y desinfectantes",
            "22.5.5.0.00.000 - Tintas, pinturas y colorantes",
            "22.5.6.0.00.000 - Combustibles y lubricantes",
            "22.5.7.0.00.000 - Especies medicinales",
            "22.5.8.0.00.000 - Productos de material plástico",
            "22.5.9.0.00.000 - Otros"
        ],
        "22.6.0.0.00.000 - Productos minerales no metálicos": [
            "22.6.1.0.00.000 - Vidrios",
            "22.6.2.0.00.000 - Productos de loza y porcelana",
            "22.6.3.0.00.000 - Productos de arcilla y cerámica",
            "22.6.4.0.00.000 - Cemento, cal y yeso",
            "22.6.5.0.00.000 - Productos de cemento, cal y yeso",
            "22.6.9.0.00.000 - Otros"
        ],
        "22.7.0.0.00.000 - Productos metálicos": [
            "22.7.1.0.00.000 - Productos de hierro y acero",
            "22.7.2.0.00.000 - Productos metálicos no ferrosos",
            "22.7.3.0.00.000 - Estructuras metálicas acabadas",
            "22.7.4.0.00.000 - Herramientas menores",
            "22.7.9.0.00.000 - Otros"
        ],
        "22.8.0.0.00.000 - Minerales": [
            "22.8.1.0.00.000 - Carbón mineral",
            "22.8.2.0.00.000 - Gas natural",
            "22.8.3.0.00.000 - Minerales metalíferos",
            "22.8.4.0.00.000 - Piedra, arcilla y arena",
            "22.8.9.0.00.000 - Otros"
        ],
        "22.9.0.0.00.000 - Otros bienes de consumo": [
            "22.9.1.0.00.000 - Elementos de limpieza",
            "22.9.2.0.00.000 - Útiles de escritorio, oficina y enseñanza",
            "22.9.3.0.00.000 - Útiles y materiales eléctricos",
            "22.9.4.0.00.000 - Utensilios de cocina y comedor",
            "22.9.5.0.00.000 - Elementos de señalamiento",
            "22.9.6.0.00.000 - Repuestos y accesorios",
            "22.9.7.0.00.000 - Bienes de consumo varios"
        ],
        "22.10.0.0.00.000 - Bienes de consumo para reventa": [
            "22.10.1.0.00.000 - Bienes de consumo para reventa"
        ]
    },
    "3. Servicios": {
        "23.1.0.0.00.000 - Servicios básicos": [
            "23.1.1.0.00.000 - Energía eléctrica",
            "23.1.2.0.00.000 - Agua",
            "23.1.3.0.00.000 - Gas",
            "23.1.4.0.00.000 - Teléfonos, telex y telecopias",
            "23.1.5.0.00.000 - Correos y telégrafos",
            "23.1.9.0.00.000 - Otros"
        ],
        "23.2.0.0.00.000 - Alquileres y derechos": [
            "23.2.1.0.00.000 - Alquiler de edificios y locales",
            "23.2.2.0.00.000 - Alquiler de tierras y terrenos",
            "23.2.3.0.00.000 - Alquiler de maquinaria y equipos",
            "23.2.4.0.00.000 - Alquiler de medios de transporte",
            "23.2.5.0.00.000 - Alquiler de equipos de computación",
            "23.2.6.0.00.000 - Derechos de bienes intangibles",
            "23.2.9.0.00.000 - Otros"
        ],
        "23.3.0.0.00.000 - Mantenimiento, reparación y limpieza": [
            "23.3.1.0.00.000 - Mantenimiento y reparación de edificios y locales",
            "23.3.2.0.00.000 - Mantenimiento y reparación de maquinaria y equipos",
            "23.3.3.0.00.000 - Mantenimiento y reparación de medios de transporte",
            "23.3.4.0.00.000 - Mantenimiento y reparación de vías de comunicación",
            "23.3.5.0.00.000 - Mantenimiento y reparación de equipos de computación",
            "23.3.6.0.00.000 - Mantenimiento y reparación de obras de infraestructura",
            "23.3.7.0.00.000 - Limpieza, aseo y fumigación",
            "23.3.8.0.00.000 - Mantenimiento de espacios verdes",
            "23.3.9.0.00.000 - Mantenimiento, reparación y limpieza varios"
        ],
        "23.4.0.0.00.000 - Servicios técnicos y profesionales": [
            "23.4.1.0.00.000 - Estudios, investigaciones y proyectos de factibilidad",
            "23.4.2.0.00.000 - Médicos y sanitarios",
            "23.4.3.0.00.000 - Jurídicos",
            "23.4.4.0.00.000 - Contabilidad y auditoría",
            "23.4.5.0.00.000 - De informática y sistemas computarizados",
            "23.4.6.0.00.000 - De capacitación",
            "23.4.7.0.00.000 - Notariales",
            "23.4.8.0.00.000 - De arquitectura e ingeniería",
            "23.4.9.0.00.000 - Servicios técnicos y profesionales varios"
        ],
        "23.5.0.0.00.000 - Servicios comerciales y financieros": [
            "23.5.1.0.00.000 - Transporte",
            "23.5.2.0.00.000 - Almacenamiento",
            "23.5.3.0.00.000 - Imprenta, publicaciones y reproducciones",
            "23.5.4.0.00.000 - Primas y gastos de seguros",
            "23.5.5.0.00.000 - Comisiones y gastos bancarios",
            "23.5.6.0.00.000 - Publicidad y propaganda",
            "23.5.7.0.00.000 - Organización de eventos",
            "23.5.8.0.00.000 - Gastos de ceremonial y protocolo",
            "23.5.9.0.00.000 - Servicios comerciales y financieros varios"
        ],
        "23.6.0.0.00.000 - Publicidad y propaganda": [
            "23.6.1.0.00.000 - Publicidad y propaganda"
        ],
        "23.7.0.0.00.000 - Pasajes y viáticos": [
            "23.7.1.0.00.000 - Pasajes",
            "23.7.2.0.00.000 - Viáticos",
            "23.7.9.0.00.000 - Gastos de movilidad"
        ],
        "23.8.0.0.00.000 - Impuestos, derechos, tasas y juicios": [
            "23.8.1.0.00.000 - Impuestos directos",
            "23.8.2.0.00.000 - Impuestos indirectos",
            "23.8.3.0.00.000 - Tasas y derechos",
            "23.8.4.0.00.000 - Multas, recargos y juicios",
            "23.8.9.0.00.000 - Otros"
        ],
        "23.9.0.0.00.000 - Otros servicios": [
            "23.9.1.0.00.000 - Servicios de vigilancia",
            "23.9.2.0.00.000 - Servicios de sepelio",
            "23.9.9.0.00.000 - Servicios no especificados precedentemente"
        ],
        "23.10.0.0.00.000 - Servicios no personales para reventa": [
            "23.10.1.0.00.000 - Servicios no personales para reventa"
        ]
    },
    "4. Bienes de Uso": {
        "24.1.0.0.00.000 - Bienes preexistentes": [
            "24.1.1.0.00.000 - Tierras y terrenos",
            "24.1.2.0.00.000 - Edificios e instalaciones",
            "24.1.9.0.00.000 - Otros"
        ],
        "24.2.0.0.00.000 - Construcciones": [
            "24.2.1.0.00.000 - Edificaciones y ampliaciones",
            "24.2.2.0.00.000 - Vías de comunicación",
            "24.2.3.0.00.000 - Obras hidráulicas y de saneamiento",
            "24.2.4.0.00.000 - Infraestructura urbana",
            "24.2.9.0.00.000 - Otras construcciones"
        ],
        "24.3.0.0.00.000 - Maquinaria y equipo": [
            "24.3.1.0.00.000 - Maquinaria y equipo de producción",
            "24.3.2.0.00.000 - Equipo para vías de comunicación y transporte",
            "24.3.3.0.00.000 - Equipo de transporte terrestre",
            "24.3.4.0.00.000 - Equipo de telecomunicaciones",
            "24.3.5.0.00.000 - Equipo de computación",
            "24.3.6.0.00.000 - Equipo de oficina y mueblería",
            "24.3.7.0.00.000 - Equipo médico, de laboratorio y sanitario",
            "24.3.8.0.00.000 - Equipo educacional y recreativo",
            "24.3.9.0.00.000 - Maquinaria y equipo varios"
        ],
        "24.4.0.0.00.000 - Equipo de seguridad": [
            "24.4.1.0.00.000 - Equipo de seguridad e incendio"
        ],
        "24.5.0.0.00.000 - Libros, revistas y otros coleccionables": [
            "24.5.1.0.00.000 - Libros y revistas",
            "24.5.2.0.00.000 - Obras de arte y objetos de valor",
            "24.5.9.0.00.000 - Otros"
        ],
        "24.6.0.0.00.000 - Semovientes": [
            "24.6.1.0.00.000 - Animales de trabajo y reproducción"
        ],
        "24.7.0.0.00.000 - Intangibles": [
            "24.7.1.0.00.000 - Programas de computación",
            "24.7.2.0.00.000 - Marcas y patentes",
            "24.7.9.0.00.000 - Otros intangibles"
        ],
        "24.8.0.0.00.000 - Obras de Arte": [
            "24.8.1.0.00.000 - Obras de arte"
        ],
        "24.9.0.0.00.000 - Aporte de Capital": [
            "24.9.1.0.00.000 - Aporte de Capital"
        ],
        "24.10.0.0.00.000 - Obras Públicas - Pavimentación y Repavimentación": [
            "24.10.1.0.00.000 - Obras Públicas - Pavimentación y Repavimentación"
        ],
        "24.11.0.0.00.000 - Obras Públicas - Arquitectura y Urbanismo": [
            "24.11.1.0.00.000 - Obras Públicas - Arquitectura y Urbanismo"
        ],
        "24.12.0.0.00.000 - Obras Públicas - Saneamiento e Infraestructura": [
            "24.12.1.0.00.000 - Obras Públicas - Saneamiento e Infraestructura"
        ],
        "24.13.0.0.00.000 - Obras Públicas - Electrificación y Alumbrado Público": [
            "24.13.1.0.00.000 - Obras Públicas - Electrificación y Alumbrado Público"
        ],
        "24.14.0.0.00.000 - Obras Públicas - Mantenimiento y Reparaciones Mayores": [
            "24.14.1.0.00.000 - Obras Públicas - Mantenimiento y Reparaciones Mayores"
        ],
        "24.15.0.0.00.000 - Adquisiciones con Fondos Afectados": [
            "24.15.1.0.00.000 - Adquisiciones con Fondos Afectados"
        ]
    },
    "5. Transferencias": {
        "25.1.0.0.00.000 - Transferencias al sector privado para financiar gastos corrientes": [
            "25.1.1.0.00.000 - Becas y ayudas a estudiantes",
            "25.1.2.0.00.000 - Subsidios a personas e instituciones de bien público",
            "25.1.3.0.00.000 - Aportes a entidades deportivas y culturales",
            "25.1.4.0.00.000 - Ayudas sociales a personas y familias",
            "25.1.5.0.00.000 - Promoción industrial y comercial",
            "25.1.9.0.00.000 - Otras transferencias al sector privado"
        ],
        "25.2.0.0.00.000 - Transferencias al sector privado para financiar gastos de capital": [
            "25.2.1.0.00.000 - Subsidios para inversiones y equipamiento",
            "25.2.2.0.00.000 - Aportes de capital a emprendimientos de interés municipal",
            "25.2.9.0.00.000 - Otras transferencias de capital al sector privado"
        ],
        "25.3.0.0.00.000 - Transferencias al sector público para financiar gastos corrientes": [
            "25.3.1.0.00.000 - Aportes a comunas y municipios",
            "25.3.2.0.00.000 - Aportes a la provincia",
            "25.3.3.0.00.000 - Aportes a entes descentralizados e interjurisdiccionales",
            "25.3.9.0.00.000 - Otras transferencias corrientes al sector público"
        ],
        "25.4.0.0.00.000 - Transferencias al sector público para financiar gastos de capital": [
            "25.4.1.0.00.000 - Transferencias de capital a comunas y municipios",
            "25.4.2.0.00.000 - Transferencias de capital a entes públicos",
            "25.4.9.0.00.000 - Otras transferencias de capital al sector público"
        ],
        "25.5.0.0.00.000 - Transferencias al sector externo": [
            "25.5.1.0.00.000 - Transferencias al sector externo"
        ],
        "25.6.0.0.00.000 - Subsidios y Asistencia Social": [
            "25.6.1.0.00.000 - Subsidios e Indemnizaciones Sociales",
            "25.6.2.0.00.000 - Asistencia Médica, Farmacéutica y Sanitaria",
            "25.6.3.0.00.000 - Aportes Institucionales y Comunitarios",
            "25.6.4.0.00.000 - Aportes Educativos, Becas y Pasantías",
            "25.6.5.0.00.000 - Fomento Económico, Comercial y Emprendimientos",
            "25.6.6.0.00.000 - Fondo de Asistencia Educativa (F.A.E.)",
            "25.6.7.0.00.000 - Programas Sociales y Comunitarios Especiales"
        ],
        "25.7.0.0.00.000 - Aportes a Entidades Interjurisdiccionales y Organismos Especiales": [
            "25.7.1.0.00.000 - Aportes a Entidades Interjurisdiccionales y Organismos Especiales"
        ],
        "25.8.0.0.00.000 - Transferencias para Financiar Gastos de Capital": [
            "25.8.1.0.00.000 - Transferencias para Financiar Gastos de Capital"
        ]
    },
    "6. Activos Financieros": {
        "26.1.0.0.00.000 - Adquisición de títulos y valores": [
            "26.1.1.0.00.000 - Títulos públicos",
            "26.1.2.0.00.000 - Acciones y participaciones de capital",
            "26.1.9.0.00.000 - Otros títulos y valores"
        ],
        "26.2.0.0.00.000 - Concesión de préstamos": [
            "26.2.1.0.00.000 - Préstamos a personas",
            "26.2.2.0.00.000 - Préstamos a empresas privadas",
            "26.2.3.0.00.000 - Préstamos al sector público",
            "26.2.9.0.00.000 - Otros préstamos"
        ],
        "26.3.0.0.00.000 - Incremento de caja y bancos": [
            "26.3.1.0.00.000 - Depósitos a plazo fijo",
            "26.3.9.0.00.000 - Otros activos financieros"
        ],
        "26.4.0.0.00.000 - Anticipos a Proveedores y Contratistas": [
            "26.4.1.0.00.000 - Anticipos a Proveedores y Contratistas"
        ],
        "26.5.0.0.00.000 - Otorgamiento de Créditos y Microcréditos": [
            "26.5.1.0.00.000 - Otorgamiento de Créditos y Microcréditos"
        ],
        "26.6.0.0.00.000 - Integración de Capital y Aportes Financieros": [
            "26.6.1.0.00.000 - Integración de Capital y Aportes Financieros"
        ],
        "26.7.0.0.00.000 - Constituciones de Depósitos a Plazo y Fondos de Reserva": [
            "26.7.1.0.00.000 - Constituciones de Depósitos a Plazo y Fondos de Reserva"
        ]
    },
    "7. Servicio de la deuda": {
        "27.1.0.0.00.000 - Amortización de la deuda interna": [
            "27.1.1.0.00.000 - Amortización de préstamos del sector financiero",
            "27.1.2.0.00.000 - Amortización de préstamos del gobierno provincial",
            "27.1.3.0.00.000 - Amortización de títulos y bonos municipales",
            "27.1.4.0.00.000 - Amortización de la deuda consolidada",
            "27.1.9.0.00.000 - Otras amortizaciones de deuda interna"
        ],
        "27.2.0.0.00.000 - Intereses de la deuda interna": [
            "27.2.1.0.00.000 - Intereses de préstamos del sector financiero",
            "27.2.2.0.00.000 - Intereses de préstamos del gobierno provincial",
            "27.2.3.0.00.000 - Intereses de títulos y bonos municipales",
            "27.2.9.0.00.000 - Otros intereses de deuda interna"
        ],
        "27.3.0.0.00.000 - Gastos de la deuda interna": [
            "27.3.1.0.00.000 - Comisiones y gastos de refinanciación y colocación"
        ],
        "27.4.0.0.00.000 - Amortización de la deuda flotante": [
            "27.4.1.0.00.000 - Cancelación de deuda con proveedores de ejercicios anteriores",
            "27.4.2.0.00.000 - Cancelación de deuda por personal de ejercicios anteriores",
            "27.4.9.0.00.000 - Cancelación de otros pasivos de ejercicios anteriores"
        ],
        "27.5.0.0.00.000 - Amortización de Deuda Consolidada y Empréstitos": [
            "27.5.1.0.00.000 - Amortización de Deuda Consolidada y Empréstitos"
        ],
        "27.6.0.0.00.000 - Pago de Intereses y Gastos Financieros": [
            "27.6.1.0.00.000 - Pago de Intereses y Gastos Financieros"
        ],
        "27.7.0.0.00.000 - Cancelación de Deuda Flotante y Ejercicios Anteriores": [
            "27.7.1.0.00.000 - Cancelación de Deuda Flotante y Ejercicios Anteriores"
        ],
        "27.8.0.0.00.000 - Devolución de Garantías y Depósitos en Garantía": [
            "27.8.1.0.00.000 - Devolución de Garantías y Depósitos en Garantía"
        ],
        "27.9.0.0.00.000 - Cumplimiento de Sentencias Judiciales": [
            "27.9.1.0.00.000 - Cumplimiento de Sentencias Judiciales"
        ]
    },
    "8. Otros Gastos": {
        "28.1.0.0.00.000 - Fondo de Reserva y Contingencias Presupuestarias": [
            "28.1.1.0.00.000 - Fondo de Reserva y Contingencias Presupuestarias"
        ]
    },
    "9. Gastos figurativos": {
        "29.1.0.0.00.000 - Gastos figurativos para transacciones corrientes": [
            "29.1.1.0.00.000 - Contribución a la administración central / entes descentralizados"
        ]
    }
}
MAPEO_ESTRUCTURA = {
    "AGENCIA MUNICIPAL DE SEGURIDAD": ["AGENCIA MUNICIPAL DE SEGURIDAD"],
    "SECRETARÍA DE GESTIÓN AMBIENTAL Y TERRITORIAL": ["SUBSECRETARÍA DE OBRAS", "SUBSECRETARÍA DE AMBIENTE Y ACCIÓN CLIMÁTICA"],
    "SECRETARÍA DE GOBIERNO": ["SUBSECRETARÍA DE GESTIÓN Y DESARROLLO"],
    "SECRETARÍA DE DESARROLLO Y PROMOCIÓN DE DDHH": ["SUBSECRETARÍA DE PROMOCIÓN DE DDHH"],
    "INTENDENCIA": ["INTENDENCIA"],
    "HCD": ["HCD"]
}

opciones_secretarias = list(MAPEO_ESTRUCTURA.keys())
opciones_objetos = list(MAPEO_GASTOS.keys())
opciones_fuente_fin = ["Municipal", "Provincial", "Nacional"]
opciones_clase = ["Corriente", "Capital"]
opciones_tipo = ["Libre", "Afectado"]
opciones_finalidad = ["Legislativa", "Salud", "Seguridad"]

# MENÚ LATERAL A LA IZQUIERDA (SIDEBAR)
with st.sidebar:
    st.title("🍩 Homero")
    st.caption("Municipalidad de Sunchales - 2027")
    st.markdown("---")
    opcion_menu = st.radio(
        "Navegación del Sistema:",
        [
            "📝 FORMULARIO DE REGISTRO", 
            "➕ GESTIÓN DE DESTINOS",
            "📉 GENERAL (Base de Datos Sheet)",
            "🏛️ REPORTE OFICIAL POR DESTINO",
            "🛠️ PANEL DE MODIFICACIONES"
        ]
    )

st.title("🍩 Homero - Sistema de Registro Presupuestario")
st.write("📍 Municipalidad de Sunchales | Conexión Cooperativa a Google Sheets **2027**")

# =====================================================================
# SECCIÓN 1: FORMULARIO PRINCIPAL DE REGISTRO
# =====================================================================
if opcion_menu == "📝 FORMULARIO DE REGISTRO":
    st.subheader("📥 Cargar Nuevo Renglón Presupuestario")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**📍 1. Ubicación Institucional**")
        f_sec = st.selectbox("SECRETARÍA:", options=[""] + opciones_secretarias, format_func=lambda x: "--- Seleccioná ---" if x == "" else x, key="reg_sec")

        if f_sec != "":
            f_sub = st.selectbox("SUBSECRETARÍA:", options=[""] + MAPEO_ESTRUCTURA[f_sec], format_func=lambda x: "--- Seleccioná ---" if x == "" else x, key="reg_sub")
            if f_sub != "":
                df_dest_gsheet = leer_datos_gsheet(URL_READ_DESTINOS)
                lista_d = []
                if not df_dest_gsheet.empty and "destino" in df_dest_gsheet.columns:
                    df_fil = df_dest_gsheet[(df_dest_gsheet["secretaria"] == f_sec) & (df_dest_gsheet["subsecretaria"] == f_sub)]
                    lista_d = df_fil["destino"].dropna().astype(str).tolist()

                for d_loc in st.session_state.get("db_local_backup", {}).get("destinos", []):
                    if isinstance(d_loc, dict):
                        if d_loc.get("secretaria") == f_sec and d_loc.get("subsecretaria") == f_sub:
                            if d_loc.get("destino") not in lista_d:
                                lista_d.append(d_loc.get("destino"))

                f_dest = st.selectbox("DESTINO SELECCIONADO:", options=[""] + lista_d, format_func=lambda x: "--- Seleccioná ---" if x == "" else str(x).upper(), key="reg_dest") if lista_d else None
                if not lista_d: 
                    st.warning("⚠️ Sin destinos creados. Cargalo en la pestaña contigua.")
            else: 
                f_dest = None
        else: 
            f_sub, f_dest = "", None

    with col2:
        st.markdown("**📊 2. Imputación de Partida**")
        f_obj = st.selectbox("OBJETO DE GASTO:", options=[""] + opciones_objetos, format_func=lambda x: "--- Seleccioná ---" if x == "" else x, key="reg_obj")
        if f_obj != "":
            f_padre = st.selectbox("CUENTA PADRE:", options=[""] + list(MAPEO_GASTOS[f_obj].keys()), format_func=lambda x: "--- Seleccioná ---" if x == "" else x, key="reg_padre")
            f_presup = st.selectbox("CUENTA DE IMPUTACIÓN / PARTIDA:", options=[""] + MAPEO_GASTOS[f_obj][f_padre], format_func=lambda x: "--- Seleccioná ---" if x == "" else x, key="reg_presup") if f_padre != "" else ""
        else: 
            f_padre, f_presup = "", ""

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
    if st.button("💾 GUARDAR REGISTRO INMEDIATO", type="primary", use_container_width=True, disabled=not campos_completos) and f_total > 0:
        nuevo_renglon = {
            "secretaria": f_sec, "subsecretaria": f_sub, "destino": f_dest,
            "objeto_gasto": f_obj, "cuenta_padre": f_padre, "cuenta_presupuestaria": f_presup,
            "total": f_total, "fuente_fin": f_fuente, "clase": f_clase, "tipo": f_tipo, "finalidad": f_finalidad
        }
        guardar_fila_gsheet("egresos", nuevo_renglon)
        st.success("✅ ¡Renglón presupuestario guardado de forma cooperativa!")
        st.balloons()
        st.rerun()

# =====================================================================
# SECCIÓN 2: GESTIÓN DE DESTINOS DINÁMICOS
# =====================================================================
elif opcion_menu == "➕ GESTIÓN DE DESTINOS":
    st.subheader("⚙️ Panel de Configuración de Destinos")
    col_a, col_b = st.columns([1, 1.2])
    with col_a:
        st.markdown("**➕ Registrar Nuevo Destino**")
        d_sec = st.selectbox("Asociar a SECRETARÍA:", opciones_secretarias, key="dest_sec")
        d_sub = st.selectbox("Asociar a SUBSECRETARÍA:", MAPEO_ESTRUCTURA[d_sec], key="dest_sub")
        d_nombre = st.text_input("Nombre del Destino:").strip().upper()
        if st.button("✨ Registrar Destino", type="secondary", use_container_width=True) and d_nombre:
            nuevo_destino = {"secretaria": d_sec, "subsecretaria": d_sub, "destino": d_nombre}
            guardar_fila_gsheet("destinos", nuevo_destino)
            st.success("🎯 Destino añadido correctamente al repositorio.")
            st.rerun()
    with col_b:
        st.markdown("**📋 Listado de Destinos Activos**")
        df_dt_gsheet = leer_datos_gsheet(URL_READ_DESTINOS)
        lista_destinos_mostrar = []
        if not df_dt_gsheet.empty and "destino" in df_dt_gsheet.columns:
            lista_destinos_mostrar = df_dt_gsheet[["subsecretaria", "destino"]].dropna().to_dict('records')
        for d_l in st.session_state.get("db_local_backup", {}).get("destinos", []):
            if isinstance(d_l, dict) and "subsecretaria" in d_l and "destino" in d_l:
                elem = {"subsecretaria": d_l["subsecretaria"], "destino": d_l["destino"]}
                if elem not in lista_destinos_mostrar:
                    lista_destinos_mostrar.append(elem)
        if lista_destinos_mostrar:
            df_dt_vista = pd.DataFrame(lista_destinos_mostrar).rename(columns={"subsecretaria": "SUBSECRETARÍA", "destino": "DESTINO"})
            st.dataframe(df_dt_vista, use_container_width=True, hide_index=True)

# =====================================================================
# SECCIÓN 3: BASE DE DATOS GENERAL (REPORTE TIPO SHEET MASIVO)
# =====================================================================
elif opcion_menu == "📉 GENERAL (Base de Datos Sheet)":
    st.subheader("📊 Base de Datos General de Egresos")

    df_egr_gsheet = leer_datos_gsheet(URL_READ_EGRESOS)
    lista_egr_mostrar = []

    if not df_egr_gsheet.empty:
        df_egr_gsheet = df_egr_gsheet.fillna({"total": 0.0}).fillna("")
        lista_egr_mostrar = df_egr_gsheet.to_dict('records')

    for e_l in st.session_state.get("db_local_backup", {}).get("egresos", []):
        lista_egr_mostrar.append(e_l)

    if not lista_egr_mostrar:
        df_egr_completo = pd.DataFrame(columns=["secretaria", "subsecretaria", "destino", "objeto_gasto", "cuenta_padre", "cuenta_presupuestaria", "total", "fuente_fin", "clase", "tipo", "finalidad"])
        df_egr_completo["total"] = df_egr_completo["total"].astype(float)
    else:
        df_egr_completo = pd.DataFrame(lista_egr_mostrar)
        if "total" not in df_egr_completo.columns:
            df_egr_completo["total"] = 0.0

    df_egr_completo["total"] = pd.to_numeric(df_egr_completo["total"], errors='coerce').fillna(0.0)
    st.metric(label="📋 TOTAL GENERAL ACUMULADO MUNICIPAL (EGRESOS)", value=f"${df_egr_completo['total'].sum():,.2f}")

    for col in ["secretaria", "subsecretaria", "destino", "objeto_gasto", "cuenta_padre", "cuenta_presupuestaria", "fuente_fin", "clase", "tipo", "finalidad"]:
        if col not in df_egr_completo.columns:
            df_egr_completo[col] = ""

    df_plano_masivo = pd.DataFrame({
        "SECRETARIA": df_egr_completo["secretaria"], "SUBSECRETARIA": df_egr_completo["subsecretaria"],
        "DESTINO": df_egr_completo["destino"], "OBJETO DEL GASTO": df_egr_completo["objeto_gasto"],
        "CUENTA PADRE": df_egr_completo["cuenta_padre"], "CUENTA IMPUTACIÓN": df_egr_completo["cuenta_presupuestaria"],
        "TOTAL": df_egr_completo["total"].map(lambda x: f"${x:,.2f}"), "FUENTE FIN.": df_egr_completo["fuente_fin"],
        "CLASE": df_egr_completo["clase"], "TIPO": df_egr_completo["tipo"], "FINALIDAD/FUNCIÓN": df_egr_completo["finalidad"]
    })
    st.dataframe(df_plano_masivo, use_container_width=True, hide_index=True)

    st.markdown("---")
    df_excel_global = pd.DataFrame({
        "SECRETARIA": df_egr_completo["secretaria"], "SUBSECRETARIA": df_egr_completo["subsecretaria"],
        "DESTINO": df_egr_completo["destino"], "OBJETO DEL GASTO": df_egr_completo["objeto_gasto"],
        "CUENTA PADRE": df_egr_completo["cuenta_padre"], "CUENTA IMPUTACIÓN": df_egr_completo["cuenta_presupuestaria"],
        "TOTAL": df_egr_completo["total"], "FUENTE FIN.": df_egr_completo["fuente_fin"],
        "CLASE": df_egr_completo["clase"], "TIPO": df_egr_completo["tipo"], "FINALIDAD/FUNCIÓN": df_egr_completo["finalidad"]
    })
    csv_global_data = df_excel_global.to_csv(index=False, sep=';').encode('utf-8-sig')
    st.download_button(label="📗 Descargar Base de Datos Completa en 11 Columnas (.xls)", data=csv_global_data, file_name="Base_De_Datos_Egresos_General.xls", mime="application/vnd.ms-excel", use_container_width=True)

# =====================================================================
# SECCIÓN 4: REPORTE GRÁFICO OFICIAL MUNICIPAL 2027
# =====================================================================
elif opcion_menu == "🏛️ REPORTE OFICIAL POR DESTINO":
    st.subheader("📋 Consulta de Presupuesto de Gasto por Destino Oficial")

    if df_egr_completo.empty:
        st.info("No hay transacciones cargadas en el servidor actualmente.")
    else:
        cf1, cf2, col_f3 = st.columns(3)
        with cf1: 
            sec_s = st.selectbox("1. SELECCIONÁ SECRETARÍA:", options=[""] + opciones_secretarias, key="of_sec")
        with cf2:
            sb_opts = [""] + MAPEO_ESTRUCTURA[sec_s] if (sec_s != "" and sec_s in MAPEO_ESTRUCTURA) else [""]
            sub_s = st.selectbox("2. SELECCIONÁ SUBSECRETARÍA:", options=sb_opts, key="of_sub")
        with col_f3:
            if sec_s != "" and sub_s != "":
                lista_dest_oficial = []
                df_d_g = leer_datos_gsheet(URL_READ_DESTINOS)

                if not df_d_g.empty and "destino" in df_d_g.columns:
                    mask_dest = (df_d_g["secretaria"].astype(str).str.strip().str.upper() == sec_s.strip().upper()) & \
                                (df_d_g["subsecretaria"].astype(str).str.strip().str.upper() == sub_s.strip().upper())
                    lista_dest_oficial.extend([str(d).strip().upper() for d in df_d_g[mask_dest]["destino"].dropna().tolist() if str(d).strip() != ""])

                if not df_egr_completo.empty and "destino" in df_egr_completo.columns:
                    mask_egr = (df_egr_completo["secretaria"].astype(str).str.strip().str.upper() == sec_s.strip().upper()) & \
                               (df_egr_completo["subsecretaria"].astype(str).str.strip().str.upper() == sub_s.strip().upper())
                    lista_dest_oficial.extend([str(d).strip().upper() for d in df_egr_completo[mask_egr]["destino"].dropna().tolist() if str(d).strip() != ""])

                backup_data = st.session_state.get("db_local_backup", {})
                if isinstance(backup_data, dict):
                    lista_dest_backup = backup_data.get("destinos", [])
                    if isinstance(lista_dest_backup, list):
                        for d_l in lista_dest_backup:
                            if isinstance(d_l, dict):
                                if str(d_l.get("secretaria","")).strip().upper() == sec_s.strip().upper() and str(d_l.get("subsecretaria","")).strip().upper() == sub_s.strip().upper():
                                    d_nom = str(d_l.get("destino","")).strip().upper()
                                    if d_nom:
                                        lista_dest_oficial.append(d_nom)

                opciones_destinos_unicos = sorted(list(set(lista_dest_oficial)))
                dest_s = st.selectbox("3. SELECCIONÁ DESTINO:", options=[""] + opciones_destinos_unicos, format_func=lambda x: "--- Seleccioná ---" if x == "" else str(x).upper(), key="of_dest")
            else: 
                dest_s = st.selectbox("3. SELECCIONÁ DESTINO:", options=[""], key="of_dest")

        if sec_s != "" and sub_s != "" and dest_s != "":
            dest_target = str(dest_s).strip().upper()

            df_f_of = df_egr_completo[
                df_egr_completo["destino"].astype(str).str.strip().str.upper() == dest_target
            ].copy()

            tot_dest = df_f_of["total"].sum() if not df_f_of.empty else 0.0

            st.markdown(f"""
            <div style="border: 1px solid #000; padding: 0px; border-radius: 2px; background-color: #fff; font-family: Arial, sans-serif;">
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="width: 25%; font-size: 11px; padding: 15px; border-right: 1px solid #000; text-align: left;"><b>Municipalidad de Sunchales</b><br><span style="font-size: 9px; color: #777;">Presupuesto Oficial 2027</span></td>
                        <td style="width: 50%; text-align: center; padding: 15px; border-right: 1px solid #000; vertical-align: middle;"><h2 style="margin: 0; font-size: 18px; font-weight: bold;">PRESUPUESTO DE GASTO POR DESTINO</h2><h4 style="margin: 4px 0 0 0; font-size: 13px; font-weight: normal;">-2027-</h4></td>
                        <td style="width: 25%; text-align: center; background-color: #f5f5f5; vertical-align: middle;"><div style="font-size: 13px; font-weight: bold; border-bottom: 1px solid #000; padding: 4px 0;">Total Destino</div><div style="font-size: 18px; font-weight: bold;">${tot_dest:,.2f}</div></td>
                    </tr>
                </table>
                <div style="border-top: 1px solid #000; font-size: 11px; padding: 6px 10px;">
                    <b>SECRETARÍA:</b> {sec_s} | <b>SUBSECRETARÍA:</b> {sub_s} | <span style="float: right;"><b>DESTINO:</b> {str(dest_s).upper()}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if df_f_of.empty:
                st.warning(f"⚠️ No se encontraron gastos registrados para **{dest_s}**.")
            else:
                f_plan, html_rows = [], ""
                for obj, df_obj in df_f_of.groupby("objeto_gasto"):
                    t_o = df_obj["total"].sum()
                    f_plan.append({"OBJETO DEL GASTO": f"<b>{obj}</b>", "PRESUPUESTO": f"<b>${t_o:,.2f}</b>", "F.FIN": "", "CLASE": "", "TIPO": "", "FINANCIAMIENTO": ""})
                    html_rows += f'<tr style="font-weight: bold; background-color: #f9f9f5;"><td style="text-align: left; padding-left: 5px;">{obj}</td><td>${t_o:,.2f}</td><td></td><td></td><td></td><td></td></tr>'

                    for pad, df_pad in df_obj.groupby("cuenta_padre"):
                        t_p = df_pad["total"].sum()
                        f_plan.append({"OBJETO DEL GASTO": f"&nbsp;&nbsp;&nbsp;&nbsp;<b>{pad}</b>", "PRESUPUESTO": f"<b>${t_p:,.2f}</b>", "F.FIN": "", "CLASE": "", "TIPO": "", "FINANCIAMIENTO": ""})
                        html_rows += f'<tr style="font-weight: bold;"><td style="text-align: left; padding-left: 20px;">{pad}</td><td>${t_p:,.2f}</td><td></td><td></td><td></td><td></td></tr>'

                        for _, r in df_pad.iterrows():
                            f_plan.append({"OBJETO DEL GASTO": f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{r['cuenta_presupuestaria']}", "PRESUPUESTO": f"${r['total']:,.2f}", "F.FIN": r["fuente_fin"], "CLASE": r["clase"], "TIPO": r["tipo"], "FINANCIAMIENTO": r["finalidad"]})
                            html_rows += f'<tr><td style="text-align: left; padding-left: 40px;">{r["cuenta_presupuestaria"]}</td><td>${r["total"]:,.2f}</td><td>{r["fuente_fin"]}</td><td>{r["clase"]}</td><td>{r["tipo"]}</td><td>{r["finalidad"]}</td></tr>'

                st.write(pd.DataFrame(f_plan).to_html(escape=False, index=False), unsafe_allow_html=True)

                st.markdown("---")
                html_imp = f"""
                <html>
                <head>
                    <meta charset="utf-8">
                    <style>
                        @page {{ size: A4 landscape; margin: 15mm; }}
                        body {{ font-family: Arial, sans-serif; color: #000; margin: 0 auto; width: 100%; max-width: 1050px; }}
                        .m-box {{ border: 1px solid #000; padding: 12px; margin-bottom: 20px; }}
                        .t-hdr {{ width: 100%; border-collapse: collapse; }}
                        .t-hdr td {{ padding: 5px; vertical-align: middle; border: none; }}
                        .b-tot {{ border: 1px solid #000; background-color: #f5f5f5; text-align: center; }}
                        .tabla-datos {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 11px; }}
                        .tabla-datos th {{ border-bottom: 2px solid #000; padding: 8px 5px; text-align: center; font-weight: bold; }}
                        .tabla-datos td {{ border-bottom: 1px solid #e0e0e0; padding: 8px 5px; vertical-align: middle; text-align: center; }}
                        .tabla-datos th:first-child, .tabla-datos td:first-child {{ text-align: left !important; padding-left: 10px; }}
                    </style>
                </head>
                <body onload="window.print();">
                    <div class="m-box">
                        <table class="t-hdr">
                            <tr>
                                <td style="width: 25%; text-align: left; font-size: 10px;"><b>Municipalidad de Sunchales</b><br><span style="font-size: 8px; color: #555;">Presupuesto Oficial 2027</span></td>
                                <td style="width: 50%; text-align: center;"><b>PRESUPUESTO DE GASTO POR DESTINO</b><br><small>-2027-</small></td>
                                <td style="width: 25%;" class="b-tot"><small>Total Destino</small><br><b>${tot_dest:,.2f}</b></td>
                            </tr>
                        </table>
                        <div style="border-top: 1px solid #000; font-size: 11px; padding-top: 8px; margin-top: 8px;">
                            <b>SECRETARÍA:</b> {sec_s} | <b>SUBSECRETARÍA:</b> {sub_s} | <span style="float: right;"><b>DESTINO:</b> {str(dest_s).upper()}</span>
                        </div>
                    </div>
                    <table class="tabla-datos">
                        <thead><tr><th>OBJETO DEL GASTO</th><th>PRESUPUESTO</th><th>F.FIN</th><th>CLASE</th><th>TIPO</th><th>FINANCIAMIENTO</th></tr></thead>
                        <tbody>{html_rows}</tbody>
                    </table>
                </body>
                </html>
                """
                st.download_button(label="🖨️ GENERAR Y ABRIR REPORTE IMPRIMIBLE A PDF", data=html_imp, file_name=f"Reporte_{str(dest_s).replace(' ', '_')}.html", mime="text/html", use_container_width=True)

# =====================================================================
# SECCIÓN 5: PANEL EXCLUSIVO DE MODIFICACIONES
# =====================================================================
elif opcion_menu == "🛠️ PANEL DE MODIFICACIONES":
    st.subheader("🛠️ Panel Supervisor de Modificaciones y Actualización")

    diccionario_opciones = {}
    if not df_egr_completo.empty:
        for i, r in df_egr_completo.iterrows():
            sec_txt = str(r.get('secretaria', '')).strip().upper()
            sub_txt = str(r.get('subsecretaria', '')).strip().upper()
            destino_txt = str(r.get('destino', '')).strip().upper()
            partida_txt = str(r.get('cuenta_presupuestaria', '')).strip()

            try:
                monto_val = float(r.get('total', 0.0))
            except Exception:
                monto_val = 0.0

            if not destino_txt or destino_txt == "NAN":
                destino_txt = "SIN DESTINO"
            if not partida_txt or partida_txt == "NAN":
                partida_txt = "SIN PARTIDA"

            texto_descriptivo = f"[ID: {i+1}] Fila {i+1} | Destino: {destino_txt} | Partida: {partida_txt[:30]} | Monto: ${monto_val:,.2f}"
            diccionario_opciones[texto_descriptivo] = i

    lista_claves_validas = list(diccionario_opciones.keys())

    if len(lista_claves_validas) == 0:
        st.info("💡 No hay registros contables activos para modificar en este momento.")
    else:
        st.caption("Seleccioná un renglón para corregir sus valores contables o darlo de baja.")

        linea_sel = st.selectbox("Seleccioná el registro a modificar por su número de fila:", options=lista_claves_validas, key="sel_mod_panel")
        idx_real = diccionario_opciones[linea_sel]
        fila_r = df_egr_completo.loc[idx_real]

        st.markdown("---")
        st.subheader(f"📝 Formulario de Edición Contable (Fila {idx_real + 1})")

        col_mod1, col_mod2 = st.columns([2, 1])

        with col_mod1:
            st.markdown("#### ✏️ Modificar Datos del Renglón")
            st.info(f"📍 **Ubicación Fija:** {fila_r.get('secretaria', '')} ➔ {fila_r.get('subsecretaria', '')} ➔ **{fila_r.get('destino', '')}**")
            
            with st.form(key=f"form_modificacion_{idx_real}"):
                val_obj_act = str(fila_r.get("objeto_gasto", ""))
                idx_obj = opciones_objetos.index(val_obj_act) if val_obj_act in opciones_objetos else 0
                mod_obj = st.selectbox("OBJETO DE GASTO:", options=opciones_objetos, index=idx_obj)

                cuentas_padre_opts = list(MAPEO_GASTOS.get(mod_obj, {}).keys())
                val_padre_act = str(fila_r.get("cuenta_padre", ""))
                idx_padre = cuentas_padre_opts.index(val_padre_act) if val_padre_act in cuentas_padre_opts else 0
                mod_padre = st.selectbox("CUENTA PADRE:", options=cuentas_padre_opts, index=idx_padre) if cuentas_padre_opts else st.text_input("CUENTA PADRE:", value=val_padre_act)

                cuentas_partida_opts = MAPEO_GASTOS.get(mod_obj, {}).get(mod_padre, [])
                val_presup_act = str(fila_r.get("cuenta_presupuestaria", ""))
                idx_presup = cuentas_partida_opts.index(val_presup_act) if val_presup_act in cuentas_partida_opts else 0
                mod_presup = st.selectbox("CUENTA DE IMPUTACIÓN / PARTIDA:", options=cuentas_partida_opts, index=idx_presup) if cuentas_partida_opts else st.text_input("CUENTA DE IMPUTACIÓN / PARTIDA:", value=val_presup_act)

                st.markdown("---")
                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    mod_monto = st.number_input("PRESUPUESTO / VALOR ($):", value=float(fila_r.get("total", 0.0)), min_value=0.0, step=100.0)
                    
                    val_fuente = str(fila_r.get("fuente_fin", ""))
                    idx_f = opciones_fuente_fin.index(val_fuente) if val_fuente in opciones_fuente_fin else 0
                    mod_fuente = st.selectbox("F.FIN:", options=opciones_fuente_fin, index=idx_f)

                with col_m2:
                    val_clase = str(fila_r.get("clase", ""))
                    idx_c = opciones_clase.index(val_clase) if val_clase in opciones_clase else 0
                    mod_clase = st.selectbox("CLASE:", options=opciones_clase, index=idx_c)

                    val_tipo = str(fila_r.get("tipo", ""))
                    idx_t = opciones_tipo.index(val_tipo) if val_tipo in opciones_tipo else 0
                    mod_tipo = st.selectbox("TIPO:", options=opciones_tipo, index=idx_t)

                val_fin = str(fila_r.get("finalidad", ""))
                idx_fin = opciones_finalidad.index(val_fin) if val_fin in opciones_finalidad else 0
                mod_finalidad = st.selectbox("FINALIDAD / FUNCIÓN:", options=opciones_finalidad, index=idx_fin)

                if st.form_submit_button("💾 Guardar Cambios en este Registro", use_container_width=True, type="primary"):
                    if idx_real < len(st.session_state["db_local_backup"]["egresos"]):
                        st.session_state["db_local_backup"]["egresos"][idx_real].update({
                            "objeto_gasto": mod_obj,
                            "cuenta_padre": mod_padre,
                            "cuenta_presupuestaria": mod_presup,
                            "total": mod_monto,
                            "fuente_fin": mod_fuente,
                            "clase": mod_clase,
                            "tipo": mod_tipo,
                            "finalidad": mod_finalidad
                        })
                    st.success(f"¡Renglón {idx_real + 1} actualizado correctamente!")
                    st.rerun()

        with col_mod2:
            st.markdown("#### 🗑️ Dar de Baja")
            st.warning("Esta operación eliminará permanentemente el registro seleccionado de la sesión.")
            if st.button("❌ Confirmar Baja de Fila", key=f"btn_del_{idx_real}", use_container_width=True):
                if idx_real < len(st.session_state["db_local_backup"]["egresos"]):
                    st.session_state["db_local_backup"]["egresos"].pop(idx_real)
                st.success(f"Renglón {idx_real + 1} eliminado.")
                st.rerun()
