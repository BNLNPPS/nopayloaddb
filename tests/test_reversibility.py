"""Which changes can be undone, and which invalidate the baseline."""

import pytest

from bench.reversibility import ADVISORY, IRREVERSIBLE, REVERSIBLE, UNKNOWN, baseline_advice, classify


class TestClassify:
    @pytest.mark.parametrize("sql", ['ANALYZE "PayloadIOV";', "analyze payloadiov"])
    def test_analyze_is_irreversible(self, sql):
        c = classify(sql)
        assert c["reversibility"] == IRREVERSIBLE
        assert c["requires_fresh_baseline"] is True

    def test_vacuum_is_irreversible_and_mentions_the_visibility_map(self):
        c = classify('VACUUM (ANALYZE) "PayloadIOV";')
        assert c["reversibility"] == IRREVERSIBLE
        assert "visibility map" in c["undo"]

    def test_reindex_is_irreversible(self):
        assert classify("REINDEX CONCURRENTLY covering_idx;")["reversibility"] == IRREVERSIBLE

    def test_create_index_is_reversible_and_names_the_undo(self):
        c = classify("CREATE INDEX CONCURRENTLY covering_idx_v2 ON \"PayloadIOV\" (x);")
        assert c["reversibility"] == REVERSIBLE
        assert "DROP INDEX CONCURRENTLY covering_idx_v2" in c["undo"]
        assert c["requires_fresh_baseline"] is False

    def test_alter_system_is_reversible_but_warns_about_configmap_conflict(self):
        c = classify("ALTER SYSTEM SET work_mem = '64MB';")
        assert c["reversibility"] == REVERSIBLE
        assert "ALTER SYSTEM RESET work_mem" in c["undo"]
        assert "postgresql.auto.conf wins" in c["undo"]

    def test_set_is_reversible(self):
        assert "RESET work_mem" in classify("SET work_mem = '64MB';")["undo"]

    def test_alter_table_storage_parameter_is_reversible(self):
        c = classify('ALTER TABLE "PayloadIOV" SET (autovacuum_vacuum_scale_factor = 0.05);')
        assert c["reversibility"] == REVERSIBLE
        assert "PayloadIOV" in c["undo"]

    def test_temp_table_is_advisory(self):
        c = classify("CREATE TEMP TABLE _gt_lookup ON COMMIT DROP AS SELECT 1;")
        assert c["reversibility"] == ADVISORY
        assert c["requires_fresh_baseline"] is False

    @pytest.mark.parametrize("sql", [None, "", "   "])
    def test_no_sql_is_advisory(self, sql):
        assert classify(sql)["reversibility"] == ADVISORY

    def test_unrecognised_sql_is_treated_as_irreversible(self):
        # Fail safe: an unknown statement must not be assumed harmless.
        c = classify("FROBNICATE the_database;")
        assert c["reversibility"] == UNKNOWN
        assert c["requires_fresh_baseline"] is True


class TestAdvice:
    def test_irreversible_advice_mentions_the_baseline(self):
        assert "no longer a valid comparison point" in baseline_advice('ANALYZE "PayloadIOV";')

    def test_reversible_advice_is_short(self):
        assert baseline_advice("SET work_mem = '64MB';").startswith("Reversible")
