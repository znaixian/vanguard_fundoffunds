"""
FactSet API Client
Handles all interactions with FactSet Formula API
"""

import requests
import base64
import pandas as pd
import time
import yaml
import os
from typing import List
from pathlib import Path


class APIConnectionError(Exception):
    """Cannot reach FactSet API"""
    pass


class APIAuthError(Exception):
    """Invalid credentials"""
    pass


class DataNotAvailableError(Exception):
    """Data not available for date"""
    pass


class MissingDataError(Exception):
    """Some IDs returned null values"""
    pass


class FactSetClient:
    """Client for FactSet Formula API with retry logic and error handling."""

    def __init__(self, credentials_path: str):
        """
        Initialize FactSet client.

        Args:
            credentials_path: Path to api_credentials.yaml (will fall back to env vars if not found)
        """
        self.config = self._load_credentials(credentials_path)
        self.base_url = self.config['factset']['base_url']
        self.timeout = self.config['factset']['timeout_seconds']
        self.max_retries = self.config['factset']['retry_attempts']
        self.retry_delay = self.config['factset']['retry_delay_seconds']
        self.username = self.config['factset']['username']

        # Load API key from file or environment variable
        if 'api_key_file' in self.config['factset']:
            api_key_file = Path(self.config['factset']['api_key_file'])
            if api_key_file.exists():
                with open(api_key_file) as f:
                    self.api_key = f.read().strip()
            else:
                # Fall back to environment variable
                self.api_key = os.getenv('FACTSET_API_KEY', '')
        else:
            # Config loaded from env vars, API key already set
            self.api_key = self.config['factset']['api_key']

    def _load_credentials(self, path: str) -> dict:
        """
        Load credentials from YAML file or environment variables.

        Priority:
        1. Try loading from YAML file (local setup)
        2. Fall back to environment variables (FactSet.io deployment)
        """
        # Try loading from file first (existing behavior for local)
        if os.path.exists(path):
            with open(path) as f:
                return yaml.safe_load(f)

        # Fall back to environment variables (for FactSet.io deployment)
        print(f"[INFO] Config file {path} not found, using environment variables")
        return {
            'factset': {
                'username': os.getenv('FACTSET_USERNAME', ''),
                'api_key': os.getenv('FACTSET_API_KEY', ''),
                'base_url': os.getenv('FACTSET_BASE_URL', 'https://api.factset.com/formula-api/v1'),
                'timeout_seconds': int(os.getenv('FACTSET_TIMEOUT', '30')),
                'retry_attempts': int(os.getenv('FACTSET_RETRY_ATTEMPTS', '3')),
                'retry_delay_seconds': int(os.getenv('FACTSET_RETRY_DELAY', '5'))
            }
        }

    def _get_auth_headers(self) -> dict:
        """Generate authentication headers."""
        auth_string = f"{self.username.upper()}:{self.api_key}"
        auth_bytes = base64.b64encode(auth_string.encode('utf-8'))
        auth_b64 = auth_bytes.decode('ascii')

        return {
            'Authorization': f'Basic {auth_b64}',
            'Content-Type': 'application/json'
        }

    def get_market_caps(self, ids: List[str], date: str) -> pd.DataFrame:
        """
        Fetch fresh market cap data for given IDs and date.

        Args:
            ids: List of security IDs (e.g., ['LHMN34611', 'I00010', ...])
            date: Date in YYYYMMDD format

        Returns:
            DataFrame with columns: ['symbol', 'MarketCapIndex']

        Raises:
            APIConnectionError: Cannot reach FactSet API
            APIAuthError: Invalid credentials
            DataNotAvailableError: Data not available for date
            MissingDataError: Some IDs returned null values
        """
        for attempt in range(1, self.max_retries + 1):
            try:
                return self._fetch_with_validation(ids, date)
            except (APIConnectionError, requests.Timeout) as e:
                if attempt == self.max_retries:
                    raise
                wait_time = self.retry_delay * (2 ** (attempt - 1))  # Exponential backoff
                print(f"API call failed (attempt {attempt}/{self.max_retries}), retrying in {wait_time}s: {e}")
                time.sleep(wait_time)

    def _fetch_with_validation(self, ids: List[str], date: str) -> pd.DataFrame:
        """Make API call and validate response."""
        # Build request
        ids_string = ','.join(ids)
        formula = f'FG_MCAP_IDX({date},{date},,USD)'
        url = f'{self.base_url}/time-series?ids={ids_string}&formulas={formula}&flatten=Y'

        try:
            # Make request
            response = requests.get(url, headers=self._get_auth_headers(), timeout=self.timeout)

            # Check for auth errors
            if response.status_code == 401:
                raise APIAuthError("Invalid or expired API credentials")

            response.raise_for_status()

        except requests.exceptions.ConnectionError as e:
            raise APIConnectionError(f"Cannot reach FactSet API: {e}")
        except requests.exceptions.Timeout as e:
            raise APIConnectionError(f"FactSet API timeout: {e}")

        # Parse response
        try:
            data = response.json()
        except ValueError as e:
            raise APIConnectionError(f"Invalid JSON response from FactSet: {e}")

        if 'data' not in data:
            raise DataNotAvailableError(f"No data returned from FactSet API")

        df = pd.DataFrame(data['data'])

        if df.empty:
            raise DataNotAvailableError(f"Empty data returned for date {date}")

        df = df.rename(columns={
            'requestId': 'symbol',
            formula: 'MarketCapIndex'
        })[['symbol', 'MarketCapIndex']]

        # Validate
        df['MarketCapIndex'] = pd.to_numeric(df['MarketCapIndex'], errors='coerce')

        # Check for missing data
        if df['MarketCapIndex'].isnull().any():
            missing = df[df['MarketCapIndex'].isnull()]['symbol'].tolist()
            raise MissingDataError(f"Missing market cap data for: {missing}")

        if len(df) != len(ids):
            missing = set(ids) - set(df['symbol'])
            raise MissingDataError(f"IDs not returned by API: {missing}")

        print(f"Successfully fetched market caps for {len(df)} securities")
        return df

    def fetch_data(self, ids: List[str], formulas: dict) -> pd.DataFrame:
        """
        Generic method to fetch data for multiple FactSet formulas.
        Use this for advanced scenarios requiring multiple metrics.

        Args:
            ids: List of security IDs (e.g., ['LHMN34611', 'I00010', ...])
            formulas: Dictionary mapping output column names to FactSet formulas.
                     Formulas must be fully constructed with all parameters.
                     Example: {
                         'MarketCapIndex': 'FG_MCAP_IDX(20250821,20250821,,USD)',
                         'Return_1M': 'FG_RETURN(20250721,20250821)',
                         'Price': 'FG_PRICE(20250821)',
                         'Volume': 'FG_VOLUME(20250821)'
                     }

        Returns:
            DataFrame with columns: ['symbol', <column_names_from_formulas>...]
            Column order: 'symbol' first, then formula columns in dict order

        Raises:
            APIConnectionError: Cannot reach FactSet API
            APIAuthError: Invalid credentials
            DataNotAvailableError: Data not available
            MissingDataError: Some IDs returned null values for any metric

        Example:
            # Fetch market cap and returns
            formulas = {
                'MarketCapIndex': f'FG_MCAP_IDX({date},{date},,USD)',
                'Return_1M': f'FG_RETURN({start_date},{date})'
            }
            df = client.fetch_data(ids=['LHMN34611', 'I00010'], formulas=formulas)
            # Returns: ['symbol', 'MarketCapIndex', 'Return_1M']
        """
        for attempt in range(1, self.max_retries + 1):
            try:
                return self._fetch_formulas_with_validation(ids, formulas)
            except (APIConnectionError, requests.Timeout) as e:
                if attempt == self.max_retries:
                    raise
                wait_time = self.retry_delay * (2 ** (attempt - 1))  # Exponential backoff
                print(f"API call failed (attempt {attempt}/{self.max_retries}), retrying in {wait_time}s: {e}")
                time.sleep(wait_time)

    def _fetch_formulas_with_validation(self, ids: List[str], formulas: dict) -> pd.DataFrame:
        """Make API call for multiple formulas and validate response."""
        if not formulas:
            raise ValueError("formulas dictionary cannot be empty")

        # Build request with multiple formulas
        ids_string = ','.join(ids)
        formulas_string = ','.join(formulas.values())
        url = f'{self.base_url}/time-series?ids={ids_string}&formulas={formulas_string}&flatten=Y'

        try:
            # Make request
            response = requests.get(url, headers=self._get_auth_headers(), timeout=self.timeout)

            # Check for auth errors
            if response.status_code == 401:
                raise APIAuthError("Invalid or expired API credentials")

            response.raise_for_status()

        except requests.exceptions.ConnectionError as e:
            raise APIConnectionError(f"Cannot reach FactSet API: {e}")
        except requests.exceptions.Timeout as e:
            raise APIConnectionError(f"FactSet API timeout: {e}")

        # Parse response
        try:
            data = response.json()
        except ValueError as e:
            raise APIConnectionError(f"Invalid JSON response from FactSet: {e}")

        if 'data' not in data:
            raise DataNotAvailableError(f"No data returned from FactSet API")

        df = pd.DataFrame(data['data'])

        if df.empty:
            raise DataNotAvailableError(f"Empty data returned")

        # Rename columns: map FactSet formula strings to desired column names
        rename_map = {'requestId': 'symbol'}
        for col_name, formula_str in formulas.items():
            rename_map[formula_str] = col_name

        df = df.rename(columns=rename_map)

        # Select only the columns we care about (symbol + formula columns)
        expected_columns = ['symbol'] + list(formulas.keys())
        df = df[expected_columns]

        # Validate each formula column
        for col_name in formulas.keys():
            # Convert to numeric
            df[col_name] = pd.to_numeric(df[col_name], errors='coerce')

            # Check for missing data
            if df[col_name].isnull().any():
                missing = df[df[col_name].isnull()]['symbol'].tolist()
                raise MissingDataError(f"Missing data for metric '{col_name}': {missing}")

        # Check all IDs were returned
        if len(df) != len(ids):
            missing = set(ids) - set(df['symbol'])
            raise MissingDataError(f"IDs not returned by API: {missing}")

        print(f"Successfully fetched {len(formulas)} metrics for {len(df)} securities")
        return df

    def get_returns(self, id_to_factset_map: dict, date: str) -> pd.DataFrame:
        """
        Fetch return data using RA_RET formula for given securities.

        Args:
            id_to_factset_map: Dictionary mapping internal IDs to full FactSet identifiers
                              Example: {'LHMN34611': 'LEHHEUR:LHMN34611', 'I00010': 'FTG_N:I00010'}
            date: Date in YYYYMMDD format (e.g., '20251121')

        Returns:
            DataFrame with columns: ['symbol', 'Return']
            - symbol: Internal security ID
            - Return: Daily return value

        Raises:
            APIConnectionError: Cannot reach FactSet API
            APIAuthError: Invalid credentials
            DataNotAvailableError: Data not available for date
            MissingDataError: Some IDs returned null values

        Example:
            id_map = {
                'LHMN34611': 'LEHHEUR:LHMN34611',
                'I00010': 'FTG_N:I00010'
            }
            df = client.get_returns(id_map, '20251121')
            # Returns DataFrame with columns: ['symbol', 'Return']
        """
        # Convert date from YYYYMMDD to MM/DD/YYYY format for RA_RET formula
        # Example: '20251121' -> '11/21/2025'
        year = date[:4]
        month = date[4:6]
        day = date[6:8]
        formatted_date = f"{month}/{day}/{year}"

        # Make the API call
        for attempt in range(1, self.max_retries + 1):
            try:
                df_result = self._fetch_returns_with_validation(id_to_factset_map, formatted_date)
                return df_result
            except (APIConnectionError, requests.Timeout) as e:
                if attempt == self.max_retries:
                    raise
                wait_time = self.retry_delay * (2 ** (attempt - 1))
                print(f"Returns API call failed (attempt {attempt}/{self.max_retries}), retrying in {wait_time}s: {e}")
                time.sleep(wait_time)

    def _fetch_returns_with_validation(self, id_to_factset_map: dict, formatted_date: str) -> pd.DataFrame:
        """
        Fetch returns using multiple RA_RET formulas.

        This makes a single API call to fetch returns for all securities.

        Args:
            id_to_factset_map: Dict mapping internal IDs to FactSet identifiers
            formatted_date: Date in MM/DD/YYYY format

        Returns:
            DataFrame with columns: ['symbol', 'Return']
        """
        # Build RA_RET formulas for each security
        # Also build mapping from formula string to internal ID
        formulas_list = []
        formula_to_id = {}

        for internal_id, factset_id in id_to_factset_map.items():
            formula = f'RA_RET("{factset_id}",-1,{formatted_date},D,FIVEDAY,EUR,1)'
            formulas_list.append(formula)
            formula_to_id[formula] = internal_id

        # Build URL
        # Use the internal IDs as the ids parameter (they become the requestId in response)
        ids_string = ','.join(id_to_factset_map.keys())
        formulas_string = ','.join(formulas_list)
        url = f'{self.base_url}/time-series?ids={ids_string}&formulas={formulas_string}&flatten=Y'

        try:
            response = requests.get(url, headers=self._get_auth_headers(), timeout=self.timeout)

            if response.status_code == 401:
                raise APIAuthError("Invalid or expired API credentials")

            response.raise_for_status()

        except requests.exceptions.ConnectionError as e:
            raise APIConnectionError(f"Cannot reach FactSet API: {e}")
        except requests.exceptions.Timeout as e:
            raise APIConnectionError(f"FactSet API timeout: {e}")

        # Parse response
        try:
            data = response.json()
        except ValueError as e:
            raise APIConnectionError(f"Invalid JSON response from FactSet: {e}")

        if 'data' not in data:
            raise DataNotAvailableError(f"No data returned from FactSet API for returns")

        df = pd.DataFrame(data['data'])

        if df.empty:
            raise DataNotAvailableError(f"Empty return data for date {formatted_date}")

        # Response structure (with flatten=Y and multiple IDs):
        # We get one row per ID, with columns for all formulas
        # {
        #   "data": [
        #     {
        #       "requestId": "LHMN34611",
        #       "RA_RET(\"LEHHEUR:LHMN34611\",-1,11/21/2025,D,FIVEDAY,EUR,1)": 0.123,
        #       "RA_RET(\"LEHHEUR:LHMN21140\",-1,11/21/2025,D,FIVEDAY,EUR,1)": 0.170,
        #       ...all other formulas...,
        #       "date": "2025-11-21"
        #     },
        #     {
        #       "requestId": "LHMN21140",
        #       "RA_RET(\"LEHHEUR:LHMN34611\",-1,11/21/2025,D,FIVEDAY,EUR,1)": 0.123,
        #       "RA_RET(\"LEHHEUR:LHMN21140\",-1,11/21/2025,D,FIVEDAY,EUR,1)": 0.170,
        #       ...all other formulas...,
        #       "date": "2025-11-21"
        #     },
        #     ... (one row per ID)
        #   ]
        # }

        # We expect one row per ID
        expected_rows = len(id_to_factset_map)
        if len(df) != expected_rows:
            raise DataNotAvailableError(f"Unexpected response structure: expected {expected_rows} rows, got {len(df)}")

        # For each row, we need to find the matching formula for that ID
        # Each row has the same formula columns, but we only want the value
        # from the formula that corresponds to that row's requestId

        result_data = []
        for idx, row in df.iterrows():
            request_id = row['requestId']

            # Find the formula that corresponds to this requestId
            # The requestId is the internal ID, so find its FactSet ID and formula
            if request_id in id_to_factset_map:
                factset_id = id_to_factset_map[request_id]
                formula = f'RA_RET("{factset_id}",-1,{formatted_date},D,FIVEDAY,EUR,1)'

                if formula in row.index:
                    return_value = row[formula]
                    result_data.append({
                        'symbol': request_id,
                        'Return': return_value
                    })
                else:
                    raise DataNotAvailableError(f"Formula not found in row for {request_id}: {formula}")
            else:
                raise DataNotAvailableError(f"Unknown requestId in response: {request_id}")

        result_df = pd.DataFrame(result_data)

        # Validate - convert to numeric (this will convert nulls to NaN)
        result_df['Return'] = pd.to_numeric(result_df['Return'], errors='coerce')

        # Check for missing data (NaN values) - log warning but don't fail
        if result_df['Return'].isnull().any():
            missing = result_df[result_df['Return'].isnull()]['symbol'].tolist()
            print(f"Warning: {len(missing)} securities have no return data (will be NA): {missing}")

        # Verify all IDs were processed
        if len(result_df) != len(id_to_factset_map):
            missing = set(id_to_factset_map.keys()) - set(result_df['symbol'])
            raise MissingDataError(f"IDs not returned by returns API: {missing}")

        successful = result_df['Return'].notna().sum()
        print(f"Successfully fetched returns for {successful}/{len(result_df)} securities ({len(result_df) - successful} with missing data)")
        return result_df
