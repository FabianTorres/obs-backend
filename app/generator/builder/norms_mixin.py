class NormGeneratorMixin:
    def _generate_norm_cases(self, norm_block, full_context, vars_block):
        if not norm_block: return
        instr_list = norm_block if isinstance(norm_block, list) else [norm_block]
        
        # --- FASE 0: HIDRATACIÓN (CONTEXTO RICO) ---
        rich_context = full_context.copy()
        all_involved_vars = self._extract_leaf_vars(instr_list)
        
        for var in all_involved_vars:
            if (var.startswith("Vx") or var.startswith("C")) and var not in rich_context:
                rich_context[var] = 1000  # ACTUALIZADO: Valor base 1000 para ser consistente
        
        condition_node = None
        calc_nodes = []
        for item in instr_list:
            if isinstance(item, dict) and "op" in item and item["op"] in [">", "<", ">=", "<=", "=", "≠"]:
                condition_node = item
            elif isinstance(item, dict) and "target" in item:
                calc_nodes.append(item)

        if not condition_node:
            self._add_norm_result(rich_context, calc_nodes, "Norma Genérica", "Ejecución Estándar")
            return

        op = condition_node["op"]
        left_node = condition_node["left"]
        right_node = condition_node["right"]
        
        # Variaciones
        variations = self._generate_function_variations(right_node, rich_context)
        
        if not variations:
            variations = [{"label": "", "context": rich_context}]
            
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
            
            left_vars = self._extract_leaf_vars(left_node)
            target_var = left_vars[0] if left_vars else "Unknown"
            
            # --- CASO OK ---
            inputs_ok = self._filter_inputs(ctx_variant)
            val_ok = self._calculate_boundary_value(op, right_val, force_true=True)
            self._smart_set_input(inputs_ok, target_var, val_ok)
            
            for v in left_vars[1:]:
                if v not in inputs_ok and v in rich_context: 
                    inputs_ok[v] = rich_context[v]

            ctx_ok = {**inputs_ok, **self.parameters}
            vars_ok = self._calculate_variables(vars_block, ctx_ok)
            full_ctx_ok = {**ctx_ok, **vars_ok}
            
            self._add_norm_result(full_ctx_ok, calc_nodes, "Norma OK", f"Borde Cumple {label_suffix} ({target_var}={val_ok} vs {right_val})")

            # --- CASO NK ---
            inputs_nk = self._filter_inputs(ctx_variant)
            val_nk = self._calculate_boundary_value(op, right_val, force_true=False)
            self._smart_set_input(inputs_nk, target_var, val_nk)
            
            for v in left_vars[1:]:
                if v not in inputs_nk and v in rich_context:
                    inputs_nk[v] = rich_context[v]

            ctx_nk = {**inputs_nk, **self.parameters}
            vars_nk = self._calculate_variables(vars_block, ctx_nk)
            full_ctx_nk = {**ctx_nk, **vars_nk}
            
            self._add_norm_result(full_ctx_nk, calc_nodes, "Norma NK", f"Borde No Cumple {label_suffix} ({target_var}={val_nk} vs {right_val})", is_nk=True)
            
            # --- CASO ESPECIAL: VALIDA POS=0 ---
            if need_pos_zero_check:
                inputs_pz = self._filter_inputs(ctx_variant)
                self._smart_set_input(inputs_pz, target_var, 1) 
                
                for v in left_vars[1:]:
                    if v not in inputs_pz and v in rich_context: 
                        inputs_pz[v] = rich_context[v]
                
                ctx_pz = {**inputs_pz, **self.parameters}
                vars_pz = self._calculate_variables(vars_block, ctx_pz)
                full_ctx_pz = {**ctx_pz, **vars_pz}
                
                self._add_norm_result(full_ctx_pz, calc_nodes, "Valida POS=0", f"Prueba Interna {label_suffix} (Forzando {target_var}=1)", is_nk=True)

    def _generate_function_variations(self, logic_node, base_context):
        variations = []
        target_nodes = self._find_all_function_nodes(logic_node, ["MAX", "MIN", "POS"])
        seen_labels = set()

        for node in target_nodes:
            fname = node["function"]
            args = node["args"]
            
            if fname in ["MAX", "MIN"]:
                all_involved = []
                for arg in args: all_involved.extend(self._get_recursive_roots(arg))
                
                for i, arg in enumerate(args):
                    roots = self._get_recursive_roots(arg)
                    if not roots: continue
                    
                    new_ctx = base_context.copy()
                    for r in all_involved: 
                        if r not in self.parameters: new_ctx[r] = 10
                    for r in roots: 
                        if r not in self.parameters: new_ctx[r] = 1000
                    
                    label = f"(Gana Arg{i+1} de {fname})"
                    if label not in seen_labels:
                        variations.append({"label": label, "context": new_ctx})
                        seen_labels.add(label)

            elif fname == "POS":
                arg_tree = args[0]
                pos_atoms, neg_atoms = self._analyze_polarity(arg_tree)
                
                pos_roots = self._resolve_roots(pos_atoms)
                neg_roots = self._resolve_roots(neg_atoms)
                
                if not pos_roots and not neg_roots: continue

                if pos_roots:
                    ctx_activa = base_context.copy()
                    all_involved = pos_roots + neg_roots
                    for r in all_involved: 
                        if r not in self.parameters: ctx_activa[r] = 10
                    for r in pos_roots: 
                        if r not in self.parameters: ctx_activa[r] = 1000
                    
                    label_activa = "(Activa POS)"
                    if label_activa not in seen_labels:
                        variations.append({"label": label_activa, "context": ctx_activa})
                        seen_labels.add(label_activa)

                if neg_roots:
                    ctx_anula = base_context.copy()
                    all_involved = pos_roots + neg_roots
                    for r in all_involved:
                        if r not in self.parameters: ctx_anula[r] = 10
                    for r in neg_roots:
                        if r not in self.parameters: ctx_anula[r] = 1000
                    
                    label_anula = "(Anula POS)"
                    if label_anula not in seen_labels:
                        variations.append({"label": label_anula, "context": ctx_anula})
                        seen_labels.add(label_anula)

        return variations

    def _find_all_function_nodes(self, node, function_names):
        found = []
        if isinstance(node, dict):
            if "function" in node and node["function"] in function_names:
                found.append(node)
            for k, v in node.items():
                if isinstance(v, dict):
                    found.extend(self._find_all_function_nodes(v, function_names))
                elif isinstance(v, list):
                    for item in v:
                        found.extend(self._find_all_function_nodes(item, function_names))
        return found

    def _analyze_polarity(self, tree, current_sign=1):
        pos_atoms = []
        neg_atoms = []
        if isinstance(tree, str):
            if current_sign > 0: pos_atoms.append(tree)
            else: neg_atoms.append(tree)
            return pos_atoms, neg_atoms
        if isinstance(tree, dict) and "op" in tree:
            op = tree["op"]
            if op == "+":
                p1, n1 = self._analyze_polarity(tree.get("left") or tree.get("terms")[0], current_sign)
                p2, n2 = self._analyze_polarity(tree.get("right") or tree.get("terms")[1], current_sign)
                pos_atoms += p1 + p2; neg_atoms += n1 + n2
            elif op in ["-", "–"]:
                p1, n1 = self._analyze_polarity(tree["left"], current_sign)
                p2, n2 = self._analyze_polarity(tree["right"], current_sign * -1) 
                pos_atoms += p1 + p2; neg_atoms += n1 + n2
            elif op == "*":
                p1, n1 = self._analyze_polarity(tree["left"], current_sign)
                p2, n2 = self._analyze_polarity(tree["right"], current_sign)
                pos_atoms += p1 + p2; neg_atoms += n1 + n2
        return pos_atoms, neg_atoms

    def _resolve_roots(self, atoms):
        roots = []
        for atom in atoms:
            if atom in self.var_definitions:
                roots.extend(self._get_recursive_roots(self.var_definitions[atom]))
            elif atom.startswith("Vx") or atom.startswith("C"):
                roots.append(atom)
        return roots

    def _add_norm_result(self, context, calc_nodes, tipo, desc, is_nk=False):
        if is_nk:
            res_str = "No cumple Norma"
        else:
            results = []
            current_context = context
            for item in calc_nodes:
                name = item["target"]
                val = self.math_engine.evaluate(item["logic"], current_context)
                if isinstance(val, float) and val.is_integer(): val = int(val)
                current_context[name] = val 
                results.append(f"{name}={val}")
            res_str = " ".join(results) if results else "Cumple"

        inputs_only = self._filter_inputs(context)
        self._add_case(tipo, desc, inputs_only, res_str)