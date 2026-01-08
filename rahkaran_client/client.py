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
            base_url: The root URL (e.g., https://charsotej.rahkaran.ir/sg3g/x5200d5ed)
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
