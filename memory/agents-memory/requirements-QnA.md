# Requirements Completeness Assessment

The requirements for the Oracle Analytics Publisher Universal Task are exceptionally detailed and well-structured. They specify exact SOAP XML request/response structures, complete field definitions with types, defaults, and validation rules, a comprehensive status normalization vocabulary covering 15+ Oracle-documented status values, security constraints, operator-friendly error message templates, 14 acceptance criteria, 24 unit test cases, and 6 integration test scenarios.

**Classification: High Detail**

What the requirements establish clearly and completely:
- Target SOAP service (`v2/ScheduleService`), operation pair (`scheduleReport` + `getScheduledReportStatus`), and XML namespace
- Full asynchronous execution pattern with bounded polling and monotonic-clock timing
- All Connection, Report, Schedule Request, and Polling input fields — with types, required/optional status, and safe defaults
- Authentication architecture (HTTP Basic Auth + SOAP credential elements in body, secrets never logged)
- Status vocabulary normalization and terminal-state mapping across multiple Oracle status sets
- HTTP retry semantics, including the explicit no-retry rule for ambiguous `scheduleReport` submissions
- XML parsing requirements (namespace-aware, prefix-independent, no external entity expansion, no regex)
- Five output fields with descriptions
- Error message templates for all major failure modes

The questions below focus on genuine design decisions and gaps not addressed by the requirements, specifically: module selection (where requirements leave the choice open), one field type ambiguity, report parameter input style, re-run behavior (entirely unaddressed), STDOUT presentation, and poll transport retry configuration.

---

# Platform Compatibility

**Platform Compatibility from Requirements**: Linux-only

Confirmed by the build environment file: OS is Linux, Architecture x86_64, and the `bdist.linux-x86_64` build directory is present. The `manylinux_2_17_x86_64` wheel compatibility rules apply. C extension modules with a confirmed `manylinux_2_17_x86_64` wheel are viable on this platform.

**Platform Compatibility Agreement**: Linux-only (x86_64 / manylinux_2_17_x86_64)

---

# Python Modules and Versions

## Researched Modules

All modules below were verified against PyPI for Python 3.11 / `manylinux_2_17_x86_64` compatibility.

**requests**
- **Module Purpose**: HTTP client for SOAP POST requests — provides Session management, Basic Auth, TLS certificate verification, and configurable connection/read timeouts. Explicitly referenced in requirements section 14.2.
- **Version**: 2.34.2
- **Type**: Pure Python

**lxml**
- **Module Purpose**: High-performance XML and HTML parser with full namespace support and XPath — alternative to Python's stdlib `xml.etree.ElementTree` for SOAP response parsing.
- **Version**: 7.0.0a1 ⚠️ **Pre-release alpha — not recommended for production**
- **Type**: C bindings (manylinux_2_17_x86_64 wheel available)

**httpx**
- **Module Purpose**: Modern synchronous and asynchronous HTTP client — alternative to `requests` with finer-grained timeout control.
- **Version**: 1.0.dev1 ⚠️ **Development pre-release — not recommended for production**
- **Type**: Pure Python

**certifi**
- **Module Purpose**: Mozilla CA certificate bundle used by `requests` (and `httpx`) for TLS certificate verification of well-known public domains such as Oracle Fusion Cloud (`*.oraclecloud.com`).
- **Version**: 2026.7.22
- **Type**: Pure Python

**tabulate**
- **Module Purpose**: Formats data as ASCII/Unicode tables for STDOUT — supports the `rounded_outline` table style recommended in the architect notes for clean terminal output.
- **Version**: 0.10.0
- **Type**: Pure Python

---

## Agreed Python Modules and Versions

*This section is a placeholder. It will be updated once all question answers are confirmed.*

| Module | Purpose | Version | Type |
|---|---|---|---|
| [Pending Q1] | HTTP client (SOAP POST, Basic Auth, TLS) | [TBD] | [TBD] |
| Python stdlib `xml.etree.ElementTree` | XML/SOAP request building and response parsing | Built-in (Python ≥ 3.11) | Pure Python |
| certifi | TLS CA certificate bundle | 2026.7.22 | Pure Python |
| [Pending Q6] | STDOUT summary table formatting | [TBD] | [TBD] |

---

# Question Rationale

Seven questions are raised. They fall into three categories:

1. **Module selection** (Q1, Q2): The requirements reference `requests` conditionally and say "use a real XML parser" without naming one — both are genuine open decisions.
2. **Field design ambiguity** (Q3, Q4): The Output Format field is typed as "Text/Choice" and Report Parameters as "Large Text / JSON" — both notations admit more than one UAC field type.
3. **Unaddressed scenarios and conventions** (Q5, Q6, Q7): Re-run behavior is entirely absent from the requirements; STDOUT format style follows the architect notes recommendation rather than an explicit requirement; poll transport retry count is mentioned but not quantified or exposed.

---

# Clarifying Questions for Requirements Refinement

## Critical Decision Path Questions

**Question 1**: Which HTTP client library should be used — `requests` or `httpx`?

- **Question Type**: Clarification on existing requirement
- **Context & Resources**: Section 14.2 references `requests` with conditional language ("If using `requests`...") and describes its session and auth configuration in detail. Two libraries were evaluated for this platform:
  - **`requests` 2.34.2** — Pure Python. The most widely deployed Python HTTP library. The requirements describe its `Session` + `HTTPBasicAuth` pattern directly. The Stonebranch architect notes cite it as "the more commonly used" of the two options. Fully covers synchronous SOAP POST with Basic Auth, explicit TLS verification, and configurable connect/read timeouts.
  - **`httpx` 1.0.dev1** — Pure Python. Supports finer-grained timeout control and async execution (not required here). However, the latest version for the target platform is a **development pre-release** (1.0.dev1), which is unsuitable for a production-grade extension.
  - References: [Requests docs](https://requests.readthedocs.io/) | [HTTPX docs](https://www.python-httpx.org/) | Architect notes — HTTPX vs REQUESTS section
- **Question Dependencies**: None
- **Recommended Answer**: `requests` 2.34.2
- **Rationale**: `requests` is explicitly referenced in the requirements and is stable. The `httpx` pre-release status makes it an unsuitable dependency for a production extension at this time.
- **Trade-offs**: `requests` provides a stable, well-documented API that precisely matches the patterns described in section 14.2. `httpx` would add per-request timeout granularity, but that level of control is not required by this synchronous, two-operation integration.
- **Requirement Impact**: None — `requests` aligns with requirements section 14.2 as written.
- **User's Answer**: `requests` 2.34.2

---

**Question 2**: Which XML library should be used for building SOAP requests and parsing SOAP responses — Python's built-in `xml.etree.ElementTree` or `lxml`?

- **Question Type**: New Discussion Topic
- **Context & Resources**: Section 13 specifies: "Use a real XML parser", "Namespace-aware", "Do not depend on prefixes", "Reject malformed XML with a clear error", "Protect against XML parser features that are unnecessary for this use case (no external entity expansion)". Two options were evaluated:
  - **Python stdlib `xml.etree.ElementTree`** — Built into Python 3.11+, no additional dependency. Fully namespace-aware: element lookup uses `{namespace_uri}localname` notation, making prefix independence straightforward. External entity expansion is not triggered by default for the operations used here. Sufficient for constructing `scheduleReport` / `getScheduledReportStatus` envelopes and parsing their simple responses.
  - **`lxml` 7.0.0a1** — C extension with a manylinux_2_17_x86_64 wheel available. Provides more descriptive parse errors, XPath support, and faster processing for large documents. However, the latest compatible version for the target platform is a **pre-release alpha** (7.0.0a1), which is unsuitable for production use.
  - References: [xml.etree.ElementTree Python docs](https://docs.python.org/3/library/xml.etree.elementtree.html) | [lxml project](https://lxml.de/)
- **Question Dependencies**: None
- **Recommended Answer**: Python stdlib `xml.etree.ElementTree`
- **Rationale**: The two SOAP operations have simple, predictable response structures: a single Job ID string and a three-field `JobStatus` object. Stdlib handles these comfortably, avoids adding a C extension dependency, and the `lxml` pre-release status rules it out in any case.
- **Trade-offs**: Stdlib parse error messages are less descriptive than lxml's, but requirements sections 7.3 and 8.2 already specify exactly what the parser must extract and what errors to surface — the description of the error at a higher level is defined in code, not left to the library. No XPath or advanced schema validation is needed.
- **Requirement Impact**: None — stdlib satisfies all XML requirements in sections 7, 8, and 13.
- **User's Answer**: Python stdlib `xml.etree.ElementTree`

---

## Essential Input/Output Questions

**Question 3**: Should the `Output Format` field be a **static choice dropdown** with Oracle's documented format codes, or a **free text field**?

- **Question Type**: Clarification on existing requirement
- **Context & Resources**: Section 5.2 marks Output Format as `"Text/Choice"` — a notation that permits either UAC field type. Oracle documents the following valid `attributeFormat` values: `pdf`, `html`, `rtf`, `excel`, `excel2000`, `xlsx`, `ppt`, `pptx`, `mhtml`, `pdfa`, `pdfx`, `pdfz`, `xslfo`, `xml`, `csv`, `text`, `flash` (17 values). The requirements also state "If omitted, allow Publisher/report defaults" and "Do not try to pre-validate every format/template combination in Python."
  - **Option A — Static Choice Field**: Dropdown listing the 17 Oracle-documented codes. Allows empty selection (`choiceAllowEmpty: true`) to use the report default. Eliminates typos; Oracle remains the authority on validity — unsupported format/template combinations still surface as clear SOAP faults.
  - **Option B — Free Text Field**: User types the format code manually. Maximum flexibility; works even if Oracle adds format codes not in the predefined list.
  - Reference: [Oracle attributeFormat values](https://docs.oracle.com/en/cloud/paas/analytics-cloud/acspd/to_values_for_attributeformat.html)
- **Question Dependencies**: None
- **Recommended Answer**: Option A — Static Choice Field with `choiceAllowEmpty: true`
- **Rationale**: Oracle's format vocabulary is documented and stable. A choice field prevents a common class of integration failure — submitting a misspelled or wrong-case format code that produces a cryptic SOAP fault. Oracle's validation remains the authority on whether a given format is valid for a specific report template, so the choice list does not reduce reliability.
- **Trade-offs**: A static list could theoretically miss a future Oracle format code, but Oracle's format set is rarely extended. Any new code would still work as a SOAP request — it would simply not appear in the dropdown. In practice this is a very low risk.
- **Requirement Impact**: Output Format field type changes from text to a Choice Field with `choiceAllowEmpty: true`. The 17 Oracle-documented format codes become the predefined choice values.
- **User's Answer**: Option A — Static Choice Field with `choiceAllowEmpty: true`

---

**Question 4**: Should `Report Parameters (JSON)` be a **Large Text Field** (user types or pastes JSON directly) or a **UAC Script Field** (user references a UAC Data Script containing the JSON)?

- **Question Type**: New Discussion Topic
- **Context & Resources**: Section 5.2 specifies "Large Text / JSON" — again a notation that admits more than one UAC field type. The architect notes identify Script Fields as the right choice for "Payloads (Like JSON/XML/SQL etc)" and "Configuration options... that require structure, hierarchy, re-usability." Two options:
  - **Option A — Large Text Field**: User types or pastes the JSON parameters directly into the task definition form. The JSON is embedded in the task. Simple and self-contained — no additional UAC entity required.
  - **Option B — UAC Script Field**: User creates a UAC Data Script (type: "Data Script") containing the JSON and references it from the task. The extension reads the script file path at runtime. Enables reuse of the same parameter set across multiple task definitions, independent version control of parameters, and separation of report configuration from task configuration.
- **Question Dependencies**: None
- **Recommended Answer**: Option A — Large Text Field
- **Rationale**: Most report executions have task-specific parameter values (date ranges, ledger IDs, business unit codes) that differ between task definitions. A Large Text field is simpler, matches the requirements notation directly, and avoids the overhead of managing UAC Data Script entities for the common case. A Script Field can be added later if reuse becomes a priority.
- **Trade-offs**: Large Text is self-contained but ties parameters to each task definition. Script Field enables reuse and version control but requires users to understand and manage UAC Data Script entities as an additional configuration step.
- **Requirement Impact**: None if Option A is selected. Requirements section 5.2 documents the field as "Large Text / JSON" which this option satisfies directly.
- **User's Answer**: Option A — Large Text Field

---

## Operational Behavior Questions

**Question 5**: If a previous task execution already obtained a Publisher Job ID (stored in the `Scheduled Job ID` output field) but the UAC task then failed during polling, should a **re-run skip `scheduleReport` and poll the existing job**, or **always submit a fresh report**?

- **Question Type**: New Discussion Topic
- **Context & Resources**: The requirements are silent on re-run behavior. In UAC, when a task instance fails, the operator can re-run it. The architect notes describe the **Resource Identifier Persistence Pattern**: output-only fields can be marked with `preserveOutputOnRerun: true`, making the field value from the previous execution available at the start of the re-run. Two options:
  - **Option A — Poll Existing Job on Re-run**: If the `Scheduled Job ID` output field is populated from a previous run, skip `scheduleReport` and go directly to polling `getScheduledReportStatus` with that Job ID. This covers the scenario where the UAC task timed out (e.g., `Maximum Wait Seconds` was too short) or suffered a transient failure during polling — the Publisher job may still be running or may have completed in Oracle.
  - **Option B — Always Fresh Submission**: Re-run always calls `scheduleReport`, submitting a new Publisher job. Simpler control flow, but creates a duplicate job in Oracle if the previous submission was successful.
- **Question Dependencies**: None
- **Recommended Answer**: Option A — Poll Existing Job when a preserved Job ID is available
- **Rationale**: Section 11.2 explicitly prohibits automatically retrying `scheduleReport` after an ambiguous failure precisely to avoid duplicate submissions. Ignoring a preserved Job ID on re-run would contradict that design principle. If the Job ID is present, the submission already succeeded — re-polling is the correct action.
- **Trade-offs**: Option A requires a small startup check for the preserved output field and appropriate logging to make the behavior transparent ("Re-run detected: polling existing Publisher job 123456"). Option B is simpler but risks creating duplicate jobs, which is directly contrary to section 11.2.
- **Requirement Impact**: The `Scheduled Job ID` output field must be configured with `preserveOutputOnRerun: true` and `fieldRestriction: "Output Only"`. The re-run polling path should include a log message indicating it is using the preserved Job ID.
- **User's Answer**: Option A — Poll Existing Job when a preserved Job ID is available

---

**Question 6**: Should the STDOUT output include a **formatted summary table** at task completion, in addition to the log lines already specified in section 16.1?

- **Question Type**: New Discussion Topic
- **Context & Resources**: Section 16.1 provides log-line examples in plain text format (e.g., `"Oracle Publisher job 123456 completed successfully in 42s"`). The architect notes recommend ASCII table format for STDOUT "when information can be printed nicely in rows or in columns using well known python libraries" and suggest `tablefmt="rounded_outline"` from the `tabulate` library. Two options:
  - **Option A — Plain Log Lines Only**: STDOUT follows exactly the logging style shown in section 16.1. Simple; no additional library required.
  - **Option B — Plain Log Lines + Final Summary Table**: Append a formatted summary table at the end of task execution using `tabulate` (0.10.0, pure Python). The table includes: Scheduled Job ID, Report Path, Final Status, Status Message, Elapsed Seconds.

    Example output (Option B):
    ```
    ╭──────────────────────┬────────────────────────────────────────────╮
    │ Scheduled Job ID     │ 123456                                     │
    │ Report Path          │ /Custom/Financials/UAC Test Report.xdo     │
    │ Final Status         │ Success                                    │
    │ Status Message       │ Completed successfully                     │
    │ Elapsed Seconds      │ 42                                         │
    ╰──────────────────────┴────────────────────────────────────────────╯
    ```

  - Reference: Architect notes — Multi-Channel Output Pattern; `tabulate` library [PyPI](https://pypi.org/project/tabulate/)
- **Question Dependencies**: None
- **Recommended Answer**: Option B — Plain Log Lines + Final Summary Table
- **Rationale**: A summary table gives operators an at-a-glance confirmation of the completed job without scrolling through log lines. The `tabulate` library is pure Python (0.10.0 stable), adds no platform constraints, and is specifically called out in the architect notes for this use case. STDOUT output size for this extension is naturally bounded (one job, one table), so database size concerns do not apply.
- **Trade-offs**: Option B adds `tabulate` as a dependency and a small amount of STDOUT output. Option A has no extra dependency. The trade-off strongly favors Option B given the bounded output size and the concrete UX improvement.
- **Requirement Impact**: If Option B is selected, add `tabulate==0.10.0` to `requirements.txt`. The five fields listed in section 15 become the table rows.
- **User's Answer**: Option B — Plain Log Lines + Final Summary Table

---

**Question 7**: Should the maximum number of transient transport retries for `getScheduledReportStatus` polls be controlled by an **environment variable** (`UE_POLL_RETRY_COUNT`), or should it be **hardcoded** as an implementation constant?

- **Question Type**: New Discussion Topic
- **Context & Resources**: Section 11.3 specifies that poll transport failures should be retried with "bounded attempts" and a "short backoff", but does not assign a specific count or expose it as an input field. The architect notes recommend environment variables for "input parameters that are not commonly tuned and/or have some sensible defaults like HTTP Client Timeouts" and specify the `UE_` prefix for custom env vars. Note: this retry count is distinct from `Unknown Status Retry Count` (section 5.4), which is already defined as an Integer Field and covers consecutive unrecognized status values — not transport-layer failures. Two options:
  - **Option A — Environment Variable `UE_POLL_RETRY_COUNT`**: Default 3. Advanced users or operators in unstable network environments can override without code changes. Follows the architect notes naming convention.
  - **Option B — Hardcoded**: Fix the retry count at 3 in the implementation. Simpler; no documentation burden for an infrequently-changed constant.
- **Question Dependencies**: None
- **Recommended Answer**: Option A — Environment Variable `UE_POLL_RETRY_COUNT` with default 3
- **Rationale**: Poll transport reliability varies by network environment and Oracle Fusion pod. An env var provides an operational escape valve for environments where transient connectivity is a known issue, without exposing a rarely-changed parameter in the task form. Default of 3 is conservative and appropriate for most environments.
- **Trade-offs**: An env var requires brief documentation. A hardcoded constant is simpler for the initial implementation. Given that this parameter affects reliability in degraded-network scenarios, the documentation cost is worth the flexibility.
- **Requirement Impact**: Requirements section 11.3 should note: "The maximum number of transient transport retry attempts for each poll request is controlled by the `UE_POLL_RETRY_COUNT` environment variable (default: 3)."
- **User's Answer**: Option A — Environment Variable `UE_POLL_RETRY_COUNT` with default 3
