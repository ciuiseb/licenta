import logging
from itertools import count

import torch
import torch.nn as nn
from torch.optim import LBFGS
from app.utils.config_loader import load_pinn_config

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
logger = logging.getLogger(__name__)


class PINN(nn.Module):
    def __init__(self, layers, activation_name):
        super(PINN, self).__init__()
        self.depth = len(layers) - 1

        if activation_name == "tanh":
            self.activation = nn.Tanh()
        elif activation_name == "sigmoid":
            self.activation = nn.Sigmoid()
        else:
            self.activation = nn.Tanh()

        layer_list = []
        for i in range(self.depth):
            layer_list.append(nn.Linear(layers[i], layers[i + 1]))

        self.layers = nn.ModuleList(layer_list)

    def forward(self, x):
        for i in range(self.depth - 1):
            x = self.activation(self.layers[i](x))
        x = self.layers[-1](x)
        return x


class PinnService:
    def __init__(self, config_file="pinn_config.json", custom_params=None):
        self.config = load_pinn_config(config_file)

        self.tolerance = 1e-5
        self.patience = 500
        self.stop_requested = False

        if custom_params:
            if 'tolerance' in custom_params:
                try:
                    tol = float(custom_params['tolerance'])
                    if tol > 0:
                        self.tolerance = tol
                except (ValueError, TypeError):
                    logger.warning(f"Invalid tolerance value: {custom_params['tolerance']}, using default")

            if 'patience' in custom_params:
                try:
                    pat = int(custom_params['patience'])
                    if pat > 0:
                        self.patience = pat
                except (ValueError, TypeError):
                    logger.warning(f"Invalid patience value: {custom_params['patience']}, using default")

        self.model = PINN(
            self.config["architecture"]["layers"],
            self.config["architecture"]["activation"]
        ).to(device)

        self.optimizer = torch.optim.Adam(
            self.model.parameters(),
            lr=self.config["training"]["learning_rate"]
        )

        self.lbfgs_optimizer = LBFGS(
            self.model.parameters(),
            lr=0.1,
            max_iter=20,
            max_eval=25,
            tolerance_grad=1e-7,
            tolerance_change=1e-9,
            line_search_fn="strong_wolfe"
        )

    def request_stop(self):
        self.stop_requested = True

    def physics_loss(self, t, physics_function):
        import inspect

        t.requires_grad_(True)
        y = self.model(t)

        sig = inspect.signature(physics_function)
        num_params = len(sig.parameters)
        order = num_params - 2

        derivatives = [y]
        current_deriv = y

        for i in range(1, order + 1):
            current_deriv = torch.autograd.grad(
                current_deriv, t,
                grad_outputs=torch.ones_like(current_deriv),
                create_graph=True,
                retain_graph=True
            )[0]
            derivatives.append(current_deriv)

        residual = physics_function(t, *derivatives)
        return torch.mean(residual ** 2)

    def cauchy_loss(self, conditions):
        """
        Calculates loss for Initial Value Problems.
        Expects a list of dicts: [{'t': t0, 'val': y0}, {'t': t0, 'val': y'0}, ...]
        """
        t_val = float(conditions[0]['t'])
        t0 = torch.tensor([[t_val]], device=device, requires_grad=True)
        y_pred = self.model(t0)

        loss_cauchy = 0.0
        current_deriv = y_pred

        for i, cond in enumerate(conditions):
            target_val = float(cond['val'])
            target_tensor = torch.tensor([[target_val]], device=device)

            if i == 0:
                loss_cauchy += torch.mean((current_deriv - target_tensor) ** 2)
            else:
                current_deriv = torch.autograd.grad(
                    current_deriv, t0,
                    grad_outputs=torch.ones_like(current_deriv),
                    create_graph=True,
                    retain_graph=True
                )[0]
                loss_cauchy += torch.mean((current_deriv - target_tensor) ** 2)

        return loss_cauchy

    def bvp_loss(self, conditions):
        loss_bvp = 0.0
        for cond in conditions:
            t_val = float(cond['t'])
            target_val = float(cond['val'])
            order = int(cond.get('order', 0))

            t_tensor = torch.tensor([[t_val]], device=device, requires_grad=True)
            current_pred = self.model(t_tensor)

            for _ in range(order):
                current_pred = torch.autograd.grad(
                    current_pred, t_tensor,
                    grad_outputs=torch.ones_like(current_pred),
                    create_graph=True,
                    retain_graph=True
                )[0]

            target_tensor = torch.tensor([[target_val]], device=device)
            loss_bvp += torch.mean((current_pred - target_tensor) ** 2)
        return loss_bvp / len(conditions) if conditions else torch.tensor(0.0, device=device)


    def train_model_stream(self, physics_function, conditions, problem_type="ivp", t_max_override=None, callback=None):
        adam_epochs = self.config["training"].get("adam_epochs", 4000)
        lbfgs_epochs = self.config["training"].get("lbfgs_epochs", 1000)
        adam_iter = range(adam_epochs) if adam_epochs is not None else count()
        adam_total_label = adam_epochs if adam_epochs is not None else "unbounded"
        lambda_phys = self.config["loss_weights"]["physics"]
        lambda_bound = self.config["loss_weights"]["boundary"]

        if problem_type == "ivp" and conditions:
            t_min = float(conditions[0]['t'])
        elif problem_type == "bvp" and len(conditions) >= 2:
            t_min = min(float(c['t']) for c in conditions)
        else:
            t_min = self.config["domain"]["t_min"]
        t_max = t_max_override if t_max_override is not None else self.config["domain"]["t_max"]
        n_points = self.config["domain"]["training_points"]

        self.model.train()

        best_loss = float('inf')
        epochs_no_improve = 0
        converged = False
        stop_reason = None
        last_epoch = 0

        logger.info(
            f"Phase 1: Adam optimization (max {adam_total_label} epochs, "
            f"tolerance={self.tolerance:.1e}, patience={self.patience})"
        )
        for epoch in adam_iter:
            if self.stop_requested:
                logger.info(f"Manual stop requested during Adam phase at epoch {epoch}")
                break
            last_epoch = epoch
            self.optimizer.zero_grad()

            t_physics = torch.rand((n_points, 1), device=device) * (t_max - t_min) + t_min
            loss_physics = self.physics_loss(t_physics, physics_function)

            if problem_type == "ivp":
                loss_conditions = self.cauchy_loss(conditions)
            elif problem_type == "bvp":
                loss_conditions = self.bvp_loss(conditions)

            total_loss = lambda_phys * loss_physics + lambda_bound * loss_conditions
            self._ensure_finite_loss(total_loss, "Adam optimization", epoch)
            total_loss.backward()
            self.optimizer.step()

            current_loss = total_loss.item()

            if current_loss < best_loss - 1e-12:
                best_loss = current_loss
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1

            is_last_adam = adam_epochs is not None and epoch == adam_epochs - 1
            if callback and (epoch % 50 == 0 or is_last_adam):
                function_data = self.get_function_data(t_min, t_max, points=50)
                yield callback(epoch, loss_physics.item(), loss_conditions.item(), current_loss, function_data)

            if epoch % 500 == 0:
                logger.info(f"Adam Epoch {epoch}: Loss {current_loss:.6e} (Phys: {loss_physics.item():.6e}, Bound: {loss_conditions.item():.6e})")

            if current_loss <= self.tolerance:
                converged = True
                stop_reason = f"tolerance {self.tolerance:.1e} reached at Adam epoch {epoch}"
                logger.info(stop_reason)
                break

            if epochs_no_improve >= self.patience:
                stop_reason = f"no improvement for {self.patience} epochs (Adam epoch {epoch}, best loss {best_loss:.6e})"
                logger.info(f"Early stopping: {stop_reason}")
                if callback:
                    function_data = self.get_function_data(t_min, t_max, points=50)
                    yield callback(epoch, loss_physics.item(), loss_conditions.item(), current_loss, function_data)
                break

        if converged:
            logger.info(f"Skipping L-BFGS phase - already converged")
            if callback:
                function_data = self.get_function_data(t_min, t_max, points=50)
                yield callback(last_epoch, loss_physics.item(), loss_conditions.item(), best_loss, function_data)
            return self.get_function_data(t_min, t_max)

        lbfgs_start = last_epoch + 1
        if lbfgs_epochs is not None:
            lbfgs_iter = range(lbfgs_start, lbfgs_start + lbfgs_epochs)
            lbfgs_total_label = lbfgs_epochs
        else:
            lbfgs_iter = count(lbfgs_start)
            lbfgs_total_label = "unbounded"
        logger.info(f"Phase 2: L-BFGS optimization (max {lbfgs_total_label} epochs)")

        epochs_no_improve = 0

        current_lbfgs_epoch = lbfgs_start
        lbfgs_t_physics = None

        def closure():
            if self.stop_requested:
                raise StopIteration()
            self.lbfgs_optimizer.zero_grad()
            loss_physics = self.physics_loss(lbfgs_t_physics, physics_function)

            if problem_type == "ivp":
                loss_conditions = self.cauchy_loss(conditions)
            elif problem_type == "bvp":
                loss_conditions = self.bvp_loss(conditions)

            total_loss = lambda_phys * loss_physics + lambda_bound * loss_conditions
            self._ensure_finite_loss(total_loss, "L-BFGS optimization", current_lbfgs_epoch)
            total_loss.backward()
            return total_loss

        def get_current_losses(t_physics):
            loss_physics = self.physics_loss(t_physics, physics_function)

            if problem_type == "ivp":
                loss_conditions = self.cauchy_loss(conditions)
            elif problem_type == "bvp":
                loss_conditions = self.bvp_loss(conditions)

            total_loss = lambda_phys * loss_physics + lambda_bound * loss_conditions
            self._ensure_finite_loss(total_loss, "L-BFGS evaluation", current_lbfgs_epoch)
            return loss_physics, loss_conditions, total_loss

        for epoch in lbfgs_iter:
            if self.stop_requested:
                logger.info(f"Manual stop requested during L-BFGS phase at epoch {epoch}")
                break
            current_lbfgs_epoch = epoch
            lbfgs_t_physics = torch.rand((n_points, 1), device=device) * (t_max - t_min) + t_min
            try:
                loss = self.lbfgs_optimizer.step(closure)
            except StopIteration:
                logger.info(f"Manual stop requested during L-BFGS closure at epoch {epoch}")
                break
            self._ensure_finite_loss(loss, "L-BFGS step", epoch)

            current_loss = loss.item()

            if current_loss < best_loss - 1e-12:
                best_loss = current_loss
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1

            is_last_lbfgs = lbfgs_epochs is not None and epoch == lbfgs_start + lbfgs_epochs - 1
            if callback and (epoch % 100 == 0 or is_last_lbfgs):
                function_data = self.get_function_data(t_min, t_max, points=50)
                loss_physics, loss_conditions, total_loss = get_current_losses(lbfgs_t_physics)
                yield callback(epoch, loss_physics.item(), loss_conditions.item(), total_loss.item(), function_data)

            if epoch % 100 == 0:
                logger.info(f"L-BFGS Epoch {epoch}: Loss {current_loss:.6e}")

            if current_loss <= self.tolerance:
                logger.info(f"Tolerance {self.tolerance:.1e} reached at L-BFGS epoch {epoch}")
                if callback:
                    function_data = self.get_function_data(t_min, t_max, points=50)
                    loss_physics, loss_conditions, total_loss = get_current_losses(lbfgs_t_physics)
                    yield callback(epoch, loss_physics.item(), loss_conditions.item(), total_loss.item(), function_data)
                break

            if epochs_no_improve >= self.patience:
                logger.info(f"Early stopping at L-BFGS epoch {epoch}: no improvement for {self.patience} epochs (best loss {best_loss:.6e})")
                if callback:
                    function_data = self.get_function_data(t_min, t_max, points=50)
                    loss_physics, loss_conditions, total_loss = get_current_losses(lbfgs_t_physics)
                    yield callback(epoch, loss_physics.item(), loss_conditions.item(), total_loss.item(), function_data)
                break

        return self.get_function_data(t_min, t_max)

    def evaluate_at_point(self, t_value):
        """
        Evaluează modelul PINN antrenat la un singur punct t.
        Returnează valoarea y(t) prezisă de model.
        """
        self.model.eval()
        t_tensor = torch.tensor([[t_value]], dtype=torch.float32, device=device)
        with torch.no_grad():
            y_pred = self.model(t_tensor)
        return y_pred.cpu().item()

    def compute_final_losses(self, physics_function, conditions, problem_type, t_min, t_max, n_points=500):
        """
        Compute final physics and boundary losses after training.
        
        Returns:
            dict with physics_loss and boundary_loss
        """
        self.model.eval()
        t_physics = torch.linspace(t_min, t_max, n_points).view(-1, 1).to(device)
        t_physics.requires_grad_(True)
        
        loss_physics = self.physics_loss(t_physics, physics_function)
        
        if problem_type == "ivp":
            loss_conditions = self.cauchy_loss(conditions)
        elif problem_type == "bvp":
            loss_conditions = self.bvp_loss(conditions)
        else:
            loss_conditions = torch.tensor(0.0)
        
        return {
            "physics_residual": float(loss_physics.item()),
            "boundary_error": float(loss_conditions.item())
        }

    def compute_validation_metrics(self, t_points, y_pinn, y_reference):
        """
        Compute L2 and Linf errors between PINN and reference solution.
        
        Args:
            t_points: numpy array of t values
            y_pinn: numpy array of PINN predictions
            y_reference: numpy array of reference solution values
            
        Returns:
            dict with l2_error, l2_relative, linf_error, accuracy_percent
        """
        import numpy as np
        
        abs_error = np.abs(y_pinn - y_reference)
        
        l2_error = np.sqrt(np.mean((y_pinn - y_reference) ** 2))
        
        y_ref_norm = np.sqrt(np.mean(y_reference ** 2))
        l2_relative = l2_error / (y_ref_norm + 1e-10)
        
        linf_error = np.max(abs_error)
        
        accuracy_percent = max(0.0, min(100.0, (1 - l2_relative) * 100))
        
        return {
            "l2_error": float(l2_error),
            "l2_relative": float(l2_relative),
            "linf_error": float(linf_error),
            "accuracy_percent": float(accuracy_percent)
        }

    def get_function_data(self, t_min, t_max, points=200):
        """
        Generează date complete pentru graficul funcției aproximate de PINN.
        Returnează x, y.
        """
        self.model.eval()
        t_eval = torch.linspace(t_min, t_max, points).view(-1, 1).to(device)
        with torch.no_grad():
            y_eval = self.model(t_eval)

        t_numpy = t_eval.cpu().numpy().flatten()
        y_numpy = y_eval.cpu().numpy().flatten()

        return {
            "function_data": {
                "x": t_numpy.tolist(),
                "y": y_numpy.tolist()
            },
            "metadata": {
                "domain": [t_min, t_max],
                "points": points,
                "model_info": {
                    "layers": self.config["architecture"]["layers"],
                    "activation": self.config["architecture"]["activation"]
                }
            }
        }
    def _ensure_finite_loss(self, loss, phase, epoch):
        if not torch.isfinite(loss):
            raise ValueError(f"Non-finite loss encountered during {phase} at epoch {epoch}: {loss.item()}")
