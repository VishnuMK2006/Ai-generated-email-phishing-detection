import email
from email import policy
import re
import pandas as pd
import numpy as np
import dateutil.parser
from datetime import datetime, timezone
import pickle

def extract_features_from_raw_email(raw_email: str) -> dict:
    """
    Parses a single raw email header/message string and extracts 
    Temporal, Network, Topological, and Structural features.
    """
    try:
        msg = email.message_from_string(raw_email, policy=policy.default)
    except Exception:
        msg = email.message_from_string("", policy=policy.default)

    features = {}

    # ==========================================
    # 1. TEMPORAL FEATURES
    # ==========================================
    date_header_str = msg.get("Date")
    date_header_ts = None
    if date_header_str:
        try:
            date_str_clean = re.sub(r'\s*\([A-Z]{3,4}\)$', '', str(date_header_str).strip())
            dt = dateutil.parser.parse(date_str_clean)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            date_header_ts = dt.timestamp()
        except Exception:
            date_header_ts = None
            
    # We rely on negative_latency_anomaly instead of the exact date timestamp

    # Extract Received headers
    received_headers = msg.get_all("Received") or []
    if not received_headers:
        received_matches = re.findall(
            r'Received:\s*(.*?)(?=(?:Received:|X-|Date:|From:|To:|Subject:|Message-Id:|Return-Path:|Content-Type:|MIME-Version:|User-Agent:|$))', 
            raw_email, re.IGNORECASE
        )
        received_headers = received_matches

    received_timestamps = []
    for r in received_headers:
        if ";" in r:
            date_part = r.rsplit(";", 1)[-1].strip()
            date_part_clean = re.sub(r'\s*\([A-Z]{3,4}\)$', '', date_part)
            try:
                dt = dateutil.parser.parse(date_part_clean)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                received_timestamps.append(dt.timestamp())
            except Exception:
                pass

    features["received_timestamps_count"] = len(received_timestamps)
    
    # Inter-hop delays & Latency Anomalies
    chrono_timestamps = list(reversed(received_timestamps))
    delays = []
    has_negative_latency = False

    if date_header_ts and chrono_timestamps:
        first_hop_delay = chrono_timestamps[0] - date_header_ts
        delays.append(first_hop_delay)
        if first_hop_delay < 0:
            has_negative_latency = True

    for i in range(len(chrono_timestamps) - 1):
        delay = chrono_timestamps[i+1] - chrono_timestamps[i]
        delays.append(delay)
        if delay < 0:
            has_negative_latency = True

    features["negative_latency_anomaly"] = int(has_negative_latency)

    # ==========================================
    # 2. NETWORK FEATURES
    # ==========================================
    ipv4_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
    extracted_ips = set()
    
    for r in received_headers:
        for ip in re.findall(ipv4_pattern, str(r)):
            extracted_ips.add(ip)

    spf_header = msg.get("Received-SPF", "")
    for ip in re.findall(ipv4_pattern, str(spf_header)):
        extracted_ips.add(ip)

    features["ip_address_count"] = len(extracted_ips)

    # Extract Domains to calculate relations
    def extract_domain(email_str):
        if not email_str:
            return ""
        match = re.search(r'[\w\.-]+@([\w\.-]+)', str(email_str))
        return match.group(1).lower() if match else ""

    from_dom = extract_domain(msg.get("From", ""))
    msg_id = msg.get("Message-ID", "")
    msg_dom = ""
    if "@" in str(msg_id):
        msg_dom = str(msg_id).split("@")[-1].strip(">").strip().lower()

    # ==========================================
    # 3. TOPOLOGICAL FEATURES
    # ==========================================
    features["hop_count"] = len(received_headers)
    features["path_length"] = len(received_headers)
    
    unusual_indicators = ["127.0.0.1", "localhost", "::1", "10.", "192.168.", "172.16."]
    has_unusual_relay = any(
        any(ind in str(r).lower() for ind in unusual_indicators)
        for r in received_headers
    )
    features["unusual_relay_indicator"] = int(has_unusual_relay)

    # Authentication Results
    auth_matches = re.findall(r'(?:Authentication-Results|ARC-Authentication-Results):\s*([^\n\r]+)', raw_email, re.IGNORECASE)
    auth_str = " ".join(auth_matches).lower()
    spf_pass = "spf=pass" in auth_str
    dkim_pass = "dkim=pass" in auth_str

    # ==========================================
    # 4. STRUCTURAL FEATURES
    # ==========================================
    # Domain Consistency Check
    base_match = bool(from_dom and msg_dom and (from_dom in msg_dom or msg_dom in from_dom))
    
    if spf_pass and dkim_pass:
        features["msg_id_matches_from"] = 1
    else:
        features["msg_id_matches_from"] = int(base_match)
    features["has_x_mailer"] = int("x-mailer:" in raw_email.lower())
    features["has_user_agent"] = int("user-agent:" in raw_email.lower())

    has_plain, has_html = False, False
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/plain":
                has_plain = True
            elif ctype == "text/html":
                has_html = True
    else:
        ctype = msg.get_content_type()
        if ctype == "text/plain":
            has_plain = True
        elif ctype == "text/html":
            has_html = True

    features["has_plain_text"] = int(has_plain or ("text/plain" in raw_email.lower()))
    features["has_html_text"] = int(has_html or ("text/html" in raw_email.lower()))
    features["is_multipart"] = int(msg.is_multipart() or ("multipart/" in raw_email.lower()))

    header_names = re.findall(r'\b([A-Z][a-zA-Z0-9-]*):', raw_email)
    features["total_header_count"] = len(header_names) if header_names else len(msg.keys())
    features["received_header_count"] = len(received_headers)

    return features
