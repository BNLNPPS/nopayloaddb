"""The 13 rules, the safe_sql boundary, and the bugs each fix closed."""

import pytest

from tests.rule_engine_import import rule_engine as R


def node(node_type, relation=None, plan_rows=0, actual_rows=0, loops=1,
         hit=0, read=0, children=None, **props):
    return R.PlanNode(
        node_type=node_type, relation=relation, startup_cost=0.0, total_cost=0.0,
        plan_rows=plan_rows, actual_rows=actual_rows, actual_loops=loops,
        actual_time_ms=0.0, shared_hit_blocks=hit, shared_read_blocks=read,
        properties=props, children=children or [],
    )


def ctx(**kw):
    base = dict(queryid="q1", query_text="SELECT 1", mean_exec_time=1.0, calls=1,
                rows_count=1, shared_blks_read=0, shared_blks_hit=0,
                total_exec_time=1.0, stddev_exec_time=0.0)
    base.update(kw)
    return R.RuleContext(**base)


def fire(root, context):
    return {s.rule_id for s in R.RuleEngine().run(root, context)}


class TestValidateSafeSql:
    @pytest.mark.parametrize("sql", [
        'ANALYZE "PayloadIOV";',
        'VACUUM (ANALYZE) "PayloadIOV";',
        'CREATE INDEX CONCURRENTLY i ON "PayloadIOV" (x);',
        'REINDEX CONCURRENTLY covering_idx;',
        'ALTER TABLE "PayloadIOV" SET (autovacuum_vacuum_scale_factor = 0.05);',
    ])
    def test_allowed(self, sql):
        assert R.validate_safe_sql(sql) == sql

    @pytest.mark.parametrize("sql", [
        'ANALYZE "PayloadIOV"; DROP INDEX covering_idx;',
        'ANALYZE "PayloadIOV"; TRUNCATE "PayloadIOV";',
        'ANALYZE "PayloadIOV" -- ; DROP INDEX covering_idx',
        'ANALYZE /* sneaky */ "PayloadIOV"',
        'VACUUM; DROP TABLE "GlobalTag"',
    ])
    def test_rejects_smuggling(self, sql):
        assert R.validate_safe_sql(sql) is None

    @pytest.mark.parametrize("sql", [
        "DROP TABLE \"PayloadIOV\";", "TRUNCATE \"PayloadIOV\";",
        "UPDATE \"PayloadIOV\" SET size = 0;", "DELETE FROM \"PayloadIOV\";",
        "GRANT ALL ON \"PayloadIOV\" TO PUBLIC;",
    ])
    def test_rejects_destructive(self, sql):
        assert R.validate_safe_sql(sql) is None

    def test_rejects_session_set(self):
        # Session-scoped, so it never reaches Django's workers.
        assert R.validate_safe_sql("SET work_mem = '64MB';") is None

    def test_rejects_alter_system(self):
        # Writes postgresql.auto.conf, which outranks the ConfigMap.
        assert R.validate_safe_sql("ALTER SYSTEM SET work_mem = '64MB';") is None

    @pytest.mark.parametrize("sql", [None, "", "   "])
    def test_empty(self, sql):
        assert R.validate_safe_sql(sql) is None


class TestIsExecutable:
    def test_plain_sql_is_executable(self):
        assert R.is_executable_safe_sql('ANALYZE "PayloadIOV";') is True

    def test_placeholder_sql_is_not(self):
        # R13's advice carries %(my_gt)s, which psycopg would try to bind.
        assert R.is_executable_safe_sql(
            'CREATE TEMP TABLE _gt ON COMMIT DROP AS SELECT id FROM "GlobalTag" '
            'WHERE name = %(my_gt)s;') is False

    def test_rejected_sql_is_not_executable(self):
        assert R.is_executable_safe_sql("DROP TABLE x;") is False


class TestQuoteIdent:
    def test_quotes(self):
        assert R.quote_ident("PayloadIOV") == '"PayloadIOV"'

    def test_escapes_embedded_quote(self):
        assert R.quote_ident('we"ird') == '"we""ird"'


FILTER = {"Filter": "(payload_list_id = 42)"}


class TestR1SeqScan:
    def test_fires_on_a_genuinely_large_filtered_scan(self):
        assert "R1" in fire(node("Seq Scan", "PayloadIOV", actual_rows=50000, **FILTER), ctx())

    def test_counts_rows_across_loops(self):
        # 10 rows x 5000 loops = 50k rows of work, which per-loop reads as 10.
        assert "R1" in fire(node("Seq Scan", "PayloadIOV", actual_rows=10, loops=5000, **FILTER),
                            ctx())

    def test_silent_on_an_unfiltered_full_table_read(self):
        # No predicate means a Seq Scan is optimal; this fired on real traffic.
        assert "R1" not in fire(node("Seq Scan", "PayloadIOV", actual_rows=50000), ctx())

    def test_silent_on_a_small_scan(self):
        assert "R1" not in fire(node("Seq Scan", "PayloadList", actual_rows=12, **FILTER), ctx())

    def test_silent_without_actuals(self):
        assert "R1" not in fire(node("Seq Scan", "PayloadIOV", actual_rows=50000, **FILTER),
                                ctx(has_actuals=False))


class TestR2StaleStats:
    def test_fires_on_a_large_misestimate(self):
        assert "R2" in fire(node("Index Scan", "PayloadIOV", plan_rows=94, actual_rows=1_400_000), ctx())

    def test_silent_on_a_trivial_node(self):
        # A 32x error over nine rows: real arithmetic, zero operational meaning.
        assert "R2" not in fire(node("Seq Scan", "explain_plans", plan_rows=290, actual_rows=9), ctx())

    def test_silent_without_actuals(self):
        assert "R2" not in fire(
            node("Index Scan", "PayloadIOV", plan_rows=94, actual_rows=1_400_000),
            ctx(has_actuals=False))

    def test_generated_sql_is_quoted(self):
        s = [x for x in R.RuleEngine().run(
            node("Index Scan", "PayloadIOV", plan_rows=94, actual_rows=1_400_000), ctx())
            if x.rule_id == "R2"][0]
        assert s.safe_sql == 'ANALYZE "PayloadIOV";'


class TestR3R4WorkMem:
    def test_hash_spill_is_advisory_not_a_no_op_set(self):
        s = [x for x in R.RuleEngine().run(node("Hash", **{"Hash Batches": 8}), ctx())
             if x.rule_id == "R3"][0]
        assert s.safe_sql is None
        assert "ConfigMap" in s.message

    def test_external_sort_is_advisory(self):
        s = [x for x in R.RuleEngine().run(
            node("Sort", **{"Sort Method": "external merge Disk: 210000kB"}), ctx())
            if x.rule_id == "R4"][0]
        assert s.safe_sql is None
        assert "ConfigMap" in s.message

    def test_in_memory_sort_is_silent(self):
        assert "R4" not in fire(node("Sort", **{"Sort Method": "quicksort"}), ctx())


class TestR5CacheMiss:
    def test_fires_on_meaningful_io(self):
        assert "R5" in fire(node("Seq Scan", "PayloadIOV", hit=1000, read=40000), ctx())

    def test_silent_on_two_blocks(self):
        # 1 miss of 2 blocks is a 50% miss ratio and means nothing.
        assert "R5" not in fire(node("Seq Scan", "PayloadIOV", hit=1, read=1), ctx())

    def test_silent_without_actuals(self):
        assert "R5" not in fire(node("Seq Scan", "PayloadIOV", hit=1000, read=40000),
                                ctx(has_actuals=False))


class TestR6CoveringIndexBypassed:
    def test_fires_when_the_covering_index_path_is_seq_scanned(self):
        assert "R6" in fire(
            node("Seq Scan", "PayloadIOV", actual_rows=1_400_000, **FILTER), ctx())

    def test_silent_on_an_unfiltered_aggregate(self):
        # An unfiltered scan was never a candidate for covering_idx.
        assert "R6" not in fire(node("Seq Scan", "PayloadIOV", actual_rows=1_400_000), ctx())

    def test_silent_when_filtering_on_an_unrelated_column(self):
        assert "R6" not in fire(
            node("Seq Scan", "PayloadIOV", actual_rows=1_400_000,
                 **{"Filter": "(checksum = 'abc')"}), ctx())

    def test_silent_on_a_tiny_seq_scan(self):
        assert "R6" not in fire(node("Seq Scan", "PayloadIOV", actual_rows=5, **FILTER), ctx())


class TestR7CoveringIndexInclude:
    LATERAL = "SELECT ... JOIN LATERAL ( SELECT ... ) pi ON true"

    def test_fires_on_index_scan_in_the_lateral_path(self):
        s = fire(node("Index Scan", "PayloadIOV", actual_rows=1000),
                 ctx(query_text=self.LATERAL))
        assert "R7" in s

    def test_silent_once_the_include_index_exists(self):
        # Otherwise it re-fires every cycle after being applied.
        assert "R7" not in fire(
            node("Index Scan", "PayloadIOV", actual_rows=1000),
            ctx(query_text=self.LATERAL,
                existing_indexes=('CREATE INDEX covering_idx_v2 ON public."PayloadIOV" '
                                  '(payload_list_id, comb_iov) INCLUDE (payload_url)',)))

    def test_silent_when_already_index_only(self):
        root = node("Nested Loop", children=[node("Index Only Scan", "PayloadIOV", actual_rows=1000)])
        assert "R7" not in fire(root, ctx(query_text=self.LATERAL))

    def test_carries_the_visibility_map_prerequisite(self):
        s = [x for x in R.RuleEngine().run(
            node("Index Scan", "PayloadIOV", actual_rows=1000), ctx(query_text=self.LATERAL))
            if x.rule_id == "R7"][0]
        assert s.prerequisite and "all-visible" in s.prerequisite


class TestWindowedHotness:
    """R8/R9/R12 must judge current load, not load since the server booted."""

    def test_r8_silent_on_cumulative_calls_alone(self):
        # Lifetime calls high, none this cycle: not hot now.
        assert "R8" not in fire(node("Result"), ctx(calls=50000, window_calls=0,
                                                    stddev_exec_time=1.0))

    def test_r8_fires_on_window_traffic(self):
        assert "R8" in fire(node("Result"), ctx(calls=50000, window_calls=5000,
                                                stddev_exec_time=1.0))

    def test_r8_silent_on_first_sighting(self):
        # No previous reading, so no window exists.
        assert "R8" not in fire(node("Result"), ctx(calls=50000, window_calls=None,
                                                    stddev_exec_time=1.0))

    def test_r9_needs_a_really_locked_global_tag(self):
        base = dict(query_text="SELECT * FROM PayloadIOV", window_calls=5000,
                    global_tag_name="gt_1")
        assert "R9" not in fire(node("Result"), ctx(has_locked_gt=False, **base))
        assert "R9" in fire(node("Result"), ctx(has_locked_gt=True, **base))

    def test_r9_needs_to_know_which_global_tag(self):
        # The suggestion names the tag, so an unattributable query gets no advice.
        base = dict(query_text="SELECT * FROM PayloadIOV", window_calls=5000,
                    has_locked_gt=True)
        assert "R9" not in fire(node("Result"), ctx(global_tag_name=None, **base))

    def test_r12_uses_the_window_mean(self):
        text = "INSERT INTO GlobalTag ... PayloadList ..."
        # Cumulative mean slow, current window fast: not a problem now.
        assert "R12" not in fire(node("Result"),
                                 ctx(query_text=text, mean_exec_time=9000.0,
                                     window_mean_exec_time=12.0))
        assert "R12" in fire(node("Result"),
                             ctx(query_text=text, mean_exec_time=1.0,
                                 window_mean_exec_time=9000.0))


class TestR11AndR13:
    def test_r11_on_dead_tuple_ratio(self):
        assert "R11" in fire(node("Result"), ctx(payloadiov_dead_tuple_ratio=0.30))
        assert "R11" not in fire(node("Result"), ctx(payloadiov_dead_tuple_ratio=0.01))

    def test_r13_needs_actuals(self):
        root = node("Nested Loop", children=[node("Index Scan", "PayloadIOV", **{"Actual Loops": 500})])
        assert "R13" not in fire(root, ctx(query_text="JOIN LATERAL", has_actuals=False))


class TestParser:
    def test_reads_actual_loops(self):
        plan = [{"Plan": {"Node Type": "Seq Scan", "Relation Name": "PayloadIOV",
                          "Actual Rows": 10, "Actual Loops": 5000, "Plan Rows": 10}}]
        assert R.parse_explain_plan(plan).actual_loops == 5000

    def test_defaults_loops_to_one(self):
        plan = [{"Plan": {"Node Type": "Seq Scan", "Relation Name": "x"}}]
        assert R.parse_explain_plan(plan).actual_loops == 1

    def test_rejects_garbage(self):
        with pytest.raises(ValueError):
            R.parse_explain_plan({"nope": 1})


class TestNoRuleEmitsUnvalidatedSql:
    def test_every_generated_safe_sql_passes_the_allow_list(self):
        root = node("Nested Loop", actual_rows=500, loops=200, children=[
            node("Seq Scan", "PayloadIOV", plan_rows=94, actual_rows=1_400_000,
                 hit=1000, read=40000, **{"Filter": "(payload_list_id = 1)"}),
            node("Hash", **{"Hash Batches": 8}),
            node("Sort", **{"Sort Method": "external merge"}),
            node("Index Scan", "PayloadIOV", actual_rows=5000, **{"Actual Loops": 500}),
        ])
        suggestions = R.RuleEngine().run(
            root, ctx(query_text="JOIN LATERAL PayloadIOV GlobalTag PayloadList",
                      window_calls=5000, stddev_exec_time=1.0, has_locked_gt=True,
                      payloadiov_dead_tuple_ratio=0.3, window_mean_exec_time=9000.0))
        assert suggestions
        for s in suggestions:
            if s.safe_sql is not None:
                assert R.validate_safe_sql(s.safe_sql) == s.safe_sql, s.rule_id


class TestR6DistinguishesCause:
    """Two causes, two remedies: index present means stale stats, absent means create it."""

    COVERING = ('CREATE INDEX covering_idx ON public."PayloadIOV" '
                '(payload_list_id, comb_iov DESC NULLS LAST)',)

    def _suggestion(self, indexes):
        out = [x for x in R.RuleEngine().run(
            node("Seq Scan", "PayloadIOV", actual_rows=1_400_000, **FILTER),
            ctx(existing_indexes=indexes)) if x.rule_id == "R6"]
        return out[0] if out else None

    def test_index_present_means_stale_statistics(self):
        s = self._suggestion(self.COVERING)
        assert s.category == "STATISTICS"
        assert s.safe_sql == 'ANALYZE "PayloadIOV";'
        assert "declining it" in s.message

    def test_index_absent_recommends_creating_it(self):
        s = self._suggestion(())
        assert s.category == "INDEX"
        assert s.safe_sql.startswith("CREATE INDEX CONCURRENTLY covering_idx ")
        assert "ANALYZE will not help" in s.message

    def test_both_remedies_pass_the_allow_list(self):
        for indexes in (self.COVERING, ()):
            s = self._suggestion(indexes)
            assert R.validate_safe_sql(s.safe_sql) == s.safe_sql


class TestR2IgnoresEarlyStop:
    """A node beneath a LIMIT returns fewer rows than estimated by design. The
    production LATERAL subquery is exactly that shape, and R2 called it stale stats."""

    LIMITED = [{"Plan": {
        "Node Type": "Limit", "Plan Rows": 1, "Actual Rows": 1, "Actual Loops": 8,
        "Plans": [{
            "Node Type": "Index Scan", "Relation Name": "PayloadIOV",
            "Plan Rows": 14999, "Actual Rows": 1, "Actual Loops": 8,
        }],
    }}]

    UNLIMITED = [{"Plan": {
        "Node Type": "Index Scan", "Relation Name": "PayloadIOV",
        "Plan Rows": 14999, "Actual Rows": 1, "Actual Loops": 8,
    }}]

    def test_parser_marks_children_of_a_limit(self):
        root = R.parse_explain_plan(self.LIMITED)
        assert root.beneath_early_stop is False
        assert root.children[0].beneath_early_stop is True

    def test_silent_on_an_over_estimate_under_a_limit(self):
        assert "R2" not in fire(R.parse_explain_plan(self.LIMITED), ctx())

    def test_still_fires_on_the_same_shape_without_a_limit(self):
        assert "R2" in fire(R.parse_explain_plan(self.UNLIMITED), ctx())

    def test_under_estimates_still_fire_beneath_a_limit(self):
        # actual >> planned is a real problem regardless of early stopping.
        plan = [{"Plan": {
            "Node Type": "Limit", "Plan Rows": 1, "Actual Rows": 1,
            "Plans": [{"Node Type": "Seq Scan", "Relation Name": "PayloadIOV",
                       "Plan Rows": 94, "Actual Rows": 1_400_000}],
        }}]
        assert "R2" in fire(R.parse_explain_plan(plan), ctx())

    def test_semi_joins_also_stop_early(self):
        plan = [{"Plan": {
            "Node Type": "Nested Loop", "Join Type": "Semi",
            "Plan Rows": 1, "Actual Rows": 1,
            "Plans": [{"Node Type": "Index Scan", "Relation Name": "PayloadIOV",
                       "Plan Rows": 14999, "Actual Rows": 1}],
        }}]
        assert "R2" not in fire(R.parse_explain_plan(plan), ctx())
