import re

COURSE_CODE_MAP: dict[str, str] = {
    "civil engineering": "CV",
    "mechanical engineering": "ME",
    "chemical engineering": "CE",
    "electrical engineering": "EE",
    "electrical and electronic engineering": "EE",
    "electronic engineering": "EE",
    "computer engineering": "ComE",
    "materials engineering": "MAT",
    "materials science and engineering": "MAT",
    "petroleum engineering": "PE",
    "applied chemistry": "AC",
}


_CODE_TO_LABEL: dict[str, str] = {
    "CV":    "Civil Engineering",
    "ME":    "Mechanical Engineering",
    "CE":    "Chemical Engineering",
    "EE":    "Electrical Engineering",
    "ComE":  "Computer Engineering",
    "MAT":   "Materials Engineering",
    "PE":    "Petroleum Engineering",
    "AC":    "Applied Chemistry",
    "OTHER": "Engineering",
}


def map_course_to_code(course_name: str) -> str:
    normalised = course_name.strip().lower()
    return COURSE_CODE_MAP.get(normalised, "OTHER")


def course_label(code: str) -> str:
    return _CODE_TO_LABEL.get(code, "Engineering")


def derive_project_type(degree: str) -> str:
    lower = degree.lower()
    if "master" in lower or "doctor" in lower or "phd" in lower or "msc" in lower:
        return "POSTGRAD"
    return "FYP"
