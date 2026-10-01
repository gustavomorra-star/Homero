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

# ===================================================================== #
# SALUDO INICIAL DE BIENVENIDA (Sunchales - Presupuesto 2027)             #
# ===================================================================== #
if "saludo_inicial" not in st.session_state:
  st.session_state["saludo_inicial"] = True

if st.session_state["saludo_inicial"]:
  # Contenedor principal de bienvenida centrado
  _, col_centro, _ = st.columns([1, 2, 1])
  with col_centro:
    st.markdown(
        """
        <div style="background: linear-gradient(135deg, #003366 0%, #0056b3 100%); padding: 30px; border-radius: 12px; text-align: center; color: white; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 20px;">
            <h1 style="margin: 0; font-size: 2.2rem; color: #FFFFFF;">Municipalidad de Sunchales</h1>
            <h3 style="margin: 10px 0 0 0; font-weight: 300; font-size: 1.2rem; color: #E2E8F0;">Santa Fe — Sistema Homero (Presupuesto 2027)</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Bandera institucional
    st.image(
        "https://upload.wikimedia.org/wikipedia/commons/c/c5/Bandera_de_la_Ciudad_de_Sunchales.svg",
        use_container_width=True,
    )

    st.markdown(
        "<p style='text-align: center; font-size: 1.1rem; color: #4B5563;"
        " margin: 20px 0;'>Bienvenido al sistema oficial de gestión y"
        " planificación presupuestaria.</p>",
        unsafe_allow_html=True,
    )

    # Botón para entrar al sistema principal
    if st.button("🚀 Ingresar al Sistema", use_container_width=True):
      st.session_state["saludo_inicial"] = False
      st.rerun()

  # Detiene la ejecución solo durante la pantalla de bienvenida inicial
  st.stop()
# =====================================================================
# 1. CONEXIÓN Y LECTURA ROBUSTA DESDE GOOGLE SHEETS
# =====================================================================

SPREADSHEET_ID = "1r6izG5X1gil8MaZA1zD-WW2T1BA5mSC1Yq9-R663azU"

URL_READ_EGRESOS = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid=0"
URL_READ_DESTINOS = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid=1365567783"
URL_READ_RECURSOS = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid=269081959"
URL_READ_TECHOS = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid=671713267"
URL_READ_EJECUCION = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid=810226733"

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
        # Aumentamos el timeout a 30 segundos para evitar cortes con planillas grandes
        resp = requests.get(url, timeout=30)
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

# URL de tu Webhook de Google Apps Script para escritura real
URL_WEBHOOK_GSHEET = "https://script.google.com/macros/s/AKfycbwOfDQPZ2b62zMIESSkUcyvZIB2_JzpBD85ORXZXFx0pmccK5ChZcl8OKH4za6xTDkq/exec"

def guardar_fila_gsheet(pestana, nuevo_dict):
    # Respaldo local inmediato en sesión
    if pestana in st.session_state["db_local_backup"]:
        st.session_state["db_local_backup"][pestana].append(nuevo_dict)

    # Sincronización con Google Sheets
    try:
        payload = {"pestana": pestana, **nuevo_dict}
        # allow_redirects=True permite seguir la redirección estándar de Google Apps Script
        resp = requests.post(URL_WEBHOOK_GSHEET, json=payload, timeout=10, allow_redirects=True)

        # Google Apps Script suele retornar 200 u OK tras el ciclo de redirección
        if resp.status_code in [200, 302]:
            st.success("✅ ¡Guardado localmente y sincronizado en Google Sheets!")
        else:
            st.warning(f"⚠️ El servidor respondió con código: {resp.status_code}")
    except Exception as e:
        st.warning(f"⚠️ Guardado en la sesión. Error de conexión: {e}")

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
        "22.1.0.0.00.000 - Productos alimenticios, agropecuarios y forestales": ["22.1.1.0.00.000 - Alimentos para personas", "22.1.2.0.00.000 - Alimentos para animales","22.1.3.0.00.000 - Productos pecuarios","22.1.4.0.00.000 - Productos agroforestales","22.1.5.0.00.000 - Madera, corcho y sus manufacturas"],
	    "22.2.0.0.00.000 - Textiles y vestuarios": ["22.2.1.0.00.000 - Hilados y telas","22.2.2.0.00.000 - Prendas de vestir","22.2.3.0.00.000 - Confecciones textiles"],
	    "22.3.0.0.00.000 - Productos de papel, cartón e impresos": ["22.3.1.0.00.000 - Papel de Escritorio y cartón","22.3.2.0.00.000 - Papel de computación","22.3.3.0.00.000 - Productos de artes gráficas","22.3.4.0.00.000 - Productos de papel y cartón","22.3.5.0.00.000 - Libros, revistas y periódicos","22.3.6.0.00.000 - Textos de enseñanza","22.3.7.0.00.000 - Especias timbradas y valores"],
	    "22.4.0.0.00.000 - Productos de cuero y caucho": ["22.4.1.0.00.000 - Cueros y Pieles","22.4.2.0.00.000 - Artículos de Cuero","22.4.3.0.00.000 - Artículos de caucho","22.4.4.0.00.000 - Cubiertas y cámaras de aire"],
        "22.5.0.0.00.000 - Productos químicos, combustibles y lubricantes": ["22.5.1.0.00.000 - Compuestos químicos","22.5.2.0.00.000 - Productos farmacéuticos y medicinales","22.5.3.0.00.000 - Abonos y fertilizantes","22.5.4.0.00.000 - Insecticidad, fumigantes y otros","22.5.5.0.00.000 - Tintas, Pinturas y Colorantes","22.5.6.0.00.000 - Combustibles y lubricantes","22.5.7.0.00.000 - Específicos veterinarios","22.5.8.0.00.000 - Productos de material plático","22.5.9.1.00.000 - Productos de Brea y materiales asfálticos"],
	    "22.6.0.0.00.000 - Productos minerales no metálicos": ["22.6.1.0.00.000 - Productos de arcilla y de cerámica","22.6.2.0.00.000 - Productos de Vidrio","22.6.3.0.00.000 - Productos de Loza y porcelana","22.6.4.0.00.000 - Productos de Cemento, asbesto y yeso","22.6.5.0.00.000 - Productos de Cemento, Cal y Yeso"],
	    "22.7.0.0.00.000 - Productos metálicos": ["22.7.1.0.00.000 - Productos Ferrosos","22.7.2.0.00.000 - Productos no ferrosos","22.7.3.0.00.000 - Material de Guerra","22.7.4.0.00.000 - Estructuras metálicas acabadas","22.7.5.0.00.000 - Herramientas menores"],
	    "22.8.0.0.00.000 - Minerales": ["22.8.1.0.00.000 - Minerales metalíferos","22.8.2.0.00.000 - Petróleo crudo y gas natural","22.8.3.0.00.000 - Carbón mineral","22.8.4.0.00.000 - Piedra, Arcilla y Arena"],
	    "22.9.0.0.00.000 - Otros bienes de consumo": ["22.9.1.0.00.000 - Elementos de limpieza","22.9.2.0.00.000 - Útiles de escritorio, oficina y enseñanza","22.9.3.0.00.000 - Útiles y materiales eléctricos","22.9.4.0.00.000 - Utencillos de cocina y comedor","22.9.5.0.00.000 - Útiles menores médico-quirúrgico y de laboratorio","22.9.6.0.00.000 - Repuestos y accesorios"],
	    "22.9.7.0.00.000 - Equipos y Elementos de Seguridad": ["22.9.7.1.00.000 - Extintores y equipos contra incendios","22.9.7.2.00.000 - Señalización y Vallado","22.9.7.3.01.000 - Calzado, Guantes e Indumentarias","22.9.7.3.02.000 - Protección Respiratoria, Auditiva y Visual","22.9.7.3.03.000 - Cascos y Arnes"],
	    "22.9.9.0.00.000 - Otros no especificados precedentemente": ["22.9.9.1.01.000 - Electromésticos","22.9.9.1.02.000 - Mobiliario de oficina","22.9.9.1.03.000 - Mobiliario de Cocina","22.9.9.1.04 - Mobiliarios Varios","22.9.9.2.00.000 - Equipos y Elementos Deportivos"]
    },
    "3. Servicios": {
        "23.1.0.0.00.000 - Servicios básicos": ["23.1.1.0.00.000 - Energía Eléctrica","23.1.2.0.00.000 - Agua","23.2.3.0.00.000 - Gas","23.1.4.0.00.000 - Telefono, telex, telefax","23.1.5.0.00.000 - Correo y telégrafos"],
		"23.2.0.0.00.000 - Alquiler y derechos": ["23.2.1.0.00.000 - Alquiler de edificios y locales","23.2.2.0.00.000 - Alquiler de maquinaria, equipo y medios de transporte","23.2.3.0.00.000 - Alquiler de equipos de computación","23.2.4.0.00.000 - Alquiler de fotocopiadoras","23.2.5.0.00.000 - Alquiler de tierras y terrenos","23.2.6.0.00.000 - Derechos de bienes intangibles"],
		"23.2.9.1.00.000 - Otros alquileres no comprendidos precedentemente": ["23.2.9.1.00.000 - Alquiler de máquinas expendedoras de alimentos","23.2.9.2.00.000 - Alquiler de expendedoras de agua","23.2.9.3.00.000 - Alquiler de baños químicos","23.2.9.4.00.000 - Alquiler Estructuras Varias (Incluye Vallas Seguridad, Gradas, etc)"],
   		"23.3.0.0.00.000 - Mantenimiento, reparación y limpieza": ["23.3.1.0.00.000 - Mantenimiento y reparación de edificios y locales","23.3.2.0.00.000 - Mantenimiento y reparación de vehículos","23.3.3.0.00.000 - Mantenimiento y reparación de mauqinaria y equipo","23.3.4.0.00.000 - Mantenimiento y reparación de vías de comunicación","23.3.5.0.00.000"],
		"23.3.9.0.00.000 - Otros no especificados precedentemente": ["23.3.9.1.01.000 - Corte de pasto y desmalezado","23.3.9.1.02.000 - Poda y mantenimiento de arbolado","23.3.9.2.01 - Mantenimiento de Desaües","23.3.9.2.02.000 - Mantenimiento de Canales","23.3.9.2.03.000 - Mantenimiento de Cordón Cuneta","23.3.9.3.00.000 - Limpieza de calles y caminos","23.3.9.4.00.000 - Mantenimiento de conexiones cloacales","23.3.9.5.00.000 - Mantenimiento de Alumbrado Público y tendido eléctrico","23.3.9.6.01.000 - Mantenimiento de Semáforos","23.3.9.6.02.000 - Mantenimiento de Señalización Vial"],
		"23.4.0.0.00.000 - Servicios técnicos y profesionales": ["23.4.1.0.00.000 - Estudios, investigación y proyectos de factibilidad","23.4.2.0.00.000 - Médicos y Sanitarios","23.5.3.0.00.000 - Jurídicos","23.4.4.0.00.000 - Contabilidad y auditoría","23.4.5.0.00.000 - De Capacitación","23.4.6.0.00.000 - De Informática y sistemas computarizados","23.4.7.0.00.000 - De Turismo","23.4.8.0.00.000 - De Geriátricos","23.4.9.1.00.000 - Servicio de Alarma","23.4.9.2.00.000 - Servicio de Escribanía","23.4.9.3.00.000 - Servicio de Agrimensura","23.4.9.4.00.000 - Servicio de Arquitectura","23.4.9.5.00.000 - Servicios relacionados a la Agronomía","23.4.9.6.01.000 - Servicios de Ingeniería Industrial","23.4.9.6.02.000 - Servicio de Ingeniería Agrónoma","23.4.9.6.03.000 - Servicio de Ingeniería Informática","23.4.9.6.04.000 - Servicio de Ingeniería Civil","23.4.9.6.05.000 - Servicios de Ingeniería Híbrica","23.4.9.7.00.000 - Servicio de Sonido e Iluminación"],
		"23.5.0.0.00.000 - Servicios comerciales y financieros": ["23.5.1.0.00.000 - Transporte","23.5.2.0.00.000 - Almacenamiento","23.5.3.0.00.000 - Imprenta, publicaciones y reproducciones","23.5.4.0.00.000 - Primas y gastos de seguros","23.5.5.0.00.000 - Comisiones y Gastos Bancarios","23.5.6.0.00.000 - Internet"],
		"23.5.9.0.00.000 - Otros no especificados precedentemente": ["23.5.9.1.00.000 - Estampillas y estampillados","23.5.9.2.00.000 - Gestión de Cobranza"],
		"23.6.0.0.00.000 - Publicidad y Propaganda": ["23.6.1.0.00.000 - Publicidad y Propaganda MCS","23.6.2.0.00.000 - Publicidad y Propaganda rodante","23.6.3.0.00.000 - Publicidad"],
		"23.7.0.0.00.000 - Pasajes y viáticos": ["23.7.1.0.00.000 - Pasajes","23.7.2.0.00.000 - Viáticos","23.7.3.0.00.000 - Combustibles y Peajes"],
		"23.8.0.0.00.000 - Impuestos, derechos y tasas": ["23.8.1.0.00.000 - Impuestos indirectos","23.8.2.0.00.000 - Impuestos directos","23.8.3.0.00.000 - Derechos y tasas","23.8.4.0.00.000 - Multas y recargos","23.8.5.0.00.000 - Regalías","23.8.6.0.00.000 - Juicios y mediaciones","23.8.7.0.00.000 - Aportes colegios profesinales"],
		"23.9.0.0.00.000 - Otros servicios": ["23.9.1.0.00.000 - Servicio de Ceremonial","23.9.2.0.00.000 - Gastos reservados","23.9.3.0.00.000 - Servicio de Vigilancia","23.9.4.0.00.000 - Gastos potocolares","23.9.5.0.00.000 - Edictos y publicaciones oficiales","23.9.6.0.00.000 - Becas de Investigación","23.9.7.0.00.000 - Contratación de Servicios Artísticos","23.9.8.0.00.000 - Ambientación, Arte y Decoración"],
		"23.9.9.0.00.000 - Otros NEP": ["23.9.9.1.00.000 - Hotelería","23.9.9.2.00.000 - Servicios de educación no formal","23.9.9.3.00.000 - Servicios relacionados a deporte y recreación","23.9.9.4.00.000 - Promoción Actividades Económicas e institucionales","23.9.9.5.00.000 - Servicios relacionados con la comunicación"]

	},

	"4. Bienes de Uso": {
		"24.1.0.0.00.000 - Bienes preexistentes": ["24.1.1.0.00.000 - Tierras y terrenos", "24.1.2.0.00.000 - Edificios e instalaciones", "24.1.3.0.00.000 - Otros Bienes preexistentes"],
		"24.2.1.0.00.000 - Construcciones en Bienes de Dominio Privado": ["24.2.1.1.01.000 - Const. de Dom. Priv. por Adm. Ctral. (Libre)", "24.2.1.1.02.000 - Const. de Dom. Priv. por Adm. Ctral (Afectado)", "24.2.1.2.01.000 - Const. de Dom. Priv. por Ad. Ctral. (libre)","24.2.1.2.02.000 - Const. de Dom. Priv. por Ad. Ctral. (Afectado)", "24.2.2.1.01.000 - Const. de Dom. Priv. por Ad. Ctral. (libre)","24.2.2.2.02.000 - Const. de Dom. Priv. por Ad. Ctral. (Afectado)", "24.2.3.0.00.000 - Forestación"],
        "24.3.0.0.00.000 - Maquinaria y equipo": ["24.3.1.0.00.000 - Maquinaria y equipo de producción", "24.3.2.2.00.000 - Equipo de transporte, tracción y elevación", "24.3.3.0.00.000 - Sanitario y de Laboratorio", "24.3.4.0.00.000 - Equipo de comunicación y señalamiento", "24.3.5.0.00.000 - Equipo educacional y recreativo", "24.3.6.1.00.000 - Equipo para computación", "24.3.6.2.01.000 - Equipo para computación (Fondo HCD)", "24.3.6.2.02.000 - Equipo para computación (Fondo Provincial)", "24.3.7.1.00.000 - Equipo de oficina y mueble (F. Propio)", "24.3.7.2.00.000 - Equipo de Oficina y Mueble (Fondos Provinciales)", "24.3.8.0.00.000 - Herramientas y repuestos mayores", "24.3.8.0.00.000 - Herramientas y repuestos mayores", "24.3.9.1.01.000 - Equipo y material de Sonido", "24.3.9.2.00.000 - Teléfonos celulares, Tablet y símil", "24.3.9.3.00.000 - Electrodomésticos", "24.3.9.4.00.000 - Equipos de y para Monitoreo"],
		"24.4.0.0.00.000 - Equipo de Seguridad": ["N/N"],
		"24.5.0.0.00.000 - Libros, revistas y otros elementos coleccionables": ["24.5.1.0.00.000 - Libros y Partituras"],
		"24.6.0.0.00.000 - Obras de arte":["N/N"],
		"24.7.0.0.00.000 - Semovientes": ["N/N"],
		"24.8.0.0.00.000 - Activos intangibles": ["24.8.1.0.00.000 - Programas de Computación y Software", "24.8.9.0.00.000 - Otros Activos intangibles"]

    },
    "5. Transferencias": {
        "25.1.0.0.00.000 - Transferencias al sector privado para financiar gastos corrientes": ["25.1.1.0.00.000 - Jubilaciones y/o retiros", "25.1.2.0.00.000 -  Pensiones", "25.1.3.0.00.000 - Becas y Pasantías"], 
		"25.1.4.0.00.000 - Ayudas Sociales a Personas": ["25.1.4.1.01.000 - Ayudas Sociales a Personas (Viáticos Salud)", "25.1.4.1.02.000 - Ayuda Soc. a Personas para gastos de Alquiler", "25.1.4.1.03.000 - Ayuda Soc. a Personas para pago de servicios", "25.1.4.1.04.000 - Ayuda Soc. a Personas para sepelios", "25.1.4.1.05.000 - Ayuda Soc. a Personas para Medicamentos y Prod. Farmacéuticos", "25.1.4.1.06.000 - Ayuda Soc. a personas para Gastos Corrientes", "25.1.4.1.07.000 - Ayuda Soc. a personas para eventos deportivos"],
		"25.1.4.0.00.000 - Ayudas Sociales a Personas (b)": ["25.1.4.2.00.000 - Premios, recompensas y reconocimientos destacados", "25.1.4.3.00.000 - Promoción Social", "25.1.4.4.00.000 - Boleto Educativo"],
		"25.1.5.0.00.000 - Transferencia a Instituciones de Enseñanaza": ["N/N"],
		"25.1.5.1.00.000 - Fondo de Asistencia Educativa": ["25.1.5.1.01.000 - Instituciones Públicas", "25.1.5.1.02.000 - Instituciones Privadas"],
		"25.1.6.0.00.000 - Transferencias para actividades científicas o académicas": ["25.1.6.0.00.000 - Transferencias para actividades científicas o académicas"],
		"25.1.7.0.00.000 - Transferencias a Instituciones culturales y sociales sin fines de lucro": ["25.1.7.1.00.000 - Transferencias a Instituciones Culturales y/o religiosas", "25.1.7.2.00.000 - Transferencias a Instituciones Sociales", "25.1.7.4.00.000 - ADESU", "25.1.7.6.00.000 - Centro Comercial y de la Producción", "25.1.7.7.00.000 - Instituciones de Bien Público", "25.1.7.8.00.000 - Presupuesto Participativo"],
		"25.1.7.5.00.000 - Transferencias a Instituciones culturas y sociales sin fines de lucro (Vecinales)": ["25.1.7.5.01.000 - B. Centro", "25.1.7.5.02.000 - B. Sur", "25.1.7.5.03.000 - B. Sancor", "25.1.7.5.04.000 - B. Colón", "25.1.7.5.05.000 - B. Villa del Parque", "25.1.7.5.06.000 - B. Moreno", "25.1.7.5.07.000 - B. Cooperativo", "25.1.7.5.08.000 - B. Villa Autódromo", "25.1.7.5.09.000 - B. 9 de Julio"],
		"25.1.7.9.00.000 - Otras Instituciones": ["25.1.7.9.01.000 - Comparasas", "25.1.7.9.02.000 - Instituciones Deportivas", "25.1.7.9.03.000 - Transferencia LAZOS"],
		"25.1.8.0.00.000 - Transferencias a Cooperativas": ["N/N"],
		"25.1.9.0.00.000 - Transferencias a empresas privadas": ["25.1.9.0.00.000 - Transferencias a empresas privadas"],
		"25.2.0.0.00.000 - Transferencias al sector privado para financiar gastos de Capital": ["25.2.1.1.01.000 - Transf. Personas. Mej. Habitacional", "25.2.1.1.02.000 - Trans. Construcción Lote Propio", "25.2.1.2.00.000 - Transferencias a Personas para adquisición de Otros bienes tangibles", "25.2.1.3.00.000 - Transferencias a Personas para adquisición de Bienes Intangibles"],
        "25.7.0.0.00.000 - Transferencias a instituciones provinciales y municipales para financiar gasto corriente": ["25.7.4.1.00.000 - Fondo de Asistencia Educativa", "25.7.6.1.00.000 - Concejo Municipal","25.7.6.2.00.000 - Patrimonio Cultural Sunchalense", "25.7.6.3.00.000 - Concejo de Inclusión y Discapacidad", "25.7.6.4.00.000 - Comisión Niños y Adolescentes", "25.7.6.5.00.000 - Fondo Acción Vecinal", "25.7.6.6.00.000 - GIRSU", "25.7.6.7.00.000 - Instituto Municipal de la Vivienda", "25.7.9.1.00.000 - Transferencia S.A.M.C.O", "25.7.9.2.00.000 - Transferencia Policía de Santa Fe", "25.7.9.3.00.000 - Transferencia Policía Rural 'Los Pumas'", "25.7.9.5.00.000 - ENRESS", "25.7.9.6.00.000 - Fondo Departamento Castellanos"],
        "25.8.0.0.00.000 - Transferencias a Instituciones provinciales y municipales para Financiar gastos de Capital": ["N/N"],
	},
    "6. Activos Financieros": {
        "26.2.0.0.00.000 - Prestamos a corto plazo": ["26.2.1.6.01.000 - Préstamos Aportes Sociales Reintegrables"],
        "26.1.0.0.00.000 - Aportes de capital": ["26.1.1.0.00.000 - Aportes de Capital a empresas privadas","26.1.2.0.00.000 - Aportes de Capital a empresas públicas no financieras","26.1.3.0.00.000 - Aportes de Capital a Instituciones Públicas Financieras"],
		"26.2.0.0.00.000 - Prestamos a Corto plazo al Sector Privado": ["Préstamos a Microemprendedores","26.2.1.2.00.000 - Préstamos a Emprendedores","26.2..3.00.00 - Préstamos a empresas","26.2.1.4.00.000 - Préstamos a Pymes"],
		"26.2.1.5.00.000 - Préstamos a Intituciones": ["26.2.1.5.01.000 - Préstamos a Intituciones Públicas No Financieras","26.2.1.5.02.000 - Préstamos a Intituciones Públicas Financieras","26.2.1.5.03.000 - Préstamos a Intituciones Privadas No Financieras","26.2.1.5.04.000 - Préstamos a Intituciones Privadas Financieras"],
		"26.2.1.6.00.000 - Préstamo a Personas": ["26.2.1.6.01.001 - Préstamos Aporte Social Reintegrable para Salud","26.2.1.6.01.002 - Préstamo Aporte Social Reintegrable para Alquiler","26.2.1.6.01.003 - Préstamo Aporte Social Reintegrable para Sepelio","26.2.1.6.01.004 - Préstamo Aporte Social Reintegrable para Servicios Básicos","26.2.1.6.01.005 - Préstamo Aporte Social Reintegrable (Otros)","26.2.1.6.02.000 - Préstamos Empleados"],
		"26.3.0.0.00.000 - Prestamos a largo plazo": ["26.3.1.1.00.000 - Préstamos a Personas","26.3.1.2.00.000 - Préstamos a  Emprendedores","26.3.1.3.00.000 - Préstamos a Empresas","26.3.1.4.00.000 - Préstamo a Pymes","26.3.1.5.01.000 - Préstamo a Intituciones Públicas No Financieras","26.3.1.5.02.000 - Préstamo a Intituciones Públicas Financieras","26.3.1.5.03.000 - Préstamo a Intituciones Privadas No Financieras","26.3.1.5.04.000 - Préstamo a Intituciones Privadas Financieras"],
		"26.4.0.0.00.000 - Titulos y valores": ["26.4.1.0.00.000 - Títulos y Valores a Corto Plazo","26.4.2.0.00.000 - Títulos y Valores a Largo Plazo"],
		"26.5.0.0.00.000 - Incremento de disponibilidades": ["26.5.1.0.00.000 - Incremento de Caja y Bancos","26.5.2.0.00.000 - Incremento de Inversiones financieras temporarias"],
		"26.6.0.0.00.000 - Incremento de cuentas a cobrar": ["26.6.1.0.00.000 - Incremento de Ctas. Comerciales a cobrar a corto plazo","26.6.2.0.00.000 - Incremento de Otras Ctas. a cobrar a corto plazo","26.6.3.0.00.000 - Incremento de Ctas. a cobrar comerciales a largo plazo","26.6.4.0.00.000 - Incremento de otros documentos a cobrar a largo plazo"],
		"26.7.0.0.00.000 - Incremento de documentos a cobrar": ["26.7.1.0.00.000 - Incremento de documentos comerciales a cobrar a corto plazo","26.7.2.0.00.000 - Incremento de otros documentos a cobrar a corto plazo","26.7.3.0.00.000 - Incremento de documentos comerciales a cobrar a largo plazo","26.7.4.0.00.000 - Incremento de otros documentos a cobrar a largo plazo"],

    },
    "7. Servicio de la deuda": {
        "27.1.0.0.00.000 - Servicio de la deuda interna": ["27.1.1.0.00.000 - Intereses de la deuda a Corto Plazo","27.1.2.0.00.000 - Amortización de la deuda interna a corto plazo","27.1.3.0.00.000 - Comisiones y otros gastos de la deuda interna a corto plazo","27.1.7.0.00.000 Amortización de la deuda interna a largo plazo"],
		"27.4.0.0.00.000 - Disminucion de prestamos a corto plazo": ["27.4.5.0.00.000 - Disminución de préstamos recibidos de provincia y municipios"],
		"27.5.0.0.00.000 - Disminucion de prestamos a largo plazo": ["27.5.5.0.00.000 - Disminución de préstamos a largo plazo recibidos de provincia y municipalidades"],
		"27.6.0.0.00.000 - Disminucion de cuentas y documentos a pagar": ["27.6.1.0.00.000 - Disminución de cuentas a pagar comerciales a corto plazo","27.6.2.0.00.000 - Disminución de otras cuentas a pagar a corto plazo"],

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
    "SECRETARÍA DE GOBIERNO": ["SECRETARÍA DE GOBIERNO","SUBSECRETARÍA DE GESTIÓN Y DESARROLLO"],
    "SECRETARÍA DE DESARROLLO Y PROMOCIÓN DE DDHH": ["SECRETARÍA DE DESARROLLO Y PROMOCIÓN DE DDHH", "SUBSECRETARÍA DE CULTURA","SUBSECRETARÍA DE PROMOCIÓN DE DDHH"],
    "INTENDENCIA": ["INTENDENCIA"],
    "HCD": ["HCD"]
}

opciones_secretarias = list(MAPEO_ESTRUCTURA.keys())
opciones_objetos = list(MAPEO_GASTOS.keys())
opciones_fuente_fin = ["Municipal", "Provincial", "Nacional"]
opciones_clase = ["Corriente", "Capital"]
opciones_tipo = ["Libre", "Afectado"]
opciones_finalidad = ["Administración Central", "Promoción y asistencia social","Educación","Cultura","Ciencia y técnica","Servicios urbanos","Vivienda y urbanismo","Deuda Pública","Ecología y medio ambiente","Deporte y recreación","Obra pública","Apoyo a Instituciones","Desarrollo de Gestión","Legislativa", "Salud", "Seguridad","Promoción industrial y Laboral"]

# =====================================================================
# MENÚ LATERAL A LA IZQUIERDA (SIDEBAR)
# =====================================================================
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
            "🔄 COMPARATIVO E HISTÓRICO",
			"📈 REPORTE DE EJECUCIÓN OFICIAL"
        ])

    # 🔄 PEGÁ ESTO ACÁ ABAJO EN LA BARRA LATERAL:
    st.markdown("---")
    if st.button("🔄 Sincronizar y Limpiar Caché", use_container_width=True):
        if "db_local_backup" in st.session_state:
            st.session_state["db_local_backup"] = {"destinos": [], "egresos": [], "recursos": []}
        st.cache_data.clear()
        st.success("¡Caché limpiada y datos actualizados desde Google Sheets!")
        st.rerun()


# =====================================================================
# SECCIÓN: REGISTRO DE RECURSOS (INGRESOS)
# =====================================================================
if opcion_menu == "📥 REGISTRO DE RECURSOS":
    st.subheader("📥 Cargar Nuevo Recurso / Ingreso Presupuestario")

    df_rec_gsheet = leer_datos_gsheet(URL_READ_RECURSOS)
    lista_rec_mostrar = []

    if not df_rec_gsheet.empty:
        df_rec_gsheet.columns = [str(c).strip().upper() for c in df_rec_gsheet.columns]

        cols_necesarias = ["ORIGEN GENERAL", "PARTIDA / CUENTA PADRE", "CONCEPTO ESPECÍFICO", "VALOR", "TOTALES", "TIPO", "DESTINO"]
        for cn in cols_necesarias:
            if cn not in df_rec_gsheet.columns:
                df_rec_gsheet[cn] = ""

        df_rec_gsheet["VALOR"] = pd.to_numeric(df_rec_gsheet["VALOR"].astype(str).str.replace("$", "", regex=False).str.replace(".", "", regex=False).str.replace(",", ".", regex=False), errors='coerce').fillna(0.0)
        df_rec_gsheet["TOTALES"] = pd.to_numeric(df_rec_gsheet["TOTALES"].astype(str).str.replace("$", "", regex=False).str.replace(".", "", regex=False).str.replace(",", ".", regex=False), errors='coerce').fillna(0.0)

        lista_rec_mostrar = df_rec_gsheet.to_dict('records')

    for r_l in st.session_state.get("db_local_backup", {}).get("recursos", []):
        lista_rec_mostrar.append(r_l)

    df_rec_completo = pd.DataFrame(lista_rec_mostrar) if lista_rec_mostrar else pd.DataFrame(columns=["ORIGEN GENERAL", "PARTIDA / CUENTA PADRE", "CONCEPTO ESPECÍFICO", "VALOR", "TOTALES", "TIPO", "DESTINO"])

    for col_n in ["VALOR", "TOTALES"]:
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

    # 🛡️ Blindaje de seguridad para evitar NameError
    if 'r_origen' not in locals(): r_origen = ""
    if 'r_cuenta_padre' not in locals(): r_cuenta_padre = ""
    if 'r_concepto' not in locals(): r_concepto = ""
    if 'r_tipo' not in locals(): r_tipo = ""
    if 'r_destino' not in locals(): r_destino = ""
    if 'r_valor' not in locals(): r_valor = 0.0

    recurso_completo = (r_origen != "") and (r_concepto != "") and (r_tipo != "") and (r_destino.strip() != "") and (r_valor > 0)

    if st.button("💾 GUARDAR RECURSO EN GOOGLE SHEETS", type="primary", use_container_width=True, disabled=not recurso_completo):
        nuevo_recurso = {
            "ORIGEN GENERAL": r_origen.upper(), 
            "PARTIDA / CUENTA PADRE": r_cuenta_padre.upper(), 
            "CONCEPTO ESPECÍFICO": r_concepto.upper(), 
            "VALOR": float(r_valor), 
            "TOTALES": float(r_totales), 
            "TIPO": r_tipo.upper(), 
            "DESTINO": r_destino.strip().upper()
        }
        guardar_fila_gsheet("recursos", nuevo_recurso)

        # 🧹 LIMPIAR LAS KEYS PARA QUE LOS INPUTS SE RESETEEN
        keys_a_limpiar = ["rec_origen_map", "rec_padre_map", "rec_con_map", "rec_tipo_map", "rec_destino", "rec_valor", "rec_totales"]
        for k in keys_a_limpiar:
            if k in st.session_state:
                del st.session_state[k]

        st.success("✅ ¡Recurso guardado correctamente en la base de datos!")
        st.balloons()
        st.rerun()

    st.markdown("---")
    st.markdown("### 📋 Listado Consolidado de Recursos")

    if not df_rec_completo.empty:
        tot_val_gral = df_rec_completo["VALOR"].sum() if "VALOR" in df_rec_completo.columns else 0.0
        tot_tot_gral = df_rec_completo["TOTALES"].sum() if "TOTALES" in df_rec_completo.columns else 0.0

        m1, m2 = st.columns(2)
        m1.metric(label="💰 TOTAL VALOR", value=f"${tot_val_gral:,.2f}")
        m2.metric(label="📊 TOTAL GENERAL ACUMULADO", value=f"${tot_tot_gral:,.2f}")

        df_v_rec = df_rec_completo.copy()
        if "VALOR" in df_v_rec.columns:
            df_v_rec["VALOR"] = df_v_rec["VALOR"].map(lambda x: f"${x:,.2f}")
        if "TOTALES" in df_v_rec.columns:
            df_v_rec["TOTALES"] = df_v_rec["TOTALES"].map(lambda x: f"${x:,.2f}")

        st.dataframe(df_v_rec, use_container_width=True, hide_index=True)

        # --- BOTONES DE EXPORTACIÓN E IMPRESIÓN ---
        st.markdown("---")
        col_exp1, col_exp2 = st.columns(2)

        with col_exp1:
            html_imprimir = """
            <script>
            function imprimirSeccion() {
                window.print();
            }
            </script>
            <button onclick="imprimirSeccion()" style="
                width: 100%;
                background-color: #ff4b4b;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                cursor: pointer;
                font-size: 16px;">
                🖨️ Imprimir / Guardar PDF
            </button>
            """
            st.components.v1.html(html_imprimir, height=50)

        with col_exp2:
            csv_recursos = df_rec_completo.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Descargar Reporte en CSV",
                data=csv_recursos,
                file_name="reporte_recursos.csv",
                mime="text/csv",
                use_container_width=True
            )

        st.markdown("""
            <style>
            @media print {
                [data-testid="stSidebar"], header, footer, .stButton {
                    display: none !important;
                }
                .main {
                    background-color: white !important;
                }
            }
            </style>
        """, unsafe_allow_html=True)
    else:
        st.info("💡 Todavía no hay recursos registrados.")

# =====================================================================
# SECCIÓN 1: FORMULARIO PRINCIPAL DE REGISTRO
# =====================================================================
if opcion_menu == "📝 FORMULARIO DE REGISTRO":
    st.subheader("📥 Cargar Nuevo Renglón Presupuestario")

    # 🛡️ Inicialización previa de todas las variables para evitar NameError
    f_sec, f_sub, f_dest = "", "", None
    f_obj, f_padre, f_presup = "", "", ""

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

        # 🧹 LIMPIAR LAS KEYS DE REGISTRO
        keys_reg = ["reg_sec", "reg_sub", "reg_dest", "reg_obj", "reg_padre", "reg_presup"]
        for k in keys_reg:
            if k in st.session_state:
                del st.session_state[k]

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

        # Limpiar estado si usaras key, o simplemente forzar un reseteo limpio
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

                # Botón de envío correctamente indentado dentro del formulario
                if st.form_submit_button("🛠️ Guardar Cambios en este Registro", use_container_width=True):
                    if idx_real < len(st.session_state["db_local_backup"]["egresos"]):
                        # 1. Armamos el diccionario completo incluyendo los campos fijos (secretaria, subsecretaria, destino)
                        datos_actualizados = {
                            "secretaria": str(fila_r.get("secretaria", "")),
                            "subsecretaria": str(fila_r.get("subsecretaria", "")),
                            "destino": str(fila_r.get("destino", "")),
                            "objeto_gasto": mod_obj,
                            "cuenta_padre": mod_padre,
                            "cuenta_presupuestaria": mod_presup,
                            "total": mod_monto,
                            "fuente_fin": mod_fuente,
                            "clase": mod_clase,
                            "tipo": mod_tipo,
                            "finalidad": mod_finalidad
                        }
                        
                        # Actualizamos la sesión local
                        st.session_state["db_local_backup"]["egresos"][idx_real].update(datos_actualizados)
                        
                        # 2. Sincronizamos los cambios con Google Sheets a través del Webhook enviando el paquete completo
                        try:
                            payload = {
                                "pestana": "egresos", 
                                "fila_idx": idx_real,
                                **datos_actualizados
                            }
                            resp = requests.post(URL_WEBHOOK_GSHEET, json=payload, timeout=10, allow_redirects=True)
                            
                            if resp.status_code in [200, 302]:
                                st.success(f"¡Renglón {idx_real + 1} actualizado en la sesión y sincronizado en Google Sheets!")
                            else:
                                st.warning(f"⚠️ Actualizado localmente, pero el Webhook respondió con código: {resp.status_code}")
                        except Exception as e:
                            st.warning(f"⚠️ Actualizado en la sesión. Error al sincronizar con Google Sheets: {e}")
                        
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
# SECCIÓN 6: REPORTE CONSOLIDADO Y ESTADÍSTICAS
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
# SECCIÓN 7: BUSCADOR AVANZADO
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
# SECCIÓN 8: EXPORTACIÓN Y FIRMAS
# =====================================================================
elif opcion_menu == "📄 EXPORTACIÓN Y FIRMAS":
    st.subheader("📄 Exportación General Oficial por Destino (con Cuadro de Firmas)")

    if df_egr_completo.empty:
        st.info("💡 No hay registros contables cargados en el sistema para exportar.")
    else:
        tot_general_exp = df_egr_completo["total"].sum()
        st.metric(label="📋 TOTAL GENERAL A EXPORTAR", value=f"${tot_general_exp:,.2f}")

        bloques_html_destinos = ""

        for (sec_exp, sub_exp, dest_exp), df_dest_exp in df_egr_completo.groupby(["secretaria", "subsecretaria", "destino"]):
            tot_dest_exp = df_dest_exp["total"].sum()
            rows_dest_exp = ""

            for obj, df_obj in df_dest_exp.groupby("objeto_gasto"):
                t_o = df_obj["total"].sum()
                rows_dest_exp += f'<tr style="font-weight: bold; background-color: #f9f9f5;"><td style="text-align: left; padding-left: 5px;">{obj}</td><td style="text-align: right;">${t_o:,.2f}</td><td></td><td></td><td></td><td></td></tr>'

                for pad, df_pad in df_obj.groupby("cuenta_padre"):
                    t_p = df_pad["total"].sum()
                    rows_dest_exp += f'<tr style="font-weight: bold;"><td style="text-align: left; padding-left: 20px;">{pad}</td><td style="text-align: right;">${t_p:,.2f}</td><td></td><td></td><td></td><td></td></tr>'

                    for _, r in df_pad.iterrows():
                        rows_dest_exp += f'<tr><td style="text-align: left; padding-left: 40px;">{r["cuenta_presupuestaria"]}</td><td style="text-align: right;">${r["total"]:,.2f}</td><td style="text-align: center;">{r["fuente_fin"]}</td><td style="text-align: center;">{r["clase"]}</td><td style="text-align: center;">{r["tipo"]}</td><td style="text-align: center;">{r["finalidad"]}</td></tr>'

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
                <div class="firma-box">Sec. Hacienda</div>
                <div class="firma-box">Intendente</div>
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
# SECCIÓN 9: RANKING Y MAYORES EROGACIONES
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
                    "secretaria": "SECRETARÍA", "destino": "DESTINO", "objeto_gasto": "OBJETO GASTO",
                    "cuenta_presupuestaria": "PARTIDA", "total": "MONTO TOTAL ($)", "fuente_fin": "FUENTE"
                }
            ),
            use_container_width=True, hide_index=True
        )

# =====================================================================
# SECCIÓN 10: COMPARATIVO DE ESTRUCTURA Y FUENTES
# =====================================================================
elif opcion_menu == "⚖️ COMPARATIVO DE ESTRUCTURA Y FUENTES":
    st.subheader("⚖️ Matriz Comparativa: Clase de Gasto vs Fuente de Financiamiento")

    if df_egr_completo.empty:
        st.info("💡 No hay datos suficientes para armar la matriz comparativa.")
    else:
        matriz = pd.pivot_table(
            df_egr_completo, values="total", index="clase", columns="fuente_fin", aggfunc="sum", fill_value=0.0
        )
        st.markdown("##### 📊 Matriz de Totales por Clase y Fuente ($)")
        st.dataframe(matriz.style.format("${:,.2f}"), use_container_width=True)

# =====================================================================
# SECCIÓN 11: AUDITORÍA Y CONTROL DE CALIDAD
# =====================================================================
elif opcion_menu == "🧹 AUDITORÍA Y CONTROL DE CALIDAD":
    st.subheader("🧹 Panel de Auditoría y Verificación de Datos")

    if df_egr_completo.empty:
        st.info("💡 No hay datos para auditar.")
    else:
        df_cero = df_egr_completo[df_egr_completo["total"] == 0]
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
# SECCIÓN 12: VISTA POR SECRETARÍA Y SUBSECRETARÍA
# =====================================================================
elif opcion_menu == "🏢 VISTA POR SECRETARÍA Y SUBSECRETARÍA":
    st.subheader("🏢 Vista Jerárquica por Secretaría y Subsecretaría")

    if df_egr_completo.empty:
        st.info("💡 No hay registros contables cargados para mostrar.")
    else:
        lista_secretarias = sorted([s for s in df_egr_completo["secretaria"].unique() if str(s).strip() != ""])
        col_sec, col_sub = st.columns(2)

        with col_sec:
            sec_seleccionada = st.selectbox("1. Seleccionar Secretaría:", lista_secretarias)

        df_sec_filtrado = df_egr_completo[df_egr_completo["secretaria"] == sec_seleccionada]
        lista_subsecretarias = sorted([s for s in df_sec_filtrado["subsecretaria"].unique() if str(s).strip() != ""])

        with col_sub:
            sub_seleccionada = st.selectbox("2. Seleccionar Subsecretaría:", lista_subsecretarias)

        df_area = df_sec_filtrado[df_sec_filtrado["subsecretaria"] == sub_seleccionada]
        st.markdown("---")

        if df_area.empty:
            st.warning("No se encontraron registros cargados para la combinación seleccionada.")
        else:
            tot_area = df_area["total"].sum()
            cant_destinos = df_area["destino"].nunique()

            m_a1, m_a2 = st.columns(2)
            m_a1.metric("💰 Presupuesto Total de la Subsecretaría", f"${tot_area:,.2f}")
            m_a2.metric("📌 Cantidad de Destinos Asignados", f"{cant_destinos}")

            st.markdown("### 📍 Resumen de Destinos")
            df_destinos_resumen = df_area.groupby("destino")["total"].sum().reset_index()
            df_destinos_resumen["total_fmt"] = df_destinos_resumen["total"].map(lambda x: f"${x:,.2f}")
            df_destinos_resumen.columns = ["DESTINO", "TOTAL ($)", "PRESUPUESTO FORMATEADO"]

            st.dataframe(df_destinos_resumen[["DESTINO", "PRESUPUESTO FORMATEADO"]], use_container_width=True, hide_index=True)

            st.markdown("---")
            st.markdown("### 🔍 Detalle por Destino y Partidas")

            for dest, df_d in df_area.groupby("destino"):
                tot_d = df_d["total"].sum()
                with st.expander(f"📌 DESTINO: {str(dest).upper()} — Total: ${tot_d:,.2f}"):
                    df_mostrar = df_d.copy()
                    df_mostrar["total"] = df_mostrar["total"].map(lambda x: f"${x:,.2f}")
                    st.dataframe(
                        df_mostrar[["objeto_gasto", "cuenta_padre", "cuenta_presupuestaria", "total", "fuente_fin", "clase", "tipo"]].rename(
                            columns={"objeto_gasto": "OBJETO GASTO", "cuenta_padre": "CUENTA PADRE", "cuenta_presupuestaria": "PARTIDA", "total": "MONTO ($)", "fuente_fin": "FUENTE", "clase": "CLASE", "tipo": "TIPO"}
                        ),
                        use_container_width=True, hide_index=True
                    )

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
                    <div class="firma-box">Sec. Hacienda</div>
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
# SECCIÓN 13: REPORTE POR FINALIDAD Y FUNCIÓN
# =====================================================================
elif opcion_menu == "🎯 REPORTE POR FINALIDAD Y FUNCIÓN":
    st.subheader("🎯 Consolidado Presupuestario por Finalidad y Función")

    if df_egr_completo.empty:
        st.info("💡 No hay registros contables cargados para generar el reporte de finalidades.")
    else:
        col_fin = "finalidad" if "finalidad" in df_egr_completo.columns else df_egr_completo.columns[0]
        col_fun = "tipo" if "tipo" in df_egr_completo.columns else col_fin

        tot_general_ff = df_egr_completo["total"].sum()
        st.metric("💰 TOTAL GENERAL PRESUPUESTO", f"${tot_general_ff:,.2f}")

        df_fin_fun = df_egr_completo.groupby([col_fin, col_fun])["total"].sum().reset_index()

        st.markdown("---")
        st.markdown("##### 📋 Resumen en Pantalla")

        df_tabla_ff = df_fin_fun.copy()
        df_tabla_ff["porcentaje"] = (df_tabla_ff["total"] / (tot_general_ff if tot_general_ff > 0 else 1)) * 100
        df_tabla_ff["total_fmt"] = df_tabla_ff["total"].map(lambda x: f"${x:,.2f}")
        df_tabla_ff["porcentaje_fmt"] = df_tabla_ff["porcentaje"].map(lambda x: f"{x:.2f}%")

        st.dataframe(
            df_tabla_ff[[col_fin, col_fun, "total_fmt", "porcentaje_fmt"]].rename(
                columns={col_fin: "FINALIDAD", col_fun: "FUNCIÓN / TIPO", "total_fmt": "TOTAL PRESUPUESTADO ($)", "porcentaje_fmt": "% DEL TOTAL"}
            ),
            use_container_width=True, hide_index=True
        )

        rows_html_ff = ""
        for fin, df_g in df_fin_fun.groupby(col_fin):
            t_fin = df_g["total"].sum()
            pct_fin = (t_fin / (tot_general_ff if tot_general_ff > 0 else 1)) * 100

            rows_html_ff += f'<tr style="font-weight: bold; background-color: #f2f2f2;"><td style="text-align: left; padding-left: 8px;">{fin}</td><td style="text-align: right;">${t_fin:,.2f}</td><td style="text-align: center;">{pct_fin:.2f}%</td></tr>'

            for _, r in df_g.iterrows():
                pct_fun = (r["total"] / (tot_general_ff if tot_general_ff > 0 else 1)) * 100
                rows_html_ff += f'<tr><td style="text-align: left; padding-left: 30px;">{r[col_fun]}</td><td style="text-align: right;">${r["total"]:,.2f}</td><td style="text-align: center;">{pct_fun:.2f}%</td></tr>'

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
				<div class="firma-box">Sec. Hacienda</div>
                <div class="firma-box">Intendente</div>
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
# SECCIÓN 14: TOTALES POR OBJETO DEL GASTO
# =====================================================================
elif opcion_menu == "📦 TOTALES POR OBJETO DEL GASTO":
    st.subheader("📦 Consolidado Presupuestario por Objeto del Gasto")

    if df_egr_completo.empty:
        st.info("💡 No hay registros contables cargados para generar el reporte por Objeto del Gasto.")
    else:
        tot_general_obj = df_egr_completo["total"].sum()
        st.metric("💰 TOTAL GENERAL PRESUPUESTO", f"${tot_general_obj:,.2f}")

        df_obj_res = df_egr_completo.groupby("objeto_gasto")["total"].sum().reset_index()
        df_obj_res["porcentaje"] = (df_obj_res["total"] / (tot_general_obj if tot_general_obj > 0 else 1)) * 100

        st.markdown("---")
        st.markdown("##### 📋 Resumen en Pantalla")

        df_obj_pantalla = df_obj_res.copy()
        df_obj_pantalla["total_fmt"] = df_obj_pantalla["total"].map(lambda x: f"${x:,.2f}")
        df_obj_pantalla["porcentaje_fmt"] = df_obj_pantalla["porcentaje"].map(lambda x: f"{x:.2f}%")

        st.dataframe(
            df_obj_pantalla[["objeto_gasto", "total_fmt", "porcentaje_fmt"]].rename(
                columns={"objeto_gasto": "OBJETO DEL GASTO", "total_fmt": "TOTAL PRESUPUESTADO ($)", "porcentaje_fmt": "% DEL TOTAL"}
            ),
            use_container_width=True, hide_index=True
        )

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
                <div class="firma-box">Sec. Hacienda</div>
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
# SECCIÓN 15: MATRIZ SUBSECRETARÍA VS OBJETOS DE GASTO
# =====================================================================
elif opcion_menu == "📊 MATRIZ SUBSECRETARÍA VS OBJETOS":
    st.subheader("📊 Matriz Cruzada: Subsecretarías vs Objetos del Gasto")

    if df_egr_completo.empty:
        st.info("💡 No hay registros contables cargados para generar la matriz cruzada.")
    else:
        matriz_pivot = pd.pivot_table(
            df_egr_completo, values="total", index="subsecretaria", columns="objeto_gasto", aggfunc="sum", fill_value=0.0
        )
        matriz_pivot["TOTAL GENERAL"] = matriz_pivot.sum(axis=1)

        st.markdown("##### 📋 Matriz Cruzada en Pantalla ($)")
        st.dataframe(matriz_pivot.style.format("${:,.2f}"), use_container_width=True)

        cols_objetos = [c for c in matriz_pivot.columns if c != "TOTAL GENERAL"]
        tot_general_matriz = matriz_pivot["TOTAL GENERAL"].sum()

        th_cols_html = "".join([f'<th style="text-align: right; font-size: 9px;">{col}</th>' for col in cols_objetos])

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
                <div class="firma-box">Sec. Hacienda</div>
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
# SECCIÓN 16: PROYECCIÓN Y ESTRUCTURA TEMPORAL
# =====================================================================
elif opcion_menu == "📈 PROYECCIÓN Y ESTRUCTURA TEMPORAL":
    st.subheader("📈 Proyección y Programación de Ejecución Temporal")

    if df_egr_completo.empty:
        st.info("💡 No hay registros contables cargados.")
    else:
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
            df_sec_prog.style.format({"total": "${:,.2f}", "Q1 (25%)": "${:,.2f}", "Q2 (25%)": "${:,.2f}", "Q3 (25%)": "${:,.2f}", "Q4 (25%)": "${:,.2f}"}),
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

        pivot_econ = pd.pivot_table(df_egr_completo, values="total", index="secretaria", columns="clase", aggfunc="sum", fill_value=0.0)
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
        df_sec_techos = df_egr_completo.groupby("secretaria")["total"].sum().reset_index()

        # Cargar techos guardados en disco para que no se borren al reiniciar
        techos_guardados = cargar_techos_disco()

        # Asegurar valores iniciales por defecto si no existen
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
                # 1. Actualizamos el diccionario local
                techos_guardados[sec_a_editar] = nuevo_techo
                guardar_techos_disco(techos_guardados)

                # 2. Sincronizamos con Google Sheets a través del Webhook
                dict_techo = {
                    "secretaria": sec_a_editar,
                    "techo": float(nuevo_techo)
                }
                guardar_fila_gsheet("techos", dict_techo)

                st.success(f"¡Techo guardado permanentemente para {sec_a_editar} y sincronizado en el Sheet!")
                st.rerun()

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
                "SECRETARÍA": sec_nom, "PRESUPUESTO CARGADO ($)": f"${cargado:,.2f}",
                "TECHO PERMITIDO ($)": f"${techo:,.2f}", "DISPONIBLE / DESVÍO ($)": f"${diferencia:,.2f}", "ESTADO": estado
            })

        st.dataframe(pd.DataFrame(filas_techos), use_container_width=True, hide_index=True)
# =====================================================================
# SECCIÓN 19: FICHA TÉCNICA POR DESTINO
# =====================================================================
elif opcion_menu == "📋 FICHA TÉCNICA POR DESTINO":
    st.subheader("📋 Ficha Técnica Ejecutiva por Destino")

    if df_egr_completo.empty:
        st.info("💡 No hay registros contables cargados.")
    else:
        destinos_lista = sorted([d for d in df_egr_completo["destino"].unique() if str(d).strip() != ""])
        destino_f_elegido = st.selectbox("Seleccionar Destino:", destinos_lista)

        df_f_destino = df_egr_completo[df_egr_completo["destino"] == destino_f_elegido]
        tot_f_destino = df_f_destino["total"].sum()

        st.markdown("---")
        st.markdown(f"### 📌 Destino: **{str(destino_f_elegido).upper()}**")
        st.metric("💰 Presupuesto Asignado", f"${tot_f_destino:,.2f}")

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

# =============================================================
# SECCIÓN: COMPARATIVO E HISTÓRICO (CON VISTA PREVIA Y FIRMAS)
# =============================================================
elif opcion_menu == "🔄 COMPARATIVO E HISTÓRICO":
    st.markdown("##### 📈 Reporte Comparativo e Histórico por Destino")

    col_comp1, col_comp2, col_comp3 = st.columns(3)
    with col_comp1:
        anio_base = st.selectbox("Año Base (1):", options=[2026, 2025], key="comp_anio_1")
    with col_comp2:
        anio_comparar = st.selectbox("Año a Comparar (2):", options=[2027, 2026], index=0, key="comp_anio_2")
    with col_comp3:
        metrica_comp = st.selectbox("Métrica a Comparar:", options=["DEVENGADO", "PRESUPUESTO"], key="comp_metrica")

    def limpiar_monto_comp(val):
        if pd.isna(val): return 0.0
        s = str(val).replace("$", "").replace(" ", "").strip()
        if not s or s.lower() == "nan": return 0.0
        if "," in s and "." in s:
            s = s.replace(".", "").replace(",", ".")
        elif "," in s:
            s = s.replace(",", ".")
        try:
            return float(s)
        except:
            return 0.0

    # 1. Cargamos las fuentes diferenciadas por año:
    # - Año 2027 (o futuro): Usa la hoja de Egresos general (df_egr_completo)
    # - Año 2026 (o anterior): Usa la hoja de Ejecución (URL_READ_EJECUCION)
    df_ejecucion_raw = leer_datos_gsheet(URL_READ_EJECUCION)
    if df_ejecucion_raw.empty:
        df_ejecucion_raw = df_egr_completo.copy()

    df_egresos_raw = df_egr_completo.copy()

    if df_ejecucion_raw.empty and df_egresos_raw.empty:
        st.warning("⚠️ No se encontraron registros cargados en el sistema para realizar la comparación.")
        st.stop()

    # Normalizamos columnas de ejecución
    df_ejecucion_raw.columns = [str(c).strip().upper() for c in df_ejecucion_raw.columns]
    cols_ejec = df_ejecucion_raw.columns.tolist()

    # Normalizamos columnas de egresos
    df_egresos_raw.columns = [str(c).strip().upper() for c in df_egresos_raw.columns]
    cols_egr = df_egresos_raw.columns.tolist()

    c_dest_comp = cols_ejec[2] if len(cols_ejec) > 2 else "DESTINO"

    # Definimos qué columna buscar según la métrica elegida ("DEVENGADO" o "PRESUPUESTO")
    # En ejecución/egresos solemos tener Presupuesto en una columna y Devengado en otra.
    # Ajustá los índices [6] y [7] si tus columnas varían, o usa los nombres exactos si los conocés.
    col_presupuesto_ejec = cols_ejec[6] if len(cols_ejec) > 6 else "TOTAL"
    col_devengado_ejec = cols_ejec[7] if len(cols_ejec) > 7 else col_presupuesto_ejec

    col_presupuesto_egr = cols_egr[6] if len(cols_egr) > 6 else "TOTAL"

    # 2. Preparamos un DataFrame unificado por Destino agrupando correctamente cada fuente
    def procesar_fuente_anio(df, col_valor, filtro_valido_idx):
        if df.empty: return pd.DataFrame(columns=["_DEST", "_VAL"])
        
        cols_actuales = df.columns.tolist()
        c_dest_actual = cols_actuales[2] if len(cols_actuales) > 2 else "DESTINO"
        col_filtro = cols_actuales[filtro_valido_idx] if len(cols_actuales) > filtro_valido_idx else cols_actuales[3]

        df_f = df[
            df[col_filtro].notna() & 
            (df[col_filtro].astype(str).str.strip() != "") & 
            (df[col_filtro].astype(str).str.upper() != "NAN")
        ].copy()
        
        df_f["_DEST"] = df_f[c_dest_actual].astype(str).str.strip().str.upper()
        df_f["_VAL"] = df_f[col_valor].apply(limpiar_monto_comp)
        return df_f.groupby("_DEST")["_VAL"].sum().reset_index()

    # --- DATOS PARA EL AÑO BASE (1) ---
    if anio_base == 2027:
        df_base_grouped = procesar_fuente_anio(df_egresos_raw, col_presupuesto_egr, 3)
    else: # 2026 o 2025 (Ejecución)
        col_val_base_col = col_devengado_ejec if metrica_comp == "DEVENGADO" else col_presupuesto_ejec
        df_base_grouped = procesar_fuente_anio(df_ejecucion_raw, col_val_base_col, 3)

    # --- DATOS PARA EL AÑO A COMPARAR (2) ---
    if anio_comparar == 2027:
        df_comp_grouped = procesar_fuente_anio(df_egresos_raw, col_presupuesto_egr, 3)
    else: # 2026
        col_val_comp_col = col_devengado_ejec if metrica_comp == "DEVENGADO" else col_presupuesto_ejec
        df_comp_grouped = procesar_fuente_anio(df_ejecucion_raw, col_val_comp_col, 3)

    # --- DATOS PARA EL AÑO A COMPARAR (2) ---
    if anio_comparar == 2027:
        col_val_comp_col = col_presupuesto_egr if metrica_comp == "PRESUPUESTO" else col_presupuesto_egr
        df_comp_grouped = procesar_fuente_anio(df_egresos_raw, col_val_comp_col, 3)
    else: # 2026
        col_val_comp_col = col_devengado_ejec if metrica_comp == "DEVENGADO" else col_presupuesto_ejec
        df_comp_grouped = procesar_fuente_anio(df_ejecucion_raw, col_val_comp_col, 3)

    # Fusionamos ambos años por Destino para la comparativa final
    df_f_comparativo = pd.merge(df_base_grouped, df_comp_grouped, on="_DEST", how="outer", suffixes=("_1", "_2")).fillna(0.0)
    df_f_comparativo = df_f_comparativo[df_f_comparativo["_DEST"].notna() & (df_f_comparativo["_DEST"] != "NAN") & (df_f_comparativo["_DEST"] != "")]

    total_val_anio1 = df_f_comparativo["_VAL_1"].sum()
    total_val_anio2 = df_f_comparativo["_VAL_2"].sum()
    variacion_global = total_val_anio2 - total_val_anio1
    porcentaje_var = (variacion_global / total_val_anio1 * 100) if total_val_anio1 > 0 else 0.0

    f_plan_comp = []
    rows_html_comp = ""

    destinos_unicos = sorted(df_f_comparativo["_DEST"].dropna().unique())

    for dest in destinos_unicos:
        if not dest or dest == "NAN": continue

        sub_df = df_f_comparativo[df_f_comparativo["_DEST"] == dest]
        val_1 = sub_df["_VAL_1"].values[0] if not sub_df.empty else 0.0
        val_2 = sub_df["_VAL_2"].values[0] if not sub_df.empty else 0.0
        dif = val_2 - val_1

        f_plan_comp.append({
            "DESTINO": f"<b>{dest}</b>",
            f"{metrica_comp} ({anio_base})": f"<b>${val_1:,.2f}</b>",
            f"{metrica_comp} ({anio_comparar})": f"<b>${val_2:,.2f}</b>",
            "DIFERENCIA": f"<b>${dif:,.2f}</b>"
        })

        rows_html_comp += f'<tr style="font-weight: bold; background-color: #f9f9f5;"><td style="text-align: left; padding-left: 5px;">{dest}</td><td style="text-align: right;">${val_1:,.2f}</td><td style="text-align: right;">${val_2:,.2f}</td><td style="text-align: right;">${dif:,.2f}</td></tr>'

    # 1. VISTA PREVIA ESTÉTICA EN LA APP
    st.markdown(f"""
    <div style="border: 1px solid #000; padding: 0px; border-radius: 2px; background-color: #fff; font-family: Arial, sans-serif;">
        <table style="width: 100%; border-collapse: collapse;">
            <tr>
                <td style="width: 25%; font-size: 11px; padding: 15px; border-right: 1px solid #000; text-align: left;"><b>Municipalidad de Sunchales</b><br><span style="font-size: 9px; color: #777;">Comparativo por Destino - {metrica_comp}</span></td>
                <td style="width: 50%; text-align: center; padding: 15px; border-right: 1px solid #000; vertical-align: middle;"><h2 style="margin: 0; font-size: 15px; font-weight: bold;">REPORTE COMPARATIVO POR DESTINO</h2><h4 style="margin: 4px 0 0 0; font-size: 11px; font-weight: normal;">{anio_base} vs {anio_comparar} ({metrica_comp})</h4></td>
                <td style="width: 25%; text-align: center; background-color: #f5f5f5; vertical-align: middle;"><div style="font-size: 11px; font-weight: bold; border-bottom: 1px solid #000; padding: 3px 0;">Variación Global</div><div style="font-size: 14px; font-weight: bold; color: {'#008000' if variacion_global >= 0 else '#cc0000'};">${variacion_global:,.2f} ({porcentaje_var:+.1f}%)</div></td>
            </tr>
        </table>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if f_plan_comp:
        st.write(pd.DataFrame(f_plan_comp).to_html(escape=False, index=False), unsafe_allow_html=True)
    else:
        st.warning("No hay registros para mostrar en la vista comparativa por destino.")

    # HTML estructurado para impresión limpia y descarga
    html_reporte_comparativo = f"""
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
            .tabla-datos th {{ border-bottom: 2px solid #000; padding: 6px 4px; font-weight: bold; background-color: #f2f2f2; text-align: right; }}
            .tabla-datos th:first-child {{ text-align: left !important; padding-left: 8px; }}
            .tabla-datos td {{ border-bottom: 1px solid #e0e0e0; padding: 6px 4px; vertical-align: middle; text-align: right; }}
            .tabla-datos td:first-child {{ text-align: left !important; padding-left: 8px; }}
            .resumen-final {{ border: 2px solid #000; padding: 15px; margin-top: 20px; background-color: #fafafa; text-align: center; font-size: 13px; page-break-inside: avoid; }}
            .firmas-container {{ margin-top: 50px; width: 100%; page-break-inside: avoid; }}
            .firma-box {{ width: 30%; float: left; text-align: center; border-top: 1px solid #000; padding-top: 5px; margin: 0 1.5%; font-size: 11px; font-weight: bold; }}
        </style>
    </head>
    <body onload="window.print();">
        <div class="m-box">
            <table class="t-hdr">
                <tr>
                    <td style="width: 25%; text-align: left; font-size: 10px;"><b>Municipalidad de Sunchales</b><br><span style="font-size: 8px; color: #555;">Comparativo por Destino</span></td>
                    <td style="width: 50%; text-align: center;"><b>REPORTE COMPARATIVO POR DESTINO DE {metrica_comp} ({anio_base} vs {anio_comparar})</b><br><small>- Análisis por Destino -</small></td>
                    <td style="width: 25%;" class="b-tot"><small>Total {anio_comparar}</small><br><b>${total_val_anio2:,.2f}</b></td>
                </tr>
            </table>
        </div>
        <table class="tabla-datos">
            <thead>
                <tr>
                    <th style="text-align: left; padding-left: 8px;">DESTINO</th>
                    <th>{metrica_comp} ({anio_base})</th>
                    <th>{metrica_comp} ({anio_comparar})</th>
                    <th>DIFERENCIA</th>
                </tr>
            </thead>
            <tbody>
                {rows_html_comp}
            </tbody>
        </table>
        <div class="resumen-final">
            <b>TOTALES GENERALES ({metrica_comp}):</b> {anio_base}: ${total_val_anio1:,.2f} &nbsp;|&nbsp; {anio_comparar}: ${total_val_anio2:,.2f} &nbsp;|&nbsp; <b>Variación: ${variacion_global:,.2f} ({porcentaje_var:+.1f}%)</b>
        </div>
        <div class="firmas-container">
            <div class="firma-box">Responsable Presupuesto</div>
            <div class="firma-box">Sec. Hacienda</div>
            <div class="firma-box">Intendente</div>
        </div>
    </body>
    </html>
    """

    st.markdown("<br>", unsafe_allow_html=True)
    st.download_button(
        label=f"📥 Descargar Reporte Comparativo por Destino de {metrica_comp} (HTML/PDF)",
        data=html_reporte_comparativo,
        file_name=f"Comparativo_Destino_{metrica_comp}_{anio_base}_vs_{anio_comparar}_{time.strftime('%Y%m%d')}.html",
        mime="text/html",
        use_container_width=True,
        type="primary"
    )
# =====================================================================
# SECCIÓN 21: REPORTE DE EJECUCIÓN OFICIAL (TODAS LAS SOLAPAS)
# =====================================================================
elif opcion_menu == "📈 REPORTE DE EJECUCIÓN OFICIAL":
    st.subheader("📈 Módulo de Ejecución Presupuestaria - Reportes Oficiales")

    df_ejec_completo = leer_datos_gsheet(URL_READ_EJECUCION)

    if df_ejec_completo.empty:
        st.warning("⚠️ No se pudieron cargar los datos de la hoja de ejecución.")
    else:
        df_ejec_completo.columns = [str(c).strip().upper() for c in df_ejec_completo.columns]
        cols_e = df_ejec_completo.columns.tolist()

        def limpiar_monto_val(val):
            if pd.isna(val): return 0.0
            s = str(val).replace("$", "").replace(" ", "").strip()
            if not s or s.lower() == "nan": return 0.0
            if "," in s and "." in s:
                s = s.replace(".", "").replace(",", ".")
            elif "," in s:
                s = s.replace(",", ".")
            try:
                return float(s)
            except Exception:
                return 0.0

        c_sec_k = cols_e[0] if len(cols_e) > 0 else "SECRETARIA"
        c_sub_k = cols_e[1] if len(cols_e) > 1 else "SUBSECRETARÍA"
        c_dest_k = cols_e[2] if len(cols_e) > 2 else "DESTINO"
        c_obj = cols_e[3] if len(cols_e) > 3 else "OBJETO_GASTO" # Columna D
        c_partida = cols_e[4] if len(cols_e) > 4 else cols_e[5] # Columna E (Imputación)
        c_padre = cols_e[13] if len(cols_e) > 13 else cols_e[4] # Columna N (Cuenta Padre)

        c_pres = cols_e[6] if len(cols_e) > 6 else cols_e[6]
        c_dev = cols_e[7] if len(cols_e) > 7 else cols_e[6]
        c_ejec = cols_e[8] if len(cols_e) > 8 else cols_e[6]
        c_mod = cols_e[9] if len(cols_e) > 9 else cols_e[6]
        c_saldo = cols_e[10] if len(cols_e) > 10 else cols_e[6]

        df_validas = df_ejec_completo[
            df_ejec_completo[c_obj].notna() & 
            (df_ejec_completo[c_obj].astype(str).str.strip() != "") & 
            (df_ejec_completo[c_obj].astype(str).str.upper() != "NAN") &
            df_ejec_completo[c_padre].notna() & 
            (df_ejec_completo[c_padre].astype(str).str.strip() != "") & 
            (df_ejec_completo[c_padre].astype(str).str.upper() != "NAN") &
            df_ejec_completo[c_partida].notna() & 
            (df_ejec_completo[c_partida].astype(str).str.strip() != "") & 
            (df_ejec_completo[c_partida].astype(str).str.upper() != "NAN")
        ].copy()

        tab_ejec_1, tab_ejec_2, tab_ejec_3, tab_ejec_4, tab_ejec_5, tab_ejec_6 = st.tabs([
            "📊 Resumen por Destino (Matriz)",
            "🏛️ Desglose Escalonado por Destino",
            "📦 Totales por Objeto del Gasto",
            "🔍 Buscador y Control de Saldos",
            "📄 Exportación y Firmas (PDF)",
            "🏛️ Reporte por Finalidad y Función"
        ])

        # -------------------------------------------------------------
        # SOLAPA 1: MATRIZ DE DESTINOS VS OBJETOS
        # -------------------------------------------------------------
        with tab_ejec_1:
            st.markdown("##### 📊 Cuadro Resumen: Destinos vs. Objetos del Gasto")
            st.info("💡 Cada fila representa un **Destino** y cada columna un **Objeto del Gasto** con su respectivo total devengado.")

            if not df_validas.empty:
                df_validas["_DEV_NUM"] = df_validas[c_dev].apply(limpiar_monto_val)

                df_pivote = df_validas.pivot_table(
                    index=c_dest_k, 
                    columns=c_obj, 
                    values="_DEV_NUM", 
                    aggfunc="sum", 
                    fill_value=0.0
                ).reset_index()

                cols_obj_piv = [c for c in df_pivote.columns if c != c_dest_k]
                df_pivote_fmt = df_pivote.copy()
                for col in cols_obj_piv:
                    df_pivote_fmt[col] = df_pivote_fmt[col].map(lambda x: f"${x:,.2f}" if x > 0 else "$0.00")

                st.dataframe(df_pivote_fmt, use_container_width=True, hide_index=True)

                tot_matriz_gral = df_validas["_DEV_NUM"].sum()
                rows_matriz_html = ""
                for _, rw in df_pivote.iterrows():
                    dest_n = rw[c_dest_k]
                    rows_matriz_html += f'<tr><td style="text-align: left; padding-left: 8px; font-weight: bold;">{dest_n}</td>'
                    for c_o in cols_obj_piv:
                        val_c = rw[c_o]
                        rows_matriz_html += f'<td style="text-align: right;">${val_c:,.2f}</td>'
                    rows_matriz_html += '</tr>'

                headers_matriz_th = "".join([f'<th style="text-align: right;">{col}</th>' for col in cols_obj_piv])

                html_matriz_reporte = f"""
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
                        .tabla-datos {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 10px; margin-bottom: 25px; }}
                        .tabla-datos th {{ border-bottom: 2px solid #000; padding: 6px 4px; font-weight: bold; background-color: #f2f2f2; }}
                        .tabla-datos td {{ border-bottom: 1px solid #e0e0e0; padding: 6px 4px; vertical-align: middle; }}
                        .resumen-final {{ border: 2px solid #000; padding: 15px; margin-top: 20px; background-color: #fafafa; text-align: center; font-size: 14px; page-break-inside: avoid; }}
                        .firmas-container {{ margin-top: 50px; width: 100%; page-break-inside: avoid; }}
                        .firma-box {{ width: 30%; float: left; text-align: center; border-top: 1px solid #000; padding-top: 5px; margin: 0 1.5%; font-size: 11px; font-weight: bold; }}
                    </style>
                </head>
                <body onload="window.print();">
                    <div class="m-box">
                        <table class="t-hdr">
                            <tr>
                                <td style="width: 25%; text-align: left; font-size: 10px;"><b>Municipalidad de Sunchales</b><br><span style="font-size: 8px; color: #555;">Ejecución de Egresos - Año 2026</span></td>
                                <td style="width: 50%; text-align: center;"><b>MATRIZ RESUMEN: DESTINOS VS OBJETOS</b><br><small>- Control Financiero -</small></td>
                                <td style="width: 25%;" class="b-tot"><small>Total General</small><br><b>${tot_matriz_gral:,.2f}</b></td>
                            </tr>
                        </table>
                    </div>
                    <table class="tabla-datos">
                        <thead>
                            <tr>
                                <th style="text-align: left; padding-left: 8px;">DESTINO</th>
                                {headers_matriz_th}
                            </tr>
                        </thead>
                        <tbody>
                            {rows_matriz_html}
                        </tbody>
                    </table>
                    <div class="resumen-final">
                        <b>TOTAL GENERAL DEVENGADO MUNICIPAL:</b> ${tot_matriz_gral:,.2f}
                    </div>
                    <div class="firmas-container">
                        <div class="firma-box">Responsable Presupuesto</div>
                        <div class="firma-box">Sec. Hacienda</div>
                        <div class="firma-box">Intendente</div>
                    </div>
                </body>
                </html>
                """

                st.download_button(
                    label="📥 Descargar Matriz Resumen Oficial (PDF/HTML)",
                    data=html_matriz_reporte,
                    file_name=f"Matriz_Resumen_Destinos_{time.strftime('%Y%m%d')}.html",
                    mime="text/html",
                    use_container_width=True
                )
            else:
                st.warning("⚠️ No hay datos suficientes para generar la matriz.")

        # -------------------------------------------------------------
        # SOLAPA 2: DESGLOSE ESCALONADO POR DESTINO
        # -------------------------------------------------------------
        with tab_ejec_2:
            st.markdown("##### 🏛️ Desglose Escalonado por Destino")
            cf1, cf2, col_f3 = st.columns(3)
            sec_ops = sorted([str(x) for x in df_validas[c_sec_k].unique() if str(x).strip() != ""])

            with cf1:
                sec_s_ejec = st.selectbox("1. SECRETARÍA:", options=[""] + sec_ops, key="ejec_of_sec")

            df_ejec_f1 = df_validas[df_validas[c_sec_k].astype(str).str.strip().str.upper() == sec_s_ejec.strip().upper()] if sec_s_ejec else pd.DataFrame()
            sub_ops = sorted([str(x) for x in df_ejec_f1[c_sub_k].unique() if str(x).strip() != ""]) if not df_ejec_f1.empty else []

            with cf2:
                sub_s_ejec = st.selectbox("2. SUBSECRETARÍA:", options=[""] + sub_ops, key="ejec_of_sub")

            with col_f3:
                if sec_s_ejec and sub_s_ejec:
                    df_ejec_f2 = df_ejec_f1[df_ejec_f1[c_sub_k].astype(str).str.strip().str.upper() == sub_s_ejec.strip().upper()]
                    dest_ops = sorted([str(x) for x in df_ejec_f2[c_dest_k].unique() if str(x).strip() != ""])
                    dest_s_ejec = st.selectbox("3. DESTINO:", options=[""] + dest_ops, key="ejec_of_dest")
                else:
                    dest_s_ejec = st.selectbox("3. DESTINO:", options=[""], key="ejec_of_dest")

            if sec_s_ejec and sub_s_ejec and dest_s_ejec:
                df_f_oficial_ejec = df_ejec_f2[df_ejec_f2[c_dest_k].astype(str).str.strip().str.upper() == dest_s_ejec.strip().upper()].copy()

                df_f_oficial_ejec["_G_VAL"] = df_f_oficial_ejec[c_pres].apply(limpiar_monto_val)
                df_f_oficial_ejec["_H_VAL"] = df_f_oficial_ejec[c_dev].apply(limpiar_monto_val)
                df_f_oficial_ejec["_I_VAL"] = df_f_oficial_ejec[c_ejec].apply(limpiar_monto_val)
                df_f_oficial_ejec["_J_VAL"] = df_f_oficial_ejec[c_mod].apply(limpiar_monto_val)
                df_f_oficial_ejec["_K_VAL"] = df_f_oficial_ejec[c_saldo].apply(limpiar_monto_val)

                tot_devengado_val = df_f_oficial_ejec["_H_VAL"].sum()

                f_plan_ejec = []
                rows_html_esc = ""
                for obj, df_obj in df_f_oficial_ejec.groupby(c_obj):
                    tp_g = df_obj["_G_VAL"].sum()
                    tp_h = df_obj["_H_VAL"].sum()
                    tp_i = df_obj["_I_VAL"].sum()
                    tp_j = df_obj["_J_VAL"].sum()
                    tp_k = df_obj["_K_VAL"].sum()

                    f_plan_ejec.append({
                        "OBJETO / CUENTA / IMPUTACIÓN": f"<b>{obj}</b>",
                        "PRESUPUESTO": f"<b>${tp_g:,.2f}</b>",
                        "DEVENGADO": f"<b>${tp_h:,.2f}</b>",
                        "EJECUTADO": f"<b>${tp_i:,.2f}</b>",
                        "MODIFICACIONES": f"<b>${tp_j:,.2f}</b>",
                        "SALDO": f"<b>${tp_k:,.2f}</b>"
                    })
                    rows_html_esc += f'<tr style="font-weight: bold; background-color: #f9f9f5;"><td style="text-align: left; padding-left: 5px;">{obj}</td><td style="text-align: right;">${tp_g:,.2f}</td><td style="text-align: right;">${tp_h:,.2f}</td><td style="text-align: right;">${tp_i:,.2f}</td><td style="text-align: right;">${tp_j:,.2f}</td><td style="text-align: right;">${tp_k:,.2f}</td></tr>'

                    for pad, df_pad in df_obj.groupby(c_padre):
                        pad_g = df_pad["_G_VAL"].sum()
                        pad_h = df_pad["_H_VAL"].sum()
                        pad_i = df_pad["_I_VAL"].sum()
                        pad_j = df_pad["_J_VAL"].sum()
                        pad_k = df_pad["_K_VAL"].sum()

                        f_plan_ejec.append({
                            "OBJETO / CUENTA / IMPUTACIÓN": f"&nbsp;&nbsp;&nbsp;&nbsp;<b>{pad}</b>",
                            "PRESUPUESTO": f"<b>${pad_g:,.2f}</b>",
                            "DEVENGADO": f"<b>${pad_h:,.2f}</b>",
                            "EJECUTADO": f"<b>${pad_i:,.2f}</b>",
                            "MODIFICACIONES": f"<b>${pad_j:,.2f}</b>",
                            "SALDO": f"<b>${pad_k:,.2f}</b>"
                        })
                        rows_html_esc += f'<tr style="font-weight: bold;"><td style="text-align: left; padding-left: 20px;">{pad}</td><td style="text-align: right;">${pad_g:,.2f}</td><td style="text-align: right;">${pad_h:,.2f}</td><td style="text-align: right;">${pad_i:,.2f}</td><td style="text-align: right;">${pad_j:,.2f}</td><td style="text-align: right;">${pad_k:,.2f}</td></tr>'

                        for _, r in df_pad.iterrows():
                            vg = limpiar_monto_val(r.get(c_pres, 0))
                            vh = limpiar_monto_val(r.get(c_dev, 0))
                            vi = limpiar_monto_val(r.get(c_ejec, 0))
                            vj = limpiar_monto_val(r.get(c_mod, 0))
                            vk = limpiar_monto_val(r.get(c_saldo, 0))
                            partida_val = str(r.get(c_partida, ""))

                            f_plan_ejec.append({
                                "OBJETO / CUENTA / IMPUTACIÓN": f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{partida_val}",
                                "PRESUPUESTO": f"${vg:,.2f}",
                                "DEVENGADO": f"${vh:,.2f}",
                                "EJECUTADO": f"${vi:,.2f}",
                                "MODIFICACIONES": f"${vj:,.2f}",
                                "SALDO": f"${vk:,.2f}"
                            })
                            rows_html_esc += f'<tr><td style="text-align: left; padding-left: 40px;">{partida_val}</td><td style="text-align: right;">${vg:,.2f}</td><td style="text-align: right;">${vh:,.2f}</td><td style="text-align: right;">${vi:,.2f}</td><td style="text-align: right;">${vj:,.2f}</td><td style="text-align: right;">${vk:,.2f}</td></tr>'

                # Vista Previa Estética en la App
                st.markdown(f"""
                <div style="border: 1px solid #000; padding: 0px; border-radius: 2px; background-color: #fff; font-family: Arial, sans-serif;">
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="width: 25%; font-size: 11px; padding: 15px; border-right: 1px solid #000; text-align: left;"><b>Municipalidad de Sunchales</b><br><span style="font-size: 9px; color: #777;">Ejecución de Egresos - Año 2026</span></td>
                            <td style="width: 50%; text-align: center; padding: 15px; border-right: 1px solid #000; vertical-align: middle;"><h2 style="margin: 0; font-size: 16px; font-weight: bold;">REPORTE DE EJECUCIÓN POR DESTINO</h2><h4 style="margin: 4px 0 0 0; font-size: 12px; font-weight: normal;">- Desglose Escalonado -</h4></td>
                            <td style="width: 25%; text-align: center; background-color: #f5f5f5; vertical-align: middle;"><div style="font-size: 12px; font-weight: bold; border-bottom: 1px solid #000; padding: 4px 0;">Total Devengado</div><div style="font-size: 16px; font-weight: bold;">${tot_devengado_val:,.2f}</div></td>
                        </tr>
                    </table>
                    <div style="border-top: 1px solid #000; font-size: 11px; padding: 6px 10px;">
                        <b>SECRETARÍA:</b> {sec_s_ejec} | <b>SUBSECRETARÍA:</b> {sub_s_ejec} | <span style="float: right;"><b>DESTINO:</b> {str(dest_s_ejec).upper()}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)
                st.write(pd.DataFrame(f_plan_ejec).to_html(escape=False, index=False), unsafe_allow_html=True)

                # HTML para impresión limpia sin letras de columnas
                html_reporte_escalonado = f"""
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
                        .tabla-datos th {{ border-bottom: 2px solid #000; padding: 6px 4px; font-weight: bold; background-color: #f2f2f2; text-align: right; }}
                        .tabla-datos th:first-child {{ text-align: left !important; padding-left: 8px; }}
                        .tabla-datos td {{ border-bottom: 1px solid #e0e0e0; padding: 6px 4px; vertical-align: middle; text-align: right; }}
                        .tabla-datos td:first-child {{ text-align: left !important; padding-left: 8px; }}
                        .resumen-final {{ border: 2px solid #000; padding: 15px; margin-top: 20px; background-color: #fafafa; text-align: center; font-size: 14px; page-break-inside: avoid; }}
                        .firmas-container {{ margin-top: 50px; width: 100%; page-break-inside: avoid; }}
                        .firma-box {{ width: 30%; float: left; text-align: center; border-top: 1px solid #000; padding-top: 5px; margin: 0 1.5%; font-size: 11px; font-weight: bold; }}
                    </style>
                </head>
                <body onload="window.print();">
                    <div class="m-box">
                        <table class="t-hdr">
                            <tr>
                                <td style="width: 25%; text-align: left; font-size: 10px;"><b>Municipalidad de Sunchales</b><br><span style="font-size: 8px; color: #555;">Ejecución de Egresos - Año 2026</span></td>
                                <td style="width: 50%; text-align: center;"><b>REPORTE DE EJECUCIÓN POR DESTINO (ESCALONADO)</b><br><small>- Control Financiero -</small></td>
                                <td style="width: 25%;" class="b-tot"><small>Total Devengado</small><br><b>${tot_devengado_val:,.2f}</b></td>
                            </tr>
                        </table>
                        <div style="border-top: 1px solid #000; font-size: 11px; padding-top: 6px; margin-top: 6px;">
                            <b>SECRETARÍA:</b> {sec_s_ejec} | <b>SUBSECRETARÍA:</b> {sub_s_ejec} | <span style="float: right;"><b>DESTINO:</b> {str(dest_s_ejec).upper()}</span>
                        </div>
                    </div>
                    <table class="tabla-datos">
                        <thead>
                            <tr>
                                <th style="text-align: left; padding-left: 8px;">OBJETO / CUENTA / IMPUTACIÓN</th>
                                <th>PRESUPUESTO</th>
                                <th>DEVENGADO</th>
                                <th>EJECUTADO</th>
                                <th>MODIFICACIONES</th>
                                <th>SALDO</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows_html_esc}
                        </tbody>
                    </table>
                    <div class="resumen-final">
                        <b>TOTAL DEVENGADO DESTINO ({str(dest_s_ejec).upper()}):</b> ${tot_devengado_val:,.2f}
                    </div>
                    <div class="firmas-container">
                        <div class="firma-box">Responsable Presupuesto</div>
                        <div class="firma-box">Sec. Hacienda</div>
                        <div class="firma-box">Intendente</div>
                    </div>
                </body>
                </html>
                """

                st.markdown("<br>", unsafe_allow_html=True)
                st.download_button(
                    label="📥 Descargar Reporte Escalonado Oficial por Destino (HTML/PDF)",
                    data=html_reporte_escalonado,
                    file_name=f"Desglose_Escalonado_{str(dest_s_ejec).replace(' ', '_')}_{time.strftime('%Y%m%d')}.html",
                    mime="text/html",
                    use_container_width=True,
                    type="primary"
                )
            else:
                st.info("💡 Seleccioná Secretaría, Subsecretaría y Destino arriba para desplegar el reporte.")
        # -------------------------------------------------------------
        # SOLAPA 3: TOTALES POR OBJETO DEL GASTO
        # -------------------------------------------------------------
        with tab_ejec_3:
            st.markdown("##### 📦 Consolidado de Egresos por Objeto del Gasto")
            df_validas["_H_VAL"] = df_validas[c_dev].apply(limpiar_monto_val)
            df_obj_res = df_validas.groupby(c_obj)["_H_VAL"].sum().reset_index()
            df_obj_res.columns = ["OBJETO DEL GASTO", "DEVENGADO ($)"]
            df_obj_res["DEVENGADO ($)"] = df_obj_res["DEVENGADO ($)"].map(lambda x: f"${x:,.2f}")
            st.dataframe(df_obj_res, use_container_width=True, hide_index=True)

        # -------------------------------------------------------------
        # SOLAPA 4: BUSCADOR GENERAL DE EGRESOS
        # -------------------------------------------------------------
        with tab_ejec_4:
            st.markdown("##### 🔍 Buscador General de Egresos")
            q_ejec = st.text_input("Buscar texto o partida:", key="busq_ejec_s3").strip()
            if q_ejec:
                mask_q = df_validas.astype(str).apply(lambda r: r.str.lower().str.contains(q_ejec.lower()).any(), axis=1)
                st.dataframe(df_validas[mask_q], use_container_width=True, hide_index=True)
            else:
                st.info("Escribí un criterio para buscar.")

        # -------------------------------------------------------------
        # SOLAPA 5: EXPORTACIÓN OFICIAL Y FIRMAS (CONSOLIDADO)
        # -------------------------------------------------------------
        with tab_ejec_5:
            st.markdown("##### 📄 Exportación Oficial Consolidada de Egresos")
            st.info("💡 Hacé clic abajo para descargar el reporte oficial completo con sus columnas financieras y firmas.")

            bloques_ejec_html = ""
            total_general_devengado = 0.0

            for (s_exp, sub_e, d_exp), df_g_exp in df_validas.groupby([c_sec_k, c_sub_k, c_dest_k]):
                rows_html_exp = ""
                tot_dev_dest = 0.0

                for obj, df_obj in df_g_exp.groupby(c_obj):
                    tp_g = sum(limpiar_monto_val(r.get(c_pres, 0)) for _, r in df_obj.iterrows())
                    tp_h = sum(limpiar_monto_val(r.get(c_dev, 0)) for _, r in df_obj.iterrows())
                    tp_i = sum(limpiar_monto_val(r.get(c_ejec, 0)) for _, r in df_obj.iterrows())
                    tp_j = sum(limpiar_monto_val(r.get(c_mod, 0)) for _, r in df_obj.iterrows())
                    tp_k = sum(limpiar_monto_val(r.get(c_saldo, 0)) for _, r in df_obj.iterrows())
                    tot_dev_dest += tp_h

                    rows_html_exp += f'<tr style="font-weight: bold; background-color: #f9f9f5;"><td style="text-align: left; padding-left: 5px;">{obj}</td><td style="text-align: right;">${tp_g:,.2f}</td><td style="text-align: right;">${tp_h:,.2f}</td><td style="text-align: right;">${tp_i:,.2f}</td><td style="text-align: right;">${tp_j:,.2f}</td><td style="text-align: right;">${tp_k:,.2f}</td></tr>'

                    for pad, df_pad in df_obj.groupby(c_padre):
                        pad_g = sum(limpiar_monto_val(r.get(c_pres, 0)) for _, r in df_pad.iterrows())
                        pad_h = sum(limpiar_monto_val(r.get(c_dev, 0)) for _, r in df_pad.iterrows())
                        pad_i = sum(limpiar_monto_val(r.get(c_ejec, 0)) for _, r in df_pad.iterrows())
                        pad_j = sum(limpiar_monto_val(r.get(c_mod, 0)) for _, r in df_pad.iterrows())
                        pad_k = sum(limpiar_monto_val(r.get(c_saldo, 0)) for _, r in df_pad.iterrows())

                        rows_html_exp += f'<tr style="font-weight: bold;"><td style="text-align: left; padding-left: 20px;">{pad}</td><td style="text-align: right;">${pad_g:,.2f}</td><td style="text-align: right;">${pad_h:,.2f}</td><td style="text-align: right;">${pad_i:,.2f}</td><td style="text-align: right;">${pad_j:,.2f}</td><td style="text-align: right;">${pad_k:,.2f}</td></tr>'

                        for _, rw in df_pad.iterrows():
                            vg = limpiar_monto_val(rw.get(c_pres, 0))
                            vh = limpiar_monto_val(rw.get(c_dev, 0))
                            vi = limpiar_monto_val(rw.get(c_ejec, 0))
                            vj = limpiar_monto_val(rw.get(c_mod, 0))
                            vk = limpiar_monto_val(rw.get(c_saldo, 0))
                            partida_txt = str(rw.get(c_partida, ""))

                            rows_html_exp += f'<tr><td style="text-align: left; padding-left: 40px;">{partida_txt}</td><td style="text-align: right;">${vg:,.2f}</td><td style="text-align: right;">${vh:,.2f}</td><td style="text-align: right;">${vi:,.2f}</td><td style="text-align: right;">${vj:,.2f}</td><td style="text-align: right;">${vk:,.2f}</td></tr>'

                total_general_devengado += tot_dev_dest

                bloques_ejec_html += f"""
                <div class="bloque-destino">
                    <div class="m-box">
                        <table class="t-hdr">
                            <tr>
                                <td style="width: 25%; text-align: left; font-size: 10px;"><b>Municipalidad de Sunchales</b><br><span style="font-size: 8px; color: #555;">Ejecución de Egresos - Año 2026</span></td>
                                <td style="width: 50%; text-align: center;"><b>REPORTE OFICIAL DE EJECUCIÓN</b><br><small>- Egresos -</small></td>
                                <td style="width: 25%;" class="b-tot"><small>Total Devengado</small><br><b>${tot_dev_dest:,.2f}</b></td>
                            </tr>
                        </table>
                        <div style="border-top: 1px solid #000; font-size: 11px; padding-top: 6px; margin-top: 6px;">
                            <b>SECRETARÍA:</b> {s_exp} | <b>SUBSECRETARÍA:</b> {sub_e} | <span style="float: right;"><b>DESTINO:</b> {str(d_exp).upper()}</span>
                        </div>
                    </div>
                    <table class="tabla-datos">
                        <thead>
                            <tr>
                                <th style="text-align: left; padding-left: 8px;">OBJETO / CUENTA / IMPUTACIÓN</th>
                                <th style="text-align: right;">PRESUPUESTO</th>
                                <th style="text-align: right;">DEVENGADO</th>
                                <th style="text-align: right;">EJECUTADO</th>
                                <th style="text-align: right;">MODIFICACIONES</th>
                                <th style="text-align: right;">SALDO</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows_html_exp}
                        </tbody>
                    </table>
                    <div class="salto-pagina"></div>
                </div>
                """

            html_completo_ejec_oficial = f"""
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
                {bloques_ejec_html}
                <div class="resumen-final">
                    <b>TOTAL GENERAL DEVENGADO MUNICIPAL:</b> ${total_general_devengado:,.2f}
                </div>
                <div class="firmas-container">
                    <div class="firma-box">Responsable Presupuesto</div>
                    <div class="firma-box">Sec. Hacienda</div>
                    <div class="firma-box">Intendente</div>
                </div>
            </body>
            </html>
            """

            st.download_button(
                label="📥 Descargar Reporte Oficial Consolidado (HTML/PDF)",
                data=html_completo_ejec_oficial,
                file_name=f"Reporte_Ejecucion_Consolidado_{time.strftime('%Y%m%d')}.html",
                mime="text/html",
                use_container_width=True,
                type="primary"
            )

        # -------------------------------------------------------------
        # SOLAPA 6: REPORTE POR FINALIDAD Y FUNCIÓN (CON IMPRESIÓN)
        # -------------------------------------------------------------
        with tab_ejec_6:
            st.markdown("##### 🏛️ Reporte Consolidado por Finalidad y Función")
            st.info("💡 Este reporte agrupa la ejecución de egresos según la finalidad y función presupuestaria, con opción de descarga e impresión formal.")

            if not df_validas.empty and "FINALIDAD" in [c.upper() for c in df_validas.columns] or any("FINALIDAD" in c for c in df_validas.columns):
                col_fin_detectada = [c for c in df_validas.columns if "FINALIDAD" in c.upper()][0]

                df_validas["_DEV_NUM"] = df_validas[c_dev].apply(limpiar_monto_val)
                df_validas["_PRES_NUM"] = df_validas[c_pres].apply(limpiar_monto_val)
                df_validas["_EJEC_NUM"] = df_validas[c_ejec].apply(limpiar_monto_val)
                df_validas["_MOD_NUM"] = df_validas[c_mod].apply(limpiar_monto_val)
                df_validas["_SALDO_NUM"] = df_validas[c_saldo].apply(limpiar_monto_val)

                df_fin_res = df_validas.groupby(col_fin_detectada).agg({
                    "_PRES_NUM": "sum",
                    "_DEV_NUM": "sum",
                    "_EJEC_NUM": "sum",
                    "_MOD_NUM": "sum",
                    "_SALDO_NUM": "sum"
                }).reset_index()

                df_fin_res.columns = ["FINALIDAD / FUNCIÓN", "PRESUPUESTO", "DEVENGADO", "EJECUTADO", "MODIFICACIONES", "SALDO"]

                df_fin_vista = df_fin_res.copy()
                for c_m in ["PRESUPUESTO", "DEVENGADO", "EJECUTADO", "MODIFICACIONES", "SALDO"]:
                    df_fin_vista[c_m] = df_fin_vista[c_m].map(lambda x: f"${x:,.2f}")

                st.dataframe(df_fin_vista, use_container_width=True, hide_index=True)

                tot_gral_fin = df_fin_res["DEVENGADO"].sum()
                rows_fin_html = ""
                for _, r_f in df_fin_res.iterrows():
                    rows_fin_html += f"""
                    <tr>
                        <td style="text-align: left; padding-left: 8px; font-weight: bold;">{r_f['FINALIDAD / FUNCIÓN']}</td>
                        <td style="text-align: right;">${r_f['PRESUPUESTO']:,.2f}</td>
                        <td style="text-align: right;">${r_f['DEVENGADO']:,.2f}</td>
                        <td style="text-align: right;">${r_f['EJECUTADO']:,.2f}</td>
                        <td style="text-align: right;">${r_f['MODIFICACIONES']:,.2f}</td>
                        <td style="text-align: right;">${r_f['SALDO']:,.2f}</td>
                    </tr>
                    """

                html_reporte_fin = f"""
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
                        .tabla-datos th {{ border-bottom: 2px solid #000; padding: 6px 4px; font-weight: bold; background-color: #f2f2f2; }}
                        .tabla-datos td {{ border-bottom: 1px solid #e0e0e0; padding: 6px 4px; vertical-align: middle; }}
                        .resumen-final {{ border: 2px solid #000; padding: 15px; margin-top: 20px; background-color: #fafafa; text-align: center; font-size: 14px; page-break-inside: avoid; }}
                        .firmas-container {{ margin-top: 50px; width: 100%; page-break-inside: avoid; }}
                        .firma-box {{ width: 30%; float: left; text-align: center; border-top: 1px solid #000; padding-top: 5px; margin: 0 1.5%; font-size: 11px; font-weight: bold; }}
                    </style>
                </head>
                <body onload="window.print();">
                    <div class="m-box">
                        <table class="t-hdr">
                            <tr>
                                <td style="width: 25%; text-align: left; font-size: 10px;"><b>Municipalidad de Sunchales</b><br><span style="font-size: 8px; color: #555;">Ejecución de Egresos - Año 2026</span></td>
                                <td style="width: 50%; text-align: center;"><b>REPORTE OFICIAL POR FINALIDAD Y FUNCIÓN</b><br><small>- Control Financiero -</small></td>
                                <td style="width: 25%;" class="b-tot"><small>Total Devengado</small><br><b>${tot_gral_fin:,.2f}</b></td>
                            </tr>
                        </table>
                    </div>
                    <table class="tabla-datos">
                        <thead>
                            <tr>
                                <th style="text-align: left; padding-left: 8px;">FINALIDAD / FUNCIÓN</th>
                                <th style="text-align: right;">PRESUPUESTO</th>
                                <th style="text-align: right;">DEVENGADO</th>
                                <th style="text-align: right;">EJECUTADO</th>
                                <th style="text-align: right;">MODIFICACIONES</th>
                                <th style="text-align: right;">SALDO</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows_fin_html}
                        </tbody>
                    </table>
                    <div class="resumen-final">
                        <b>TOTAL GENERAL DEVENGADO MUNICIPAL:</b> ${tot_gral_fin:,.2f}
                    </div>
                    <div class="firmas-container">
                        <div class="firma-box">Responsable Presupuesto</div>
                        <div class="firma-box">Sec. Hacienda</div>
                        <div class="firma-box">Intendente</div>
                    </div>
                </body>
                </html>
                """

                st.download_button(
                    label="📥 Descargar Reporte Oficial por Finalidad (PDF/HTML)",
                    data=html_reporte_fin,
                    file_name=f"Reporte_Finalidad_Funcion_{time.strftime('%Y%m%d')}.html",
                    mime="text/html",
                    use_container_width=True
                )
            else:
                st.warning("⚠️ No se encontró la columna de finalidad en la planilla.")
