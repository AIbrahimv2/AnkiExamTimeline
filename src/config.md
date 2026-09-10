# Exam Timeline

The timeline appears on the **deck** and **deck overview** screens. To add or remove exams,
open the editor window from **Tools → Exam Timeline** (or the **Edit** button on
the widget).

You normally don't need to edit this config by hand — use the editor instead.
Each exam is stored as:

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
