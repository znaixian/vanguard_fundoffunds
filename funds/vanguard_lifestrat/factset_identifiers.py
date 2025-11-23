"""
FactSet Identifier Mappings for Vanguard LifeStrategy
Maps internal security IDs to their full FactSet identifiers with prefixes
"""

# Mapping of security IDs to their full FactSet identifiers for RA_RET formula
# Format: 'internal_id': 'PREFIX:FACTSET_ID'
FACTSET_IDENTIFIER_MAP = {
    # Fixed Income - Bloomberg Global Aggregate (LEHHEUR prefix)
    'LHMN34611': 'LEHHEUR:LHMN34611',

    # Fixed Income - Tier 3 (LEHHEUR prefix)
    'LHMN21140': 'LEHHEUR:LHMN21140',
    'LHMN9913': 'LEHHEUR:LHMN9913',
    'LHMN21153': 'LEHHEUR:LHMN21153',

    # Fixed Income - Tier 3 (LEHUEUR prefix)
    'LHMN2004': 'LEHUEUR:LHMN2004',
    'LHMN2002': 'LEHUEUR:LHMN2002',

    # Equity - FTSE indices (FTG_N prefix)
    'I00010': 'FTG_N:I00010',      # FTSE All-World
    'I01018': 'FTG_N:I01018',      # FTSE Developed
    'I01270': 'FTG_N:I01270',      # FTSE Emerging Markets
    'I00586': 'FTG_N:I00586',      # FTSE North America
    'I27049': 'FTG_N:I27049',      # FTSE Europe
    'I26152': 'FTG_N:I26152',      # FTSE Asia Pacific
    '180948': 'FTG_N:180948',      # FTSE Japan

    # S&P 500 (SPUS_GR prefix with different ID)
    'SP50': 'SPUS_GR:00000117',    # S&P 500 index
}


def get_factset_identifier(internal_id: str) -> str:
    """
    Get the full FactSet identifier for a security ID.

    Args:
        internal_id: Internal security ID (e.g., 'LHMN34611', 'I00010', 'SP50')

    Returns:
        Full FactSet identifier with prefix (e.g., 'LEHHEUR:LHMN34611')

    Raises:
        KeyError: If internal_id is not found in mapping
    """
    if internal_id not in FACTSET_IDENTIFIER_MAP:
        raise KeyError(f"No FactSet identifier mapping found for ID: {internal_id}")

    return FACTSET_IDENTIFIER_MAP[internal_id]


def build_ra_ret_formula(internal_id: str, date: str) -> str:
    """
    Build RA_RET formula for a security.

    Formula format: RA_RET("PREFIX:ID", -1, DATE, D, FIVEDAY, EUR, 1)
    Where:
        - PREFIX:ID is the full FactSet identifier
        - -1 means 1 day before the date (start of return period)
        - DATE is the calculation date (end of return period)
        - D is daily frequency
        - FIVEDAY is the calculation method
        - EUR is the currency
        - 1 is an additional parameter

    Args:
        internal_id: Internal security ID (e.g., 'LHMN34611')
        date: Date in MM/DD/YYYY format (e.g., '11/21/2025')

    Returns:
        RA_RET formula string

    Example:
        >>> build_ra_ret_formula('LHMN34611', '11/21/2025')
        'RA_RET("LEHHEUR:LHMN34611",-1,11/21/2025,D,FIVEDAY,EUR,1)'
    """
    factset_id = get_factset_identifier(internal_id)
    return f'RA_RET("{factset_id}",-1,{date},D,FIVEDAY,EUR,1)'


def get_all_identifiers() -> dict:
    """
    Get all FactSet identifier mappings.

    Returns:
        Dictionary mapping internal IDs to FactSet identifiers
    """
    return FACTSET_IDENTIFIER_MAP.copy()
