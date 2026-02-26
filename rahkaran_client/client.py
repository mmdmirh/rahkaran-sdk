import requests
import logging
from typing import Optional, Dict, List, Any, Union
from .urls import URLs
from .exceptions import RahkaranError, RahkaranAuthError, RahkaranServerError, RahkaranClientError

# Try importing the user's auth library. 
try:
    from rahkaran_auth import RahkaranAuth
except ImportError:
    RahkaranAuth = None

logger = logging.getLogger(__name__)

class RahkaranClient:
    """
    Client for interacting with Rahkaran ERP APIs.
    """

    def __init__(self, base_url: str, username: Optional[str] = None, password: Optional[str] = None, cookies: Optional[Dict] = None):
        """
        Initialize the client.
        
        Args:
            base_url: The root URL (e.g., https://example.rahkaran.ir/sgXg/xXXXXXXXX)
            username: Username for auth (if cookies not provided)
            password: Password for auth
            cookies: Pre-authenticated cookies (optional)
        """
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "RahkaranPythonClient/1.0",
            "Accept": "application/json"
        })

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
        """Register a Sales Invoice in Rahkaran."""
        return self._request("POST", URLs.REGISTER_INVOICE, json=invoice_payload)

    def register_sales_order(self, order_payload: Dict) -> Dict:
        """Register a Sales Order in Rahkaran."""
        return self._request("POST", URLs.REGISTER_SALES_ORDER, json=order_payload)

    def create_sales_invoice(self,
                             customer_id: int,
                             store_id: int,
                             settlement_policy_id: int,
                             items: List[Dict],
                             document_pattern_id: int = 1,
                             date: Optional[str] = None,
                             currency_id: int = 1) -> Dict:
        """
        Helper to create a Sales Invoice from a list of products.
        
        Args:
            customer_id: The Rahkaran Customer ID.
            store_id: The Retail Store ID.
            settlement_policy_id: The ID of the settlement policy (e.g., Cash, POS).
            items: List of item dictionaries. Each should have:
                   - 'productId': The Rahkaran Product ID.
                   - 'quantity': Quantity to sell.
                   - 'unitId': (Optional) Unit ID. Defaults to 1.
                   - 'fee': (Optional) Unit Price (Fee).
            document_pattern_id: (Optional) Document pattern ID. Defaults to 1.
            date: (Optional) Invoice date.
            currency_id: (Optional) Currency ID. Defaults to 1 (IRR).
        """
        invoice_items = []
        for item in items:
            invoice_items.append({
                "productId": item.get("productId") or item.get("id"),
                "unitId": item.get("unitId") or item.get("units", [{}])[0].get("id", 1),
                "quantity": item.get("quantity", 0),
                "storeId": store_id,
                "fee": item.get("fee", 0)
            })

        payload = {
            "customerId": customer_id,
            "storeId": store_id,
            "settlementPolicyId": settlement_policy_id,
            "documentPatternId": document_pattern_id,
            "currencyId": currency_id,
            "items": invoice_items
        }

        if date:
            payload["date"] = date

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
                          city_id: int,
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
            city_id: ID of the city for the address (Required).
            address_detail: Full address detail (Required).
            gender: 0 for unknown/unspecified, 1 for Male, 2 for Female.
            birth_date: (Optional) "YYYY-MM-DD".
            address_name: (Optional) A name for the address (e.g., "Home", "Office").
        
        Returns:
            A dictionary containing the results of both operations.
        """
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

    # --- Material Management APIs ---

    def get_tracking_factors(self) -> Dict:
        """Fetch tracking factors (e.g. Batch Numbers, Serial parameters)."""
        return self._request("GET", URLs.GET_TRACKING_FACTORS)

    # --- Retail APIs ---

    def get_retail_shops(self, with_stores: bool = True) -> Dict:
        """
        Fetch available retail shops.
        Args:
           with_stores: If true, includes stores in the response.
        """
        return self._request("GET", URLs.GET_RETAIL_SHOPS, params={"withStores": str(with_stores).lower()})

    def get_products(self, store_id: int, from_: int = 0, number_of_records: int = 600, time_out: int = 30) -> Dict:
        """Fetch products for a specific store with pagination."""
        params = {
            "storeId": store_id,
            "from": from_,
            "numberOfRecords": number_of_records
        }
        return self._request("GET", URLs.GET_PRODUCTS, params=params, time_out=time_out)

    def get_remaining(self, store_id: int, product_id: int) -> Dict:
        """Fetch remaining stock for a product in a store."""
        return self._request("POST", URLs.GET_REMAINING, json={"storeId": store_id, "productId": product_id})

    def get_price(self, store_id: int, item_id: int) -> Dict:
        """Fetch price for an item."""
        return self._request("POST", URLs.GET_PRICE, json={"storeId": store_id, "itemId": item_id})
