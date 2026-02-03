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

        # 3. VARIABLES
        vars_block = self._find_section("Variables")
        self._generate_variable_cases(vars_block, golden_inputs)

        # 4. Contexto Completo y Normas
        initial_context = {**golden_inputs, **self.parameters}
        computed_vars = self._calculate_variables(vars_block, initial_context)
        full_context = {**golden_inputs, **self.parameters, **computed_vars}
        self._generate_norm_cases(full_context)

        return self.scenarios

    # --- GENERACIÓN DE VARIABLES ---

    def _generate_variable_cases(self, block, base_inputs):
        if not block: return
        instr_list = block if isinstance(block, list) else [block]

        for instr in instr_list:
            target_name = instr["target"]
            logic = instr["logic"]
            
            # Usamos un despachador centralizado para resolver la lógica
            self._dispatch_logic_solver(target_name, logic, base_inputs, prefix="")

    def _dispatch_logic_solver(self, target_name, logic, base_inputs, prefix=""):
        """Decide qué estrategia usar según el tipo de lógica (Condicional, POS, MAX, Simple)"""
        
        # 1. Condicionales
        if isinstance(logic, dict) and "type" in logic and logic["type"].startswith("conditional"):
            self._solve_conditional_variable(target_name, logic, base_inputs, prefix)
        
        # 2. Funciones Especiales
        elif isinstance(logic, dict) and "function" in logic:
            fname = logic["function"]
            if fname == "POS":
                self._solve_pos_case(target_name, logic, base_inputs, prefix)
            elif fname in ["MAX", "MIN"]:
                self._solve_min_max_case(target_name, logic, base_inputs, prefix)
            else:
                self._solve_calculation_only(target_name, logic, base_inputs, prefix)
        
        # 3. Default
        else:
            self._solve_calculation_only(target_name, logic, base_inputs, prefix)

    def _solve_conditional_variable(self, var_name, logic_node, base_inputs, prefix=""):
        branches_to_test = []

        # Normalización de ramas (Standard vs Piecewise)
        if "cond" in logic_node:
            branches_to_test.append({"cond": logic_node["cond"], "val": logic_node["true"], "label": "Branch TRUE"})
            branches_to_test.append({"cond": None, "val": logic_node["false"], "label": "Branch FALSE"})
        elif "cond_1" in logic_node:
            branches_to_test.append({"cond": logic_node["cond_1"], "val": logic_node.get("val_1"), "label": "Rama 1"})
            if "cond_2" in logic_node and logic_node["cond_2"]:
                branches_to_test.append({"cond": logic_node["cond_2"], "val": logic_node.get("val_2"), "label": "Rama 2"})
            else:
                branches_to_test.append({"cond": None, "val": logic_node.get("val_2"), "label": "Rama Defecto"})

        # Procesar cada rama
        for branch in branches_to_test:
            condition = branch["cond"]
            value_logic = branch["val"] # ¡Aquí está el MAX o el 0!
            label = f"{prefix}{branch['label']}"

            # 1. Determinar inputs para entrar a la rama
            branch_inputs_list = []
            if condition:
                # Expansión combinatoria para entrar al IF
                triggers = self._generate_ok_combinations(condition)
                for t in triggers: branch_inputs_list.append({**base_inputs, **t})
            else:
                # Rama else/default usa base inputs
                branch_inputs_list.append(base_inputs.copy())

            # 2. Para cada forma de entrar, resolver la lógica interna
            for i, inputs_ctx in enumerate(branch_inputs_list):
                # Generamos una descripción de qué activó la rama
                desc_trigger = ""
                if condition:
                    actives = [f"{k}={v}" for k,v in inputs_ctx.items() if k not in base_inputs and k not in self.parameters]
                    if actives: desc_trigger = f" (Trigger: {', '.join(actives)})"
                
                final_label = f"{label}{desc_trigger}"
                
                # ¡RECURSIVIDAD MÁGICA!
                # En vez de calcular directo, le pedimos al dispatcher que analice el 'value_logic'.
                # Si es MAX, generará casos MAX. Si es 0, calculará directo.
                self._dispatch_logic_solver(var_name, value_logic, inputs_ctx, prefix=f"{final_label} -> ")

    def _solve_min_max_case(self, var_name, logic_node, base_inputs, prefix=""):
        """Genera casos donde gana el argumento A y casos donde gana B"""
        fname = logic_node["function"]
        args = logic_node["args"]
        
        # Simplificación: Solo tomamos los 2 primeros argumentos para contrastar
        if len(args) < 2:
            self._solve_calculation_only(var_name, logic_node, base_inputs, prefix)
            return

        arg_a = args[0]
        arg_b = args[1]
        
        vars_a = self._extract_leaf_vars(arg_a)
        vars_b = self._extract_leaf_vars(arg_b)

        # CASO 1: GANA A (Izquierda)
        inputs_a = base_inputs.copy()
        # Inflamos A, desinflamos B
        for v in vars_a: inputs_a[v] = 1000
        for v in vars_b: inputs_a[v] = 100
        
        # Ajuste para evitar empates si comparten variables
        if vars_a: inputs_a[vars_a[0]] += 50 

        self._finalize_and_add(var_name, logic_node, inputs_a, f"{prefix}{fname}: Gana Izq")

        # CASO 2: GANA B (Derecha)
        inputs_b = base_inputs.copy()
        # Inflamos B, desinflamos A
        for v in vars_a: inputs_b[v] = 100
        for v in vars_b: inputs_b[v] = 1000
        if vars_b: inputs_b[vars_b[0]] += 50

        self._finalize_and_add(var_name, logic_node, inputs_b, f"{prefix}{fname}: Gana Der")

    def _solve_pos_case(self, var_name, logic_node, base_inputs, prefix=""):
        expression_tree = logic_node["args"][0]
        atoms_positive = []
        atoms_negative = []
        self._decompose_additive_expression(expression_tree, atoms_positive, atoms_negative)

        if not atoms_negative:
            self._solve_calculation_only(var_name, logic_node, base_inputs, prefix)
            return

        base_val_pos = (len(atoms_negative) or 1) * 100
        base_val_neg = (len(atoms_positive) or 1) * 100

        # CASO 1: POSITIVO
        inputs_p = base_inputs.copy()
        for atom in atoms_positive: inputs_p[atom] = base_val_pos
        for atom in atoms_negative: inputs_p[atom] = base_val_neg
        if atoms_positive: inputs_p[atoms_positive[0]] += 1 
        
        self._finalize_and_add(var_name, logic_node, inputs_p, f"{prefix}POS > 0")

        # CASO 2: CERO
        inputs_z = base_inputs.copy()
        for atom in atoms_positive: inputs_z[atom] = base_val_pos
        for atom in atoms_negative: inputs_z[atom] = base_val_neg
        if atoms_negative: inputs_z[atoms_negative[0]] += 1
            
        self._finalize_and_add(var_name, logic_node, inputs_z, f"{prefix}POS = 0")

    def _solve_calculation_only(self, var_name, logic, base_inputs, prefix=""):
        self._finalize_and_add(var_name, logic, base_inputs, f"{prefix}Calc")

    def _finalize_and_add(self, var_name, logic, inputs, desc):
        """Helper final para calcular y agregar"""
        ctx = {**inputs, **self.parameters}
        val = self.math_engine.evaluate(logic, ctx)
        if isinstance(val, float) and val.is_integer(): val = int(val)
        self._add_case(var_name, desc, inputs, str(val))


    # --- UTILIDADES CORE (IGUAL QUE ANTES) ---
    def _generate_ok_combinations(self, logic_block):
        and_components = self._flatten_logic(logic_block, "AND")
        component_options = []
        for comp in and_components:
            or_options = self._flatten_logic(comp, "OR")
            final_options = []
            for opt in or_options:
                final_options.extend(self._try_expand_complex_comparison(opt))
            solved_options = []
            for option in final_options:
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

    def _try_expand_complex_comparison(self, logic_node):
        if isinstance(logic_node, dict) and "op" in logic_node:
            op = logic_node["op"]
            if op in [">", ">=", "≠"]:
                left = logic_node["left"]
                right = logic_node["right"]
                if isinstance(left, dict):
                    atoms = self._extract_leaf_vars(left)
                    if len(atoms) > 1:
                        variants = []
                        for var in atoms: variants.append({"op": op, "left": var, "right": right})
                        return variants
        return [logic_node]

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

    def _extract_predicates(self, block):
        preds = []
        if isinstance(block, list):
            for item in block: preds.extend(self._extract_predicates(item))
        elif isinstance(block, dict):
            if "op" in block and block["op"] in [">", "<", ">=", "<=", "=", "≠"]:
                left = block["left"]
                right = block["right"]
                if isinstance(left, str):
                    preds.append({"target": left, "op": block["op"], "right_tree": right})
                elif isinstance(left, dict):
                    atoms = self._extract_leaf_vars(left)
                    if atoms:
                        leader = atoms[0]
                        preds.append({"target": leader, "op": block["op"], "right_tree": right})
            for k, v in block.items():
                if isinstance(v, (dict, list)): preds.extend(self._extract_predicates(v))
        return preds

    def _extract_leaf_vars(self, node):
        vars_found = []
        if isinstance(node, str):
            if len(node) > 0 and node not in ["AND", "OR", "POS", "MIN", "MAX", "si", "no", "sino"]:
                if node.isalnum() or node.startswith("Vx") or "_" in node:
                    vars_found.append(node)
        elif isinstance(node, list):
            for item in node: vars_found.extend(self._extract_leaf_vars(item))
        elif isinstance(node, dict):
            for k, v in node.items():
                if k in ["op", "function", "type", "section"]: continue
                vars_found.extend(self._extract_leaf_vars(v))
        return vars_found

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
                elif op == "≠": new_val = target_val + 1
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