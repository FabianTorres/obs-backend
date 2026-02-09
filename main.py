import os
import json
import re
import traceback # Importante para ver errores completos
from lark import Lark, UnexpectedCharacters, UnexpectedToken
from app.parser.transformer import ObservacionTransformer
from app.parser.normalizer import Normalizer
from app.generator.scanner import VariableScanner
from app.generator.csv_exporter import CSVExporter
from app.generator.sii_exporter import SIIExporter
from app.generator.builder import ScenarioBuilder
from app.generator.param_loader import ParamLoader
# 1. IMPORTAR DEFINICIONES GLOBALES
from app.generator.global_definitions import GLOBAL_DEFINITIONS 

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GRAMMAR_PATH = os.path.join(BASE_DIR, 'app', 'parser', 'grammar.lark')
INPUT_PATH = os.path.join(BASE_DIR, 'input.txt')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
PARAM_PATH = os.path.join(BASE_DIR, 'parameters.csv')
os.makedirs(OUTPUT_DIR, exist_ok=True)

def cargar_gramatica():
    try:
        with open(GRAMMAR_PATH, 'r', encoding='utf-8') as file: return file.read()
    except FileNotFoundError: exit()

def guardar_json(nombre, datos):
    path = os.path.join(OUTPUT_DIR, nombre)
    with open(path, 'w', encoding='utf-8') as f: json.dump(datos, f, indent=2, ensure_ascii=False)
    return path

def leer_input_segmentado(path):
    with open(path, 'r', encoding='utf-8') as f: content = f.read()
    def extract(tag):
        match = re.search(f'<<<{tag}>>>(.*?)($|<<<)', content, re.DOTALL)
        return match.group(1).strip() if match else ""
    return {
        "vars_pre": extract("VARIABLES_PRE"),
        "cond_entrada": extract("CONDICION_ENTRADA"),
        "vars_post": extract("VARIABLES_POST"),
        "normas": extract("NORMAS")
    }

if __name__ == "__main__":
    try:
        print("📥 Cargando Parámetros...")
        param_loader = ParamLoader(PARAM_PATH)
        parametros_dict = param_loader.load()

        print("📥 Leyendo segmentos de entrada...")
        input_data = leer_input_segmentado(INPUT_PATH)
        
        print("🧹 Normalizando reglas de negocio...")
        normalizer = Normalizer()
        
        clean_vars_pre = normalizer.clean_section(input_data["vars_pre"], "Variables PRE")
        clean_cond = normalizer.clean_section(input_data["cond_entrada"], "Condición Entrada")
        clean_vars_post = normalizer.clean_section(input_data["vars_post"], "Variables POST")
        clean_normas = normalizer.clean_section(input_data["normas"], "Normas")

        # --- GESTIÓN DE REPORTES DE CALIDAD ---
        path_json_report = guardar_json("reporte_calidad.json", normalizer.report)
        path_txt_report = os.path.join(OUTPUT_DIR, "advertencias_sintaxis.txt")
        critical_count = 0
        with open(path_txt_report, 'w', encoding='utf-8') as f:
            if normalizer.report:
                f.write("="*80 + "\n")
                f.write("⚠️  REPORTE DE INCIDENCIAS EN EL DOCUMENTO ORIGINAL\n")
                f.write("="*80 + "\n\n")
                for item in normalizer.report:
                    prefix = "[INFO]"
                    if item['nivel'] == 'CRITICAL': 
                        prefix = "[⛔ ERROR GRAVE]"
                        critical_count += 1
                    elif item['nivel'] == 'WARNING':
                        prefix = "[⚠️ ADVERTENCIA]"
                    f.write(f"{prefix} {item['contexto']}\n")
                    f.write(f"    {item['mensaje']}\n")
                    f.write("-" * 40 + "\n")
            else:
                f.write("✅ Documento procesado sin incidencias.")
        
        # ENSAMBLAJE DEL TEXTO MAESTRO
        texto_maestro = ""
        if clean_cond: texto_maestro += f"Condición de Entrada: {clean_cond}\n\n"
        
        vars_total = []
        if clean_vars_pre: vars_total.append(clean_vars_pre)
        if clean_vars_post: vars_total.append(clean_vars_post)
        if vars_total: texto_maestro += "Variables:\n" + "\n".join(vars_total) + "\n\n"
        
        if clean_normas: texto_maestro += clean_normas + "\n"

        with open(os.path.join(OUTPUT_DIR, "debug_assembler.txt"), 'w', encoding='utf-8') as f:
            f.write(texto_maestro)

        # PARSING
        grammar_text = cargar_gramatica()
        parser = Lark(grammar_text, start='start', propagate_positions=True)
        arbol_bruto = parser.parse(texto_maestro)
        transformer = ObservacionTransformer()
        datos_arbol = transformer.transform(arbol_bruto)

        # 2. PROCESAR MACROS GLOBALES (FIXED)
        print("\n🌍 Procesando Definiciones Globales...")
        parsed_macros = {}
        
        for name, formula in GLOBAL_DEFINITIONS.items():
            try:
                # 1. Normalización
                raw_input = f"{name} = {formula}"
                clean_formula = normalizer.clean_section(raw_input, context_name=f"Macro {name}")
                clean_formula = clean_formula.strip()
                
                if not clean_formula: continue

                # 2. Parseo
                macro_text = f"Variables:\n{clean_formula}"
                macro_tree = parser.parse(macro_text)
                
                # 3. Transformación
                macro_data_list = transformer.transform(macro_tree)
                
                # 4. Extracción Correcta (Manejo de Lista de Secciones)
                logic_found = None
                
                # Iteramos sobre las secciones encontradas (usualmente solo una: Variables)
                for section in macro_data_list:
                    if section.get('section') == 'Variables':
                        # Iteramos sobre las variables dentro de la sección
                        for var_item in section.get('content', []):
                            if var_item.get('target') == name:
                                logic_found = var_item.get('logic')
                                break
                    if logic_found: break
                
                if logic_found:
                    parsed_macros[name] = logic_found
                    # print(f"   ✅ {name} cargada.")
                else:
                    print(f"   ⚠️ FALLO: No se pudo extraer la lógica para {name}.")

            except Exception as e:
                print(f"   ❌ ERROR en {name}: {e}")

        print(f"🐛 [DEBUG] Macros cargadas: {len(parsed_macros)}")

        # GENERACIÓN
        scanner = VariableScanner()
        scanner.scan(datos_arbol)

        print("🔍 Escaneando variables en macros globales...")
        for macro_name, macro_logic in parsed_macros.items():
            dummy_structure = {
                "variables": [
                    {"target": macro_name, "logic": macro_logic}
                ]
            }
            scanner.scan(dummy_structure)
        
        reporte_vars = scanner.get_report()

        print("🧠 Generando Escenarios...")
        # 3. PASAMOS LAS MACROS AL BUILDER
        builder = ScenarioBuilder(datos_arbol, parameters=parametros_dict, macros=parsed_macros)
        escenarios = builder.build_suite()

        headers = reporte_vars["Vectores_Requeridos"] + reporte_vars["Codigos_Requeridos"]
        CSVExporter(OUTPUT_DIR).export("casos_de_prueba.csv", headers, escenarios)
        SIIExporter(OUTPUT_DIR).export("casos_oficiales_sii.txt", headers, escenarios)
        
        guardar_json("arbol_logico.json", datos_arbol)
        
        print("\n✅ PROCESO COMPLETADO")
        print(f"🚀 {len(escenarios)} escenarios generados.")

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n❌ ERROR FATAL: {e}")