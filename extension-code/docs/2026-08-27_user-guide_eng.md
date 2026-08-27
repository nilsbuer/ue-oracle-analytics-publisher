> **Version:** ue-oracle-analytics-publisher v1.0.0
> **Date:** 2026-08-27

# Oracle Analytics Publisher — Universal Extension User Guide

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Task Actions](#task-actions)
4. [Task Configuration](#task-configuration)
   - [Action](#action)
   - [Authentication](#authentication)
   - [Connection](#connection)
   - [Report Configuration](#report-configuration)
   - [Job Settings](#job-settings)
   - [Polling and Monitoring](#polling-and-monitoring)
   - [Output Fields](#output-fields)
5. [Example Walkthrough](#example-walkthrough)
   - [Scenario 1: Generate a Sales Summary PDF Report](#scenario-1-generate-a-sales-summary-pdf-report)
   - [Scenario 2: Generate a Parameterized Financial Report with Bursting](#scenario-2-generate-a-parameterized-financial-report-with-bursting)
6. [Troubleshooting](#troubleshooting)
7. [Full Field Reference](#full-field-reference)

---

## Overview

The **Oracle Analytics Publisher** Universal Extension authenticates to an Oracle Analytics Publisher instance using HTTP Basic Auth, submits a scheduled report job via the SOAP `scheduleReport` operation, and continuously polls `getScheduledReportStatus` until the job reaches a terminal state or the configured maximum wait time is exceeded.

On task re-run, if a Job ID from a prior execution is preserved in the `scheduled_job_id` output field, the submission step is skipped and polling resumes from the preserved Job ID — preventing duplicate report submissions.

---

## Prerequisites

- A Stonebranch UAC environment with the `ue-oracle-analytics-publisher` extension installed and registered.
- A running Oracle Analytics Publisher instance accessible over HTTP or HTTPS from the UAC agent host.
- An Oracle Publisher user account with sufficient privileges to schedule reports and read job status via the SOAP API.
- The full catalog path of the target report (must end with `.xdo`), obtainable from the Oracle Publisher catalog browser.
- The full SOAP endpoint URL for the Oracle ScheduleService (e.g., `https://obi.example.com/xmlpserver/services/v2/ScheduleService`).
- A UAC Credential record containing the Oracle username and password.

---

## Task Actions

### Schedule and Monitor Report

This is the only available action. It covers two execution paths:

| Path | Trigger | Behavior |
|------|---------|----------|
| **Fresh submission** | `action = "Schedule and Monitor Report"` and `scheduled_job_id` output field is empty | Validates inputs → builds SOAP job request → calls `scheduleReport` → captures the Oracle Job ID → polls `getScheduledReportStatus` in a loop until the job reaches a successful or failure terminal state |
| **Re-run (resume polling)** | `action = "Schedule and Monitor Report"` and `scheduled_job_id` contains a preserved Job ID from a prior run | Skips the SOAP submission step entirely → resumes polling using the preserved Job ID |

#### Execution Flow (Fresh Submission)

1. Input validation runs first — all field errors are collected before execution stops.
2. The SOAP `scheduleReport` request is built and sent to the configured endpoint.
3. Oracle returns a Job ID, which is immediately written to the `scheduled_job_id` output field.
4. The polling loop starts, calling `getScheduledReportStatus` every `poll_interval_seconds`.
5. Status transitions are logged to standard output as they occur.
6. The task completes successfully when Oracle reports a successful terminal status (e.g., `success`).
7. On completion, `final_status`, `status_message`, `elapsed_seconds`, and `report_path` are populated.

#### Re-run Behavior

When UAC re-executes the task and `scheduled_job_id` is non-empty, the extension detects the preserved Job ID and skips SOAP submission. This prevents submitting a duplicate report job. Polling resumes immediately using the preserved ID. All output fields are preserved across re-runs.

#### Completion and Status Checks

The task exit code is `0` on success and `1` on any error. The `final_status` output field contains the raw Oracle job status string at the terminal state. The `status_message` field contains any additional message Oracle returned. The `elapsed_seconds` field reports the total polling duration.

---

## Task Configuration

### Action

| Field | Description | Default | Required |
|-------|-------------|---------|----------|
| Action | The operation to perform. Currently only `Schedule and Monitor Report` is available. | `Schedule and Monitor Report` | No |

---

### Authentication

| Field | Description | Required |
|-------|-------------|----------|
| **Oracle Credential** | A UAC Credential record supplying the Oracle username (mapped to `user`) and password (mapped to `password`) used for HTTP Basic Auth on all SOAP requests. | **Yes** |

Both `user` and `password` within the credential must be non-empty.

---

### Connection

| Field | Description | Default | Required |
|-------|-------------|---------|----------|
| **Schedule Service URL** | Full SOAP endpoint URL for the Oracle Analytics Publisher v2 ScheduleService. Must begin with `http://` or `https://`. Example: `https://obi.example.com/xmlpserver/services/v2/ScheduleService` | — | **Yes** |
| Verify TLS | Controls TLS certificate validation. Uses the certifi CA bundle when enabled. Disable only in non-production environments with self-signed certificates. | `true` | No |
| Connection Timeout (s) | TCP/TLS connection-phase timeout in seconds for each SOAP request. Minimum value: 1. | `30` | No |
| Request Timeout (s) | Read/response timeout in seconds per SOAP request after the connection is established. Minimum value: 1. | `60` | No |

---

### Report Configuration

| Field | Description | Default | Required |
|-------|-------------|---------|----------|
| **Report Absolute Path** | Absolute Oracle Publisher catalog path to the report definition. Must end with `.xdo`. Example: `/Custom/Finance/SalesSummary.xdo` | — | **Yes** |
| Report Parameters | Report runtime parameters as a JSON object. Each key maps to an Oracle `ParamNameValue` element. Array values must be non-empty. Leave empty or omit for parameter-free reports. Example: `{"region": "EMEA", "year": "2025"}` | `{}` | No |
| Output Format | Desired report output format. When empty, Oracle uses the template's default format. | _(empty)_ | No |
| Report Template | Oracle Publisher report template name within the report definition. Leave empty to use the default template. | — | No |
| Report Locale | Locale for report output content (e.g., `en-US`, `fr-FR`). Controls number/date formatting in the output document. | — | No |
| UI Locale | Oracle Publisher UI locale during report processing (e.g., `en-US`). Independent of `report_locale`. | — | No |
| Report Timezone | Java-compatible time zone for report output (e.g., `America/New_York`, `Europe/Berlin`). | — | No |

**Supported output formats:** `pdf`, `html`, `rtf`, `excel`, `excel2000`, `xlsx`, `ppt`, `pptx`, `mhtml`, `pdfa`, `pdfx`, `pdfz`, `xslfo`, `xml`, `csv`, `text`, `flash`

---

### Job Settings

| Field | Description | Default | Required |
|-------|-------------|---------|----------|
| Job Name | Oracle Publisher scheduled job name. Auto-generated as `UAC-<report-basename>-<timestamp>` when left empty. | _(auto)_ | No |
| Job Description | Oracle Publisher scheduled job description visible in the Publisher console. | `Submitted by Stonebranch UAC` | No |
| Save Data | When enabled, Oracle saves the report data extract alongside the rendered output in the Publisher repository. | `false` | No |
| Save Output | When enabled, Oracle saves the rendered report output document in the Publisher repository. | `false` | No |
| Bursting | When enabled, Oracle applies report bursting — splitting and distributing the report to multiple recipients according to the bursting definition. | `false` | No |
| Public Schedule | When enabled, the Oracle scheduled job is visible to all Publisher users, not just the submitting user. | `false` | No |
| Job Locale | Locale for the Oracle scheduled job context. Required when report parameter values are not in English (e.g., `fr-FR`). | — | No |
| Job Timezone | Java-compatible time zone for the Oracle scheduled job execution context (e.g., `America/Chicago`). Independent of `report_timezone`. | — | No |

---

### Polling and Monitoring

| Field | Description | Default | Required |
|-------|-------------|---------|----------|
| Poll Interval (s) | Delay in seconds between consecutive `getScheduledReportStatus` SOAP calls. Minimum value: 1. | `10` | No |
| Maximum Wait (s) | Maximum elapsed polling time in seconds. The task fails with `PollTimeoutError` if this limit is reached without a terminal status. Must be ≥ `poll_interval_seconds`. | `3600` | No |
| Unknown Status Retry Count | Number of consecutive unrecognized Oracle job status values allowed before the task fails. The counter resets when a recognized status is returned. Minimum value: 0. | `3` | No |

---

### Output Fields

These fields are populated by the extension at runtime and are read-only. They are preserved across task re-runs.

| Field | Description |
|-------|-------------|
| **Scheduled Job ID** | Oracle scheduled Job ID returned by `scheduleReport`. A non-empty value in this field triggers re-run behavior on the next execution. |
| **Final Status** | Raw `jobStatus` string from Oracle at the terminal state (e.g., `success`, `failed`). Shown in the default task list view. |
| **Status Message** | Oracle `JobStatus.message` at the terminal state. May contain additional detail about failures. |
| **Elapsed Seconds** | Number of seconds from Job ID capture to terminal status or failure. |
| **Report Path** | Echoes the `report_absolute_path` input value for reference in downstream tasks. |

---

## Example Walkthrough

### Scenario 1: Generate a Sales Summary PDF Report

**Goal:** Submit the regional sales summary report to Oracle Publisher and receive a PDF output.

**Prerequisites:**
- A UAC Credential named `oracle-obi-prod` with the Oracle Publisher username and password.
- The report exists at `/Custom/Sales/RegionalSummary.xdo` in the Oracle Publisher catalog.
- The Oracle Publisher ScheduleService is reachable at `https://obi.example.com/xmlpserver/services/v2/ScheduleService`.
- The UAC agent host can reach the Oracle Publisher host over HTTPS on port 443.
- The Oracle user has the `Schedule Report` privilege in Oracle Publisher.

| Field | Value | Notes |
|-------|-------|-------|
| Action | `Schedule and Monitor Report` | |
| Oracle Credential | `oracle-obi-prod` | Must contain valid Oracle username and password |
| Schedule Service URL | `https://obi.example.com/xmlpserver/services/v2/ScheduleService` | |
| Verify TLS | `true` | Keep enabled for production |
| Report Absolute Path | `/Custom/Sales/RegionalSummary.xdo` | Must end with `.xdo` |
| Output Format | `pdf` | |
| Report Parameters | `{"region": "EMEA", "fiscal_year": "2025"}` | JSON object |
| Job Description | `Sales PDF — EMEA FY2025` | Optional label in Oracle Publisher console |
| Maximum Wait (s) | `1800` | 30-minute limit; increase for large reports |
| Poll Interval (s) | `15` | |
| Connection Timeout (s) | `30` | |
| Request Timeout (s) | `60` | |

**What happens:**
- The extension validates all inputs and sends the `scheduleReport` SOAP request with the EMEA and fiscal year parameters.
- Oracle returns a Job ID (e.g., `123456`), which is written to `scheduled_job_id` immediately.
- The extension polls every 15 seconds until Oracle reports `success` or until 30 minutes elapse.
- Status transitions (e.g., `running`, `success`) are printed to the task output log.
- On success, `final_status` is set to `success` and `elapsed_seconds` shows the total polling time.
- If re-run, the existing `scheduled_job_id` is detected and submission is skipped — polling resumes directly.

---

### Scenario 2: Generate a Parameterized Financial Report with Bursting

**Goal:** Submit a financial consolidation report that must be split and distributed to regional recipients via Oracle Publisher bursting.

**Prerequisites:**
- A UAC Credential named `oracle-obi-finance` configured with a Finance Publisher service account.
- The bursting-enabled report exists at `/Enterprise/Finance/ConsolidationReport.xdo` in the Oracle catalog.
- The bursting definition is configured directly on the report in Oracle Publisher.
- `Save Output` is required so that Oracle retains the burst output documents in the repository.
- The Oracle service account has the `Schedule Report` and `Bursting` privileges.

| Field | Value | Notes |
|-------|-------|-------|
| Action | `Schedule and Monitor Report` | |
| Oracle Credential | `oracle-obi-finance` | Finance service account |
| Schedule Service URL | `https://obi-finance.example.com/xmlpserver/services/v2/ScheduleService` | Finance-specific endpoint |
| Verify TLS | `true` | |
| Report Absolute Path | `/Enterprise/Finance/ConsolidationReport.xdo` | |
| Report Parameters | `{"quarter": "Q4", "entity": ["EMEA", "APAC"]}` | Multi-value array per parameter |
| Output Format | `xlsx` | Excel output for recipient delivery |
| Bursting | `true` | Required to activate Oracle bursting logic |
| Save Output | `true` | Retain burst documents in Publisher repository |
| Public Schedule | `false` | Restrict visibility to the service account |
| Job Name | `Finance-Consolidation-Q4-2025` | Meaningful name for Oracle Publisher audit trail |
| Job Description | `Q4 2025 Consolidation — EMEA and APAC burst delivery` | |
| Report Timezone | `Europe/London` | Controls date/time in report output |
| Maximum Wait (s) | `7200` | 2-hour limit for large bursting jobs |
| Poll Interval (s) | `30` | Reduce poll frequency for long-running jobs |
| Unknown Status Retry Count | `5` | Allow for extra unknown status responses during burst processing |

**What happens:**
- The extension submits the SOAP `scheduleReport` request with the Q4 quarter and multi-entity parameters and bursting enabled.
- Oracle schedules the job and returns a Job ID which is captured in `scheduled_job_id`.
- The extension polls every 30 seconds; Oracle transitions through `running` → `success` as bursting completes.
- Burst output documents are stored in the Oracle Publisher repository (because `save_output = true`).
- On successful completion, `final_status` is `success`, `status_message` may contain delivery confirmation, and `elapsed_seconds` reflects total processing time.
- If Oracle returns an unexpected status during burst delivery (e.g., `output has error`), the task fails with `PublisherJobFailedError` and the raw status and Oracle message are included in the failure output.

---

## Troubleshooting

### Authentication Failures

**Symptom:** Task fails with `OracleAuthenticationError` (HTTP 401).

**Possible cause:** The username or password in the `oracle_credential` is incorrect, or the account is locked in Oracle Publisher.

**Resolution:** Verify the credential in the UAC Credential record. Confirm the Oracle user account is active and not locked by logging into the Oracle Publisher console directly. Update the credential if the password has changed.

---

### Permission Errors

**Symptom:** Task fails with `OracleAuthorizationError` (HTTP 403).

**Possible cause:** The authenticated Oracle user does not have the `Schedule Report` privilege, or the catalog path is in a folder the user cannot access.

**Resolution:** In Oracle Publisher, grant the user the `Schedule Report` role and verify the user has read permission on the target report's catalog folder.

---

### Endpoint Not Found

**Symptom:** Task fails with `OracleEndpointNotFoundError` (HTTP 404).

**Possible cause:** The `schedule_service_url` is incorrect — wrong hostname, port, or path.

**Resolution:** Confirm the SOAP endpoint URL by checking the Oracle Publisher server configuration. The correct path is typically `/xmlpserver/services/v2/ScheduleService`. Test the URL directly from the UAC agent host using a tool such as `curl`.

---

### Report Path Validation Error

**Symptom:** Task fails with `DataValidationError` mentioning `report_absolute_path`.

**Possible cause:** The `report_absolute_path` value does not end with `.xdo`, or the field is empty.

**Resolution:** Provide the full Oracle Publisher catalog path ending in `.xdo`. Example: `/Custom/Finance/SalesSummary.xdo`. The path can be found in the Oracle Publisher catalog browser.

---

### Network / Connection Failures

**Symptom:** Task fails with `OracleConnectionError`.

**Possible cause:** The UAC agent cannot reach the Oracle Publisher host — DNS resolution failure, firewall blocking the port, or the Oracle server is down.

**Resolution:** Confirm network connectivity from the UAC agent host to the Oracle Publisher hostname and port. Check firewall rules and proxy configuration. The SOAP request was never sent when this error occurs, so there is no risk of a duplicate job.

---

### Ambiguous Submission (Potential Duplicate Job)

**Symptom:** Task fails with `AmbiguousSubmissionError`.

**Possible cause:** A network timeout or connection reset occurred during the `scheduleReport` SOAP call — the request body may have already reached Oracle before the connection dropped.

**Resolution:** Do not automatically re-run the task without first checking Oracle Publisher manually. Log in to the Oracle Publisher console and inspect recent scheduled jobs to determine whether the report job was created. If it was created, note the Job ID and check whether to proceed or cancel it before re-running in UAC.

---

### Report Generation Failure

**Symptom:** Task fails with `PublisherJobFailedError`.

**Possible cause:** Oracle returned a terminal failure status such as `failed`, `error`, `output has error`, or `delivery has error`. The Oracle job rejected the report definition, encountered a data error, or a bursting delivery failure occurred.

**Resolution:** Check the `status_message` output field for the Oracle error message. Log into Oracle Publisher and inspect the job details for that Job ID. Common causes include an invalid report template, a missing data source connection, or a bursting configuration error.

---

### Poll Timeout

**Symptom:** Task fails with `PollTimeoutError`.

**Possible cause:** Oracle did not reach a terminal status within the configured `maximum_wait_seconds`. The report may still be running or Oracle may be unresponsive.

**Resolution:** Increase `maximum_wait_seconds` to accommodate longer-running reports. Log into Oracle Publisher and check the scheduled job status for the preserved `scheduled_job_id`. If the job completed in Oracle after the UAC timeout, re-run the UAC task — it will resume polling from the preserved Job ID.

---

### Unknown Status Threshold Exceeded

**Symptom:** Task fails with `UnknownStatusThresholdError`.

**Possible cause:** Oracle returned consecutive unrecognized status strings that exceeded the `unknown_status_retry_count` threshold. This may indicate an Oracle Publisher version mismatch or an unexpected job state.

**Resolution:** Increase `unknown_status_retry_count` temporarily to allow the job to transition past the unknown status. Check Oracle Publisher logs for the job ID to understand what state it is in. If Oracle consistently returns unrecognized statuses, contact your Oracle Administrator.

---

### SOAP Fault on Submission

**Symptom:** Task fails with `OracleSoapFaultError`.

**Possible cause:** Oracle returned a SOAP Fault in the `scheduleReport` response. Common causes: the report path does not exist in the catalog, the specified output format is not supported by the report template, or an Oracle server-side error.

**Resolution:** Verify the `report_absolute_path` exists in the Oracle Publisher catalog. Confirm the `output_format` is supported by the target report template. Check `faultcode` and `faultstring` in the task output for the specific Oracle error.

---

### SOAP Fault During Polling

**Symptom:** Task fails with `OracleSoapFaultStatusError`.

**Possible cause:** Oracle returned a SOAP Fault in a `getScheduledReportStatus` response. The polling is not retried for SOAP faults.

**Resolution:** Check the `faultstring` in the task output. Log into Oracle Publisher and inspect the job status for the preserved Job ID. This may indicate the job was deleted or Oracle encountered an internal error.

---

### Report Parameter Validation Error

**Symptom:** Task fails with `DataValidationError` mentioning `report_parameters`.

**Possible cause:** The `report_parameters` value is not valid JSON, is not a JSON object (`{}`), or contains a parameter whose value is an empty array (`[]`).

**Resolution:** Ensure `report_parameters` is a valid JSON object. Example: `{"region": "EMEA"}`. Multi-value parameters must use a non-empty array: `{"entity": ["EMEA", "APAC"]}`. Empty arrays are not accepted.

---

### TLS Certificate Error

**Symptom:** Task fails with `OracleConnectionError` with a certificate-related message.

**Possible cause:** Oracle Publisher uses a self-signed or internally signed TLS certificate that is not trusted by the certifi CA bundle used when `verify_tls = true`.

**Resolution:** For production environments, obtain a certificate signed by a publicly trusted CA or install the internal CA certificate on the UAC agent system and update the certifi bundle. As a temporary workaround in development, set `verify_tls = false` — do not use this in production.

---

## Full Field Reference

| # | Name | Label | Type | Required | Default | Description | Allowed Values |
|---|------|-------|------|----------|---------|-------------|----------------|
| 0 | `action` | Action | Choice | No | `Schedule and Monitor Report` | Operation to perform | `Schedule and Monitor Report` |
| 1 | `oracle_credential` | Oracle Credential | Credential | **Yes** | — | UAC Credential supplying Oracle username and password for HTTP Basic Auth | Valid UAC Credential with `user` and `password` |
| 2 | `schedule_service_url` | Schedule Service URL | Text | **Yes** | — | Full SOAP endpoint URL for Oracle v2/ScheduleService | Must begin with `http://` or `https://` |
| 3 | `verify_tls` | Verify TLS | Boolean | No | `true` | Enables TLS certificate validation using the certifi CA bundle | `true` / `false` |
| 4 | `connection_timeout_seconds` | Connection Timeout (s) | Integer | No | `30` | TCP/TLS connection-phase timeout per SOAP request | Integer ≥ 1 |
| 5 | `request_timeout_seconds` | Request Timeout (s) | Integer | No | `60` | Read/response timeout per SOAP request after connection | Integer ≥ 1 |
| 6 | `report_absolute_path` | Report Absolute Path | Text | **Yes** | — | Absolute Oracle Publisher catalog path to the report | Must end with `.xdo` |
| 7 | `report_parameters` | Report Parameters | Large Text | No | `{}` | Report runtime parameters as a JSON object | Valid JSON object; array values must be non-empty |
| 8 | `output_format` | Output Format | Choice | No | _(empty)_ | Desired report output format; empty = Oracle template default | `pdf`, `html`, `rtf`, `excel`, `excel2000`, `xlsx`, `ppt`, `pptx`, `mhtml`, `pdfa`, `pdfx`, `pdfz`, `xslfo`, `xml`, `csv`, `text`, `flash` |
| 9 | `report_template` | Report Template | Text | No | — | Oracle Publisher report template name within the report definition | Any string |
| 10 | `report_locale` | Report Locale | Text | No | — | Locale for report output content | Standard locale code, e.g., `en-US`, `fr-FR` |
| 11 | `ui_locale` | UI Locale | Text | No | — | Oracle Publisher UI locale during report processing | Standard locale code, e.g., `en-US` |
| 12 | `report_timezone` | Report Timezone | Text | No | — | Time zone for report output | Java-supported time zone, e.g., `America/New_York` |
| 13 | `bypass_cache` | Bypass Cache | Boolean | No | `false` | Forces Oracle to execute a fresh data query, bypassing cached report data | `true` / `false` |
| 14 | `job_name` | Job Name | Text | No | _(auto)_ | Oracle Publisher scheduled job name; auto-generated as `UAC-<basename>-<timestamp>` when empty | Any string |
| 15 | `job_description` | Job Description | Text | No | `Submitted by Stonebranch UAC` | Oracle Publisher scheduled job description | Any string |
| 16 | `save_data` | Save Data | Boolean | No | `false` | Saves the report data extract in the Oracle Publisher repository | `true` / `false` |
| 17 | `save_output` | Save Output | Boolean | No | `false` | Saves the rendered report output in the Oracle Publisher repository | `true` / `false` |
| 18 | `bursting` | Bursting | Boolean | No | `false` | Activates Oracle report bursting (split and distribute to multiple recipients) | `true` / `false` |
| 19 | `public_schedule` | Public Schedule | Boolean | No | `false` | Makes the Oracle scheduled job visible to all Publisher users | `true` / `false` |
| 20 | `job_locale` | Job Locale | Text | No | — | Locale for the Oracle scheduled job context; required when parameter values are not in English | Standard locale code, e.g., `fr-FR` |
| 21 | `job_timezone` | Job Timezone | Text | No | — | Time zone for the Oracle scheduled job execution context | Java-supported time zone, e.g., `America/Chicago` |
| 22 | `poll_interval_seconds` | Poll Interval (s) | Integer | No | `10` | Delay in seconds between consecutive `getScheduledReportStatus` calls | Integer ≥ 1 |
| 23 | `maximum_wait_seconds` | Maximum Wait (s) | Integer | No | `3600` | Maximum elapsed polling time in seconds; must be ≥ `poll_interval_seconds` | Integer ≥ `poll_interval_seconds` |
| 24 | `unknown_status_retry_count` | Unknown Status Retry Count | Integer | No | `3` | Consecutive unrecognized Oracle status values allowed before task failure; resets on a recognized status | Integer ≥ 0 |
| 25 | `scheduled_job_id` | Scheduled Job ID | Text (Output) | — | — | Oracle scheduled Job ID from `scheduleReport`; non-empty value triggers re-run behavior | Auto-populated |
| 26 | `final_status` | Final Status | Text (Output) | — | — | Raw Oracle `jobStatus` string at terminal state | Auto-populated |
| 27 | `status_message` | Status Message | Text (Output) | — | — | Oracle `JobStatus.message` at terminal state | Auto-populated |
| 28 | `elapsed_seconds` | Elapsed Seconds | Text (Output) | — | — | Seconds from Job ID capture to terminal state | Auto-populated |
| 29 | `report_path` | Report Path | Text (Output) | — | — | Echoes the `report_absolute_path` input value | Auto-populated |
