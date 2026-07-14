import os
import requests

BASE_URL = os.environ.get("CDB_URL", "http://localhost:8000/api/cdb_rest")
TOKEN = os.environ.get("CDB_TOKEN", "")
HEADERS = {"Content-Type": "application/json"}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"


def post(api, obj):
    r = requests.post(f"{BASE_URL}/{api}", headers=HEADERS, json=obj)
    if not r.ok:
        print(f"  ERROR POST {api}: {r.status_code} {r.text}")
        return {}
    return r.json()


def put(api, obj):
    r = requests.put(f"{BASE_URL}/{api}", headers=HEADERS, json=obj)
    if not r.ok:
        print(f"  ERROR PUT {api}: {r.status_code} {r.text}")
        return {}
    return r.json()


def get(api, params=None):
    r = requests.get(f"{BASE_URL}/{api}", headers=HEADERS, params=params)
    if not r.ok:
        print(f"  ERROR GET {api}: {r.status_code} {r.text}")
        return {}
    return r.json()


# ── Data definitions ──

STATUSES = ["unlocked", "locked", "frozen"]

PAYLOAD_TYPES = [
    "Alignment", "Calibration", "FieldMap", "Geometry",
    "BeamParameters", "TriggerConfig", "DAQConfig",
    "RecoConfig", "SimConfig", "NoiseMap",
]

GLOBAL_TAGS = [
    {"name": "Production_2024",        "status": "unlocked", "author": "admin",     "types": ["Alignment", "Calibration", "FieldMap", "Geometry", "BeamParameters", "TriggerConfig", "DAQConfig", "RecoConfig"]},
    {"name": "Production_2025",        "status": "unlocked", "author": "admin",     "types": ["Alignment", "Calibration", "FieldMap", "Geometry", "BeamParameters"]},
    {"name": "MC_Campaign_v1",         "status": "locked",   "author": "mcteam",    "types": ["SimConfig", "Geometry", "FieldMap", "BeamParameters"]},
    {"name": "MC_Campaign_v2",         "status": "locked",   "author": "mcteam",    "types": ["SimConfig", "Geometry", "FieldMap", "BeamParameters", "RecoConfig"]},
    {"name": "MC_Campaign_v3",         "status": "unlocked", "author": "mcteam",    "types": []},
    {"name": "Alignment_Run001",       "status": "frozen",   "author": "alignment", "types": ["Alignment", "Geometry"]},
    {"name": "Alignment_Run002",       "status": "frozen",   "author": "alignment", "types": ["Alignment", "Geometry"]},
    {"name": "Alignment_Run003",       "status": "unlocked", "author": "alignment", "types": []},
    {"name": "Calibration_Summer2024", "status": "locked",   "author": "calteam",   "types": ["Calibration", "NoiseMap", "DAQConfig"]},
    {"name": "Calibration_Winter2025", "status": "unlocked", "author": "calteam",   "types": []},
    {"name": "TestGT_Dev",             "status": "unlocked", "author": "dev",       "types": []},
    {"name": "TestGT_QA",              "status": "locked",   "author": "qa",        "types": []},
    {"name": "Geometry_v1",            "status": "frozen",   "author": "geometry",  "types": ["Geometry", "FieldMap"]},
    {"name": "Geometry_v2",            "status": "locked",   "author": "geometry",  "types": ["Geometry", "FieldMap"]},
    {"name": "Geometry_v3",            "status": "unlocked", "author": "geometry",  "types": []},
]

IOVS = [
    {"payload_url": "alignment_v1.root",       "type": "Alignment",      "major_iov": 0,   "minor_iov": 0, "major_iov_end": 100,  "minor_iov_end": 0},
    {"payload_url": "alignment_v2.root",       "type": "Alignment",      "major_iov": 100, "minor_iov": 0, "major_iov_end": 200,  "minor_iov_end": 0},
    {"payload_url": "calibration_run1.dat",    "type": "Calibration",    "major_iov": 0,   "minor_iov": 0, "major_iov_end": 50,   "minor_iov_end": 0},
    {"payload_url": "calibration_run2.dat",    "type": "Calibration",    "major_iov": 50,  "minor_iov": 0, "major_iov_end": 150,  "minor_iov_end": 0},
    {"payload_url": "fieldmap_3d.root",        "type": "FieldMap",       "major_iov": 0,   "minor_iov": 0, "major_iov_end": 9999, "minor_iov_end": 0},
    {"payload_url": "geometry_v1.xml",         "type": "Geometry",       "major_iov": 0,   "minor_iov": 0, "major_iov_end": 9999, "minor_iov_end": 0},
    {"payload_url": "beam_params_2024.json",   "type": "BeamParameters", "major_iov": 0,   "minor_iov": 0, "major_iov_end": 500,  "minor_iov_end": 0},
    {"payload_url": "trigger_default.json",    "type": "TriggerConfig",  "major_iov": 0,   "minor_iov": 0, "major_iov_end": 9999, "minor_iov_end": 0},
    {"payload_url": "daq_config_v3.json",      "type": "DAQConfig",      "major_iov": 0,   "minor_iov": 0, "major_iov_end": 9999, "minor_iov_end": 0},
    {"payload_url": "reco_params_2024.root",   "type": "RecoConfig",     "major_iov": 0,   "minor_iov": 0, "major_iov_end": 300,  "minor_iov_end": 0},
    {"payload_url": "sim_config_mc.json",      "type": "SimConfig",      "major_iov": 0,   "minor_iov": 0, "major_iov_end": 9999, "minor_iov_end": 0},
    {"payload_url": "noise_map_summer.root",   "type": "NoiseMap",       "major_iov": 0,   "minor_iov": 0, "major_iov_end": 200,  "minor_iov_end": 0},
]


def populate():
    print(f"Populating {BASE_URL}\n")

    # 1. Create statuses
    print("Creating statuses...")
    for s in STATUSES:
        result = post("gtstatus", {"name": s})
        print(f"  {s}: id={result.get('id', '?')}")

    # 2. Create payload types
    print("\nCreating payload types...")
    for pt in PAYLOAD_TYPES:
        result = post("pt", {"name": pt})
        print(f"  {pt}: id={result.get('id', '?')}")

    # 3. Create GTs, payload lists, and attach
    print("\nCreating global tags and attaching payload lists...")
    for gt in GLOBAL_TAGS:
        target_status = gt["status"]

        # Create GT as unlocked first (can't attach to frozen/locked)
        post("gt", {"name": gt["name"], "status": "unlocked", "author": gt.get("author", "")})
        print(f"\n  GT: {gt['name']}")

        for pt_name in gt["types"]:
            pl = post("pl", {"payload_type": pt_name})
            if not pl:
                continue
            put("pl_attach", {"global_tag": gt["name"], "payload_list": pl["name"]})
            print(f"    + {pl.get('name', '?')} ({pt_name})")

        # Set final status
        if target_status != "unlocked":
            put(f"gt_change_status/{gt['name']}/{target_status}", {})
            print(f"    -> status: {target_status}")

    # 4. Create IOVs and attach to first GT that has the matching type
    print("\nCreating and attaching IOVs...")
    gt_payload_lists = {}
    for gt in GLOBAL_TAGS:
        if gt["types"]:
            pl_data = get(f"gtPayloadLists/{gt['name']}")
            if pl_data:
                gt_payload_lists[gt["name"]] = pl_data

    for iov_def in IOVS:
        piov = post("piov", {
            "payload_url": iov_def["payload_url"],
            "major_iov": iov_def["major_iov"],
            "minor_iov": iov_def["minor_iov"],
            "major_iov_end": iov_def["major_iov_end"],
            "minor_iov_end": iov_def["minor_iov_end"],
        })
        if not piov:
            continue

        # Attach to first unlocked GT that has this payload type
        for gt in GLOBAL_TAGS:
            if gt["status"] == "frozen":
                continue
            pls = gt_payload_lists.get(gt["name"], {})
            pl_name = pls.get(iov_def["type"])
            if pl_name:
                put("piov_attach", {"payload_list": pl_name, "piov_id": piov["id"]})
                print(f"  {iov_def['payload_url']} -> {pl_name} ({gt['name']})")
                break

    # 5. Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    gts_data = get("globalTags")
    if isinstance(gts_data, list):
        fmt = "{:<30} {:<10} {:>4} {:>5}"
        print(fmt.format("Name", "Status", "PLs", "IOVs"))
        print("-" * 55)
        for gt in sorted(gts_data, key=lambda x: x["name"]):
            print(fmt.format(gt["name"], gt["status"], gt["payload_lists_count"], gt["payload_iov_count"]))
        print(f"\nTotal: {len(gts_data)} Global Tags")

    pts_data = get("pt")
    pls_data = get("pl")
    if isinstance(pts_data, list):
        print(f"Total: {len(pts_data)} Payload Types")
    if isinstance(pls_data, list):
        print(f"Total: {len(pls_data)} Payload Lists")

    # Readback test
    print("\nReadback test:")
    result = get("payloadiovs/", {"gtName": "Production_2024", "majorIOV": 0, "minorIOV": 0})
    if isinstance(result, list):
        print(f"  payloadiovs for Production_2024 @ (0,0): {len(result)} results")
    else:
        print(f"  payloadiovs response: {result}")


if __name__ == "__main__":
    populate()

