import pandas as pd
from typing import Tuple, Dict
import logging
import numpy as np


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
    look_ahead_hours: int = 24,  # Extended to look at full day
    enable_proactive_buying: bool = True  # New parameter to enable/disable proactive buying
) -> Tuple[float, float, float, float]:
    """
    Make a comprehensive decision about energy distribution with P2P price considerations
    and price spike awareness.
    
    Args:
        production: Energy produced in the current hour (kWh)
        consumption: Energy consumed in the current hour (kWh)
        current_storage: Current energy in storage (kWh)
        max_storage: Maximum storage capacity (kWh)
        grid_prices: DataFrame containing grid prices
        hour: Current hour (0-23)
        p2p_price: Current peer-to-peer trading price
        look_ahead_hours: Number of hours to look ahead for price forecasting
        enable_proactive_buying: Flag to enable proactive buying before price spikes
        
    Returns:
        Tuple of:
        - energy_to_storage: Energy to add to storage (kWh)
        - sell_to_grid: Energy to sell to grid (kWh)
        - buy_from_grid: Energy to buy from grid (kWh)
        - take_from_storage: Energy to take from storage (kWh)
    """
    
    # Get current hour prices
    current_prices = get_grid_prices_for_hour(grid_prices, hour)
    grid_purchase_price = current_prices["purchase"]
    grid_sale_price = current_prices["sale"]
    
    # Get all 24 hours of price data for better analysis
    all_hours = list(range(24))
    all_prices = [get_grid_prices_for_hour(grid_prices, h) for h in all_hours]
    all_purchase_prices = [p["purchase"] for p in all_prices]
    all_sale_prices = [p["sale"] for p in all_prices]
    
    # Calculate price statistics
    mean_purchase_price = np.mean(all_purchase_prices)
    std_purchase_price = np.std(all_purchase_prices)
    mean_sale_price = np.mean(all_sale_prices)
    
    # Define price spike thresholds (purchase price > mean + 1 std dev)
    purchase_spike_threshold = mean_purchase_price + std_purchase_price
    
    # Look ahead to detect upcoming price spikes
    upcoming_hours = [(hour + i) % 24 for i in range(1, look_ahead_hours + 1)]
    upcoming_prices = [get_grid_prices_for_hour(grid_prices, h) for h in upcoming_hours]
    
    # Identify upcoming price spikes within the look-ahead window
    upcoming_spikes = []
    for i, price_data in enumerate(upcoming_prices):
        if price_data["purchase"] > purchase_spike_threshold:
            upcoming_spikes.append({
                "hour": upcoming_hours[i],
                "price": price_data["purchase"],
                "hours_away": i + 1
            })
    
    # Calculate hours until the next price spike
    hours_to_next_spike = float('inf')
    if upcoming_spikes:
        hours_to_next_spike = upcoming_spikes[0]["hours_away"]
    
    # Calculate optimal sell hours (when grid sale price is high)
    high_sale_price_threshold = np.percentile(all_sale_prices, 75)
    upcoming_good_sell_hours = [
        h for i, h in enumerate(upcoming_hours) 
        if all_prices[h]["sale"] > high_sale_price_threshold
    ]
    
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
        storage_capacity_left = max_storage - current_storage
        
        # Calculate storage urgency factor based on proximity to next price spike
        # Higher urgency means we prioritize storage more
        if hours_to_next_spike < float('inf'):
            # Exponential decay function: urgency increases as we get closer to spike
            storage_urgency = np.exp(-0.1 * hours_to_next_spike) 
        else:
            storage_urgency = 0.1  # Base storage urgency when no spikes detected
        
        # Storage capacity target increases as we approach a price spike
        target_storage_percentage = min(0.9, 0.5 + storage_urgency)
        target_storage_level = max_storage * target_storage_percentage
        
        # Determine if we should prioritize storage
        storage_deficit = max(0, target_storage_level - current_storage)
        is_p2p_price_competitive = p2p_price < grid_sale_price * 0.9  # 10% tolerance
        
        should_prioritize_storage = (
            (storage_deficit > 0 and hours_to_next_spike < 12) or  # Spike approaching
            is_p2p_price_competitive or                            # P2P price is good
            (len(upcoming_good_sell_hours) > 0 and storage_deficit > 0)  # Good sell opportunity coming
        )
        
        if should_prioritize_storage and storage_capacity_left > 0:
            # Store energy - based on urgency and available capacity
            energy_to_storage = min(available_surplus, storage_capacity_left)
            available_surplus -= energy_to_storage
        
        # Sell remaining surplus to grid
        if available_surplus > 0:
            sell_to_grid = available_surplus
    
    # Case 2: We have energy deficit
    else:
        energy_needed = -energy_balance  # Make positive for easier handling
        
        # Determine if current hour is a price spike
        is_current_price_spike = grid_purchase_price > purchase_spike_threshold
        
        # Determine if we should use storage based on current prices and upcoming spikes
        should_use_storage = (
            is_current_price_spike or                    # Current prices are high
            (hours_to_next_spike > 6) or                 # No spikes coming soon
            (current_storage > 0.8 * max_storage)        # Storage is relatively full
        )
        
        if should_use_storage and current_storage > 0:
            # If in a price spike, use more storage; otherwise, be conservative
            storage_usage_cap = current_storage if is_current_price_spike else current_storage * 0.5
            take_from_storage = min(storage_usage_cap, energy_needed)
            energy_needed -= take_from_storage
        
        # Buy remaining needs from grid
        if energy_needed > 0:
            # If prices are very low compared to average, consider buying extra for storage
            is_price_very_low = grid_purchase_price < mean_purchase_price * 0.8
            storage_space_available = max_storage - current_storage
            
            # Basic energy need
            buy_from_grid = energy_needed
            
            # If price is very low and we have upcoming spikes, buy extra for storage
            if is_price_very_low and hours_to_next_spike < 12 and storage_space_available > 0:
                # Calculate how much extra to buy based on price advantage
                price_advantage_ratio = (mean_purchase_price - grid_purchase_price) / mean_purchase_price
                extra_buy = min(storage_space_available, price_advantage_ratio * 10)  # Scale factor of 10 kWh
                
                # Add extra energy to storage
                energy_to_storage += extra_buy
                buy_from_grid += extra_buy
    
    # Apply proactive buying strategy if enabled
    if enable_proactive_buying:
        extra_grid_buy, extra_storage = calculate_proactive_buying(
            current_storage, 
            max_storage, 
            grid_purchase_price, 
            mean_purchase_price, 
            upcoming_spikes, 
            energy_to_storage
        )
        buy_from_grid += extra_grid_buy
        energy_to_storage += extra_storage
    
    # Ensure we don't have negative values (safety check)
    energy_to_storage = max(0, energy_to_storage)
    sell_to_grid = max(0, sell_to_grid)
    buy_from_grid = max(0, buy_from_grid)
    take_from_storage = max(0, take_from_storage)
    
    return energy_to_storage, sell_to_grid, buy_from_grid, take_from_storage

def calculate_proactive_buying(
    current_storage: float,
    max_storage: float,
    current_price: float,
    mean_price: float,
    upcoming_spikes: list,
    current_to_storage: float
) -> Tuple[float, float]:
    """
    Calculate proactive energy buying from grid before price spikes.
    This function implements a strategy to buy energy when prices are
    relatively low, in anticipation of upcoming price spikes.
    
    Args:
        current_storage: Current energy in storage (kWh)
        max_storage: Maximum storage capacity (kWh)
        current_price: Current grid purchase price
        mean_price: Mean purchase price over the forecast period
        upcoming_spikes: List of upcoming price spikes with hour, price, and hours_away
        current_to_storage: Energy already allocated to storage in main function
        
    Returns:
        Tuple of:
        - extra_grid_buy: Additional energy to buy from grid (kWh)
        - extra_to_storage: Additional energy to store (kWh)
    """
    # If there are no upcoming spikes, don't buy proactively
    if not upcoming_spikes:
        return 0.0, 0.0
    
    # Calculate available storage space (considering what's already being stored)
    available_storage = max_storage - current_storage - current_to_storage
    
    # If storage is already full or nearly full, don't buy more
    if available_storage < 1.0:  # Threshold of 1 kWh
        return 0.0, 0.0
    
    # Calculate price advantage: how much cheaper current price is vs mean
    price_advantage = mean_price - current_price
    price_advantage_ratio = price_advantage / mean_price
    
    # Only buy if there's a significant price advantage
    if price_advantage_ratio <= 0.05:  # At least 5% cheaper than mean
        return 0.0, 0.0
    
    # Get the first upcoming spike information
    next_spike = upcoming_spikes[0]
    hours_to_spike = next_spike["hours_away"]
    spike_price = next_spike["price"]
    
    # Calculate the price difference between spike and current price
    spike_to_current_ratio = spike_price / current_price
    
    # Calculate buying aggressiveness based on:
    # 1. How soon the spike will occur
    # 2. How severe the spike is compared to current price
    # 3. Current price advantage compared to mean
    
    # Time factor: more aggressive as spike approaches, but not too close
    # Optimal buying window is between 2-12 hours before spike
    if hours_to_spike < 2 or hours_to_spike > 12:
        time_factor = 0.3
    else:
        # Peaked at middle of window (around 7 hours before spike)
        time_factor = 1.0 - abs(hours_to_spike - 7) / 5
    
    # Price advantage factor: more aggressive with larger advantage
    price_factor = min(1.0, spike_to_current_ratio / 2)
    
    # Combine factors to determine buying aggressiveness (0-1 scale)
    buying_factor = time_factor * price_factor * price_advantage_ratio
    
    # Calculate base amount to buy - more aggressive as price advantage increases
    # and as spike approaches within optimal window
    base_amount = 5.0  # Base amount in kWh
    scaled_amount = base_amount * buying_factor * spike_to_current_ratio
    
    # Scale based on storage capacity
    capacity_factor = min(1.0, available_storage / 20.0)  # Scale up to 20 kWh
    
    # Calculate the final amount to buy
    extra_energy = min(scaled_amount * capacity_factor, available_storage)
    
    # Safety limit - cap at 50% of available storage in one go
    extra_energy = min(extra_energy, available_storage * 0.5)
    
    return extra_energy, extra_energy

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