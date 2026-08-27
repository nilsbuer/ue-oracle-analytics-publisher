# Requirements: Stonebranch Universal Task for Oracle Fusion Analytics Publisher Asynchronous Report Scheduling

## 1. Purpose

Build a **Stonebranch Universal Automation Center (UAC) Universal Task** implemented in Python that submits and monitors an **Oracle Analytics Publisher / BI Publisher report in an Oracle Fusion Applications environment** by using Oracle's SOAP **`v2/ScheduleService`** API.

This integration is specifically for the Publisher service embedded in **Oracle Fusion Applications**, not a standalone/dedicated Oracle Analytics Server installation.

The task must implement an **asynchronous execution pattern**:

1. Authenticate to the Oracle Fusion Analytics Publisher SOAP service.
2. Submit a report by calling `ScheduleService.scheduleReport`.
3. Parse and store the returned **scheduled Job ID**.
4. Poll `ScheduleService.getScheduledReportStatus` using that Job ID.
5. Finish the UAC task successfully only when Oracle reports a successful terminal state.
6. Fail the UAC task when Oracle reports a failed/cancelled/non-success terminal state, a SOAP fault, an authentication/HTTP error, an invalid response, or the configured polling timeout is reached.

The first version is an **execution-and-monitoring task only**. Retrieving or downloading the generated report output is out of scope.

---

## 2. Target Oracle Service

### 2.1 Target environment

Example Fusion Applications Publisher endpoint supplied for development:

```text
https://icbpjb-dev3.fa.ocs.oraclecloud.com/xmlpserver/services/v2/ScheduleService
```

WSDL:

```text
https://icbpjb-dev3.fa.ocs.oraclecloud.com/xmlpserver/services/v2/ScheduleService?wsdl
```

The implementation **must not hard-code this hostname**. The ScheduleService URL must be a task/configuration field so that the same Universal Task can be used against DEV, TEST, and PROD Fusion environments.

### 2.2 Oracle SOAP namespace

For the `v2/ScheduleService`, use:

```text
http://xmlns.oracle.com/oxp/service/v2
```

SOAP 1.1 envelope namespace:

```text
http://schemas.xmlsoap.org/soap/envelope/
```

Primary content type:

```text
text/xml; charset=utf-8
```

### 2.3 Oracle documentation basis

Oracle documents `ScheduleService` as the Publisher service used to schedule report jobs, retrieve report outputs, and manage report histories.

Oracle's current documentation for `scheduleReport` states:

```text
String scheduleReport(ScheduleRequest scheduleRequest, String userID, String password)
```

and states that the method returns the Job ID of the scheduled job.

Oracle's current documentation for `getScheduledReportStatus` states:

```text
JobStatus getScheduledReportStatus(
    String scheduledJobID,
    String userID,
    String password
)
```

The returned `JobStatus` contains:

- `jobID`
- `jobStatus`
- `message`

See the source references at the end of this document.

---

## 3. Important Authentication Requirement

### 3.1 UAC authentication input

The Universal Task must expose credentials through the standard secure UAC credential mechanism:

- Username
- Password

The password must be handled as a secret/password field and must never be printed in normal or debug logs.

### 3.2 Fusion `v2/ScheduleService` operation credentials

For the **public Fusion Applications Publisher `v2/ScheduleService`**, the Python implementation must pass the username and password in the SOAP operation payload because:

- Oracle documents `userID` and `password` as parameters of both `scheduleReport` and `getScheduledReportStatus`.
- Oracle's Fusion Applications BI Publisher integration documentation describes the public `v2/ReportService` and `v2/ScheduleService` services as services that expect credentials in the SOAP payload/body.

Therefore, for the endpoint in scope, **do not omit the SOAP `userID` and `password` elements merely because HTTP Basic Authentication is also configured**.

### 3.3 HTTP Basic Authentication

The requested first authentication mode is **HTTP Basic Authentication over HTTPS**.

The Python HTTP client should support sending:

```text
Authorization: Basic <base64(username:password)>
```

using the HTTP client's normal Basic Authentication feature rather than manually logging or constructing the header.

The same UAC credential should be used for:

1. HTTP Basic Authentication, and
2. the Oracle `userID` / `password` SOAP operation elements.

This dual use is intentional for the first implementation because the Oracle `v2` public service contract includes credentials in the method body.

### 3.4 Authentication compatibility note

Oracle Analytics deployments can also be configured for OAuth/SSO. OAuth support is **not part of MVP**, but the implementation should isolate authentication logic sufficiently that an OAuth mode can be added later without redesigning report submission or status polling.

If the target Fusion environment rejects Basic Authentication, the task must fail with a clear authentication error. It must not silently retry using another authentication mechanism.

---

## 4. Functional Scope

### 4.1 Required operation

One UAC task execution represents **one report execution**.

The task must:

- Submit one report.
- Capture one Oracle scheduled Job ID.
- Poll that Job ID.
- Return one final task result.

### 4.2 Out of scope for MVP

Do **not** implement the following in the initial task:

- Publisher recurring schedules.
- Cron recurrence expressions.
- `scheduleReportInSession`.
- `SecurityService.login` and `bipSessionToken`.
- OAuth authentication.
- Downloading report output.
- `getDocumentData`.
- `downloadDocumentData`.
- Retrieving job history.
- Cancelling a Publisher job when the UAC task is cancelled.
- Email/FTP/WCC/Object Storage delivery-channel configuration.
- Creating or modifying Publisher catalog reports.
- Synchronous `ReportService.runReport`.

Recurring scheduling should especially remain out of scope. Although the generic ScheduleRequest type contains recurrence fields, Oracle Community contains a case where an Oracle SR response stated that recurring jobs using `recurrenceExpression` were not supported through that web service scenario. UAC itself should own recurrence: if a report needs to run every day/hour/etc., schedule the **UAC task/workflow**, and let each execution submit one Publisher job.

---

## 5. Universal Task Inputs

The exact UAC field names can follow Stonebranch naming conventions, but the following logical inputs are required.

### 5.1 Connection

| Field | Type | Required | Default | Requirements |
|---|---|---:|---|---|
| `Schedule Service URL` | Text | Yes | none | Full SOAP endpoint, for example `https://host/xmlpserver/services/v2/ScheduleService`. |
| `Username` | Credential/User | Yes | none | Oracle Fusion / Publisher user. |
| `Password` | Credential/Password | Yes | none | Secret. Never log. |
| `Verify TLS Certificate` | Boolean | No | `true` | TLS certificate validation must be enabled by default. |
| `Connection Timeout Seconds` | Integer | No | `30` | TCP/TLS connection timeout. |
| `Request Timeout Seconds` | Integer | No | `60` | Timeout for one SOAP request. |

Do not expose an option that disables TLS verification without a warning. Production use should retain certificate verification.

### 5.2 Report

| Field | Type | Required | Default | Requirements |
|---|---|---:|---|---|
| `Report Absolute Path` | Text | Yes | none | Absolute Publisher catalog path ending in `.xdo`, e.g. `/Custom/Financials/My Report.xdo`. |
| `Report Parameters` | Large Text / JSON | No | `{}` | JSON representation described below. |
| `Output Format` | Text/Choice | No | empty | Maps to `ReportRequest.attributeFormat`. If omitted, allow Publisher/report defaults. |
| `Template` | Text | No | empty | Maps to `ReportRequest.attributeTemplate`. |
| `Report Locale` | Text | No | empty | Maps to `ReportRequest.attributeLocale`, e.g. `en-US`. |
| `UI Locale` | Text | No | empty | Maps to `ReportRequest.attributeUILocale`. |
| `Report Time Zone` | Text | No | empty | Maps to `ReportRequest.attributeTimeZone`; must be a Java-supported time-zone ID when supplied. |
| `Bypass Cache` | Boolean | No | `false` | Maps to `ReportRequest.byPassCache`. |

Oracle documents output-format values such as `pdf`, `html`, `rtf`, `excel`, `excel2000`, `xlsx`, `ppt`, `pptx`, `mhtml`, `pdfa`, `pdfx`, `pdfz`, `xslfo`, `xml`, `csv`, `text`, and `flash`, with actual validity depending on the report template type.

Do not try to pre-validate every format/template combination in Python. Oracle Publisher remains the authority and SOAP faults/errors must be surfaced clearly.

### 5.3 Schedule request

| Field | Type | Required | Default | Requirements |
|---|---|---:|---|---|
| `Job Name` | Text | No | generated | Maps to `ScheduleRequest.userJobName`. Use a meaningful generated value when omitted. |
| `Job Description` | Text | No | generated/empty | Maps to `ScheduleRequest.userJobDesc`. |
| `Save Data` | Boolean | No | `false` | Maps to `ScheduleRequest.saveDataOption`. |
| `Save Output` | Boolean | No | `false` | Maps to `ScheduleRequest.saveOutputOption`. Oracle documents the default as false. |
| `Bursting` | Boolean | No | `false` | Maps to `ScheduleRequest.scheduleBurstingOption`. |
| `Public Schedule` | Boolean | No | `false` | Maps to `ScheduleRequest.schedulePublicOption`. |
| `Job Locale` | Text | No | empty | Maps to `ScheduleRequest.jobLocale`; Oracle notes this is required when submitted parameter values are not English. |
| `Job Time Zone` | Text | No | empty | Maps to `ScheduleRequest.jobTZ`. |

The task is intended to run the job immediately. Do not expose recurring schedule fields in MVP.

If an explicit `startDate` is required by the target Fusion WSDL/runtime, use the immediate-run convention proven against that target environment. Oracle documentation states that `scheduleReport` supports immediate execution, while Oracle Community SOAP examples commonly use `SYSDATE` for `startDate`. Keep this behavior isolated in one request-builder function so it can be adjusted after WSDL/pod validation.

### 5.4 Polling

| Field | Type | Required | Default | Requirements |
|---|---|---:|---|---|
| `Poll Interval Seconds` | Integer | No | `10` | Delay between status requests. Minimum recommended value: 1 second. |
| `Maximum Wait Seconds` | Integer | No | `3600` | Maximum elapsed polling time after successful submission. |
| `Unknown Status Retry Count` | Integer | No | `3` | Number of consecutive unknown/unrecognized statuses allowed before failing. |

Polling must not be a tight loop.

---

## 6. Report Parameter Input Format

The task must accept report parameters as JSON.

### 6.1 Simple single-value parameters

Example:

```json
{
  "P_BUSINESS_UNIT": "Vision Operations",
  "P_LEDGER_ID": 300000001,
  "P_INCLUDE_ZERO": "N",
  "P_AS_OF_DATE": "2026-08-27"
}
```

Generate one Oracle `ParamNameValue` per JSON property:

```xml
<v2:parameterNameValues>
  <v2:listOfParamNameValues>
    <v2:item>
      <v2:name>P_BUSINESS_UNIT</v2:name>
      <v2:values>
        <v2:item>Vision Operations</v2:item>
      </v2:values>
    </v2:item>
  </v2:listOfParamNameValues>
</v2:parameterNameValues>
```

### 6.2 Multi-value parameters

JSON arrays must become multiple `<v2:item>` elements under `<v2:values>`.

Example:

```json
{
  "P_LEDGER_ID": [300000001, 300000002]
}
```

SOAP fragment:

```xml
<v2:item>
  <v2:name>P_LEDGER_ID</v2:name>
  <v2:values>
    <v2:item>300000001</v2:item>
    <v2:item>300000002</v2:item>
  </v2:values>
</v2:item>
```

Oracle's `ParamNameValue` type documents `name` and an `ArrayOfString values`, and also documents that multi-value parameters may contain multiple values.

### 6.3 Null handling

Use the following behavior:

- Missing JSON property: parameter is not submitted.
- JSON `null`: omit that parameter by default rather than serializing the literal string `"null"`.
- Empty string `""`: submit an empty string value.
- Empty list `[]`: reject as invalid input unless target behavior has been explicitly tested.

### 6.4 XML escaping

Parameter names and values, report paths, template names, job names, descriptions, username, and password must be XML-escaped by an XML library.

Do not build SOAP requests with unescaped string concatenation.

---

## 7. SOAP Request: `scheduleReport`

### 7.1 Required structure

Construct a SOAP 1.1 request in this form:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope
    xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
    xmlns:v2="http://xmlns.oracle.com/oxp/service/v2">
  <soapenv:Header/>
  <soapenv:Body>
    <v2:scheduleReport>
      <v2:scheduleRequest>

        <v2:reportRequest>
          <v2:attributeFormat>pdf</v2:attributeFormat>

          <v2:parameterNameValues>
            <v2:listOfParamNameValues>
              <v2:item>
                <v2:name>P_EXAMPLE</v2:name>
                <v2:values>
                  <v2:item>VALUE</v2:item>
                </v2:values>
              </v2:item>
            </v2:listOfParamNameValues>
          </v2:parameterNameValues>

          <v2:reportAbsolutePath>/Custom/Example/Example Report.xdo</v2:reportAbsolutePath>
        </v2:reportRequest>

        <v2:saveDataOption>false</v2:saveDataOption>
        <v2:saveOutputOption>false</v2:saveOutputOption>
        <v2:scheduleBurstingOption>false</v2:scheduleBurstingOption>
        <v2:schedulePublicOption>false</v2:schedulePublicOption>

        <v2:userJobDesc>Submitted by Stonebranch UAC</v2:userJobDesc>
        <v2:userJobName>UAC Example Report</v2:userJobName>

      </v2:scheduleRequest>

      <v2:userID>ORACLE_USER</v2:userID>
      <v2:password>ORACLE_PASSWORD</v2:password>
    </v2:scheduleReport>
  </soapenv:Body>
</soapenv:Envelope>
```

Only include optional fields when they are configured or when a tested default is intentionally required.

### 7.2 HTTP request

Use an HTTP `POST` to the configured Schedule Service URL.

Required/expected headers:

```text
Content-Type: text/xml; charset=utf-8
Accept: text/xml
```

For HTTP Basic mode, send the Basic Authorization header through the HTTP library's auth support.

`SOAPAction` handling must follow the target WSDL. Do not assume a hard-coded `SOAPAction` is portable if the WSDL specifies an empty action. If a SOAPAction header is required by the Fusion pod, centralize it as an operation-specific constant/configuration and add an automated test.

### 7.3 Response parsing

Oracle documents that `scheduleReport` returns a string Job ID.

The parser must:

1. Detect a SOAP Fault before attempting normal response parsing.
2. Locate the `scheduleReport` return value without depending on a specific XML prefix.
3. Strip surrounding whitespace.
4. Validate that a non-empty Job ID was returned.
5. Preserve the Job ID as a string, even when it contains only digits.

Typical WSDL naming is expected to contain a `scheduleReportResponse` with a `scheduleReportReturn` value, but parsing should be namespace-aware/local-name tolerant because SOAP prefix names can vary.

### 7.4 Submission success criteria

Submission is successful only if:

- HTTP transport completes successfully.
- No SOAP Fault exists.
- The response is valid XML.
- A non-empty scheduled Job ID is parsed.

If any of the above is false, the task must fail without entering the poll loop.

---

## 8. SOAP Request: `getScheduledReportStatus`

### 8.1 Required structure

For every poll, construct a request equivalent to:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope
    xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
    xmlns:v2="http://xmlns.oracle.com/oxp/service/v2">
  <soapenv:Header/>
  <soapenv:Body>
    <v2:getScheduledReportStatus>
      <v2:scheduledJobID>123456</v2:scheduledJobID>
      <v2:userID>ORACLE_USER</v2:userID>
      <v2:password>ORACLE_PASSWORD</v2:password>
    </v2:getScheduledReportStatus>
  </soapenv:Body>
</soapenv:Envelope>
```

### 8.2 Oracle response model

Oracle documents `JobStatus` with the fields:

```text
jobID
jobStatus
message
```

The parser must extract all three if present.

Expected semantic result:

```python
{
    "job_id": "123456",
    "status": "Running",
    "message": "..."
}
```

### 8.3 Job ID validation

If Oracle returns a `jobID` in `JobStatus`, compare it to the submitted Job ID.

- If it matches: continue.
- If it is absent: do not fail solely because it is absent.
- If it is present and differs: fail as an invalid/inconsistent response.

---

## 9. Status Handling

### 9.1 Do not rely on one Oracle status vocabulary

Oracle documentation and Oracle community information show different status wording across Publisher versions/interfaces.

Examples found in Oracle material include:

- `Running`
- `Success`
- `Failed`
- `Cancelling`
- `Canceled`
- `Output has Error`
- `Delivery has Error`
- `Update Status has Error`
- `Deleted`
- `Scheduled`
- `Suspended`
- `Skipped`
- `Waiting`
- and older documentation using values such as `Completed`, `Error`, and `Unknown`.

Therefore, normalize the returned value before deciding task state:

```text
trim whitespace
case-fold / lowercase
collapse repeated internal whitespace
```

### 9.2 Successful terminal states

Treat the following as successful terminal states:

```text
success
completed
done
```

On a successful terminal state:

- Stop polling.
- UAC task result = success.
- Publish/log scheduled Job ID.
- Publish/log final Oracle status.
- Publish/log Oracle status message if non-secret.

### 9.3 In-progress states

Treat these as in progress:

```text
scheduled
waiting
running
cancelling
```

For these values:

- Log the status only when it changes, or at a controlled diagnostic cadence.
- Sleep for the configured poll interval.
- Poll again until Maximum Wait Seconds is reached.

### 9.4 Failure terminal states

Treat these as terminal non-success:

```text
failed
error
canceled
cancelled
output has error
delivery has error
update status has error
deleted
skipped
suspended
```

For a terminal non-success state:

- Stop polling immediately.
- UAC task result = failure.
- Include Job ID, final status, and Oracle `message` in the task error message.

`Suspended` should be treated as failure for this UAC task because this task's contract is to wait for a completed report execution; a suspended Publisher schedule cannot meet that contract without external intervention.

### 9.5 Unknown/unrecognized states

For:

```text
unknown
```

or any status value not recognized by the implementation:

- Do not immediately declare success.
- Retry for `Unknown Status Retry Count` consecutive polls.
- Reset the unknown counter if a recognized state is later returned.
- Fail after the configured consecutive threshold with a message containing the raw Oracle status and Job ID.

This provides tolerance for brief scheduler inconsistencies while avoiding an infinite loop on a new/unsupported status.

---

## 10. Polling Algorithm

Required logical flow:

```text
validate task inputs
        |
        v
build scheduleReport SOAP request
        |
        v
POST scheduleReport
        |
        +---- transport/SOAP/parse error ----> FAIL
        |
        v
capture scheduled Job ID
        |
        v
record monotonic start time
        |
        v
sleep poll interval
        |
        v
POST getScheduledReportStatus
        |
        +---- transport/SOAP/parse error ----> retry policy or FAIL
        |
        v
normalize Oracle jobStatus
        |
        +---- successful terminal -----------> SUCCESS
        |
        +---- failed terminal ----------------> FAIL
        |
        +---- in progress --------------------> poll again
        |
        +---- unknown ------------------------> limited retry
        |
        v
maximum wait exceeded
        |
        v
FAIL with timeout + Job ID
```

Use a **monotonic clock** for elapsed-time calculations.

The maximum-wait timer starts after the Job ID has been successfully returned.

---

## 11. HTTP and Retry Behavior

### 11.1 HTTP status

Handle at minimum:

- `2xx`: parse SOAP.
- `401`: authentication failure; fail immediately.
- `403`: authorization failure; fail immediately.
- `404`: bad endpoint/service path; fail immediately.
- `408`: request timeout; transient candidate.
- `429`: rate/traffic throttling; transient candidate.
- `5xx`: server-side/transient candidate.

A `200 OK` can still contain a SOAP Fault. Always inspect the XML body for SOAP Faults.

### 11.2 Submission retries

Avoid blindly retrying `scheduleReport`.

A network failure can occur after Oracle accepted the request but before the client received the Job ID. Retrying the submission could create a duplicate Publisher job.

MVP requirement:

- **Do not automatically retry `scheduleReport` after an ambiguous transport failure** unless a safe idempotency strategy is added.
- Fail with a message explaining that submission outcome is unknown when the connection breaks after the request may have been sent.
- Include the generated UAC/Publisher job name in the error so an operator can search Publisher job history.

Safe automatic retries are acceptable only for failures known to occur before request transmission.

### 11.3 Poll retries

`getScheduledReportStatus` is read-only and may be retried for transient transport errors.

Recommended behavior:

- Retry transient poll failures with bounded attempts.
- Use a short backoff.
- Do not reset the overall `Maximum Wait Seconds` timer.
- Authentication, authorization, SOAP Faults indicating invalid credentials/parameters, and malformed responses should fail immediately rather than being endlessly retried.

---

## 12. SOAP Fault Handling

The Python implementation must explicitly detect:

```xml
<soapenv:Fault>
```

Extract, when available:

- `faultcode`
- `faultstring`
- useful text from `detail`

Return a concise UAC failure message similar to:

```text
Oracle Publisher scheduleReport failed: SOAP Fault
faultcode=...
faultstring=...
```

Do not include the entire request payload in the error because it contains the Oracle password.

If a raw response is logged in debug mode, redact any credential material and enforce a reasonable maximum length.

---

## 13. XML Parsing Requirements

Use a real XML parser.

Requirements:

- Namespace-aware.
- Do not depend on prefixes such as `soapenv`, `v2`, `ns0`, etc.; prefixes are arbitrary.
- Support normal SOAP 1.1 response envelopes.
- Reject malformed XML with a clear error.
- Protect against XML parser features that are unnecessary for this use case (no external entity expansion).
- Do not use regular expressions to parse SOAP XML.

Request XML should also be built using an XML library where practical to guarantee escaping.

---

## 14. Python Implementation Requirements

### 14.1 Structure

Keep the Oracle client behavior separate from UAC glue.

Suggested logical modules/functions:

```text
validate_inputs(...)
build_schedule_report_envelope(...)
build_status_envelope(...)
soap_post(...)
parse_soap_fault(...)
parse_schedule_report_response(...)
parse_job_status_response(...)
normalize_job_status(...)
submit_report(...)
wait_for_report(...)
main / UAC entry point
```

A class-based design such as `OraclePublisherScheduleClient` is also acceptable.

### 14.2 Dependencies

Prefer a minimal dependency footprint.

If using `requests`:

- Use `requests.Session`.
- Configure Basic Auth once on the session.
- Configure TLS verification and timeouts explicitly.
- Ensure the dependency is available in the UAC execution environment or package/vendor it according to the existing Stonebranch Universal Task build pattern.

Do not require a heavyweight SOAP client such as `zeep` unless there is a clear packaging reason. The task only needs two operations and can construct/parse the SOAP messages directly.

### 14.3 Secrets

Never log:

- password
- Authorization header
- full SOAP requests containing `<password>`
- UAC credential object internals

Redaction helper functions should be unit tested.

### 14.4 Cancellation

MVP does not need to call Oracle `cancelSchedule`.

If the UAC task process is terminated, it may leave the already submitted Publisher job running. Document this behavior.

A future version may implement UAC cancellation by calling Oracle's `cancelSchedule` operation.

---

## 15. UAC Task Outputs

At minimum, expose the following as task output/status information using the Universal Task conventions available in the implementation repository:

| Output | Description |
|---|---|
| `Scheduled Job ID` | Job ID returned by `scheduleReport`. |
| `Final Status` | Raw final `JobStatus.jobStatus` value returned by Oracle. |
| `Status Message` | Oracle `JobStatus.message`, when present. |
| `Elapsed Seconds` | Time from successful submission response until terminal status. |
| `Report Path` | Submitted Publisher catalog path. |

The scheduled Job ID is especially important for troubleshooting and must be available even when polling later fails.

---

## 16. Logging Requirements

### 16.1 Normal logging

Log:

- target ScheduleService host/path
- report absolute path
- generated/provided job name
- number of report parameters, not necessarily every value
- successful submission and scheduled Job ID
- status transitions
- final status
- elapsed time
- errors

Example:

```text
Submitting Oracle Publisher report /Custom/Financials/Example.xdo
Oracle Publisher scheduled Job ID: 123456
Job 123456 status changed: Scheduled -> Running
Job 123456 status changed: Running -> Success
Oracle Publisher job 123456 completed successfully in 42s
```

### 16.2 Debug logging

Debug logging may include:

- HTTP status code
- response headers excluding authentication/security-sensitive headers
- sanitized/truncated SOAP response
- normalized status decision

Never include the password.

---

## 17. Validation Requirements

Fail before calling Oracle when:

- Schedule Service URL is empty.
- URL is not HTTP/HTTPS.
- Username is empty.
- Password is empty.
- Report Absolute Path is empty.
- Report Parameters is not valid JSON.
- Report Parameters is not a JSON object.
- Poll Interval is less than 1.
- Maximum Wait Seconds is less than Poll Interval.
- Timeouts are non-positive.
- Unknown Status Retry Count is negative.

Recommended report-path validation:

- Warn or fail if path does not end in `.xdo`.
- Do not URL-encode the catalog path inside the SOAP XML; it is an XML string value.

---

## 18. Error Messages

Errors must be operator-friendly.

Examples:

### Authentication

```text
Oracle Publisher authentication failed (HTTP 401) for https://host/.../ScheduleService.
```

### Authorization

```text
Oracle Publisher authorization failed (HTTP 403). Verify that the Fusion user can access the report and Publisher web service.
```

### SOAP fault

```text
Oracle Publisher scheduleReport returned a SOAP Fault: <faultstring>.
```

### Missing Job ID

```text
Oracle Publisher scheduleReport returned no scheduled Job ID.
```

### Failed Publisher job

```text
Oracle Publisher job 123456 ended with status 'Failed': <Oracle message>.
```

### Poll timeout

```text
Timed out after 3600 seconds waiting for Oracle Publisher job 123456. Last status: 'Running'.
```

### Invalid status response

```text
Oracle Publisher returned an unrecognized status 'XYZ' for job 123456 for 3 consecutive polls.
```

---

## 19. Acceptance Criteria

The implementation is complete when all of the following are true.

### AC-01: Successful submission

Given valid credentials and a valid report path, the Universal Task calls `scheduleReport`, captures the returned Job ID, and displays/exposes it.

### AC-02: Successful asynchronous completion

Given a submitted job whose statuses progress from `Scheduled` to `Running` to `Success`, the task polls and finishes successfully.

### AC-03: Older success wording

If Oracle returns `Completed` or `Done`, the task also finishes successfully.

### AC-04: Publisher failure

If Oracle returns `Failed`, `Error`, `Output has Error`, `Delivery has Error`, `Update Status has Error`, `Canceled`, `Deleted`, `Skipped`, or `Suspended`, the task stops polling and fails.

### AC-05: Waiting state

If Oracle returns `Waiting`, the task continues polling.

### AC-06: SOAP fault on submission

If `scheduleReport` returns a SOAP Fault, the task fails and reports the fault without printing credentials.

### AC-07: SOAP fault during poll

If `getScheduledReportStatus` returns a non-transient SOAP Fault, the task fails and includes the scheduled Job ID.

### AC-08: HTTP authentication error

If the endpoint returns HTTP 401, the task fails immediately with an authentication-specific message.

### AC-09: Poll timeout

If no terminal status is reached before `Maximum Wait Seconds`, the task fails and reports Job ID and last known status.

### AC-10: Parameters

Single-value and array-valued JSON report parameters are converted to the Oracle `ParamNameValues` SOAP structure correctly.

### AC-11: Special XML characters

A report parameter containing characters such as:

```text
A&B <test> "quoted"
```

is transmitted as valid XML and recovered by the server as the original value.

### AC-12: Secret protection

No test, normal log, debug log, exception, or UAC task output contains the configured password or Basic Authorization value.

### AC-13: No unsafe submit retry

An ambiguous timeout/connection loss during `scheduleReport` does not automatically resubmit and create a possible duplicate job.

### AC-14: Configurable endpoint

The same task can run against another Fusion pod by changing only connection/task fields; no code change is required.

---

## 20. Unit Test Requirements

Mock HTTP/SOAP responses. Do not require a live Oracle environment for unit tests.

At minimum test:

1. Parse `scheduleReportReturn`.
2. Parse `JobStatus` fields.
3. SOAP namespace prefixes different from request prefixes.
4. SOAP Fault parsing.
5. `Success`.
6. `Completed`.
7. `Done`.
8. `Running`.
9. `Scheduled`.
10. `Waiting`.
11. `Failed`.
12. `Output has Error`.
13. `Delivery has Error`.
14. `Suspended`.
15. Unknown status retry threshold.
16. Maximum-wait timeout.
17. Parameter JSON single values.
18. Parameter JSON multi-values.
19. XML escaping.
20. Password redaction.
21. HTTP 401/403.
22. HTTP 500 during poll with bounded retry.
23. Missing schedule Job ID.
24. Returned JobStatus Job ID mismatch.

---

## 21. Integration Test Requirements

Against a non-production Fusion pod:

### Test A — minimal report

Use a simple custom `.xdo` report with no parameters.

Expected:

```text
scheduleReport -> Job ID -> Scheduled/Running -> Success
```

### Test B — report parameters

Use a report with at least:

- one text parameter
- one numeric parameter
- one date parameter
- one multi-select parameter if available

Verify Publisher receives the expected values.

### Test C — invalid report path

Submit a nonexistent `.xdo` path.

Expected: SOAP/application failure is surfaced clearly.

### Test D — invalid credential

Expected: authentication/access failure; password is not logged.

### Test E — long-running report

Verify polling lasts longer than multiple poll intervals and completes without duplicate submission.

### Test F — UAC timeout behavior

Set a short Maximum Wait Seconds and verify task failure includes the Oracle Job ID and last status.

---

## 22. Suggested MVP User Experience

Example UAC fields:

```text
Connection
  Schedule Service URL
  Credentials
  Verify TLS Certificate

Report
  Report Absolute Path
  Report Parameters (JSON)
  Output Format
  Template

Options
  Job Name
  Job Description
  Save Data
  Save Output
  Bursting
  Job Locale
  Job Time Zone

Polling
  Poll Interval Seconds
  Maximum Wait Seconds
```

The common/simple user flow should require only:

```text
Schedule Service URL
Credentials
Report Absolute Path
Report Parameters (optional)
```

Everything else should have safe defaults.

---

## 23. Example End-to-End Scenario

Input:

```text
Schedule Service URL:
https://icbpjb-dev3.fa.ocs.oraclecloud.com/xmlpserver/services/v2/ScheduleService

Report Absolute Path:
/Custom/Financials/UAC Test/UAC Test Report.xdo

Report Parameters:
{
  "P_LEDGER_ID": "300000001",
  "P_FROM_DATE": "2026-08-01",
  "P_TO_DATE": "2026-08-27"
}

Output Format:
pdf

Poll Interval:
10

Maximum Wait:
1800
```

Expected flow:

```text
1. Validate input.
2. Build SOAP scheduleReport request.
3. POST request using HTTPS + Basic Auth and SOAP body userID/password.
4. Receive scheduleReportReturn = 123456.
5. Store/output Job ID 123456.
6. Wait 10 seconds.
7. Call getScheduledReportStatus(123456).
8. Receive Scheduled.
9. Wait 10 seconds.
10. Receive Running.
11. Wait 10 seconds.
12. Receive Success.
13. Return UAC success with:
    Scheduled Job ID = 123456
    Final Status = Success
    Status Message = ...
```

---

## 24. Implementation Decisions Claude Must Preserve

When generating the Universal Task, do not change these design decisions without an explicit reason:

1. Use the Fusion Publisher **`v2/ScheduleService`** endpoint supplied/configured by the user.
2. Use **`scheduleReport`**, not synchronous `runReport`.
3. Capture the returned scheduled **Job ID**.
4. Poll **`getScheduledReportStatus`**.
5. Send the Oracle username/password in the SOAP body for these stateless `v2` methods.
6. Support HTTP Basic Authentication as the first transport authentication mode.
7. Never log credentials.
8. Treat report execution as asynchronous.
9. Do not retry ambiguous report submission automatically.
10. Normalize multiple Oracle status vocabularies.
11. Keep Publisher recurrence out of MVP; UAC scheduling controls repetition.
12. Keep report-output retrieval out of MVP.
13. Use configurable endpoint/timeout/polling settings.
14. Build and parse XML safely.
15. Provide unit tests with mocked SOAP responses.

---

## 25. Oracle Source References

### Primary Oracle documentation

1. **Oracle Analytics Publisher Developer's Guide — Publisher ScheduleService**  
   https://docs.oracle.com/en/cloud/paas/analytics-cloud/acspd/publisher-scheduleservice.html

2. **`scheduleReport()` Method** — Oracle documents the `ScheduleRequest`, `userID`, and `password` parameters and states that the method returns a Job ID.  
   https://docs.oracle.com/en/cloud/paas/analytics-cloud/acspd/to_schedulereport_method.html

3. **`getScheduledReportStatus()` Method** — Oracle documents the scheduled Job ID, `userID`, and `password` parameters and `JobStatus` return type.  
   https://docs.oracle.com/en/cloud/paas/analytics-cloud/acspd/to_getscheduledreportstatus_method.html

4. **`ScheduleRequest` data type** — fields including report request, locale/time zone, save options, bursting, scheduling, and job name/description.  
   https://docs.oracle.com/en/cloud/paas/analytics-cloud/acspd/to_schedulerequest.html

5. **`ReportRequest` data type** — report path, output format, template, parameters, locale/time zone, cache behavior, etc.  
   https://docs.oracle.com/en/cloud/paas/analytics-cloud/acspd/to_reportrequest.html

6. **`JobStatus` data type** — `jobID`, `jobStatus`, and `message`.  
   https://docs.oracle.com/en/cloud/paas/analytics-cloud/acspd/to_jobstatus.html

7. **`ParamNameValue` data type** — parameter name, values, data type, multi-value behavior.  
   https://docs.oracle.com/en/cloud/paas/analytics-cloud/acspd/to_paramnamevalue.html

8. **`ParamNameValues` data type**  
   https://docs.oracle.com/en/cloud/paas/analytics-cloud/acspd/to_paramnamevalues.html

9. **Valid `attributeFormat` values**  
   https://docs.oracle.com/en/cloud/paas/analytics-cloud/acspd/to_values_for_attributeformat.html

10. **Accessing Publisher WSDLs** — lists `v2/ScheduleService`.  
    https://docs.oracle.com/en/cloud/paas/analytics-cloud/acspd/accessing-wsdls.html

11. **Oracle Fusion Applications BI Publisher Report Services from Oracle Integration** — distinguishes public Publisher services (including `v2/ScheduleService`) that expect credentials in the SOAP payload/body from protected services.  
    https://docs.oracle.com/en/cloud/paas/application-integration/soap-adapter/call-oracle-fusion-applications-business-intelligence-publisher-report-services.html

12. **Authenticating Web Services** — current Oracle Analytics Publisher authentication documentation; useful for future OAuth support and for understanding that authentication can depend on environment configuration.  
    https://docs.oracle.com/en/cloud/paas/analytics-cloud/acspd/authenticating-web-services.html

### Oracle community / Oracle-hosted supporting information

13. **ScheduleService SOAP — Oracle Analytics Community**  
    Oracle response lists `getScheduledReportStatus` statuses including Running, Success, Failed, Cancelling, Canceled, Output has Error, Delivery has Error, Update Status has Error, Deleted, Scheduled, Suspended, and Skipped; an Oracle response also identifies `W` as Waiting.  
    https://community.oracle.com/products/oracleanalytics/discussion/20518/scheduleservice-soap

14. **BI Publisher ScheduleService v2 `scheduleReport` — Oracle Analytics Community**  
    Contains a representative `v2` SOAP payload with `reportRequest`, `parameterNameValues`, `reportAbsolutePath`, save options, `startDate`, `userID`, and `password`. The accepted update reports an Oracle SR response concerning recurring schedules through this web-service scenario.  
    https://community.oracle.com/products/oracleanalytics/discussion/19401/bi-publisher-scheduleservice-v2-schedulereport

---

## 26. Notes About Source Authority

Use the sources in this order when implementation details conflict:

1. The **actual WSDL from the target Fusion pod**.
2. Current Oracle product documentation for the relevant `v2/ScheduleService` operation/data type.
3. Oracle Fusion-specific integration documentation.
4. Oracle-hosted community posts, especially accepted answers or responses from Oracle employees.
5. Older Oracle BI Publisher documentation only as compatibility evidence.

The target WSDL is the definitive source for:

- element names
- namespaces
- element order where enforced
- SOAP binding
- SOAPAction
- request/response wrapper names

Because the supplied Fusion WSDL may require authentication and may not be reachable from every development environment, the implementation should be easy to adjust after capturing a sanitized WSDL/request-response sample from the target pod.

---

## 27. Definition of Done

The deliverable should include:

- Python source implementing the Universal Task behavior.
- UAC Universal Task/template definition needed by the existing Stonebranch repository/build pattern.
- Secure credential fields.
- Configurable ScheduleService endpoint.
- JSON report-parameter support.
- Asynchronous `scheduleReport` + `getScheduledReportStatus` implementation.
- Status normalization.
- Bounded polling.
- Safe error handling and secret redaction.
- Unit tests.
- README with setup, inputs, outputs, examples, and Oracle references.
- A sample sanitized SOAP request/response fixture set.
- No embedded customer credentials, host-specific secrets, or hard-coded Fusion pod.
