import math

# --- FUNCIONES MATEMATICAS BASICAS SII ---

def SII_POS(valor):
    """Retorna el valor si es positivo, sino 0"""
    try:
        return max(0, float(valor))
    except:
        return 0

def SII_MIN(*args):
    """Retorna el mínimo de una lista de argumentos"""
    try:
        # Filtramos valores no numéricos por seguridad
        valid_nums = [float(x) for x in args if x is not None]
        return min(valid_nums) if valid_nums else 0
    except:
        return 0

def SII_MAX(*args):
    """Retorna el máximo de una lista de argumentos"""
    try:
        valid_nums = [float(x) for x in args if x is not None]
        return max(valid_nums) if valid_nums else 0
    except:
        return 0

# --- AQUI AGREGARAS TUS FUNCIONES RARAS DESPUES ---
# def SII_BIN1(valor): ...