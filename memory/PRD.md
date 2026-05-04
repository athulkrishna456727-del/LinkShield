# Link Shield - Product Requirements Document

## Original Problem Statement
Full-stack SaaS cybersecurity scanning platform with URL/file scanning, credits, premium/enterprise plans, admin panel, and real security API integrations.

## Tech Stack
- **Backend**: FastAPI (Python) on port 8001
- **Frontend**: React.js on port 3000
- **Database**: MongoDB (motor async driver)
- **Queue**: Redis (priority scanning queue)
- **PDF**: fpdf2 library
- **UI**: Shadcn/UI + Tailwind CSS, dark cybersecurity theme, green (#00FF94) accent
- **Auth**: JWT + API Key (dual auth)

## Architecture
```
/app/backend/
├── server.py              # All API endpoints (plan-gated, role-based)
├── services/
│   ├── __init__.py        # Real scanning (VT, urlscan, URLhaus, MalwareBazaar) + IOC extraction
│   ├── queue.py           # Redis priority queue
│   ├── reports.py         # PDF generation + email delivery
│   └── webhooks.py        # Webhook delivery service
├── .env                   # All config (MONGO_URL, REDIS_URL, VT_API_KEY, etc.)
└── requirements.txt

/app/frontend/src/
├── pages/
│   ├── Dashboard.js       # Quick Actions (plan-gated), stats, recent scans
│   ├── Scan.js            # URL + file scanning
│   ├── ScanResult.js      # Risk score, threats, IOC table, PDF/CSV export
│   ├── History.js         # Scan history
│   ├── Plans.js           # Dynamic pricing from DB
│   ├── ApiKeys.js         # API key management (Premium+)
│   ├── Reports.js         # PDF download + email schedule (Premium+)
│   ├── Teams.js           # Team workspace (Enterprise)
│   ├── Webhooks.js        # Webhook management (Enterprise)
│   ├── AdminDashboard.js  # User mgmt + plan change (Admin/Owner)
│   └── OwnerControls.js   # Pricing, Payment Gateway, Create Admin, Audit Logs
├── context/AuthContext.js
└── App.js                 # All routes
```

## DB Collections
- **users**: {id, email, username, password_hash, name, role, plan, credits, api_key, api_call_count, api_call_reset, created_at}
- **scans**: {id, user_id, scan_type, target, status, risk_score, risk_level, threats, raw_results, created_at}
- **iocs**: {scan_id, ioc_type, value, confidence, created_at}
- **teams**: {id, name, owner_id, created_at}
- **team_members**: {id, team_id, user_id, role}
- **webhooks**: {id, user_id, url, events, secret, enabled, created_at}
- **webhook_deliveries**: {webhook_id, event_type, payload, response_status, success, created_at}
- **report_schedules**: {id, user_id, frequency, format, last_sent, next_send, enabled}
- **site_settings**: {key, value, updated_by, updated_at}
- **payment_settings**: {_id: "razorpay", key_id, key_secret_encrypted, is_active, updated_at}
- **audit_logs**: {id, action_type, performed_by, target_user, details, timestamp}
- **notifications**: {id, user_id, type, message, read, created_at}
- **credit_history**: {user_id, amount, reason, admin_id, timestamp}

## Plan Features
| Feature | Free | Premium | Enterprise |
|---------|------|---------|------------|
| Credits/month | 50 | 500 | Unlimited |
| Scan priority | Normal (3) | High (2) | Highest (1) |
| Scanners | URLhaus + VT | + urlscan.io | + All |
| IOC Export | No | CSV/JSON | CSV/JSON |
| API Access | No | 1000/day | 10,000/day |
| PDF Reports | No | Yes | Yes |
| Email Reports | No | Yes | Yes |
| Teams | No | No | Up to 50 |
| Webhooks | No | No | Up to 10 |

## Test Credentials
- **Owner**: athulkrishna456727@gmail.com / #AThr401012#
- **Admin**: athulmark401012@gmail.com / dgskgsnskz
- **API Key**: ls_4263f7e699fae9e67ff7656deb491fd3467dec81685e13bbe77b4d621b69c358

## What's Been Implemented (All features have REAL working code)
- [x] JWT auth (signup/login) + API key auth
- [x] Role-based access (user/admin/owner)
- [x] Plan-gated feature access (free/premium/enterprise)
- [x] Real URL scanning (VirusTotal + urlscan.io + URLhaus) with graceful fallback when keys missing
- [x] Real file scanning (VirusTotal + MalwareBazaar + 7 local heuristic scanners: PE, PDF, ZIP, DOC, APK, Image, generic)
- [x] **Sensitivity slider** (Low/Normal/High/Aggressive) on Scan page — sent with both URL and File scans
- [x] **Rich ScanResult page**: sensitivity badge, file type detected, engines x/y, explanations list, heuristic findings, cache indicator
- [x] **24h scan cache** keyed by (url|hash, sensitivity, plan) — re-evaluates on sensitivity change
- [x] IOC extraction from scan results
- [x] IOC export (CSV/JSON) for Premium+
- [x] Redis priority queue for scanning
- [x] API key system with rate limiting
- [x] PDF scan reports (per-scan + summary)
- [x] Email report scheduling (daily/weekly/monthly)
- [x] Teams workspace (Enterprise, up to 50 members)
- [x] Webhooks (Enterprise, up to 10 endpoints)
- [x] Webhook test ping + delivery history
- [x] Owner dynamic price control (no code changes needed)
- [x] Owner payment gateway settings (encrypted storage)
- [x] Admin user plan management with confirmation dialog
- [x] Audit logging for all sensitive actions
- [x] Credit system with plan-based deduction
- [x] Scan history with truncation

## Environment Variables Needed
```
MONGO_URL=mongodb://localhost:27017
DB_NAME=test_database
REDIS_URL=redis://localhost:6379
JWT_SECRET=<strong-secret>
VT_API_KEY=<your-virustotal-key>
URLSCAN_API_KEY=<your-urlscan-key>
SMTP_HOST=<smtp-host>
SMTP_PORT=587
SMTP_USER=<email>
SMTP_PASSWORD=<password>
SMTP_FROM=noreply@linkshield.io
RAZORPAY_KEY_ID=<fallback-key>
RAZORPAY_KEY_SECRET=<fallback-secret>
```

## Backlog / Future Tasks
- [ ] Provide real VirusTotal API key for full scanning
- [ ] Provide real urlscan.io API key for enhanced analysis
- [ ] Configure SMTP for email report delivery
- [ ] Complete Razorpay payment flow with real keys
- [ ] Add Stripe gateway support
- [ ] Add PayPal gateway support
- [ ] Background scan worker (currently synchronous)
- [ ] Rate limiting middleware for all endpoints
- [ ] User password reset flow
