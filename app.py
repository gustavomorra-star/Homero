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
                # 1. Limpiar nombres de columnas
                df.columns = [str(col).strip().lower() for col in df.columns]

                # 2. Reemplazar valores NaN por texto vacío ""
                df = df.fillna("")

                # 3. Limpiar espacios extra en textos
                for col in df.select_dtypes(include=['object', 'string']).columns:
                    df[col] = df[col].astype(str).str.strip()

                # 4. Convertir 'total' a numérico de forma segura (Formato Argentina / Internacional)
                if "total" in df.columns:
                    s_total = df["total"].astype(str).str.replace("$", "", regex=False).str.strip()
                    # Quitar puntos de miles y cambiar la coma decimal por punto
                    s_total = s_total.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
                    df["total"] = pd.to_numeric(s_total, errors='coerce').fillna(0.0)
            return df
        else:
            st.error(f"⚠️ No se pudo acceder al Sheet (Código HTTP: {resp.status_code}). Comprobá que el enlace esté en 'Cualquier persona con el enlace puede ver'.")
    except Exception as e:
        st.warning(f"Error de conexión con Google Sheets: {e}")

    # Retorno de DataFrame vacío estructurado en caso de fallo
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
            "21.3.4.0.00.000 - Otros Gastos en Personal",
            "21.3.4.1.00.000 - Aportes Personales",
            "21.3.4.2.00.000 - Aportes Sindicales",
            "21.3.5.0.00.000 - Anticipo Financiero"
        ],
        "21.4.0.0.00.000 - Asignaciones familiares": [
            "21.4.0.0.00.000 - Asignaciones familiares"
        ],
        "21.5.0.0.00.000 - Asistencia social al personal": [
            "21.5.1.0.00.000 - Seguro de riesto de trabajo",
            "21.5.9.0.00.000 - Otras asistenvias sociales al personal"
        ],
        "21.6.0.0.00.000 - Beneficios y compensaciones": [
            "21.6.0.0.00.000 - Beneficios y compensaciones"
        ],
        "21.7.0.0.00.000 - Gabinete de autoridades superiores del poder Ejecutivo": [
            "21.7.0.0.00.000 - Gabinete de autoridades superiores del poder Ejecutivo"
        ],
        "21.8.0.0.00.000 - Personal Contratado": [
            "21.8.1.0.00.000 - Retribuciones por contratos",
            "21.8.2.0.00.000 - Adicionales al contrato",
            "21.8.3.0.00.000 - Sueldo Anual Complementario",
            "21.8.5.0.00.000 - Contribuciones patronales",
            "21.8.7.0.00.000 - Contratos especiales",
            "21.8.8.0.00.000 - Otros Gastos en Personal",
            "21.8.8.1.00.000 - Aportes Personales",
            "21.8.8.2.00.000 - Aportes Sindicales",
            "21.8.9.0.00.000 - Anticipo Financiero"
        ],
        "21.1.9.0.00.000 - Retenciones PP": [
            "21.1.9.1.00.000 - Retenciones Ganancias",
            "21.1.9.2.00.000 - Retenciones Cuota Alimentaria",
            "21.1.9.3.00.000 - Retenciones Sindicales",
            "21.1.9.4.00.000 - Retenciones Aportes Partidarios",
            "21.1.9.5.00.000 - Retenciones Caja de jubilaciones",
            "21.1.9.6.00.000 - Retenciones IAPOS",
            "21.1.9.7.00.000 - Retenciones Embargos"
        ],
        "21.2.9.0.00.000 - Retenciones PT": [
            "21.2.9.1.00.000 - Retenciones Ganancias PT",
            "21.2.9.2.00.000 - Retenciones Cuota Alimentaria PT",
            "21.2.9.3.00.000.- Retenciones Sindicales PT",
            "21.2.9.4.00.000 - Retenciones Aportes Partidarios PT",
            "21.2.9.5.00.000 - Retenciones Embargos PT",
            "21.2.9.6.00.000 - Retenciones IAPOS PT"
        ]
    },
    "2. Bienes de consumo": {
        "22.1.0.0.00.000 - Productos alimenticios agropecuarios y forestales": [
            "22.1.1.0.00.000 - Alimentos para personas",
            "22.1.2.0.00.000 - Alimentos para animales",
            "22.1.3.0.00.000 - Productos Pecuarios",
            "22.1.4.0.00.000 - Productos agroforestales",
            "22.1.5.0.00.000 - Madera, corcho y sus manufacturas",
            "22.1.9.0.00.000 - Otros no especificados precedentemente"
        ],
        "22.2.0.0.00.000 - Textiles y vestuarios": [
            "22.2.1.0.00.000 - Hilados y telas",
            "22.2.2.0.00.000 - Prendas de vestir",
            "22.2.3.0.00.000 - Confecciones textiles",
            "22.2.9.0.00.000 - Otros noi especificados precedentemente"
        ],
        "22.3.0.0.00.000 - Productos de papel, cartón e impresos": [
            "22.3.1.0.00.000 - Papel de escritorio y cartón",
            "22.3.2.0.00.000 - Papel para computación",
            "22.3.3.0.00.000 - Productos de artes gráficas",
            "22.3.4.0.00.000 - Productos de papel y cartón",
            "22.3.5.0.00.000 - Libros, revistas y periódicos",
            "22.3.6.0.00.000 - Textos de enseñanza",
            "22.3.7.0.00.000 - Especias timbradas y valores",
            "22.3.9.0.00.000 - Otros no especificados precedentemente"
        ],
        "22.4.0.0.00.000 - Productos de cuero y caucho": [
            "22.4.1.0.00.000 - Cueros y Pieles",
            "22.4.2.0.00.000 - Artículos de Cuero",
            "22.4.3.0.00.000 - Artículos de caucho",
            "22.4.4.0.00.000 - Cubiertas y cámaras de aire",
            "22.4.9.0.00.000 - Otros no especificados precedentemente"
        ],
        "22.5.0.0.00.000 - Productos químicos, combustibles y lubricantes": [
            "22.5.1.0.00.000 - Compuestos químicos",
            "22.5.2.0.00.000 - Productos farmacéuticos y medicinales",
            "22.5.3.0.00.000 - Abonos y fertilizantes",
            "22.5.4.0.00.000 - Insecticidas, fumigantes y otros",
            "22.5.5.0.00.000 - Tintas, Pinturas y Colorantes",
            "22.5.6.0.00.000 - Combustibles y lubricantes",
            "22.5.7.0.00.000 - Específicos veterinarios",
            "22.5.8.0.00.000 - Productos de material plástivo",
            "22.5.9.0.00.000 - Otros no especificados precedentemente",
            "22.5.9.1.00.000 - Productos de Brea y material asfáltico"
        ],
        "22.6.0.0.00.000 - Productos minerales no metálicos": [
            "22.6.1.0.00.000 - Productos de arcilla y de cerámica",
            "22.6.2.0.00.000 - Productos de Vidrio",
            "22.6.3.0.00.000 - Productos de Loza y porcelana",
            "22.6.4.0.00.000 - Productos de Cemento, asbesto y yeso",
            "22.6.5.0.00.000 - Productos de Cemento, Cal y Yeso",
            "22.6.9.0.00.000 - Otros no especificados precedentemente"
        ],
        "22.7.0.0.00.000 - Productos metálicos": [
            "22.7.1.0.00.000 - Productos Ferrosos",
            "22.7.2.0.00.000 - Productos no ferrosos",
            "22.7.3.0.00.000 - Material de Guerra",
            "22.7.4.0.00.000 - Estructuras metálicas acabadas",
            "22.7.5.0.00.000 - Herramientas menores",
            "22.7.9.0.00.000 - Otros no especificados precedentemente"
        ],
        "22.8.0.0.00.000 - Minerales": [
            "22.8.1.0.00.000 - Minerales metalíferos",
            "22.8.2.0.00.000 - Petróleo crudo y gas natural",
            "22.8.3.0.00.000 - Carbón mineral",
            "22.8.4.0.00.000 - Piedra, Arcilla y Arena",
            "22.8.9.0.00.000 - Otros no especificados precedentemente"
        ],
        "22.9.0.0.00.000 - Otros bienes de consumo": [
            "22.9.1.0.00.000 - Elementos de limpieza",
            "22.9.2.0.00.000 - Útiles de escritorio, oficina y eseñanza",
            "22.9.3.0.00.000 - Útiles y materiales eléctricos",
            "22.9.4.0.00.000 - Utensillos de cocina y comedor",
            "22.9.5.0.00.000 - Útiles menores médico-quirúrgico y de laboratorio",
            "22.9.6.0.00.000 - Repuestos y accesorios",
            "22.9.7.0.00.000 - Equipos y Elementos de Seguridad",
            "22.9.7.1.00.000 - Extintores y equipos contra incendios",
            "22.9.7.2.00.000 - Señalización y Vallado",
            "22.9.7.3.00.000 - EPP",
            "22.9.7.3.01.000 - Calzado, Guantes e Indumentaria",
            "22.9.7.3.02.000 - Protección Respiratoria, Auditiva y Visual",
            "22.9.7.3.03.000 - Cascos y Arnes",
            "22.9.9.0.00.000 - Otros no especificados precedentemente",
            "22.9.9.1.00.000 - Artículos para el hogar",
            "22.9.9.1.01.000 - Electrodomésticos",
            "22.9.9.1.02.000 - Mobiliario de oficina",
            "22.9.9.1.03.000 - Mobiliario de Cocina",
            "22.9.9.1.04.000 - Mobiliarios Varios"
        ],
        "22.9.9.0.00.000 - Otros no especificados": [
            "22.9.9.2.00.000 - Equipos y elementos deportivos"
        ]
    },
    "3. Servicios": {
        "23.1.0.0.00.000 - Servicios básicos": [
            "23.1.1.0.00.000 - Energía Eléctrica",
            "23.1.2.0.00.000 - Agua",
            "23.1.3.0.00.000 - Gas",
            "23.1.4.0.00.000 - Telefono, telex, telefax",
            "23.1.5.0.00.000 - Correos y telégrafos",
            "23.1.9.0.00.000 - Otros No especificados precedentemente"
        ],
        "23.2.0.0.00.000 - Alquileres y derechos": [
            "23.2.1.0.00.000 - Alquiler de edificios y locales",
            "23.2.2.0.00.000 - Alquiler de maquinaria, equipo y medios de transporte",
            "23.2.3.0.00.000 - Alquiler de equipos de computación",
            "23.2.4.0.00.000 - Alquiler de fotocopiadoras",
            "23.2.5.0.00.000 - Alquiler de tierras y terrenos",
            "23.2.6.0.00.000 - Derechos de bienes intangibles",
            "23.2.9.0.00.000 - Otros alquileres no comprendidos precedentemente",
            "23.2.9.1.00.000 - Alquiler de máquinas expendedoras de alimentos",
            "23.2.9.2.00.000 - Alquiler de expendedores de agua",
            "23.2.9.4.00.000 - Alquiler Estructuras Varias (Incluye Vallas Seguridad, Gradas, etc)",
            "23.2.9.4.00.000 - Alquiler Vallas de Seguridad y Símil",
            "23.2.9.3.00.000 - Alquiler de Baños químicos"
        ],
        "23.3.0.0.00.000 - Mantenimiento, reparación y limpieza": [
            "23.3.1.0.00.000 - Mantenimiento y reparación de edificios y locales",
            "23.3.2.0.00.000 - Mantenimiento y reparación de vehículos",
            "23.3.3.0.00.000 - Mantenimiento y reparación de maquinaria y equipo",
            "23.3.4.0.00.000 - Mantenimiento y reparación de vías de comunicación",
            "23.3.5.0.00.000 - Limpieza, aseo y fumigación",
            "23.3.6.0.00.000 - Mantenimiento de sistemas informáticos y accesorios",
            "23.3.9.0.00.000 - Otros no especificados precedentemente",
            "23.3.9.1.00.000 - Mantenimiento de Espacios Verdes",
            "23.3.9.1.01.000 - Corte de pasto y desmalezado",
            "23.3.9.1.02.000 - Poda y mantenimiento de arbolado",
            "23.3.9.2.00.000 - Mantenimiento y limpieza de desagües y canales",
            "23.3.9.2.01.000 - Mantenimiento de Desagües",
            "23.3.9.2.02.000 - Mantenimiento de Canales",
            "23.3.9.2.03.000 - Mantenimiento de Cordón Cuneta",
            "23.3.9.3.00.000 - Limpieza de calles y caminos",
            "23.3.9.4.00.000 - Mantenimiento de conexiones cloacales",
            "23.3.9.5.00.000 - Mantenimiento de Alumbrado Público y tendido eléctrico",
            "23.3.9.6.00.000 - Mantenimiento de Señalización Vial",
            "23.3.9.6.01.000 - Mantenimiento de Semáforos",
            "23.3.9.6.02.000 - Mantenimiento de Señalización Vial"
        ],
        "23.4.0.0.00.000 - Servicios técnicos y profesionales": [
            "23.4.1.0.00.000 - Estudios, investigación y proyectos de factibilidad",
            "23.4.2.0.00.000 - Médicos y Sanitarios",
            "23.4.3.0.00.000 - Jurídicos",
            "23.4.4.0.00.000 - Contabilidad y auditoría",
            "23.4.5.0.00.000 - De Capacitación",
            "23.4.6.0.00.000 - De Informática y sistemas computarizados",
            "23.4.7.0.00.000 - De Turismo",
            "23.4.8.0.00.000 - De Geriátricos",
            "23.4.9.0.00.000 - Otros no especificados precedentemente",
            "23.4.9.1.00.000 - Servicio de Alarma",
            "23.4.9.2.00.000 - Servicio de Escribanía",
            "23.4.9.3.00.000 - Servicio de Agrimensura",
            "23.4.9.4.00.000 - Servicio de Arquitectura",
            "23.4.9.5.00.000 - Servicios relacionados a la Agronomía",
            "23.4.9.6.00.000 - Servicios de Ingeniería",
            "23.4.9.6.01.000 - Servicios de Ingeniería Industrial",
            "23.4.9.6.02.000 - Servicio de Ingeniería Agrónoma",
            "23.4.9.6.03.000 - Servicio de Ingeniería Informática",
            "23.4.9.6.04.000 - Servicio de Ingeniería Civil",
            "23.4.9.6.05.000 - Servicios de Ingeniería Hídrica",
            "23.4.9.7.00.000 - Servicio Sonido e Iluminación",
            "23.4.9.9.00.000 - Otros NCP"
        ],
        "23.5.0.0.00.000 - Servicios comerciales y financieros": [
            "23.5.1.0.00.000 - Transporte",
            "23.5.2.0.00.000 - Almacenamiento",
            "23.5.3.0.00.000 - Imprenta, publicaciones y reproducciones",
            "23.5.4.0.00.000 - Primas y gastos de seguros",
            "23.5.5.0.00.000 - Comisiones y Gastos Bancarios",
            "23.5.6.0.00.000 - Internet",
            "23.5.9.0.00.000 - Otros no especificados precedentemente",
            "23.5.9.1.00.000 - Estampillas y estampillados",
            "23.5.9.2.00.000 - Gestión de Cobranza"
        ],
        "23.6.0.0.00.000 - Publicidad y propaganda": [
            "23.6.1.0.00.000 - Publicidad y Propaganda MCS",
            "23.6.2.0.00.000 - Publicidad y Propaganda rodante"
        ],
        "23.7.0.0.00.000 - Pasajes y viáticos": [
            "23.7.1.0.00.000 - Pasajes",
            "23.7.2.0.00.000 - Viáticos",
            "23.7.3.0.00.000 - Combustibles y Peajes"
        ],
        "23.8.0.0.00.000 - Impuestos, derechos y tasas": [
            "23.8.1.0.00.000 - Impuestos indirectos",
            "23.8.2.0.00.000 - Impuestos directos",
            "23.8.3.0.00.000 - Derechos y tasas",
            "23.8.4.0.00.000 - Multas y recargos",
            "23.8.5.0.00.000 - Regalías",
            "23.8.6.0.00.000 - Juicios y mediaciones",
            "23.8.7.0.00.000 - Aporte colegios profesionales",
            "23.8.9.0.00.000 - Otros no especificados precedentemente"
        ],
        "23.9.0.0.00.000 - Otros servicios": [
            "23.9.1.0.00.000 - Servicio de Ceremonial",
            "23.9.2.0.00.000 - Gastos reservados",
            "23.9.3.0.00.000 - Servicio de Vigilancia",
            "23.9.4.0.00.000 - Gastos protocolares",
            "23.9.5.0.00.000 - Edictos y publicaciones oficiales",
            "23.9.6.0.00.000 - Becas de Investigación",
            "23.9.7.0.00.000 - Contratación de Servicios Artísticos",
            "23.9.9.1.00.000 - Hotelería",
            "23.9.8.0.00.000 - Ambientación, arte y decoración",
            "23.9.9.5.00.000 - Servicios relacionados con la comunicación",
            "23.9.9.3.00.000 - Servicios relacionados a deporte y recreación"
        ],
        "23.6.0.0.00.000 - Publicida y Propaganda": [
            "23.6.3.0.00.0000 - Publicidad"
        ]
    },
    "4. Bienes de Uso": {
        "24.1.0.0.00.000 - Bienes preexistentes": [
            "24.1.1.0.00.000 - Tierras y Terrenos",
            "24.1.2.0.00.000 - Edificios e instalaciones",
            "24.1.3.0.00.000 - Otros Bienes preexistentes"
        ],
        "24.2.0.0.00.000 - Construcciones": [
            "24.2.1.0.00.000 - Construcciones en Bienes de dominio Privado",
            "24.2.1.1.00.000 - Const. de Dom. Priv. por Administración Central",
            "24.2.1.1.01.000 - Materiales de Construcción y mano de obra",
            "24.2.1.1.02.000 - Mano de Obra",
            "24.2.1.2.00.000 - Const. de Dom. Priv. por terceros",
            "24.2.1.2.01.000 - Materiales de Construcción",
            "24.2.1.2.02.000 - Mano de Obra",
            "24.2.2.0.00.000 - Construcciones en Bienes de Dominio Público",
            "24.2.2.1.00.000 - Const. Dom. Pub. por Administración Central",
            "24.2.2.1.01.000 - Materiales de Construcción y mano de obra",
            "24.2.2.2.00.000 - Const. de Dom. Pub. por Terceros",
            "24.2.2.2.01.000 - Materiales de Construcción",
            "24.2.2.2.02.000 - Construcciones Bienes de Dominio Privado por Adm. Terceros"
        ],
        "24.2.2.1.00.000 - Const. Dom. Pub. por Administración Central": [
            "24.2.2.1.02.000 - Construcciones Dom. Publ. por Adm. Central (Afectado)"
        ],
        "24.3.0.0.00.000 - Maquinaria y equipo": [
            "24.3.1.0.00.000 - Maquinaria y equipo de producción",
            "24.3.2.0.00.000 - Equipo de transporte, tracción y elevación",
            "24.3.2.1.00.000 - Equipo de transporte, tracción y elevación (R. Prov)",
            "24.3.2.2.00.000 - Equipo de transporte, tracción y elevación (R Propio)",
            "24.3.3.0.00.000 - Equipo Sanitario y de Laboratorio",
            "24.3.4.0.00.000 - Equipo de comunicación y señalamiento",
            "24.3.5.0.00.000 - Equipo educacional y recreativo",
            "24.3.6.0.00.000 - Equipo para computación",
            "24.3.7.2.00.000 - Equipo de Oficina y Mueble (F Prov)",
            "24.3.8.0.00.000 - Herramientos y repuestos mayores",
            "24.3.9.0.00.000 - Equipos Varios"
        ],
        "24.4.0.0.00.000 - Equipo de seguridad": [
            "24.4.0.0.00.000 - Equipo de seguridad"
        ],
        "24.5.0.0.00.000 - Libros, revistas y otros elementos coleccionables": [
            "24.5.0.0.00.000 - Libros, revistas y otros elementos coleccionables"
        ],
        "24.6.0.0.00.000 - Obras de arte": [
            "24.6.0.0.00.000 - Obras de arte"
        ],
        "24.7.0.0.00.000 - Semovientes": [
            "24.7.0.0.00.000 - Semovientes"
        ],
        "24.8.0.0.00.000 - Activos intangibles": [
            "24.8.1.0.00.000 - Programas de Computación y Software",
            "24.8.9.0.00.000 - Otros activos intangible"
        ],
        "24.3.6.0.00.000 - Equipo para computación": [
            "24.3.6.0,02.000 - Equipo para computación (Fondo Provincial)"
        ],
        "24.3.9.1.00.000-Equipos Varios": [
            "24.3.9.1.01.000-Equipo y material de sonido (Fondo Propio)",
            "24.3.9.2.00.000 - Teléfonos Celulares, Tablet y Símil",
            "24.3.9.3.00.000 Electrodomésticos",
            "24.3.9.1.01.000-Equipo y material de sonido (Fondo ProV)",
            "24.3.9.1.02.000-Equipo y material de sonido (Fondo Provincial)"
        ],
        "24.3.9.4.00.000 - Equipos de y para Monitoreo": [
            "24.3.9.4.00.000 - Equipos de y para Monitoreo"
        ],
        "24.3.9.0.00.000 - Equipos Varios": [
            "24.3.9.2.00.000 - Teléfonos, Celulares, Tablet y Símil"
        ],
        "24.3.7.0.00.000 - Equipo de Oficina y Mueble": [
            "24.3.7.1.00.000 - Equipo de Oficina y Mueble (F Propio)"
        ],
        "24.2.1.0.00.000 - Construcciones en Bienes de Dominio Privado": [
            "24.2.1.1.02.000 - Const. Dominio Priv. por Adm. Central"
        ]
    },
    "5. Transferencias": {
        "25.1.0.0.00.000 - Transferencias al sector privado para financiar gastos corrientes": [
            "25.1.0.0.00.000 - Transferencias al sector privado para financiar gastos corrientes",
            "25.1.1.0.00.000 - Jubilaciones y/o retiros",
            "25.1.2.0.00.000 - Pensiones",
            "25.1.3.0.00.000 - Becas y Pasantías",
            "25.1.4.0.00.000 - Ayudas Sociales a Personas",
            "25.1.4.1.00.000 - Ayudas Sociales a Personas",
            "25.1.4.1.01.000 - Ayudas. Soc. a Personas (Viáticos Salud)",
            "25.1.4.1.02.000 - Ayudas Soc. a Personas para gastos de Alquiler",
            "25.1.4.1.03.000 - Ayudas Soc. a Personas para pago de Servicios",
            "25.1.4.1.04.000 - Ayudas Soc. a Personas para Sepelios",
            "25.1.4.1.05.000 - Ayudas Soc. a Personas para Medicamentos y Prod. Farmacéuticos",
            "25.1.4.1.06.000 - Ayudas Soc. a Personas para Gasto Corriente",
            "25.1.4.1.07.000 - Ayudas Soc. a Personas para eventos Deportivos",
            "25.1.4.2.00.000 - Premios, recompensas y reconocimientos destacados",
            "25.1.4.3.00.000 - Promoción Social",
            "25.1.4.4.00.000 - Boleto Educativo",
            "25.1.5.0.00.000 - Transferencias a Instituciones de Enseñanza",
            "25.1.5.1.00.000 - Fondo Asistencia Educativa",
            "25.1.5.1.01.000 - Instituciones Públicas",
            "25.1.5.1.02.000 - Instituciones Privadas",
            "25.1.5.2.00.000 - Otras Instituciones de Enseñanza",
            "25.1.6.0.00.000 - Transferencias para actividades científicas o académicas",
            "25.1.7.0.00.000 - Transferencias a Instituciones culturales y sociales sin fines de lucro",
            "25.1.7.1.00.000 - Transferencia a Instituciones Culturales y/o religiosas",
            "25.1.7.2.00.000 - Transferencia a Instituciones Sociales",
            "25.1.7.3.00.000 - Bomberos Voluntarios",
            "25.1.7.4.00.000 - ADESU",
            "25.1.7.5.00.000 - Vecinales",
            "25.1.7.5.01.000 - B. Centro",
            "25.1.7.5.02.000 - B. Sur",
            "25.1.7.5.03.000 - B. Sancor",
            "25.1.7.5.04.000 - B. Colón",
            "25.1.7.5.05.000 - B. Villa del Parque",
            "25.1.7.5.06.000 - B. Moreno",
            "25.1.7.5.07.000 - B. Cooperativo",
            "25.1.7.5.08.000 - B. Villa Autódromo",
            "25.1.7.5.09.000 - B. 9 de Julio",
            "25.1.7.6.00.000 - Centro Comercial y de la Producción",
            "25.1.7.7.00.000 - Instituciones de Bien Público",
            "25.1.7.8.00.000 - Presupuesto Participativo",
            "25.1.7.9.00.000 - Otras Instituciones",
            "25.1.7.9.01.000 - Comparsas",
            "25.1.7.9.02.000 - Instituciones Deportivas",
            "25.1.7.9.03.000 - Transferencia LAZOS",
            "25.1.8.0.00.000 - Transferencias a Cooperativas",
            "25.1.9.0.00.000 - Transferencias a empresas privadas"
        ],
        "25.2.0.0.00.000 - Transferencias al sector privado para financiar gastos de capital": [
            "25.2.1.0.00.000 - Transferencias a Personas",
            "25.2.1.1.00.000 - Trasnferencias a Personas Mejoramiento Habitacional",
            "25.2.1.1.01.000 - Transf. Personas. Mej. Hab. Mano de Obra",
            "25.2.1.1.02.000 - Trans. Const. Lote Propio",
            "25.2.1.2.00.000 - Transferencias a Personas para adquisición de Otros Bienes Tangibles",
            "25.2.1.3.00.000 - Transferencias a Personas para adquisición de Bienes Intangibles",
            "25.2.2.0.00.000 - Transferencias a Instituciones de Enseñanza",
            "25.2.2.1.00.000 - Fondo Asistencia Educativa",
            "25.2.2.1.01.000 - Instituciones Privadas",
            "25.2.2.1.02.000 - Instituciones Públicas",
            "25.2.3.0.00.000 - Transferencias para actividades científicas y/o académicas",
            "25.2.4.0.00.000 - Transferencias a otras instituciones culturales y sociales sin fines de lucro",
            "25.2.4.1.00.000 - Transferencias a Instituciones culturales y/o religiosas",
            "25.2.4.2.00.000 - Transferencias a Instituciones Sociales",
            "25.2.4.3.00.000 - Bomberos Voluntarios",
            "25.2.4.4.00.000 - ADESU",
            "25.2.4.5.00.000 - Vecinales",
            "25.2.4.5.01.000 - B. Centro",
            "25.2.4.5.02.000 - B. Sur",
            "25.2.4.5.03.000 - B. Sancor",
            "25.2.4.5.04.000 - B. Colón",
            "25.2.4.5.05.000 - B. Villa del Parque",
            "25.2.4.5.06.000 - B. Moreno",
            "25.2.4.5.07.000 - B. Cooperativo",
            "25.2.4.5.08.000 - B. Villa Autódromo",
            "25.2.4.5.09.000 - B. 9 de Julio",
            "25.2.4.6.00.000 - Centro Comercial y de la Producción",
            "25.2.4.7.00.000 - Instituciones de Bien Público",
            "25.2.4.8.00.000 - Presupuesto Participativo",
            "25.2.4.8.01.000 - Barrio Centro",
            "25.2.4.8.02.000 - Barrio Sur",
            "25.2.4.8.03.000 - Barrio Sancor",
            "25.2.4.8.04.000 - Barrio Colón",
            "25.2.4.8.05.000 - Barrio Villa del Parque",
            "25.2.4.8.06.000 - Barrio Moreno",
            "25.2.4.8.07.000 - Barrio Cooperativo",
            "25.2.4.8.08.000 - Barrio Villa Autódromo",
            "25.2.4.8.09.000 - Barrio 9 de Julio",
            "25.2.4.9.00.000 - Otras Instituciones",
            "25.2.4.9.01.000 - Comparsas",
            "25.2.4.9.02.000 - Instituciones Deportivas",
            "25.2.5.0.00.000 - Transferencias a Cooperativas",
            "25.2.5.1.00.000 - Transferencias a Cooperativas Escolares",
            "25.2.5.2.00.000 - Transferencias a Cooperativas empresariales con fines de lucro",
            "25.2.5.3.00.000 - Transferencias a Cooperativas empresariales sin fines de lucro",
            "25.2.5.4.00.000 - Transferencia a otras Cooperativas",
            "25.2.6.0.00.000 - Transferencias a empresas privadas",
            "25.2.4.8.01.000 - B. Centro",
            "25.2.4.8.04.000 - B. Colón",
            "25.2.4.8.02.000 - B. Sur",
            "25.2.4.8.03.000 - B. Sancor",
            "25.2.4.8.05.000 - B. Villa del Parque",
            "25.2.4.8.09.000 - B. 9 de Julio",
            "25.2.4.8.06.000 - B. Moreno",
            "25.2.4.8.07.000 - B. Cooperativo",
            "25.2.4.8.08.000 - B. Villa Autódromo"
        ],
        "25.3.0.0.00.000 - Transferencias al sector publico nacional para financiar gastos corrientes": [
            "25.3.1.0.00.000 - Transferecnias a la administración central para financiar gastos corrientes",
            "25.3.2.0.00.000 - Transferencias a Organismos descentralizados para financiar gastos corrientes",
            "25.3.3.0.00.000 - Transferencias a Instituciones de Seguridad Social para financiar gastos corrientes"
        ],
        "25.4.0.0.00.000 - Transferencias al sector publico nacional para financiar gastos de capital": [
            "25.4.1.0.00.000 - Transferencias a la administración central para gastos de Capital",
            "25.4.2.0.00.000 - Transferencias a Organismos descentralizados para financiar gastos de capital",
            "25.4.3.0.00.000 - Transferencias a instituciones de seguridad social para financiar gastos de capital"
        ],
        "25.5.0.0.00.000 - Transferencias al sector publico empresarial": [
            "25.5.1.0.00.000 - Transferencias a Instituciones públñicas financieras para financiar Gastos Corrientes",
            "25.5.2.0.00.000 - Transferecnias a empresas públicas no financieras para financiar gastos corrientes",
            "25.5.3.0.00.000 - Transferencias a empresas públicas multinacionales para financiar gastos corrientes",
            "25.5.4.0.00.000 - Transferencias a fondos fiduciarios y otros entes del sector público nacional no financiero para GC",
            "25.5.6.0.00.000 - Transferecnias a instituciones públicas financieras para financiar gastos de Capital",
            "25.5.7.0.00.000 - Transferencias a instituciones públicas financieras para financiar gastos de capital",
            "25.5.8.0.00.000 - Transferencias a empresas públicas multinacionales para financiar gastos de capital",
            "25.5.9.0.00.000 - Transferencias a fondos fiduciarios y otros entes del sect. público nacional no financiero"
        ],
        "25.6.0.0.00.000 - Transferencias a universidades nacionales": [
            "25.6.1.0.00.000 - Transferencias a Universidades nacionales para financiar Gastos Corrientes",
            "25.6.2.0.00.000 - Transferencias a Universidades Nacionales para financiar Gastos de Capital"
        ],
        "25.7.0.0.00.000 - Transferencias a instituciones provinciales y municipales para financiar gastos corrientes": [
            "25.7.1.0.00.000 - Transferencias a Gobiernos Provinciales",
            "25.7.2.0.00.000 - Transferencias a instituciones públicas financieras provinciales",
            "25.7.3.0.00.000 - Transferencias a empresas públicas no financieras provinciales",
            "25.7.4.0.00.000 - Transferencias a instituciones de enseñanza provinciales",
            "25.7.4.1.00.000 - Fondo de Asistencia Educativa",
            "25.7.5.0.00.000 - Transferencias a Instituciones Públicas no financieras municipales",
            "25.7.6.0.00.000 - Transferencias a gobiernos y entes municipales",
            "25.7.6.1.00.000 - Concejo Municipal",
            "25.7.6.2.00.000 - Patrimonio Cultural Sunchalense",
            "25.7.6.3.00.000 - Concejo de Inclusión y Discapacidad",
            "25.7.6.4.00.000 - Comisión Niños y Adolescentes",
            "25.7.6.5.00.000 - Fondo Acción Vecinal",
            "25.7.6.6.00.000 - GIRSU",
            "25.7.6.7.00.000 - Instituto Municipal de la Vivienda",
            "25.7.7.0.00.000 - Transferencias a instituciones públicas financieras municipales",
            "25.7.8.0.00.000 - Transferencias a empresas públicas no financieras municipales",
            "25.7.9.0.00.000 - Transferencias a instituciones públicas provinciales",
            "25.7.9.1.00.000 - Transferencia S.A.M.C.O",
            "25.7.9.2.00.000 - Transferencia Policía de Santa Fe",
            "25.7.9.3.00.000 - Transferencia Policía Rural \"Los Pumas\"",
            "25.7.9.5.00.000 - ENRESS",
            "25.7.9.6.00.000 - Fondo Departamento Castellanos"
        ],
        "25.8.0.0.00.000 - Transferencias a instituciones provinciales y municipales para financiar gastos de capital": [
            "25.8.1.0.00.000 - Transferencias a gobiernos provinciales",
            "25.8.2.0.00.000 - Transferencias a instituciones públicas financieras provinciales",
            "25.8.3.0.00.000 - Transferencias a gobiernos y entes municipales",
            "25.8.3.1.00.000 - Concejo Municipal",
            "25.8.3.2.00.000 - Patrimonio Cultural Sunchalense",
            "25.8.3.3.00.000 - Concejo de Inclusión y Discapacidad",
            "25.8.3.4.00.000 - Comisión Niños y Adolescentes",
            "25.8.3.5.00.000 - Fondo de Acción Vecinal",
            "25.8.3.6.00.000 - GIRSU",
            "25.8.3.7.00.000 - Instituto Municipal de la Vivienda",
            "25.8.4.0.00.000 - Transferencias a Instituciones Públicas Provinciales",
            "25.8.4.1.00.000 - Transferencia S.A.M.C.O",
            "25.8.4.2.00.000 - Transferencia Policía de Santa Fe",
            "25.8.4.3.00.000 - Transferencia Policía Rural \"Los Pumas\"",
            "25.8.5.0.00.000 - Transferencia a Instituciones de enseñanza",
            "25.8.5.1.00.000 - Transferencias a Instituciones de enseñanza Provincial",
            "25.8.5.1.01.000 - Transferencia a Instituciones de enseñanza Provincial Privada",
            "25.8.5.1.01.001 - Fondo de Asistencia Educativa",
            "25.8.5.1.02.000 - Transferencias a Instituciones de enseñanza Provincial Pública",
            "25.8.5.1.02.001 - Fondo de Asistencia Educativa",
            "25.8.5.2.00.000 - Transferencias a Instituciones de enseñanza Local",
            "25.8.5.2.01.000 - Transferencias a Instituciones de enseñanza local Privada",
            "25.8.5.2.01.001 - Fondo de Asistencia Educativa",
            "25.8.5.2.02.000 - Transferencias a Instituciones de enseñanza local Pública",
            "25.8.5.2.02.001 - Fondo de Asistencia Educativa",
            "25.8.5.1.02.002 Transferencia a Instituciones de enseñanza Pública Provincial"
        ]
    },
    "6. Activos Financieros": {
        "26.1.0.0.00.000 - Aportes de capital": [
            "26.1.1.0.00.000 - Aportes de Capital a empresas privadas",
            "26.1.2.0.00.000 - Aportes de Capital a empresas públicas no financieras",
            "26.1.3.0.00.000 - Aportes de Capital a Instituciones Públicas Financieras"
        ],
        "26.2.0.0.00.000 - Prestamos a corto plazo": [
            "26.2.1.0.00.000 - Préstamos a Corto plazo al Sector Privado",
            "26.2.1.1.00.000 - Préstamo a Microemprendedores",
            "26.2.1.2.00.000 - Préstamo a Emprendedores",
            "26.2.1.3.00.000 - Préstamos a empresas",
            "26.2.1.4.00.000 - Préstamos a Pymes",
            "26.2.1.5.00.000 - Préstamos a Instituciones",
            "26.2.1.5.01.000 - Préstamos a Instituciones Públicas No Financieras",
            "26.2.1.5.02.000 - Préstamo a Instituciones Públicas Financieras",
            "26.2.1.5.03.000 - Préstamo a Instituciones Privadas No Financieras",
            "26.2.1.5.04.000 - Préstamo a Instituciones Privadas Financieras",
            "26.2.1.6.00.000 - Préstamo a Personas",
            "26.2.1.6.01.000 - Préstamos Aportes Sociales Reintegrables",
            "26.2.1.6.01.001 - Préstamos Aporte Social Reintegrable para Salud",
            "26.2.1.6.01.002 - Préstamo Aporte Social Reintegrable para Alquiler",
            "26.2.1.6.01.003 - Préstamo Aporte Social Reintegrable para Sepelio",
            "26.2.1.6.01.004 - Préstamo Aporte Social Reintegrable para Servicios Básicos",
            "26.2.1.6.01.005 - Préstamo Aporte Social Reintegrable (Otros)",
            "26.2.1.6.02.000 - Préstamos Empleados"
        ],
        "26.3.0.0.00.000 - Prestamos a largo plazo": [
            "26.3.1.0.00.000 - Préstamos a Largo Plazo al Sector Privado",
            "26.3.1.1.00.000 - Préstamos a Microemprendedores",
            "26.3.1.2.00.000 - Préstamos a Emprendedores",
            "26.3.1.3.00.000 - Préstamos a Empresas",
            "26.3.1.4.00.000 - Préstamo a Pymes",
            "26.3.1.5.00.000 - Préstamos a Instituciones",
            "26.3.1.5.01.000 - Préstamo a Instituciones Públicas No Financieras",
            "26.3.1.5.02.000 - Préstamo a Instituciones Públicas Financieras",
            "26.3.1.5.03.000 - Préstamo a Instituciones Privadas No Financieras",
            "26.3.1.5.04.000 - Préstamo a Instituciones Privadas Financieras"
        ],
        "26.4.0.0.00.000 - Titulos y valores": [
            "26.4.1.0.00.000 - Títulos y Valores a Corto Plazo",
            "26.4.2.0.00.000 - Títulos y Valores a Largo Plazo"
        ],
        "26.5.0.0.00.000 - Incremento de disponibilidades": [
            "26.5.1.0.00.000 - Incremento de Caja y Bancos",
            "26.5.2.0.00.000 - Incremento de Inversiones financieras temporarias",
            "26.6.0.0.00.000 - Incremento de cuentas a cobrar",
            "26.6.1.0.00.000 - Incremento de Ctas. Comerciales a cobrar a corto plazo",
            "26.6.2.0.00.000 - Incremento de Otras Ctas. a cobrar a corto plazo",
            "26.6.3.0.00.000 - Incremento de Ctas. a cobrar comerciales a largo plazo",
            "26.6.4.0.00.000 - Incremento de otros documentos a cobrar a largo plazo"
        ],
        "26.7.0.0.00.000 - Incremento de documentos a cobrar": [
            "26.7.1.0.00.000 - Incremento de documentos comerciales a cobrar a corto plazo",
            "26.7.2.0.00.000 - Incremento de otros documentos a cobrar a corto plazo",
            "26.7.3.0.00.000 - Incremento de documentos comerciales a cobrar a largo plazo",
            "26.7.4.0.00.000 - Incremento de otros documentos a cobrar a largo plazo"
        ],
        "26.8.0.0.00.000 - Incremento de activos diferidos y adelantos a proveedores y contratistas": [
            "26.8.0.0.00.000 - Incremento de activos diferidos y adelantos a proveedores y contratistas"
        ]
    },
    "7. Servicio de la deuda": {
        "27.0.0.0.00.000 - Servicio de la deuda y disminución de otros pasivos": [
            "27.1.0.0.00.000 - Servicio de la deuda interna",
            "27.1.1.0.00.000 - Intereses de la deuda a Corto Plazo",
            "27.1.2.0.00.000 - Amortización de la deuda interna a corto plazo",
            "27.1.3.0.00.000 - Comisiones y otros gastos de la deuda interna a corto plazo",
            "27.1.7.0.00.000 - Amortización de la deuda interna a largo plazo"
        ],
        "27.2.0.0.00.000 - Servicio de la deuda externa": [
            "27.2.0.0.00.000 - Servicio de la deuda externa"
        ],
        "27.3.0.0.00.000 - Intereses por prestamos recibidos": [
            "27.3.0.0.00.000 - Intereses por prestamos recibidos"
        ],
        "27.4.0.0.00.000 - Disminucion de prestamos a corto plazo": [
            "27.4.0.0.00.000 - Disminucion de prestamos a corto plazo"
        ],
        "27.5.0.0.00.000 - Disminucion de prestamos a largo plazo": [
            "27.5.0.0.00.000 - Disminucion de prestamos a largo plazo",
            "27.5.5.0.00.000 - Disminución de préstamos a largo plazo recibidos de provincia y municipalidades"
        ],
        "27.6.0.0.00.000 - Disminucion de cuentas y documentos a pagar": [
            "27.6.1.0.00.000 - Disminucion de cuentas comerciales a pagar",
            "27.6.1.0.00.000 - Disminucion de cuentas y documentos a pagar",
            "27.6.2.0.00.000 - Disminucion de otras cuentas a pagar a corto plazo"
        ],
        "27.7.0.0.00.000 - Disminucion de depósitos en instituciones públicas financieras": [
            "27.7.0.0.00.000 - Disminucion de depósitos en instituciones públicas financieras"
        ],
        "27.8.0.0.00.000 - Disminucion de otros pasivos": [
            "27.8.0.0.00.000 - Disminucion de otros pasivos"
        ],
        "27.9.0.0.00.000 - Conversion de la deuda": [
            "27.9.0.0.00.000 - Conversion de la deuda"
        ]
    },
    "8. Otros Gastos": {
        "28.0.0.0.00.000 - Otros gastos": [
            "28.1.0.0.00.000 - Intereses de instituciones publicas financieras",
            "28.2.0.0.00.000 - Depreciacon y amortizacion",
            "28.3.0.0.00.000 - Descuentos y bonificaciones",
            "28.4.0.0.00.000 - Otras perdidas",
            "28.5.0.0.00.000 - Disminucion del patrimonio"
        ]
    },
    "9. Gastos figurativos": {
        "29.0.0.0.00.000 - Gastos figurativos": [
            "29.1.0.0.00.000 - Gastos figurativos de la administración provincial para transacciones corrientes",
            "29.2.0.0.00.000 - Gastos figurativos de la administración provincial para transacciones de capital",
            "29.3.0.0.00.000 - Gastos figurativos de la administración provincial para aplicaciones"
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
opciones_finalidad = ["Administración Central", "Promoción y asistencia social","Educación","Cultura","Ciencia y técnica","Servicios urbanos","Vivienda y urbanismo","Deuda Pública","Ecología y medio ambiente","Deporte y recreación","Obra pública","Apoyo a Instituciones","Desarrollo de Gestión","Legislativa", "Salud", "Seguridad","Promoción industrial y Laboral"]

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
            "🛠️ PANEL DE MODIFICACIONES",
            "📊 REPORTE CONSOLIDADO Y ESTADÍSTICAS",
            "🔍 BUSCADOR AVANZADO",
            "📄 EXPORTACIÓN Y FIRMAS",
            "🏆 RANKING Y MAYORES EROGACIONES",
            "⚖️ COMPARATIVO DE ESTRUCTURA Y FUENTES",
            "🧹 AUDITORÍA Y CONTROL DE CALIDAD",
            "🏢 VISTA POR SECRETARÍA Y SUBSECRETARÍA",
            "🎯 REPORTE POR FINALIDAD Y FUNCIÓN",
            "📦 TOTALES POR OBJETO DEL GASTO",
            "📊 MATRIZ SUBSECRETARÍA VS OBJETOS",
            # --- NUEVAS 5 SECCIONES ---
            "📈 PROYECCIÓN Y ESTRUCTURA TEMPORAL",
            "🏛️ CLASIFICACIÓN ECONÓMICA DEL GASTO",
            "🛡️ CONTROL DE TECHOS PRESUPUESTARIOS",
            "📋 FICHA TÉCNICA POR DESTINO",
            "🔄 COMPARATIVO E HISTÓRICO"
        ]
    )
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
# =====================================================================
# SECCIÓN 6: REPORTE CONSOLIDADO Y ESTADÍSTICAS (NUEVA)
# =====================================================================
elif opcion_menu == "📊 REPORTE CONSOLIDADO Y ESTADÍSTICAS":
    st.subheader("📊 Análisis Consolidado del Presupuesto 2027")

    if df_egr_completo.empty or df_egr_completo["total"].sum() == 0:
        st.info("💡 No hay registros contables cargados para generar estadísticas.")
    else:
        tot_gral = df_egr_completo["total"].sum()
        cant_reg = len(df_egr_completo)
        promedio = df_egr_completo["total"].mean()

        m1, m2, m3 = st.columns(3)
        m1.metric("💰 Total Presupuesto Acumulado", f"${tot_gral:,.2f}")
        m2.metric("📋 Cantidad de Registros Cargados", f"{cant_reg}")
        m3.metric("📊 Promedio por Renglón", f"${promedio:,.2f}")

        st.markdown("---")
        col_g1, col_g2 = st.columns(2)

        with col_g1:
            st.markdown("##### 📍 Total Presupuestado por Secretaría")
            df_sec = df_egr_completo.groupby("secretaria")["total"].sum().reset_index()
            df_sec["total_fmt"] = df_sec["total"].map(lambda x: f"${x:,.2f}")
            st.dataframe(df_sec.rename(columns={"secretaria": "SECRETARÍA", "total_fmt": "TOTAL ($)"}), use_container_width=True, hide_index=True)

        with col_g2:
            st.markdown("##### 🏛️ Distribución por Fuente de Financiamiento")
            df_fuente = df_egr_completo.groupby("fuente_fin")["total"].sum().reset_index()
            df_fuente["total_fmt"] = df_fuente["total"].map(lambda x: f"${x:,.2f}")
            st.dataframe(df_fuente.rename(columns={"fuente_fin": "FUENTE FINANCIAMIENTO", "total_fmt": "TOTAL ($)"}), use_container_width=True, hide_index=True)


# =====================================================================
# SECCIÓN 7: BUSCADOR AVANZADO (NUEVA)
# =====================================================================
elif opcion_menu == "🔍 BUSCADOR AVANZADO":
    st.subheader("🔍 Buscador Filtrado de Partidas Presupuestarias")

    if df_egr_completo.empty:
        st.info("💡 La base de datos está vacía en este momento.")
    else:
        st.caption("Filtrá por palabras clave en cualquier campo o establecé un rango de montos.")
        
        col_b1, col_b2, col_b3 = st.columns(3)
        with col_b1:
            texto_buscar = st.text_input("🔎 Palabra clave (Texto/Destino/Partida):").strip().lower()
        with col_b2:
            min_monto = st.number_input("Monto Mínimo ($):", min_value=0.0, value=0.0)
        with col_b3:
            max_monto = st.number_input("Monto Máximo ($):", min_value=0.0, value=float(df_egr_completo["total"].max() or 1000000000.0))

        # Filtrado
        df_busqueda = df_egr_completo.copy()
        
        if texto_buscar:
            mask_texto = df_busqueda.astype(str).apply(lambda row: row.str.lower().str.contains(texto_buscar).any(), axis=1)
            df_busqueda = df_busqueda[mask_texto]

        df_busqueda = df_busqueda[(df_busqueda["total"] >= min_monto) & (df_busqueda["total"] <= max_monto)]

        st.markdown(f"**Resultados encontrados:** {len(df_busqueda)} renglón(es)")
        
        if not df_busqueda.empty:
            df_v_busq = df_busqueda.copy()
            df_v_busq["total"] = df_v_busq["total"].map(lambda x: f"${x:,.2f}")
            st.dataframe(df_v_busq, use_container_width=True, hide_index=True)
        else:
            st.warning("No se encontraron registros que coincidan con los criterios de búsqueda.")


# =====================================================================
# SECCIÓN 8: EXPORTACIÓN Y FIRMAS (REPORTE OFICIAL COMPLETO CON FIRMAS)
# =====================================================================
elif opcion_menu == "📄 EXPORTACIÓN Y FIRMAS":
    st.subheader("📄 Exportación General Oficial por Destino (con Cuadro de Firmas)")

    if df_egr_completo.empty:
        st.info("💡 No hay registros contables cargados en el sistema para exportar.")
    else:
        st.caption("Generá un documento oficial en formato HTML para imprimir o guardar en PDF que agrupa automáticamente **TODOS los Destinos** con el formato oficial municipal e incluye el panel de firmas al pie.")

        tot_general_exp = df_egr_completo["total"].sum()
        st.metric(label="📋 TOTAL GENERAL A EXPORTAR", value=f"${tot_general_exp:,.2f}")

        bloques_html_destinos = ""

        # Agrupar todos los registros cargados por Secretaría, Subsecretaría y Destino
        for (sec_exp, sub_exp, dest_exp), df_dest_exp in df_egr_completo.groupby(["secretaria", "subsecretaria", "destino"]):
            tot_dest_exp = df_dest_exp["total"].sum()
            
            rows_dest_exp = ""
            # Agrupar por Objeto del Gasto
            for obj, df_obj in df_dest_exp.groupby("objeto_gasto"):
                t_o = df_obj["total"].sum()
                rows_dest_exp += f'<tr style="font-weight: bold; background-color: #f9f9f5;"><td style="text-align: left; padding-left: 5px;">{obj}</td><td style="text-align: right;">${t_o:,.2f}</td><td></td><td></td><td></td><td></td></tr>'
                
                # Agrupar por Cuenta Padre
                for pad, df_pad in df_obj.groupby("cuenta_padre"):
                    t_p = df_pad["total"].sum()
                    rows_dest_exp += f'<tr style="font-weight: bold;"><td style="text-align: left; padding-left: 20px;">{pad}</td><td style="text-align: right;">${t_p:,.2f}</td><td></td><td></td><td></td><td></td></tr>'
                    
                    # Imprimir Cuentas de Imputación
                    for _, r in df_pad.iterrows():
                        rows_dest_exp += f'<tr><td style="text-align: left; padding-left: 40px;">{r["cuenta_presupuestaria"]}</td><td style="text-align: right;">${r["total"]:,.2f}</td><td style="text-align: center;">{r["fuente_fin"]}</td><td style="text-align: center;">{r["clase"]}</td><td style="text-align: center;">{r["tipo"]}</td><td style="text-align: center;">{r["finalidad"]}</td></tr>'

            # Armar bloque gráfico oficial por Destino
            bloques_html_destinos += f"""
            <div class="bloque-destino">
                <div class="m-box">
                    <table class="t-hdr">
                        <tr>
                            <td style="width: 25%; text-align: left; font-size: 10px;"><b>Municipalidad de Sunchales</b><br><span style="font-size: 8px; color: #555;">Presupuesto Oficial 2027</span></td>
                            <td style="width: 50%; text-align: center;"><b>PRESUPUESTO DE GASTO POR DESTINO</b><br><small>-2027-</small></td>
                            <td style="width: 25%;" class="b-tot"><small>Total Destino</small><br><b>${tot_dest_exp:,.2f}</b></td>
                        </tr>
                    </table>
                    <div style="border-top: 1px solid #000; font-size: 11px; padding-top: 6px; margin-top: 6px;">
                        <b>SECRETARÍA:</b> {sec_exp} | <b>SUBSECRETARÍA:</b> {sub_exp} | <span style="float: right;"><b>DESTINO:</b> {str(dest_exp).upper()}</span>
                    </div>
                </div>

                <table class="tabla-datos">
                    <thead>
                        <tr>
                            <th>OBJETO DEL GASTO</th>
                            <th style="text-align: right;">PRESUPUESTO</th>
                            <th>F.FIN</th>
                            <th>CLASE</th>
                            <th>TIPO</th>
                            <th>FINANCIAMIENTO</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_dest_exp}
                    </tbody>
                </table>
                <div class="salto-pagina"></div>
            </div>
            """

        # HTML General Completo con Estilos y Cuadro de Firmas Final
        html_completo_oficial = f"""
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                @page {{ size: A4 landscape; margin: 12mm; }}
                body {{ font-family: Arial, sans-serif; color: #000; margin: 0 auto; width: 100%; max-width: 1050px; }}
                .m-box {{ border: 1px solid #000; padding: 10px; margin-bottom: 15px; background-color: #fff; }}
                .t-hdr {{ width: 100%; border-collapse: collapse; }}
                .t-hdr td {{ padding: 4px; vertical-align: middle; border: none; }}
                .b-tot {{ border: 1px solid #000; background-color: #f5f5f5; text-align: center; }}
                .tabla-datos {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 11px; margin-bottom: 25px; }}
                .tabla-datos th {{ border-bottom: 2px solid #000; padding: 6px 4px; text-align: center; font-weight: bold; background-color: #f2f2f2; }}
                .tabla-datos td {{ border-bottom: 1px solid #e0e0e0; padding: 6px 4px; vertical-align: middle; text-align: center; }}
                .tabla-datos th:first-child, .tabla-datos td:first-child {{ text-align: left !important; padding-left: 8px; }}
                .salto-pagina {{ page-break-after: always; }}
                .firmas-container {{ margin-top: 50px; width: 100%; page-break-inside: avoid; }}
                .firma-box {{ width: 30%; float: left; text-align: center; border-top: 1px solid #000; padding-top: 5px; margin: 0 1.5%; font-size: 11px; font-weight: bold; }}
                .resumen-final {{ border: 2px solid #000; padding: 15px; margin-top: 20px; background-color: #fafafa; text-align: center; font-size: 14px; page-break-inside: avoid; }}
            </style>
        </head>
        <body onload="window.print();">
            {bloques_html_destinos}

            <div class="resumen-final">
                <b>TOTAL GENERAL PRESUPUESTO MUNICIPAL 2027:</b> ${tot_general_exp:,.2f}
            </div>

            <div class="firmas-container">
                <div class="firma-box">Responsable Presupuesto</div>
                <div class="firma-box">Contaduría General</div>
                <div class="firma-box">Intendente / Secretario</div>
            </div>
        </body>
        </html>
        """

        st.download_button(
            label="🖨️ GENERAR Y DESCARGAR REPORTE CONSOLIDADO COMPLETO (PDF/PRINT)",
            data=html_completo_oficial,
            file_name=f"Presupuesto_Oficial_Consolidado_{time.strftime('%Y%m%d')}.html",
            mime="text/html",
            use_container_width=True,
            type="primary"
        )
# =====================================================================
# SECCIÓN 9: RANKING Y MAYORES EROGACIONES (NUEVA)
# =====================================================================
elif opcion_menu == "🏆 RANKING Y MAYORES EROGACIONES":
    st.subheader("🏆 Ranking de Partidas y Erogaciones Mayores")

    if df_egr_completo.empty:
        st.info("💡 No hay registros para analizar.")
    else:
        top_n = st.slider("Cantidad de partidas a mostrar:", min_value=3, max_value=20, value=10)
        
        df_sorted = df_egr_completo.sort_values(by="total", ascending=False).head(top_n).copy()
        df_sorted["total"] = df_sorted["total"].map(lambda x: f"${x:,.2f}")

        st.markdown(f"##### 🔝 Top {top_n} Renglones Presupuestarios de Mayor Importe")
        st.dataframe(
            df_sorted[["secretaria", "destino", "objeto_gasto", "cuenta_presupuestaria", "total", "fuente_fin"]].rename(
                columns={
                    "secretaria": "SECRETARÍA",
                    "destino": "DESTINO",
                    "objeto_gasto": "OBJETO GASTO",
                    "cuenta_presupuestaria": "PARTIDA",
                    "total": "MONTO TOTAL ($)",
                    "fuente_fin": "FUENTE"
                }
            ),
            use_container_width=True,
            hide_index=True
        )


# =====================================================================
# SECCIÓN 10: COMPARATIVO DE ESTRUCTURA Y FUENTES (NUEVA)
# =====================================================================
elif opcion_menu == "⚖️ COMPARATIVO DE ESTRUCTURA Y FUENTES":
    st.subheader("⚖️ Matriz Comparativa: Clase de Gasto vs Fuente de Financiamiento")

    if df_egr_completo.empty:
        st.info("💡 No hay datos suficientes para armar la matriz comparativa.")
    else:
        st.caption("Cruza la Clase de Gasto (Corriente/Capital) con la Fuente de Financiamiento.")
        
        matriz = pd.pivot_table(
            df_egr_completo,
            values="total",
            index="clase",
            columns="fuente_fin",
            aggfunc="sum",
            fill_value=0.0
        )

        st.markdown("##### 📊 Matriz de Totales por Clase y Fuente ($)")
        st.dataframe(matriz.style.format("${:,.2f}"), use_container_width=True)


# =====================================================================
# SECCIÓN 11: AUDITORÍA Y CONTROL DE CALIDAD (NUEVA)
# =====================================================================
elif opcion_menu == "🧹 AUDITORÍA Y CONTROL DE CALIDAD":
    st.subheader("🧹 Panel de Auditoría y Verificación de Datos")

    if df_egr_completo.empty:
        st.info("💡 No hay datos para auditar.")
    else:
        # Detectar renglones con monto cero
        df_cero = df_egr_completo[df_egr_completo["total"] == 0]
        # Detectar renglones con campos vacíos esenciales
        df_vacios = df_egr_completo[
            (df_egr_completo["secretaria"] == "") | 
            (df_egr_completo["destino"] == "") | 
            (df_egr_completo["cuenta_presupuestaria"] == "")
        ]

        c_a1, c_a2 = st.columns(2)
        c_a1.metric("⚠️ Renglones con Monto $0.00", f"{len(df_cero)}")
        c_a2.metric("⚠️ Renglones con Datos Incompletos", f"{len(df_vacios)}")

        st.markdown("---")
        if len(df_cero) > 0:
            st.markdown("##### 🔴 Renglones con Importe en $0.00")
            st.dataframe(df_cero[["secretaria", "destino", "cuenta_presupuestaria"]], use_container_width=True, hide_index=True)
        else:
            st.success("✅ ¡Excelente! No existen renglones registrados con monto en $0.00.")

        if len(df_vacios) > 0:
            st.markdown("##### 🟡 Renglones con Campos Obligatorios Vacíos")
            st.dataframe(df_vacios[["secretaria", "subsecretaria", "destino", "cuenta_presupuestaria"]], use_container_width=True, hide_index=True)
        else:
            st.success("✅ ¡Excelente! Todos los renglones tienen su ubicación e imputación completa.")
# =====================================================================
# SECCIÓN 12: VISTA POR SECRETARÍA Y SUBSECRETARÍA (CON EXPORTACIÓN HORIZONTAL)
# =====================================================================
elif opcion_menu == "🏢 VISTA POR SECRETARÍA Y SUBSECRETARÍA":
    st.subheader("🏢 Vista Jerárquica por Secretaría y Subsecretaría")

    if df_egr_completo.empty:
        st.info("💡 No hay registros contables cargados para mostrar.")
    else:
        st.caption("Seleccioná la Secretaría y la Subsecretaría para consultar los Destinos y sus partidas presupuestarias asignadas, o exportar la planilla oficial firmable.")

        # Obtener lista de secretarías únicas
        lista_secretarias = sorted([s for s in df_egr_completo["secretaria"].unique() if str(s).strip() != ""])

        col_sec, col_sub = st.columns(2)

        with col_sec:
            sec_seleccionada = st.selectbox("1. Seleccionar Secretaría:", lista_secretarias)

        # Filtrar subsecretarías pertenecientes a la secretaría elegida
        df_sec_filtrado = df_egr_completo[df_egr_completo["secretaria"] == sec_seleccionada]
        lista_subsecretarias = sorted([s for s in df_sec_filtrado["subsecretaria"].unique() if str(s).strip() != ""])

        with col_sub:
            sub_seleccionada = st.selectbox("2. Seleccionar Subsecretaría:", lista_subsecretarias)

        # Filtrar datos finales por Secretaría y Subsecretaría
        df_area = df_sec_filtrado[df_sec_filtrado["subsecretaria"] == sub_seleccionada]

        st.markdown("---")

        if df_area.empty:
            st.warning("No se encontraron registros cargados para la combinación seleccionada.")
        else:
            tot_area = df_area["total"].sum()
            cant_destinos = df_area["destino"].nunique()

            # Métricas rápidas del Área
            m_a1, m_a2 = st.columns(2)
            m_a1.metric("💰 Presupuesto Total de la Subsecretaría", f"${tot_area:,.2f}")
            m_a2.metric("📌 Cantidad de Destinos Asignados", f"{cant_destinos}")

            st.markdown("### 📍 Resumen de Destinos")

            # Resumen acumulado por Destino
            df_destinos_resumen = df_area.groupby("destino")["total"].sum().reset_index()
            df_destinos_resumen["total_fmt"] = df_destinos_resumen["total"].map(lambda x: f"${x:,.2f}")
            df_destinos_resumen.columns = ["DESTINO", "TOTAL ($)", "PRESUPUESTO FORMATEADO"]

            st.dataframe(
                df_destinos_resumen[["DESTINO", "PRESUPUESTO FORMATEADO"]],
                use_container_width=True,
                hide_index=True
            )

            st.markdown("---")
            st.markdown("### 🔍 Detalle por Destino y Partidas")

            # Desplegable individual por Destino
            for dest, df_d in df_area.groupby("destino"):
                tot_d = df_d["total"].sum()
                with st.expander(f"📌 DESTINO: {str(dest).upper()} — Total: ${tot_d:,.2f}"):
                    df_mostrar = df_d.copy()
                    df_mostrar["total"] = df_mostrar["total"].map(lambda x: f"${x:,.2f}")
                    st.dataframe(
                        df_mostrar[["objeto_gasto", "cuenta_padre", "cuenta_presupuestaria", "total", "fuente_fin", "clase", "tipo"]].rename(
                            columns={
                                "objeto_gasto": "OBJETO GASTO",
                                "cuenta_padre": "CUENTA PADRE",
                                "cuenta_presupuestaria": "PARTIDA",
                                "total": "MONTO ($)",
                                "fuente_fin": "FUENTE",
                                "clase": "CLASE",
                                "tipo": "TIPO"
                            }
                        ),
                        use_container_width=True,
                        hide_index=True
                    )

            # -------------------------------------------------------------
            # GENERACIÓN DEL DOCUMENTO HORIZONTAL (PDF / FIRMAS)
            # -------------------------------------------------------------
            bloques_html_sec = ""

            for dest_sec, df_d_sec in df_area.groupby("destino"):
                tot_d_sec = df_d_sec["total"].sum()
                rows_d_sec = ""

                for obj, df_obj in df_d_sec.groupby("objeto_gasto"):
                    t_o = df_obj["total"].sum()
                    rows_d_sec += f'<tr style="font-weight: bold; background-color: #f9f9f5;"><td style="text-align: left; padding-left: 5px;">{obj}</td><td style="text-align: right;">${t_o:,.2f}</td><td></td><td></td><td></td><td></td></tr>'

                    for pad, df_pad in df_obj.groupby("cuenta_padre"):
                        t_p = df_pad["total"].sum()
                        rows_d_sec += f'<tr style="font-weight: bold;"><td style="text-align: left; padding-left: 20px;">{pad}</td><td style="text-align: right;">${t_p:,.2f}</td><td></td><td></td><td></td><td></td></tr>'

                        for _, r in df_pad.iterrows():
                            rows_d_sec += f'<tr><td style="text-align: left; padding-left: 40px;">{r["cuenta_presupuestaria"]}</td><td style="text-align: right;">${r["total"]:,.2f}</td><td style="text-align: center;">{r["fuente_fin"]}</td><td style="text-align: center;">{r["clase"]}</td><td style="text-align: center;">{r["tipo"]}</td><td style="text-align: center;">{r["finalidad"]}</td></tr>'

                bloques_html_sec += f"""
                <div class="bloque-destino">
                    <div class="m-box">
                        <table class="t-hdr">
                            <tr>
                                <td style="width: 25%; text-align: left; font-size: 10px;"><b>Municipalidad de Sunchales</b><br><span style="font-size: 8px; color: #555;">Presupuesto Oficial 2027</span></td>
                                <td style="width: 50%; text-align: center;"><b>PRESUPUESTO DE GASTO POR SUBSECRETARÍA</b><br><small>-2027-</small></td>
                                <td style="width: 25%;" class="b-tot"><small>Total Destino</small><br><b>${tot_d_sec:,.2f}</b></td>
                            </tr>
                        </table>
                        <div style="border-top: 1px solid #000; font-size: 11px; padding-top: 6px; margin-top: 6px;">
                            <b>SECRETARÍA:</b> {sec_seleccionada} | <b>SUBSECRETARÍA:</b> {sub_seleccionada} | <span style="float: right;"><b>DESTINO:</b> {str(dest_sec).upper()}</span>
                        </div>
                    </div>

                    <table class="tabla-datos">
                        <thead>
                            <tr>
                                <th>OBJETO DEL GASTO</th>
                                <th style="text-align: right;">PRESUPUESTO</th>
                                <th>F.FIN</th>
                                <th>CLASE</th>
                                <th>TIPO</th>
                                <th>FINANCIAMIENTO</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows_d_sec}
                        </tbody>
                    </table>
                    <div class="salto-pagina"></div>
                </div>
                """

            html_sec_oficial = f"""
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    @page {{ size: A4 landscape; margin: 12mm; }}
                    body {{ font-family: Arial, sans-serif; color: #000; margin: 0 auto; width: 100%; max-width: 1050px; }}
                    .m-box {{ border: 1px solid #000; padding: 10px; margin-bottom: 15px; background-color: #fff; }}
                    .t-hdr {{ width: 100%; border-collapse: collapse; }}
                    .t-hdr td {{ padding: 4px; vertical-align: middle; border: none; }}
                    .b-tot {{ border: 1px solid #000; background-color: #f5f5f5; text-align: center; }}
                    .tabla-datos {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 11px; margin-bottom: 25px; }}
                    .tabla-datos th {{ border-bottom: 2px solid #000; padding: 6px 4px; text-align: center; font-weight: bold; background-color: #f2f2f2; }}
                    .tabla-datos td {{ border-bottom: 1px solid #e0e0e0; padding: 6px 4px; vertical-align: middle; text-align: center; }}
                    .tabla-datos th:first-child, .tabla-datos td:first-child {{ text-align: left !important; padding-left: 8px; }}
                    .salto-pagina {{ page-break-after: always; }}
                    .firmas-container {{ margin-top: 50px; width: 100%; page-break-inside: avoid; }}
                    .firma-box {{ width: 30%; float: left; text-align: center; border-top: 1px solid #000; padding-top: 5px; margin: 0 1.5%; font-size: 11px; font-weight: bold; }}
                    .resumen-final {{ border: 2px solid #000; padding: 15px; margin-top: 20px; background-color: #fafafa; text-align: center; font-size: 14px; page-break-inside: avoid; }}
                </style>
            </head>
            <body onload="window.print();">
                {bloques_html_sec}

                <div class="resumen-final">
                    <b>TOTAL PRESUPUESTO - {sub_seleccionada}:</b> ${tot_area:,.2f}
                </div>

                <div class="firmas-container">
                    <div class="firma-box">Responsable Presupuesto</div>
                    <div class="firma-box">Contaduría General</div>
                    <div class="firma-box">Intendente / Secretario</div>
                </div>
            </body>
            </html>
            """

            st.markdown("---")
            st.download_button(
                label="🖨️ GENERAR Y DESCARGAR REPORTE DE ESTA SUBSECRETARÍA (PDF HORIZONTAL / FIRMAS)",
                data=html_sec_oficial,
                file_name=f"Reporte_{sub_seleccionada.replace(' ', '_')}_2027.html",
                mime="text/html",
                use_container_width=True,
                type="primary"
            )
# =====================================================================
# SECCIÓN 13: REPORTE POR FINALIDAD Y FUNCIÓN (CON EXPORTACIÓN OFICIAL)
# =====================================================================
elif opcion_menu == "🎯 REPORTE POR FINALIDAD Y FUNCIÓN":
    st.subheader("🎯 Consolidado Presupuestario por Finalidad y Función")

    if df_egr_completo.empty:
        st.info("💡 No hay registros contables cargados para generar el reporte de finalidades.")
    else:
        st.caption("Resumen consolidado con la suma total del presupuesto distribuido por **Finalidad y Función**, listo para consultar en pantalla o exportar con formato oficial.")

        # Identificar columnas
        col_fin = "finalidad" if "finalidad" in df_egr_completo.columns else df_egr_completo.columns[0]
        col_fun = "tipo" if "tipo" in df_egr_completo.columns else col_fin

        tot_general_ff = df_egr_completo["total"].sum()

        st.metric("💰 TOTAL GENERAL PRESUPUESTO", f"${tot_general_ff:,.2f}")

        # Agrupamiento principal
        df_fin_fun = df_egr_completo.groupby([col_fin, col_fun])["total"].sum().reset_index()

        # -------------------------------------------------------------
        # VISTA EN PANTALLA (TABLA INTERACTIVA)
        # -------------------------------------------------------------
        st.markdown("---")
        st.markdown("##### 📋 Resumen en Pantalla")

        df_tabla_ff = df_fin_fun.copy()
        df_tabla_ff["porcentaje"] = (df_tabla_ff["total"] / (tot_general_ff if tot_general_ff > 0 else 1)) * 100
        df_tabla_ff["total_fmt"] = df_tabla_ff["total"].map(lambda x: f"${x:,.2f}")
        df_tabla_ff["porcentaje_fmt"] = df_tabla_ff["porcentaje"].map(lambda x: f"{x:.2f}%")

        st.dataframe(
            df_tabla_ff[[col_fin, col_fun, "total_fmt", "porcentaje_fmt"]].rename(
                columns={
                    col_fin: "FINALIDAD",
                    col_fun: "FUNCIÓN / TIPO",
                    "total_fmt": "TOTAL PRESUPUESTADO ($)",
                    "porcentaje_fmt": "% DEL TOTAL"
                }
            ),
            use_container_width=True,
            hide_index=True
        )

        # -------------------------------------------------------------
        # GENERACIÓN DEL DOCUMENTO IMPRESO / PDF OFICIAL
        # -------------------------------------------------------------
        rows_html_ff = ""

        # Recorrer por Finalidad y luego por Función
        for fin, df_g in df_fin_fun.groupby(col_fin):
            t_fin = df_g["total"].sum()
            pct_fin = (t_fin / (tot_general_ff if tot_general_ff > 0 else 1)) * 100
            
            # Fila de Cabecera por Finalidad (Negrita)
            rows_html_ff += f'<tr style="font-weight: bold; background-color: #f2f2f2;"><td style="text-align: left; padding-left: 8px;">{fin}</td><td style="text-align: right;">${t_fin:,.2f}</td><td style="text-align: center;">{pct_fin:.2f}%</td></tr>'
            
            # Filas de Función / Tipo (Sangría)
            for _, r in df_g.iterrows():
                pct_fun = (r["total"] / (tot_general_ff if tot_general_ff > 0 else 1)) * 100
                rows_html_ff += f'<tr><td style="text-align: left; padding-left: 30px;">{r[col_fun]}</td><td style="text-align: right;">${r["total"]:,.2f}</td><td style="text-align: center;">{pct_fun:.2f}%</td></tr>'

        # Documento HTML Completo con membrete oficial y cuadro de firmas
        html_ff_oficial = f"""
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                @page {{ size: A4 portrait; margin: 12mm; }}
                body {{ font-family: Arial, sans-serif; color: #000; margin: 0 auto; width: 100%; max-width: 900px; }}
                .m-box {{ border: 1px solid #000; padding: 10px; margin-bottom: 20px; background-color: #fff; }}
                .t-hdr {{ width: 100%; border-collapse: collapse; }}
                .t-hdr td {{ padding: 4px; vertical-align: middle; border: none; }}
                .b-tot {{ border: 1px solid #000; background-color: #f5f5f5; text-align: center; }}
                .tabla-datos {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 11px; margin-bottom: 25px; }}
                .tabla-datos th {{ border-bottom: 2px solid #000; padding: 6px 4px; text-align: center; font-weight: bold; background-color: #f2f2f2; }}
                .tabla-datos td {{ border-bottom: 1px solid #e0e0e0; padding: 6px 4px; vertical-align: middle; }}
                .firmas-container {{ margin-top: 50px; width: 100%; page-break-inside: avoid; }}
                .firma-box {{ width: 30%; float: left; text-align: center; border-top: 1px solid #000; padding-top: 5px; margin: 0 1.5%; font-size: 11px; font-weight: bold; }}
                .resumen-final {{ border: 2px solid #000; padding: 12px; margin-top: 20px; background-color: #fafafa; text-align: center; font-size: 13px; page-break-inside: avoid; }}
            </style>
        </head>
        <body onload="window.print();">
            <div class="m-box">
                <table class="t-hdr">
                    <tr>
                        <td style="width: 25%; text-align: left; font-size: 10px;"><b>Municipalidad de Sunchales</b><br><span style="font-size: 8px; color: #555;">Presupuesto Oficial 2027</span></td>
                        <td style="width: 50%; text-align: center;"><b>PRESUPUESTO POR FINALIDAD Y FUNCIÓN</b><br><small>-2027-</small></td>
                        <td style="width: 25%;" class="b-tot"><small>Total Presupuesto</small><br><b>${tot_general_ff:,.2f}</b></td>
                    </tr>
                </table>
            </div>

            <table class="tabla-datos">
                <thead>
                    <tr>
                        <th style="text-align: left; padding-left: 8px;">FINALIDAD / FUNCIÓN</th>
                        <th style="text-align: right;">PRESUPUESTO ($)</th>
                        <th style="text-align: center;">% DEL TOTAL</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html_ff}
                </tbody>
            </table>

            <div class="resumen-final">
                <b>TOTAL GENERAL DEL PRESUPUESTO MUNICIPAL:</b> ${tot_general_ff:,.2f}
            </div>

            <div class="firmas-container">
                <div class="firma-box">Responsable Presupuesto</div>
                <div class="firma-box">Contaduría General</div>
                <div class="firma-box">Intendente / Secretario</div>
            </div>
        </body>
        </html>
        """

        st.markdown("---")
        st.download_button(
            label="🖨️ GENERAR Y DESCARGAR REPORTE DE FINALIDAD Y FUNCIÓN (PDF / FIRMAS)",
            data=html_ff_oficial,
            file_name=f"Reporte_Finalidad_y_Funcion_2027.html",
            mime="text/html",
            use_container_width=True,
            type="primary"
        )
# =====================================================================
# SECCIÓN 14: TOTALES POR OBJETO DEL GASTO (NUEVA)
# =====================================================================
elif opcion_menu == "📦 TOTALES POR OBJETO DEL GASTO":
    st.subheader("📦 Consolidado Presupuestario por Objeto del Gasto")

    if df_egr_completo.empty:
        st.info("💡 No hay registros contables cargados para generar el reporte por Objeto del Gasto.")
    else:
        st.caption("Resumen general del presupuesto acumulado por cada **Objeto del Gasto**, con porcentajes de participación y opción de impresión oficial.")

        tot_general_obj = df_egr_completo["total"].sum()
        st.metric("💰 TOTAL GENERAL PRESUPUESTO", f"${tot_general_obj:,.2f}")

        # Agrupamiento por Objeto del Gasto
        df_obj_res = df_egr_completo.groupby("objeto_gasto")["total"].sum().reset_index()
        df_obj_res["porcentaje"] = (df_obj_res["total"] / (tot_general_obj if tot_general_obj > 0 else 1)) * 100
        
        # Tabla en Pantalla
        st.markdown("---")
        st.markdown("##### 📋 Resumen en Pantalla")
        
        df_obj_pantalla = df_obj_res.copy()
        df_obj_pantalla["total_fmt"] = df_obj_pantalla["total"].map(lambda x: f"${x:,.2f}")
        df_obj_pantalla["porcentaje_fmt"] = df_obj_pantalla["porcentaje"].map(lambda x: f"{x:.2f}%")

        st.dataframe(
            df_obj_pantalla[["objeto_gasto", "total_fmt", "porcentaje_fmt"]].rename(
                columns={
                    "objeto_gasto": "OBJETO DEL GASTO",
                    "total_fmt": "TOTAL PRESUPUESTADO ($)",
                    "porcentaje_fmt": "% DEL TOTAL"
                }
            ),
            use_container_width=True,
            hide_index=True
        )

        # -------------------------------------------------------------
        # REPORTES IMPRESO / PDF (A4 PORTRAIT)
        # -------------------------------------------------------------
        rows_obj_html = ""
        for _, r in df_obj_res.iterrows():
            rows_obj_html += f"""
            <tr>
                <td style="text-align: left; padding-left: 10px;">{r['objeto_gasto']}</td>
                <td style="text-align: right;">${r['total']:,.2f}</td>
                <td style="text-align: center;">{r['porcentaje']:.2f}%</td>
            </tr>
            """

        html_obj_oficial = f"""
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                @page {{ size: A4 portrait; margin: 12mm; }}
                body {{ font-family: Arial, sans-serif; color: #000; margin: 0 auto; width: 100%; max-width: 900px; }}
                .m-box {{ border: 1px solid #000; padding: 10px; margin-bottom: 20px; background-color: #fff; }}
                .t-hdr {{ width: 100%; border-collapse: collapse; }}
                .t-hdr td {{ padding: 4px; vertical-align: middle; border: none; }}
                .b-tot {{ border: 1px solid #000; background-color: #f5f5f5; text-align: center; }}
                .tabla-datos {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 11px; margin-bottom: 25px; }}
                .tabla-datos th {{ border-bottom: 2px solid #000; padding: 6px 4px; text-align: center; font-weight: bold; background-color: #f2f2f2; }}
                .tabla-datos td {{ border-bottom: 1px solid #e0e0e0; padding: 6px 4px; vertical-align: middle; }}
                .firmas-container {{ margin-top: 50px; width: 100%; page-break-inside: avoid; }}
                .firma-box {{ width: 30%; float: left; text-align: center; border-top: 1px solid #000; padding-top: 5px; margin: 0 1.5%; font-size: 11px; font-weight: bold; }}
                .resumen-final {{ border: 2px solid #000; padding: 12px; margin-top: 20px; background-color: #fafafa; text-align: center; font-size: 13px; page-break-inside: avoid; }}
            </style>
        </head>
        <body onload="window.print();">
            <div class="m-box">
                <table class="t-hdr">
                    <tr>
                        <td style="width: 25%; text-align: left; font-size: 10px;"><b>Municipalidad de Sunchales</b><br><span style="font-size: 8px; color: #555;">Presupuesto Oficial 2027</span></td>
                        <td style="width: 50%; text-align: center;"><b>CONSOLIDADO POR OBJETO DEL GASTO</b><br><small>-2027-</small></td>
                        <td style="width: 25%;" class="b-tot"><small>Total Presupuesto</small><br><b>${tot_general_obj:,.2f}</b></td>
                    </tr>
                </table>
            </div>

            <table class="tabla-datos">
                <thead>
                    <tr>
                        <th style="text-align: left; padding-left: 10px;">OBJETO DEL GASTO</th>
                        <th style="text-align: right;">PRESUPUESTO ($)</th>
                        <th style="text-align: center;">% DEL TOTAL</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_obj_html}
                </tbody>
            </table>

            <div class="resumen-final">
                <b>TOTAL GENERAL DEL PRESUPUESTO MUNICIPAL:</b> ${tot_general_obj:,.2f}
            </div>

            <div class="firmas-container">
                <div class="firma-box">Responsable Presupuesto</div>
                <div class="firma-box">Contaduría General</div>
                <div class="firma-box">Intendente / Secretario</div>
            </div>
        </body>
        </html>
        """

        st.markdown("---")
        st.download_button(
            label="🖨️ GENERAR Y DESCARGAR REPORTE POR OBJETO (PDF / FIRMAS)",
            data=html_obj_oficial,
            file_name="Reporte_Totales_Por_Objeto_Gasto_2027.html",
            mime="text/html",
            use_container_width=True,
            type="primary"
        )


# =====================================================================
# SECCIÓN 15: MATRIZ SUBSECRETARÍA VS OBJETOS DE GASTO (NUEVA)
# =====================================================================
elif opcion_menu == "📊 MATRIZ SUBSECRETARÍA VS OBJETOS":
    st.subheader("📊 Matriz Cruzada: Subsecretarías vs Objetos del Gasto")

    if df_egr_completo.empty:
        st.info("💡 No hay registros contables cargados para generar la matriz cruzada.")
    else:
        st.caption("Cuadro comparativo donde la **Columna 1 es la Subsecretaría** y las columnas continuas representan cada **Objeto del Gasto**.")

        # Generar Pivot Table
        matriz_pivot = pd.pivot_table(
            df_egr_completo,
            values="total",
            index="subsecretaria",
            columns="objeto_gasto",
            aggfunc="sum",
            fill_value=0.0
        )

        # Calcular Total por fila (Subsecretaría)
        matriz_pivot["TOTAL GENERAL"] = matriz_pivot.sum(axis=1)

        st.markdown("##### 📋 Matriz Cruzada en Pantalla ($)")
        st.dataframe(matriz_pivot.style.format("${:,.2f}"), use_container_width=True)

        # -------------------------------------------------------------
        # GENERACIÓN DEL DOCUMENTO HORIZONTAL (A4 LANDSCAPE)
        # -------------------------------------------------------------
        cols_objetos = [c for c in matriz_pivot.columns if c != "TOTAL GENERAL"]
        tot_general_matriz = matriz_pivot["TOTAL GENERAL"].sum()

        # Encabezados de la tabla HTML
        th_cols_html = "".join([f'<th style="text-align: right; font-size: 9px;">{col}</th>' for col in cols_objetos])
        
        # Filas de datos HTML
        rows_matriz_html = ""
        for sub_nom, r in matriz_pivot.iterrows():
            tds_objetos = "".join([f'<td style="text-align: right;">${r[col]:,.2f}</td>' for col in cols_objetos])
            rows_matriz_html += f"""
            <tr>
                <td style="text-align: left; font-weight: bold; padding-left: 5px;">{sub_nom}</td>
                {tds_objetos}
                <td style="text-align: right; font-weight: bold; background-color: #f5f5f5;">${r['TOTAL GENERAL']:,.2f}</td>
            </tr>
            """

        # Fila final de Totales por columna
        tds_totales_cols = "".join([f'<td style="text-align: right; font-weight: bold;">${matriz_pivot[col].sum():,.2f}</td>' for col in cols_objetos])
        row_totales_final = f"""
        <tr style="background-color: #e6e6e6; border-top: 2px solid #000;">
            <td style="text-align: left; font-weight: bold; padding-left: 5px;">TOTAL GENERAL</td>
            {tds_totales_cols}
            <td style="text-align: right; font-weight: bold;">${tot_general_matriz:,.2f}</td>
        </tr>
        """

        html_matriz_oficial = f"""
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                @page {{ size: A4 landscape; margin: 10mm; }}
                body {{ font-family: Arial, sans-serif; color: #000; margin: 0 auto; width: 100%; max-width: 1100px; }}
                .m-box {{ border: 1px solid #000; padding: 8px; margin-bottom: 12px; background-color: #fff; }}
                .t-hdr {{ width: 100%; border-collapse: collapse; }}
                .t-hdr td {{ padding: 3px; vertical-align: middle; border: none; }}
                .b-tot {{ border: 1px solid #000; background-color: #f5f5f5; text-align: center; }}
                .tabla-datos {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 10px; margin-bottom: 20px; }}
                .tabla-datos th {{ border-bottom: 2px solid #000; padding: 5px 3px; font-weight: bold; background-color: #f2f2f2; }}
                .tabla-datos td {{ border-bottom: 1px solid #e0e0e0; padding: 5px 3px; vertical-align: middle; }}
                .firmas-container {{ margin-top: 40px; width: 100%; page-break-inside: avoid; }}
                .firma-box {{ width: 30%; float: left; text-align: center; border-top: 1px solid #000; padding-top: 5px; margin: 0 1.5%; font-size: 11px; font-weight: bold; }}
            </style>
        </head>
        <body onload="window.print();">
            <div class="m-box">
                <table class="t-hdr">
                    <tr>
                        <td style="width: 25%; text-align: left; font-size: 10px;"><b>Municipalidad de Sunchales</b><br><span style="font-size: 8px; color: #555;">Presupuesto Oficial 2027</span></td>
                        <td style="width: 50%; text-align: center;"><b>MATRIZ DE GASTOS POR SUBSECRETARÍA Y OBJETO</b><br><small>-2027-</small></td>
                        <td style="width: 25%;" class="b-tot"><small>Total Presupuesto</small><br><b>${tot_general_matriz:,.2f}</b></td>
                    </tr>
                </table>
            </div>

            <table class="tabla-datos">
                <thead>
                    <tr>
                        <th style="text-align: left; padding-left: 5px;">SUBSECRETARÍA</th>
                        {th_cols_html}
                        <th style="text-align: right; background-color: #e6e6e6;">TOTAL GENERAL</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_matriz_html}
                    {row_totales_final}
                </tbody>
            </table>

            <div class="firmas-container">
                <div class="firma-box">Responsable Presupuesto</div>
                <div class="firma-box">Contaduría General</div>
                <div class="firma-box">Intendente / Secretario</div>
            </div>
        </body>
        </html>
        """

        st.markdown("---")
        st.download_button(
            label="🖨️ GENERAR Y DESCARGAR MATRIZ HORIZONTAL (PDF / FIRMAS)",
            data=html_matriz_oficial,
            file_name="Matriz_Subsecretaria_vs_Objetos_2027.html",
            mime="text/html",
            use_container_width=True,
            type="primary"
        )
# =====================================================================
# SECCIÓN 16: PROYECCIÓN Y ESTRUCTURA TEMPORAL (TRIMESTRAL / SEMESTRAL)
# =====================================================================
elif opcion_menu == "📈 PROYECCIÓN Y ESTRUCTURA TEMPORAL":
    st.subheader("📈 Proyección y Programación de Ejecución Temporal")

    if df_egr_completo.empty:
        st.info("💡 No hay registros contables cargados.")
    else:
        st.caption("Estimación del flujo de fondos presupuestarios divididos por Trimestres (Q1 a Q4) o Semestres para la planificación financiera.")

        tot_anual = df_egr_completo["total"].sum()
        
        st.markdown("##### 🗓️ Distribución Trimestral Estimada")
        
        col_q1, col_q2, col_q3, col_q4 = st.columns(4)
        col_q1.metric("1° Trimestre (Q1 - 25%)", f"${(tot_anual * 0.25):,.2f}")
        col_q2.metric("2° Trimestre (Q2 - 25%)", f"${(tot_anual * 0.25):,.2f}")
        col_q3.metric("3° Trimestre (Q3 - 25%)", f"${(tot_anual * 0.25):,.2f}")
        col_q4.metric("4° Trimestre (Q4 - 25%)", f"${(tot_anual * 0.25):,.2f}")

        st.markdown("---")
        st.markdown("##### 🏛️ Programación de Caja por Secretaría (Estimación Trimestral)")
        
        df_sec_prog = df_egr_completo.groupby("secretaria")["total"].sum().reset_index()
        df_sec_prog["Q1 (25%)"] = df_sec_prog["total"] * 0.25
        df_sec_prog["Q2 (25%)"] = df_sec_prog["total"] * 0.25
        df_sec_prog["Q3 (25%)"] = df_sec_prog["total"] * 0.25
        df_sec_prog["Q4 (25%)"] = df_sec_prog["total"] * 0.25
        
        st.dataframe(
            df_sec_prog.style.format({
                "total": "${:,.2f}",
                "Q1 (25%)": "${:,.2f}",
                "Q2 (25%)": "${:,.2f}",
                "Q3 (25%)": "${:,.2f}",
                "Q4 (25%)": "${:,.2f}"
            }),
            use_container_width=True
        )


# =====================================================================
# SECCIÓN 17: CLASIFICACIÓN ECONÓMICA DEL GASTO
# =====================================================================
elif opcion_menu == "🏛️ CLASIFICACIÓN ECONÓMICA DEL GASTO":
    st.subheader("🏛️ Clasificación Económica: Gastos Corrientes vs Capital")

    if df_egr_completo.empty:
        st.info("💡 No hay registros contables cargados.")
    else:
        st.caption("Agrupación presupuestaria requerida por el Tribunal de Cuentas (Gastos Corrientes vs. Gastos de Capital e Inversión).")

        df_econ = df_egr_completo.groupby("clase")["total"].sum().reset_index()
        tot_general_econ = df_econ["total"].sum()
        df_econ["porcentaje"] = (df_econ["total"] / (tot_general_econ if tot_general_econ > 0 else 1)) * 100

        col_ec1, col_ec2 = st.columns(2)
        
        for idx, row in df_econ.iterrows():
            if "corriente" in str(row["clase"]).lower():
                col_ec1.metric(f"🔄 {row['clase']}", f"${row['total']:,.2f}", f"{row['porcentaje']:.2f}% del total")
            else:
                col_ec2.metric(f"🏗️ {row['clase']}", f"${row['total']:,.2f}", f"{row['porcentaje']:.2f}% del total")

        st.markdown("---")
        st.markdown("##### 📋 Detalle por Secretaría y Clasificación Económica")
        
        pivot_econ = pd.pivot_table(
            df_egr_completo,
            values="total",
            index="secretaria",
            columns="clase",
            aggfunc="sum",
            fill_value=0.0
        )
        pivot_econ["TOTAL"] = pivot_econ.sum(axis=1)
        
        st.dataframe(pivot_econ.style.format("${:,.2f}"), use_container_width=True)


# =====================================================================
# SECCIÓN 18: CONTROL DE TECHOS PRESUPUESTARIOS
# =====================================================================
elif opcion_menu == "🛡️ CONTROL DE TECHOS PRESUPUESTARIOS":
    st.subheader("🛡️ Panel de Control y Techos Presupuestarios por Secretaría")

    if df_egr_completo.empty:
        st.info("💡 No hay registros contables cargados.")
    else:
        st.caption("Define el límite o techo presupuestario asignado a cada Secretaría para controlar desvíos en tiempo real.")

        df_sec_techos = df_egr_completo.groupby("secretaria")["total"].sum().reset_index()

        # Inicializar techos en session_state si no existen
        if "techos_presupuesto" not in st.session_state:
            st.session_state.techos_presupuesto = {row["secretaria"]: float(row["total"] * 1.1) for _, row in df_sec_techos.iterrows()}

        st.markdown("##### ⚙️ Definir Techos Presupuestarios ($)")
        
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            sec_a_editar = st.selectbox("Seleccionar Secretaría:", df_sec_techos["secretaria"].unique())
        with col_t2:
            nuevo_techo = st.number_input(
                "Techo Límite ($):",
                value=float(st.session_state.techos_presupuesto.get(sec_a_editar, 0.0)),
                step=500000.0
            )
            if st.button("💾 Guardar Techo"):
                st.session_state.techos_presupuesto[sec_a_editar] = nuevo_techo
                st.success("Techo actualizado correctamente.")

        st.markdown("---")
        st.markdown("##### 📊 Estado de Cumplimiento por Secretaría")

        filas_techos = []
        for _, r in df_sec_techos.iterrows():
            sec_nom = r["secretaria"]
            cargado = r["total"]
            techo = st.session_state.techos_presupuesto.get(sec_nom, cargado)
            diferencia = techo - cargado
            estado = "✅ DENTRO DEL TECHO" if diferencia >= 0 else "🚨 EXCEDIDO"
            
            filas_techos.append({
                "SECRETARÍA": sec_nom,
                "PRESUPUESTO CARGADO ($)": f"${cargado:,.2f}",
                "TECHO PERMITIDO ($)": f"${techo:,.2f}",
                "DISPONIBLE / DESVÍO ($)": f"${diferencia:,.2f}",
                "ESTADO": estado
            })

        st.dataframe(pd.DataFrame(filas_techos), use_container_width=True, hide_index=True)


# =====================================================================
# SECCIÓN 19: FICHA TÉCNICA POR DESTINO (FICHA INDIVIDUAL)
# =====================================================================
elif opcion_menu == "📋 FICHA TÉCNICA POR DESTINO":
    st.subheader("📋 Ficha Técnica Ejecutiva por Destino")

    if df_egr_completo.empty:
        st.info("💡 No hay registros contables cargados.")
    else:
        st.caption("Generación de Ficha Ejecutiva resumida de una sola página por Destino, ideal para la firma del responsable del área.")

        destinos_lista = sorted([d for d in df_egr_completo["destino"].unique() if str(d).strip() != ""])
        destino_f_elegido = st.selectbox("Seleccionar Destino:", destinos_lista)

        df_f_destino = df_egr_completo[df_egr_completo["destino"] == destino_f_elegido]
        tot_f_destino = df_f_destino["total"].sum()

        st.markdown("---")
        st.markdown(f"### 📌 Destino: **{str(destino_f_elegido).upper()}**")
        st.metric("💰 Presupuesto Asignado", f"${tot_f_destino:,.2f}")

        # HTML Individual A4
        rows_f_html = ""
        for _, r in df_f_destino.iterrows():
            rows_f_html += f"""
            <tr>
                <td style="text-align: left;">{r['objeto_gasto']}</td>
                <td style="text-align: left;">{r['cuenta_presupuestaria']}</td>
                <td style="text-align: right;">${r['total']:,.2f}</td>
                <td style="text-align: center;">{r['fuente_fin']}</td>
            </tr>
            """

        html_ficha_oficial = f"""
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                @page {{ size: A4 portrait; margin: 15mm; }}
                body {{ font-family: Arial, sans-serif; color: #000; margin: 0 auto; width: 100%; max-width: 800px; }}
                .box-hdr {{ border: 2px solid #000; padding: 12px; text-align: center; margin-bottom: 20px; }}
                .tabla-datos {{ width: 100%; border-collapse: collapse; font-size: 11px; margin-top: 15px; }}
                .tabla-datos th {{ border-bottom: 2px solid #000; padding: 6px; text-align: left; background-color: #f2f2f2; }}
                .tabla-datos td {{ border-bottom: 1px solid #ddd; padding: 6px; }}
                .tot-box {{ border: 1px solid #000; padding: 10px; margin-top: 20px; text-align: right; font-size: 14px; background-color: #fafafa; }}
                .firmas {{ margin-top: 60px; width: 100%; }}
                .firma {{ width: 45%; float: left; text-align: center; border-top: 1px solid #000; padding-top: 5px; font-weight: bold; font-size: 11px; margin: 0 2.5%; }}
            </style>
        </head>
        <body onload="window.print();">
            <div class="box-hdr">
                <h3 style="margin:0;">MUNICIPALIDAD DE SUNCHALES</h3>
                <h4 style="margin:5px 0;">FICHA TÉCNICA PRESUPUESTARIA 2027</h4>
                <p style="margin:0; font-size:12px;"><b>DESTINO:</b> {str(destino_f_elegido).upper()}</p>
            </div>

            <table class="tabla-datos">
                <thead>
                    <tr>
                        <th>OBJETO DEL GASTO</th>
                        <th>PARTIDA PRESUPUESTARIA</th>
                        <th style="text-align: right;">MONTO ($)</th>
                        <th style="text-align: center;">FUENTE</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_f_html}
                </tbody>
            </table>

            <div class="tot-box">
                <b>TOTAL ASIGNADO AL DESTINO: ${tot_f_destino:,.2f}</b>
            </div>

            <div class="firmas">
                <div class="firma">Responsable del Area ({destino_f_elegido})</div>
                <div class="firma">Secretaría de Hacienda</div>
            </div>
        </body>
        </html>
        """

        st.download_button(
            label="🖨️ IMPRIMIR FICHA TÉCNICA DEL DESTINO (PDF A4)",
            data=html_ficha_oficial,
            file_name=f"Ficha_{destino_f_elegido.replace(' ', '_')}_2027.html",
            mime="text/html",
            use_container_width=True,
            type="primary"
        )

# =====================================================================
# SECCIÓN 20: COMPARATIVO E HISTÓRICO DE MODIFICACIONES (FILTRO RECURSOS)
# =====================================================================
elif opcion_menu == "🔄 COMPARATIVO E HISTÓRICO":
    st.subheader("🔄 Comparativo e Histórico Presupuestario (2026 vs 2027)")

    if df_egr_completo.empty:
        st.info("💡 No hay registros contables cargados para el proyecto 2027.")
    else:
        st.caption("Cruce en tiempo real sumando únicamente las **cuentas de imputación de gastos** (filtrando recursos y subtotales).")

        CSV_URL_SALDOS = "https://docs.google.com/spreadsheets/d/1JLCDkHYiSFV_cCOjVigcIXLkpD61pHpoxOmJ1CvK2m4/export?format=csv&gid=2027704109"

        c_mod1, c_mod2 = st.columns(2)
        with c_mod1:
            modo_comparacion = st.selectbox(
                "📌 Seleccionar Base de Comparación para 2026:",
                ["Presupuesto Aprobado / Inicial (Columna Presupuestado)", "Gasto Real Efectivo (Columna EJECUTADO)", "Gasto Devengado (Columna Devengado)"]
            )

        try:
            # 1. Detectar cabecera real
            df_raw_no_header = pd.read_csv(CSV_URL_SALDOS, header=None)
            
            header_row_idx = 0
            for idx, row in df_raw_no_header.iterrows():
                row_str = " ".join([str(val).upper() for val in row.values])
                if "PRESUPUESTADO" in row_str and "DEVENGADO" in row_str:
                    header_row_idx = idx
                    break

            # 2. Cargar datos salteando membrete
            df_2026 = pd.read_csv(CSV_URL_SALDOS, skiprows=header_row_idx)
            df_2026.columns = [str(c).strip().upper() for c in df_2026.columns]

            # ---------------------------------------------------------
            # FILTRADO 1: QUITAR RECURSOS
            # ---------------------------------------------------------
            # Crear una representación en texto de toda la fila para detectar si es un recurso
            fila_texto = df_2026.astype(str).apply(lambda row: " ".join(row).upper(), axis=1)
            
            # Excluir filas que contengan "RECURSO", "RECURSOS", "INGRESOS", etc.
            filtro_recursos = ~fila_texto.str.contains(
                r"\bRECURSO\b|\bRECURSOS\b|\bINGRESOS TRIBUTARIOS\b|\bINGRESOS NO TRIBUTARIOS\b|\bRECURSOS PROPIOS\b", 
                regex=True
            )
            df_2026 = df_2026[filtro_recursos]

            # ---------------------------------------------------------
            # FILTRADO 2: CONSERVAR SOLO CUENTAS DE IMPUTACIÓN (DESCARTAR SUBTOTALES)
            # ---------------------------------------------------------
            if "CUENTA DE GASTO" in df_2026.columns:
                df_2026 = df_2026[
                    df_2026["CUENTA DE GASTO"].notna() & 
                    (df_2026["CUENTA DE GASTO"].astype(str).str.strip() != "") &
                    (df_2026["CUENTA DE GASTO"].astype(str).str.strip() != "0")
                ]
            elif "OBJETO DE GASTO" in df_2026.columns:
                df_2026 = df_2026[df_2026["OBJETO DE GASTO"].astype(str).str.contains(r"\d", regex=True, na=False)]

            # 3. Mapear columna seleccionada
            if "Inicial" in modo_comparacion:
                col_monto_target = "PRESUPUESTADO"
            elif "Efectivo" in modo_comparacion:
                col_monto_target = "EJECUTADO"
            else:
                col_monto_target = "DEVENGADO"

            col_encontrada = None
            for c in df_2026.columns:
                if col_monto_target in c:
                    col_encontrada = c
                    break

            # 4. Función de conversión numérica para formato argentino
            def parse_num_arg(val):
                if pd.isna(val):
                    return 0.0
                s = str(val).strip().replace("$", "").replace(" ", "")
                if "," in s:
                    s = s.replace(".", "").replace(",", ".")
                return pd.to_numeric(s, errors="coerce")

            if col_encontrada:
                df_2026["TOTAL_2026_CLEAN"] = df_2026[col_encontrada].apply(parse_num_arg).fillna(0.0)
            else:
                df_2026["TOTAL_2026_CLEAN"] = 0.0

            hay_datos_2026 = True
        except Exception as e:
            hay_datos_2026 = False
            st.error(f"⚠️ No se pudo procesar la planilla: {e}")

        # -------------------------------------------------------------
        # PROCESAR Y DESPLEGAR COMPARATIVA
        # -------------------------------------------------------------
        if hay_datos_2026 and not df_2026.empty:
            tot_2026 = df_2026["TOTAL_2026_CLEAN"].sum()
            tot_2027 = df_egr_completo["total"].sum()

            incremento = tot_2027 - tot_2026
            porc_incremento = (incremento / tot_2026) * 100 if tot_2026 > 0 else 0.0

            st.markdown("---")
            st.markdown("##### 📊 Variación Interanual Global (Solo Gastos de Imputación)")
            m_h1, m_h2, m_h3 = st.columns(3)
            m_h1.metric(f"Base 2026 ({col_monto_target})", f"${tot_2026:,.2f}")
            m_h2.metric("Proyecto 2027", f"${tot_2027:,.2f}")
            m_h3.metric("Variación Interanual", f"${incremento:,.2f}", f"{porc_incremento:+.2f}%")

            st.markdown("---")
            st.markdown("##### 🏛️ Comparativo por Secretaría (2026 vs 2027)")

            # Agrupamiento 2027
            sec_2027 = df_egr_completo.groupby("secretaria")["total"].sum().reset_index()
            sec_2027.columns = ["SECRETARÍA", "PROYECTO 2027 ($)"]
            sec_2027["SECRETARÍA"] = sec_2027["SECRETARÍA"].astype(str).str.strip().str.upper()

            # Agrupamiento 2026
            col_sec_2026 = "SECRETARÍA" if "SECRETARÍA" in df_2026.columns else ("SECRETARIA" if "SECRETARIA" in df_2026.columns else None)

            if col_sec_2026:
                df_2026[col_sec_2026] = df_2026[col_sec_2026].astype(str).str.strip().str.upper()
                sec_2026 = df_2026.groupby(col_sec_2026)["TOTAL_2026_CLEAN"].sum().reset_index()
                sec_2026.columns = ["SECRETARÍA", f"BASE 2026 ({col_monto_target}) ($)"]
            else:
                sec_2026 = pd.DataFrame(columns=["SECRETARÍA", f"BASE 2026 ({col_monto_target}) ($)"])

            # Merge / Cruzamiento por Secretaría
            df_comp_sec = pd.merge(sec_2027, sec_2026, on="SECRETARÍA", how="outer").fillna(0.0)
            col_base_nom = f"BASE 2026 ({col_monto_target}) ($)"

            # Descartar nulos
            df_comp_sec = df_comp_sec[~df_comp_sec["SECRETARÍA"].isin(["NAN", "NONE", "", "0.0", "UNNAMED: 0"])]

            df_comp_sec["VARIACIÓN ($)"] = df_comp_sec["PROYECTO 2027 ($)"] - df_comp_sec[col_base_nom]
            df_comp_sec["% VARIACIÓN"] = df_comp_sec.apply(
                lambda r: ((r["VARIACIÓN ($)"] / r[col_base_nom]) * 100) if r[col_base_nom] > 0 else 0.0, 
                axis=1
            )

            st.dataframe(
                df_comp_sec.style.format({
                    "PROYECTO 2027 ($)": "${:,.2f}",
                    col_base_nom: "${:,.2f}",
                    "VARIACIÓN ($)": "${:,.2f}",
                    "% VARIACIÓN": "{:+.2f}%"
                }),
                use_container_width=True,
                hide_index=True
            )
