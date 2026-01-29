from app.generator.sii_functions import SII_POS, SII_MIN, SII_MAX

class MathEngine:
    def __init__(self):
        pass

    def evaluate(self, logic_tree, context_inputs):
        """
        Calcula el valor de una expresión dado un diccionario de inputs.
        logic_tree: El nodo JSON (operación, función o átomo).
        context_inputs: Diccionario {'Vx...': 10, 'C...': 5}
        """
        # 1. Si es un valor directo (int/float)
        if isinstance(logic_tree, (int, float)):
            return logic_tree
        
        # 2. Si es un string (Variable o Input)
        if isinstance(logic_tree, str):
            # Limpiamos nombre (Vx01... -> Vx01...)
            name = logic_tree.strip()
            # Buscamos en el contexto (inputs actuales)
            val = context_inputs.get(name, 0) # Si no existe, asumimos 0 (regla de negocio)
            return float(val)

        # 3. Si es un diccionario (Operación o Función)
        if isinstance(logic_tree, dict):
            
            # A. Funciones SII
            if "function" in logic_tree:
                fname = logic_tree["function"]
                # Evaluamos recursivamente los argumentos
                args = [self.evaluate(arg, context_inputs) for arg in logic_tree["args"]]
                
                if fname == "POS": return SII_POS(args[0])
                if fname == "MIN": return SII_MIN(*args)
                if fname == "MAX": return SII_MAX(*args)
                # Aquí agregaremos más funciones a futuro
                return 0

            # B. Operaciones Matemáticas
            if "op" in logic_tree:
                op = logic_tree["op"]
                # Suma de n términos
                if op == "+" and "terms" in logic_tree:
                    return sum(self.evaluate(t, context_inputs) for t in logic_tree["terms"])
                
                # Operaciones binarias
                left = self.evaluate(logic_tree.get("left"), context_inputs)
                right = self.evaluate(logic_tree.get("right"), context_inputs)
                
                if op == "+": return left + right
                if op == "-": return left - right
                if op == "*": return left * right
                if op == "/": return left / right if right != 0 else 0
        
        return 0