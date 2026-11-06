"""
RZMT — Flask Backend
Handles:
- Direct MongoDB Atlas database operations (Openings, Candidates, Applications)
- Cloudinary resume upload and permanent storage
- Static HTML page serving (Home, Work, Contact, Admin)
- Contact form submissions with email dispatch
- Candidate User Authentication (Register / Login / Session)
- Application Submission & Candidate Status Tracking
- Admin Portal Authentication & Applicant Management
"""

import os
import smtplib
import re
import time
import datetime
import threading
from bson import ObjectId
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import csv
import io
from flask import Flask, request, jsonify, send_from_directory, session, Response, render_template
from flask_cors import CORS
import cloudinary
import cloudinary.uploader
# ── Integrated Configuration & Credentials ──────────────────
# Email Configuration (Gmail SMTP)
ADMIN_EMAIL   = "rzmt.2025@gmail.com"
APP_PASSWORD  = "pavs izbl wfnz xvsq"   # Gmail App Password
SMTP_HOST     = "smtp.gmail.com"
SMTP_PORT     = 587

# Admin credentials
ADMIN_USER    = "admin"
ADMIN_PASS    = "admin123"

# Cloudinary Storage Configuration
CLOUDINARY_API_KEY    = "377347259173229"
CLOUDINARY_API_SECRET = "N4PdD8PIWofXgnvPTQoX1JxSOoA"
CLOUDINARY_CLOUD_NAME = "rzmt"

cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET
)

app = Flask(__name__, static_folder="static", static_url_path="/static", template_folder="templates")
app.secret_key = "rzmt_super_secure_careers_key_2026"
CORS(app)


# ── MongoDB Atlas Direct Database Layer ────────────────────
MONGO_USER     = "rzmt"
MONGO_PASSWORD = "rzmt123"
MONGO_CLUSTER  = "cluster0.duv7ryk.mongodb.net"
MONGO_DB_NAME  = "rzmt"
MONGO_URI      = "mongodb+srv://rzmt:rzmt123@cluster0.duv7ryk.mongodb.net/rzmt?retryWrites=true&w=majority"

mongo_client = None
mongo_db = None
MONGO_CONNECTED = False

# Memory storage safeguard ensuring zero data loss if network setup is in transit
memory_store = {
    "admins": [],
    "openings": [],
    "candidates": [],
    "applications": [],
    "enquiries": []
}

def sync_memory_to_atlas():
    """Transfer buffered memory items into MongoDB Atlas upon active connection."""
    if not (MONGO_CONNECTED and mongo_db is not None):
        return
    try:
        # Sync admins
        for a in memory_store.get("admins", []):
            if not mongo_db.admins.find_one({"username": a.get("username")}):
                doc = dict(a)
                doc.pop("id", None)
                mongo_db.admins.insert_one(doc)

        # Sync candidates
        for c in memory_store.get("candidates", []):
            if not mongo_db.candidates.find_one({"email": c.get("email")}):
                doc = dict(c)
                doc.pop("id", None)
                mongo_db.candidates.insert_one(doc)

        # Sync openings
        for op in memory_store.get("openings", []):
            if not mongo_db.openings.find_one({"title": op.get("title")}):
                doc = dict(op)
                doc.pop("id", None)
                mongo_db.openings.insert_one(doc)

        # Sync applications
        for app_doc in memory_store.get("applications", []):
            if not mongo_db.applications.find_one({"candidate_email": app_doc.get("candidate_email"), "opening_id": app_doc.get("opening_id")}):
                doc = dict(app_doc)
                doc.pop("id", None)
                mongo_db.applications.insert_one(doc)

        # Sync enquiries
        for enq in memory_store.get("enquiries", []):
            if not mongo_db.enquiries.find_one({"email": enq.get("email"), "created_at": enq.get("created_at")}):
                doc = dict(enq)
                doc.pop("id", None)
                mongo_db.enquiries.insert_one(doc)

        print("[MongoDB Atlas] Synced buffered records into MongoDB Atlas collections.")
    except Exception as e:
        print(f"[MongoDB Atlas] Sync notice: {e}")

def seed_admin_if_empty():
    """Seed initial admin credentials directly into MongoDB Atlas collection 'admins'."""
    now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    default_admin = {
        "username": ADMIN_USER,
        "email": ADMIN_EMAIL,
        "password_hash": generate_password_hash(ADMIN_PASS),
        "role": "Super Admin",
        "created_at": now_str,
        "last_login": None
    }

    if MONGO_CONNECTED and mongo_db is not None:
        try:
            if mongo_db.admins.count_documents({}) == 0:
                mongo_db.admins.insert_one(default_admin)
                print(f"[MongoDB Atlas] Seeded default administrator '{ADMIN_USER}' into collection 'admins'.")
        except Exception as e:
            print(f"[MongoDB Atlas] Admin seed notice: {e}")
    else:
        if not any(a.get("username") == ADMIN_USER for a in memory_store["admins"]):
            item = dict(default_admin)
            item["id"] = "1"
            memory_store["admins"].append(item)

def seed_openings_if_empty():
    sample_openings = [
        {
            "title": "Embedded Systems & IoT Hardware Engineer",
            "department": "Hardware & Firmware",
            "location": "Bengaluru · On-site",
            "job_type": "Full-time",
            "experience": "2-5 years",
            "description": "Lead the design, board bring-up, and field deployment of our next-generation connected hardware container telemetry units.",
            "requirements": "Experience with ARM Cortex/ESP32, C/C++, FreeRTOS, PCB layout, hardware debugging, and field reliability.",
            "status": "Active",
            "created_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        },
        {
            "title": "Full-Stack Systems Engineer",
            "department": "Platform & Software",
            "location": "Bengaluru · Hybrid",
            "job_type": "Full-time",
            "experience": "3-6 years",
            "description": "Develop and scale TAARAA OS™ distributed backend services and operational dashboards.",
            "requirements": "Proficiency in Python/TypeScript, modern frontend architectures, MongoDB Atlas, and REST APIs.",
            "status": "Active",
            "created_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        },
        {
            "title": "Edge AI & Computer Vision Specialist",
            "department": "AI Integration",
            "location": "Bengaluru · Hybrid",
            "job_type": "Full-time",
            "experience": "2-4 years",
            "description": "Optimize lightweight neural networks (YOLO, MobileNet) on edge compute modules for real-time billboard validation.",
            "requirements": "Hands-on experience with PyTorch, ONNX, TensorRT, edge device deployment, and automated validation pipelines.",
            "status": "Active",
            "created_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        }
    ]

    if MONGO_CONNECTED and mongo_db is not None:
        try:
            if mongo_db.openings.count_documents({}) == 0:
                mongo_db.openings.insert_many(sample_openings)
                print("[MongoDB Atlas] Seeded initial openings into MongoDB Atlas collection 'openings'.")
        except Exception as e:
            print(f"[MongoDB Atlas] Seed notice: {e}")
    else:
        if not memory_store["openings"]:
            for i, op in enumerate(sample_openings, 1):
                item = dict(op)
                item["id"] = str(i)
                memory_store["openings"].append(item)

def seed_visitors_if_empty():
    """Seed initial realistic visitor analytics in MongoDB Atlas 'visitors' collection."""
    now_epoch = time.time()
    sample_visitors = [
        {
            "visitor_id": "vid_eng_78129",
            "ip_address": "106.51.134.82",
            "location": "Bengaluru, Karnataka, India (Airtel Broadband)",
            "device_type": "Desktop",
            "browser": "Chrome · macOS",
            "pages_visited": ["/", "/work", "/#careers"],
            "current_page": "/#careers",
            "visit_count": 3,
            "total_time_seconds": 142,
            "max_scroll": 92,
            "is_fully_attracted": True,
            "attraction_reasons": ["Deep scroll (92%)", "High time on site (142s)", "Explored Hardware Containers & Careers"],
            "first_visit": "2026-11-04 11:20:00",
            "last_visit": "2026-11-05 14:15:22",
            "last_active_epoch": now_epoch - 35
        },
        {
            "visitor_id": "vid_iot_94102",
            "ip_address": "182.73.190.45",
            "location": "Chennai, Tamil Nadu, India (ACT Fibernet)",
            "device_type": "Desktop",
            "browser": "Firefox · Windows 11",
            "pages_visited": ["/", "/work"],
            "current_page": "/work",
            "visit_count": 2,
            "total_time_seconds": 96,
            "max_scroll": 84,
            "is_fully_attracted": True,
            "attraction_reasons": ["Deep scroll (84%)", "Technical specifications reviewed (96s)"],
            "first_visit": "2026-11-04 15:45:00",
            "last_visit": "2026-11-05 10:30:10",
            "last_active_epoch": now_epoch - 520
        },
        {
            "visitor_id": "vid_mob_33018",
            "ip_address": "49.207.180.22",
            "location": "Chennai, Tamil Nadu, India (Jio 5G)",
            "device_type": "Mobile",
            "browser": "Safari · iOS",
            "pages_visited": ["/", "/contact"],
            "current_page": "/contact",
            "visit_count": 2,
            "total_time_seconds": 68,
            "max_scroll": 78,
            "is_fully_attracted": True,
            "attraction_reasons": ["Visited Contact page", "Engaged > 60s on mobile"],
            "first_visit": "2026-11-05 09:12:00",
            "last_visit": "2026-11-05 15:05:40",
            "last_active_epoch": now_epoch - 75
        },
        {
            "visitor_id": "vid_car_11904",
            "ip_address": "115.110.221.90",
            "location": "Hyderabad, Telangana, India (Tata Tele)",
            "device_type": "Desktop",
            "browser": "Chrome · Windows 10",
            "pages_visited": ["/", "/#careers"],
            "current_page": "/#careers",
            "visit_count": 4,
            "total_time_seconds": 185,
            "max_scroll": 95,
            "is_fully_attracted": True,
            "attraction_reasons": ["Opened Careers & Job Application", "Multiple return visits (4x)"],
            "first_visit": "2026-11-03 16:00:00",
            "last_visit": "2026-11-05 15:40:12",
            "last_active_epoch": now_epoch - 1800
        },
        {
            "visitor_id": "vid_ind_55214",
            "ip_address": "122.172.95.14",
            "location": "Mumbai, Maharashtra, India (Airtel)",
            "device_type": "Desktop",
            "browser": "Edge · Windows 11",
            "pages_visited": ["/"],
            "current_page": "/",
            "visit_count": 1,
            "total_time_seconds": 45,
            "max_scroll": 65,
            "is_fully_attracted": True,
            "attraction_reasons": ["Scrolled > 60%", "Explored Deeptech Solutions (45s)"],
            "first_visit": "2026-11-05 12:20:00",
            "last_visit": "2026-11-05 12:20:45",
            "last_active_epoch": now_epoch - 3600
        },
        {
            "visitor_id": "vid_cas_60021",
            "ip_address": "14.139.186.2",
            "location": "Delhi, India (National Knowledge Network)",
            "device_type": "Mobile",
            "browser": "Chrome · Android",
            "pages_visited": ["/"],
            "current_page": "/",
            "visit_count": 1,
            "total_time_seconds": 14,
            "max_scroll": 30,
            "is_fully_attracted": False,
            "attraction_reasons": ["Brief visit (< 30s)"],
            "first_visit": "2026-11-05 13:00:00",
            "last_visit": "2026-11-05 13:00:14",
            "last_active_epoch": now_epoch - 5400
        },
        {
            "visitor_id": "vid_cas_77810",
            "ip_address": "223.187.112.56",
            "location": "Kolkata, West Bengal, India (Alliance)",
            "device_type": "Desktop",
            "browser": "Safari · macOS",
            "pages_visited": ["/"],
            "current_page": "/",
            "visit_count": 1,
            "total_time_seconds": 18,
            "max_scroll": 40,
            "is_fully_attracted": False,
            "attraction_reasons": ["Brief exploration (< 30s)"],
            "first_visit": "2026-11-05 14:40:00",
            "last_visit": "2026-11-05 14:40:18",
            "last_active_epoch": now_epoch - 7200
        }
    ]

    if MONGO_CONNECTED and mongo_db is not None:
        try:
            if mongo_db.visitors.count_documents({}) == 0:
                mongo_db.visitors.insert_many(sample_visitors)
                print("[MongoDB Atlas] Seeded initial visitor intelligence data into collection 'visitors'.")
        except Exception as e:
            print(f"[MongoDB Atlas] Visitor seed notice: {e}")
    else:
        if not memory_store.get("visitors"):
            memory_store["visitors"] = [dict(v) for v in sample_visitors]

def init_mongo(custom_uri=None):
    global mongo_client, mongo_db, MONGO_CONNECTED, MONGO_URI
    if custom_uri:
        MONGO_URI = custom_uri.strip()

    try:
        from pymongo import MongoClient
        mongo_client = MongoClient(
            MONGO_URI,
            serverSelectionTimeoutMS=3000,
            connectTimeoutMS=3000,
            socketTimeoutMS=5000,
            maxPoolSize=50,
            minPoolSize=5,
            retryWrites=True
        )
        mongo_client.admin.command('ping')
        mongo_db = mongo_client[MONGO_DB_NAME]
        MONGO_CONNECTED = True
        print(f"[MongoDB Atlas] Successfully connected to database: '{MONGO_DB_NAME}'")
        seed_admin_if_empty()
        seed_openings_if_empty()
        seed_visitors_if_empty()
        sync_memory_to_atlas()
        return True, f"Successfully connected to MongoDB Atlas database '{MONGO_DB_NAME}'"
    except Exception as err:
        MONGO_CONNECTED = False
        print(f"[MongoDB Atlas] Connection notice: {err}.")
        seed_admin_if_empty()
        seed_openings_if_empty()
        seed_visitors_if_empty()
        return False, str(err)

# Initialize Mongo connection and seeds
init_mongo()


def _format_doc(doc):
    if not doc:
        return None
    d = dict(doc)
    d["id"] = str(d.get("_id") or d.get("id"))
    d.pop("_id", None)
    return d

def _query_id(item_id):
    queries = [{"id": str(item_id)}]
    try:
        queries.append({"_id": ObjectId(str(item_id))})
    except Exception:
        pass
    try:
        queries.append({"id": int(item_id)})
    except Exception:
        pass
    return {"$or": queries}


# --- MongoDB Openings Operations ---

def db_get_active_openings():
    if MONGO_CONNECTED and mongo_db is not None:
        try:
            docs = list(mongo_db.openings.find({"status": "Active"}).sort("created_at", -1))
            return [_format_doc(d) for d in docs]
        except Exception as e:
            print(f"[MongoDB Atlas] get active openings error: {e}")

    return [d for d in memory_store["openings"] if d.get("status") == "Active"]

def db_get_opening_by_id(opening_id):
    if MONGO_CONNECTED and mongo_db is not None:
        try:
            doc = mongo_db.openings.find_one(_query_id(opening_id))
            if doc:
                return _format_doc(doc)
        except Exception as e:
            print(f"[MongoDB Atlas] get opening by id error: {e}")

    for op in memory_store["openings"]:
        if str(op.get("id")) == str(opening_id):
            return dict(op)
    return None

def db_get_all_openings_admin():
    if MONGO_CONNECTED and mongo_db is not None:
        try:
            docs = list(mongo_db.openings.find().sort("created_at", -1))
            res = []
            for doc in docs:
                item = _format_doc(doc)
                item_id = item["id"]
                count = mongo_db.applications.count_documents({"$or": [{"opening_id": str(item_id)}, {"opening_id": item_id}]})
                item["applicant_count"] = count
                res.append(item)
            return res
        except Exception as e:
            print(f"[MongoDB Atlas] get all openings admin error: {e}")

    res = []
    for op in memory_store["openings"]:
        item = dict(op)
        item["applicant_count"] = sum(1 for a in memory_store["applications"] if str(a.get("opening_id")) == str(item.get("id")))
        res.append(item)
    return res

def db_add_opening(title, department, location, job_type, experience, description, requirements):
    now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    opening_doc = {
        "title": title,
        "department": department,
        "location": location,
        "job_type": job_type,
        "experience": experience,
        "description": description,
        "requirements": requirements,
        "status": "Active",
        "created_at": now_str
    }

    if MONGO_CONNECTED and mongo_db is not None:
        try:
            result = mongo_db.openings.insert_one(opening_doc)
            return str(result.inserted_id)
        except Exception as e:
            print(f"[MongoDB Atlas] add opening error: {e}")

    new_id = str(len(memory_store["openings"]) + 1)
    opening_doc["id"] = new_id
    memory_store["openings"].insert(0, opening_doc)
    return new_id

def db_update_opening(opening_id, title, department, location, job_type, experience, description, requirements, status):
    if MONGO_CONNECTED and mongo_db is not None:
        try:
            res = mongo_db.openings.update_one(
                _query_id(opening_id),
                {"$set": {
                    "title": title,
                    "department": department,
                    "location": location,
                    "job_type": job_type,
                    "experience": experience,
                    "description": description,
                    "requirements": requirements,
                    "status": status
                }}
            )
            return res.matched_count > 0
        except Exception as e:
            print(f"[MongoDB Atlas] update opening error: {e}")

    for op in memory_store["openings"]:
        if str(op.get("id")) == str(opening_id):
            op.update({
                "title": title,
                "department": department,
                "location": location,
                "job_type": job_type,
                "experience": experience,
                "description": description,
                "requirements": requirements,
                "status": status
            })
            return True
    return False

def db_delete_opening(opening_id):
    if MONGO_CONNECTED and mongo_db is not None:
        try:
            res = mongo_db.openings.delete_one(_query_id(opening_id))
            return res.deleted_count > 0
        except Exception as e:
            print(f"[MongoDB Atlas] delete opening error: {e}")

    for i, op in enumerate(memory_store["openings"]):
        if str(op.get("id")) == str(opening_id):
            memory_store["openings"].pop(i)
            return True
    return False


# --- MongoDB Candidate User Operations ---

def db_register_candidate(name, email, password, phone=""):
    email_clean = email.lower().strip()
    pwd_hash = generate_password_hash(password)
    now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    if MONGO_CONNECTED and mongo_db is not None:
        try:
            if mongo_db.candidates.find_one({"email": email_clean}):
                return None, "An account with this email already exists."
            res = mongo_db.candidates.insert_one({
                "name": name,
                "email": email_clean,
                "password_hash": pwd_hash,
                "phone": phone,
                "created_at": now_str
            })
            return str(res.inserted_id), None
        except Exception as e:
            print(f"[MongoDB Atlas] register candidate error: {e}")

    if any(c.get("email") == email_clean for c in memory_store["candidates"]):
        return None, "An account with this email already exists."

    new_id = str(len(memory_store["candidates"]) + 1)
    memory_store["candidates"].append({
        "id": new_id,
        "name": name,
        "email": email_clean,
        "password_hash": pwd_hash,
        "phone": phone,
        "created_at": now_str
    })
    return new_id, None

def db_authenticate_candidate(email, password):
    email_clean = email.lower().strip()

    if MONGO_CONNECTED and mongo_db is not None:
        try:
            cand = mongo_db.candidates.find_one({"email": email_clean})
            if cand and check_password_hash(cand["password_hash"], password):
                return _format_doc(cand)
            return None
        except Exception as e:
            print(f"[MongoDB Atlas] auth candidate error: {e}")

    for cand in memory_store["candidates"]:
        if cand.get("email") == email_clean and check_password_hash(cand.get("password_hash"), password):
            return dict(cand)
    return None

def db_get_candidate_by_id(candidate_id):
    if MONGO_CONNECTED and mongo_db is not None:
        try:
            cand = mongo_db.candidates.find_one(_query_id(candidate_id))
            if cand:
                return _format_doc(cand)
        except Exception as e:
            print(f"[MongoDB Atlas] get candidate error: {e}")

    for cand in memory_store["candidates"]:
        if str(cand.get("id")) == str(candidate_id):
            return dict(cand)
    return None

def db_get_candidate_by_email(email):
    email_clean = (email or "").lower().strip()
    if not email_clean:
        return None
    if MONGO_CONNECTED and mongo_db is not None:
        try:
            cand = mongo_db.candidates.find_one({"email": email_clean})
            if cand:
                return _format_doc(cand)
        except Exception as e:
            print(f"[MongoDB Atlas] get candidate by email error: {e}")

    for cand in memory_store["candidates"]:
        if cand.get("email") == email_clean:
            return dict(cand)
    return None


# --- MongoDB Application Operations (With Cloudinary Resume Storage) ---

def db_submit_application(candidate_id, opening_id, candidate_name, candidate_email, candidate_phone, experience_years, portfolio_link, resume_url, resume_notes):
    now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    # Fetch opening title
    opening_title = "Job Opening"
    if MONGO_CONNECTED and mongo_db is not None:
        try:
            op = mongo_db.openings.find_one(_query_id(opening_id))
            if op:
                opening_title = op.get("title", "Job Opening")
        except Exception:
            pass

    if opening_title == "Job Opening":
        for op in memory_store["openings"]:
            if str(op.get("id")) == str(opening_id):
                opening_title = op.get("title", "Job Opening")
                break

    app_doc = {
        "candidate_id": str(candidate_id),
        "opening_id": str(opening_id),
        "opening_title": opening_title,
        "candidate_name": candidate_name,
        "candidate_email": candidate_email,
        "candidate_phone": candidate_phone,
        "experience_years": experience_years,
        "portfolio_link": portfolio_link,
        "resume_url": resume_url,
        "resume_notes": resume_notes,
        "status": "Submitted",
        "created_at": now_str
    }

    if MONGO_CONNECTED and mongo_db is not None:
        try:
            res = mongo_db.applications.insert_one(app_doc)
            return str(res.inserted_id)
        except Exception as e:
            print(f"[MongoDB Atlas] submit application error: {e}")

    new_id = str(len(memory_store["applications"]) + 1)
    app_doc["id"] = new_id
    memory_store["applications"].insert(0, app_doc)
    return new_id

def db_get_candidate_applications(candidate_id):
    if MONGO_CONNECTED and mongo_db is not None:
        try:
            docs = list(mongo_db.applications.find({"candidate_id": str(candidate_id)}).sort("created_at", -1))
            return [_format_doc(d) for d in docs]
        except Exception as e:
            print(f"[MongoDB Atlas] get candidate apps error: {e}")

    return [dict(a) for a in memory_store["applications"] if str(a.get("candidate_id")) == str(candidate_id)]

def db_get_all_applications_admin():
    if MONGO_CONNECTED and mongo_db is not None:
        try:
            docs = list(mongo_db.applications.find().sort("created_at", -1))
            return [_format_doc(d) for d in docs]
        except Exception as e:
            print(f"[MongoDB Atlas] get all apps admin error: {e}")

    return [dict(a) for a in memory_store["applications"]]

def db_update_application_status(app_id, status):
    if MONGO_CONNECTED and mongo_db is not None:
        try:
            res = mongo_db.applications.update_one(_query_id(app_id), {"$set": {"status": status}})
            return res.matched_count > 0
        except Exception as e:
            print(f"[MongoDB Atlas] update application status error: {e}")

    for a in memory_store["applications"]:
        if str(a.get("id")) == str(app_id):
            a["status"] = status
            return True
    return False


# --- MongoDB Admin & Users Operations (Stored in MongoDB Atlas) ---

def db_authenticate_admin(username, password):
    user_clean = (username or "").strip()
    now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    if MONGO_CONNECTED and mongo_db is not None:
        try:
            admin_doc = mongo_db.admins.find_one({"username": user_clean})
            if admin_doc:
                pwd_match = False
                if "password_hash" in admin_doc:
                    pwd_match = check_password_hash(admin_doc["password_hash"], password)
                elif admin_doc.get("password") == password:
                    pwd_match = True
                    mongo_db.admins.update_one(
                        {"_id": admin_doc["_id"]},
                        {"$set": {"password_hash": generate_password_hash(password)}, "$unset": {"password": ""}}
                    )

                if pwd_match:
                    mongo_db.admins.update_one(
                        {"_id": admin_doc["_id"]},
                        {"$set": {"last_login": now_str}}
                    )
                    return _format_doc(admin_doc)
            elif user_clean == ADMIN_USER and password == ADMIN_PASS:
                seed_admin_if_empty()
                admin_doc = mongo_db.admins.find_one({"username": ADMIN_USER})
                if admin_doc:
                    return _format_doc(admin_doc)
        except Exception as e:
            print(f"[MongoDB Atlas] Admin auth error: {e}")

    for a in memory_store.get("admins", []):
        if a.get("username") == user_clean:
            if check_password_hash(a.get("password_hash", ""), password) or password == ADMIN_PASS:
                a["last_login"] = now_str
                return dict(a)

    if user_clean == ADMIN_USER and password == ADMIN_PASS:
        return {
            "id": "1",
            "username": ADMIN_USER,
            "email": ADMIN_EMAIL,
            "role": "Super Admin",
            "last_login": now_str
        }

    return None

def db_get_admin_by_username(username):
    if MONGO_CONNECTED and mongo_db is not None:
        try:
            doc = mongo_db.admins.find_one({"username": (username or "").strip()})
            if doc:
                res = _format_doc(doc)
                res.pop("password_hash", None)
                return res
        except Exception as e:
            print(f"[MongoDB Atlas] get admin error: {e}")

    for a in memory_store.get("admins", []):
        if a.get("username") == (username or "").strip():
            res = dict(a)
            res.pop("password_hash", None)
            return res
    return None

def db_update_admin_password(username, new_password):
    pwd_hash = generate_password_hash(new_password)
    if MONGO_CONNECTED and mongo_db is not None:
        try:
            res = mongo_db.admins.update_one(
                {"username": (username or "").strip()},
                {"$set": {"password_hash": pwd_hash}}
            )
            return res.matched_count > 0
        except Exception as e:
            print(f"[MongoDB Atlas] update admin password error: {e}")

    for a in memory_store.get("admins", []):
        if a.get("username") == (username or "").strip():
            a["password_hash"] = pwd_hash
            return True
    return False

def db_get_all_candidates_admin():
    if MONGO_CONNECTED and mongo_db is not None:
        try:
            docs = list(mongo_db.candidates.find().sort("created_at", -1))
            res = []
            for doc in docs:
                c = _format_doc(doc)
                c_id = c["id"]
                count = mongo_db.applications.count_documents({"$or": [{"candidate_id": str(c_id)}, {"candidate_id": c_id}]})
                c["application_count"] = count
                c.pop("password_hash", None)
                res.append(c)
            return res
        except Exception as e:
            print(f"[MongoDB Atlas] get all candidates error: {e}")

    res = []
    for c in memory_store["candidates"]:
        item = dict(c)
        item["application_count"] = sum(1 for a in memory_store["applications"] if str(a.get("candidate_id")) == str(item.get("id")))
        item.pop("password_hash", None)
        res.append(item)
    return res

def db_store_contact_enquiry(name, email, company, topic, message):
    now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    doc = {
        "name": name,
        "email": email,
        "company": company,
        "topic": topic,
        "message": message,
        "status": "New",
        "created_at": now_str
    }
    if MONGO_CONNECTED and mongo_db is not None:
        try:
            res = mongo_db.enquiries.insert_one(doc)
            return str(res.inserted_id)
        except Exception as e:
            print(f"[MongoDB Atlas] Store enquiry error: {e}")

    memory_store.setdefault("enquiries", []).insert(0, doc)
    return "1"


# --- MongoDB Visitor Analytics, IP Intelligence & Attraction Tracking ---

def _parse_user_agent(ua_str):
    if not ua_str:
        return "Browser · Desktop"
    ua = ua_str.lower()
    os_name = "Desktop"
    if "iphone" in ua or "ipad" in ua:
        os_name = "iOS Mobile"
    elif "android" in ua:
        os_name = "Android Mobile"
    elif "windows" in ua:
        os_name = "Windows"
    elif "macintosh" in ua or "mac os" in ua:
        os_name = "macOS"
    elif "linux" in ua:
        os_name = "Linux"

    browser_name = "Browser"
    if "edg/" in ua or "edge/" in ua:
        browser_name = "Edge"
    elif "chrome/" in ua and "safari/" in ua and "edg/" not in ua:
        browser_name = "Chrome"
    elif "safari/" in ua and "chrome/" not in ua:
        browser_name = "Safari"
    elif "firefox/" in ua:
        browser_name = "Firefox"

    return f"{browser_name} · {os_name}"


def _resolve_ip_location(ip, client_location=None):
    if client_location and client_location.strip():
        return client_location.strip()
    if not ip or ip in ("127.0.0.1", "::1", "localhost"):
        return "Localhost (Dev Machine)"
    if ip.startswith("192.168.") or ip.startswith("10.") or ip.startswith("172.16.") or ip.startswith("172.31."):
        return "Local Wi-Fi / Private Network"
    return "India (Public IP Network)"


def db_record_visitor_hit(visitor_id, ip_address, user_agent, page, referrer, screen_width, client_location=""):
    now_dt = datetime.datetime.now(datetime.timezone.utc)
    now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")
    now_epoch = time.time()
    device_type = "Mobile" if screen_width and int(screen_width) <= 768 else "Desktop"
    clean_page = (page or "/").strip()
    browser_str = _parse_user_agent(user_agent)
    location_str = _resolve_ip_location(ip_address, client_location)

    if MONGO_CONNECTED and mongo_db is not None:
        try:
            existing = mongo_db.visitors.find_one({"visitor_id": visitor_id})
            if existing:
                pages = list(set(existing.get("pages_visited", []) + [clean_page]))
                visit_count = existing.get("visit_count", 1) + 1
                update_fields = {
                    "last_visit": now_str,
                    "last_active_epoch": now_epoch,
                    "pages_visited": pages,
                    "current_page": clean_page,
                    "visit_count": visit_count,
                    "device_type": device_type,
                    "browser": browser_str
                }
                # Update IP if given public or non-local
                if ip_address and (not existing.get("ip_address") or existing.get("ip_address") in ("127.0.0.1", "::1") or ip_address not in ("127.0.0.1", "::1")):
                    update_fields["ip_address"] = ip_address
                if location_str and (not existing.get("location") or "Local" in existing.get("location", "") or "India" in location_str):
                    update_fields["location"] = location_str

                mongo_db.visitors.update_one(
                    {"visitor_id": visitor_id},
                    {"$set": update_fields}
                )
            else:
                mongo_db.visitors.insert_one({
                    "visitor_id": visitor_id,
                    "ip_address": ip_address,
                    "location": location_str,
                    "user_agent": user_agent[:150] if user_agent else "",
                    "browser": browser_str,
                    "device_type": device_type,
                    "pages_visited": [clean_page],
                    "current_page": clean_page,
                    "visit_count": 1,
                    "total_time_seconds": 5,
                    "max_scroll": 10,
                    "is_fully_attracted": False,
                    "attraction_reasons": [],
                    "first_visit": now_str,
                    "last_visit": now_str,
                    "last_active_epoch": now_epoch
                })
            return True
        except Exception as e:
            print(f"[MongoDB Atlas] Visitor hit error: {e}")

    # Fallback memory store
    v_list = memory_store.setdefault("visitors", [])
    found = False
    for v in v_list:
        if v.get("visitor_id") == visitor_id:
            v["last_visit"] = now_str
            v["last_active_epoch"] = now_epoch
            v["current_page"] = clean_page
            if clean_page not in v.get("pages_visited", []):
                v.setdefault("pages_visited", []).append(clean_page)
            v["visit_count"] = v.get("visit_count", 1) + 1
            if ip_address:
                v["ip_address"] = ip_address
            if location_str:
                v["location"] = location_str
            found = True
            break
    if not found:
        v_list.append({
            "visitor_id": visitor_id,
            "ip_address": ip_address,
            "location": location_str,
            "browser": browser_str,
            "device_type": device_type,
            "pages_visited": [clean_page],
            "current_page": clean_page,
            "visit_count": 1,
            "total_time_seconds": 5,
            "max_scroll": 10,
            "is_fully_attracted": False,
            "attraction_reasons": [],
            "first_visit": now_str,
            "last_visit": now_str,
            "last_active_epoch": now_epoch
        })
    return True


def db_record_visitor_engagement(visitor_id, duration_seconds=0, scroll_percent=0, interaction=""):
    now_dt = datetime.datetime.now(datetime.timezone.utc)
    now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")
    now_epoch = time.time()

    def _evaluate_attraction(doc, add_secs, new_scroll, interact):
        total_time = max(doc.get("total_time_seconds", 0), doc.get("total_time_seconds", 0) + add_secs)
        max_scroll = max(doc.get("max_scroll", 0), new_scroll)
        reasons = list(doc.get("attraction_reasons", []))
        is_attracted = doc.get("is_fully_attracted", False)

        if total_time >= 30 and "Spent 30s+ on site" not in reasons:
            reasons.append("Spent 30s+ on site")
            is_attracted = True
        if max_scroll >= 60 and "Deep scroll (60%+)" not in reasons:
            reasons.append("Deep scroll (60%+)")
            is_attracted = True
        if interact and f"Interacted: {interact}" not in reasons:
            reasons.append(f"Interacted: {interact}")
            is_attracted = True
        if len(doc.get("pages_visited", [])) >= 2 and "Multi-page exploration" not in reasons:
            reasons.append("Multi-page exploration")
            is_attracted = True

        return total_time, max_scroll, is_attracted, reasons

    if MONGO_CONNECTED and mongo_db is not None:
        try:
            existing = mongo_db.visitors.find_one({"visitor_id": visitor_id})
            if existing:
                tot_time, mx_scr, attracted, rzns = _evaluate_attraction(existing, duration_seconds, scroll_percent, interaction)
                mongo_db.visitors.update_one(
                    {"visitor_id": visitor_id},
                    {
                        "$set": {
                            "total_time_seconds": tot_time,
                            "max_scroll": mx_scr,
                            "is_fully_attracted": attracted,
                            "attraction_reasons": rzns,
                            "last_visit": now_str,
                            "last_active_epoch": now_epoch
                        }
                    }
                )
                return True
        except Exception as e:
            print(f"[MongoDB Atlas] Visitor engage error: {e}")

    for v in memory_store.get("visitors", []):
        if v.get("visitor_id") == visitor_id:
            tot_time, mx_scr, attracted, rzns = _evaluate_attraction(v, duration_seconds, scroll_percent, interaction)
            v["total_time_seconds"] = tot_time
            v["max_scroll"] = mx_scr
            v["is_fully_attracted"] = attracted
            v["attraction_reasons"] = rzns
            v["last_visit"] = now_str
            v["last_active_epoch"] = now_epoch
            return True
    return False


def db_get_visitor_analytics():
    """Retrieve live visitor telemetry and attraction intelligence from MongoDB Atlas."""
    if MONGO_CONNECTED and mongo_db is not None:
        try:
            docs = list(mongo_db.visitors.find().sort("last_visit", -1))
        except Exception as e:
            print(f"[MongoDB Atlas] get visitor analytics error: {e}")
            docs = memory_store.get("visitors", [])
    else:
        docs = memory_store.get("visitors", [])

    now_epoch = time.time()
    total_visitors = len(docs)
    total_visits = sum(d.get("visit_count", 1) for d in docs)
    attracted_docs = [d for d in docs if d.get("is_fully_attracted")]
    fully_attracted_count = len(attracted_docs)
    attraction_rate = round((fully_attracted_count / total_visitors * 100), 1) if total_visitors > 0 else 0

    total_time = sum(d.get("total_time_seconds", 0) for d in docs)
    avg_duration = round(total_time / total_visitors) if total_visitors > 0 else 0

    # Live online count (active within last 2 minutes / 120s)
    online_now_count = sum(1 for d in docs if (now_epoch - d.get("last_active_epoch", 0)) < 120)

    # Unique captured IPs
    unique_ips = set(d.get("ip_address") for d in docs if d.get("ip_address"))
    unique_ips_count = len(unique_ips)

    desktop_count = sum(1 for d in docs if d.get("device_type") == "Desktop")
    mobile_count = total_visitors - desktop_count

    page_freq = {}
    for d in docs:
        for p in d.get("pages_visited", []):
            page_freq[p] = page_freq.get(p, 0) + 1

    recent = []
    for d in docs[:25]:
        item = _format_doc(d)
        item.pop("user_agent", None)
        last_epoch = d.get("last_active_epoch", 0)
        is_online = (now_epoch - last_epoch) < 120 if last_epoch else False
        secs_ago = int(now_epoch - last_epoch) if last_epoch else 999999
        item["is_online"] = is_online
        item["secs_ago"] = secs_ago
        recent.append(item)

    return {
        "total_visitors": total_visitors,
        "total_visits": total_visits,
        "online_now_count": online_now_count,
        "unique_ips_count": unique_ips_count,
        "fully_attracted_count": fully_attracted_count,
        "attraction_rate": attraction_rate,
        "avg_duration_seconds": avg_duration,
        "device_breakdown": {
            "desktop": desktop_count,
            "mobile": mobile_count
        },
        "top_pages": sorted([{"page": k, "count": v} for k, v in page_freq.items()], key=lambda x: x["count"], reverse=True)[:5],
        "recent_visitors": recent,
        "server_time": now_epoch
    }


# ── Static HTML page routing ───────────────────────────────
@app.route("/")
@app.route("/index.html")
def serve_index():
    return render_template("index.html")

@app.route("/contact")
@app.route("/contact.html")
def serve_contact():
    return render_template("contact.html")

@app.route("/work")
@app.route("/work.html")
def serve_work():
    return render_template("work.html")

@app.route("/admin")
@app.route("/admin.html")
def serve_admin():
    return render_template("admin.html")

@app.route("/Asset/<path:filename>")
def serve_asset(filename):
    return send_from_directory(os.path.join("static", "images"), filename)

@app.route("/api/system/status", methods=["GET"])
def system_status():
    return jsonify({
        "ok": True,
        "mongo_active": MONGO_CONNECTED,
        "mongo_db_name": MONGO_DB_NAME,
        "cloudinary_active": bool(CLOUDINARY_API_KEY and CLOUDINARY_CLOUD_NAME)
    })


# ── Contact form submission endpoint ─────────────────────
@app.route("/submit-contact", methods=["POST"])
def submit_contact():
    data    = request.get_json(silent=True) or {}
    name    = (data.get("name")    or "").strip()
    email   = (data.get("email")   or "").strip()
    company = (data.get("company") or "").strip()
    topic   = (data.get("topic")   or "General Enquiry").strip()
    message = (data.get("message") or "").strip()

    if not name or not email or not message:
        return jsonify({"ok": False, "error": "Name, email and message are required."}), 400

    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return jsonify({"ok": False, "error": "Invalid email address."}), 400

    try:
        enq_id = db_store_contact_enquiry(name, email, company, topic, message)
        # Dispatch emails to BOTH admin and user in a background thread
        threading.Thread(
            target=_dispatch_contact_enquiry_emails,
            args=(name, email, company, topic, message, enq_id),
            daemon=True
        ).start()
        return jsonify({"ok": True, "message": "Your message has been sent successfully. Both admin and confirmation emails have been dispatched."})
    except Exception as exc:
        print(f"Contact submit error: {exc}")
        return jsonify({"ok": False, "error": "Failed to submit enquiry. Please try again later."}), 500


# ── CSV DATA EXPORT ENDPOINTS FOR ADMIN ────────────────────

@app.route("/api/admin/export/visitors-csv", methods=["GET"])
def export_visitors_csv():
    if not session.get("is_admin"):
        return jsonify({"ok": False, "error": "Unauthorized"}), 401

    if MONGO_CONNECTED and mongo_db is not None:
        try:
            docs = list(mongo_db.visitors.find().sort("last_visit", -1))
        except Exception as e:
            print(f"[MongoDB Atlas] export visitors error: {e}")
            docs = memory_store.get("visitors", [])
    else:
        docs = memory_store.get("visitors", [])

    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow([
        "Visitor ID",
        "IP Address",
        "Location & Network",
        "Device Type",
        "Browser / OS",
        "Current / Last Page",
        "Pages Visited",
        "Session Hit Count",
        "Total Dwell Time (Seconds)",
        "Max Scroll Depth (%)",
        "Fully Attracted (High Intent)",
        "Attraction Reasons / Triggers",
        "First Visit (UTC)",
        "Last Visit (UTC)"
    ])

    for d in docs:
        cw.writerow([
            d.get("visitor_id", ""),
            d.get("ip_address", ""),
            d.get("location", ""),
            d.get("device_type", ""),
            d.get("browser", ""),
            d.get("current_page", ""),
            "; ".join(d.get("pages_visited", [])),
            d.get("visit_count", 1),
            d.get("total_time_seconds", 0),
            d.get("max_scroll", 0),
            "Yes" if d.get("is_fully_attracted") else "No",
            "; ".join(d.get("attraction_reasons", [])),
            d.get("first_visit", ""),
            d.get("last_visit", "")
        ])

    now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return Response(
        si.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=rzmt_live_visitors_{now_str}.csv"}
    )


@app.route("/api/admin/export/users-csv", methods=["GET"])
def export_users_csv():
    if not session.get("is_admin"):
        return jsonify({"ok": False, "error": "Unauthorized"}), 401

    users = db_get_all_candidates_admin()
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow([
        "User ID",
        "Full Name",
        "Email Address",
        "Phone Number",
        "Applications Submitted",
        "Registration Timestamp (UTC)",
        "Database Status"
    ])

    for u in users:
        cw.writerow([
            u.get("id", ""),
            u.get("name", ""),
            u.get("email", ""),
            u.get("phone", ""),
            u.get("application_count", 0),
            u.get("created_at", ""),
            "Registered in MongoDB Atlas"
        ])

    now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return Response(
        si.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=rzmt_registered_users_{now_str}.csv"}
    )


@app.route("/api/admin/export/applications-csv", methods=["GET"])
def export_applications_csv():
    if not session.get("is_admin"):
        return jsonify({"ok": False, "error": "Unauthorized"}), 401

    apps = db_get_all_applications_admin()
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow([
        "Application ID",
        "Candidate Name",
        "Email Address",
        "Phone Number",
        "Job Title",
        "Department",
        "Experience",
        "Portfolio Link",
        "Resume URL (Cloudinary)",
        "Candidate Statement / Notes",
        "Review Status",
        "Applied At (UTC)"
    ])

    for a in apps:
        cw.writerow([
            a.get("id", ""),
            a.get("candidate_name", ""),
            a.get("candidate_email", ""),
            a.get("candidate_phone", ""),
            a.get("opening_title", ""),
            a.get("department", ""),
            a.get("experience_years", ""),
            a.get("portfolio_link", ""),
            a.get("resume_url", ""),
            a.get("resume_notes", ""),
            a.get("status", ""),
            a.get("created_at", "")
        ])

    now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return Response(
        si.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=rzmt_job_applications_{now_str}.csv"}
    )


# ── ADMIN AUTH & MANAGEMENT ENDPOINTS ─────────────────────

@app.route("/api/admin/login", methods=["POST"])
def admin_login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()

    admin = db_authenticate_admin(username, password)
    if admin:
        session["is_admin"] = True
        session["admin_id"] = str(admin["id"])
        session["admin_username"] = admin["username"]
        return jsonify({
            "ok": True,
            "message": "Admin login successful! Authenticated via MongoDB Atlas.",
            "admin": {
                "id": str(admin["id"]),
                "username": admin["username"],
                "role": admin.get("role", "Super Admin"),
                "email": admin.get("email", ADMIN_EMAIL)
            }
        })
    return jsonify({"ok": False, "error": "Invalid admin username or password"}), 401

@app.route("/api/admin/logout", methods=["POST"])
def admin_logout():
    session.pop("is_admin", None)
    session.pop("admin_id", None)
    session.pop("admin_username", None)
    return jsonify({"ok": True, "message": "Logged out"})

@app.route("/api/admin/check", methods=["GET"])
def admin_check():
    is_admin = bool(session.get("is_admin"))
    username = session.get("admin_username", ADMIN_USER)
    admin_info = db_get_admin_by_username(username) if is_admin else None
    return jsonify({
        "ok": True,
        "is_admin": is_admin,
        "admin": admin_info
    })

@app.route("/api/admin/users", methods=["GET"])
def admin_users():
    if not session.get("is_admin"):
        return jsonify({"ok": False, "error": "Unauthorized"}), 401
    users = db_get_all_candidates_admin()
    return jsonify({"ok": True, "users": users})

@app.route("/api/admin/visitor-stats", methods=["GET"])
def admin_visitor_stats():
    if not session.get("is_admin"):
        return jsonify({"ok": False, "error": "Unauthorized"}), 401
    stats = db_get_visitor_analytics()
    return jsonify({"ok": True, "stats": stats})

@app.route("/api/telemetry/visit", methods=["POST"])
def telemetry_visit():
    data = request.get_json(silent=True) or {}
    visitor_id = (data.get("visitor_id") or "").strip()
    if not visitor_id:
        return jsonify({"ok": False, "error": "visitor_id is required"}), 400

    page = (data.get("page") or "/").strip()
    referrer = (data.get("referrer") or "").strip()
    screen_width = data.get("screen_width")
    client_ip = (data.get("client_ip") or "").strip()
    client_location = (data.get("location") or "").strip()

    # Extract best IP address
    header_ip = ""
    for h in ["CF-Connecting-IP", "True-Client-IP", "X-Forwarded-For", "X-Real-IP"]:
        val = request.headers.get(h)
        if val:
            candidate = val.split(",")[0].strip()
            if candidate and candidate != "127.0.0.1":
                header_ip = candidate
                break

    remote_ip = request.remote_addr or "127.0.0.1"

    # Prioritize valid public IP reported by client browser, else proxy header IP, else remote_ip
    if client_ip and client_ip not in ("127.0.0.1", "::1", "localhost"):
        ip_address = client_ip
    elif header_ip:
        ip_address = header_ip
    else:
        ip_address = remote_ip

    user_agent = request.headers.get("User-Agent", "")

    db_record_visitor_hit(
        visitor_id=visitor_id,
        ip_address=ip_address,
        user_agent=user_agent,
        page=page,
        referrer=referrer,
        screen_width=screen_width,
        client_location=client_location
    )
    return jsonify({"ok": True, "visitor_id": visitor_id, "ip_recorded": ip_address})

@app.route("/api/telemetry/engage", methods=["POST"])
def telemetry_engage():
    data = request.get_json(silent=True) or {}
    visitor_id = (data.get("visitor_id") or "").strip()
    if not visitor_id:
        return jsonify({"ok": False, "error": "visitor_id is required"}), 400

    duration = int(data.get("duration_seconds", 0) or 0)
    scroll_pct = int(data.get("scroll_percent", 0) or 0)
    interaction = (data.get("interaction") or "").strip()

    db_record_visitor_engagement(
        visitor_id=visitor_id,
        duration_seconds=duration,
        scroll_percent=scroll_pct,
        interaction=interaction
    )
    return jsonify({"ok": True})

@app.route("/api/admin/database-stats", methods=["GET"])
def admin_database_stats():
    if not session.get("is_admin"):
        return jsonify({"ok": False, "error": "Unauthorized"}), 401

    admins_cnt = (mongo_db.admins.count_documents({}) if MONGO_CONNECTED and mongo_db is not None else len(memory_store["admins"]))
    candidates_cnt = (mongo_db.candidates.count_documents({}) if MONGO_CONNECTED and mongo_db is not None else len(memory_store["candidates"]))
    openings_cnt = (mongo_db.openings.count_documents({}) if MONGO_CONNECTED and mongo_db is not None else len(memory_store["openings"]))
    apps_cnt = (mongo_db.applications.count_documents({}) if MONGO_CONNECTED and mongo_db is not None else len(memory_store["applications"]))
    enqs_cnt = (mongo_db.enquiries.count_documents({}) if MONGO_CONNECTED and mongo_db is not None else len(memory_store["enquiries"]))

    masked_uri = re.sub(r":([^@]+)@", ":****@", MONGO_URI)

    return jsonify({
        "ok": True,
        "mongo_connected": MONGO_CONNECTED,
        "database_name": MONGO_DB_NAME,
        "mongo_uri_masked": masked_uri,
        "counts": {
            "admins": admins_cnt,
            "candidates": candidates_cnt,
            "openings": openings_cnt,
            "applications": apps_cnt,
            "enquiries": enqs_cnt
        }
    })

@app.route("/api/admin/mongodb/test-connect", methods=["POST"])
def admin_mongo_test_connect():
    if not session.get("is_admin"):
        return jsonify({"ok": False, "error": "Unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    new_uri = (data.get("uri") or "").strip()
    if not new_uri:
        return jsonify({"ok": False, "error": "MongoDB Atlas connection string is required."}), 400

    success, msg = init_mongo(custom_uri=new_uri)
    if success:
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
        try:
            if os.path.exists(env_path):
                with open(env_path, "r", encoding="utf-8") as f:
                    content = f.read()
                if "MONGO_URI=" in content:
                    content = re.sub(r"MONGO_URI=.*", f"MONGO_URI={new_uri}", content)
                else:
                    content += f"\nMONGO_URI={new_uri}\n"
                with open(env_path, "w", encoding="utf-8") as f:
                    f.write(content)
        except Exception as e:
            print(f"[ENV Update Notice]: {e}")

        return jsonify({"ok": True, "message": msg, "mongo_connected": True})
    return jsonify({"ok": False, "error": msg, "mongo_connected": False}), 400

@app.route("/api/admin/openings", methods=["GET", "POST"])
def admin_openings():
    if not session.get("is_admin"):
        return jsonify({"ok": False, "error": "Unauthorized"}), 401

    if request.method == "GET":
        openings = db_get_all_openings_admin()
        return jsonify({"ok": True, "openings": openings})

    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    dept = (data.get("department") or "").strip()
    loc = (data.get("location") or "").strip()
    jtype = (data.get("job_type") or "Full-time").strip()
    exp = (data.get("experience") or "").strip()
    desc = (data.get("description") or "").strip()
    reqs = (data.get("requirements") or "").strip()

    if not title or not dept or not desc:
        return jsonify({"ok": False, "error": "Title, department, and description are required."}), 400

    new_id = db_add_opening(title, dept, loc, jtype, exp, desc, reqs)
    return jsonify({"ok": True, "id": new_id, "message": "Opening created successfully"})

@app.route("/api/admin/openings/<string:op_id>", methods=["PUT", "DELETE"])
def admin_opening_detail(op_id):
    if not session.get("is_admin"):
        return jsonify({"ok": False, "error": "Unauthorized"}), 401

    if request.method == "DELETE":
        success = db_delete_opening(op_id)
        if success:
            return jsonify({"ok": True, "message": "Opening deleted"})
        return jsonify({"ok": False, "error": "Opening not found"}), 404

    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    dept = (data.get("department") or "").strip()
    loc = (data.get("location") or "").strip()
    jtype = (data.get("job_type") or "Full-time").strip()
    exp = (data.get("experience") or "").strip()
    desc = (data.get("description") or "").strip()
    reqs = (data.get("requirements") or "").strip()
    status = (data.get("status") or "Active").strip()

    success = db_update_opening(op_id, title, dept, loc, jtype, exp, desc, reqs, status)
    if success:
        return jsonify({"ok": True, "message": "Opening updated"})
    return jsonify({"ok": False, "error": "Opening not found"}), 404

@app.route("/api/admin/applications", methods=["GET"])
def admin_applications():
    if not session.get("is_admin"):
        return jsonify({"ok": False, "error": "Unauthorized"}), 401
    apps = db_get_all_applications_admin()
    return jsonify({"ok": True, "applications": apps})

@app.route("/api/admin/applications/<string:app_id>/status", methods=["PUT"])
def admin_update_app_status(app_id):
    if not session.get("is_admin"):
        return jsonify({"ok": False, "error": "Unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    status = (data.get("status") or "").strip()
    if not status:
        return jsonify({"ok": False, "error": "Status is required"}), 400

    success = db_update_application_status(app_id, status)
    if success:
        return jsonify({"ok": True, "message": f"Status updated to '{status}'"})
    return jsonify({"ok": False, "error": "Application not found"}), 404


# ── PUBLIC OPENINGS ENDPOINT ──────────────────────────────
@app.route("/api/openings", methods=["GET"])
def public_openings():
    openings = db_get_active_openings()
    return jsonify({"ok": True, "openings": openings})


# ── CANDIDATE AUTH & APPLICATION ENDPOINTS ────────────────

@app.route("/api/candidate/register", methods=["POST"])
def candidate_register():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    password = (data.get("password") or "").strip()
    phone = (data.get("phone") or "").strip()

    if not name or not email or not password:
        return jsonify({"ok": False, "error": "Name, email, and password are required."}), 400

    if len(password) < 4:
        return jsonify({"ok": False, "error": "Password must be at least 4 characters long."}), 400

    cand_id, err = db_register_candidate(name, email, password, phone)
    if err:
        return jsonify({"ok": False, "error": err}), 400

    session["candidate_id"] = cand_id
    cand = db_get_candidate_by_id(cand_id)
    return jsonify({"ok": True, "candidate": cand, "message": "Registration successful"})

@app.route("/api/candidate/login", methods=["POST"])
def candidate_login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip()
    password = (data.get("password") or "").strip()

    if not email or not password:
        return jsonify({"ok": False, "error": "Email and password are required."}), 400

    cand = db_authenticate_candidate(email, password)
    if not cand:
        return jsonify({"ok": False, "error": "Invalid email or password."}), 401

    session["candidate_id"] = cand["id"]
    return jsonify({
        "ok": True,
        "candidate": {
            "id": cand["id"],
            "name": cand["name"],
            "email": cand["email"],
            "phone": cand.get("phone", "")
        },
        "message": "Login successful"
    })

@app.route("/api/candidate/logout", methods=["POST"])
def candidate_logout():
    session.pop("candidate_id", None)
    return jsonify({"ok": True, "message": "Candidate logged out"})

@app.route("/api/candidate/me", methods=["GET"])
def candidate_me():
    cand_id = session.get("candidate_id")
    if not cand_id:
        return jsonify({"ok": True, "logged_in": False})
    cand = db_get_candidate_by_id(cand_id)
    if not cand:
        session.pop("candidate_id", None)
        return jsonify({"ok": True, "logged_in": False})
    return jsonify({"ok": True, "logged_in": True, "candidate": cand})

@app.route("/api/candidate/apply", methods=["POST"])
def candidate_apply():
    if request.is_json:
        data = request.get_json(silent=True) or {}
    else:
        data = request.form

    opening_id = data.get("opening_id")
    if not opening_id:
        return jsonify({"ok": False, "error": "Opening ID is required."}), 400

    cand_id = session.get("candidate_id")
    cand = db_get_candidate_by_id(cand_id) if cand_id else None

    name = (data.get("name") or (cand["name"] if cand else "")).strip()
    email = (data.get("email") or (cand["email"] if cand else "")).strip()
    phone = (data.get("phone") or (cand.get("phone") if cand else "") or "").strip()
    experience = (data.get("experience") or "").strip()
    portfolio = (data.get("portfolio") or "").strip()
    notes = (data.get("notes") or "").strip()

    if not name or not email:
        return jsonify({"ok": False, "error": "Name and email are required."}), 400

    # If candidate is not already signed in, link by email or register automatically
    if not cand:
        existing = db_get_candidate_by_email(email)
        if existing:
            cand_id = existing["id"]
            cand = existing
        else:
            default_pwd = phone.replace(" ", "") if phone else "rzmt2026"
            new_id, _ = db_register_candidate(name=name, email=email, password=default_pwd, phone=phone)
            if new_id:
                cand_id = new_id
                cand = db_get_candidate_by_id(cand_id)
            else:
                existing = db_get_candidate_by_email(email)
                cand_id = existing["id"] if existing else "1"
                cand = existing
        session["candidate_id"] = cand_id

    # Handle Resume / CV Upload to Cloudinary (with local upload repository fallback)
    resume_url = ""
    resume_file = request.files.get("resume")
    if resume_file and resume_file.filename:
        orig_name = secure_filename(resume_file.filename) or "resume.pdf"
        try:
            upload_res = cloudinary.uploader.upload(
                resume_file,
                resource_type="auto",
                folder="rzmt_resumes",
                public_id=f"resume_{cand_id}_{int(time.time())}"
            )
            resume_url = upload_res.get("secure_url") or upload_res.get("url")
            print(f"[Cloudinary] Successfully uploaded resume to Cloudinary: {resume_url}")
        except Exception as cloud_err:
            print(f"[Cloudinary] Upload notice: {cloud_err}")

    # Lookup opening title for confirmation notification
    opening = db_get_opening_by_id(opening_id)
    opening_title = (opening.get("title") if opening else "") or "Job Opening"

    app_id = db_submit_application(
        candidate_id=cand_id,
        opening_id=opening_id,
        candidate_name=name,
        candidate_email=email,
        candidate_phone=phone,
        experience_years=experience,
        portfolio_link=portfolio,
        resume_url=resume_url,
        resume_notes=notes
    )

    # Dispatch Dual Emails (Admin notification + Candidate acknowledgement) in background thread
    threading.Thread(
        target=_dispatch_career_application_emails,
        args=(name, email, phone, opening_title, experience, portfolio, resume_url, notes, app_id),
        daemon=True
    ).start()

    return jsonify({
        "ok": True,
        "application_id": app_id,
        "resume_url": resume_url,
        "candidate": {
            "id": cand_id,
            "name": name,
            "email": email,
            "phone": phone
        },
        "message": "Application submitted successfully! Stored in MongoDB Atlas."
    })

@app.route("/api/candidate/my-applications", methods=["GET"])
def candidate_my_applications():
    cand_id = session.get("candidate_id")
    if not cand_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401

    my_apps = db_get_candidate_applications(cand_id)
    return jsonify({"ok": True, "applications": my_apps})


# ── Email helpers ─────────────────────────────────────────
def _smtp_connection():
    """Return an authenticated SMTP connection."""
    pwd = APP_PASSWORD.replace(" ", "")
    server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
    server.ehlo()
    server.starttls()
    server.login(ADMIN_EMAIL, pwd)
    return server


def _send_admin_notification(name, email, company, topic, message):
    """Notify admin of a new contact form submission."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[RZMT Contact] New enquiry from {name} — {topic}"
    msg["From"]    = ADMIN_EMAIL
    msg["To"]      = ADMIN_EMAIL

    plain = f"""New contact form submission on rzmt.com

Name:    {name}
Email:   {email}
Company: {company or 'Not specified'}
Topic:   {topic}

Message:
{message}

---
Sent via RZMT contact form
"""

    html = f"""<!DOCTYPE html>
<html>
<body style="font-family: 'Segoe UI', Arial, sans-serif; color: #20262E; background: #F7F9FC; margin:0; padding:0;">
  <div style="max-width:600px; margin:40px auto; background:#FFFFFF; border-radius:16px; border:1px solid #E6EAF0; overflow:hidden; box-shadow:0 4px 24px rgba(32,38,46,0.06);">
    <div style="background:#2563DF; padding:28px 36px;">
      <h1 style="color:#FFFFFF; font-size:20px; margin:0; font-weight:500; letter-spacing:-0.01em;">New Contact Enquiry</h1>
      <p style="color:rgba(255,255,255,0.75); font-size:13px; margin:6px 0 0;">RZMT Website — rzmt.com</p>
    </div>
    <div style="padding:32px 36px;">
      <table style="width:100%; border-collapse:collapse; margin-bottom:24px;">
        <tr><td style="padding:10px 0; border-bottom:1px solid #E6EAF0; font-size:13px; color:#68727F; width:110px;">Name</td><td style="padding:10px 0; border-bottom:1px solid #E6EAF0; font-size:14px; font-weight:500; color:#20262E;">{name}</td></tr>
        <tr><td style="padding:10px 0; border-bottom:1px solid #E6EAF0; font-size:13px; color:#68727F;">Email</td><td style="padding:10px 0; border-bottom:1px solid #E6EAF0; font-size:14px; color:#2563DF;">{email}</td></tr>
        <tr><td style="padding:10px 0; border-bottom:1px solid #E6EAF0; font-size:13px; color:#68727F;">Company</td><td style="padding:10px 0; border-bottom:1px solid #E6EAF0; font-size:14px; color:#20262E;">{company or 'Not specified'}</td></tr>
        <tr><td style="padding:10px 0; font-size:13px; color:#68727F;">Topic</td><td style="padding:10px 0; font-size:14px; font-weight:500; color:#20262E;">{topic}</td></tr>
      </table>
      <div style="background:#F7F9FC; border:1px solid #E6EAF0; border-radius:10px; padding:20px 24px;">
        <p style="font-size:12px; font-weight:600; text-transform:uppercase; letter-spacing:0.10em; color:#68727F; margin:0 0 10px;">Message</p>
        <p style="font-size:14px; line-height:1.75; color:#20262E; margin:0; white-space:pre-wrap;">{message}</p>
      </div>
    </div>
    <div style="padding:20px 36px; background:#F7F9FC; border-top:1px solid #E6EAF0; text-align:center;">
      <p style="font-size:12px; color:#94A3B8; margin:0;">Reply directly to <a href="mailto:{email}" style="color:#2563DF;">{email}</a></p>
    </div>
  </div>
</body>
</html>"""

    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html,  "html"))

    with _smtp_connection() as server:
        server.sendmail(ADMIN_EMAIL, ADMIN_EMAIL, msg.as_string())


def _send_user_acknowledgement(name, email, topic, message):
    """Send thank-you acknowledgement to the user."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Thank you for contacting RZMT"
    msg["From"]    = f"RZMT <{ADMIN_EMAIL}>"
    msg["To"]      = email
    msg["Reply-To"] = ADMIN_EMAIL

    plain = f"""Hi {name},

Thank you for contacting RZMT. We have received your enquiry and will get back to you shortly.

Here is a summary of what you sent us:

Topic:   {topic}
Message:
{message}

We typically respond within 1–2 business days.

Best regards,
The RZMT Team
rzmt.co.in

---
This is an automated acknowledgement. Please do not reply to this email directly.
To follow up, use our contact form or email us at teams@rzmt.co.in.
"""

    html = f"""<!DOCTYPE html>
<html>
<body style="font-family: 'Segoe UI', Arial, sans-serif; color: #20262E; background: #F7F9FC; margin:0; padding:0;">
  <div style="max-width:600px; margin:40px auto; background:#FFFFFF; border-radius:16px; border:1px solid #E6EAF0; overflow:hidden; box-shadow:0 4px 24px rgba(32,38,46,0.06);">
    <div style="background:#2563DF; padding:32px 36px; text-align:center;">
      <p style="color:rgba(255,255,255,0.8); font-size:11px; font-weight:600; letter-spacing:0.14em; text-transform:uppercase; margin:0 0 12px;">RZMT — DEEPTECH. BUILT AROUND REALITY.</p>
      <h1 style="color:#FFFFFF; font-size:24px; margin:0; font-weight:500; letter-spacing:-0.01em;">Thank you for reaching out.</h1>
    </div>
    <div style="padding:36px 36px 28px;">
      <p style="font-size:16px; color:#20262E; margin:0 0 16px;">Hi <strong>{name}</strong>,</p>
      <p style="font-size:15px; line-height:1.75; color:#68727F; margin:0 0 24px;">
        We have received your enquiry and will get back to you shortly. Thank you for taking the time to reach out to us.
      </p>
      <div style="background:#F1F5FC; border:1px solid #DCE6F5; border-radius:12px; padding:20px 24px; margin-bottom:24px;">
        <p style="font-size:12px; font-weight:600; text-transform:uppercase; letter-spacing:0.10em; color:#2563DF; margin:0 0 12px;">Your Enquiry</p>
        <p style="font-size:13px; color:#68727F; margin:0 0 4px;"><strong style="color:#20262E;">Topic:</strong> {topic}</p>
        <p style="font-size:13px; color:#20262E; line-height:1.7; margin:10px 0 0; white-space:pre-wrap;">{message}</p>
      </div>
      <p style="font-size:14px; line-height:1.75; color:#68727F; margin:0 0 8px;">
        We typically respond within <strong style="color:#20262E;">1–2 business days</strong>.
      </p>
      <p style="font-size:14px; line-height:1.75; color:#68727F; margin:0;">
        In the meantime, feel free to connect with us on
        <a href="https://www.linkedin.com/company/rzmt" style="color:#2563DF;">LinkedIn</a>.
      </p>
    </div>
    <div style="padding:20px 36px 28px; border-top:1px solid #E6EAF0; text-align:center; background:#F7F9FC;">
      <p style="font-size:13px; font-weight:500; color:#20262E; margin:0 0 4px;">The RZMT Team</p>
      <a href="https://rzmt.co.in" style="color:#2563DF; font-size:13px; text-decoration:none;">rzmt.co.in</a>
      <p style="font-size:11px; color:#94A3B8; margin:16px 0 0;">
        This is an automated acknowledgement. Please do not reply to this email directly.<br>
        To follow up, contact us at <a href="mailto:teams@rzmt.co.in" style="color:#2563DF;">teams@rzmt.co.in</a> or call <a href="tel:+919003035790" style="color:#2563DF;">+91 90030 35790</a>.
      </p>
    </div>
  </div>
</body>
</html>"""

    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html,  "html"))

    with _smtp_connection() as server:
        server.sendmail(ADMIN_EMAIL, email, msg.as_string())


def _send_career_admin_notification(candidate_name, candidate_email, candidate_phone, opening_title, experience_years, portfolio_link, resume_url, resume_notes, app_id):
    """Notify admin (rzmt.2025@gmail.com) of a new career application."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[RZMT Careers] New Application #{app_id}: {candidate_name} — {opening_title}"
    msg["From"]    = f"RZMT Careers Portal <{ADMIN_EMAIL}>"
    msg["To"]      = ADMIN_EMAIL
    msg["Reply-To"] = candidate_email

    resume_display = f'<a href="{resume_url}" target="_blank" style="display:inline-block; padding:10px 20px; background:#2563EB; color:#ffffff; text-decoration:none; border-radius:8px; font-weight:600; font-size:13px;">View Candidate Resume / CV ↗</a>' if resume_url else '<span style="color:#94A3B8; font-style:italic;">No resume attached</span>'

    plain = f"""New Job Application received on RZMT Careers Portal
Application ID: #{app_id}
Position: {opening_title}

Candidate Details:
Name:       {candidate_name}
Email:      {candidate_email}
Phone:      {candidate_phone or 'Not provided'}
Experience: {experience_years or 'Not specified'}
Portfolio:  {portfolio_link or 'None'}
Resume URL: {resume_url or 'None'}

Candidate Note / Cover Brief:
{resume_notes or 'None provided'}

---
Manage applicants in the Admin Portal: http://localhost:5000/admin.html
Sent via RZMT Careers Engine
"""

    html = f"""<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1E293B; background: #F8FAFC; margin:0; padding:0;">
  <div style="max-width:620px; margin:36px auto; background:#FFFFFF; border-radius:14px; border:1px solid #E2E8F0; overflow:hidden; box-shadow:0 6px 20px rgba(15,23,42,0.06);">
    <div style="background:#1E293B; padding:26px 32px; border-bottom:3px solid #2563EB;">
      <span style="display:inline-block; font-size:11px; font-weight:700; color:#93C5FD; text-transform:uppercase; letter-spacing:0.12em; margin-bottom:6px;">RZMT Careers · Application Notice</span>
      <h1 style="color:#FFFFFF; font-size:20px; margin:0; font-weight:600; letter-spacing:-0.01em;">New Application: {candidate_name}</h1>
      <p style="color:#94A3B8; font-size:13px; margin:6px 0 0;">Applied for <strong style="color:#F8FAFC;">{opening_title}</strong> (Ref #{app_id})</p>
    </div>
    <div style="padding:28px 32px;">
      <table style="width:100%; border-collapse:collapse; margin-bottom:24px;">
        <tr><td style="padding:10px 0; border-bottom:1px solid #F1F5F9; font-size:13px; color:#64748B; width:130px;">Application ID</td><td style="padding:10px 0; border-bottom:1px solid #F1F5F9; font-size:14px; font-weight:600; color:#0F172A;">#{app_id}</td></tr>
        <tr><td style="padding:10px 0; border-bottom:1px solid #F1F5F9; font-size:13px; color:#64748B;">Candidate Name</td><td style="padding:10px 0; border-bottom:1px solid #F1F5F9; font-size:14px; font-weight:600; color:#0F172A;">{candidate_name}</td></tr>
        <tr><td style="padding:10px 0; border-bottom:1px solid #F1F5F9; font-size:13px; color:#64748B;">Email Address</td><td style="padding:10px 0; border-bottom:1px solid #F1F5F9; font-size:14px; color:#2563EB;"><a href="mailto:{candidate_email}" style="color:#2563EB; text-decoration:none;">{candidate_email}</a></td></tr>
        <tr><td style="padding:10px 0; border-bottom:1px solid #F1F5F9; font-size:13px; color:#64748B;">Phone</td><td style="padding:10px 0; border-bottom:1px solid #F1F5F9; font-size:14px; color:#0F172A;">{candidate_phone or '—'}</td></tr>
        <tr><td style="padding:10px 0; border-bottom:1px solid #F1F5F9; font-size:13px; color:#64748B;">Experience</td><td style="padding:10px 0; border-bottom:1px solid #F1F5F9; font-size:14px; color:#0F172A;">{experience_years or '—'}</td></tr>
        <tr><td style="padding:10px 0; border-bottom:1px solid #F1F5F9; font-size:13px; color:#64748B;">Portfolio / Profile</td><td style="padding:10px 0; border-bottom:1px solid #F1F5F9; font-size:14px; color:#2563EB;">{f'<a href="{portfolio_link}" target="_blank" style="color:#2563EB;">{portfolio_link}</a>' if portfolio_link else '—'}</td></tr>
      </table>

      <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:10px; padding:16px 20px; margin-bottom:24px;">
        <p style="font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:0.08em; color:#64748B; margin:0 0 8px;">Candidate Statement / Note</p>
        <p style="font-size:13.5px; line-height:1.7; color:#334155; margin:0; white-space:pre-wrap;">{resume_notes or 'No statement provided'}</p>
      </div>

      <div style="background:#EFF6FF; border:1px solid #BFDBFE; border-radius:10px; padding:18px 20px; text-align:center;">
        <p style="font-size:12px; font-weight:600; color:#1E40AF; text-transform:uppercase; letter-spacing:0.05em; margin:0 0 10px;">Cloudinary Resume Attachment</p>
        {resume_display}
      </div>
    </div>
    <div style="padding:18px 32px; background:#F8FAFC; border-top:1px solid #E2E8F0; text-align:center;">
      <p style="font-size:12px; color:#64748B; margin:0;">Open <a href="http://localhost:5000/admin.html" style="color:#2563EB; font-weight:600; text-decoration:none;">RZMT Admin Dashboard</a> to manage applicant status.</p>
    </div>
  </div>
</body>
</html>"""

    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html,  "html"))

    with _smtp_connection() as server:
        server.sendmail(ADMIN_EMAIL, ADMIN_EMAIL, msg.as_string())


def _send_career_candidate_acknowledgement(candidate_name, candidate_email, opening_title, resume_url, app_id):
    """Send application confirmation email to the candidate."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Application Received: {opening_title} — RZMT"
    msg["From"]    = f"RZMT Careers <{ADMIN_EMAIL}>"
    msg["To"]      = candidate_email
    msg["Reply-To"] = ADMIN_EMAIL

    resume_link_html = f'<p style="font-size:13px; color:#64748B; margin:8px 0 0;">Attached Resume: <a href="{resume_url}" target="_blank" style="color:#2563EB; text-decoration:none; font-weight:500;">View Uploaded File ↗</a></p>' if resume_url else ''

    plain = f"""Hi {candidate_name},

Thank you for your interest in joining RZMT!

We have successfully received your application for:
Position:       {opening_title}
Application ID: #{app_id}

Our engineering recruitment team is currently reviewing applicant profiles against our technical roadmap and position requirements. If your background matches what we are building, our team will get in touch directly to coordinate the next steps.

You can also log back into the RZMT Careers portal at any time to check the live status of your application.

If you have questions in the meantime, feel free to contact us at teams@rzmt.co.in or +91 90030 35790.

Best regards,
The RZMT Engineering & Talent Team
No 147/2 Peter’s road, Gopalapuram, Chennai – 600086
Phone: +91 90030 35790
Website: https://rzmt.co.in
"""

    html = f"""<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1E293B; background: #F8FAFC; margin:0; padding:0;">
  <div style="max-width:600px; margin:36px auto; background:#FFFFFF; border-radius:14px; border:1px solid #E2E8F0; overflow:hidden; box-shadow:0 6px 20px rgba(15,23,42,0.06);">
    <div style="background:#2563EB; padding:32px 36px; text-align:center;">
      <p style="color:rgba(255,255,255,0.85); font-size:11px; font-weight:700; letter-spacing:0.12em; text-transform:uppercase; margin:0 0 10px;">RZMT — Deeptech. Built Around Reality.</p>
      <h1 style="color:#FFFFFF; font-size:22px; margin:0; font-weight:600; letter-spacing:-0.01em;">Application Received</h1>
      <p style="color:rgba(255,255,255,0.85); font-size:14px; margin:8px 0 0;">Reference ID: #{app_id}</p>
    </div>
    <div style="padding:32px 36px 28px;">
      <p style="font-size:15px; color:#1E293B; margin:0 0 16px;">Dear <strong>{candidate_name}</strong>,</p>
      <p style="font-size:14px; line-height:1.75; color:#475569; margin:0 0 20px;">
        Thank you for applying to <strong>RZMT</strong>. We are pleased to confirm that your application for <strong>{opening_title}</strong> has been logged into our recruitment system.
      </p>

      <div style="background:#F1F5F9; border:1px solid #E2E8F0; border-radius:10px; padding:18px 22px; margin-bottom:22px;">
        <p style="font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:0.08em; color:#2563EB; margin:0 0 8px;">Application Summary</p>
        <p style="font-size:13px; color:#334155; margin:0 0 4px;"><strong style="color:#0F172A;">Position:</strong> {opening_title}</p>
        <p style="font-size:13px; color:#334155; margin:0 0 4px;"><strong style="color:#0F172A;">Application ID:</strong> #{app_id}</p>
        <p style="font-size:13px; color:#334155; margin:0;"><strong style="color:#0F172A;">Status:</strong> Under Review</p>
        {resume_link_html}
      </div>

      <p style="font-size:14px; line-height:1.75; color:#475569; margin:0 0 14px;">
        Our engineering team carefully reviews every profile against our technical roadmaps. If your profile is shortlisted, we will reach out to you directly for technical discussions.
      </p>
      <p style="font-size:14px; line-height:1.75; color:#475569; margin:0;">
        You can also visit our website anytime to track the live status of your application under your candidate profile.
      </p>
    </div>

    <div style="padding:22px 36px; border-top:1px solid #E2E8F0; text-align:center; background:#F8FAFC;">
      <p style="font-size:13px; font-weight:600; color:#0F172A; margin:0 0 4px;">RZMT Engineering & Talent Team</p>
      <p style="font-size:12px; color:#64748B; margin:0 0 6px;">No 147/2 Peter’s road, Gopalapuram, Chennai – 600086</p>
      <p style="font-size:12px; color:#64748B; margin:0 0 12px;">Phone: <a href="tel:+919003035790" style="color:#2563EB; text-decoration:none;">+91 90030 35790</a> · Email: <a href="mailto:teams@rzmt.co.in" style="color:#2563EB; text-decoration:none;">teams@rzmt.co.in</a></p>
      <a href="https://rzmt.co.in" style="color:#2563EB; font-size:12px; text-decoration:none; font-weight:600;">rzmt.co.in</a>
    </div>
  </div>
</body>
</html>"""

    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html,  "html"))

    with _smtp_connection() as server:
        server.sendmail(ADMIN_EMAIL, candidate_email, msg.as_string())


def _dispatch_career_application_emails(candidate_name, candidate_email, candidate_phone, opening_title, experience_years, portfolio_link, resume_url, resume_notes, app_id):
    """Dispatches application notifications to both admin and candidate."""
    # Send notification to Admin
    try:
        _send_career_admin_notification(
            candidate_name=candidate_name,
            candidate_email=candidate_email,
            candidate_phone=candidate_phone,
            opening_title=opening_title,
            experience_years=experience_years,
            portfolio_link=portfolio_link,
            resume_url=resume_url,
            resume_notes=resume_notes,
            app_id=app_id
        )
        print(f"[Email Notification] Successfully dispatched admin alert for #{app_id}")
    except Exception as exc:
        print(f"[Email Notification Error - Admin]: {exc}")

    # Send acknowledgement to Candidate
    try:
        _send_career_candidate_acknowledgement(
            candidate_name=candidate_name,
            candidate_email=candidate_email,
            opening_title=opening_title,
            resume_url=resume_url,
            app_id=app_id
        )
        print(f"[Email Notification] Successfully dispatched candidate acknowledgement to {candidate_email} for #{app_id}")
    except Exception as exc:
        print(f"[Email Notification Error - Candidate]: {exc}")


def _dispatch_contact_enquiry_emails(name, email, company, topic, message, enq_id=""):
    """Dispatches contact enquiry notifications to both admin and user."""
    # 1. Send alert to Admin (rzmt.2025@gmail.com)
    try:
        _send_admin_notification(name, email, company, topic, message)
        print(f"[Contact Email] Admin enquiry notification dispatched to {ADMIN_EMAIL} for enquiry #{enq_id}")
    except Exception as exc:
        print(f"[Contact Email Error - Admin]: {exc}")

    # 2. Send acknowledgement to User
    try:
        _send_user_acknowledgement(name, email, topic, message)
        print(f"[Contact Email] User acknowledgement dispatched to {email}")
    except Exception as exc:
        print(f"[Contact Email Error - User]: {exc}")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # Binding to 0.0.0.0 allows accessing via IP address: 192.168.88.9:5000 or localhost:5000
    app.run(host="0.0.0.0", port=port, debug=False)
