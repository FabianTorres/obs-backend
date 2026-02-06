from app.generator.math_engine import MathEngine
from .utils_mixin import BuilderUtilsMixin
from .combinatorics_mixin import CombinatoricsMixin
from .solvers_mixin import VariableSolverMixin
from .norms_mixin import NormGeneratorMixin

class ScenarioBuilder(BuilderUtilsMixin, CombinatoricsMixin, VariableSolverMixin, NormGeneratorMixin):
    def __init__(self, logic_tree, parameters={}, macros={}):
        self.logic_tree = logic_tree
        self.parameters = parameters
        self.macros = macros
        self.math_engine = MathEngine(macros=self.macros)
        self.scenarios = []
        self.case_id = 11467
        self.var_definitions = self._map_variable_definitions()

    def build_suite(self):
        """Genera la suite completa de pruebas"""
        
        # 1. Condición de Entrada
        cond_block = self._find_section("Condicion_Entrada")
        ok_scenarios_inputs = self._generate_ok_combinations(cond_block)
        
        golden_inputs = {} 
        for i, inputs in enumerate(ok_scenarios_inputs):
            if i == 0: golden_inputs = inputs
            desc = self._describe_scenario(inputs)
            self._add_case("Cond. OK", f"Camino válido #{i+1}: {desc}", inputs, "Cumple Condición")

        # 2. Casos NK
        self._generate_nk_cases(cond_block, golden_inputs)

        # 3. VARIABLES
        vars_block = self._find_section("Variables")
        self._generate_variable_cases(vars_block, golden_inputs)

        # 4. Contexto Completo
        initial_context = {**golden_inputs, **self.parameters}
        computed_vars = self._calculate_variables(vars_block, initial_context)
        full_context = {**golden_inputs, **self.parameters, **computed_vars}
        
        # 5. Generación de Casos de Norma
        norm_block = self._find_section("Norma_Observacion")
        self._generate_norm_cases(norm_block, full_context, vars_block)

        return self.scenarios