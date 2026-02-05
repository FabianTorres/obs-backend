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
        
        # Mapa de definiciones para búsqueda rápida
        self.var_definitions = self._map_variable_definitions()

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

        # 4. Contexto Completo para Normas
        initial_context = {**golden_inputs, **self.parameters}
        computed_vars = self._calculate_variables(vars_block, initial_context)
        full_context = {**golden_inputs, **self.parameters, **computed_vars}
        
        # 5. Generación de Casos de Norma
        norm_block = self._find_section("Norma_Observacion")
        self._generate_norm_cases(norm_block, full_context, vars_block)

        return self.scenarios

    # --- NUEVO: MAPEO DE VARIABLES ---
    def _map_variable_definitions(self):
        """Crea un diccionario {NombreVar: Logica} para resolver dependencias"""
        definitions = {}
        vars_block = self._find_section("Variables")
        if vars_block:
            for item in vars_block:
                if "target" in item:
                    definitions[item["target"]] = item["logic"]
        return definitions

    # --- GENERACIÓN DE VARIABLES ---

    def _generate_variable_cases(self, block, base_inputs):
        if not block: return
        instr_list = block if isinstance(block, list) else [block]

        for instr in instr_list:
            target_name = instr["target"]
            logic = instr["logic"]
            self._dispatch_logic_solver(target_name, logic, base_inputs, prefix="")

    def _dispatch_logic_solver(self, target_name, logic, base_inputs, prefix=""):
        if isinstance(logic, dict) and "type" in logic and logic["type"].startswith("conditional"):
            self._solve_conditional_variable(target_name, logic, base_inputs, prefix)
        elif isinstance(logic, dict) and "function" in logic:
            fname = logic["function"]
            if fname == "POS":
                self._solve_pos_case(target_name, logic, base_inputs, prefix)
            elif fname in ["MAX", "MIN"]:
                self._solve_min_max_case(target_name, logic, base_inputs, prefix)
            else:
                self._solve_calculation_only(target_name, logic, base_inputs, prefix)
        else:
            self._solve_calculation_only(target_name, logic, base_inputs, prefix)

    def _solve_conditional_variable(self, var_name, logic_node, base_inputs, prefix=""):
        branches_to_test = []
        if "cond" in logic_node:
            branches_to_test.append({"cond": logic_node["cond"], "val": logic_node["true"], "label": "Branch TRUE"})
            branches_to_test.append({"cond": None, "val": logic_node["false"], "label": "Branch FALSE"})
        elif "cond_1" in logic_node:
            branches_to_test.append({"cond": logic_node["cond_1"], "val": logic_node.get("val_1"), "label": "Rama 1"})
            if "cond_2" in logic_node and logic_node["cond_2"]:
                branches_to_test.append({"cond": logic_node["cond_2"], "val": logic_node.get("val_2"), "label": "Rama 2"})
            else:
                branches_to_test.append({"cond": None, "val": logic_node.get("val_2"), "label": "Rama Defecto"})

        for branch in branches_to_test:
            condition = branch["cond"]
            value_logic = branch["val"]
            label = f"{prefix}{branch['label']}"

            branch_inputs_list = []
            if condition:
                triggers = self._generate_ok_combinations(condition)
                for t in triggers: branch_inputs_list.append({**base_inputs, **t})
            else:
                branch_inputs_list.append(base_inputs.copy())

            for i, inputs_ctx in enumerate(branch_inputs_list):
                desc_trigger = ""
                if condition:
                    actives = [f"{k}={v}" for k,v in inputs_ctx.items() if k not in base_inputs and k not in self.parameters]
                    if actives: desc_trigger = f" (Trigger: {', '.join(actives)})"
                final_label = f"{label}{desc_trigger}"
                self._dispatch_logic_solver(var_name, value_logic, inputs_ctx, prefix=f"{final_label} -> ")

    def _solve_min_max_case(self, var_name, logic_node, base_inputs, prefix=""):
        fname = logic_node["function"]
        args = logic_node["args"]
        if len(args) < 2:
            self._solve_calculation_only(var_name, logic_node, base_inputs, prefix)
            return
        
        arg_a = args[0]
        arg_b = args[1]
        vars_a = self._extract_leaf_vars(arg_a)
        vars_b = self._extract_leaf_vars(arg_b)

        # GANA A
        inputs_a = base_inputs.copy()
        for v in vars_a: inputs_a[v] = 1000
        for v in vars_b: inputs_a[v] = 100
        if vars_a: inputs_a[vars_a[0]] += 50 
        self._finalize_and_add(var_name, logic_node, inputs_a, f"{prefix}{fname}: Gana Izq")

        # GANA B
        inputs_b = base_inputs.copy()
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

        inputs_p = base_inputs.copy()
        for atom in atoms_positive: inputs_p[atom] = base_val_pos
        for atom in atoms_negative: inputs_p[atom] = base_val_neg
        if atoms_positive: inputs_p[atoms_positive[0]] += 1 
        self._finalize_and_add(var_name, logic_node, inputs_p, f"{prefix}POS > 0")

        inputs_z = base_inputs.copy()
        for atom in atoms_positive: inputs_z[atom] = base_val_pos
        for atom in atoms_negative: inputs_z[atom] = base_val_neg
        if atoms_negative: inputs_z[atoms_negative[0]] += 1
        self._finalize_and_add(var_name, logic_node, inputs_z, f"{prefix}POS = 0")

    def _solve_calculation_only(self, var_name, logic, base_inputs, prefix=""):
        deps = self._extract_leaf_vars(logic)
        augmented_inputs = base_inputs.copy()
        for d in deps:
            if d not in self.parameters and d != var_name and d not in augmented_inputs:
                augmented_inputs[d] = 100
        self._finalize_and_add(var_name, logic, augmented_inputs, f"{prefix}Calc")

    def _finalize_and_add(self, var_name, logic, inputs, desc):
        ctx = {**inputs, **self.parameters}
        val = self.math_engine.evaluate(logic, ctx)
        if isinstance(val, float) and val.is_integer(): val = int(val)
        self._add_case(var_name, desc, inputs, str(val))

    # --- GENERACIÓN DE NORMAS (LÓGICA MEJORADA) ---

    def _generate_norm_cases(self, norm_block, full_context, vars_block):
        if not norm_block: return
        instr_list = norm_block if isinstance(norm_block, list) else [norm_block]
        
        condition_node = None
        calc_nodes = []
        for item in instr_list:
            if isinstance(item, dict) and "op" in item and item["op"] in [">", "<", ">=", "<=", "=", "≠"]:
                condition_node = item
            elif isinstance(item, dict) and "target" in item:
                calc_nodes.append(item)

        if not condition_node:
            self._add_norm_result(full_context, calc_nodes, "Norma Genérica", "Ejecución Estándar")
            return

        op = condition_node["op"]
        left_node = condition_node["left"]
        right_node = condition_node["right"]
        
        # Generar variaciones competitivas (Gana Beta vs Gana Epsilon)
        variations = self._generate_function_variations(right_node, full_context)
        
        if not variations:
            variations = [{"label": "", "context": full_context}]
            
        # Detectar si se requiere prueba de POS=0 en los cálculos (DIF, etc)
        # Nota: Se verifica si alguna de las fórmulas de cálculo usa la función POS
        need_pos_zero_check = False
        for node in calc_nodes:
            if self._find_function_node(node["logic"], ["POS"]):
                need_pos_zero_check = True
                break

        for variant in variations:
            ctx_variant = variant["context"]
            label_suffix = variant["label"]
            
            if label_suffix:
                recalc_vars = self._calculate_variables(vars_block, ctx_variant)
                ctx_variant = {**ctx_variant, **recalc_vars}

            right_val = self.math_engine.evaluate(right_node, ctx_variant)
            target_var = self._extract_leaf_vars(left_node)[0] 
            
            # --- CASO OK (POS > 0 implícito) ---
            inputs_ok = self._filter_inputs(ctx_variant)
            val_ok = self._calculate_boundary_value(op, right_val, force_true=True)
            self._smart_set_input(inputs_ok, target_var, val_ok)
            
            ctx_ok = {**inputs_ok, **self.parameters}
            vars_ok = self._calculate_variables(vars_block, ctx_ok)
            full_ctx_ok = {**ctx_ok, **vars_ok}
            
            self._add_norm_result(full_ctx_ok, calc_nodes, "Norma OK", f"Borde Cumple {label_suffix} ({target_var}={val_ok} vs {right_val})")

            # --- CASO NK (POS > 0 probable) ---
            inputs_nk = self._filter_inputs(ctx_variant)
            val_nk = self._calculate_boundary_value(op, right_val, force_true=False)
            self._smart_set_input(inputs_nk, target_var, val_nk)
            
            ctx_nk = {**inputs_nk, **self.parameters}
            vars_nk = self._calculate_variables(vars_block, ctx_nk)
            full_ctx_nk = {**ctx_nk, **vars_nk}
            
            self._add_norm_result(full_ctx_nk, calc_nodes, "Norma NK", f"Borde No Cumple {label_suffix} ({target_var}={val_nk} vs {right_val})", is_nk=True)
            
            # --- CASO ESPECIAL: VALIDA POS=0 (NUEVO) ---
            # Si hay cálculos con POS, forzamos la variable objetivo al mínimo (1)
            # para garantizar que la resta interna sea negativa y el POS devuelva 0.
            if need_pos_zero_check:
                inputs_pz = self._filter_inputs(ctx_variant)
                self._smart_set_input(inputs_pz, target_var, 1) # Forzamos suelo
                
                ctx_pz = {**inputs_pz, **self.parameters}
                vars_pz = self._calculate_variables(vars_block, ctx_pz)
                full_ctx_pz = {**ctx_pz, **vars_pz}
                
                self._add_norm_result(full_ctx_pz, calc_nodes, "Valida POS=0", f"Prueba Interna {label_suffix} (Forzando {target_var}=1)", is_nk=True)

    def _generate_function_variations(self, logic_node, base_context):
        """Busca funciones MAX/MIN y genera contextos manipulados"""
        variations = []
        target_node = self._find_function_node(logic_node, ["MAX", "MIN"])
        
        if target_node:
            fname = target_node["function"]
            args = target_node["args"]
            
            all_involved_roots = []
            for arg in args:
                all_involved_roots.extend(self._get_recursive_roots(arg))
            
            for i, arg in enumerate(args):
                roots_of_arg = self._get_recursive_roots(arg)
                if not roots_of_arg: continue 
                
                new_ctx = base_context.copy()
                
                # 1. Aplanar todo (10)
                for root in all_involved_roots:
                    if root not in self.parameters:
                        new_ctx[root] = 10
                
                # 2. Inflar al ganador (1000)
                for root in roots_of_arg:
                    if root not in self.parameters:
                        new_ctx[root] = 1000
                
                vars_in_arg = self._extract_leaf_vars(arg)
                arg_name = vars_in_arg[0] if vars_in_arg else f"Arg{i+1}"
                
                variations.append({
                    "label": f"(Gana {arg_name})",
                    "context": new_ctx
                })
        
        return variations

    def _find_function_node(self, node, function_names):
        if isinstance(node, dict):
            if "function" in node and node["function"] in function_names:
                return node
            if "left" in node:
                found = self._find_function_node(node["left"], function_names)
                if found: return found
            if "right" in node:
                found = self._find_function_node(node["right"], function_names)
                if found: return found
            if "terms" in node:
                for term in node["terms"]:
                    found = self._find_function_node(term, function_names)
                    if found: return found
        return None

    def _get_recursive_roots(self, node):
        leaf_vars = self._extract_leaf_vars(node)
        roots = []
        for var in leaf_vars:
            if var in self.var_definitions:
                roots.extend(self._get_recursive_roots(self.var_definitions[var]))
            else:
                roots.append(var)
        return roots

    def _calculate_boundary_value(self, op, threshold, force_true):
        base = float(threshold)
        if force_true:
            if op == ">": return base + 1
            if op == ">=": return base
            if op == "<": return base - 1
            if op == "<=": return base
            if op == "=": return base
            if op == "≠": return base + 1
        else: 
            if op == ">": return base
            if op == ">=": return base - 1
            if op == "<": return base
            if op == "<=": return base + 1
            if op == "=": return base + 1
            if op == "≠": return base
        return base

    def _add_norm_result(self, context, calc_nodes, tipo, desc, is_nk=False):
        if is_nk:
            res_str = "No cumple Norma"
        else:
            results = []
            for item in calc_nodes:
                name = item["target"]
                val = self.math_engine.evaluate(item["logic"], context)
                if isinstance(val, float) and val.is_integer(): val = int(val)
                results.append(f"{name}={val}")
            res_str = " ".join(results) if results else "Cumple"

        inputs_only = self._filter_inputs(context)
        self._add_case(tipo, desc, inputs_only, res_str)

    def _filter_inputs(self, context):
        return {k: v for k, v in context.items() if k not in self.parameters and (k in self.var_definitions or k.startswith("Vx") or k.startswith("C"))}

    # --- UTILIDADES CORE ---

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
                    self._smart_set_input(bad_inputs, target, broken_val)
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
                        self._smart_set_input(bad_inputs, target, broken_val)
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
                self._smart_set_input(current_inputs, target, new_val)
        return {k: v for k, v in current_inputs.items() if k not in self.parameters}

    def _smart_set_input(self, inputs_dict, target, value):
        inputs_dict[target] = value
        if target in self.var_definitions:
            definition = self.var_definitions[target]
            if isinstance(definition, str):
                self._smart_set_input(inputs_dict, definition, value)

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