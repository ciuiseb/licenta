import numpy as np
from scipy.integrate import solve_ivp
import sympy

class NumericalSolver:
    def solve_numerical(self, equation_expr, initial_conditions, t_range=(0, 10), points=100, var_name='y'):
        t_sym = sympy.Symbol('t')
        func_sym = sympy.Function(var_name)(t_sym)

        try:
            highest_order = 0
            derivs = equation_expr.atoms(sympy.Derivative)
            for d in derivs:
                if d.has(func_sym):
                    order = d.derivative_count
                    if order > highest_order:
                        highest_order = order

            if highest_order == 0:
                highest_order = 1

            if len(initial_conditions) != highest_order:
                raise ValueError(f"Ecuația este de ordin {highest_order}, dar ai oferit {len(initial_conditions)} condiții inițiale.")

            highest_deriv_term = func_sym.diff(t_sym, highest_order)

            solved = sympy.solve(equation_expr, highest_deriv_term)

            if not solved:
                raise ValueError("Nu am putut izola cea mai mare derivată.")

            f_expr = solved[0]
            u_syms = sympy.symbols(f'u0:{highest_order}')
            subs_dict = {func_sym: u_syms[0]}
            for i in range(1, highest_order):
                subs_dict[func_sym.diff(t_sym, i)] = u_syms[i]

            f_system_expr = f_expr.subs(subs_dict)
            system_exprs = list(u_syms[1:]) + [f_system_expr]
            f_lambda = sympy.lambdify((u_syms, t_sym), system_exprs, modules='numpy')

            def ode_system(t, U):
                return f_lambda(U, t)

            t_eval = np.linspace(t_range[0], t_range[1], points)

            solution = solve_ivp(
                ode_system,
                t_range,
                initial_conditions,
                method='RK45',
                t_eval=t_eval
            )

            if not solution.success:
                raise ValueError(f"Integrarea a eșuat: {solution.message}")

            y_vals = solution.y[0]

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