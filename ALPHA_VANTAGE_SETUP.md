# Alpha Vantage Real-Time Data Integration

This document explains how to set up and use the Alpha Vantage integration for real-time stock data in your trading automation system.

## Overview

The Alpha Vantage integration provides:
- Real-time stock quotes and pricing data
- Company fundamentals and market cap information
- Trading volume and change percentages
- Enhanced accuracy for micro-cap stock trading decisions

## Setup Instructions

### 1. Get an Alpha Vantage API Key

1. Visit [Alpha Vantage](https://www.alphavantage.co/support/#api-key)
2. Sign up for a free account (provides 25 API calls per day)
3. Or upgrade to a premium plan for higher limits
4. Copy your API key

### 2. Set Up Environment Variables

**Option A: Set environment variable (Recommended)**
```bash
export ALPHA_VANTAGE_API_KEY=your_alpha_vantage_api_key_here
```

**Option B: Pass as command line argument**
```bash
python hugo_automation.py --alpha-vantage-key your_alpha_vantage_api_key_here
```

### 3. Install Node.js (Required for MCP Server)

The Alpha Vantage MCP server requires Node.js:
```bash
# Check if you have Node.js installed
node --version

# If not installed, visit https://nodejs.org/ and install Node.js
```

## Usage

### Basic Usage with Real-Time Data

```bash
# Set your API keys
export OPENAI_API_KEY=your_openai_key
export ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key

# Run with real-time data
python hugo_automation.py
```

### Test the Integration

```bash
# Test the Alpha Vantage connection
python test_alpha_vantage.py
```

### Command Line Options

```bash
python hugo_automation.py [OPTIONS]

Options:
  --api-key TEXT              OpenAI API key (or set OPENAI_API_KEY env var)
  --alpha-vantage-key TEXT    Alpha Vantage API key (or set ALPHA_VANTAGE_API_KEY env var)
  --model TEXT                OpenAI model to use (default: gpt-4)
  --data-dir TEXT             Data directory (default: Start Your Own)
  --dry-run                   Don't execute trades, just show recommendations
```

## How It Works

1. **Market Data Fetching**: The system fetches real-time prices for:
   - Current portfolio holdings (VTSI, CRWS)
   - Common micro-cap research targets (MVIS, SNDL, BCDA, CARV)

2. **Enhanced Prompts**: The AI receives:
   - Current stock prices with timestamps
   - Volume and change percentage data
   - Clear instructions to use real-time data for all calculations

3. **Improved Accuracy**: Real-time data eliminates:
   - Price estimation errors
   - Outdated market information
   - Position sizing mistakes

## Example Output

When real-time data is available, you'll see:

```
Portfolio loaded: $4,034.42 cash, $10,000.00 total equity
Fetching real-time market data...
Market data fetched successfully for 6 symbols
Generated prompt (5200 characters)
Calling LLM for trading recommendations...
```

The AI will receive data like:
```
=== REAL-TIME MARKET DATA ===
Data fetched at: 2025-01-06T18:30:00Z
Symbols analyzed: 6

[ Current Market Prices ]
VTSI: $5.23 (-2.1%) Vol: 125,430
CRWS: $2.91 (+1.2%) Vol: 89,200
MVIS: $1.45 (-0.8%) Vol: 2,150,000
...
```

## Rate Limits and Best Practices

### Free Tier Limits
- 25 API calls per day
- 5 API calls per minute

### Optimization Tips
1. **Limited Symbol Lists**: The system automatically fetches data for portfolio holdings plus 4-6 research targets
2. **Caching**: Consider adding caching for multiple runs in the same day
3. **Error Handling**: The system gracefully falls back to LLM knowledge if API calls fail

## Troubleshooting

### Common Issues

**"Alpha Vantage API key is required"**
- Solution: Set the ALPHA_VANTAGE_API_KEY environment variable

**"Failed to connect to Alpha Vantage MCP server"**
- Solution: Ensure Node.js is installed and npx is available

**"Rate limit exceeded"**
- Solution: Wait or upgrade to a premium Alpha Vantage plan

**"Error fetching quote for SYMBOL"**
- Solution: Check if the stock symbol is valid and actively traded

### Debug Mode

For debugging, you can run the client directly:
```python
from alpha_vantage_client import get_stock_prices_sync
prices = get_stock_prices_sync(['MVIS', 'SNDL'])
print(prices)
```

## Benefits

### Before (LLM Knowledge Only)
- Outdated or estimated prices
- Risk of position sizing errors
- Less accurate trading decisions

### After (Real-Time Data)
- Current market prices with timestamps
- Accurate volume and liquidity information
- Precise position sizing calculations
- Better risk management

## Next Steps

1. Set up your Alpha Vantage API key
2. Run the test script to verify integration
3. Run your first automated trading session with real-time data
4. Monitor the improved accuracy of trading recommendations

For questions or issues, check the logs or run the test script for diagnostics.