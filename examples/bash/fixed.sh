#!/usr/bin/bash
OUTPUT=/home/student/output-

for HOST in server{a,b}; do
    if test -f ${OUTPUT}${HOST}; then
        rm -v ${OUTPUT}${HOST}
    fi
    echo "$(ssh student@${HOST} hostname -f)" >> ${OUTPUT}${HOST}  # ✅ NAPRAWIONO: Poprawiono pozycję cudzysłowu
    echo "#####"
    ssh student@${HOST} lscpu | grep "^CPU" >> ${OUTPUT}${HOST}
done

cd /some/directory
read NAME
echo "Hello $NAME"
