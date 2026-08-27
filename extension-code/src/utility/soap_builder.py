"""
SOAP XML Builder for Oracle Analytics Publisher v2/ScheduleService.

Constructs namespace-correct SOAP 1.1 envelope XML using xml.etree.ElementTree.
All string values are XML-escaped by ElementTree. Optional fields are only
included when their values are non-empty.
"""
import logging
import xml.etree.ElementTree as ET
from typing import Any

logger = logging.getLogger("UNV")

# XML namespaces
_NS_ENVELOPE = "http://schemas.xmlsoap.org/soap/envelope/"
_NS_ORACLE = "http://xmlns.oracle.com/oxp/service/v2"

# Register namespace prefixes for readable serialization
ET.register_namespace("soapenv", _NS_ENVELOPE)
ET.register_namespace("v2", _NS_ORACLE)

# Qualified tag helpers
_SOAPENV = "{%s}" % _NS_ENVELOPE
_V2 = "{%s}" % _NS_ORACLE


def _envelope() -> tuple[ET.Element, ET.Element]:
    """Create a SOAP envelope root and body element.

    Returns:
        Tuple of (envelope, body) elements.
    """
    envelope = ET.Element(f"{_SOAPENV}Envelope")
    body = ET.SubElement(envelope, f"{_SOAPENV}Body")
    return envelope, body


def _text(parent: ET.Element, tag: str, value: str) -> ET.Element:
    """Append a v2-namespaced child element with text content.

    Args:
        parent: Parent element.
        tag: Local tag name (no namespace prefix).
        value: Text content.

    Returns:
        The created child element.
    """
    child = ET.SubElement(parent, f"{_V2}{tag}")
    child.text = value
    return child


def build_schedule_report_envelope(
    report_absolute_path: str,
    user_id: str,
    password: str,
    bypass_cache: bool,
    user_job_name: str,
    user_job_desc: str,
    save_data: bool,
    save_output: bool,
    bursting: bool,
    public_schedule: bool,
    parameters: dict[str, Any],
    output_format: str = "",
    report_template: str = "",
    report_locale: str = "",
    ui_locale: str = "",
    report_timezone: str = "",
    job_locale: str = "",
    job_timezone: str = "",
) -> bytes:
    """Build a scheduleReport SOAP 1.1 envelope.

    Constructs the full SOAP envelope for the Oracle v2/ScheduleService
    scheduleReport operation. The v2 WSDL defines the top-level parameter
    sequence as: userID, password, reportRequest, scheduleRequest — credentials
    are emitted first, before the request complex types. Optional string fields
    are omitted when empty. The ``parameters`` dict maps parameter names to
    their values; ``None`` values are skipped entirely; scalar values produce
    one ``<v2:item>`` element; list values produce one ``<v2:item>`` per entry.

    Args:
        report_absolute_path: Oracle Publisher catalog path for the report.
        user_id: Oracle username for SOAP body authentication.
        password: Oracle password for SOAP body authentication.
        bypass_cache: Maps to ``ReportRequest.byPassCache``.
        user_job_name: Maps to ``ScheduleRequest.userJobName``.
        user_job_desc: Maps to ``ScheduleRequest.userJobDesc``.
        save_data: Maps to ``ScheduleRequest.saveDataOption``.
        save_output: Maps to ``ScheduleRequest.saveOutputOption``.
        bursting: Maps to ``ScheduleRequest.scheduleBurstingOption``.
        public_schedule: Maps to ``ScheduleRequest.schedulePublicOption``.
        parameters: Report parameters as name-to-value mapping. None values
            are omitted. Scalars produce a single item; lists produce multiple.
        output_format: Optional ``ReportRequest.attributeFormat`` value.
        report_template: Optional ``ReportRequest.attributeTemplate`` value.
        report_locale: Optional ``ReportRequest.attributeLocale`` value.
        ui_locale: Optional ``ReportRequest.attributeUILocale`` value.
        report_timezone: Optional ``ReportRequest.attributeTimeZone`` value.
        job_locale: Optional ``ScheduleRequest.jobLocale`` value.
        job_timezone: Optional ``ScheduleRequest.jobTZ`` value.

    Returns:
        UTF-8 encoded byte string of the serialized SOAP envelope.
    """
    logger.debug(
        "Building scheduleReport SOAP envelope: report_path=%s, job_name=%s, "
        "param_count=%d",
        report_absolute_path,
        user_job_name,
        sum(1 for v in parameters.values() if v is not None),
    )

    envelope, body = _envelope()
    operation = ET.SubElement(body, f"{_V2}scheduleReport")

    # --- credentials (must precede reportRequest / scheduleRequest per v2 WSDL) ---
    _text(operation, "userID", user_id)
    _text(operation, "password", password)

    # --- reportRequest ---
    report_req = ET.SubElement(operation, f"{_V2}reportRequest")
    _text(report_req, "reportAbsolutePath", report_absolute_path)

    # parameterNameValues — omit entirely when no non-null parameters
    non_null_params = {k: v for k, v in parameters.items() if v is not None}
    if non_null_params:
        param_name_values = ET.SubElement(report_req, f"{_V2}parameterNameValues")
        for name, value in non_null_params.items():
            item = ET.SubElement(param_name_values, f"{_V2}item")
            _text(item, "name", name)
            values_el = ET.SubElement(item, f"{_V2}values")
            entries = value if isinstance(value, list) else [value]
            for entry in entries:
                _text(values_el, "item", str(entry))

    # Optional report attributes
    if output_format:
        _text(report_req, "attributeFormat", output_format)
    if report_template:
        _text(report_req, "attributeTemplate", report_template)
    if report_locale:
        _text(report_req, "attributeLocale", report_locale)
    if ui_locale:
        _text(report_req, "attributeUILocale", ui_locale)
    if report_timezone:
        _text(report_req, "attributeTimeZone", report_timezone)

    _text(report_req, "byPassCache", str(bypass_cache).lower())

    # --- scheduleRequest ---
    sched_req = ET.SubElement(operation, f"{_V2}scheduleRequest")
    _text(sched_req, "userJobName", user_job_name)
    _text(sched_req, "userJobDesc", user_job_desc)
    _text(sched_req, "saveDataOption", str(save_data).lower())
    _text(sched_req, "saveOutputOption", str(save_output).lower())
    _text(sched_req, "scheduleBurstingOption", str(bursting).lower())
    _text(sched_req, "schedulePublicOption", str(public_schedule).lower())
    if job_locale:
        _text(sched_req, "jobLocale", job_locale)
    if job_timezone:
        _text(sched_req, "jobTZ", job_timezone)

    xml_bytes = ET.tostring(envelope, encoding="utf-8", xml_declaration=True)
    logger.debug("scheduleReport envelope built (%d bytes)", len(xml_bytes))
    return xml_bytes


def build_get_scheduled_report_status_envelope(
    job_id: str,
    user_id: str,
    password: str,
) -> bytes:
    """Build a getScheduledReportStatus SOAP 1.1 envelope.

    Args:
        job_id: The Oracle scheduled Job ID to poll.
        user_id: Oracle username for SOAP body authentication.
        password: Oracle password for SOAP body authentication.

    Returns:
        UTF-8 encoded byte string of the serialized SOAP envelope.
    """
    logger.debug("Building getScheduledReportStatus SOAP envelope: job_id=%s", job_id)

    envelope, body = _envelope()
    operation = ET.SubElement(body, f"{_V2}getScheduledReportStatus")
    _text(operation, "jobID", job_id)
    _text(operation, "userID", user_id)
    _text(operation, "password", password)

    xml_bytes = ET.tostring(envelope, encoding="utf-8", xml_declaration=True)
    logger.debug(
        "getScheduledReportStatus envelope built (%d bytes)", len(xml_bytes)
    )
    return xml_bytes
