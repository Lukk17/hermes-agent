from bs4 import BeautifulSoup
import re


def parse_ceidg_html(html: str) -> dict:
    data = {}
    if not html:
        return data
    try:
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all(["th", "td"])
                if len(cells) >= 2:
                    label = cells[0].get_text(strip=True).lower()
                    value = cells[1].get_text(strip=True)
                    if label and value:
                        data[label] = value
        paragraphs = soup.find_all("p")
        for p in paragraphs:
            text = p.get_text(strip=True)
            nip_match = re.search(r"nip[\s:]*(\d{10})", text, re.IGNORECASE)
            if nip_match and "nip" not in data:
                data["nip"] = nip_match.group(1)
            regon_match = re.search(r"regon[\s:]*(\d{9})", text, re.IGNORECASE)
            if regon_match and "regon" not in data:
                data["regon"] = regon_match.group(1)
            name_match = re.search(r"nazwa[\s:]*([^\n\r]+)", text, re.IGNORECASE)
            if name_match and "nazwa" not in data:
                data["nazwa"] = name_match.group(1).strip()
        address_tds = soup.find_all("td")
        for td in address_tds:
            text = td.get_text(strip=True)
            if re.match(r"^\d{2}-\d{3}\s+.+", text):
                data["address"] = text
                break
    except Exception:
        pass
    return data


def parse_ekrs_xml(xml: str) -> dict:
    data = {}
    if not xml:
        return data
    try:
        soup = BeautifulSoup(xml, "xml")
        data["krs"] = soup.find("KRS") or soup.find("krs")
        data["nazwa"] = soup.find("NAZWA") or soup.find("nazwa")
        data["formaprawna"] = soup.find("FORMA_PRAWNA") or soup.find("forma_prawna")
        data["siedziba"] = soup.find("SIEDZIBA") or soup.find("siedziba")
        data["adres"] = soup.find("ADRES") or soup.find("adres")
        data["nip"] = soup.find("NIP") or soup.find("nip")
        data["regon"] = soup.find("REGON") or soup.find("regon")
        data["krs"] = str(data.get("krs", "").get_text(strip=True) if hasattr(data.get("krs", ""), "get_text") else data.get("krs", ""))
        for key in ["nazwa", "formaprawna", "siedziba", "adres", "nip", "regon"]:
            if hasattr(data.get(key, ""), "get_text"):
                data[key] = data[key].get_text(strip=True)
        data["raw_snippet"] = xml[:2000]
    except Exception:
        data["raw_snippet"] = xml[:2000]
    return {k: v for k, v in data.items() if v}


def parse_vat_registry_html(html: str) -> dict:
    data = {}
    if not html:
        return data
    try:
        soup = BeautifulSoup(html, "html.parser")
        status = soup.find(string=re.compile(r"(Status|status)[\s:]*", re.IGNORECASE))
        if status:
            data["status"] = status.strip()
        nip_spans = soup.find_all("span", string=re.compile(r"\d{10}"))
        for span in nip_spans:
            data["nip"] = span.get_text(strip=True)
            break
        account_divs = soup.find_all(string=re.compile(r"\d{2}\s+\d{4}\s+\d{4}\s+\d{4}\s+\d{4}\s+\d{4}"))
        if account_divs:
            data["bank_account"] = account_divs[0].strip()
    except Exception:
        pass
    return data
