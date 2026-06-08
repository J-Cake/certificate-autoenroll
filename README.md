# Certificate Autoenroll

CA-Autoenroll is a utility that lets system administrators issue machine-local certificates via SSH. It is designed to act as an issuing certificate authority where machines present certificates via SSH and automatically receive a refreshed certificate.

# Usage

The script operates in two modes: 

1. Manual mode - The administrator logs in to the CA via standard SSH flows. The credential flow is currrently hard-coded into the script. Alter if needed. The script autopopulates an SSH command to enable this. The server is executed, returning a valid certificate
2. Automatic mode - The SSH server is configured to trust certificates it has issued. If the client attempts to log in by presenting its certificate, the SSH server will use information encoded in previously issued certificates to invoke the `server.py` script as the `machine-enroll` user, thereby issuing a certificate.

# Security

The security of this system rests on the assumtion that the SSH server is a privileged operation. Users who can connect to the server via SSH can issue themselves a certificate. Depending on the power of such a certificate, this can be a highly sensitive operation.

# Setup

Manual mode requires little setup apart from copying the files to a directory accessible to the system. Presently, the /usr/local/src/renew-ca/ directory is used. Ensure the `server.py` script is executable by *both* the `machine-enroll` user as well as any administrative users you indend to grant access. This may require [ACLs](https://www.redhat.com/en/blog/linux-access-control-lists).

Automatic mode requires the creation of the `machine-enroll` user and its owning group. Typically, the `/usr/local/src/renew-ca/` directory is owned by `machine-enroll:machine-enroll` with execute permissions on both the user and its group. 

Additionally, the SSH server must be configured to spawn the server upon login to this user. This is achieved by copying the [`./ca.conf`](./ca.conf) file to `/etc/ssh/sshd_config.d/` and refreshing the SSH Server's config. (`systemctl reload ssh`). 

Finally, a key is required; The script is hard-coded to assume the `/etc/ssl/machine-enroll/` directory as the directory in which private keys and configuration files are stored. This directory should be treated with utmost care, similarly to the source directory above. 

Two keys are required; OpenSSL for x.509 certificates and an SSH key for future SSH authentication (refresh et al).

```
openssl ecparam -name prime256v1 -genkey  -noout -out /etc/ssl/machine-enroll/authority.key
ssh-keygen -t ed25519 -f /etc/ssl/machine-enroll/ssh-ca.key
```

Once setup is complete, **verify SSH authentication is rock solid before proceeding!**

Finally, the [`./client.sh`](./client.sh) file can be rolled out to clients. This can similarly be achieved by any means desirable including the now functional SSH channel. 

Typically, this file is made executable under `/usr/local/bin/refresh-cert` and should run such that certificates are kept up-to-date. By default certificates expire after 128 days. Configure the `server.py` file to adjust this. See the two unit file for example units. 
