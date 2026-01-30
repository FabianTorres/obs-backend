import copy
import itertools
from app.generator.math_engine import MathEngine
from app.generator.sii_functions import SII_POS, SII_MIN, SII_MAX

class ScenarioBuilder:
    def __init__(self, logic_tree, parameters={}):
        self.logic_tree = logic_tree
        self.parameters = parameters
        self.math_engine = MathEngine()
        self.scenarios = []
        self.case_id = 11467

    def build_suite(self):
        """Genera la suite completa de pruebas"""
        
        # 1. Condición de Entrada
        cond_block = self._find_section("Condicion_Entrada")
        ok_scenarios_inputs = self._generate_ok_combinations(cond_block)
        
        golden_inputs = {} 
        for i, inputs in enumerate(ok_scenarios_inputs):
            if i == 0: golden_inputs = inputs
            desc = self._describe_scenario(inputs)
            self._add_case("Cond. OK", f"Camino válido #{i+1}: {desc}", inputs, "Cumple Condición")

        # 2. Casos NK
        self._generate_nk_cases(cond_block, golden_inputs)

        # 3. VARIABLES (Fuzzer + Branch Testing)
        vars_block = self._find_section("Variables")
        self._generate_variable_cases(vars_block, golden_inputs)

        # 4. Contexto Completo y Normas
        initial_context = {**golden_inputs, **self.parameters}
        computed_vars = self._calculate_variables(vars_block, initial_context)
        full_context = {**golden_inputs, **self.parameters, **computed_vars}
        self._generate_norm_cases(full_context)

        return self.scenarios

    # --- GENERACIÓN DE VARIABLES MEJORADA ---

    def _generate_variable_cases(self, block, base_inputs):
        if not block: return
        instr_list = block if isinstance(block, list) else [block]

        for instr in instr_list:
            target_name = instr["target"]
            logic = instr["logic"]
            
            # Detectamos si es un Condicional (Branch Testing)
            if isinstance(logic, dict) and "type" in logic and logic["type"].startswith("conditional"):
                self._solve_conditional_variable(target_name, logic, base_inputs)
            
            # Detectamos si es Función Especial (POS)
            elif isinstance(logic, dict) and "function" in logic:
                fname = logic["function"]
                if fname == "POS":
                    self._solve_pos_case(target_name, logic["args"][0], base_inputs)
                else:
                    self._solve_calculation_only(target_name, logic, base_inputs)
            
            # Default
            else:
                self._solve_calculation_only(target_name, logic, base_inputs)

    def _solve_conditional_variable(self, var_name, logic_node, base_inputs):
        """
        Genera casos para probar el SI (True) y el SINO (False) de una variable condicional.
        Ahora soporta expansión combinatoria (ORs) en la condición.
        """
        # 1. Extraer la lógica de la condición
        condition_logic = None
        if "cond" in logic_node: condition_logic = logic_node["cond"]
        elif "cond_1" in logic_node: condition_logic = logic_node["cond_1"]
        
        if not condition_logic:
            self._solve_calculation_only(var_name, logic_node, base_inputs)
            return

        # --- CASO A: FORZAR BRANCH TRUE (Expansión Combinatoria) ---
        # Usamos la misma lógica que en Condición de Entrada para detectar ORs
        # Esto nos devolverá una lista de inputs: [{Vx:511}, {Vx:512}]
        possible_trigger_inputs = self._generate_ok_combinations(condition_logic)
        
        for i, trigger_input in enumerate(possible_trigger_inputs):
            # Mezclamos con la base
            inputs_true = {**base_inputs, **trigger_input}
            
            # Calculamos resultado
            ctx_true = {**inputs_true, **self.parameters}
            val_true = self.math_engine.evaluate(logic_node, ctx_true)
            if isinstance(val_true, float) and val_true.is_integer(): val_true = int(val_true)
            
            # Generamos descripción dinámica (qué activamos)
            desc_vars = [f"{k}={v}" for k, v in trigger_input.items() if k not in self.parameters]
            desc = f"Branch TRUE (Opción {i+1}: {', '.join(desc_vars)})"
            
            self._add_case(var_name, desc, inputs_true, str(val_true))

        # --- CASO B: FORZAR BRANCH FALSE (Else / Sino) ---
        inputs_false = base_inputs.copy()
        
        # Para asegurar que entramos al False, deberíamos "limpiar" las variables que activan el True.
        # En el caso de OMICRON, la semilla no tiene Vx010599, así que vale 0. 0 != 511 y 0 != 512.
        # Funciona natural.
        
        ctx_false = {**inputs_false, **self.parameters}
        val_false = self.math_engine.evaluate(logic_node, ctx_false)
        if isinstance(val_false, float) and val_false.is_integer(): val_false = int(val_false)
        
        self._add_case(var_name, "Branch FALSE (Condición no cumple)", inputs_false, str(val_false))

    def _solve_pos_case(self, var_name, expression_tree, base_inputs):
        # Lógica de Balanza (IGUAL QUE ANTES)
        atoms_positive = []
        atoms_negative = []
        self._decompose_additive_expression(expression_tree, atoms_positive, atoms_negative)

        if not atoms_negative:
            self._solve_calculation_only(var_name, expression_tree, base_inputs)
            return

        base_val_pos = (len(atoms_negative) or 1) * 100
        base_val_neg = (len(atoms_positive) or 1) * 100

        # CASO 1: POSITIVO
        inputs_p = base_inputs.copy()
        for atom in atoms_positive: inputs_p[atom] = base_val_pos
        for atom in atoms_negative: inputs_p[atom] = base_val_neg
        if atoms_positive: inputs_p[atoms_positive[0]] += 1 
        
        ctx_p = {**inputs_p, **self.parameters}
        val_p = SII_POS(self._calculate_raw_expression(expression_tree, ctx_p))
        if isinstance(val_p, float) and val_p.is_integer(): val_p = int(val_p)
        self._add_case(var_name, "Borde POS > 0 (Diferencia = 1)", inputs_p, str(val_p))

        # CASO 2: CERO
        inputs_z = base_inputs.copy()
        for atom in atoms_positive: inputs_z[atom] = base_val_pos
        for atom in atoms_negative: inputs_z[atom] = base_val_neg
        if atoms_negative: inputs_z[atoms_negative[0]] += 1
            
        ctx_z = {**inputs_z, **self.parameters}
        val_z = SII_POS(self._calculate_raw_expression(expression_tree, ctx_z))
        if isinstance(val_z, float) and val_z.is_integer(): val_z = int(val_z)
        self._add_case(var_name, "Borde POS = 0 (Negativos ganan por 1)", inputs_z, str(val_z))

    def _solve_calculation_only(self, var_name, logic, base_inputs):
        ctx = {**base_inputs, **self.parameters}
        val = self.math_engine.evaluate(logic, ctx)
        if isinstance(val, float) and val.is_integer(): val = int(val)
        self._add_case(var_name, "Cálculo estándar (Semilla)", base_inputs, str(val))

    # --- RESTO DE MÉTODOS AUXILIARES (IGUAL QUE ANTES) ---
    
    def _generate_ok_combinations(self, logic_block):
        and_components = self._flatten_logic(logic_block, "AND")
        component_options = []
        for comp in and_components:
            or_options = self._flatten_logic(comp, "OR")
            solved_options = []
            for option in or_options:
                preds = self._extract_predicates(option)
                inputs = self._solve_for_true(preds)
                if inputs: solved_options.append(inputs)
            if solved_options: component_options.append(solved_options)
        
        all_combinations = []
        for combo in itertools.product(*component_options):
            merged_inputs = {}
            for d in combo: merged_inputs.update(d)
            all_combinations.append(merged_inputs)
        return all_combinations

    def _generate_nk_cases(self, cond_block, golden_inputs):
        and_components = self._flatten_logic(cond_block, "AND")
        for i, comp in enumerate(and_components):
            bad_inputs = golden_inputs.copy()
            comp_preds = self._extract_predicates(comp)
            
            if len(comp_preds) == 1:
                target = comp_preds[0]['target']
                op = comp_preds[0]['op']
                right_tree = comp_preds[0]['right_tree']
                context = {**golden_inputs, **self.parameters}
                ref_val = self.math_engine.evaluate(right_tree, context)
                broken_val = self._get_broken_value(op, ref_val)
                if broken_val is not None:
                    bad_inputs[target] = broken_val
                    self._add_case("Cond. NK", f"Fallo forzado en {target} (Bloque #{i+1})", bad_inputs, "No cumple Condición")
            else:
                description_parts = []
                possible_sabotage = True
                for p in comp_preds:
                    target = p['target']
                    op = p['op']
                    right_tree = p['right_tree']
                    context = {**golden_inputs, **self.parameters}
                    ref_val = self.math_engine.evaluate(right_tree, context)
                    broken_val = self._get_broken_value(op, ref_val)
                    if broken_val is not None:
                        bad_inputs[target] = broken_val
                        description_parts.append(target)
                    else: possible_sabotage = False
                
                if possible_sabotage:
                    desc = f"Fallo total del Grupo OR ({', '.join(description_parts)})"
                    self._add_case("Cond. NK", desc, bad_inputs, "No cumple Condición")

    def _decompose_additive_expression(self, tree, pos_list, neg_list, current_sign=1):
        if isinstance(tree, str):
            if current_sign > 0: pos_list.append(tree)
            else: neg_list.append(tree)
            return
        if isinstance(tree, dict) and "op" in tree:
            op = tree["op"]
            if op == "+":
                if "terms" in tree:
                    for term in tree["terms"]: self._decompose_additive_expression(term, pos_list, neg_list, current_sign)
                else:
                    self._decompose_additive_expression(tree["left"], pos_list, neg_list, current_sign)
                    self._decompose_additive_expression(tree["right"], pos_list, neg_list, current_sign)
            elif op == "-" or op == "–":
                self._decompose_additive_expression(tree["left"], pos_list, neg_list, current_sign)
                self._decompose_additive_expression(tree["right"], pos_list, neg_list, current_sign * -1)

    def _solve_for_true(self, predicates):
        current_inputs = self.parameters.copy()
        for i in range(2): 
            for p in predicates:
                target = p['target']
                op = p['op']
                target_val = self.math_engine.evaluate(p['right_tree'], current_inputs)
                new_val = current_inputs.get(target, 0)
                if op == ">": new_val = target_val + 1
                elif op == ">=": new_val = target_val
                elif op == "<": new_val = target_val - 1
                elif op == "<=": new_val = target_val
                elif op == "=": new_val = target_val
                elif op == "IN": new_val = p['value'][0] 
                current_inputs[target] = new_val
        return {k: v for k, v in current_inputs.items() if k not in self.parameters}

    def _flatten_logic(self, node, split_op):
        items = []
        if isinstance(node, list):
            if split_op == "AND":
                for item in node: items.extend(self._flatten_logic(item, split_op))
            else: items.append(node)
            return items
        if isinstance(node, dict):
            if "op" in node:
                op = node["op"]
                is_target_op = False
                if split_op == "AND" and op in ["AND", ".y.", ".Y."]: is_target_op = True
                if split_op == "OR" and op in ["OR", ".o.", ".O."]: is_target_op = True
                if is_target_op:
                    items.extend(self._flatten_logic(node["left"], split_op))
                    items.extend(self._flatten_logic(node["right"], split_op))
                    return items
        items.append(node)
        return items

    def _extract_predicates(self, block):
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

    def _describe_scenario(self, inputs):
        active_vars = [k for k, v in inputs.items() if v > 0 and k not in self.parameters]
        return f"Activando {', '.join(active_vars[:4])}..."
    
    def _get_broken_value(self, op, ref_value):
        if op == ">": return ref_value
        elif op == ">=": return ref_value - 1
        elif op == "<": return ref_value
        elif op == "<=": return ref_value + 1
        elif op == "=": return ref_value + 1
        elif op == "≠": return ref_value
        return None

    def _calculate_raw_expression(self, tree, context):
        return self.math_engine.evaluate(tree, context)