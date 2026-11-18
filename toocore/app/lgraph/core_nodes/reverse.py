

def hel(feed:str)->str:
    feed1=feed[::-1]
    feed2="".join(reversed(feed))

    feed3=""
    for ch in feed:feed3=ch+feed3
    return f"hel {feed1} {feed2} {feed3}"

print(hel("abcde"))