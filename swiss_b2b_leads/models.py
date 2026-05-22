from dataclasses import dataclass


@dataclass
class Lead:
    company_name: str = ""
    industry: str = ""
    street: str = ""
    postal_code: str = ""
    city: str = ""
    canton: str = ""
    country: str = "Switzerland"
    phone: str = ""
    email: str = ""
    website: str = ""
    source: str = ""
    source_url: str = ""
    contact_page_url: str = ""
    status: str = ""
    notes: str = ""
    linkedin_company_url: str = ""
    contact_person: str = ""
    contact_role: str = ""
    quality_score: int = 0

    def to_dict(self) -> dict:
        return {
            "company_name": self.company_name,
            "industry": self.industry,
            "street": self.street,
            "postal_code": self.postal_code,
            "city": self.city,
            "canton": self.canton,
            "country": self.country,
            "phone": self.phone,
            "email": self.email,
            "website": self.website,
            "source": self.source,
            "source_url": self.source_url,
            "contact_page_url": self.contact_page_url,
            "status": self.status,
            "notes": self.notes,
            "linkedin_company_url": self.linkedin_company_url,
            "contact_person": self.contact_person,
            "contact_role": self.contact_role,
            "quality_score": self.quality_score,
        }
