
import requests
from bs4 import BeautifulSoup

url = "https://www.arthurmurray.com/locations/"
r = requests.get(url, timeout=30)
soup = BeautifulSoup(r.text, "html.parser")

print("HTTP status:", r.status_code)
print("Final URL:", r.url)
print("Page title:", soup.title.get_text(" ", strip=True) if soup.title else "NONE")
print("HTML length:", len(r.text))

for word in ["USA Locations", "Canada", "International", "Albuquerque"]:
    print(word, "found:", word.lower() in soup.get_text(" ", strip=True).lower())

print("Number of links:", len(soup.find_all("a", href=True)))
print("Number of headings:", len(soup.find_all(["h1", "h2", "h3", "h4"])))

for h in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
    title = h.get_text(" ", strip=True)
    if any(x in title.lower() for x in ["usa locations", "canada locations", "international", "albuquerque"]):
        print("HEADING:", repr(title), "TAG:", h.name, "PARENT:", h.parent.name if h.parent else "none")
