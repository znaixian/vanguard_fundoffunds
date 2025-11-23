"""
Vanguard LifeStrategy Calculator
Implements multi-tier waterfall calculation logic with UCITS caps
"""

import pandas as pd
import numpy as np
from pathlib import Path
from .config import PORTFOLIO_CONFIGS, FIXED_INCOME_COMPONENTS, EQUITY_COMPONENTS, FIXED_WEIGHT_IDS


def calculate_all_portfolios(market_data: pd.DataFrame, returns_data: pd.DataFrame, date: str) -> pd.DataFrame:
    """
    Calculate weights for all portfolios (LSE20, LSE40, LSE60, LSE80).

    Args:
        market_data: DataFrame with columns ['symbol', 'MarketCapIndex']
        returns_data: DataFrame with columns ['symbol', 'Return']
        date: Calculation date (YYYYMMDD)

    Returns:
        Combined DataFrame with all portfolios' weights and returns
    """
    # Read base template
    base_df = pd.read_csv('vanguard_base_eu_lifestrategy.csv')

    # Process each portfolio
    df = None
    for portfolio_type in ['LSE20', 'LSE40', 'LSE60', 'LSE80']:
        portfolio_df = calculate_weights(portfolio_type, base_df.copy(), market_data)

        if df is None:
            df = portfolio_df
        else:
            # Update weights for this portfolio
            mask = portfolio_df['Benchmark ID'].str.contains(f'{portfolio_type}_', na=False)
            df.loc[mask, 'Weight'] = portfolio_df.loc[mask, 'Weight']

    # Add date column at the beginning
    df.insert(0, 'Date', date)

    # Merge returns data if available
    if not returns_data.empty:
        # Extract symbol from Benchmark ID for matching
        # Benchmark ID format: LSE80_LHMN34611 -> extract LHMN34611
        df['_temp_symbol'] = df['Benchmark ID'].str.extract(r'_(\w+)(?:\s+|$)')[0]

        # Merge with returns data
        df = df.merge(
            returns_data[['symbol', 'Return']],
            left_on='_temp_symbol',
            right_on='symbol',
            how='left',
            suffixes=('', '_from_returns')
        )

        # Clean up
        df = df.drop(columns=['_temp_symbol', 'symbol_from_returns'], errors='ignore')

        # Move Return column to appear after Weight column
        cols = df.columns.tolist()
        if 'Return' in cols and 'Weight' in cols:
            # Remove Return from its current position
            cols.remove('Return')
            # Find Weight position and insert Return after it
            weight_idx = cols.index('Weight')
            cols.insert(weight_idx + 1, 'Return')
            df = df[cols]

        print(f"Added Return column with {df['Return'].notna().sum()} values")
    else:
        # Add empty Return column if no returns data
        weight_idx = df.columns.tolist().index('Weight')
        df.insert(weight_idx + 1, 'Return', np.nan)
        print("Warning: No returns data available - Return column will be empty")

    return df


def calculate_weights(portfolio_type: str, base_df: pd.DataFrame, market_data: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate weights for a single portfolio.

    Args:
        portfolio_type: Portfolio name (e.g., 'LSE80')
        base_df: Base template DataFrame
        market_data: Market cap data

    Returns:
        DataFrame with calculated weights
    """
    if portfolio_type not in PORTFOLIO_CONFIGS:
        raise ValueError(f"Portfolio type must be one of {list(PORTFOLIO_CONFIGS.keys())}")

    config = PORTFOLIO_CONFIGS[portfolio_type]

    # Prepare dataframe
    df = base_df.copy()
    df['symbol'] = df['Benchmark ID'].str.extract(r'_(\w+)(?:\s+|$)')

    # Add dummy market cap for fixed weight components (they don't need real market cap)
    fixed_weight_df = pd.DataFrame({
        'symbol': FIXED_WEIGHT_IDS,
        'MarketCapIndex': [1.0] * len(FIXED_WEIGHT_IDS)  # Dummy value, not used
    })

    # Combine market data with fixed weight dummies
    combined_market_data = pd.concat([market_data, fixed_weight_df], ignore_index=True)

    df = df.merge(combined_market_data[['symbol', 'MarketCapIndex']], on='symbol', how='left')
    df['Weight'] = np.nan

    # Calculate weights
    calculate_fi_weights(df, portfolio_type, config)
    calculate_equity_weights(df, portfolio_type, config)

    return df


def calculate_fi_weights(df: pd.DataFrame, portfolio_type: str, config: dict):
    """
    Calculate fixed income weights using tier-based waterfall.

    Logic:
    - Tier 1 (LHMN34611): Fixed at 19.25%
    - Tier 3: Market cap weighted from remaining allocation
    - Overflow redistribution if any component capped at 19.25%

    Modifies df in place.
    """
    print(f"\nCalculating {portfolio_type} Fixed Income Weights:")

    fi_symbols = ['LHMN34611', 'LHMN21140', 'LHMN9913', 'LHMN21153', 'LHMN2004', 'LHMN2002']
    fi_mask = df['symbol'].isin(fi_symbols) & df['Benchmark ID'].str.contains(f'{portfolio_type}_', na=False)

    # Calculate total market cap for non-base weight FI assets
    fi_tier_3_total_mcap = df[fi_mask & (df['symbol'] != 'LHMN34611')]['MarketCapIndex'].sum()
    print(f"FI_TIER_3_TOTAL_MCAP: {fi_tier_3_total_mcap:,.9f}")

    # First pass: calculate weights without capping
    weights = {}
    total_weight = 0
    base_weight = config['base_weight']
    remaining_allocation = config['fixed_income_allocation'] - base_weight

    for idx in df[fi_mask].index:
        symbol = df.loc[idx, 'symbol']
        if symbol == 'LHMN34611':
            weights[symbol] = base_weight
            print(f"{symbol}: Fixed weight = {base_weight}")
        else:
            mcap = df.loc[idx, 'MarketCapIndex']
            ratio = mcap / fi_tier_3_total_mcap
            weights[symbol] = remaining_allocation * ratio
            print(f"{symbol} (uncapped): mcap={mcap:,.9f}, ratio={ratio:.9f}, weight={weights[symbol]:.9f}")

    # Check if any weights exceed base_weight and need capping
    total_capped = 0
    capped_weights = {}

    for symbol, weight in weights.items():
        if symbol != 'LHMN34611':  # Don't cap the base weight
            if weight > base_weight:
                total_capped += base_weight
                capped_weights[symbol] = base_weight
            else:
                total_capped += weight
                capped_weights[symbol] = weight

    # If we have capping, redistribute the excess weight
    if total_capped < (config['fixed_income_allocation'] - base_weight):
        excess = (config['fixed_income_allocation'] - base_weight) - total_capped
        # Distribute excess to non-capped assets proportionally
        non_capped = {k: v for k, v in weights.items()
                     if k != 'LHMN34611' and v < base_weight}
        if non_capped:
            total_non_capped = sum(non_capped.values())
            for symbol in non_capped:
                if total_non_capped > 0:
                    capped_weights[symbol] += excess * (non_capped[symbol] / total_non_capped)
                else:
                    capped_weights[symbol] = excess / len(non_capped)

    # Apply the final weights
    for idx in df[fi_mask].index:
        symbol = df.loc[idx, 'symbol']
        if symbol == 'LHMN34611':
            df.loc[idx, 'Weight'] = weights[symbol]
        else:
            df.loc[idx, 'Weight'] = min(capped_weights.get(symbol, 0), base_weight)
            print(f"{symbol}: final weight={df.loc[idx, 'Weight']:.9f}")


def calculate_equity_weights(df: pd.DataFrame, portfolio_type: str, config: dict):
    """
    Calculate equity weights using tier-based cascade.

    Logic:
    - Tier 1 (I00010): Fixed at 19.25%
    - Tier 2 (I01018, I01270): Market cap weighted from remaining
    - Tier 3: Market cap weighted from remaining after Tier 2
    - Tier 4 (SP50): Overflow only if Tier 3 North America capped

    Modifies df in place.
    """
    print(f"\nCalculating {portfolio_type} Equity Weights:")

    base_weight = config['base_weight']

    # Step 1: Fix I00010 weight
    i00010_mask = df['Benchmark ID'].str.contains(f'{portfolio_type}_I00010', na=False)
    df.loc[i00010_mask, 'Weight'] = base_weight
    print(f"{portfolio_type}_I00010: Fixed weight = {base_weight}")

    # Step 2: Calculate Tier 2 weights (I01018 and I01270)
    i01018_mcap = df.loc[df['Benchmark ID'].str.contains(f'{portfolio_type}_I01018', na=False), 'MarketCapIndex'].iloc[0]
    i01270_mcap = df.loc[df['Benchmark ID'].str.contains(f'{portfolio_type}_I01270', na=False), 'MarketCapIndex'].iloc[0]
    equity_tier_2_total_mcap = i01018_mcap + i01270_mcap
    print(f"EQUITY_TIER_2_TOTAL_MCAP: {equity_tier_2_total_mcap:,.9f}")

    # Calculate I01018 and I01270 weights
    for symbol, mcap in [('I01018', i01018_mcap), ('I01270', i01270_mcap)]:
        weight = min(base_weight,
                    (config['equity_allocation'] - base_weight) *
                    (mcap / equity_tier_2_total_mcap))
        df.loc[df['Benchmark ID'].str.contains(f'{portfolio_type}_{symbol}', na=False), 'Weight'] = weight
        print(f"{portfolio_type}_{symbol}: mcap={mcap:,.9f}, weight={weight:.9f}")
        if symbol == 'I01018':
            i01018_weight = weight
        else:
            i01270_weight = weight

    # Step 3: Calculate Tier 3 weights
    tier_3_symbols = ['I00586', 'I27049', 'I26152', '180948']
    tier_3_mcaps = {}
    equity_tier_3_total_mcap = 0

    for symbol in tier_3_symbols:
        mask = df['Benchmark ID'].str.contains(f'{portfolio_type}_{symbol}', na=False)
        if len(df[mask]) > 0:
            mcap = df.loc[mask, 'MarketCapIndex'].iloc[0]
            tier_3_mcaps[symbol] = mcap
            equity_tier_3_total_mcap += mcap

    print(f"\nEQUITY_TIER_3_TOTAL_MCAP: {equity_tier_3_total_mcap:,.9f}")

    remaining_weight = config['equity_allocation'] - (base_weight + i01018_weight + i01270_weight)
    print(f"Remaining weight for Tier 3: {remaining_weight:.9f}")

    if remaining_weight <= 0:
        print("No remaining weight for Tier 3, setting all to 0")
        for symbol in tier_3_symbols:
            df.loc[df['Benchmark ID'].str.contains(f'{portfolio_type}_{symbol}', na=False), 'Weight'] = 0
    else:
        for symbol in tier_3_symbols:
            mask = df['Benchmark ID'].str.contains(f'{portfolio_type}_{symbol}', na=False)
            if len(df[mask]) > 0:
                mcap = tier_3_mcaps[symbol]
                weight = min(base_weight,
                           remaining_weight * (mcap / equity_tier_3_total_mcap))
                df.loc[mask, 'Weight'] = weight
                print(f"{portfolio_type}_{symbol}: mcap={mcap:,.9f}, weight={weight:.9f}")

    # Step 4: Calculate SP50 weight
    i00586_weight = df.loc[df['Benchmark ID'].str.contains(f'{portfolio_type}_I00586', na=False), 'Weight'].iloc[0]
    print(f"\nI00586 weight for SP50 check: {i00586_weight:.9f}")

    if i00586_weight < base_weight:
        print(f"Setting SP50 weight to 0 as I00586 weight < {base_weight}")
        df.loc[df['Benchmark ID'].str.contains(f'{portfolio_type}_SP50', na=False), 'Weight'] = 0
    else:
        total_other_weights = (base_weight + i01018_weight + i01270_weight +
                             df.loc[df['Benchmark ID'].str.contains(f'{portfolio_type}_') &
                                   df['symbol'].isin(tier_3_symbols), 'Weight'].sum())
        sp50_weight = max(0, config['equity_allocation'] - total_other_weights)
        df.loc[df['Benchmark ID'].str.contains(f'{portfolio_type}_SP50', na=False), 'Weight'] = sp50_weight
        print(f"SP50: total_other_weights={total_other_weights:.9f}, sp50_weight={sp50_weight:.9f}")
