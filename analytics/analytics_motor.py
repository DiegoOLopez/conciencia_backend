import pandas as pd
import numpy as np
import os

# =====================================================================
# 🔒 1. PROTECCIÓN DE PRIVACIDAD & GOBERNANZA DE DATOS (LFPDPPP)
# =====================================================================
def anonimizar_coordenadas(lat, lon):
    """
    Aplica la técnica de Anonimización por Agregación Celular exigida por la ley.
    Trunca las coordenadas GPS a 3 decimales para aproximar la zona (~110m),
    imposibilitando el rastreo de un individuo específico analizando flujos macro.
    """
    if pd.isna(lat) or pd.isna(lon):
        return None, None
    return np.round(lat, 3), np.round(lon, 3)


# =====================================================================
# 📂 2. CARGA DIRECTA DE DATASETS YA LIMPIOS
# =====================================================================
def cargar_datasets_limpios(path_c5_limpio, path_rtp_limpio, path_electricos_limpio):
    """
    Carga de forma directa los archivos CSV previamente procesados y limpios.
    Garantiza que el sistema funcione fluidamente o use respaldos en caso de error.
    """
    print("Cargando datasets optimizados desde el almacenamiento...")
    
    # Carga de Riesgo Vial (C5)
    if os.path.exists(path_c5_limpio):
        df_c5 = pd.read_csv(path_c5_limpio)
    else:
        print(f"⚠️ Alerta: No se encontró {path_c5_limpio}. Se inicializa vacío.")
        df_c5 = pd.DataFrame()
        
    # Carga de Afluencia Diaria RTP
    if os.path.exists(path_rtp_limpio):
        df_rtp = pd.read_csv(path_rtp_limpio)
    else:
        print(f"⚠️ Alerta: No se encontró {path_rtp_limpio}. Se inicializa vacío.")
        df_rtp = pd.DataFrame()
        
    # Carga de Afluencia Diaria Transportes Eléctricos
    if os.path.exists(path_electricos_limpio):
        df_elec = pd.read_csv(path_electricos_limpio)
    else:
        print(f"⚠️ Alerta: No se encontró {path_electricos_limpio}. Se inicializa vacío.")
        df_elec = pd.DataFrame()
        
    return df_c5, df_rtp, df_elec


# =====================================================================
# 📊 3. GENERACIÓN DE MATRICES PREDICTIVAS (ESPACIO-TEMPORAL & CALENDARIO)
# =====================================================================
def construir_matrices_predictivas(df_c5, df_rtp, df_elec):
    """
    Construye los modelos analíticos de probabilidad.
    - C5: Mantiene resolución por HORA y DÍA para predecir picos de accidentes.
    - RTP/Eléctricos: Modificado a perfil diario utilizando las columnas ['dia', 'mes'].
    """
    matriz_riesgo = {}
    matriz_saturacion_diaria = {}
    
    # 1. Matriz de Riesgo Vial Predictivo (C5) - Se mapea por bloque de tiempo
    # Asume que tu CSV limpio de C5 ya tiene las columnas 'dia_semana' y 'hora'
    if not df_c5.empty and 'dia_semana' in df_c5.columns and 'hora' in df_c5.columns:
        matriz_riesgo = df_c5.groupby(['dia_semana', 'hora']).size().to_dict()
        
    # 2. Matriz de Inferencia de Saturación Diaria (RTP + Eléctricos unificados)
    # Agrupa por el par estructural de calendario: Mes y Día
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
        
    return matriz_riesgo, matriz_saturacion_diaria


# =====================================================================
# 🧠 4. FUNCIÓN DE COSTO DINÁMICA DE ENRUTAMIENTO (IA CONTEXTUAL)
# =====================================================================
def calcular_costo_dinamico(tramo_distancia, dia_numerico, mes_numerico, hora, dia_semana, matriz_riesgo, matriz_saturacion):
    """
    Ecuación Adaptativa: Costo = Distancia + (Beta * RiesgoVial) + (Gamma * AfluenciaDiaria)
    
    Usa la Hora/Día de la semana para predecir picos de riesgo vial del C5,
    y usa el Día/Mes para evaluar el comportamiento histórico de afluencia masiva en Tlalpan.
    """
    # Recuperación probabilística de las matrices
    riesgo_historico = matriz_riesgo.get((dia_semana, hora), 1)
    afluencia_diaria_historica = matriz_saturacion.get((mes_numerico, dia_numerico), 100.0)
    
    # --- PESOS DINÁMICOS CONTEXTUALES (Lógica de la IA) ---
    # Evaluamos si la consulta del estudiante cae en hora pico de días hábiles
    es_hora_pico = (7 <= hora <= 9) or (17 <= hora <= 20)
    es_dia_habil = dia_semana in ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']
    
    if es_dia_habil and es_hora_pico:
        # Penaliza fuertemente calles con antecedentes de atropellamientos/choques a esa hora
        beta_riesgo = 2.5
        # Eleva el peso de la afluencia diaria para evitar estaciones colapsadas ese día del mes
        gamma_afluencia = 1.5
    else:
        # Valores estándar para horarios valle o fines de semana
        beta_riesgo = 1.0
        gamma_afluencia = 1.0
        
    # Cálculo matemático del impacto analítico
    costo_riesgo_vial = beta_riesgo * riesgo_historico
    costo_saturacion = gamma_afluencia * (afluencia_diaria_historica / 1000.0) # Escalado de volumen base
    
    costo_total = tramo_distancia + costo_riesgo_vial + costo_saturacion
    
    return {
        "costo_total": np.round(costo_total, 2),
        "incidentes_estimados_hora": riesgo_historico,
        "afluencia_historica_dia": np.round(afluencia_diaria_historica, 1)
    }


# =====================================================================
# 🧪 5. ORQUESTADOR DE PRUEBAS LOCALES (TEST RUNNER)
# =====================================================================
if __name__ == "__main__":
    # Definición de rutas a tus nuevos archivos CSV limpios
    PATH_C5_L = "clean_data/incidentes_c5.csv"
    PATH_RTP_L = "clean_data/afluencia_rtp.csv"
    PATH_ELEC_L = "clean_data/afluencia_electricos.csv"
    
    print("=== INICIALIZANDO BACKEND DE EcoMIT-Analytics ===")
    
    # Orquestación del pipeline
    df_c5, df_rtp, df_elec = cargar_datasets_limpios(PATH_C5_L, PATH_RTP_L, PATH_ELEC_L)
    matriz_riesgo, matriz_sat_diaria = construir_matrices_predictivas(df_c5, df_rtp, df_elec)
    
    # Inyección de datos de contingencia (Fallback) si los archivos no están en la ruta aún
    if not matriz_sat_diaria:
        print("Registrando datos sintéticos de respaldo para testeo...")
        matriz_riesgo = {("Viernes", 18): 35, ("Domingo", 8): 1}
        # Simula Mes 6 (Junio), Día 5 con alta afluencia (ej. fin de cursos) vs un día normal
        matriz_sat_diaria = {(6, 5): 5200.0, (6, 15): 1200.0}
        
    # --- SIMULACIÓN 1: Estudiante viajando en Hora Pico (Viernes, 5 de Junio) ---
    # Variables de entrada: tramo_dist=100m, dia=5, mes=6, hora=18, dia_sem='Viernes'
    test_pico = calcular_costo_dinamico(100, 5, 6, 18, "Viernes", matriz_riesgo, matriz_sat_diaria)
    print(f"\n🔴 SIMULACIÓN 1: VIERNES 5 DE JUNIO - 06:00 PM (Hora Pico Escolar):")
    print(f" -> Costo de la vía indexado: {test_pico['costo_total']}")
    print(f" -> Historial de incidentes a esta hora: {test_pico['incidentes_estimados_hora']}")
    print(f" -> Afluencia histórica proyectada para este día: {test_pico['afluencia_historica_dia']} pasajeros.")
    
    # --- SIMULACIÓN 2: Mismo tramo en Horario Valle (Domingo, 15 de Junio) ---
    test_valle = calcular_costo_dinamico(100, 15, 6, 8, "Domingo", matriz_riesgo, matriz_sat_diaria)
    print(f"\n🟢 SIMULACIÓN 2: DOMINGO 15 DE JUNIO - 08:00 AM (Horario Valle):")
    print(f" -> Costo de la vía indexado: {test_valle['costo_total']}")
    print(f" -> Historial de incidentes a esta hora: {test_valle['incidentes_estimados_hora']}")
    print(f" -> Afluencia histórica proyectada para este día: {test_valle['afluencia_historica_dia']} pasajeros.")
    
    # --- SIMULACIÓN 3: Lunes de regreso a clases (Lunes, 2 de Septiembre - 07:30 AM) ---
    test_regreso_clases = calcular_costo_dinamico(100, 2, 9, 7, "Lunes", matriz_riesgo, matriz_sat_diaria)
    print(f"\n🟡 SIMULACIÓN 3: LUNES 2 DE SEPTIEMBRE - 07:30 AM (Regreso a Clases):")
    print(f" -> Costo de la vía indexado: {test_regreso_clases['costo_total']}")
    print(f" -> Historial de incidentes a esta hora: {test_regreso_clases['incidentes_estimados_hora']}")
    print(f" -> Afluencia histórica proyectada para este día: {test_regreso_clases['afluencia_historica_dia']} pasajeros.")
    
    # --- SIMULACIÓN 4: Miércoles en hora de salida escolar (Miércoles, 10 de Junio - 02:00 PM) ---
    test_salida_escolar = calcular_costo_dinamico(100, 10, 6, 14, "Miércoles", matriz_riesgo, matriz_sat_diaria)
    print(f"\n🟠 SIMULACIÓN 4: MIÉRCOLES 10 DE JUNIO - 02:00 PM (Salida Escolar):")
    print(f" -> Costo de la vía indexado: {test_salida_escolar['costo_total']}")
    print(f" -> Historial de incidentes a esta hora: {test_salida_escolar['incidentes_estimados_hora']}")
    print(f" -> Afluencia histórica proyectada para este día: {test_salida_escolar['afluencia_historica_dia']} pasajeros.")
    
    # --- SIMULACIÓN 5: Sábado por la tarde (Sábado, 20 de Junio - 03:00 PM) ---
    test_sabado_tarde = calcular_costo_dinamico(100, 20, 6, 15, "Sábado", matriz_riesgo, matriz_sat_diaria)
    print(f"\n🔵 SIMULACIÓN 5: SÁBADO 20 DE JUNIO - 03:00 PM (Fin de Semana - Actividades Recreativas):")
    print(f" -> Costo de la vía indexado: {test_sabado_tarde['costo_total']}")
    print(f" -> Historial de incidentes a esta hora: {test_sabado_tarde['incidentes_estimados_hora']}")
    print(f" -> Afluencia histórica proyectada para este día: {test_sabado_tarde['afluencia_historica_dia']} pasajeros.")
    
    # --- SIMULACIÓN 6: Jueves en hora pico vespertina (Jueves, 12 de Junio - 06:30 PM) ---
    test_jueves_pico = calcular_costo_dinamico(100, 12, 6, 18, "Jueves", matriz_riesgo, matriz_sat_diaria)
    print(f"\n🔴 SIMULACIÓN 6: JUEVES 12 DE JUNIO - 06:30 PM (Hora Pico Vespertina):")
    print(f" -> Costo de la vía indexado: {test_jueves_pico['costo_total']}")
    print(f" -> Historial de incidentes a esta hora: {test_jueves_pico['incidentes_estimados_hora']}")
    print(f" -> Afluencia histórica proyectada para este día: {test_jueves_pico['afluencia_historica_dia']} pasajeros.")
    
    # --- SIMULACIÓN 7: Martes madrugada (Martes, 8 de Junio - 05:00 AM) ---
    test_madrugada = calcular_costo_dinamico(100, 8, 6, 5, "Martes", matriz_riesgo, matriz_sat_diaria)
    print(f"\n🌙 SIMULACIÓN 7: MARTES 8 DE JUNIO - 05:00 AM (Madrugada - Tráfico Mínimo):")
    print(f" -> Costo de la vía indexado: {test_madrugada['costo_total']}")
    print(f" -> Historial de incidentes a esta hora: {test_madrugada['incidentes_estimados_hora']}")
    print(f" -> Afluencia histórica proyectada para este día: {test_madrugada['afluencia_historica_dia']} pasajeros.")
    
    # --- SIMULACIÓN 8: Viernes noche (Viernes, 19 de Junio - 10:00 PM) ---
    test_viernes_noche = calcular_costo_dinamico(100, 19, 6, 22, "Viernes", matriz_riesgo, matriz_sat_diaria)
    print(f"\n🌃 SIMULACIÓN 8: VIERNES 19 DE JUNIO - 10:00 PM (Viernes Noche - Vida Nocturna):")
    print(f" -> Costo de la vía indexado: {test_viernes_noche['costo_total']}")
    print(f" -> Historial de incidentes a esta hora: {test_viernes_noche['incidentes_estimados_hora']}")
    print(f" -> Afluencia histórica proyectada para este día: {test_viernes_noche['afluencia_historica_dia']} pasajeros.")
    
    # --- SIMULACIÓN 9: Lunes de Octubre - Regreso de puente (Lunes, 14 de Octubre - 08:00 AM) ---
    test_octubre_puente = calcular_costo_dinamico(100, 14, 10, 8, "Lunes", matriz_riesgo, matriz_sat_diaria)
    print(f"\n🟠 SIMULACIÓN 9: LUNES 14 DE OCTUBRE - 08:00 AM (Regreso de Puente Largo):")
    print(f" -> Costo de la vía indexado: {test_octubre_puente['costo_total']}")
    print(f" -> Historial de incidentes a esta hora: {test_octubre_puente['incidentes_estimados_hora']}")
    print(f" -> Afluencia histórica proyectada para este día: {test_octubre_puente['afluencia_historica_dia']} pasajeros.")
    
    # --- SIMULACIÓN 10: Miércoles de Octubre - Medio día (Miércoles, 23 de Octubre - 01:00 PM) ---
    test_octubre_mediodia = calcular_costo_dinamico(100, 23, 10, 13, "Miércoles", matriz_riesgo, matriz_sat_diaria)
    print(f"\n🟡 SIMULACIÓN 10: MIÉRCOLES 23 DE OCTUBRE - 01:00 PM (Hora de Comida):")
    print(f" -> Costo de la vía indexado: {test_octubre_mediodia['costo_total']}")
    print(f" -> Historial de incidentes a esta hora: {test_octubre_mediodia['incidentes_estimados_hora']}")
    print(f" -> Afluencia histórica proyectada para este día: {test_octubre_mediodia['afluencia_historica_dia']} pasajeros.")
    
    # --- SIMULACIÓN 11: Viernes de Noviembre - Inicio de fin de semana largo (Viernes, 1 de Noviembre - 05:00 PM) ---
    test_noviembre_findesemana = calcular_costo_dinamico(100, 1, 11, 17, "Viernes", matriz_riesgo, matriz_sat_diaria)
    print(f"\n🔴 SIMULACIÓN 11: VIERNES 1 DE NOVIEMBRE - 05:00 PM (Día de Muertos - Salida Temprana):")
    print(f" -> Costo de la vía indexado: {test_noviembre_findesemana['costo_total']}")
    print(f" -> Historial de incidentes a esta hora: {test_noviembre_findesemana['incidentes_estimados_hora']}")
    print(f" -> Afluencia histórica proyectada para este día: {test_noviembre_findesemana['afluencia_historica_dia']} pasajeros.")
    
    # --- SIMULACIÓN 12: Martes de Noviembre - Día normal (Martes, 19 de Noviembre - 09:00 AM) ---
    test_noviembre_normal = calcular_costo_dinamico(100, 19, 11, 9, "Martes", matriz_riesgo, matriz_sat_diaria)
    print(f"\n🟢 SIMULACIÓN 12: MARTES 19 DE NOVIEMBRE - 09:00 AM (Día Normal de Clases):")
    print(f" -> Costo de la vía indexado: {test_noviembre_normal['costo_total']}")
    print(f" -> Historial de incidentes a esta hora: {test_noviembre_normal['incidentes_estimados_hora']}")
    print(f" -> Afluencia histórica proyectada para este día: {test_noviembre_normal['afluencia_historica_dia']} pasajeros.")
    
    print("\n=== ANÁLISIS COMPLETADO ===")