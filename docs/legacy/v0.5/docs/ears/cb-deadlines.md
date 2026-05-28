# /sq-deadlines — EARS Specifications

## Unit 1: Deadline display

| ID | EARS statement |
|----|----------------|
| R-1.1 | WHEN the user invokes `/sq-deadlines`, THE SYSTEM SHALL execute `python3 deadline_scanner.py --vault <vault_path> --pretty` and render its output grouped by urgency level |
| R-1.2 | WHEN `$ARGUMENTS` contains `--level <levels>`, THE SYSTEM SHALL pass `--level <levels>` to `deadline_scanner.py` and display only the matching urgency buckets |
| R-1.3 | WHEN `deadline_scanner.py` returns zero items across all displayed levels, THE SYSTEM SHALL display "No deadlines found" and stop |
| R-1.4 | WHEN `deadline_scanner.py` exits with a non-zero code, THE SYSTEM SHALL surface the error message and exit without displaying a deadline report |
| R-1.5 | THE SYSTEM SHALL NOT write to any vault file or state file during a `/sq-deadlines` invocation |
| R-1.6 | WHERE `deadline_scanner.py` cannot be located, THE SYSTEM SHALL display an installation error and exit |
