from uagents import Model


class DecisionInput(Model):
    hour: int
    production: float
    consumption: float
    storage_levels: dict  # {storage_name: current_level}
    grid_purchase_price: float
    grid_sale_price: float
    p2p_base_price: float
    token_balance: float
    
    def __str__(self):
        storage_str = '\n    '.join([f"{name}: {level}" for name, level in self.storage_levels.items()])
        return (f"DecisionInput:\n"
                f"  Hour: {self.hour}"
                f"  Production: {self.production} kWh\n"
                f"  Consumption: {self.consumption} kWh\n"
                f"  Storage Levels:\n    {storage_str}\n"
                f"  Grid Purchase Price: {self.grid_purchase_price}\n"
                f"  Grid Sale Price: {self.grid_sale_price}\n"
                f"  P2P Base Price: {self.p2p_base_price}\n"
                f"  Token Balance: {self.token_balance}")
    
    def __repr__(self):
        return self.__str__()


class DecisionOutput(Model):
    energy_added_to_storage: float
    energy_sold_to_grid: float
    energy_bought_from_storages: float
    energy_bought_from_grid: float
    
    def __str__(self):
        return (f"DecisionOutput:\n"
                f"  Energy Added to Storage: {self.energy_added_to_storage} kWh\n"
                f"  Energy Sold to Grid: {self.energy_sold_to_grid} kWh\n"
                f"  Energy Bought from Storages: {self.energy_bought_from_storages} kWh\n"
                f"  Energy Bought from Grid: {self.energy_bought_from_grid} kWh")
    
    def __repr__(self):
        return self.__str__()