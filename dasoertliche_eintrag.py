
Search logs
1s
1s
0s
13s
43s
Run python dasoertliche_eintrag.py
=======================================================
Das Oertliche Automatisierung
=======================================================

Starte Eintrag fuer: Opopumfrima
  OK Cookie-Banner entfernt
  OK Grundeintrag gewaehlt

Fehler: Locator.click: Timeout 30000ms exceeded.
Call log:
  - waiting for locator("#companystreet")
    - locator resolved to <input value="" type="text" id="companystreet" name="companystreet" class="long simple part1  error"/>
  - attempting click action
    2 × waiting for element to be visible, enabled and stable
      - element is visible, enabled and stable
      - scrolling into view if needed
      - done scrolling
      - <div id="cmpwrapper" class="cmpwrapper"></div> intercepts pointer events
    - retrying click action
    - waiting 20ms
    2 × waiting for element to be visible, enabled and stable
      - element is visible, enabled and stable
      - scrolling into view if needed
Traceback (most recent call last):
  File "/home/runner/work/dasoertliche-automation/dasoertliche-automation/dasoertliche_eintrag.py", line 246, in <module>
    main()
  File "/home/runner/work/dasoertliche-automation/dasoertliche-automation/dasoertliche_eintrag.py", line 235, in main
    fill_form(page, c)
  File "/home/runner/work/dasoertliche-automation/dasoertliche-automation/dasoertliche_eintrag.py", line 101, in fill_form
    tippe(page, "#companystreet", c["strasse"])
  File "/home/runner/work/dasoertliche-automation/dasoertliche-automation/dasoertliche_eintrag.py", line 70, in tippe
    locator.click()
  File "/opt/hostedtoolcache/Python/3.11.14/x64/lib/python3.11/site-packages/playwright/sync_api/_generated.py", line 15631, in click
      - done scrolling
      - <div id="cmpwrapper" class="cmpwrapper"></div> intercepts pointer events
    - retrying click action
      - waiting 100ms
    58 × waiting for element to be visible, enabled and stable
       - element is visible, enabled and stable
       - scrolling into view if needed
       - done scrolling
       - <div id="cmpwrapper" class="cmpwrapper"></div> intercepts pointer events
     - retrying click action
       - waiting 500ms

    self._sync(
  File "/opt/hostedtoolcache/Python/3.11.14/x64/lib/python3.11/site-packages/playwright/_impl/_sync_base.py", line 115, in _sync
    return task.result()
           ^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.11.14/x64/lib/python3.11/site-packages/playwright/_impl/_locator.py", line 162, in click
    return await self._frame._click(self._selector, strict=True, **params)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.11.14/x64/lib/python3.11/site-packages/playwright/_impl/_frame.py", line 566, in _click
    await self._channel.send("click", self._timeout, locals_to_params(locals()))
  File "/opt/hostedtoolcache/Python/3.11.14/x64/lib/python3.11/site-packages/playwright/_impl/_connection.py", line 69, in send
    return await self._connection.wrap_api_call(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.11.14/x64/lib/python3.11/site-packages/playwright/_impl/_connection.py", line 559, in wrap_api_call
    raise rewrite_error(error, f"{parsed_st['apiName']}: {error}") from None
playwright._impl._errors.TimeoutError: Locator.click: Timeout 30000ms exceeded.
Call log:
  - waiting for locator("#companystreet")
    - locator resolved to <input value="" type="text" id="companystreet" name="companystreet" class="long simple part1  error"/>
  - attempting click action
    2 × waiting for element to be visible, enabled and stable
      - element is visible, enabled and stable
      - scrolling into view if needed
      - done scrolling
      - <div id="cmpwrapper" class="cmpwrapper"></div> intercepts pointer events
    - retrying click action
    - waiting 20ms
    2 × waiting for element to be visible, enabled and stable
      - element is visible, enabled and stable
      - scrolling into view if needed
      - done scrolling
      - <div id="cmpwrapper" class="cmpwrapper"></div> intercepts pointer events
    - retrying click action
      - waiting 100ms
    58 × waiting for element to be visible, enabled and stable
       - element is visible, enabled and stable
       - scrolling into view if needed
       - done scrolling
       - <div id="cmpwrapper" class="cmpwrapper"></div> intercepts pointer events
     - retrying click action
       - waiting 500ms

Error: Process completed with exit code 1.
