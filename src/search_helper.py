import urllib.request
import urllib.parse
import json

def search_duckduckgo(query, max_results=2):
    """
    Zero-dependency pure-Python DuckDuckGo API search.
    Requires no native C++ DLLs, immune to Windows Application Control blocks.
    """
    try:
        url = "https://api.duckduckgo.com/?q=" + urllib.parse.quote(query) + "&format=json&no_html=1&skip_disambig=1"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) wat-this/1.0"}
        )
        with urllib.request.urlopen(req, timeout=1.2) as response:
            data = json.loads(response.read().decode('utf-8', errors='ignore'))
            results = []
            if data.get("Abstract"):
                results.append(data["Abstract"])
            if len(results) < max_results:
                for topic in data.get("RelatedTopics", []):
                    if isinstance(topic, dict) and topic.get("Text"):
                        results.append(topic["Text"])
                        if len(results) >= max_results:
                            break
            return results
    except Exception:
        return []

if __name__ == "__main__":
    res = search_duckduckgo("React JavaScript")
    print(f"Results ({len(res)}):", res[0][:80] if res else "None")
