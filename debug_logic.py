import os
import json
from lark import Lark
from app.parser.transformer import ObservacionTransformer
from app.parser.normalizer import Normalizer
from app.generator.builder.logic_processor import LogicProcessor

# --- DEFINICIONES A DIAGNOSTICAR ---
DEFINITIONS = {
    "EPSILON": "SI(REX_2+ Vx010156= 0 Y Vx010053>0; 1; 0)",
    "LAMBDA": "SI((Vx012946 + Vx012947) * (1-Mi) * (épsilon) > 0; 1; 0)" # Simplificada para ver estructura
}

# --- CONFIGURACIÓN ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GRAMMAR_PATH = os.path.join(BASE_DIR, 'app', 'parser', 'grammar.lark')

def debug_definitions():
    print("🔬 INICIANDO DIAGNÓSTICO DE LÓGICA 🔬\n")
    
    # 1. Cargar Gramática
    with open(GRAMMAR_PATH, 'r', encoding='utf-8') as f:
        grammar = f.read()
    parser = Lark(grammar, start='start', propagate_positions=True)
    normalizer = Normalizer()
    transformer = ObservacionTransformer()
    processor = LogicProcessor()

    for name, formula in DEFINITIONS.items():
        print(f"{'='*60}")
        print(f"📘 VARIABLE: {name}")
        print(f"📝 Fórmula Original: {formula}")
        
        # 2. Normalizar
        raw_input = f"{name} = {formula}"
        clean = normalizer.clean_section(raw_input, f"Debug {name}").strip()
        print(f"🧹 Normalizada: {clean}")
        
        # 3. Parsear y Transformar
        tree = parser.parse(f"Variables:\n{clean}")
        data = transformer.transform(tree)
        
        # Extraer el nodo lógico principal (la condición del SI)
        # Asumimos que data es una lista de secciones, buscamos 'Variables'
        logic_node = None
        for sec in data:
            if sec.get('section') == 'Variables':
                for item in sec.get('content', []):
                    if item.get('target') == name:
                        # Si es condicional, nos interesa la condición ('cond')
                        logic = item.get('logic', {})
                        if logic.get('type') == 'conditional':
                            logic_node = logic.get('cond')
                        else:
                            logic_node = logic
        
        if not logic_node:
            print("❌ ERROR: No se pudo extraer el nodo lógico.")
            continue

        print(f"🌳 Estructura del Árbol (Condición):")
        print(json.dumps(logic_node, indent=2))
        
        # 4. Prueba de LogicProcessor (Flatten + Extract)
        print(f"\n🧠 Análisis del LogicProcessor:")
        
        # A. Flatten (Descomponer ANDs)
        print("   👉 Intentando aplanar lógica (AND)...")
        flat_components = processor.flatten_logic(logic_node, "AND")
        print(f"      Componentes encontrados: {len(flat_components)}")
        
        # B. Extract Predicates (Extraer metas)
        print("   👉 Extrayendo Predicados (Metas)...")
        all_preds = []
        for comp in flat_components:
            preds = processor.extract_predicates(comp)
            all_preds.extend(preds)
            
        if not all_preds:
            print("      ⚠️ ALERTA: No se extrajeron predicados.")
        else:
            for i, p in enumerate(all_preds):
                print(f"      ✅ Predicado #{i+1}: {p}")

        # Verificación específica para EPSILON
        if name == "EPSILON":
            has_vx53 = any("Vx010053" in str(p) or "Vx53" in str(p) for p in all_preds)
            if has_vx53:
                print("\n   🎉 DIAGNÓSTICO: Vx53 fue detectado correctamente.")
            else:
                print("\n   ⛔ DIAGNÓSTICO: Vx53 NO aparece. El procesador ignoró la segunda parte del AND.")

if __name__ == "__main__":
    debug_definitions()