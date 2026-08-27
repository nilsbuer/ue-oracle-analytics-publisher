"""
Utility modules for the Oracle Analytics Publisher Asynchronous Report Scheduler extension.

Modules:
    soap_builder       — Build SOAP 1.1 envelope XML for Oracle v2/ScheduleService operations
    soap_parser        — Parse Oracle SOAP responses; detect faults and extract results
    http_client        — Manage requests.Session lifecycle and SOAP request execution
    status_classifier  — Normalize and classify raw Oracle job status strings
    output_formatter   — STDOUT progressive log lines and summary table rendering
"""
