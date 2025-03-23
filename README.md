# Smart Energy Management System

## Overview

A smart energy management system built with uAgents that optimizes energy distribution based on grid prices, storage capacity, and consumption patterns to help users save money.

## Features

- Real-time decision making based on current and forecasted prices
- Smart storage management (store when cheap, use when expensive)
- Grid integration for buying and selling at optimal times

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