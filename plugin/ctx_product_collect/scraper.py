"""
CTX 상품 상세 스크래퍼
- Selenium headless Chrome 으로 ctx.cretec.kr 상품 상세 페이지를 수집
- 사양(spec), 배송정보(delivery), 상세설명(detail) 을 JSON 으로 반환
"""

import re

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

WAIT_SECONDS = 10
CTX_ITEM_DTL_URL = "https://ctx.cretec.kr/CtxApp/ctx/selectItemDtlIfrm.do"


# ────────────────────────────────────────────────
# Chrome Driver
# ────────────────────────────────────────────────

def _create_driver() -> webdriver.Chrome:
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--blink-settings=imagesEnabled=false")
    options.add_argument("--window-size=1920,1080")
    # Linux 서버 환경(cloudtype 등)에서 Chrome 바이너리 경로 명시
    for chrome_path in [
        "/usr/bin/google-chrome",
        "/usr/bin/chromium-browser",
        "/usr/bin/chromium",
    ]:
        import os
        if os.path.exists(chrome_path):
            options.binary_location = chrome_path
            break
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


# ────────────────────────────────────────────────
# 파싱 헬퍼
# ────────────────────────────────────────────────

def _clean(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _parse_spec(html: str) -> dict:
    """사양 테이블 파싱 — active 버튼 우선 취득"""
    soup = BeautifulSoup(html, "html.parser")
    result = {}
    for row in soup.find_all("tr"):
        tds = row.find_all("td")
        if len(tds) < 2:
            continue
        key = _clean(tds[0].get_text())
        buttons = tds[1].find_all("button")
        if buttons:
            value = next(
                (_clean(b.get_text()) for b in buttons if b.get("data-active") == "Y"),
                _clean(tds[1].get_text()),
            )
        else:
            value = _clean(tds[1].get_text())
        result[key] = value
    return result


def _parse_delivery(html: str) -> dict:
    """배송정보 테이블 파싱 — 금액은 int 변환"""
    soup = BeautifulSoup(html, "html.parser")
    result = {}
    for row in soup.find_all("tr"):
        tds = row.find_all("td")
        if len(tds) < 2:
            continue
        key = _clean(tds[0].get_text())
        raw = _clean(tds[1].get_text()).replace("￦", "").replace(",", "")
        try:
            result[key] = int(raw)
        except ValueError:
            result[key] = raw
    return result


def _clean_detail_html(html: str) -> str:
    """상세 설명 HTML — style/script 제거, hr → div"""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["style", "script"]):
        tag.decompose()
    for hr in soup.find_all("hr"):
        hr.replace_with(
            soup.new_tag("div", style="border-top:1px solid #ccc;margin:20px 0;")
        )
    return re.sub(r"\s+", " ", str(soup)).strip()


# ────────────────────────────────────────────────
# 메인 함수
# ────────────────────────────────────────────────

def get_product_detail(item_cd: str) -> dict:
    """
    item_cd(proino) 로 CTX 상품 상세 페이지를 스크래핑해 JSON 반환

    Returns:
        {
            "success": True,
            "item_cd": "...",
            "spec": {...},
            "delivery": {...},
            "detail": "<html>..."
        }
        또는
        {
            "success": False,
            "item_cd": "...",
            "error": "..."
        }
    """
    driver = None
    try:
        driver = _create_driver()
        url = f"{CTX_ITEM_DTL_URL}?itemCd={item_cd}&compCd="
        driver.get(url)

        WebDriverWait(driver, WAIT_SECONDS).until(
            EC.presence_of_element_located((By.ID, "metaInfoTbl"))
        )

        # 사양
        meta_html = driver.find_element(By.ID, "metaInfoTbl").get_attribute("outerHTML")

        # 배송정보
        try:
            deli_html = driver.find_element(
                By.XPATH, '//*[@id="itemDtlTbl"]/tbody/tr[10]/td/table'
            ).get_attribute("outerHTML")
        except Exception:
            deli_html = ""

        # 상세 설명
        try:
            detail_html = driver.find_element(
                By.ID, "itemDetailDiv"
            ).get_attribute("outerHTML")
        except Exception:
            detail_html = ""

        return {
            "success": True,
            "item_cd": item_cd,
            "spec": _parse_spec(meta_html),
            "delivery": _parse_delivery(deli_html) if deli_html else {},
            "detail": _clean_detail_html(detail_html) if detail_html else "",
        }

    except Exception as e:
        return {"success": False, "item_cd": item_cd, "error": str(e)}

    finally:
        if driver:
            driver.quit()
