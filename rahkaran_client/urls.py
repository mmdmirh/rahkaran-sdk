# Base Service Paths
SERVICE_BASE = "Services"
LOGISTICS_BASE = f"{SERVICE_BASE}/Logistics"
RETAIL_BASE = f"{SERVICE_BASE}/Retail"

# Service Names
VOUCHER_SVC = "VoucherProcessingService.svc"
MATERIAL_SVC = "MaterialManagementService.svc"
ESALES_SVC = "ESales.svc"

class URLs:
    # --- Logistics ---
    # Voucher Processing
    GET_VOUCHER_SPEC = f"{LOGISTICS_BASE}/{VOUCHER_SVC}/GetVoucherSpecificationByCode"
    IS_VOUCHER_EXISTS = f"{LOGISTICS_BASE}/{VOUCHER_SVC}/IsVoucherExists"
    REGISTER_VOUCHER = f"{LOGISTICS_BASE}/{VOUCHER_SVC}/RegisterVoucher"
    GET_BY_REF = f"{LOGISTICS_BASE}/{VOUCHER_SVC}/InventoryVouchersByReferenceOrReturnable"

    # Material Management
    GET_TRACKING_FACTORS = f"{LOGISTICS_BASE}/{MATERIAL_SVC}/GetTrackingFactors"
    GET_PART_BY_CODE = f"{LOGISTICS_BASE}/{MATERIAL_SVC}/GetPartByCode"

    # --- Retail (ESales web services, per official Hamkaran System docs) ---
    # Shops & Products
    GET_RETAIL_SHOPS = f"{RETAIL_BASE}/{ESALES_SVC}/shops"
    GET_PRODUCTS = f"{RETAIL_BASE}/{ESALES_SVC}/Products"
    GET_PRODUCT = f"{RETAIL_BASE}/{ESALES_SVC}/Product"

    # Sales
    REGISTER_INVOICE = f"{RETAIL_BASE}/{ESALES_SVC}/Invoice"
    GET_INVOICE = f"{RETAIL_BASE}/{ESALES_SVC}/Invoice"
    GET_INVOICES = f"{RETAIL_BASE}/{ESALES_SVC}/Invoices"
    REGISTER_SALES_ORDER = f"{RETAIL_BASE}/{ESALES_SVC}/salesOrder"
    CALCULATE_POLICY = f"{RETAIL_BASE}/{ESALES_SVC}/Policy"
    CALCULATE_SALES_ORDER_POLICY = f"{RETAIL_BASE}/{ESALES_SVC}/salesOrderPolicy"
    # GetSettlementPolicyInfo — the docs say 'settlementpolicy' but the live
    # service maps it to '/settlement' (param: settlementPolicyId)
    GET_SETTLEMENT_POLICIES = f"{RETAIL_BASE}/{ESALES_SVC}/settlement"
    GET_COUPON = f"{RETAIL_BASE}/{ESALES_SVC}/Coupon"
    GET_DISCOUNT_CARD = f"{RETAIL_BASE}/{ESALES_SVC}/DiscountCard"

    # Customer
    CUSTOMER = f"{RETAIL_BASE}/{ESALES_SVC}/Customer"
    ADDRESS = f"{RETAIL_BASE}/{ESALES_SVC}/Address"
    GET_CUSTOMERS = f"{RETAIL_BASE}/{ESALES_SVC}/Customers"
    GET_PLACES = f"{RETAIL_BASE}/{ESALES_SVC}/Places"

    # Stock
    GET_REMAINING = f"{RETAIL_BASE}/{ESALES_SVC}/Remaining"

    # Pricing
    GET_PRICE = f"{RETAIL_BASE}/{ESALES_SVC}/Price"

    @staticmethod
    def build_url(base_host: str, endpoint: str) -> str:
        """Helper to construct full URL.
        Args:
            base_host: e.g. "https://blahblah.rahkaran.ir/sg5g/x8710x6ee"
            endpoint: One of the constants above.
        """
        return f"{base_host.rstrip('/')}/{endpoint.lstrip('/')}"
