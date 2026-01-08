# Base Service Paths
SERVICE_BASE = "Services"
LOGISTICS_BASE =f"{SERVICE_BASE}/Logistics"
RETAIL_BASE = f"{SERVICE_BASE}/Retail"

# Service Names
VOUCHER_SVC = "VoucherProcessingService.svc"
MATERIAL_SVC = "MaterialManagementService.svc"
RETAIL_SVC = "RetailShopService.svc"
PRODUCT_SVC = "ProductService.svc" # Assuming standard naming for GetProducts context
PRICING_SVC = "PricingService.svc" # Assuming for Price API

class URLs:
    # --- Logistics ---
    # Voucher Processing
    GET_VOUCHER_SPEC = f"{LOGISTICS_BASE}/{VOUCHER_SVC}/GetVoucherSpecificationByCode"
    IS_VOUCHER_EXISTS = f"{LOGISTICS_BASE}/{VOUCHER_SVC}/IsVoucherExists"
    REGISTER_VOUCHER = f"{LOGISTICS_BASE}/{VOUCHER_SVC}/RegisterVoucher"
    GET_BY_REF = f"{LOGISTICS_BASE}/{VOUCHER_SVC}/InventoryVouchersByReferenceOrReturnable"
    
    # Material Management
    GET_TRACKING_FACTORS = f"{LOGISTICS_BASE}/{MATERIAL_SVC}/GetTrackingFactors"

    # --- Retail ---
    # Shops & Products
    GET_RETAIL_SHOPS = f"{RETAIL_BASE}/ESales.svc/shops"
    # Note: These paths are based on your previous Postman collection. 
    # Adjust 'ProductService' if the actual SVC name differs.
    GET_PRODUCTS = f"{RETAIL_BASE}/ESales.svc/products" 
    
    # Stock
    GET_REMAINING = f"{RETAIL_BASE}/InventoryService.svc/GetRemaining" # Deduced from /remaining
    
    # Pricing
    GET_PRICE = f"{RETAIL_BASE}/PriceService.svc/GetPrice" # Deduced from /price

    @staticmethod
    def build_url(base_host: str, endpoint: str) -> str:
        """Helper to construct full URL.
        Args:
            base_host: e.g. "https://blahblah.rahkaran.ir/sg5g/x8710x6ee"
            endpoint: One of the constants above.
        """
        return f"{base_host.rstrip('/')}/{endpoint.lstrip('/')}"
