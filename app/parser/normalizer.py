import re

class Normalizer:
    def __init__(self):
        # Lista de diccionarios: { "nivel":Str, "contexto":Str, "mensaje":Str }
        self.report = [] 

    def clean_section(self, raw_text, context_name="General"):
        """
        Limpia un bloque de texto, elimina títulos y corrige sintaxis agresivamente.
        """
        # 1. Limpieza básica
        text = raw_text.replace("–", "-").replace("“", '"').replace("”", '"')
        
        # 2. Eliminación de Títulos de Usuario
        text = re.sub(r'^\s*Condici[oó]n de Entrada\s*:?\s*', '', text, flags=re.IGNORECASE | re.MULTILINE)
        text = re.sub(r'^\s*Variables\s*:?\s*', '', text, flags=re.IGNORECASE | re.MULTILINE)
        
        # 3. Unificar líneas rotas
        lines = text.split('\n')
        consolidated_lines = []
        buffer = []
        
        for line in lines:
            line = line.strip()
            if not line: continue
            
            # Detectamos inicio de instrucción
            is_start = ("=" in line and not line.lower().startswith(("si", "sino", "."))) or line.strip().endswith(":")
            if not buffer and not is_start: is_start = True

            if is_start:
                if buffer: consolidated_lines.append(" ".join(buffer))
                buffer = [line]
            else:
                buffer.append(line)
        
        if buffer: consolidated_lines.append(" ".join(buffer))
        
        # 4. Procesar línea por línea
        normalized_lines = []
        for line in consolidated_lines:
            # CORRECCIÓN DE PUNTOS:
            # 1. "116." al final -> "116"
            line = line.rstrip('.')
            # 2. "116.)" -> "116)"
            line = re.sub(r'(\d+)\.\s*\)', r'\1)', line)
            
            # A. Auditoría Preventiva
            self._audit_line(line, context_name)
            
            # B. Normalización y Corrección
            norm = self._normalize_formula(line, context_name)
            norm = self._balance_parentheses(norm, context_name)
            normalized_lines.append(norm)
            
        return "\n".join(normalized_lines)

    def _add_log(self, level, context, message):
        self.report.append({
            "nivel": level,
            "contexto": context,
            "mensaje": message
        })

    def _audit_line(self, text, context):
        """
        Analiza la línea cruda buscando errores lógicos que no se deben autocorregir.
        """
        var_owner = text.split("=")[0].strip() if "=" in text else "Condición"
        full_context = f"{context} -> {var_owner}"

        # 1. VALIDACIÓN DE VECTORES
        matches = re.finditer(r'\b[vV][xX]\.?\s*(\d+)', text)
        for match in matches:
            digits = match.group(1)
            full_str = match.group(0)
            if len(digits) != 6:
                self._add_log("CRITICAL", full_context, 
                              f"AMBIGÜEDAD GRAVE: El vector '{full_str}' tiene {len(digits)} dígitos. "
                              f"Se requieren exactamente 6 dígitos (ej: Vx011555). "
                              f"NO SE PUEDE DETERMINAR QUÉ VECTOR ES.")

        # 2. DETECCIÓN DE AMBIGÜEDAD DE OPERADORES
        has_and = re.search(r'(\.[yY]\.| \s*[yY]\s* )', text)
        has_or = re.search(r'(\.[oO]\.| \s*[oO]\s* )', text)

        if has_and and has_or:
            if "(" not in text and ")" not in text:
                 self._add_log("CRITICAL", full_context, 
                              "AMBIGÜEDAD LÓGICA GRAVE: Uso mixto de 'Y' y 'O' sin paréntesis. "
                              "POR FAVOR USE PARÉNTESIS para definir la jerarquía explícitamente.")
            else:
                 self._add_log("WARNING", full_context,
                               "PRECAUCIÓN LÓGICA: Se detectó mezcla de 'Y' y 'O'. Verifique paréntesis.")

    def _balance_parentheses(self, text, context):
        open_count = text.count("(")
        close_count = text.count(")")
        
        if open_count == close_count:
            return text
            
        var_name = text.split("=")[0].strip() if "=" in text else "Expresión"
        full_context = f"{context} -> {var_name}"
        
        if close_count > open_count:
            diff = close_count - open_count
            new_text = text
            for _ in range(diff):
                last_paren_index = new_text.rfind(")")
                if last_paren_index != -1:
                    new_text = new_text[:last_paren_index] + new_text[last_paren_index+1:]
            self._add_log("CRITICAL", full_context, f"ERROR GRAVE: Sobraban {diff} paréntesis de cierre. Se eliminaron.")
            return new_text

        if open_count > close_count:
            diff = open_count - close_count
            new_text = text + (")" * diff)
            self._add_log("CRITICAL", full_context, f"ERROR GRAVE: Faltaban {diff} paréntesis de cierre. Se agregaron.")
            return new_text
            
        return text

    def _normalize_formula(self, text, context):
        # --- FASE 0: ESTANDARIZACIÓN DE ENTIDADES ---
        text = re.sub(r'\b[vV][xX]\.?\s*(\d+)', r'Vx\1', text)
        text = re.sub(r'\b[cC]\s*(\d+)', r'C\1', text)
        text = re.sub(r'\b[pP]\s*(\d+)', r'P\1', text)

        # FASE 0.5: Expansión de "Shorthand OR" (VERSIÓN FINAL ROBUSTA)
        # Vx=1 .o. 2 -> Vx=1 .o. Vx=2
        
        for _ in range(10): # Límite de seguridad
            def expand_or(match):
                full_assign = match.group(1)   
                var_name = full_assign.split('=')[0].strip()
                next_val = match.group(2)      
                
                # Doble check de seguridad
                if '=' in next_val: return match.group(0)
                
                return f"{full_assign} .o. {var_name}={next_val}"

            # REGEX BLINDADA:
            # 1. (\b[a-zA-Z_]\w*\s*=\s*[\w\.]+) -> Captura Vx=111
            # 2. \s*\.[oO]\.\s* -> Captura .o.
            # 3. ([\w\.]+)                      -> Captura 112
            # 4. (?=\s*(?:\.[oO]\.|\.[yY]\.|\)|$)) -> LOOKAHEAD POSITIVO
            #    Asegura que lo que sigue es OBLIGATORIAMENTE un separador (.o., .y., ) o Fin).
            #    Si sigue un "=", fallará y no hará match.
            
            pattern = r'(\b[a-zA-Z_]\w*\s*=\s*[\w\.]+)\s*\.[oO]\.\s*([\w\.]+)(?=\s*(?:\.[oO]\.|\.[yY]\.|\)|$))'
            
            new_text = re.sub(pattern, expand_or, text, flags=re.IGNORECASE)
            if new_text == text: break
            text = new_text

        # FASE 1: Operadores
        text = re.sub(r'\s*\.[yY]\.\s*', ' Y ', text)
        text = re.sub(r'\s*\.[oO]\.\s*', ' O ', text)
        text = re.sub(r'\bMin\b', 'MIN', text, flags=re.IGNORECASE)
        text = re.sub(r'\bMax\b', 'MAX', text, flags=re.IGNORECASE)
        text = re.sub(r'\bPos\b', 'POS', text, flags=re.IGNORECASE)
        text = text.replace("{", "(").replace("}", ")")

        # FASE 2: Patrones Condicionales
        text = re.sub(r'=\s*Si\s*\((.*?)\)\s*=\s*(\d+)\s+(\d+)\s*,\s*Sino', r'= SI(\1; \2; \3)', text, flags=re.IGNORECASE)
        text = re.sub(r'=\s*(\d+)\s*,\s*si\s*(.*?)\s*,\s*(\d+)\s*,\s*sino', r'= SI(\2; \1; \3)', text, flags=re.IGNORECASE)
        text = re.sub(r'=\s*(\d+)\s*;\s*(.+?)\s+(\d+)\s*;\s*si\s*no', r'= SI(\2; \1; \3)', text, flags=re.IGNORECASE)

        if ",si" in text.lower():
            def replace_piecewise(match):
                prefix = match.group(1)
                val1 = match.group(2)
                cond1 = match.group(3)
                val2 = match.group(4)
                cond2 = match.group(5)
                if val1.startswith("(") and val1.count("(") > val1.count(")"):
                    val1 = val1[1:]
                return f"{prefix} SI({cond1}; {val1}; {val2})"
            pattern = r'(.*?=\s*)(.+?)\s*,si\s*(.+)\s+(.+?)\s*,si\s*(.*)'
            text = re.sub(pattern, replace_piecewise, text, flags=re.IGNORECASE)

        text = re.sub(r'\(\s*(.*?)\s*;\s*(.*?)\s*[;]\s*(.*?)\s*;\s*sino\s*\)', r'SI(\2; \1; \3)', text, flags=re.IGNORECASE)

        return text