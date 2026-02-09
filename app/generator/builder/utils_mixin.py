class BuilderUtilsMixin:
    def _map_variable_definitions(self):
        definitions = {}
        vars_block = self._find_section("Variables")
        if vars_block:
            for item in vars_block:
                if "target" in item:
                    definitions[item["target"]] = item.get("logic")
        return definitions

    def _find_section(self, name):
        if hasattr(self, 'logic_tree') and isinstance(self.logic_tree, dict):
             if name == "Variables": return self.logic_tree.get("variables", [])
             if name == "Condicion_Entrada": return self.logic_tree.get("condicion_entrada", [])
             if name == "Norma_Observacion": return self.logic_tree.get("norma_observacion", [])
        
        if isinstance(self.logic_tree, list):
            for sec in self.logic_tree:
                if sec.get("section") == name: return sec.get("content")
        return []

    def _add_case(self, tipo, desc, inputs, resultado):
        self.case_id += 1
        filtered_inputs = self._filter_inputs(inputs)
        inputs_str = "; ".join([f"{k}={v}" if k.startswith("Vx") else f"[{k[1:]}]={v}" for k, v in filtered_inputs.items()])
        row = {
            "ID_Caso": str(self.case_id),
            "Tipo": tipo,
            "Descripcion": desc,
            "Resultado_Esperado": resultado,
            "Contexto_Visual": inputs_str,
            **filtered_inputs
        }
        self.scenarios.append(row)

    def _describe_scenario(self, inputs):
        active_vars = [f"{k}={v}" for k, v in inputs.items() if v != 0 and k not in self.parameters]
        if not active_vars: return "Default"
        return f"Activando {', '.join(active_vars[:5])}..."
    
    def _get_broken_value(self, op, ref_value):
        if isinstance(ref_value, float) and ref_value.is_integer(): ref_value = int(ref_value)
        if op == ">": return 0 
        elif op == ">=": return ref_value - 1
        elif op == "<": return ref_value + 1000 
        elif op == "<=": return ref_value + 1
        elif op == "=": return ref_value + 1
        elif op == "≠": return ref_value
        return None

    def _extract_predicates(self, block):
        preds = []
        if isinstance(block, list):
            for item in block: preds.extend(self._extract_predicates(item))
        elif isinstance(block, dict):
            if "op" in block and block["op"] in [">", "<", ">=", "<=", "=", "≠", "IN"]:
                left = block["left"]
                right = block["right"]
                if isinstance(left, str):
                    preds.append({"target": left, "op": block["op"], "right_tree": right, "value": [0]})
                elif isinstance(left, dict):
                    atoms = self._extract_leaf_vars(left)
                    if atoms:
                        leader = atoms[0]
                        preds.append({"target": leader, "op": block["op"], "right_tree": right, "value": [0]})
            for k, v in block.items():
                if isinstance(v, (dict, list)): preds.extend(self._extract_predicates(v))
        return preds

    def _extract_leaf_vars(self, node):
        vars_found = []
        if isinstance(node, str):
            if len(node) > 0 and node not in ["AND", "OR", "Y", "O", "POS", "MIN", "MAX", "SI", "NO", "SINO", "+", "-", "*", "/", "div", "mod"]:
                if node.isalnum() or node.startswith("Vx") or "_" in node:
                    vars_found.append(node)
        elif isinstance(node, list):
            for item in node: vars_found.extend(self._extract_leaf_vars(item))
        elif isinstance(node, dict):
            for k, v in node.items():
                if k in ["op", "function", "type", "section"]: continue
                vars_found.extend(self._extract_leaf_vars(v))
        return vars_found

    def _smart_set_input(self, inputs_dict, target, value):
        # 1. Macros / Delegación
        if hasattr(self, 'macros') and target in self.macros:
            inputs_dict[target] = value
            leaves = self._extract_leaf_vars(self.macros[target])
            delegates = [v for v in leaves if v.startswith("C") or v.startswith("Vx")]
            if delegates:
                primary_delegate = delegates[0]
                val_to_set = 1000 if (isinstance(value, (int, float)) and value > 0) else 0
                self._smart_set_input(inputs_dict, primary_delegate, val_to_set)
                return

        # 2. Guardado Normal
        inputs_dict[target] = value
        
        # 3. Propagación Recursiva (Resolución hacia atrás)
        if hasattr(self, 'var_definitions') and target in self.var_definitions:
            definition = self.var_definitions[target]
            
            # Alias
            if isinstance(definition, str):
                self._smart_set_input(inputs_dict, definition, value)

            # Lógica Condicional (La magia ocurre aquí)
            elif isinstance(definition, dict) and definition.get("type") == "conditional":
                cond = definition.get("cond")
                val_true = definition.get("true")
                val_false = definition.get("false")
                
                solution = None
                
                # --- TRADUCCIÓN DE INTENCIONES ---
                
                # Intención VERDADERA: Coincidencia exacta O valor positivo alto (Heurística del Solver)
                is_true_intent = False
                if value == val_true: is_true_intent = True
                elif isinstance(val_true, (int, float)) and val_true == 1 and isinstance(value, (int, float)) and value >= 1:
                    is_true_intent = True
                
                # Intención FALSA: Coincidencia exacta O valor cero/negativo
                is_false_intent = False
                if value == val_false: is_false_intent = True
                elif isinstance(val_false, (int, float)) and val_false == 0 and isinstance(value, (int, float)) and value <= 0:
                    is_false_intent = True

                # ----------------------------------

                # Ejecutar Solver según intención
                if is_true_intent:
                    inputs_dict[target] = val_true 
                    if hasattr(self, '_generate_ok_combinations'):
                        solutions = self._generate_ok_combinations(cond)
                        if solutions: solution = solutions[0]

                elif is_false_intent:
                    inputs_dict[target] = val_false
                    if hasattr(self, '_generate_nk_combinations'):
                        solutions = self._generate_nk_combinations(cond)
                        if solutions: solution = solutions[0]
                
                # Inyectar solución encontrada
                if solution:
                    for k, v in solution.items():
                        if k != target:
                            self._smart_set_input(inputs_dict, k, v)

    def _find_function_node(self, node, function_names):
        if isinstance(node, dict):
            if "function" in node and node["function"] in function_names:
                return node
            for key in ["left", "right", "terms", "args", "cond", "true", "false", "cond_1", "val_1", "val_2"]:
                if key in node:
                    found = self._find_function_node(node[key], function_names)
                    if found: return found
            if isinstance(node.get("args"), list):
                for arg in node["args"]:
                    found = self._find_function_node(arg, function_names)
                    if found: return found
        elif isinstance(node, list):
            for item in node:
                found = self._find_function_node(item, function_names)
                if found: return found
        return None

    def _get_recursive_roots(self, node):
        leaf_vars = self._extract_leaf_vars(node)
        roots = []
        for var in leaf_vars:
            if hasattr(self, 'var_definitions') and var in self.var_definitions:
                roots.extend(self._get_recursive_roots(self.var_definitions[var]))
            else:
                roots.append(var)
        return roots

    def _calculate_boundary_value(self, op, threshold, force_true):
        base = float(threshold)
        if base.is_integer(): base = int(base)
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

    def _filter_inputs(self, context):
        filtered = {}
        sorted_keys = sorted(context.keys())
        for k in sorted_keys:
            v = context[k]
            if not (k.startswith("Vx") or k.startswith("C")): continue
            if v == 0: continue
            if k in self.parameters: continue
            filtered[k] = v
        return filtered