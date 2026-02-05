class BuilderUtilsMixin:
    def _map_variable_definitions(self):
        definitions = {}
        vars_block = self._find_section("Variables")
        if vars_block:
            for item in vars_block:
                if "target" in item:
                    definitions[item["target"]] = item["logic"]
        return definitions

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

    def _smart_set_input(self, inputs_dict, target, value):
        inputs_dict[target] = value
        if target in self.var_definitions:
            definition = self.var_definitions[target]
            if isinstance(definition, str):
                self._smart_set_input(inputs_dict, definition, value)

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

    def _filter_inputs(self, context):
        return {k: v for k, v in context.items() if k not in self.parameters and (k in self.var_definitions or k.startswith("Vx") or k.startswith("C"))}