# SAFEBOOKS AUTHENTICATION BACKEND (LOGIN & SIGN UP) SETUP

## Purpose

Implement the backend functionality for:

* User Registration (Sign Up)
* User Authentication (Login)

Using:

* Django (backend framework)
* SQLite (database)

This must be:

* Cleanly structured
* Scalable
* Aligned with existing UI
* Built step-by-step (no bulk creation)

---

## 1. PROJECT STRUCTURE (IMPORTANT)

Create a dedicated backend structure inside your Django app.

---

### Inside your main app (e.g., safebooks):

Create folders:

* models/
* services/
* validators/

---

### Final Structure Example:

safebooks/
│
├── models/
│   └── user_model.py
│
├── services/
│   └── auth_service.py
│
├── validators/
│   └── password_validator.py
│
├── views.py
├── urls.py

---

## 2. DATABASE TABLE (USER MODEL)

Create a separate file:

### models/user_model.py

---

### Fields:

* id (AutoField, Primary Key)
* full_name (CharField)
* email (CharField, unique)
* password (CharField)
* created_at (DateTimeField)

---

### Important Notes:

* Do NOT use plain text password storage
* Use Django hashing:

from django.contrib.auth.hashers import make_password, check_password

---

## 3. REGISTER (SIGN UP) LOGIC

Create service file:

### services/auth_service.py

---

### Function: register_user(data)

Steps:

1. Validate input fields
2. Validate password strength
3. Check if email already exists
4. Hash password
5. Save user to database
6. Return success or error message

---

## 4. LOGIN LOGIC

In same file:

### Function: login_user(data)

Steps:

1. Check if email exists
2. Compare password using check_password
3. If invalid → return error
4. If valid → return success

---

## 5. PASSWORD VALIDATION (IMPORTANT)

Create:

### validators/password_validator.py

---

### Rules:

Password must:

* Have at least 8 characters
* Include uppercase letter
* Include lowercase letter
* Include number
* Include special symbol

---

### Return:

* List of missing requirements

---

## 6. VIEWS (CONNECT BACKEND TO UI)

Update:

### views.py

---

### Create:

#### register_view(request)

* Accept POST data
* Call register_user()
* Return JSON response

---

#### login_view(request)

* Accept POST data
* Call login_user()
* Return JSON response

---

## 7. URL ROUTING

Update:

### urls.py

---

Add:

* /login/
* /register/

---

## 8. FRONTEND CONNECTION (IMPORTANT)

Update your existing:

* login.html
* signup.html

---

### Remove:

* Auto redirect to dashboard

---

### Add:

AJAX request using JavaScript:

#### On Login:

* Send email + password to /login/
* Handle response

---

#### On Sign Up:

* Send form data to /register/
* Handle response

---

## 9. ERROR HANDLING (UI)

---

### Login Errors:

* "User not found"
* "Invalid credentials"

---

### Register Errors:

* "Email already exists"
* "Password does not meet requirements"

---

## 10. SUCCESS MESSAGES

---

### On Login Success:

* Show: "Login successful"
* THEN redirect to dashboard

---

### On Register Success:

* Show: "Account created successfully"
* Optional: redirect to login

---

## 11. PASSWORD REQUIREMENT INDICATOR (UI)

Inside Sign Up page:

---

### Show dynamic checklist:

* Uppercase letter ✔ / ❌
* Lowercase letter ✔ / ❌
* Number ✔ / ❌
* Symbol ✔ / ❌

---

### Behavior:

* Update in real-time as user types
* Use green (valid) / red (invalid)

---

## 12. SECURITY BASICS

* Always hash passwords
* Never store raw passwords
* Validate all inputs

---

## 13. DO NOT OVERCOMPLICATE

* No JWT yet
* No sessions yet
* No Gmail login yet

---

## 14. TEST FLOW

---

### Register:

* Create new account
* Check database

---

### Login:

* Use saved credentials
* Verify access

---

## 15. GOAL

This implementation must:

* Enable real user authentication
* Store user data properly
* Provide clear feedback
* Match existing UI
* Prepare for future features

---

END OF PROMPT
