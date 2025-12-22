#!/bin/bash

# Run submission worker in background
WORKER_TYPE=submission python ./entry_point.py &
SUBMISSION_PID=$!

# Run grading worker in background
WORKER_TYPE=grading python ./entry_point.py &
GRADING_PID=$!

echo "Submission worker PID: $SUBMISSION_PID"
echo "Grading worker PID: $GRADING_PID"

# Wait for both
wait $SUBMISSION_PID $GRADING_PID