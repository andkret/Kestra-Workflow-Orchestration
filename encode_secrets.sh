#!/bin/bash

input="$(pwd)/.env"
output="$(pwd)/.env_encoded"

> "$output"

while IFS='=' read -r key value; do
    [[ -z "$key" || "$key" =~ ^# ]] && continue

    clean_value=$(printf "%s" "$value" | tr -d '\r')
    encoded=$(printf "%s" "$clean_value" | base64)

    printf "SECRET_%s=%s\n" "$key" "$encoded" >> "$output"
done < "$input"
