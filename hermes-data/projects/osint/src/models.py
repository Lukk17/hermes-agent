from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class QueryType(str, Enum):
    EMAIL = "email"
    PHONE = "phone"
    PERSON = "person"
    NIP = "nip"
    PESEL = "pesel"
    KRS = "krs"
    DOMAIN = "domain"
    LINKEDIN = "linkedin"
    CEIDG = "ceidg"
    PLATE = "plate"
    VIN = "vin"


class OsintQuery(BaseModel):
    email: Optional[str] = Field(default=None)
    phone: Optional[str] = Field(default=None)
    name: Optional[str] = Field(default=None)
    location: Optional[str] = Field(default=None)
    nip: Optional[str] = Field(default=None)
    pesel: Optional[str] = Field(default=None)
    krs: Optional[str] = Field(default=None)
    domain: Optional[str] = Field(default=None)
    linkedin: Optional[str] = Field(default=None)
    ceidg_url: Optional[str] = Field(default=None)
    plate: Optional[str] = Field(default=None)
    vin: Optional[str] = Field(default=None)


class ServiceResult(BaseModel):
    source: str
    success: bool
    data: dict = Field(default_factory=dict)
    error: Optional[str] = None


class OsintResponse(BaseModel):
    query: OsintQuery
    results: list[ServiceResult] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
