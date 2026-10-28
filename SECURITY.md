# Security policy

## Reporting a vulnerability

If GitHub private vulnerability reporting is enabled for this repository, use it to report security issues. Otherwise, contact the repository maintainer through GitHub and request a private reporting channel. Do not include live API keys, SIP passwords, caller data, recordings, public-server IP addresses copied from logs, or a working exploit in a public issue.

## Secret handling

Keep provider keys, OAuth secrets, webhook signing secrets, database files, the Fernet key, bootstrap credentials, transcripts, recordings, and deployment logs outside the repository. Revoke and rotate a credential if it was committed or shared; removing it from the latest commit does not remove it from Git history.
