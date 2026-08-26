# Security Policy

## Scope

This is a research/engineering framework for optimizing LLM program behavior, not a security
product — but two categories of issue matter here:

- **Compiler/scanner vulnerabilities**: e.g. a crafted trainset example or config that causes
  code execution, path traversal, or a crash/DoS while compiling.
- **Silent-pass bugs in Contracts**: a contract that reports "satisfied" when it shouldn't
  (e.g. due to a missing-data case defaulting to True instead of False) is a correctness bug
  with safety implications, since Contracts gate what a user might deploy. Treat these as
  higher priority than typical bugs.

## Reporting

Please don't open a public issue for a vulnerability. Use GitHub's private vulnerability
reporting for this repository, or email the maintainer directly (see README for contact).

Include a description, reproduction steps or a minimal example, and your assessment of impact.

## What to expect

Acknowledgement within a few days, and coordinated disclosure before any public writeup.
