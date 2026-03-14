import numpy as np
from scipy.integrate import odeint
import sympy

class NumericalSolver:
    def solve_numerical(self, equation_expr, initial_conditions, t_range=(0, 10), points=100):
        """
        Rezolvă numeric ecuații diferențiale de ordinul N.

        Args:
            equation_expr: Expresia SymPy (ex: y'' + y). Se presupune = 0.
            initial_conditions: Listă de valori [y(0), y'(0), ...].
            t_range: Tuplu (start, end).
            points: Numărul de puncte pentru grafic.
        """

        t_sym = sympy.Symbol('t')
        y_sym = sympy.Function('y')(t_sym)

        try:
            highest_order = 0
            derivs = equation_expr.atoms(sympy.Derivative)
            for d in derivs:
                if d.has(y_sym):
                    order = d.derivative_count
                    if order > highest_order:
                        highest_order = order

            if highest_order == 0:
                highest_order = 1

            if len(initial_conditions) != highest_order:
                raise ValueError(f"Ecuația este de ordin {highest_order}, dar ai oferit {len(initial_conditions)} condiții inițiale.")

            highest_deriv_term = y_sym.diff(t_sym, highest_order)

            solved = sympy.solve(equation_expr, highest_deriv_term)

            if not solved:
                raise ValueError("Nu am putut izola cea mai mare derivată.")

            f_expr = solved[0]


            u_syms = sympy.symbols(f'u0:{highest_order}')

            subs_dict = {y_sym: u_syms[0]}
            for i in range(1, highest_order):
                subs_dict[y_sym.diff(t_sym, i)] = u_syms[i]

            f_system_expr = f_expr.subs(subs_dict)

            system_exprs = list(u_syms[1:]) + [f_system_expr]

            f_lambda = sympy.lambdify((u_syms, t_sym), system_exprs, modules='numpy')

            def ode_system(U, t):
                return f_lambda(U, t)

            t_eval = np.linspace(t_range[0], t_range[1], points)

            solution = odeint(ode_system, initial_conditions, t_eval)

            y_vals = solution[:, 0]

            return {
                "success": True,
                "data": {
                    "x": t_eval.tolist(),
                    "y": y_vals.tolist()
                }
            }

        except Exception as e:
            print(f"Eroare Numerică Internă: {e}")
            return {
                "success": False,
                "error": f"Nu am putut rezolva numeric: {str(e)}"
            }