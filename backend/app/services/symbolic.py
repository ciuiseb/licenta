import logging
import sympy
import numpy as np
from sympy import dsolve, Eq, Symbol, Function
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

DSOLVE_TIMEOUT = 15

logger = logging.getLogger(__name__)

class SymbolicSolver:
    def solve_exact(self, equation_expr, conditions=None, t_range=(0, 10), points=100, var_name='y'):
        logger.info(f"Starting symbolic solution for equation: {equation_expr}")
        logger.debug(f"Raw conditions received: {conditions}")

        try:
            t_sym = sympy.Symbol('t')
            y_sym = sympy.Function(var_name)(t_sym)

            ics = {}

            if conditions:
                for index, cond in enumerate(conditions):
                    t_val = sympy.sympify(str(cond['t']))
                    val = sympy.sympify(str(cond['val']))

                    order = cond.get('order', index)

                    if order == 0:
                        condition_key = y_sym.subs(t_sym, t_val)
                    else:
                        condition_key = y_sym.diff(t_sym, order).subs(t_sym, t_val)

                    ics[condition_key] = val
                    logger.debug(f"Mapped condition: {condition_key} = {val}")

            logger.info(f"Calling dsolve with ics: {ics}")
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(dsolve, Eq(equation_expr, 0), y_sym, ics=ics)
                try:
                    solution = future.result(timeout=DSOLVE_TIMEOUT)
                except FuturesTimeoutError:
                    logger.warning(f"dsolve timed out after {DSOLVE_TIMEOUT}s")
                    return {
                        "success": False,
                        "error": f"Symbolic solving timed out after {DSOLVE_TIMEOUT} seconds"
                    }

            if isinstance(solution, list):
                solution = solution[0]

            logger.info(f"Symbolic solution found: {solution.rhs}")

            t_vals = np.linspace(t_range[0], t_range[1], points)
            y_vals = []

            logger.debug(f"Lambdifying solution for {points} points in range {t_range}")
            solution_func = sympy.lambdify(t_sym, solution.rhs, 'numpy')

            try:
                y_vals = solution_func(t_vals)
                if isinstance(y_vals, (int, float)):
                    y_vals = [y_vals] * len(t_vals)
                else:
                    y_vals = y_vals.tolist()
                logger.debug("Successfully evaluated points using numpy lambdify.")
            except Exception as eval_error:
                logger.warning(f"Lambdify evaluation failed ({eval_error}). Falling back to sympy evaluation.")
                solution_func_sympy = sympy.lambdify(t_sym, solution.rhs, 'sympy')
                y_vals = np.vectorize(lambda t_val: float(solution_func_sympy(t_val)))(t_vals).tolist()

            logger.info("Successfully generated numerical data from symbolic solution.")
            return {
                "success": True,
                "formula_str": str(solution.rhs),
                "latex": sympy.latex(solution),
                "data": {
                    "x": t_vals.tolist(),
                    "y": y_vals
                }
            }

        except Exception as e:
            logger.error(f"Symbolic solver failed: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": f"No exact symbolic solution found: {str(e)}"
            }