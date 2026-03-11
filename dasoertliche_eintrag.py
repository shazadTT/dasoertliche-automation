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
    # Schritt 1: Button klicken falls sichtbar
    try:
        page.wait_for_selector("button:has-text('Ablehnen')", timeout=6000)
        page.click("button:has-text('Ablehnen')")
        time.sleep(1.5)
        print("  OK Cookie-Banner per Button abgelehnt")
    except PlaywrightTimeout:
        try:
            page.wait_for_selector("button:has-text('Alle Akzeptieren')", timeout=3000)
            page.click("button:has-text('Alle Akzeptieren')")
            time.sleep(1.5)
            print("  OK Cookie-Banner akzeptiert")
        except PlaywrightTimeout:
            print("  - Kein Cookie-Button gefunden")

    # Schritt 2: cmpwrapper IMMER aus DOM entfernen (blockiert sonst Klicks)
    page.evaluate("""
        () => {
            const selectors = [
                '#cmpwrapper', '.cmpwrapper',
                '#usercentrics-root',
                '[id*="cmp"]', '[class*="cmpwrap"]'
            ];
            selectors.forEach(sel => {
                document.querySelectorAll(sel).forEach(el => el.remove());
            });
            document.body.style.overflow = 'auto';
            document.documentElement.style.overflow = 'auto';
        }
    """)
    time.sleep(0.5)
    print("  OK cmpwrapper entfernt")


def tippe(page, selector, wert):
    """Tippt Text ein und loest JS-Validierung aus."""
    locator = page.locator(selector)
    locator.click()
    time.sleep(0.2)
    locator.fill("")
    # type() unterstuetzt Sonderzeichen wie ae, oe, ue, ss
    page.keyboard.type(wert, delay=50)
    page.keyboard.press("Tab")
    time.sleep(0.3)


def fill_form(page, c):
    print(f"\nStarte Eintrag fuer: {c['firma']}")

    page.goto("https://services.dasoertliche.de/services/schnupperpaket/sp/")
    page.wait_for_load_state("networkidle")
    time.sleep(3)

    cookie_banner_schliessen(page)

    # Grundeintrag waehlen
    page.wait_for_selector("text=Los geht's", timeout=15000)
    page.click("text=Los geht's")
    time.sleep(2)
    print("  OK Grundeintrag gewaehlt")

    # Schritt 1: Adresse
    page.wait_for_selector("#companyname", timeout=15000)
    time.sleep(1)

    # cmpwrapper nochmal entfernen - wird nach Seitennavigation neu geladen
    page.evaluate("""
        () => {
            document.querySelectorAll('#cmpwrapper, .cmpwrapper, [id*="cmp"]')
                .forEach(el => el.remove());
            document.body.style.overflow = 'auto';
        }
    """)
    # MutationObserver: verhindert dass cmpwrapper wieder erscheint
    page.evaluate("""
        () => {
            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    mutation.addedNodes.forEach((node) => {
                        if (node.id && node.id.includes('cmp')) {
                            node.remove();
                        }
                        if (node.className && typeof node.className === 'string' && node.className.includes('cmp')) {
                            node.remove();
                        }
                    });
                });
            });
            observer.observe(document.body, { childList: true, subtree: true });
        }
    """)
    time.sleep(0.5)

    # Adresse befuellen - Telefon-Felder werden danach freigeschaltet
    tippe(page, "#companyname", c["firma"])
    tippe(page, "#companystreet", c["strasse"])
    if c["hausnummer"]:
        tippe(page, "#companyhnr", c["hausnummer"])
    tippe(page, "#companypc", c["plz"])

    # PLZ zuerst - loest Ortssuche aus
    page.locator("#companypc").click()
    time.sleep(0.2)
    page.locator("#companypc").fill("")
    page.keyboard.type(c["plz"], delay=100)
    time.sleep(2)

    # Ort befuellen und Dropdown abwarten
    page.locator("#companycity").click()
    time.sleep(0.3)
    page.locator("#companycity").fill("")
    page.keyboard.type(c["ort"], delay=80)
    time.sleep(2)

    # Dropdown-Eintrag waehlen
    try:
        page.wait_for_selector("#citylist li", timeout=5000)
        page.locator("#citylist li").first.click()
        print("  OK Ort aus Dropdown gewaehlt")
        time.sleep(1)
    except PlaywrightTimeout:
        # Fallback: PLZ und Ort nochmal direkt setzen + Enter
        page.locator("#companypc").fill(c["plz"])
        time.sleep(0.3)
        page.locator("#companycity").fill(c["ort"])
        time.sleep(0.3)
        page.locator("#companycity").press("Enter")
        print("  - Ort per Enter bestaetigt")
        time.sleep(1)

    # Warten bis Telefon-Felder enabled werden (max 15 Sekunden)
    print("  Warte auf Freischaltung der Telefon-Felder...")
    try:
        page.wait_for_selector("#companytelpre:not([disabled])", timeout=15000)
        print("  OK Telefon-Felder freigeschaltet")
    except PlaywrightTimeout:
        # Telefon per JavaScript aktivieren
        print("  - Aktiviere Telefon-Felder per JS...")
        page.evaluate("""
            () => {
                document.querySelectorAll('.part2').forEach(el => {
                    el.removeAttribute('disabled');
                    el.classList.remove('disabled');
                });
                document.querySelectorAll('.inputwrap.disabled').forEach(el => {
                    el.classList.remove('disabled');
                });
            }
        """)
        time.sleep(0.5)

    # Telefon befuellen
    if c["telpre"] and c["telnummer"]:
        tippe(page, "#companytelpre", c["telpre"])
        tippe(page, "#companytelnumber", c["telnummer"])

    if c["mobtelpre"] and c["mobtelnummer"]:
        tippe(page, "#companymobtelpre", c["mobtelpre"])
        tippe(page, "#companymobtelnumber", c["mobtelnummer"])

    # Optional - Website
    if c["website"]:
        tippe(page, "#companyurl", c["website"])

    # E-Mail - Pflichtfeld, nach Telefon befuellen (erst dann ist es enabled)
    email_fuer_formular = c["email"] if c["email"] else c["kontakt_email"]
    tippe(page, "#companyemail", email_fuer_formular)

    if c["facebook"]:
        tippe(page, "#socfacebook", c["facebook"])
    if c["instagram"]:
        tippe(page, "#socinstagram", c["instagram"])

    # Branche - keyboard.type fuer Sonderzeichen, dann Dropdown
    page.locator("#rubric").click()
    time.sleep(0.2)
    page.locator("#rubric").fill("")
    page.keyboard.type(c["branche"], delay=80)
    time.sleep(2)
    try:
        page.wait_for_selector("#rubriclist li", timeout=4000)
        page.locator("#rubriclist li").first.click()
        print(f"  OK Branche aus Dropdown gewaehlt")
    except PlaywrightTimeout:
        branche_val = c["branche"].replace("'", "\'")
        page.evaluate(f"""
            () => {{
                document.getElementById('rubric').value = '{branche_val}';
                const rubricid = document.getElementById('rubricid');
                if (rubricid) rubricid.value = '0000001';
            }}
        """)
        print(f"  - Branche per JS gesetzt")
    time.sleep(0.5)
    # Ausführlicher Debug vor Submit
    email_aktuell = page.evaluate("() => { const el = document.getElementById('companyemail'); return el ? el.value + ' (disabled:' + el.disabled + ')' : 'nicht gefunden'; }")
    print(f"  DEBUG E-Mail im Feld: {email_aktuell}")
    alle_fehler = page.evaluate("() => Array.from(document.querySelectorAll('.uups p, .error-message, [class*=uups]')).map(e => e.textContent.trim()).join(' | ')")
    print(f"  DEBUG alle Fehler: {alle_fehler}")
    submit_status = page.evaluate("() => { const el = document.getElementById('SubmitForward'); return el ? 'disabled:' + el.disabled : 'nicht gefunden'; }")
    print(f"  DEBUG Submit: {submit_status}")

    # Weiter - erst normaler Klick versuchen, dann JS-Fallback
    try:
        page.locator("#SubmitForward:not([disabled])").click(timeout=5000)
        print("  OK Weiter geklickt")
    except PlaywrightTimeout:
        print("  - Weiter disabled, versuche JS-Klick")
        page.evaluate("document.getElementById('SubmitForward').removeAttribute('disabled')")
        time.sleep(0.3)
        page.evaluate("document.getElementById('SubmitForward').click()")
    time.sleep(3)
    page.evaluate("document.querySelectorAll('#cmpwrapper, .cmpwrapper').forEach(el => el.remove())")
    time.sleep(0.5)

    aktuell = page.evaluate("() => document.querySelector('h1') ? document.querySelector('h1').textContent.trim() : ''")
    print(f"  DEBUG aktuelle Seite: {aktuell}")
    print("  OK Schritt 1 abgeschlossen")



    # Schritt 2: Oeffnungszeiten + Logo (ueberspringen)
    page.wait_for_selector("text=Schritt 2 von 4", timeout=20000)
    time.sleep(0.5)
    page.evaluate("document.getElementById('SubmitForward').click()")
    time.sleep(3)
    page.evaluate("document.querySelectorAll('#cmpwrapper, .cmpwrapper').forEach(el => el.remove())")
    time.sleep(0.5)
    print("  OK Schritt 2 uebersprungen")

    # Schritt 3: Zahlungsmethoden + Beschreibung
    page.wait_for_selector("text=Schritt 3 von 4", timeout=20000)
    time.sleep(0.5)
    if c["beschreibung"]:
        page.locator("#freetext").fill(c["beschreibung"][:500])
        time.sleep(0.3)
    page.evaluate("document.getElementById('SubmitForward').click()")
    time.sleep(3)
    page.evaluate("document.querySelectorAll('#cmpwrapper, .cmpwrapper').forEach(el => el.remove())")
    time.sleep(0.5)
    print("  OK Schritt 3 abgeschlossen")

    # Schritt 4: Vorschau + Ansprechpartner
    page.wait_for_selector("text=Schritt 4 von 4", timeout=20000)
    time.sleep(1)
    page.evaluate("document.querySelectorAll('#cmpwrapper, .cmpwrapper').forEach(el => el.remove())")
    time.sleep(0.5)

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

    page.evaluate("document.getElementById('SubmitForward').removeAttribute('disabled')")
    time.sleep(0.3)
    page.evaluate("document.getElementById('SubmitForward').click()")
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
