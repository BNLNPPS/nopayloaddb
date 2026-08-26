"""EXPLAIN JSON fixtures shaped like the real payloadiovs/ LATERAL JOIN plan."""


def _lateral(pi_node, total_time=120.0):
    """Wrap a PayloadIOV scan node in the production LATERAL JOIN shape."""
    return [{
        "Plan": {
            "Node Type": "Nested Loop",
            "Join Type": "Inner",
            "Startup Cost": 0.7,
            "Total Cost": 900.0,
            "Plan Rows": 12,
            "Actual Rows": 12,
            "Actual Loops": 1,
            "Actual Total Time": total_time,
            "Shared Hit Blocks": 40,
            "Shared Read Blocks": 2,
            "Plans": [
                {
                    "Node Type": "Hash Join",
                    "Join Type": "Inner",
                    "Plan Rows": 12,
                    "Actual Rows": 12,
                    "Actual Loops": 1,
                    "Actual Total Time": 1.2,
                    "Shared Hit Blocks": 20,
                    "Shared Read Blocks": 0,
                    "Plans": [
                        {
                            "Node Type": "Seq Scan",
                            "Relation Name": "PayloadList",
                            "Plan Rows": 12,
                            "Actual Rows": 12,
                            "Actual Loops": 1,
                            "Actual Total Time": 0.3,
                            "Shared Hit Blocks": 4,
                            "Shared Read Blocks": 0,
                        },
                        {
                            "Node Type": "Hash",
                            "Hash Batches": 1,
                            "Original Hash Batches": 1,
                            "Plan Rows": 1,
                            "Actual Rows": 1,
                            "Actual Loops": 1,
                            "Actual Total Time": 0.2,
                            "Shared Hit Blocks": 2,
                            "Shared Read Blocks": 0,
                            "Plans": [{
                                "Node Type": "Index Scan",
                                "Relation Name": "GlobalTag",
                                "Plan Rows": 1,
                                "Actual Rows": 1,
                                "Actual Loops": 1,
                                "Actual Total Time": 0.1,
                                "Shared Hit Blocks": 2,
                                "Shared Read Blocks": 0,
                            }],
                        },
                    ],
                },
                pi_node,
            ],
        },
        "Execution Time": total_time,
    }]


# R6 baseline: covering_idx bypassed, planner estimate wildly wrong.
SEQ_SCAN_STALE_STATS = _lateral({
    "Node Type": "Seq Scan",
    "Relation Name": "PayloadIOV",
    "Plan Rows": 94,
    "Actual Rows": 1400000,
    "Actual Loops": 12,
    "Actual Total Time": 810.0,
    "Shared Hit Blocks": 120,
    "Shared Read Blocks": 48000,
}, total_time=830.0)

# R6/R2 after ANALYZE: index used again, estimate close to reality.
INDEX_SCAN_FRESH_STATS = _lateral({
    "Node Type": "Index Scan",
    "Relation Name": "PayloadIOV",
    "Index Name": "covering_idx",
    "Plan Rows": 1350000,
    "Actual Rows": 1400000,
    "Actual Loops": 12,
    "Actual Total Time": 190.0,
    "Shared Hit Blocks": 9000,
    "Shared Read Blocks": 1200,
}, total_time=205.0)

# R7 baseline: plain Index Scan, so every row still visits the heap.
INDEX_SCAN_HEAP = _lateral({
    "Node Type": "Index Scan",
    "Relation Name": "PayloadIOV",
    "Index Name": "covering_idx",
    "Plan Rows": 1350000,
    "Actual Rows": 1400000,
    "Actual Loops": 12,
    "Actual Total Time": 190.0,
    "Shared Hit Blocks": 9000,
    "Shared Read Blocks": 1200,
}, total_time=205.0)

# R7 confirmed: covering_idx_v2 with INCLUDE columns, heap fetches eliminated.
INDEX_ONLY_SCAN_CLEAN = _lateral({
    "Node Type": "Index Only Scan",
    "Relation Name": "PayloadIOV",
    "Index Name": "covering_idx_v2",
    "Heap Fetches": 0,
    "Plan Rows": 1350000,
    "Actual Rows": 1400000,
    "Actual Loops": 12,
    "Actual Total Time": 55.0,
    "Shared Hit Blocks": 6200,
    "Shared Read Blocks": 90,
}, total_time=62.0)

# R7 refuted: Index Only Scan but a stale visibility map, so the heap is still read.
INDEX_ONLY_SCAN_STALE_VM = _lateral({
    "Node Type": "Index Only Scan",
    "Relation Name": "PayloadIOV",
    "Index Name": "covering_idx_v2",
    "Heap Fetches": 1380000,
    "Plan Rows": 1350000,
    "Actual Rows": 1400000,
    "Actual Loops": 12,
    "Actual Total Time": 188.0,
    "Shared Hit Blocks": 9100,
    "Shared Read Blocks": 1150,
}, total_time=200.0)


def _sort_plan(sort_method, total_time, disk_kb=None):
    node = {
        "Node Type": "Sort",
        "Sort Method": sort_method,
        "Sort Key": ["pi.comb_iov DESC"],
        "Plan Rows": 500000,
        "Actual Rows": 500000,
        "Actual Loops": 1,
        "Actual Total Time": total_time,
        "Shared Hit Blocks": 100,
        "Shared Read Blocks": 20,
        "Plans": [{
            "Node Type": "Seq Scan",
            "Relation Name": "PayloadIOV",
            "Plan Rows": 500000,
            "Actual Rows": 500000,
            "Actual Loops": 1,
            "Actual Total Time": 40.0,
            "Shared Hit Blocks": 90,
            "Shared Read Blocks": 20,
        }],
    }
    if disk_kb:
        node["Sort Space Used"] = disk_kb
        node["Sort Space Type"] = "Disk"
    return [{"Plan": node, "Execution Time": total_time}]


EXTERNAL_MERGE_SORT = _sort_plan("external merge", 940.0, disk_kb=210000)
QUICKSORT = _sort_plan("quicksort", 120.0)


def _hash_plan(batches, total_time):
    return [{
        "Plan": {
            "Node Type": "Hash Join",
            "Join Type": "Inner",
            "Plan Rows": 200000,
            "Actual Rows": 200000,
            "Actual Loops": 1,
            "Actual Total Time": total_time,
            "Shared Hit Blocks": 500,
            "Shared Read Blocks": 100,
            "Plans": [
                {
                    "Node Type": "Seq Scan",
                    "Relation Name": "PayloadList",
                    "Plan Rows": 200000,
                    "Actual Rows": 200000,
                    "Actual Loops": 1,
                    "Actual Total Time": 30.0,
                    "Shared Hit Blocks": 200,
                    "Shared Read Blocks": 50,
                },
                {
                    "Node Type": "Hash",
                    "Hash Batches": batches,
                    "Original Hash Batches": batches,
                    "Hash Buckets": 8192,
                    "Plan Rows": 100000,
                    "Actual Rows": 100000,
                    "Actual Loops": 1,
                    "Actual Total Time": 60.0,
                    "Shared Hit Blocks": 300,
                    "Shared Read Blocks": 50,
                    "Plans": [{
                        "Node Type": "Seq Scan",
                        "Relation Name": "PayloadIOV",
                        "Plan Rows": 100000,
                        "Actual Rows": 100000,
                        "Actual Loops": 1,
                        "Actual Total Time": 25.0,
                        "Shared Hit Blocks": 300,
                        "Shared Read Blocks": 50,
                    }],
                },
            ],
        },
        "Execution Time": total_time,
    }]


HASH_JOIN_SPILL = _hash_plan(8, 780.0)
HASH_JOIN_IN_MEMORY = _hash_plan(1, 210.0)
