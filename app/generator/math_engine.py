from app.generator.sii_functions import SII_POS, SII_MIN, SII_MAX

class MathEngine:
    def __init__(self):
        pass

    def evaluate(self, logic_tree, context_inputs):
        result = self._evaluate_recursive(logic_tree, context_inputs)
        
        # Corrección cosmética: Si es 5.0 -> 5
        try:
            if isinstance(result, float) and result.is_integer():
                return int(result)
        except:
            pass
        return result

    def _evaluate_recursive(self, logic_tree, context_inputs):
        # 1. Valor Directo
        if isinstance(logic_tree, (int, float)):
            return logic_tree
        
        # 2. Variable / Input
        if isinstance(logic_tree, str):
            name = logic_tree.strip()
            # Tratamiento especial para "no" o "sino" en condicionales
            if name.lower() in ["no", "sino"]: return 0 
            return float(context_inputs.get(name, 0))

        # 3. Estructura Compleja
        if isinstance(logic_tree, dict):
            
            # --- NUEVO: SOPORTE PARA CONDICIONALES ---
            if "type" in logic_tree:
                t = logic_tree["type"]
                
                # Unificar lógica de extracción según el tipo de condicional del Transformer
                cond = None
                val_true = None
                val_false = None

                # Tipo estándar (ternary_prefix, comma, brace, semi)
                if t == "conditional":
                    cond = logic_tree["cond"]
                    val_true = logic_tree["true"]
                    val_false = logic_tree["false"]
                
                # Tipos explícitos (ternary_explicit, piecewise)
                elif t.startswith("conditional_"):
                    # Asumimos estructura simple: Si Cond1 -> Val1, Sino -> Val2
                    # (Si hay piecewise anidado, evaluamos solo el primer nivel por ahora)
                    cond = logic_tree.get("cond_1")
                    val_true = logic_tree.get("val_1")
                    val_false = logic_tree.get("val_2")

                # Evaluación
                if cond:
                    cond_result = self._evaluate_condition(cond, context_inputs)
                    if cond_result:
                        return self._evaluate_recursive(val_true, context_inputs)
                    else:
                        return self._evaluate_recursive(val_false, context_inputs)
                return 0

            # --- FUNCIONES ---
            if "function" in logic_tree:
                fname = logic_tree["function"]
                args = [self._evaluate_recursive(arg, context_inputs) for arg in logic_tree["args"]]
                if fname == "POS": return SII_POS(args[0])
                if fname == "MIN": return SII_MIN(*args)
                if fname == "MAX": return SII_MAX(*args)
                return 0

            # --- OPERACIONES ---
            if "op" in logic_tree:
                op = logic_tree["op"]
                if op == "+" and "terms" in logic_tree:
                    return sum(self._evaluate_recursive(t, context_inputs) for t in logic_tree["terms"])
                
                left = self._evaluate_recursive(logic_tree.get("left"), context_inputs)
                right = self._evaluate_recursive(logic_tree.get("right"), context_inputs)
                
                if op == "+": return left + right
                if op == "-": return left - right
                if op == "–": return left - right
                if op == "*": return left * right
                if op == "/": return left / right if right != 0 else 0
                
                # Soporte para evaluación lógica dentro del motor (retorna 1.0 si True, 0.0 si False)
                if op == ">": return 1.0 if left > right else 0.0
                if op == ">=": return 1.0 if left >= right else 0.0
                if op == "<": return 1.0 if left < right else 0.0
                if op == "<=": return 1.0 if left <= right else 0.0
                if op == "=": return 1.0 if left == right else 0.0
                if op == "≠": return 1.0 if left != right else 0.0
                if op == "OR": return 1.0 if (left or right) else 0.0
                if op == "AND": return 1.0 if (left and right) else 0.0

        return 0

    def _evaluate_condition(self, logic_tree, context_inputs):
        """Helper que asegura retorno booleano"""
        val = self._evaluate_recursive(logic_tree, context_inputs)
        return bool(val)