"""Optional supervised risk research pipeline. Requires real labelled data; not used for safety-critical route weights."""
import argparse,csv,pathlib,json
p=argparse.ArgumentParser();p.add_argument('--csv',required=True);p.add_argument('--output',default='models/risk.joblib');a=p.parse_args()
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import classification_report
import joblib
rows=list(csv.DictReader(open(a.csv)));features=['hazard_count','high_severity_count','disaster_count','distance_km'];required=set(features+['risk_label','road_group'])
if not rows or not required.issubset(rows[0]):raise SystemExit('CSV requires '+','.join(sorted(required)))
if len(rows)<100:raise SystemExit('Need at least 100 independently labelled observations. Do not invent training rows.')
x=[[float(r[k]) for k in features] for r in rows];y=[r['risk_label'] for r in rows];groups=[r['road_group'] for r in rows]
train,test=next(GroupShuffleSplit(n_splits=1,test_size=.25,random_state=42).split(x,y,groups));model=HistGradientBoostingClassifier(random_state=42);model.fit([x[i] for i in train],[y[i] for i in train]);prediction=model.predict([x[i] for i in test]);metrics=classification_report([y[i] for i in test],prediction,output_dict=True,zero_division=0)
pathlib.Path(a.output).parent.mkdir(parents=True,exist_ok=True);joblib.dump({'model':model,'features':features},a.output);pathlib.Path(a.output+'.metrics.json').write_text(json.dumps(metrics,indent=2));print(json.dumps(metrics,indent=2));print('Research artifact only: not automatically used to score navigation routes.')
