import json
import os

import torch
import torch.nn as nn
from torch.optim import LBFGS

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


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
            print(f"Warning: Config not found at {config_path}. Using defaults.")
            self.config = {
                "architecture": {"layers": [1, 20, 20, 20, 1], "activation": "tanh"},
                "training": {"epochs": 5000, "adam_epochs": 4000, "learning_rate": 0.001},
                "loss_weights": {"physics": 1.0, "boundary": 100.0},
                "domain": {"t_min": 0.0, "t_max": 10.0, "training_points": 200}
            }

        if custom_params:
            if 'learning_rate' in custom_params:
                self.config["training"]["learning_rate"] = custom_params['learning_rate']

            if 'hidden_layers' in custom_params and 'neurons_per_layer' in custom_params:
                num_hidden = custom_params['hidden_layers']
                neurons = custom_params['neurons_per_layer']
                self.config["architecture"]["layers"] = [1] + [neurons] * num_hidden + [1]

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
        """Placeholder for Boundary Value Problems"""
        loss_bvp = 0.0
        # Will be implemented when you build the BVP frontend
        return loss_bvp

    def train_model(self, physics_function, conditions, problem_type="ivp", t_max_override=None):
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

        print(f"Phase 1: Adam optimization for {adam_epochs} epochs")
        for epoch in range(adam_epochs):
            self.optimizer.zero_grad()

            t_physics = torch.rand((n_points, 1), device=device) * (t_max - t_min) + t_min
            loss_physics = self.physics_loss(t_physics, physics_function)

            if problem_type == "ivp":
                loss_conditions = self.cauchy_loss(conditions)
            elif problem_type == "bvp":
                loss_conditions = self.bvp_loss(conditions)
            else:
                loss_conditions = self.cauchy_loss(conditions)

            total_loss = lambda_phys * loss_physics + lambda_bound * loss_conditions

            total_loss.backward()
            self.optimizer.step()

            if epoch % 500 == 0:
                print(f"Adam Epoch {epoch}: Loss {total_loss.item():.5f} (Phys: {loss_physics.item():.5f}, Bound: {loss_conditions.item():.5f})")

        print(f"Phase 2: L-BFGS optimization for {epochs - adam_epochs} epochs")

        def closure():
            self.lbfgs_optimizer.zero_grad()
            t_physics = torch.rand((n_points, 1), device=device) * (t_max - t_min) + t_min
            loss_physics = self.physics_loss(t_physics, physics_function)

            if problem_type == "ivp":
                loss_conditions = self.cauchy_loss(conditions)
            elif problem_type == "bvp":
                loss_conditions = self.bvp_loss(conditions)
            else:
                loss_conditions = self.cauchy_loss(conditions)

            total_loss = lambda_phys * loss_physics + lambda_bound * loss_conditions
            total_loss.backward()
            return total_loss

        for epoch in range(adam_epochs, epochs):
            loss = self.lbfgs_optimizer.step(closure)
            if epoch % 100 == 0:
                print(f"L-BFGS Epoch {epoch}: Loss {loss.item():.5f}")

        return self.get_function_data(t_min, t_max)

    def train_model_stream(self, physics_function, conditions, problem_type="ivp", t_max_override=None, callback=None):
        epochs = self.config["training"]["epochs"]
        lambda_phys = self.config["loss_weights"]["physics"]
        lambda_bound = self.config["loss_weights"]["boundary"]

        # For IVP: use initial condition time as t_min, for BVP: extract min/max from conditions
        if problem_type == "ivp" and conditions:
            t_min = float(conditions[0]['t'])
        elif problem_type == "bvp" and len(conditions) >= 2:
            t_min = min(float(c['t']) for c in conditions)
        else:
            t_min = self.config["domain"]["t_min"]
        t_max = t_max_override if t_max_override is not None else self.config["domain"]["t_max"]
        n_points = self.config["domain"]["training_points"]

        self.model.train()

        for epoch in range(epochs):
            self.optimizer.zero_grad()

            t_physics = torch.rand((n_points, 1), device=device) * (t_max - t_min) + t_min
            loss_physics = self.physics_loss(t_physics, physics_function)

            if problem_type == "ivp":
                loss_conditions = self.cauchy_loss(conditions)
            elif problem_type == "bvp":
                loss_conditions = self.bvp_loss(conditions)
            else:
                loss_conditions = self.cauchy_loss(conditions)

            total_loss = lambda_phys * loss_physics + lambda_bound * loss_conditions
            total_loss.backward()
            self.optimizer.step()

            if callback and (epoch % 50 == 0 or epoch == epochs - 1):
                function_data = self.get_function_data(t_min, t_max, points=50)
                yield callback(epoch, loss_physics.item(), loss_conditions.item(), total_loss.item(), function_data)

            if epoch % 500 == 0:
                print(f"Epoch {epoch}: Loss {total_loss.item():.5f} (Phys: {loss_physics.item():.5f}, Bound: {loss_conditions.item():.5f})")

        return self.get_function_data(t_min, t_max)

    def predict_solution(self, t_min, t_max, points=100):
        self.model.eval()
        t_eval = torch.linspace(t_min, t_max, points).view(-1, 1).to(device)
        with torch.no_grad():
            y_eval = self.model(t_eval)

        return {
            "x": t_eval.cpu().numpy().flatten().tolist(),
            "y": y_eval.cpu().numpy().flatten().tolist()
        }

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
        Returnează x, y, și informații despre convergență.
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

    def get_derivatives_data(self, t_min, t_max, points=200):
        """
        Generează date pentru derivatele funcției (y' și y'').
        Util pentru a vizualiza cum învață PINN derivatele.
        """
        self.model.eval()
        t_eval = torch.linspace(t_min, t_max, points).view(-1, 1).to(device)
        t_eval.requires_grad_(True)
        y_eval = self.model(t_eval)

        dy_dt = torch.autograd.grad(
            y_eval, t_eval,
            grad_outputs=torch.ones_like(y_eval),
            create_graph=True,
            retain_graph=True
        )[0]

        d2y_dt2 = torch.autograd.grad(
            dy_dt, t_eval,
            grad_outputs=torch.ones_like(dy_dt),
            create_graph=True,
            retain_graph=True
        )[0]

        t_numpy = t_eval.detach().cpu().numpy().flatten()
        y_numpy = y_eval.detach().cpu().numpy().flatten()
        dy_numpy = dy_dt.detach().cpu().numpy().flatten()
        d2y_numpy = d2y_dt2.detach().cpu().numpy().flatten()

        return {
            "derivatives": {
                "x": t_numpy.tolist(),
                "y": y_numpy.tolist(),
                "dy": dy_numpy.tolist(),
                "d2y": d2y_numpy.tolist()
            }
        }