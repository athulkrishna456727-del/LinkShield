# Link Shield - Product Requirements Document

## Original Problem Statement
Build a full-stack SaaS web application called "Link Shield" — a cybersecurity scanning platform where users can scan URLs, files, apps, PDFs, and images, with a full account system, credits, premium plans, and admin panel.

## Tech Stack
- **Backend**: FastAPI (Python) on port 8001
- **Frontend**: React.js on port 3000
- **Database**: MongoDB (via motor async driver)
- **UI**: Shadcn/UI + Tailwind CSS, dark cybersecurity theme with green (#00FF94) accent
- **Auth**: JWT-based with role system (user, admin, owner)

## Architecture
```
/app/
├── backend/
│   ├── server.py          # All API endpoints
│   ├── .env               # MONGO_URL, DB_NAME, RAZORPAY keys
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── context/AuthContext.js   # Auth state management
    │   ├── pages/                   # All page components
    │   ├── components/ui/           # Shadcn components
    │   └── App.js                   # Routes
    └── .env                         # REACT_APP_BACKEND_URL
```

## DB Collections
- **users**: {id, email, username, password_hash, name, role, plan, credits, status, created_at}
- **scans**: {id, user_id, scan_type, target, status, risk_score, risk_level, metadata, iocs, summary, created_at}
- **transactions**: {id, user_id, plan, amount, status, order_id, payment_id, created_at}
- **audit_logs**: {id, action_type, performed_by, target_user, details, timestamp}
- **payment_settings**: {_id: "razorpay", gateway, key_id, key_secret_encrypted, is_active, updated_at, updated_by}
- **credit_history**: {id, user_id, amount, reason, scan_id, admin_id, timestamp}
- **notifications**: {id, user_id, type, message, read, created_at}

## Key API Endpoints
- `/api/auth/{signup, login, me}`
- `/api/scan/{url, file, {scan_id}, history/list}`
- `/api/admin/users/{user_id}/{plan, role, status, add-credits, deduct-credits, reset-credits}`
- `/api/owner/{create-admin, payment-settings, payment-settings/test, audit-logs}`
- `/api/billing/{plans, create-order, verify-payment, webhook}`

## Test Credentials
- **Owner**: athulkrishna456727@gmail.com / #AThr401012#
- **Admin**: athulmark401012@gmail.com / dgskgsnskz

## What's Been Implemented
- [x] Full auth system (signup/login with JWT, no OTP)
- [x] Role-based access (user/admin/owner)
- [x] User dashboard with Quick Scan, stats, recent scans
- [x] URL/File scanning with simulated risk analysis
- [x] Scan result detail pages with metadata + IOCs
- [x] Scan history with search and truncation
- [x] Credit system (deduction on scan, history tracking)
- [x] Plans page (Free/Premium/Enterprise) with pricing
- [x] Admin dashboard (Overview, Users, Scans, Analytics, Owner tabs)
- [x] **Owner Plan Management** — promote/demote user plans from Admin > Users tab with confirmation dialog, auto-credit update, audit logging
- [x] **Payment Settings** — Owner Controls > Payment Settings tab for dynamic Razorpay key management (encrypted storage, test connection, no restart needed)
- [x] Owner Controls (Create Admin, Payment Settings, Audit Logs, System Info + Quick Actions)
- [x] Modular payment gateway architecture (Razorpay active, Stripe/PayPal slots ready)
- [x] Account settings (change email/password/username)
- [x] Notifications system
- [x] Audit logging for all sensitive actions
- [x] Text overflow fix for long URLs/filenames
- [x] OTP system removed (direct signup/login)

## MOCKED Features
- **Scanning engine**: Simulated risk analysis (not real security scanning)
- **Razorpay**: Demo keys in .env — create-order fails without real keys. Owner can update via Payment Settings.

## Backlog / Future Tasks
- [ ] Complete Razorpay integration with real API keys (owner can set via UI)
- [ ] Add Stripe gateway support
- [ ] Add PayPal gateway support
- [ ] Production hardening (JWT secret rotation, rate limiting, security headers)
- [ ] Real scanning engine integration
- [ ] Email notifications (SendGrid/SES)
- [ ] PDF report export for scans
- [ ] Team workspace for Enterprise plan
