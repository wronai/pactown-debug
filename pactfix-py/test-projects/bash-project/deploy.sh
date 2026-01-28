#!/bin/bash
# Sample Bash script with intentional issues for pactfix testing

OUTPUT_DIR=/tmp/output
# pactfix: Dodano klamerki do zmiennych (was: LOG_FILE=$OUTPUT_DIR/deploy.log)
LOG_FILE=${OUTPUT_DIR}/deploy.log

# Missing error handling for cd (SC2164)
# pactfix: Dodano obsługę błędów dla cd (was: cd /var/www/html)
cd /var/www/html || exit 1

# Variables without braces
# pactfix: Dodano klamerki do zmiennych (was: echo "Deploying to $OUTPUT_DIR")
echo "Deploying to ${OUTPUT_DIR}"
# pactfix: Dodano klamerki do zmiennych (was: echo "Log file: $LOG_FILE")
echo "Log file: ${LOG_FILE}"

# Read without -r (SC2162)
read USER_INPUT
# pactfix: Dodano klamerki do zmiennych (was: echo "You entered: $USER_INPUT")
echo "You entered: ${USER_INPUT}"

# Misplaced quotes
# pactfix: Poprawiono cudzysłowy (was: NAME="deploy"script)
NAME="deployscript"

# More unbraced variables
for HOST in server1 server2; do
    # pactfix: Dodano klamerki do zmiennych (was: ssh user@$HOST "systemctl restart app")
    ssh user@${HOST} "systemctl restart app"
    # pactfix: Dodano klamerki do zmiennych (was: echo "Deployed to $HOST")
    echo "Deployed to ${HOST}"
done

echo "Deployment complete"
