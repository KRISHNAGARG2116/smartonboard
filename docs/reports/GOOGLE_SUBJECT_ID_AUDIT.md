# Google Subject ID Audit

This document audits the design, persistence, and mapping behavior of the Google Subject Identifier (`sub`) in SmartOnboard (Phase 14B).

---

## 1. Vulnerability of Email-Only Mapping

In naive OAuth implementations, the user is identified entirely by their email address. However:
- Users can change their primary email addresses on Google.
- Google Workspace admins can change primary domains or rename user accounts.
- If a user's email changes, mapping by email alone can result in orphaned accounts or security cross-linking.

To resolve this, SmartOnboard stores Google's permanent and immutable Subject ID (`sub` claim), which uniquely identifies a Google user forever.

---

## 2. Database Schema Enforcement

The `google_subject_id` field has been added to the `users` table via Alembic.

### Schema Attributes:
- **Type**: `VARCHAR(255)`
- **Constraints**: `UNIQUE`
- **Indexing**: An index is placed on `google_subject_id` to ensure sub-millisecond lookups during auth.

### Alembic Migration Detail:
```python
# alembic/versions/081496f36c3b_add_google_auth_fields.py
def upgrade() -> None:
    # Add columns
    op.add_column('users', sa.Column('auth_provider', sa.Enum('LOCAL', 'GOOGLE', name='authprovider'), nullable=True))
    op.add_column('users', sa.Column('google_subject_id', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('google_hosted_domain', sa.String(length=255), nullable=True))
    
    # Unique constraint and index
    op.create_unique_constraint('uq_users_google_subject_id', 'users', ['google_subject_id'])
    op.create_index('ix_users_google_subject_id', 'users', ['google_subject_id'])
```

---

## 3. OAuth Identity Linking Flow

When a Google ID Token is verified, the backend queries the database using a strict hierarchy:

```
                  Google Sign-In Request
                            │
                            ▼
              Query: google_subject_id == sub
              (Strict Immutable ID Matching)
               ┌────────────┴────────────┐
               ▼ (Found)                 ▼ (Not Found)
        Authenticate User        Query: email == token_email
                                 ┌───────┴───────┐
                                 ▼ (Found)       ▼ (Not Found)
                          Link Subject ID     Create New User
                          & Authenticate      & Authenticate
```

### Linking Legacy Accounts
If a user created an account via email/password (`LOCAL` provider) and later logs in using Google with the same email:
1. Lookup by `google_subject_id` returns `None`.
2. Lookup by lowercase email matches the existing account.
3. The backend updates the record, setting `google_subject_id = sub` and `auth_provider = AuthProvider.GOOGLE`.
4. All subsequent logins are resolved instantly via the fast `google_subject_id` index.
5. Email changes on the Google side will not break mapping, as the immutable `sub` claim will continue to match the indexed field.
