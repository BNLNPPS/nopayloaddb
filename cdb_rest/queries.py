get_payload_iovs = '''
WITH major_max_table AS(
    SELECT m.payload_list_id, m.payload_url, m.major_iov, m.minor_iov, t.major_max
    FROM (
        SELECT payload_list_id, MAX(major_iov) AS major_max
        FROM "PayloadIOV"
        WHERE ((major_iov < %(my_major_iov)s) OR (major_iov = %(my_major_iov)s AND minor_iov <= %(my_minor_iov)s))
        AND payload_list_id IN (
            SELECT id FROM "PayloadList"
            WHERE global_tag_id = (
                SELECT id FROM "GlobalTag"
                WHERE name = %(my_gt)s
            )
        )
    GROUP BY payload_list_id
    ) t JOIN "PayloadIOV" m ON m.payload_list_id = t.payload_list_id AND t.major_max = m.major_iov
),
major_minor_max_table AS(
    SELECT n.payload_list_id, n.payload_url, n.major_iov, n.minor_iov
    FROM (
        SELECT payload_list_id, MAX(minor_iov) AS minor_max
        FROM major_max_table
        GROUP BY payload_list_id
    ) u JOIN major_max_table n ON n.payload_list_id = u.payload_list_id AND u.minor_max = n.minor_iov
)
SELECT y.name AS payload_type_name, x.payload_url, x.major_iov, x.minor_iov
FROM
  major_minor_max_table x
  JOIN "PayloadList" z ON x.payload_list_id = z.id
  JOIN "PayloadType" y ON z.payload_type_id = y.id
;
'''
get_payload_iovs2 = '''
SELECT pt.name AS payload_type_name, pi.payload_url, pi.checksum, pi.major_iov, pi.minor_iov, pi.major_iov_end, pi.minor_iov_end
FROM "PayloadList" pl
JOIN "GlobalTag" gt ON pl.global_tag_id = gt.id AND gt.name = %(my_gt)s
JOIN LATERAL (
   SELECT payload_url, checksum, major_iov, minor_iov, major_iov_end, minor_iov_end
   FROM   "PayloadIOV" pi
   WHERE  pi.payload_list_id = pl.id
     AND pi.comb_iov <= CAST(%(my_major_iov)s + CAST(%(my_minor_iov)s AS DECIMAL(19,0)) / 10E18 AS DECIMAL(38,19))
   ORDER BY pi.comb_iov DESC NULLS LAST
   LIMIT 1
) pi ON true
JOIN "PayloadType" pt ON pl.payload_type_id = pt.id;
'''

