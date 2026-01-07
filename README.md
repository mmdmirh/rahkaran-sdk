# Rahkaran Python Client

A robust Python client library for interacting with the Rahkaran ERP System.

## Features
- **Authentication**: Integrated with `rahkaran_login_webservice`.
- **APIs**: Voucher Processing, Retail (Shops, Products, Prices), and Inventory.
- **Error Handling**: Typed exceptions (`RahkaranAuthError`, `RahkaranServerError`).

## Installation

1. Clone the repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Install this package:
   ```bash
   pip install -e .
   ```

## Usage

```python
from rahkaran_client import RahkaranClient

# With Cookies
client = RahkaranClient("https://your-rahkaran-host", cookies={...})

# Or with Username/Password (requires auth lib setup)
# client = RahkaranClient("https://your-rahkaran-host", username="user", password="pwd")

# 1. Get Voucher Specs
spec = client.get_voucher_specification(2)
print(spec)

# 2. Register Voucher
payload = {...}
try:
    result = client.register_voucher(payload)
except Exception as e:
    print(f"Error: {e}")
```
