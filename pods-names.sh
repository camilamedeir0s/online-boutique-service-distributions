#!/bin/bash

# Obtendo os nomes dos pods na namespace default
pod_names=$(kubectl get pods -n default -o custom-columns=":metadata.name" --no-headers)

# Contando a quantidade de pods
pod_count=$(echo "$pod_names" | wc -w)
echo "Quantidade de pods na namespace 'default': $pod_count"

# Iterando sobre os nomes dos pods
for pod in $pod_names; do
    echo "Pod encontrado: $pod"
    export POD_NAME=$pod
    envsubst < http-failure-template.yaml | kubectl apply -f -
done
