import sys
import os

# Simulación de dependencias para no cargar todo el framework
class MockMathEngine:
    def evaluate(self, tree, ctx):
        return 0 # Default para simplificar

class LogicProcessor:
    def flatten_logic(self, node, op):
        # Simula: (Sum) AND (1-Mi) AND (Ep)
        if op == "AND":
            return [
                {"op": ">", "left": "Sum", "right": 0},
                {"op": "<", "left": "Mi", "right": 1},
                {"op": ">", "left": "Epsilon", "right": 0}
            ]
        return [node] # ORs simulados

    def extract_predicates(self, node):
        # Simula extracción básica
        target = node.get("left")
        op = node.get("op")
        return [{"target": target, "op": op, "right_tree": node.get("right"), "value": [0]}]

    def decompose_additive_expression(self, node, pos, neg):
        pass # No necesario para este debug de alto nivel

# --- CLASE A DEBUGEAR (Versión Simplificada del Mixin) ---
class DebugCombinatoricsMixin:
    def __init__(self):
        self.logic_processor = LogicProcessor()
        self.math_engine = MockMathEngine()
        self.parameters = {}
        self.scenarios = []
        self.case_id = 0

    def _smart_set_input(self, inputs, target, value):
        # Simulación simple
        inputs[target] = value
        print(f"      [DEBUG] Set {target} = {value}")

    def _generate_ok_combinations(self, logic_block):
        # Simula devolver un Happy Path perfecto
        print("   [DEBUG] Generando OK Combinations (Happy Path)...")
        return [{"Sum": 1000, "Mi": 0, "Epsilon": 1000}]

    def _generate_nk_combinations(self, logic_block):
        # Simula devolver los modos de fallo
        print("   [DEBUG] Generando NK Combinations (Modos de Fallo)...")
        # Modo 1: Falla Suma
        mode1 = {"Sum": 0} 
        # Modo 2: Falla Mi (Sabotaje)
        mode2 = {"Mi": 1}
        # Modo 3: Falla Epsilon
        mode3 = {"Epsilon": 0}
        
        return [mode1, mode2, mode3]

    def _apply_sabotage(self, inputs, bad_inputs):
        print(f"   [DEBUG] Aplicando Sabotaje: {bad_inputs} sobre {inputs}")
        for k, v in bad_inputs.items():
            inputs[k] = v
        print(f"   [DEBUG] Resultado Final: {inputs}")

    def _generate_nk_cases(self, cond_block, golden_inputs):
        print("\n🏁 INICIANDO DEBUG DE GENERACIÓN NK 🏁")
        
        # 1. Happy Path
        ok_scenarios = self._generate_ok_combinations(cond_block)
        reference_happy_input = ok_scenarios[0] if ok_scenarios else {}
        print(f"   [DEBUG] Happy Path de Referencia: {reference_happy_input}")

        # 2. Modos de Fallo
        bad_scenarios = self._generate_nk_combinations(cond_block)
        print(f"   [DEBUG] Escenarios Malos Generados: {bad_scenarios}")
        
        for i, bad_inputs in enumerate(bad_scenarios):
            print(f"\n   🔸 Procesando Caso Negativo #{i+1}")
            
            # 3. Construcción del Caso
            case_inputs = golden_inputs.copy()
            print(f"      1. Base Golden: {case_inputs}")
            
            case_inputs.update(reference_happy_input)
            print(f"      2. + Happy Path: {case_inputs}")
            
            self._apply_sabotage(case_inputs, bad_inputs)
            print(f"      3. + Sabotaje: {case_inputs}")

# --- EJECUCIÓN ---
print("Simulando lógica de LAMBDA...")
debugger = DebugCombinatoricsMixin()
debugger._generate_nk_cases({}, {"Golden_Var": 1})