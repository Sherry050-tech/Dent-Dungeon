# API

API documentation.

# API Contract

This document is the agreement between the backend (`apps/api`, FastAPI) and the frontend (`apps/web`, Next.js). The frontend can build against these shapes using mock data before the backend exists. If an endpoint needs to change, discuss it first, update this file in the same PR as the code, and then merge.

Once the backend is running, FastAPI's live docs at `http://localhost:8000/docs` become the source of truth for exact schemas. This file stays the human-readable plan and the place where rules are explained.

Field names match the tables in `docs/database.md`.

---

## 1. Conventions

| Topic | Rule |
|---|---|
| Base URL | `/api/v1` (e.g. `http://localhost:8000/api/v1`) |
| Format | JSON, `snake_case` field names, UTF-8 |
| IDs | UUID strings |
| Dates | `date`: `YYYY-MM-DD`. `datetime`: ISO 8601 in UTC, e.g. `2026-10-03T10:00:00Z`. The frontend converts to local time (Asia/Karachi) for display. |
| Money | Decimal numbers sent as **strings** (`"2500.00"`) to avoid floating-point errors |
| Auth | `Authorization: Bearer <access_token>` on every endpoint except those marked **Public** |
| Updates | `PATCH` with only the fields that change. `PUT` is not used. |
| Deletes | Return `204 No Content`. Patients, users and catalog items are soft-deleted. |

### Pagination (all list endpoints)

Query: `?page=1&limit=20` (default `limit` 20, max 100)

```json
{
  "items": [ ],
  "total": 134,
  "page": 1,
  "limit": 20
}
```

### Error format (all errors)

```json
{
  "detail": "Human readable message",
  "code": "MACHINE_READABLE_CODE",
  "fields": { "phone": "Phone number is required" }
}
```

`fields` appears only on validation errors.

| Status | Meaning | Example `code` |
|---|---|---|
| 400 | Bad request | `BAD_REQUEST` |
| 401 | Not logged in or token expired | `NOT_AUTHENTICATED`, `TOKEN_EXPIRED` |
| 403 | Logged in but not allowed | `FORBIDDEN` |
| 404 | Not found | `NOT_FOUND` |
| 409 | Conflict | `APPOINTMENT_CONFLICT`, `EMAIL_TAKEN` |
| 413 | File too large | `FILE_TOO_LARGE` |
| 415 | File type not allowed | `UNSUPPORTED_FILE_TYPE` |
| 422 | Validation failed | `VALIDATION_ERROR` |
| 500 | Server error | `INTERNAL_ERROR` |

---

## 2. Roles and permissions

Roles: `admin`, `doctor`, `receptionist`.

| Area | admin | doctor | receptionist |
|---|---|---|---|
| Users (manage staff) | Full | Read self | Read self |
| Patients: read / create / edit | Yes | Yes | Yes |
| Patients: delete | Yes | No | No |
| Appointments | Full | Full | Full |
| Treatment catalog: read | Yes | Yes | Yes |
| Treatment catalog: edit | Yes | No | No |
| Patient treatments: create / edit | Yes | Yes | No (read only) |
| Dental chart: write | Yes | Yes | No (read only) |
| Documents and images: upload / view | Yes | Yes | Upload and view documents; view images |
| Invoices and payments | Full | Read | Full |
| AI assistant | Yes | Yes | No |
| Clinic settings | Edit | Read | Read |
| Audit logs | Read | No | No |

---

## 3. Auth

### `POST /auth/register` (Public)

Creates a staff account. The **first account ever created** becomes an active `admin`. Every later registration is created as an inactive `receptionist` until an admin activates it and sets the proper role.

Request:
```json
{ "full_name": "Dr. Sara Ahmed", "email": "sara@clinic.com", "password": "min 8 chars" }
```
Response `201`:
```json
{ "id": "uuid", "full_name": "Dr. Sara Ahmed", "email": "sara@clinic.com", "role": "receptionist", "is_active": false }
```
Errors: `409 EMAIL_TAKEN`, `422 VALIDATION_ERROR`.

### `POST /auth/login` (Public)

Request:
```json
{ "email": "sara@clinic.com", "password": "..." }
```
Response `200`:
```json
{
  "access_token": "jwt",
  "refresh_token": "jwt",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": { "id": "uuid", "full_name": "Dr. Sara Ahmed", "email": "sara@clinic.com", "role": "doctor" }
}
```
Errors: `401 INVALID_CREDENTIALS`, `403 ACCOUNT_INACTIVE`.

Access token lifetime: 60 minutes. Refresh token lifetime: 7 days.

### `POST /auth/refresh` (Public)

Request: `{ "refresh_token": "jwt" }`
Response `200`: `{ "access_token": "jwt", "expires_in": 3600 }`
Errors: `401 TOKEN_EXPIRED`.

### `GET /auth/me`

Returns the current user (same shape as `user` in the login response, plus `phone` and `specialization`).

### `POST /auth/change-password`

Request: `{ "current_password": "...", "new_password": "..." }`
Response `204`. Errors: `400 WRONG_PASSWORD`.

> Logout is handled by the frontend discarding both tokens.

---

## 4. Users (admin)

| Method | Path | Description |
|---|---|---|
| GET | `/users?role=&is_active=&page=&limit=` | List staff |
| POST | `/users` | Create a staff member (admin sets role and active state) |
| GET | `/users/{id}` | Get one |
| PATCH | `/users/{id}` | Update name, role, phone, specialization, `is_active` |
| GET | `/users/doctors` | Active doctors only (for appointment booking dropdowns). Any role. |

User object:
```json
{
  "id": "uuid", "full_name": "...", "email": "...", "role": "doctor",
  "phone": "...", "specialization": "Orthodontist", "is_active": true,
  "created_at": "2026-10-03T10:00:00Z"
}
```

---

## 5. Patients

Patient object:
```json
{
  "id": "uuid",
  "patient_number": "P-000123",
  "first_name": "Ali",
  "last_name": "Khan",
  "gender": "male",
  "date_of_birth": "1995-04-12",
  "phone": "03001234567",
  "email": "ali@example.com",
  "address": "...",
  "national_id": "35202-1234567-1",
  "emergency_contact_name": "...",
  "emergency_contact_phone": "...",
  "allergies": "Penicillin",
  "medical_history": "...",
  "notes": "...",
  "created_at": "2026-10-03T10:00:00Z",
  "updated_at": "2026-10-03T10:00:00Z"
}
```

| Method | Path | Description |
|---|---|---|
| GET | `/patients?search=&page=&limit=` | List. `search` matches name, phone or patient number. List items contain: `id`, `patient_number`, `first_name`, `last_name`, `phone`, `date_of_birth`, `last_visit` (nullable datetime), `next_appointment` (nullable datetime). |
| POST | `/patients` | Create. Required: `first_name`, `last_name`, `phone`. Returns `201` with the full object. |
| GET | `/patients/{id}` | Full object |
| PATCH | `/patients/{id}` | Update any fields |
| DELETE | `/patients/{id}` | Soft delete (admin only), `204` |
| GET | `/patients/{id}/summary` | Overview for the patient page: `{ "patient": {...}, "upcoming_appointments": [...], "active_treatments": [...], "outstanding_balance": "5000.00" }` |

---

## 6. Appointments

Appointment object:
```json
{
  "id": "uuid",
  "patient": { "id": "uuid", "first_name": "Ali", "last_name": "Khan", "phone": "0300..." },
  "doctor": { "id": "uuid", "full_name": "Dr. Sara Ahmed" },
  "start_time": "2026-10-05T09:00:00Z",
  "end_time": "2026-10-05T09:30:00Z",
  "status": "scheduled",
  "reason": "Toothache",
  "notes": null,
  "cancelled_reason": null
}
```

Patient and doctor are embedded so the calendar needs no extra calls.

| Method | Path | Description |
|---|---|---|
| GET | `/appointments?from=&to=&doctor_id=&patient_id=&status=&page=&limit=` | List. `from` and `to` are datetimes. Use them for calendar views (day, week, month). |
| POST | `/appointments` | Create. Body: `patient_id`, `doctor_id`, `start_time`, `end_time`, `reason?`, `notes?` |
| GET | `/appointments/{id}` | One appointment |
| PATCH | `/appointments/{id}` | Reschedule or edit (`start_time`, `end_time`, `doctor_id`, `status`, `reason`, `notes`) |
| POST | `/appointments/{id}/cancel` | Body: `{ "cancelled_reason": "..." }`. Sets status to `cancelled`. |
| GET | `/patients/{id}/appointments` | Same list, filtered to one patient |
| GET | `/appointments/availability?doctor_id=&date=` | Free slots for that day: `{ "slots": [{ "start_time": "...", "end_time": "..." }] }`, based on working hours and slot length in settings |

Errors: `409 APPOINTMENT_CONFLICT` when the doctor already has an overlapping appointment. The response includes the conflicting appointment id in `detail`.

Status flow: `scheduled` -> `confirmed` -> `in_progress` -> `completed`. From `scheduled` or `confirmed` it can also go to `cancelled` or `no_show`.

---

## 7. Treatments

### Treatment catalog (the price list)

Object: `{ "id", "code", "name", "category", "description", "default_price": "2500.00", "default_duration_min": 30, "is_active": true }`

| Method | Path | Description |
|---|---|---|
| GET | `/treatment-catalog?search=&category=&is_active=&page=&limit=` | List |
| POST | `/treatment-catalog` | Create (admin) |
| PATCH | `/treatment-catalog/{id}` | Update (admin). To retire an item set `is_active` to `false`. |

### Patient treatments

Object:
```json
{
  "id": "uuid",
  "patient_id": "uuid",
  "catalog": { "id": "uuid", "code": "RCT-01", "name": "Root Canal" },
  "doctor": { "id": "uuid", "full_name": "Dr. Sara Ahmed" },
  "appointment_id": null,
  "tooth_number": 36,
  "surfaces": null,
  "status": "planned",
  "price": "15000.00",
  "discount": "0.00",
  "notes": null,
  "performed_at": null
}
```

| Method | Path | Description |
|---|---|---|
| GET | `/patients/{id}/treatments?status=` | A patient's treatments |
| POST | `/patients/{id}/treatments` | Add. Body: `catalog_id`, `doctor_id`, `tooth_number?`, `surfaces?`, `price?` (defaults to catalog price), `discount?`, `appointment_id?`, `notes?` |
| PATCH | `/treatments/{id}` | Update details or `status`. Setting `completed` stamps `performed_at`. |
| DELETE | `/treatments/{id}` | Only allowed while `planned` and not yet invoiced, `204` |

---

## 7a. Dental chart

Teeth use FDI numbering (11-48 adult, 51-85 baby teeth).

| Method | Path | Description |
|---|---|---|
| GET | `/patients/{id}/dental-chart` | **Current** state: latest entry per tooth |
| GET | `/patients/{id}/dental-chart/history?tooth_number=` | Full history (optionally one tooth), newest first |
| POST | `/patients/{id}/dental-chart/entries` | Record a finding (doctor, admin) |

Current chart response:
```json
{
  "patient_id": "uuid",
  "teeth": [
    { "tooth_number": 36, "surface": "O", "condition": "cavity", "notes": "Deep caries", "recorded_at": "2026-10-03T10:00:00Z", "recorded_by": "Dr. Sara Ahmed" }
  ]
}
```
Teeth with no entries are omitted. The frontend treats them as `healthy`.

Create body: `{ "tooth_number": 36, "surface": "O", "condition": "cavity", "notes": "..." }`
Response `201`: the created entry.

---

## 8. Documents and imaging

Files are uploaded as `multipart/form-data`. Limits: documents 10 MB (PDF, JPG, PNG, DOCX), images 25 MB (JPG, PNG, DICOM).

### Documents

Object: `{ "id", "patient_id", "type", "title", "mime_type", "size_bytes", "index_status", "uploaded_by", "created_at" }`

| Method | Path | Description |
|---|---|---|
| GET | `/patients/{id}/documents?type=` | List |
| POST | `/patients/{id}/documents` | Upload. Form fields: `file`, `type`, `title`. Triggers AI indexing in the background (`index_status`: `pending` -> `indexed` or `failed`). |
| GET | `/documents/{id}/download` | Returns the file |
| DELETE | `/documents/{id}` | `204`. Also removes its AI chunks. |

### Images

Object: `{ "id", "patient_id", "image_type", "tooth_number", "thumbnail_url", "mime_type", "size_bytes", "taken_at", "notes", "created_at" }`

| Method | Path | Description |
|---|---|---|
| GET | `/patients/{id}/images?image_type=&tooth_number=` | List with thumbnail URLs |
| POST | `/patients/{id}/images` | Upload. Form fields: `file`, `image_type`, `tooth_number?`, `taken_at?`, `notes?` |
| GET | `/images/{id}/file` | Returns the full-size image |
| PATCH | `/images/{id}` | Edit `image_type`, `tooth_number`, `taken_at`, `notes` |
| DELETE | `/images/{id}` | `204` |

File downloads require the `Authorization` header, so the frontend fetches them with the token and displays them as blob URLs. Files are never served as public static URLs.

---

## 9. Billing

Invoice object:
```json
{
  "id": "uuid",
  "invoice_number": "INV-2026-0001",
  "patient": { "id": "uuid", "first_name": "Ali", "last_name": "Khan" },
  "status": "issued",
  "items": [
    { "id": "uuid", "patient_treatment_id": "uuid", "description": "Root Canal - tooth 36", "quantity": 1, "unit_price": "15000.00", "line_total": "15000.00" }
  ],
  "subtotal": "15000.00",
  "discount": "1000.00",
  "total": "14000.00",
  "paid_amount": "5000.00",
  "balance": "9000.00",
  "issued_at": "2026-10-03T10:00:00Z",
  "due_date": "2026-10-17",
  "payments": [
    { "id": "uuid", "amount": "5000.00", "method": "cash", "reference": null, "paid_at": "2026-10-03T10:30:00Z" }
  ]
}
```

`balance` is calculated by the backend (`total - paid_amount`).

| Method | Path | Description |
|---|---|---|
| GET | `/invoices?status=&patient_id=&from=&to=&page=&limit=` | List (items and payments omitted from list rows) |
| POST | `/invoices` | Create a draft. Body: `patient_id`, `treatment_ids: [uuid]` (completed treatments to bill) and/or `custom_items: [{description, quantity, unit_price}]`, `discount?`, `due_date?`, `notes?` |
| GET | `/invoices/{id}` | Full invoice |
| PATCH | `/invoices/{id}` | Edit a **draft** only |
| POST | `/invoices/{id}/issue` | Draft -> issued |
| POST | `/invoices/{id}/payments` | Record a payment. Body: `amount`, `method`, `reference?`, `paid_at?`. Updates status automatically. |
| POST | `/invoices/{id}/void` | Voids the invoice (admin). Body: `{ "reason": "..." }` |
| GET | `/patients/{id}/invoices` | One patient's invoices |

Errors: `400 OVERPAYMENT` (payment exceeds balance), `400 INVOICE_NOT_PAYABLE` (draft or void), `400 INVOICE_LOCKED` (editing an issued invoice).

---

## 10. Dashboard

### `GET /dashboard/summary`

```json
{
  "today": {
    "appointments_total": 12,
    "appointments_completed": 5,
    "appointments_remaining": 7,
    "new_patients": 2
  },
  "revenue": { "today": "45000.00", "this_month": "820000.00" },
  "outstanding_balance_total": "130000.00",
  "upcoming_appointments": [ { "...": "appointment objects, next 5" } ],
  "recent_patients": [ { "id": "uuid", "first_name": "...", "last_name": "...", "created_at": "..." } ]
}
```

A doctor sees only their own appointment counts. Revenue figures are returned to admin and receptionist only; for doctors the `revenue` field is `null`.

---

## 11. AI assistant (per patient)

Doctors and admins only. The assistant answers using only that patient's data (profile, dental chart, treatments, uploaded documents). It never sees another patient's data.

Conversation object: `{ "id", "patient_id", "title", "created_at", "updated_at" }`

Message object:
```json
{
  "id": "uuid",
  "role": "assistant",
  "content": "Based on the chart, tooth 36 has a deep cavity...",
  "sources": [
    { "type": "dental_chart", "id": "uuid", "label": "Tooth 36, 2026-10-03" },
    { "type": "document", "id": "uuid", "label": "Lab report.pdf", "page": 2 }
  ],
  "created_at": "2026-10-03T10:00:00Z"
}
```

| Method | Path | Description |
|---|---|---|
| GET | `/patients/{id}/ai/conversations` | List conversations |
| POST | `/patients/{id}/ai/conversations` | Start one. Body: `{ "title"?: "..." }` |
| GET | `/ai/conversations/{id}/messages` | Message history |
| POST | `/ai/conversations/{id}/messages` | Send a question. Body: `{ "content": "..." }` |
| DELETE | `/ai/conversations/{id}` | `204` |

### Streaming

`POST /ai/conversations/{id}/messages` streams the answer when the request has the header `Accept: text/event-stream`. Events:

```
event: token
data: {"text": "Based on"}

event: sources
data: {"sources": [ ... ]}

event: done
data: {"message_id": "uuid"}
```

Without that header it returns the complete message object as normal JSON.

Errors: `403 FORBIDDEN` (receptionist), `503 AI_UNAVAILABLE` (model provider unreachable).

The AI gives decision support only, never a diagnosis. The UI must show a short notice: "AI suggestions must be reviewed by a qualified dentist."

---

## 12. Settings and admin

| Method | Path | Description |
|---|---|---|
| GET | `/settings/clinic` | Clinic profile and defaults (any role) |
| PATCH | `/settings/clinic` | Update (admin). Fields: `clinic_name`, `address`, `phone`, `email`, `currency`, `timezone`, `working_hours`, `default_slot_min` |
| GET | `/audit-logs?user_id=&entity_type=&from=&to=&page=&limit=` | Audit trail (admin) |
| GET | `/health` | **Public.** `{ "status": "ok" }` for checks |

---

## 13. Build order

| Phase | Endpoints | Backend | Frontend |
|---|---|---|---|
| 1 | Auth, users, settings, health | You | Login, register, layout |
| 2 | Patients, appointments, treatments | You | Patient pages, calendar |
| 3 | Dental chart, documents, images, billing, dashboard | You | Chart UI, viewer, billing |
| 4 | AI conversations | You | AI chat UI |

---

## 14. Change process

1. Propose the change in a GitHub issue or message.
2. Update this file in the same PR as the code change.
3. The other person reviews both.
4. Never remove or rename a field without telling the frontend first. Adding optional fields is safe.

