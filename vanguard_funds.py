import pandas as pd
import numpy as np
import requests
import base64

# Configuration for all portfolios
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

# Fetch the market cap data for the funds using formula API
username = "FDS_DEMO_US-420289"
api_key = ''
with open('../config/api-key.txt') as f:
    api_key = f.read()
auth = bytes(f"{username.upper()}:{api_key}", "utf-8")
headers = {
    'Authorization': 'Basic %s' % str(base64.b64encode(auth).decode('ascii'))
}

idlist = ['180948', 'I00010', 'I00586', 'I01018', 'I01270', 'I26152', 'I27049', 'LHMN2002', 'LHMN2004', 'LHMN21140', 'LHMN21153', 'LHMN34611', 'LHMN9913', 'SP50']
ids_string = ','.join(idlist)
date = '20250821'
url = f'https://api.factset.com/formula-api/v1/time-series?ids={ids_string}&formulas=FG_MCAP_IDX({date},{date},,USD)&flatten=Y'
r = requests.get(url, headers=headers)

# After the API call, transform the response to match market_caps_df structure
market_caps_df = pd.DataFrame(r.json()['data'][:])
market_caps_df = market_caps_df.rename(columns={
    'requestId': 'symbol',
    f'FG_MCAP_IDX({date},{date},,USD)': 'MarketCapIndex'
})[['symbol', 'MarketCapIndex']]  # Keep only the needed columns in the right order

# Convert MarketCapIndex to float if it's not already
market_caps_df['MarketCapIndex'] = pd.to_numeric(market_caps_df['MarketCapIndex'], errors='coerce')

print("Processed DataFrame:")
print(market_caps_df)

# Define function to calculate weights
def calculate_weights(portfolio_type):
    """Calculate weights for a given portfolio type (LSE20, LSE40, LSE60 or LSE80)"""
    if portfolio_type not in PORTFOLIO_CONFIGS:
        raise ValueError(f"Portfolio type must be one of {list(PORTFOLIO_CONFIGS.keys())}")
    
    config = PORTFOLIO_CONFIGS[portfolio_type]
    
    # Read and prepare the base dataframe
    df = pd.read_csv('vanguard_base.csv')
    df['symbol'] = df['Benchmark ID'].str.extract(r'_(\w+)(?:\s+|$)')
    df = df.merge(market_caps_df[['symbol', 'MarketCapIndex']], on='symbol', how='left')
    df['Weight'] = np.nan
    
    def calculate_fi_weights():
        """Calculate fixed income weights ensuring total allocation equals fixed_income_allocation"""
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
    
    def calculate_equity_weights():
        """Calculate equity weights"""
        print(f"\nCalculating {portfolio_type} Equity Weights:")
        
        # Step 1: Fix I00010 weight
        i00010_mask = df['Benchmark ID'].str.contains(f'{portfolio_type}_I00010', na=False)
        df.loc[i00010_mask, 'Weight'] = config['base_weight']
        print(f"{portfolio_type}_I00010: Fixed weight = {config['base_weight']}")
        
        # Step 2: Calculate Tier 2 weights (I01018 and I01270)
        i01018_mcap = df.loc[df['Benchmark ID'].str.contains(f'{portfolio_type}_I01018', na=False), 'MarketCapIndex'].iloc[0]
        i01270_mcap = df.loc[df['Benchmark ID'].str.contains(f'{portfolio_type}_I01270', na=False), 'MarketCapIndex'].iloc[0]
        equity_tier_2_total_mcap = i01018_mcap + i01270_mcap
        print(f"EQUITY_TIER_2_TOTAL_MCAP: {equity_tier_2_total_mcap:,.9f}")
        
        # Calculate I01018 and I01270 weights
        for symbol, mcap in [('I01018', i01018_mcap), ('I01270', i01270_mcap)]:
            weight = min(config['base_weight'], 
                        (config['equity_allocation'] - config['base_weight']) * 
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
        
        remaining_weight = config['equity_allocation'] - (config['base_weight'] + i01018_weight + i01270_weight)
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
                    weight = min(config['base_weight'], 
                               remaining_weight * (mcap / equity_tier_3_total_mcap))
                    df.loc[mask, 'Weight'] = weight
                    print(f"{portfolio_type}_{symbol}: mcap={mcap:,.9f}, weight={weight:.9f}")
        
        # Step 4: Calculate SP50 weight
        i00586_weight = df.loc[df['Benchmark ID'].str.contains(f'{portfolio_type}_I00586', na=False), 'Weight'].iloc[0]
        print(f"\nI00586 weight for SP50 check: {i00586_weight:.9f}")
        
        if i00586_weight < config['base_weight']:
            print(f"Setting SP50 weight to 0 as I00586 weight < {config['base_weight']}")
            df.loc[df['Benchmark ID'].str.contains(f'{portfolio_type}_SP50', na=False), 'Weight'] = 0
        else:
            total_other_weights = (config['base_weight'] + i01018_weight + i01270_weight + 
                                 df.loc[df['Benchmark ID'].str.contains(f'{portfolio_type}_') & 
                                       df['symbol'].isin(tier_3_symbols), 'Weight'].sum())
            sp50_weight = max(0, config['equity_allocation'] - total_other_weights)
            df.loc[df['Benchmark ID'].str.contains(f'{portfolio_type}_SP50', na=False), 'Weight'] = sp50_weight
            print(f"SP50: total_other_weights={total_other_weights:.9f}, sp50_weight={sp50_weight:.9f}")
    
    # Calculate weights for both components
    calculate_fi_weights()
    calculate_equity_weights()
    
    return df

def main():
    # Process all portfolio types
    df = None
    for portfolio_type in ['LSE20', 'LSE40', 'LSE60', 'LSE80']:
        if df is None:
            df = calculate_weights(portfolio_type)
        else:
            # Update weights for subsequent portfolios
            portfolio_df = calculate_weights(portfolio_type)
            mask = portfolio_df['Benchmark ID'].str.contains(f'{portfolio_type}_', na=False)
            df.loc[mask, 'Weight'] = portfolio_df.loc[mask, 'Weight']
    
    # Add date column at the beginning
    df.insert(0, 'Date', date)
    
    # Print summaries for all portfolios
    for portfolio_type in ['LSE20', 'LSE40', 'LSE60', 'LSE80']:
        print(f"\n{portfolio_type} Weights Summary:")
        print("-" * 50)
        mask = df['Benchmark ID'].str.contains(f'{portfolio_type}_', na=False)
        summary_df = df[mask][['Benchmark ID', 'Weight']].sort_values('Benchmark ID')
        print(summary_df.to_string(index=False))
        total_weight = df[mask]['Weight'].sum()
        print(f"\nTotal {portfolio_type} Weight: {total_weight:.9f}")
    
    # Print number of non-null weights
    print(f"\nNumber of non-null weights: {df['Weight'].count()}")
    
    # Save the results with specific float format
    df.to_csv(f'vanguard_combined_weights_consolidated_{date}.csv', index=False, float_format='%.9f')
    print(f"\nCombined weights saved to vanguard_combined_weights_consolidated_{date}.csv")

if __name__ == "__main__":
    main()


