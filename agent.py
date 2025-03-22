from uagents import Agent, Context
from uagents.setup import fund_agent_if_low

from src.models.decision_models import DecisionInput, DecisionOutput


alice = Agent(
    name="Alice",
    seed="khavaioghgjabougrvbosubvisgvgjfkf",
    port=8000,
    endpoint=["http://127.0.0.1:8000/submit"]
)


@alice.on_rest_post("/decision", decision_output=DecisionOutput)
async def handle_decision(ctx: Context, msg: DecisionInput) -> DecisionOutput:
    ctx.logger.info("Received input data via REST")

    energy_added_to_storage = max(0, msg.production - msg.consumption)
    energy_sold_to_grid = 100
    energy_bought_from_storages = 100
    energy_bought_from_grid = 100

    return DecisionOutput(
        energy_added_to_storage=energy_added_to_storage,
        energy_sold_to_grid=energy_sold_to_grid,
        energy_bought_from_storages=energy_bought_from_storages,
        energy_bought_from_grid=energy_bought_from_grid
    )


if __name__ == "__main__":
    fund_agent_if_low(alice.wallet.address())
    alice.run()
