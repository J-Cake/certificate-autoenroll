#!/bin/env bash

HOSTNAME=$(hostname -f)
CA=valentin.synovo.lan
KEY="/etc/ssl/private/$HOSTNAME.key"
CONF="/etc/ssl/private/$HOSTNAME.conf"
CRT="/etc/ssl/private/$HOSTNAME.crt"

if [ ! -f $KEY ]; then
    printf "Generating new key file\n"

    openssl ecparam -name prime256v1 -genkey -noout -out $KEY
fi

CSR=$(mktemp)
openssl req -new -key $KEY -subj "/C=DE/ST=Baden-Württemberg/O=Synovo GmbH/CN=$HOSTNAME" -addext "subjectAltName=DNS:$HOSTNAME" -out $CSR

printf "Wrote CSR to $CSR\n"

SSH_KEY="/etc/ssl/private/$CA.key"
SSH_CERT="/etc/ssl/private/$CA.crt"
if [ ! -f $SSH_KEY ]; then
    cp $KEY $SSH_KEY
    ssh-keygen -p -f $SSH_KEY -N ""
fi

if [[ -f $SSH_CERT ]] && [[ " $* " =~ " --auto " ]] && [[ -s "$SSH_CERT" ]]; then
    cat > /etc/ssh/machine-enroll.conf << EOF
Host $CA
    IdentityFile $SSH_KEY
    CertificateFile $SSH_CERT
EOF
    TMP_X509=$(mktemp)
    TMP_SSH=$(mktemp)

    cat $CSR | ssh -F /etc/ssh/machine-enroll.conf machine-enroll@$CA | tee >(jq -r '.x509' > $TMP_X509) >(jq -r '.ssh' > $TMP_SSH) >/dev/null

    mv $TMP_X509 $CRT
    mv $TMP_SSH $SSH_CERT
else
    printf "No or bad CA certificate present. You need to manually acquire a certificate.\nUsername: "

    TMP_X509=$(mktemp)
    TMP_SSH=$(mktemp)

    read USERNAME
    cat $CSR | ssh $USERNAME@$CA /usr/local/src/renew-ca/server.py | tee >(jq -r '.x509' > $TMP_X509) >(jq -r '.ssh' > $TMP_SSH) >/dev/null

    mv $TMP_X509 $CRT
    mv $TMP_SSH $SSH_CERT
fi
