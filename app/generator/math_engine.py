from app.generator.sii_functions import SII_POS, SII_MIN, SII_MAX
import math

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
        # ... (Aquí va toda la lógica anterior que tenías en 'evaluate') ...
        # Copia y pega tu lógica anterior aquí adentro (la de if int, if str, if dict...)
        
        # 1. Valor Directo
        if isinstance(logic_tree, (int, float)):
            return logic_tree
        
        # 2. Variable / Input
        if isinstance(logic_tree, str):
            name = logic_tree.strip()
            return float(context_inputs.get(name, 0))

        # 3. Estructura Compleja
        if isinstance(logic_tree, dict):
            if "function" in logic_tree:
                fname = logic_tree["function"]
                args = [self._evaluate_recursive(arg, context_inputs) for arg in logic_tree["args"]]
                if fname == "POS": return SII_POS(args[0])
                if fname == "MIN": return SII_MIN(*args)
                if fname == "MAX": return SII_MAX(*args)
                return 0

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

        return 0