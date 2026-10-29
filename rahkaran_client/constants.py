"""Enum-like constants for Rahkaran ESales retail documents.

Values verified directly against the live ESales WSDL (fetched from a real
instance's `ESalesService.svc?wsdl` and its imported schemas), not guessed
from docs — Rahkaran's own documentation does not list them.
"""


class RetailSalesOrderBillIssueTime:
    """`BillIssueTime` on `ESalesOrderDocument` — مقطع صدور صورتحساب:
    when the invoice is issued relative to delivery of the goods.
    From `SystemGroup.Retail.RetailDocuments.Common.RetailSalesOrderBillIssueTime`.
    """
    BEFORE_DELIVERY = "BeforeDelivery"
    AFTER_DELIVERY = "AfterDelivery"


class RetailSalesOrderStatus:
    """`Status` on `ESalesOrderDocument` / its items — the sales-order
    lifecycle state Rahkaran reports back.
    From `SystemGroup.Retail.DocumentStructure.Common.RetailSalesOrderStatus`.
    """
    REGISTERED = "Registered"
    CONFIRMED = "Confirmed"
    CLOSED = "Closed"
    REJECTED = "Rejected"
    CONFIRMING = "Confirming"
    REJECTING = "Rejecting"
    REGISTERING = "Registering"
