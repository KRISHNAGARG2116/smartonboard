def validate_company_profile(
    name: str,
    website: str,
    domain: str,
    industry: str,
    company_size: str,
) -> bool:
    """Validate company profile information according to the system constraints.
    
    Returns True if valid, False otherwise.
    """
    if not name or len(name.strip()) < 2 or len(name) > 255:
        return False
    if not website or len(website.strip()) < 3 or len(website) > 255 or "." not in website:
        return False
    if not domain or len(domain.strip()) < 3 or len(domain) > 255:
        return False
    if not industry or len(industry.strip()) < 2 or len(industry) > 255:
        return False
    if not company_size or len(company_size.strip()) < 1 or len(company_size) > 255:
        return False
    return True
