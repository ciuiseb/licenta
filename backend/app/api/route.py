from flask import Blueprint, request, jsonify, Response, stream_with_context
import json
import time
import logging
import uuid
import sympy
import numpy as np
import threading
from app.services.validator import CauchyValidator
from app.services.numerical import NumericalSolver
from app.services.symbolic import SymbolicSolver
from app.services.pinn_service import PinnService
from app.services.training_queue import training_queue
from app.utils.error_handler import handle_errors, ValidationError, ServerError
from app.utils.validators import validate_solve_request
from app.middleware.auth import require_auth, get_session_id

logger = logging.getLogger(__name__)
PINN_MODEL_TTL_SECONDS = 3600
STREAM_MAX_DURATION_SECONDS = 1800

math_bp = Blueprint('math', __name__)

validator = CauchyValidator()
numerical = NumericalSolver()
symbolic = SymbolicSolver()

active_pinn_solvers = {}
solvers_lock = threading.Lock()

def _prepare_solve_context(data):
    formula, conditions, t_max, equation_type = process_data(data)

    check = validator.validate(formula, conditions)
    if not check['valid']:
        raise ValidationError(check['error'])

    parsed_data = check['parsed']
    order = check['order']
    t0 = _get_t_range_start(conditions, equation_type)

    return {
        "formula": formula,
        "conditions": conditions,
        "t_max": t_max,
        "equation_type": equation_type,
        "parsed_data": parsed_data,
        "order": order,
        "t0": t0
    }

def _compute_initial_solutions(parsed_data, conditions, equation_type, t0, t_max):
    var_name = parsed_data['meta'].get('variable')

    sym_res = symbolic.solve_exact(
        parsed_data['sympy_object'],
        conditions,
        t_range=(t0, t_max),
        points=100,
        var_name=var_name,
    )

    num_res = numerical.solve_numerical(
        parsed_data['sympy_object'],
        conditions,
        equation_type=equation_type,
        t_range=(t0, t_max),
        var_name=var_name
    )

    return sym_res, num_res


def _build_validation_metrics(pinn_solver, final_result, sym_res, num_res, torch_func, conditions, equation_type, t0, t_max):
    validation_metrics = {}

    pinn_t = np.array(final_result["function_data"]["x"])
    pinn_y = np.array(final_result["function_data"]["y"])

    if sym_res.get("success") and sym_res.get("data"):
        sym_t = np.array(sym_res["data"]["x"])
        sym_y = np.array(sym_res["data"]["y"])

        sym_y_interp = np.interp(pinn_t, sym_t, sym_y)
        validation_metrics["symbolic"] = pinn_solver.compute_validation_metrics(
            pinn_t, pinn_y, sym_y_interp
        )

    if num_res.get("success") and num_res.get("data"):
        num_t = np.array(num_res["data"]["x"])
        num_y = np.array(num_res["data"]["y"])

        num_y_interp = np.interp(pinn_t, num_t, num_y)
        validation_metrics["numerical"] = pinn_solver.compute_validation_metrics(
            pinn_t, pinn_y, num_y_interp
        )

    final_losses = pinn_solver.compute_final_losses(
        torch_func, conditions, equation_type, t0, t_max
    )
    validation_metrics["losses"] = final_losses
    return validation_metrics

def process_data(data):
    """Extract and process validated request data."""
    validated_data = validate_solve_request(data)

    formula = validated_data['formula']
    conditions = validated_data['conditions']
    t_max = validated_data['tMax']
    equation_type = validated_data['equation_type']
    return formula, conditions, t_max, equation_type


@math_bp.route('/solve/stream', methods=['POST', 'OPTIONS'])
@require_auth
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
        solve_context = _prepare_solve_context(data)
        formula = solve_context['formula']
        conditions = solve_context['conditions']
        t_max = solve_context['t_max']
        equation_type = solve_context['equation_type']
        parsed_data = solve_context['parsed_data']
        t0 = solve_context['t0']

        logger.info(f"Formula: {formula}, tMax: {t_max}, conditions: {conditions}")

        torch_func = parsed_data['torch_func']
        custom_params = data.get('parameters', {})
        def generate_training_stream():
            training_start_time = time.time()
            model_id = None
            ticket = training_queue.enqueue()
            slot_acquired = False
            try:
                pos, active, capacity, waiting = training_queue.snapshot(ticket)
                yield _sse_data({
                    "type": "queue_update",
                    "position": pos,
                    "active": active,
                    "capacity": capacity,
                    "waiting": waiting,
                    "timestamp": time.time()
                })

                last_position = pos
                while not slot_acquired:
                    slot_acquired = training_queue.wait_for_slot(ticket, timeout=1.0)
                    if slot_acquired:
                        break
                    if time.time() - training_start_time > STREAM_MAX_DURATION_SECONDS:
                        raise ServerError("Timed out waiting in training queue")
                    pos, active, capacity, waiting = training_queue.snapshot(ticket)
                    if pos != last_position:
                        last_position = pos
                        yield _sse_data({
                            "type": "queue_update",
                            "position": pos,
                            "active": active,
                            "capacity": capacity,
                            "waiting": waiting,
                            "timestamp": time.time()
                        })


                training_start_time = time.time()
                yield _sse_data({
                    "type": "queue_update",
                    "position": -1,
                    "active": training_queue.snapshot(ticket)[1],
                    "capacity": training_queue.max_concurrent,
                    "waiting": training_queue.snapshot(ticket)[3],
                    "timestamp": time.time()
                })

                sym_res, num_res = _compute_initial_solutions(
                    parsed_data,
                    conditions,
                    equation_type,
                    t0,
                    t_max
                )

                initial_data = {
                    "type": "initial_solutions",
                    "numerical": num_res,
                    "symbolic": sym_res,
                    "timestamp": time.time()
                }
                yield _sse_data(initial_data)
                pinn_solver = PinnService(custom_params=custom_params)
                session_id = get_session_id()
                model_id = _store_pinn_solver(pinn_solver, session_id)
                yield _sse_data({
                    "type": "model_ready",
                    "model_id": model_id,
                    "timestamp": time.time()
                })

                def training_callback(epoch, loss_physics, loss_boundary, total_loss, function_data):
                    if time.time() - training_start_time > STREAM_MAX_DURATION_SECONDS:
                        raise ServerError("Training stream timed out")
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
                    return _sse_data(update_data)

                for update in pinn_solver.train_model_stream(
                        torch_func,
                        conditions,
                        problem_type=equation_type,
                        t_max_override=t_max,
                        callback=training_callback
                ):
                    yield update

                final_result = pinn_solver.get_function_data(t0, t_max)
                validation_metrics = _build_validation_metrics(
                    pinn_solver, final_result, sym_res, num_res, torch_func, conditions, equation_type, t0, t_max
                )
                
                final_data = {
                    "type": "training_complete",
                    "success": True,
                    "model_id": model_id,
                    "final_data": final_result,
                    "validation": validation_metrics,
                    "timestamp": time.time()
                }
                yield _sse_data(final_data)

            except Exception as e:
                logger.error(f"Training error: {str(e)}", exc_info=True)
                error_data = {
                    "type": "training_error",
                    "error": str(e),
                    "timestamp": time.time()
                }
                yield _sse_data(error_data)
                _remove_pinn_solver(model_id)
            finally:
                if slot_acquired:
                    training_queue.release(ticket)
                else:
                    training_queue.abandon(ticket)

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
        logger.warning(f"OUTER Validation error: {str(e)}")
        error_data = {
            "type": "validation_error",
            "error": str(e),
            "timestamp": time.time()
        }
        return Response(
            _sse_data(error_data),
            mimetype='text/event-stream',
            status=400
        )
    except Exception as e:
        logger.error(f"OUTER Unexpected error: {str(e)}", exc_info=True)
        error_data = {
            "type": "server_error",
            "error": "An unexpected error occurred",
            "timestamp": time.time()
        }
        return Response(
            _sse_data(error_data),
            mimetype='text/event-stream',
            status=500
        )


@math_bp.route('/stop', methods=['POST'])
@require_auth
@handle_errors
def stop_training():
    data = request.get_json()

    if not data:
        raise ValidationError("Request body is required")

    model_id = data.get('model_id')
    if not model_id or not isinstance(model_id, str):
        raise ValidationError("Missing required parameter: 'model_id'")

    session_id = get_session_id()
    pinn_solver = _get_pinn_solver(model_id, session_id)
    if pinn_solver is None:
        raise ValidationError("No active trained model available for the provided model_id")

    pinn_solver.request_stop()

    return jsonify({
        "success": True,
        "model_id": model_id,
        "message": "Stop requested"
    })

@math_bp.route('/evaluate', methods=['POST'])
@require_auth
@handle_errors
def evaluate_point():
    """
    Evaluate the trained PINN model at a specific point.
    Requires a model_id returned from a previous /solve/stream call.
    """
    data = request.get_json()

    if not data:
        raise ValidationError("Request body is required")

    model_id = data.get('model_id')
    if not model_id or not isinstance(model_id, str):
        raise ValidationError("Missing required parameter: 'model_id'")

    session_id = get_session_id()
    pinn_solver = _get_pinn_solver(model_id, session_id)
    if pinn_solver is None:
        raise ValidationError("No trained model available for the provided model_id. Please train a model first using /solve/stream")
    
    if 't' not in data:
        raise ValidationError("Missing required parameter: 't'")
    
    try:
        t_value = float(data['t'])
    except (ValueError, TypeError):
        raise ValidationError(f"Invalid value for 't': {data['t']}. Must be a number.")
    
    y_value = pinn_solver.evaluate_at_point(t_value)
    
    return jsonify({
        "success": True,
        "model_id": model_id,
        "t": t_value,
        "y": y_value
    })

def _get_t_range_start(conditions, equation_type):
    if equation_type == 'bvp' and conditions:
        return min(float(cond['t']) for cond in conditions)
    return float(conditions[0]['t'])


def _cleanup_expired_pinn_solvers():
    current_time = time.time()
    with solvers_lock:
        expired_model_ids = [
            model_id
            for model_id, model_entry in active_pinn_solvers.items()
            if current_time - model_entry["created_at"] > PINN_MODEL_TTL_SECONDS
        ]
        for model_id in expired_model_ids:
            active_pinn_solvers.pop(model_id, None)
            logger.info(f"Cleaned up expired model: {model_id}")


def _store_pinn_solver(pinn_solver, session_id):
    _cleanup_expired_pinn_solvers()
    model_id = str(uuid.uuid4())
    with solvers_lock:
        active_pinn_solvers[model_id] = {
            "solver": pinn_solver,
            "session_id": session_id,
            "created_at": time.time()
        }
    logger.info(f"Stored model {model_id} for session {session_id}")
    return model_id


def _get_pinn_solver(model_id, session_id):
    _cleanup_expired_pinn_solvers()
    with solvers_lock:
        model_entry = active_pinn_solvers.get(model_id)
        if model_entry and model_entry.get("session_id") == session_id:
            return model_entry["solver"]
    return None


def _remove_pinn_solver(model_id):
    if model_id:
        with solvers_lock:
            active_pinn_solvers.pop(model_id, None)
        logger.info(f"Removed model: {model_id}")


def _json_default(value):
    if isinstance(value, sympy.Basic):
        if value.is_real:
            return float(value)
        return str(value)

    item_method = getattr(value, 'item', None)
    if callable(item_method):
        try:
            return value.item()
        except Exception:
            pass

    raise TypeError(f"Object of type {value.__class__.__name__} is not JSON serializable")


def _sse_data(payload):
    return f"data: {json.dumps(payload, default=_json_default)}\n\n"