import pandas as pd
from typing import Tuple, Dict, Any
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Load the grid prices from the CSV
def load_grid_prices() -> pd.DataFrame:
    try:
        return pd.read_csv('grid_prices.csv', index_col=0)
    except FileNotFoundError:
        logger.error("grid_prices.csv not found in the project root directory")
        raise FileNotFoundError("grid_prices.csv not found. Please ensure it exists in the project root.")
    except Exception as e:
        logger.error(f"Error loading grid prices: {str(e)}")
        raise

def parse_hour_range_from_int(hour: int) -> str:
    """Convert an hour integer (0-23) to the string format used in the grid_prices.csv"""
    hour = int(hour) % 24  # Ensure it's an int and handle overflow
    start = f"{hour:02d}:00"
    end_hour = (hour + 1) % 24
    end = f"{end_hour:02d}:00"
    return f"{start} - {end}"  # Format matches the CSV index

def get_grid_prices_for_hour(grid_prices: pd.DataFrame, hour: int) -> Dict[str, float]:
    """Get grid purchase and sale prices for a specific hour"""
    hour_range = parse_hour_range_from_int(hour)
    try:
        return {
            "purchase": grid_prices.loc[hour_range, 'Purchase'],
            "sale": grid_prices.loc[hour_range, 'Sale']
        }
    except KeyError:
        logger.error(f"Could not find price data for hour range: {hour_range}")
        # Return default fallback values
        return {"purchase": 0.5, "sale": 0.25}

def decide_energy_distribution(
    production: float,
    consumption: float,
    current_storage: float,
    max_storage: float,
    grid_prices: pd.DataFrame,
    hour: int,
    p2p_price: float,
    look_ahead_hours: int = 3
) -> Tuple[float, float, float, float, float]:
    """
    Make a comprehensive decision about energy distribution.
    
    Args:
        production: Energy produced in the current hour (kWh)
        consumption: Energy consumed in the current hour (kWh)
        current_storage: Current energy in storage (kWh)
        max_storage: Maximum storage capacity (kWh)
        grid_prices: DataFrame containing grid prices
        hour: Current hour (0-23)
        p2p_price: Current peer-to-peer trading price
        token_balance: Current token balance for P2P trading
        look_ahead_hours: Number of hours to look ahead for price forecasting
        
    Returns:
        Tuple of:
        - energy_to_storage: Energy to add to storage (kWh)
        - sell_to_p2p: Energy to sell to P2P network (kWh)
        - sell_to_grid: Energy to sell to grid (kWh)
        - buy_from_grid: Energy to buy from grid (kWh)
        - take_from_storage: Energy to take from storage (kWh)
    """
    # Get current hour prices
    current_prices = get_grid_prices_for_hour(grid_prices, hour)
    grid_purchase_price = current_prices["purchase"]
    grid_sale_price = current_prices["sale"]
    
    # Look ahead at future prices
    future_prices = []
    for i in range(1, look_ahead_hours + 1):
        future_hour = (hour + i) % 24
        future_price = get_grid_prices_for_hour(grid_prices, future_hour)
        future_prices.append({
            "hour": future_hour,
            "buy_price": future_price["purchase"],
            "sell_price": future_price["sale"]
        })
    
    # Find the best future buying and selling prices
    best_future_buy = min(future_prices, key=lambda x: x['buy_price'], default={"buy_price": grid_purchase_price})
    best_future_sell = max(future_prices, key=lambda x: x['sell_price'], default={"sell_price": grid_sale_price})
    
    # Calculate energy balance
    energy_balance = production - consumption  # Positive = surplus, Negative = deficit
    
    # Initialize all decision variables
    energy_to_storage = 0.0
    sell_to_grid = 0.0
    buy_from_grid = 0.0
    take_from_storage = 0.0
    
    # Case 1: We have energy surplus
    if energy_balance > 0:
        available_surplus = energy_balance
        
        # Should we store energy for future use?
        # Store if future buying prices are higher or if we expect higher P2P demand
        storage_capacity_left = max_storage - current_storage
        better_prices_coming = best_future_sell["sell_price"] > grid_sale_price
        
        if better_prices_coming and storage_capacity_left > 0:
            # Store energy for future high-price hours
            energy_to_storage = min(available_surplus, storage_capacity_left)
            available_surplus -= energy_to_storage
        
        # Sell to grid
        if available_surplus > 0:
            sell_to_grid = available_surplus
    
    # Case 2: We have energy deficit
    else:
        energy_needed = -energy_balance  # Make positive for easier handling
        
        # Should we take from storage or buy from grid?
        # Take from storage if current grid prices are high compared to future
        grid_prices_will_drop = best_future_buy["buy_price"] < grid_purchase_price
        
        if current_storage > 0 and not grid_prices_will_drop:
            # Use storage since grid prices won't get better soon
            take_from_storage = min(current_storage, energy_needed)
            energy_needed -= take_from_storage
        
        # Buy remaining needs from grid
        if energy_needed > 0:
            buy_from_grid = energy_needed
    
    # Ensure we don't have negative values (safety check)
    energy_to_storage = max(0, energy_to_storage)
    sell_to_grid = max(0, sell_to_grid)
    buy_from_grid = max(0, buy_from_grid)
    take_from_storage = max(0, take_from_storage)
    
    return energy_to_storage, sell_to_grid, buy_from_grid, take_from_storage

def calculate_cost(
    buy_from_grid: float,
    sell_to_grid: float,
    sell_to_p2p: float,
    take_from_storage: float,
    grid_prices: pd.DataFrame,
    hour: int,
    p2p_price: float
) -> float:
    """
    Calculate the net cost of energy decisions
    
    Returns:
        float: Net cost (positive) or profit (negative)
    """
    # Get prices for the current hour
    current_prices = get_grid_prices_for_hour(grid_prices, hour)
    buy_price = current_prices["purchase"]
    sell_price = current_prices["sale"]
    
    # Calculate costs and revenues
    grid_purchase_cost = buy_from_grid * buy_price
    grid_sale_revenue = sell_to_grid * sell_price
    p2p_sale_revenue = sell_to_p2p * p2p_price
    #storage_cost = take_from_storage * 0.01  # Nominal cost for using storage
    
    # Net cost (positive = cost, negative = profit)
    net_cost = grid_purchase_cost - grid_sale_revenue - p2p_sale_revenue
    
    return net_cost