# Rahkaran Python Client

A robust Python client library for interacting with the Rahkaran ERP System.

## Features
- **Authentication**: Integrated with `rahkaran_login_webservice`.
- **APIs**: Voucher Processing, Retail (Shops, Products, Prices), and Inventory.
- **Error Handling**: Typed exceptions (`RahkaranAuthError`, `RahkaranServerError`).

## Installation

1. Clone the repository.
2. Install dependencies (including the authentication library):
   ```bash
   pip install -r requirements.txt
   ```
3. Install this package:
   ```bash
   pip install -e .
   ```
   
   *Alternatively, install directly from GitHub (ensure prerequisites are installed):*
   ```bash
   pip install git+https://github.com/mmdmirh/Rahkaran_login_webservice.git#egg=rahkaran-auth
   pip install git+https://github.com/mmdmirh/rahkaran-sdk.git
   ```

## Usage

```python
from rahkaran_client import RahkaranClient

# 1. Login with Username/Password (Requires rahkaran-auth installed)
# The client will automatically handle the handshake and session cookies.
try:
    client = RahkaranClient("https://your-rahkaran-host", 
                           username="your_user", 
                           password="your_password")
    print("Logged in successfully!")
except Exception as e:
    print(f"Login failed: {e}")

# OR with existing Cookies
# client = RahkaranClient("https://your-rahkaran-host", cookies={...})

# 2. Call APIs
try:
    shops = client.get_retail_shops()
    print(shops)
except Exception as e:
    print(f"Error: {e}")
```
