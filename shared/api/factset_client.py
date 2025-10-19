"""
FactSet API Client
Handles all interactions with FactSet Formula API
"""

import requests
import base64
import pandas as pd
import time
import yaml
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
            credentials_path: Path to api_credentials.yaml
        """
        self.config = self._load_credentials(credentials_path)
        self.base_url = self.config['factset']['base_url']
        self.timeout = self.config['factset']['timeout_seconds']
        self.max_retries = self.config['factset']['retry_attempts']
        self.retry_delay = self.config['factset']['retry_delay_seconds']
        self.username = self.config['factset']['username']

        # Load API key from separate file
        api_key_file = Path(self.config['factset']['api_key_file'])
        with open(api_key_file) as f:
            self.api_key = f.read().strip()

    def _load_credentials(self, path: str) -> dict:
        """Load credentials from YAML file."""
        with open(path) as f:
            return yaml.safe_load(f)

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
