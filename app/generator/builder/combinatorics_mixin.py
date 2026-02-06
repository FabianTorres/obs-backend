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

    def _generate_nk_combinations(self, logic_block):
        """
        Genera una lista de inputs donde CADA uno rompe la condición lógica dada.
        Útil para probar ramas 'SINO' o 'ELSE'.
        """
        nk_scenarios = []
        and_components = self._flatten_logic(logic_block, "AND")
        
        for comp in and_components:
            or_options = self._flatten_logic(comp, "OR")
            
            merged_bad_input = {}
            possible = True
            
            for opt in or_options:
                # Intento 1: Predicados Simples (Var = Val)
                preds = self._extract_predicates(opt)
                
                if preds:
                    p = preds[0]
                    target = p['target']
                    op = p['op']
                    right_tree = p['right_tree']
                    
                    ctx = self.parameters.copy()
                    ref_val = self.math_engine.evaluate(right_tree, ctx)
                    broken_val = self._get_broken_value(op, ref_val)
                    
                    if broken_val is not None:
                        self._smart_set_input(merged_bad_input, target, broken_val)
                    else:
                        possible = False
                
                # Intento 2: Expresiones Complejas (Suma = Val, etc.) - NUEVO
                elif isinstance(opt, dict) and "op" in opt:
                    op = opt["op"]
                    if op in ["=", ">", "<", ">=", "<=", "≠"]:
                        # Romper una expresión compleja
                        left_node = opt["left"]
                        right_node = opt["right"]
                        ctx = self.parameters.copy()
                        ref_val = self.math_engine.evaluate(right_node, ctx)
                        
                        # Estrategia: Tomar la primera variable hoja y forzarla
                        atoms = self._extract_leaf_vars(left_node)
                        if atoms:
                            target = atoms[0] # Ej: REX_2
                            # Intentamos romper la igualdad manipulando esa variable
                            broken_val = self._get_broken_value(op, ref_val)
                            
                            if broken_val is not None:
                                self._smart_set_input(merged_bad_input, target, broken_val)
                            else:
                                possible = False
                        else:
                            possible = False # No hay variables para manipular
                    else:
                        possible = False
                else:
                    possible = False # No sabemos cómo romper esto
            
            if possible and merged_bad_input:
                nk_scenarios.append(merged_bad_input)
                
        return nk_scenarios

    def _get_broken_value(self, op, ref_val):
        """Helper para calcular un valor que rompa la condición"""
        if isinstance(ref_val, float) and ref_val.is_integer(): ref_val = int(ref_val)
        
        if op == "=": return ref_val + 1 # Si pide 0, damos 1
        if op == "≠": return ref_val     # Si pide != 1, damos 1
        if op == ">": return 0           # Si pide > 0, damos 0 (o ref_val si es mayor)
        if op == ">=": return ref_val - 1
        if op == "<": return ref_val + 1000 # Exageramos para romper
        if op == "<=": return ref_val + 1
        return None

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
                        for var in atoms: 
                            variants.append({"op": op, "left": var, "right": right})
                        return variants
                        
        return [logic_node]

    def _generate_nk_cases(self, cond_block, golden_inputs):
        """Genera casos NK para la Condition de Entrada"""
        and_components = self._flatten_logic(cond_block, "AND")
        for i, comp in enumerate(and_components):
            bad_inputs = golden_inputs.copy()
            or_options = self._flatten_logic(comp, "OR")
            
            merged_bad_input = {}
            desc_parts = []
            
            for opt in or_options:
                preds = self._extract_predicates(opt)
                if not preds: continue
                p = preds[0]
                ref_val = self.math_engine.evaluate(p['right_tree'], {**golden_inputs, **self.parameters})
                broken_val = self._get_broken_value(p['op'], ref_val)
                if broken_val is not None:
                    self._smart_set_input(bad_inputs, p['target'], broken_val)
                    desc_parts.append(p['target'])

            if desc_parts:
                desc = f"Fallo forzado en {', '.join(desc_parts)} (Bloque #{i+1})"
                self._add_case("Cond. NK", desc, bad_inputs, "No cumple Condición")

    def _solve_for_true(self, predicates):
        current_inputs = self.parameters.copy()
        
        # Hidratación Inteligente
        for p in predicates:
            all_vars = self._extract_leaf_vars(p['right_tree'])
            if 'target' in p: all_vars.append(p['target'])
            
            for var in all_vars:
                if var not in current_inputs and (var.startswith("Vx") or var.startswith("C")):
                    current_inputs[var] = 1000 

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
                
                # Boosting
                if op in [">", ">="]:
                     if new_val < 1000:
                         new_val = 1000

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
                if split_op == "AND" and op in ["AND", ".y.", ".Y.", "Y"]: is_target_op = True
                if split_op == "OR" and op in ["OR", ".o.", ".O.", "O"]: is_target_op = True
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