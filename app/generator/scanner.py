class VariableScanner:
    def __init__(self):
        self.inputs_vector = set()  # Vx...
        self.inputs_codigo = set()  # C...
        self.parameters = set()     # P...
        self.defined_vars = set()   # Variables calculadas

    def scan(self, logic_tree):
        """
        Recibe el JSON completo (o una parte) y extrae las variables.
        """
        # CASO 1: Es una LISTA (Aquí estaba el error)
        if isinstance(logic_tree, list):
            for item in logic_tree:
                # Si el item es una estructura compleja, recursividad
                if isinstance(item, (dict, list)):
                    self.scan(item)
                # ¡CORRECCION! Si el item es un String directo (ej: "Vx014639"), leerlo
                elif isinstance(item, str):
                    self._categorize(item)
        
        # CASO 2: Es un DICCIONARIO
        elif isinstance(logic_tree, dict):
            # Guardamos el nombre de la variable objetivo (target)
            if "target" in logic_tree:
                self.defined_vars.add(logic_tree["target"])
            
            # Recorremos valores
            for key, value in logic_tree.items():
                if isinstance(value, (dict, list)):
                    self.scan(value) # Recursividad
                elif isinstance(value, str):
                    self._categorize(value)

    def _categorize(self, value):
        """Clasifica un string según su prefijo"""
        # Limpiamos espacios y comas que se hayan colado
        val = value.strip().replace(",", "").replace(";", "")
        
        if not val: return

        if val.startswith("Vx"):
            self.inputs_vector.add(val)
        elif val.startswith("C") and len(val) > 1 and val[1].isdigit(): # C123
            self.inputs_codigo.add(val)
        elif val.startswith("P") and len(val) > 1 and val[1].isdigit(): # P231
            self.parameters.add(val)

    def get_report(self):
        """Devuelve un resumen ordenado"""
        return {
            "Total_Inputs": len(self.inputs_vector) + len(self.inputs_codigo),
            "Vectores_Requeridos": sorted(list(self.inputs_vector)),
            "Codigos_Requeridos": sorted(list(self.inputs_codigo)),
            "Parametros_Fijos": sorted(list(self.parameters)),
            "Variables_Calculadas": sorted(list(self.defined_vars))
        }