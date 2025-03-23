# Smart Energy Management System

## Overview

A smart energy management system built with uAgents that optimizes energy distribution based on grid prices, storage capacity, and consumption patterns to help users save money.

## Features

- Real-time decision making based on current and forecasted prices
- Smart storage management (store when cheap, use when expensive)
- Grid integration for buying and selling at optimal times
- Proactive buying energy from the grid at lower prices

## Getting Started

### Prerequisites

- Python 3.13+
- uAgents framework

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/smypmsa/c4e-hackathon-agent.git
   cd c4e-hackathon-agent
   ```

2. Set up environment:
   ```
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Create `.env` file:
   ```
   SEED=your_secret_seed_here
   ```

## Usage

Start the manager agent:
```
python -m src.agents.manager
```

## How It Works

The system analyzes:
- Energy production and consumption
- Storage levels
- Grid prices (current and future)
- P2P trading prices

It then decides whether to:
- Store excess energy
- Sell to grid
- Buy from grid
- Use stored energy

## Project Structure

```
hackathon-1/
├── grid_prices.csv - Hourly grid prices
├── src/
│   ├── agents/manager.py - Main agent
│   ├── decisions/trading.py - Decision algorithms
│   └── models/decision_models.py - Data models
```

# Logic Behind All This Mess

### Energy Surplus Handling (When producing more than consuming)
- Prioritizes storing energy when:
  - Price spikes are approaching
  - Battery isn't full
  - P2P trading prices aren't competitive
- Sells excess energy to the grid if storage is full or not prioritized

### Energy Deficit Handling (When consuming more than producing)
- Uses stored energy when:
  - Grid prices are currently high
  - No price spikes are expected soon
  - Battery is relatively full
- Buys energy from the grid when needed after using available storage

### Proactive Buying
- Special feature that buys extra energy when prices are low
- Stores this energy in anticipation of upcoming price spikes
- Only activates when:
  - Current prices are significantly below average
  - Price spikes are expected in the next 2-12 hours
  - There's enough storage space available

## How Decisions Are Made

1. **Energy Balance Calculation**:
   - System first calculates if there's surplus or deficit energy

2. **For Energy Surplus**:
   - Decides how much to store based on storage capacity and upcoming price events
   - Sells remaining energy to the grid if it can't be stored

3. **For Energy Deficit**:
   - Decides whether to use stored energy based on current prices and future outlook
   - Buys from grid to cover remaining needs

4. **Proactive Strategy**:
   - Calculates if buying extra energy now (at low prices) to store for later high-price periods makes sense
   - Factors in how soon price spikes will happen and how severe they'll be
