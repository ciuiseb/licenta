import numpy as np
from scipy.integrate import solve_ivp, solve_bvp
import sympy
import logging
import traceback

logger = logging.getLogger(__name__)

class NumericalSolver:
    def solve_numerical(self, equation_expr, conditions, equation_type='ivp', t_range=(0, 10), points=100, var_name='y'):
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

            if len(conditions) != highest_order:
                raise ValueError(f"Equation is of order {highest_order}, but {len(conditions)} conditions were provided.")

            highest_deriv_term = func_sym.diff(t_sym, highest_order)
            solved = sympy.solve(equation_expr, highest_deriv_term)

            if not solved:
                raise ValueError("Could not isolate the highest derivative.")

            f_expr = solved[0]
            u_syms = sympy.symbols(f'u0:{highest_order}')
            subs_dict = {func_sym: u_syms[0]}
            for i in range(1, highest_order):
                subs_dict[func_sym.diff(t_sym, i)] = u_syms[i]

            f_system_expr = f_expr.subs(subs_dict)
            system_exprs = list(u_syms[1:]) + [f_system_expr]

            f_lambda = sympy.lambdify((u_syms, t_sym), system_exprs, modules='numpy')

            t_eval = np.linspace(t_range[0], t_range[1], points)

            if equation_type == 'ivp':
                y0 = [0.0] * highest_order
                for cond in conditions:
                    order = int(cond.get('order', 0))
                    if order < highest_order:
                        y0[order] = float(cond['val'])

                def ode_system_ivp(t, U):
                    return f_lambda(tuple(U), t)

                solution = solve_ivp(
                    ode_system_ivp,
                    t_range,
                    y0,
                    method='RK45',
                    t_eval=t_eval
                )

                if not solution.success:
                    raise ValueError(f"Integration failed: {solution.message}")

                y_vals = solution.y[0]

            elif equation_type == 'bvp':
                def ode_system_bvp(x, U):
                    U_unpacked = tuple(U[i] for i in range(U.shape[0]))
                    res = f_lambda(U_unpacked, x)

                    res_broadcast = [np.broadcast_to(r, x.shape) for r in res]
                    return np.array(res_broadcast)

                def bc(ya, yb):
                    res = []
                    for cond in conditions:
                        order = int(cond.get('order', 0))
                        target_val = float(cond['val'])
                        t_val = float(cond['t'])

                        if np.isclose(t_val, t_range[0], rtol=1e-9):
                            res.append(ya[order] - target_val)
                        elif np.isclose(t_val, t_range[1], rtol=1e-9):
                            res.append(yb[order] - target_val)
                        else:
                            if abs(t_val - t_range[0]) < abs(t_val - t_range[1]):
                                res.append(ya[order] - target_val)
                            else:
                                res.append(yb[order] - target_val)

                    return np.array(res)

                y_init = np.zeros((highest_order, points))

                solution = solve_bvp(ode_system_bvp, bc, t_eval, y_init)

                if not solution.success:
                    raise ValueError(f"BVP solver failed: {solution.message}")

                y_vals = solution.y[0]

            else:
                raise ValueError(f"Unknown equation type: {equation_type}")

            return {
                "success": True,
                "data": {
                    "x": t_eval.tolist(),
                    "y": y_vals.tolist()
                }
            }

        except Exception as e:
            logger.error(f"Numerical solver error: {str(e)}")
            logger.debug(f"Full traceback:\n{traceback.format_exc()}")
            return {
                "success": False,
                "error": f"Could not solve numerically: {str(e)}"
            }