#!/bin/bash
API_URL="http://localhost:8000"
API_KEY="123e4567-e89b-12d3-a456-426614174000"

echo "Creating job..."
RESPONSE=$(curl -s -X POST "$API_URL/api/v1/jobs" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "content_type": "video",
    "prompt": "A beautiful sunset",
    "model_name": "moneyprinter-turbo",
    "parameters": {"duration": 5}
  }')

echo "Response: $RESPONSE"
JOB_ID=$(echo $RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo "Job ID: $JOB_ID"

if [ "$JOB_ID" == "None" ] || [ -z "$JOB_ID" ]; then
  echo "Failed to create job"
  exit 1
fi

echo "Monitoring job..."
for i in {1..60}; do
  STATUS_RES=$(curl -s -H "X-API-Key: $API_KEY" "$API_URL/api/v1/jobs/$JOB_ID")
  STATUS=$(echo $STATUS_RES | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])")
  PROGRESS=$(echo $STATUS_RES | python3 -c "import sys, json; print(json.load(sys.stdin).get('progress', 0))")
  
  echo "Attempt $i: Status=$STATUS, Progress=$PROGRESS%"
  
  if [ "$STATUS" == "completed" ]; then
    echo "Video generation completed!"
    RESULT_URL=$(echo $STATUS_RES | python3 -c "import sys, json; print(json.load(sys.stdin)['result_url'])")
    echo "Result URL: $RESULT_URL"
    exit 0
  fi
  
  if [ "$STATUS" == "failed" ]; then
    echo "Video generation failed!"
    ERROR=$(echo $STATUS_RES | python3 -c "import sys, json; print(json.load(sys.stdin)['error_message'])")
    echo "Error: $ERROR"
    exit 1
  fi
  
  sleep 5
done

echo "Timeout"
exit 1
