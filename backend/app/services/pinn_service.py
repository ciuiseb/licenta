import json
import os
import logging

import torch
import torch.nn as nn
from torch.optim import LBFGS

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
        base_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(base_dir, '..', '..', 'configs', config_file)

        try:
            with open(config_path, 'r') as f:
                self.config = json.load(f)
        except FileNotFoundError:
            logger.warning(f"Config not found at {config_path}. Using defaults.")
            self.config = {
                "architecture": {"layers": [1, 20, 20, 20, 1], "activation": "tanh"},
                "training": {"epochs": 5000, "adam_epochs": 4000, "learning_rate": 0.001},
                "loss_weights": {"physics": 1.0, "boundary": 100.0},
                "domain": {"t_min": 0.0, "t_max": 10.0, "training_points": 200}
            }

        self.tolerance = 1e-5
        self.patience = 500

        if custom_params:
            if 'learning_rate' in custom_params:
                self.config["training"]["learning_rate"] = custom_params['learning_rate']

            if 'hidden_layers' in custom_params and 'neurons_per_layer' in custom_params:
                num_hidden = custom_params['hidden_layers']
                neurons = custom_params['neurons_per_layer']
                self.config["architecture"]["layers"] = [1] + [neurons] * num_hidden + [1]

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
        epochs = self.config["training"]["epochs"]
        adam_epochs = self.config["training"].get("adam_epochs", 4000)
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
            f"Phase 1: Adam optimization (max {adam_epochs} epochs, "
            f"tolerance={self.tolerance:.1e}, patience={self.patience})"
        )
        for epoch in range(adam_epochs):
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

            if callback and (epoch % 50 == 0 or epoch == adam_epochs - 1):
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
                break

        if converged:
            logger.info(f"Skipping L-BFGS phase - already converged")
            if callback:
                function_data = self.get_function_data(t_min, t_max, points=50)
                yield callback(last_epoch, loss_physics.item(), loss_conditions.item(), best_loss, function_data)
            return self.get_function_data(t_min, t_max)

        logger.info(f"Phase 2: L-BFGS optimization (max {epochs - adam_epochs} epochs)")

        current_lbfgs_epoch = adam_epochs
        lbfgs_t_physics = None

        def closure():
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

        for epoch in range(adam_epochs, epochs):
            current_lbfgs_epoch = epoch
            lbfgs_t_physics = torch.rand((n_points, 1), device=device) * (t_max - t_min) + t_min
            loss = self.lbfgs_optimizer.step(closure)
            self._ensure_finite_loss(loss, "L-BFGS step", epoch)

            current_loss = loss.item()

            if current_loss < best_loss - 1e-12:
                best_loss = current_loss
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1

            if callback and (epoch % 100 == 0 or epoch == epochs - 1):
                function_data = self.get_function_data(t_min, t_max, points=50)
                loss_physics, loss_conditions, total_loss = get_current_losses(lbfgs_t_physics)
                yield callback(epoch, loss_physics.item(), loss_conditions.item(), total_loss.item(), function_data)

            if epoch % 100 == 0:
                logger.info(f"L-BFGS Epoch {epoch}: Loss {current_loss:.6e}")

            if current_loss <= self.tolerance:
                logger.info(f"Tolerance {self.tolerance:.1e} reached at L-BFGS epoch {epoch}")
                break

            if epochs_no_improve >= self.patience:
                logger.info(f"Early stopping at L-BFGS epoch {epoch}: no improvement for {self.patience} epochs (best loss {best_loss:.6e})")
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
