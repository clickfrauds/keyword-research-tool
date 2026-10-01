"""A keyword Google refuses on policy grounds is dropped, not the campaign.
Real google-ads message types, no credentials, no network."""
import os
import sys
import types
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

try:
    from google.ads.googleads.client import GoogleAdsClient
    HAVE_ADS = True
except Exception:  # pragma: no cover
    HAVE_ADS = False


@unittest.skipUnless(HAVE_ADS, "google-ads not installed")
class PolicyKeywordOps(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import push_to_google_ads as p
        cls.p = p
        cls.c = GoogleAdsClient(credentials=None, developer_token="x", use_proto_plus=True)

    def _kw_op(self, text):
        o = self.c.get_type("MutateOperation")
        o.ad_group_criterion_operation.create.keyword.text = text
        return o

    def _campaign_op(self):
        o = self.c.get_type("MutateOperation")
        o.campaign_operation.create.name = "C"
        return o

    def _exc(self, *errs):
        failure = self.c.get_type("GoogleAdsFailure")
        for idx, code in errs:
            e = self.c.get_type("GoogleAdsError")
            if code == "policy":
                e.error_code._pb.policy_violation_error = 2      # POLICY_ERROR
                e.details.policy_violation_details.external_policy_name = "Trademarks"
            else:
                e.error_code._pb.request_error = 1               # UNKNOWN
            el = self.c.get_type("ErrorLocation").FieldPathElement()
            el.field_name = "mutate_operations"
            el.index = idx
            e.location.field_path_elements.append(el)
            failure.errors.append(e)
        return types.SimpleNamespace(failure=failure)

    def test_keyword_policy_errors_are_droppable(self):
        ops = [self._campaign_op(), self._kw_op("fridge repair"),
               self._kw_op("haier led tv screen replacement cost")]
        got = self.p.policy_keyword_ops(self._exc((2, "policy")), ops)
        self.assertEqual(got, [(2, "haier led tv screen replacement cost", "Trademarks")])

    def test_policy_error_on_a_non_keyword_stops(self):
        ops = [self._campaign_op(), self._kw_op("fridge repair")]
        self.assertIsNone(self.p.policy_keyword_ops(self._exc((0, "policy")), ops))

    def test_any_other_error_stops(self):
        ops = [self._campaign_op(), self._kw_op("a"), self._kw_op("b")]
        self.assertIsNone(self.p.policy_keyword_ops(
            self._exc((1, "policy"), (2, "other")), ops))

    def test_index_out_of_range_stops(self):
        self.assertIsNone(self.p.policy_keyword_ops(
            self._exc((9, "policy")), [self._kw_op("a")]))


if __name__ == "__main__":
    unittest.main()
