import time
import requests
import logging
from datetime import datetime
from typing import Optional, Dict, List, Any, Union
from .urls import URLs
from .auth_compat import patch_rahkaran_auth
from .exceptions import RahkaranError, RahkaranAuthError, RahkaranServerError, RahkaranClientError

# Try importing the user's auth library.
try:
    from rahkaran_auth import RahkaranAuth
except ImportError:
    RahkaranAuth = None

logger = logging.getLogger(__name__)

# Rahkaran expects dates in this format, e.g. "Thursday, 09 July 2020"
RAHKARAN_DATE_FORMAT = "%A, %d %B %Y"

class RahkaranClient:
    """
    Client for interacting with Rahkaran ERP APIs.
    """

    def __init__(self, base_url: str, username: Optional[str] = None, password: Optional[str] = None, cookies: Optional[Dict] = None, verify_ssl: bool = True):
        """
        Initialize the client.

        Args:
            base_url: The root URL (e.g., https://example.rahkaran.ir/sgXg/xXXXXXXXX)
            username: Username for auth (if cookies not provided)
            password: Password for auth
            cookies: Pre-authenticated cookies (optional)
            verify_ssl: Set False to skip TLS certificate verification (some
                        on-premise Rahkaran instances use self-signed certs).
        """
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "RahkaranPythonClient/1.0",
            "Accept": "application/json"
        })

        if not verify_ssl:
            self.session.verify = False
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        if cookies:
            self.session.cookies.update(cookies)
        elif username and password:
            self.authenticate(username, password)
        else:
            logger.warning("Client initialized without credentials or cookies.")

    def authenticate(self, username, password):
        """
        Authenticates using the external 'rahkaran-auth' library.
        """
        if not RahkaranAuth:
            raise ImportError("rahkaran-auth library not found. Please install it to use username/password authentication.")

        # Make rahkaran_auth's node-based RSA encryption work on hosts where
        # the node binary is not on PATH (e.g. Azure App Service).
        patch_rahkaran_auth()

        try:
            logger.info(f"Authenticating user {username}...")
            auth = RahkaranAuth()
            result = auth.login(self.base_url, username, password)
            
            if result.get("success"):
                self.session.cookies.update(result.get("cookies", {}))
                logger.info("Authentication successful.")
            else:
                error_msg = result.get("error", "Unknown login error")
                raise RahkaranAuthError(f"Authentication failed: {error_msg}")
                
        except Exception as e:
            # Re-raise standard auth errors, wrap others
            if isinstance(e, RahkaranAuthError):
                raise e
            raise RahkaranAuthError(f"Authentication process failed: {e}")

    def _request(self, method: str, endpoint: str, time_out: int = 30, **kwargs) -> Dict[str, Any]:
        """Internal request handler with error mapping."""
        url = URLs.build_url(self.base_url, endpoint)
        
        try:
            response = self.session.request(method, url, timeout=time_out, **kwargs)
            
            if response.status_code == 401 or response.status_code == 403:
                raise RahkaranAuthError(f"Unauthorized ({response.status_code}): {response.text}")
            elif response.status_code >= 500:
                raise RahkaranServerError(f"Server Error ({response.status_code}): {response.text}")
            elif response.status_code >= 400:
                raise RahkaranClientError(f"Client Error ({response.status_code}): {response.text}")

            try:
                # Handle void responses or empty queries
                if not response.content:
                    return {}
                
                # Check for BOM and decode if necessary
                text = response.text
                if text.startswith(u'\ufeff'):
                    text = text.encode('utf-8')[3:].decode('utf-8')
                
                # Standard json decode
                try:
                    return response.json()
                except ValueError:
                    # Fallback to manual parsing if .json() failed (e.g. BOM issues not caught)
                    import json
                    return json.loads(text.strip())

            except ValueError:
                # Some endpoints return plain text or HTML on error despite 200 OK
                return {"raw_text": response.text}

        except requests.RequestException as e:
            raise RahkaranError(f"Network error: {e}")

    # --- Logistics / Voucher APIs ---

    def get_voucher_specification(self, code: int) -> Dict:
        """Fetch voucher specification by internal code."""
        return self._request("GET", URLs.GET_VOUCHER_SPEC, params={"code": code})

    def is_voucher_exists(self, voucher_id: int) -> Dict:
        """Check if a voucher exists (Behavior check)."""
        # Based on investigation, typically checks valid combinations
        return self._request("POST", URLs.IS_VOUCHER_EXISTS, json={"voucherID": voucher_id})

    def get_inventory_vouchers_by_reference(self, reference_type: int, ref_id: int) -> List[Dict]:
        """
        Fetch vouchers by reference.
        Args:
            reference_type: 1 (Returns), 2 (Standard/Source)
            ref_id: The ID of the reference document.
        """
        payload = {"ReferenceType": reference_type}
        if reference_type == 1:
            payload["ReturnableVoucherRef"] = ref_id
        else:
            payload["ReferenceRef"] = ref_id
            
        return self._request("POST", URLs.GET_BY_REF, json=payload)

    def register_voucher(self, voucher_payload: Dict) -> Dict:
        """
        Register a new voucher.
        Note: Wraps payload in 'voucher' if not present, as required by endpoint.
        """
        # Ensure wrapper per investigation
        if "voucher" not in voucher_payload:
            final_payload = {"voucher": voucher_payload}
        else:
            final_payload = voucher_payload

        return self._request("POST", URLs.REGISTER_VOUCHER, json=final_payload)

    def create_inventory_voucher(self, 
                                 store_id: int, 
                                 voucher_type: int, 
                                 items: List[Dict], 
                                 date: Optional[str] = None, 
                                 description: str = "") -> Dict:
        """
        High-level helper to create an inventory voucher from product items.
        
        Args:
            store_id: The ID of the warehouse/store (StockRef).
            voucher_type: The internal ID for the voucher type (VoucherTypeRef).
            items: List of item dictionaries. Each should have:
                   - 'partId': Mapping to 'PartRef'
                   - 'quantity': The quantity to register
                   - 'unitId': (Optional) Mapping to 'UnitRef'. Defaults to 1.
            date: (Optional) Voucher date.
            description: (Optional) Voucher description.
        """
        voucher_items = []
        for item in items:
            voucher_items.append({
                "PartRef": item.get("partId"),
                "Quantity": item.get("quantity", 0),
                "UnitRef": item.get("unitId") or item.get("units", [{}])[0].get("id", 1),
                "TrackingFactors": item.get("trackingFactors", [])
            })
            
        voucher_payload = {
            "VoucherTypeRef": voucher_type,
            "StockRef": store_id,
            "VoucherItems": voucher_items,
            "Description": description
        }
        
        if date:
            voucher_payload["Date"] = date
            
        return self.register_voucher(voucher_payload)

    # --- Sales APIs ---

    def register_invoice(self, invoice_payload: Dict) -> Dict:
        """Register a Sales Invoice in Rahkaran (POST ESales.svc/Invoice)."""
        return self._request("POST", URLs.REGISTER_INVOICE, json=invoice_payload)

    def get_invoice(self, invoice_id: int) -> Dict:
        """Fetch a single registered Sales Invoice by its ID."""
        return self._request("GET", URLs.GET_INVOICE, params={"Id": invoice_id})

    def get_invoices(self, customer_id: int) -> Dict:
        """Fetch the Sales Invoices registered for a customer."""
        return self._request("GET", URLs.GET_INVOICES, params={"Customer ID": customer_id})

    def register_sales_order(self, order_payload: Dict) -> Dict:
        """Register a Sales Order in Rahkaran."""
        return self._request("POST", URLs.REGISTER_SALES_ORDER, json=order_payload)

    def get_settlement_policies(self, settlement_id: Optional[int] = None) -> Dict:
        """
        Fetch the settlement policies (انواع دریافت فاکتور) defined in Rahkaran,
        e.g. Cash, EReceipt. Used as `settlementPolicyId` when registering invoices.
        """
        params = {}
        if settlement_id is not None:
            params["Settlement ID"] = settlement_id
        return self._request("GET", URLs.GET_SETTLEMENT_POLICIES, params=params)

    def calculate_policies(self, document: Dict) -> Dict:
        """
        Calculate the sales policies (سیاست های فروش, e.g. discounts) applicable
        to an invoice document before registering it.
        """
        return self._request("POST", URLs.CALCULATE_POLICY, json=document)

    def create_sales_invoice(self,
                             customer_id: int,
                             store_id: int,
                             settlement_policy_id: int,
                             items: List[Dict],
                             document_pattern_id: int = 1,
                             date: Optional[str] = None,
                             currency_id: int = 1,
                             invoice_id: int = 0) -> Dict:
        """
        Helper to create a Sales Invoice from a list of products.

        Builds the payload documented in "مستند فنی وب سرویس های خرده فروشی"
        (ثبت فاکتور فروش - Invoice, POST).

        Args:
            customer_id: The Rahkaran Customer ID.
            store_id: The Store (warehouse) ID used for the invoice and its items.
            settlement_policy_id: The ID of the settlement policy (e.g., Cash, POS).
            items: List of item dictionaries. Each should have:
                   - 'productId': The Rahkaran Product ID.
                   - 'quantity': Quantity to sell.
                   - 'unitId': (Optional) Unit ID. Defaults to 1.
                   - 'fee': (Optional) Unit Price (Fee).
                   - 'price'/'netPrice': (Optional) Line totals. Default fee*quantity.
            document_pattern_id: (Optional) Document pattern ID. Defaults to 1.
            date: (Optional) Invoice date string. Defaults to today, formatted
                  as Rahkaran expects (e.g. "Thursday, 09 July 2020").
            currency_id: (Optional) Currency ID. Defaults to 1 (IRR).
            invoice_id: (Optional) Website-side invoice identifier ('Id' field).
        """
        invoice_items = []
        total_price = 0
        total_net_price = 0
        for item in items:
            quantity = item.get("quantity", 0)
            fee = item.get("fee", 0)
            price = item.get("price", fee * quantity)
            net_price = item.get("netPrice", price)
            total_price += price
            total_net_price += net_price
            invoice_items.append({
                "productId": item.get("productId") or item.get("id"),
                "unitId": item.get("unitId") or item.get("units", [{}])[0].get("id", 1),
                "quantity": quantity,
                "storeId": item.get("storeId", store_id),
                "fee": fee,
                "price": price,
                "netPrice": net_price,
                "policies": item.get("policies", [])
            })

        payload = {
            "Id": invoice_id,
            "date": date or datetime.now().strftime(RAHKARAN_DATE_FORMAT),
            "customerId": customer_id,
            "storeId": store_id,
            "settlementPolicyId": settlement_policy_id,
            "documentPatternId": document_pattern_id,
            "currencyId": currency_id,
            "price": total_price,
            "netPrice": total_net_price,
            "items": invoice_items,
            "policies": []
        }

        return self.register_invoice(payload)

    # --- Customer and Address APIs ---

    def create_customer(self, customer_data: Dict) -> Dict:
        """Register a new customer in Rahkaran."""
        return self._request("POST", URLs.CUSTOMER, json=customer_data)

    def get_customers(self, 
                      from_: int = 0, 
                      count: int = 100, 
                      name: Optional[str] = None, 
                      national_id: Optional[str] = None, 
                      mobile: Optional[str] = None) -> Dict:
        """
        Retrieve a list of customers with optional filters.
        
        Args:
            from_: Starting index (pagination).
            count: Number of records to fetch.
            name: (Optional) Filter by customer name.
            national_id: (Optional) Filter by national ID.
            mobile: (Optional) Filter by mobile number.
        """
        params = {
            "From": from_, 
            "Number of Records": count
        }
        if name:
            params["Name"] = name
        if national_id:
            params["National ID"] = national_id
        if mobile:
            params["Mobile"] = mobile
            
        return self._request("GET", URLs.GET_CUSTOMERS, params=params)

    def get_places(self) -> Dict:
        """
        Retrieve a list of countries and cities (Places) from Rahkaran.
        Useful for finding CityId for customer addresses.
        """
        return self._request("GET", URLs.GET_PLACES)

    def add_customer_address(self, customer_id: int, address_data: Dict) -> Dict:
        """
        Add an address to an existing customer.
        
        Args:
            customer_id: The ID of the customer.
            address_data: A dictionary containing:
                - 'CityId' (Required)
                - 'Detail' (Required)
                - 'Name' (Optional)
                - 'Isdefault' (Boolean)
        """
        payload = {
            "Customer": customer_id,
            "AddressData": address_data
        }
        return self._request("POST", URLs.ADDRESS, json=payload)

    def register_customer(self,
                          first_name: str,
                          last_name: str,
                          national_code: str,
                          mobile: str,
                          city: Union[int, str],
                          address_detail: str,
                          gender: int = 0,
                          birth_date: Optional[str] = None,
                          address_name: Optional[str] = None) -> Dict:
        """
        High-level helper to register a customer with basic details and a mandatory address.
        
        Args:
            first_name: Customer's first name.
            last_name: Customer's last name.
            national_code: Customer's national identity code.
            mobile: Mobile phone number.
            city: Either the integer City ID or the City Name string (e.g., "تهران").
            address_detail: Full address detail (Required).
            gender: 0 for unknown/unspecified, 1 for Male, 2 for Female.
            birth_date: (Optional) "YYYY-MM-DD".
            address_name: (Optional) A name for the address (e.g., "Home", "Office").
        
        Returns:
            A dictionary containing the results of both operations.
        """
        # 0. Handle City Name lookup
        city_id = None
        if isinstance(city, str):
            places_res = self.get_places()
            places = places_res.get("result", [])
            for place in places:
                if place.get("type") == "City" and place.get("name") == city:
                    city_id = place.get("id")
                    break
            
            if not city_id:
                raise ValueError(f"City '{city}' not found in Rahkaran. Please check the name or use an ID.")
        else:
            city_id = city

        # 1. Create the customer
        payload = {
            "FirstName": first_name,
            "Lastname": last_name,
            "Nationalcode": national_code,
            "mobile": mobile,
            "Gender": gender
        }
        if birth_date:
            payload["Birthdate"] = birth_date
            
        reg_result = self.create_customer(payload)
        
        # 2. Add address if registration was successful
        customer_id = reg_result.get("result")
        address_result = None
        
        if customer_id and customer_id > 0:
            address_data = {
                "CityId": city_id,
                "Detail": address_detail,
                "Isdefault": True
            }
            if address_name:
                address_data["Name"] = address_name
                
            address_result = self.add_customer_address(customer_id, address_data)
            
        return {
            "registration": reg_result,
            "address": address_result,
            "result": customer_id # For backward compatibility
        }

    def ensure_customer(self,
                        national_id: str,
                        first_name: str,
                        last_name: str,
                        mobile: str,
                        city: Union[int, str],
                        address: str) -> Optional[int]:
        """
        Ensure a customer exists in Rahkaran, looked up by National ID.
        Registers a new customer (with address) when none is found.

        Returns:
            The Rahkaran Customer ID, or None if registration failed.
        """
        search_res = self.get_customers(national_id=national_id)
        customers = search_res.get("result") or []
        if customers:
            customer = customers[0]
            customer_id = customer.get("id")
            logger.info(f"Customer found in Rahkaran: {customer_id}")

            # The national ID is the authoritative key. If the mobile on file
            # in Rahkaran differs (the customer changed their phone), keep
            # using the existing customer and only log the mismatch — the
            # ESales web services expose no customer-update endpoint.
            existing_mobile = str(customer.get("mobile") or "")
            if mobile and existing_mobile and existing_mobile[-10:] != str(mobile)[-10:]:
                logger.warning(
                    f"Rahkaran customer {customer_id} (national ID {national_id}) has mobile "
                    f"'{existing_mobile}' but the caller provided '{mobile}'. Using the existing "
                    f"customer; update the mobile in Rahkaran manually if needed."
                )
            return customer_id

        logger.info(f"Customer not found. Registering new customer: {national_id}")
        reg_res = self.register_customer(
            first_name=first_name,
            last_name=last_name,
            national_code=national_id,
            mobile=mobile,
            city=city,
            address_detail=address
        )
        return reg_res.get("result")

    # --- Material Management APIs ---

    def get_tracking_factors(self) -> Dict:
        """Fetch tracking factors (e.g. Batch Numbers, Serial parameters)."""
        return self._request("GET", URLs.GET_TRACKING_FACTORS)

    def get_part_by_code(self, code: str) -> Dict:
        """Fetch detailed part/product information by its code."""
        from urllib.parse import urlsplit
        parts = urlsplit(self.base_url)
        headers = {
            "Referer": f"{self.base_url}/Login.aspx",
            "Origin": f"{parts.scheme}://{parts.netloc}"
        }
        return self._request("GET", URLs.GET_PART_BY_CODE, params={"code": code}, headers=headers)

    # --- Retail APIs ---

    def get_retail_shops(self, with_stores: bool = True) -> Dict:
        """
        Fetch available retail shops.
        Args:
           with_stores: If true, includes stores in the response.
        """
        return self._request("GET", URLs.GET_RETAIL_SHOPS, params={"withStores": str(with_stores).lower()})

    def get_warehouses(self) -> List[Dict]:
        """
        Fetch all warehouses (stores) across retail shops as a flat list of
        {id, name, code, shop_name, shop_id} dictionaries.
        """
        shops_data = self.get_retail_shops()
        warehouses = []
        for shop in shops_data.get('result') or []:
            shop_name = shop.get('name', '')
            for store in shop.get('stores') or []:
                warehouses.append({
                    'id': store['id'],
                    'name': store.get('name', ''),
                    'code': store.get('code', ''),
                    'shop_name': shop_name,
                    'shop_id': shop.get('id')
                })
        return warehouses

    def get_products(self, store_id: int, from_: int = 0, number_of_records: int = 600, time_out: int = 30) -> Dict:
        """Fetch products for a specific store with pagination."""
        params = {
            "storeId": store_id,
            "from": from_,
            "numberOfRecords": number_of_records
        }
        return self._request("GET", URLs.GET_PRODUCTS, params=params, time_out=time_out)

    def get_all_products(self,
                         store_id: int,
                         offset: int = 0,
                         batch_size: int = 600,
                         time_limit: Optional[float] = None,
                         max_records: Optional[int] = None) -> Dict:
        """
        Fetch products for a store, iterating over pages with optional time and
        record budgets so callers can resume from `metadata.next_offset`.

        Returns:
            {"result": [...products...],
             "metadata": {"isSuccessfull", "total_count", "next_offset", "has_more"}}
        """
        all_products = []
        current_offset = offset
        start_time = time.time()
        has_more = False

        logger.info(f"Fetching products for Store {store_id} (Offset: {offset}, Batch: {batch_size})")

        while True:
            if time_limit and (time.time() - start_time > time_limit):
                logger.info("Time limit reached. Halting fetch to save progress.")
                has_more = True
                break

            if max_records and len(all_products) >= max_records:
                logger.info(f"Max records limit ({max_records}) reached. Halting fetch to save progress.")
                has_more = True
                break

            try:
                # Call the endpoint directly (not self.get_products) so that
                # subclasses overriding get_products cannot break pagination.
                response = self._request("GET", URLs.GET_PRODUCTS, params={
                    "storeId": store_id,
                    "from": current_offset,
                    "numberOfRecords": batch_size
                })
                items = response.get('result') or []
                if not items:
                    break

                all_products.extend(items)
                current_offset += len(items)
                logger.info(f"Fetched {len(items)} items (Total: {len(all_products)})")

                if len(items) < batch_size:
                    break

            except Exception as e:
                logger.error(f"Error fetching products batch starting at {current_offset}: {e}")
                has_more = True  # Treat as a temporary stop so callers keep what was fetched
                break

        return {
            "result": all_products,
            "metadata": {
                "isSuccessfull": True,
                "total_count": len(all_products),
                "next_offset": current_offset,
                "has_more": has_more
            }
        }

    def get_remaining(self, store_id: int, product_id: int, tracking_factor_id: Optional[int] = None) -> Dict:
        """Fetch remaining stock for a product in a store (POST ESales.svc/Remaining)."""
        payload = {"storeId": store_id, "productId": product_id}
        if tracking_factor_id is not None:
            payload["trackingFactorId"] = tracking_factor_id
        return self._request("POST", URLs.GET_REMAINING, json=payload)

    def get_price(self, retail_shop_id: int, product_id: int, unit_id: int, customer_id: Optional[int] = None, quantity: float = 1) -> Dict:
        """
        Fetch the approved sale price for a product/unit in a retail shop
        (POST ESales.svc/Price).
        """
        items = [{
            "itemId": product_id,
            "productId": product_id,
            "unitId": unit_id,
            "quantity": quantity
        }]
        return self.get_batch_prices(retail_shop_id, items, customer_id=customer_id)

    def get_batch_prices(self, retail_shop_id: int, items: List[Dict], customer_id: Optional[int] = None) -> Dict:
        """
        Fetch prices for a list of items in one request.

        Args:
            retail_shop_id: The Retail Shop ID.
            items: List of {"itemId", "productId", "unitId", "quantity"} dicts.
            customer_id: (Optional) Customer ID for customer-specific pricing.
        """
        payload = {
            "retailShopId": retail_shop_id,
            "customerId": customer_id or 0,
            "items": items
        }
        return self._request("POST", URLs.GET_PRICE, json=payload)
