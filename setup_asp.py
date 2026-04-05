import os
import sys
import json
import time
import logging
from pymongo import MongoClient
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ── Parse CLI flags ──────────────────────────────────────────────────
DRY_RUN = "--dry-run" in sys.argv
if DRY_RUN:
    logger.info("🏜️  DRY-RUN MODE — will validate pipelines but NOT deploy")

# ── Stream Processor connection ──────────────────────────────────────
uri_base = os.getenv("MONGODB_STREAMPROCESSOR_URI")
username = quote_plus(os.getenv("MONGODB_STREAMPROCESSOR_USERNAME", ""))
password = quote_plus(os.getenv("MONGODB_STREAMPROCESSOR_PASSWORD", ""))

if not uri_base:
    raise ValueError("MONGODB_STREAMPROCESSOR_URI is not set")

if username and password:
    if "@" not in uri_base:
        uri = uri_base.replace("mongodb://", f"mongodb://{username}:{password}@")
    else:
        uri = uri_base
else:
    uri = uri_base

if "?tls" not in uri and "&tls" not in uri:
    separator = "&" if "?" in uri else "?"
    uri += f"{separator}tls=true"

# ── Core database connection ─────────────────────────────────────────
main_db_uri = os.getenv("MONGODB_URI")

# ── Pipeline files ───────────────────────────────────────────────────
base_dir = os.path.dirname(os.path.abspath(__file__))
processors = {
    "asp1_session_state_builder": os.path.join(base_dir, "external/atlas-stream-processing/asp1_session_state_builder_.js"),
    "asp2_exit_risk": os.path.join(base_dir, "external/atlas-stream-processing/asp2_exit_risk.js"),
    "asp2_high_intent": os.path.join(base_dir, "external/atlas-stream-processing/asp2_high_intent.js"),
    "asp2_search_friction": os.path.join(base_dir, "external/atlas-stream-processing/asp2_search_friction.js")
}


# =====================================================================
# PRE-DEPLOY VALIDATION
# =====================================================================

def lint_timefield(pipeline, name):
    """Check for $toDate wrapping on timeField — risky if source is already BSON Date."""
    source = pipeline[0].get("$source", {}) if pipeline else {}
    tf = source.get("timeField")
    if isinstance(tf, dict) and "$toDate" in tf:
        logger.warning(f"⚠️  {name}: timeField uses $toDate on '{tf['$toDate']}' — risky if already a BSON Date")
        return False
    return True


def validate_schema_contract(db, name):
    """For asp2_* processors, verify session_state has the fields they need."""
    if not name.startswith("asp2_"):
        return True

    required_fields = {
        "asp2_exit_risk": ["lastSeen", "sessionId", "userId", "last10s.lastEvent.event"],
        "asp2_high_intent": ["lastSeen", "firstSeen", "sessionId", "userId", "last10s.intent.products"],
        "asp2_search_friction": ["lastSeen", "sessionId", "userId", "last10s.intent.products",
                                  "last10s.intent.articleTypes", "last10s.intent.subCategories"],
    }

    fields = required_fields.get(name, [])
    if not fields:
        return True

    doc = db.session_state.find_one()
    if not doc:
        logger.warning(f"⚠️  {name}: No session_state documents found — cannot validate schema contract (OK if fresh)")
        return True  # Not a failure, just nothing to check yet

    missing = []
    for field in fields:
        parts = field.split(".")
        obj = doc
        for part in parts:
            if isinstance(obj, dict):
                obj = obj.get(part)
            else:
                obj = None
                break
        if obj is None:
            missing.append(field)

    if missing:
        logger.error(f"❌ {name}: session_state missing fields needed by this processor: {missing}")
        return False

    logger.info(f"  ✅ {name}: Schema contract validated — all required fields present in session_state")
    return True


def lint_pipeline(pipeline, name):
    """Run all static pipeline linters."""
    ok = True
    if not lint_timefield(pipeline, name):
        ok = False
    return ok


# =====================================================================
# DEPLOY
# =====================================================================

# First, ensure target collections have necessary unique indexes for $merge
if main_db_uri:
    logger.info("Connecting to core database to create indexes...")
    main_client = MongoClient(main_db_uri)
    main_db = main_client.leafy_popup_store
    main_db.session_state.create_index("sessionId", unique=True)
    logger.info("Unique index on sessionId for session_state created.")
else:
    main_db = None

logger.info(f"Connecting to Stream Processing Instance...")
client = MongoClient(uri)

# Pre-deploy: lint all pipelines
logger.info("=" * 60)
logger.info("PRE-DEPLOY VALIDATION")
logger.info("=" * 60)

all_pipelines = {}
lint_ok = True
for name, filepath in processors.items():
    with open(filepath, 'r') as f:
        pipeline = json.load(f)
    all_pipelines[name] = pipeline

    if not lint_pipeline(pipeline, name):
        lint_ok = False

    if main_db:
        if not validate_schema_contract(main_db, name):
            lint_ok = False

if not lint_ok:
    logger.error("❌ Pre-deploy validation found issues. Review warnings above.")
    if not DRY_RUN:
        logger.warning("Proceeding with deployment despite warnings...")

if DRY_RUN:
    logger.info("🏜️  DRY-RUN complete. Exiting without deploying.")
    sys.exit(0)

# Deploy each processor
logger.info("=" * 60)
logger.info("DEPLOYING STREAM PROCESSORS")
logger.info("=" * 60)

for name, filepath in processors.items():
    logger.info(f"--- Setting up {name} ---")
    try:
        pipeline = all_pipelines[name]

        try:
            logger.info(f"Stopping processor {name} if running...")
            client.admin.command({"stopStreamProcessor": name})
        except Exception:
            pass

        try:
            logger.info(f"Dropping processor {name} if exists...")
            client.admin.command({"dropStreamProcessor": name})
        except Exception:
            pass

        logger.info(f"Creating processor {name}...")
        client.admin.command({
            "createStreamProcessor": name,
            "pipeline": pipeline,
            "dlq": {"connectionName": "retail_customer_retention", "coll": "dlq", "db": "leafy_popup_store"}
        })

        logger.info(f"Starting processor {name}...")
        client.admin.command({"startStreamProcessor": name})
        logger.info(f"✅ Successfully started {name}")

    except Exception as e:
        logger.error(f"❌ Failed to set up {name}: {e}")

logger.info("Done configuring Stream Processors!")

# =====================================================================
# POST-DEPLOY VALIDATION — DLQ Monitor
# =====================================================================
if main_db:
    logger.info("=" * 60)
    logger.info("POST-DEPLOY: DLQ monitor (30 seconds)...")
    logger.info("=" * 60)

    baseline = main_db.dlq.count_documents({})
    logger.info(f"Baseline DLQ count: {baseline}")

    poll_duration = 30
    poll_interval = 10
    start = time.time()
    alert_raised = False

    while time.time() - start < poll_duration:
        time.sleep(poll_interval)
        current = main_db.dlq.count_documents({})
        elapsed = int(time.time() - start)

        if current > baseline:
            new_count = current - baseline
            logger.warning(f"🚨 {new_count} new DLQ entries at +{elapsed}s!")
            for doc in main_db.dlq.find().sort("dlqTime", -1).limit(3):
                logger.warning(f"  Processor: {doc.get('processorName')}, "
                               f"Error: {doc.get('errInfo', {}).get('reason', 'N/A')}, "
                               f"Operator: {doc.get('operatorName')}")
            baseline = current
            alert_raised = True
        else:
            logger.info(f"  +{elapsed}s: No new DLQ entries (count: {current})")

    if alert_raised:
        logger.warning("⚠️  DLQ entries appeared after deployment — investigate!")
    else:
        logger.info("✅ No new DLQ entries during post-deploy monitoring window")
