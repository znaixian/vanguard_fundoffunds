# FactSet Client Usage Guide

## Overview

The `FactSetClient` provides two methods for fetching data from FactSet Formula API:

1. **`get_market_caps()`** - Legacy method for market cap only (backward compatible)
2. **`fetch_data()`** - NEW generic method for multiple metrics (future-proof)

---

## Method 1: `get_market_caps()` - Market Cap Only

**Use when**: You only need market capitalization data (current production use case)

**Signature**:
```python
def get_market_caps(self, ids: List[str], date: str) -> pd.DataFrame
```

**Returns**:
```
DataFrame with exactly 2 columns: ['symbol', 'MarketCapIndex']
```

**Example**:
```python
from shared.api.factset_client import FactSetClient

client = FactSetClient('config/api_credentials.yaml')

# Fetch market caps for specific date
market_data = client.get_market_caps(
    ids=['LHMN34611', 'I00010', 'I01018'],
    date='20250821'
)

# Result:
#   symbol       MarketCapIndex
#   LHMN34611    13383929.764
#   I00010       78748805.608
#   I01018       8811976.832
```

**Features**:
- ✅ Automatic retry with exponential backoff (3 attempts)
- ✅ Null value detection and error raising
- ✅ Missing ID detection
- ✅ Type conversion to numeric
- ✅ Email notifications on failure (via pipeline)

---

## Method 2: `fetch_data()` - Multiple Metrics (NEW)

**Use when**: You need market cap + other metrics (returns, prices, volume, etc.)

**Signature**:
```python
def fetch_data(self, ids: List[str], formulas: dict) -> pd.DataFrame
```

**Returns**:
```
DataFrame with columns: ['symbol', <formula_column_names>...]
Number of columns = 1 + len(formulas)
```

### Example 1: Market Cap + Returns

```python
from shared.api.factset_client import FactSetClient

client = FactSetClient('config/api_credentials.yaml')

# Define formulas with dynamic dates
date = '20250821'
start_date = '20250721'  # 1 month ago

formulas = {
    'MarketCapIndex': f'FG_MCAP_IDX({date},{date},,USD)',
    'Return_1M': f'FG_RETURN({start_date},{date})',
    'Price': f'FG_PRICE({date})'
}

# Fetch multiple metrics
data = client.fetch_data(
    ids=['LHMN34611', 'I00010'],
    formulas=formulas
)

# Result:
#   symbol       MarketCapIndex  Return_1M  Price
#   LHMN34611    13383929.764   0.0234     102.45
#   I00010       78748805.608   0.0187     85.32
```

### Example 2: Multiple Date Ranges

```python
formulas = {
    'MarketCap': f'FG_MCAP_IDX({date},{date},,USD)',
    'Return_1M': f'FG_RETURN({date_1m},{date})',
    'Return_3M': f'FG_RETURN({date_3m},{date})',
    'Return_6M': f'FG_RETURN({date_6m},{date})',
    'Return_YTD': f'FG_RETURN({ytd_start},{date})'
}

data = client.fetch_data(ids=security_ids, formulas=formulas)

# Result has 6 columns: symbol + 5 metrics
```

### Example 3: Using in a Fund Calculator

```python
# In a new fund that needs returns for weighting
class PerformanceWeightedFund:
    def calculate_weights(self, ids, date):
        client = FactSetClient('config/api_credentials.yaml')

        # Fetch market cap AND returns
        formulas = {
            'MarketCapIndex': f'FG_MCAP_IDX({date},{date},,USD)',
            'Return_12M': f'FG_RETURN({date_12m_ago},{date})'
        }

        data = client.fetch_data(ids, formulas)

        # Weight by market cap * (1 + return)
        data['AdjustedWeight'] = data['MarketCapIndex'] * (1 + data['Return_12M'])
        # ... rest of calculation
```

---

## Key Features of `fetch_data()`

### 1. Dynamic Formula Construction
```python
# ❌ DON'T hardcode dates
formulas = {
    'MarketCap': 'FG_MCAP_IDX(20250821,20250821,,USD)'  # WRONG
}

# ✅ DO use variables
date = '20250821'
formulas = {
    'MarketCap': f'FG_MCAP_IDX({date},{date},,USD)'  # CORRECT
}
```

### 2. Generic Validation
- Validates **all** formula columns for null values
- Reports which specific metric failed
- Example error: `MissingDataError: Missing data for metric 'Return_1M': ['LHMN34611']`

### 3. Flexible Column Names
```python
# You choose the output column names
formulas = {
    'MktCap_USD': f'FG_MCAP_IDX({date},{date},,USD)',
    'Ret1M': f'FG_RETURN({start},{date})',
    'Vol': f'FG_VOLUME({date})'
}

# Columns in result: ['symbol', 'MktCap_USD', 'Ret1M', 'Vol']
```

### 4. Automatic Retry & Error Handling
Same as `get_market_caps()`:
- 3 retry attempts
- Exponential backoff
- Connection error handling
- Auth error detection

---

## Common FactSet Formulas

| Formula | Description | Example |
|---------|-------------|---------|
| `FG_MCAP_IDX(start,end,,currency)` | Market cap index | `FG_MCAP_IDX(20250821,20250821,,USD)` |
| `FG_RETURN(start,end)` | Total return | `FG_RETURN(20250721,20250821)` |
| `FG_PRICE(date)` | Price | `FG_PRICE(20250821)` |
| `FG_VOLUME(date)` | Trading volume | `FG_VOLUME(20250821)` |
| `FG_BETA(date)` | Beta | `FG_BETA(20250821)` |
| `FG_VOLATILITY(start,end)` | Volatility | `FG_VOLATILITY(20250721,20250821)` |

Refer to FactSet Formula API documentation for complete list.

---

## Migration Path

### Current Production (Vanguard LifeStrategy)
```python
# Uses get_market_caps() - NO CHANGES NEEDED
market_data = client.get_market_caps(ids=all_ids, date=run_date)
# Returns: ['symbol', 'MarketCapIndex']
```

### Future Fund 2 (if needs returns)
```python
# Option A: Still use get_market_caps() if only market cap needed
market_data = client.get_market_caps(ids=all_ids, date=run_date)

# Option B: Use fetch_data() for additional metrics
formulas = {
    'MarketCapIndex': f'FG_MCAP_IDX({date},{date},,USD)',
    'Return_6M': f'FG_RETURN({date_6m},{date})'
}
market_data = client.fetch_data(ids=all_ids, formulas=formulas)
# Returns: ['symbol', 'MarketCapIndex', 'Return_6M']

# Calculator can use MarketCapIndex as before
# Plus now has access to Return_6M for additional logic
```

---

## Error Handling

Both methods raise the same exceptions:

| Exception | When | How to Handle |
|-----------|------|---------------|
| `APIConnectionError` | Network issues, timeouts | Retry manually or check network |
| `APIAuthError` | Invalid credentials | Update `config/api-key.txt` |
| `DataNotAvailableError` | Weekend/holiday, invalid date | Use previous business day |
| `MissingDataError` | Null values, missing IDs | Check FactSet data availability |

**Example**:
```python
try:
    data = client.fetch_data(ids, formulas)
except MissingDataError as e:
    logger.error(f"Missing data: {e}")
    # Send email notification
    # Return error status
```

---

## Performance Considerations

### Single API Call for Multiple Metrics
```python
# ❌ DON'T make multiple calls
market_caps = client.get_market_caps(ids, date)  # API call 1
# ... then fetch returns separately somehow

# ✅ DO fetch everything in one call
formulas = {
    'MarketCapIndex': f'FG_MCAP_IDX({date},{date},,USD)',
    'Return_1M': f'FG_RETURN({start},{date})'
}
data = client.fetch_data(ids, formulas)  # Single API call
```

### Shared Data Across Funds
Current pipeline already does this correctly:
```python
# main_pipeline.py fetches once for all funds
market_data = client.get_market_caps(all_ids, date)

# Passes to each fund
for fund in funds:
    fund.calculate(market_data)  # Each fund uses subset
```

---

## Testing

### Test `get_market_caps()`
```bash
python -m orchestration.main_pipeline --date=20250821
# Should complete successfully
```

### Test `fetch_data()` (future)
```python
# Create test script: test_fetch_data.py
from shared.api.factset_client import FactSetClient

client = FactSetClient('config/api_credentials.yaml')

formulas = {
    'MarketCapIndex': 'FG_MCAP_IDX(20250821,20250821,,USD)',
    'Return_1M': 'FG_RETURN(20250721,20250821)'
}

data = client.fetch_data(
    ids=['LHMN34611', 'I00010'],
    formulas=formulas
)

print(data)
# Should show 2 rows, 3 columns
```

---

## Summary

| Feature | `get_market_caps()` | `fetch_data()` |
|---------|---------------------|----------------|
| **Use Case** | Market cap only | Multiple metrics |
| **Columns** | Fixed: `['symbol', 'MarketCapIndex']` | Dynamic: `['symbol', ...]` |
| **Current Use** | Production (Vanguard) | Future funds |
| **Breaking Changes** | None - stable | None - new method |
| **Performance** | 1 API call | 1 API call (multiple formulas) |
| **Validation** | MarketCapIndex only | All formula columns |
| **Flexibility** | Low | High |

**Recommendation**:
- Keep using `get_market_caps()` for current production
- Use `fetch_data()` when you need additional metrics
- Both methods are fully supported and maintained
