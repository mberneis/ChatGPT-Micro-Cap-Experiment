# Easy Portfolio Setup Guide

## 🎯 **Quick Start - Editing Your Portfolio**

### **Step 1: Edit your portfolio settings**
Open `portfolio_config.py` in any text editor and modify:

```python
# Change your cash balance
CASH_BALANCE = 5000.00  # Set to your actual cash

# Update your stock holdings
CURRENT_HOLDINGS = {
    "VTSI": {
        "shares": 557,        # How many shares you own
        "buy_price": 5.44,    # What you paid per share
        "stop_loss": 4.57     # Your stop loss price
    },
    "CRWS": {
        "shares": 1030,
        "buy_price": 2.85,
        "stop_loss": 2.46
    }
    # Add more stocks by copying the format above
}
```

### **Step 2: Set your API keys**
Either in the config file:
```python
ALPHA_VANTAGE_API_KEY = "your_key_here"  # Your Alpha Vantage key
```

Or as environment variables (recommended):
```bash
export ALPHA_VANTAGE_API_KEY=your_key_here
export OPENAI_API_KEY=your_openai_key_here
```

### **Step 3: Run your trading system**
```bash
python hugo_automation_v2.py --dry-run  # Test mode
python hugo_automation_v2.py            # Live trading
```

## 📝 **Common Portfolio Updates**

### **Adding a New Stock**
```python
CURRENT_HOLDINGS = {
    "VTSI": {"shares": 557, "buy_price": 5.44, "stop_loss": 4.57},
    "CRWS": {"shares": 1030, "buy_price": 2.85, "stop_loss": 2.46},
    "MVIS": {"shares": 500, "buy_price": 1.20, "stop_loss": 1.00}  # NEW
}
```

### **Removing a Stock**
Just delete the entire entry:
```python
CURRENT_HOLDINGS = {
    "VTSI": {"shares": 557, "buy_price": 5.44, "stop_loss": 4.57}
    # CRWS removed
}
```

### **Starting Fresh**
```python
CASH_BALANCE = 10000.00
CURRENT_HOLDINGS = {}  # Empty portfolio
```

### **After Buying/Selling Stocks**
Update both cash and holdings:
```python
CASH_BALANCE = 3500.00  # Reduced after buying more
CURRENT_HOLDINGS = {
    "VTSI": {"shares": 757, "buy_price": 5.44, "stop_loss": 4.57},  # Added 200 shares
    "CRWS": {"shares": 1030, "buy_price": 2.85, "stop_loss": 2.46}
}
```

## 🔧 **Useful Commands**

### **Test Your Configuration**
```bash
python portfolio_config.py              # Test config file
python hugo_automation_v2.py --test-config  # Test with trading system
```

### **Run Trading System**
```bash
python hugo_automation_v2.py --dry-run  # See what it would do
python hugo_automation_v2.py            # Actually execute trades
```

### **Check Your Portfolio**
```python
# In Python terminal:
import portfolio_config
print(portfolio_config.get_portfolio_summary())
```

## ⚙️ **Advanced Settings You Can Modify**

```python
# Research symbols (stocks to get data for)
RESEARCH_SYMBOLS = ["MVIS", "SNDL", "BCDA", "CARV"]

# Trading preferences
MIN_CONFIDENCE_THRESHOLD = 0.8  # Only execute trades with 80%+ confidence
DEFAULT_STOP_LOSS_PERCENT = 0.15  # 15% stop loss
MAX_POSITION_SIZE_PERCENT = 0.25  # Max 25% per position

# API settings
MAX_SYMBOLS_PER_BATCH = 12  # Limit for API rate limits
PRICE_TOLERANCE_PERCENT = 0.05  # Allow 5% price difference
```

## 🚨 **Important Notes**

1. **Save backup of your config** before major changes
2. **Test with --dry-run** before live trading
3. **Validate config** shows any errors in your setup
4. **Real-time data requires** Alpha Vantage API key
5. **All prices** will be validated against real market data

## 🔄 **Migration from Old System**

Your old CSV files in `Start Your Own/` are still there as backup. The new system reads from `portfolio_config.py` instead, giving you much easier control over your portfolio settings.

**No more editing CSV files!** 🎉