from app.generator.sii_functions import SII_POS, SII_MIN, SII_MAX

class VariableSolverMixin:
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
            # Rama TRUE (OK)
            branches_to_test.append({
                "cond": logic_node["cond"], 
                "val": logic_node["true"], 
                "label": "Branch TRUE",
                "mode": "OK" # Modo Normal
            })
            # Rama FALSE (NK)
            branches_to_test.append({
                "cond": logic_node["cond"], 
                "val": logic_node["false"], 
                "label": "Branch FALSE",
                "mode": "NK" # Modo Ruptura (Nuevo)
            })
        elif "cond_1" in logic_node:
            branches_to_test.append({"cond": logic_node["cond_1"], "val": logic_node.get("val_1"), "label": "Rama 1", "mode": "OK"})
            if "cond_2" in logic_node and logic_node["cond_2"]:
                branches_to_test.append({"cond": logic_node["cond_2"], "val": logic_node.get("val_2"), "label": "Rama 2", "mode": "OK"})
            else:
                # Rama defecto compleja: Debería romper cond_1 (y cond_2 si existe)
                # Por simplicidad, la dejamos neutra, o podríamos implementar ruptura múltiple.
                branches_to_test.append({"cond": None, "val": logic_node.get("val_2"), "label": "Rama Defecto", "mode": "DEFAULT"})

        for branch in branches_to_test:
            condition = branch["cond"]
            value_logic = branch["val"]
            mode = branch.get("mode", "OK")
            label = f"{prefix}{branch['label']}"

            branch_inputs_list = []
            
            if condition:
                if mode == "OK":
                    triggers = self._generate_ok_combinations(condition)
                elif mode == "NK":
                    # AQUÍ ESTÁ LA MAGIA: Generamos inputs explícitos para romper la condición
                    triggers = self._generate_nk_combinations(condition)
                    
                    # Si no pudimos generar triggers (ej: condición vacía), fallback a default
                    if not triggers: 
                        triggers = [{}] 
                else:
                    triggers = [{}]

                for t in triggers: 
                    branch_inputs_list.append({**base_inputs, **t})
            else:
                branch_inputs_list.append(base_inputs.copy())

            for i, inputs_ctx in enumerate(branch_inputs_list):
                desc_trigger = ""
                # Generamos descripción dinámica
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