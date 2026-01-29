import os
import json
from lark import Lark, UnexpectedCharacters, UnexpectedToken
from app.parser.transformer import ObservacionTransformer
from app.generator.scanner import VariableScanner
from app.generator.conditions import ConditionExtractor
from app.generator.test_designer import TestDesigner 
from app.generator.csv_exporter import CSVExporter
from app.generator.sii_exporter import SIIExporter
from app.generator.scenario_builder import ScenarioBuilder
from app.generator.param_loader import ParamLoader

# --- CONFIGURACION DE RUTAS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GRAMMAR_PATH = os.path.join(BASE_DIR, 'app', 'parser', 'grammar.lark')
INPUT_PATH = os.path.join(BASE_DIR, 'input.txt')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
PARAM_PATH = os.path.join(BASE_DIR, 'parameters.csv')

# Aseguramos que exista la carpeta de salida
os.makedirs(OUTPUT_DIR, exist_ok=True)

def cargar_gramatica():
    try:
        with open(GRAMMAR_PATH, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        print("❌ ERROR CRÍTICO: No encuentro el archivo grammar.lark")
        exit()

def guardar_json(nombre_archivo, datos):
    path = os.path.join(OUTPUT_DIR, nombre_archivo)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(datos, f, indent=2, ensure_ascii=False)
    return path

# --- EJECUCION PRINCIPAL ---
if __name__ == "__main__":
    texto_para_error = "" # Variable auxiliar para el manejo de errores
    try:

        # 0. CARGAR PARAMETROS (Fase 1)
        print("📥 Cargando Parámetros...")
        param_loader = ParamLoader(PARAM_PATH)
        parametros_dict = param_loader.load()
        print(f"   🔹 {len(parametros_dict)} parámetros cargados.")

        # 1. PARSING
        grammar_text = cargar_gramatica()
        parser = Lark(grammar_text, start='start', propagate_positions=True)
        
        with open(INPUT_PATH, 'r', encoding='utf-8') as f:
            texto_para_error = f.read() # Guardamos en variable externa por si falla
        
        arbol_bruto = parser.parse(texto_para_error)
        transformer = ObservacionTransformer()
        datos_arbol = transformer.transform(arbol_bruto)

        # 2. SCANNER
        scanner = VariableScanner()
        scanner.scan(datos_arbol)
        reporte_vars = scanner.get_report()

        # 3. CONSTRUCTOR DE ESCENARIOS
        print("🧠 Generando Escenarios de Prueba...")
        builder = ScenarioBuilder(datos_arbol, parameters=parametros_dict)
        escenarios = builder.build_suite()

        # 4. EXPORTAR A CSV (Formato Excel - Columnas separadas)
        headers = reporte_vars["Vectores_Requeridos"] + reporte_vars["Codigos_Requeridos"]
        
        print("💾 Guardando formato Excel...")
        exporter_csv = CSVExporter(OUTPUT_DIR)
        path_csv = exporter_csv.export("casos_de_prueba.csv", headers, escenarios)
        
        # 5. EXPORTAR A TXT/CSV (Formato SII - Pipe Delimited)
        print("💾 Guardando formato SII Oficial...")
        exporter_sii = SIIExporter(OUTPUT_DIR)
        path_sii = exporter_sii.export("casos_oficiales_sii.txt", headers, escenarios)

        # --- GENERACION DE SALIDAS ---
        path_arbol = guardar_json("arbol_logico.json", datos_arbol)
        path_vars = guardar_json("reporte_variables.json", reporte_vars)
        path_scenarios = guardar_json("escenarios_debug.json", escenarios)

        # --- DASHBOARD ---
        total_secciones = len(datos_arbol) if isinstance(datos_arbol, list) else 0
        
        print("\n✅ PROCESO COMPLETADO EXITOSAMENTE")
        print("="*40)
        print(f"📊 ESTADÍSTICAS DEL ALGORITMO")
        print("="*40)
        print(f"🔹 Secciones Identificadas : {total_secciones}")
        print("-" * 40)
        print(f"🔹 Vectores (Inputs)       : {len(reporte_vars['Vectores_Requeridos'])}")
        print(f"🔹 Códigos F22 (Inputs)    : {len(reporte_vars['Codigos_Requeridos'])}")
        print(f"🔹 Variables Calculadas    : {len(reporte_vars['Variables_Calculadas'])}")
        print(f"🔹 Parámetros Cargados     : {len(parametros_dict)}")
        print("-" * 40)
        print(f"🚀 ESCENARIOS GENERADOS    : {len(escenarios)}")
        print("="*40)
        print("\n📂 Archivos generados:")
        print(f"   1. {path_csv}")
        print(f"   2. {path_sii}")
        print(f"   3. {path_scenarios}")

    except UnexpectedCharacters as e:
        print(f"\n❌ ERROR DE CARACTER en Línea {e.line}, Columna {e.column}")
        print(f"Contexto:\n{e.get_context(texto_para_error)}")
    except UnexpectedToken as e:
        print(f"\n❌ ERROR DE SINTAXIS en Línea {e.line}, Columna {e.column}")
        print(f"Contexto:\n{e.get_context(texto_para_error)}")
    except Exception as e:
        # Imprimimos el error completo para debuggear mejor si pasa algo más
        import traceback
        traceback.print_exc()
        print(f"\n❌ ERROR GENERAL: {e}")
