"""
Simple Automation Script for ChatGPT Micro-Cap Trading

This script integrates with the existing trading_script.py to provide
automated LLM-based trading decisions.

Usage:
    python simple_automation.py --api-key YOUR_KEY
"""

import json
import os
import re
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Any, Tuple
import pandas as pd

# Import existing trading functions
from trading_script import (
    process_portfolio, daily_results, load_latest_portfolio_state,
    set_data_dir, PORTFOLIO_CSV, TRADE_LOG_CSV, last_trading_date
)

# Import Alpha Vantage client for real-time data
from alpha_vantage_client import get_stock_prices_sync, get_stock_info_sync

# Import configuration
try:
    import portfolio_config as config
    print("✅ Loaded portfolio configuration from portfolio_config.py")
except ImportError:
    print("❌ Could not load portfolio_config.py - using defaults")
    config = None

try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


def create_portfolio_from_config() -> Tuple[pd.DataFrame, float]:
    """Create portfolio DataFrame and cash balance from config"""
    
    if not config:
        # Fallback to defaults
        return pd.DataFrame(columns=["ticker", "shares", "stop_loss", "buy_price", "cost_basis"]), 10000.0
    
    # Validate configuration
    errors = config.validate_configuration()
    if errors:
        print("⚠️ Configuration validation errors:")
        for error in errors:
            print(f"   {error}")
        print("Using defaults instead...")
        return pd.DataFrame(columns=["ticker", "shares", "stop_loss", "buy_price", "cost_basis"]), 10000.0
    
    # Create portfolio DataFrame from config
    portfolio_data = []
    for ticker, holding in config.CURRENT_HOLDINGS.items():
        cost_basis = holding["shares"] * holding["buy_price"]
        portfolio_data.append({
            "ticker": ticker,
            "shares": holding["shares"], 
            "stop_loss": holding["stop_loss"],
            "buy_price": holding["buy_price"],
            "cost_basis": cost_basis
        })
    
    portfolio_df = pd.DataFrame(portfolio_data)
    cash_balance = config.CASH_BALANCE
    
    return portfolio_df, cash_balance


def fetch_current_market_data(portfolio_df: pd.DataFrame, alpha_vantage_api_key: str = None) -> Dict[str, Any]:
    """Fetch real-time market data for portfolio holdings and potential targets"""
    
    try:
        # Get symbols from current portfolio
        current_symbols = []
        if not portfolio_df.empty and 'ticker' in portfolio_df.columns:
            current_symbols = portfolio_df['ticker'].tolist()
        
        # Add research symbols from config
        research_symbols = config.RESEARCH_SYMBOLS if config else ['MVIS', 'SNDL', 'BCDA', 'CARV', 'XELA', 'BBIG', 'ATER', 'GREE']
        all_symbols = list(set(current_symbols + research_symbols))
        
        # Limit symbols to avoid API rate limits
        max_symbols = config.MAX_SYMBOLS_PER_BATCH if config else 12
        if len(all_symbols) > max_symbols:
            print(f"⚠️ Limiting to {max_symbols} symbols to avoid API rate limits")
            all_symbols = all_symbols[:max_symbols]
        
        if not all_symbols:
            return {"error": "No symbols to fetch"}
        
        print(f"Fetching real-time data for {len(all_symbols)} symbols: {', '.join(all_symbols)}")
        
        # Fetch real-time prices
        market_data = get_stock_prices_sync(all_symbols, alpha_vantage_api_key)
        
        # Validate and filter out invalid responses
        validated_data = {}
        failed_symbols = []
        
        for symbol, data in market_data.items():
            if 'error' not in data and data.get('price') and data.get('price') != 'N/A':
                try:
                    # Ensure price is numeric
                    price = float(data['price'])
                    if price > 0:  # Valid price
                        validated_data[symbol] = data
                    else:
                        failed_symbols.append(f"{symbol}: Invalid price {price}")
                except (ValueError, TypeError):
                    failed_symbols.append(f"{symbol}: Non-numeric price {data.get('price')}")
            else:
                failed_symbols.append(f"{symbol}: {data.get('error', 'No data available')}")
        
        if failed_symbols:
            print(f"Warning: Failed to get valid data for: {'; '.join(failed_symbols)}")
        
        return {
            "success": len(validated_data) > 0,
            "data": validated_data,
            "timestamp": pd.Timestamp.now().isoformat(),
            "symbols_fetched": len(validated_data),
            "symbols_failed": len(failed_symbols),
            "failed_symbols": failed_symbols
        }
        
    except Exception as e:
        return {
            "error": f"Failed to fetch market data: {str(e)}",
            "success": False
        }


def generate_trading_prompt(portfolio_df: pd.DataFrame, cash: float, total_equity: float, market_data: Dict[str, Any] = None) -> str:
    """Generate Hugo's Deep Research trading prompt with current portfolio data and real-time market data"""

    # Format holdings
    if portfolio_df.empty:
        holdings_text = "No current holdings"
    else:
        holdings_text = portfolio_df.to_string(index=False)

    # Get current date
    today = last_trading_date().date().isoformat()
    
    # Get confidence threshold from config
    min_confidence = config.MIN_CONFIDENCE_THRESHOLD if config else 0.8
    
    # Format market data section with strict validation
    market_data_section = ""
    available_symbols = []
    
    if market_data and market_data.get('success') and market_data.get('data'):
        valid_data = market_data['data']
        available_symbols = list(valid_data.keys())
        
        market_data_section = f"""

=== VERIFIED REAL-TIME MARKET DATA ===
Data Source: Alpha Vantage API (Direct Integration)
Data fetched at: {market_data.get('timestamp', 'N/A')}
Valid symbols with verified prices: {market_data.get('symbols_fetched', 0)}
Failed/Invalid symbols: {market_data.get('symbols_failed', 0)}

[ VERIFIED CURRENT MARKET PRICES - USE THESE EXACT VALUES ]
"""
        
        for symbol, data in valid_data.items():
            price = data.get('price', 'N/A')
            change = data.get('change_percent', 'N/A')
            volume = data.get('volume', 'N/A')
            market_data_section += f"{symbol}: ${price} ({change}) Volume: {volume}\n"
        
        if market_data.get('failed_symbols'):
            market_data_section += f"\n[ UNAVAILABLE SYMBOLS - DO NOT TRADE ]"
            for failed in market_data.get('failed_symbols', []):
                market_data_section += f"\n{failed}"
                
        market_data_section += f"""

=== TRADING RESTRICTIONS BASED ON DATA AVAILABILITY ===
ONLY trade symbols with verified prices above: {', '.join(available_symbols)}
ABSOLUTE PROHIBITION: Do not recommend any symbol not in the verified list above
If you need to trade a symbol not in the verified list, recommend NO TRADE instead
=== END VERIFIED MARKET DATA ===
"""
    elif market_data and 'error' in market_data:
        market_data_section = f"""
=== MARKET DATA UNAVAILABLE ===
Error: {market_data['error']}
CRITICAL: No real-time data available - recommend NO TRADES to avoid inaccurate pricing
Only proceed if you have extremely high confidence in recent price knowledge
=== END MARKET DATA ===
"""
    else:
        market_data_section = f"""
=== NO REAL-TIME DATA PROVIDED ===
WARNING: Operating without real-time market data
RECOMMENDATION: Use extreme caution with pricing or recommend NO TRADES
All prices must be manually verified before execution
=== END MARKET DATA SECTION ===
"""

    # Hugo's Deep Research Prompt (adapted from Prompts.md)
    prompt = f"""SYSTEM MESSAGE:

You are a professional-grade portfolio analyst operating in Deep Research Mode. Your job is to reevaluate the portfolio and produce a complete action plan with exact orders. Optimize risk-adjusted return under strict constraints. Begin by restating the rules to confirm understanding, then deliver your research, decisions, and orders.

Core Rules:
- Budget discipline: no new capital beyond what is shown. Track cash precisely.
- Execution limits: full shares only. No options, shorting, leverage, margin, or derivatives. Long-only.
- Universe: primarily U.S. micro-caps under 300M market cap unless told otherwise. Respect liquidity, average volume, spread, and slippage.
- Risk control: respect provided stop-loss levels and position sizing. Flag any breaches immediately.
- Cadence: this is the weekly deep research window. You may add new names, exit, trim, or add to positions.
- Complete freedom: you have complete control to act in your best interest to generate alpha.

CRITICAL REQUIREMENT - REAL COMPANIES ONLY:
- You MUST only recommend actual, publicly traded companies with real ticker symbols
- DO NOT use fictional tickers like ABCD, EFGH, WXYZ, etc.
- Every ticker must be verifiable on major financial websites (Yahoo Finance, Google Finance, etc.)
- Use your knowledge of real U.S. micro-cap companies (<$300M market cap)
- If you cannot identify real micro-cap opportunities with confidence, recommend NO trades
- Example real micro-caps: CARV, BCDA, MVIS, SNDL, etc. (use actual current ones)

CRITICAL REQUIREMENT - MANDATORY REAL DATA USAGE:
- You MUST ONLY use the VERIFIED REAL-TIME MARKET DATA provided above
- ABSOLUTE REQUIREMENT: Only trade symbols that appear in the "VERIFIED CURRENT MARKET PRICES" section
- Use the EXACT prices shown in the verified data - no estimates, no guesses, no approximations
- If a symbol you want to trade is NOT in the verified list, recommend NO TRADE instead
- If real-time data shows any symbol as unavailable/failed, NEVER recommend trading that symbol
- Calculate position sizes using ONLY the verified prices: shares × verified_price = total_cost
- Use verified volume data to ensure sufficient liquidity before recommending trades
- ZERO TOLERANCE for fictional prices or unverified symbols
- If no real-time data is available, default recommendation should be NO TRADES

Deep Research Requirements:
- Reevaluate current holdings and consider new candidates.
- Build a clear rationale for every keep, add, trim, exit, and new entry.
- Provide exact order details for every proposed trade using ONLY real ticker symbols.
- Confirm liquidity and risk checks before finalizing orders.
- End with a short thesis review summary for next week.

Current Portfolio State as of {today}:

[ Holdings ]
{holdings_text}

[ Snapshot ]
Cash Balance: ${cash:,.2f}
Total Equity: ${total_equity:,.2f}
{market_data_section}

Constraints & Reminders To Enforce:
- Hard budget. Use only available cash shown above. No new capital.
- Full shares only. No options/shorting/margin/derivatives.
- Prefer U.S. micro-caps and respect liquidity.
- ONLY use real, verifiable ticker symbols - no fictional companies.
- CRITICAL: Use accurate, current stock prices - verify share price * quantity = realistic total cost
- Research recent trading ranges to ensure price accuracy before recommending trades
- If uncertain about current prices, recommend smaller position sizes or no trades
- Maintain or set stop-losses on all long positions.
- This is the weekly deep research window. You should present complete decisions and orders now.

Respond with ONLY a JSON object in this exact format:
{{
    "analysis": "Deep research analysis and market conditions",
    "trades": [
        {{
            "action": "buy",
            "ticker": "REAL_TICKER_ONLY",
            "shares": 100,
            "price": 25.50,
            "stop_loss": 20.00,
            "reason": "Deep research rationale with catalyst and liquidity note for this REAL company with VERIFIED CURRENT PRICING"
        }}
    ],
    "confidence": 0.8,
    "price_disclaimer": "I acknowledge that I may not have access to real-time pricing data and my price estimates may be inaccurate",
    "thesis_summary": "Brief thesis for next week monitoring"
}}

Only recommend trades with a confidence rate of at least {min_confidence:.1f}.
If no trades are recommended due to lack of suitable real opportunities, use an empty trades array.
REMEMBER: Every ticker symbol MUST be a real, publicly traded company.
FINAL WARNING: Use accurate current stock prices or recommend NO TRADES if uncertain about pricing.
IMPORTANT: All prices should be manually verified before executing any trades."""

    return prompt


def call_openai_api(prompt: str, api_key: str, model: str = "gpt-4") -> str:
    """Call OpenAI API and return response"""
    print (prompt)
    # sys.exit()
    if not HAS_OPENAI:
        raise ImportError("openai package not installed. Run: pip install openai")

    client = openai.OpenAI(api_key=api_key)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a professional portfolio analyst. Always respond with valid JSON in the exact format requested."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2500
        )
        print ("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        print( response.choices[0].message.content)
        print ("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        return response.choices[0].message.content
    except Exception as e:
        return f'{{"error": "API call failed: {e}"}}'


def parse_llm_response(response: str) -> Dict[str, Any]:
    """Parse LLM response and extract trading decisions"""
    try:
        # Clean the response first
        response = response.strip()

        # Try to extract JSON from response
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            json_str = json_match.group().strip()
            return json.loads(json_str)
        else:
            # Try to parse the entire response as JSON
            return json.loads(response)
    except json.JSONDecodeError as e:
        print(f"Failed to parse LLM response: {e}")
        print(f"Raw response: {response[:500]}...")  # Truncate long responses
        return {"error": "Failed to parse response", "raw_response": response}


def execute_automated_trades(trades: List[Dict[str, Any]], portfolio_df: pd.DataFrame, cash: float, market_data: Dict[str, Any] = None) -> Tuple[pd.DataFrame, float]:
    """Execute trades recommended by LLM with real-time data validation"""

    print(f"\n=== Executing {len(trades)} LLM-recommended trades ===")
    
    # Get verified symbols from market data for validation
    verified_symbols = set()
    verified_prices = {}
    
    if market_data and market_data.get('success') and market_data.get('data'):
        verified_symbols = set(market_data['data'].keys())
        verified_prices = {symbol: float(data['price']) for symbol, data in market_data['data'].items()}
        print(f"Verified symbols available: {', '.join(verified_symbols)}")
    else:
        print("WARNING: No verified market data available for trade validation")

    # Get price tolerance from config
    price_tolerance = config.PRICE_TOLERANCE_PERCENT if config else 0.05

    for trade in trades:
        action = trade.get('action', '').lower()
        ticker = trade.get('ticker', '').upper()
        shares = float(trade.get('shares', 0))
        price = float(trade.get('price', 0))
        stop_loss = float(trade.get('stop_loss', 0))
        reason = trade.get('reason', 'LLM recommendation')

        if action == 'buy':
            # Validate symbol and price against real-time data
            if verified_symbols and ticker not in verified_symbols:
                print(f"❌ BUY REJECTED: {ticker} - Symbol not in verified market data")
                print(f"   Available verified symbols: {', '.join(verified_symbols)}")
                continue
                
            if verified_prices and ticker in verified_prices:
                verified_price = verified_prices[ticker]
                price_diff = abs(price - verified_price) / verified_price if verified_price > 0 else float('inf')
                if price_diff > price_tolerance:
                    print(f"❌ BUY REJECTED: {ticker} - Price mismatch")
                    print(f"   LLM suggested: ${price:.2f}, Verified real price: ${verified_price:.2f} (diff: {price_diff:.1%})")
                    continue
                # Use verified price for execution
                execution_price = verified_price
            else:
                execution_price = price
                print(f"⚠️  WARNING: {ticker} - No price verification available")
            
            if shares > 0 and execution_price > 0 and ticker:
                cost = shares * execution_price
                if cost <= cash:
                    print(f"✅ BUY: {shares} shares of {ticker} at ${execution_price:.2f} (stop: ${stop_loss:.2f}) - {reason}")
                    if verified_prices and ticker in verified_prices:
                        print(f"   ✓ Price verified against real-time data: ${verified_prices[ticker]:.2f}")
                    # Here you would call the actual buy function from trading_script
                    # For now, just simulate the trade
                    cash -= cost
                    print(f"   Simulated: Cash reduced by ${cost:.2f}, new balance: ${cash:.2f}")
                else:
                    print(f"❌ BUY REJECTED: {ticker} - Insufficient cash (need ${cost:.2f}, have ${cash:.2f})")
            else:
                print(f"❌ INVALID BUY ORDER: {trade}")

        elif action == 'sell':
            # Validate symbol and price against real-time data
            if verified_symbols and ticker not in verified_symbols:
                print(f"❌ SELL REJECTED: {ticker} - Symbol not in verified market data")
                print(f"   Available verified symbols: {', '.join(verified_symbols)}")
                continue
                
            if verified_prices and ticker in verified_prices:
                verified_price = verified_prices[ticker]
                price_diff = abs(price - verified_price) / verified_price if verified_price > 0 else float('inf')
                if price_diff > price_tolerance:
                    print(f"❌ SELL REJECTED: {ticker} - Price mismatch")
                    print(f"   LLM suggested: ${price:.2f}, Verified real price: ${verified_price:.2f} (diff: {price_diff:.1%})")
                    continue
                # Use verified price for execution
                execution_price = verified_price
            else:
                execution_price = price
                print(f"⚠️  WARNING: {ticker} - No price verification available")
                
            if shares > 0 and execution_price > 0 and ticker:
                proceeds = shares * execution_price
                print(f"✅ SELL: {shares} shares of {ticker} at ${execution_price:.2f} - {reason}")
                if verified_prices and ticker in verified_prices:
                    print(f"   ✓ Price verified against real-time data: ${verified_prices[ticker]:.2f}")
                # Here you would call the actual sell function from trading_script
                # For now, just simulate the trade
                cash += proceeds
                print(f"   Simulated: Cash increased by ${proceeds:.2f}, new balance: ${cash:.2f}")
            else:
                print(f"❌ INVALID SELL ORDER: {trade}")

        elif action == 'hold':
            print(f"HOLD: {ticker} - {reason}")

        else:
            print(f"UNKNOWN ACTION: {action} for {ticker}")

    return portfolio_df, cash


def run_automated_trading(api_key: str, model: str = "gpt-4", data_dir: str = "Start Your Own", dry_run: bool = False, alpha_vantage_key: str = None):
    """Run the automated trading process"""

    print("=== Enhanced Hugo Automation Trading System ===")
    
    if config:
        print(config.get_portfolio_summary())

    # Set up data directory
    data_path = Path(data_dir)
    set_data_dir(data_path)

    # Always use portfolio_config.py for portfolio data and cash
    errors = []
    if config:
        errors = config.validate_configuration()
        if errors:
            print("⚠️ Configuration validation errors:")
            for error in errors:
                print(f"   {error}")
            print("Using config, but please fix the above errors!")
        portfolio_df, cash = create_portfolio_from_config()
    else:
        print("❌ Could not load portfolio_config.py - using empty portfolio and $10,000 cash fallback.")
        portfolio_df = pd.DataFrame(columns=["ticker", "shares", "stop_loss", "buy_price", "cost_basis"])
        cash = 10000.0

    # Calculate total equity (simplified)
    total_value = portfolio_df['cost_basis'].sum() if not portfolio_df.empty and 'cost_basis' in portfolio_df.columns else 0.0
    total_equity = cash + total_value

    print(f"Portfolio loaded: ${cash:,.2f} cash, ${total_equity:,.2f} total equity")
    
    # Fetch real-time market data if Alpha Vantage key is provided
    market_data = None
    if alpha_vantage_key:
        print("Fetching real-time market data...")
        market_data = fetch_current_market_data(portfolio_df, alpha_vantage_key)
        if market_data.get('success'):
            print(f"✅ Market data fetched successfully!")
            print(f"   Verified symbols: {market_data.get('symbols_fetched', 0)}")
            print(f"   Failed symbols: {market_data.get('symbols_failed', 0)}")
            if market_data.get('data'):
                print("   Real-time prices:")
                for symbol, data in list(market_data['data'].items())[:5]:  # Show first 5
                    print(f"     {symbol}: ${data.get('price', 'N/A')} ({data.get('change_percent', 'N/A')})")
                if len(market_data['data']) > 5:
                    print(f"     ... and {len(market_data['data']) - 5} more symbols")
        else:
            print(f"❌ Warning: Market data fetch failed - {market_data.get('error', 'Unknown error')}")
    else:
        print("No Alpha Vantage API key provided - using LLM knowledge only")

    # Generate prompt with market data
    prompt = generate_trading_prompt(portfolio_df, cash, total_equity, market_data)
    print(f"\nGenerated prompt ({len(prompt)} characters)")

    # Call LLM
    print("Calling LLM for trading recommendations...")
    response = call_openai_api(prompt, api_key, model)
    print(f"Received response ({len(response)} characters)")

    # Parse response
    parsed_response = parse_llm_response(response)

    if "error" in parsed_response:
        print(f"Error: {parsed_response['error']}")
        return

    # Display analysis
    analysis = parsed_response.get('analysis', 'No analysis provided')
    confidence = parsed_response.get('confidence', 0.0)
    trades = parsed_response.get('trades', [])

    print(f"\n=== LLM Analysis ===")
    print(f"Analysis: {analysis}")
    print(f"Confidence: {confidence:.1%}")
    print(f"Recommended trades: {len(trades)}")

    # Execute trades with market data validation
    if trades and not dry_run:
        portfolio_df, cash = execute_automated_trades(trades, portfolio_df, cash, market_data)
    elif trades and dry_run:
        print(f"\n=== DRY RUN - Would execute {len(trades)} trades ===")
        print("Note: In actual execution, all trades would be validated against real-time data")
        for trade in trades:
            ticker = trade.get('ticker', 'unknown')
            price = trade.get('price', 0)
            shares = trade.get('shares', 0)
            
            # Show validation status in dry run
            validation_status = ""
            if market_data and market_data.get('success') and market_data.get('data'):
                if ticker in market_data['data']:
                    real_price = float(market_data['data'][ticker]['price'])
                    if abs(price - real_price) / real_price <= 0.05:
                        validation_status = f" ✓ (Real price: ${real_price:.2f})"
                    else:
                        validation_status = f" ❌ (Real price: ${real_price:.2f}, LLM price: ${price:.2f})"
                else:
                    validation_status = " ❌ (Symbol not in verified data)"
            else:
                validation_status = " ⚠️ (No real-time validation available)"
            
            print(f"  {trade.get('action', 'unknown').upper()}: {shares} shares of {ticker} at ${price:.2f}{validation_status}")
    else:
        print("No trades recommended")

    # Save the LLM response for review
    response_file = data_path / "llm_responses.jsonl"
    try:
        with open(response_file, "a") as f:
            f.write(json.dumps({
                "timestamp": pd.Timestamp.now().isoformat(),
                "response": parsed_response,
                "raw_response": response
            }) + "\n")
    except Exception as e:
        print(f"Warning: Could not save response to {response_file}: {e}")

    print(f"\n=== Analysis Complete ===")
    print(f"Response saved to: {response_file}")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Simple Automated Trading")
    parser.add_argument("--api-key", help="OpenAI API key (or set OPENAI_API_KEY env var)")
    parser.add_argument("--alpha-vantage-key", help="Alpha Vantage API key for real-time data (or set ALPHA_VANTAGE_API_KEY env var)")
    parser.add_argument("--model", default="gpt-4", help="OpenAI model to use")
    parser.add_argument("--data-dir", default="Start Your Own", help="Data directory")
    parser.add_argument("--dry-run", action="store_true", help="Don't execute trades, just show recommendations")

    args = parser.parse_args()

    # Get API keys
    api_key = args.api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OpenAI API key required. Set OPENAI_API_KEY env var or use --api-key")
        return
        
    alpha_vantage_key = args.alpha_vantage_key or os.getenv("ALPHA_VANTAGE_API_KEY")
    if not alpha_vantage_key:
        print("Warning: No Alpha Vantage API key provided. Trading will use LLM knowledge only.")
        print("For better accuracy, set ALPHA_VANTAGE_API_KEY env var or use --alpha-vantage-key")

    # Run automated trading
    run_automated_trading(
        api_key=api_key,
        model=args.model,
        data_dir=args.data_dir,
        dry_run=args.dry_run,
        alpha_vantage_key=alpha_vantage_key
    )


if __name__ == "__main__":
    main()
