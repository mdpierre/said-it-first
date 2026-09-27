---
title: "Parser bug"
date: "2025-06-01"
source: "chatgpt-export"
conversation_id: "5002e8bb-e70e-50aa-b63b-2844f45b9444"
user_turns: 1
user_words: 93
days_touched: 1
---

# Parser bug

## Me

Why does this throw? I want the parser to skip empty lines.

```python
def parse(lines):
    for line in lines:
        yield line.split(',')[1]
def parse(lines):
    for line in lines:
        yield line.split(',')[1]
def parse(lines):
    for line in lines:
        yield line.split(',')[1]
def parse(lines):
    for line in lines:
        yield line.split(',')[1]
def parse(lines):
    for line in lines:
        yield line.split(',')[1]
def parse(lines):
    for line in lines:
        yield line.split(',')[1]
```
It fails on the blank line at the end of the file every time.

### ChatGPT

```python
for line in lines:
    if line.strip(): ...
```
