# Oracle Analytics Publisher Asynchronous Report Scheduler - Implementation Analysis

**Extension Name:** *Oracle Analytics Publisher Asynchronous Report Scheduler (ue-oracle-analytics-publisher)*
**Universal Template Name:** *Ue Oracle Analytics Publisher*
**Target Platform:** Linux

---

## Extension Overview

This extension authenticates to Oracle Analytics Publisher (BI Publisher) using HTTP Basic Authentication, submits a report job via the Oracle `v2/ScheduleService` SOAP API (`scheduleReport`), captures the returned Oracle scheduled Job ID, and polls `getScheduledReportStatus` until Oracle reports a terminal state (success or failure) or the configured polling timeout is reached. On re-run, if a preserved Job ID from a previous execution is available in the `scheduled_job_id` output field, the submission step is skipped and polling resumes directly using that Job ID. The extension exposes five output fields: Scheduled Job ID, Final Status, Status Message, Elapsed Seconds, and Report Path.

---

# Template Fields

## 1. Input Fields

**action**
- **Type**: Choice Field (Single-select)
- **Visible When**: always
- **Required When**: always
- **Options**:
  - Schedule and Monitor Report - Submits a report to Oracle Analytics Publisher and polls until a terminal state is reached
- **Default Value**: Schedule and Monitor Report
- **Validation**:
  - Must be one of the options
- **Purpose**: Specifies the action to perform

**oracle_credential**
- **Type**: Credential Field
- **Visible When**: always
- **Required When**: always
- **Validation**:
  - `user` attribute must not be empty (Oracle Fusion username)
  - `password` attribute must not be empty (Oracle Fusion password)
- **Purpose**: Oracle Fusion / Analytics Publisher credential. The `user` attribute maps to the Oracle username used for both HTTP Basic Authentication and the SOAP body `userID` element. The `password` attribute maps to the Oracle password used for both HTTP Basic Authentication and the SOAP body `password` element. The password must never appear in any log, STDOUT, STDERR, error message, or UAC output field.

**schedule_service_url**
- **Type**: Text Field
- **Visible When**: always
- **Required When**: always
- **Validation**:
  - Must not be empty
  - Must begin with `http://` or `https://`
- **Purpose**: Full SOAP endpoint URL for the Oracle `v2/ScheduleService`. Changing this field alone switches between environments (DEV, TEST, PROD).
- **Example**: `https://host.fa.ocs.oraclecloud.com/xmlpserver/services/v2/ScheduleService`

**verify_tls**
- **Type**: Boolean Field
- **Visible When**: always
- **Required When**: always
- **Default Value**: true
- **Purpose**: Controls TLS certificate validation for HTTPS connections. When true, the certifi CA bundle is used. Must remain true in production environments.

**connection_timeout_seconds**
- **Type**: Int Field
- **Visible When**: always
- **Required When**: never
- **Default Value**: 30
- **Validation**:
  - Must be a positive integer (minimum 1)
- **Purpose**: TCP/TLS connection-phase timeout in seconds for each SOAP HTTP request

**request_timeout_seconds**
- **Type**: Int Field
- **Visible When**: always
- **Required When**: never
- **Default Value**: 60
- **Validation**:
  - Must be a positive integer (minimum 1)
- **Purpose**: Read/response timeout in seconds for a single SOAP HTTP request after the connection is established

**report_absolute_path**
- **Type**: Text Field
- **Visible When**: always
- **Required When**: always
- **Validation**:
  - Must not be empty
  - Must end with `.xdo` (fail with validation error if it does not)
  - Must not be URL-encoded; the raw catalog path is placed directly into SOAP XML
- **Purpose**: Absolute Oracle Publisher catalog path for the report to submit. Maps to `ReportRequest.reportAbsolutePath`.
- **Example**: `/Custom/Financials/My Report.xdo`

**report_parameters**
- **Type**: Text Field (Large)
- **Visible When**: always
- **Required When**: never
- **Default Value**: `{}`
- **Validation**:
  - When provided and non-empty, must be valid JSON
  - Must be a JSON object (not an array, scalar, or null at the top level)
  - No parameter value may be an empty array `[]` (rejected as invalid input)
  - JSON `null` parameter values are accepted (the parameter is omitted from the SOAP request)
  - Empty string `""` parameter values are accepted (submitted as an empty string value)
- **Purpose**: Report parameters as a JSON object. Each property maps to one Oracle `ParamNameValue` element. Scalar values produce a single `<v2:item>` under `<v2:values>`. JSON arrays produce multiple `<v2:item>` elements. Properties set to `null` are omitted from the SOAP request.
- **Example**: `{"P_LEDGER_ID": "300000001", "P_FROM_DATE": "2026-08-01"}`

**output_format**
- **Type**: Choice Field (Single-select)
- **Visible When**: always
- **Required When**: never
- **Options**:
  - pdf - PDF format
  - html - HTML format
  - rtf - RTF format
  - excel - Excel (legacy) format
  - excel2000 - Excel 2000 format
  - xlsx - Excel XLSX format
  - ppt - PowerPoint format
  - pptx - PowerPoint PPTX format
  - mhtml - MHTML format
  - pdfa - PDF/A format
  - pdfx - PDF/X format
  - pdfz - PDF/Z compressed format
  - xslfo - XSL-FO format
  - xml - XML format
  - csv - CSV format
  - text - Plain text format
  - flash - Flash format
- **Default Value**: (empty — use report/template default)
- **Validation**:
  - Must be one of the listed options or empty (choiceAllowEmpty: true)
- **Purpose**: Maps to `ReportRequest.attributeFormat`. When empty, Oracle Publisher applies the report template's default format. Unsupported format/template combinations surface as SOAP faults from Oracle.

**report_template**
- **Type**: Text Field
- **Visible When**: always
- **Required When**: never
- **Purpose**: Maps to `ReportRequest.attributeTemplate`. Oracle Publisher report template name within the report definition.
- **Example**: `Template1`

**report_locale**
- **Type**: Text Field
- **Visible When**: always
- **Required When**: never
- **Purpose**: Maps to `ReportRequest.attributeLocale`. Standard locale identifier for the report output.
- **Example**: `en-US`

**ui_locale**
- **Type**: Text Field
- **Visible When**: always
- **Required When**: never
- **Purpose**: Maps to `ReportRequest.attributeUILocale`. Standard locale identifier for the Oracle Publisher UI during report processing.
- **Example**: `en-US`

**report_timezone**
- **Type**: Text Field
- **Visible When**: always
- **Required When**: never
- **Purpose**: Maps to `ReportRequest.attributeTimeZone`. Must be a Java-supported time zone ID when supplied.
- **Example**: `America/New_York`

**bypass_cache**
- **Type**: Boolean Field
- **Visible When**: always
- **Required When**: always
- **Default Value**: false
- **Purpose**: Maps to `ReportRequest.byPassCache`. When true, Oracle bypasses any cached report data and executes a fresh data query.

**job_name**
- **Type**: Text Field
- **Visible When**: always
- **Required When**: never
- **Purpose**: Maps to `ScheduleRequest.userJobName`. When empty, the extension auto-generates a name as `UAC-<report-basename>-<timestamp>` where `report-basename` is the filename portion of `report_absolute_path` without the `.xdo` extension and `timestamp` is formatted as `YYYYMMDDHHmmss`. The generated or configured name is included in ambiguous submission error messages to facilitate manual investigation in Oracle Publisher.
- **Example**: `UAC-MyReport-20260827120000`

**job_description**
- **Type**: Text Field
- **Visible When**: always
- **Required When**: never
- **Purpose**: Maps to `ScheduleRequest.userJobDesc`. When empty, defaults to `Submitted by Stonebranch UAC`.
- **Example**: `Monthly financials report for Q3`

**save_data**
- **Type**: Boolean Field
- **Visible When**: always
- **Required When**: always
- **Default Value**: false
- **Purpose**: Maps to `ScheduleRequest.saveDataOption`. Controls whether Oracle saves the report data extract alongside the output.

**save_output**
- **Type**: Boolean Field
- **Visible When**: always
- **Required When**: always
- **Default Value**: false
- **Purpose**: Maps to `ScheduleRequest.saveOutputOption`. Controls whether Oracle saves the report output document in the Publisher repository.

**bursting**
- **Type**: Boolean Field
- **Visible When**: always
- **Required When**: always
- **Default Value**: false
- **Purpose**: Maps to `ScheduleRequest.scheduleBurstingOption`. Controls whether Oracle applies report bursting (splitting and distributing report output to multiple recipients).

**public_schedule**
- **Type**: Boolean Field
- **Visible When**: always
- **Required When**: always
- **Default Value**: false
- **Purpose**: Maps to `ScheduleRequest.schedulePublicOption`. Controls whether the Oracle scheduled job is visible to all Publisher users.

**job_locale**
- **Type**: Text Field
- **Visible When**: always
- **Required When**: never
- **Purpose**: Maps to `ScheduleRequest.jobLocale`. Oracle requires this when submitted parameter values are not in English.
- **Example**: `fr-FR`

**job_timezone**
- **Type**: Text Field
- **Visible When**: always
- **Required When**: never
- **Purpose**: Maps to `ScheduleRequest.jobTZ`. Java-supported time zone ID for the Oracle scheduled job execution context.
- **Example**: `America/New_York`

**poll_interval_seconds**
- **Type**: Int Field
- **Visible When**: always
- **Required When**: never
- **Default Value**: 10
- **Validation**:
  - Must be at least 1
- **Purpose**: Delay in seconds between consecutive `getScheduledReportStatus` SOAP calls.

**maximum_wait_seconds**
- **Type**: Int Field
- **Visible When**: always
- **Required When**: never
- **Default Value**: 3600
- **Validation**:
  - Must be greater than or equal to `poll_interval_seconds`
- **Purpose**: Maximum elapsed polling time in seconds measured from the moment the `scheduleReport` Job ID is captured (or from the start of polling on re-run). When this threshold is exceeded without reaching a terminal state, the task fails with a timeout error including the Job ID and last known status.

**unknown_status_retry_count**
- **Type**: Int Field
- **Visible When**: always
- **Required When**: never
- **Default Value**: 3
- **Validation**:
  - Must not be negative (minimum 0)
- **Purpose**: Number of consecutive unrecognized Oracle job status values allowed before the task fails. The counter resets to zero whenever a recognized status (successful terminal, failure terminal, or in-progress) is subsequently returned.

---

## 2. Output Fields

**scheduled_job_id**
- **Type**: Text Output
- **Purpose**: Oracle scheduled Job ID returned by `scheduleReport`. Configured with `preserveOutputOnRerun: true` and `fieldRestriction: Output Only`. A non-empty preserved value triggers re-run behavior: the extension skips `scheduleReport` and polls this Job ID directly.
- **Examples**: `"123456"`, `"789012"`

**final_status**
- **Type**: Text Output
- **Purpose**: Raw `JobStatus.jobStatus` string value returned by Oracle at the terminal state (before normalization). Empty if the task fails before reaching a terminal Oracle status.
- **Examples**: `"Success"`, `"Failed"`, `"Completed"`

**status_message**
- **Type**: Text Output
- **Purpose**: Oracle `JobStatus.message` value at terminal state. Empty if Oracle returns no message field or the task fails before polling produces a message.
- **Examples**: `"Completed successfully"`, `"Report execution failed"`

**elapsed_seconds**
- **Type**: Text Output
- **Purpose**: Integer number of seconds from the moment the Job ID is captured (or polling begins on re-run) until the terminal status is reached or the task fails. Formatted as a plain integer string.
- **Examples**: `"42"`, `"186"`

**report_path**
- **Type**: Text Output
- **Purpose**: Submitted Oracle Publisher catalog path, echoed from `report_absolute_path` input. Set at task completion regardless of success or failure.
- **Examples**: `"/Custom/Financials/UAC Test Report.xdo"`

---

## 3. Field Ordering

The task form uses a **2-column grid layout**.

**Layout Rules:**
- Credential fields ALWAYS span full-width (both columns)
- Related timeout fields are grouped side-by-side
- Primary identifier and configuration fields span full-width
- Logically paired boolean fields share a row

**Field Order (Visual Layout):**

```
┌─────────────────────────────────────────────┐
│                   action                     │  ← Full-width
├─────────────────────────────────────────────┤
│              oracle_credential               │  ← Full-width (credential)
├─────────────────────────────────────────────┤
│            schedule_service_url              │  ← Full-width
├─────────────────────────────────────────────┤
│              verify_tls                      │  ← Full-width (security toggle)
├──────────────────────┬──────────────────────┤
│ connection_timeout_s │ request_timeout_s     │  ← Half-width pair
├──────────────────────┴──────────────────────┤
│            report_absolute_path              │  ← Full-width
├─────────────────────────────────────────────┤
│             report_parameters                │  ← Full-width (Large Text)
├─────────────────────────────────────────────┤
│               output_format                  │  ← Full-width (choice)
├──────────────────────┬──────────────────────┤
│   report_template    │    report_locale      │  ← Half-width pair
├──────────────────────┼──────────────────────┤
│     ui_locale        │   report_timezone     │  ← Half-width pair
├──────────────────────┴──────────────────────┤
│               bypass_cache                   │  ← Full-width
├─────────────────────────────────────────────┤
│                job_name                      │  ← Full-width
├─────────────────────────────────────────────┤
│             job_description                  │  ← Full-width
├──────────────────────┬──────────────────────┤
│      save_data       │     save_output       │  ← Half-width pair
├──────────────────────┼──────────────────────┤
│      bursting        │   public_schedule     │  ← Half-width pair
├──────────────────────┼──────────────────────┤
│     job_locale       │    job_timezone       │  ← Half-width pair
├──────────────────────┴──────────────────────┤
│  poll_interval_sec   │ maximum_wait_sec      │  ← Half-width pair
├─────────────────────────────────────────────┤
│        unknown_status_retry_count            │  ← Full-width
├─────────────────────────────────────────────┤
│              scheduled_job_id                │  ← Full-width (output, preserve on rerun)
├──────────────────────┬──────────────────────┤
│     final_status     │   status_message      │  ← Half-width pair (output)
├──────────────────────┼──────────────────────┤
│   elapsed_seconds    │    report_path        │  ← Half-width pair (output)
└──────────────────────┴──────────────────────┘
```

---

# Actions

## Action 1: Schedule and Monitor Report

**Description**: Authenticates to Oracle Analytics Publisher, submits a report job via `scheduleReport`, captures the Oracle scheduled Job ID, then polls `getScheduledReportStatus` until Oracle returns a terminal status or the maximum wait time is exceeded. On re-run, polling resumes using the preserved Job ID without resubmitting.

### Input Requirements

- **action**
- **oracle_credential**
- **schedule_service_url**
- **verify_tls**
- **connection_timeout_seconds**
- **request_timeout_seconds**
- **report_absolute_path**
- **report_parameters**
- **output_format**
- **report_template**
- **report_locale**
- **ui_locale**
- **report_timezone**
- **bypass_cache**
- **job_name**
- **job_description**
- **save_data**
- **save_output**
- **bursting**
- **public_schedule**
- **job_locale**
- **job_timezone**
- **poll_interval_seconds**
- **maximum_wait_seconds**
- **unknown_status_retry_count**
- **scheduled_job_id** (output field, read from previous run for re-run detection)

### Execution Flow

**Step 1: Re-run Detection**
- Read the `scheduled_job_id` output field value (available from a previous task execution when `preserveOutputOnRerun: true`).
- If `scheduled_job_id` is non-empty: record it as the active Job ID, log `Re-run detected: polling existing Publisher job <job_id>` to STDOUT, and jump directly to Step 5 (Polling Loop). Set the elapsed timer start at this point.
- If `scheduled_job_id` is empty or absent: continue to Step 2.

**Step 2: Input Validation**
Validate all fields before making any Oracle API call. Collect all violations and fail with exit code 20 and a descriptive message per violated rule:
- `schedule_service_url`: must not be empty; scheme must be `http://` or `https://`
- `oracle_credential.user`: must not be empty
- `oracle_credential.password`: must not be empty
- `report_absolute_path`: must not be empty; must end with `.xdo`
- `report_parameters`: when provided and non-empty, must be valid JSON; must be a JSON object (not array or scalar); no parameter value may be an empty array `[]`
- `poll_interval_seconds`: must be at least 1
- `maximum_wait_seconds`: must be greater than or equal to `poll_interval_seconds`
- `connection_timeout_seconds`: must be a positive integer (minimum 1)
- `request_timeout_seconds`: must be a positive integer (minimum 1)
- `unknown_status_retry_count`: must not be negative

**Step 3: Pre-submission Preparation**
- Log the target URL and report path to STDOUT: `Target: <schedule_service_url>` then `Submitting Oracle Publisher report <report_absolute_path>`
- Resolve `job_name`: if empty, generate `UAC-<report-basename>-<timestamp>` where `report-basename` is the filename portion of `report_absolute_path` without the `.xdo` extension, and `timestamp` is `YYYYMMDDHHmmss` in UTC.
- Resolve `job_description`: if empty, use `Submitted by Stonebranch UAC`.
- Parse `report_parameters` JSON: convert each property into a SOAP `ParamNameValue` structure. Skip properties with `null` values. Convert scalar values to a single-element list. Convert array values to a multi-element list. Empty JSON object `{}` produces zero `ParamNameValue` elements.
- Log: `Job name: <job_name> | Parameters: <count>` where count is the number of non-null parameters.
- Initialize requests.Session with:
  - HTTP Basic Auth using `oracle_credential.user` and `oracle_credential.password`
  - TLS verification: certifi CA bundle when `verify_tls` is true; no verification when false
  - Timeout tuple: `(connection_timeout_seconds, request_timeout_seconds)`

**Step 4: Submit Report via scheduleReport**
- Build the `scheduleReport` SOAP envelope (namespace: `http://xmlns.oracle.com/oxp/service/v2`):
  - `<v2:reportRequest>` containing: `reportAbsolutePath`, `parameterNameValues` (if any parameters exist), `attributeFormat` (if `output_format` is non-empty), `attributeTemplate` (if `report_template` is non-empty), `attributeLocale` (if `report_locale` is non-empty), `attributeUILocale` (if `ui_locale` is non-empty), `attributeTimeZone` (if `report_timezone` is non-empty), `byPassCache`
  - `<v2:scheduleRequest>` containing: `userJobName`, `userJobDesc`, `saveDataOption`, `saveOutputOption`, `scheduleBurstingOption`, `schedulePublicOption`, `jobLocale` (if `job_locale` is non-empty), `jobTZ` (if `job_timezone` is non-empty)
  - `<v2:userID>` and `<v2:password>` elements in the operation body (alongside reportRequest and scheduleRequest)
  - Content-Type header: `text/xml; charset=utf-8`
- Execute the SOAP POST. Handle outcomes:
  - **HTTP 401**: Fail immediately with `OracleAuthenticationError`; no retry
  - **HTTP 403**: Fail immediately with `OracleAuthorizationError`; no retry
  - **HTTP 404**: Fail immediately with `OracleEndpointNotFoundError`; no retry
  - **Timeout or connection reset after the request body may have been transmitted**: Fail immediately with `AmbiguousSubmissionError`; no retry (to prevent duplicate Oracle job creation)
  - **Connection-level error before request transmission** (DNS failure, connection refused): Fail immediately with `OracleConnectionError`; no retry
  - **2xx response**: Proceed to parse the SOAP response
- Parse the SOAP response (namespace-aware, without relying on specific namespace prefixes):
  - If a SOAP Fault element is present: extract `faultcode`, `faultstring`, and `detail`; fail with `OracleSoapFaultError`
  - If the XML is malformed: fail with `OracleParseError`
  - Extract the value of `scheduleReportReturn`; if absent or empty: fail with `MissingJobIdError`
- Record the captured Job ID. Set `scheduled_job_id` output field.
- Start the monotonic elapsed timer.
- Log: `Oracle Publisher scheduled Job ID: <job_id>`

**Step 5: Polling Loop**
- Read `UE_POLL_RETRY_COUNT` environment variable (default 3); this is the per-poll transient transport retry limit.
- Initialize `consecutive_unknown_count = 0` and `last_known_status = None`.

Loop until terminal condition:
1. Check elapsed time against `maximum_wait_seconds`. If exceeded: fail with `PollTimeoutError` including Job ID and `last_known_status`.
2. Sleep `poll_interval_seconds` seconds.
3. Build the `getScheduledReportStatus` SOAP envelope containing `<v2:jobID>`, `<v2:userID>`, and `<v2:password>`.
4. Execute the SOAP POST. For transient transport errors (HTTP 408, 429, 5xx, or read timeout), retry up to `UE_POLL_RETRY_COUNT` times with a short fixed backoff (2 seconds between retries) without resetting the overall elapsed timer. If all retries are exhausted: fail with `OracleTransientError`.
5. Parse the SOAP response:
   - If a SOAP Fault element is present: fail with `OracleSoapFaultStatusError` including Job ID and faultstring
   - If the XML is malformed: fail with `OracleParseError`
   - Extract `jobID`, `jobStatus`, and `message` from `getScheduledReportStatusReturn`
   - If the returned `jobID` differs from the submitted Job ID: fail with `InconsistentJobIdError`
6. Normalize the raw `jobStatus`: strip leading and trailing whitespace, convert to lowercase, collapse any repeated internal whitespace to a single space.
7. Classify the normalized status:
   - **Successful terminal** (`success`, `completed`, `done`): Break loop → proceed to Step 6
   - **Failure terminal** (`failed`, `error`, `canceled`, `cancelled`, `output has error`, `delivery has error`, `update status has error`, `deleted`, `skipped`, `suspended`): fail with `PublisherJobFailedError` including Job ID, raw status, and Oracle message
   - **In-progress** (`scheduled`, `waiting`, `running`, `cancelling`): reset `consecutive_unknown_count` to 0
   - **Unknown**: increment `consecutive_unknown_count`. If `consecutive_unknown_count` exceeds `unknown_status_retry_count`: fail with `UnknownStatusThresholdError` including raw status, Job ID, and consecutive count
8. If the normalized status differs from `last_known_status`: log `Job <job_id> status changed: <last_known_status> -> <raw_jobStatus>` to STDOUT. Update `last_known_status` to the current normalized status.

**Step 6: Completion**
- Calculate `elapsed_seconds` from the elapsed timer.
- Set output fields: `final_status` (raw jobStatus from the terminal response), `status_message` (Oracle message field, empty string if absent), `elapsed_seconds` (integer seconds as string), `report_path` (value of `report_absolute_path` input).
- Log: `Oracle Publisher job <job_id> completed successfully in <elapsed_seconds>s`
- Print formatted summary table to STDOUT using tabulate with `rounded_outline` style, with rows in this order: Scheduled Job ID, Report Path, Final Status, Status Message, Elapsed Seconds.
- Return exit code 0 and status description: `Oracle Publisher job <job_id> completed successfully in <elapsed_seconds>s`

### Output Examples

**STDOUT**:
```
Target: https://host.fa.ocs.oraclecloud.com/xmlpserver/services/v2/ScheduleService
Submitting Oracle Publisher report /Custom/Financials/UAC Test Report.xdo
Job name: UAC-UAC-Test-Report-20260827120000 | Parameters: 2
Oracle Publisher scheduled Job ID: 123456
Job 123456 status changed: None -> Scheduled
Job 123456 status changed: Scheduled -> Running
Job 123456 status changed: Running -> Success
Oracle Publisher job 123456 completed successfully in 42s
╭──────────────────────┬────────────────────────────────────────────╮
│ Scheduled Job ID     │ 123456                                     │
│ Report Path          │ /Custom/Financials/UAC Test Report.xdo     │
│ Final Status         │ Success                                    │
│ Status Message       │ Completed successfully                     │
│ Elapsed Seconds      │ 42                                         │
╰──────────────────────┴────────────────────────────────────────────╯
```

**Extension Output result object (JSON)**:

The Extension output also includes `exit_code`, `status_description`, and `invocation` elements added automatically during implementation time.

```json
{
  "result": {
    "scheduled_job_id": "123456",
    "report_path": "/Custom/Financials/UAC Test Report.xdo",
    "final_status": "Success",
    "status_message": "Completed successfully",
    "elapsed_seconds": 42
  }
}
```

### Success Criteria
1. HTTP transport completes with a 2xx response code for the `scheduleReport` request.
2. The SOAP response contains no Fault element.
3. The SOAP response is valid XML.
4. A non-empty Job ID is parsed from `scheduleReportReturn`.
5. Oracle returns a recognized successful terminal status (`success`, `completed`, or `done`) during polling before `maximum_wait_seconds` elapses.

---

# Progress Reporting

Progress Reporting (percentage of completion report) is not required.

The extension logs the following events to STDOUT during execution:
- Target `ScheduleService` URL and report absolute path at startup (before any API call)
- Generated or configured job name and parameter count (not parameter values) before submission
- Successful submission confirmation including the Oracle scheduled Job ID
- Status transitions logged only when the status changes from the previous poll (format: `Job <id> status changed: <old> -> <new>`)
- Final terminal status and elapsed time upon task completion
- Operator-friendly error messages upon failure

---

# Dynamic Choice Field Population

No Dynamic choice fields should be implemented. The `output_format` field uses a static choice list of Oracle's 17 documented `attributeFormat` values defined in the template.

---

# Cancellation Behavior

Default cancellation logic is used (TERM signal). No custom cancellation code is implemented in the extension.

**Important behavioral note**: When the UAC task process is terminated by the TERM signal during the polling loop or submission phase, any Oracle Analytics Publisher job that was already submitted continues running independently in Oracle. The extension does not call Oracle's `cancelSchedule` operation. Any already-submitted Oracle Publisher job must be managed manually through the Oracle Publisher interface. A future version may implement cancellation via Oracle's `cancelSchedule` API.

---

# Re-Run Behavior

**Purpose**: Skip the `scheduleReport` submission step and directly poll an already-submitted Oracle Publisher job when a preserved Job ID from a previous task execution is available. This prevents duplicate Oracle Publisher job creation on task re-run.

**Dependent fields**: `scheduled_job_id` (output field configured with `preserveOutputOnRerun: true`; populated from a prior successful submission and available at the start of a re-run execution)

**Execution Flow**:
1. At the very start of execution (before input validation), read the `scheduled_job_id` output field value.
2. If `scheduled_job_id` is non-empty: record it as the active Job ID, start the elapsed timer, log the re-run detection message to STDOUT, and skip directly to the polling loop. Input validation still runs before polling begins to catch misconfigured polling parameters.
3. If `scheduled_job_id` is empty: execute the full flow including input validation and `scheduleReport` submission.

**STDOUT Message**: `Re-run detected: polling existing Publisher job <job_id>`

---

# Dynamic Commands

No Dynamic commands should be implemented.

---

# Utility Modules

## Required Utility Modules

### 1. SOAP XML Builder

**Purpose:** Construct namespace-correct SOAP 1.1 envelope XML for Oracle `v2/ScheduleService` operations using `xml.etree.ElementTree`. All string values are XML-escaped. Optional fields are only included when their values are non-empty.

**Required Capabilities:**

**scheduleReport envelope construction:**
- Build the SOAP envelope and body with the `http://schemas.xmlsoap.org/soap/envelope/` namespace and `http://xmlns.oracle.com/oxp/service/v2` Oracle namespace
- Build `<v2:reportRequest>` with: `reportAbsolutePath`, `byPassCache`, and conditionally `attributeFormat`, `attributeTemplate`, `attributeLocale`, `attributeUILocale`, `attributeTimeZone`
- Build `<v2:parameterNameValues>` containing one `<v2:item>` per non-null parameter, each with `<v2:name>` and `<v2:values>` containing one or more `<v2:item>` child elements (one per scalar or array element)
- Build `<v2:scheduleRequest>` with: `userJobName`, `userJobDesc`, `saveDataOption`, `saveOutputOption`, `scheduleBurstingOption`, `schedulePublicOption`, and conditionally `jobLocale`, `jobTZ`
- Place `<v2:userID>` and `<v2:password>` elements as direct children of the operation element (same level as `reportRequest` and `scheduleRequest`)

**getScheduledReportStatus envelope construction:**
- Build the SOAP envelope containing `<v2:jobID>`, `<v2:userID>`, and `<v2:password>` as direct children of the operation element

**Serialization:**
- Serialize the ElementTree to a UTF-8 encoded byte string for use as the HTTP request body

**Used By:** Oracle HTTP Client (Step 4 and Step 5 of the execution flow)

---

### 2. SOAP Response Parser

**Purpose:** Parse Oracle `v2/ScheduleService` SOAP responses using namespace-aware XML parsing without relying on specific namespace prefixes.

**Required Capabilities:**

**Fault detection:**
- Detect SOAP Fault elements in the response regardless of which namespace prefix is used
- Extract `faultcode`, `faultstring`, and `detail` text values from Fault elements
- Return a structured fault object when a Fault is detected

**scheduleReport response parsing:**
- Locate the `scheduleReportReturn` element by its local name within the `http://xmlns.oracle.com/oxp/service/v2` namespace
- Return the text content as the Job ID string; return None if the element is absent or its text is empty

**getScheduledReportStatus response parsing:**
- Locate `getScheduledReportStatusReturn` element within the Oracle namespace
- Extract child elements `jobID`, `jobStatus`, and `message` by local name within the Oracle namespace
- Return a structured object with `job_id`, `job_status`, and `message` fields; `message` is an empty string if the element is absent

**XML parsing safety:**
- Parse the full response byte content using `xml.etree.ElementTree.fromstring`
- Raise `OracleParseError` on any `ParseError` or `ElementTree` exception

**Used By:** Oracle HTTP Client (response handling in Steps 4 and 5)

---

### 3. Oracle HTTP Client

**Purpose:** Manage the `requests.Session` lifecycle, execute SOAP POST requests, classify HTTP and transport errors into domain exceptions, and implement poll-phase retry logic.

**Required Capabilities:**

**Session management:**
- Initialize a `requests.Session` with HTTP Basic Auth, TLS verification setting (certifi bundle or disabled), and per-request timeout tuple `(connection_timeout_seconds, request_timeout_seconds)`
- Close the session at the end of task execution

**SOAP request execution:**
- Execute HTTP POST with Content-Type `text/xml; charset=utf-8` and the serialized SOAP envelope as the request body
- Accept the response and pass it to the SOAP Response Parser

**Submission error classification (no retry):**
- HTTP 401 → raise `OracleAuthenticationError`
- HTTP 403 → raise `OracleAuthorizationError`
- HTTP 404 → raise `OracleEndpointNotFoundError`
- `requests.exceptions.ConnectionError` or `requests.exceptions.Timeout` raised after the request body was at least partially transmitted → raise `AmbiguousSubmissionError` (include the job name in the error message)
- `requests.exceptions.ConnectionError` clearly before transmission → raise `OracleConnectionError`
- SOAP Fault in 2xx response → raise `OracleSoapFaultError`
- Missing Job ID in parsed response → raise `MissingJobIdError`

**Poll request retry logic:**
- For `getScheduledReportStatus` requests: retry up to `UE_POLL_RETRY_COUNT` times on transient errors (HTTP 408, 429, 5xx, or `requests.exceptions.Timeout`)
- Fixed 2-second sleep between poll retries
- The overall elapsed timer is not reset by poll retries
- After all poll retries exhausted: raise `OracleTransientError`
- SOAP Fault during polling → raise `OracleSoapFaultStatusError` immediately (not retried)

**Credential protection:**
- Never include credential values in any exception message, log entry, or error string

**Used By:** Action 1 execution flow (Steps 4 and 5)

---

### 4. Status Normalizer and Classifier

**Purpose:** Normalize raw Oracle job status strings and classify them into actionable categories.

**Required Capabilities:**

**Normalization:**
- Strip leading and trailing whitespace from the raw status string
- Convert to lowercase
- Collapse any sequence of internal whitespace characters (spaces, tabs, newlines) to a single space

**Classification** (applied to the normalized string):
- **Successful terminal**: normalized status is one of: `success`, `completed`, `done`
- **Failure terminal**: normalized status is one of: `failed`, `error`, `canceled`, `cancelled`, `output has error`, `delivery has error`, `update status has error`, `deleted`, `skipped`, `suspended`
- **In-progress**: normalized status is one of: `scheduled`, `waiting`, `running`, `cancelling`
- **Unknown**: normalized status matches none of the above categories

**Used By:** Action 1 polling loop (Step 5, status classification)

---

### 5. Output Formatter

**Purpose:** Handle all STDOUT output: progressive execution log lines and the final summary table.

**Required Capabilities:**

**Progressive log lines:**
- Log the target URL line: `Target: <schedule_service_url>`
- Log the report submission line: `Submitting Oracle Publisher report <report_absolute_path>`
- Log the job preparation line: `Job name: <job_name> | Parameters: <count>`
- Log the Job ID confirmation: `Oracle Publisher scheduled Job ID: <job_id>`
- Log status transitions (only when status changes): `Job <job_id> status changed: <previous_status> -> <current_raw_status>` where `<previous_status>` is `None` on the first transition
- Log re-run detection: `Re-run detected: polling existing Publisher job <job_id>`
- Log completion: `Oracle Publisher job <job_id> completed successfully in <elapsed_seconds>s`
- Log operator-friendly error messages upon failure

**Summary table:**
- Use `tabulate` library with `tablefmt="rounded_outline"`
- Table contains two columns (no headers) with five rows in this exact order: Scheduled Job ID, Report Path, Final Status, Status Message, Elapsed Seconds
- Print the table to STDOUT after the completion log line (on both success and failure paths where output fields are available)

**Used By:** Action 1 execution flow (Steps 3, 4, 5, 6)

---

## Exception Mapping Strategy

**Input Validation Errors:**
- Any field fails pre-flight validation rule → `InputValidationError` (exit code 20, user configuration/input error, non-retryable)

**HTTP Authentication and Authorization Errors (submission only):**
- HTTP 401 response → `OracleAuthenticationError` (exit code 1, user configuration — invalid credentials, non-retryable)
- HTTP 403 response → `OracleAuthorizationError` (exit code 1, user configuration — insufficient permissions, non-retryable)
- HTTP 404 response → `OracleEndpointNotFoundError` (exit code 1, user configuration — wrong endpoint URL, non-retryable)

**Transport and Connection Errors:**
- Connection-level error before request transmission (DNS failure, connection refused) → `OracleConnectionError` (exit code 1, system/network, non-retryable)
- Timeout or connection reset after request body may have been transmitted (submission only) → `AmbiguousSubmissionError` (exit code 1, network, no retry — duplicate-submission risk)
- Transient transport error during polling (HTTP 408, 429, 5xx, read timeout), all retries exhausted → `OracleTransientError` (exit code 1, transient/system, retried up to `UE_POLL_RETRY_COUNT`)

**SOAP Response Errors:**
- SOAP Fault in `scheduleReport` response → `OracleSoapFaultError` (exit code 1, Oracle server or user input error, non-retryable)
- SOAP Fault in `getScheduledReportStatus` response → `OracleSoapFaultStatusError` (exit code 1, Oracle server error, non-retryable)
- No or empty Job ID in successful `scheduleReport` response → `MissingJobIdError` (exit code 1, unexpected Oracle response, non-retryable)
- Malformed XML in any SOAP response → `OracleParseError` (exit code 1, unexpected Oracle response, non-retryable)

**Oracle Status and Business Logic Errors:**
- Failure terminal Oracle job status returned during polling → `PublisherJobFailedError` (exit code 1, Oracle job execution failure, non-retryable)
- `maximum_wait_seconds` exceeded without reaching a terminal status → `PollTimeoutError` (exit code 1, timeout — insufficient wait configuration or long-running report, non-retryable)
- Consecutive unknown statuses exceed `unknown_status_retry_count` → `UnknownStatusThresholdError` (exit code 1, unrecognized Oracle status vocabulary, non-retryable)
- `jobID` in `getScheduledReportStatus` response differs from submitted Job ID → `InconsistentJobIdError` (exit code 1, Oracle response integrity error, non-retryable)

**Exit Code Guide:**
- Exit code 0: Successful execution
- Exit code 1: Execution failure (all transport, SOAP, Oracle job, and polling errors)
- Exit code 20: Input validation error (user configuration or input error, detected before any Oracle API call)

---

# Dependencies

## 1. External API Dependencies

**1. Oracle Analytics Publisher v2/ScheduleService SOAP API**
- **Endpoint**: `<schedule_service_url>` (user-configured; e.g., `https://host.fa.ocs.oraclecloud.com/xmlpserver/services/v2/ScheduleService`)
- **Purpose**: Submit report jobs and poll job status within Oracle Fusion Applications
- **Protocol**: SOAP 1.1 over HTTPS
- **Method**: HTTP POST for both operations
- **Authentication**: HTTP Basic Authentication (Authorization header) + `userID` and `password` elements in the SOAP operation body
- **Response Format**: XML (SOAP envelope)
- **Operations Used**:
  - `scheduleReport`: submits a report job; returns `scheduleReportReturn` containing the Oracle Job ID
  - `getScheduledReportStatus`: polls job status; returns `getScheduledReportStatusReturn` containing `jobID`, `jobStatus`, and `message`
- **SOAP Namespace**: `http://xmlns.oracle.com/oxp/service/v2`
- **Content-Type**: `text/xml; charset=utf-8`

**General API Requirements:**
- An Oracle Fusion Applications account with access to the BI Publisher `v2/ScheduleService` web service endpoint
- The Oracle user must have permission to access the report catalog path and execute the specified report
- The `schedule_service_url` must point to the correct Fusion pod environment (DEV, TEST, PROD)
- Oracle's WSDL for the target pod is the definitive authority on element ordering, namespace details, and SOAPAction header values

---

## 2. Python version dependency

Python >= 3.11 is required.

---

## 3. Target Platform

Linux only (x86_64 / manylinux_2_17_x86_64). C extension modules with a confirmed `manylinux_2_17_x86_64` wheel are viable in addition to pure-Python modules.

---

## 4. Python Library Dependencies

**1. requests**
- **Purpose**: HTTP client for executing SOAP POST requests with session management, HTTP Basic Authentication, TLS certificate verification, and configurable connection and read timeouts
- **Version**: 2.34.2
- **Installation**: `pip install requests==2.34.2`
- **Usage**: Oracle HTTP Client utility module; SOAP POST execution for both `scheduleReport` and `getScheduledReportStatus`
- **Features Used**: `requests.Session`, Basic Auth, TLS verification with certifi, `timeout` tuple `(connect, read)`, response status codes, exception types (`ConnectionError`, `Timeout`)

**2. certifi**
- **Purpose**: Mozilla CA certificate bundle for TLS verification of Oracle Fusion Cloud HTTPS endpoints
- **Version**: 2026.7.22
- **Installation**: `pip install certifi==2026.7.22`
- **Usage**: Provided to `requests.Session` as the `verify` parameter when `verify_tls` is true
- **Features Used**: `certifi.where()` to obtain the CA bundle path

**3. tabulate**
- **Purpose**: STDOUT summary table formatting in `rounded_outline` style
- **Version**: 0.10.0
- **Installation**: `pip install tabulate==0.10.0`
- **Usage**: Output Formatter utility module; generates the five-row summary table printed to STDOUT at task completion
- **Features Used**: `tabulate()` function with `tablefmt="rounded_outline"`

---

## 5. Python Standard Library Dependencies

**1. xml.etree.ElementTree**
- **Purpose**: Namespace-aware XML request building and SOAP response parsing
- **Version**: Built-in (Python >= 3.11)
- **Installation**: No installation required
- **Usage**: SOAP XML Builder and SOAP Response Parser utility modules
- **Features Used**: `Element`, `SubElement`, `tostring`, `fromstring`, namespace-qualified tag lookups using `{namespace}localname` format

**2. json**
- **Purpose**: Parsing the `report_parameters` Large Text field value into a Python dictionary for SOAP construction
- **Version**: Built-in (Python >= 3.11)
- **Installation**: No installation required
- **Usage**: Input validation (Step 2) and SOAP XML Builder
- **Features Used**: `json.loads()`, `json.JSONDecodeError`

**3. time**
- **Purpose**: Monotonic clock for measuring elapsed seconds from submission to terminal status
- **Version**: Built-in (Python >= 3.11)
- **Installation**: No installation required
- **Usage**: Polling loop (Step 5) and completion (Step 6)
- **Features Used**: `time.monotonic()`

**4. os**
- **Purpose**: Reading the `UE_POLL_RETRY_COUNT` environment variable
- **Version**: Built-in (Python >= 3.11)
- **Installation**: No installation required
- **Usage**: Oracle HTTP Client utility module initialization
- **Features Used**: `os.environ.get()`

**5. datetime**
- **Purpose**: Generating the timestamp component of auto-generated job names
- **Version**: Built-in (Python >= 3.11)
- **Installation**: No installation required
- **Usage**: Pre-submission preparation (Step 3)
- **Features Used**: `datetime.datetime.utcnow()` formatted as `YYYYMMDDHHmmss`

**6. urllib.parse**
- **Purpose**: URL scheme validation during input validation
- **Version**: Built-in (Python >= 3.11)
- **Installation**: No installation required
- **Usage**: Input validation (Step 2)
- **Features Used**: `urllib.parse.urlparse()` to extract and check the URL scheme

---

## 6. CLI Tool Dependencies

No Dependencies.

---

## 7. Environment Variables

**UE_POLL_RETRY_COUNT** (integer, optional):
- **Purpose**: Controls the maximum number of transient transport retry attempts for each `getScheduledReportStatus` poll request. Distinct from `unknown_status_retry_count`, which governs consecutive unrecognized Oracle status values.
- **Default**: `3`
- **Usage**: Oracle HTTP Client utility module; applied to every `getScheduledReportStatus` call that encounters a transient HTTP error (408, 429, 5xx) or read timeout
- **Examples**: `UE_POLL_RETRY_COUNT=5` for environments with known intermittent connectivity; `UE_POLL_RETRY_COUNT=0` to disable transient retries entirely
