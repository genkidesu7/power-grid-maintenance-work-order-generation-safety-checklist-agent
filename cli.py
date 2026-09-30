"""AGENTIC STAR Marketplace entrypoint — one-shot Pod process.

Referenced by agenticstar-deploy/Dockerfile's `CMD ["python", "cli.py"]`.
Compiles the agent, provisions its secrets, then hands off to
shared.bootstrap.marketplace_app for the Marketplace lifecycle (identity,
input, events, terminal delivery, exit).
"""

from pathlib import Path

from framework.utils.config_loader import load_agent_config
from shared.bootstrap.marketplace_app import run_agent_marketplace

from src.graph.graph import WorkOrderGenerationAgent

# Add config overrides here if needed, instead of editing config/config.yaml.
extend_config: dict[str, object] = {}

if __name__ == "__main__":
    run_agent_marketplace(
        WorkOrderGenerationAgent,
        agent_name="ENE-C2-034",
        namespace="ene",
        config={**load_agent_config(Path(__file__).resolve().parent), **extend_config},
    )
