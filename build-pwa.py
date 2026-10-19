"""Refresh the offline cache version after changing application assets."""
from pathlib import Path
import hashlib,re
root=Path(__file__).parent/'dist'
files=['index.html','menu.json','pwa.js','manifest.webmanifest']
version=hashlib.sha256(b''.join((root/name).read_bytes() for name in files)).hexdigest()[:12]
p=root/'sw.js';s=p.read_text();s=re.sub(r"const CACHE_NAME = CACHE_PREFIX \+ '[^']+';",f"const CACHE_NAME = CACHE_PREFIX + '{version}';",s);p.write_text(s)
print('PWA cache version:',version)
