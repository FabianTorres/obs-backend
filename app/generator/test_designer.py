import copy

class TestDesigner:
    def __init__(self, variables_report):
        self.inputs = variables_report["Vectores_Requeridos"] + variables_report["Codigos_Requeridos"]
        self.scenarios = []

    def generate_scenarios(self, conditions):
        """
        Recorre las condiciones y crea escenarios de prueba para cada una.
        """
        case_id = 1
        
        for cond in conditions:
            # Estrategia: Solo podemos generar valores automáticos para inputs directos (Vx... o C...)
            # Si la condición es sobre una variable calculada (ej: CHI > RHO), es un caso complejo.
            
            target = self._extract_target_variable(cond["detalle_tecnico"])
            
            if target in self.inputs:
                # ¡Bingo! Es una variable que controlamos directamente (ej: Vx014648 = 8)
                new_scenarios = self._create_boundary_cases(case_id, cond, target)
                self.scenarios.extend(new_scenarios)
                case_id += len(new_scenarios)
            else:
                # Es una variable calculada (ej: CHI > RHO)
                # Creamos un escenario "placeholder" para que el humano o un solver avanzado lo revise
                self.scenarios.append({
                    "id": f"TC_{case_id:03d}",
                    "tipo": "Lógica Compleja",
                    "descripcion": f"Verificar {cond['seccion']}: {cond['expresion_legible']}",
                    "variable_foco": "Calculada",
                    "valor_sugerido": "Requiere cálculo de dependencia"
                })
                case_id += 1
        
        return self.scenarios

    def _extract_target_variable(self, logic_node):
        """Intenta adivinar cuál es la variable principal de la condición"""
        left = logic_node.get("left")
        
        # Si la izquierda es un string directo (ej: "Vx014648")
        if isinstance(left, str):
            return left
        # Si la izquierda es una operación (ej: Vx + 1), intentamos buscar adentro (simplificado)
        return "Complex"

    def _create_boundary_cases(self, start_id, cond, variable):
        """Genera los casos de borde según el operador"""
        op = cond["detalle_tecnico"]["op"]
        try:
            # Intentamos obtener el valor de referencia (right side)
            ref_value = float(cond["detalle_tecnico"]["right"])
        except (ValueError, TypeError):
            # Si comparamos contra otra variable (Vx > Vy), no podemos automatizar el valor simple
            return []

        cases = []
        
        # Generador de Casos según Operador
        if op == "=":
            # Caso 1: Igualdad (Happy Path)
            cases.append(self._make_case(start_id, variable, ref_value, f"Valor Igual a {ref_value}"))
            # Caso 2: Diferencia (Unhappy Path)
            cases.append(self._make_case(start_id+1, variable, ref_value + 1, f"Valor Distinto (Borde Superior)"))

        elif op == "≠" or op == "<>":
             cases.append(self._make_case(start_id, variable, ref_value + 1, f"Valor Distinto"))
             cases.append(self._make_case(start_id+1, variable, ref_value, f"Valor Prohibido (Igual)"))

        elif op == ">":
            cases.append(self._make_case(start_id, variable, ref_value + 1, f"Mayor que {ref_value} (Cumple)"))
            cases.append(self._make_case(start_id+1, variable, ref_value, f"Igual a {ref_value} (Borde - No Cumple)"))
        
        elif op == ">=":
            cases.append(self._make_case(start_id, variable, ref_value, f"Igual a {ref_value} (Borde - Cumple)"))
            cases.append(self._make_case(start_id+1, variable, ref_value - 1, f"Menor que {ref_value} (No Cumple)"))

        elif op == "<":
            cases.append(self._make_case(start_id, variable, ref_value - 1, f"Menor que {ref_value} (Cumple)"))
            cases.append(self._make_case(start_id+1, variable, ref_value, f"Igual a {ref_value} (Borde - No Cumple)"))

        return cases

    def _make_case(self, cid, variable, valor, desc):
        return {
            "id": f"TC_{cid:03d}",
            "tipo": "Borde Directo",
            "descripcion": f"Prueba de {variable}: {desc}",
            "variable_foco": variable,
            "valor_sugerido": valor
        }