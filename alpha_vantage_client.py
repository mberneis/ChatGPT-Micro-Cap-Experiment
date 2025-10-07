"""
Alpha Vantage MCP Client for Real-Time Stock Data
This module provides an interface to connect to the Alpha Vantage MCP server
and fetch real-time stock data for trading decisions.
"""

import asyncio
import json
import os
from typing import Dict, List, Optional, Any
import logging
from pathlib import Path

# HTTP client imports
import requests
from urllib.parse import urlencode

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AlphaVantageClient:
    """Direct client for Alpha Vantage API"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Alpha Vantage client
        
        Args:
            api_key: Alpha Vantage API key. If not provided, will try to get from environment
        """
        self.api_key = api_key or os.getenv('ALPHA_VANTAGE_API_KEY')
        if not self.api_key:
            raise ValueError("Alpha Vantage API key is required. Set ALPHA_VANTAGE_API_KEY environment variable or pass api_key parameter")
        
        self.base_url = "https://www.alphavantage.co/query"
        self.session = requests.Session()
        
    def connect(self):
        """Connect to the Alpha Vantage API (no-op for HTTP client)"""
        logger.info("Connected to Alpha Vantage API")
        return True
            
    def disconnect(self):
        """Disconnect from the API"""
        if self.session:
            self.session.close()
            logger.info("Disconnected from Alpha Vantage API")
                
    def get_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Get real-time quote for a stock symbol
        
        Args:
            symbol: Stock ticker symbol (e.g., 'AAPL')
            
        Returns:
            Dictionary containing quote data
        """
        try:
            # Alpha Vantage GLOBAL_QUOTE endpoint
            params = {
                'function': 'GLOBAL_QUOTE',
                'symbol': symbol.upper(),
                'apikey': self.api_key
            }
            
            response = self.session.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Check for API errors
            if 'Error Message' in data:
                return {"error": data['Error Message']}
            
            if 'Note' in data:
                return {"error": f"API limit reached: {data['Note']}"}
            
            # Extract quote data from Global Quote response
            quote_key = 'Global Quote'
            if quote_key not in data:
                return {"error": f"No quote data found for {symbol}"}
            
            quote_data = data[quote_key]
            
            # Transform to our standard format
            result = {
                '05. price': quote_data.get('05. price', 'N/A'),
                '09. change': quote_data.get('09. change', 'N/A'), 
                '10. change percent': quote_data.get('10. change percent', 'N/A'),
                '06. volume': quote_data.get('06. volume', 'N/A'),
                '07. latest trading day': quote_data.get('07. latest trading day', 'N/A')
            }
            
            logger.info(f"Retrieved quote for {symbol}: {result.get('05. price', 'N/A')}")
            return result
            
        except Exception as e:
            logger.error(f"Error fetching quote for {symbol}: {e}")
            return {"error": str(e)}
            
    def get_company_overview(self, symbol: str) -> Dict[str, Any]:
        """
        Get company overview data
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Dictionary containing company data
        """
        try:
            # Alpha Vantage OVERVIEW endpoint
            params = {
                'function': 'OVERVIEW',
                'symbol': symbol.upper(),
                'apikey': self.api_key
            }
            
            response = self.session.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Check for API errors
            if 'Error Message' in data:
                return {"error": data['Error Message']}
            
            if 'Note' in data:
                return {"error": f"API limit reached: {data['Note']}"}
            
            if not data or data.get('Symbol') != symbol.upper():
                return {"error": f"No company data found for {symbol}"}
            
            logger.info(f"Retrieved company overview for {symbol}")
            return data
            
        except Exception as e:
            logger.error(f"Error fetching company overview for {symbol}: {e}")
            return {"error": str(e)}
            
    def get_daily_prices(self, symbol: str, outputsize: str = "compact") -> Dict[str, Any]:
        """
        Get daily price data
        
        Args:
            symbol: Stock ticker symbol
            outputsize: 'compact' for last 100 days, 'full' for full history
            
        Returns:
            Dictionary containing daily price data
        """
        try:
            # Alpha Vantage TIME_SERIES_DAILY endpoint
            params = {
                'function': 'TIME_SERIES_DAILY',
                'symbol': symbol.upper(),
                'outputsize': outputsize,
                'apikey': self.api_key
            }
            
            response = self.session.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Check for API errors
            if 'Error Message' in data:
                return {"error": data['Error Message']}
            
            if 'Note' in data:
                return {"error": f"API limit reached: {data['Note']}"}
            
            logger.info(f"Retrieved daily prices for {symbol}")
            return data
            
        except Exception as e:
            logger.error(f"Error fetching daily prices for {symbol}: {e}")
            return {"error": str(e)}


class StockDataFetcher:
    """High-level interface for fetching stock data"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.client = AlphaVantageClient(api_key)
        
    def get_current_prices(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get current prices for multiple symbols
        
        Args:
            symbols: List of stock ticker symbols
            
        Returns:
            Dictionary mapping symbols to price data
        """
        self.client.connect()
        
        try:
            results = {}
            for symbol in symbols:
                quote = self.client.get_quote(symbol.upper())
                if "error" not in quote:
                    results[symbol] = {
                        "symbol": symbol,
                        "price": quote.get("05. price", "N/A"),
                        "change": quote.get("09. change", "N/A"),
                        "change_percent": quote.get("10. change percent", "N/A"),
                        "volume": quote.get("06. volume", "N/A"),
                        "timestamp": quote.get("07. latest trading day", "N/A")
                    }
                else:
                    results[symbol] = {"error": quote["error"]}
                    
            return results
            
        finally:
            self.client.disconnect()
            
    def get_stock_info(self, symbol: str) -> Dict[str, Any]:
        """
        Get comprehensive stock information including price and company data
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Dictionary with stock information
        """
        self.client.connect()
        
        try:
            # Get both quote and company overview
            quote = self.client.get_quote(symbol.upper())
            company = self.client.get_company_overview(symbol.upper())
            
            result = {"symbol": symbol.upper()}
            
            # Process quote data
            if "error" not in quote:
                result.update({
                    "current_price": quote.get("05. price", "N/A"),
                    "change": quote.get("09. change", "N/A"),
                    "change_percent": quote.get("10. change percent", "N/A"),
                    "volume": quote.get("06. volume", "N/A"),
                    "last_trading_day": quote.get("07. latest trading day", "N/A")
                })
            
            # Process company data
            if "error" not in company:
                result.update({
                    "market_cap": company.get("MarketCapitalization", "N/A"),
                    "pe_ratio": company.get("PERatio", "N/A"),
                    "sector": company.get("Sector", "N/A"),
                    "industry": company.get("Industry", "N/A"),
                    "description": company.get("Description", "N/A")[:200] + "..." if company.get("Description") else "N/A"
                })
            
            return result
            
        finally:
            self.client.disconnect()


# Synchronous wrapper functions for easier integration
def get_stock_prices_sync(symbols: List[str], api_key: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    """
    Synchronous function to get current stock prices
    
    Args:
        symbols: List of stock ticker symbols
        api_key: Alpha Vantage API key
        
    Returns:
        Dictionary mapping symbols to price data
    """
    fetcher = StockDataFetcher(api_key)
    return fetcher.get_current_prices(symbols)


def get_stock_info_sync(symbol: str, api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Synchronous function to get comprehensive stock information
    
    Args:
        symbol: Stock ticker symbol  
        api_key: Alpha Vantage API key
        
    Returns:
        Dictionary with stock information
    """
    fetcher = StockDataFetcher(api_key)
    return fetcher.get_stock_info(symbol)


# Example usage and testing
if __name__ == "__main__":
    import sys
    
    # Test the client with IBM as it's always available in demo mode
    test_symbols = ["IBM"]
    
    try:
        print("Testing Alpha Vantage Direct API Client...")
        
        # Try with environment variable first
        api_key = os.getenv('ALPHA_VANTAGE_API_KEY')
        if not api_key:
            print("No API key found, using demo endpoint...")
            api_key = "demo"  # Alpha Vantage demo key
        
        prices = get_stock_prices_sync(test_symbols, api_key)
        
        print("\n=== Stock Prices ===")
        for symbol, data in prices.items():
            if "error" not in data:
                print(f"✅ {symbol}: ${data['price']} ({data['change_percent']})")
            else:
                print(f"❌ {symbol}: Error - {data['error']}")
        
        # Test if we got valid data
        success = any("error" not in data for data in prices.values())
        if success:
            print("\n🎉 Direct API integration is working!")
            print("Now get your free API key at: https://www.alphavantage.co/support/#api-key")
        else:
            print("\n⚠️  API integration needs debugging or valid API key")
                
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print("Please check your internet connection or get an API key")
        sys.exit(1)
