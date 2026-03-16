from app.services.parser_service import MathParser

class CauchyValidator:
    def __init__(self):
        self.parser = MathParser()

    def validate(self, formula_str, conditions):
        if not formula_str or not formula_str.strip():
            return {"valid": False, "error": "Equation cannot be empty."}

        parse_result = self.parser.parse(formula_str)
        if not parse_result['success']:
            return {
                "valid": False,
                    "error": parse_result.get('error')
            }

        required_order = parse_result['meta']['order']
        if len(conditions) != required_order:
            return {
                "valid": False,
                "error": f"Equation is Order {required_order}, but you gave {len(conditions)} conditions. Need {required_order}."
            }

        return {
            "valid": True,
            "parsed": parse_result,
            "order": required_order
        }