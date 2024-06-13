#!/bin/bash

LINE_LENGTH=120
SEP="----------"

echo "$SEP pycodestyle $SEP"
pycodestyle --max-line-length=$LINE_LENGTH chatbot/
if [[ $? -ne 0 ]]; then
    exit
fi
echo -e "$SEP end pycodestyle $SEP\n"

echo "$SEP pylint $SEP"
pylint --max-line-length=$LINE_LENGTH --disable W1203,R0902 chatbot/
echo -e "$SEP end pylint $SEP\n"
