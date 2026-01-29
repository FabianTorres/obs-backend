import csv
import os

class ParamLoader:
    def __init__(self, filepath):
        self.filepath = filepath

    def load(self):
        """
        Lee el CSV de parámetros y devuelve un diccionario:
        {'P31': 1500.0, 'P520': 53200.0, ...}
        """
        parameters = {}
        
        if not os.path.exists(self.filepath):
            print(f"⚠️ ADVERTENCIA: No se encontró el archivo de parámetros: {self.filepath}")
            return parameters

        try:
            with open(self.filepath, mode='r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    key = row['ID'].strip()
                    raw_val = row['Valor'].strip()
                    type_val = row['Tipo'].strip().lower()
                    
                    # Conversión de Tipos
                    if type_val == 'numero':
                        try:
                            # Reemplazamos coma por punto por si acaso (formato excel)
                            clean_val = raw_val.replace(',', '.')
                            parameters[key] = float(clean_val)
                        except ValueError:
                            print(f"⚠️ Error convirtiendo parámetro {key} a número. Se usará 0.")
                            parameters[key] = 0.0
                    
                    elif type_val == 'fecha':
                        # Por ahora lo dejamos como string, más adelante podemos usar objetos date
                        parameters[key] = raw_val
                    
                    else:
                        # Alfanumérico o Texto
                        parameters[key] = raw_val
                        
            return parameters

        except Exception as e:
            print(f"❌ Error leyendo parámetros: {e}")
            return {}