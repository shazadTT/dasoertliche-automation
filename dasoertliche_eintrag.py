import os
import time
import json
import urllib.request
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

PORTAL = "Das Oertliche"
WEBHOOK_URL = "https://hooks.zapier.com/hooks/catch/16619542/uxr6x3s/"

FREEMAIL = [
    "gmail", "gmx", "web.de", "yahoo", "hotmail", "outlook",
    "icloud", "t-online", "freenet", "mailbox", "aol", "proton"
]


def webhook_fehler(firma, fehler_text):
    try:
        data = json.dumps({
            "portal": PORTAL, "firma": firma,
            "status": "fehler", "fehler": fehler_text[:300]
        }).encode("utf-8")
        req = urllib.request.Request(WEBHOOK_URL, data=data,
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=10) as r:
            print(f"  OK Webhook gesendet: {r.status}")
    except Exception as e:
        print(f"  WARN Webhook fehlgeschlagen: {e}")


def fehler_beschreiben(e):
    """Wandelt technische Fehlermeldung in kurzen, verstaendlichen Text um."""
    msg = str(e)
    if "Pflichtfelder fehlen" in msg:
        return f"Pflichtfelder fehlen: {msg.split(': ', 1)[-1]}"
    if "Mobilnummer" in msg:
        return "Mobilnummer ungültig – muss mit 015, 016 oder 017 beginnen"
    if "Schritt 1 fehlgeschlagen" in msg:
        return f"Formular Schritt 1 nicht abgeschickt – {msg}"
    if "Schritt 2" in msg:
        return "Schritt 2 (Öffnungszeiten) fehlgeschlagen"
    if "Schritt 3" in msg:
        return "Schritt 3 (Beschreibung) fehlgeschlagen"
    if "Schritt 4" in msg:
        return "Schritt 4 (Kontaktdaten) fehlgeschlagen"
    if "Timeout" in msg or "timeout" in msg:
        return "Seite hat nicht reagiert (Timeout) – bitte erneut versuchen"
    if "net::" in msg or "ERR_" in msg:
        return "Netzwerkfehler – Seite nicht erreichbar"
    # Fallback: ersten 120 Zeichen
    return msg[:120]


def get_data():
    return {
        "firma":             os.environ.get("FIRMA", ""),
        "strasse":           os.environ.get("STRASSE", ""),
        "hausnummer":        os.environ.get("HAUSNUMMER", ""),
        "plz":               os.environ.get("PLZ", ""),
        "ort":               os.environ.get("ORT", ""),
        "telpre":            os.environ.get("TELPRE", ""),
        "telnummer":         os.environ.get("TELNUMMER", ""),
        "mobtelpre":         os.environ.get("MOBTELPRE", ""),
        "mobtelnummer":      os.environ.get("MOBTELNUMMER", ""),
        "email":             os.environ.get("EMAIL", ""),
        "website":           os.environ.get("WEBSITE", ""),
        "facebook":          os.environ.get("FACEBOOK", ""),
        "instagram":         os.environ.get("INSTAGRAM", ""),
        "branche":           os.environ.get("BRANCHE", ""),
        "beschreibung":      os.environ.get("BESCHREIBUNG", ""),
        "kontakt_vorname":   os.environ.get("KONTAKT_VORNAME", ""),
        "kontakt_nachname":  os.environ.get("KONTAKT_NACHNAME", ""),
        "kontakt_telpre":    os.environ.get("KONTAKT_TELPRE", ""),
        "kontakt_telnummer": os.environ.get("KONTAKT_TELNUMMER", ""),
        "kontakt_email":     os.environ.get("KONTAKT_EMAIL", ""),
    }


def validiere(c):
    pflicht = ["firma", "strasse", "plz", "ort", "branche",
               "kontakt_vorname", "kontakt_nachname",
               "kontakt_telpre", "kontakt_telnummer", "kontakt_email"]
    fehlend = [f for f in pflicht if not c.get(f)]
    if fehlend:
        raise ValueError(f"Pflichtfelder fehlen: {', '.join(fehlend)}")
    if not c.get("telpre") and not c.get("mobtelpre"):
        raise ValueError("Mindestens Festnetz-Vorwahl oder Mobil-Vorwahl erforderlich")


def ist_freemail(email):
    return any(f in email.lower() for f in FREEMAIL)


def cmp_entfernen(page):
    page.evaluate("""
        () => {
            ['#cmpwrapper', '.cmpwrapper', '#usercentrics-root',
             '[id*="cmp"]', '[class*="cmpwrap"]'].forEach(sel => {
                document.querySelectorAll(sel).forEach(el => el.remove());
            });
            document.body.style.overflow = 'auto';
            document.documentElement.style.overflow = 'auto';
        }
    """)


def cookie_banner_schliessen(page):
    for text in ["Ablehnen", "Alle ablehnen", "Alle Akzeptieren"]:
        try:
            page.wait_for_selector(f"button:has-text('{text}')", timeout=4000)
            page.click(f"button:has-text('{text}')")
            time.sleep(1.5)
            print(f"  OK Cookie-Banner: '{text}' geklickt")
            break
        except PlaywrightTimeout:
            continue
    else:
        print("  - Kein Cookie-Button gefunden")
    cmp_entfernen(page)
    print("  OK cmpwrapper entfernt")


def tippe(page, selector, wert, delay=60):
    try:
        loc = page.locator(selector)
        loc.scroll_into_view_if_needed(timeout=5000)
        loc.click()
        time.sleep(0.2)
        loc.fill("")
        page.keyboard.type(wert, delay=delay)
        page.keyboard.press("Tab")
        time.sleep(0.3)
    except Exception as e:
        print(f"  WARN tippe({selector}): {e}")


def dropdown_auswaehlen(page, dropdown_sel, timeout=4000):
    try:
        page.wait_for_selector(dropdown_sel, timeout=timeout)
        page.locator(dropdown_sel).first.click()
        time.sleep(0.8)
        return True
    except PlaywrightTimeout:
        return False


def submit_schritt(page, erwarteter_naechster_schritt, schritt_nr):
    cmp_entfernen(page)
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(0.5)

    btn_disabled = page.evaluate("() => { const b = document.getElementById('SubmitForward'); return b ? b.disabled : true; }")
    if btn_disabled:
        print(f"  WARN Schritt {schritt_nr}: Button disabled – JS-Unlock")
        page.evaluate("""
            () => {
                const btn = document.getElementById('SubmitForward');
                if (btn) {
                    btn.removeAttribute('disabled');
                    btn.classList.remove('disabled');
                    btn.click();
                }
            }
        """)
    else:
        page.evaluate("document.getElementById('SubmitForward').click()")

    time.sleep(4)
    cmp_entfernen(page)

    try:
        page.wait_for_selector(f"text={erwarteter_naechster_schritt}", timeout=15000)
        print(f"  OK Schritt {schritt_nr} abgeschlossen → {erwarteter_naechster_schritt}")
    except PlaywrightTimeout:
        server_fehler = page.evaluate("""
            () => {
                const el = document.querySelector('.alert, .error-msg, [class*="alert"], [class*="error-message"]');
                return el ? el.innerText.trim() : '';
            }
        """)
        h1 = page.evaluate("() => document.querySelector('h1') ? document.querySelector('h1').textContent.trim() : ''")
        if server_fehler:
            raise Exception(f"Schritt {schritt_nr} fehlgeschlagen. Server: '{server_fehler}'")
        raise Exception(f"Schritt {schritt_nr} fehlgeschlagen. Seite: '{h1}'")


def fill_form(page, c):
    print(f"\nStarte Eintrag fuer: {c['firma']}")

    page.goto("https://services.dasoertliche.de/services/schnupperpaket/sp/")
    page.wait_for_load_state("networkidle")
    time.sleep(3)

    cookie_banner_schliessen(page)

    page.wait_for_selector("text=Los geht's", timeout=15000)
    page.click("text=Los geht's")
    time.sleep(2)
    print("  OK Grundeintrag gewaehlt")

    # ── SCHRITT 1 ────────────────────────────────────────────────────────────
    page.wait_for_selector("#companyname", timeout=15000)
    time.sleep(1)

    page.evaluate("""
        () => {
            document.querySelectorAll('#cmpwrapper, .cmpwrapper, [id*="cmp"]').forEach(el => el.remove());
            document.body.style.overflow = 'auto';
            const obs = new MutationObserver(muts => {
                muts.forEach(m => m.addedNodes.forEach(n => {
                    if (n.id && n.id.includes('cmp')) n.remove();
                    if (n.className && typeof n.className === 'string' && n.className.includes('cmp')) n.remove();
                }));
            });
            obs.observe(document.body, { childList: true, subtree: true });
        }
    """)
    time.sleep(0.5)

    tippe(page, "#companyname", c["firma"])
    tippe(page, "#companystreet", c["strasse"])
    if c.get("hausnummer"):
        tippe(page, "#companyhnr", c["hausnummer"])

    page.locator("#companypc").click()
    time.sleep(0.2)
    page.locator("#companypc").fill("")
    page.keyboard.type(c["plz"], delay=100)
    time.sleep(2)

    if dropdown_auswaehlen(page, "#pclist li, #citylist li", timeout=4000):
        print("  OK PLZ aus Dropdown gewaehlt")
    else:
        page.locator("#companypc").press("Tab")
        print("  - PLZ per Tab")
        time.sleep(0.5)

    page.evaluate("""
        () => {
            const el = document.getElementById('companypc');
            if (el && el.classList.contains('error')) {
                el.classList.remove('error');
                el.dispatchEvent(new Event('change', {bubbles: true}));
            }
        }
    """)

    page.locator("#companycity").click()
    time.sleep(0.3)
    page.locator("#companycity").fill("")
    page.keyboard.type(c["ort"], delay=80)
    time.sleep(2)

    if dropdown_auswaehlen(page, "#citylist li", timeout=5000):
        print("  OK Ort aus Dropdown gewaehlt")
    else:
        page.locator("#companycity").press("Enter")
        print("  - Ort per Enter")
        time.sleep(0.5)

    print("  Warte auf Freischaltung der Telefon-Felder...")
    try:
        page.wait_for_selector("#companytelpre:not([disabled])", timeout=12000)
        print("  OK Telefon-Felder freigeschaltet")
    except PlaywrightTimeout:
        print("  - Aktiviere Telefon-Felder per JS...")
        page.evaluate("""
            () => {
                document.querySelectorAll('.part2, #companytelpre, #companytelnumber, #companymobtelpre, #companymobtelnumber').forEach(el => {
                    el.removeAttribute('disabled');
                    el.classList.remove('disabled');
                });
                document.querySelectorAll('.inputwrap.disabled').forEach(el => el.classList.remove('disabled'));
            }
        """)
        time.sleep(0.5)

    # Telefon per JS direkt setzen – cmpwrapper blockiert click() zu oft
    if c.get("telpre") and c.get("telnummer"):
        cmp_entfernen(page)
        page.evaluate(f"""() => {{
            const pre = document.getElementById('companytelpre');
            const num = document.getElementById('companytelnumber');
            if (pre) {{ pre.value = '{c["telpre"]}'; pre.dispatchEvent(new Event('input', {{bubbles:true}})); pre.dispatchEvent(new Event('change', {{bubbles:true}})); }}
            if (num) {{ num.value = '{c["telnummer"]}'; num.dispatchEvent(new Event('input', {{bubbles:true}})); num.dispatchEvent(new Event('change', {{bubbles:true}})); }}
        }}""")
        time.sleep(0.3)
        print(f"  OK Festnetz: {c['telpre']} {c['telnummer']}")

    if c.get("mobtelpre") and c.get("mobtelnummer"):
        cmp_entfernen(page)
        page.evaluate(f"""() => {{
            const pre = document.getElementById('companymobtelpre');
            const num = document.getElementById('companymobtelnumber');
            if (pre) {{ pre.value = '{c["mobtelpre"]}'; pre.dispatchEvent(new Event('input', {{bubbles:true}})); pre.dispatchEvent(new Event('change', {{bubbles:true}})); }}
            if (num) {{ num.value = '{c["mobtelnummer"]}'; num.dispatchEvent(new Event('input', {{bubbles:true}})); num.dispatchEvent(new Event('change', {{bubbles:true}})); }}
        }}""")
        time.sleep(0.3)
        print(f"  OK Mobil: {c['mobtelpre']} {c['mobtelnummer']}")

    if c.get("website"):
        tippe(page, "#companyurl", c["website"])
    if c.get("facebook"):
        tippe(page, "#socfacebook", c["facebook"])
    if c.get("instagram"):
        tippe(page, "#socinstagram", c["instagram"])

    email = c.get("email", "")
    if email and not ist_freemail(email):
        tippe(page, "#companyemail", email)
        print(f"  OK E-Mail: {email}")
    elif email:
        print(f"  - E-Mail uebersprungen (Freemail): {email}")

    # cmpwrapper nochmal entfernen – Das Oertliche laedt ihn nach Formular-Interaktion neu
    cmp_entfernen(page)
    time.sleep(0.3)

    page.locator("#rubric").click()
    time.sleep(0.2)
    page.locator("#rubric").fill("")
    page.keyboard.type(c["branche"], delay=80)
    time.sleep(2)

    if dropdown_auswaehlen(page, "#rubriclist li", timeout=4000):
        print(f"  OK Branche aus Dropdown: {c['branche']}")
    else:
        branche_safe = c["branche"].replace("\\", "\\\\").replace("'", "\\'")
        page.evaluate(f"""
            () => {{
                const el = document.getElementById('rubric');
                if (el) el.value = '{branche_safe}';
                const rid = document.getElementById('rubricid');
                if (rid) rid.value = '0000001';
                if (el) el.dispatchEvent(new Event('change', {{bubbles: true}}));
            }}
        """)
        print(f"  - Branche per JS: {c['branche']}")
    time.sleep(0.5)

    submit_schritt(page, "Schritt 2 von 4", schritt_nr=1)

    # ── SCHRITT 2 ────────────────────────────────────────────────────────────
    time.sleep(0.5)
    page.evaluate("document.getElementById('SubmitForward').click()")
    time.sleep(3)
    cmp_entfernen(page)
    try:
        page.wait_for_selector("text=Schritt 3 von 4", timeout=15000)
        print("  OK Schritt 2 uebersprungen")
    except PlaywrightTimeout:
        raise Exception("Schritt 2 → Schritt 3 fehlgeschlagen")

    # ── SCHRITT 3 ────────────────────────────────────────────────────────────
    time.sleep(0.5)
    if c.get("beschreibung"):
        try:
            page.locator("#freetext").fill(c["beschreibung"][:500])
            time.sleep(0.3)
            print("  OK Beschreibung eingetragen")
        except Exception:
            pass
    page.evaluate("document.getElementById('SubmitForward').click()")
    time.sleep(3)
    cmp_entfernen(page)
    try:
        page.wait_for_selector("text=Schritt 4 von 4", timeout=15000)
        print("  OK Schritt 3 abgeschlossen")
    except PlaywrightTimeout:
        raise Exception("Schritt 3 → Schritt 4 fehlgeschlagen")

    # ── SCHRITT 4 ────────────────────────────────────────────────────────────
    time.sleep(1)
    cmp_entfernen(page)
    try:
        page.locator("#contactfirstname").fill(c["kontakt_vorname"])
        time.sleep(0.2)
        page.locator("#contactlastname").fill(c["kontakt_nachname"])
        time.sleep(0.2)
        page.locator("#contactprefixnumber").fill(c["kontakt_telpre"])
        time.sleep(0.2)
        page.locator("#contactcallnumber").fill(c["kontakt_telnummer"])
        time.sleep(0.2)
        page.locator("#contactemail").fill(c["kontakt_email"])
        time.sleep(0.3)
        print(f"  OK Ansprechpartner: {c['kontakt_vorname']} {c['kontakt_nachname']}")
    except Exception as e:
        raise Exception(f"Schritt 4 Kontaktfelder: {e}")

    page.evaluate("document.getElementById('SubmitForward').removeAttribute('disabled')")
    time.sleep(0.3)
    page.evaluate("document.getElementById('SubmitForward').click()")
    time.sleep(4)
    print("  OK Eintrag abgesendet!")
    print(f"\n  Bestaetigung geht an: {c['kontakt_email']}")
    print("  Ansprechpartner muss den Link in der E-Mail bestaetigen.")


def main():
    print("=" * 55)
    print("Das Oertliche Automatisierung")
    print("=" * 55)

    c = get_data()
    firma = c.get("firma", "unbekannt")

    try:
        validiere(c)
    except ValueError as e:
        kurzer_fehler = fehler_beschreiben(e)
        print(f"\nFehler: {kurzer_fehler}")
        webhook_fehler(firma, kurzer_fehler)
        exit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="de-DE"
        )
        page = context.new_page()

        try:
            fill_form(page, c)
            print("\nErfolgreich abgeschlossen!")
        except Exception as e:
            page.screenshot(path="fehler_screenshot.png")
            kurzer_fehler = fehler_beschreiben(e)
            print(f"\nFehler: {kurzer_fehler}")
            webhook_fehler(firma, kurzer_fehler)
            raise
        finally:
            browser.close()


if __name__ == "__main__":
    main()
