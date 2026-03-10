import os
import time
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


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


def cookie_banner_schliessen(page):
    try:
        page.evaluate("""
            () => {
                const ucRoot = document.querySelector('#usercentrics-root');
                if (ucRoot && ucRoot.shadowRoot) {
                    const buttons = Array.from(ucRoot.shadowRoot.querySelectorAll('button'));
                    const btn = buttons.find(b =>
                        b.textContent.trim().includes('Ablehnen') ||
                        b.textContent.trim().includes('Alle Akzeptieren')
                    );
                    if (btn) btn.click();
                }
                ['#cmpwrapper', '#usercentrics-root', '.cmpwrapper'].forEach(sel => {
                    document.querySelectorAll(sel).forEach(el => el.remove());
                });
                document.body.style.overflow = 'auto';
            }
        """)
        time.sleep(2)
        print("  OK Cookie-Banner entfernt")
    except Exception as e:
        print(f"  - Cookie-Banner: {e}")


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

    # Schritt 1: Adresse + Kontakt + Branche
    page.wait_for_selector("#companyname", timeout=15000)
    time.sleep(1)

    ids = page.evaluate("() => Array.from(document.querySelectorAll('input')).filter(i => i.offsetParent !== null).map(i => i.id + '/' + i.name)")
    print(f"  DEBUG Schritt1 Inputs: {ids}")

    page.locator("#companyname").fill(c["firma"])
    time.sleep(0.3)
    page.locator("#companystreet").fill(c["strasse"])
    time.sleep(0.3)
    if c["hausnummer"]:
        page.locator("#companyhnr").fill(c["hausnummer"])
        time.sleep(0.3)
    page.locator("#companypc").fill(c["plz"])
    time.sleep(0.5)
    page.locator("#companycity").fill(c["ort"])
    time.sleep(1)
    try:
        page.locator("#citylist li").first.click(timeout=3000)
        time.sleep(0.5)
    except PlaywrightTimeout:
        pass

    if c["telpre"] and c["telnummer"]:
        page.locator("#companytelpre").fill(c["telpre"])
        time.sleep(0.3)
        page.locator("#companytelnumber").fill(c["telnummer"])
        time.sleep(0.3)

    if c["mobtelpre"] and c["mobtelnummer"]:
        page.locator("#companymobtelpre").fill(c["mobtelpre"])
        time.sleep(0.3)
        page.locator("#companymobtelnumber").fill(c["mobtelnummer"])
        time.sleep(0.3)

    if c["website"]:
        page.locator("#companyurl").fill(c["website"])
        time.sleep(0.3)
    if c["email"]:
        page.locator("#companyemail").fill(c["email"])
        time.sleep(0.3)
    if c["facebook"]:
        page.locator("#socfacebook").fill(c["facebook"])
        time.sleep(0.3)
    if c["instagram"]:
        page.locator("#socinstagram").fill(c["instagram"])
        time.sleep(0.3)

    page.locator("#rubric").fill(c["branche"])
    time.sleep(2)
    try:
        page.locator("#rubriclist li").first.click(timeout=4000)
        print(f"  OK Branche aus Dropdown gewaehlt")
    except PlaywrightTimeout:
        print(f"  - Branche Dropdown nicht erschienen, Enter druecken")
        page.locator("#rubric").press("Enter")
    time.sleep(0.5)

    page.locator("#SubmitForward").click()
    time.sleep(2)
    print("  OK Schritt 1 abgeschlossen")

    # Schritt 2: Oeffnungszeiten + Logo (ueberspringen)
    page.wait_for_selector("text=Schritt 2 von 4", timeout=15000)
    time.sleep(0.5)
    page.locator("#SubmitForward").click()
    time.sleep(2)
    print("  OK Schritt 2 uebersprungen")

    # Schritt 3: Zahlungsmethoden + Beschreibung
    page.wait_for_selector("text=Schritt 3 von 4", timeout=15000)
    time.sleep(0.5)
    if c["beschreibung"]:
        page.locator("#freetext").fill(c["beschreibung"][:500])
        time.sleep(0.3)
    page.locator("#SubmitForward").click()
    time.sleep(2)
    print("  OK Schritt 3 abgeschlossen")

    # Schritt 4: Vorschau + Ansprechpartner
    page.wait_for_selector("text=Schritt 4 von 4", timeout=15000)
    time.sleep(1)

    ids4 = page.evaluate("() => Array.from(document.querySelectorAll('input')).filter(i => i.offsetParent !== null && i.type !== 'hidden' && i.type !== 'submit' && i.type !== 'checkbox').map(i => i.id + '/' + i.name)")
    print(f"  DEBUG Schritt4 Inputs: {ids4}")

    page.locator("#contactfirstname").fill(c["kontakt_vorname"])
    time.sleep(0.3)
    page.locator("#contactlastname").fill(c["kontakt_nachname"])
    time.sleep(0.3)
    page.locator("#contactprefixnumber").fill(c["kontakt_telpre"])
    time.sleep(0.3)
    page.locator("#contactcallnumber").fill(c["kontakt_telnummer"])
    time.sleep(0.3)
    page.locator("#contactemail").fill(c["kontakt_email"])
    time.sleep(0.5)

    page.locator("#SubmitForward").click()
    time.sleep(3)
    print("  OK Eintrag abgesendet!")
    print(f"\n  E-Mail geht an: {c['kontakt_email']}")
    print("  Ansprechpartner muss den Link bestaetigen.")


def main():
    print("=" * 55)
    print("Das Oertliche Automatisierung")
    print("=" * 55)

    c = get_data()

    try:
        validiere(c)
    except ValueError as e:
        print(f"\nFehler: {e}")
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
            print(f"\nFehler: {e}")
            raise
        finally:
            browser.close()


if __name__ == "__main__":
    main()
