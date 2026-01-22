n = int(input())
A = list(map(int, input().split()))
total = sum(A)
if total != 0:
    print('YES')
    print(1)
    print(1, n)
else:
    x = -1
    for i, a in enumerate(A):
        if a != 0:
            x = i
            break
    if x == -1:
        print('NO')
    else:
        print('YES')
        if x == n-1:
            print(1)
            print(1, n)
        else:
            print(2)
            print(1, x+1)
            print(x+2, n)
