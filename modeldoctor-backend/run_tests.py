from tests.test_engine import test_data_leakage_scaling_before_split, test_missing_validation
from tests.test_scoring import test_scoring_realistic_cap

print("Testing Engine...")
test_data_leakage_scaling_before_split()
test_missing_validation()
print("Testing Scoring...")
test_scoring_realistic_cap()
print("All tests passed!")
