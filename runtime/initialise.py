"""Initialize the supplied DVWA application, using only the private lab network."""
import http.cookiejar
import re
import time
import urllib.parse
import urllib.request

opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
for attempt in range(40):
    try:
        url = 'http://dvwa.dmz/setup.php'
        page = opener.open(url, timeout=5).read().decode()
        fields = {'create_db': 'Create / Reset Database'}
        tag = re.search(r'<input[^>]*name=[\'"]user_token[\'"][^>]*>', page, re.I)
        if tag:
            token = re.search(r'value=[\'"]([^\'"]+)', tag.group(), re.I)
            if token:
                fields['user_token'] = token.group(1)
        opener.open(url, urllib.parse.urlencode(fields).encode(), timeout=10).read()
        break
    except Exception:
        if attempt == 39:
            raise
        time.sleep(1)
