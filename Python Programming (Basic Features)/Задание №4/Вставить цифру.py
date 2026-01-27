t = int(input())
for _ in range(t):
    n, d = input().split()
    s = input()
    inserted = False
    res = []
    for c in s:
        if not inserted and c < d:
            res.append(d)
            inserted = True
        res.append(c)
    if not inserted:
        res.append(d)  
    print("".join(res))