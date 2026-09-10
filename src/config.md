# Exam Timeline

Open **Tools → Exam Timeline** to view your countdown and add or remove exams.

You normally don't need to edit this config by hand — use the window's form
instead. Each exam is stored as:

```json
{
  "exams": [
    { "id": 1736500000000, "name": "USMLE Step 1", "date": "2026-11-20" }
  ]
}
```

- `name` — the exam's label.
- `date` — the exam date in `YYYY-MM-DD` format.
- `id` — a unique number used internally to identify each exam.

Exams whose date is in the past are hidden automatically.
