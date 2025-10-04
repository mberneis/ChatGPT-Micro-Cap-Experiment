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

try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


def generate_trading_prompt(portfolio_df: pd.DataFrame, cash: float, total_equity: float) -> str:
    """Generate Hugo's Deep Research trading prompt with current portfolio data"""

    # Format holdings
    if portfolio_df.empty:
        holdings_text = "No current holdings"
    else:
        holdings_text = portfolio_df.to_string(index=False)

    # Get current date
    today = last_trading_date().date().isoformat()

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

CRITICAL REQUIREMENT - ACCURATE CURRENT PRICES:
- You MUST use current, accurate stock prices for all recommendations
- DO NOT guess or estimate prices - use your most recent knowledge of actual market prices
- Many micro-cap stocks trade under $5, some under $1 - use realistic prices
- BCDA typically trades around $0.50-$2.00, MVIS around $0.50-$3.00 (use actual current prices)
- If you don't know the exact current price, be VERY conservative or recommend NO trades
- Verify that your price per share multiplied by shares equals a realistic total cost
- Double-check that prices make sense relative to the company's recent trading range
- Price accuracy is essential for proper position sizing and risk management
- When in doubt about pricing, recommend smaller positions or skip the trade entirely

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

Only recommend trades with a confidence rate of at least 80%.
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


def execute_automated_trades(trades: List[Dict[str, Any]], portfolio_df: pd.DataFrame, cash: float) -> Tuple[pd.DataFrame, float]:
    """Execute trades recommended by LLM"""

    print(f"\n=== Executing {len(trades)} LLM-recommended trades ===")

    for trade in trades:
        action = trade.get('action', '').lower()
        ticker = trade.get('ticker', '').upper()
        shares = float(trade.get('shares', 0))
        price = float(trade.get('price', 0))
        stop_loss = float(trade.get('stop_loss', 0))
        reason = trade.get('reason', 'LLM recommendation')

        if action == 'buy':
            if shares > 0 and price > 0 and ticker:
                cost = shares * price
                if cost <= cash:
                    print(f"BUY: {shares} shares of {ticker} at ${price:.2f} (stop: ${stop_loss:.2f}) - {reason}")
                    # Here you would call the actual buy function from trading_script
                    # For now, just simulate the trade
                    cash -= cost
                    print(f"  Simulated: Cash reduced by ${cost:.2f}, new balance: ${cash:.2f}")
                else:
                    print(f"BUY REJECTED: {ticker} - Insufficient cash (need ${cost:.2f}, have ${cash:.2f})")
            else:
                print(f"INVALID BUY ORDER: {trade}")

        elif action == 'sell':
            if shares > 0 and price > 0 and ticker:
                proceeds = shares * price
                print(f"SELL: {shares} shares of {ticker} at ${price:.2f} - {reason}")
                # Here you would call the actual sell function from trading_script
                # For now, just simulate the trade
                cash += proceeds
                print(f"  Simulated: Cash increased by ${proceeds:.2f}, new balance: ${cash:.2f}")
            else:
                print(f"INVALID SELL ORDER: {trade}")

        elif action == 'hold':
            print(f"HOLD: {ticker} - {reason}")

        else:
            print(f"UNKNOWN ACTION: {action} for {ticker}")

    return portfolio_df, cash


def run_automated_trading(api_key: str, model: str = "gpt-4", data_dir: str = "Start Your Own", dry_run: bool = False):
    """Run the automated trading process"""

    print("=== Automated Trading System ===")

    # Set up data directory
    data_path = Path(data_dir)
    set_data_dir(data_path)

    # Load current portfolio
    portfolio_file = data_path / "chatgpt_portfolio_update.csv"
    if portfolio_file.exists():
        portfolio_data, cash = load_latest_portfolio_state()
        if not isinstance(portfolio_data, pd.DataFrame):
            portfolio_df = pd.DataFrame(portfolio_data)
        else:
            portfolio_df = portfolio_data
    else:
        portfolio_df = pd.DataFrame(columns=["ticker", "shares", "stop_loss", "buy_price", "cost_basis"])
        cash = 10000.0  # Default starting cash

    # Calculate total equity (simplified)
    total_value = portfolio_df['cost_basis'].sum() if not portfolio_df.empty and 'cost_basis' in portfolio_df.columns else 0.0
    total_equity = cash + total_value

    print(f"Portfolio loaded: ${cash:,.2f} cash, ${total_equity:,.2f} total equity")

    # Generate prompt
    prompt = generate_trading_prompt(portfolio_df, cash, total_equity)
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

    # Execute trades
    if trades and not dry_run:
        portfolio_df, cash = execute_automated_trades(trades, portfolio_df, cash)
    elif trades and dry_run:
        print(f"\n=== DRY RUN - Would execute {len(trades)} trades ===")
        for trade in trades:
            print(f"  {trade.get('action', 'unknown').upper()}: {trade.get('shares', 0)} shares of {trade.get('ticker', 'unknown')} at ${trade.get('price', 0):.2f}")
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
    parser.add_argument("--model", default="gpt-4", help="OpenAI model to use")
    parser.add_argument("--data-dir", default="Start Your Own", help="Data directory")
    parser.add_argument("--dry-run", action="store_true", help="Don't execute trades, just show recommendations")

    args = parser.parse_args()

    # Get API key
    api_key = args.api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OpenAI API key required. Set OPENAI_API_KEY env var or use --api-key")
        return

    # Run automated trading
    run_automated_trading(
        api_key=api_key,
        model=args.model,
        data_dir=args.data_dir,
        dry_run=args.dry_run
    )


if __name__ == "__main__":
    main()
