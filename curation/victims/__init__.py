from .ecommerce import run_ecommerce_attack
from .dental import run_dental_attack
from .dev_assistant import run_dev_attack
from .agentdojo_victims import run_banking_attack, run_workspace_attack

__all__ = [
    "run_ecommerce_attack",
    "run_dental_attack",
    "run_dev_attack",
    "run_banking_attack",
    "run_workspace_attack",
]


VICTIM_REGISTRY = {
    "ecommerce": run_ecommerce_attack,
    "dental": run_dental_attack,
    "dev_assistant": run_dev_attack,
    "banking": run_banking_attack,
    "workspace": run_workspace_attack,
}
