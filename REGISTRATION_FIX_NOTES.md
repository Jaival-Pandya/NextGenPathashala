# Registration reliability fix

## What changed

- The registration route now normalizes the email to lowercase and checks its basic format before touching the database.
- It checks whether that email already belongs to a user. Since this app uses globally unique email addresses for login, the UI now explains that the person should sign in or use another email for a separate workspace.
- It catches `IntegrityError` separately to handle two near-simultaneous registrations safely.
- Database exceptions are logged server-side and the user sees a clearer recovery message; raw database details are not shown.
- Added regression tests in `tests/test_app.py`.

## How to verify locally

1. Install dependencies in your project virtual environment: `python -m pip install -r requirements-dev.txt`.
2. Run database migrations as described in `README.md`.
3. Run `pytest`.
4. Start the app using the README's local development command.
5. Create a workspace using a new email. Confirm it redirects to the dashboard.
6. Sign out and attempt registration again with the same email (case differences included). Confirm a clear duplicate-email message appears and no second institution is created.
7. Try an invalid email and a password over 128 characters. Confirm inline/server-side validation feedback appears.

## Verification status

The dependency-light release check passes in the build environment. Full pytest and live database tests were not executed here because the environment does not have Flask dependencies installed and cannot reach package indexes. This patch is not a claim that the entire product is already 5/5 or production-certified; teacher/student workflows and security must still be exercised in a running environment.
