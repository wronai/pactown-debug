#!/bin/bash
# Sample Bash script with intentional issues for pactfix testing

OUTPUT_DIR=/tmp/output
LOG_FILE=$OUTPUT_DIR/deploy.log

cd /var/www/html

echo "Deploying to $OUTPUT_DIR"
echo "Log file: $LOG_FILE"

# Misplaced quotes
NAME="deploy"script

echo "Name: $NAME"
