import re
import sympy
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
    convert_xor
)
from sympy import Symbol, Function, Eq, classify_ode, ode_order

class MathParser:
    def __init__(self):
        self.t = Symbol('t')
        self.transformations = (
                standard_transformations +
                (implicit_multiplication_application, convert_xor)
        )

    def parse(self, equation_str):
        try:
            var_match = re.search(r"\b([a-zA-Z])'+", equation_str)
            var_name = var_match.group(1) if var_match else 'y'

            dyn_func = Function(var_name)(self.t)

            def check_notation_consistency(equation):
                single_letters = set(re.findall(r'\b[a-zA-Z]\b', equation))
                allowed_letters = {var_name, 't', 'e'}
                invalid_letters = single_letters - allowed_letters

                if invalid_letters:
                    return False, f"Inconsistent variables detected: {', '.join(invalid_letters)}. Use only '{var_name}' and 't'."

                if re.search(fr"\b{var_name}\([^)]*\)'+", equation):
                    return False, f"Invalid notation. Use {var_name}'(t) instead of {var_name}(t)'."

                has_deriv_with_t = bool(re.search(fr"\b{var_name}'+\s*\(", equation))
                has_deriv_without_t = bool(re.search(fr"\b{var_name}'+(?!\s*\()", equation))
                has_plain_with_t = bool(re.search(fr"\b{var_name}\b\s*\(", equation))
                has_plain_without_t = bool(re.search(fr"\b{var_name}\b(?!\s*['(])", equation))

                if (has_deriv_with_t and has_plain_without_t) or (has_deriv_without_t and has_plain_with_t):
                    return False, f"Mixed notation detected. Use either {var_name}'(t) + {var_name}(t) or {var_name}' + {var_name} consistently."

                return True, ""

            is_consistent, error_msg = check_notation_consistency(equation_str)
            if not is_consistent:
                return {"success": False, "error": error_msg}

            def replace_derivative(match):
                prime_count = len(match.group(1))
                if prime_count == 1:
                    return f"diff({var_name},t)"
                else:
                    t_params = ",".join(["t"] * (prime_count - 1))
                    return f"diff({var_name},t,{t_params})"

            clean_str = re.sub(fr"\b{var_name}('+)\([^)]*\)", replace_derivative, equation_str)
            clean_str = re.sub(fr"\b{var_name}('+(?!\())", replace_derivative, clean_str)

            local_dict = {var_name: dyn_func, 't': self.t}

            if "=" in clean_str:
                lhs_str, rhs_str = clean_str.split("=")
                lhs = parse_expr(lhs_str, local_dict=local_dict, transformations=self.transformations)
                rhs = parse_expr(rhs_str, local_dict=local_dict, transformations=self.transformations)
                equation_expr = lhs - rhs
            else:
                equation_expr = parse_expr(clean_str, local_dict=local_dict, transformations=self.transformations)

            order = ode_order(equation_expr, dyn_func)
            
            if order > 4:
                return {
                    "success": False,
                    "error": f"Equation order ({order}) exceeds maximum supported order (4)"
                }
            
            hints = classify_ode(Eq(equation_expr, 0), dyn_func)
            is_linear = any("linear" in hint for hint in hints)

            val_t = Symbol('val_t')
            val_y = Symbol('val_y')

            derivative_symbols = [val_y]
            substitutions = {
                dyn_func: val_y,
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
                substitutions[dyn_func.diff(self.t, i)] = deriv_symbol

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
                    "methods": hints,
                    "variable": var_name
                }
            }

        except Exception as e:
            return { "success": False, "error": str(e) }