from lark import Transformer, Discard

class ObservacionTransformer(Transformer):
    
    # --- ESTRUCTURA GENERAL ---
    def start(self, sections): return sections
    
    def section(self, items):
        return {"section": items[0], "content": items[1]}

    def instruction_block(self, items): return items
    
    def header_condicion(self, _): return "Condicion_Entrada"
    def header_variables(self, _): return "Variables"
    def header_norma(self, _): return "Norma_Observacion"

    def instruction(self, items):
        return {"target": items[0], "logic": items[1]}

    # --- LIMPIEZA DE SEPARADORES ---
    def separator(self, _):
        return Discard

    # --- OPERADORES Y NORMALIZACIÓN LÓGICA ---
    
    def or_op(self, items): 
        left = items[0]
        right = items[1]
        
        # MAGIA: Contexto Implícito (Vx=511 .o. 512 -> Vx=511 .o. Vx=512)
        # Si la izquierda es una comparación y la derecha es solo un número...
        if isinstance(left, dict) and "op" in left and isinstance(right, (int, float)):
            # ...clonamos la estructura de la izquierda pero con el valor de la derecha
            right = {
                "op": left["op"],       # Copiamos operador (=)
                "left": left["left"],   # Copiamos variable (Vx...)
                "right": right          # Ponemos el nuevo valor (512)
            }
            
        return {"op": "OR", "left": left, "right": right}

    def and_op(self, items): return {"op": "AND", "left": items[0], "right": items[1]}
    
    def comparison(self, items): 
        return {"op": str(items[1]), "left": items[0], "right": items[2]}
    
    def suma(self, items): return {"op": "+", "terms": items}
    def resta(self, items): return {"op": "-", "left": items[0], "right": items[1]}
    def multi(self, items): return {"op": "*", "left": items[0], "right": items[1]}
    def div(self, items): return {"op": "/", "left": items[0], "right": items[1]}

    # --- FUNCIONES ---
    def function_call(self, items):
        return {"function": str(items[0]).upper(), "args": items[1]}

    def args(self, items):
        return items 

    # --- VARIABLES Y ATOMOS ---
    def atom(self, items):
        return items[0]

    def var_valor(self, items): return f"VALOR_{items[0]}"
    def var_nombre(self, items): return str(items[0])
    def VECTOR(self, t): return str(t)
    def CODIGO(self, t): return f"C{t.split('C')[-1].strip()}"
    def PARAMETRO(self, t): return str(t)
    def NUMBER(self, t): return float(t) if '.' in t else int(t)

    # --- CONDICIONALES ---
    
    # Caso 1: PDF Roto { Val, si Cond ...
    def ternary_piecewise(self, items):
        return {
            "type": "conditional_piecewise_pdf",
            "val_1": items[0],
            "cond_1": items[1],
            "val_2": items[2],
            "cond_2": items[3] if len(items) > 3 else None
        }

    # Caso 2: Explicito Val, si Cond...
    def ternary_explicit(self, items):
        res = {
            "type": "conditional_explicit",
            "val_1": items[0],
            "cond_1": items[1],
            "val_2": items[2]
        }
        if len(items) > 3:
            res["cond_2"] = items[3]
        return res

    # Caso 3: Prefijo Si (Cond) = ...
    def ternary_prefix(self, items):
        return {"type": "conditional", "true": items[1], "cond": items[0], "false": items[2]}

    # Caso 4: Llaves { 1 ; si ... }
    def ternary_brace(self, items):
        return {"type": "conditional", "true": items[0], "cond": items[1], "false": items[2]}
    
    # Caso 5: Comas 0, si ...
    def ternary_comma(self, items):
        return {"type": "conditional", "true": items[0], "cond": items[1], "false": items[2]}

    # Caso 6: Puntos y coma 1 ; Cond ...
    def ternary_semi(self, items):
        return {"type": "conditional", "true": items[0], "cond": items[1], "false": items[2]}