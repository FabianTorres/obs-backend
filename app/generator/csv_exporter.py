import csv
import os
import re

class CSVExporter:
    def __init__(self, output_dir):
        self.output_dir = output_dir

    def export(self, filename, headers_inputs, scenarios):
        path = os.path.join(self.output_dir, filename)
        
        # 1. Normalizar Headers (Columnas)
        # Convertimos 'Vx010599' -> 'Vx599' y 'C1593' -> '[1593]'
        clean_headers = [self._normalize_header(h) for h in headers_inputs]
        
        # Definimos las columnas finales
        fieldnames = ["ID_Caso", "Tipo", "Descripcion", "Resultado_Esperado"] + clean_headers
        
        with open(path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()

            for scen in scenarios:
                # 2. Normalizar las filas
                # Como cambiamos los nombres de las columnas, debemos cambiar las llaves del diccionario
                # para que coincidan.
                clean_row = {}
                
                # Copiamos los metadatos fijos
                clean_row["ID_Caso"] = scen.get("ID_Caso", "")
                clean_row["Tipo"] = scen.get("Tipo", "")
                clean_row["Descripcion"] = scen.get("Descripcion", "")
                clean_row["Resultado_Esperado"] = scen.get("Resultado_Esperado", "")
                
                # Mapeamos los inputs a sus nombres limpios
                for original_key in headers_inputs:
                    if original_key in scen:
                        new_key = self._normalize_header(original_key)
                        clean_row[new_key] = scen[original_key]
                
                writer.writerow(clean_row)
        
        return path

    def _normalize_header(self, name):
        """Aplica el formato visual solicitado por el equipo de QA"""
        name = name.strip()
        
        # Regla 1: Vectores Vx01XXXX -> VxXXXX
        # Asumimos que siempre empieza con Vx01 y queremos quitar el 01
        if name.startswith("Vx01"):
            # Vx010599 -> Vx599 (Quitamos '01' y ceros a la izquierda del numero si quisieras, 
            # pero tu ejemplo 'Vx599' implica conservar el numero tal cual viene despues del 01?
            # Si Vx010599 es vector 599, entonces cortamos el "Vx01" y parseamos int para quitar ceros extra
            try:
                num_part = name[4:] # "0599"
                return f"Vx{int(num_part)}" # "Vx599"
            except:
                return name # Fallback

        # Regla 2: Códigos CXXXX -> [XXXX]
        if name.startswith("C") and name[1:].isdigit():
            return f"[{name[1:]}]"
            
        return name