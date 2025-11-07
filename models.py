from sqlalchemy import Column, Integer, String, ForeignKey, Text, Boolean, Date, Numeric, TIMESTAMP
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()

# ============================================
# CORE AI MODELS
# ============================================

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    user = relationship("User", back_populates="conversations")
    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"))
    role = Column(String, nullable=False)   # "user" | "ai"
    content = Column(Text, nullable=False)

    conversation = relationship("Conversation", back_populates="messages")

# ============================================
# BUSINESS MODELS (para referência e queries)
# ============================================

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    password = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String(512))
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = relationship("Organization", back_populates="users")
    conversations = relationship("Conversation", back_populates="user")

class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    slug = Column(String(50), unique=True)
    description = Column(Text)
    active = Column(Boolean, default=True)
    contact_email = Column(String(100))
    contact_phone = Column(String(20))
    address = Column(String(200))
    document = Column(String(50))
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    users = relationship("User", back_populates="organization")
    clients = relationship("Client", back_populates="organization")
    vehicles = relationship("Vehicle", back_populates="organization")
    service_orders = relationship("ServiceOrder", back_populates="organization")
    parts = relationship("Part", back_populates="organization")
    inventory_items = relationship("InventoryItem", back_populates="organization")

class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    name = Column(String(255))
    document = Column(String(100))
    phone = Column(String(100))
    email = Column(String(255))
    address = Column(String(255))
    birth_date = Column(Date)
    observations = Column(Text)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = relationship("Organization", back_populates="clients")
    vehicles = relationship("Vehicle", back_populates="client")
    service_orders = relationship("ServiceOrder", back_populates="client")

class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    license_plate = Column(String(20), nullable=False)
    brand = Column(String(100), nullable=False)
    model = Column(String(100), nullable=False)
    manufacture_date = Column(Date, nullable=False)
    color = Column(String(50))
    observations = Column(Text)
    kilometers = Column(Integer, nullable=False)
    chassis_id = Column(String(100), nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = relationship("Organization", back_populates="vehicles")
    client = relationship("Client", back_populates="vehicles")
    service_orders = relationship("ServiceOrder", back_populates="vehicle")

class ServiceOrder(Base):
    __tablename__ = "service_orders"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    order_number = Column(String(50), nullable=False)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    description = Column(Text)
    problem_description = Column(Text)
    diagnosis = Column(Text)
    solution_description = Column(Text)
    status = Column(String(20), default="PENDING")
    labor_cost = Column(Numeric(10, 2), default=0)
    parts_cost = Column(Numeric(10, 2), default=0)
    total_cost = Column(Numeric(10, 2), default=0)
    discount = Column(Numeric(10, 2), default=0)
    estimated_completion = Column(TIMESTAMP)
    actual_completion = Column(TIMESTAMP)
    observations = Column(Text)
    technician_name = Column(String(100))
    current_kilometers = Column(Numeric(10, 2))
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = relationship("Organization", back_populates="service_orders")
    vehicle = relationship("Vehicle", back_populates="service_orders")
    client = relationship("Client", back_populates="service_orders")
    items = relationship("ServiceOrderItem", back_populates="service_order")

class ServiceOrderItem(Base):
    __tablename__ = "service_order_items"

    id = Column(Integer, primary_key=True, index=True)
    service_order_id = Column(Integer, ForeignKey("service_orders.id", ondelete="CASCADE"), nullable=False)
    description = Column(String(500), nullable=False)
    item_type = Column(String(20), nullable=False)
    quantity = Column(Integer, default=1)
    unit_price = Column(Numeric(10, 2), default=0)
    total_price = Column(Numeric(10, 2), default=0)
    product_code = Column(String(100))
    requires_stock = Column(Boolean, default=False)
    stock_reserved = Column(Boolean, default=False)
    stock_product_id = Column(Integer)
    applied = Column(Boolean, default=False)
    observations = Column(Text)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    service_order = relationship("ServiceOrder", back_populates="items")

class Part(Base):
    __tablename__ = "parts"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    name = Column(String(150), nullable=False)
    sku = Column(String(100), nullable=False)
    manufacturer = Column(String(150))
    description = Column(Text)
    unit_cost = Column(Numeric(10, 2))
    unit_price = Column(Numeric(10, 2))
    active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = relationship("Organization", back_populates="parts")
    inventory_items = relationship("InventoryItem", back_populates="part")

class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    part_id = Column(Integer, ForeignKey("parts.id"), nullable=False)
    location = Column(String(100), nullable=False)
    quantity = Column(Integer, default=0)
    reserved_quantity = Column(Integer, default=0)
    minimum_quantity = Column(Integer, default=0)
    unit_cost = Column(Numeric(10, 2))
    sale_price = Column(Numeric(10, 2))
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = relationship("Organization", back_populates="inventory_items")
    part = relationship("Part", back_populates="inventory_items")
    movements = relationship("InventoryMovement", back_populates="inventory_item")

class InventoryMovement(Base):
    __tablename__ = "inventory_movements"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    inventory_item_id = Column(Integer, ForeignKey("inventory_items.id"), nullable=False)
    part_id = Column(Integer, ForeignKey("parts.id"), nullable=False)
    service_order_id = Column(Integer, ForeignKey("service_orders.id"))
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"))
    movement_type = Column(String(50), nullable=False)
    quantity = Column(Integer, nullable=False)
    reference_code = Column(String(100))
    notes = Column(Text)
    movement_date = Column(TIMESTAMP, default=datetime.utcnow)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    inventory_item = relationship("InventoryItem", back_populates="movements")
