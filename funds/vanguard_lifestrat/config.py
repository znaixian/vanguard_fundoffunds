"""
Vanguard LifeStrategy Configuration
Portfolio configurations and component definitions
"""

# Portfolio configurations
PORTFOLIO_CONFIGS = {
    'LSE20': {
        'equity_allocation': 20,
        'fixed_income_allocation': 80,
        'base_weight': 19.25,
    },
    'LSE40': {
        'equity_allocation': 40,
        'fixed_income_allocation': 60,
        'base_weight': 19.25,
    },
    'LSE60': {
        'equity_allocation': 60,
        'fixed_income_allocation': 40,
        'base_weight': 19.25,
    },
    'LSE80': {
        'equity_allocation': 80,
        'fixed_income_allocation': 20,
        'base_weight': 19.25,
    }
}

# Fixed Income Components
FIXED_INCOME_COMPONENTS = {
    'tier_1': ['LHMN34611'],  # Bloomberg Global Aggregate
    'tier_3': ['LHMN21140', 'LHMN9913', 'LHMN21153', 'LHMN2004', 'LHMN2002']
}

# Equity Components
EQUITY_COMPONENTS = {
    'tier_1': ['I00010'],  # FTSE All-World
    'tier_2': ['I01018', 'I01270'],  # FTSE Developed, FTSE EM
    'tier_3': ['I00586', 'I27049', 'I26152', '180948'],  # Regional
    'tier_4': ['SP50']  # S&P 500
}

# Components that need market cap data (exclude fixed weight components)
MARKET_CAP_REQUIRED_IDS = (
    FIXED_INCOME_COMPONENTS['tier_3'] +  # Tier 3 FI needs market cap
    EQUITY_COMPONENTS['tier_2'] +  # Tier 2 equity needs market cap
    EQUITY_COMPONENTS['tier_3'] +  # Tier 3 equity needs market cap
    EQUITY_COMPONENTS['tier_4']    # Tier 4 equity needs market cap
)

# Components with fixed weights (don't need market cap)
FIXED_WEIGHT_IDS = (
    FIXED_INCOME_COMPONENTS['tier_1'] +  # LHMN34611 has fixed 19.25%
    EQUITY_COMPONENTS['tier_1']           # I00010 has fixed 19.25%
)

# All component IDs for API fetching
# Note: For returns, we need ALL components including fixed weight ones
ALL_COMPONENT_IDS = MARKET_CAP_REQUIRED_IDS
ALL_COMPONENT_IDS_FOR_RETURNS = (
    FIXED_INCOME_COMPONENTS['tier_1'] +
    FIXED_INCOME_COMPONENTS['tier_3'] +
    EQUITY_COMPONENTS['tier_1'] +
    EQUITY_COMPONENTS['tier_2'] +
    EQUITY_COMPONENTS['tier_3'] +
    EQUITY_COMPONENTS['tier_4']
)
