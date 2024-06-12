#!/bin/bash

LINE_LENGTH=120
SEP="----------"

echo "$SEP pylint $SEP"
pylint --max-line-length=$LINE_LENGTH --disable W1203 chatbot/
echo -e "$SEP end pylint $SEP\n"

echo "$SEP pycodestyle $SEP"
pycodestyle --max-line-length=$LINE_LENGTH chatbot/
echo -e "$SEP end pycodestyle $SEP\n"

echo "$SEP pydocstyle $SEP"
pydocstyle chatbot/
echo -e "$SEP end pydocstyle $SEP\n"
