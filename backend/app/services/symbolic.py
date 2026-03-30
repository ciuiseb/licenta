import logging
import sympy
import numpy as np
from sympy import dsolve, Eq, Symbol, Function

class SymbolicSolver:
    def solve_exact(self, equation_expr, conditions=None, t_range=(0, 10), points=100, var_name='y'):
        try:
            t_sym = sympy.Symbol('t')
            y_sym = sympy.Function(var_name)(t_sym)

            ics = {}

            if conditions:
                for cond in conditions:
                    t_val = float(cond['t'])
                    val = float(cond['val'])
                    order = cond.get('order', 0)

                    if order == 0:
                        condition_key = y_sym.subs(t_sym, t_val)
                    else:
                        condition_key = y_sym.diff(t_sym, order).subs(t_sym, t_val)

                    ics[condition_key] = val

            solution = dsolve(Eq(equation_expr, 0), y_sym, ics=ics)

            if isinstance(solution, list):
                solution = solution[0]


            t_vals = np.linspace(t_range[0], t_range[1], points)
            y_vals = []

            solution_func = sympy.lambdify(t_sym, solution.rhs, 'numpy')

            try:
                y_vals = solution_func(t_vals)
                if isinstance(y_vals, (int, float)):
                    y_vals = [y_vals] * len(t_vals)
                else:
                    y_vals = y_vals.tolist()
            except Exception as eval_error:
                for t_val in t_vals:
                    y_val = float(solution.rhs.subs(t_sym, t_val))
                    y_vals.append(y_val)

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
            return {
                "success": False,
                "error": f"Nu s-a găsit soluție simbolică exactă: {str(e)}"
            }