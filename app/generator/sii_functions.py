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
def SII_BIN1(val1, val2):
    """Entrega primer valor solo si este es MAYOR que el segundo, si no 0"""
    return val1 if val1 > val2 else 0

def SII_BIN2(val1, val2):
    """Entrega primer valor solo si este es MENOR que el segundo, si no 0"""
    return val1 if val1 < val2 else 0

def SII_ABS(val):
    """Valor absoluto"""
    return abs(val)

def SII_NEG(val):
    """Opuesto de POS: Si es negativo entrega su valor absoluto, sino 0"""
    return abs(val) if val < 0 else 0

def SII_M11(val):
    """
    Cálculo de Dígito Verificador (Módulo 11) estándar chileno.
    Retorna el DV (0-9 o 'K').
    """
    try:
        # Aseguramos que trabajamos con la parte entera del número
        numero = int(val)
    except:
        return 0 # Manejo de error por defecto

    reversed_digits = map(int, reversed(str(numero)))
    factors = itertools.cycle(range(2, 8)) # 2, 3, 4, 5, 6, 7, 2...
    s = sum(d * f for d, f in zip(reversed_digits, factors))
    
    res = (-s) % 11
    
    if res == 10: return "K" # Ojo: Retorna String
    return res

# Necesario para el M11
import itertools