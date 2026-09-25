from services.parser import parse_code
from services.pipeline_analyzer import analyze_pipeline
from services.engine import DetectionEngine
from services.rules.data_leakage import DataLeakageRule
from services.rules.overfitting import OverfittingRule
from services.rules.best_practices import BestPracticesRule

def test_data_leakage_scaling_before_split():
    engine = DetectionEngine()
    engine.register_rule(DataLeakageRule())
    engine.register_rule(OverfittingRule())
    engine.register_rule(BestPracticesRule())

    code = """
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression

df = pd.read_csv('data.csv')
X = df.drop('target', axis=1)
y = df['target']

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X) # LEAKAGE

X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2)
clf = LogisticRegression()
clf.fit(X_train, y_train)
    """
    parsed = parse_code(code)
    evidence = analyze_pipeline(parsed)
    issues = engine.run_all(parsed, evidence)
    
    dl_issues = [i for i in issues if i.id == "DL-001"]
    print(f"Evidence stages: {evidence.stages}")
    print(f"All issues: {issues}")
    assert len(dl_issues) == 1
    assert dl_issues[0].severity == "CRITICAL"

def test_missing_validation():
    engine = DetectionEngine()
    engine.register_rule(DataLeakageRule())
    engine.register_rule(OverfittingRule())
    engine.register_rule(BestPracticesRule())

    code = """
from sklearn.ensemble import RandomForestClassifier
X, y = load_data()
clf = RandomForestClassifier()
clf.fit(X, y)
    """
    parsed = parse_code(code)
    evidence = analyze_pipeline(parsed)
    issues = engine.run_all(parsed, evidence)
    
    of_issues = [i for i in issues if i.id == "OF-001"]
    assert len(of_issues) == 1
    assert of_issues[0].severity == "HIGH"
