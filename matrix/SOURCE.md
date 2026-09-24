# Matrix synchronization

These matrix files are a synchronized copy of:

```text
Repository: HM-Abdellah/school-discord-manager
Branch: main
Commit: 0f14d5f31474b3008ea2e698d52358065eda9111
```

The E2E repository keeps a local copy so the operator can run the observer independently from the application checkout.

## Synchronization rule

When the School Manager command surface or E2E contract changes:

1. update the application repository first;
2. identify the exact application commit;
3. copy the five matrix JSON files from `school-discord-manager/e2e/matrix/`;
4. update the commit reference in `e2e/command_catalog.py` and this file;
5. run the offline test suite on Python 3.12 and 3.13;
6. only then start live E2E.

Do not silently modify matrix expectations in the observer repository to make a failing live test pass.
