from lark import Transformer, Discard

class ObservacionTransformer(Transformer):
    # ... (Encabezados igual que antes) ...
    def start(self, s): return s
    def section(self, s): return {"section": s[0], "content": s[1]}
    def instruction_block(self, s): return s
    def header_condicion(self, _): return "Condicion_Entrada"
    def header_variables(self, _): return "Variables"
    def header_norma(self, _): return "Norma_Observacion"
    def instruction(self, s): return {"target": s[0], "logic": s[1]}

    # --- OPERADORES EXCEL ---
    def or_op(self, s): return {"op": "OR", "left": s[0], "right": s[1]}
    def and_op(self, s): return {"op": "AND", "left": s[0], "right": s[1]}
    
    # ... (Suma, Resta, Multi, Div, Comparison IGUAL QUE ANTES) ...
    def comparison(self, s): return {"op": str(s[1]), "left": s[0], "right": s[2]}
    def suma(self, s): return {"op": "+", "terms": s}
    def resta(self, s): return {"op": "-", "left": s[0], "right": s[1]}
    def multi(self, s): return {"op": "*", "left": s[0], "right": s[1]}
    def div(self, s): return {"op": "/", "left": s[0], "right": s[1]}

    # --- FUNCIONES ---
    def function_call(self, items):
        fname = str(items[0]).upper()
        args = items[1]
        
        # MAPEO ESPECIAL: SI(Cond; True; False) -> Estructura interna 'conditional'
        if fname == "SI":
            return {
                "type": "conditional",
                "cond": args[0],
                "true": args[1],
                "false": args[2] if len(args) > 2 else 0
            }
            
        return {"function": fname, "args": args}

    def args(self, items): return items
    
    # --- ATOMOS (IGUAL QUE ANTES) ---
    def atom(self, s): return s[0]
    def var_valor(self, s): return f"VALOR_{s[0]}"
    def var_nombre(self, s): return str(s[0])
    def VECTOR(self, t): return str(t)
    def CODIGO(self, t): return f"C{t.split('C')[-1].strip()}"
    def PARAMETRO(self, t): return str(t)
    def NUMBER(self, t): return float(t) if '.' in t else int(t)