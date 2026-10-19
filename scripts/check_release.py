#!/usr/bin/env python3
"""Run dependency-light checks before starting a local or staging release.

This script intentionally does not claim to replace pytest or a live database
integration test. It catches common syntax, template, manifest, and asset issues
without importing Flask application code.
"""
from __future__ import annotations

import json
import shutil
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
errors: list[str] = []
notes: list[str] = []


def check(condition: bool, message: str) -> None:
    (notes if condition else errors).append(("PASS: " if condition else "FAIL: ") + message)


def main() -> int:
    # Verify that Python sources compile without executing application imports.
    compile_result = subprocess.run(
        [sys.executable, "-m", "compileall", "-q", "app.py", "config.py", "extensions.py", "study_content.py", "nextgen", "tests", "migrations"],
        cwd=ROOT, capture_output=True, text=True,
    )
    check(compile_result.returncode == 0, "Python source compilation")
    if compile_result.stderr.strip():
        notes.append(compile_result.stderr.strip())

    # Parse every Jinja template. This catches malformed template syntax without
    # needing a running Flask application or a database.
    try:
        from jinja2 import Environment
        environment = Environment()
        template_paths = sorted((ROOT / "nextgen" / "templates").glob("*.html"))
        for path in template_paths:
            environment.parse(path.read_text(encoding="utf-8"))
        check(bool(template_paths), f"Jinja syntax ({len(template_paths)} templates)")
    except Exception as exc:  # keep checking independent assets after one failure
        check(False, f"Jinja template parsing: {exc}")

    # Validate the PWA manifest as real JSON and confirm every declared icon exists.
    try:
        manifest_path = ROOT / "nextgen" / "static" / "manifest.webmanifest"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        icon_ok = True
        for item in manifest.get("icons", []):
            path = ROOT / "nextgen" / "static" / item["src"].removeprefix("/static/")
            icon_ok = icon_ok and path.is_file()
            if path.is_file():
                raw = path.read_bytes()
                icon_ok = icon_ok and raw[:8] == b"\x89PNG\r\n\x1a\n" and len(raw) >= 24
                if len(raw) >= 24 and raw[:8] == b"\x89PNG\r\n\x1a\n":
                    width, height = struct.unpack(">II", raw[16:24])
                    declared = item.get("sizes", "")
                    icon_ok = icon_ok and declared == f"{width}x{height}"
        check(bool(manifest.get("name")) and bool(manifest.get("start_url")), "PWA manifest content")
        check(icon_ok and bool(manifest.get("icons")), "PWA icons exist and dimensions match manifest")
    except Exception as exc:
        check(False, f"PWA manifest/icon validation: {exc}")

    # Ensure static files referenced by root templates exist in the expected static tree.
    required_assets = [
        ROOT / "nextgen/static/css/style.css",
        ROOT / "nextgen/static/css/landing.css",
        ROOT / "nextgen/static/css/lovable-ui.css",
        ROOT / "nextgen/static/js/app.js",
        ROOT / "nextgen/static/sw.js",
    ]
    check(all(path.is_file() for path in required_assets), "Required CSS, JavaScript and service-worker assets exist")
    service_worker = (ROOT / "nextgen" / "static" / "sw.js").read_text(encoding="utf-8")
    check("/static/css/lovable-ui.css" in service_worker, "PWA shell cache includes the merged Lovable UI stylesheet")
    check((ROOT / "migrations" / "versions" / "0003_subject_catalog.py").is_file(), "Subject catalog migration exists")
    check((ROOT / "migrations" / "versions" / "0004_classroom_assessments.py").is_file(), "Classroom assessment migration exists")
    dashboard = (ROOT / "nextgen" / "templates" / "dashboard.html").read_text(encoding="utf-8")
    app_js = (ROOT / "nextgen" / "static" / "js" / "app.js").read_text(encoding="utf-8")
    check('id="section-study"' in dashboard and 'data-section="study"' in dashboard, "Study Lab navigation and page section exist")
    check('id="section-study-buddy"' in dashboard and 'data-section="study-buddy"' in dashboard, "Study Buddy navigation and separate page exist")
    check("STUDY_QUESTIONS" in app_js and "bindStudyLab" in app_js and "tutorReply" in app_js, "Practice MCQ, mock test and study helper handlers exist")
    check('id="assessmentForm"' in dashboard and 'id="assessmentAttemptForm"' in app_js and 'data-assessment-results' in app_js, "Teacher-created assessment and student attempt UI wiring exists")
    check("retrieve_relevant_chunks" in (ROOT / "study_content.py").read_text(encoding="utf-8"), "Course-note retrieval helper exists")
    api_source = (ROOT / "nextgen" / "api.py").read_text(encoding="utf-8")
    model_source = (ROOT / "nextgen" / "models.py").read_text(encoding="utf-8")
    check('"/assessments"' in api_source and '"/assessments/<int:assessment_id>/attempts"' in api_source and "class AssessmentAttempt" in model_source, "Assessment API and data models exist")
    check("nextgenpathashala-shell-v9-visible-account-control" in service_worker, "Service-worker cache version bumped for visible account control")

    # Check linear Alembic revision links without importing the Flask app.
    try:
        import ast
        revisions = {}
        for migration_path in sorted((ROOT / "migrations" / "versions").glob("*.py")):
            if migration_path.name == "__init__.py":
                continue
            module = ast.parse(migration_path.read_text(encoding="utf-8"))
            values = {}
            for node in module.body:
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id in {"revision", "down_revision"}:
                            values[target.id] = ast.literal_eval(node.value)
            if "revision" in values:
                revisions[values["revision"]] = values.get("down_revision")
        chain_ok = bool(revisions) and len(revisions) == len(set(revisions))
        chain_ok = chain_ok and all(parent is None or parent in revisions for parent in revisions.values())
        chain_ok = chain_ok and revisions.get("0004_classroom_assessments") == "0003_subject_catalog"
        check(chain_ok, f"Alembic revision links ({len(revisions)} revisions)")
    except Exception as exc:
        check(False, f"Alembic revision link validation: {exc}")

    # Dependency-free course-content tests run without importing the Flask app.
    unit_result = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_study_content_unit.py"],
        cwd=ROOT, capture_output=True, text=True,
    )
    check(unit_result.returncode == 0, "Dependency-free course-note unit tests")
    if unit_result.stdout.strip():
        notes.append(unit_result.stdout.strip())
    if unit_result.stderr.strip():
        notes.append(unit_result.stderr.strip())

    # Optional JavaScript syntax and question-bank checks. They are skipped, not passed, if Node is absent.
    node = shutil.which("node")
    if node:
        result = subprocess.run([node, "--check", "nextgen/static/js/app.js"], cwd=ROOT, capture_output=True, text=True)
        check(result.returncode == 0, "JavaScript syntax (node --check)")
        if result.stderr.strip():
            notes.append(result.stderr.strip())
        bank_result = subprocess.run([node, "scripts/check_study_bank.cjs"], cwd=ROOT, capture_output=True, text=True)
        check(bank_result.returncode == 0, "MCQ answer keys, unique options and topic coverage")
        if bank_result.stdout.strip():
            notes.append(bank_result.stdout.strip())
        if bank_result.stderr.strip():
            notes.append(bank_result.stderr.strip())
    else:
        notes.append("SKIP: Node.js not installed; JavaScript syntax and question-bank checks were not checked.")

    for note in notes:
        print(note)
    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        print(f"Release checks failed: {len(errors)} issue(s).", file=sys.stderr)
        return 1
    print("Static release checks completed. Run pytest and live database checks separately.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
