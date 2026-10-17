import enum


class UserRole(str, enum.Enum):
    BUSINESS = "BUSINESS"
    CUSTOMER = "CUSTOMER"


class OrderStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"


class PurchaseOrderStatus(str, enum.Enum):
    PENDING = "PENDING"      
    ORDERED = "ORDERED"     
    RECEIVED = "RECEIVED"    
    CANCELLED = "CANCELLED"


class ProductStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
