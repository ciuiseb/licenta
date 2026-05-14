from sympy import dsolve, Eq


def run_dsolve(equation_expr, y_sym, ics, queue):
    try:
        solution = dsolve(Eq(equation_expr, 0), y_sym, ics=ics if ics else None)
        queue.put(("ok", solution))
    except Exception as e:
        queue.put(("error", str(e)))
