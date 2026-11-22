# Security Policy

## Supported Versions

Only the latest release of the current major version is supported with security updates and bug fixes.

| Version | Supported |
| ------- | -------- |
| Latest version of current major `2.x.y`| :white_check_mark: |
| Older versions of current major `2.x.y-1` | :x: |
| Previous major versions `1.x.y` | :x: |
| Beta versions `n.x.y-beta-z` | :warning: Testing only |

Beta releases are intended for testing, evaluation and feedback. They may contain bugs, incomplete features or security issues. Use beta versions at your own risk. They are not intended for production environments.

## Reporting a Vulnerability

If you discover a security vulnerability in this integration, please report it through GitHub's private vulnerability reporting feature, if available, or contact the maintainer directly through GitHub.

**Do not disclose security vulnerabilities publicly before the maintainer has had a reasonable opportunity to investigate.**

When reporting a vulnerability, include:

- A description of the vulnerability.
- Steps to reproduce the issue.
- The potential impact.
- Relevant logs or screenshots, with sensitive information removed (ip, hostname, credentials, disk labels etc)

### Response and remediation

- Reports will be reviewed as soon as reasonably possible.
- The maintainer will assess the severity, impact and scope of the vulnerability.
- Accepted vulnerabilities affecting this repository will be addressed in this repository, where possible.
- Fixes may be released as a patch or as part of a new release, depending on the severity and scope.

## Dependencies and third-party components

This integration relies on Home Assistant and may rely on other third-party libraries and components.

The maintainer is responsible for addressing security issues within this repository. Security issues in Home Assistant, Python libraries or other upstream dependencies are outside the direct control of this project.

Upstream issues may be reported to their respective maintainers. Depending on the circumstances, the integration may implement a workaround, mitigation or compatibility change. However, upstream fixes are not guaranteed to be implemented or maintained by this project.

## Scope and limitations

Security fixes are provided on a best-effort basis and are limited to the supported version described above.

Users are responsible for keeping Home Assistant, the integration and its dependencies up to date, and for securing their own network and SNMP configuration.

The maintainer does not guarantee that the integration is free from security vulnerabilities.
