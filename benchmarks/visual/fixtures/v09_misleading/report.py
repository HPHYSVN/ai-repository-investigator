from parser import parse_count

def next_count(raw):
    count = parse_count(raw)
    return count + 1
