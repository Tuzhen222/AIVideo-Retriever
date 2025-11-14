#!/bin/bash

# Test ensemble with multimodal + IC
echo "=== Testing Ensemble: Multimodal + IC ==="
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "cheese",
    "method": "ensemble",
    "top_k": 20,
    "mode": "E",
    "queries": [
      {
        "query": "cheese",
        "toggles": {
          "multimodal": true,
          "ic": true,
          "asr": false,
          "ocr": false,
          "objectFilter": false
        },
        "selectedObjects": []
      }
    ],
    "filters": {
      "objectFilter": false,
      "selectedObjects": []
    }
  }' | jq '.total, .method'

echo ""
echo "=== Testing Ensemble: Multimodal + IC + OCR ==="
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "cheese",
    "method": "ensemble",
    "top_k": 20,
    "mode": "A",
    "queries": [
      {
        "query": "cheese",
        "toggles": {
          "multimodal": true,
          "ic": true,
          "asr": false,
          "ocr": true,
          "objectFilter": false
        },
        "selectedObjects": []
      }
    ],
    "filters": {
      "objectFilter": false,
      "selectedObjects": []
    }
  }' | jq '.total, .per_method_results | keys'

echo ""
echo "Check backend logs for [ENSEMBLE] messages"
