"""Exercise the offline player in headless Chromium with development clips only."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile


def check(folder, browser):
    html = (folder / "player/index.html").read_text(encoding="utf-8")
    if '"split": "development"' not in html:
        raise ValueError("Player smoke requires development stimuli")
    key = json.loads((folder / "zuordnung.json").read_bytes())
    assert len(key) == 7 and all((folder / "player" / (k+".wav")).is_file() for k in key)
    script = """<script>
    let captured;
    URL.createObjectURL = blob => { captured = blob; return 'about:blank'; };
    HTMLAnchorElement.prototype.click = () => {};
    document.querySelector('#save').click();
    if(captured) throw Error('Incomplete export');
    document.querySelectorAll('input').forEach((e,i) => {
      e.value=i===6?100:i; e.dispatchEvent(new Event('input',{bubbles:true}));
    });
    document.querySelector('#save').click();
    captured.text().then(s=>{
      let x=JSON.parse(s), values=Object.values(x.ratings).map(r=>r.score);
      if(x.split==='development' && x.person==='Demo' && x.session_id==='EXPECTED_SESSION' && values.length===7 &&
         values.includes(0) && values.includes(100) && Date.parse(x.completed_at))
          document.title='P11 pilot passed';
    });
    </script>"""
    key_hash = hashlib.sha256(json.dumps(key, sort_keys=True).encode()).hexdigest()
    script = script.replace("EXPECTED_SESSION", key_hash)
    with tempfile.TemporaryDirectory() as scratch:
        path = Path(scratch) / "pilot.html"
        path.write_text(html.replace("</html>", script+"</html>"), encoding="utf-8")
        result = subprocess.run([str(browser), "--headless", "--disable-gpu", "--no-first-run",
                     "--user-data-dir="+str(Path(scratch)/"profile"), "--virtual-time-budget=4000",
                     "--dump-dom", path.as_uri()], capture_output=True, timeout=90, check=True)
        if b"<title>P11 pilot passed</title>" not in result.stdout:
            raise ValueError("Development export did not pass the browser check")
    print("Seven blind development labels, incomplete export blocked, scores 0 through 100 exported.")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("folder", type=Path)
    p.add_argument("--browser", type=Path, default=Path("C:/Program Files/Google/Chrome/Application/chrome.exe"))
    args = p.parse_args()
    check(args.folder, args.browser)
