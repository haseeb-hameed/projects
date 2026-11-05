import hashlib,pathlib,sys
p=pathlib.Path(__file__).resolve().parents[1]/'models/pothole.pt'
expected='af2ac6ce7bfec72e71643659ac946caf80ced84869e526a60135c457abfbb200'
if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=expected:sys.exit('Model missing or checksum differs. Do not load an untrusted replacement.')
print('Bundled model SHA256 verified. This is provenance checking, not accuracy validation.')
