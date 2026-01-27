t = int(input())
for _ in range(t):
    n = int(input())
    a = list(map(int, input().split()))
    total = 1

    if 0 in a:
        result = 1
        zero = False
        for x in a:
            if x == 0 and not zero:
                zero = True
                continue
            else:
                result *= x
        print(result)
        continue
    for x in a:
        total *= x
    print(total // min(a) * (min(a)+1))