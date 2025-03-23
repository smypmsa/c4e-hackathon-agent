from uagents import Agent, Context
from uagents.setup import fund_agent_if_low

from src.models.decision_models import DecisionInput, DecisionOutput
from src.decisions.trading import load_grid_prices, decide_energy_distribution, calculate_cost

import os
from dotenv import load_dotenv

load_dotenv()


manager = Agent(
    name="Alice",
    seed=os.getenv('SEED'),
    port=8000,
    endpoint=["http://127.0.0.1:8000"]
)


@manager.on_rest_post("/decision_test", request=DecisionInput, response=DecisionOutput)
async def handle_decision_test(ctx: Context, msg: DecisionInput) -> DecisionOutput:
    ctx.logger.info(f"Received input data: {msg}")

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

@manager.on_rest_post("/decision", request=DecisionInput, response=DecisionOutput)
async def handle_decision(ctx: Context, msg: DecisionInput) -> DecisionOutput:
    """
    Handler for energy distribution decisions
    
    Args:
        ctx: Agent context
        msg: Input data containing energy production, consumption, etc.
        
    Returns:
        DecisionOutput: Decision on how to distribute energy
    """
    #ctx.logger.info(f"Received input data: {msg}")

    try:
        # Calculate total capacity and total current level from all storages
        total_capacity = sum(storage['capacity'] for storage in msg.storage_levels.values())
        total_current_level = sum(storage['current_level'] for storage in msg.storage_levels.values())
        
        # Log the totals for debugging
        ctx.logger.info(f"Total Storage Capacity: {total_capacity} kWh")
        ctx.logger.info(f"Total Current Storage Level: {total_current_level} kWh")
        ctx.logger.info(f"Grid sale price: {msg.grid_sale_price} kWh")
        ctx.logger.info(f"Grid buy price: {msg.grid_sale_price} kWh")
        ctx.logger.info(f"P2P price: {msg.p2p_base_price} kWh")
        
        # Load grid prices
        grid_prices = load_grid_prices()
        
        # Make comprehensive energy distribution decision
        energy_to_storage, sell_to_grid, buy_from_grid, take_from_storage = decide_energy_distribution(
            production=msg.production,
            consumption=msg.consumption,
            current_storage=total_current_level,
            max_storage=total_capacity,
            grid_prices=grid_prices,
            hour=msg.hour,
            p2p_price=msg.p2p_base_price,
            look_ahead_hours=12
        )
        
        # Calculate the cost/profit of the decision
        cost = calculate_cost(
            buy_from_grid=buy_from_grid,
            sell_to_grid=sell_to_grid,
            sell_to_p2p=energy_to_storage, # put to storage
            take_from_storage=take_from_storage,
            grid_prices=grid_prices,
            hour=msg.hour,
            p2p_price=msg.p2p_base_price
        )
        
        # Log the decision details
        ctx.logger.info(
            f"Decision made: "
            f"Store: {energy_to_storage:.2f} kWh, "
            f"Sell Grid: {sell_to_grid:.2f} kWh, "
            f"Buy Grid: {buy_from_grid:.2f} kWh, "
            f"Use Storage: {take_from_storage:.2f} kWh, "
            f"Net Cost: {cost:.2f}"
        )
        
        # Return the decision
        return DecisionOutput(
            energy_added_to_storage=energy_to_storage,
            energy_sold_to_grid=sell_to_grid,
            energy_bought_from_grid=buy_from_grid,
            energy_bought_from_storages=take_from_storage
        )
        
    except Exception as e:
        # Log the error
        ctx.logger.error(f"Error making energy decision: {str(e)}")
        
        # Return a safe fallback decision
        fallback_value = 0.0
        return DecisionOutput(
            energy_added_to_storage=fallback_value,
            energy_sold_to_grid=fallback_value,
            energy_bought_from_grid=msg.consumption,  # Fallback to buying all needed energy
            energy_bought_from_storages=fallback_value
        )
    

if __name__ == "__main__":
    fund_agent_if_low(manager.wallet.address())
    manager.run()
