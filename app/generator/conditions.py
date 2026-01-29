class ConditionExtractor:
    def __init__(self):
        self.conditions = []
        self.current_section = "General"
        self.current_target = None # Para saber si estamos dentro de una variable (ej: OMEGA)

    def extract(self, logic_tree):
        """
        Recorre el árbol y extrae todas las comparaciones lógicas.
        """
        if isinstance(logic_tree, list):
            for item in logic_tree:
                self.extract(item)
        
        elif isinstance(logic_tree, dict):
            # 1. Detectar cambio de Sección
            if "section" in logic_tree:
                self.current_section = logic_tree["section"]
                self.extract(logic_tree["content"])
            
            # 2. Detectar si estamos definiendo una Variable (Target)
            elif "target" in logic_tree:
                prev_target = self.current_target
                self.current_target = logic_tree["target"]
                self.extract(logic_tree["logic"])
                self.current_target = prev_target # Volvemos al anterior al salir
            
            # 3. Detectar una Comparación (El corazón de la prueba)
            elif "op" in logic_tree and logic_tree["op"] in [">", "<", ">=", "<=", "=", "≠", "<>", "AND", "OR"]:
                # Si es AND/OR, seguimos bajando recursivamente
                if logic_tree["op"] in ["AND", "OR"]:
                    self.extract(logic_tree["left"])
                    self.extract(logic_tree["right"])
                else:
                    # Es una comparación pura (ej: CHI > RHO) -> ¡ESTO ES UN CASO DE PRUEBA!
                    self._add_condition(logic_tree)
            
            # 4. Detectar Condicionales (si ... sino)
            elif "type" in logic_tree and "conditional" in logic_tree["type"]:
                # Revisar las condiciones dentro del IF
                if "cond" in logic_tree: self.extract(logic_tree["cond"])
                if "cond_1" in logic_tree: self.extract(logic_tree["cond_1"])
                if "cond_2" in logic_tree: self.extract(logic_tree["cond_2"])
                # Seguir bajando por los valores true/false por si hay mas lógica anidada
                if "true" in logic_tree: self.extract(logic_tree["true"])
                if "val_1" in logic_tree: self.extract(logic_tree["val_1"])

            # 5. Recursividad genérica para otros dicts
            else:
                for key, value in logic_tree.items():
                    if isinstance(value, (dict, list)):
                        self.extract(value)

    def _add_condition(self, node):
        """Formatea y guarda la condición encontrada"""
        
        # Convertimos el nodo JSON a texto legible (ej: "CHI > RHO")
        readable_expr = f"{self._to_str(node['left'])} {node['op']} {self._to_str(node['right'])}"
        
        entry = {
            "seccion": self.current_section,
            "variable_origen": self.current_target if self.current_target else "N/A",
            "expresion_legible": readable_expr,
            "detalle_tecnico": node # Guardamos el JSON crudo por si acaso
        }
        self.conditions.append(entry)

    def _to_str(self, item):
        """Convierte un sub-arbol en string simple para leerlo facil"""
        if isinstance(item, str) or isinstance(item, (int, float)):
            return str(item)
        if isinstance(item, dict):
            if "function" in item:
                args = [self._to_str(a) for a in item["args"]]
                return f"{item['function']}({', '.join(args)})"
            if "op" in item:
                if "terms" in item: # Suma de varios
                    return "(" + " + ".join([self._to_str(t) for t in item["terms"]]) + ")"
                return f"({self._to_str(item.get('left'))} {item['op']} {self._to_str(item.get('right'))})"
        return "?"

    def get_report(self):
        return self.conditions