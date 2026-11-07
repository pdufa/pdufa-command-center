"""Temporary read-only market-cap fallback source format diagnostic."""
import re
import requests
from bs4 import BeautifulSoup

for ticker in ("CAPR","PHVS","ZBIO"):
    url=f"https://stockanalysis.com/stocks/{ticker.lower()}/market-cap/"
    try:
        resp=requests.get(url,timeout=18,headers={
          "User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
          "Accept":"text/html,application/xhtml+xml",
        })
        print("TICKER",ticker,"STATUS",resp.status_code,"LEN",len(resp.content),
              "URL_OK",resp.url==url,"TYPE",resp.headers.get("content-type","")[:80])
        soup=BeautifulSoup(resp.text,"html.parser")
        print("TITLE",soup.title.get_text(" ",strip=True)[:140] if soup.title else "")
        print("H1",[(h.name,h.get_text(" ",strip=True)[:160]) for h in soup.find_all(["h1","h2"])[:12]])
        title=soup.select_one("meta[property='og:title']")
        print("OG", title.get("content","")[:130] if title else None)
        t=soup.get_text(" ",strip=True)
        for word in ("Market Cap", "as of", "At close:", "Data Source:"):
            hits=list(re.finditer(re.escape(word),t,re.IGNORECASE))
            print("WORD",word,"HITS",len(hits),"CONTEXTS",[t[max(0,m.start()-55):m.start()+145] for m in hits[:4]])
        for tag in soup.find_all(string=re.compile(r"Market Cap",re.I))[:6]:
            print("TEXT_NODE",repr(str(tag)[:80]),"PARENT",str(tag.parent)[:600])
    except Exception as exc:
        print("ERROR",ticker,type(exc).__name__,str(exc)[:300])
