import sympy
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
    convert_xor
)
from sympy import Symbol, Function, Derivative, Eq, classify_ode, ode_order

class MathParser:
    def __init__(self):
        self.t = Symbol('t')
        self.y = Function('y')(self.t)
        self.transformations = (
                standard_transformations +
                (implicit_multiplication_application, convert_xor)
        )

    def parse(self, equation_str):
        try:
            import re
            
            def replace_derivative(match):
                prime_count = len(match.group(1))
                if prime_count == 1:
                    return "diff(y,t)"
                else:
                    t_params = ",".join(["t"] * (prime_count - 1))
                    return f"diff(y,t,{t_params})"
            
            clean_str = re.sub(r"y('+)", replace_derivative, equation_str)

            local_dict = {'y': self.y, 't': self.t}
            if "=" in clean_str:
                lhs_str, rhs_str = clean_str.split("=")
                lhs = parse_expr(lhs_str, local_dict=local_dict, transformations=self.transformations)
                rhs = parse_expr(rhs_str, local_dict=local_dict, transformations=self.transformations)
                equation_expr = lhs - rhs
            else:
                equation_expr = parse_expr(clean_str, local_dict=local_dict, transformations=self.transformations)

            order = ode_order(equation_expr, self.y)
            hints = classify_ode(Eq(equation_expr, 0), self.y)
            is_linear = any("linear" in hint for hint in hints)

            val_t = Symbol('val_t')
            val_y = Symbol('val_y')
            
            derivative_symbols = [val_y]
            substitutions = {
                self.y: val_y,
                self.t: val_t
            }
            
            for i in range(1, order + 1):
                if i == 1:
                    deriv_symbol = Symbol('val_dy')
                elif i == 2:
                    deriv_symbol = Symbol('val_d2y')
                elif i == 3:
                    deriv_symbol = Symbol('val_d3y')
                elif i == 4:
                    deriv_symbol = Symbol('val_d4y')
                else:
                    deriv_symbol = Symbol(f'val_d{i}y')
                
                derivative_symbols.append(deriv_symbol)
                substitutions[self.y.diff(self.t, i)] = deriv_symbol
            
            func_expr = equation_expr.subs(substitutions)

            torch_func = sympy.lambdify(
                tuple([val_t] + derivative_symbols),
                func_expr,
                modules="torch"
            )

            return {
                "success": True,
                "latex": sympy.latex(Eq(equation_expr, 0)),
                "sympy_object": equation_expr,
                "torch_func": torch_func,

                "meta": {
                    "linearity": "Linear" if is_linear else "Non-linear",
                    "order": order,
                    "methods": hints
                }
            }

        except Exception as e:
            return { "success": False, "error": str(e) }