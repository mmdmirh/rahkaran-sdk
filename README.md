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
    client = RahkaranClient("https://your-rahkaran-host/sgXg/xXXXXXXXX",
                           username="your_user",
                           password="your_password",
                           verify_ssl=False)  # some instances use self-signed certs
    print("Logged in successfully!")
except Exception as e:
    print(f"Login failed: {e}")

# OR with existing Cookies
# client = RahkaranClient("https://your-rahkaran-host", cookies={...})

# 2. Call APIs
shops = client.get_retail_shops()
warehouses = client.get_warehouses()                 # flat list across shops
products = client.get_all_products(store_id=9)      # handles pagination
stock = client.get_remaining(store_id=9, product_id=44)
price = client.get_price(retail_shop_id=6, product_id=44, unit_id=279)

# 3. Finalize a sale: register a Sales Invoice (ثبت فاکتور فروش)
policies = client.get_settlement_policies()
customer_id = client.ensure_customer(
    national_id="1234567890", first_name="علی", last_name="علوی",
    mobile="09120000000", city="تهران", address="...")
result = client.create_sales_invoice(
    customer_id=customer_id,
    store_id=9,                 # warehouse/store ID
    settlement_policy_id=8,     # from get_settlement_policies()
    items=[{"productId": 44, "unitId": 279, "quantity": 2, "fee": 100000}],
    invoice_id=555,             # your website-side invoice/order number
)
```

## Changelog

### 0.2.0
- Fixed `Remaining` and `Price` endpoints to use `ESales.svc` per the official
  retail web services documentation (previous URLs were guessed and wrong).
- Fixed missing `URLs.GET_PRODUCTS` (made `get_products()` raise `AttributeError`).
- `create_sales_invoice` now sends the full documented payload (`Id`, `date`,
  per-item and total `price`/`netPrice`, `policies`).
- New APIs: `get_settlement_policies`, `calculate_policies`, `get_invoice(s)`,
  `get_part_by_code`, `get_warehouses`, `get_all_products` (paginated),
  `get_batch_prices`, `ensure_customer`.
- New `verify_ssl` constructor flag.
- `authenticate()` now patches `rahkaran_auth` to resolve the Node.js binary on
  hosts where it is not on PATH (e.g. Azure App Service), installing it via
  `nodeenv` as a last resort.
