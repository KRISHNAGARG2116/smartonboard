import re
import uuid


def slugify(value: str) -> str:
    slug = value.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "-", slug).strip("-")
    return slug[:80] or "company"


def unique_slug(base: str, existing: set[str]) -> str:
    slug = slugify(base)
    if slug not in existing:
        return slug
    suffix = uuid.uuid4().hex[:6]
    return f"{slug}-{suffix}"[:100]
