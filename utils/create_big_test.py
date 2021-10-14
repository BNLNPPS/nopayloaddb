import os
import time
import requests
  
base_url = 'http://127.0.0.1:8000'
#base_url = 'http://188.185.87.14'

#Create GT type and status
GT_NAME = "TestSmallGT2"
NUM_PAYLOAD_LISTS = 10
NUM_PAYLOAD_IOVS = 10


gttype = {'name':'test', 'id': 1}
url = base_url + '/api/cdb_rest/gttype'
r = requests.post(url = url, json=gttype)

gtstatus = {'name':'test', 'id': 1}
url = base_url + '/api/cdb_rest/gtstatus'
r = requests.post(url = url, json=gtstatus)

pltype = {'name':'test', 'id':1}
url = base_url + '/api/cdb_rest/pt'
r = requests.post(url = url, json=pltype)

#Create GT
gt = {
       'name': GT_NAME,
       'status': 1,
       'type': 1
      }

url = base_url + '/api/cdb_rest/gt'
r = requests.post(url = url, json=gt)
data = r.json()
gt_id = data['id']
print("Global tag id = ", gt_id)

#Payload Lists ids
pl_ids = []

#Create PL
for i in range(0,NUM_PAYLOAD_LISTS):
    pl_name = GT_NAME+'List%d'% i
     
    plist = {
            'name': pl_name,
            'payload_type': 1,
            'global_tag': gt_id
            }

    url = base_url + '/api/cdb_rest/pl'
    r = requests.post(url = url, json=plist)
    data = r.json()
    pl_id = data['id'] 
    pl_ids.append(pl_id)


# FAKE A TIME stamp
first_iov = int(time.time())

#Create PIOV
for i in range(0,NUM_PAYLOAD_IOVS):
    iov = first_iov + i
    for pl_id in pl_ids:
        pname = GT_NAME+'Payload%d_%d' % (i,pl_id)
        piov = {
               'payload_url': pname,
               'payload_list': pl_id,
               'major_iov':  0,
               'minor_iov': iov
               }

        url = base_url + '/api/cdb_rest/piov'
        r = requests.post(url = url, json=piov)

