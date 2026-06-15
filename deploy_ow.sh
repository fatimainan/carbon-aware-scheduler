#!/bin/bash
CODE=$(base64 -w0 functions/data_processor.py)
curl -s -X PUT \
  "http://localhost:3233/api/v1/namespaces/guest/actions/data_processor?overwrite=true" \
  -u "23bc46b1-71f6-4ed5-8c54-816aa4f8c502:123zO3xZCLrMN6v2BKK1dXYFpXlPkccOFqm12CdAsMgRU4VrNZ9lyGVCGuMDGIwP" \
  -H "Content-Type: application/json" \
  -d "{\"namespace\":\"guest\",\"name\":\"data_processor\",\"exec\":{\"kind\":\"python:3.11\",\"code\":\"$CODE\"}}" \
  | python3 -c "import sys,json; r=json.load(sys.stdin); print('✅ Deploy OK:', r.get('name')) if 'name' in r else print('❌ Hata:', r)"
