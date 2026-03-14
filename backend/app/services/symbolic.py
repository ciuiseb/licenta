import sympy
import numpy as np
from sympy import dsolve, Eq, Symbol, Function

class SymbolicSolver:
    def solve_exact(self, equation_expr, initial_values=None, t_range=(0, 10), points=100):
        """
        Rezolvă simbolic ecuații de ordin N.

        Args:
            equation_expr: Expresia SymPy (partea stângă a ecuației = 0).
            initial_values: Listă de valori [y(0), y'(0), y''(0), ...].
                            Dacă e None sau goală, returnează soluția generală (cu C1, C2).
        """
        try:
            t_sym = sympy.Symbol('t')
            y_sym = sympy.Function('y')(t_sym)

            print(f"DEBUG: Solving equation: {equation_expr} = 0")
            print(f"DEBUG: Initial values: {initial_values}")

            ics = {}

            if initial_values:
                for i, val in enumerate(initial_values):
                    if i == 0:
                        condition_key = y_sym.subs(t_sym, 0)
                    else:
                        condition_key = y_sym.diff(t_sym, i).subs(t_sym, 0)

                    ics[condition_key] = val
                    print(f"DEBUG: Condition {i}: {condition_key} = {val}")

            print(f"DEBUG: ICS dictionary: {ics}")

            solution = dsolve(Eq(equation_expr, 0), y_sym, ics=ics)
            print(f"DEBUG: Raw solution: {solution}")
            print(f"DEBUG: Solution type: {type(solution)}")

            if isinstance(solution, list):
                solution = solution[0]
                print(f"DEBUG: Using first solution from list: {solution}")

            print(f"DEBUG: Final solution: {solution}")
            print(f"DEBUG: Solution RHS: {solution.rhs}")

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