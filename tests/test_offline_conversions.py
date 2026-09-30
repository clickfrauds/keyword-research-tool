"""Offline: the job action is created with every new campaign (Stage 0-CONV),
from the SAME definition the uploader uses, and the bidding-readiness report
reads the gates right. No credentials, no network."""
import os
import sys
import types
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import upload_offline_conversions as up  # noqa: E402
import setup_conversions as sc  # noqa: E402

try:
    from google.ads.googleads.client import GoogleAdsClient
    from google.ads.googleads.errors import GoogleAdsException
    HAVE_ADS = True
except Exception:  # pragma: no cover - CI installs requirements.txt
    HAVE_ADS = False


def _row(**kw):
    return types.SimpleNamespace(**kw)


class Graduation(unittest.TestCase):
    def test_under_30_stays_manual(self):
        a = up.graduation_advice(12, 30000, False, ["MANUAL_CPC"])
        self.assertEqual(a["stage"], "manual")
        self.assertNotIn("WARNING", a["advice"])

    def test_smart_bidding_too_early_is_flagged(self):
        a = up.graduation_advice(5, 30000, False, ["MAXIMIZE_CONVERSIONS"])
        self.assertEqual(a["stage"], "manual")
        self.assertIn("WARNING", a["advice"])

    def test_30_to_49_is_maximize_conversions(self):
        a = up.graduation_advice(35, 70000, False, ["MANUAL_CPC"])
        self.assertEqual(a["stage"], "maximize_conversions")
        self.assertIn("PRIMARY", a["advice"])

    def test_50_plus_is_target_cpa_at_110_percent(self):
        a = up.graduation_advice(60, 60000, True, ["MAXIMIZE_CONVERSIONS"])
        self.assertEqual(a["stage"], "target_cpa")
        self.assertEqual(a["cpa"], 1000)
        self.assertEqual(a["target_cpa"], 1100)

    def test_reads_only_the_offline_action(self):
        class Svc:
            def search(self, customer_id, query):
                if "conversion_action_name" in query:
                    return [_row(segments=_row(conversion_action_name="Job (offline)"),
                                 metrics=_row(all_conversions=31)),
                            _row(segments=_row(conversion_action_name="Phone Call Click"),
                                 metrics=_row(all_conversions=400))]
                if "cost_micros" in query:
                    return [_row(metrics=_row(cost_micros=62_000_000_000))]
                if "primary_for_goal" in query:
                    return [_row(conversion_action=_row(primary_for_goal=False))]
                return [_row(campaign=_row(bidding_strategy_type=_row(name="MANUAL_CPC")))]
        a = up.readiness_for_account(Svc(), "123")
        self.assertEqual(a["jobs_30d"], 31)
        self.assertEqual(a["cpa"], 2000)
        self.assertEqual(a["stage"], "maximize_conversions")


@unittest.skipUnless(HAVE_ADS, "google-ads not installed")
class OfflineActionAtSetup(unittest.TestCase):
    def setUp(self):
        self.client = GoogleAdsClient(credentials=None, developer_token="x", use_proto_plus=True)
        sc.PUSH_CUSTOMER_ID = "1234567890"
        self.sent = []

        test = self

        class CaSvc:
            def mutate_conversion_actions(self, request):
                test.sent.append(request)
        self.ca_svc = CaSvc()

    def _svc(self, rows):
        class Svc:
            def search(self, customer_id, query):
                return rows
        return Svc()

    def test_one_definition_upload_clicks_not_primary(self):
        op = up.build_offline_action_op(self.client, "Job (offline)")
        ca = op.create
        self.assertEqual(ca.type_, self.client.enums.ConversionActionTypeEnum.UPLOAD_CLICKS)
        self.assertEqual(ca.category, self.client.enums.ConversionActionCategoryEnum.CONVERTED_LEAD)
        self.assertFalse(ca.primary_for_goal)
        self.assertEqual(ca.click_through_lookback_window_days, 90)

    def test_created_with_the_campaign_in_validate_mode(self):
        status = sc.ensure_offline_action(self.client, self._svc([]), self.ca_svc,
                                          True, GoogleAdsException)
        self.assertEqual(status, "would create")
        self.assertEqual(len(self.sent), 1)
        req = self.sent[0]
        self.assertTrue(req.validate_only)
        self.assertEqual(req.customer_id, "1234567890")
        self.assertEqual(req.operations[0].create.name, "Job (offline)")

    def test_existing_action_is_left_alone(self):
        ca = _row(resource_name="customers/1/conversionActions/9", id=9, name="job (OFFLINE)",
                  status=_row(name="ENABLED"), tag_snippets=[])
        status = sc.ensure_offline_action(self.client, self._svc([_row(conversion_action=ca)]),
                                          self.ca_svc, False, GoogleAdsException)
        self.assertEqual(status, "exists")
        self.assertEqual(self.sent, [])

    def test_never_raises(self):
        class Broken:
            def search(self, customer_id, query):
                raise RuntimeError("quota")
        self.assertEqual(sc.ensure_offline_action(self.client, Broken(), self.ca_svc, False,
                                                  GoogleAdsException), "lookup failed")


if __name__ == "__main__":
    unittest.main()
