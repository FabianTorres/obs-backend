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

    def _generate_nk_cases(self, cond_block, golden_inputs):
        """
        Genera los casos de prueba NK (No Cumple) en el reporte.
        Usa _generate_nk_combinations para calcular los inputs de ruptura.
        """
        # 1. Obtenemos los escenarios que rompen la lógica (usando Sabotaje Proporcional)
        bad_scenarios = self._generate_nk_combinations(cond_block)
        
        for i, bad_inputs in enumerate(bad_scenarios):
            # 2. Mezclamos con los inputs dorados (Golden)
            # Esto asegura que el resto de variables tengan valores válidos y solo falle lo que queremos.
            case_inputs = golden_inputs.copy()
            
            # Sobreescribimos con los valores "malos"
            # (Ej: REX_2=1 o Restas=Alto)
            case_inputs.update(bad_inputs)
            
            # 3. Generamos descripción dinámica
            actives = [k for k in bad_inputs.keys() if k not in self.parameters]
            desc = f"Fallo forzado en Bloque #{i+1} (Trigger: {', '.join(actives[:4])})"
            
            self._add_case("Cond. NK", desc, case_inputs, "No cumple Condición")

    def _generate_nk_combinations(self, logic_block):
        """
        Genera una lista de inputs donde CADA uno rompe la condición lógica dada.
        Implementa 'Sabotaje Proporcional' para probar la existencia de restas.
        """
        nk_scenarios = []
        and_components = self._flatten_logic(logic_block, "AND")
        
        for comp in and_components:
            or_options = self._flatten_logic(comp, "OR")
            
            merged_bad_input = {}
            possible = True
            complex_handled = False
            
            for opt in or_options:
                # -----------------------------------------------------------
                # INTENTO 1 (PRIORIDAD ALTA): Expresiones Complejas y Signos
                # -----------------------------------------------------------
                if isinstance(opt, dict) and "op" in opt:
                    op = opt["op"]
                    if op in ["=", ">", "<", ">=", "<=", "≠"]:
                        left_node = opt["left"]
                        right_node = opt["right"]
                        
                        # Analizamos estructura de suma/resta o POS
                        pos_terms = []
                        neg_terms = []
                        
                        analysis_node = left_node
                        if isinstance(left_node, dict) and left_node.get("function") == "POS":
                             if "args" in left_node and left_node["args"]:
                                analysis_node = left_node["args"][0]

                        self._decompose_additive_expression(analysis_node, pos_terms, neg_terms, current_sign=1)
                        
                        if len(pos_terms) + len(neg_terms) > 1 or len(neg_terms) > 0:
                            complex_handled = True
                            
                            ctx = self.parameters.copy()
                            ref_val = self.math_engine.evaluate(right_node, ctx)
                            
                            # Aseguramos un entero base para cálculos
                            base_threshold = int(ref_val) if isinstance(ref_val, (int, float)) else 0

                            # --- CORRECCIÓN DE LÓGICA DE SABOTAJE ---

                            # CASO A: Queremos que la suma sea PEQUEÑA (Romper > o >=)
                            if op in [">", ">="]:
                                # SOLO aplicamos sabotaje (inflar) si hay negativos para frenar
                                if neg_terms:
                                    margin = 2000
                                    target_pos_sum = base_threshold + margin
                                    val_pos = int(target_pos_sum / max(1, len(pos_terms))) + 1
                                    for p in pos_terms: self._smart_set_input(merged_bad_input, p, val_pos)
                                    
                                    target_neg_sum = margin + 1000 
                                    val_neg = int(target_neg_sum / max(1, len(neg_terms))) + 1
                                    for n in neg_terms: self._smart_set_input(merged_bad_input, n, val_neg)
                                else:
                                    # Si NO hay negativos (ej: A+B > 0), la única forma de romper es ir a 0
                                    for p in pos_terms: self._smart_set_input(merged_bad_input, p, 0)

                            # CASO B: Queremos que la suma sea GRANDE (Romper < o <=)
                            elif op in ["<", "<="]:
                                margin = 2000
                                target_pos_sum = base_threshold + margin
                                val_pos = int(target_pos_sum / max(1, len(pos_terms))) + 1
                                for p in pos_terms: self._smart_set_input(merged_bad_input, p, val_pos)
                                for n in neg_terms: self._smart_set_input(merged_bad_input, n, 0)
                            
                            # CASO C: Otros
                            else:
                                if pos_terms:
                                    target = pos_terms[0]
                                    bv = self._get_broken_value(op, ref_val)
                                    if bv is not None: self._smart_set_input(merged_bad_input, target, bv)
                                    
                # -----------------------------------------------------------
                # INTENTO 2 (FALLBACK): Predicados Simples
                # -----------------------------------------------------------
                if not complex_handled:
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
                    else:
                        possible = False
            
            if possible and merged_bad_input:
                nk_scenarios.append(merged_bad_input)
                
        return nk_scenarios

    def _get_broken_value(self, op, ref_val):
        """Helper para calcular un valor que rompa la condición"""
        if isinstance(ref_val, float) and ref_val.is_integer(): ref_val = int(ref_val)
        
        if op == "=": return ref_val + 1 
        if op == "≠": return ref_val     
        if op == ">": return 0           
        if op == ">=": return ref_val - 1
        if op == "<": return ref_val + 1000 
        if op == "<=": return ref_val + 1
        return None

    def _try_expand_complex_comparison(self, logic_node):
        """
        Expande lógica compleja. AHORA SOPORTA MULTIPLICACIÓN EN > 0.
        (A * B * C) > 0  --> [ {A>0, B>0, C>0} ]
        """
        if isinstance(logic_node, dict) and "op" in logic_node:
            op = logic_node["op"]
            right = logic_node["right"]
            
            # 1. Detección de Multiplicación (A * B * C > 0)
            if op in [">", ">="] and (right == 0 or right == "0"):
                left = logic_node["left"]
                factors = []
                self._decompose_multiplication(left, factors)
                
                if len(factors) > 1:
                    # Devolvemos una lista con UN solo elemento (AND implícito)
                    # que contiene múltiples restricciones para _extract_predicates
                    compound_constraint = []
                    for f in factors:
                        compound_constraint.append({"op": op, "left": f, "right": right})
                    return [compound_constraint]

            # 2. Detección de Sumas/Restas (Lógica original)
            if op in [">", ">=", "<", "<=", "≠"]:
                left = logic_node["left"]
                is_pos_wrapper = False
                if isinstance(left, dict) and left.get("function") == "POS":
                    left = left["args"][0]
                    is_pos_wrapper = True

                pos_terms = []
                neg_terms = []
                self._decompose_additive_expression(left, pos_terms, neg_terms, current_sign=1)
                
                variants = []
                if op in [">", ">="]:
                    for var in pos_terms: variants.append({"op": op, "left": var, "right": right})
                elif op in ["<", "<="]: return [logic_node] 
                elif op == "≠":
                    all_terms = pos_terms + neg_terms
                    for var in all_terms: variants.append({"op": op, "left": var, "right": right})

                if variants: return variants
        return [logic_node]

    def _decompose_multiplication(self, node, factors):
        """Descompone recursivamente A * B * C en [A, B, C]"""
        if isinstance(node, dict) and node.get("op") == "*":
            self._decompose_multiplication(node["left"], factors)
            self._decompose_multiplication(node["right"], factors)
        else:
            factors.append(node)

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
                if op in [">", ">="]:
                    
                     if new_val < 1000: new_val = 1000
                if op in ["<", "<="]: 
                     if new_val < 0: new_val = 0
                
                # REGLA DE ORO PARA CEROS:
                # Si la lógica pide "= 0", respetamos el 0 absoluto (no activamos)
                if op == "=" and target_val == 0:
                     new_val = 0
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
    
    def _extract_predicates(self, block):
        """
        Extrae predicados simples. AHORA SOPORTA MULTIPLICACIÓN EN DESIGUALDADES POSITIVAS.
        Si ve: (A * B * C) > 0 -> Genera predicados: A>0, B>0, C>0.
        """
        preds = []
        if isinstance(block, list):
            for item in block: preds.extend(self._extract_predicates(item))
        elif isinstance(block, dict):
            # --- LÓGICA DE INVERSIÓN (1 - Var > 0  =>  Var < 1) ---
            if "op" in block and block["op"] in [">", ">="] and block["right"] == 0:
                left = block["left"]
                if isinstance(left, dict) and left.get("op") == "-":
                    # Chequeamos si es (1 - Var)
                    const_left = left.get("left")
                    var_right = left.get("right")
                    
                    # Si la izquierda es un número (ej: 1)
                    if isinstance(const_left, (int, float, str)) and str(const_left).isdigit():
                         # Invertimos la lógica: Var < Constant
                         constant_part = const_left
                         variable_part = var_right
                         
                         # Extraemos la variable objetivo
                         atoms = self._extract_leaf_vars(variable_part)
                         if atoms:
                             # Generamos predicado INVERTIDO: Var < 1
                             preds.append({"target": atoms[0], "op": "<", "right_tree": constant_part, "value": [0]})
                             return preds
            # --------------------------------------------------------
            # Lógica especial para Multiplicación en Desigualdades Positivas
            if "op" in block and block["op"] in [">", ">="] and block["right"] == 0:
                left = block["left"]
                # Si el lado izquierdo es una multiplicación
                if isinstance(left, dict) and left.get("op") == "*":
                    # Descomponemos: A * B > 0  =>  A > 0 AND B > 0
                    # Generamos recursivamente predicados para ambos lados
                    term1 = {"op": block["op"], "left": left["left"], "right": 0}
                    term2 = {"op": block["op"], "left": left["right"], "right": 0}
                    preds.extend(self._extract_predicates(term1))
                    preds.extend(self._extract_predicates(term2))
                    return preds

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