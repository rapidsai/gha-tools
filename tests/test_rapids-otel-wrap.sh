#!/bin/bash
#

SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
out=$(${SCRIPT_DIR}/../tools/rapids-otel-wrap echo "abc")
if [ "$out" != "abc" ]; then
    echo "error on simple echo case"; exit 1;
fi

out=$(${SCRIPT_DIR}/../tools/rapids-otel-wrap echo "arg with a space")
if [ "$out" != "arg with a space" ]; then
    echo "error on space case"; exit 1;
fi

out=$(${SCRIPT_DIR}/../tools/rapids-otel-wrap echo "cmd" "arg with a space" --somearg '"blah blah"')
if [ "$out" != 'cmd arg with a space --somearg "blah blah"' ]; then
    echo "error on harder space case"; exit 1;
fi

out=$(${SCRIPT_DIR}/../tools/rapids-otel-wrap cat <<EOF
arg" with a space --somearg 'a<b'
EOF
);
if [ "$out" != "arg\" with a space --somearg 'a<b'" ]; then
    echo "error on inequality case as heredoc";
    echo "output was:"
    echo "$out"
    exit 1;
fi

out=$(${SCRIPT_DIR}/../tools/rapids-otel-wrap echo "a<b");
if [ "$out" != "a<b" ]; then
    echo "error on inequality case as arg";
    echo "output was:"
    echo "$out"
    exit 1;
fi
