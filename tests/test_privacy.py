"""Privacy release regressions using fictional data only."""
import base64
import gzip
import json
import unittest

from data_construction.privacy import (
    BUSINESS_PLACEHOLDER, PLACEHOLDER, encoded_business_value,
    sanitize_json_row, validate_private_fields,
)


class PrivacyTest(unittest.TestCase):
    def test_review_record_scrubs_linkable_context_and_preserves_shape(self):
        review = {"author": {"name": "Fictional Reviewer", "user_id": 123},
                  "date": "2025-01-01", "hotel_id": 456, "review_id": 789,
                  "reviewer_photos": ["https://example.invalid/photo"],
                  "pros": "Fictional personal travel narrative", "average_score": 8.5}
        row = {"context": {"reviews": [review, review]}, "answer": "unchanged"}
        cleaned = sanitize_json_row(row)
        result = cleaned["context"]["reviews"]
        self.assertEqual(result[0], result[1])
        self.assertEqual(set(result[0]), set(review))
        self.assertEqual(result[0]["author"], {"name": PLACEHOLDER, "user_id": 0})
        self.assertEqual(result[0]["reviewer_photos"], [PLACEHOLDER])
        self.assertEqual(result[0]["hotel_id"], 0)
        self.assertEqual(result[0]["date"], PLACEHOLDER)
        self.assertEqual(result[0]["pros"], PLACEHOLDER)
        self.assertEqual(cleaned["answer"], "unchanged")
        self.assertEqual(cleaned, sanitize_json_row(cleaned))

    def test_business_references_and_encoded_fields_are_not_usable(self):
        compressed = base64.urlsafe_b64encode(gzip.compress(
            b"https://example.invalid/offer?selectionKey=fictional")).decode()
        encoded = base64.b64encode(json.dumps({"driversAge": 30, "pickup": "fictional"}).encode()).decode()
        row = {"context": {"token": "opaque", "offerReference": compressed,
                           "unrecognized_field": encoded,
                           "search_context": {"driversAge": 30, "pickup": "fictional"}}}
        cleaned = sanitize_json_row(row)
        self.assertEqual(cleaned["context"]["token"], BUSINESS_PLACEHOLDER)
        self.assertEqual(cleaned["context"]["offerReference"], BUSINESS_PLACEHOLDER)
        self.assertEqual(cleaned["context"]["unrecognized_field"], BUSINESS_PLACEHOLDER)
        self.assertEqual(cleaned["context"]["search_context"]["driversAge"], 0)
        validate_private_fields(cleaned)

    def test_reintroduced_fields_and_false_synthetic_claim_are_rejected(self):
        row = sanitize_json_row({"context": {"token": "fictional-original"}})
        row["context"]["token"] = "reintroduced-opaque-reference"
        with self.assertRaisesRegex(ValueError, "unsanitized"):
            validate_private_fields(row)
        row = sanitize_json_row({"context": {}})
        row["metadata"]["privacy_transform"]["whole_record_synthetic"] = True
        with self.assertRaisesRegex(ValueError, "source-derived"):
            validate_private_fields(row)

    def test_protected_answer_is_never_silently_replaced(self):
        encoded = base64.b64encode(json.dumps({"pinnedProduct": "fictional-id"}).encode()).decode()
        with self.assertRaisesRegex(ValueError, "protected QA"):
            sanitize_json_row({"answer": encoded, "context": {}})

    def test_public_attribution_and_bounded_decoding(self):
        row = {"context": {"source": "https://example.org/public-dataset", "name": "Public museum"}}
        self.assertEqual(sanitize_json_row(row)["context"], row["context"])
        self.assertFalse(encoded_business_value("not-base64!" * 4))
        oversized = base64.b64encode(gzip.compress(b"x" * 100000)).decode()
        self.assertTrue(encoded_business_value(oversized))


if __name__ == "__main__":
    unittest.main()
