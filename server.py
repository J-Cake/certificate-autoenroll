#!/usr/bin/env python3

import json
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.x509 import CertificateSigningRequest
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

# 1. This CA is accessed via SSH. Passing the SSH server means you are authorised to request a certificate.
# 2. You pass a certificate signing request via STDIN
# 3. The CA checks whether it's valid, including a MAC to Hostname lookup
# 4. If so, it signs it using an authorised certificate and writes it back via STDOUT
# 5. The client then places the result adjacent to the certificate's key in its store.


VALIDITY_DAYS = 128
AUTH_CERT = "/etc/ssl/machine-enroll/authority.crt"
AUTH_KEY = "/etc/ssl/machine-enroll/authority.key"
SSH_CA_KEY = "/etc/ssl/machine-enroll/ssh-ca.key"
SSH_PRINCIPAL = "machine-enroll"


def validate(csr: CertificateSigningRequest) -> bool:
    if not csr.is_signature_valid:
        return False

    cn = csr.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value

    print(cn, file=sys.stderr)

    return True  # Stub for now


if __name__ != "__main__":
    print("This script must be called directly via SSH.", file=sys.stderr)
    sys.exit(1)

csr_pem = sys.stdin.buffer.read()
csr = x509.load_pem_x509_csr(csr_pem)
cn = csr.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value

if not validate(csr):
    print("Validation failed.", file=sys.stderr)
    sys.exit(1)

ca_cert = x509.load_pem_x509_certificate(Path(AUTH_CERT).read_bytes())
ca_key = serialization.load_pem_private_key(Path(AUTH_KEY).read_bytes(), None)


def sign_x509():
    return (
        (
            x509.CertificateBuilder()
            .subject_name(csr.subject)
            .issuer_name(ca_cert.subject)
            .public_key(csr.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.now(timezone.utc))
            .not_valid_after(datetime.now(timezone.utc) + timedelta(days=VALIDITY_DAYS))
            .add_extension(
                x509.BasicConstraints(ca=False, path_length=None), critical=True
            )
            .add_extension(
                x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH]), critical=False
            )
            .add_extension(
                x509.SubjectAlternativeName([x509.DNSName(cn)]), critical=False
            )
            .sign(ca_key, hashes.SHA256())
        )
        .public_bytes(serialization.Encoding.PEM)
        .decode()
    )


def sign_ssh():
    pubkey_pem = csr.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    ssh_pubkey = subprocess.run(
        ["ssh-keygen", "-f", "/dev/stdin", "-i", "-m", "PKCS8"],
        input=pubkey_pem,
        capture_output=True,
        check=True,
    ).stdout

    with tempfile.TemporaryDirectory() as tmp:
        pub_path = Path(tmp) / "key.pub"
        cert_path = Path(tmp) / "key-cert.pub"
        pub_path.write_bytes(ssh_pubkey)

        subprocess.run(
            [
                "ssh-keygen",
                "-s",
                SSH_CA_KEY,
                "-I",
                cn,
                "-n",
                SSH_PRINCIPAL,
                "-V",
                f"+{VALIDITY_DAYS}d",
                str(pub_path),
            ],
            check=True,
            capture_output=True,
        )

        return cert_path.read_text()


json.dump({"x509": sign_x509(), "ssh": sign_ssh()}, sys.stdout)
