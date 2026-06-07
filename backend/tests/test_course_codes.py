import pytest
from app.core.course_codes import map_course_to_code, derive_project_type


@pytest.mark.parametrize("course_name,expected_code", [
    ("Civil Engineering", "CV"),
    ("civil engineering", "CV"),
    ("  Civil Engineering  ", "CV"),
    ("Mechanical Engineering", "ME"),
    ("Chemical Engineering", "CE"),
    ("Electrical Engineering", "EE"),
    ("Electrical and Electronic Engineering", "EE"),
    ("Computer Engineering", "ComE"),
    ("Materials Engineering", "MAT"),
    ("Petroleum Engineering", "PE"),
    ("Applied Chemistry", "AC"),
    ("Unknown Subject", "OTHER"),
    ("", "OTHER"),
])
def test_map_course_to_code(course_name, expected_code):
    assert map_course_to_code(course_name) == expected_code


@pytest.mark.parametrize("degree,expected_type", [
    ("Bachelor of Engineering (Hons) Civil Engineering", "FYP"),
    ("B.Eng (Hons) Mechanical Engineering", "FYP"),
    ("Master of Science", "POSTGRAD"),
    ("Master of Engineering", "POSTGRAD"),
    ("Doctor of Philosophy", "POSTGRAD"),
    ("PhD in Chemical Engineering", "POSTGRAD"),
    ("MSc Petroleum Engineering", "POSTGRAD"),
    ("", "FYP"),  # unknown → default FYP
])
def test_derive_project_type(degree, expected_type):
    assert derive_project_type(degree) == expected_type
