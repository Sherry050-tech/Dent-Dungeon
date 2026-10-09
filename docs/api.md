# API Contract

Contract between `apps/api` (FastAPI) and `apps/web` (Next.js). Update this file in the same PR as API changes. Implemented schemas are ultimately verified at `http://localhost:8000/docs`.

## 1. Conventions

| Topic | Rule |
|---|---|
| Base URL | `/api/v1` |
| Format | JSON, UTF-8, `snake_case` |
| IDs | UUID strings |
| Dates | `YYYY-MM-DD`; datetimes ISO 8601 UTC |
| Money | Decimal strings such as `"2500.00"` |
| Auth | `Authorization: Bearer <access_token>` except public endpoints |
| Updates | `PATCH` for partial updates |
| Deletes | `204 No Content`; soft-delete/deactivate patients, staff and catalog items; retain clinical/financial history |
| Tenant scope | Every authenticated request is scoped to the user's `clinic_id` |
| Files | Private storage; API authorization required for every download |

### Pagination

List endpoints accept `?page=1&limit=20` (default 20, maximum 100) and return `{"items":[],"total":0,"page":1,"limit":20}`.

### Error format

```json
{
  "detail": "Human-readable message",
  "code": "MACHINE_READABLE_CODE",
  "fields": {"field_name": "Validation message"}
}
```

`fields` is optional. Common status codes: `400 BAD_REQUEST`, `401 NOT_AUTHENTICATED`, `403 FORBIDDEN`, `404 NOT_FOUND`, `409 APPOINTMENT_CONFLICT`/`DUPLICATE_PATIENT`, `413 FILE_TOO_LARGE`, `415 UNSUPPORTED_FILE_TYPE`, `422 VALIDATION_ERROR`, `500 INTERNAL_ERROR`, `503 AI_UNAVAILABLE`.

Do not reveal whether an out-of-scope record exists in another clinic; return `404`.

## 2. Product model: clinics, roles and permissions

Each clinic is a separate tenant. Every patient, appointment, clinical record, invoice, file, conversation, staff member and setting belongs to one clinic. The backend must enforce tenant isolation on every request.

Roles: `admin`, `doctor`, `receptionist`. `is_practitioner` is independent of role: an admin/owner can also treat patients without needing a second account.

| Area | Admin | Doctor/practitioner | Receptionist |
|---|---|---|---|
| Clinic settings/staff | Manage | Read self | Read self |
| Patients | Read/create/edit; soft-delete | Read/create/edit | Read/create/edit |
| Appointments | Full | Manage own; view as permitted | Schedule/manage |
| Treatment catalog | Read/edit | Read | Read |
| Treatments/chart/tooth cases | Full | Create/edit clinical records | Read only |
| Documents/images | Manage | View/upload/manage | Document upload/view; image access by policy |
| Invoices/payments | Full | Read | Operational billing as authorized |
| Financial dashboard | Full | No clinic-wide totals by default | As authorized by clinic policy |
| Patient-scoped AI | Yes | Yes | No |
| Audit logs | Read | No | No |

Backend authorization is mandatory; hiding frontend controls is not security.

## 3. Auth and onboarding

### `POST /auth/register` — Public, initial clinic onboarding only

Creates a clinic and its first active admin/owner atomically. Do not make the first user in the entire database an admin; each clinic has its own owner. Do not accept a public `clinic_id` that lets users join another clinic.

Request:

```json
{
  "clinic_name": "Bright Smile Dental",
  "full_name": "Dr. Sara Ahmed",
  "email": "sara@example.com",
  "password": "at least 8 characters",
  "is_practitioner": true
}
```

Response `201`:

```json
{
  "clinic": {"id": "uuid", "name": "Bright Smile Dental"},
  "user": {
    "id": "uuid",
    "clinic_id": "uuid",
    "full_name": "Dr. Sara Ahmed",
    "email": "sara@example.com",
    "role": "admin",
    "is_practitioner": true,
    "is_active": true
  }
}
```

### `POST /auth/login` — Public

Request: `{"email":"sara@example.com","password":"..."}`

Response `200` includes `access_token`, `refresh_token`, `token_type: "bearer"`, `expires_in: 3600`, and a `user` object containing `id`, `clinic_id`, `full_name`, `email`, `role`, and `is_practitioner`.

Access token lifetime: 60 minutes; refresh token lifetime: 7 days. Store only password hashes (Argon2 recommended). Refresh-token revocation/session tracking should be implemented before production.

| Method | Path | Description |
|---|---|---|
| POST | `/auth/refresh` | Exchange valid refresh token for new access token |
| GET | `/auth/me` | Current user and clinic context |
| POST | `/auth/change-password` | Verify current password and change it |
| POST | `/auth/logout` | Invalidate refresh session when server-side tracking is implemented |

Staff are added by an authenticated clinic admin, preferably through invitations—not by public registration with a user-supplied clinic ID.

## 4. Staff and practitioners

| Method | Path | Description |
|---|---|---|
| GET | `/users?role=&is_active=&page=&limit=` | List staff in current clinic (admin) |
| POST | `/users/invitations` | Invite staff with role and optional practitioner flag |
| GET | `/users/{id}` | Get staff member in current clinic |
| PATCH | `/users/{id}` | Update name, role, phone, specialization, `is_practitioner`, active state (admin) |
| GET | `/users/doctors` | Active users who can treat patients (`role=doctor` or `is_practitioner=true`) |

User object includes `id`, `clinic_id`, `full_name`, `email`, `role`, nullable `phone`, nullable `specialization`, `is_practitioner`, `is_active`, and timestamps. A practitioner must be active and belong to the same clinic as the appointment/patient.

## 5. Patients

Patient object:

```json
{
  "id": "uuid",
  "clinic_id": "uuid",
  "patient_number": "P-000123",
  "first_name": "Ali",
  "last_name": "Khan",
  "gender": "male",
  "date_of_birth": "1995-04-12",
  "phone": null,
  "emergency_contact_name": null,
  "emergency_contact_phone": null,
  "allergies": "Penicillin",
  "medical_history": "Asthma",
  "medications": "Medication and dosage as reported",
  "notes": "General patient notes",
  "created_at": "2026-10-03T10:00:00Z",
  "updated_at": "2026-10-03T10:00:00Z"
}
```

Do not collect patient CNIC/national ID, residential address or email in the default product. Patient phone is optional. Clinic contact details are separate.

| Method | Path | Description |
|---|---|---|
| GET | `/patients?search=&page=&limit=` | Search by name, optional phone, patient number |
| POST | `/patients` | Create; `first_name` and `last_name` required; phone optional |
| GET | `/patients/{id}` | Get profile |
| PATCH | `/patients/{id}` | Update allowed profile fields |
| DELETE | `/patients/{id}` | Soft-delete (admin); preserve linked history |
| GET | `/patients/{id}/summary` | Patient, upcoming appointments, active treatments, outstanding balance |
| GET | `/patients/{id}/appointments` | Patient appointments |
| GET | `/patients/{id}/treatments?status=` | Patient treatments |
| GET | `/patients/{id}/invoices` | Patient invoices |

`patient_number` is generated by the backend and unique within a clinic. Phone is not unique (family members may share it). Every referenced patient must belong to the authenticated clinic.

## 6. Patient CSV import — planned after core patient APIs

| Method | Path | Description |
|---|---|---|
| POST | `/patients/import/preview` | Validate uploaded CSV, map columns, flag errors/possible duplicates; no records written |
| POST | `/patients/import/confirm` | Confirm preview/import token and import valid rows |

Preview and require confirmation. Never silently overwrite records. Import only supported fields; do not import CNIC, patient address or patient email. Enforce row/file limits and clinic scope. These endpoints are planned, not Phase 1.

## 7. Appointments

Object includes appointment `id`, embedded patient (`id`, name, optional phone), embedded doctor (`id`, name), `start_time`, `end_time`, `status`, `reason`, `notes`, and `cancelled_reason`.

| Method | Path | Description |
|---|---|---|
| GET | `/appointments?from=&to=&doctor_id=&patient_id=&status=&page=&limit=` | List for calendar |
| POST | `/appointments` | Create using patient, practitioner, start/end and optional reason/notes |
| GET | `/appointments/{id}` | Get one |
| PATCH | `/appointments/{id}` | Reschedule/update |
| POST | `/appointments/{id}/cancel` | Cancel with optional reason |
| GET | `/appointments/availability?doctor_id=&date=` | Available slots based on clinic hours |
| GET | `/patients/{id}/appointments` | Appointments for patient |

Prevent overlapping appointments for the same practitioner using a database exclusion constraint; exclude `cancelled` and `no_show`. Return `409 APPOINTMENT_CONFLICT`. Status flow: `scheduled` → `confirmed` → `in_progress` → `completed`; scheduled/confirmed may also become `cancelled` or `no_show`.

## 8. Treatment catalog and patient treatments

Treatment catalog object: `id`, `code`, `name`, `category`, `description`, `default_price` (decimal string), `default_duration_min`, `is_active`.

| Method | Path | Description |
|---|---|---|
| GET | `/treatment-catalog?search=&category=&is_active=&page=&limit=` | List clinic catalog |
| POST | `/treatment-catalog` | Create (admin) |
| PATCH | `/treatment-catalog/{id}` | Update/retire (admin) |
| GET | `/patients/{id}/treatments?status=` | Patient treatment list |
| POST | `/patients/{id}/treatments` | Add treatment |
| PATCH | `/treatments/{id}` | Update; completion stamps `performed_at` |
| DELETE | `/treatments/{id}` | Only planned and not invoiced |

Treatment object includes `patient_id`, nullable `tooth_case_id`, `catalog`, `doctor`, nullable `appointment_id`, nullable `tooth_number`, `surfaces`, `status`, `price`, `discount`, `notes`, `performed_at`. If a case is supplied, case/patient/clinic/tooth must match.

## 9. Dental chart and tooth cases

FDI numbering: adult `11–18`, `21–28`, `31–38`, `41–48`; primary `51–55`, `61–65`, `71–75`, `81–85`. Surface notation includes `M`, `O`, `D`, `B`, `L`, `I`.

### Dental chart

| Method | Path | Description |
|---|---|---|
| GET | `/patients/{id}/dental-chart` | Current state |
| GET | `/patients/{id}/dental-chart/history?tooth_number=` | Historical findings |
| POST | `/patients/{id}/dental-chart/entries` | Add historical finding (authorized clinical staff) |

Each chart change is a new row; don't overwrite past findings.

### Tooth cases

A case groups tooth-specific clinical notes, findings, treatment plan, treatments and imaging. One tooth can have multiple cases over time.

| Method | Path | Description |
|---|---|---|
| GET | `/patients/{patient_id}/tooth-cases?tooth_number=&status=` | List patient cases |
| POST | `/patients/{patient_id}/tooth-cases` | Create with `tooth_number`, `title`, optional `diagnosis_notes`, `treatment_plan` |
| GET | `/patients/{patient_id}/tooth-cases/{case_id}` | Case details and linked records |
| PATCH | `/patients/{patient_id}/tooth-cases/{case_id}` | Update title, status, notes or plan |

Statuses: `open`, `in_progress`, `resolved`, `closed`. Validate FDI number and confirm case belongs to route patient and current clinic.

## 10. Documents and imaging

Uploads use `multipart/form-data`. Proposed initial limits: documents 10 MB (PDF/JPG/PNG/DOCX), images 25 MB (JPG/PNG/DICOM). Validate actual content server-side and store in private object storage.

### Documents

Object: `id`, `patient_id`, `type`, `title`, `mime_type`, `size_bytes`, `index_status`, `uploaded_by`, `created_at`.

| Method | Path | Description |
|---|---|---|
| GET | `/patients/{id}/documents?type=` | List |
| POST | `/patients/{id}/documents` | Upload |
| GET | `/documents/{id}/download` | Authenticated download |
| DELETE | `/documents/{id}` | Remove from active workspace and remove AI chunks; retain audit trail |

### Images

Object includes `id`, `patient_id`, nullable `tooth_case_id`, `image_type`, nullable `tooth_number`, `mime_type`, `size_bytes`, `taken_at`, `notes`, `created_at`.

| Method | Path | Description |
|---|---|---|
| GET | `/patients/{id}/images?image_type=&tooth_number=&tooth_case_id=` | List |
| POST | `/patients/{id}/images` | Upload image with optional tooth/case/date/notes |
| GET | `/images/{id}/file` | Authenticated full-size image |
| PATCH | `/images/{id}` | Update metadata |
| DELETE | `/images/{id}` | Remove from active workspace under retention policy |

Never expose permanent public URLs for clinical files. Check clinic and patient authorization on every file request.

## 11. Billing

Invoice fields include `id`, clinic-unique `invoice_number`, patient, `status`, `items`, `subtotal`, `discount`, `total`, `paid_amount`, computed `balance`, `issued_at`, `due_date`, `notes`, and payments. Money is represented as decimal strings. `balance = total - paid_amount`.

| Method | Path | Description |
|---|---|---|
| GET | `/invoices?status=&patient_id=&from=&to=&page=&limit=` | List |
| POST | `/invoices` | Create draft from completed treatment IDs and/or custom line items |
| GET | `/invoices/{id}` | Full invoice |
| PATCH | `/invoices/{id}` | Edit draft only |
| POST | `/invoices/{id}/issue` | Issue draft |
| POST | `/invoices/{id}/payments` | Record amount, method, optional reference/date |
| POST | `/invoices/{id}/void` | Void invoice (admin, reason required) |
| GET | `/patients/{id}/invoices` | Patient invoices |

Reject overpayment, payment on draft/void invoices, and edits to issued invoices. Update invoice totals/status and payment records transactionally. Payments are immutable; corrections require an auditable correction/reversal process.

## 12. Dashboard and reports

`GET /dashboard/summary` returns today's appointment counts, new patients, upcoming appointments, recent patients, today's/monthly revenue and outstanding balances according to permissions. Doctors see their own schedule and no clinic-wide financial totals by default. Admins receive owner-level metrics. Receptionist financial access follows clinic policy. All date boundaries use the clinic timezone.

## 13. AI assistant — planned Phase 4

Doctors/practitioners and admins only. AI is decision support, not autonomous diagnosis; display: “AI suggestions must be reviewed by a qualified dentist.”

| Method | Path | Description |
|---|---|---|
| GET | `/patients/{id}/ai/conversations` | List |
| POST | `/patients/{id}/ai/conversations` | Start |
| GET | `/ai/conversations/{id}/messages` | History |
| POST | `/ai/conversations/{id}/messages` | Ask question; optional SSE |
| DELETE | `/ai/conversations/{id}` | Delete under retention policy |

Every retrieval and citation must be scoped to authorized clinic and patient. Include source references to documents/pages, chart entries, cases or treatments. Review privacy/data-handling settings before sending clinical data to external model providers.

## 14. Settings, audit and health

| Method | Path | Description |
|---|---|---|
| GET | `/settings/clinic` | Current clinic settings |
| PATCH | `/settings/clinic` | Admin updates clinic name/contact, currency, timezone, hours and default slot length |
| GET | `/audit-logs?user_id=&entity_type=&from=&to=&page=&limit=` | Admin audit trail |
| GET | `/health` | Public API process health: `{"status":"ok"}` |

Clinic contact address/email are allowed; patient address/email are not part of the default patient schema. Never log passwords or tokens.

## 15. Build order

1. Phase 1: clinic onboarding, users, settings, health, DB connection, migrations and authentication.
2. Phase 2: patients, appointments, treatment catalog and patient treatments.
3. Phase 3: dental chart, tooth cases, documents/images, billing and dashboard.
4. Phase 3.5: CSV import preview/confirmation.
5. Phase 4: patient-scoped AI/RAG.
6. Later: appointment reminders after validating WhatsApp/SMS demand, consent and provider costs.

## 16. Change process

1. Discuss changes before implementation.
2. Update this file in the same PR as code.
3. Review contract changes with frontend owner.
4. Treat documented endpoints as planned until implemented and tested.
