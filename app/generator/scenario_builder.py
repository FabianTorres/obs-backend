import copy
import itertools
from app.generator.math_engine import MathEngine

class ScenarioBuilder:
    def __init__(self, logic_tree, parameters={}):
        self.logic_tree = logic_tree
        self.parameters = parameters
        self.math_engine = MathEngine()
        self.scenarios = []
        self.case_id = 11467

    def build_suite(self):
        """Genera la suite completa con cobertura de ramas para OR"""
        
        # 1. Analizar Condición de Entrada
        cond_block = self._find_section("Condicion_Entrada")
        
        # PASO CLAVE: Generar Multiples Casos OK (Branch Coverage)
        # Esto devuelve una lista de diccionarios (un dict por cada camino válido del OR)
        ok_scenarios_inputs = self._generate_ok_combinations(cond_block)
        
        # Guardamos todos los casos OK generados
        golden_inputs = {} # Guardaremos el primero como "Semilla" para las variables y NK
        
        for i, inputs in enumerate(ok_scenarios_inputs):
            if i == 0: golden_inputs = inputs # Usamos el primero como base para lo demás
            
            # Identificamos qué rama estamos probando para la descripción
            desc = self._describe_scenario(inputs)
            self._add_case("Cond. OK", f"Camino válido #{i+1}: {desc}", inputs, "Cumple Condición")

        # 2. Generar Casos NK (Usamos la semilla golden para romperla)
        # Extraemos predicados simples para saber qué romper
        predicates = self._extract_predicates(cond_block)
        self._generate_nk_cases(predicates, golden_inputs)

        # 3. Calcular Variables (Con la Semilla Golden)
        vars_block = self._find_section("Variables")
        initial_context = {**golden_inputs, **self.parameters}
        computed_vars = self._calculate_variables(vars_block, initial_context)
        
        for var_name, val in computed_vars.items():
            self._add_case(var_name, f"Verificar cálculo de {var_name}", golden_inputs, f"{val}")

        # 4. Normas (Con contexto completo)
        full_context = {**golden_inputs, **self.parameters, **computed_vars}
        self._generate_norm_cases(full_context)

        return self.scenarios

    # --- LÓGICA DE EXPANSIÓN COMBINATORIA (NUEVO) ---

    def _generate_ok_combinations(self, logic_block):
        """
        Descompone el árbol en grupos AND y OR, y genera el producto cartesiano
        de todas las combinaciones válidas.
        """
        # 1. Aplanar el nivel superior (ANDs)
        # Un bloque de entrada es implícitamente un AND gigante de sus partes
        and_components = self._flatten_logic(logic_block, "AND")
        
        # 2. Analizar cada componente
        # Cada componente puede ser:
        # - Un átomo (Comparación simple C > 0) -> Solo tiene 1 forma de ser True
        # - Un grupo OR (C1 .o. C2 .o. C3) -> Tiene 3 formas de ser True
        component_options = []
        
        for comp in and_components:
            # Aplanamos internamente si es un OR
            or_options = self._flatten_logic(comp, "OR")
            
            # Para cada opción del OR, calculamos qué inputs necesita para ser True
            solved_options = []
            for option in or_options:
                # Extraemos el predicado único de esta opción
                preds = self._extract_predicates(option)
                # Resolvemos inputs para que ESTA opción sea True
                inputs = self._solve_for_true(preds)
                if inputs:
                    solved_options.append(inputs)
            
            if solved_options:
                component_options.append(solved_options)

        # 3. Producto Cartesiano
        # Si tenemos [ [A], [B1, B2, B3], [C] ]
        # Generamos: A+B1+C, A+B2+C, A+B3+C
        all_combinations = []
        for combo in itertools.product(*component_options):
            # Fusionamos los diccionarios de la combinación
            merged_inputs = {}
            for d in combo:
                merged_inputs.update(d)
            all_combinations.append(merged_inputs)
            
        return all_combinations

    def _flatten_logic(self, node, split_op):
        """
        Convierte un árbol anidado A .op. (B .op. C) en una lista [A, B, C].
        """
        items = []
        
        # Si es una lista, asumimos implícitamente AND entre sus elementos (si split_op es AND)
        if isinstance(node, list):
            if split_op == "AND":
                for item in node: items.extend(self._flatten_logic(item, split_op))
            else:
                # Si estamos buscando ORs pero encontramos lista, la tratamos como unidad
                items.append(node)
            return items

        if isinstance(node, dict):
            # Si encontramos el operador que buscamos, recursividad por izquierda y derecha
            if "op" in node:
                op = node["op"]
                # Mapeo de mis operadores internos a tu lógica
                is_target_op = False
                if split_op == "AND" and op in ["AND", ".y.", ".Y."]: is_target_op = True
                if split_op == "OR" and op in ["OR", ".o.", ".O."]: is_target_op = True
                
                if is_target_op:
                    items.extend(self._flatten_logic(node["left"], split_op))
                    items.extend(self._flatten_logic(node["right"], split_op))
                    return items

        # Si no es el operador que buscamos (es una hoja o el operador contrario), lo devolvemos tal cual
        items.append(node)
        return items

    def _describe_scenario(self, inputs):
        """Genera una descripción corta basada en qué variables están activas"""
        active_vars = [k for k, v in inputs.items() if v > 0 and k not in self.parameters]
        # Limpiamos un poco para que no sea eterno
        return f"Activando {', '.join(active_vars[:4])}..."

    # --- SOLVER BÁSICO (REUTILIZADO) ---

    def _solve_for_true(self, predicates):
        """Resuelve un set de predicados simples (Sin ORs complejos)"""
        current_inputs = self.parameters.copy()
        for i in range(2): # Pequeña iteración para dependencias simples
            for p in predicates:
                target = p['target']
                op = p['op']
                # Evaluamos lado derecho
                target_val = self.math_engine.evaluate(p['right_tree'], current_inputs)
                
                new_val = current_inputs.get(target, 0)
                if op == ">": new_val = target_val + 1
                elif op == ">=": new_val = target_val
                elif op == "<": new_val = target_val - 1
                elif op == "<=": new_val = target_val
                elif op == "=": new_val = target_val
                
                current_inputs[target] = new_val
        
        # Retornamos solo los inputs que no son parámetros
        return {k: v for k, v in current_inputs.items() if k not in self.parameters}

    def _generate_nk_cases(self, predicates, golden_inputs):
        """Genera casos NK rompiendo un predicado a la vez"""
        context = {**golden_inputs, **self.parameters}
        for p in predicates:
            target = p['target']
            op = p['op']
            ref_value = self.math_engine.evaluate(p['right_tree'], context)
            
            bad_inputs = golden_inputs.copy()
            broken_val = None
            
            # Invertimos lógica
            if op == ">": broken_val = ref_value
            elif op == ">=": broken_val = ref_value - 1
            elif op == "<": broken_val = ref_value
            elif op == "<=": broken_val = ref_value + 1
            elif op == "=": broken_val = ref_value + 1
            
            if broken_val is not None:
                bad_inputs[target] = broken_val
                self._add_case("Cond. NK", f"Romper {target} ({op} {ref_value}) con {broken_val}", bad_inputs, "No cumple Condición")

    # --- UTILIDADES ---
    
    def _extract_predicates(self, block):
        """Extrae comparaciones atómicas"""
        preds = []
        if isinstance(block, list):
            for item in block: preds.extend(self._extract_predicates(item))
        elif isinstance(block, dict):
            if "op" in block and block["op"] in [">", "<", ">=", "<=", "=", "≠"]:
                left = block["left"]
                if isinstance(left, str):
                    preds.append({"target": left, "op": block["op"], "right_tree": block["right"]})
            for k, v in block.items():
                if isinstance(v, (dict, list)): preds.extend(self._extract_predicates(v))
        return preds

    def _calculate_variables(self, block, context_inputs):
        results = {}
        if not block: return results
        instr_list = block if isinstance(block, list) else [block]
        current_context = context_inputs.copy()
        for item in instr_list:
            if "target" in item:
                name = item["target"]
                val = self.math_engine.evaluate(item["logic"], current_context)
                results[name] = val
                current_context[name] = val
        return results

    def _generate_norm_cases(self, context):
        self._add_case("Norma 1", "Verificar cumplimiento de Norma", context, "DIF=Calc DISC=Calc")
        self._add_case("Norma NK", "Verificar No Cumplimiento", context, "No cumple Norma")

    def _find_section(self, name):
        if isinstance(self.logic_tree, list):
            for sec in self.logic_tree:
                if sec.get("section") == name: return sec.get("content")
        return None

    def _add_case(self, tipo, desc, inputs, resultado):
        row = {
            "ID_Caso": str(self.case_id),
            "Tipo": tipo,
            "Descripcion": desc,
            "Resultado_Esperado": resultado,
            **inputs
        }
        self.scenarios.append(row)
        self.case_id += 1