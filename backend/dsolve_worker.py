from sympy import dsolve, Eq, simplify


def run_dsolve(equation_expr, y_sym, ics, queue):
    try:
        if ics:
            solution = dsolve(Eq(equation_expr, 0), y_sym, ics=ics)
        else:
            solution = dsolve(Eq(equation_expr, 0), y_sym, simplify=False)
            try:
                if isinstance(solution, list):
                    solution = [Eq(s.lhs, simplify(s.rhs)) for s in solution]
                else:
                    solution = Eq(solution.lhs, simplify(solution.rhs))
            except Exception:
                pass
        queue.put(("ok", solution))
    except Exception as e:
        queue.put(("error", str(e)))
