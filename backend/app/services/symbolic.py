import logging
import sympy
import numpy as np
import multiprocessing as mp
from sympy import dsolve, Eq, Symbol, Function

DSOLVE_TIMEOUT = 15
IC_RESIDUAL_TOLERANCE = 1e-8  # branches with combined IC residual below this are considered to satisfy ICs

logger = logging.getLogger(__name__)


def _dsolve_worker(equation_expr, y_sym, ics, queue):
    """Run dsolve in a child process and put the result (or error) on the queue."""
    try:
        solution = dsolve(Eq(equation_expr, 0), y_sym, ics=ics)
        queue.put(("ok", solution))
    except Exception as e:
        queue.put(("error", str(e)))


def _ic_residual(branch, conditions, t_sym, var_name='y'):
    """Total absolute residual when ICs are substituted into a candidate branch.

    Lower is better. ~0 means the branch satisfies all ICs.
    Returns float('inf') if any substitution fails (e.g. complex / undefined).
    """
    try:
        rhs = branch.rhs
        total = sympy.Float(0)
        for index, cond in enumerate(conditions):
            t_val = sympy.sympify(str(cond['t']))
            val = sympy.sympify(str(cond['val']))
            order = cond.get('order', index)
            expr_at_t = rhs.diff(t_sym, order).subs(t_sym, t_val) if order > 0 else rhs.subs(t_sym, t_val)
            total += sympy.Abs(sympy.nsimplify(expr_at_t) - val)
        return float(sympy.N(total))
    except Exception as e:
        logger.debug(f"IC residual evaluation failed for branch {branch}: {e}")
        return float('inf')

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
            ctx = mp.get_context("spawn")
            queue = ctx.Queue()
            proc = ctx.Process(target=_dsolve_worker, args=(equation_expr, y_sym, ics, queue))
            proc.start()
            proc.join(timeout=DSOLVE_TIMEOUT)

            if proc.is_alive():
                logger.warning(f"dsolve timed out after {DSOLVE_TIMEOUT}s, terminating worker process")
                proc.terminate()
                proc.join(timeout=2)
                if proc.is_alive():
                    proc.kill()
                    proc.join()
                return {
                    "success": False,
                    "error": f"Symbolic solving timed out after {DSOLVE_TIMEOUT} seconds"
                }

            try:
                status, payload = queue.get_nowait()
            except Exception:
                return {
                    "success": False,
                    "error": "Symbolic worker exited without producing a result"
                }

            if status == "error":
                return {
                    "success": False,
                    "error": f"dsolve raised: {payload}"
                }

            solution = payload

            if isinstance(solution, list):
                if len(solution) == 1:
                    solution = solution[0]
                else:
                    logger.warning(f"dsolve returned {len(solution)} candidate branches; filtering by ICs")
                    residuals = [(_ic_residual(b, conditions or [], t_sym, var_name), b) for b in solution]
                    for r, b in residuals:
                        logger.info(f"  branch {b.rhs} -> IC residual = {r:.3e}")
                    matching = [b for r, b in residuals if r < IC_RESIDUAL_TOLERANCE]

                    if len(matching) == 1:
                        solution = matching[0]
                        logger.info(f"Selected unique branch satisfying ICs: {solution.rhs}")
                    elif len(matching) == 0:
                        return {
                            "success": False,
                            "error": (
                                f"dsolve produced {len(solution)} branches, none satisfying the "
                                f"initial conditions within tolerance {IC_RESIDUAL_TOLERANCE:.0e}"
                            )
                        }
                    else:
                        branch_strs = ", ".join(str(b.rhs) for b in matching)
                        logger.warning(
                            f"Non-unique solution: {len(matching)} branches all satisfy the ICs "
                            f"(Picard uniqueness fails). Branches: {branch_strs}"
                        )
                        return {
                            "success": False,
                            "error": (
                                f"ODE has {len(matching)} distinct solutions matching the given "
                                f"initial conditions (uniqueness fails); cannot pick one symbolically. "
                                f"Branches: {branch_strs}"
                            )
                        }

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