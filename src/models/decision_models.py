from uagents import Model

class DecisionInput(Model):
    production: float
    consumption: float
    storage_levels: dict  # {storage_name: current_level}
    grid_purchase_price: float
    grid_sale_price: float
    p2p_base_price: float
    token_balance: float

class DecisionOutput(Model):
    energy_added_to_storage: float
    energy_sold_to_grid: float
    energy_bought_from_storages: float
    energy_bought_from_grid: float
