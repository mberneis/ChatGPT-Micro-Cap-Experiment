"""
Portfolio Configuration for Hugo Automation Trading System

This file allows you to easily configure your portfolio settings:
- Starting cash balance
- Current stock holdings
- Trading preferences
- API keys

Simply modify the values below and the system will use these settings.
"""

# =============================================================================
# PORTFOLIO SETTINGS
# =============================================================================

# Starting cash balance (USD)
CASH_BALANCE = 500.02

# Current stock holdings
# Format: "TICKER": {"shares": number_of_shares, "buy_price": price_per_share, "stop_loss": stop_price}

CURRENT_HOLDINGS = {
    "NVDA": {
        "shares": 2.63,
        "buy_price": 440.00,
        "stop_loss": 374.00
    },
    "GOOGL": {
        "shares": 0.625,
        "buy_price": 135.00,
        "stop_loss": 115.00
    },
    "AMZN": {
        "shares": 0.433,
        "buy_price": 130.00,
        "stop_loss": 110.00
    },
    "MSFT": {
        "shares": 0.4,
        "buy_price": 320.00,
        "stop_loss": 272.00
    },
    "NET": {
        "shares": 0.442,
        "buy_price": 65.00,
        "stop_loss": 55.00
    }
}

# Additional micro-cap research symbols (will fetch real-time data for these)
RESEARCH_SYMBOLS = [
    "MVIS",    # MicroVision
    "SNDL",    # Sundial Growers
    "BCDA",    # BioCardia
    "CARV",    # Carver Bancorp
    "XELA",    # Exela Technologies
    "BBIG",    # Vinco Ventures
    "ATER",    # Aterian
    "GREE"     # Greenidge Generation
]

# =============================================================================
# TRADING PREFERENCES
# =============================================================================

# Default data directory for CSV files and logs
DATA_DIRECTORY = "Start Your Own"

# Trading model preferences
OPENAI_MODEL = "gpt-4"              # OpenAI model to use
MIN_CONFIDENCE_THRESHOLD = 0.8     # Minimum confidence for trade execution (0.0 to 1.0)

# Risk management
DEFAULT_STOP_LOSS_PERCENT = 0.15   # 15% stop loss if not specified
MAX_POSITION_SIZE_PERCENT = 0.25   # Maximum 25% of portfolio per position

# =============================================================================
# API CONFIGURATION
# =============================================================================

# API Keys (can be overridden by environment variables)
# Leave as None to use environment variables: OPENAI_API_KEY, ALPHA_VANTAGE_API_KEY
OPENAI_API_KEY = None       # Set to your key or use: export OPENAI_API_KEY=your_key
ALPHA_VANTAGE_API_KEY = None # Set to your key or use: export ALPHA_VANTAGE_API_KEY=your_key

# =============================================================================
# ADVANCED SETTINGS
# =============================================================================

# Portfolio validation
VALIDATE_REAL_TIME_DATA = True     # Enforce real-time data validation
REJECT_FICTIONAL_SYMBOLS = True    # Block trades on non-verified symbols
PRICE_TOLERANCE_PERCENT = 0.05     # Allow 5% price difference from real-time data

# Logging and output
SAVE_LLM_RESPONSES = True          # Save AI responses to jsonl file
VERBOSE_OUTPUT = True              # Show detailed trading information

# Market data preferences
MAX_SYMBOLS_PER_BATCH = 12         # Limit symbols to avoid API rate limits
API_TIMEOUT_SECONDS = 30           # Timeout for API calls

# =============================================================================
# HELPER FUNCTIONS (Don't modify unless you know what you're doing)
# =============================================================================

def get_total_portfolio_value():
    """Calculate total portfolio value based on current holdings"""
    total_invested = sum(
        holding["shares"] * holding["buy_price"] 
        for holding in CURRENT_HOLDINGS.values()
    )
    return CASH_BALANCE + total_invested

def get_portfolio_summary():
    """Get a formatted summary of the current portfolio"""
    total_value = get_total_portfolio_value()
    
    summary = f"""
Portfolio Summary:
==================
Cash Balance: ${CASH_BALANCE:,.2f}
Total Portfolio Value: ${total_value:,.2f}

Current Holdings:
"""
    
    for ticker, holding in CURRENT_HOLDINGS.items():
        position_value = holding["shares"] * holding["buy_price"]
        percentage = (position_value / total_value) * 100
        summary += f"  {ticker}: {holding['shares']} shares @ ${holding['buy_price']:.2f} = ${position_value:,.2f} ({percentage:.1f}%)\n"
    
    return summary

def validate_configuration():
    """Validate the configuration settings"""
    errors = []
    
    # Check cash balance
    if CASH_BALANCE < 0:
        errors.append("Cash balance cannot be negative")
    
    # Check holdings
    for ticker, holding in CURRENT_HOLDINGS.items():
        if not isinstance(ticker, str) or len(ticker) < 1:
            errors.append(f"Invalid ticker symbol: {ticker}")
        
        if holding["shares"] <= 0:
            errors.append(f"{ticker}: Shares must be positive")
        
        if holding["buy_price"] <= 0:
            errors.append(f"{ticker}: Buy price must be positive")
        
        if holding["stop_loss"] <= 0:
            errors.append(f"{ticker}: Stop loss must be positive")
        
        if holding["stop_loss"] >= holding["buy_price"]:
            errors.append(f"{ticker}: Stop loss should be below buy price")
    
    # Check thresholds
    if not 0 <= MIN_CONFIDENCE_THRESHOLD <= 1:
        errors.append("Confidence threshold must be between 0 and 1")
    
    if not 0 <= MAX_POSITION_SIZE_PERCENT <= 1:
        errors.append("Max position size percent must be between 0 and 1")
    
    return errors

# =============================================================================
# QUICK SETUP EXAMPLES
# =============================================================================

"""
EXAMPLE 1: Starting fresh with $10,000
CASH_BALANCE = 10000.00
CURRENT_HOLDINGS = {}

EXAMPLE 2: Adding a new stock position
CURRENT_HOLDINGS = {
    "VTSI": {"shares": 557, "buy_price": 5.44, "stop_loss": 4.57},
    "CRWS": {"shares": 1030, "buy_price": 2.85, "stop_loss": 2.46},
    "MVIS": {"shares": 500, "buy_price": 1.20, "stop_loss": 1.00}  # New position
}

EXAMPLE 3: Updating cash after a trade
CASH_BALANCE = 3500.00  # Reduced cash after buying more stocks

EXAMPLE 4: Setting API keys directly (not recommended - use environment variables)
OPENAI_API_KEY = "sk-your-openai-key-here"
ALPHA_VANTAGE_API_KEY = "your-alpha-vantage-key-here"
"""

if __name__ == "__main__":
    # Test the configuration
    print(get_portfolio_summary())
    
    errors = validate_configuration()
    if errors:
        print("Configuration Errors:")
        for error in errors:
            print(f"  ❌ {error}")
    else:
        print("✅ Configuration is valid!")
        print(f"\nTotal symbols to track: {len(CURRENT_HOLDINGS) + len(RESEARCH_SYMBOLS)}")
        print(f"Research symbols: {', '.join(RESEARCH_SYMBOLS)}")