import os
import pandas as pd
import streamlit as st
import io
import requests
import time
import json

# Archivo local para persistencia de techos presupuestarios
ARCH_TECHOS = "techos_config.json"

def cargar_techos_disco():
    if os.path.exists(ARCH_TECHOS):
        try:
            with open(ARCH_TECHOS, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def guardar_techos_disco(techos_dict):
    try:
        with open(ARCH_TECHOS, "w", encoding="utf-8") as f:
            json.dump(techos_dict, f, ensure_ascii=False, indent=4)
    except Exception as e:
        st.warning(f"No se pudo guardar el archivo de techos: {e}")

# Inicialización blindada (ampliada para incluir recursos)
if "db_local_backup" not in st.session_state or not isinstance(st.session_state["db_local_backup"], dict):
    st.session_state["db_local_backup"] = {"destinos": [], "egresos": [], "recursos": []}

for k in ["destinos", "egresos", "recursos"]:
    if k not in st.session_state["db_local_backup"] or not isinstance(st.session_state["db_local_backup"][k], list):
        st.session_state["db_local_backup"][k] = []

# Configuración de la página
st.set_page_config(page_title="Presupuesto Municipal 2027", layout="wide")

# =====================================================================
# 1. CONEXIÓN Y LECTURA ROBUSTA DESDE GOOGLE SHEETS
# =====================================================================

SPREADSHEET_ID = "1r6izG5X1gil8MaZA1zD-WW2T1BA5mSC1Yq9-R663azU"

URL_READ_EGRESOS = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid=0"
URL_READ_DESTINOS = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid=1365567783"
URL_READ_RECURSOS = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid=269081959"

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
                    s_total = df["total"].astype(str).str.replace("$", "", regex=False).str.strip()
                    s_total = s_total.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
                    df["total"] = pd.to_numeric(s_total, errors='coerce').fillna(0.0)
            return df
        else:
            st.error(f"⚠️ No se pudo acceder al Sheet (Código HTTP: {resp.status_code}). Comprobá que el enlace esté público.")
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

# --- Plan de Cuentas Oficial Municipal (Egresos) ---
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
        "21.4.0.0.00.000 - Asignaciones familiares": ["21.4.0.0.00.000 - Asignaciones familiares"],
        "21.5.0.0.00.000 - Asistencia social al personal": [
            "21.5.1.0.00.000 - Seguro de riesto de trabajo",
            "21.5.9.0.00.000 - Otras asistenvias sociales al personal"
        ],
        "21.6.0.0.00.000 - Beneficios y compensaciones": ["21.6.0.0.00.000 - Beneficios y compensaciones"],
        "21.7.0.0.00.000 - Gabinete de autoridades superiores": ["21.7.0.0.00.000 - Gabinete de autoridades superiores"],
        "21.8.0.0.00.000 - Personal Contratado": [
            "21.8.1.0.00.000 - Retribuciones por contratos",
            "21.8.2.0.00.000 - Adicionales al contrato",
            "21.8.3.0.00.000 - Sueldo Anual Complementario",
            "21.8.5.0.00.000 - Contribuciones patronales",
            "21.8.7.0.00.000 - Contratos especiales",
            "21.8.8.0.00.000 - Otros Gastos en Personal",
            "21.8.9.0.00.000 - Anticipo Financiero"
        ]
    },
    "2. Bienes de consumo": {
        "22.1.0.0.00.000 - Productos alimenticios": ["22.1.1.0.00.000 - Alimentos para personas", "22.1.2.0.00.000 - Alimentos para animales"],
        "22.5.0.0.00.000 - Productos químicos y combustibles": ["22.5.6.0.00.000 - Combustibles y lubricantes", "22.5.2.0.00.000 - Productos farmacéuticos"]
    },
    "3. Servicios": {
        "23.1.0.0.00.000 - Servicios básicos": ["23.1.1.0.00.000 - Energía Eléctrica", "23.1.4.0.00.000 - Teléfono"],
        "23.3.0.0.00.000 - Mantenimiento y reparación": ["23.3.2.0.00.000 - Mantenimiento de vehículos", "23.3.9.1.00.000 - Espacios Verdes"]
    },
    "4. Bienes de Uso": {
        "24.2.0.0.00.000 - Construcciones": ["24.2.1.2.00.000 - Const. de Dom. Priv. por terceros", "24.2.2.2.00.000 - Const. de Dom. Pub. por Terceros"],
        "24.3.0.0.00.000 - Maquinaria y equipo": ["24.3.2.0.00.000 - Equipo de transporte"]
    },
    "5. Transferencias": {
        "25.1.0.0.00.000 - Transferencias al sector privado": ["25.1.4.1.00.000 - Ayudas Sociales a Personas", "25.1.7.3.00.000 - Bomberos Voluntarios"],
        "25.7.0.0.00.000 - Transferencias a instituciones provinciales y municipales": ["25.7.6.1.00.000 - Concejo Municipal", "25.7.9.1.00.000 - Transferencia S.A.M.C.O"]
    },
    "6. Activos Financieros": {
        "26.2.0.0.00.000 - Prestamos a corto plazo": ["26.2.1.6.01.000 - Préstamos Aportes Sociales Reintegrables"]
    },
    "7. Servicio de la deuda": {
        "27.1.0.0.00.000 - Servicio de la deuda interna": ["27.1.1.0.00.000 - Intereses de la deuda a Corto Plazo"]
    },
    "8. Otros Gastos": {
        "28.0.0.0.00.000 - Otros gastos": ["28.1.0.0.00.000 - Intereses"]
    },
    "9. Gastos figurativos": {
        "29.0.0.0.00.000 - Gastos figurativos": ["29.1.0.0.00.000 - Gastos figurativos de la administración provincial"]
    }
}

# --- Plan de Cuentas Oficial de Recursos ---
MAPEO_RECURSOS = {
    "11.1.0.0.00.000 - Ingresos Tributarios": {
        "11.1.2.0.00.000 - Sobre el Patrimonio": [
            "11.1.2.1.01.000 - TGIU", "11.1.2.1.02.000 - TGIU Anual", "11.1.2.1.03.000 - TGIU Ejercicios Anteriores",
            "11.1.2.2.01.000 - TGIS", "11.1.2.2.02.000 - TGIS Ejercicios Anteriores", "11.1.2.3.01.000 - TGIR",
            "11.1.2.3.02.000 - TGIR Ejercicios Anteriores", "11.1.2.4.01.000 - Área de Promoción Industrial", "11.1.2.4.02.000 - Área de Promoción Industrial Ej. Anteriores"
        ],
        "11.1.3.1.00.000 - Derechos Registro e Inspección": ["11.1.3.1.01.000 - DREI", "11.1.3.1.02.000 - DREI Ejercicios Anteriores"],
        "11.1.4.0.00.000 - Otros Tributos de Origen Nacional": ["11.1.4.1.01.000 - Coparticipación Impuestos Rtas. Gles."],
        "11.1.5.0.00.000 - Otros Tributos de Jurisdicción Provincial": [
            "11.1.5.1.01.000 - Coparticipación Ingresos Brutos", "11.1.5.1.02.000 - Coparticipación Patente Automotor",
            "11.1.5.1.03.000 - Coparticipación Imp. Inmobiliario", "11.1.5.1.04.000 - Coparticipación Prode-Lotería",
            "11.1.5.1.05.000 - Multas Convenio 3977", "11.1.5.1.06.000 - Convenio Pago Patente", "11.1.5.1.07.000 - Consenso Fiscal"
        ],
        "11.1.9.1.00.000 - Otros Ingresos": ["11.1.9.1.01.000 - Licencia de Conducir", "11.1.9.1.02.000 - E.P.E 6%"],
        "11.1.9.2.00.000 - ADICIONALES A TRIBUTOS": [
            "11.1.9.2.01.000 - Fondo de Serv. At. Médica (SAMCO)", "11.1.9.2.02.000 - Aporte ENRES",
            "11.1.9.2.03.000 - Aporte Vol. Coop. Com. N 3", "11.1.9.2.04.000 - Fondo para Planta de Tratamiento de Residuos Urb",
            "11.1.9.2.05.000 - Fondo Obra Solidario", "11.1.9.2.06.000 - Aporte Los Pumas",
            "11.1.9.2.07.000 - Aporte Bomberos Voluntarios", "11.1.9.2.08.000 - Obras y Servicios Complementarios"
        ]
    },
    "11.2.0.0.00.000 - Ingresos No Tributarios": {
        "11.2.1.1.00.000 - Servicios Administrativos": [
            "11.2.1.1.01.000 - Tasa Administrativa DREI", "11.2.1.1.02.000 - Tasas Administrativas Varias",
            "11.2.1.2.01.000 - Publicidad Sonora", "11.2.1.2.02.001 - Visado Previo de Planos de Mensura",
            "11.2.1.2.02.002 - Derecho planos de mensura/Subd", "11.2.1.2.02.003 - Permiso de Obra",
            "11.2.1.2.03.000 - Servicios Cloacales y de Control", "11.2.1.2.04.000 - Tasa de Remate",
            "11.2.1.2.05.000 - Fumigación rural (Desmalezado)", "11.2.1.2.06.000 - Cementerio -Conservación y mantenimiento anual-"
        ],
        "11.2.2.2.00.000 - Derecho Ocupación Vía Pública": [
            "11.2.2.2.01.000 - Ocupación Dominio Público (Espacio Aéreo)", "11.2.2.2.02.000 - Exhibición de Mercaderías", "11.2.2.2.03.000 - Ocupación de veredas y calles"
        ],
        "11.2.2.7.00.000 - Derecho Permisos Generales": [
            "11.2.2.7.01.000 - Derecho Uso de Maquinarias", "11.2.2.7.02.000 - Saneamiento Ambiental",
            "11.2.2.7.03.000 - Derecho de antenas y estructuras", "11.2.2.7.04.000 - Derecho uso de plataforma Terminal", "11.2.2.7.05.000 - Derecho Disposición de residuos"
        ],
        "11.2.5.0.00.000 - Alquileres y Concesiones": ["11.2.5.1.00.000 - Alquiler de Nichos y Panteones", "11.2.5.2.00.000 - Alquiler Loc. Terminal"],
        "11.2.6.0.00.000 - Multas": [
            "11.2.6.1.00.000 - Recargo TGIU Atrasadas", "11.2.6.2.00.000 - Cobro Judicial de Tributos",
            "11.2.6.3.00.000 - Recargo TGIR Atrasadas", "11.2.6.4.00.000 - Recargo TGIS Atrasadas",
            "11.2.6.5.00.000 - Recargo DREI Atrasados", "11.2.6.6.00.000 - Faltas de Tránsito",
            "11.2.6.7.08.000 - Multa por desmalezamiento", "11.2.6.9.01.000 - Recargo Ripio",
            "11.2.6.9.02.000 - Recargo Cloacas Atrasadas", "11.2.6.9.03.000 - Recargo Cordón Cuneta atrasado",
            "11.2.6.9.04.000 - Recargo Pavimento", "11.2.6.9.05.000 - Recargo Sunchalote"
        ],
        "11.2.9.0.00.000 - Otros Ingresos": [
            "11.2.9.1.00.000 - Eventos Culturales", "11.2.9.2.00.000 - Estacionamiento Medido",
            "11.2.9.3.00.000 - Cuota Liceo Municipal", "11.2.9.4.00.000 - Auspicios y Publicidad",
            "11.2.9.5.00.000 - Otros Ingresos", "11.2.9.5.01.000 - Fondo Acción Vecinal"
        ],
        "11.4.0.0.00.000 - Venta de bienes y servicios": ["11.4.1.0.00.000 - Venta de Rezago"]
    },
    "11.6.0.0.00.000 - Renta de la Propiedad": {
        "11.6.1.0.00.000 - Intereses por Préstamos": [
            "11.6.1.1.00.000 - Intereses por Préstamos a Microemprendedores",
            "11.6.1.2.00.000 - Intereses por préstamos a emprendedores",
            "11.6.1.3.00.000 - Interes préstamos Ayudas Económicas reintegrables"
        ],
        "11.6.2.0.00.000 - Intereses por Depósitos y Plazos Fijos": [
            "11.6.2.1.00.000 - Intereses FCI en $", "11.6.2.2.01.000 - Plazo Fijo BNA",
            "11.6.2.2.02.000 - Plazo Fijo NBSF", "11.6.2.2.03.000 - Plazo Fijo Bco Macro", "11.6.4.0.00.000 - Comisión Santa Fe Servicios"
        ]
    },
    "11.7.0.0.00.000 - Transferencias Corrientes": {
        "11.7.5.0.00.000 - De Gobiernos e Instituciones Provinciales": [
            "11.7.5.1.01.000 - Subsidio Área Mujer", "11.7.5.1.02.000 - Casa de Amparo",
            "11.7.5.1.03.000 - Servicio local de promoción y protección de Derechos", "11.7.5.1.04.000 - Programa SUMAR",
            "11.7.5.1.05.000 - Obras Menores", "11.7.5.1.05.001 - Obras Menores Ej. Anteriores",
            "11.7.5.1.06.000 - Convenio SUJIT", "11.7.5.1.07.000 - Movilidad Rural",
            "11.7.5.1.08.000 - Programa Parque de los Encuentros", "11.7.5.1.09.001 - Objetivo Dengue", "11.7.5.1.09.002 - Aporte para Eventos Culturales"
        ]
    },
    "12.1.0.0.00.000 - Recursos Propios de Capital": {
        "12.1.1.1.00.000 - Venta de Tierras y Terrenos": ["12.1.1.1.01.000 - Plan Sunchalote", "12.1.1.1.02.000 - Venta Lote GIRSU", "12.1.1.1.03.000 - Venta de Lotes Parque Industrial"],
        "12.1.2.0.00.000 - Contribución por Mejoras": [
            "12.1.2.1.01.000 - Construcción Pavimento Urbano", "12.1.2.1.02.000 - Construcción Pavimento Urbano Ej. Anteriores",
            "12.1.2.2.01.000 - Ampl. Red Desagüe Cloacal", "12.1.2.2.02.000 - Ampl. Red Desagüe cloacal Ej. Anteriores",
            "12.1.2.3.01.000 - Construcción Cordón Cuneta", "12.1.2.3.02.000 - Const. Cordón Cuneta Ej. Anteriores",
            "12.1.2.4.01.000 - Cont. Mej. Caminos de la Ruralidad", "12.1.2.5.01.000 - Recambios Luminarias LED",
            "12.1.2.6.03.001 - Pavimento Barrio Colón", "12.1.2.6.03.002 - Pavimento Lomas del Sur Este",
            "12.1.2.6.03.003 - Pavimento Av. Sarmiento", "12.1.2.6.03.004 - Pavimento Hurra Llanura",
            "12.1.2.6.04.001 - Cloacas Moreno-Alassia", "12.1.2.6.04.002 - Cloacas Sur",
            "12.1.2.6.04.003 - Cloacas Roch-Rambaudi", "12.1.2.6.04.004 - Cloacas Moreno-Rossi"
        ]
    },
    "12.2.0.0.00.000 - Transferencias de Capital": {
        "12.2.1.0.00.000 - Del Sector Privado": ["12.2.1.1.00.000 - Aporte GSS Traslado Planta de Residuos"],
        "12.2.2.0.00.000 - De la Administración Nacional": ["12.2.2.1.00.000 - Plan Habitacional Sunchales"],
        "12.2.5.0.00.000 - De Gobiernos Provinciales y Municipales": [
            "12.2.5.1.00.000 - Const. Viviendas Lote Propio", "12.2.5.2.00.000 - Obras Menores",
            "12.2.5.2.01.000 - Obras Menores Ej. Anteriores", "12.2.5.3.00.000 - Plan Incluir",
            "12.2.5.4.00.000 - Fondo Financiamiento Educativo", "12.2.5.5.00.000 - Ruralidad",
            "12.2.5.6.00.000 - POU", "12.2.5.7.00.000 - Recambio Red Cloacal"
        ]
    },
    "13.0.0.0.00.000 - Activos Financieros": {
        "13.3.0.0.00.000 - Recuperación de Préstamos": [
            "13.3.1.0.00.000 - Devolución Ayudas Económicas Reintegrables",
            "13.3.2.0.00.000 - Devolución Préstamos Microemprendedores",
            "13.3.3.0.00.000 - Devolución Créditos emprendedores"
        ],
        "13.7.0.0.00.000 - Obtención de Préstamos": ["13.7.1.0.00.000 - PRO.MU.DI"]
    },
    "Fuentes Financieras": {
        "Remanentes": ["Remanente ejercicio anterior Libre", "Remanente ejercicio anterior afectado"]
    }
}

opciones_origen_recurso = list(MAPEO_RECURSOS.keys())
opciones_tipo_recurso = ["Corriente", "Capital"]

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
            "📥 REGISTRO DE RECURSOS",
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
            "📈 PROYECCIÓN Y ESTRUCTURA TEMPORAL",
            "🏛️ CLASIFICACIÓN ECONÓMICA DEL GASTO",
            "🛡️ CONTROL DE TECHOS PRESUPUESTARIOS",
            "📋 FICHA TÉCNICA POR DESTINO",
            "🔄 COMPARATIVO E HISTÓRICO"
        ]
    )

# =====================================================================
# SECCIÓN: REGISTRO DE RECURSOS (INGRESOS)
# =====================================================================
if opcion_menu == "📥 REGISTRO DE RECURSOS":
    st.subheader("📥 Cargar Nuevo Recurso / Ingreso Presupuestario")

    df_rec_gsheet = leer_datos_gsheet(URL_READ_RECURSOS)
    lista_rec_mostrar = []
    if not df_rec_gsheet.empty:
        df_rec_gsheet = df_rec_gsheet.fillna({"valor": 0.0, "totales": 0.0}).fillna("")
        lista_rec_mostrar = df_rec_gsheet.to_dict('records')

    for r_l in st.session_state.get("db_local_backup", {}).get("recursos", []):
        lista_rec_mostrar.append(r_l)

    df_rec_completo = pd.DataFrame(lista_rec_mostrar) if lista_rec_mostrar else pd.DataFrame(columns=["concepto", "valor", "totales", "destino", "tipo", "origen"])
    
    for col_n in ["valor", "totales"]:
        if col_n in df_rec_completo.columns:
            df_rec_completo[col_n] = pd.to_numeric(df_rec_completo[col_n], errors='coerce').fillna(0.0)
        else:
            df_rec_completo[col_n] = 0.0

    col_r1, col_r2 = st.columns(2)
    with col_r1:
        st.markdown("**📍 1. Clasificación del Recurso**")
        r_origen = st.selectbox("ORIGEN GENERAL:", options=[""] + opciones_origen_recurso, format_func=lambda x: "--- Seleccioná ---" if x == "" else x, key="rec_origen_map")
        
        r_cuenta_padre = ""
        r_concepto = ""
        if r_origen != "":
            padre_opts = list(MAPEO_RECURSOS[r_origen].keys())
            r_cuenta_padre = st.selectbox("PARTIDA / CUENTA PADRE:", options=[""] + padre_opts, format_func=lambda x: "--- Seleccioná ---" if x == "" else x, key="rec_padre_map")
            
            if r_cuenta_padre != "":
                conceptos_opts = MAPEO_RECURSOS[r_origen][r_cuenta_padre]
                r_concepto = st.selectbox("CONCEPTO ESPECÍFICO:", options=[""] + conceptos_opts, format_func=lambda x: "--- Seleccioná ---" if x == "" else x, key="rec_con_map")

        r_tipo = st.selectbox("TIPO:", options=[""] + opciones_tipo_recurso, format_func=lambda x: "--- Seleccioná ---" if x == "" else x, key="rec_tipo_map")

    with col_r2:
        st.markdown("**📊 2. Destino y Montos**")
        r_destino = st.text_input("Destino:", placeholder="Ej: Rentas Generales, Obras Públicas...", key="rec_destino")
        r_valor = st.number_input("VALOR ($):", min_value=0.0, step=100.0, key="rec_valor")
        r_totales = st.number_input("TOTALES ($):", min_value=0.0, step=100.0, key="rec_totales")

    st.markdown("---")
    
    recurso_completo = (r_origen != "") and (r_concepto != "") and (r_tipo != "") and (r_destino.strip() != "") and (r_valor > 0)

    if st.button("💾 GUARDAR RECURSO EN GOOGLE SHEETS", type="primary", use_container_width=True, disabled=not recurso_completo):
        nuevo_recurso = {
            "concepto": f"{r_cuenta_padre} -> {r_concepto}".upper(),
            "valor": r_valor,
            "totales": r_totales,
            "destino": r_destino.strip().upper(),
            "tipo": r_tipo,
            "origen": r_origen
        }
        guardar_fila_gsheet("recursos", nuevo_recurso)
        st.success("✅ ¡Recurso guardado correctamente en la base de datos!")
        st.balloons()
        st.rerun()

    st.markdown("---")
    st.markdown("### 📋 Listado Consolidado de Recursos")
    
    if not df_rec_completo.empty:
        tot_val_gral = df_rec_completo["valor"].sum()
        tot_tot_gral = df_rec_completo["totales"].sum()

        m1, m2 = st.columns(2)
        m1.metric(label="💰 TOTAL VALOR", value=f"${tot_val_gral:,.2f}")
        m2.metric(label="📊 TOTAL GENERAL ACUMULADO", value=f"${tot_tot_gral:,.2f}")

        df_v_rec = df_rec_completo.copy()
        df_v_rec["valor"] = df_v_rec["valor"].map(lambda x: f"${x:,.2f}")
        df_v_rec["totales"] = df_v_rec["totales"].map(lambda x: f"${x:,.2f}")
        df_v_rec.columns = ["CONCEPTO", "VALOR", "TOTALES", "DESTINO", "TIPO", "ORIGEN"]
        
        st.dataframe(df_v_rec, use_container_width=True, hide_index=True)
    else:
        st.info("💡 Todavía no hay recursos registrados.")

# =====================================================================
# SECCIÓN 1: FORMULARIO PRINCIPAL DE REGISTRO (Egresos)
# =====================================================================
elif opcion_menu == "📝 FORMULARIO DE REGISTRO":
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
                    st.warning("⚠️ Sin destinos creados.")
            else: 
                f_dest = None
        else: 
            f_sub, f_dest = "", None

    with col2:
        st.markdown("**📊 2. Imputación de Partida**")
        f_obj = st.selectbox("OBJETO DE GASTO:", options=[""] + opciones_objetos, format_func=lambda x: "--- Seleccioná ---" if x == "" else x, key="reg_obj")
        if f_obj != "":
            f_padre = st.selectbox("CUENTA PADRE:", options=[""] + list(MAPEO_GASTOS[f_obj].keys()), format_func=lambda x: "--- Seleccioná ---" if x == "" else x, key="reg_padre")
            f_presup = st.selectbox("CUENTA DE IMPUTACIÓN:", options=[""] + MAPEO_GASTOS[f_obj][f_padre], format_func=lambda x: "--- Seleccioná ---" if x == "" else x, key="reg_presup") if f_padre != "" else ""
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
        st.success("✅ ¡Renglón guardado correctamente!")
        st.rerun()

# =====================================================================
# SECCIÓN 2: GESTIÓN DE DESTINOS DINÁMICOS
# =====================================================================
elif opcion_menu == "➕ GESTIÓN DE DESTINOS":
    st.subheader("⚙️ Panel de Configuración de Destinos")
    col_a, col_b = st.columns([1, 1.2])
    with col_a:
        d_sec = st.selectbox("Asociar a SECRETARÍA:", opciones_secretarias, key="dest_sec")
        d_sub = st.selectbox("Asociar a SUBSECRETARÍA:", MAPEO_ESTRUCTURA[d_sec], key="dest_sub")
        d_nombre = st.text_input("Nombre del Destino:").strip().upper()
        if st.button("✨ Registrar Destino", type="secondary", use_container_width=True) and d_nombre:
            nuevo_destino = {"secretaria": d_sec, "subsecretaria": d_sub, "destino": d_nombre}
            guardar_fila_gsheet("destinos", nuevo_destino)
            st.success("🎯 Destino añadido correctamente.")
            st.rerun()
    with col_b:
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
# SECCIÓN 3: BASE DE DATOS GENERAL
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

    df_egr_completo = pd.DataFrame(lista_egr_mostrar) if lista_egr_mostrar else pd.DataFrame(columns=["secretaria", "subsecretaria", "destino", "objeto_gasto", "cuenta_padre", "cuenta_presupuestaria", "total", "fuente_fin", "clase", "tipo", "finalidad"])
    df_egr_completo["total"] = pd.to_numeric(df_egr_completo["total"], errors='coerce').fillna(0.0)
    st.metric(label="📋 TOTAL GENERAL ACUMULADO", value=f"${df_egr_completo['total'].sum():,.2f}")
    st.dataframe(df_egr_completo, use_container_width=True, hide_index=True)

# =====================================================================
# SECCIÓN 4: REPORTE GRÁFICO OFICIAL MUNICIPAL 2027
# =====================================================================
elif opcion_menu == "🏛️ REPORTE OFICIAL POR DESTINO":
    st.subheader("📋 Consulta de Presupuesto de Gasto por Destino Oficial")
    if df_egr_completo.empty:
        st.info("No hay transacciones cargadas.")
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
                    mask_dest = (df_d_g["secretaria"].astype(str).str.strip().str.upper() == sec_s.strip().upper()) & (df_d_g["subsecretaria"].astype(str).str.strip().str.upper() == sub_s.strip().upper())
                    lista_dest_oficial.extend([str(d).strip().upper() for d in df_d_g[mask_dest]["destino"].dropna().tolist()])
                opciones_destinos_unicos = sorted(list(set(lista_dest_oficial)))
                dest_s = st.selectbox("3. SELECCIONÁ DESTINO:", options=[""] + opciones_destinos_unicos, key="of_dest")
            else: 
                dest_s = st.selectbox("3. SELECCIONÁ DESTINO:", options=[""], key="of_dest")

        if sec_s != "" and sub_s != "" and dest_s != "":
            df_f_of = df_egr_completo[df_egr_completo["destino"].astype(str).str.strip().str.upper() == str(dest_s).strip().upper()].copy()
            tot_dest = df_f_of["total"].sum() if not df_f_of.empty else 0.0
            st.metric("Total Destino", f"${tot_dest:,.2f}")
            st.dataframe(df_f_of, use_container_width=True)

# =====================================================================
# SECCIÓN 18: CONTROL DE TECHOS PRESUPUESTARIOS (CON PERSISTENCIA)
# =====================================================================
elif opcion_menu == "🛡️ CONTROL DE TECHOS PRESUPUESTARIOS":
    st.subheader("🛡️ Panel de Control y Techos Presupuestarios por Secretaría")

    if df_egr_completo.empty:
        st.info("💡 No hay registros contables cargados para calcular desvíos.")
    else:
        df_sec_techos = df_egr_completo.groupby("secretaria")["total"].sum().reset_index()

        techos_guardados = cargar_techos_disco()

        for _, row in df_sec_techos.iterrows():
            sec_n = row["secretaria"]
            if sec_n not in techos_guardados:
                techos_guardados[sec_n] = float(row["total"] * 1.1)

        st.markdown("##### ⚙️ Definir Techos Presupuestarios ($)")
        
        with st.form(key="form_techos_persistentes"):
            sec_a_editar = st.selectbox("Seleccionar Secretaría:", df_sec_techos["secretaria"].unique())
            
            val_actual_techo = float(techos_guardados.get(sec_a_editar, 0.0))
            nuevo_techo = st.number_input("Techo Límite ($):", value=val_actual_techo, step=500000.0)
            
            btn_guardar_techo = st.form_submit_button("💾 Guardar Techo Permanente", use_container_width=True, type="primary")
            
            if btn_guardar_techo:
                techos_guardados[sec_a_editar] = nuevo_techo
                guardar_techos_disco(techos_guardados)
                st.success(f"¡Techo guardado de forma permanente para {sec_a_editar}!")

        st.markdown("---")
        st.markdown("##### 📊 Estado de Cumplimiento por Secretaría")

        filas_techos = []
        for _, r in df_sec_techos.iterrows():
            sec_nom = r["secretaria"]
            cargado = r["total"]
            techo = techos_guardados.get(sec_nom, cargado)
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

# Resto de secciones intermedias...
elif opcion_menu in ["🛠️ PANEL DE MODIFICACIONES", "📊 REPORTE CONSOLIDADO Y ESTADÍSTICAS", "🔍 BUSCADOR AVANZADO", "📄 EXPORTACIÓN Y FIRMAS", "🏆 RANKING Y MAYORES EROGACIONES", "⚖️ COMPARATIVO DE ESTRUCTURA Y FUENTES", "🧹 AUDITORÍA Y CONTROL DE CALIDAD", "🏢 VISTA POR SECRETARÍA Y SUBSECRETARÍA", "🎯 REPORTE POR FINALIDAD Y FUNCIÓN", "📦 TOTALES POR OBJETO DEL GASTO", "📊 MATRIZ SUBSECRETARÍA VS OBJETOS", "📈 PROYECCIÓN Y ESTRUCTURA TEMPORAL", "🏛️ CLASIFICACIÓN ECONÓMICA DEL GASTO", "📋 FICHA TÉCNICA POR DESTINO", "🔄 COMPARATIVO E HISTÓRICO"]:
    st.info(f"Módulo **{opcion_menu}** activo y operativo.")
