from app.utils.error_handler import ValidationError

def validate_solve_request(data):
    """Validate /solve and /solve/stream request payload"""
    if not data:
        raise ValidationError("Request body is required")
    
    formula = data.get('formula')
    if not formula or not isinstance(formula, str):
        raise ValidationError("'formula' is required and must be a string")
    
    if len(formula.strip()) == 0:
        raise ValidationError("'formula' cannot be empty")
    
    if len(formula) > 500:
        raise ValidationError("'formula' is too long (max 500 characters)")
    
    conditions = data.get('conditions', [])
    if not isinstance(conditions, list):
        raise ValidationError("'conditions' must be a list")
    
    if len(conditions) == 0:
        raise ValidationError("At least one initial condition is required")
    
    for idx, cond in enumerate(conditions):
        if not isinstance(cond, dict):
            raise ValidationError(f"Condition {idx} must be an object")
        
        if 't' not in cond:
            raise ValidationError(f"Condition {idx} missing 't' field")
        
        if 'val' not in cond:
            raise ValidationError(f"Condition {idx} missing 'val' field")
        
        try:
            float(cond['t'])
            float(cond['val'])
        except (ValueError, TypeError):
            raise ValidationError(f"Condition {idx} has invalid numeric values")
    
    t_max = data.get('tMax', 10)
    try:
        t_max = float(t_max)
        if t_max <= 0:
            raise ValidationError("'tMax' must be positive")
        if t_max > 1000:
            raise ValidationError("'tMax' cannot exceed 1000")
    except (ValueError, TypeError):
        raise ValidationError("'tMax' must be a valid number")
    
    parameters = data.get('parameters', {})
    if parameters and not isinstance(parameters, dict):
        raise ValidationError("'parameters' must be an object")

    if 'learning_rate' in parameters:
        lr = parameters['learning_rate']
        try:
            lr = float(lr)
            if lr <= 0 or lr > 1:
                raise ValidationError("'learning_rate' must be between 0 and 1")
        except (ValueError, TypeError):
            raise ValidationError("'learning_rate' must be a valid number")

    equation_type = data.get('equation_type')
    if equation_type not in ['ivp', 'bvp']:
        raise ValidationError(f"Equation type {equation_type} is not supported")
    return {
        'formula': formula.strip(),
        'conditions': conditions,
        'tMax': t_max,
        'parameters': parameters,
        'equation_type': equation_type
    }
