# Windows Computer Use Rules

- Before controlling any desktop application with `computer` or `computer_batch`, ensure it is authorized via `request_access` (unless `accessMode` is `allow-all` in `settings.json`).
- Prefer `target` (UIA control name or `id:<AutomationId>`) and `computer_batch` over single-step coordinate clicking when possible.
- Never enter passwords, payment information, or bypass security verifications; stop and ask the user to complete those steps.
- When finished with a desktop task, call `windows(action="tidy")` if you opened or restored windows that should be tidied up.
