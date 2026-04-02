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
- **credit_history**: {id, user_id, amount, reason, scan_id, admin_id, timestamp}
- **notifications**: {id, user_id, type, message, read, created_at}
- **activity_logs**: {id, user_id, action, details, timestamp}
- **system_settings**: {_id: "main", maintenance_mode, scan costs, file size limits}

## Key API Endpoints
- `/api/auth/{signup, login, me}`
- `/api/account/{email, password, username}`
- `/api/scan/{url, file, {scan_id}, history/list}`
- `/api/user/{profile, stats, credits/history, notifications}`
- `/api/billing/{plans, upgrade, create-order, verify-payment, webhook, history}`
- `/api/admin/{users, stats, scans, analytics, activity}`
- `/api/owner/{create-admin, remove-admin, admins, audit-logs, system-settings, revenue}`

## Test Credentials
- **Owner**: athulkrishna456727@gmail.com / #AThr401012#
- **Admin**: athulmark401012@gmail.com / dgskgsnskz

## What's Been Implemented
- [x] Full auth system (signup/login with JWT, no OTP)
- [x] Role-based access (user/admin/owner)
- [x] User dashboard with Quick Scan, stats, recent scans
- [x] URL scanning with simulated risk analysis
- [x] File scanning with simulated analysis
- [x] Scan result detail pages with metadata + IOCs
- [x] Scan history with search and truncation
- [x] Credit system (deduction on scan, history tracking)
- [x] Plans page (Free/Premium/Enterprise) with pricing
- [x] Admin dashboard (Overview, Users, Scans, Analytics tabs)
- [x] Owner Controls (Create Admin, Audit Logs, System Info + Quick Actions)
- [x] Account settings (change email/password/username)
- [x] Notifications system
- [x] Audit logging for sensitive actions
- [x] Text overflow fix for long URLs/filenames
- [x] OTP system removed (direct signup/login)

## MOCKED Features
- **Scanning engine**: Simulated risk analysis (not real security scanning)
- **Razorpay**: Placeholder demo keys — create-order fails (needs real keys)

## Backlog / Future Tasks
- [ ] Complete Razorpay integration with real API keys
- [ ] Production hardening (JWT secret rotation, rate limiting, security headers)
- [ ] Real scanning engine integration
- [ ] Email notifications (SendGrid/SES)
- [ ] PDF report export for scans
- [ ] Team workspace for Enterprise plan
