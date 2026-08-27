# Universal Extension Requirements (Refined)

**Extension Name:** Oracle Analytics Publisher Asynchronous Report Scheduler
**Original Generated:** Not explicitly dated (see References)
**Refined:** 2026-08-27
**Agent_id:** 1
**Requirements Completeness:** High Detail
**Target Platform:** Linux

---

# Table of Contents

1. [Overview](#overview)
2. [Actions](#actions)
   - 2.1 [Action 1: Schedule and Monitor Report](#action-1-schedule-and-monitor-report)
3. [Input Requirements](#input-requirements)
   - 3.1 [Connection Parameters](#connection-parameters)
   - 3.2 [Report Parameters](#report-parameters)
   - 3.3 [Schedule Request Parameters](#schedule-request-parameters)
   - 3.4 [Polling Parameters](#polling-parameters)
4. [Output Requirements](#output-requirements)
   - 4.1 [On Success](#on-success)
   - 4.2 [On Error](#on-error)
5. [Authentication Requirements](#authentication-requirements)
6. [Environment Variables](#environment-variables)
7. [Operational Behavior](#operational-behavior)
8. [Implementation Notes](#implementation-notes)
   - 8.1 [Python Compatibility](#python-compatibility)
   - 8.2 [Target Platform](#target-platform)
   - 8.3 [Third-Party Services and Tools](#third-party-services-and-tools)
   - 8.4 [Error Handling](#error-handling)
   - 8.5 [Resource Cleanup](#resource-cleanup)
9. [Requirements Summary](#requirements-summary)
10. [Document Change History](#document-change-history)
11. [References](#references)

---

# Overview

This document defines the functional requirements for a Stonebranch Universal Automation Center (UAC) Universal Extension that submits and monitors Oracle Analytics Publisher (BI Publisher) reports in an Oracle Fusion Applications environment via the Oracle SOAP `v2/ScheduleService` API.

**Integration Purpose:** The extension authenticates to Oracle Analytics Publisher, asynchronously submits a report job via `scheduleReport`, captures the returned Oracle scheduled Job ID, and polls `getScheduledReportStatus` until Oracle reports a terminal state (success or failure) or the configured polling timeout is reached. Report output retrieval is out of scope for this version.

---

# Actions

## Action 1: Schedule and Monitor Report

**Functional Requirements:**

1. The extension must validate all input fields before making any Oracle API calls.
2. The extension must authenticate to the Oracle `v2/ScheduleService` SOAP endpoint using HTTP Basic Authentication.
3. The extension must submit the report by calling `scheduleReport` with the configured report path, parameters, output options, and schedule options.
4. The extension must pass the Oracle username and password both as HTTP Basic Authentication credentials and within the SOAP operation body (`userID` and `password` elements) for the stateless `v2` public service contract.
5. The extension must parse the `scheduleReportReturn` value from the SOAP response and store it as the Oracle scheduled Job ID.
6. The extension must fail before entering the polling loop if the submission does not produce a valid, non-empty Job ID.
7. The extension must poll `getScheduledReportStatus` using the obtained Job ID at the configured poll interval until a terminal state is reached or the maximum wait time is exceeded.
8. The extension must normalize Oracle job status values (trim whitespace, case-fold to lowercase, collapse repeated internal whitespace) before determining task state.
9. The extension must classify Oracle job statuses as: successful terminal, in-progress, failure terminal, or unknown.
10. The extension must stop polling and report UAC task success when a successful terminal state is returned.
11. The extension must stop polling and report UAC task failure when a failure terminal state is returned.
12. The extension must implement bounded retries for consecutive unknown status values before failing.
13. The extension must fail with a timeout error including the Job ID and last known status when the maximum wait time is exceeded without reaching a terminal state.
14. The extension must not retry `scheduleReport` automatically after an ambiguous transport failure to avoid creating duplicate Publisher jobs.
15. The extension must expose the Scheduled Job ID, Final Status, Status Message, Elapsed Seconds, and Report Path as output fields.
16. The extension must print a formatted summary table to STDOUT upon task completion (success or failure).

---

# Input Requirements

## Connection Parameters

- **Schedule Service URL** (Text, Required): Full SOAP endpoint URL for the Oracle `v2/ScheduleService`. The same extension must support different Fusion environments (DEV, TEST, PROD) by changing this field alone.
  - Example: `https://host.fa.ocs.oraclecloud.com/xmlpserver/services/v2/ScheduleService`
  - Applicability: Action 1
  - Default Value: None

- **Username** (Credential/User, Required): Oracle Fusion / Publisher username used for both HTTP Basic Authentication and the SOAP `userID` parameter.
  - Example: `oracle_user`
  - Applicability: Action 1
  - Default Value: None

- **Password** (Credential/Password, Required): Oracle Fusion / Publisher password. Must be treated as a secret at all times and must never appear in logs, STDOUT, STDERR, debug output, or any UAC output field.
  - Applicability: Action 1
  - Default Value: None

- **Verify TLS Certificate** (Boolean, Optional): Controls TLS certificate validation for HTTPS connections. Must be enabled by default. Production environments must retain certificate verification.
  - Applicability: Action 1
  - Default Value: `true`

- **Connection Timeout Seconds** (Integer, Optional): TCP/TLS connection timeout in seconds.
  - Applicability: Action 1
  - Default Value: `30`

- **Request Timeout Seconds** (Integer, Optional): Timeout for a single SOAP HTTP request in seconds.
  - Applicability: Action 1
  - Default Value: `60`

## Report Parameters

- **Report Absolute Path** (Text, Required): Absolute Oracle Publisher catalog path. Must end in `.xdo`. Must not be URL-encoded inside the SOAP XML.
  - Example: `/Custom/Financials/My Report.xdo`
  - Applicability: Action 1
  - Default Value: None

- **Report Parameters** (Large Text, Optional): Report parameters supplied as a JSON object. Each JSON property maps to one Oracle `ParamNameValue`. Scalar values produce a single `<v2:item>` under `<v2:values>`; JSON arrays produce multiple `<v2:item>` elements. A missing property means that parameter is not submitted. A JSON `null` value omits that parameter. An empty string `""` submits an empty string value. An empty array `[]` is rejected as invalid input. Must be valid JSON and must be a JSON object (not array or scalar).
  - Example (single-value): `{"P_LEDGER_ID": "300000001", "P_FROM_DATE": "2026-08-01"}`
  - Example (multi-value): `{"P_LEDGER_ID": [300000001, 300000002]}`
  - Applicability: Action 1
  - Default Value: `{}`

- **Output Format** (Choice, Optional): Maps to `ReportRequest.attributeFormat`. If left empty, Oracle Publisher/report defaults are used. Oracle remains the authority on format validity for a specific report template; unsupported combinations surface as SOAP faults.
  - Available options: `pdf`, `html`, `rtf`, `excel`, `excel2000`, `xlsx`, `ppt`, `pptx`, `mhtml`, `pdfa`, `pdfx`, `pdfz`, `xslfo`, `xml`, `csv`, `text`, `flash`
  - Default presented option: empty (use report default)
  - Field type: Static choice dropdown with `choiceAllowEmpty: true`
  - Applicability: Action 1
  - Default Value: empty

- **Template** (Text, Optional): Maps to `ReportRequest.attributeTemplate`. Publisher report template name.
  - Applicability: Action 1
  - Default Value: empty

- **Report Locale** (Text, Optional): Maps to `ReportRequest.attributeLocale`. Standard locale identifier.
  - Example: `en-US`
  - Applicability: Action 1
  - Default Value: empty

- **UI Locale** (Text, Optional): Maps to `ReportRequest.attributeUILocale`. Standard locale identifier.
  - Applicability: Action 1
  - Default Value: empty

- **Report Time Zone** (Text, Optional): Maps to `ReportRequest.attributeTimeZone`. Must be a Java-supported time zone ID when supplied.
  - Example: `America/New_York`
  - Applicability: Action 1
  - Default Value: empty

- **Bypass Cache** (Boolean, Optional): Maps to `ReportRequest.byPassCache`.
  - Applicability: Action 1
  - Default Value: `false`

## Schedule Request Parameters

- **Job Name** (Text, Optional): Maps to `ScheduleRequest.userJobName`. When omitted, a meaningful value must be generated automatically. The generated job name must be included in error messages when submission outcome is unknown.
  - Applicability: Action 1
  - Default Value: Generated (e.g., `UAC-<report-name>-<timestamp>`)

- **Job Description** (Text, Optional): Maps to `ScheduleRequest.userJobDesc`.
  - Applicability: Action 1
  - Default Value: Generated or empty (e.g., `Submitted by Stonebranch UAC`)

- **Save Data** (Boolean, Optional): Maps to `ScheduleRequest.saveDataOption`.
  - Applicability: Action 1
  - Default Value: `false`

- **Save Output** (Boolean, Optional): Maps to `ScheduleRequest.saveOutputOption`.
  - Applicability: Action 1
  - Default Value: `false`

- **Bursting** (Boolean, Optional): Maps to `ScheduleRequest.scheduleBurstingOption`.
  - Applicability: Action 1
  - Default Value: `false`

- **Public Schedule** (Boolean, Optional): Maps to `ScheduleRequest.schedulePublicOption`.
  - Applicability: Action 1
  - Default Value: `false`

- **Job Locale** (Text, Optional): Maps to `ScheduleRequest.jobLocale`. Oracle notes this is required when submitted parameter values are not in English.
  - Applicability: Action 1
  - Default Value: empty

- **Job Time Zone** (Text, Optional): Maps to `ScheduleRequest.jobTZ`.
  - Applicability: Action 1
  - Default Value: empty

## Polling Parameters

- **Poll Interval Seconds** (Integer, Optional): Delay between consecutive `getScheduledReportStatus` requests. Minimum value: 1.
  - Applicability: Action 1
  - Default Value: `10`

- **Maximum Wait Seconds** (Integer, Optional): Maximum elapsed polling time measured from successful submission response. The monotonic clock starts after the Job ID is successfully captured.
  - Applicability: Action 1
  - Default Value: `3600`

- **Unknown Status Retry Count** (Integer, Optional): Number of consecutive unknown or unrecognized Oracle status values allowed before the task fails. The counter resets if a recognized status is subsequently returned.
  - Applicability: Action 1
  - Default Value: `3`

---

# Output Requirements

## On Success

**Return code:** 0

**Status description:** `Oracle Publisher job <Job ID> completed successfully in <N>s`

**Output-only fields:**

| Field | Type | Description |
|---|---|---|
| Scheduled Job ID | String | Job ID returned by `scheduleReport`. Must be preserved across re-runs (`preserveOutputOnRerun: true`). |
| Final Status | String | Raw final `JobStatus.jobStatus` value returned by Oracle at the terminal state. |
| Status Message | String | Oracle `JobStatus.message` value when present. |
| Elapsed Seconds | Numeric | Time in seconds from successful submission response until terminal status is reached. |
| Report Path | String | Submitted Oracle Publisher catalog path. |

**STDOUT output:**

1. Progressive log lines during execution (see Operational Behavior — Progress Reporting).
2. A formatted summary table at task completion using `tabulate` with `rounded_outline` style, containing all five output fields as rows.

Example summary table (success):
```
╭──────────────────────┬────────────────────────────────────────────╮
│ Scheduled Job ID     │ 123456                                     │
│ Report Path          │ /Custom/Financials/UAC Test Report.xdo     │
│ Final Status         │ Success                                    │
│ Status Message       │ Completed successfully                     │
│ Elapsed Seconds      │ 42                                         │
╰──────────────────────┴────────────────────────────────────────────╯
```

**Success Criteria:**

1. HTTP transport completes with a 2xx response code for the `scheduleReport` request.
2. The SOAP response contains no Fault element.
3. The SOAP response is valid XML.
4. A non-empty Job ID is parsed from `scheduleReportReturn`.
5. Oracle returns a recognized successful terminal status (`success`, `completed`, or `done`) during polling.

## On Error

**Failure Scenarios:**

**1. Input Validation Failure**
- Description: One or more input fields fail pre-flight validation before any Oracle call is made.
- Root causes: Empty required field, invalid URL scheme, non-JSON or non-object Report Parameters, Poll Interval < 1, Maximum Wait Seconds < Poll Interval, non-positive timeout values, negative Unknown Status Retry Count.
- Return code: Non-zero
- Status description pattern: Descriptive validation message per violated rule (e.g., `Schedule Service URL must not be empty`, `Report Parameters must be a valid JSON object`)

**2. Authentication Failure**
- Description: Oracle returns HTTP 401 for the SOAP request.
- Root causes: Invalid username or password.
- Return code: Non-zero
- Status description pattern: `Oracle Publisher authentication failed (HTTP 401) for <URL>`

**3. Authorization Failure**
- Description: Oracle returns HTTP 403 for the SOAP request.
- Root causes: User exists but lacks permission for the report or the Publisher web service.
- Return code: Non-zero
- Status description pattern: `Oracle Publisher authorization failed (HTTP 403). Verify that the Fusion user can access the report and Publisher web service.`

**4. Bad Endpoint**
- Description: Oracle returns HTTP 404 for the SOAP request.
- Root causes: Incorrect `Schedule Service URL`, wrong service path.
- Return code: Non-zero
- Status description pattern: `Oracle Publisher endpoint not found (HTTP 404) at <URL>`

**5. SOAP Fault on Submission**
- Description: `scheduleReport` returns a SOAP Fault element in the response body.
- Root causes: Invalid report path, unsupported format/template combination, malformed SOAP request, server-side Oracle error.
- Return code: Non-zero
- Status description pattern: `Oracle Publisher scheduleReport returned a SOAP Fault: <faultstring>` (includes `faultcode` and `detail` when available; never includes credentials)

**6. Missing Job ID**
- Description: `scheduleReport` returns a 2xx response with no SOAP Fault, but no Job ID is parseable.
- Root causes: Unexpected Oracle response structure.
- Return code: Non-zero
- Status description pattern: `Oracle Publisher scheduleReport returned no scheduled Job ID.`

**7. Ambiguous Submission Failure**
- Description: A network or transport failure occurs after the request may have been transmitted, making the submission outcome unknown.
- Root causes: Connection loss, timeout after request may have been sent.
- Return code: Non-zero
- Status description pattern: `Oracle Publisher scheduleReport outcome unknown due to transport error. Check Publisher job history for job named '<job name>'.` (No automatic retry is performed.)

**8. SOAP Fault During Polling**
- Description: `getScheduledReportStatus` returns a non-transient SOAP Fault.
- Root causes: Invalid credentials for status call, invalid Job ID, Oracle server-side error.
- Return code: Non-zero
- Status description pattern: `Oracle Publisher getScheduledReportStatus returned a SOAP Fault for job <Job ID>: <faultstring>`

**9. Publisher Job Failure Terminal State**
- Description: Oracle returns a recognized failure terminal status for the submitted job.
- Root causes: Report execution error, delivery failure, job canceled or suspended in Oracle.
- Return code: Non-zero
- Status description pattern: `Oracle Publisher job <Job ID> ended with status '<status>': <Oracle message>`
- Failure terminal statuses: `failed`, `error`, `canceled`, `cancelled`, `output has error`, `delivery has error`, `update status has error`, `deleted`, `skipped`, `suspended`

**10. Poll Timeout**
- Description: No terminal state is reached before `Maximum Wait Seconds` elapses.
- Root causes: Long-running report, insufficient timeout configuration, Oracle job stuck in-progress.
- Return code: Non-zero
- Status description pattern: `Timed out after <N> seconds waiting for Oracle Publisher job <Job ID>. Last status: '<status>'.`

**11. Unknown Status Threshold Exceeded**
- Description: Oracle returns an unrecognized status value for more than `Unknown Status Retry Count` consecutive polls.
- Root causes: New Oracle status vocabulary not covered by the extension, unexpected Oracle response.
- Return code: Non-zero
- Status description pattern: `Oracle Publisher returned an unrecognized status '<raw status>' for job <Job ID> for <N> consecutive polls.`

**12. Inconsistent Job ID in Response**
- Description: Oracle's `JobStatus` response contains a `jobID` value that differs from the submitted Job ID.
- Root causes: Oracle response error, misdirected response.
- Return code: Non-zero
- Status description pattern: `Oracle Publisher returned Job ID '<returned ID>' in status response but submitted Job ID was '<submitted ID>'.`

**Input Validation Rules:**

- `Schedule Service URL` must not be empty and must use an `http://` or `https://` scheme.
- `Username` must not be empty.
- `Password` must not be empty.
- `Report Absolute Path` must not be empty. A warning or failure must be produced if the path does not end in `.xdo`.
- `Report Parameters` must be valid JSON and must be a JSON object (not an array or scalar). An empty array `[]` value for any parameter must be rejected.
- `Poll Interval Seconds` must be at least 1.
- `Maximum Wait Seconds` must be greater than or equal to `Poll Interval Seconds`.
- `Connection Timeout Seconds` and `Request Timeout Seconds` must be positive integers.
- `Unknown Status Retry Count` must not be negative.

**STDERR:** Transport and parsing error details may be written to STDERR for diagnostic purposes. Credentials must never appear in STDERR output.

---

# Authentication Requirements

The extension supports **HTTP Basic Authentication over HTTPS** as the transport authentication mechanism.

The same Oracle credential (username and password) is used for two distinct purposes simultaneously:
1. As the HTTP `Authorization: Basic <base64(username:password)>` header, configured through the HTTP client's built-in Basic Auth support (not manually constructed).
2. As the `userID` and `password` SOAP body elements in both `scheduleReport` and `getScheduledReportStatus` operations, as required by the Oracle Fusion public `v2` service contract.

If the Oracle Fusion environment rejects Basic Authentication (e.g., HTTP 401), the task must fail immediately with a clear authentication error. The task must not silently retry using a different authentication mechanism.

OAuth authentication is out of scope for this version. The authentication logic must be isolated sufficiently to allow OAuth mode to be added in a future version without redesigning the report submission or status polling logic.

---

# Environment Variables

- **`UE_POLL_RETRY_COUNT`** (Integer, default: `3`): Controls the maximum number of transient transport retry attempts for each `getScheduledReportStatus` poll request. This is distinct from `Unknown Status Retry Count`, which governs consecutive unrecognized Oracle status values. This environment variable is intended for operators in environments with known intermittent connectivity issues.

---

# Operational Behavior

**Dynamic Choice Fields:**
The `Output Format` field is a static choice dropdown populated with Oracle's 17 documented `attributeFormat` values. It allows an empty selection to defer to the report default. No dynamic population from Oracle is required.

**Cancel Action:**
When the UAC task process is terminated or cancelled, the extension does not call Oracle's `cancelSchedule` operation. Any already-submitted Oracle Publisher job will continue running in Oracle independently. This behavior must be documented. A future version may implement UAC cancellation via Oracle's `cancelSchedule` operation.

**Re-run Capability:**
The `Scheduled Job ID` output field must be configured with `preserveOutputOnRerun: true` and `fieldRestriction: Output Only`. On task re-run, if a preserved `Scheduled Job ID` value is detected from a previous execution, the extension must skip `scheduleReport` and go directly to polling `getScheduledReportStatus` with the preserved Job ID. A log message must indicate this behavior (e.g., `Re-run detected: polling existing Publisher job 123456`). If no preserved Job ID is present, the extension must submit a fresh report.

**Progress Reporting:**
The extension must log the following events to STDOUT during execution:
- Target ScheduleService host/path and report absolute path at startup.
- Generated or configured job name and number of report parameters (not parameter values).
- Successful submission confirmation including the Oracle scheduled Job ID.
- Status transitions (logged only when the status changes from the previous poll).
- Final terminal status and elapsed time.
- All errors with operator-friendly messages.

Example log sequence:
```
Submitting Oracle Publisher report /Custom/Financials/Example.xdo
Oracle Publisher scheduled Job ID: 123456
Job 123456 status changed: Scheduled -> Running
Job 123456 status changed: Running -> Success
Oracle Publisher job 123456 completed successfully in 42s
```

At task completion (success or failure), a formatted summary table must be appended to STDOUT using `tabulate` with `rounded_outline` style, containing the five output fields as rows.

**Dynamic Commands:**
None.

---

# Implementation Notes

## Python Compatibility

Targeting compatibility for Python 3.11.

## Target Platform

Linux only (x86_64 / manylinux_2_17_x86_64). C extension modules with a confirmed `manylinux_2_17_x86_64` wheel are viable in addition to pure-Python modules.

**Confirmed Python dependencies:**

| Module | Purpose | Version | Type |
|---|---|---|---|
| `requests` | HTTP client for SOAP POST — Session management, Basic Auth, TLS verification, configurable timeouts | 2.34.2 | Pure Python |
| Python stdlib `xml.etree.ElementTree` | Namespace-aware XML request building and SOAP response parsing | Built-in (Python ≥ 3.11) | Pure Python |
| `certifi` | Mozilla CA certificate bundle for TLS verification of Oracle Fusion Cloud endpoints | 2026.7.22 | Pure Python |
| `tabulate` | STDOUT summary table formatting with `rounded_outline` style | 0.10.0 | Pure Python |

## Third-Party Services and Tools

**Oracle Analytics Publisher `v2/ScheduleService` SOAP API**
- Description: Oracle's web service for scheduling, monitoring, and managing BI Publisher report jobs within Oracle Fusion Applications.
- Version constraints: Targets the public `v2/ScheduleService` endpoint. The WSDL from the target Fusion pod is the definitive source for element names, namespaces, element ordering, SOAP binding, and SOAPAction.
- Integration approach: SOAP 1.1 over HTTPS. Two operations used: `scheduleReport` (submit) and `getScheduledReportStatus` (poll). SOAP namespace: `http://xmlns.oracle.com/oxp/service/v2`. Content-Type: `text/xml; charset=utf-8`.

## Error Handling

**Error categories:**
1. **Input validation errors** — Caught before any Oracle call; fail immediately with descriptive messages.
2. **Transport errors** — HTTP connectivity and timeout failures; categorized as immediate failures (401, 403, 404) or transient candidates (408, 429, 5xx).
3. **SOAP fault errors** — Detected in the XML response body regardless of HTTP status code; always surface `faultcode`, `faultstring`, and `detail`; never include credentials.
4. **Parse errors** — Malformed XML or missing required response elements; fail immediately with a clear error.
5. **Oracle status-based failures** — Terminal non-success statuses returned during polling; fail immediately.
6. **Polling timeout** — Maximum wait elapsed without terminal state; fail with Job ID and last status.
7. **Unknown status threshold** — Consecutive unrecognized status values exceeding the configured count; fail with raw status and Job ID.

**Error handling strategy:**
- Submission failures (except ambiguous transport failures) and non-transient errors always cause immediate task failure.
- Transient transport errors during polling are retried up to `UE_POLL_RETRY_COUNT` times with short backoff before failing.
- The overall `Maximum Wait Seconds` timer is not reset by poll transport retries.
- Ambiguous submission failures (possible duplicate-submission risk) fail immediately without retry and include the generated job name in the error to allow manual investigation.
- A `200 OK` HTTP response must still be inspected for SOAP Fault elements before treating it as a successful response.
- All SOAP XML must be parsed using a namespace-aware XML library; regular-expression-based parsing is prohibited.
- Password and Authorization header values must never appear in any error output.

## Resource Cleanup

- The extension holds an HTTP session (`requests.Session`) for the duration of one task execution; no persistent connections are maintained beyond task completion.
- If the UAC task process is terminated externally, the HTTP session is abandoned. Any Oracle Publisher job that was already submitted continues running in Oracle and is not automatically cancelled.
- No temporary files are created by the extension.

---

# Requirements Summary

The Oracle Analytics Publisher Asynchronous Report Scheduler Universal Extension must:

1. Accept a configurable `v2/ScheduleService` URL, credential, report path, JSON parameters, output options, schedule options, and polling settings through UAC input fields.
2. Validate all inputs before making any Oracle API call, failing with operator-friendly messages for each violation.
3. Authenticate using HTTP Basic Authentication and include the same credential in the SOAP operation body as required by the Oracle `v2` public service contract.
4. Submit the report by calling `scheduleReport` exactly once per task execution (or zero times if re-running with a preserved Job ID).
5. Capture the Oracle scheduled Job ID and expose it as a preserved output field.
6. Poll `getScheduledReportStatus` at the configured interval, normalizing status values (lowercase, whitespace-trimmed) before classification.
7. Classify Oracle statuses as: successful terminal (`success`, `completed`, `done`), in-progress (`scheduled`, `waiting`, `running`, `cancelling`), failure terminal (`failed`, `error`, `canceled`, `cancelled`, `output has error`, `delivery has error`, `update status has error`, `deleted`, `skipped`, `suspended`), or unknown.
8. Succeed when a successful terminal status is reached; fail when a failure terminal status or the polling timeout is reached.
9. Implement bounded retries for unknown statuses (controlled by `Unknown Status Retry Count`) and for transient transport failures during polling (controlled by `UE_POLL_RETRY_COUNT` environment variable).
10. Never retry `scheduleReport` automatically after an ambiguous transport failure.
11. On re-run, poll the preserved Job ID from a prior successful submission instead of submitting a new job.
12. Expose five output fields: Scheduled Job ID, Final Status, Status Message, Elapsed Seconds, and Report Path.
13. Log status transitions and completion; append a formatted `tabulate` summary table to STDOUT at task completion.
14. Never log, output, or include the password or Authorization header in any log, STDOUT, STDERR, error message, or UAC output field.
15. Build all SOAP XML using an XML library with proper escaping; parse SOAP responses using a namespace-aware XML parser without relying on specific namespace prefixes.
16. Support unit tests with mocked SOAP responses covering all major success, failure, status, and edge-case scenarios.

---

# Document Change History

- **2026-08-27 (original):** Initial requirements document generated. Completeness level: High Detail. Covered SOAP service contract, full input field set, authentication architecture, status normalization, retry semantics, XML parsing, output fields, logging, validation, acceptance criteria, and unit/integration test requirements.
- **2026-08-27 (refined):** Comprehensive refinement based on 7 clarification questions and user feedback. Changes: (1) HTTP client confirmed as `requests` 2.34.2; (2) XML library confirmed as Python stdlib `xml.etree.ElementTree`; (3) `Output Format` field type resolved from `Text/Choice` to static choice dropdown with `choiceAllowEmpty: true` and 17 Oracle-documented format codes; (4) `Report Parameters` field type resolved from `Large Text / JSON` to Large Text field; (5) Re-run behavior defined: poll preserved Job ID when available, skip `scheduleReport`; (6) STDOUT output defined as progressive log lines plus final `tabulate` summary table in `rounded_outline` style; (7) Poll transport retry count defined as `UE_POLL_RETRY_COUNT` environment variable (default: 3). Platform confirmed as Linux-only (x86_64 / manylinux_2_17_x86_64).

---

# References

- **Original Requirements Document:** `memory/requirements.md`
- **Original Requirements Q&A Document:** `memory/agents-memory/requirements-QnA.md`
- Oracle Analytics Publisher Developer's Guide — Publisher ScheduleService: https://docs.oracle.com/en/cloud/paas/analytics-cloud/acspd/publisher-scheduleservice.html
- `scheduleReport()` Method: https://docs.oracle.com/en/cloud/paas/analytics-cloud/acspd/to_schedulereport_method.html
- `getScheduledReportStatus()` Method: https://docs.oracle.com/en/cloud/paas/analytics-cloud/acspd/to_getscheduledreportstatus_method.html
- Oracle ScheduleService SOAP — Oracle Analytics Community: https://community.oracle.com/products/oracleanalytics/discussion/20518/scheduleservice-soap
