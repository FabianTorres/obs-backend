class LogicProcessor:
    """
    Cerebro Matemático: Analiza, descompone y extrae predicados del árbol lógico.
    Separa la lógica de 'entender la fórmula' de la lógica de 'generar combinaciones'.
    """
    
    def extract_predicates(self, block):
        """
        Versión 'Puertas Abiertas': Si no es un predicado terminal,
        siempre recursa. Esto garantiza encontrar variables dentro de Y/O.
        """
        preds = []
        
        if isinstance(block, list):
            for item in block: preds.extend(self.extract_predicates(item))
            return preds
        
        if isinstance(block, dict):
            op = block.get("op")
            left = block.get("left")
            right = block.get("right")

            # --- CASO 1: Multiplicación en Desigualdades (A * B > 0) ---
            if op in [">", ">="] and self._is_zero(right):
                factors = []
                self._flatten_multiplication(left, factors)
                if len(factors) > 1:
                    for f in factors:
                        synthetic_block = {"op": op, "left": f, "right": 0}
                        preds.extend(self.extract_predicates(synthetic_block))
                    return preds

            # --- CASO 2: Inversión (1 - Var > 0) ---
            if op in [">", ">="] and self._is_zero(right):
                if isinstance(left, dict) and left.get("op") in ["-", "–"]:
                    const_left = left.get("left")
                    var_right = left.get("right")
                    if self._is_positive_constant(const_left):
                        atoms = self._extract_leaf_vars(var_right)
                        if atoms:
                            preds.append({"target": atoms[0], "op": "<", "right_tree": const_left, "value": [0]})
                            return preds

            # --- CASO 3: Predicados Terminales ---
            if op in [">", "<", ">=", "<=", "=", "≠", "IN"]:
                if isinstance(left, str):
                    preds.append({"target": left, "op": op, "right_tree": right, "value": [0]})
                elif isinstance(left, dict):
                    atoms = self._extract_leaf_vars(left)
                    if atoms:
                        leader = atoms[0]
                        preds.append({"target": leader, "op": op, "right_tree": right, "value": [0]})
                # ¡IMPORTANTE! Aquí retornamos para NO recursar más sobre esto mismo
                return preds
            
            # --- CASO 4: Recurso Universal (AND, OR, Y, O, Funciones...) ---
            # Si llegamos aquí, es porque no era un > o < terminal.
            # Entramos a explorar TODO lo que haya dentro.
            for k, v in block.items():
                if isinstance(v, (dict, list)): 
                    preds.extend(self.extract_predicates(v))
                    
        return preds

    def decompose_additive_expression(self, tree, pos_list, neg_list, current_sign=1):
        """Descompone sumas y restas en listas de términos positivos y negativos."""
        if isinstance(tree, str):
            if current_sign > 0: pos_list.append(tree)
            else: neg_list.append(tree)
            return
            
        if isinstance(tree, dict):
            # Manejo de POS() wrapper (Crucial para MI)
            if tree.get("function") == "POS":
                 args = tree.get("args", [])
                 if args: self.decompose_additive_expression(args[0], pos_list, neg_list, current_sign)
                 return

            if "op" in tree:
                op = tree["op"]
                if op == "+":
                    if "terms" in tree:
                        for term in tree["terms"]: 
                            self.decompose_additive_expression(term, pos_list, neg_list, current_sign)
                    else:
                        self.decompose_additive_expression(tree.get("left"), pos_list, neg_list, current_sign)
                        self.decompose_additive_expression(tree.get("right"), pos_list, neg_list, current_sign)
                elif op in ["-", "–"]:
                    self.decompose_additive_expression(tree.get("left"), pos_list, neg_list, current_sign)
                    self.decompose_additive_expression(tree.get("right"), pos_list, neg_list, current_sign * -1)

    def flatten_logic(self, node, split_op):
        """Aplana estructuras lógicas anidadas (AND/OR)."""
        items = []
        if isinstance(node, list):
            if split_op == "AND":
                for item in node: items.extend(self.flatten_logic(item, split_op))
            else: items.append(node)
            return items
            
        if isinstance(node, dict):
            if "op" in node:
                op = node["op"]
                is_target_op = False
                if split_op == "AND" and op in ["AND", ".y.", ".Y.", "Y"]: is_target_op = True
                if split_op == "OR" and op in ["OR", ".o.", ".O.", "O"]: is_target_op = True
                
                if is_target_op:
                    items.extend(self.flatten_logic(node["left"], split_op))
                    items.extend(self.flatten_logic(node["right"], split_op))
                    return items
        items.append(node)
        return items

    def _flatten_multiplication(self, node, factors):
        """Descompone recursivamente A * B * C en una lista [A, B, C]."""
        if isinstance(node, dict) and node.get("op") == "*":
            self._flatten_multiplication(node["left"], factors)
            self._flatten_multiplication(node["right"], factors)
        else:
            factors.append(node)

    def _extract_leaf_vars(self, node):
        """Extrae nombres de variables (hojas) de un sub-árbol."""
        vars_found = []
        if isinstance(node, str):
            if len(node) > 0 and node not in ["AND", "OR", "SI", "NO", "POS", "+", "-", "*", "/", "div", "mod"]:
                if node.isalnum() or node.startswith("Vx") or "_" in node:
                    vars_found.append(node)
        elif isinstance(node, list):
            for item in node: vars_found.extend(self._extract_leaf_vars(item))
        elif isinstance(node, dict):
            for k, v in node.items():
                if k in ["op", "function"]: continue
                vars_found.extend(self._extract_leaf_vars(v))
        return vars_found

    def _is_zero(self, val):
        return val == 0 or val == "0"

    def _is_positive_constant(self, val):
        try:
            return float(val) > 0
        except (ValueError, TypeError):
            return False