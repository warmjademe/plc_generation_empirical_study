#!/usr/bin/env python3
"""Exercise the downloadable-project approval UI in a real browser viewport.

The script logs into a deployed service, renders a synthetic already-approved
contract in the production JavaScript bundle, and verifies that the physical
I/O review is the visible and actionable modal state.  It never submits a PLC
generation job or clicks the final approval button.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.actions.wheel_input import ScrollOrigin
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as conditions
from selenium.webdriver.support.ui import WebDriverWait


def synthetic_job() -> dict:
    return {
        "id": "ui-e2e-downloadable-project",
        "status": "awaiting_contract_approval",
        "request": {
            "delivery_mode": "downloadable_project",
            "plc_model": "AS228T-A",
            "output_language": "st",
        },
        "contract": {
            "task_id": "PLC_UI_E2E",
            "title": "AS228T-A downloadable approval viewport test",
            "engineering_template": {
                "target": "AS228T-A",
                "target_profile": "delta-as228t-a",
                "project_name": "PLC_UI_E2E",
                "scan_period_ms": 100,
                "output_electrical_type": "transistor",
                "input_addresses": [f"X{i}" for i in range(8)],
                "output_addresses": [f"Y{i}" for i in range(8)],
                "mappings": [
                    *[
                        {"symbol": f"Input{i}", "direction": "input", "iec_type": "BOOL", "address": f"X{i}", "active_high": True, "safe_logical_value": False, "description": f"现场输入 {i}"}
                        for i in range(8)
                    ],
                    *[
                        {"symbol": f"Output{i}", "direction": "output", "iec_type": "BOOL", "address": f"Y{i}", "active_high": True, "safe_logical_value": False, "description": f"现场输出 {i}"}
                        for i in range(8)
                    ],
                ],
            },
        },
    }


def progress() -> dict:
    return {
        "job_id": "ui-e2e-downloadable-project",
        "phase": "awaiting_contract_approval",
        "message": "验证契约已就绪，等待用户确认",
        "detail_message": "可下载工程必须核对物理 I/O。",
        "contract_attempt": 1,
        "contract_budget": 10,
        "current_attempt": 0,
        "candidate_budget": 20,
        "current_component": "awaiting_contract_approval",
        "elapsed_seconds": 30,
        "idle_seconds": 2,
        "phase_percent": 15,
        "health": "working",
        "active": True,
        "events": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="https://ai.fuxtagent.com:18080/")
    parser.add_argument("--report-dir", type=Path, required=True)
    args = parser.parse_args()
    username = os.environ.get("PLC_LOGIN_USERNAME", "")
    password = os.environ.get("PLC_LOGIN_PASSWORD", "")
    if not username or not password:
        raise SystemExit("PLC_LOGIN_USERNAME and PLC_LOGIN_PASSWORD are required")

    args.report_dir.mkdir(parents=True, exist_ok=True)
    options = Options()
    options.add_argument("-headless")
    snap_firefox = Path("/snap/firefox/current/usr/lib/firefox/firefox")
    if snap_firefox.is_file():
        options.binary_location = str(snap_firefox)
    driver = webdriver.Firefox(options=options)
    results: list[dict] = []
    try:
        driver.set_page_load_timeout(60)
        driver.get(args.url)
        if driver.find_elements(By.ID, "loginForm"):
            driver.find_element(By.ID, "username").clear()
            driver.find_element(By.ID, "username").send_keys(username)
            driver.find_element(By.ID, "password").clear()
            driver.find_element(By.ID, "password").send_keys(password)
            driver.find_element(By.CSS_SELECTOR, "#loginForm button").click()
        WebDriverWait(driver, 30).until(
            conditions.presence_of_element_located((By.ID, "contractPanel"))
        )

        for width, height, label in ((1366, 768, "desktop"), (390, 844, "mobile")):
            driver.set_window_size(width, height)
            driver.execute_script(
                "window.__uiE2EJob=arguments[0]; window.__uiE2EProgress=arguments[1];"
                "if(!window.__uiE2ENativeFetch) window.__uiE2ENativeFetch=window.fetch.bind(window);"
                "window.fetch=(input,options)=>{const url=String(typeof input==='string'?input:input.url);"
                "if(url.endsWith('/api/jobs/ui-e2e-downloadable-project/progress'))"
                "return Promise.resolve(new Response(JSON.stringify(window.__uiE2EProgress),{status:200,headers:{'Content-Type':'application/json'}}));"
                "if(url.endsWith('/api/jobs/ui-e2e-downloadable-project'))"
                "return Promise.resolve(new Response(JSON.stringify(window.__uiE2EJob),{status:200,headers:{'Content-Type':'application/json'}}));"
                "return window.__uiE2ENativeFetch(input,options);};"
                "selectTrackedJob('ui-e2e-downloadable-project');",
                synthetic_job(), progress(),
            )
            wait = WebDriverWait(driver, 10)
            contract = wait.until(conditions.visibility_of_element_located((By.ID, "contractPanel")))
            engineering = wait.until(conditions.visibility_of_element_located((By.ID, "engineeringPanel")))
            progress_panel = driver.find_element(By.ID, "progressPanel")
            approve = driver.find_element(By.ID, "approve")
            details = driver.find_element(By.ID, "contractDetails")
            assert not progress_panel.is_displayed(), "progress log still obscures the approval form"
            assert contract.is_displayed() and engineering.is_displayed()
            assert details.get_attribute("open") is None, "downloadable contract details should start collapsed"
            assert "等待人工确认物理 I/O 映射" in driver.find_element(By.ID, "approvalCountdown").text

            scroll_before = driver.execute_script("return arguments[0].scrollTop", contract)
            scroll_extent = driver.execute_script(
                "return {height:arguments[0].clientHeight,total:arguments[0].scrollHeight}", contract
            )
            assert scroll_extent["total"] > scroll_extent["height"], "fixture must overflow the approval panel"
            ActionChains(driver).scroll_from_origin(ScrollOrigin.from_element(contract), 0, 420).perform()
            wait.until(
                lambda _driver: driver.execute_script("return arguments[0].scrollTop", contract) > scroll_before,
                message="mouse-wheel scrolling did not move the approval panel",
            )
            scroll_after = driver.execute_script("return arguments[0].scrollTop", contract)
            driver.execute_script(
                "document.getElementById('wiringReviewAck').checked=false;"
                "document.getElementById('fieldAcceptanceAck').checked=false;"
                "updateEngineeringApprovalState();"
            )
            assert approve.get_attribute("disabled") is not None

            driver.find_element(By.ID, "wiringReviewAck").click()
            driver.find_element(By.ID, "fieldAcceptanceAck").click()
            approval_state = driver.execute_script(
                "return {wiring:document.getElementById('wiringReviewAck').checked,"
                "field:document.getElementById('fieldAcceptanceAck').checked,"
                "disabled:document.getElementById('approve').disabled,"
                "error:document.getElementById('engineeringError').textContent,"
                "status:document.getElementById('jobStatus').textContent};"
            )
            print(json.dumps({"viewport": label, "approval_state": approval_state}, ensure_ascii=False), flush=True)
            wait.until(
                lambda _driver: approve.is_enabled(),
                message=f"approval did not become enabled: {approval_state}",
            )
            wait.until(conditions.element_to_be_clickable((By.ID, "approve")))
            card = driver.find_element(By.CSS_SELECTOR, ".job-modal-card")
            geometry = driver.execute_script(
                "const a=arguments[0].getBoundingClientRect(), c=arguments[1].getBoundingClientRect();"
                "return {buttonTop:a.top,buttonBottom:a.bottom,cardTop:c.top,cardBottom:c.bottom,"
                "scrollTop:arguments[1].scrollTop,scrollHeight:arguments[1].scrollHeight,clientHeight:arguments[1].clientHeight};",
                approve, card,
            )
            assert geometry["buttonTop"] >= geometry["cardTop"]
            assert geometry["buttonBottom"] <= geometry["cardBottom"]
            screenshot = args.report_dir / f"downloadable-approval-{label}.png"
            driver.save_screenshot(str(screenshot))
            results.append({
                "viewport": {"width": width, "height": height},
                "progress_hidden": True,
                "contract_visible": True,
                "engineering_visible": True,
                "approval_enabled_after_acknowledgements": True,
                "approval_button_in_viewport": True,
                "wheel_scroll_worked": scroll_after > scroll_before,
                "scroll_before": scroll_before,
                "scroll_after": scroll_after,
                "geometry": geometry,
                "screenshot": screenshot.name,
            })
    finally:
        driver.quit()

    report = {
        "schema_version": 1,
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "status": "pass",
        "url": args.url,
        "results": results,
    }
    output = args.report_dir / "downloadable-approval-ui-e2e.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "pass", "viewports": len(results)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
