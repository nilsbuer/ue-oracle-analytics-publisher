<!-- generated: 2026-08-27 -->
# Universal Extension — ue-oracle-analytics-publisher v1.0.0

## Purpose

Authenticates to Oracle Analytics Publisher via HTTP Basic Auth, submits a report job using the SOAP `scheduleReport` operation, and polls `getScheduledReportStatus` until a terminal state is reached or the maximum wait time is exceeded.

---

## Execution Modes / Actions

| Mode | Trigger | Description |
|------|---------|-------------|
| Schedule and Monitor Report (fresh) | `action = "Schedule and Monitor Report"` and `scheduled_job_id` is empty | Validates inputs → builds SOAP job request → calls `scheduleReport` → captures Job ID → polls status until success or failure terminal state |
| Schedule and Monitor Report (re-run) | `action = "Schedule and Monitor Report"` and `scheduled_job_id` has a preserved value | Skips submission; resumes polling from the preserved Job ID captured in a prior run |

---

## Complete Field Table

| # | Name | Label | Type | Mapping | Required | Default | Choices / Notes |
|---|------|-------|------|---------|----------|---------|-----------------|
| 0 | `action` | Action | Choice | Choice Field 1 | No | `Schedule and Monitor Report` | `Schedule and Monitor Report` |
| 1 | `oracle_credential` | Oracle Credential | Credential | Credential Field 1 | **Yes** | — | Maps `user` → Oracle username, `password` → Oracle password for HTTP Basic Auth and SOAP body |
| 2 | `schedule_service_url` | Schedule Service URL | Text | Text Field 1 | **Yes** | — | Full SOAP endpoint URL for Oracle v2/ScheduleService; must begin with `http://` or `https://` |
| 3 | `verify_tls` | Verify TLS | Boolean | Boolean Field 1 | No | `true` | Controls TLS certificate validation; uses certifi CA bundle when true; must stay true in production |
| 4 | `connection_timeout_seconds` | Connection Timeout (s) | Integer | Integer Field 1 | No | `30` | TCP/TLS connection-phase timeout per SOAP request; min 1 |
| 5 | `request_timeout_seconds` | Request Timeout (s) | Integer | Integer Field 2 | No | `60` | Read/response timeout per SOAP request after connection; min 1 |
| 6 | `report_absolute_path` | Report Absolute Path | Text | Text Field 2 | **Yes** | — | Absolute Oracle Publisher catalog path; must end with `.xdo` |
| 7 | `report_parameters` | Report Parameters | Text | Large Text Field 1 | No | `{}` | Report parameters as a JSON object; each key maps to an Oracle `ParamNameValue` element; empty array values are rejected |
| 8 | `output_format` | Output Format | Choice | Choice Field 2 | No | _(empty)_ | `pdf`, `html`, `rtf`, `excel`, `excel2000`, `xlsx`, `ppt`, `pptx`, `mhtml`, `pdfa`, `pdfx`, `pdfz`, `xslfo`, `xml`, `csv`, `text`, `flash`; empty = Oracle template default |
| 9 | `report_template` | Report Template | Text | Text Field 3 | No | — | Oracle Publisher report template name within the report definition |
| 10 | `report_locale` | Report Locale | Text | Text Field 4 | No | — | Standard locale for report output (e.g., `en-US`) |
| 11 | `ui_locale` | UI Locale | Text | Text Field 5 | No | — | Standard locale for Oracle Publisher UI during processing (e.g., `en-US`) |
| 12 | `report_timezone` | Report Timezone | Text | Text Field 6 | No | — | Java-supported time zone for report output (e.g., `America/New_York`) |
| 13 | `bypass_cache` | Bypass Cache | Boolean | Boolean Field 2 | No | `false` | When true, Oracle bypasses cached report data and executes a fresh data query |
| 14 | `job_name` | Job Name | Text | Text Field 7 | No | _(auto)_ | Oracle Publisher scheduled job name; auto-generated as `UAC-<report-basename>-<timestamp>` when empty |
| 15 | `job_description` | Job Description | Text | Text Field 8 | No | `Submitted by Stonebranch UAC` | Oracle Publisher scheduled job description |
| 16 | `save_data` | Save Data | Boolean | Boolean Field 3 | No | `false` | Controls whether Oracle saves the report data extract alongside the output |
| 17 | `save_output` | Save Output | Boolean | Boolean Field 4 | No | `false` | Controls whether Oracle saves the report output document in the Publisher repository |
| 18 | `bursting` | Bursting | Boolean | Boolean Field 5 | No | `false` | Controls whether Oracle applies report bursting (split and distribute to multiple recipients) |
| 19 | `public_schedule` | Public Schedule | Boolean | Boolean Field 6 | No | `false` | Controls whether the Oracle scheduled job is visible to all Publisher users |
| 20 | `job_locale` | Job Locale | Text | Text Field 9 | No | — | Locale for the Oracle scheduled job; required when parameter values are not in English (e.g., `fr-FR`) |
| 21 | `job_timezone` | Job Timezone | Text | Text Field 10 | No | — | Java-supported time zone for the Oracle scheduled job execution context (e.g., `America/New_York`) |
| 22 | `poll_interval_seconds` | Poll Interval (s) | Integer | Integer Field 3 | No | `10` | Delay between consecutive `getScheduledReportStatus` SOAP calls; min 1 |
| 23 | `maximum_wait_seconds` | Maximum Wait (s) | Integer | Integer Field 4 | No | `3600` | Maximum elapsed polling time; task fails when exceeded without terminal state; must be >= `poll_interval_seconds` |
| 24 | `unknown_status_retry_count` | Unknown Status Retry Count | Integer | Integer Field 5 | No | `3` | Consecutive unrecognized Oracle job status values allowed before task fails; min 0 |
| 25 | `scheduled_job_id` | Scheduled Job ID | Text (Output Only) | Text Field 11 | No | — | Oracle scheduled Job ID returned by `scheduleReport`; `extensionStatus: true`; `preserveOutputOnRerun: true`; non-empty preserved value triggers re-run behavior |
| 26 | `final_status` | Final Status | Text (Output Only) | Text Field 12 | No | — | Raw `jobStatus` string from Oracle at terminal state; `defaultListView: true`; `preserveOutputOnRerun: true` |
| 27 | `status_message` | Status Message | Text (Output Only) | Text Field 13 | No | — | Oracle `JobStatus.message` at terminal state; `preserveOutputOnRerun: true` |
| 28 | `elapsed_seconds` | Elapsed Seconds | Text (Output Only) | Text Field 14 | No | — | Seconds from Job ID capture to terminal status or failure; `preserveOutputOnRerun: true` |
| 29 | `report_path` | Report Path | Text (Output Only) | Text Field 15 | No | — | Echoed `report_absolute_path` input value; `preserveOutputOnRerun: true` |

---

## Cross-References

### Always Required
- `oracle_credential` — must supply both `user` (Oracle username) and `password`
- `schedule_service_url` — must be a non-empty URL beginning with `http://` or `https://`
- `report_absolute_path` — must be a non-empty string ending in `.xdo`

### Conditionally Required / Runtime Constraints
- `maximum_wait_seconds` must be >= `poll_interval_seconds`; validated at runtime before the polling loop begins
- `connection_timeout_seconds` and `request_timeout_seconds` must each be >= 1
- `poll_interval_seconds` must be >= 1
- `unknown_status_retry_count` must be >= 0

### Re-run / State Carry-over
- `scheduled_job_id` is preserved across re-runs (`preserveOutputOnRerun: true`); when non-empty, the SOAP submission step is entirely skipped and polling resumes from the preserved Job ID
- `final_status`, `status_message`, `elapsed_seconds`, and `report_path` are all preserved across re-runs for inspection after completion

### Visibility / Auto-computed
- `job_name`: auto-generated as `UAC-<report-basename>-<timestamp>` when left empty; user value takes precedence
- `job_description`: defaults to `"Submitted by Stonebranch UAC"` when left empty; user value takes precedence
- `output_format`: optional (`choiceAllowEmpty: true`); when empty, Oracle Publisher applies the report template's default format

### Mutually Exclusive Options
- `report_locale` controls output language/formatting; `ui_locale` controls Oracle Publisher's UI locale during processing — these are independent and may differ
- `report_timezone` controls report output timezone; `job_timezone` controls the Oracle scheduled job execution context timezone — both can be set independently

---

## Error Handling Table

| Scope | Error | Handling |
|-------|-------|----------|
| Input validation (pre-flight) | `DataValidationError` / `InputValidationError` | Exit code 20; all field violations are collected before a single exception is raised; non-retryable — user must correct configuration |
| Input validation (pre-flight) | `DataValidationError` on `report_parameters` | JSON must be a valid object `{}`; array values per parameter must be non-empty; all violations collected |
| Authentication | `OracleAuthenticationError` (HTTP 401) | Exit code 1; Oracle rejected credentials; non-retryable without correcting credential configuration |
| Authorization | `OracleAuthorizationError` (HTTP 403) | Exit code 1; authenticated user lacks permissions; non-retryable without Oracle role/catalog permission fix |
| Endpoint not found | `OracleEndpointNotFoundError` (HTTP 404) | Exit code 1; `schedule_service_url` does not point to a valid ScheduleService endpoint; verify URL for the target environment |
| Network / connection | `OracleConnectionError` (pre-transmission) | Exit code 1; DNS failure, connection refused, network unreachable; request was never sent so no duplicate job risk; non-retryable until network issue is resolved |
| Ambiguous submission | `AmbiguousSubmissionError` (timeout/reset during `scheduleReport`) | Exit code 1; request body may have already reached Oracle; no auto-retry to prevent duplicate jobs; operator must check Oracle Publisher manually before re-running |
| Polling transient failure | `OracleTransientError` (HTTP 408/429/5xx or read timeout during polling) | Exit code 1; retries are exhausted (retry count controlled by `UE_POLL_RETRY_COUNT` env var, default 3); overall elapsed timer is not reset between retries |
| SOAP fault — submission | `OracleSoapFaultError` | Exit code 1; `scheduleReport` response contained a SOAP Fault element (invalid report path, unsupported format/template, Oracle server error); includes `faultcode` and `faultstring` |
| SOAP fault — polling | `OracleSoapFaultStatusError` | Exit code 1; `getScheduledReportStatus` response contained a SOAP Fault; not retried regardless of fault type; includes Job ID and `faultstring` |
| Missing Job ID | `MissingJobIdError` | Exit code 1; valid 2xx response from `scheduleReport` but `scheduleReportReturn` element is absent or empty; cannot proceed without a Job ID |
| XML parse error | `OracleParseError` | Exit code 1; malformed XML in any SOAP response (submission or polling); includes context identifying which operation returned the unparseable response |
| Oracle job failed | `PublisherJobFailedError` | Exit code 1; Oracle returned a failure terminal status (`failed`, `error`, `canceled`, `cancelled`, `output has error`, `delivery has error`, `update status has error`, `deleted`, `skipped`, `suspended`); includes Job ID, raw status, and Oracle message |
| Poll timeout | `PollTimeoutError` | Exit code 1; `maximum_wait_seconds` exceeded without Oracle returning a terminal status; includes Job ID and last known status; increase `maximum_wait_seconds` or investigate in Oracle Publisher |
| Unknown status threshold | `UnknownStatusThresholdError` | Exit code 1; consecutive unrecognized Oracle status values exceeded `unknown_status_retry_count`; counter resets when a recognized status is returned; includes raw status, Job ID, and consecutive count |
| Inconsistent Job ID | `InconsistentJobIdError` | Exit code 1; `jobID` in a `getScheduledReportStatus` response differs from the submitted/preserved Job ID; unexpected Oracle response integrity issue; includes both expected and returned Job IDs |
| Unexpected system error | `UnexpectedSystemError` | Exit code 1; unhandled Python exception caught by the top-level handler; error message includes exception type and message |
