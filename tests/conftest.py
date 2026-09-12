import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import pymupdf as fitz


def make_pdf_bytes(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    rect = fitz.Rect(50, 50, page.rect.width - 50, page.rect.height - 50)
    page.insert_textbox(rect, text, fontsize=10, fontname="helv")
    data = doc.tobytes()
    doc.close()
    return data


@pytest.fixture
def make_pdf():
    return make_pdf_bytes


SAMPLE_JD_TEXT = """Junior Full Stack Developer Intern
TechNova Solutions

Responsibilities
Develop and maintain REST APIs using Node.js and Express
Build responsive user interfaces using React
Work with MongoDB for data storage and retrieval

Required Skills
JavaScript
React
Node.js
Express.js
MongoDB
Git
HTML
CSS
REST API

Preferred Skills
TypeScript
Docker
AWS
Redux
Jest
Agile/Scrum experience

Qualifications
Pursuing a Bachelor's degree in Computer Science
0-1 years of experience
"""

STRONG_RESUME_TEXT = """Test Candidate Strong
test.strong@example.com

Education
B.Tech Computer Science, 2026

Skills
JavaScript, React, Node.js, Express.js, MongoDB, Git, HTML, CSS, TypeScript, Docker

Projects
Marketplace App - Built a full-stack app using React frontend and Node.js/Express
backend with MongoDB storage, exposing REST APIs for listings.

Experience
Software Development Intern, Example Corp
Built REST APIs in Node.js/Express and integrated MongoDB queries.
"""

WEAK_RESUME_TEXT = """Test Candidate Weak
test.weak@example.com

Education
B.Sc Statistics, 2026

Skills
Python, Pandas, NumPy, Excel, Power BI

Projects
Sales Prediction Model - Built a regression model using scikit-learn and pandas.

Experience
Data Analyst Intern, Example Analytics
Cleaned datasets using pandas and built dashboards in Power BI.
"""
