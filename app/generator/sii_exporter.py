import os

class SIIExporter:
    def __init__(self, output_dir):
        self.output_dir = output_dir

    def export(self, filename, headers_inputs, scenarios):
        """
        Genera un archivo delimitado por PIPES (|) con el formato:
        Numero de caso|Tipo de caso|Datos de prueba|Resultado
        Donde Datos de prueba es: [Cod]=Val; ... ; VxVector=Val;
        """
        path = os.path.join(self.output_dir, filename)
        
        # --- MAPA DE TRADUCCIÓN (NUEVO) ---
        # Convierte tipos internos de debug a tipos oficiales del SII
        TYPE_MAPPING = {
            "Valida POS=0": "Norma NK",
        }

        # Encabezado del archivo
        header_row = "Numero de caso|Tipo de caso|Datos de prueba|Resultado\n"
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(header_row)

            for scen in scenarios:
                # 1. Construir la cadena de Datos de Prueba
                input_string = self._build_input_string(scen, headers_inputs)
                
                # 2. Formatear Resultado (limpieza básica)
                resultado = str(scen.get("Resultado_Esperado", "")).replace("\n", " ")

                # 3. Traducir Tipo de Caso (NUEVO LÓGICA)
                tipo_original = scen['Tipo']
                tipo_final = TYPE_MAPPING.get(tipo_original, tipo_original)

                # 4. Construir la línea final
                line = f"{scen['ID_Caso']}|{tipo_final}|{input_string}|{resultado}\n"
                f.write(line)
        
        return path

    def _build_input_string(self, scenario_data, headers_inputs):
        """
        Separa en Códigos y Vectores, normaliza nombres y valores, y une con punto y coma.
        """
        codigos = []
        vectores = []

        # Recorremos todos los inputs posibles que detectó el Scanner
        for key in headers_inputs:
            # Obtenemos el valor del escenario (si no existe, asumimos vacío o 0 según logica, aquí vacío para no ensuciar)
            raw_val = scenario_data.get(key)
            
            # Solo agregamos si hay un valor definido (distinto de None)
            if raw_val is not None:
                # Normalizamos Valor (111.0 -> 111)
                val_str = self._format_number(raw_val)
                
                # Normalizamos Llave y clasificamos
                norm_key = self._normalize_header(key)
                
                # Armamos el par "Llave=Valor"
                entry = f"{norm_key}={val_str}"

                if "[" in norm_key: # Es un Código [123]
                    codigos.append(entry)
                else: # Es un Vector Vx...
                    vectores.append(entry)

        # Ordenamos alfabéticamente para que se vea ordenado (opcional pero recomendado)
        codigos.sort()
        vectores.sort()

        # Unimos: Primero Códigos, luego Vectores
        full_list = codigos + vectores
        return "; ".join(full_list) + ";" # Agregamos ; al final como en tu ejemplo

    def _normalize_header(self, name):
        """Convierte C123 -> [123] y Vx010599 -> Vx599"""
        name = name.strip()
        
        if name.startswith("Vx01"):
            try:
                num_part = name[4:] 
                return f"Vx{int(num_part)}" # Vx599
            except:
                return name 

        if name.startswith("C") and name[1:].isdigit():
            return f"[{name[1:]}]"
            
        return name

    def _format_number(self, value):
        """Convierte float 111.0 a string '111', pero deja 0.5 como '0.5'"""
        try:
            f_val = float(value)
            if f_val.is_integer():
                return str(int(f_val))
            return str(f_val)
        except:
            return str(value)