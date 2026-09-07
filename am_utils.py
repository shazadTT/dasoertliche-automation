"""
am_utils – gemeinsame Hilfsfunktionen für alle A&M Portal-Eintrags-Skripte.

Enthält:
  - normalisiere_daten(c)   : PLZ/Ort-Vertauschung korrigieren, Telefon normalisieren,
                              Whitespace säubern, Website-Schema ergänzen
  - pruefe_deutsche_plz(plz): klare Fehlermeldung bei AT/CH/LU-Adressen
  - branche_kandidaten(...) : Suchbegriffe pro Portal (Synonym-Mapping)
  - beste_option(...)       : robuste Auswahl der passendsten Dropdown-Option
  - split_telefon(...)      : Vorwahl / Rufnummer trennen

Diese Datei ist in allen Repos identisch – Änderungen bitte überall einspielen.
"""

import re

# ─────────────────────────────────────────────────────────────────────────────
# PLZ / ORT
# ─────────────────────────────────────────────────────────────────────────────

_PLZ_RE = re.compile(r"^\d{5}$")
_PLZ_ORT_RE = re.compile(r"^\s*(\d{4,5})\s+(.+?)\s*$")         # "30159 Hannover"
_ORT_PLZ_RE = re.compile(r"^\s*(.+?)[\s,]+(\d{4,5})\s*$")      # "Hannover 30159" / "Hannover, 30159"


def _clean(s):
    return re.sub(r"\s+", " ", str(s or "")).strip()


def korrigiere_plz_ort(plz, ort):
    """
    Sorgt dafür, dass PLZ immer die Postleitzahl und ORT immer der Ortsname ist –
    egal wie die Daten aus Zapier/HubSpot ankommen.

    Behandelt:
      - vertauschte Felder            PLZ='Marl'            ORT='45770'
      - beides in einem Feld          PLZ='45770 Marl'      ORT=''
      - beides in einem Feld (andersrum) PLZ=''             ORT='45770 Marl'
      - Ort mit PLZ hinten            ORT='Marl 45770'
      - führende Nullen verloren      PLZ='6110' (Excel)   -> '06110' (nur bei DE-typischer 4-Ziffer + Ort in DE)
      - Whitespace/Sonderzeichen
    Gibt (plz, ort, hinweise[]) zurück.
    """
    hinweise = []
    plz = _clean(plz)
    ort = _clean(ort)

    plz_ist_zahl = bool(re.fullmatch(r"\d{4,5}", plz))
    ort_ist_zahl = bool(re.fullmatch(r"\d{4,5}", ort))

    # 1) glatt vertauscht
    if not plz_ist_zahl and ort_ist_zahl:
        plz, ort = ort, plz
        hinweise.append(f"PLZ/Ort waren vertauscht -> PLZ={plz}, Ort={ort}")
        plz_ist_zahl, ort_ist_zahl = True, False

    # 2) kombiniert in einem Feld
    if not plz_ist_zahl:
        m = _PLZ_ORT_RE.match(plz) or _ORT_PLZ_RE.match(plz)
        if m:
            a, b = m.group(1), m.group(2)
            neu_plz, neu_ort = (a, b) if a.isdigit() else (b, a)
            if not ort or ort.isdigit():
                ort = neu_ort
            plz = neu_plz
            hinweise.append(f"PLZ-Feld enthielt 'PLZ Ort' -> PLZ={plz}, Ort={ort}")
            plz_ist_zahl = True

    if (not plz or not plz_ist_zahl) and ort:
        m = _PLZ_ORT_RE.match(ort) or _ORT_PLZ_RE.match(ort)
        if m:
            a, b = m.group(1), m.group(2)
            neu_plz, neu_ort = (a, b) if a.isdigit() else (b, a)
            plz, ort = neu_plz, neu_ort
            hinweise.append(f"Ort-Feld enthielt 'PLZ Ort' -> PLZ={plz}, Ort={ort}")
            plz_ist_zahl = True

    # 3) Ort enthält zusätzlich noch die PLZ ("45770 Marl") obwohl PLZ schon korrekt ist
    if plz_ist_zahl and ort:
        m = _PLZ_ORT_RE.match(ort) or _ORT_PLZ_RE.match(ort)
        if m:
            a, b = m.group(1), m.group(2)
            nur_ort = b if a.isdigit() else a
            if nur_ort and not nur_ort.isdigit():
                ort = nur_ort
                hinweise.append(f"PLZ aus Ort-Feld entfernt -> Ort={ort}")

    # 4) führende Null verloren (z.B. '6110' Halle) – 4-stellig, aber deutscher Ort
    if re.fullmatch(r"\d{4}", plz) and ort and not _ist_dach_nachbar(ort):
        plz = "0" + plz
        hinweise.append(f"Führende Null ergänzt -> PLZ={plz}")

    return plz, ort, hinweise


_AT_CH_HINWEISE = ("langenzersdorf", "wien", "graz", "linz", "salzburg", "innsbruck",
                   "zürich", "zuerich", "bern", "basel", "luzern", "mönchaltorf", "winterthur",
                   "luxemburg", "luxembourg")


def _ist_dach_nachbar(ort):
    o = ort.lower()
    return any(h in o for h in _AT_CH_HINWEISE)


def pruefe_deutsche_plz(plz, ort=""):
    """Wirft ValueError mit klarer, verständlicher Meldung wenn keine deutsche PLZ vorliegt."""
    if not _PLZ_RE.match(plz or ""):
        if re.fullmatch(r"\d{4}", plz or ""):
            raise ValueError(
                f"PLZ-Format ungültig: '{plz}' ({ort}) – 4-stellig, vermutlich Österreich/Schweiz. "
                f"Das Portal nimmt nur deutsche Adressen an."
            )
        raise ValueError(f"PLZ-Format ungültig: '{plz}' – erwartet 5 Ziffern (DE)")


# ─────────────────────────────────────────────────────────────────────────────
# TELEFON
# ─────────────────────────────────────────────────────────────────────────────

# 3-stellige deutsche Ortsvorwahlen (alle anderen Festnetz-Vorwahlen sind 4- oder 5-stellig)
_VORWAHL_3 = {"030", "040", "069", "089"}
# 5-stellige Vorwahlen beginnen mit diesen 4 Ziffern (Auszug – Rest wird 4-stellig angenommen)
# Faustregel: Vorwahlen 02xxx/03xxx… mit 5 Stellen kommen aus dem Ziffernblock 0x2.. bis 0x9..
# Wir verwenden das offizielle Schema: 2. Ziffer 2-9, 3. Ziffer 2-9  -> 5-stellig,
# 3. Ziffer 0/1 -> 4-stellig (z.B. 0201 Essen, 0511 Hannover, 0711 Stuttgart, 0221 Köln)
# Ausnahmen (4-stellig trotz 3. Ziffer 2-9) sind selten (z.B. 0621, 0631, 0641 …) -> Liste:
_VORWAHL_4_AUSNAHMEN = {
    "0621", "0631", "0641", "0651", "0661", "0681", "0721", "0731", "0741", "0751", "0761",
    "0771", "0781", "0791", "0821", "0831", "0841", "0851", "0861", "0871", "0881", "0906",
    "0921", "0931", "0941", "0951", "0961", "0971", "0981", "0991", "0521", "0531", "0541",
    "0551", "0561", "0571", "0581", "0591", "0421", "0431", "0441", "0451", "0461", "0471",
    "0481", "0491", "0331", "0335", "0340", "0341", "0345", "0351", "0355", "0361", "0365",
    "0371", "0375", "0381", "0385", "0391", "0395", "0221", "0228", "0231", "0234", "0241",
    "0251", "0261", "0271", "0281", "0291", "0202", "0203", "0208", "0209", "0211", "0212",
    "0214", "0201", "0511", "0611", "0711", "0911", "0921", "0231", "0233", "0203",
}


def normalisiere_telefon(nummer):
    """
    Bringt eine Telefonnummer in nationales Format '0…' (nur Ziffern).
      '+49 511 123456'   -> '0511123456'
      '0049511123456'    -> '0511123456'
      '49511123456'      -> '0511123456'
      '511123456'        -> '0511123456'   (führende 0 vergessen)
      '15209054298'      -> '015209054298' (Mobil ohne 0)
      '0152 545226 23'   -> '015254522623'
    Ausländische Nummern (+41, +43, …) bleiben im Format '00xx…' erhalten.
    """
    if not nummer:
        return ""
    n = str(nummer).strip()
    n = re.sub(r"[^\d+]", "", n)
    if n.startswith("+"):
        n = "00" + n[1:]
    if n.startswith("0049"):
        n = "0" + n[4:]
    elif n.startswith("49") and len(n) >= 10 and not n.startswith("490"):
        # '49511…' ohne Plus – aber nicht '0490…' o.ä.
        n = "0" + n[2:]
    elif n.startswith("00"):
        return n  # anderes Land – unverändert lassen
    elif not n.startswith("0"):
        n = "0" + n
    return n


def ist_deutsche_nummer(nummer):
    n = normalisiere_telefon(nummer)
    return bool(n) and n.startswith("0") and not n.startswith("00")


def ist_mobil(nummer):
    n = normalisiere_telefon(nummer)
    return n.startswith(("015", "016", "017"))


def split_telefon(nummer, vorwahl=""):
    """
    Liefert (vorwahl, rufnummer). Wenn eine Vorwahl mitgegeben wurde, wird sie
    nur normalisiert (führende 0 ergänzt). Sonst wird die Vorwahl heuristisch
    aus der Gesamtnummer abgetrennt.
    """
    vorwahl = re.sub(r"\D", "", str(vorwahl or ""))
    nummer_norm = normalisiere_telefon(nummer)

    if vorwahl:
        if not vorwahl.startswith("0"):
            vorwahl = "0" + vorwahl
        rest = re.sub(r"\D", "", str(nummer or ""))
        # Falls die Rufnummer versehentlich die Vorwahl nochmal enthält
        if rest.startswith(vorwahl):
            rest = rest[len(vorwahl):]
        elif rest.startswith(vorwahl.lstrip("0")) and len(rest) > 8:
            rest = rest[len(vorwahl.lstrip("0")):]
        return vorwahl, rest.lstrip("0") if len(rest) > 3 else rest

    if not nummer_norm or nummer_norm.startswith("00"):
        return "", re.sub(r"\D", "", str(nummer or ""))

    if ist_mobil(nummer_norm):
        return nummer_norm[:4], nummer_norm[4:]
    if nummer_norm[:3] in _VORWAHL_3:
        return nummer_norm[:3], nummer_norm[3:]
    if nummer_norm[:4] in _VORWAHL_4_AUSNAHMEN:
        return nummer_norm[:4], nummer_norm[4:]
    if len(nummer_norm) >= 4 and nummer_norm[2] in "01":
        return nummer_norm[:4], nummer_norm[4:]
    if len(nummer_norm) >= 11:
        return nummer_norm[:5], nummer_norm[5:]
    return nummer_norm[:4], nummer_norm[4:]


# ─────────────────────────────────────────────────────────────────────────────
# GESAMT-NORMALISIERUNG
# ─────────────────────────────────────────────────────────────────────────────

def normalisiere_daten(c, log=print):
    """
    Wird direkt nach get_data() aufgerufen. Korrigiert das Dict IN PLACE:
      - PLZ/Ort
      - Telefonfelder (telefon, kontakt_telefon, kontakt_mobil, telpre/telnummer, mobtelpre/mobtelnummer …)
      - Whitespace
      - Website-Schema
    """
    for k, v in list(c.items()):
        if isinstance(v, str):
            c[k] = _clean(v)

    if "plz" in c or "ort" in c:
        plz, ort, hinweise = korrigiere_plz_ort(c.get("plz", ""), c.get("ort", ""))
        c["plz"], c["ort"] = plz, ort
        for h in hinweise:
            log(f"  ~ Korrektur: {h}")

    # Vollständige Telefonnummern
    for feld in ("telefon", "kontakt_telefon", "kontakt_mobil", "mobil"):
        if c.get(feld):
            neu = normalisiere_telefon(c[feld])
            if neu != re.sub(r"\D", "", c[feld]):
                log(f"  ~ Korrektur: {feld} '{c[feld]}' -> '{neu}'")
            c[feld] = neu

    # Getrennte Vorwahl/Rufnummer-Paare
    for pre, num in (("telpre", "telnummer"), ("mobtelpre", "mobtelnummer"),
                     ("kontakt_telpre", "kontakt_telnummer")):
        if pre in c or num in c:
            if c.get(num) and not c.get(pre):
                vw, rn = split_telefon(c[num])
                log(f"  ~ Korrektur: {pre} fehlte -> aus {num} abgeleitet: {vw} / {rn}")
                c[pre], c[num] = vw, rn
            elif c.get(pre):
                vw, rn = split_telefon(c.get(num, ""), c[pre])
                if vw != c.get(pre) or rn != c.get(num):
                    log(f"  ~ Korrektur: {pre}/{num} '{c.get(pre)}'/'{c.get(num)}' -> '{vw}'/'{rn}'")
                c[pre], c[num] = vw, rn

    for feld in ("website", "url"):
        w = c.get(feld, "")
        if w and w.lower() in ("keine", "nein", "-", "n/a", "none", "null"):
            c[feld] = ""
        elif w and not w.lower().startswith(("http://", "https://")):
            c[feld] = "https://" + w

    for feld in ("email", "kontakt_email"):
        if c.get(feld):
            c[feld] = c[feld].lower()

    return c


# ─────────────────────────────────────────────────────────────────────────────
# BRANCHEN
# ─────────────────────────────────────────────────────────────────────────────

# Generische Synonyme (Reihenfolge = Priorität). Der Original-Begriff wird immer zuerst probiert.
_SYNONYME = {
    "rohrreinigung":        ["Rohrreinigung", "Kanalreinigung", "Rohr- und Kanalreinigung", "Sanitärinstallation"],
    "kanalreinigung":       ["Kanalreinigung", "Rohrreinigung"],
    "abdichtung":           ["Abdichtarbeiten", "Abdichtungstechnik", "Abdichten", "Bauwerksabdichtung", "Bautenschutz"],
    "bauwerksabdichtung":   ["Bauwerksabdichtung", "Abdichtarbeiten", "Abdichtungstechnik", "Abdichten", "Bautenschutz"],
    "innenabdichtung":      ["Innenabdichtung", "Abdichtarbeiten", "Abdichtungstechnik", "Abdichten",
                             "Kellerabdichtungen", "Kellerisolierungen", "Bautenschutz"],
    "kellerabdichtung":     ["Kellerabdichtungen", "Kellerabdichtung", "Abdichtungstechnik", "Kellerisolierungen",
                             "Kellertrockenlegung", "Abdichtarbeiten", "Abdichten", "Bautenschutz"],
    "kellersanierung":      ["Kellersanierungen", "Kellersanierung", "Kellertrockenlegung", "Kellerabdichtungen", "Bausanierung"],
    "bautenschutz":         ["Bautenschutz", "Abdichtarbeiten"],
    "photovoltaikanlage":   ["Photovoltaik", "Photovoltaikanlagen", "Solaranlagen", "Solartechnik", "Solarstrom"],
    "photovoltaik":         ["Photovoltaik", "Photovoltaikanlagen", "Solaranlagen", "Solartechnik"],
    "solaranlage":          ["Solaranlagen", "Solartechnik", "Photovoltaik", "Solarthermie"],
    "sanierungsarbeiten":   ["Sanierungsarbeiten", "Bausanierung", "Bausanierungen", "Altbausanierung", "Bauunternehmen"],
    "haussanierung":        ["Bausanierung", "Bausanierungen", "Altbausanierung", "Sanierungsarbeiten", "Bauunternehmen"],
    "sanierung":            ["Sanierungsarbeiten", "Bausanierung", "Altbausanierung", "Bauunternehmen"],
    "schimmelsanierung":    ["Schimmelpilzbekämpfung", "Schimmelsanierung", "Schimmelpilzsanierung", "Bautenschutz"],
    "badsanierung":         ["Badsanierung", "Badsanierungen", "Bäder", "Sanitärinstallation", "Sanitär", "Installateur"],
    "bodensanierung":       ["Bodensanierung", "Bodenbeläge", "Bodenleger", "Fußbodenbau"],
    "terrassenüberdachung": ["Terrassenüberdachungen", "Terrassenüberdachung", "Überdachungen", "Terrassenbau"],
    "überdachung":          ["Überdachungen", "Terrassenüberdachungen"],
    "wärmepumpe":           ["Wärmepumpen", "Wärmepumpe", "Heizungsbau", "Heizung"],
    "heizung":              ["Heizungsbau", "Heizung", "Heizungs- und Lüftungsbau", "Sanitär- und Heizungstechnik"],
    "entrümpelung":         ["Entrümpelungen", "Entrümpelung", "Haushaltsauflösungen", "Entsorgung"],
    "fenster":              ["Fenster", "Fensterbau", "Fenster und Türen"],
    "maler":                ["Malerbetriebe", "Maler", "Malerfachbetrieb", "Maler und Lackierer"],
    "tischler":             ["Tischlereien", "Tischler", "Tischlerei", "Schreinerei"],
    "schreiner":            ["Schreinereien", "Schreiner", "Tischlereien", "Tischler"],
    "dachdecker":           ["Dachdeckereien", "Dachdecker", "Dachdeckerei", "Dachdeckerbetriebe"],
    "dachsanierung":        ["Dachsanierungen", "Dachsanierung", "Dachdeckereien", "Dachdecker"],
    "zimmerer":             ["Zimmereien", "Zimmerer", "Zimmerei", "Holzbau"],
    "gartenbau":            ["Garten- und Landschaftsbau", "Gartenbaubetriebe", "Gartenbau", "Gartengestaltung"],
    "spanndecke":           ["Spanndecken", "Spanndecke", "Deckengestaltung"],
    "innenausbau":          ["Innenausbau", "Trockenbau"],
    "ingenieur":            ["Ingenieurbüros", "Ingenieurbüro", "Ingenieurbüros: Bauwesen"],
    "elektriker":           ["Elektroinstallationen", "Elektriker", "Elektrotechnik"],
    "sanitär":              ["Sanitärinstallation", "Sanitär", "Installateur"],
}

# Portal-spezifische Kategorienamen (heute im jeweiligen Portal verifiziert).
# Diese werden VOR den generischen Synonymen probiert.
_PORTAL_SYNONYME = {
    "gelbeseiten": {
        "rohrreinigung":      ["Rohrreinigung"],
        "abdichtung":         ["Abdichtarbeiten"],
        "innenabdichtung":    ["Abdichtarbeiten", "Kellerabdichtungen"],
        "kellerabdichtung":   ["Kellerabdichtungen"],
        "photovoltaikanlage": ["Photovoltaik"],
        "sanierungsarbeiten": ["Sanierungsarbeiten"],
        "schimmelsanierung":  ["Schimmelpilzbekämpfung"],
    },
    "11880": {
        "rohrreinigung":      ["Rohrreinigung"],
        "abdichtung":         ["Abdichtungstechnik"],
        "innenabdichtung":    ["Abdichtungstechnik"],
        "kellerabdichtung":   ["Abdichtungstechnik", "Bautenschutz"],
        "photovoltaikanlage": ["Photovoltaik"],
        "solaranlage":        ["Solaranlagen"],
        "sanierungsarbeiten": ["Bauunternehmen", "Bautenschutz"],
        "haussanierung":      ["Bauunternehmen"],
        "schimmelsanierung":  ["Bautenschutz"],
        "gartenbau":          ["Garten- und Landschaftsbau"],
    },
    "telefonbuch": {
        "rohrreinigung":      ["Rohrreinigung"],
        "abdichtung":         ["Abdichtarbeiten"],
        "innenabdichtung":    ["Abdichtarbeiten", "Kellerabdichtungen"],
        "kellerabdichtung":   ["Kellerabdichtungen"],
        "photovoltaikanlage": ["Photovoltaik"],
        "sanierungsarbeiten": ["Sanierungsarbeiten"],
        "haussanierung":      ["Altbausanierungen", "Bausanierungen"],
        "schimmelsanierung":  ["Schimmelpilzbekämpfung"],
        "badsanierung":       ["Badsanierung", "Bäder", "Sanitärinstallationen"],
        "maler":              ["Malerbetriebe"],
        "tischler":           ["Tischlereien"],
        "gartenbau":          ["Gartenbaubetriebe"],
        "terrassenüberdachung": ["Terrassenüberdachungen"],
        "wärmepumpe":         ["Wärmepumpen"],
    },
    "opendi": {
        "rohrreinigung":      ["Rohrreinigung"],
        "abdichtung":         ["Abdichten"],
        "innenabdichtung":    ["Abdichten", "Kellerisolierungen"],
        "kellerabdichtung":   ["Kellerisolierungen", "Kellertrockenlegung", "Abdichten"],
        "photovoltaikanlage": ["Photovoltaik"],
        "sanierungsarbeiten": ["Sanierungsarbeiten", "Bausanierung"],
        "haussanierung":      ["Bausanierung", "Altbausanierung"],
        "schimmelsanierung":  ["Schimmelpilzbekämpfung"],
        "maler":              ["Maler"],
    },
    "dasoertliche": {},
}

# Optionen, die (fast) nie gemeint sind, wenn ein Handwerksbetrieb eingetragen wird
_STRAF_WOERTER = ("sachverständig", "rechtsanwalt", "rechtsanwälte", "fachanwalt", "gutachter",
                  "bedarf", "hersteller", "großhandel", "grosshandel", "zubehör", "verlag",
                  "schule", "verein", "kunstmaler", "porzellan", "solarium", "solarien",
                  "sektkeller", "kellerei", "insolvenz", "wohnmobil", "luftkanal",
                  "fahrrad", "schwimmbad", "tiefgarage", "notdienst", "wartung", "reinigung", "moden", "möbel", "planung")


def _norm(s):
    s = s.lower().strip()
    s = s.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def _stamm(s):
    """grobe Singular-/Pluralform angleichen: 'kellerabdichtungen' -> 'kellerabdichtung'"""
    s = _norm(s)
    for endung in ("ungen", "eien", "en", "e", "n", "s"):
        if s.endswith(endung) and len(s) - len(endung) >= 4:
            return s[: -len(endung)]
    return s


def branche_kandidaten(branche, portal=None):
    """
    Liefert die geordnete Liste der Suchbegriffe für die Branche im jeweiligen Portal.
    Der Original-Begriff steht immer an erster Stelle.
    """
    b = _clean(branche)
    key = b.lower()
    kand = [b]
    if portal:
        kand += _PORTAL_SYNONYME.get(portal, {}).get(key, [])
    kand += _SYNONYME.get(key, [])
    # Teilwort-Treffer im Synonym-Katalog (z.B. 'Kellerabdichtung GmbH')
    if key not in _SYNONYME:
        for k, v in _SYNONYME.items():
            if k in key or key in k:
                kand += v
    # Duplikate entfernen, Reihenfolge behalten
    seen, out = set(), []
    for k in kand:
        if k and k.lower() not in seen:
            seen.add(k.lower())
            out.append(k)
    return out


def bewerte_option(begriff, option):
    """Score 0..100 wie gut eine Dropdown-Option zum Suchbegriff passt."""
    if not option:
        return 0
    b, o = _norm(begriff), _norm(option)
    bs, os_ = _stamm(begriff), _stamm(option)
    score = 0
    if o == b or os_ == bs:
        return 100
    elif o.startswith(b) or os_.startswith(bs):
        score = 85 if len(o) <= len(b) + 4 else 72
    elif re.search(r"\b" + re.escape(b) + r"\b", o) or re.search(r"\b" + re.escape(bs), o):
        score = 70
    elif b in o or bs in o:
        score = 48
    elif len(b) >= 6 and (b[:6] in o):
        score = 35
    else:
        return 0
    if any(w in o and w not in b for w in _STRAF_WOERTER):
        score -= 40
    # kürzere Optionen sind i.d.R. die allgemeine Kategorie
    score -= min(len(o) // 12, 8)
    return max(score, 0)


def beste_option(begriff, optionen, min_score=50):
    """
    Wählt aus einer Liste von Dropdown-Texten die passendste Option.
    Gibt (text, score) zurück oder (None, 0) wenn nichts gut genug passt.
    """
    best, best_score = None, 0
    for opt in optionen:
        s = bewerte_option(begriff, opt)
        if s > best_score:
            best, best_score = opt, s
    if best_score >= min_score:
        return best, best_score
    return None, best_score


def waehle_branche(branche, optionen_fuer_begriff, portal=None, log=print, min_score=50):
    """
    Generische Branchen-Auswahl:
      optionen_fuer_begriff(begriff) -> Liste der angezeigten Dropdown-Texte für diesen Suchbegriff
    Probiert alle Kandidaten durch, bewertet ALLE gefundenen Optionen global
    (Score minus Kandidaten-Priorität) und gibt (gewaehlter_text, begriff) zurück
    oder (None, None). Ein exakter Treffer (Score 100) bricht sofort ab.
    """
    versucht = []
    global_best = (None, None, 0)
    for idx, begriff in enumerate(branche_kandidaten(branche, portal)):
        try:
            opts = [o for o in (optionen_fuer_begriff(begriff) or []) if o and o.strip()]
        except Exception as e:
            log(f"  – Branche '{begriff}': Fehler beim Laden der Vorschläge: {e}")
            opts = []
        versucht.append(f"{begriff}({len(opts)})")
        if not opts:
            continue
        treffer, score = beste_option(begriff, opts, min_score=1)
        if not treffer:
            continue
        eff = score - 3 * idx
        if score >= 100:
            log(f"  OK Branche: '{treffer}' (Suchbegriff '{begriff}', exakt)")
            return treffer, begriff
        if eff > global_best[2]:
            global_best = (treffer, begriff, eff)
    treffer, begriff, eff = global_best
    if treffer and eff >= min_score:
        log(f"  OK Branche: '{treffer}' (Suchbegriff '{begriff}', Score {eff})")
        return treffer, begriff
    log(f"  !! Branche '{branche}' nicht gefunden – versucht: {', '.join(versucht)}")
    return None, None
