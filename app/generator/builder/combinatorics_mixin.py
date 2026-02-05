import itertools

class CombinatoricsMixin:
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