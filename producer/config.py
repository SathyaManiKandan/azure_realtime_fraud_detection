# simulator/config.py

# ── Simulation settings ───────────────────────────────────────────
FRAUD_RATE           = 0.08
TRANSACTIONS_PER_SEC = 2
TOTAL_CUSTOMERS      = 500

# ── Fraud thresholds (used internally only — not in output) ───────
HIGH_AMOUNT_THRESHOLD = 50000
ODD_HOUR_START        = 23
ODD_HOUR_END          = 4

# ── Data pools ────────────────────────────────────────────────────
NORMAL_MERCHANTS = [
    "BigBazaar", "Swiggy", "Zomato", "Amazon", "Flipkart",
    "Reliance Fresh", "DMart", "BookMyShow", "Ola", "Uber",
    "PhonePe", "GooglePay", "IRCTC", "MakeMyTrip", "Myntra",
    "Nykaa", "Meesho", "Blinkit", "Zepto", "Cred"
]

SUSPICIOUS_MERCHANTS = [
    "CASINO", "CRYPTO_EXCHANGE", "UNKNOWN",
    "OFFSHORE_BETTING", "DARK_MARKET"
]

NORMAL_LOCATIONS = [
    "Mumbai", "Bangalore", "Chennai", "Delhi", "Hyderabad",
    "Pune", "Kolkata", "Ahmedabad", "Jaipur", "Surat",
    "Mangalore", "Mysore", "Coimbatore", "Kochi", "Nagpur"
]

FOREIGN_LOCATIONS = [
    "Dubai", "Singapore", "London", "New York", "Zurich",
    "Cayman Islands", "Hong Kong", "Panama City", "Macau"
]

TXN_TYPES = ["UPI", "NEFT", "IMPS", "ATM", "POS", "online"]