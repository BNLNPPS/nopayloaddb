import sys
import requests

# Config
TOKEN = "token"
HEADERS = {"Content-Type": "application/json", "Authorization": f"Bearer {TOKEN}"}
DEST_DB = "http://localhost:8000/api/cdb_rest/"
gt_name = "generic_gt"  # Fully generic GT name

def post(api, obj):
    r = requests.post(f"{DEST_DB}{api}", headers=HEADERS, json=obj)
    return r.json()

def put(api, obj):
    r = requests.put(f"{DEST_DB}{api}", headers=HEADERS, json=obj)
    return r.json()

#def get(api, params=None):
#    r = requests.get(f"{DEST_DB}{api}", headers=HEADERS, params=params)
#    return r.json()
#

# 1️⃣ Create GT statuses
for status in ['unlocked', 'locked']:
    post('gtstatus', {'name': status})

# 2️⃣ Generic GT to migrate
gts = [{
    'name': gt_name,
    'description': 'Generic global tag description',
    'globalTagId': 0,  # placeholder
}]

for gt in gts:
    print("Processing GT:", gt['name'])

    # Create GT
    gt_obj = {'name': gt['name'], 'status': 'unlocked', 'description': gt['description']}
    post('gt', gt_obj)

    # 3️⃣ Generic Payloads for this GT
    payloads = [{
        'payload_url': '/example/payload1.root',
        'payload_type_name': 'GenericModule',
        'payload_iovs': [
            {'expStart': 0, 'expEnd': 1, 'runStart': 0, 'runEnd': 10}
        ]
    }]

    for payload in payloads:
        print("Payload:", payload['payload_url'])

        # Create Payload Type
        pt = post('pt', {'name': payload['payload_type_name']})

        # Create Payload List
        pl = post('pl', {'payload_type': payload['payload_type_name']})

        # Attach Payload List to GT
        put('pl_attach', {
            'global_tag': gt['name'],
            'payload_type': payload['payload_type_name'],
            'payload_list': pl['name']
        })

        # Create Payload IOVs
        for iov in payload['payload_iovs']:
            exp_end = sys.maxsize if iov['expEnd'] == -1 else iov['expEnd']
            run_end = sys.maxsize if iov['runEnd'] == -1 else iov['runEnd'] + 1

            piov = post('piov', {
                'payload_url': payload['payload_url'],
                'major_iov': iov['expStart'],
                'minor_iov': iov['runStart'],
                'major_iov_end': exp_end,
                'minor_iov_end': run_end,
                'checksum': 'dummy_checksum'
            })

            # Attach Payload IOV to Payload List
            put('piov_attach', {'payload_list': pl['name'], 'piov_id': piov['id']})

# Read back IOV info for GT
#query_params = {
#    'gtName': gt_name,
#    'majorIOV': 10,
#    'minorIOV': 10
#}
#iov_data = get('', params=query_params)
#print("\n=== Read back IOV Data ===")
#print(iov_data)

#READBACK
#curl "http://localhost:8000/api/cdb_rest/payloadiovs/?gtName=generic_gt&majorIOV=10&minorIOV=10"

