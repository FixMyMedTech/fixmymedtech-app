# models.py — SQLAlchemy models for fixmymedtech schema
# Install: pip install sqlalchemy psycopg2-binary

import os

from sqlalchemy import (
    Column, String, Text, Integer, Numeric, Date, DateTime,
    ForeignKey, CheckConstraint, MetaData, event
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func
import uuid
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.ext.hybrid import hybrid_property


# ── Schema setup ─────────────────────────────────────────────
SCHEMA = os.getenv("SUPABASE_DB_SCHEMA")
metadata = MetaData(schema=SCHEMA)


class Base(DeclarativeBase):
    metadata = metadata

# ══════════════════════════════════════════════════════════════
# AUTH USERS (from Supabase auth.users table) - only add columns I actually need
# ══════════════════════════════════════════════════════════════


class AuthUser(Base):
    __tablename__ = "users"
    __table_args__ = {
        "schema": "auth",
        "extend_existing": True,  # don't try to redefine if already reflected elsewhere
    }

    id = Column(UUID(as_uuid=True), primary_key=True)
    email = Column(String)


# ══════════════════════════════════════════════════════════════
# ORGANIZATIONS
# ══════════════════════════════════════════════════════════════

class Organization(Base):
    __tablename__ = "organizations"
    __table_args__ = (
        CheckConstraint(
            "type IN ('hospital', 'clinic', 'health_centre', 'lab', 'engineering')",
            name="organizations_type_check"
        ),
        {"schema": SCHEMA},
    )

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name            = Column(Text, nullable=False)
    country         = Column(Text, nullable=False)
    region          = Column(Text)
    type            = Column(Text, default="hospital")
    contact_email   = Column(Text)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    profiles        = relationship("Profile", back_populates="organization", foreign_keys="Profile.organization_id")
    devices         = relationship("Device", back_populates="organization", foreign_keys="Device.organization_id")
    devices_maintained = relationship("Device", back_populates="organization_maintenance", foreign_keys="Device.organization_maintenance_id")

    def __repr__(self):
        return f"<Organization {self.name} ({self.country})>"


# ══════════════════════════════════════════════════════════════
# PROFILES
# ══════════════════════════════════════════════════════════════

class Profile(Base):
    __tablename__ = "profiles"
    __table_args__ = (
        CheckConstraint(
            "role IN ('admin', 'technician', 'clinical_staff', 'engineering_staff')",
            name="profiles_role_check"
        ),
        {"schema": SCHEMA},
    )

    id              = Column(UUID(as_uuid=True), ForeignKey(f"auth.users.id", ondelete="CASCADE"), primary_key=True)  # References auth.users
    organization_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.organizations.id"))
    full_name       = Column(Text)
    role            = Column(Text, nullable=False, default="clinical_staff")
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    organization    = relationship("Organization", back_populates="profiles", foreign_keys=[organization_id])
    maintenance_logs = relationship("MaintenanceLog", back_populates="performed_by_profile")
    fault_reports   = relationship("FaultReport", back_populates="reported_by_profile")
    auth_user = relationship("AuthUser", backref="profile", lazy="selectin")

    def __repr__(self):
        return f"<Profile {self.full_name} ({self.role})>"


# ══════════════════════════════════════════════════════════════
# DEVICE CATEGORIES
# ══════════════════════════════════════════════════════════════

class DeviceCategory(Base):
    __tablename__ = "device_categories"
    __table_args__ = {"schema": SCHEMA}

    id      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name    = Column(Text, nullable=False)
    icon    = Column(Text, default="🏥")

    # Relationships
    devices   = relationship("Device", back_populates="category")
    documents = relationship("Document", back_populates="category")

    def __repr__(self):
        return f"<DeviceCategory {self.icon} {self.name}>"


# ══════════════════════════════════════════════════════════════
# DEVICES
# ══════════════════════════════════════════════════════════════

class Device(Base):
    __tablename__ = "devices"
    __table_args__ = (
        CheckConstraint(
            "acquisition_type IN ('purchased', 'donated', 'leased')",
            name="devices_acquisition_type_check"
        ),
        CheckConstraint(
            "status IN ('operational', 'maintenance', 'fault', 'decommissioned')",
            name="devices_status_check"
        ),
        {"schema": SCHEMA},
    )

    id                          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id             = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.organizations.id"), nullable=False)
    organization_maintenance_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.organizations.id"), nullable=False)
    category_id                 = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.device_categories.id"))
    name                        = Column(Text, nullable=False)
    manufacturer                = Column(Text)
    model                       = Column(Text)
    serial_number               = Column(Text)
    manufacture_year            = Column(Integer)
    acquisition_date            = Column(Date)
    acquisition_type            = Column(Text, default="purchased")
    location                    = Column(Text)
    status                      = Column(Text, default="operational")
    last_maintenance            = Column(Date)
    next_maintenance            = Column(Date)
    notes                       = Column(Text)
    created_at                  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at                  = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    organization             = relationship("Organization", back_populates="devices", foreign_keys=[organization_id])
    organization_maintenance = relationship("Organization", back_populates="devices_maintained", foreign_keys=[organization_maintenance_id])
    category                 = relationship("DeviceCategory", back_populates="devices")
    documents                = relationship("Document", back_populates="device", cascade="all, delete-orphan")
    maintenance_logs         = relationship("MaintenanceLog", back_populates="device", cascade="all, delete-orphan")
    fault_reports            = relationship("FaultReport", back_populates="device", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Device {self.name} [{self.status}]>"


# ══════════════════════════════════════════════════════════════
# DOCUMENTS
# ══════════════════════════════════════════════════════════════

class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint(
            "type IN ('manual', 'quick_guide', 'video', 'diagram', 'checklist')",
            name="documents_type_check"
        ),
        {"schema": SCHEMA},
    )

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id   = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.devices.id", ondelete="CASCADE"))
    category_id = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.device_categories.id"))
    title       = Column(Text, nullable=False)
    type        = Column(Text, nullable=False)
    language    = Column(Text, default="en")
    url         = Column(Text, nullable=False)
    size_kb     = Column(Integer)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    device      = relationship("Device", back_populates="documents")
    category    = relationship("DeviceCategory", back_populates="documents")

    def __repr__(self):
        return f"<Document {self.title} ({self.type})>"


# ══════════════════════════════════════════════════════════════
# MAINTENANCE LOGS
# ══════════════════════════════════════════════════════════════

class MaintenanceLog(Base):
    __tablename__ = "maintenance_logs"
    __table_args__ = (
        CheckConstraint(
            "type IN ('preventive', 'corrective', 'inspection')",
            name="maintenance_logs_type_check"
        ),
        {"schema": SCHEMA},
    )

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id       = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.devices.id", ondelete="CASCADE"), nullable=False)
    performed_by    = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.profiles.id"))
    performed_at    = Column(DateTime(timezone=True), server_default=func.now())
    type            = Column(Text, nullable=False)
    description     = Column(Text)
    parts_replaced  = Column(Text)
    cost_usd        = Column(Numeric(10, 2))
    next_due        = Column(Date)

    # Relationships
    device                  = relationship("Device", back_populates="maintenance_logs")
    performed_by_profile    = relationship("Profile", back_populates="maintenance_logs")

    def __repr__(self):
        return f"<MaintenanceLog {self.type} on {self.device_id} at {self.performed_at}>"


# ══════════════════════════════════════════════════════════════
# FAULT REPORTS
# ══════════════════════════════════════════════════════════════

class FaultReport(Base):
    __tablename__ = "fault_reports"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name="fault_reports_severity_check"
        ),
        CheckConstraint(
            "status IN ('open', 'assigned', 'in_progress', 'resolved')",
            name="fault_reports_status_check"
        ),
        {"schema": SCHEMA},
    )

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id           = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.devices.id", ondelete="CASCADE"), nullable=False)
    reported_by         = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA}.profiles.id"))
    reporter_name       = Column(Text)
    reported_at         = Column(DateTime(timezone=True), server_default=func.now())
    description         = Column(Text, nullable=False)
    severity            = Column(Text, default="medium")
    status              = Column(Text, default="open")
    resolved_at         = Column(DateTime(timezone=True))
    resolution_notes    = Column(Text)

    # Relationships
    device                  = relationship("Device", back_populates="fault_reports")
    reported_by_profile     = relationship("Profile", back_populates="fault_reports")

    def __repr__(self):
        return f"<FaultReport {self.severity} on {self.device_id} [{self.status}]>"