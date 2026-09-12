# SafeBooks Architecture Style (Quick Guide)

A simple, easy-to-read summary of our project's architecture.

---

## 1. Our Architectural Style

Our project uses **Django MVT + Service Layer Pattern**.

It has **4 main layers**:

| Layer | Folder / File | What It Does |
| :--- | :--- | :--- |
| **1. UI (Presentation)** | `templates/` & `static/` | What the user sees (HTML, CSS, JavaScript). |
| **2. Controller (Traffic Cop)** | `views.py` & `urls.py` | Receives the user's click/request, checks if logged in, and asks `services/` to do the work. |
| **3. Logic (The Brain)** | `services/` | All calculations, tax formulas, password hashing, and rules. |
| **4. Database (Storage)** | `models/` | Where tables and data are saved. |

---

## 2. Django (MVT) vs. Laravel / PHP (MVC)

Django uses the same idea as PHP's MVC, but with different names:

* **In Laravel / PHP (MVC):**  
  Model $\rightarrow$ **Controller** $\rightarrow$ **View** (Blade HTML)

* **In Django (MVT):**  
  Model $\rightarrow$ **View** (`views.py`) $\rightarrow$ **Template** (HTML)

> **Tip:** In Django, `views.py` **IS** your Controller!

---

## 3. What is the `services/` Folder For?

Instead of putting thousands of lines of logic into `views.py`, we split the logic into dedicated service files:

* [client_service.py](file:///c:/Users/Romul/FOR_UI/safebooks/services/client_service.py) $\rightarrow$ Adding, updating, and validating clients.
* [financial_record_service.py](file:///c:/Users/Romul/FOR_UI/safebooks/services/financial_record_service.py) $\rightarrow$ Sales, expenses, and BIR tax formulas.
* [auth_service.py](file:///c:/Users/Romul/FOR_UI/safebooks/services/auth_service.py) $\rightarrow$ Login, password security, email verification codes, and Google login.
* [analytics_service.py](file:///c:/Users/Romul/FOR_UI/safebooks/services/analytics_service.py) & [forecasting_service.py](file:///c:/Users/Romul/FOR_UI/safebooks/services/forecasting_service.py) $\rightarrow$ Financial charts and AI/SARIMA forecasting.

This keeps `views.py` clean, short, and easy to maintain.

---

## 4. Why is `views.py` a File and Not a Folder?

* In Laravel, it creates an `app/Http/Controllers/` folder by default.
* In Django, it creates a single `views.py` file by default.
* Because all the heavy logic is already organized inside the `services/` folder, our `views.py` only needs to be a lightweight traffic cop passing requests to services.

---

## 5. What is the `tests/` Folder For?

The `tests/` folder contains **automated tests**:
* Whenever we update code or fix styles, running `python manage.py test` automatically tests 42+ features in 15 seconds.
* It ensures we never accidentally break existing features.

---

## 6. How to Answer in Class (One Sentence)

> *"Our project uses Django's **MVT** architecture combined with a **Service Layer** to separate web requests from our core business logic."*
