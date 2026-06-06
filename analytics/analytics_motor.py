import pandas as pd
import numpy as np
import os

# =====================================================================
# 🏙️ ECOMIT-ANALYTICS - MOTOR DE ANALÍTICA URBANA PARA TLALPAN, CDMX
# =====================================================================
# Sistema de Inteligencia Artificial para Movilidad Segura
# Integra: Riesgo Vial (C5) + Seguridad Pública (Delitos) + Afluencia (RTP/Eléctricos)
# Desarrollado por: Equipo IBM - Científicos de Datos Urbanos
# =====================================================================


# =====================================================================
# 📂 1. CARGA DIRECTA DE DATASETS YA LIMPIOS (INCLUYE DELITOS)
# =====================================================================
def cargar_datasets_limpios(path_c5_limpio, path_rtp_limpio, path_electricos_limpio, path_delitos_limpio):
    """
    Carga de forma directa los 4 archivos CSV previamente procesados y limpios.
    Garantiza que el sistema funcione fluidamente o use respaldos en caso de error.
    
    Parámetros:
        path_c5_limpio (str): Ruta al archivo de incidentes viales C5
        path_rtp_limpio (str): Ruta al archivo de afluencia RTP
        path_electricos_limpio (str): Ruta al archivo de afluencia transportes eléctricos
        path_delitos_limpio (str): Ruta al archivo de delitos (NUEVO)
    
    Retorna:
        tuple: (df_c5, df_rtp, df_elec, df_delitos) - 4 DataFrames
    """
    print("🔄 Cargando datasets optimizados desde el almacenamiento...")
    
    # Carga de Riesgo Vial (C5)
    if os.path.exists(path_c5_limpio):
        df_c5 = pd.read_csv(path_c5_limpio)
        print(f"✅ C5 cargado: {len(df_c5)} registros de incidentes viales")
    else:
        print(f"⚠️ Alerta: No se encontró {path_c5_limpio}. Se inicializa vacío.")
        df_c5 = pd.DataFrame()
        
    # Carga de Afluencia Diaria RTP
    if os.path.exists(path_rtp_limpio):
        df_rtp = pd.read_csv(path_rtp_limpio)
        print(f"✅ RTP cargado: {len(df_rtp)} registros de afluencia")
    else:
        print(f"⚠️ Alerta: No se encontró {path_rtp_limpio}. Se inicializa vacío.")
        df_rtp = pd.DataFrame()
        
    # Carga de Afluencia Diaria Transportes Eléctricos
    if os.path.exists(path_electricos_limpio):
        df_elec = pd.read_csv(path_electricos_limpio)
        print(f"✅ Eléctricos cargado: {len(df_elec)} registros de afluencia")
    else:
        print(f"⚠️ Alerta: No se encontró {path_electricos_limpio}. Se inicializa vacío.")
        df_elec = pd.DataFrame()
    
    # Carga de Delitos (NUEVO - Seguridad Pública)
    if os.path.exists(path_delitos_limpio):
        df_delitos = pd.read_csv(path_delitos_limpio)
        print(f"✅ Delitos cargado: {len(df_delitos)} registros de seguridad pública")
    else:
        print(f"⚠️ Alerta: No se encontró {path_delitos_limpio}. Se inicializa vacío.")
        df_delitos = pd.DataFrame()
        
    return df_c5, df_rtp, df_elec, df_delitos


# =====================================================================
# 📊 2. GENERACIÓN DE MATRICES PREDICTIVAS (CRUCE ESPACIO-TEMPORAL)
# =====================================================================
def construir_matrices_predictivas(df_c5, df_rtp, df_elec, df_delitos):
    """
    Construye los modelos analíticos de probabilidad con resolución geoespacial.
    
    MATRICES GENERADAS:
    1. Matriz de Riesgo Vial (C5): Indexada por (lat_anon, lon_anon, dia_semana, hora)
    2. Matriz de Delitos: Indexada por (lat_anon, lon_anon, dia_semana, hora)
    3. Matriz de Saturación Diaria (RTP/Eléctricos): Indexada por (mes, dia)
    
    Las coordenadas lat_anon y lon_anon YA VIENEN PRE-ANONIMIZADAS desde los scripts de limpieza.
    
    Parámetros:
        df_c5 (DataFrame): Incidentes viales con columnas [lat_anon, lon_anon, dia_semana, hora]
        df_rtp (DataFrame): Afluencia RTP con columnas [mes_numerico, dia, afluencia]
        df_elec (DataFrame): Afluencia eléctricos con columnas [mes_numerico, dia, afluencia]
        df_delitos (DataFrame): Delitos con columnas [lat_anon, lon_anon, dia_semana, hora]
    
    Retorna:
        tuple: (matriz_vial, matriz_delitos, matriz_saturacion_diaria)
    """
    matriz_vial = {}
    matriz_delitos = {}
    matriz_saturacion_diaria = {}
    
    # 1. MATRIZ DE RIESGO VIAL PREDICTIVO (C5) - Resolución Espacio-Temporal
    # Agrupa por la tupla exacta: (lat_anon, lon_anon, dia_semana, hora)
    if not df_c5.empty and all(col in df_c5.columns for col in ['lat_anon', 'lon_anon', 'dia_semana', 'hora']):
        matriz_vial = df_c5.groupby(['lat_anon', 'lon_anon', 'dia_semana', 'hora']).size().to_dict()
        print(f"📍 Matriz Vial construida: {len(matriz_vial)} puntos espacio-temporales únicos")
    else:
        print("⚠️ Matriz Vial vacía: Faltan columnas [lat_anon, lon_anon, dia_semana, hora] en C5")
    
    # 2. MATRIZ DE DELITOS (SEGURIDAD PÚBLICA) - Resolución Espacio-Temporal
    # Agrupa por la tupla exacta: (lat_anon, lon_anon, dia_semana, hora)
    if not df_delitos.empty and all(col in df_delitos.columns for col in ['lat_anon', 'lon_anon', 'dia_semana', 'hora']):
        matriz_delitos = df_delitos.groupby(['lat_anon', 'lon_anon', 'dia_semana', 'hora']).size().to_dict()
        print(f"🚨 Matriz Delitos construida: {len(matriz_delitos)} puntos espacio-temporales únicos")
    else:
        print("⚠️ Matriz Delitos vacía: Faltan columnas [lat_anon, lon_anon, dia_semana, hora] en Delitos")
        
    # 3. MATRIZ DE INFERENCIA DE SATURACIÓN DIARIA (RTP + Eléctricos unificados)
    # Agrupa por el par estructural de calendario: (mes, dia)
    lista_dfs = []
    
    # Validamos y estandarizamos columnas del CSV limpio de RTP
    if not df_rtp.empty and all(col in df_rtp.columns for col in ['dia', 'mes_numerico', 'afluencia']):
        lista_dfs.append(df_rtp[['mes_numerico', 'dia', 'afluencia']])
        
    # Validamos y estandarizamos columnas del CSV limpio de Eléctricos
    if not df_elec.empty and all(col in df_elec.columns for col in ['dia', 'mes_numerico', 'afluencia']):
        lista_dfs.append(df_elec[['mes_numerico', 'dia', 'afluencia']])
        
    if lista_dfs:
        df_unificado = pd.concat(lista_dfs, ignore_index=True)
        # Obtenemos el promedio histórico diario exacto para cada día del mes
        matriz_saturacion_diaria = df_unificado.groupby(['mes_numerico', 'dia'])['afluencia'].mean().to_dict()
        print(f"🚇 Matriz Saturación construida: {len(matriz_saturacion_diaria)} días únicos")
    else:
        print("⚠️ Matriz Saturación vacía: No hay datos de RTP ni Eléctricos")
        
    return matriz_vial, matriz_delitos, matriz_saturacion_diaria


# =====================================================================
# 🧠 3. FUNCIÓN DE COSTO DINÁMICA DE ENRUTAMIENTO (IA CONTEXTUAL)
# =====================================================================
def calcular_costo_dinamico(tramo_distancia, tramo_lat, tramo_lon, dia_numerico, mes_numerico, 
                           hora, dia_semana, matriz_vial, matriz_delitos, matriz_saturacion):
    """
    Ecuación Adaptativa Completa con Seguridad Pública:
    
    Costo = Distancia + (Beta * RiesgoVial) + (Omega * RiesgoDelitos) + (Gamma * AfluenciaDiaria)
    
    MODIFICADORES DINÁMICOS:
    - Hora Pico Escolar (7-9 AM o 5-8 PM en días hábiles): Eleva Beta (riesgo vial)
    - Hora Nocturna (8 PM a 5 AM): TRIPLICA Omega (delitos) para proteger al peatón
    
    Parámetros:
        tramo_distancia (float): Distancia del tramo en metros
        tramo_lat (float): Latitud anonimizada del punto
        tramo_lon (float): Longitud anonimizada del punto
        dia_numerico (int): Día del mes (1-31)
        mes_numerico (int): Mes del año (1-12)
        hora (int): Hora del día (0-23)
        dia_semana (str): Día de la semana ('Lunes', 'Martes', etc.)
        matriz_vial (dict): Diccionario de frecuencias de incidentes viales
        matriz_delitos (dict): Diccionario de frecuencias de delitos
        matriz_saturacion (dict): Diccionario de afluencia diaria
    
    Retorna:
        dict: Diccionario con costo_total, incidentes_viales, delitos_punto, afluencia_dia
    """
    # Recuperación probabilística de las matrices con clave espacio-temporal
    clave_espaciotemporal = (tramo_lat, tramo_lon, dia_semana, hora)
    
    riesgo_vial_historico = matriz_vial.get(clave_espaciotemporal, 0)
    riesgo_delitos_historico = matriz_delitos.get(clave_espaciotemporal, 0)
    afluencia_diaria_historica = matriz_saturacion.get((mes_numerico, dia_numerico), 100.0)
    
    # --- PESOS DINÁMICOS CONTEXTUALES (Lógica de la IA) ---
    
    # Evaluamos si la consulta cae en hora pico escolar de días hábiles
    es_hora_pico_escolar = (7 <= hora <= 9) or (17 <= hora <= 20)
    es_dia_habil = dia_semana in ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']
    
    # Evaluamos si es horario nocturno (mayor riesgo de delitos)
    es_hora_nocturna = (hora >= 20) or (hora < 5)
    
    # INICIALIZACIÓN DE PESOS BASE
    beta_riesgo_vial = 1.0
    omega_riesgo_delitos = 0.5
    gamma_afluencia = 1.0
    
    # MODIFICADOR 1: Hora Pico Escolar en Día Hábil
    if es_dia_habil and es_hora_pico_escolar:
        # Penaliza fuertemente calles con antecedentes de atropellamientos/choques a esa hora
        beta_riesgo_vial = 2.8
        # Eleva el peso de la afluencia diaria para evitar estaciones colapsadas ese día del mes
        gamma_afluencia = 1.8
        
    # MODIFICADOR 2: Horario Nocturno (CRÍTICO PARA SEGURIDAD)
    if es_hora_nocturna:
        # TRIPLICA drásticamente el peso de delitos para proteger al peatón
        omega_riesgo_delitos = 4.5
        # En horario nocturno, el riesgo vial también aumenta (visibilidad reducida)
        beta_riesgo_vial = max(beta_riesgo_vial, 1.8)
        
    # Cálculo matemático del impacto analítico
    costo_riesgo_vial = beta_riesgo_vial * riesgo_vial_historico
    costo_riesgo_delitos = omega_riesgo_delitos * riesgo_delitos_historico
    costo_saturacion = gamma_afluencia * (afluencia_diaria_historica / 1000.0)  # Escalado de volumen base
    
    costo_total = tramo_distancia + costo_riesgo_vial + costo_riesgo_delitos + costo_saturacion
    
    return {
        "costo_total": np.round(costo_total, 2),
        "incidentes_viales_punto": riesgo_vial_historico,
        "delitos_punto": riesgo_delitos_historico,
        "afluencia_historica_dia": np.round(afluencia_diaria_historica, 1),
        "pesos_aplicados": {
            "beta_vial": beta_riesgo_vial,
            "omega_delitos": omega_riesgo_delitos,
            "gamma_afluencia": gamma_afluencia
        }
    }


# =====================================================================
# 🧪 4. ORQUESTADOR DE PRUEBAS LOCALES (TEST RUNNER)
# =====================================================================
if __name__ == "__main__":
    # Definición de rutas a los 4 archivos CSV limpios
    PATH_C5_L = "clean_data/incidentes_c5.csv"
    PATH_RTP_L = "clean_data/afluencia_rtp.csv"
    PATH_ELEC_L = "clean_data/afluencia_electricos.csv"
    PATH_DELITOS_L = "clean_data/delitos.csv"  # NUEVO
    
    print("=" * 70)
    print("🏙️  INICIALIZANDO BACKEND DE ECOMIT-ANALYTICS - TLALPAN, CDMX")
    print("=" * 70)
    
    # Orquestación del pipeline con 4 datasets
    df_c5, df_rtp, df_elec, df_delitos = cargar_datasets_limpios(
        PATH_C5_L, PATH_RTP_L, PATH_ELEC_L, PATH_DELITOS_L
    )
    
    matriz_vial, matriz_delitos, matriz_sat_diaria = construir_matrices_predictivas(
        df_c5, df_rtp, df_elec, df_delitos
    )
    
    # Inyección de datos de contingencia (Fallback) si los archivos no están en la ruta aún
    # IMPORTANTE: Ahora usamos tuplas de 4 elementos (lat_anon, lon_anon, dia_semana, hora)
    if not matriz_vial and not matriz_delitos:
        print("\n⚙️  Registrando datos sintéticos de respaldo para testeo...")
        
        # Coordenadas simuladas de Tlalpan (pre-anonimizadas)
        lat_tlalpan = 19.170
        lon_tlalpan = 99.081
        
        # Matriz Vial: Viernes 6 PM tiene 28 incidentes, Domingo 8 AM tiene 2
        matriz_vial = {
            (lat_tlalpan, lon_tlalpan, "Viernes", 18): 28,
            (lat_tlalpan, lon_tlalpan, "Domingo", 8): 2
        }
        
        # Matriz Delitos: Viernes 10 PM tiene 15 delitos, Domingo 8 AM tiene 1
        matriz_delitos = {
            (lat_tlalpan, lon_tlalpan, "Viernes", 22): 15,
            (lat_tlalpan, lon_tlalpan, "Domingo", 8): 1
        }
        
        # Matriz Saturación: Simula Junio con días de alta y baja afluencia
        matriz_sat_diaria = {
            (6, 5): 5200.0,   # Viernes 5 de Junio - Alta afluencia
            (6, 7): 1200.0    # Domingo 7 de Junio - Baja afluencia
        }
        
        print("✅ Datos de contingencia cargados correctamente")
    
    print("\n" + "=" * 70)
    print("🧪 EJECUTANDO SIMULACIONES DE ESCENARIOS")
    print("=" * 70)
    
    # Coordenadas reales de Tlalpan para las pruebas
    LAT_TLALPAN = 19.170
    LON_TLALPAN = 99.081
    DISTANCIA_TRAMO = 1  # metros
    
    # ========================================================================
    # 🔴 SIMULACIÓN 1: VIERNES EN HORA PICO ESCOLAR (Riesgo Alto)
    # ========================================================================
    print("\n" + "─" * 70)
    print("🔴 SIMULACIÓN 1: VIERNES 5 DE JUNIO - 06:00 PM")
    print("   Contexto: Hora Pico Escolar en Día Hábil")
    print("─" * 70)
    
    resultado_pico = calcular_costo_dinamico(
        tramo_distancia=DISTANCIA_TRAMO,
        tramo_lat=LAT_TLALPAN,
        tramo_lon=LON_TLALPAN,
        dia_numerico=5,
        mes_numerico=6,
        hora=18,
        dia_semana="Viernes",
        matriz_vial=matriz_vial,
        matriz_delitos=matriz_delitos,
        matriz_saturacion=matriz_sat_diaria
    )
    
    print(f"📊 RESULTADOS DEL ANÁLISIS:")
    print(f"   • Costo Total de la Vía: {resultado_pico['costo_total']}")
    print(f"   • Incidentes Viales en este Punto: {resultado_pico['incidentes_viales_punto']}")
    print(f"   • Delitos Registrados en este Punto: {resultado_pico['delitos_punto']}")
    print(f"   • Afluencia Histórica del Día: {resultado_pico['afluencia_historica_dia']} pasajeros")
    print(f"\n🎯 PESOS APLICADOS:")
    print(f"   • Beta (Riesgo Vial): {resultado_pico['pesos_aplicados']['beta_vial']}")
    print(f"   • Omega (Delitos): {resultado_pico['pesos_aplicados']['omega_delitos']}")
    print(f"   • Gamma (Afluencia): {resultado_pico['pesos_aplicados']['gamma_afluencia']}")
    
    # ========================================================================
    # 🟢 SIMULACIÓN 2: DOMINGO POR LA MAÑANA EN HORARIO VALLE (Riesgo Bajo)
    # ========================================================================
    print("\n" + "─" * 70)
    print("🟢 SIMULACIÓN 2: DOMINGO 7 DE JUNIO - 08:00 AM")
    print("   Contexto: Horario Valle en Fin de Semana")
    print("─" * 70)
    
    resultado_valle = calcular_costo_dinamico(
        tramo_distancia=DISTANCIA_TRAMO,
        tramo_lat=LAT_TLALPAN,
        tramo_lon=LON_TLALPAN,
        dia_numerico=7,
        mes_numerico=6,
        hora=8,
        dia_semana="Domingo",
        matriz_vial=matriz_vial,
        matriz_delitos=matriz_delitos,
        matriz_saturacion=matriz_sat_diaria
    )
    
    print(f"📊 RESULTADOS DEL ANÁLISIS:")
    print(f"   • Costo Total de la Vía: {resultado_valle['costo_total']}")
    print(f"   • Incidentes Viales en este Punto: {resultado_valle['incidentes_viales_punto']}")
    print(f"   • Delitos Registrados en este Punto: {resultado_valle['delitos_punto']}")
    print(f"   • Afluencia Histórica del Día: {resultado_valle['afluencia_historica_dia']} pasajeros")
    print(f"\n🎯 PESOS APLICADOS:")
    print(f"   • Beta (Riesgo Vial): {resultado_valle['pesos_aplicados']['beta_vial']}")
    print(f"   • Omega (Delitos): {resultado_valle['pesos_aplicados']['omega_delitos']}")
    print(f"   • Gamma (Afluencia): {resultado_valle['pesos_aplicados']['gamma_afluencia']}")
    
    # ========================================================================
    # 🌙 SIMULACIÓN ADICIONAL: VIERNES NOCHE (Riesgo Delictivo Crítico)
    # ========================================================================
    print("\n" + "─" * 70)
    print("🌙 SIMULACIÓN ADICIONAL: VIERNES 5 DE JUNIO - 10:00 PM")
    print("   Contexto: Horario Nocturno - Peso de Delitos TRIPLICADO")
    print("─" * 70)
    
    resultado_noche = calcular_costo_dinamico(
        tramo_distancia=DISTANCIA_TRAMO,
        tramo_lat=LAT_TLALPAN,
        tramo_lon=LON_TLALPAN,
        dia_numerico=5,
        mes_numerico=6,
        hora=22,
        dia_semana="Viernes",
        matriz_vial=matriz_vial,
        matriz_delitos=matriz_delitos,
        matriz_saturacion=matriz_sat_diaria
    )
    
    print(f"📊 RESULTADOS DEL ANÁLISIS:")
    print(f"   • Costo Total de la Vía: {resultado_noche['costo_total']}")
    print(f"   • Incidentes Viales en este Punto: {resultado_noche['incidentes_viales_punto']}")
    print(f"   • Delitos Registrados en este Punto: {resultado_noche['delitos_punto']}")
    print(f"   • Afluencia Histórica del Día: {resultado_noche['afluencia_historica_dia']} pasajeros")
    print(f"\n🎯 PESOS APLICADOS:")
    print(f"   • Beta (Riesgo Vial): {resultado_noche['pesos_aplicados']['beta_vial']}")
    print(f"   • Omega (Delitos): {resultado_noche['pesos_aplicados']['omega_delitos']} ⚠️ TRIPLICADO")
    print(f"   • Gamma (Afluencia): {resultado_noche['pesos_aplicados']['gamma_afluencia']}")
    
    print("\n" + "=" * 70)
    print("✅ ANÁLISIS COMPLETADO - SISTEMA ECOMIT-ANALYTICS OPERATIVO")
    print("=" * 70)

# Made with Bob
