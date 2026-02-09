import itertools
from app.generator.builder.logic_processor import LogicProcessor

class CombinatoricsMixin:
    def __init__(self):
        if not hasattr(self, 'logic_processor'):
            self.logic_processor = LogicProcessor()

    def _generate_ok_combinations(self, logic_block):
        processor = getattr(self, 'logic_processor', LogicProcessor())
        and_components = processor.flatten_logic(logic_block, "AND")
        component_options = []
        
        for comp in and_components:
            or_options = processor.flatten_logic(comp, "OR")
            final_options = []
            for opt in or_options:
                final_options.extend(self._try_expand_complex_comparison(opt))
            
            solved_options = []
            for option in final_options:
                preds = processor.extract_predicates(option)
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
        Genera casos negativos aplicando sabotaje sobre un 'Happy Path'.
        Garantiza contexto activo para evidenciar el fallo.
        """
        # 1. Generamos Happy Path de referencia
        ok_scenarios = self._generate_ok_combinations(cond_block)
        reference_happy_input = ok_scenarios[0] if ok_scenarios else {}

        # 2. Generamos escenarios de ruptura
        bad_scenarios = self._generate_nk_combinations(cond_block)
        
        for i, bad_inputs in enumerate(bad_scenarios):
            # 3. Construimos: Base + Contexto OK + Sabotaje
            case_inputs = golden_inputs.copy()
            case_inputs.update(reference_happy_input)
            
            # Aplicamos sabotaje (sobreescribe al Happy Path)
            self._apply_sabotage(case_inputs, bad_inputs)
            
            actives = [k for k in bad_inputs.keys() if k not in self.parameters]
            desc = f"Fallo forzado en Bloque #{i+1} (Trigger: {', '.join(actives[:4])})"
            self._add_case("Cond. NK", desc, case_inputs, "No cumple Condición")

    def _apply_sabotage(self, inputs, bad_inputs):
        for k, v in bad_inputs.items():
            inputs[k] = v

    def _generate_nk_combinations(self, logic_block):
        processor = getattr(self, 'logic_processor', LogicProcessor())
        nk_scenarios = []
        and_components = processor.flatten_logic(logic_block, "AND")
        
        for comp in and_components:
            or_options = processor.flatten_logic(comp, "OR")
            options_failure_modes = [] # Modos de fallo por opción
            
            for opt in or_options:
                current_opt_modes = []
                complex_handled = False
                
                # --- Sabotaje Proporcional (Sumas) ---
                if isinstance(opt, dict) and "op" in opt:
                    op = opt["op"]
                    if op in ["=", ">", "<", ">=", "<=", "≠"]:
                        left_node = opt["left"]
                        right_node = opt["right"]
                        pos_terms, neg_terms = [], []
                        processor.decompose_additive_expression(left_node, pos_terms, neg_terms)
                        
                        if len(pos_terms) + len(neg_terms) > 1 or len(neg_terms) > 0:
                            complex_handled = True
                            sabotage_input = {}
                            ctx = self.parameters.copy()
                            ref_val = self.math_engine.evaluate(right_node, ctx)
                            base_threshold = int(ref_val) if isinstance(ref_val, (int, float)) else 0
                            
                            if op in [">", ">="]:
                                if neg_terms: # Inflar ambos
                                    margin = 2000
                                    t_pos = base_threshold + margin
                                    v_pos = int(t_pos / max(1, len(pos_terms))) + 1
                                    for p in pos_terms: self._smart_set_input(sabotage_input, p, v_pos)
                                    v_neg = int((margin + 1000) / max(1, len(neg_terms))) + 1
                                    for n in neg_terms: self._smart_set_input(sabotage_input, n, v_neg)
                                else: # Anular positivos
                                    for p in pos_terms: self._smart_set_input(sabotage_input, p, 0)
                            
                            elif op in ["<", "<="]: # Inflar positivos
                                margin = 2000
                                v_pos = int((base_threshold + margin) / max(1, len(pos_terms))) + 1
                                for p in pos_terms: self._smart_set_input(sabotage_input, p, v_pos)
                                for n in neg_terms: self._smart_set_input(sabotage_input, n, 0)
                            
                            elif op == "≠": # Forzar igualdad
                                pass # Implementar si necesario
                            
                            elif op == "=": # Forzar diferencia
                                pass # Implementar si necesario

                            else: # Fallback a valor roto
                                if pos_terms:
                                    target = pos_terms[0]
                                    bv = self._get_broken_value(op, ref_val)
                                    if bv is not None: self._smart_set_input(sabotage_input, target, bv)
                            
                            if sabotage_input: current_opt_modes.append(sabotage_input)

                # --- Predicados Simples / Multiplicación ---
                if not complex_handled:
                    preds = processor.extract_predicates(opt)
                    if preds:
                        for p in preds:
                            target = p['target']
                            op = p['op']
                            right_tree = p['right_tree']
                            ctx = self.parameters.copy()
                            ref_val = self.math_engine.evaluate(right_tree, ctx)
                            broken_val = self._get_broken_value(op, ref_val)
                            
                            if broken_val is not None:
                                mode_input = {}
                                self._smart_set_input(mode_input, target, broken_val)
                                current_opt_modes.append(mode_input)
                
                if current_opt_modes: options_failure_modes.append(current_opt_modes)
            
            # Producto Cartesiano para romper ORs
            if options_failure_modes:
                for combo in itertools.product(*options_failure_modes):
                    merged = {}
                    for d in combo: merged.update(d)
                    nk_scenarios.append(merged)
        return nk_scenarios

    def _get_broken_value(self, op, ref_val):
        if isinstance(ref_val, float) and ref_val.is_integer(): ref_val = int(ref_val)
        if op == "=": return ref_val + 1 
        if op == "≠": return ref_val     
        if op == ">": return 0           
        if op == ">=": return ref_val - 1
        if op == "<": return ref_val + 1000 
        if op == "<=": return ref_val + 1
        return None

    def _try_expand_complex_comparison(self, logic_node):
        processor = getattr(self, 'logic_processor', LogicProcessor())
        if isinstance(logic_node, dict) and "op" in logic_node:
            op = logic_node["op"]
            right = logic_node["right"]
            left = logic_node.get("left")

            if op in [">", ">="] and (right == 0 or right == "0"):
                 factors = []
                 processor._flatten_multiplication(left, factors)
                 if len(factors) > 1: return [logic_node]

            if op in [">", ">=", "<", "<=", "≠"]:
                pos_terms, neg_terms = [], []
                processor.decompose_additive_expression(left, pos_terms, neg_terms)
                variants = []
                if op in [">", ">="]:
                    for var in pos_terms: variants.append({"op": op, "left": var, "right": right})
                elif op in ["<", "<="]: return [logic_node] 
                elif op == "≠":
                    all_terms = pos_terms + neg_terms
                    for var in all_terms: variants.append({"op": op, "left": var, "right": right})
                if variants: return variants
        return [logic_node]

    def _solve_for_true(self, predicates):
        processor = getattr(self, 'logic_processor', LogicProcessor())
        current_inputs = self.parameters.copy()
        
        for p in predicates:
            if p['op'] in [">", ">=", "<", "<="]:
                 all_vars = processor._extract_leaf_vars(p['right_tree'])
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
                
                if op in [">", ">="] and new_val < 1000: new_val = 1000
                if op in ["<", "<="] and new_val < 0: new_val = 0
                if op == "=" and target_val == 0: new_val = 0

                self._smart_set_input(current_inputs, target, new_val)
        return {k: v for k, v in current_inputs.items() if k not in self.parameters}