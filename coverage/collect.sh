#!/bin/sh
./collect.py ../results/clean_html/base &&
./collect.py ../results/iban/base &&
./collect.py ../results/saml/base &&
./collect.py ../results/clean_html/base_corp &&
./collect.py ../results/iban/base_corp &&
./collect.py ../results/saml/base_corp &&

./collect.py ../results/clean_html/codegen-16B-multi/pt &&
./collect.py ../results/iban/codegen-16B-multi/pt &&
./collect.py ../results/saml/codegen-16B-multi/pt
