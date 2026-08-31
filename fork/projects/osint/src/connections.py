from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Connection:
    conn_type: str
    value: str
    source_service: str
    passive: bool = False
    label: Optional[str] = None
    meta: dict = field(default_factory=dict)

    def key(self) -> tuple:
        return (self.conn_type, self.value)

    def __hash__(self):
        return hash(self.key())


CONNECTION_TYPES = {
    "person_email": "Email (subject's own — follow)",
    "person_company": "Company affiliation (follow)",
    "person_domain": "Domain owned by subject (follow)",
    "person_phone": "Phone number (follow)",
    "person_profile": "Social profile found for subject (follow to get more)",
    "company_nip": "Company NIP (follow)",
    "company_krs": "Company KRS (follow)",
    "company_domain": "Company website domain (follow)",
    "company_subdomain": "Subdomain found (follow)",
    "company_ssl": "SSL certificate domain (follow)",
    "company_github_org": "GitHub org linked to domain (follow)",
    "company_employee": "Employee found (passive — list only)",
    "company_address": "Company address (passive)",
    "company_regon": "Company REGON (passive)",
    "other_person": "Other person found (passive — list only)",
    "other_profile": "Profile of other person (passive)",
}
