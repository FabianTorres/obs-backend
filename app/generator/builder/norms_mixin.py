class NormGeneratorMixin:
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
        
        # Variaciones competitivas
        variations = self._generate_function_variations(right_node, full_context)
        
        if not variations:
            variations = [{"label": "", "context": full_context}]
            
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
            
            # OK
            inputs_ok = self._filter_inputs(ctx_variant)
            val_ok = self._calculate_boundary_value(op, right_val, force_true=True)
            self._smart_set_input(inputs_ok, target_var, val_ok)
            
            ctx_ok = {**inputs_ok, **self.parameters}
            vars_ok = self._calculate_variables(vars_block, ctx_ok)
            full_ctx_ok = {**ctx_ok, **vars_ok}
            
            self._add_norm_result(full_ctx_ok, calc_nodes, "Norma OK", f"Borde Cumple {label_suffix} ({target_var}={val_ok} vs {right_val})")

            # NK
            inputs_nk = self._filter_inputs(ctx_variant)
            val_nk = self._calculate_boundary_value(op, right_val, force_true=False)
            self._smart_set_input(inputs_nk, target_var, val_nk)
            
            ctx_nk = {**inputs_nk, **self.parameters}
            vars_nk = self._calculate_variables(vars_block, ctx_nk)
            full_ctx_nk = {**ctx_nk, **vars_nk}
            
            self._add_norm_result(full_ctx_nk, calc_nodes, "Norma NK", f"Borde No Cumple {label_suffix} ({target_var}={val_nk} vs {right_val})", is_nk=True)
            
            # Especial POS=0
            if need_pos_zero_check:
                inputs_pz = self._filter_inputs(ctx_variant)
                self._smart_set_input(inputs_pz, target_var, 1) # Forzamos suelo
                
                ctx_pz = {**inputs_pz, **self.parameters}
                vars_pz = self._calculate_variables(vars_block, ctx_pz)
                full_ctx_pz = {**ctx_pz, **vars_pz}
                
                self._add_norm_result(full_ctx_pz, calc_nodes, "Valida POS=0", f"Prueba Interna {label_suffix} (Forzando {target_var}=1)", is_nk=True)

    def _generate_function_variations(self, logic_node, base_context):
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
                
                for root in all_involved_roots:
                    if root not in self.parameters:
                        new_ctx[root] = 10
                
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