from flask import Blueprint, request, jsonify, Response, stream_with_context
import json
import time
import logging
from app.services.validator import CauchyValidator
from app.services.numerical import NumericalSolver
from app.services.symbolic import SymbolicSolver
from app.services.pinn_service import PinnService
from app.services.export_service import ExportService
from app.utils.error_handler import handle_errors, ValidationError, ServerError
from app.utils.validators import validate_solve_request, validate_export_request

logger = logging.getLogger(__name__)

math_bp = Blueprint('math', __name__)

validator = CauchyValidator()
numerical = NumericalSolver()
symbolic = SymbolicSolver()
exporter = ExportService()

current_pinn_solver = None

@math_bp.route('/solve', methods=['POST'])
@handle_errors
def solve():
    data = request.get_json()
    formula, conditions, t_max, equation_type = process_data(data)

    if equation_type == 'ivp':
        return solve_cauchy(formula, conditions, t_max)
    else:
        raise ValidationError(f"Unknown equation type: {equation_type}")


def solve_cauchy(formula, conditions, t_max):
    check = validator.validate(formula, conditions)
    if not check['valid']:
        raise ValidationError(check['error'])

    parsed_data = check['parsed']
    order = check['order']
    initial_vals = [c['val'] for c in conditions]
    t0 = float(conditions[0]['t'])

    sym_res = symbolic.solve_exact(
        parsed_data['sympy_object'],
        initial_vals,
        t_range=(t0, t_max),
        points=100,
        var_name=parsed_data['meta'].get('variable', 'y'),
    )

    num_res = numerical.solve_numerical(
        parsed_data['sympy_object'],
        initial_vals,
        t_range=(t0, t_max),
        var_name=parsed_data['meta'].get('variable', 'y')
    )

    pinn_res = None
    try:
        pinn_solver = PinnService()
        torch_func = parsed_data['torch_func']
        logger.info("Starting PINN training...")
        pinn_data = pinn_solver.train_model(
            torch_func,
            conditions,
            t_max_override=t_max
        )

        pinn_res = {
            "success": True,
            "data": pinn_data
        }
    except Exception as e:
        logger.error(f"PINN Error: {e}", exc_info=True)
        pinn_res = { "success": False, "error": str(e) }

    return jsonify({
        "success": True,
        "meta": {
            "latex": parsed_data['latex'],
            "order": order,
            "linearity": parsed_data['meta'].get('linearity', 'Unknown')
        },
        "symbolic": sym_res,
        "numerical": num_res,
        "pinn": pinn_res
    })

@math_bp.route('/export/<format_type>', methods=['POST'])
@handle_errors
def export_data(format_type):
    """
    Endpoint pentru descărcarea datelor ca CSV sau JSON.
    Primește datele (x, y) din frontend și le returnează ca fișier.
    """
    data = request.get_json()

    validated_data = validate_export_request(data)
    x_data = validated_data['x']
    y_data = validated_data['y']

    if format_type == 'csv':
        csv_content = exporter.generate_csv(x_data, y_data)
        return Response(
            csv_content,
            mimetype="text/csv",
            headers={"Content-disposition": "attachment; filename=solution.csv"}
        )

    elif format_type == 'json':
        metadata = data.get('meta', {"source": "MathPlatform License Project"})
        json_content = exporter.generate_json(x_data, y_data, metadata)

        return Response(
            json_content,
            mimetype="application/json",
            headers={"Content-disposition": "attachment; filename=solution.json"}
        )

    else:
        raise ValidationError(f"Invalid format type: {format_type}. Supported formats: csv, json")
def process_data(data):
    """Extract and process validated request data."""
    validated_data = validate_solve_request(data)

    formula = validated_data['formula']
    conditions = validated_data['conditions']
    t_max = validated_data['tMax']
    equation_type = validated_data['equation_type']
    return formula, conditions, t_max, equation_type

@math_bp.route('/solve/stream', methods=['POST', 'OPTIONS'])
def stream_pinn_training():
    """
    Streaming endpoint for real-time PINN training updates.
    Uses Server-Sent Events (SSE) for real-time communication.
    """
    if request.method == 'OPTIONS':
        return '', 200

    try:
        data = request.get_json()
        logger.info(f"Received data: {data}")
        formula, conditions, t_max, equation_type = process_data(data)
        
        logger.info(f"Formula: {formula}, tMax: {t_max}, conditions: {conditions}")

        check = validator.validate(formula, conditions)
        if not check['valid']:
            logger.error(f"Validation failed: {check.get('error')}")
            error_data = {
                "type": "training_error",
                "error": check['error'],
                "timestamp": time.time()
            }
            return Response(
                f"data: {json.dumps(error_data)}\n\n",
                mimetype='text/event-stream',
                status=400
            )

        parsed_data = check['parsed']
        initial_vals = [c['val'] for c in conditions]
        torch_func = parsed_data['torch_func']
        validated_data = validate_solve_request(data)
        t0 = float(conditions[0]['t'])
        custom_params = validated_data.get('parameters', {})
        def generate_training_stream():
            global current_pinn_solver
            try:
                if equation_type == 'ivp':
                    sym_res = symbolic.solve_exact(
                        parsed_data['sympy_object'],
                        initial_vals,
                        t_range=(t0, t_max),
                        points=100,
                        var_name=parsed_data['meta'].get('variable', 'y')
                    )
                else:
                    # Handle BVP symbolic solving when implemented
                    sym_res = {"success": False, "error": "BVP symbolic solver not implemented yet"}

                num_res = numerical.solve_numerical(
                    parsed_data['sympy_object'],
                    initial_vals,
                    t_range=(t0, t_max),
                    var_name=parsed_data['meta'].get('variable', 'y')
                )
                
                initial_data = {
                    "type": "initial_solutions",
                    "numerical": num_res,
                    "symbolic": sym_res,
                    "timestamp": time.time()
                }
                yield f"data: {json.dumps(initial_data)}\n\n"
                
                pinn_solver = PinnService(custom_params=custom_params)
                
                def training_callback(epoch, loss_physics, loss_boundary, total_loss, function_data):
                    update_data = {
                        "type": "epoch_update",
                        "epoch": epoch,
                        "loss": {
                            "total": total_loss,
                            "physics": loss_physics,
                            "boundary": loss_boundary
                        },
                        "function_data": function_data,
                        "timestamp": time.time()
                    }
                    return f"data: {json.dumps(update_data)}\n\n"
                
                for update in pinn_solver.train_model_stream(
                    torch_func, 
                    conditions,
                    problem_type=equation_type,
                    t_max_override=t_max,
                    callback=training_callback
                ):
                    yield update
                
                current_pinn_solver = pinn_solver
                
                final_result = pinn_solver.get_function_data(t0, t_max)
                final_data = {
                    "type": "training_complete",
                    "success": True,
                    "final_data": final_result,
                    "timestamp": time.time()
                }
                yield f"data: {json.dumps(final_data)}\n\n"

            except Exception as e:
                import traceback
                error_trace = traceback.format_exc()
                logger.error(f"Training error: {str(e)}")
                logger.error(f"Full traceback:\n{error_trace}")
                error_data = {
                    "type": "training_error",
                    "error": str(e),
                    "traceback": error_trace,
                    "timestamp": time.time()
                }
                yield f"data: {json.dumps(error_data)}\n\n"

        response = Response(
            stream_with_context(generate_training_stream()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no'
            }
        )
        return response
    except ValidationError as e:
        import traceback
        logger.error(f"OUTER Validation error: {str(e)}")
        logger.error(f"OUTER Validation traceback:\n{traceback.format_exc()}")
        error_data = {
            "type": "validation_error",
            "error": str(e),
            "timestamp": time.time()
        }
        return Response(
            f"data: {json.dumps(error_data)}\n\n",
            mimetype='text/event-stream',
            status=400
        )
    except Exception as e:
        import traceback
        logger.error(f"OUTER Unexpected error: {str(e)}")
        logger.error(f"OUTER Unexpected traceback:\n{traceback.format_exc()}")
        error_data = {
            "type": "server_error",
            "error": "An unexpected error occurred",
            "timestamp": time.time()
        }
        return Response(
            f"data: {json.dumps(error_data)}\n\n",
            mimetype='text/event-stream',
            status=500
        )

@math_bp.route('/evaluate', methods=['POST'])
@handle_errors
def evaluate_point():
    """
    Evaluate the trained PINN model at a specific point.
    Requires a trained model from previous /solve/stream call.
    """
    global current_pinn_solver
    
    if current_pinn_solver is None:
        raise ValidationError("No trained model available. Please train a model first using /solve/stream")
    
    data = request.get_json()
    
    if 't' not in data:
        raise ValidationError("Missing required parameter: 't'")
    
    try:
        t_value = float(data['t'])
    except (ValueError, TypeError):
        raise ValidationError(f"Invalid value for 't': {data['t']}. Must be a number.")
    
    y_value = current_pinn_solver.evaluate_at_point(t_value)
    
    return jsonify({
        "success": True,
        "t": t_value,
        "y": y_value
    })
