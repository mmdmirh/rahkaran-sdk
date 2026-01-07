import requests
import logging
from typing import Optional, Dict, List, Any, Union
from .urls import URLs
from .exceptions import RahkaranError, RahkaranAuthError, RahkaranServerError, RahkaranClientError

# Try importing the user's auth library. 
# We assume it follows a standard pattern or the user will adjust the import.
try:
    from rahkaran_login_webservice import Login # Hypothetical import based on repo name
except ImportError:
    Login = None

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
        Authenticates using the external 'Rahkaran_login_webservice' library.
        """
        if not Login:
            raise ImportError("rahkaran_login_webservice library not found. Please install it or provide cookies directly.")
        
        # Hypothetical integration - User may need to adjust based on actual lib signature
        try:
            # Assuming the lib has a method to get cookies or session
            # This is a PLACEHOLDER implementation for the external lib usage
            logger.info(f"Authenticating user {username}...")
            # auth_result = Login.login(username, password, self.base_url) 
            # self.session.cookies.update(auth_result.cookies)
            pass 
        except Exception as e:
            raise RahkaranAuthError(f"Authentication failed: {e}")

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Internal request handler with error mapping."""
        url = URLs.build_url(self.base_url, endpoint)
        
        try:
            response = self.session.request(method, url, timeout=10, **kwargs)
            
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
                return response.json()
            except ValueError:
                # Some endpoints return plain text or HTML on error despite 200 OK (Postman behavior observed)
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

    def get_retail_shops(self) -> Dict:
        """Fetch available retail shops."""
        return self._request("GET", URLs.GET_RETAIL_SHOPS)

    def get_products(self, store_id: int) -> Dict:
        """Fetch products for a specific store."""
        return self._request("POST", URLs.GET_PRODUCTS, json={"storeId": store_id})

    def get_remaining(self, store_id: int, product_id: int) -> Dict:
        """Fetch remaining stock for a product in a store."""
        return self._request("POST", URLs.GET_REMAINING, json={"storeId": store_id, "productId": product_id})

    def get_price(self, store_id: int, item_id: int) -> Dict:
        """Fetch price for an item."""
        return self._request("POST", URLs.GET_PRICE, json={"storeId": store_id, "itemId": item_id})
