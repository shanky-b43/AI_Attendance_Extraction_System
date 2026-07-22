import re
import json

text = '''[
  ["281", "1", "G5", "23BIS70101", "Parwaaz Joshi", "205", "D3", "Absent"],
  ["282", "2", "G5", "23BCG10006", "Deepanshu Singh Rautela", "205", "D3", "Present"]
]
]
]
]
]'''

# Regex to find an array of exactly 8 strings
matches = re.findall(r'\[\s*(?:"(?:[^"\\]|\\.)*"\s*,\s*){7}"(?:[^"\\]|\\.)*"\s*\]', text)
for m in matches:
    print(json.loads(m))
