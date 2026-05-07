import json
import os


class ConfigError(RuntimeError):
    """Raised when a config file is missing or malformed."""


PINN_CONFIG_SCHEMA = {
    "architecture": ["layers", "activation"],
    "training": ["adam_epochs", "learning_rate"],
    "loss_weights": ["physics", "boundary"],
    "domain": ["t_min", "t_max", "training_points"],
}


def validate_config(config, schema, source):
    """Verify that `config` contains every section/key declared in `schema`.

    Raises ConfigError listing every missing key, so the caller sees all
    problems at once instead of fixing them one-by-one.
    """
    if not isinstance(config, dict):
        raise ConfigError(f"{source}: top-level config must be a JSON object")

    missing = []
    for section, keys in schema.items():
        if section not in config:
            missing.append(section)
            continue
        if not isinstance(config[section], dict):
            raise ConfigError(f"{source}: section '{section}' must be an object")
        for key in keys:
            if key not in config[section]:
                missing.append(f"{section}.{key}")

    if missing:
        raise ConfigError(
            f"{source}: missing required key(s): {', '.join(missing)}"
        )


def load_pinn_config(config_file="pinn_config.json"):
    """Load and validate the PINN config from backend/configs/<config_file>."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.normpath(
        os.path.join(base_dir, '..', '..', 'configs', config_file)
    )

    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except FileNotFoundError as e:
        raise ConfigError(f"PINN config not found at {config_path}") from e
    except json.JSONDecodeError as e:
        raise ConfigError(
            f"PINN config at {config_path} is not valid JSON: {e}"
        ) from e

    validate_config(config, PINN_CONFIG_SCHEMA, source=config_path)
    return config
