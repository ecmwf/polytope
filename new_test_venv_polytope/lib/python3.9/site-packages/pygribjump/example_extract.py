import os
os.environ['GRIBJUMP_HOME'] = '/path/to/gribjump/build/'
os.environ['GRIBJUMP_CONFIG_FILE'] = "/path/to/gribjump/config.yaml"

import pygribjump as pygj

gj = pygj.GribJump()

reqstrs = [
    {"class": "od", "type": "fc", "stream": "oper", "expver": "0001", "levtype": "sfc", "param": "151130", "date": "20230710", "time": "1200", "step": "1", "domain": "g"},
    {"class": "od", "type": "fc", "stream": "oper", "expver": "0001", "levtype": "sfc", "param": "151130", "date": "20230710", "time": "1200", "step": "2", "domain": "g"},
    {"class": "od", "type": "fc", "stream": "oper", "expver": "0001", "levtype": "sfc", "param": "151130", "date": "20230710", "time": "1200", "step": "3/4", "domain": "g"},
    {"class": "od", "type": "fc", "stream": "oper", "expver": "0001", "levtype": "pl", "levelist": "850", "param": "130.128", "date": "20170101", "time": "0000", "step": "0", "domain": "g"},
]

ranges = [
    [(1,5), (10,20)],
    [(1,2), (3,4), (5,6)],
    [(1,20)],
    [(1000, 1005), (12000, 12005)],
]

polyrequest = [
    (reqstrs[i], ranges[i]) for i in range(len(reqstrs))
]

res = gj.extract(polyrequest)

print()
print("--------------------")
print("EXTRACT OUTPUT:")
print("--------------------")
for i in range(len(res)):
    print(f"Request {i} - {reqstrs[i]}")
    if len(res[i]) == 0:
        print("**No data**")
    for j in range(len(res[i])):
       print(f"Field {j}:")
       for k in range(len(res[i][j])):
            data = res[i][j][k][0]
            print(f"Range {k}: {ranges[i][k]}; Values:")
            print(data)
    print()
# %%
