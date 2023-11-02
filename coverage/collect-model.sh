#!/bin/sh
./collect.py ../results/clean_html/$1 &&
./collect.py ../results/iban/$1 &&
./collect.py ../results/saml/$1
