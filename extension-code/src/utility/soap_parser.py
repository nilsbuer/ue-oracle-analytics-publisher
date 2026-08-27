"""
SOAP Response Parser for Oracle Analytics Publisher v2/ScheduleService.

Parses Oracle SOAP responses using namespace-aware XML parsing without
relying on specific namespace prefixes. Detects SOAP Fault elements and
extracts result payloads for scheduleReport and getScheduledReportStatus.
"""
import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Optional

from exceptions import OracleParseError

logger = logging.getLogger("UNV")

# XML namespaces
_NS_ENVELOPE = "http://schemas.xmlsoap.org/soap/envelope/"
_NS_ORACLE = "http://xmlns.oracle.com/oxp/service/v2"


@dataclass
class SoapFault:
    """Structured representation of a SOAP Fault element.

    Attrs:
        faultcode: Fault code string (e.g., ``soap:Server``).
        faultstring: Human-readable fault description.
        detail: Optional fault detail text.
    """
    faultcode: str
    faultstring: str
    detail: str


@dataclass
class ScheduledReportStatus:
    """Parsed payload from a getScheduledReportStatusReturn element.

    Attrs:
        job_id: Oracle Job ID returned by the status response.
        job_status: Raw job status string as returned by Oracle.
        message: Oracle message field; empty string when absent.
    """
    job_id: str
    job_status: str
    message: str


def _find_by_local_name(root: ET.Element, local_name: str) -> Optional[ET.Element]:
    """Recursively search the element tree for a tag with the given local name.

    Namespace prefixes are ignored; only the local part of the qualified tag
    name (``{ns}local``) is matched.

    Args:
        root: Root element to search within.
        local_name: The local tag name to match.

    Returns:
        The first matching element, or None if not found.
    """
    for element in root.iter():
        tag = element.tag
        # Strip namespace: "{ns}local" → "local"
        local = tag.split("}", 1)[1] if "}" in tag else tag
        if local == local_name:
            return element
    return None


def _find_in_ns(
    root: ET.Element, local_name: str, namespace: str
) -> Optional[ET.Element]:
    """Search the element tree for a tag with the given local name in a namespace.

    Args:
        root: Root element to search within.
        local_name: Local tag name.
        namespace: XML namespace URI.

    Returns:
        The first matching element, or None if not found.
    """
    qualified = "{%s}%s" % (namespace, local_name)
    return root.find(".//" + qualified)


def parse_soap_response(response_bytes: bytes) -> ET.Element:
    """Parse a raw SOAP response byte string into an ElementTree root.

    Args:
        response_bytes: Raw HTTP response body bytes.

    Returns:
        The parsed XML root element.

    Raises:
        OracleParseError: When the response bytes cannot be parsed as XML.
    """
    try:
        root = ET.fromstring(response_bytes)
        logger.debug("SOAP response parsed successfully")
        return root
    except ET.ParseError as exc:
        logger.error("Failed to parse SOAP response XML: %s", str(exc))
        raise OracleParseError(
            "Malformed XML in Oracle SOAP response: %s" % str(exc)
        ) from exc
    except Exception as exc:
        logger.error("Unexpected error parsing SOAP response: %s", str(exc))
        raise OracleParseError(
            "Unexpected error parsing Oracle SOAP response: %s" % str(exc)
        ) from exc


def detect_fault(root: ET.Element) -> Optional[SoapFault]:
    """Detect and extract a SOAP Fault element from the parsed response.

    Searches the entire element tree for a ``Fault`` element regardless of
    namespace prefix or envelope structure.

    Args:
        root: Parsed XML root element.

    Returns:
        A :class:`SoapFault` instance when a fault is found, otherwise None.
    """
    fault_el = _find_by_local_name(root, "Fault")
    if fault_el is None:
        return None

    faultcode_el = _find_by_local_name(fault_el, "faultcode")
    faultstring_el = _find_by_local_name(fault_el, "faultstring")
    detail_el = _find_by_local_name(fault_el, "detail")

    faultcode = (faultcode_el.text or "") if faultcode_el is not None else ""
    faultstring = (faultstring_el.text or "") if faultstring_el is not None else ""
    detail = (detail_el.text or "") if detail_el is not None else ""

    logger.debug(
        "SOAP Fault detected: faultcode=%s, faultstring=%s", faultcode, faultstring
    )
    return SoapFault(faultcode=faultcode, faultstring=faultstring, detail=detail)


def parse_schedule_report_return(root: ET.Element) -> Optional[str]:
    """Extract the Job ID from a scheduleReport SOAP response.

    Locates the ``scheduleReportReturn`` element within the Oracle namespace
    and returns its text content as the Job ID string.

    Args:
        root: Parsed XML root element of the scheduleReport response.

    Returns:
        The Job ID string, or None if the element is absent or its text is empty.
    """
    el = _find_in_ns(root, "scheduleReportReturn", _NS_ORACLE)
    if el is None:
        logger.debug("scheduleReportReturn element not found in response")
        return None

    job_id = (el.text or "").strip()
    if not job_id:
        logger.debug("scheduleReportReturn element is empty")
        return None

    logger.debug("Extracted scheduleReportReturn Job ID: %s", job_id)
    return job_id


def parse_scheduled_report_status_return(
    root: ET.Element,
) -> ScheduledReportStatus:
    """Extract job status fields from a getScheduledReportStatus SOAP response.

    Locates the ``getScheduledReportStatusReturn`` element within the Oracle
    namespace and extracts child elements ``jobID``, ``jobStatus``, and
    ``message``.

    Args:
        root: Parsed XML root element of the getScheduledReportStatus response.

    Returns:
        A :class:`ScheduledReportStatus` with ``job_id``, ``job_status``, and
        ``message`` fields. ``message`` defaults to an empty string when absent.

    Raises:
        OracleParseError: When the ``getScheduledReportStatusReturn`` element
            or required child elements are absent from the response.
    """
    return_el = _find_in_ns(root, "getScheduledReportStatusReturn", _NS_ORACLE)
    if return_el is None:
        logger.error("getScheduledReportStatusReturn element not found in response")
        raise OracleParseError(
            "getScheduledReportStatusReturn element absent from Oracle status response"
        )

    job_id_el = _find_in_ns(return_el, "jobID", _NS_ORACLE)
    job_status_el = _find_in_ns(return_el, "jobStatus", _NS_ORACLE)
    message_el = _find_in_ns(return_el, "message", _NS_ORACLE)

    if job_id_el is None:
        logger.error("jobID element absent from getScheduledReportStatusReturn")
        raise OracleParseError(
            "jobID element absent from Oracle getScheduledReportStatusReturn"
        )
    if job_status_el is None:
        logger.error("jobStatus element absent from getScheduledReportStatusReturn")
        raise OracleParseError(
            "jobStatus element absent from Oracle getScheduledReportStatusReturn"
        )

    job_id = (job_id_el.text or "").strip()
    job_status = (job_status_el.text or "").strip()
    message = (message_el.text or "").strip() if message_el is not None else ""

    logger.debug(
        "Parsed getScheduledReportStatusReturn: job_id=%s, job_status=%s",
        job_id,
        job_status,
    )
    return ScheduledReportStatus(job_id=job_id, job_status=job_status, message=message)
