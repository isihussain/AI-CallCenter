"""Tenant-scoped OIM calendar operations backed by SQLite transactions."""

import json
import re
import sqlite3
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


DEFAULTS = {
    "timezone": "Europe/Istanbul",
    "external_calendar_provider": "auto",
    "duration_minutes": 60,
    "min_duration_minutes": 5,
    "max_duration_minutes": 480,
    "buffer_minutes": 0,
    "slot_interval_minutes": 30,
    "alternative_window_minutes": 60,
    "min_notice_minutes": 60,
    "max_days_ahead": 180,
    "business_hours": {
        "mon": [["09:00", "17:00"]], "tue": [["09:00", "17:00"]],
        "wed": [["09:00", "17:00"]], "thu": [["09:00", "17:00"]],
        "fri": [["09:00", "17:00"]], "sat": [], "sun": [],
    },
    "holidays": [],
    "blocked_intervals": [],
    "staff": [],
    "service_rules": [],
    "department_rules": [],
    "cancellation_policy": {"minimum_notice_minutes": 0},
}
DAY_KEYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def settings_for(conn, tenant_id):
    row = conn.execute("SELECT config_json FROM calendar_settings WHERE tenant_id=?", (tenant_id,)).fetchone()
    config = dict(DEFAULTS)
    if row:
        try:
            supplied = json.loads(row["config_json"])
            if isinstance(supplied, dict):
                config.update(supplied)
        except (TypeError, ValueError):
            pass
    config["business_hours"] = config.get("business_hours") if isinstance(config.get("business_hours"), dict) else DEFAULTS["business_hours"]
    return config


def validate_settings(value):
    if not isinstance(value, dict):
        raise ValueError("Calendar settings must be a JSON object.")
    config = dict(DEFAULTS)
    config.update(value)
    if config.get("external_calendar_provider") not in {"auto", "internal", "google", "microsoft"}:
        raise ValueError("external_calendar_provider must be auto, internal, google or microsoft.")
    try:
        ZoneInfo(str(config["timezone"]))
    except (ZoneInfoNotFoundError, ValueError):
        raise ValueError("Choose a valid IANA time zone.") from None
    for field, low, high in (("duration_minutes", 5, 480), ("min_duration_minutes", 5, 480),
                             ("max_duration_minutes", 5, 480), ("buffer_minutes", 0, 240),
                             ("slot_interval_minutes", 5, 240), ("alternative_window_minutes", 15, 1440),
                             ("min_notice_minutes", 0, 525600), ("max_days_ahead", 1, 730)):
        try:
            config[field] = int(config[field])
        except (TypeError, ValueError):
            raise ValueError(f"{field} must be a whole number.") from None
        if not low <= config[field] <= high:
            raise ValueError(f"{field} must be between {low} and {high}.")
    if config["min_duration_minutes"] > config["max_duration_minutes"] or not config["min_duration_minutes"] <= config["duration_minutes"] <= config["max_duration_minutes"]:
        raise ValueError("Default appointment duration must be within the configured minimum and maximum.")
    def normalize_hours(hours):
        if not isinstance(hours, dict):
            raise ValueError("business_hours must map weekdays to time ranges.")
        normalized = {}
        for day in DAY_KEYS:
            ranges = hours.get(day, [])
            if not isinstance(ranges, list) or len(ranges) > 4:
                raise ValueError("Each weekday can have up to four working intervals.")
            normalized[day] = []
            for pair in ranges:
                if not isinstance(pair, list) or len(pair) != 2:
                    raise ValueError("Working intervals must contain a start and end time.")
                try:
                    start, end = (time.fromisoformat(str(part)) for part in pair)
                except ValueError:
                    raise ValueError("Working hours must use HH:MM format.") from None
                if start >= end:
                    raise ValueError("A working interval must end after it starts.")
                normalized[day].append([start.strftime("%H:%M"), end.strftime("%H:%M")])
        return normalized

    config["business_hours"] = normalize_hours(config.get("business_hours"))
    for field in ("holidays", "blocked_intervals", "staff", "service_rules", "department_rules"):
        if not isinstance(config.get(field), list) or len(config[field]) > 1000:
            raise ValueError(f"{field} must be a list with no more than 1000 entries.")
    for item in config["holidays"]:
        try:
            date.fromisoformat(str(item))
        except ValueError:
            raise ValueError("Holiday dates must use YYYY-MM-DD format.") from None
    staff_ids = set()
    for member in config["staff"]:
        if not isinstance(member, dict):
            raise ValueError("Each staff member must be a JSON object.")
        staff_id = str(member.get("id", "")).strip()
        if not staff_id or len(staff_id) > 100 or staff_id in staff_ids:
            raise ValueError("Staff IDs must be unique and contain 1 to 100 characters.")
        staff_ids.add(staff_id)
        if "business_hours" in member:
            member["business_hours"] = normalize_hours(member["business_hours"])
        if not isinstance(member.get("holidays", []), list):
            raise ValueError("Staff holidays must be a date list.")
        for holiday in member.get("holidays", []):
            try:
                date.fromisoformat(str(holiday))
            except ValueError:
                raise ValueError("Staff holiday dates must use YYYY-MM-DD format.") from None
    for block in config["blocked_intervals"]:
        if not isinstance(block, dict) or "start" not in block or "end" not in block:
            raise ValueError("Blocked intervals need start and end date-times.")
        start = localize_start(str(block["start"]), config)
        end = localize_start(str(block["end"]), config)
        if end <= start:
            raise ValueError("Blocked interval end must be after its start.")
        block_staff = str(block.get("staff_id", "")).strip()
        if block_staff and staff_ids and block_staff not in staff_ids:
            raise ValueError("Blocked interval references an unknown staff ID.")
    for field, identity in (("service_rules", "service"), ("department_rules", "department")):
        seen = set()
        for rule in config[field]:
            if not isinstance(rule, dict):
                raise ValueError(f"Each {identity} rule must be a JSON object.")
            key = str(rule.get(identity, "")).strip()
            if not key or len(key) > 200 or key in seen:
                raise ValueError(f"{identity.title()} rules need unique names of 1 to 200 characters.")
            seen.add(key)
            for numeric, low, high in (("duration_minutes", 5, 480), ("min_duration_minutes", 5, 480),
                                       ("max_duration_minutes", 5, 480), ("buffer_minutes", 0, 240),
                                       ("capacity", 1, 100), ("min_notice_minutes", 0, 525600),
                                       ("max_days_ahead", 1, 730), ("cancel_before_minutes", 0, 525600)):
                if numeric in rule:
                    try:
                        rule[numeric] = int(rule[numeric])
                    except (TypeError, ValueError):
                        raise ValueError(f"{identity.title()} {numeric} must be a whole number.") from None
                    if not low <= rule[numeric] <= high:
                        raise ValueError(f"{identity.title()} {numeric} must be between {low} and {high}.")
            if rule.get("min_duration_minutes", 5) > rule.get("max_duration_minutes", 480):
                raise ValueError(f"{identity.title()} minimum duration cannot exceed its maximum duration.")
            if "duration_minutes" in rule and not rule.get("min_duration_minutes", 5) <= rule["duration_minutes"] <= rule.get("max_duration_minutes", 480):
                raise ValueError(f"{identity.title()} default duration must be within its configured range.")
            if "business_hours" in rule:
                rule["business_hours"] = normalize_hours(rule["business_hours"])
            if not isinstance(rule.get("holidays", []), list):
                raise ValueError(f"{identity.title()} holidays must be a date list.")
            for holiday in rule.get("holidays", []):
                try:
                    date.fromisoformat(str(holiday))
                except ValueError:
                    raise ValueError("Rule holiday dates must use YYYY-MM-DD format.") from None
            if "staff_ids" in rule and (not isinstance(rule["staff_ids"], list) or any(str(item) not in staff_ids for item in rule["staff_ids"])):
                raise ValueError("Rule staff_ids must contain configured staff IDs.")
    policy = config.get("cancellation_policy")
    if not isinstance(policy, dict):
        raise ValueError("cancellation_policy must be a JSON object.")
    try:
        policy["minimum_notice_minutes"] = int(policy.get("minimum_notice_minutes", 0))
    except (TypeError, ValueError):
        raise ValueError("Cancellation notice must be a whole number of minutes.") from None
    if not 0 <= policy["minimum_notice_minutes"] <= 525600:
        raise ValueError("Cancellation notice must be between 0 and 525600 minutes.")
    return config


def localize_start(raw, config):
    if not isinstance(raw, str) or len(raw) > 100:
        raise ValueError("Provide an ISO 8601 appointment date and time.")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw.strip()):
        raise ValueError("An appointment date must include a time.")
    try:
        candidate = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        zone = ZoneInfo(config["timezone"])
        if candidate.tzinfo is None:
            candidate = candidate.replace(tzinfo=zone)
        return candidate.astimezone(zone)
    except (ValueError, ZoneInfoNotFoundError):
        raise ValueError("Appointment date or time could not be understood.") from None


def _overlaps(conn, tenant_id, start, end, buffer_minutes, staff_id=None, exclude_id=None, service="", department="", capacity=1):
    rows = conn.execute(
        "SELECT id,appointment_at,duration_minutes,buffer_minutes,staff_id,service,department FROM appointments WHERE tenant_id=? AND status='confirmed'",
        (tenant_id,),
    ).fetchall()
    desired_start = start.astimezone(timezone.utc) - timedelta(minutes=buffer_minutes)
    desired_end = end.astimezone(timezone.utc) + timedelta(minutes=buffer_minutes)
    overlapping = 0
    for row in rows:
        if exclude_id and row["id"] == exclude_id:
            continue
        if staff_id and row["staff_id"] and row["staff_id"] != staff_id:
            continue
        try:
            other = datetime.fromisoformat(row["appointment_at"].replace("Z", "+00:00"))
            if other.tzinfo is None:
                other = other.replace(tzinfo=ZoneInfo("Europe/Istanbul"))
            other = other.astimezone(timezone.utc)
        except (ValueError, ZoneInfoNotFoundError):
            continue
        other_start = other - timedelta(minutes=int(row["buffer_minutes"] or 0))
        other_end = other + timedelta(minutes=int(row["duration_minutes"] or 60) + int(row["buffer_minutes"] or 0))
        if desired_start < other_end and other_start < desired_end:
            same_scope = (not service or str(row["service"] or "").casefold() == str(service).casefold()) and (not department or str(row["department"] or "").casefold() == str(department).casefold())
            if same_scope:
                overlapping += 1
            else:
                return True
    for block in settings_for(conn, tenant_id).get("blocked_intervals", []):
        if not isinstance(block, dict):
            continue
        block_staff = block.get("staff_id")
        if block_staff and str(block_staff) != str(staff_id or ""):
            continue
        try:
            block_start = localize_start(str(block["start"]), settings_for(conn, tenant_id)).astimezone(timezone.utc)
            block_end = localize_start(str(block["end"]), settings_for(conn, tenant_id)).astimezone(timezone.utc)
            if desired_start < block_end and block_start < desired_end:
                return True
        except (KeyError, ValueError):
            continue
    return overlapping >= max(1, int(capacity))


def _effective_config(config, service="", department=""):
    result = dict(config)
    matches = []
    if department:
        matches.extend(rule for rule in config.get("department_rules", []) if str(rule.get("department", "")).casefold() == str(department).casefold())
    if service:
        matches.extend(rule for rule in config.get("service_rules", []) if str(rule.get("service", "")).casefold() == str(service).casefold())
    allowed_staff_ids = None
    for rule in matches:
        for key in ("duration_minutes", "min_duration_minutes", "max_duration_minutes", "buffer_minutes", "capacity", "min_notice_minutes", "max_days_ahead", "business_hours", "holidays"):
            if key in rule:
                result[key] = rule[key]
        if "staff_ids" in rule:
            current = {str(value) for value in rule["staff_ids"]}
            allowed_staff_ids = current if allowed_staff_ids is None else allowed_staff_ids & current
    result["allowed_staff_ids"] = sorted(allowed_staff_ids) if allowed_staff_ids is not None else None
    return result


def _within_business_hours(start, end, config, staff_id=None):
    holidays = set(config.get("holidays", []))
    hours = config["business_hours"]
    if staff_id:
        member = next((item for item in config.get("staff", []) if isinstance(item, dict) and str(item.get("id", "")) == str(staff_id)), None)
        if config.get("staff") and not member:
            return False
        if member:
            if member.get("active", True) is False:
                return False
            holidays.update(member.get("holidays", []))
            hours = member.get("business_hours") or hours
    if start.date().isoformat() in holidays:
        return False
    intervals = hours.get(DAY_KEYS[start.weekday()], [])
    for left, right in intervals:
        opening = datetime.combine(start.date(), time.fromisoformat(left), start.tzinfo)
        closing = datetime.combine(start.date(), time.fromisoformat(right), start.tzinfo)
        if opening <= start and end <= closing:
            return True
    return False


def resolve_natural_date(value, timezone_name="Europe/Istanbul", current=None):
    """Resolve a single unambiguous date in English, Turkish or Russian."""
    try:
        zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        zone = ZoneInfo("Europe/Istanbul")
    now = current.astimezone(zone) if current else datetime.now(zone)
    raw = str(value or "").strip()
    try:
        return {"resolved": date.fromisoformat(raw).isoformat(), "needs_clarification": False}
    except ValueError:
        pass
    text = raw.casefold()
    if any(term in text for term in ("tomorrow", "yarın", "завтра")):
        return {"resolved": (now.date() + timedelta(days=1)).isoformat(), "needs_clarification": False}
    if any(term in text for term in ("today", "bugün", "сегодня")):
        return {"resolved": now.date().isoformat(), "needs_clarification": False}
    weekday_aliases = {
        0: ("monday", "pazartesi", "понедельник"), 1: ("tuesday", "salı", "вторник"),
        2: ("wednesday", "çarşamba", "среда"), 3: ("thursday", "perşembe", "четверг"),
        4: ("friday", "cuma", "пятница"), 5: ("saturday", "cumartesi", "суббота"),
        6: ("sunday", "pazar", "воскресенье"),
    }
    match = next((index for index, names in weekday_aliases.items() if any(name in text for name in names)), None)
    if match is not None:
        offset = (match - now.weekday()) % 7
        if offset == 0 or any(word in text for word in ("next", "gelecek", "следующ")):
            offset = offset or 7
            if any(word in text for word in ("next", "gelecek", "следующ")) and offset < 7:
                offset += 7
        return {"resolved": (now.date() + timedelta(days=offset)).isoformat(), "needs_clarification": False}
    return {"resolved": None, "needs_clarification": True, "reason": "Please confirm the exact date."}


def availability(conn, tenant_id, raw_start, duration_minutes=None, staff_id=None, external_check=None, exclude_id=None, service="", department="", calendar_provider=None):
    config = _effective_config(settings_for(conn, tenant_id), service, department)
    start = localize_start(raw_start, config)
    duration = int(duration_minutes or config["duration_minutes"])
    if not config["min_duration_minutes"] <= duration <= config["max_duration_minutes"]:
        raise ValueError("Appointment duration is outside the configured service or tenant range.")
    allowed_staff_ids = config.get("allowed_staff_ids")
    if allowed_staff_ids is not None:
        if staff_id and str(staff_id) not in allowed_staff_ids:
            return {"success": True, "available": False, "requested_start": start.isoformat(), "duration_minutes": duration, "timezone": config["timezone"], "reason": "staff_not_allowed"}
        if not staff_id:
            last_result = None
            for eligible_staff_id in allowed_staff_ids:
                candidate = availability(conn, tenant_id, raw_start, duration, eligible_staff_id, external_check, exclude_id, service, department, calendar_provider)
                if candidate["available"]:
                    return {**candidate, "staff_id": eligible_staff_id}
                last_result = candidate
            if last_result:
                return last_result
            return {"success": True, "available": False, "requested_start": start.isoformat(), "duration_minutes": duration, "timezone": config["timezone"], "reason": "no_eligible_staff"}
    end = start + timedelta(minutes=duration)
    minimum = datetime.now(ZoneInfo(config["timezone"])) + timedelta(minutes=config["min_notice_minutes"])
    maximum = datetime.now(ZoneInfo(config["timezone"])) + timedelta(days=config["max_days_ahead"])
    open_now = minimum <= start <= maximum and _within_business_hours(start, end, config, staff_id)
    busy = _overlaps(conn, tenant_id, start, end, config["buffer_minutes"], staff_id, exclude_id, service, department, config.get("capacity", 1))
    external_busy = False
    if open_now and not busy and external_check:
        external_event_id = None
        provider = calendar_provider
        if exclude_id:
            existing_event = conn.execute("SELECT calendar_event_id,calendar_provider FROM appointments WHERE id=? AND tenant_id=?", (exclude_id, tenant_id)).fetchone()
            external_event_id = existing_event["calendar_event_id"] if existing_event else None
            provider = existing_event["calendar_provider"] if existing_event else provider
        try:
            external = external_check(start.isoformat(), duration, external_event_id, provider)
        except TypeError:
            external = external_check(start.isoformat(), duration, external_event_id)
        if not external or not external.get("ok"):
            raise ValueError((external or {}).get("message", "Connected calendar availability could not be verified."))
        external_busy = not bool(external.get("available", True))
    result = {
        "success": True, "available": bool(open_now and not busy and not external_busy),
        "requested_start": start.isoformat(), "requested_end": end.isoformat(),
        "duration_minutes": duration, "timezone": config["timezone"],
        "reason": "available" if open_now and not busy and not external_busy else "closed_or_outside_booking_window" if not open_now else "busy",
    }
    if staff_id:
        result["staff_id"] = staff_id
    return result


def available_slots(conn, tenant_id, day_text, duration_minutes=None, staff_id=None, limit=12, external_check=None, service="", department="", calendar_provider=None):
    config = _effective_config(settings_for(conn, tenant_id), service, department)
    zone = ZoneInfo(config["timezone"])
    now = datetime.now(zone)
    phrase = str(day_text or "").casefold()
    this_week = any(term in phrase for term in ("this week", "bu hafta", "на этой неделе"))
    next_month_first_week = any(term in phrase for term in ("next month", "önümüzdeki ay", "gelecek ay", "в следующем месяце")) and any(term in phrase for term in ("first week", "ilk hafta", "первую неделю"))
    earliest = any(term in phrase for term in ("as soon as possible", "earliest available", "soonest", "mümkün olan en erken", "en erken müsait", "как можно скорее", "ближайшее время"))
    natural_request = resolve_natural_datetime(day_text, config["timezone"], now) if not this_week and not next_month_first_week and not earliest else {"needs_clarification": True}
    range_match = re.search(r"(?:between\s+|from\s+|arasında\s+)?([01]?\d|2[0-3])\s*(?:and|to|ile|до)\s*([01]?\d|2[0-3])(?:\s*(am|pm|sabah|akşam|утра|вечера))?", phrase) if any(term in phrase for term in ("between", "from", "arasında", "ile", "to", "до")) else None
    exact_start = datetime.fromisoformat(natural_request["resolved"]) if natural_request.get("resolved") and not natural_request.get("needs_clarification") and not range_match else None
    range_end_hour = int(range_match.group(2)) if range_match else None
    if range_match and range_match.group(3) and range_match.group(3).strip().casefold() in {"pm", "akşam", "вечера"} and range_end_hour < 12:
        range_end_hour += 12
    range_end = time(range_end_hour, 0) if range_end_hour is not None else None
    period = "morning" if any(term in phrase for term in ("morning", "sabah", "утром")) else "afternoon" if any(term in phrase for term in ("afternoon", "öğleden sonra", "после обеда")) else "evening" if any(term in phrase for term in ("evening", "akşam", "вечером")) else ""
    if exact_start:
        first_day = last_day = exact_start.date()
    elif this_week:
        first_day = now.date()
        last_day = first_day + timedelta(days=6 - first_day.weekday())
    elif next_month_first_week:
        first_day = (now.date().replace(day=28) + timedelta(days=4)).replace(day=1)
        last_day = first_day + timedelta(days=6)
    elif earliest:
        first_day = now.date()
        last_day = first_day + timedelta(days=min(config["max_days_ahead"], 14))
    else:
        try:
            date_result = resolve_natural_date(day_text, config["timezone"], now)
            if date_result["needs_clarification"]:
                raise ValueError("Please confirm the exact calendar date.")
            first_day = last_day = date.fromisoformat(date_result["resolved"])
        except (TypeError, ValueError):
            raise ValueError("Date must be a date, an unambiguous weekday, this week, next month's first week or earliest available.") from None
    duration = int(duration_minutes or config["duration_minutes"])
    interval = config["slot_interval_minutes"]
    found = []
    maximum = min(max(int(limit), 1), 48)
    for offset in range((last_day - first_day).days + 1):
        day = first_day + timedelta(days=offset)
        hours = config["business_hours"]
        holidays = set(config.get("holidays", []))
        if staff_id:
            member = next((item for item in config.get("staff", []) if isinstance(item, dict) and str(item.get("id", "")) == str(staff_id)), None)
            if config.get("staff") and not member:
                return {"success": True, "date": first_day.isoformat(), "timezone": config["timezone"], "duration_minutes": duration, "slots": []}
            if member:
                if member.get("active", True) is False:
                    return {"success": True, "date": first_day.isoformat(), "timezone": config["timezone"], "duration_minutes": duration, "slots": []}
                hours = member.get("business_hours") or hours
                holidays.update(member.get("holidays", []))
        intervals = [] if day.isoformat() in holidays else hours.get(DAY_KEYS[day.weekday()], [])
        for left, right in intervals:
            point = datetime.combine(day, time.fromisoformat(left), zone)
            closing = datetime.combine(day, time.fromisoformat(right), zone)
            while point + timedelta(minutes=duration) <= closing and len(found) < maximum:
                if exact_start and point.time() != exact_start.time():
                    point += timedelta(minutes=interval)
                    continue
                if range_match and not int(range_match.group(1)) <= point.hour < range_end.hour:
                    point += timedelta(minutes=interval)
                    continue
                if range_end and point + timedelta(minutes=duration) > datetime.combine(day, range_end, zone):
                    point += timedelta(minutes=interval)
                    continue
                if period and not ((6 <= point.hour < 12) if period == "morning" else (12 <= point.hour < 17) if period == "afternoon" else (17 <= point.hour < 22)):
                    point += timedelta(minutes=interval)
                    continue
                item = availability(conn, tenant_id, point.isoformat(), duration, staff_id, external_check, service=service, department=department, calendar_provider=calendar_provider)
                if item["available"]:
                    slot = {"start": point.isoformat(), "end": item["requested_end"], "available": True}
                    if item.get("staff_id"):
                        slot["staff_id"] = item["staff_id"]
                    found.append(slot)
                point += timedelta(minutes=interval)
        if earliest and found:
            break
        if len(found) >= maximum:
            break
    return {"success": True, "date": first_day.isoformat(), "date_range": {"start": first_day.isoformat(), "end": last_day.isoformat()} if first_day != last_day else None, "timezone": config["timezone"], "duration_minutes": duration, "slots": found}


def alternatives(conn, tenant_id, raw_start, duration_minutes=None, staff_id=None, external_check=None, service="", department="", calendar_provider=None):
    config = _effective_config(settings_for(conn, tenant_id), service, department)
    wanted = localize_start(raw_start, config)
    duration = int(duration_minutes or config["duration_minutes"])
    span = config["alternative_window_minutes"]
    candidates = []
    for candidate in (wanted - timedelta(minutes=span), wanted + timedelta(minutes=span)):
        if candidate.date() != wanted.date():
            continue
        check = availability(conn, tenant_id, candidate.isoformat(), duration, staff_id, external_check, service=service, department=department, calendar_provider=calendar_provider)
        if check["available"]:
            candidates.append({"start": candidate.isoformat(), "end": check["requested_end"], "available": True})
    if candidates:
        return {"success": True, "requested_start": wanted.isoformat(), "timezone": config["timezone"], "alternatives": candidates[:2]}
    slots = available_slots(conn, tenant_id, wanted.date().isoformat(), duration, staff_id, 48, external_check, service, department, calendar_provider)["slots"]
    candidates.extend(slots)
    candidates.sort(key=lambda item: abs((datetime.fromisoformat(item["start"]) - wanted).total_seconds()))
    if not candidates:
        for days in range(1, min(config["max_days_ahead"], 14) + 1):
            slots = available_slots(conn, tenant_id, (wanted.date() + timedelta(days=days)).isoformat(), duration, staff_id, 48, external_check, service, department, calendar_provider)["slots"]
            candidates.extend(slots)
            if candidates:
                break
    candidates.sort(key=lambda item: abs((datetime.fromisoformat(item["start"]) - wanted).total_seconds()))
    return {"success": True, "requested_start": wanted.isoformat(), "timezone": config["timezone"], "alternatives": candidates[:2]}


def book(conn, tenant_id, values, call_id=None, external_reserve=None, external_check=None, external_cancel=None):
    required = ("customer_name", "phone", "service", "appointment_at")
    if any(not str(values.get(field, "")).strip() for field in required):
        raise ValueError("Customer name, phone, service and appointment time are required.")
    for field, limit in (("customer_name", 200), ("phone", 100), ("service", 300), ("appointment_at", 100), ("notes", 1000), ("staff_id", 100)):
        if len(str(values.get(field, "") or "")) > limit:
            raise ValueError("Appointment details are too long.")
    idempotency_key = str(values.get("idempotency_key") or "").strip()
    if len(idempotency_key) > 200:
        raise ValueError("Idempotency key is too long.")
    config = settings_for(conn, tenant_id)
    service = str(values["service"]).strip()
    department = str(values.get("department", "") or "").strip()
    config = _effective_config(config, service, department)
    start = localize_start(str(values["appointment_at"]), config)
    duration = int(values.get("duration_minutes") or config["duration_minutes"])
    if not config["min_duration_minutes"] <= duration <= config["max_duration_minutes"]:
        raise ValueError("Appointment duration is outside the configured service or tenant range.")
    staff_id = str(values.get("staff_id") or "").strip() or None
    recurrence = values.get("recurrence")
    starts = [start]
    series_id = None
    if recurrence:
        if not isinstance(recurrence, dict):
            raise ValueError("recurrence must be an object.")
        frequency = str(recurrence.get("frequency", "weekly"))
        if frequency not in {"daily", "weekly"}:
            raise ValueError("Recurring appointments support daily or weekly frequency.")
        try:
            interval = int(recurrence.get("interval", 1))
            count = int(recurrence.get("count", 0))
        except (TypeError, ValueError):
            raise ValueError("Recurrence interval and count must be whole numbers.") from None
        if not 1 <= interval <= 4 or not 2 <= count <= 52:
            raise ValueError("Recurring series need an interval of 1–4 and 2–52 occurrences.")
        step_days = interval * (7 if frequency == "weekly" else 1)
        starts = [start + timedelta(days=step_days * index) for index in range(count)]
        import uuid
        series_id = uuid.uuid4().hex
    import hashlib
    import uuid
    recurrence_keys = [idempotency_key if index == 0 else (hashlib.sha256(f"{idempotency_key}:{index}".encode()).hexdigest() if idempotency_key else "") for index in range(len(starts))]
    conn.execute("BEGIN IMMEDIATE")
    external_created = []
    try:
        if idempotency_key:
            existing = conn.execute("SELECT id,status,appointment_at,recurrence_series_id FROM appointments WHERE tenant_id=? AND idempotency_key=?", (tenant_id, idempotency_key)).fetchone()
            if existing:
                series_rows = conn.execute("SELECT id,status,appointment_at FROM appointments WHERE tenant_id=? AND recurrence_series_id=? ORDER BY recurrence_index", (tenant_id, existing["recurrence_series_id"])).fetchall() if existing["recurrence_series_id"] else [existing]
                conn.commit()
                return {"success": existing["status"] == "confirmed", "available": existing["status"] == "confirmed", "appointment_id": existing["id"], "appointment_at": existing["appointment_at"], "status": existing["status"], "appointments": [dict(item) for item in series_rows], "duplicate": True, "message": "Appointment was already recorded." if existing["status"] == "confirmed" else "This booking request was already used and the appointment is no longer confirmed."}
        for index, candidate in enumerate(starts):
            check = availability(conn, tenant_id, candidate.isoformat(), duration, staff_id, external_check, service=service, department=department)
            if not check["available"]:
                conn.rollback()
                result = alternatives(conn, tenant_id, candidate.isoformat(), duration, staff_id, external_check, service, department)
                return {**result, "success": False, "available": False, "conflict_occurrence": index + 1, "reason": check["reason"]}
            if check.get("staff_id"):
                staff_id = check["staff_id"]
        for index, candidate in enumerate(starts):
            external = {"ok": True, "provider": "internal", "connected": False}
            if external_reserve:
                external = external_reserve({**values, "appointment_at": candidate.isoformat(), "duration_minutes": duration,
                                             "idempotency_key": recurrence_keys[index] or None, "recurrence_series_id": series_id,
                                             "recurrence_index": index + 1,
                                             "calendar_provider": external_created[0].get("provider") if external_created else values.get("calendar_provider")})
            if not external or not external.get("ok"):
                raise ValueError((external or {}).get("message", "Connected calendar reservation failed."))
            external_created.append({**external, "appointment_at": candidate.isoformat(), "duration_minutes": duration})
        appointment_rows = []
        created_at = int(__import__("time").time())
        for index, candidate in enumerate(starts):
            external = external_created[index]
            cursor = conn.execute(
                "INSERT INTO appointments(tenant_id,call_id,customer_name,phone,service,appointment_at,notes,status,created_at,duration_minutes,buffer_minutes,staff_id,idempotency_key,department,calendar_event_id,calendar_provider,recurrence_series_id,recurrence_index) VALUES(?,?,?,?,?,?,?,'confirmed',?,?,?,?,?,?,?,?,?,?)",
                (tenant_id, call_id, str(values["customer_name"]).strip(), str(values["phone"]).strip(), service,
                 candidate.isoformat(), str(values.get("notes", "")).strip(), created_at, duration,
                 config["buffer_minutes"], staff_id, recurrence_keys[index] or None, department,
                 str(external.get("event_id", "")), str(external.get("provider", "internal")), series_id, index + 1),
            )
            appointment_rows.append({"id": cursor.lastrowid, "appointment_at": candidate.isoformat(), "status": "confirmed"})
        conn.commit()
        return {"success": True, "available": True, "appointment_id": appointment_rows[0]["id"], "appointment_at": start.isoformat(), "appointments": appointment_rows, "series_id": series_id, "duration_minutes": duration, "timezone": config["timezone"], "calendar_event_id": str(external_created[0].get("event_id", "")), "duplicate": False, "message": "Recurring appointments recorded." if series_id else "Appointment recorded."}
    except sqlite3.IntegrityError:
        conn.rollback()
        if idempotency_key:
            existing = conn.execute("SELECT id,status,appointment_at FROM appointments WHERE tenant_id=? AND idempotency_key=?", (tenant_id, idempotency_key)).fetchone()
            if existing:
                return {"success": existing["status"] == "confirmed", "available": existing["status"] == "confirmed", "appointment_id": existing["id"], "appointment_at": existing["appointment_at"], "status": existing["status"], "duplicate": True, "message": "Appointment was already recorded." if existing["status"] == "confirmed" else "This booking request was already used and the appointment is no longer confirmed."}
        raise
    except Exception:
        conn.rollback()
        if external_cancel:
            cleanup_failed = False
            for external in reversed(external_created):
                event_id = str(external.get("event_id", ""))
                if event_id:
                    try:
                        result = external_cancel(event_id, "cancel", external)
                        cleanup_failed = cleanup_failed or not result or not result.get("ok")
                    except Exception:
                        cleanup_failed = True
            if cleanup_failed:
                raise ValueError("Recurring reservation failed and at least one external event could not be removed. Review connected calendar events.") from None
        raise


def find_appointment(conn, tenant_id, values):
    phone = re.sub(r"\D", "", str(values.get("phone", "")))
    appointment_id = values.get("appointment_id")
    if not phone or len(phone) < 7:
        raise ValueError("A verified customer phone number is required.")
    if appointment_id:
        row = conn.execute("SELECT id,customer_name,phone,service,appointment_at,status,duration_minutes,staff_id,calendar_event_id,calendar_provider,department FROM appointments WHERE id=? AND tenant_id=?", (int(appointment_id), tenant_id)).fetchone()
        if row and re.sub(r"\D", "", row["phone"] or "") == phone:
            return dict(row)
        return None
    else:
        rows = conn.execute("SELECT id,customer_name,phone,service,appointment_at,status,duration_minutes,staff_id,calendar_event_id,calendar_provider,department FROM appointments WHERE tenant_id=? AND status='confirmed' ORDER BY appointment_at LIMIT 500", (tenant_id,)).fetchall()
        for row in rows:
            if re.sub(r"\D", "", row["phone"] or "") == phone:
                return dict(row)
    return None


def change_appointment(conn, tenant_id, values, action, external_modify=None, external_check=None):
    appointment = find_appointment(conn, tenant_id, values)
    if not appointment:
        return {"success": False, "message": "No matching appointment was found for the verified phone number."}
    if action == "cancel":
        config = _effective_config(settings_for(conn, tenant_id), appointment.get("service", ""), appointment.get("department", ""))
        policy = config.get("cancellation_policy", {})
        service_rule = next((rule for rule in config.get("service_rules", []) if str(rule.get("service", "")).casefold() == str(appointment.get("service", "")).casefold()), {})
        minimum_notice = int(service_rule.get("cancel_before_minutes", policy.get("minimum_notice_minutes", 0)))
        appointment_time = localize_start(str(appointment["appointment_at"]), config)
        if datetime.now(ZoneInfo(config["timezone"])) + timedelta(minutes=minimum_notice) > appointment_time:
            raise ValueError("This appointment is inside the cancellation notice period and cannot be cancelled online.")
        if appointment.get("calendar_event_id") and external_modify:
            result = external_modify(appointment["calendar_event_id"], "cancel", appointment)
            if not result or not result.get("ok"):
                raise ValueError((result or {}).get("message", "Connected calendar cancellation failed."))
        conn.execute("UPDATE appointments SET status='cancelled' WHERE id=? AND tenant_id=?", (appointment["id"], tenant_id))
        conn.commit()
        return {"success": True, "appointment_id": appointment["id"], "status": "cancelled"}
    if action != "reschedule":
        raise ValueError("Unsupported appointment action.")
    moved = dict(values)
    moved.update({"customer_name": appointment["customer_name"], "phone": appointment["phone"], "service": appointment["service"], "duration_minutes": appointment["duration_minutes"], "staff_id": appointment["staff_id"], "department": appointment.get("department", ""), "idempotency_key": ""})
    config = _effective_config(settings_for(conn, tenant_id), appointment["service"], appointment.get("department", ""))
    start = localize_start(str(moved.get("appointment_at", "")), config)
    conn.execute("BEGIN IMMEDIATE")
    try:
        check = availability(conn, tenant_id, start.isoformat(), appointment["duration_minutes"], appointment["staff_id"], external_check, appointment["id"], appointment["service"], appointment.get("department", ""), appointment.get("calendar_provider"))
        if not check["available"]:
            conn.rollback()
            return {**alternatives(conn, tenant_id, start.isoformat(), appointment["duration_minutes"], appointment["staff_id"], external_check, appointment["service"], appointment.get("department", ""), appointment.get("calendar_provider")), "success": False, "available": False, "reason": check["reason"]}
        if appointment.get("calendar_event_id") and external_modify:
            result = external_modify(appointment["calendar_event_id"], "reschedule", {**appointment, "appointment_at": start.isoformat()})
            if not result or not result.get("ok"):
                raise ValueError((result or {}).get("message", "Connected calendar reschedule failed."))
        conn.execute("UPDATE appointments SET appointment_at=?,status='confirmed' WHERE id=? AND tenant_id=?", (start.isoformat(), appointment["id"], tenant_id))
        conn.commit()
        return {"success": True, "appointment_id": appointment["id"], "appointment_at": start.isoformat(), "status": "confirmed"}
    except Exception:
        conn.rollback()
        raise


def resolve_natural_datetime(value, timezone_name="Europe/Istanbul", current=None):
    """Resolve common TR/EN/RU relative phrases; return clarification for ambiguity."""
    try:
        zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        zone = ZoneInfo("Europe/Istanbul")
    now = current.astimezone(zone) if current else datetime.now(zone)
    raw = str(value or "").strip()
    try:
        return {"resolved": localize_start(raw, {"timezone": timezone_name}).isoformat(), "needs_clarification": False}
    except ValueError:
        pass
    text = raw.casefold()
    day = now.date()
    if any(term in text for term in ("tomorrow", "yarın", "завтра")):
        day += timedelta(days=1)
    elif any(term in text for term in ("today", "bugün", "сегодня")):
        pass
    else:
        weekday_aliases = {
            0: ("monday", "pazartesi", "понедельник"), 1: ("tuesday", "salı", "вторник"),
            2: ("wednesday", "çarşamba", "среда"), 3: ("thursday", "perşembe", "четверг"),
            4: ("friday", "cuma", "пятница"), 5: ("saturday", "cumartesi", "суббота"),
            6: ("sunday", "pazar", "воскресенье"),
        }
        match = next((index for index, names in weekday_aliases.items() if any(name in text for name in names)), None)
        if match is None:
            relative = re.search(r"(?:in|within|sonra|через)\s*(\d+)\s*(hours?|minutes?|saat|dakika|час(?:а|ов)?|минут(?:ы|у)?)", text)
            if relative:
                count = int(relative.group(1)); unit = relative.group(2)
                delta = timedelta(minutes=count if any(x in unit for x in ("minute", "dakika", "минут")) else count * 60)
                return {"resolved": (now + delta).replace(second=0, microsecond=0).isoformat(), "needs_clarification": False}
            relative_word = re.search(r"\b(?:in|within)\s+(one|two|three|four|five|six|seven|eight|nine|ten)\s+(hours?|minutes?)\b", text)
            if not relative_word:
                relative_word = re.search(r"\b(one|two|three|four|five|six|seven|eight|nine|ten|a|an)\s+(hours?|minutes?)\s+(?:later|from now)\b", text)
            if relative_word:
                count = {"one": 1, "a": 1, "an": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}[relative_word.group(1)]
                delta = timedelta(minutes=count if relative_word.group(2).startswith("minute") else count * 60)
                return {"resolved": (now + delta).replace(second=0, microsecond=0).isoformat(), "needs_clarification": False}
            if re.search(r"\bчерез\s+час\b", text):
                return {"resolved": (now + timedelta(hours=1)).replace(second=0, microsecond=0).isoformat(), "needs_clarification": False}
            relative_local = re.search(r"\b(один|два|три|четыре|пять|шесть|семь|восемь|девять|десять)\s+час(?:а|ов)?\s+позже\b", text)
            if relative_local:
                count = {"один": 1, "два": 2, "три": 3, "четыре": 4, "пять": 5, "шесть": 6, "семь": 7, "восемь": 8, "девять": 9, "десять": 10}[relative_local.group(1)]
                return {"resolved": (now + timedelta(hours=count)).replace(second=0, microsecond=0).isoformat(), "needs_clarification": False}
            relative_tr = re.search(r"\b(bir|iki|üç|uc|dört|dort|beş|bes|altı|alti|yedi|sekiz|dokuz|on)\s+saat\s+sonra\b", text)
            if relative_tr:
                count = {"bir": 1, "iki": 2, "üç": 3, "uc": 3, "dört": 4, "dort": 4, "beş": 5, "bes": 5, "altı": 6, "alti": 6, "yedi": 7, "sekiz": 8, "dokuz": 9, "on": 10}[relative_tr.group(1)]
                return {"resolved": (now + timedelta(hours=count)).replace(second=0, microsecond=0).isoformat(), "needs_clarification": False}
            return {"resolved": None, "needs_clarification": True, "reason": "Please confirm the exact date and time."}
        offset = (match - now.weekday()) % 7
        if offset == 0 or any(word in text for word in ("next", "gelecek", "следующ")):
            offset = offset or 7
            if any(word in text for word in ("next", "gelecek", "следующ")) and offset < 7:
                offset += 7
        day += timedelta(days=offset)
    time_match = re.search(r"(?<!\d)([01]?\d|2[0-3])(?::([0-5]\d))?\s*(am|pm|öğleden sonra|sabah|вечера|утра)?", text)
    hour = minute = None
    marker = ""
    if time_match:
        hour = int(time_match.group(1)); minute = int(time_match.group(2) or 0); marker = (time_match.group(3) or "").lower()
    else:
        number_words = {
            "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
            "bir": 1, "iki": 2, "üç": 3, "uc": 3, "dört": 4, "dort": 4, "beş": 5, "bes": 5, "altı": 6, "alti": 6, "yedi": 7, "sekiz": 8, "dokuz": 9, "on": 10, "on bir": 11, "onbir": 11, "on iki": 12, "oniki": 12,
            "один": 1, "одна": 1, "два": 2, "две": 2, "три": 3, "четыре": 4, "пять": 5, "шесть": 6, "семь": 7, "восемь": 8, "девять": 9, "десять": 10, "одиннадцать": 11, "двенадцать": 12,
        }
        words = sorted(number_words, key=len, reverse=True)
        spoken = re.search(r"(?:\bat\s+|\bsaat\s+|\bв\s+|\baround\s+)?(" + "|".join(re.escape(word) for word in words) + r")(?:\s+o'clock|\s+час(?:а|ов)?|(?:de|da|te|ta))?\b", text)
        if spoken:
            hour = number_words[spoken.group(1)]
            minute = 0
            marker = ""
    if hour is None:
        return {"resolved": None, "needs_clarification": True, "reason": "Please confirm the appointment time."}
    if any(term in text for term in ("afternoon", "öğleden sonra", "после обеда")) and hour < 12: hour += 12
    if marker in ("pm", "öğleden sonra", "вечера") and hour < 12: hour += 12
    if marker in ("am", "sabah", "утра") and hour == 12: hour = 0
    if marker == "" and hour in range(1, 7) and re.search(r"\b(?:at|saat|в)\s+(?:one|two|three|four|five|six|bir|iki|üç|uc|dört|dort|beş|bes|altı|alti|один|одна|два|две|три|четыре|пять|шесть)(?:de|da|te|ta)?\b", text) and not any(term in text for term in ("morning", "sabah", "утра")):
        hour += 12
    try:
        return {"resolved": datetime.combine(day, time(hour, minute), zone).isoformat(), "needs_clarification": False}
    except ValueError:
        return {"resolved": None, "needs_clarification": True, "reason": "Please confirm the appointment date and time."}
